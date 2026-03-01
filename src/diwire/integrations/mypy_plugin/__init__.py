from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from mypy.plugin import Plugin


__all__ = ["plugin"]


def plugin(version: str) -> type[Plugin]:
    """Return the DIWire mypy plugin class for mypy's plugin loader.

    Args:
        version: Mypy version string provided by mypy's plugin loader.

    Returns:
        DIWire mypy plugin class.

    """
    _ = version
    module = importlib.import_module("diwire._internal.integrations.mypy_plugin")
    return cast("type[Plugin]", module.DIWireMypyPlugin)
