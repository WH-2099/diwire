from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

from aiohttp import web
from typing_extensions import Self

_cleanup_paths: list[str] = []


def latest_cleanup_path() -> str | None:
    if not _cleanup_paths:
        return None
    return _cleanup_paths[-1]


@dataclass
class RequestBasedService:
    request: web.Request

    def work(self) -> str:
        return f"Request path: {self.request.path}"


@dataclass
class WebSocketBasedService:
    request: web.Request

    def work(self) -> str:
        return f"WebSocket path: {self.request.path}"


@dataclass
class CMService:
    request: web.Request

    def work(self) -> str:
        return "CMService working"

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        _cleanup_paths.append(self.request.path)
