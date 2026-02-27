from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

import pytest

pytest.importorskip("django")

from asgiref.sync import iscoroutinefunction
from django.http import HttpRequest, HttpResponse

import diwire._internal.integrations.django as django_integration
from diwire import Container
from diwire.exceptions import DIWireIntegrationError
from tests._django_setup import ensure_django_setup

ensure_django_setup()


def _build_request(path: str = "/") -> HttpRequest:
    request = HttpRequest()
    request.path = path
    request.path_info = path
    return request


def test_get_request_raises_when_context_is_missing() -> None:
    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        django_integration.get_request()


def test_request_context_middleware_sets_context_for_sync_handler() -> None:
    request = _build_request("/middleware/context")

    def handler(current_request: HttpRequest) -> HttpResponse:
        resolved_request = django_integration.get_request()
        assert resolved_request is current_request
        return HttpResponse("ok")

    middleware = django_integration.RequestContextMiddleware(handler)
    response = middleware(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200


def test_request_context_middleware_resets_context_after_sync_success() -> None:
    request = _build_request("/middleware/success")

    def handler(_request: HttpRequest) -> HttpResponse:
        assert django_integration.get_request().path == "/middleware/success"
        return HttpResponse("ok")

    middleware = django_integration.RequestContextMiddleware(handler)
    _ = middleware(request)

    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        django_integration.get_request()


def test_request_context_middleware_resets_context_after_sync_exception() -> None:
    request = _build_request("/middleware/error")

    def handler(_request: HttpRequest) -> HttpResponse:
        assert django_integration.get_request().path == "/middleware/error"
        msg = "handler failed"
        raise RuntimeError(msg)

    middleware = django_integration.RequestContextMiddleware(handler)

    with pytest.raises(RuntimeError, match="handler failed"):
        _ = middleware(request)

    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        django_integration.get_request()


@pytest.mark.asyncio
async def test_request_context_middleware_sets_context_for_async_handler() -> None:
    request = _build_request("/middleware/async")

    async def handler(current_request: HttpRequest) -> HttpResponse:
        resolved_request = django_integration.get_request()
        assert resolved_request is current_request
        return HttpResponse("ok")

    middleware = django_integration.RequestContextMiddleware(handler)
    assert iscoroutinefunction(middleware)

    response = await cast("Awaitable[HttpResponse]", middleware(request))

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_request_context_middleware_resets_context_after_async_exception() -> None:
    request = _build_request("/middleware/async-error")

    async def handler(_request: HttpRequest) -> HttpResponse:
        assert django_integration.get_request().path == "/middleware/async-error"
        msg = "handler failed"
        raise RuntimeError(msg)

    middleware = django_integration.RequestContextMiddleware(handler)

    with pytest.raises(RuntimeError, match="handler failed"):
        _ = await cast("Awaitable[HttpResponse]", middleware(request))

    with pytest.raises(DIWireIntegrationError, match="Request context not available"):
        django_integration.get_request()


def test_add_request_context_registers_factory_for_container_resolution() -> None:
    container = Container()
    django_integration.add_request_context(container)

    request = _build_request("/container/request")
    token = django_integration._request_context.set(request)
    try:
        resolved_request = container.resolve(HttpRequest)
        assert resolved_request is request
    finally:
        django_integration._request_context.reset(token)
