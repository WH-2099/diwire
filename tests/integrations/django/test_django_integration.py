from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from json import loads
from types import TracebackType
from typing import TYPE_CHECKING, cast

import pytest
from typing_extensions import Self

pytest.importorskip("django")

from django.http import HttpRequest, HttpResponseBase, JsonResponse

from diwire import Container, Injected, Lifetime, Scope, resolver_context
from tests._django_setup import ensure_django_setup

if TYPE_CHECKING:
    from diwire.integrations.django import RequestContextMiddleware

ensure_django_setup()

_cleanup_paths: list[str] = []


def _latest_cleanup_path() -> str | None:
    if not _cleanup_paths:
        return None
    return _cleanup_paths[-1]


def _build_request(path: str) -> HttpRequest:
    request = HttpRequest()
    request.path = path
    request.path_info = path
    return request


def _json_body(response: HttpResponseBase) -> dict[str, str]:
    return cast("dict[str, str]", loads(response.content))


@dataclass
class _RequestPathService:
    request: HttpRequest

    def path(self) -> str:
        return self.request.path


@dataclass
class _CMService:
    request: HttpRequest

    def work(self) -> str:
        return "CMService working"

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        _cleanup_paths.append(self.request.path)


@pytest.fixture()
def handlers() -> dict[str, Callable[[HttpRequest], HttpResponseBase] | RequestContextMiddleware]:
    from diwire.integrations.django import RequestContextMiddleware, add_request_context

    _cleanup_paths.clear()

    container = Container()
    add_request_context(container)
    container.add(
        _RequestPathService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    container.add_context_manager(_CMService, scope=Scope.REQUEST)

    @resolver_context.inject(scope=Scope.REQUEST)
    def request_direct(
        request: HttpRequest,
        resolved_request: Injected[HttpRequest],
    ) -> JsonResponse:
        _ = request
        return JsonResponse({"path": resolved_request.path})

    @resolver_context.inject(scope=Scope.REQUEST)
    def request_service(
        request: HttpRequest,
        service: Injected[_RequestPathService],
    ) -> JsonResponse:
        _ = request
        return JsonResponse({"path": service.path()})

    @resolver_context.inject(scope=Scope.REQUEST)
    def cm_service(
        request: HttpRequest,
        service: Injected[_CMService],
    ) -> JsonResponse:
        _ = request
        return JsonResponse({"message": service.work()})

    @resolver_context.inject(scope=Scope.REQUEST)
    async def request_service_async(
        request: HttpRequest,
        service: Injected[_RequestPathService],
    ) -> JsonResponse:
        _ = request
        return JsonResponse({"path": service.path()})

    return {
        "request_direct": RequestContextMiddleware(request_direct),
        "request_service": RequestContextMiddleware(request_service),
        "cm_service": RequestContextMiddleware(cm_service),
        "request_service_async": RequestContextMiddleware(request_service_async),
    }


def test_request_resolve_for_http_endpoint(
    handlers: dict[str, Callable[[HttpRequest], HttpResponseBase] | RequestContextMiddleware],
) -> None:
    request = _build_request("/request/direct")
    handler = cast("Callable[[HttpRequest], HttpResponseBase]", handlers["request_direct"])
    response = handler(request)
    assert response.status_code == 200
    assert _json_body(response) == {"path": "/request/direct"}


def test_request_resolve_in_service_for_http_endpoint(
    handlers: dict[str, Callable[[HttpRequest], HttpResponseBase] | RequestContextMiddleware],
) -> None:
    request = _build_request("/request/service")
    handler = cast("Callable[[HttpRequest], HttpResponseBase]", handlers["request_service"])
    response = handler(request)
    assert response.status_code == 200
    assert _json_body(response) == {"path": "/request/service"}


def test_context_manager_service_validates_request_scope_cleanup_path(
    handlers: dict[str, Callable[[HttpRequest], HttpResponseBase] | RequestContextMiddleware],
) -> None:
    request = _build_request("/services/cm-service")
    handler = cast("Callable[[HttpRequest], HttpResponseBase]", handlers["cm_service"])
    response = handler(request)
    assert response.status_code == 200
    assert _json_body(response) == {"message": "CMService working"}
    assert _latest_cleanup_path() == "/services/cm-service"


@pytest.mark.asyncio
async def test_request_resolve_in_service_for_async_http_endpoint(
    handlers: dict[str, Callable[[HttpRequest], HttpResponseBase] | RequestContextMiddleware],
) -> None:
    request = _build_request("/request/service/async")
    handler = cast(
        "Callable[[HttpRequest], Awaitable[HttpResponseBase]]",
        handlers["request_service_async"],
    )
    response = await handler(request)
    assert response.status_code == 200
    assert _json_body(response) == {"path": "/request/service/async"}
