from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from aiohttp import web

from diwire import Container, Lifetime
from diwire.exceptions import DIWireIntegrationError

_request_context: ContextVar[web.Request | None] = ContextVar(
    "diwire_aiohttp_request_context",
    default=None,
)


def get_request() -> web.Request:
    request = _request_context.get()
    if request is None:
        msg = (
            "Request context not available. Ensure request_context_middleware is installed via "
            "app = web.Application(middlewares=[request_context_middleware])."
        )
        raise DIWireIntegrationError(msg)
    return request


@web.middleware
async def request_context_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    token = _request_context.set(request)
    try:
        return await handler(request)
    finally:
        _request_context.reset(token)


def add_request_context(container: Container) -> None:
    container.add_factory(
        get_request,
        provides=web.Request,
        lifetime=Lifetime.TRANSIENT,
    )
