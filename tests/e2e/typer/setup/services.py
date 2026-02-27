from __future__ import annotations

import typer


class ContextInfoService:
    def __init__(self, context: typer.Context) -> None:
        self._context = context

    def describe(self, current: typer.Context) -> str:
        info_name = self._context.info_name or "<missing>"
        same = "same" if self._context is current else "different"
        return f"{info_name}:{same}"
