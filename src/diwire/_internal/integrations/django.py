from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import TypeAlias, cast

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpRequest, HttpResponseBase

from diwire import Container, Lifetime
from diwire.exceptions import DIWireIntegrationError

_request_context: ContextVar[HttpRequest | None] = ContextVar(
    "diwire_django_request_context",
    default=None,
)

_GetResponseSync: TypeAlias = Callable[..., HttpResponseBase]
_GetResponseAsync: TypeAlias = Callable[..., Awaitable[HttpResponseBase]]


def get_request() -> HttpRequest:
    request = _request_context.get()
    if request is None:
        msg = "Request context not available. Ensure RequestContextMiddleware is installed."
        raise DIWireIntegrationError(msg)
    return request


class RequestContextMiddleware:
    sync_capable = True
    async_capable = True

    def __init__(
        self,
        get_response: _GetResponseSync | _GetResponseAsync,
    ) -> None:
        self.get_response = get_response
        self._is_async = iscoroutinefunction(get_response)
        if self._is_async:
            markcoroutinefunction(self)

    def __call__(
        self,
        request: HttpRequest,
    ) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        if self._is_async:
            return self._call_async(request)
        return self._call_sync(request)

    def _call_sync(self, request: HttpRequest) -> HttpResponseBase:
        token = _request_context.set(request)
        try:
            return cast("_GetResponseSync", self.get_response)(request)
        finally:
            _request_context.reset(token)

    async def _call_async(self, request: HttpRequest) -> HttpResponseBase:
        token = _request_context.set(request)
        try:
            return await cast("_GetResponseAsync", self.get_response)(request)
        finally:
            _request_context.reset(token)


def add_request_context(container: Container) -> None:
    container.add_factory(
        get_request,
        provides=HttpRequest,
        lifetime=Lifetime.TRANSIENT,
    )
