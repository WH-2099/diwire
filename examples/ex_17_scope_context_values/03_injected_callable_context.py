"""Injected callables can consume dependencies built from ContextVar values."""

from __future__ import annotations

from contextvars import ContextVar

from diwire import Container, Injected, Lifetime, Scope, resolver_context

current_value_var: ContextVar[int] = ContextVar("current_value", default=0)


def read_current_value() -> int:
    return current_value_var.get()


def main() -> None:
    container = Container()
    container.add_factory(
        read_current_value,
        provides=int,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    @resolver_context.inject(scope=Scope.REQUEST)
    def handler(value: Injected[int]) -> int:
        return value

    with container.enter_scope(Scope.REQUEST) as request_scope:
        token = current_value_var.set(7)
        try:
            from_contextvar = handler(diwire_resolver=request_scope)
            overridden = handler(diwire_resolver=request_scope, value=8)
        finally:
            current_value_var.reset(token)

    print(f"from_contextvar={from_contextvar}")  # => from_contextvar=7
    print(f"overridden={overridden}")  # => overridden=8


if __name__ == "__main__":
    main()
