from __future__ import annotations

import os
import time
from collections.abc import Generator
from typing import Any

import pytest

_BROKER_URL_ENV = "CELERY_E2E_BROKER_URL"
_RESULT_BACKEND_ENV = "CELERY_E2E_RESULT_BACKEND"
_QUEUE_ENV = "CELERY_E2E_QUEUE"

if os.getenv(_BROKER_URL_ENV) is None or os.getenv(_RESULT_BACKEND_ENV) is None:
    pytest.skip(
        (
            f"{_BROKER_URL_ENV} or {_RESULT_BACKEND_ENV} is not set; "
            "skipping docker-compose Celery e2e tests."
        ),
        allow_module_level=True,
    )


def _wait_for_worker(app: Any, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if app.control.ping(timeout=1.0):
            return
        time.sleep(0.25)
    msg = "Timed out waiting for Celery worker to become available."
    raise AssertionError(msg)


@pytest.fixture(scope="module")
def app() -> Generator[Any]:
    pytest.importorskip("celery")
    from tests.e2e.celery.setup.app import app as celery_app

    _wait_for_worker(celery_app, timeout_seconds=20.0)
    return celery_app


def _dispatch(app: Any, task_name: str, *args: Any) -> Any:
    result = app.send_task(task_name, args=args, queue=os.getenv(_QUEUE_ENV, "diwire-e2e"))
    return result.get(timeout=20.0)


def test_task_resolves_injected_dependency(app: Any) -> None:
    payload = _dispatch(app, "tests.e2e.celery.tasks.add", 4, 6)
    assert payload == 10


def test_task_uses_scoped_lifetime_per_invocation(app: Any) -> None:
    first = _dispatch(app, "tests.e2e.celery.tasks.scope")
    second = _dispatch(app, "tests.e2e.celery.tasks.scope")

    assert first["first"] == first["second"]
    assert second["first"] == second["second"]
    assert first["first"] != second["first"]


def test_bound_task_keeps_task_instance_and_injects_dependencies(app: Any) -> None:
    payload = _dispatch(app, "tests.e2e.celery.tasks.bound", 9)
    assert payload == "tests.e2e.celery.tasks.bound:10"
