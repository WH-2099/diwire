from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


class BaseScope(int):
    """Represent a numeric DI scope level with transition metadata.

    A scope behaves like an ``int`` so comparisons and ordering are based on
    ``level``. ``skippable`` marks helper scopes that can be skipped by default
    transitions when ``enter_scope(None)`` chooses the next non-skippable scope.
    """

    def __new__(cls, *args: Any, **_kwargs: Any) -> BaseScope:  # noqa: PYI034
        return super().__new__(cls, *args)

    def __init__(self, level: int, *, skippable: bool = False) -> None:
        self.skippable = skippable
        self.level = level

    def __set_name__(
        self,
        owner: type[object],
        name: str,
    ) -> None:
        # ``BaseScope`` values are plain constants. Reusing ``Scope.REQUEST`` as a
        # class attribute on arbitrary user classes should not rewrite the shared
        # metadata used by resolver generation and scope traversal.
        if not issubclass(owner, BaseScopes):
            return

        if getattr(self, "owner", None) is owner and getattr(self, "scope_name", None) == name:
            return
        if hasattr(self, "owner") or hasattr(self, "scope_name"):
            return

        self.owner = owner
        self.scope_name = name

    def __repr__(self) -> str:
        return f"Scope.{self.scope_name}({self.level}, skippable={self.skippable})"


@dataclass(frozen=True, kw_only=True)
class BaseScopes:
    """Collect scope constants and derive helper subsets.

    The ``skippable`` tuple is populated automatically from declared scope
    members and is used by resolver transition logic.
    """

    skippable: tuple[BaseScope, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "skippable",
            tuple(scope for scope in self if scope.skippable),
        )

    def __iter__(self) -> Iterator[BaseScope]:
        for value in self.__dict__.values():
            if isinstance(value, BaseScope):
                yield value


@dataclass(frozen=True)
class Scopes(BaseScopes):
    """Define the built-in DI scope ladder ordered by ``level``.

    Levels increase with nesting depth. Calling ``enter_scope()`` with no
    explicit target transitions to the next deeper non-skippable scope.

    Examples:
        .. code-block:: python

            with container.enter_scope(Scope.REQUEST) as request_resolver:
                service = request_resolver.resolve(Service)

    """

    APP: BaseScope = field(default=BaseScope(1))
    SESSION: BaseScope = field(default=BaseScope(2, skippable=True))
    REQUEST: BaseScope = field(default=BaseScope(3))
    ACTION: BaseScope = field(default=BaseScope(4))
    STEP: BaseScope = field(default=BaseScope(5))


Scope = Scopes()
"""Provide the default scope constants used by container APIs.

Examples:
    .. code-block:: python

        with container.enter_scope(Scope.REQUEST) as request_resolver:
            handler = request_resolver.resolve(Handler)
"""
