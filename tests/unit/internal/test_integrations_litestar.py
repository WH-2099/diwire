from __future__ import annotations

from typing import Any, TypeAlias, cast

import pytest

pytest.importorskip("litestar")

from litestar.connection import ASGIConnection, Request, WebSocket
from litestar.datastructures.state import State
from litestar.enums import ScopeType
from litestar.types.asgi_types import HTTPScope, WebSocketScope

import diwire._internal.integrations.litestar as litestar_integration
from diwire import Container
from diwire.exceptions import DIWireIntegrationError

LitestarConnection: TypeAlias = ASGIConnection[object, object, object, State]
LitestarRequest: TypeAlias = Request[object, object, State]
LitestarWebSocket: TypeAlias = WebSocket[object, object, State]


def _build_http_scope(path: str = "/") -> HTTPScope:
    return cast(
        "HTTPScope",
        {
            "type": ScopeType.HTTP,
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "state": {},
        },
    )


def _build_websocket_scope(path: str = "/ws") -> WebSocketScope:
    return cast(
        "WebSocketScope",
        {
            "type": ScopeType.WEBSOCKET,
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "scheme": "ws",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "subprotocols": [],
            "state": {},
        },
    )


def _request_for_scope(path: str = "/") -> Request[object, object, State]:
    return Request(_build_http_scope(path))


def _websocket_for_scope(path: str = "/ws") -> WebSocket[object, object, State]:
    async def _receive() -> Any:
        return {"type": "websocket.disconnect", "code": 1000}

    async def _send(_message: Any) -> None:
        return None

    return WebSocket(
        _build_websocket_scope(path),
        receive=_receive,
        send=_send,
    )


def test_get_connection_raises_when_context_is_missing() -> None:
    with pytest.raises(DIWireIntegrationError, match="Connection context not available"):
        litestar_integration.get_connection(object, object, object, State)


def test_get_request_raises_when_current_connection_is_not_http_request() -> None:
    token = litestar_integration._connection_context.set(_websocket_for_scope("/websocket"))
    try:
        with pytest.raises(DIWireIntegrationError, match="not HTTP Request"):
            litestar_integration.get_request(object, object, State)
    finally:
        litestar_integration._connection_context.reset(token)


def test_get_websocket_raises_when_current_connection_is_not_websocket() -> None:
    token = litestar_integration._connection_context.set(_request_for_scope("/request"))
    try:
        with pytest.raises(DIWireIntegrationError, match="not WebSocket"):
            litestar_integration.get_websocket(object, object, State)
    finally:
        litestar_integration._connection_context.reset(token)


def test_get_request_returns_current_http_request_connection() -> None:
    request = _request_for_scope("/request")
    token = litestar_integration._connection_context.set(request)
    try:
        resolved = litestar_integration.get_request(object, object, State)
        assert resolved is request
    finally:
        litestar_integration._connection_context.reset(token)


def test_get_websocket_returns_current_websocket_connection() -> None:
    websocket = _websocket_for_scope("/websocket")
    token = litestar_integration._connection_context.set(websocket)
    try:
        resolved = litestar_integration.get_websocket(object, object, State)
        assert resolved is websocket
    finally:
        litestar_integration._connection_context.reset(token)


@pytest.mark.asyncio
async def test_request_context_middleware_sets_http_request_context() -> None:
    observed_path: str | None = None

    async def app(_scope: Any, _receive: Any, _send: Any) -> None:
        nonlocal observed_path
        observed_path = litestar_integration.get_request(object, object, State).url.path

    middleware = litestar_integration.RequestContextMiddleware()
    wrapped_app = middleware(app)
    scope = _build_http_scope("/middleware/http")

    async def receive() -> Any:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message: Any) -> None:
        return None

    await wrapped_app(scope, receive, send)

    assert observed_path == "/middleware/http"


@pytest.mark.asyncio
async def test_request_context_middleware_sets_websocket_context() -> None:
    observed_path: str | None = None

    async def app(_scope: Any, _receive: Any, _send: Any) -> None:
        nonlocal observed_path
        observed_path = litestar_integration.get_websocket(object, object, State).url.path

    middleware = litestar_integration.RequestContextMiddleware()
    wrapped_app = middleware(app)
    scope = _build_websocket_scope("/middleware/websocket")

    async def receive() -> Any:
        return {"type": "websocket.connect"}

    async def send(_message: Any) -> None:
        return None

    await wrapped_app(scope, receive, send)

    assert observed_path == "/middleware/websocket"


@pytest.mark.asyncio
async def test_request_context_middleware_resets_context_after_exception() -> None:
    async def app(_scope: Any, _receive: Any, _send: Any) -> None:
        assert (
            litestar_integration.get_request(object, object, State).url.path == "/middleware/error"
        )
        msg = "handler failed"
        raise RuntimeError(msg)

    middleware = litestar_integration.RequestContextMiddleware()
    wrapped_app = middleware(app)
    scope = _build_http_scope("/middleware/error")

    async def receive() -> Any:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message: Any) -> None:
        return None

    with pytest.raises(RuntimeError, match="handler failed"):
        await wrapped_app(scope, receive, send)

    with pytest.raises(DIWireIntegrationError, match="Connection context not available"):
        litestar_integration.get_connection(object, object, object, State)


def test_add_request_context_registers_factories_for_container_resolution() -> None:
    container = Container()
    litestar_integration.add_request_context(container)

    request = _request_for_scope("/container/request")
    request_token = litestar_integration._connection_context.set(request)
    try:
        resolved_connection = container.resolve(LitestarConnection)
        resolved_request = container.resolve(LitestarRequest)
        assert resolved_connection is request
        assert resolved_request is request
    finally:
        litestar_integration._connection_context.reset(request_token)

    websocket = _websocket_for_scope("/container/websocket")
    websocket_token = litestar_integration._connection_context.set(websocket)
    try:
        resolved_websocket = container.resolve(LitestarWebSocket)
        assert resolved_websocket is websocket
    finally:
        litestar_integration._connection_context.reset(websocket_token)
