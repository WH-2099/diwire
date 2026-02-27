from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import TracebackType
from typing import Any, cast
from uuid import uuid4

import pytest
from typing_extensions import Self

from diwire import Container, Injected, Lifetime, Scope, resolver_context


@dataclass(frozen=True)
class _Calculator:
    offset: int

    def add(self, left: int, right: int) -> int:
        return left + right + self.offset


def _build_calculator() -> _Calculator:
    return _Calculator(offset=3)


@dataclass(frozen=True)
class _ScopedToken:
    value: str


def _build_scoped_token() -> _ScopedToken:
    return _ScopedToken(value=uuid4().hex)


@dataclass
class _ScopedCleanupResource:
    closed_values: list[str]
    value: str

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.closed_values.append(self.value)


def test_resolver_context_injected_task_resolves_injected_parameters_for_sync_callable() -> None:
    container = Container()
    container.add_factory(_build_calculator, provides=_Calculator)

    @resolver_context.inject(scope=Scope.REQUEST)
    def task(left: int, right: int, calculator: Injected[_Calculator]) -> int:
        return calculator.add(left, right)

    injected_task = cast("Any", task)
    assert injected_task(5, 7) == 15


def test_resolver_context_injected_task_hides_injected_parameters_in_public_signature() -> None:
    container = Container()
    container.add_factory(_build_calculator, provides=_Calculator)

    @resolver_context.inject(scope=Scope.REQUEST)
    def task(left: int, right: int, calculator: Injected[_Calculator]) -> int:
        return calculator.add(left, right)

    parameter_names = tuple(inspect.signature(task).parameters)
    assert parameter_names == ("left", "right")


def test_resolver_context_injected_task_keeps_explicit_parameter_values() -> None:
    container = Container()
    container.add_factory(_build_calculator, provides=_Calculator)

    @resolver_context.inject(scope=Scope.REQUEST)
    def task(left: int, right: int, calculator: Injected[_Calculator]) -> int:
        return calculator.add(left, right)

    injected_task = cast("Any", task)
    explicit_calculator = _Calculator(offset=100)
    assert injected_task(2, 3, calculator=explicit_calculator) == 105


def test_resolver_context_injected_task_preserves_scope_isolation_per_invocation() -> None:
    container = Container()
    closed_values: list[str] = []
    container.add_factory(
        _build_scoped_token,
        provides=_ScopedToken,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    def _provide_cleanup_resource(token: _ScopedToken) -> _ScopedCleanupResource:
        return _ScopedCleanupResource(closed_values=closed_values, value=token.value)

    container.add_context_manager(
        _provide_cleanup_resource,
        provides=_ScopedCleanupResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    @resolver_context.inject(scope=Scope.REQUEST)
    def task(
        first: Injected[_ScopedToken],
        second: Injected[_ScopedToken],
        cleanup_resource: Injected[_ScopedCleanupResource],
    ) -> tuple[str, str, str]:
        return (first.value, second.value, cleanup_resource.value)

    injected_task = cast("Any", task)
    first = injected_task()
    second = injected_task()

    assert first[0] == first[1] == first[2]
    assert second[0] == second[1] == second[2]
    assert first[0] != second[0]
    assert closed_values == [first[0], second[0]]


@pytest.mark.asyncio
async def test_resolver_context_injected_task_resolves_injected_parameters_for_async_callable() -> (
    None
):
    container = Container()
    container.add_factory(_build_calculator, provides=_Calculator)

    @resolver_context.inject(scope=Scope.REQUEST)
    async def task(left: int, right: int, calculator: Injected[_Calculator]) -> int:
        return calculator.add(left, right)

    injected_task = cast("Any", task)
    assert await injected_task(4, 9) == 16
