from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator, Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

import pytest

from diwire import (
    AsyncProvider,
    Container,
    DependencyRegistrationPolicy,
    Injected,
    Lifetime,
    Maybe,
    Provider,
    Scope,
    resolver_context,
)
from diwire._internal.resolvers.assembly import compiler as resolver_compiler
from diwire.exceptions import (
    DIWireAsyncDependencyInSyncContextError,
    DIWireInvalidProviderSpecError,
    DIWireScopeMismatchError,
)


class _CycleB:
    def __init__(self, a: _CycleA) -> None:
        self.a = a


class _CycleA:
    def __init__(self, b_provider: Provider[_CycleB]) -> None:
        self._b_provider = b_provider

    def get_b(self) -> _CycleB:
        return self._b_provider()


class _DirectCycleA:
    def __init__(self, b: _DirectCycleB) -> None:
        self.b = b


class _DirectCycleB:
    def __init__(self, a: _DirectCycleA) -> None:
        self.a = a


class _RequestDependency:
    pass


class _RequestProviderConsumer:
    def __init__(self, dependency_provider: Provider[_RequestDependency]) -> None:
        self._dependency_provider = dependency_provider

    def get(self) -> _RequestDependency:
        return self._dependency_provider()


class _ScopedActionDependency:
    pass


class _RequestScopedProviderConsumer:
    def __init__(self, dependency_provider: Provider[_ScopedActionDependency]) -> None:
        self._dependency_provider = dependency_provider


class _VarArgDependency:
    pass


class _VarArgProviderConsumer:
    pass


def _build_vararg_provider_consumer(
    *providers: Provider[_VarArgDependency],
) -> _VarArgProviderConsumer:
    return _VarArgProviderConsumer()


class _VarKwProviderConsumer:
    pass


def _build_varkw_provider_consumer(
    **providers: Provider[_VarArgDependency],
) -> _VarKwProviderConsumer:
    return _VarKwProviderConsumer()


class _AsyncDependency:
    pass


class _AsyncConsumer:
    def __init__(self, dependency_provider: AsyncProvider[_AsyncDependency]) -> None:
        self._dependency_provider = dependency_provider

    async def get(self) -> _AsyncDependency:
        return await self._dependency_provider()


class _SyncProviderForAsyncDependency:
    def __init__(self, dependency_provider: Provider[_AsyncDependency]) -> None:
        self._dependency_provider = dependency_provider

    def get(self) -> _AsyncDependency:
        return self._dependency_provider()


class _InjectedConsumerDependency:
    pass


class _AutoregDependency:
    pass


class _AutoregConsumer:
    def __init__(self, dep_provider: Provider[_AutoregDependency]) -> None:
        self.dep_provider = dep_provider


@dataclass(slots=True)
class _LiveService:
    value: str


class _LiveProviderConsumer:
    def __init__(self, service_provider: Provider[_LiveService]) -> None:
        self._service_provider = service_provider

    def get(self) -> _LiveService:
        return self._service_provider()


class _LiveAsyncProviderConsumer:
    def __init__(self, service_provider: AsyncProvider[_LiveService]) -> None:
        self._service_provider = service_provider

    async def get(self) -> _LiveService:
        return await self._service_provider()


@dataclass(slots=True)
class _LiveResource:
    value: str


@pytest.mark.asyncio
async def test_cycle_with_provider_breaks_assembly_cycle_and_resolves() -> None:
    container = Container()
    container.add(_CycleA)
    container.add(_CycleB)

    resolved = container.resolve(_CycleA)
    resolved_b = resolved.get_b()

    assert isinstance(resolved_b, _CycleB)
    assert resolved_b.a is resolved


def test_unbroken_direct_cycle_still_raises() -> None:
    container = Container()
    container.add(_DirectCycleA)
    container.add(_DirectCycleB)

    with pytest.raises(DIWireInvalidProviderSpecError, match="Circular dependency detected"):
        container.resolve(_DirectCycleA)


def test_provider_preserves_scoped_lifetime_within_same_scope() -> None:
    container = Container()
    container.add(
        _RequestDependency,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    container.add(
        _RequestProviderConsumer,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    with container.enter_scope() as request_scope:
        consumer = request_scope.resolve(_RequestProviderConsumer)
        first = consumer.get()
        second = consumer.get()

    assert first is second


def test_provider_preserves_transient_lifetime_within_same_scope() -> None:
    container = Container()
    container.add(
        _RequestDependency,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add(
        _RequestProviderConsumer,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    with container.enter_scope() as request_scope:
        consumer = request_scope.resolve(_RequestProviderConsumer)
        first = consumer.get()
        second = consumer.get()

    assert first is not second


@pytest.mark.asyncio
async def test_async_provider_returns_awaitable_and_resolves_dependency() -> None:
    async def _build_dependency() -> _AsyncDependency:
        return _AsyncDependency()

    container = Container()
    container.add_factory(_build_dependency, provides=_AsyncDependency)
    container.add(_AsyncConsumer)

    consumer = container.resolve(_AsyncConsumer)
    dependency = await consumer.get()

    assert isinstance(dependency, _AsyncDependency)


def test_sync_provider_to_async_chain_raises_on_call() -> None:
    async def _build_dependency() -> _AsyncDependency:
        return _AsyncDependency()

    container = Container()
    container.add_factory(_build_dependency, provides=_AsyncDependency)
    container.add(_SyncProviderForAsyncDependency)

    consumer = container.resolve(_SyncProviderForAsyncDependency)

    with pytest.raises(
        DIWireAsyncDependencyInSyncContextError,
        match="requires asynchronous resolution",
    ):
        _ = consumer.get()


@pytest.mark.asyncio
async def test_direct_resolve_provider_and_async_provider_dependency_keys() -> None:
    container = Container()
    container.add(_InjectedConsumerDependency)
    resolver = container.compile()

    provider = resolver.resolve(Provider[_InjectedConsumerDependency])
    async_provider = resolver.resolve(AsyncProvider[_InjectedConsumerDependency])
    provider_from_async = await resolver.aresolve(Provider[_InjectedConsumerDependency])
    async_provider_from_async = await resolver.aresolve(AsyncProvider[_InjectedConsumerDependency])

    assert isinstance(provider(), _InjectedConsumerDependency)
    assert isinstance(await async_provider(), _InjectedConsumerDependency)
    assert isinstance(provider_from_async(), _InjectedConsumerDependency)
    assert isinstance(await async_provider_from_async(), _InjectedConsumerDependency)


@pytest.mark.asyncio
async def test_injected_wrapper_supports_provider_and_async_provider() -> None:
    container = Container()
    container.add(_InjectedConsumerDependency)

    @resolver_context.inject
    def _sync_handler(
        dependency_provider: Injected[Provider[_InjectedConsumerDependency]],
    ) -> _InjectedConsumerDependency:
        return dependency_provider()

    @resolver_context.inject
    async def _async_handler(
        dependency_provider: Injected[AsyncProvider[_InjectedConsumerDependency]],
    ) -> _InjectedConsumerDependency:
        return await dependency_provider()

    sync_handler = cast("Any", _sync_handler)
    async_handler = cast("Any", _async_handler)

    assert isinstance(sync_handler(), _InjectedConsumerDependency)
    assert isinstance(await async_handler(), _InjectedConsumerDependency)


def test_sync_provider_resolved_before_override_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    provider = container.resolve(Provider[_LiveService])

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert provider().value == "new"


def test_sync_provider_called_before_override_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    provider = container.resolve(Provider[_LiveService])
    before = provider()

    container.add_instance(_LiveService("new"), provides=_LiveService)
    after = provider()

    assert before.value == "old"
    assert after.value == "new"


def test_provider_resolved_from_stale_compiled_resolver_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)
    resolver = container.compile()

    container.add_instance(_LiveService("new"), provides=_LiveService)
    provider = resolver.resolve(Provider[_LiveService])

    assert provider().value == "new"


def test_constructor_injected_provider_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add(_LiveProviderConsumer)

    consumer = container.resolve(_LiveProviderConsumer)

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert consumer.get().value == "new"


@pytest.mark.asyncio
async def test_async_provider_resolved_before_override_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    provider = await container.aresolve(AsyncProvider[_LiveService])

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert (await provider()).value == "new"


@pytest.mark.asyncio
async def test_async_provider_called_before_override_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    provider = await container.aresolve(AsyncProvider[_LiveService])
    before = await provider()

    container.add_instance(_LiveService("new"), provides=_LiveService)
    after = await provider()

    assert before.value == "old"
    assert after.value == "new"


@pytest.mark.asyncio
async def test_async_provider_resolved_from_stale_compiled_resolver_uses_latest_container_graph() -> (
    None
):
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)
    resolver = container.compile()

    container.add_instance(_LiveService("new"), provides=_LiveService)
    provider = resolver.resolve(AsyncProvider[_LiveService])

    assert (await provider()).value == "new"


@pytest.mark.asyncio
async def test_constructor_injected_async_provider_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add(_LiveAsyncProviderConsumer)

    consumer = container.resolve(_LiveAsyncProviderConsumer)

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert (await consumer.get()).value == "new"


@pytest.mark.asyncio
async def test_compiled_resolver_async_provider_uses_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)
    resolver = container.compile()

    provider = resolver.resolve(AsyncProvider[_LiveService])

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert (await provider()).value == "new"


@pytest.mark.asyncio
async def test_maybe_provider_handles_use_latest_container_graph() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    provider = container.resolve(Maybe[Provider[_LiveService]])
    async_provider = await container.aresolve(Maybe[AsyncProvider[_LiveService]])

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert provider is not None
    assert async_provider is not None
    assert provider().value == "new"
    assert (await async_provider()).value == "new"


def test_injected_sync_provider_handle_uses_latest_container_graph_after_mutation() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    @resolver_context.inject
    def _handler(provider: Injected[Provider[_LiveService]]) -> Provider[_LiveService]:
        return provider

    handler = cast("Any", _handler)
    provider = handler()

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert provider().value == "new"


@pytest.mark.asyncio
async def test_injected_async_provider_handle_uses_latest_container_graph_after_mutation() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    @resolver_context.inject
    async def _handler(
        provider: Injected[AsyncProvider[_LiveService]],
    ) -> AsyncProvider[_LiveService]:
        return provider

    handler = cast("Any", _handler)
    provider = await handler()

    container.add_instance(_LiveService("new"), provides=_LiveService)

    assert (await provider()).value == "new"


def test_stale_scoped_provider_rebinds_same_scope_and_preserves_scoped_cache() -> None:
    container = Container()
    build_count = 0

    def _build_old() -> _LiveService:
        return _LiveService("old")

    def _build_new() -> _LiveService:
        nonlocal build_count
        build_count += 1
        return _LiveService(f"new-{build_count}")

    container.add_factory(
        _build_old,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveService])

        container.add_factory(
            _build_new,
            provides=_LiveService,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        first = provider()
        second = provider()

    assert first.value == "new-1"
    assert first is second


def test_concurrent_stale_scoped_provider_calls_share_single_rebound_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = Container()
    build_count = 0

    def _build_old() -> _LiveService:
        return _LiveService("old")

    def _build_new() -> _LiveService:
        nonlocal build_count
        build_count += 1
        return _LiveService(f"new-{build_count}")

    container.add_factory(
        _build_old,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveService])

        container.add_factory(
            _build_new,
            provides=_LiveService,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        workers = 8
        start_barrier = threading.Barrier(workers + 1)
        latest_call_count = 0
        latest_call_count_lock = threading.Lock()
        entered_latest_resolver = threading.Event()
        release_latest_resolver = threading.Event()
        original_latest_resolver = resolver_compiler._latest_container_base_resolver

        def _blocking_latest_resolver(*, container: Any) -> Any:
            nonlocal latest_call_count
            with latest_call_count_lock:
                latest_call_count += 1
            entered_latest_resolver.set()
            if not release_latest_resolver.wait(timeout=5):
                msg = "Timed out waiting to release latest resolver lookup."
                raise RuntimeError(msg)
            return original_latest_resolver(container=container)

        def _call_provider() -> _LiveService:
            start_barrier.wait(timeout=5)
            return provider()

        monkeypatch.setattr(
            resolver_compiler,
            "_latest_container_base_resolver",
            _blocking_latest_resolver,
        )
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_call_provider) for _ in range(workers)]
            start_barrier.wait(timeout=5)
            assert entered_latest_resolver.wait(timeout=5)
            assert not release_latest_resolver.wait(timeout=0.05)
            release_latest_resolver.set()
            resolved = [future.result(timeout=5) for future in futures]

    assert latest_call_count == 1
    assert build_count == 1
    assert len({id(service) for service in resolved}) == 1
    assert resolved[0].value == "new-1"


def test_stale_provider_from_initially_stateless_scope_rebinds_without_inactive_error() -> None:
    container = Container()
    container.add_instance(_LiveService("old"), provides=_LiveService)

    with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveService])

        container.add_factory(
            lambda: _LiveService("new"),
            provides=_LiveService,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        assert provider().value == "new"


def test_stale_scoped_provider_from_reused_pooled_scope_stays_closed() -> None:
    container = Container()
    container.add_factory(
        lambda: _LiveService("old"),
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    root_resolver = container.compile()

    with root_resolver.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveService])

    container.add_factory(
        lambda: _LiveService("new"),
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with root_resolver.enter_scope(Scope.REQUEST):
        pass

    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        provider()


@pytest.mark.asyncio
async def test_stale_scoped_async_provider_from_reused_pooled_scope_stays_closed() -> None:
    container = Container()

    async def _build_old() -> _LiveService:
        return _LiveService("old")

    async def _build_new() -> _LiveService:
        return _LiveService("new")

    container.add_factory(
        _build_old,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    root_resolver = container.compile()

    async with root_resolver.enter_scope(Scope.REQUEST) as request_scope:
        provider = await request_scope.aresolve(AsyncProvider[_LiveService])

    container.add_factory(
        _build_new,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    async with root_resolver.enter_scope(Scope.REQUEST):
        pass

    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        await provider()


def test_stale_scoped_provider_cleanup_preserves_outer_resolver_context() -> None:
    container = Container()

    def _build_old() -> _LiveService:
        return _LiveService("old")

    def _build_new() -> _LiveService:
        return _LiveService("new")

    container.add_factory(
        _build_old,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container as root_resolver:
        with root_resolver.enter_scope(Scope.REQUEST) as request_scope:
            provider = request_scope.resolve(Provider[_LiveService])

            container.add_factory(
                _build_new,
                provides=_LiveService,
                scope=Scope.REQUEST,
                lifetime=Lifetime.SCOPED,
            )

            assert provider().value == "new"

        assert resolver_context._get_bound_resolver_or_none() is root_resolver


@pytest.mark.asyncio
async def test_stale_scoped_async_provider_rebinds_same_scope_and_preserves_scoped_cache() -> None:
    container = Container()
    build_count = 0

    async def _build_old() -> _LiveService:
        return _LiveService("old")

    async def _build_new() -> _LiveService:
        nonlocal build_count
        build_count += 1
        return _LiveService(f"new-{build_count}")

    container.add_factory(
        _build_old,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    async with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = await request_scope.aresolve(AsyncProvider[_LiveService])

        container.add_factory(
            _build_new,
            provides=_LiveService,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        first = await provider()
        second = await provider()

    assert first.value == "new-1"
    assert first is second


@pytest.mark.asyncio
async def test_concurrent_stale_scoped_async_provider_calls_share_single_rebound_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = Container()
    build_count = 0
    latest_call_count = 0
    original_latest_resolver = resolver_compiler._latest_container_base_resolver

    async def _build_old() -> _LiveService:
        return _LiveService("old")

    async def _build_new() -> _LiveService:
        nonlocal build_count
        build_count += 1
        await asyncio.sleep(0)
        return _LiveService(f"new-{build_count}")

    def _counting_latest_resolver(*, container: Any) -> Any:
        nonlocal latest_call_count
        latest_call_count += 1
        return original_latest_resolver(container=container)

    container.add_factory(
        _build_old,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    async with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = await request_scope.aresolve(AsyncProvider[_LiveService])

        container.add_factory(
            _build_new,
            provides=_LiveService,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        monkeypatch.setattr(
            resolver_compiler,
            "_latest_container_base_resolver",
            _counting_latest_resolver,
        )
        resolved = await asyncio.gather(*(provider() for _ in range(8)))

    assert latest_call_count == 1
    assert build_count == 1
    assert len({id(service) for service in resolved}) == 1
    assert resolved[0].value == "new-1"


def test_stale_scoped_provider_rebound_scope_cleans_up_with_original_scope() -> None:
    container = Container()
    events: list[str] = []

    def _provide_old() -> Generator[_LiveResource, None, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit")

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_generator(
        _provide_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveResource])

        container.add_generator(
            _provide_new,
            provides=_LiveResource,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        assert provider().value == "new"
        assert events == ["new-enter"]

    assert events == ["new-enter", "new-exit"]


def test_stale_scoped_provider_owns_latest_root_when_resolving_root_dependency() -> None:
    container = Container()
    events: list[str] = []

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    root_resolver = container.compile()
    with root_resolver.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveResource])

        container.add_generator(_provide_new, provides=_LiveResource)

        assert provider().value == "new"
    root_resolver.close()

    assert events == ["new-enter", "new-exit"]


def test_stale_root_provider_latest_graph_cleans_up_when_container_context_exits() -> None:
    container = Container()
    events: list[str] = []

    def _provide_old() -> Generator[_LiveResource, None, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit")

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_generator(_provide_old, provides=_LiveResource)

    with container as root_resolver:
        provider = root_resolver.resolve(Provider[_LiveResource])

        container.add_generator(_provide_new, provides=_LiveResource)

        assert provider().value == "new"
        assert events == ["new-enter"]

    assert events == ["new-enter", "new-exit"]


def test_same_revision_root_provider_call_racing_close_is_cleaned_up() -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    provider_started = threading.Event()
    release_provider = threading.Event()
    provider_result: list[_LiveResource] = []

    def _provide_resource() -> Generator[_LiveResource, None, None]:
        provider_started.set()
        if not release_provider.wait(timeout=5):
            msg = "Timed out waiting to release provider."
            raise RuntimeError(msg)
        events.append("enter")
        try:
            yield _LiveResource("same")
        finally:
            events.append("exit")

    container.add_generator(_provide_resource, provides=_LiveResource)
    provider = container.resolve(Provider[_LiveResource])

    provider_thread = threading.Thread(target=lambda: provider_result.append(provider()))
    provider_thread.start()
    assert provider_started.wait(timeout=5)

    close_thread = threading.Thread(target=container.close)
    close_thread.start()
    close_thread.join(timeout=0.05)
    assert close_thread.is_alive()

    release_provider.set()
    provider_thread.join(timeout=5)
    close_thread.join(timeout=5)

    assert not provider_thread.is_alive()
    assert not close_thread.is_alive()
    assert [resource.value for resource in provider_result] == ["same"]
    assert events == ["enter", "exit"]


def test_stale_root_provider_call_racing_close_is_cleaned_up() -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    provider_started = threading.Event()
    release_provider = threading.Event()
    provider_result: list[_LiveResource] = []

    def _provide_new() -> Generator[_LiveResource, None, None]:
        provider_started.set()
        if not release_provider.wait(timeout=5):
            msg = "Timed out waiting to release provider."
            raise RuntimeError(msg)
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    provider = container.resolve(Provider[_LiveResource])
    container.add_generator(_provide_new, provides=_LiveResource)

    provider_thread = threading.Thread(target=lambda: provider_result.append(provider()))
    provider_thread.start()
    assert provider_started.wait(timeout=5)

    close_thread = threading.Thread(target=container.close)
    close_thread.start()
    close_thread.join(timeout=0.05)
    assert close_thread.is_alive()

    release_provider.set()
    provider_thread.join(timeout=5)
    close_thread.join(timeout=5)

    assert not provider_thread.is_alive()
    assert not close_thread.is_alive()
    assert [resource.value for resource in provider_result] == ["new"]
    assert events == ["new-enter", "new-exit"]


def test_stale_root_provider_racing_direct_resolver_close_before_latest_compile_is_cleaned_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    latest_compile_started = threading.Event()
    release_latest_compile = threading.Event()
    provider_result: list[_LiveResource] = []
    provider_errors: list[BaseException] = []

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    resolver = container.compile()
    provider = resolver.resolve(Provider[_LiveResource])
    container.add_generator(_provide_new, provides=_LiveResource)
    original_latest_resolver = resolver_compiler._latest_container_base_resolver

    def _blocked_latest_resolver(*, container: Container) -> Any:
        latest_compile_started.set()
        if not release_latest_compile.wait(timeout=5):
            msg = "Timed out waiting to release latest resolver compilation."
            raise RuntimeError(msg)
        return original_latest_resolver(container=container)

    monkeypatch.setattr(
        resolver_compiler,
        "_latest_container_base_resolver",
        _blocked_latest_resolver,
    )

    def _call_provider() -> None:
        try:
            provider_result.append(provider())
        except BaseException as error:
            provider_errors.append(error)

    provider_thread = threading.Thread(target=_call_provider)
    provider_thread.start()
    assert latest_compile_started.wait(timeout=5)

    close_thread = threading.Thread(target=resolver.close)
    close_thread.start()
    close_thread.join(timeout=0.05)
    assert close_thread.is_alive()

    release_latest_compile.set()
    provider_thread.join(timeout=5)
    close_thread.join(timeout=5)

    assert not provider_thread.is_alive()
    assert not close_thread.is_alive()
    assert provider_errors == []
    assert [resource.value for resource in provider_result] == ["new"]
    assert events == ["new-enter", "new-exit"]


def test_stale_root_provider_racing_container_close_after_mutation_is_cleaned_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    latest_compile_started = threading.Event()
    release_latest_compile = threading.Event()
    provider_result: list[_LiveResource] = []
    provider_errors: list[BaseException] = []
    close_errors: list[BaseException] = []

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    provider = container.resolve(Provider[_LiveResource])
    container.add_generator(_provide_new, provides=_LiveResource)
    original_latest_resolver = resolver_compiler._latest_container_base_resolver

    def _blocked_latest_resolver(*, container: Container) -> Any:
        latest_compile_started.set()
        if not release_latest_compile.wait(timeout=5):
            msg = "Timed out waiting to release latest resolver compilation."
            raise RuntimeError(msg)
        return original_latest_resolver(container=container)

    monkeypatch.setattr(
        resolver_compiler,
        "_latest_container_base_resolver",
        _blocked_latest_resolver,
    )

    def _call_provider() -> None:
        try:
            provider_result.append(provider())
        except BaseException as error:
            provider_errors.append(error)

    def _close_container() -> None:
        try:
            container.close()
        except BaseException as error:
            close_errors.append(error)

    provider_thread = threading.Thread(target=_call_provider)
    provider_thread.start()
    assert latest_compile_started.wait(timeout=5)

    close_thread = threading.Thread(target=_close_container)
    close_thread.start()
    close_thread.join(timeout=0.05)
    assert close_thread.is_alive()

    release_latest_compile.set()
    provider_thread.join(timeout=5)
    close_thread.join(timeout=5)

    assert not provider_thread.is_alive()
    assert not close_thread.is_alive()
    assert provider_errors == []
    assert close_errors == []
    assert [resource.value for resource in provider_result] == ["new"]
    assert events == ["new-enter", "new-exit"]


def test_stale_root_provider_resolved_from_compiled_resolver_owns_latest_root_cleanup() -> None:
    container = Container()
    events: list[str] = []

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    resolver = container.compile()
    provider = resolver.resolve(Provider[_LiveResource])

    container.add_generator(_provide_new, provides=_LiveResource)

    assert provider().value == "new"
    resolver.close()

    assert events == ["new-enter", "new-exit"]


def test_stale_root_provider_called_from_cleanup_closes_latest_graph() -> None:
    container = Container()
    events: list[str] = []
    provider: Provider[_LiveService] | None = None

    def _provide_resource() -> Generator[_LiveResource, None, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            events.append(f"cleanup-provider-{provider().value}")
            events.append("old-exit-end")

    def _provide_new_service() -> Generator[_LiveService, None, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_resource, provides=_LiveResource)

    with container as root_resolver:
        provider = root_resolver.resolve(Provider[_LiveService])
        assert root_resolver.resolve(_LiveResource).value == "old"

        container.add_generator(_provide_new_service, provides=_LiveService)

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-enter",
        "cleanup-provider-new",
        "old-exit-end",
        "new-exit",
    ]


def test_stale_root_provider_called_from_direct_resolver_cleanup_closes_latest_graph() -> None:
    container = Container()
    events: list[str] = []
    provider: Provider[_LiveService] | None = None

    def _provide_resource() -> Generator[_LiveResource, None, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            events.append(f"cleanup-provider-{provider().value}")
            events.append("old-exit-end")

    def _provide_new_service() -> Generator[_LiveService, None, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_resource, provides=_LiveResource)
    root_resolver = container.compile()
    provider = root_resolver.resolve(Provider[_LiveService])
    assert root_resolver.resolve(_LiveResource).value == "old"

    container.add_generator(_provide_new_service, provides=_LiveService)
    root_resolver.close()

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-enter",
        "cleanup-provider-new",
        "old-exit-end",
        "new-exit",
    ]


def test_stale_root_provider_called_before_and_during_cleanup_closes_latest_graph() -> None:
    container = Container()
    events: list[str] = []
    provider: Provider[_LiveService] | None = None

    def _provide_resource() -> Generator[_LiveResource, None, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            events.append(f"cleanup-provider-{provider().value}")
            events.append("old-exit-end")

    def _provide_new_service() -> Generator[_LiveService, None, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_resource, provides=_LiveResource)

    with container as root_resolver:
        provider = root_resolver.resolve(Provider[_LiveService])
        assert root_resolver.resolve(_LiveResource).value == "old"

        container.add_generator(_provide_new_service, provides=_LiveService)

        events.append(f"body-provider-{provider().value}")

    assert events == [
        "old-enter",
        "new-enter",
        "body-provider-new",
        "old-exit-start",
        "cleanup-provider-new",
        "old-exit-end",
        "new-exit",
    ]


def test_stale_scoped_provider_call_during_cleanup_raises_scope_mismatch() -> None:
    container = Container()
    events: list[str] = []
    provider: Provider[_LiveResource] | None = None

    def _build_old() -> _LiveResource:
        return _LiveResource("old")

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-cleanup")
            assert provider is not None
            with pytest.raises(DIWireScopeMismatchError, match="started closing"):
                provider()

    container.add_factory(
        _build_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveResource])

        container.add_generator(
            _provide_new,
            provides=_LiveResource,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        assert provider().value == "new"

    assert events == ["new-enter", "new-cleanup"]


def test_same_revision_scoped_provider_call_racing_close_is_cleaned_up() -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    provider_started = threading.Event()
    release_provider = threading.Event()
    provider_result: list[_LiveResource] = []
    provider_errors: list[BaseException] = []

    def _provide_resource() -> Generator[_LiveResource, None, None]:
        provider_started.set()
        if not release_provider.wait(timeout=5):
            msg = "Timed out waiting to release provider."
            raise RuntimeError(msg)
        events.append("enter")
        try:
            yield _LiveResource("same")
        finally:
            events.append("exit")

    container.add_generator(
        _provide_resource,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    request_scope = container.enter_scope(Scope.REQUEST)
    request_scope.__enter__()
    provider = request_scope.resolve(Provider[_LiveResource])

    def _call_provider() -> None:
        try:
            provider_result.append(provider())
        except BaseException as error:
            provider_errors.append(error)

    provider_thread = threading.Thread(target=_call_provider)
    provider_thread.start()
    assert provider_started.wait(timeout=5)

    close_thread = threading.Thread(target=lambda: request_scope.__exit__(None, None, None))
    close_thread.start()
    close_thread.join(timeout=0.05)
    assert close_thread.is_alive()

    release_provider.set()
    provider_thread.join(timeout=5)
    close_thread.join(timeout=5)

    assert not provider_thread.is_alive()
    assert not close_thread.is_alive()
    assert provider_errors == []
    assert [resource.value for resource in provider_result] == ["same"]
    assert events == ["enter", "exit"]


@pytest.mark.asyncio
async def test_stale_scoped_async_provider_rebound_scope_cleans_up_with_original_scope() -> None:
    container = Container()
    events: list[str] = []

    async def _provide_old() -> AsyncGenerator[_LiveResource, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit")

    async def _provide_new() -> AsyncGenerator[_LiveResource, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_generator(
        _provide_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    async with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = await request_scope.aresolve(AsyncProvider[_LiveResource])

        container.add_generator(
            _provide_new,
            provides=_LiveResource,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        assert (await provider()).value == "new"
        assert events == ["new-enter"]

    assert events == ["new-enter", "new-exit"]


@pytest.mark.asyncio
async def test_stale_scoped_async_provider_owns_latest_root_for_root_dependency() -> None:
    container = Container()
    events: list[str] = []

    async def _provide_new() -> AsyncGenerator[_LiveResource, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    root_resolver = container.compile()
    async with root_resolver.enter_scope(Scope.REQUEST) as request_scope:
        provider = await request_scope.aresolve(AsyncProvider[_LiveResource])

        container.add_generator(_provide_new, provides=_LiveResource)

        assert (await provider()).value == "new"
    await root_resolver.aclose()

    assert events == ["new-enter", "new-exit"]


@pytest.mark.asyncio
async def test_stale_scoped_async_provider_call_during_cleanup_raises_scope_mismatch() -> None:
    container = Container()
    events: list[str] = []
    provider: AsyncProvider[_LiveResource] | None = None

    async def _build_old() -> _LiveResource:
        return _LiveResource("old")

    async def _provide_new() -> AsyncGenerator[_LiveResource, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-cleanup")
            assert provider is not None
            with pytest.raises(DIWireScopeMismatchError, match="started closing"):
                await provider()

    container.add_factory(
        _build_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    async with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = await request_scope.aresolve(AsyncProvider[_LiveResource])

        container.add_generator(
            _provide_new,
            provides=_LiveResource,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )

        assert (await provider()).value == "new"

    assert events == ["new-enter", "new-cleanup"]


@pytest.mark.asyncio
async def test_same_revision_scoped_async_provider_call_racing_close_is_cleaned_up() -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()

    async def _provide_resource() -> AsyncGenerator[_LiveResource, None]:
        provider_started.set()
        await release_provider.wait()
        events.append("enter")
        try:
            yield _LiveResource("same")
        finally:
            events.append("exit")

    container.add_generator(
        _provide_resource,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    request_scope = container.enter_scope(Scope.REQUEST)
    await request_scope.__aenter__()
    provider = await request_scope.aresolve(AsyncProvider[_LiveResource])

    provider_task = asyncio.create_task(provider())
    await asyncio.wait_for(provider_started.wait(), timeout=5)

    close_task = asyncio.create_task(request_scope.__aexit__(None, None, None))
    await asyncio.sleep(0.01)
    assert not close_task.done()

    release_provider.set()
    resolved = await asyncio.wait_for(provider_task, timeout=5)
    await asyncio.wait_for(close_task, timeout=5)

    assert resolved.value == "same"
    assert events == ["enter", "exit"]


@pytest.mark.asyncio
async def test_stale_root_async_provider_latest_graph_cleans_up_when_container_exits() -> None:
    container = Container()
    events: list[str] = []

    async def _provide_old() -> AsyncGenerator[_LiveResource, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit")

    async def _provide_new() -> AsyncGenerator[_LiveResource, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_generator(_provide_old, provides=_LiveResource)

    async with container as root_resolver:
        provider = await root_resolver.aresolve(AsyncProvider[_LiveResource])

        container.add_generator(_provide_new, provides=_LiveResource)

        assert (await provider()).value == "new"
        assert events == ["new-enter"]

    assert events == ["new-enter", "new-exit"]


@pytest.mark.asyncio
async def test_same_revision_root_async_provider_call_racing_close_is_cleaned_up() -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()

    async def _provide_resource() -> AsyncGenerator[_LiveResource, None]:
        provider_started.set()
        await release_provider.wait()
        events.append("enter")
        try:
            yield _LiveResource("same")
        finally:
            events.append("exit")

    container.add_generator(_provide_resource, provides=_LiveResource)
    provider = await container.aresolve(AsyncProvider[_LiveResource])

    provider_task = asyncio.create_task(provider())
    await asyncio.wait_for(provider_started.wait(), timeout=5)

    close_task = asyncio.create_task(container.aclose())
    await asyncio.sleep(0.01)
    assert not close_task.done()

    release_provider.set()
    resolved = await asyncio.wait_for(provider_task, timeout=5)
    await asyncio.wait_for(close_task, timeout=5)

    assert resolved.value == "same"
    assert events == ["enter", "exit"]


@pytest.mark.asyncio
async def test_stale_root_async_provider_call_racing_close_is_cleaned_up() -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()

    async def _provide_new() -> AsyncGenerator[_LiveResource, None]:
        provider_started.set()
        await release_provider.wait()
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    provider = await container.aresolve(AsyncProvider[_LiveResource])
    container.add_generator(_provide_new, provides=_LiveResource)

    provider_task = asyncio.create_task(provider())
    await asyncio.wait_for(provider_started.wait(), timeout=5)

    close_task = asyncio.create_task(container.aclose())
    await asyncio.sleep(0.01)
    assert not close_task.done()

    release_provider.set()
    resolved = await asyncio.wait_for(provider_task, timeout=5)
    await asyncio.wait_for(close_task, timeout=5)

    assert resolved.value == "new"
    assert events == ["new-enter", "new-exit"]


@pytest.mark.asyncio
async def test_stale_root_async_provider_resolved_from_compiled_resolver_owns_latest_root_cleanup() -> (
    None
):
    container = Container()
    events: list[str] = []

    async def _provide_new() -> AsyncGenerator[_LiveResource, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveResource("old"), provides=_LiveResource)
    resolver = container.compile()
    provider = await resolver.aresolve(AsyncProvider[_LiveResource])

    container.add_generator(_provide_new, provides=_LiveResource)

    assert (await provider()).value == "new"
    await resolver.aclose()

    assert events == ["new-enter", "new-exit"]


@pytest.mark.asyncio
async def test_stale_root_async_provider_called_from_cleanup_closes_latest_graph() -> None:
    container = Container()
    events: list[str] = []
    provider: AsyncProvider[_LiveService] | None = None

    async def _provide_resource() -> AsyncGenerator[_LiveResource, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            events.append(f"cleanup-provider-{(await provider()).value}")
            events.append("old-exit-end")

    async def _provide_new_service() -> AsyncGenerator[_LiveService, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_resource, provides=_LiveResource)

    async with container as root_resolver:
        provider = await root_resolver.aresolve(AsyncProvider[_LiveService])
        assert (await root_resolver.aresolve(_LiveResource)).value == "old"

        container.add_generator(_provide_new_service, provides=_LiveService)

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-enter",
        "cleanup-provider-new",
        "old-exit-end",
        "new-exit",
    ]


@pytest.mark.asyncio
async def test_stale_root_async_provider_called_from_direct_resolver_cleanup_closes_latest() -> (
    None
):
    container = Container()
    events: list[str] = []
    provider: AsyncProvider[_LiveService] | None = None

    async def _provide_resource() -> AsyncGenerator[_LiveResource, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            events.append(f"cleanup-provider-{(await provider()).value}")
            events.append("old-exit-end")

    async def _provide_new_service() -> AsyncGenerator[_LiveService, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_resource, provides=_LiveResource)
    root_resolver = container.compile()
    provider = await root_resolver.aresolve(AsyncProvider[_LiveService])
    assert (await root_resolver.aresolve(_LiveResource)).value == "old"

    container.add_generator(_provide_new_service, provides=_LiveService)
    await root_resolver.aclose()

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-enter",
        "cleanup-provider-new",
        "old-exit-end",
        "new-exit",
    ]


@pytest.mark.asyncio
async def test_stale_root_async_provider_called_before_and_during_cleanup_closes_latest_graph() -> (
    None
):
    container = Container()
    events: list[str] = []
    provider: AsyncProvider[_LiveService] | None = None

    async def _provide_resource() -> AsyncGenerator[_LiveResource, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            events.append(f"cleanup-provider-{(await provider()).value}")
            events.append("old-exit-end")

    async def _provide_new_service() -> AsyncGenerator[_LiveService, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_resource, provides=_LiveResource)

    async with container as root_resolver:
        provider = await root_resolver.aresolve(AsyncProvider[_LiveService])
        assert (await root_resolver.aresolve(_LiveResource)).value == "old"

        container.add_generator(_provide_new_service, provides=_LiveService)

        events.append(f"body-provider-{(await provider()).value}")

    assert events == [
        "old-enter",
        "new-enter",
        "body-provider-new",
        "old-exit-start",
        "cleanup-provider-new",
        "old-exit-end",
        "new-exit",
    ]


def test_stale_scoped_provider_marks_original_scope_inactive_when_rebound_cleanup_fails() -> None:
    container = Container()
    events: list[str] = []
    provider: Provider[_LiveResource] | None = None

    def _build_old() -> _LiveResource:
        return _LiveResource("old")

    def _provide_new() -> Generator[_LiveResource, None, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")
            msg = "cleanup failed"
            raise RuntimeError(msg)

    container.add_factory(
        _build_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with pytest.raises(RuntimeError, match="cleanup failed"):
        with container.enter_scope(Scope.REQUEST) as request_scope:
            provider = request_scope.resolve(Provider[_LiveResource])

            container.add_generator(
                _provide_new,
                provides=_LiveResource,
                scope=Scope.REQUEST,
                lifetime=Lifetime.SCOPED,
            )

            assert provider().value == "new"

    assert provider is not None
    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        provider()
    assert events == ["new-enter", "new-exit"]


def test_stale_scoped_provider_closes_older_rebound_after_newer_cleanup_fails() -> None:
    container = Container()
    events: list[str] = []

    def _build_old() -> _LiveResource:
        return _LiveResource("old")

    def _provide_one() -> Generator[_LiveResource, None, None]:
        events.append("one-enter")
        try:
            yield _LiveResource("one")
        finally:
            events.append("one-exit")

    def _provide_two() -> Generator[_LiveResource, None, None]:
        events.append("two-enter")
        try:
            yield _LiveResource("two")
        finally:
            events.append("two-exit")
            msg = "cleanup failed"
            raise RuntimeError(msg)

    container.add_factory(
        _build_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with pytest.raises(RuntimeError, match="cleanup failed"):
        with container.enter_scope(Scope.REQUEST) as request_scope:
            provider = request_scope.resolve(Provider[_LiveResource])

            container.add_generator(
                _provide_one,
                provides=_LiveResource,
                scope=Scope.REQUEST,
                lifetime=Lifetime.SCOPED,
            )
            assert provider().value == "one"

            container.add_generator(
                _provide_two,
                provides=_LiveResource,
                scope=Scope.REQUEST,
                lifetime=Lifetime.SCOPED,
            )
            assert provider().value == "two"

    assert events == ["one-enter", "two-enter", "two-exit", "one-exit"]


@pytest.mark.asyncio
async def test_stale_scoped_async_provider_marks_scope_inactive_when_cleanup_fails() -> None:
    container = Container()
    events: list[str] = []
    provider: AsyncProvider[_LiveResource] | None = None

    async def _build_old() -> _LiveResource:
        return _LiveResource("old")

    async def _provide_new() -> AsyncGenerator[_LiveResource, None]:
        events.append("new-enter")
        try:
            yield _LiveResource("new")
        finally:
            events.append("new-exit")
            msg = "cleanup failed"
            raise RuntimeError(msg)

    container.add_factory(
        _build_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with pytest.raises(RuntimeError, match="cleanup failed"):
        async with container.enter_scope(Scope.REQUEST) as request_scope:
            provider = await request_scope.aresolve(AsyncProvider[_LiveResource])

            container.add_generator(
                _provide_new,
                provides=_LiveResource,
                scope=Scope.REQUEST,
                lifetime=Lifetime.SCOPED,
            )

            assert (await provider()).value == "new"

    assert provider is not None
    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        await provider()
    assert events == ["new-enter", "new-exit"]


@pytest.mark.asyncio
async def test_stale_scoped_async_provider_closes_older_rebound_after_cleanup_fails() -> None:
    container = Container()
    events: list[str] = []

    async def _build_old() -> _LiveResource:
        return _LiveResource("old")

    async def _provide_one() -> AsyncGenerator[_LiveResource, None]:
        events.append("one-enter")
        try:
            yield _LiveResource("one")
        finally:
            events.append("one-exit")

    async def _provide_two() -> AsyncGenerator[_LiveResource, None]:
        events.append("two-enter")
        try:
            yield _LiveResource("two")
        finally:
            events.append("two-exit")
            msg = "cleanup failed"
            raise RuntimeError(msg)

    container.add_factory(
        _build_old,
        provides=_LiveResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with pytest.raises(RuntimeError, match="cleanup failed"):
        async with container.enter_scope(Scope.REQUEST) as request_scope:
            provider = await request_scope.aresolve(AsyncProvider[_LiveResource])

            container.add_generator(
                _provide_one,
                provides=_LiveResource,
                scope=Scope.REQUEST,
                lifetime=Lifetime.SCOPED,
            )
            assert (await provider()).value == "one"

            container.add_generator(
                _provide_two,
                provides=_LiveResource,
                scope=Scope.REQUEST,
                lifetime=Lifetime.SCOPED,
            )
            assert (await provider()).value == "two"

    assert events == ["one-enter", "two-enter", "two-exit", "one-exit"]


def test_inactive_scoped_stale_provider_raises_scope_mismatch() -> None:
    container = Container()
    container.add_factory(
        lambda: _LiveService("old"),
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_LiveService])

    container.add_factory(
        lambda: _LiveService("new"),
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        provider()


@pytest.mark.asyncio
async def test_inactive_scoped_stale_async_provider_raises_scope_mismatch() -> None:
    container = Container()

    async def _build_old() -> _LiveService:
        return _LiveService("old")

    async def _build_new() -> _LiveService:
        return _LiveService("new")

    container.add_factory(
        _build_old,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    async with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = await request_scope.aresolve(AsyncProvider[_LiveService])

    container.add_factory(
        _build_new,
        provides=_LiveService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        await provider()


T = TypeVar("T")


class _OpenProviderService(Generic[T]):
    pass


@dataclass
class _OpenProviderServiceImpl(_OpenProviderService[T]):
    type_arg: type[T]


@dataclass
class _OpenProviderCleanupOwner(Generic[T]):
    type_arg: type[T]


def _build_open_provider_service(type_arg: type[T]) -> _OpenProviderService[T]:
    return _OpenProviderServiceImpl(type_arg=type_arg)


def test_provider_direct_resolve_supports_open_generic_dependencies() -> None:
    container = Container()
    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    resolver = container.compile()

    provider = resolver.resolve(Provider[_OpenProviderService[int]])
    resolved = provider()

    assert isinstance(resolved, _OpenProviderServiceImpl)
    assert resolved.type_arg is int


def test_open_generic_provider_handle_uses_latest_container_graph_after_mutation() -> None:
    container = Container()
    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)

    provider = container.resolve(Provider[_OpenProviderService[int]])

    container.add_instance(
        _OpenProviderServiceImpl(type_arg=str),
        provides=_OpenProviderService[int],
    )

    resolved = provider()

    assert isinstance(resolved, _OpenProviderServiceImpl)
    assert resolved.type_arg is str


def test_open_generic_stale_root_provider_resolved_from_compiled_resolver_owns_latest_root_cleanup() -> (
    None
):
    container = Container()
    events: list[str] = []

    def _provide_new_open() -> Generator[_OpenProviderService[int], None, None]:
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    resolver = container.compile()
    provider = resolver.resolve(Provider[_OpenProviderService[int]])

    container.add_generator(_provide_new_open, provides=_OpenProviderService[int])

    resolved = provider()
    assert isinstance(resolved, _OpenProviderServiceImpl)
    assert resolved.type_arg is str

    resolver.close()

    assert events == ["new-open-enter", "new-open-exit"]


def test_open_generic_stale_root_provider_call_racing_close_is_cleaned_up() -> None:
    container = Container(use_resolver_context=False)
    events: list[str] = []
    provider_started = threading.Event()
    release_provider = threading.Event()
    provider_result: list[_OpenProviderService[int]] = []
    provider_errors: list[BaseException] = []

    def _provide_new_open() -> Generator[_OpenProviderService[int], None, None]:
        provider_started.set()
        if not release_provider.wait(timeout=5):
            msg = "Timed out waiting to release provider."
            raise RuntimeError(msg)
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    provider = container.resolve(Provider[_OpenProviderService[int]])
    container.add_generator(_provide_new_open, provides=_OpenProviderService[int])

    def _call_provider() -> None:
        try:
            provider_result.append(provider())
        except BaseException as error:
            provider_errors.append(error)

    provider_thread = threading.Thread(target=_call_provider)
    provider_thread.start()
    assert provider_started.wait(timeout=5)

    close_thread = threading.Thread(target=container.close)
    close_thread.start()
    close_thread.join(timeout=0.05)
    assert close_thread.is_alive()

    release_provider.set()
    provider_thread.join(timeout=5)
    close_thread.join(timeout=5)

    assert not provider_thread.is_alive()
    assert not close_thread.is_alive()
    assert provider_errors == []
    assert len(provider_result) == 1
    resolved = provider_result[0]
    assert isinstance(resolved, _OpenProviderServiceImpl)
    assert resolved.type_arg is str
    assert events == ["new-open-enter", "new-open-exit"]


def test_open_generic_root_provider_called_from_cleanup_closes_latest_graph() -> None:
    container = Container()
    events: list[str] = []
    provider: Provider[_OpenProviderService[int]] | None = None

    def _provide_resource() -> Generator[_LiveResource, None, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            resolved = provider()
            assert isinstance(resolved, _OpenProviderServiceImpl)
            events.append(f"cleanup-provider-{resolved.type_arg.__name__}")
            events.append("old-exit-end")

    def _provide_new_open() -> Generator[_OpenProviderService[int], None, None]:
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    container.add_generator(_provide_resource, provides=_LiveResource)

    with container as root_resolver:
        provider = root_resolver.resolve(Provider[_OpenProviderService[int]])
        assert root_resolver.resolve(_LiveResource).value == "old"

        container.add_generator(_provide_new_open, provides=_OpenProviderService[int])

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-open-enter",
        "cleanup-provider-str",
        "old-exit-end",
        "new-open-exit",
    ]


def test_open_generic_root_provider_called_from_direct_resolver_cleanup_closes_latest() -> None:
    container = Container()
    events: list[str] = []
    provider: Provider[_OpenProviderService[int]] | None = None

    def _provide_resource() -> Generator[_LiveResource, None, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            resolved = provider()
            assert isinstance(resolved, _OpenProviderServiceImpl)
            events.append(f"cleanup-provider-{resolved.type_arg.__name__}")
            events.append("old-exit-end")

    def _provide_new_open() -> Generator[_OpenProviderService[int], None, None]:
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    container.add_generator(_provide_resource, provides=_LiveResource)
    root_resolver = container.compile()
    provider = root_resolver.resolve(Provider[_OpenProviderService[int]])
    assert root_resolver.resolve(_LiveResource).value == "old"

    container.add_generator(_provide_new_open, provides=_OpenProviderService[int])
    root_resolver.close()

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-open-enter",
        "cleanup-provider-str",
        "old-exit-end",
        "new-open-exit",
    ]


def test_open_generic_cleanup_callback_can_call_stale_provider_before_base_closes() -> None:
    container = Container()
    events: list[str] = []

    def _provide_open_owner(
        type_arg: type[T],
        service_provider: Provider[_LiveService],
    ) -> Generator[_OpenProviderCleanupOwner[T], None, None]:
        events.append("open-enter")
        try:
            yield _OpenProviderCleanupOwner(type_arg=type_arg)
        finally:
            events.append("open-exit-start")
            events.append(f"cleanup-provider-{service_provider().value}")
            events.append("open-exit-end")

    def _provide_new_service() -> Generator[_LiveService, None, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_open_owner, provides=_OpenProviderCleanupOwner)
    root_resolver = container.compile()
    owner = root_resolver.resolve(_OpenProviderCleanupOwner[int])
    assert owner.type_arg is int

    container.add_generator(_provide_new_service, provides=_LiveService)
    root_resolver.close()

    assert events == [
        "open-enter",
        "open-exit-start",
        "new-enter",
        "cleanup-provider-new",
        "open-exit-end",
        "new-exit",
    ]


@pytest.mark.asyncio
async def test_open_generic_async_provider_handle_uses_latest_container_graph_after_mutation() -> (
    None
):
    container = Container()
    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)

    provider = await container.aresolve(AsyncProvider[_OpenProviderService[int]])

    container.add_instance(
        _OpenProviderServiceImpl(type_arg=str),
        provides=_OpenProviderService[int],
    )

    resolved = await provider()

    assert isinstance(resolved, _OpenProviderServiceImpl)
    assert resolved.type_arg is str


@pytest.mark.asyncio
async def test_open_generic_stale_root_async_provider_from_compiled_resolver_owns_cleanup() -> None:
    container = Container()
    events: list[str] = []

    async def _provide_new_open() -> AsyncGenerator[_OpenProviderService[int], None]:
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    resolver = container.compile()
    provider = await resolver.aresolve(AsyncProvider[_OpenProviderService[int]])

    container.add_generator(_provide_new_open, provides=_OpenProviderService[int])

    resolved = await provider()
    assert isinstance(resolved, _OpenProviderServiceImpl)
    assert resolved.type_arg is str

    await resolver.aclose()

    assert events == ["new-open-enter", "new-open-exit"]


@pytest.mark.asyncio
async def test_open_generic_root_async_provider_called_from_cleanup_closes_latest_graph() -> None:
    container = Container()
    events: list[str] = []
    provider: AsyncProvider[_OpenProviderService[int]] | None = None

    async def _provide_resource() -> AsyncGenerator[_LiveResource, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            resolved = await provider()
            assert isinstance(resolved, _OpenProviderServiceImpl)
            events.append(f"cleanup-provider-{resolved.type_arg.__name__}")
            events.append("old-exit-end")

    async def _provide_new_open() -> AsyncGenerator[_OpenProviderService[int], None]:
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    container.add_generator(_provide_resource, provides=_LiveResource)

    async with container as root_resolver:
        provider = await root_resolver.aresolve(AsyncProvider[_OpenProviderService[int]])
        assert (await root_resolver.aresolve(_LiveResource)).value == "old"

        container.add_generator(_provide_new_open, provides=_OpenProviderService[int])

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-open-enter",
        "cleanup-provider-str",
        "old-exit-end",
        "new-open-exit",
    ]


@pytest.mark.asyncio
async def test_open_generic_root_async_provider_from_direct_resolver_cleanup_closes_latest() -> (
    None
):
    container = Container()
    events: list[str] = []
    provider: AsyncProvider[_OpenProviderService[int]] | None = None

    async def _provide_resource() -> AsyncGenerator[_LiveResource, None]:
        events.append("old-enter")
        try:
            yield _LiveResource("old")
        finally:
            events.append("old-exit-start")
            assert provider is not None
            resolved = await provider()
            assert isinstance(resolved, _OpenProviderServiceImpl)
            events.append(f"cleanup-provider-{resolved.type_arg.__name__}")
            events.append("old-exit-end")

    async def _provide_new_open() -> AsyncGenerator[_OpenProviderService[int], None]:
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    container.add_generator(_provide_resource, provides=_LiveResource)
    root_resolver = container.compile()
    provider = await root_resolver.aresolve(AsyncProvider[_OpenProviderService[int]])
    assert (await root_resolver.aresolve(_LiveResource)).value == "old"

    container.add_generator(_provide_new_open, provides=_OpenProviderService[int])
    await root_resolver.aclose()

    assert events == [
        "old-enter",
        "old-exit-start",
        "new-open-enter",
        "cleanup-provider-str",
        "old-exit-end",
        "new-open-exit",
    ]


@pytest.mark.asyncio
async def test_open_generic_async_cleanup_can_call_stale_provider_before_base_closes() -> None:
    container = Container()
    events: list[str] = []

    async def _provide_open_owner(
        type_arg: type[T],
        service_provider: AsyncProvider[_LiveService],
    ) -> AsyncGenerator[_OpenProviderCleanupOwner[T], None]:
        events.append("open-enter")
        try:
            yield _OpenProviderCleanupOwner(type_arg=type_arg)
        finally:
            events.append("open-exit-start")
            events.append(f"cleanup-provider-{(await service_provider()).value}")
            events.append("open-exit-end")

    async def _provide_new_service() -> AsyncGenerator[_LiveService, None]:
        events.append("new-enter")
        try:
            yield _LiveService("new")
        finally:
            events.append("new-exit")

    container.add_instance(_LiveService("old"), provides=_LiveService)
    container.add_generator(_provide_open_owner, provides=_OpenProviderCleanupOwner)
    root_resolver = container.compile()
    owner = await root_resolver.aresolve(_OpenProviderCleanupOwner[int])
    assert owner.type_arg is int

    container.add_generator(_provide_new_service, provides=_LiveService)
    await root_resolver.aclose()

    assert events == [
        "open-enter",
        "open-exit-start",
        "new-enter",
        "cleanup-provider-new",
        "open-exit-end",
        "new-exit",
    ]


def test_inactive_scoped_open_generic_stale_provider_raises_scope_mismatch() -> None:
    container = Container()
    container.add_factory(
        _build_open_provider_service,
        provides=_OpenProviderService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_OpenProviderService[int]])

    container.add_instance(
        _OpenProviderServiceImpl(type_arg=str),
        provides=_OpenProviderService[int],
    )

    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        provider()


def test_open_generic_stale_provider_from_reused_pooled_scope_stays_closed() -> None:
    container = Container()
    container.add_factory(
        _build_open_provider_service,
        provides=_OpenProviderService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    root_resolver = container.compile()

    with root_resolver.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_OpenProviderService[int]])

    container.add_instance(
        _OpenProviderServiceImpl(type_arg=str),
        provides=_OpenProviderService[int],
    )

    with root_resolver.enter_scope(Scope.REQUEST):
        pass

    with pytest.raises(DIWireScopeMismatchError, match="scope has closed"):
        provider()


def test_scoped_open_generic_provider_owns_latest_root_for_root_dependency() -> None:
    container = Container()
    events: list[str] = []

    def _provide_new_open() -> Generator[_OpenProviderService[int], None, None]:
        events.append("new-open-enter")
        try:
            yield _OpenProviderServiceImpl(type_arg=cast("type[int]", str))
        finally:
            events.append("new-open-exit")

    container.add_factory(_build_open_provider_service, provides=_OpenProviderService)
    root_resolver = container.compile()
    with root_resolver.enter_scope(Scope.REQUEST) as request_scope:
        provider = request_scope.resolve(Provider[_OpenProviderService[int]])

        container.add_generator(_provide_new_open, provides=_OpenProviderService[int])

        resolved = provider()
        assert isinstance(resolved, _OpenProviderServiceImpl)
        assert resolved.type_arg is str
    root_resolver.close()

    assert events == ["new-open-enter", "new-open-exit"]


def test_autoregistration_unwraps_provider_dependency() -> None:
    container = Container(
        dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE
    )
    container.add(_AutoregConsumer)

    assert container._providers_registrations.find_by_type(_AutoregDependency) is not None


def test_provider_rejects_deeper_scoped_dependency_during_planning() -> None:
    container = Container()
    container.add(
        _ScopedActionDependency,
        scope=Scope.ACTION,
        lifetime=Lifetime.SCOPED,
    )
    container.add(
        _RequestScopedProviderConsumer,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with pytest.raises(
        DIWireInvalidProviderSpecError,
        match="cannot bind deeper dependency",
    ):
        container.compile()


@pytest.mark.parametrize(
    "factory",
    [_build_vararg_provider_consumer, _build_varkw_provider_consumer],
)
def test_provider_rejects_star_parameter_shapes(factory: object) -> None:
    container = Container()
    container.add(_VarArgDependency)
    container.add_factory(
        cast("Any", factory),
        provides=(
            _VarArgProviderConsumer
            if factory is _build_vararg_provider_consumer
            else _VarKwProviderConsumer
        ),
    )

    with pytest.raises(
        DIWireInvalidProviderSpecError,
        match=r"star parameters \(\*args/\*\*kwargs\)",
    ):
        container.compile()
