from __future__ import annotations

from contextvars import ContextVar
from typing import Any, cast

from starlette.requests import HTTPConnection, Request, StateT
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from diwire import Container, Lifetime
from diwire.exceptions import DIWireIntegrationError

_connection_context: ContextVar[HTTPConnection | None] = ContextVar(
    "diwire_fastapi_connection_context",
    default=None,
)


def get_connection(_state_t: type[StateT]) -> HTTPConnection[StateT]:
    connection = _connection_context.get()
    if connection is None:
        msg = "Connection context not available. Ensure RequestContextMiddleware is installed."
        raise DIWireIntegrationError(msg)
    return cast("HTTPConnection[StateT]", connection)


def get_request(_state_t: type[StateT]) -> Request[StateT]:
    connection = get_connection(_state_t)
    if not isinstance(connection, Request):
        msg = "Current connection is not HTTP Request."
        raise DIWireIntegrationError(msg)
    return cast("Request[StateT]", connection)


def _get_websocket_typed(_state_t: type[StateT]) -> WebSocket[StateT]:  # type: ignore[type-arg]
    connection = get_connection(_state_t)
    if not isinstance(connection, WebSocket):
        msg = "Current connection is not WebSocket."
        raise DIWireIntegrationError(msg)
    return cast("WebSocket[StateT]", connection)  # type: ignore[redundant-cast, type-arg]


def _get_websocket_untyped() -> WebSocket:
    connection = get_connection(Any)  # type: ignore[type-var]
    if not isinstance(connection, WebSocket):  # type: ignore[unreachable]
        msg = "Current connection is not WebSocket."
        raise DIWireIntegrationError(msg)
    return connection  # type: ignore[unreachable]


try:
    if StateT in WebSocket.__orig_bases__[0].__args__:  # type: ignore[attr-defined]
        get_websocket = _get_websocket_typed
    else:
        get_websocket = _get_websocket_untyped  # type: ignore[assignment]
except (AttributeError, IndexError, TypeError):
    # WebSocket does not have __orig_bases__ or is not generic, fallback to untyped version
    get_websocket = _get_websocket_untyped  # type: ignore[assignment]


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        scope_type = scope["type"]

        if scope_type == "http":
            connection: HTTPConnection = Request(scope, receive=receive)
        elif scope_type == "websocket":
            connection = WebSocket(scope, receive=receive, send=send)
        else:
            await self.app(scope, receive, send)
            return

        token = _connection_context.set(connection)

        try:
            await self.app(scope, receive, send)
        finally:
            _connection_context.reset(token)


def add_request_context(container: Container) -> None:
    container.add_factory(
        get_connection,
        provides=HTTPConnection,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add_factory(
        get_request,
        provides=Request,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add_factory(
        get_websocket,
        provides=WebSocket,
        lifetime=Lifetime.TRANSIENT,
    )
