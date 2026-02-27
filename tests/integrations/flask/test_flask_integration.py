from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING

import pytest
from typing_extensions import Self

from diwire import Container, Injected, Lifetime, Scope, resolver_context

if TYPE_CHECKING:
    from flask import Flask, Request
    from flask.testing import FlaskClient

_cleanup_paths: list[str] = []


def _latest_cleanup_path() -> str | None:
    if not _cleanup_paths:
        return None
    return _cleanup_paths[-1]


@dataclass
class _RequestPathService:
    request: Request

    def path(self) -> str:
        return self.request.path


@dataclass
class _CMService:
    request: Request

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
def app() -> Flask:
    pytest.importorskip("flask")

    from flask import Flask, Request

    from diwire.integrations.flask import add_request_context

    globals()["Request"] = Request
    _cleanup_paths.clear()

    container = Container()
    add_request_context(container)
    container.add(
        _RequestPathService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    container.add_context_manager(_CMService, scope=Scope.REQUEST)

    app = Flask(__name__)

    @app.get("/request/direct")
    @resolver_context.inject(scope=Scope.REQUEST)
    def request_direct(request: Injected[Request]) -> dict[str, str]:
        return {"path": request.path}

    @app.get("/request/service")
    @resolver_context.inject(scope=Scope.REQUEST)
    def request_service(service: Injected[_RequestPathService]) -> dict[str, str]:
        return {"path": service.path()}

    @app.get("/services/cm-service")
    @resolver_context.inject(scope=Scope.REQUEST)
    def cm_service(service: Injected[_CMService]) -> dict[str, str]:
        return {"message": service.work()}

    @app.get("/services/cm-service/cleanup")
    def cm_service_cleanup() -> dict[str, str | None]:
        return {"path": _latest_cleanup_path()}

    return app


@pytest.fixture()
def client(app: Flask) -> Iterator[FlaskClient]:
    with app.test_client() as test_client:
        yield test_client


def test_request_resolve_for_http_endpoint(client: FlaskClient) -> None:
    response = client.get("/request/direct")
    assert response.status_code == 200
    assert response.json == {"path": "/request/direct"}


def test_request_resolve_in_service_for_http_endpoint(client: FlaskClient) -> None:
    response = client.get("/request/service")
    assert response.status_code == 200
    assert response.json == {"path": "/request/service"}


def test_context_manager_service_validates_request_scope_cleanup_path(client: FlaskClient) -> None:
    response = client.get("/services/cm-service")
    assert response.status_code == 200
    assert response.json == {"message": "CMService working"}

    cleanup_response = client.get("/services/cm-service/cleanup")
    assert cleanup_response.status_code == 200
    assert cleanup_response.json == {"path": "/services/cm-service"}
