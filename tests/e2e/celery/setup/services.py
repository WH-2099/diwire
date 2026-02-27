from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class AdderService:
    def add(self, left: int, right: int) -> int:
        return left + right


@dataclass(frozen=True)
class ScopedToken:
    value: str


def build_scoped_token() -> ScopedToken:
    return ScopedToken(value=uuid4().hex)
