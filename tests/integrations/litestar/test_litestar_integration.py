from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

import pytest

from diwire import Container, Injected, Lifetime, Scope, resolver_context

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.connection import Request, WebSocket
    from litestar.datastructures.state import State
    from litestar.testing import TestClient

LitestarRequest: TypeAlias = "Request[object, object, State]"
LitestarWebSocket: TypeAlias = "WebSocket[object, object, State]"


@dataclass
class _RequestPathService:
    request: LitestarRequest

    def path(self) -> str:
        return self.request.url.path


@dataclass
class _WebSocketPathService:
    websocket: LitestarWebSocket

    def path(self) -> str:
        return self.websocket.url.path


@pytest.fixture()
def app() -> Litestar:
    pytest.importorskip("litestar")

    from litestar import Litestar, get, websocket
    from litestar.connection import Request, WebSocket
    from litestar.datastructures.state import State

    from diwire.integrations.litestar import RequestContextMiddleware, add_request_context

    # diwire resolves dependencies via runtime type hints; populate module globals so
    # forward references like `Request[object, object, State]` can be evaluated.
    globals()["Request"] = Request
    globals()["WebSocket"] = WebSocket
    globals()["State"] = State

    container = Container()
    add_request_context(container)
    container.add(
        _RequestPathService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    container.add(
        _WebSocketPathService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    @get("/request/direct")
    @resolver_context.inject(scope=Scope.REQUEST)
    async def request_direct(
        request: LitestarRequest,
        resolved_request: Injected[LitestarRequest],
    ) -> dict[str, str]:
        _ = request
        return {"path": resolved_request.url.path}

    @get("/request/service")
    @resolver_context.inject(scope=Scope.REQUEST)
    async def request_service(service: Injected[_RequestPathService]) -> dict[str, str]:
        return {"path": service.path()}

    @websocket("/websocket/direct")
    @resolver_context.inject(scope=Scope.REQUEST)
    async def websocket_direct(
        socket: LitestarWebSocket,
        resolved_websocket: Injected[LitestarWebSocket],
    ) -> None:
        await socket.accept()
        await socket.send_json({"path": resolved_websocket.url.path})
        await socket.close()

    @websocket("/websocket/service")
    @resolver_context.inject(scope=Scope.REQUEST)
    async def websocket_service(
        socket: LitestarWebSocket,
        service: Injected[_WebSocketPathService],
    ) -> None:
        await socket.accept()
        await socket.send_json({"path": service.path()})
        await socket.close()

    return Litestar(
        route_handlers=[
            request_direct,
            request_service,
            websocket_direct,
            websocket_service,
        ],
        middleware=[RequestContextMiddleware()],
    )


@pytest.fixture()
def client(app: Litestar) -> Iterator[TestClient[Litestar]]:
    pytest.importorskip("litestar")

    from litestar.testing import TestClient

    with TestClient(app) as test_client:
        yield test_client


def test_request_resolve_for_http_endpoint(client: TestClient[Litestar]) -> None:
    response = client.get("/request/direct")
    assert response.status_code == 200
    assert response.json() == {"path": "/request/direct"}


def test_request_resolve_in_service_for_http_endpoint(client: TestClient[Litestar]) -> None:
    response = client.get("/request/service")
    assert response.status_code == 200
    assert response.json() == {"path": "/request/service"}


def test_websocket_resolve_for_websocket_endpoint(client: TestClient[Litestar]) -> None:
    with client.websocket_connect("/websocket/direct") as websocket:
        payload = websocket.receive_json()
    assert payload == {"path": "/websocket/direct"}


def test_websocket_resolve_in_service_for_websocket_endpoint(client: TestClient[Litestar]) -> None:
    with client.websocket_connect("/websocket/service") as websocket:
        payload = websocket.receive_json()
    assert payload == {"path": "/websocket/service"}
