from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

pytest.importorskip("celery")

from celery import Celery, Task

from diwire import Container, Injected, Lifetime, Scope, resolver_context


@dataclass(frozen=True)
class _AdderService:
    def add(self, left: int, right: int) -> int:
        return left + right


@dataclass(frozen=True)
class _ScopedToken:
    value: str


def _build_scoped_token() -> _ScopedToken:
    return _ScopedToken(value=uuid4().hex)


@pytest.fixture()
def celery_app() -> Celery:
    container = Container()
    container.add(_AdderService, provides=_AdderService)
    container.add_factory(
        _build_scoped_token,
        provides=_ScopedToken,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    app = Celery("diwire-tests", broker="memory://", backend="cache+memory://")
    app.conf.update(
        task_always_eager=True,
        task_store_eager_result=True,
        task_eager_propagates=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )

    @app.task(name="diwire.tests.add")
    @resolver_context.inject(scope=Scope.REQUEST)
    def add_task(left: int, right: int, adder: Injected[_AdderService]) -> int:
        return adder.add(left, right)

    @app.task(name="diwire.tests.scope")
    @resolver_context.inject(scope=Scope.REQUEST)
    def scoped_token_task(
        first: Injected[_ScopedToken],
        second: Injected[_ScopedToken],
    ) -> dict[str, str]:
        return {"first": first.value, "second": second.value}

    @app.task(bind=True, name="diwire.tests.bound")
    @resolver_context.inject(scope=Scope.REQUEST)
    def bound_task(
        task: Task,
        value: int,
        adder: Injected[_AdderService],
    ) -> str:
        return f"{task.name}:{adder.add(value, 1)}"

    return app


def test_celery_task_resolves_injected_dependencies(celery_app: Celery) -> None:
    result = celery_app.tasks["diwire.tests.add"].delay(4, 6)
    assert result.get(timeout=5.0) == 10


def test_celery_task_scoped_dependency_reused_per_task_and_isolated_between_tasks(
    celery_app: Celery,
) -> None:
    first = celery_app.tasks["diwire.tests.scope"].delay().get(timeout=5.0)
    second = celery_app.tasks["diwire.tests.scope"].delay().get(timeout=5.0)

    assert first["first"] == first["second"]
    assert second["first"] == second["second"]
    assert first["first"] != second["first"]


def test_celery_bound_task_keeps_self_argument_and_injects_dependencies(celery_app: Celery) -> None:
    result = celery_app.tasks["diwire.tests.bound"].delay(9)
    assert result.get(timeout=5.0) == "diwire.tests.bound:10"
