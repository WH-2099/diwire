from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import TypeAlias

from litestar.connection import Request, WebSocket
from litestar.datastructures.state import State
from typing_extensions import Self

LitestarRequest: TypeAlias = Request[object, object, State]
LitestarWebSocket: TypeAlias = WebSocket[object, object, State]
_cleanup_paths: list[str] = []


def latest_cleanup_path() -> str | None:
    if not _cleanup_paths:
        return None
    return _cleanup_paths[-1]


@dataclass
class RequestBasedService:
    request: LitestarRequest

    def work(self) -> str:
        return f"Request path: {self.request.url.path}"


@dataclass
class WebSocketBasedService:
    websocket: LitestarWebSocket

    def work(self) -> str:
        return f"WebSocket path: {self.websocket.url.path}"


@dataclass
class CMService:
    request: LitestarRequest

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
        _cleanup_paths.append(self.request.url.path)
