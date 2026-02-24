"""Focused example: ``add_generator`` finally validation and opt-out."""

from __future__ import annotations

from collections.abc import Generator

from diwire import Container, Lifetime, Scope
from diwire.exceptions import DIWireInvalidRegistrationError


class Resource:
    pass


def provide_without_finally() -> Generator[Resource, None, None]:
    yield Resource()


def main() -> None:
    strict_container = Container()

    try:
        strict_container.add_generator(
            provide_without_finally,
            provides=Resource,
            scope=Scope.REQUEST,
            lifetime=Lifetime.SCOPED,
        )
    except DIWireInvalidRegistrationError as error:
        print("default_validation_rejected=True")  # => default_validation_rejected=True
        print(
            f"opt_out_hint_present={'require_generator_finally=False' in str(error)}"
        )  # => opt_out_hint_present=True

    opt_out_container = Container()
    opt_out_container.add_generator(
        provide_without_finally,
        provides=Resource,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
        require_generator_finally=False,
    )

    with opt_out_container.enter_scope() as request_scope:
        resolved = request_scope.resolve(Resource)
        print(f"opt_out_resolve_ok={isinstance(resolved, Resource)}")  # => opt_out_resolve_ok=True


if __name__ == "__main__":
    main()
