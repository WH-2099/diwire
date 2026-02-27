from __future__ import annotations

from typing import cast

import pytest

pytest.importorskip("click")
pytest.importorskip("typer")

import click
import typer

import diwire._internal.integrations.typer as typer_integration
from diwire import Container
from diwire.exceptions import DIWireIntegrationError


def test_get_typer_context_raises_when_context_is_missing() -> None:
    with pytest.raises(DIWireIntegrationError, match="Typer context not available"):
        typer_integration.get_typer_context()


def test_get_typer_context_returns_current_context() -> None:
    with click.Context(click.Command("context-direct"), info_name="context-direct") as expected:
        resolved = typer_integration.get_typer_context()

    assert resolved is expected


def test_add_typer_context_registers_factory_for_container_resolution() -> None:
    container = Container()
    typer_integration.add_typer_context(container)

    with click.Context(click.Command("context-service"), info_name="context-service"):
        expected = cast("typer.Context", click.get_current_context())
        resolved = container.resolve(typer.Context)

    assert resolved is expected
