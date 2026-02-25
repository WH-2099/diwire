"""Focused example: auto-open scope reuses already-open resolvers."""

from __future__ import annotations

from collections.abc import Generator
from contextvars import ContextVar

from diwire import Container, Injected, Lifetime, Scope, resolver_context


class RequestResource:
    pass


current_value_var: ContextVar[int] = ContextVar("auto_open_scope_reuse_value", default=0)


def main() -> None:
    container = Container()
    cleanup_state = {"cleaned": False}

    def provide_request_resource() -> Generator[RequestResource, None, None]:
        try:
            yield RequestResource()
        finally:
            cleanup_state["cleaned"] = True

    def provide_current_value() -> int:
        return current_value_var.get()

    container.add_generator(
        provide_request_resource,
        provides=RequestResource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )
    container.add_factory(provide_current_value, provides=int, scope=Scope.SESSION)

    @resolver_context.inject(scope=Scope.REQUEST, auto_open_scope=True)
    def use_request_resource(resource: Injected[RequestResource]) -> RequestResource:
        return resource

    with container.enter_scope(Scope.REQUEST) as request_scope:
        resolved_resource = use_request_resource(diwire_resolver=request_scope)
        print(
            f"target_scope_reused={isinstance(resolved_resource, RequestResource) and not cleanup_state['cleaned']}",
        )  # => target_scope_reused=True

    print(
        f"cleanup_after_outer_scope={cleanup_state['cleaned']}"
    )  # => cleanup_after_outer_scope=True

    @resolver_context.inject(scope=Scope.SESSION, auto_open_scope=True)
    def read_value(value: Injected[int]) -> int:
        return value

    with (
        container.enter_scope(Scope.SESSION) as session_scope,
        session_scope.enter_scope(Scope.REQUEST) as request_scope,
    ):
        token = current_value_var.set(22)
        try:
            resolved_value = read_value(diwire_resolver=request_scope)
        finally:
            current_value_var.reset(token)
        print(
            f"deeper_scope_contextvar_reused={resolved_value}"
        )  # => deeper_scope_contextvar_reused=22


if __name__ == "__main__":
    main()
