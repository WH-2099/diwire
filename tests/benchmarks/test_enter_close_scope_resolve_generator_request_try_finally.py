from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dishka import Provider

from diwire import Lifetime, Scope
from tests.benchmarks.dishka_helpers import DishkaBenchmarkScope, make_dishka_benchmark_container
from tests.benchmarks.helpers import make_diwire_benchmark_container, run_benchmark


class _RequestResource:
    pass


def test_benchmark_diwire_enter_close_scope_resolve_generator_request_try_finally(
    benchmark: Any,
) -> None:
    cleanup_count = 0

    def build_request_resource() -> Generator[_RequestResource, None, None]:
        nonlocal cleanup_count
        resource = _RequestResource()
        try:
            yield resource
        finally:
            cleanup_count += 1

    container = make_diwire_benchmark_container()
    container.add_generator(
        build_request_resource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    container.compile()

    with container.enter_scope(Scope.REQUEST) as first_scope:
        first = first_scope.resolve(_RequestResource)
        second = first_scope.resolve(_RequestResource)
    assert first is second
    assert cleanup_count == 1

    with container.enter_scope(Scope.REQUEST) as second_scope:
        third = second_scope.resolve(_RequestResource)
    assert first is not third
    assert cleanup_count == 2

    def bench_diwire_enter_close_scope_resolve_generator_request_try_finally() -> None:
        with container.enter_scope(Scope.REQUEST) as scope:
            _ = scope.resolve(_RequestResource)

    run_benchmark(
        benchmark,
        bench_diwire_enter_close_scope_resolve_generator_request_try_finally,
        iterations=25_000,
    )


def test_benchmark_dishka_enter_close_scope_resolve_generator_request_try_finally(
    benchmark: Any,
) -> None:
    cleanup_count = 0

    def build_request_resource() -> Generator[_RequestResource, None, None]:
        nonlocal cleanup_count
        resource = _RequestResource()
        try:
            yield resource
        finally:
            cleanup_count += 1

    provider = Provider(scope=DishkaBenchmarkScope.APP)
    provider.provide(
        build_request_resource,
        scope=DishkaBenchmarkScope.REQUEST,
    )
    container = make_dishka_benchmark_container(provider)

    with container(scope=DishkaBenchmarkScope.REQUEST) as first_scope:
        first = first_scope.get(_RequestResource)
        second = first_scope.get(_RequestResource)
    assert first is second
    assert cleanup_count == 1

    with container(scope=DishkaBenchmarkScope.REQUEST) as second_scope:
        third = second_scope.get(_RequestResource)
    assert first is not third
    assert cleanup_count == 2

    def bench_dishka_enter_close_scope_resolve_generator_request_try_finally() -> None:
        with container(scope=DishkaBenchmarkScope.REQUEST) as scope:
            _ = scope.get(_RequestResource)

    run_benchmark(
        benchmark,
        bench_dishka_enter_close_scope_resolve_generator_request_try_finally,
        iterations=25_000,
    )
