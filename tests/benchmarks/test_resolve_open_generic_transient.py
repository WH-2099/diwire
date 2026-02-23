from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

from dishka import Provider

from diwire import Lifetime
from tests.benchmarks.dishka_helpers import DishkaBenchmarkScope, make_dishka_benchmark_container
from tests.benchmarks.helpers import make_diwire_benchmark_container, run_benchmark

T = TypeVar("T")


class _Repo(Generic[T]):
    pass


@dataclass
class _GenericRepo(_Repo[T]):
    dependency_type: type[T]


def test_benchmark_diwire_resolve_open_generic_transient(benchmark: Any) -> None:
    container = make_diwire_benchmark_container()
    container.add(_GenericRepo, provides=_Repo, lifetime=Lifetime.TRANSIENT)
    container.compile()

    resolved_int_first = cast("Any", container.resolve(_Repo[int]))
    resolved_int_second = cast("Any", container.resolve(_Repo[int]))
    resolved_str = cast("Any", container.resolve(_Repo[str]))
    assert isinstance(resolved_int_first, _GenericRepo)
    assert isinstance(resolved_int_second, _GenericRepo)
    assert isinstance(resolved_str, _GenericRepo)
    assert resolved_int_first is not resolved_int_second
    assert resolved_int_first.dependency_type is int
    assert resolved_str.dependency_type is str

    def bench_diwire_resolve_open_generic_transient() -> None:
        _ = container.resolve(_Repo[int])

    run_benchmark(benchmark, bench_diwire_resolve_open_generic_transient)


def test_benchmark_dishka_resolve_open_generic_transient(benchmark: Any) -> None:
    provider = Provider(scope=DishkaBenchmarkScope.APP)
    provider.provide(
        _GenericRepo,
        provides=_Repo,
        scope=DishkaBenchmarkScope.APP,
        cache=False,
    )
    container = make_dishka_benchmark_container(provider)

    resolved_int_first = cast("Any", container.get(_Repo[int]))
    resolved_int_second = cast("Any", container.get(_Repo[int]))
    resolved_str = cast("Any", container.get(_Repo[str]))
    assert isinstance(resolved_int_first, _GenericRepo)
    assert isinstance(resolved_int_second, _GenericRepo)
    assert isinstance(resolved_str, _GenericRepo)
    assert resolved_int_first is not resolved_int_second
    assert resolved_int_first.dependency_type is int
    assert resolved_str.dependency_type is str

    def bench_dishka_resolve_open_generic_transient() -> None:
        _ = container.get(_Repo[int])

    run_benchmark(benchmark, bench_dishka_resolve_open_generic_transient)
