from __future__ import annotations

from contextvars import ContextVar

import pytest

from diwire import Container, Lifetime, Scope
from diwire.exceptions import DIWireScopeMismatchError


class _RequestOnly:
    pass


class _ActionContextValue:
    def __init__(self, value: int) -> None:
        self.value = value


class _AsyncRequestOnly:
    pass


_action_value_var: ContextVar[int] = ContextVar("action_value", default=0)


def _read_action_value() -> int:
    return _action_value_var.get()


def test_container_resolve_uses_context_bound_scope_by_default() -> None:
    container = Container()
    container.add(
        _RequestOnly,
        provides=_RequestOnly,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST):
        assert isinstance(container.resolve(_RequestOnly), _RequestOnly)


@pytest.mark.asyncio
async def test_container_aresolve_uses_context_bound_scope_by_default() -> None:
    container = Container()

    async def build() -> _AsyncRequestOnly:
        return _AsyncRequestOnly()

    container.add_factory(
        build,
        provides=_AsyncRequestOnly,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST):
        assert isinstance(await container.aresolve(_AsyncRequestOnly), _AsyncRequestOnly)


def test_container_resolve_does_not_use_context_bound_scope_when_disabled() -> None:
    container = Container(use_resolver_context=False)
    container.add(
        _RequestOnly,
        provides=_RequestOnly,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST):
        with pytest.raises(DIWireScopeMismatchError, match="requires opened scope level"):
            _ = container.resolve(_RequestOnly)


def test_container_enter_scope_uses_context_bound_scope_for_nesting() -> None:
    container = Container()
    container.add_factory(
        _read_action_value,
        provides=int,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add(
        _ActionContextValue,
        provides=_ActionContextValue,
        scope=Scope.ACTION,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.REQUEST):
        token = _action_value_var.set(7)
        try:
            with container.enter_scope(Scope.ACTION):
                assert container.resolve(_ActionContextValue).value == 7
        finally:
            _action_value_var.reset(token)


def test_container_enter_scope_uses_contextvar_default_when_token_is_not_set() -> None:
    container = Container(use_resolver_context=False)
    container.add_factory(
        _read_action_value,
        provides=int,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add(
        _ActionContextValue,
        provides=_ActionContextValue,
        scope=Scope.ACTION,
        lifetime=Lifetime.SCOPED,
    )

    with container.enter_scope(Scope.ACTION) as action_resolver:
        assert action_resolver.resolve(_ActionContextValue).value == 0
