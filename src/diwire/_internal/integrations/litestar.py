from __future__ import annotations

from contextvars import ContextVar
from typing import Any, cast

from litestar.connection import ASGIConnection, Request, WebSocket
from litestar.connection.base import (
    AuthT,
    HandlerT,
    StateT,
    UserT,
)
from litestar.datastructures.state import State
from litestar.enums import ScopeType
from litestar.types import ASGIApp
from litestar.types.asgi_types import HTTPScope, Receive, Scope, Send, WebSocketScope

from diwire import Container, Lifetime
from diwire.exceptions import DIWireIntegrationError

_connection_context: ContextVar[ASGIConnection[Any, Any, Any, State] | None] = ContextVar(
    "diwire_litestar_connection_context",
    default=None,
)


def get_connection(
    _handler_t: type[HandlerT],
    _user_t: type[UserT],
    _auth_t: type[AuthT],
    _state_t: type[StateT],
) -> ASGIConnection[HandlerT, UserT, AuthT, StateT]:
    connection = _connection_context.get()
    if connection is None:
        msg = (
            "Connection context not available. Ensure RequestContextMiddleware() is installed via "
            "middleware=[RequestContextMiddleware()]."
        )
        raise DIWireIntegrationError(msg)
    return cast(
        "ASGIConnection[HandlerT, UserT, AuthT, StateT]",
        connection,
    )


def get_request(
    _user_t: type[UserT],
    _auth_t: type[AuthT],
    _state_t: type[StateT],
) -> Request[UserT, AuthT, StateT]:
    connection = get_connection(object, object, object, State)
    if not isinstance(connection, Request):
        msg = "Current connection is not HTTP Request."
        raise DIWireIntegrationError(msg)
    return cast("Request[UserT, AuthT, StateT]", connection)


def get_websocket(
    _user_t: type[UserT],
    _auth_t: type[AuthT],
    _state_t: type[StateT],
) -> WebSocket[UserT, AuthT, StateT]:
    connection = get_connection(object, object, object, State)
    if not isinstance(connection, WebSocket):
        msg = "Current connection is not WebSocket."
        raise DIWireIntegrationError(msg)
    return cast("WebSocket[UserT, AuthT, StateT]", connection)


class RequestContextMiddleware:
    def __call__(self, app: ASGIApp) -> ASGIApp:
        async def middleware(
            scope: Scope,
            receive: Receive,
            send: Send,
        ) -> None:
            scope_type = scope["type"]

            if scope_type == ScopeType.HTTP:
                connection: ASGIConnection[Any, Any, Any, State] = Request(
                    cast("HTTPScope", scope),
                    receive=receive,
                    send=send,
                )
            else:
                connection = WebSocket(
                    cast("WebSocketScope", scope),
                    receive=receive,
                    send=send,
                )

            token = _connection_context.set(connection)

            try:
                await app(scope, receive, send)
            finally:
                _connection_context.reset(token)

        return middleware


def add_request_context(container: Container) -> None:
    container.add_factory(
        get_connection,
        provides=ASGIConnection,
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
