from __future__ import annotations

from contextvars import ContextVar
from typing import Any, cast

import pytest

import diwire
from diwire import Container, Injected, Lifetime, ResolverContext, Scope
from diwire.exceptions import (
    DIWireInvalidRegistrationError,
    DIWireResolverNotSetError,
)


class _Service:
    def __init__(self, value: str) -> None:
        self.value = value


def test_top_level_resolver_context_export_is_available() -> None:
    assert isinstance(diwire.resolver_context, ResolverContext)


def test_removed_from_context_symbol_is_not_exported() -> None:
    removed_symbol = "FromContext"
    assert not hasattr(diwire, removed_symbol)


def test_removed_enter_scope_context_kwarg_raises_type_error() -> None:
    container = Container()
    kwargs = {"context": {int: 1}}

    with pytest.raises(TypeError, match="context"):
        container.enter_scope(Scope.REQUEST, **kwargs)  # type: ignore[arg-type]


def test_resolver_context_does_not_expose_resolver_stack_mutators() -> None:
    context = ResolverContext()

    assert not hasattr(context, "push_resolver")
    assert not hasattr(context, "pop_resolver")
    assert not hasattr(context, "wrap_resolver")


def test_resolve_raises_when_no_bound_resolver_and_no_fallback_container() -> None:
    context = ResolverContext()

    with pytest.raises(DIWireResolverNotSetError, match="resolver_context"):
        context.resolve(_Service)


@pytest.mark.asyncio
async def test_aresolve_raises_when_no_bound_resolver_and_no_fallback_container() -> None:
    context = ResolverContext()

    with pytest.raises(DIWireResolverNotSetError, match="resolver_context"):
        await context.aresolve(_Service)


def test_enter_scope_raises_when_no_bound_resolver_and_no_fallback_container() -> None:
    context = ResolverContext()

    with pytest.raises(DIWireResolverNotSetError, match="resolver_context"):
        context.enter_scope(Scope.REQUEST)


def test_resolve_uses_fallback_container_when_unbound() -> None:
    context = ResolverContext()
    container = Container(resolver_context=context)
    container.add_instance(_Service("fallback"), provides=_Service)

    assert context.resolve(_Service).value == "fallback"


@pytest.mark.asyncio
async def test_aresolve_uses_fallback_container_when_unbound() -> None:
    context = ResolverContext()
    container = Container(resolver_context=context)
    container.add_instance(_Service("fallback"), provides=_Service)

    assert (await context.aresolve(_Service)).value == "fallback"


def test_enter_scope_uses_fallback_container_when_unbound() -> None:
    context = ResolverContext()
    container = Container(resolver_context=context)
    container.add_instance(_Service("fallback"), provides=_Service)

    with context.enter_scope(Scope.REQUEST) as request_scope:
        assert request_scope.resolve(_Service).value == "fallback"
        with context.enter_scope(Scope.ACTION) as action_scope:
            assert action_scope.resolve(_Service).value == "fallback"
            with context.enter_scope(Scope.STEP) as step_scope:
                assert step_scope.resolve(_Service).value == "fallback"


def test_last_container_wins_for_fallback_resolve_and_enter_scope() -> None:
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance(_Service("first"), provides=_Service)
    second = Container(resolver_context=context)
    second.add_instance(_Service("second"), provides=_Service)

    assert context.resolve(_Service).value == "second"
    with context.enter_scope(Scope.REQUEST) as request_scope:
        assert request_scope.resolve(_Service).value == "second"


@pytest.mark.asyncio
async def test_last_container_wins_for_fallback_aresolve() -> None:
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance(_Service("first"), provides=_Service)
    second = Container(resolver_context=context)
    second.add_instance(_Service("second"), provides=_Service)

    assert (await context.aresolve(_Service)).value == "second"


def test_inject_raises_when_no_resolver_and_no_fallback_container() -> None:
    context = ResolverContext()

    @context.inject
    def handler(service: Injected[_Service]) -> str:
        return service.value

    with pytest.raises(DIWireResolverNotSetError, match=r"resolver_context\.inject"):
        cast("Any", handler)()


def test_inject_explicit_resolver_still_requires_fallback_container() -> None:
    context = ResolverContext()
    resolver = Container().compile()

    @context.inject
    def handler(service: Injected[_Service]) -> str:
        return service.value

    with pytest.raises(DIWireResolverNotSetError, match="fallback container"):
        cast("Any", handler)(diwire_resolver=resolver)


def test_inject_uses_fallback_container_when_unbound() -> None:
    context = ResolverContext()
    container = Container(resolver_context=context)
    container.add_instance(_Service("fallback"), provides=_Service)

    @context.inject
    def handler(service: Injected[_Service]) -> str:
        return service.value

    assert cast("Any", handler)() == "fallback"


def test_inject_requires_explicit_resolver_when_fallback_disables_resolver_context() -> None:
    context = ResolverContext()
    container = Container(resolver_context=context, use_resolver_context=False)
    container.add_instance(_Service("fallback"), provides=_Service)

    @context.inject
    def handler(service: Injected[_Service]) -> str:
        return service.value

    injected_handler = cast("Any", handler)
    with pytest.raises(DIWireResolverNotSetError, match="use_resolver_context=True"):
        injected_handler()

    with container.enter_scope(Scope.REQUEST) as request_scope:
        assert injected_handler(diwire_resolver=request_scope) == "fallback"


def test_last_container_wins_for_fallback_inject() -> None:
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance(_Service("first"), provides=_Service)
    second = Container(resolver_context=context)
    second.add_instance(_Service("second"), provides=_Service)

    @context.inject
    def handler(service: Injected[_Service]) -> str:
        return service.value

    assert cast("Any", handler)() == "second"


def test_context_bound_resolver_takes_precedence_over_fallback_container() -> None:
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance(_Service("first"), provides=_Service)
    second = Container(resolver_context=context)
    second.add_instance(_Service("second"), provides=_Service)

    @context.inject
    def handler(service: Injected[_Service]) -> str:
        return service.value

    assert cast("Any", handler)() == "second"

    with first.compile():
        assert cast("Any", handler)() == "first"


def test_context_bound_resolver_takes_precedence_over_fallback_for_resolve_and_enter_scope() -> (
    None
):
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance(_Service("first"), provides=_Service)
    second = Container(resolver_context=context)
    second.add_instance(_Service("second"), provides=_Service)

    assert context.resolve(_Service).value == "second"
    with context.enter_scope(Scope.REQUEST) as request_scope:
        assert request_scope.resolve(_Service).value == "second"

    with first.compile():
        assert context.resolve(_Service).value == "first"
        with context.enter_scope(Scope.REQUEST) as request_scope:
            assert request_scope.resolve(_Service).value == "first"

    assert context.resolve(_Service).value == "second"


@pytest.mark.asyncio
async def test_context_bound_resolver_takes_precedence_over_fallback_for_aresolve() -> None:
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance(_Service("first"), provides=_Service)
    second = Container(resolver_context=context)
    second.add_instance(_Service("second"), provides=_Service)

    assert (await context.aresolve(_Service)).value == "second"

    async with first.compile():
        assert (await context.aresolve(_Service)).value == "first"

    assert (await context.aresolve(_Service)).value == "second"


def test_nested_sync_context_manager_restores_previous_resolver() -> None:
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance("first", provides=str)
    second = Container(resolver_context=context)
    second.add_instance("second", provides=str)

    with first.compile():
        assert context.resolve(str) == "first"
        with second.compile():
            assert context.resolve(str) == "second"
        assert context.resolve(str) == "first"

    assert context.resolve(str) == "second"


@pytest.mark.asyncio
async def test_nested_async_context_manager_restores_previous_resolver() -> None:
    context = ResolverContext()
    first = Container(resolver_context=context)
    first.add_instance("first", provides=str)
    second = Container(resolver_context=context)
    second.add_instance("second", provides=str)

    async with first.compile():
        assert await context.aresolve(str) == "first"
        async with second.compile():
            assert await context.aresolve(str) == "second"
        assert await context.aresolve(str) == "first"

    assert context.resolve(str) == "second"


def test_fallback_scope_binding_works_when_container_disables_resolver_context() -> None:
    context = ResolverContext()
    container = Container(resolver_context=context, use_resolver_context=False)
    container.add_instance(_Service("fallback"), provides=_Service)

    assert context.resolve(_Service).value == "fallback"

    with context.enter_scope(Scope.REQUEST) as request_scope:
        assert request_scope.resolve(_Service).value == "fallback"
        with context.enter_scope(Scope.ACTION) as action_scope:
            assert action_scope.resolve(_Service).value == "fallback"


def test_inject_rejects_reserved_resolver_parameter_name() -> None:
    context = ResolverContext()

    with pytest.raises(DIWireInvalidRegistrationError, match="cannot declare reserved parameter"):

        @context.inject
        def _handler(diwire_resolver: object, /, service: Injected[_Service]) -> None:
            _ = service


def test_inject_allows_user_parameter_named_user_context() -> None:
    context = ResolverContext()
    container = Container(resolver_context=context)
    container.add_instance(_Service("ok"), provides=_Service)

    @context.inject
    def handler(user_context: object, /, service: Injected[_Service]) -> str:
        return f"{user_context}:{service.value}"

    assert cast("Any", handler)("payload") == "payload:ok"


def test_contextvar_backed_provider_resolves_before_and_after_scope_entry() -> None:
    current_value_var: ContextVar[int] = ContextVar("container_context_value", default=5)
    context = ResolverContext()
    container = Container(resolver_context=context)

    def read_current_value() -> int:
        return current_value_var.get()

    container.add_factory(read_current_value, provides=int, lifetime=Lifetime.TRANSIENT)

    assert context.resolve(int) == 5

    token = current_value_var.set(7)
    try:
        assert context.resolve(int) == 7
        with context.enter_scope(Scope.REQUEST) as request_scope:
            assert request_scope.resolve(int) == 7
    finally:
        current_value_var.reset(token)


def test_contextvar_backed_injected_callable_uses_current_task_value() -> None:
    current_user_id_var: ContextVar[int] = ContextVar("current_user_id", default=0)
    context = ResolverContext()
    container = Container(resolver_context=context)

    def read_current_user_id() -> int:
        return current_user_id_var.get()

    container.add_factory(
        read_current_user_id,
        provides=int,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    @context.inject(scope=Scope.REQUEST)
    def handler(value: Injected[int]) -> int:
        return value

    with context.enter_scope(Scope.REQUEST) as request_scope:
        token = current_user_id_var.set(11)
        try:
            assert cast("Any", handler)(diwire_resolver=request_scope) == 11
            assert cast("Any", handler)(diwire_resolver=request_scope, value=12) == 12
        finally:
            current_user_id_var.reset(token)


def test_contextvar_nested_override_uses_token_reset_behavior() -> None:
    current_value_var: ContextVar[int] = ContextVar("nested_context_value", default=1)
    container = Container()

    def read_current_value() -> int:
        return current_value_var.get()

    container.add_factory(
        read_current_value,
        provides=int,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        assert request_scope.resolve(int) == 1
        outer_token = current_value_var.set(5)
        try:
            assert request_scope.resolve(int) == 5
            inner_token = current_value_var.set(9)
            try:
                with request_scope.enter_scope(Scope.ACTION) as action_scope:
                    assert action_scope.resolve(int) == 9
            finally:
                current_value_var.reset(inner_token)
            assert request_scope.resolve(int) == 5
        finally:
            current_value_var.reset(outer_token)
        assert request_scope.resolve(int) == 1
