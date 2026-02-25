"""Focused example: providers can read values from ``contextvars.ContextVar``."""

from __future__ import annotations

from contextvars import ContextVar

from diwire import Container, Lifetime, Scope

request_value_var: ContextVar[int] = ContextVar("request_value", default=0)


class RequestValue:
    def __init__(self, value: int) -> None:
        self.value = value


def build_request_value() -> RequestValue:
    return RequestValue(value=request_value_var.get())


def main() -> None:
    container = Container()
    container.add_factory(
        build_request_value,
        provides=RequestValue,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        token = request_value_var.set(7)
        try:
            resolved = request_scope.resolve(RequestValue)
        finally:
            request_value_var.reset(token)

    print(f"provider_contextvar={resolved.value}")  # => provider_contextvar=7


if __name__ == "__main__":
    main()
