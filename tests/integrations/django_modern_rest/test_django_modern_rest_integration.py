from collections.abc import Iterator
from dataclasses import dataclass
from json import loads
from typing import cast

import pytest

pytest.importorskip("django")
pytest.importorskip("dmr")
pytest.importorskip("pydantic")

from django.http import HttpRequest, HttpResponseBase
from django.test import override_settings
from django.urls import path
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRClient
from pydantic import BaseModel

from diwire import Container, Injected, Lifetime, Scope, resolver_context
from diwire.integrations.django import add_request_context
from tests._django_setup import ensure_django_setup

ensure_django_setup()


def _json_body(response: HttpResponseBase) -> dict[str, str]:
    content = cast("bytes", response.content)
    return cast("dict[str, str]", loads(content))


class _PathResponse(BaseModel):
    path: str


@dataclass
class _RequestPathService:
    request: HttpRequest

    def path(self) -> str:
        return self.request.path


_container = Container()
add_request_context(_container)
_container.add(
    _RequestPathService,
    scope=Scope.REQUEST,
    lifetime=Lifetime.SCOPED,
)


class _DirectRequestController(Controller[PydanticSerializer]):
    @resolver_context.inject(scope=Scope.REQUEST)
    def get(self, request: Injected[HttpRequest]) -> _PathResponse:
        return _PathResponse(path=request.path)


class _RequestServiceController(Controller[PydanticSerializer]):
    @resolver_context.inject(scope=Scope.REQUEST)
    def get(self, service: Injected[_RequestPathService]) -> _PathResponse:
        return _PathResponse(path=service.path())


urlpatterns = [
    path("request/direct/", _DirectRequestController.as_view()),
    path("request/service/", _RequestServiceController.as_view()),
]


@pytest.fixture()
def client() -> Iterator[DMRClient]:
    with override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=["diwire.integrations.django.RequestContextMiddleware"],
    ):
        yield DMRClient()


def test_request_resolve_for_controller_endpoint(client: DMRClient) -> None:
    response = client.get("/request/direct/")
    assert response.status_code == 200
    assert _json_body(response) == {"path": "/request/direct/"}


def test_request_resolve_in_service_for_controller_endpoint(client: DMRClient) -> None:
    response = client.get("/request/service/")
    assert response.status_code == 200
    assert _json_body(response) == {"path": "/request/service/"}
