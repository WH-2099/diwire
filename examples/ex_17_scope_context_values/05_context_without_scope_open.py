"""ContextVar-backed dependencies work with default values without opening scopes."""

from __future__ import annotations

from contextvars import ContextVar

from diwire import Container, Injected, Lifetime, resolver_context

current_value_var: ContextVar[int] = ContextVar("current_value_no_scope", default=5)


def read_current_value() -> int:
    return current_value_var.get()


def main() -> None:
    container = Container()
    container.add_factory(read_current_value, provides=int, lifetime=Lifetime.TRANSIENT)

    @resolver_context.inject(auto_open_scope=False)
    def handler(value: Injected[int]) -> int:
        return value

    default_value = handler()

    token = current_value_var.set(7)
    try:
        overridden_value = handler()
    finally:
        current_value_var.reset(token)

    print(f"default_value={default_value}")  # => default_value=5
    print(f"overridden_value={overridden_value}")  # => overridden_value=7


if __name__ == "__main__":
    main()
