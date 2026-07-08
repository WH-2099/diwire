"""Focused example: provider handles observe registration updates."""

from __future__ import annotations

from dataclasses import dataclass

from diwire import Container, Provider


@dataclass(slots=True)
class Service:
    value: str


class UsesServiceProvider:
    def __init__(self, service_provider: Provider[Service]) -> None:
        self._service_provider = service_provider

    def get_service(self) -> Service:
        return self._service_provider()


def main() -> None:
    container = Container()
    container.add_instance(Service("old"), provides=Service)
    container.add(UsesServiceProvider)

    consumer = container.resolve(UsesServiceProvider)
    direct_provider = container.resolve(Provider[Service])

    container.add_instance(Service("new"), provides=Service)

    print(
        f"constructor_provider_value={consumer.get_service().value}"
    )  # => constructor_provider_value=new
    print(f"direct_provider_value={direct_provider().value}")  # => direct_provider_value=new


if __name__ == "__main__":
    main()
