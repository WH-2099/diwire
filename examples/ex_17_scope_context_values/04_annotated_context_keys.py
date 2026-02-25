"""Annotated provider keys can be backed by ContextVar values."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Annotated, TypeAlias

from diwire import Component, Container, Lifetime, Scope

ReplicaNumber: TypeAlias = Annotated[int, Component("replica")]

replica_number_var: ContextVar[int] = ContextVar("replica_number", default=0)


class ReplicaConsumer:
    def __init__(self, value: ReplicaNumber) -> None:
        self.value = value


def read_replica_number() -> ReplicaNumber:
    return replica_number_var.get()


def build_consumer(value: ReplicaNumber) -> ReplicaConsumer:
    return ReplicaConsumer(value=value)


def main() -> None:
    container = Container()
    container.add_factory(
        read_replica_number,
        provides=ReplicaNumber,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add_factory(
        build_consumer,
        provides=ReplicaConsumer,
        scope=Scope.REQUEST,
        lifetime=Lifetime.TRANSIENT,
    )

    with container.enter_scope(Scope.REQUEST) as request_scope:
        token = replica_number_var.set(42)
        try:
            resolved = request_scope.resolve(ReplicaConsumer)
            direct = request_scope.resolve(ReplicaNumber)
        finally:
            replica_number_var.reset(token)

    print(f"consumer_value={resolved.value}")  # => consumer_value=42
    print(f"direct_value={direct}")  # => direct_value=42


if __name__ == "__main__":
    main()
