from __future__ import annotations

from typing import cast

import click
import typer

from diwire import Container, Lifetime
from diwire.exceptions import DIWireIntegrationError


def get_typer_context() -> typer.Context:
    try:
        return cast("typer.Context", click.get_current_context())
    except RuntimeError as error:
        msg = "Typer context not available. Ensure the command runs inside a Typer application."
        raise DIWireIntegrationError(msg) from error


def add_typer_context(container: Container) -> None:
    container.add_factory(
        get_typer_context,
        provides=typer.Context,
        lifetime=Lifetime.TRANSIENT,
    )
