from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import pytest

from diwire import Container, Injected, Lifetime, Scope, resolver_context

if TYPE_CHECKING:
    from aiohttp import web
    from aiohttp.test_utils import TestClient


@dataclass
class _RequestPathService:
    request: web.Request

    def path(self) -> str:
        return self.request.path


@dataclass
class _WebSocketPathService:
    request: web.Request

    def path(self) -> str:
        return self.request.path


@pytest.fixture()
def app() -> web.Application:
    pytest.importorskip("aiohttp")

    from aiohttp import web

    from diwire.integrations.aiohttp import add_request_context, request_context_middleware

    # diwire resolves dependencies via runtime type hints; populate module globals so
    # forward references like `web.Request` can be evaluated.
    globals()["web"] = web

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

    app = web.Application(middlewares=[request_context_middleware])

    @resolver_context.inject(scope=Scope.REQUEST)
    async def request_direct(
        request: web.Request,
        resolved_request: Injected[web.Request],
    ) -> web.StreamResponse:
        return web.json_response({"path": resolved_request.path})

    @resolver_context.inject(scope=Scope.REQUEST)
    async def request_service(
        request: web.Request,
        service: Injected[_RequestPathService],
    ) -> web.StreamResponse:
        return web.json_response({"path": service.path()})

    @resolver_context.inject(scope=Scope.REQUEST)
    async def websocket_direct(
        request: web.Request,
        resolved_request: Injected[web.Request],
    ) -> web.StreamResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({"path": resolved_request.path})
        await ws.close()
        return ws

    @resolver_context.inject(scope=Scope.REQUEST)
    async def websocket_service(
        request: web.Request,
        service: Injected[_WebSocketPathService],
    ) -> web.StreamResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({"path": service.path()})
        await ws.close()
        return ws

    app.add_routes(
        [
            web.get(
                "/request/direct",
                cast("Callable[[web.Request], Awaitable[web.StreamResponse]]", request_direct),
            ),
            web.get(
                "/request/service",
                cast("Callable[[web.Request], Awaitable[web.StreamResponse]]", request_service),
            ),
            web.get(
                "/websocket/direct",
                cast("Callable[[web.Request], Awaitable[web.StreamResponse]]", websocket_direct),
            ),
            web.get(
                "/websocket/service",
                cast("Callable[[web.Request], Awaitable[web.StreamResponse]]", websocket_service),
            ),
        ]
    )
    return app


@pytest.fixture()
async def client(app: web.Application) -> AsyncIterator[TestClient[web.Request, web.Application]]:
    pytest.importorskip("aiohttp")

    from aiohttp.test_utils import TestClient, TestServer

    async with TestServer(app) as server:
        async with TestClient(server) as test_client:
            yield test_client


@pytest.mark.asyncio
async def test_request_resolve_for_http_endpoint(
    client: TestClient[web.Request, web.Application],
) -> None:
    response = await client.get("/request/direct")
    assert response.status == 200
    assert await response.json() == {"path": "/request/direct"}


@pytest.mark.asyncio
async def test_request_resolve_in_service_for_http_endpoint(
    client: TestClient[web.Request, web.Application],
) -> None:
    response = await client.get("/request/service")
    assert response.status == 200
    assert await response.json() == {"path": "/request/service"}


@pytest.mark.asyncio
async def test_websocket_resolve_for_websocket_endpoint(
    client: TestClient[web.Request, web.Application],
) -> None:
    websocket = await client.ws_connect("/websocket/direct")
    payload = await websocket.receive_json()
    assert payload == {"path": "/websocket/direct"}
    await websocket.close()


@pytest.mark.asyncio
async def test_websocket_resolve_in_service_for_websocket_endpoint(
    client: TestClient[web.Request, web.Application],
) -> None:
    websocket = await client.ws_connect("/websocket/service")
    payload = await websocket.receive_json()
    assert payload == {"path": "/websocket/service"}
    await websocket.close()
