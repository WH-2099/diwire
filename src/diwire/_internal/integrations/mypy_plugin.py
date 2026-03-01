from __future__ import annotations

from collections.abc import Callable

from mypy.nodes import ARG_NAMED, ARG_NAMED_OPT, ARG_OPT, ARG_POS, ArgKind
from mypy.plugin import MethodContext, Plugin
from mypy.subtypes import is_same_type
from mypy.types import AnyType, CallableType, Type, TypeOfAny, UnionType, get_proper_type

_INJECT_METHOD_FULLNAME = "diwire._internal.resolver_context.ResolverContext.inject"
_INJECT_DECORATOR_CALL_FULLNAME = "diwire._internal.resolver_context._InjectDecorator.__call__"
_INJECT_RESOLVER_KWARG = "diwire_resolver"
_RESOLVER_PROTOCOL_FULLNAME = "diwire.ResolverProtocol"
_INJECTED_UNION_ITEM_COUNT = 2


class DIWireMypyPlugin(Plugin):
    """Mypy plugin that restores precise typing for ``resolver_context.inject``."""

    def get_method_hook(
        self,
        fullname: str,
    ) -> Callable[[MethodContext], Type] | None:
        if fullname == _INJECT_METHOD_FULLNAME:
            return _transform_inject_method
        if fullname == _INJECT_DECORATOR_CALL_FULLNAME:
            return _transform_inject_decorator_call
        return None


def _transform_inject_method(ctx: MethodContext) -> Type:
    callable_type = _first_argument_callable_type(ctx)
    if callable_type is None:
        return ctx.default_return_type
    return _build_precise_injected_callable_type(ctx=ctx, callable_type=callable_type)


def _transform_inject_decorator_call(ctx: MethodContext) -> Type:
    callable_type = _first_argument_callable_type(ctx)
    if callable_type is None:
        return ctx.default_return_type
    return _build_precise_injected_callable_type(ctx=ctx, callable_type=callable_type)


def _first_argument_callable_type(ctx: MethodContext) -> CallableType | None:
    if not ctx.arg_types or not ctx.arg_types[0]:
        return None
    first_argument_type = get_proper_type(ctx.arg_types[0][0])
    if not isinstance(first_argument_type, CallableType):
        return None
    return first_argument_type


def _build_precise_injected_callable_type(
    *,
    ctx: MethodContext,
    callable_type: CallableType,
) -> CallableType:
    arg_types: list[Type] = []
    arg_kinds: list[ArgKind] = []
    arg_names: list[str | None] = []

    for arg_type, arg_kind, arg_name in zip(
        callable_type.arg_types,
        callable_type.arg_kinds,
        callable_type.arg_names,
        strict=True,
    ):
        parameter_type, is_injected = _unwrap_injected_parameter_type(arg_type)
        arg_types.append(parameter_type)
        arg_kinds.append(_to_optional_argument_kind(arg_kind) if is_injected else arg_kind)
        arg_names.append(arg_name)

    if _INJECT_RESOLVER_KWARG not in arg_names:
        arg_types.append(_resolver_protocol_type(ctx))
        arg_kinds.append(ARG_NAMED_OPT)
        arg_names.append(_INJECT_RESOLVER_KWARG)

    return callable_type.copy_modified(
        arg_types=arg_types,
        arg_kinds=arg_kinds,
        arg_names=arg_names,
    )


def _unwrap_injected_parameter_type(arg_type: Type) -> tuple[Type, bool]:
    proper_type = get_proper_type(arg_type)
    if not isinstance(proper_type, UnionType):
        return arg_type, False
    if len(proper_type.items) != _INJECTED_UNION_ITEM_COUNT:
        return arg_type, False

    left_item, right_item = proper_type.items
    if not is_same_type(left_item, right_item):
        return arg_type, False

    return left_item, True


def _to_optional_argument_kind(arg_kind: ArgKind) -> ArgKind:
    if arg_kind == ARG_POS:
        return ARG_OPT
    if arg_kind == ARG_NAMED:
        return ARG_NAMED_OPT
    return arg_kind


def _resolver_protocol_type(ctx: MethodContext) -> Type:
    try:
        return ctx.api.named_generic_type(_RESOLVER_PROTOCOL_FULLNAME, [])
    except (AssertionError, KeyError):
        return AnyType(TypeOfAny.from_error)
