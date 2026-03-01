from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from mypy.nodes import ARG_NAMED, ARG_NAMED_OPT, ARG_OPT, ARG_POS, ARG_STAR2
from mypy.types import AnyType, TypeOfAny

from diwire._internal.integrations import mypy_plugin


class _FakeCallableType:
    def __init__(
        self,
        *,
        arg_types: list[Any],
        arg_kinds: list[Any],
        arg_names: list[str | None],
    ) -> None:
        self.arg_types = arg_types
        self.arg_kinds = arg_kinds
        self.arg_names = arg_names

    def copy_modified(
        self,
        *,
        arg_types: list[Any],
        arg_kinds: list[Any],
        arg_names: list[str | None],
    ) -> tuple[list[Any], list[Any], list[str | None]]:
        return (arg_types, arg_kinds, arg_names)


class _FakeUnionType:
    def __init__(self, items: list[Any]) -> None:
        self.items = items


class _FailingLookupApi:
    def __init__(self, error: type[BaseException]) -> None:
        self._error = error

    def named_generic_type(self, _name: str, _args: list[Any]) -> Any:
        raise self._error("lookup failed")


class _SuccessfulLookupApi:
    def __init__(self, resolved_type: Any) -> None:
        self._resolved_type = resolved_type

    def named_generic_type(self, _name: str, _args: list[Any]) -> Any:
        return self._resolved_type


def test_get_method_hook_dispatches_expected_hooks() -> None:
    plugin = cast("Any", object())

    assert (
        mypy_plugin.DIWireMypyPlugin.get_method_hook(plugin, mypy_plugin._INJECT_METHOD_FULLNAME)
        is mypy_plugin._transform_inject_method
    )
    assert (
        mypy_plugin.DIWireMypyPlugin.get_method_hook(
            plugin,
            mypy_plugin._INJECT_DECORATOR_CALL_FULLNAME,
        )
        is mypy_plugin._transform_inject_decorator_call
    )
    assert mypy_plugin.DIWireMypyPlugin.get_method_hook(plugin, "unknown.fullname") is None


def test_transform_inject_decorator_call_returns_default_when_first_argument_is_not_callable(
    monkeypatch: Any,
) -> None:
    default_return_type = object()
    ctx = SimpleNamespace(default_return_type=default_return_type)
    monkeypatch.setattr(mypy_plugin, "_first_argument_callable_type", lambda _ctx: None)

    transformed = mypy_plugin._transform_inject_decorator_call(cast("Any", ctx))

    assert transformed is default_return_type


def test_first_argument_callable_type_returns_none_for_non_callable(monkeypatch: Any) -> None:
    ctx = SimpleNamespace(arg_types=[[object()]])
    monkeypatch.setattr(mypy_plugin, "get_proper_type", lambda value: value)

    resolved = mypy_plugin._first_argument_callable_type(cast("Any", ctx))

    assert resolved is None


def test_build_precise_injected_callable_type_appends_optional_resolver(monkeypatch: Any) -> None:
    callable_type = _FakeCallableType(
        arg_types=["injected_param"],
        arg_kinds=[ARG_POS],
        arg_names=["service"],
    )
    monkeypatch.setattr(
        mypy_plugin, "_unwrap_injected_parameter_type", lambda _value: ("Service", True)
    )
    monkeypatch.setattr(mypy_plugin, "_resolver_protocol_type", lambda _ctx: "ResolverProtocol")

    transformed = mypy_plugin._build_precise_injected_callable_type(
        ctx=cast("Any", SimpleNamespace()),
        callable_type=cast("Any", callable_type),
    )

    assert transformed == (
        ["Service", "ResolverProtocol"],
        [ARG_OPT, ARG_NAMED_OPT],
        ["service", "diwire_resolver"],
    )


def test_build_precise_injected_callable_type_keeps_existing_resolver_kwarg(
    monkeypatch: Any,
) -> None:
    callable_type = _FakeCallableType(
        arg_types=["ResolverProtocol"],
        arg_kinds=[ARG_NAMED_OPT],
        arg_names=["diwire_resolver"],
    )
    monkeypatch.setattr(
        mypy_plugin, "_unwrap_injected_parameter_type", lambda value: (value, False)
    )

    transformed = mypy_plugin._build_precise_injected_callable_type(
        ctx=cast("Any", SimpleNamespace()),
        callable_type=cast("Any", callable_type),
    )

    assert transformed == (
        ["ResolverProtocol"],
        [ARG_NAMED_OPT],
        ["diwire_resolver"],
    )


def test_build_precise_injected_callable_type_inserts_resolver_before_kwargs(
    monkeypatch: Any,
) -> None:
    callable_type = _FakeCallableType(
        arg_types=["required", "kwargs"],
        arg_kinds=[ARG_POS, ARG_STAR2],
        arg_names=["required", None],
    )
    monkeypatch.setattr(
        mypy_plugin, "_unwrap_injected_parameter_type", lambda value: (value, False)
    )
    monkeypatch.setattr(mypy_plugin, "_resolver_protocol_type", lambda _ctx: "ResolverProtocol")

    transformed = mypy_plugin._build_precise_injected_callable_type(
        ctx=cast("Any", SimpleNamespace()),
        callable_type=cast("Any", callable_type),
    )

    assert transformed == (
        ["required", "ResolverProtocol", "kwargs"],
        [ARG_POS, ARG_NAMED_OPT, ARG_STAR2],
        ["required", "diwire_resolver", None],
    )


def test_unwrap_injected_parameter_type_rejects_non_duplicate_union_shapes(
    monkeypatch: Any,
) -> None:
    original_type = object()
    monkeypatch.setattr(mypy_plugin, "UnionType", _FakeUnionType)
    monkeypatch.setattr(mypy_plugin, "get_proper_type", lambda _value: _FakeUnionType([1, 2, 3]))

    unwrapped, is_injected = mypy_plugin._unwrap_injected_parameter_type(cast("Any", original_type))

    assert unwrapped is original_type
    assert is_injected is False


def test_unwrap_injected_parameter_type_rejects_non_matching_duplicate_union(
    monkeypatch: Any,
) -> None:
    original_type = object()
    monkeypatch.setattr(mypy_plugin, "UnionType", _FakeUnionType)
    monkeypatch.setattr(mypy_plugin, "get_proper_type", lambda _value: _FakeUnionType([1, 2]))
    monkeypatch.setattr(mypy_plugin, "is_same_type", lambda _left, _right: False)

    unwrapped, is_injected = mypy_plugin._unwrap_injected_parameter_type(cast("Any", original_type))

    assert unwrapped is original_type
    assert is_injected is False


def test_to_optional_argument_kind_maps_named_and_passthrough() -> None:
    assert mypy_plugin._to_optional_argument_kind(ARG_NAMED) == ARG_NAMED_OPT
    assert mypy_plugin._to_optional_argument_kind(ARG_NAMED_OPT) == ARG_NAMED_OPT


def test_resolver_protocol_type_returns_any_when_lookup_fails() -> None:
    for error in (AssertionError, KeyError):
        ctx = SimpleNamespace(api=_FailingLookupApi(error))
        resolved = mypy_plugin._resolver_protocol_type(cast("Any", ctx))
        assert isinstance(resolved, AnyType)
        assert resolved.type_of_any == TypeOfAny.from_error


def test_resolver_protocol_type_returns_named_type_when_lookup_succeeds() -> None:
    expected_type = object()
    ctx = SimpleNamespace(api=_SuccessfulLookupApi(expected_type))

    resolved = mypy_plugin._resolver_protocol_type(cast("Any", ctx))

    assert resolved is expected_type
