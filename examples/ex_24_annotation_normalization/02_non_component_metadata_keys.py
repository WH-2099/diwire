"""Non-component Annotated metadata is ignored for registration key normalization."""

from __future__ import annotations

from typing import Annotated, TypeAlias

from diwire import Component, Container

Priority: TypeAlias = Annotated[int, Component("priority")]
PriorityWithMeta: TypeAlias = Annotated[int, Component("priority"), "meta"]


def main() -> None:
    container = Container()
    container.add_instance(7, provides=int)
    container.add_instance(42, provides=Priority)

    plain = container.resolve(Annotated[int, "request-id"])
    component = container.resolve(PriorityWithMeta)

    print(f"plain={plain}")  # => plain=7
    print(f"component={component}")  # => component=42


if __name__ == "__main__":
    main()
