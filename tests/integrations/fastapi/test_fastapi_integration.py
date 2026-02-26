from __future__ import annotations

from collections.abc import Iterator

import pytest

from diwire import Container, Injected, Lifetime, Scope, resolver_context
from diwire.integrations.fastapi import RequestContextMiddleware, add_request_context

pytest.importorskip("fastapi")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import State
from starlette.requests import Request
from starlette.websockets import WebSocket


class _RequestPathService:
    def __init__(self, request: Request[State]) -> None:
        self._request = request

    def path(self) -> str:
        return self._request.url.path


class _WebSocketPathService:
    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    def path(self) -> str:
        return self._websocket.url.path


@pytest.fixture()
def app() -> FastAPI:
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

    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/request/direct")
    @resolver_context.inject(scope=Scope.REQUEST)
    def request_direct(request: Injected[Request[State]]) -> dict[str, str]:
        return {"path": request.url.path}

    @app.get("/request/service")
    @resolver_context.inject(scope=Scope.REQUEST)
    def request_service(service: Injected[_RequestPathService]) -> dict[str, str]:
        return {"path": service.path()}

    @app.websocket("/websocket/direct")
    @resolver_context.inject(scope=Scope.REQUEST)
    async def websocket_direct(
        websocket: WebSocket,
        resolved_websocket: Injected[WebSocket],
    ) -> None:
        await websocket.accept()
        await websocket.send_json({"path": resolved_websocket.url.path})
        await websocket.close()

    @app.websocket("/websocket/service")
    @resolver_context.inject(scope=Scope.REQUEST)
    async def websocket_service(
        websocket: WebSocket,
        service: Injected[_WebSocketPathService],
    ) -> None:
        await websocket.accept()
        await websocket.send_json({"path": service.path()})
        await websocket.close()

    return app


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_request_resolve_for_http_endpoint(client: TestClient) -> None:
    response = client.get("/request/direct")
    assert response.status_code == 200
    assert response.json() == {"path": "/request/direct"}


def test_request_resolve_in_service_for_http_endpoint(client: TestClient) -> None:
    response = client.get("/request/service")
    assert response.status_code == 200
    assert response.json() == {"path": "/request/service"}


def test_websocket_resolve_for_websocket_endpoint(client: TestClient) -> None:
    with client.websocket_connect("/websocket/direct") as websocket:
        payload = websocket.receive_json()
    assert payload == {"path": "/websocket/direct"}


def test_websocket_resolve_in_service_for_websocket_endpoint(client: TestClient) -> None:
    with client.websocket_connect("/websocket/service") as websocket:
        payload = websocket.receive_json()
    assert payload == {"path": "/websocket/service"}
