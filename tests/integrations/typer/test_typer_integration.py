from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from diwire import Container, Injected, Lifetime, Scope, resolver_context
from diwire.exceptions import DIWireIntegrationError

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner

click = pytest.importorskip("click")
typer = pytest.importorskip("typer")


class _ContextInfoService:
    def __init__(self, context: typer.Context) -> None:
        self._context = context

    def describe(self, current: typer.Context) -> str:
        info_name = self._context.info_name or "<missing>"
        same = "same" if self._context is current else "different"
        return f"{info_name}:{same}"


def _get_typer_context() -> typer.Context:
    try:
        return cast("typer.Context", click.get_current_context())
    except RuntimeError as error:
        msg = "Typer context not available. Ensure the command runs inside a Typer application."
        raise DIWireIntegrationError(msg) from error


@pytest.fixture()
def app() -> typer.Typer:
    container = Container()
    container.add_factory(
        _get_typer_context,
        provides=typer.Context,
        lifetime=Lifetime.TRANSIENT,
    )
    container.add(
        _ContextInfoService,
        scope=Scope.REQUEST,
        lifetime=Lifetime.SCOPED,
    )

    app = typer.Typer()

    @app.command("context-direct")
    @resolver_context.inject(scope=Scope.REQUEST)
    def context_direct(
        ctx: typer.Context,
        resolved_ctx: Injected[typer.Context],
    ) -> None:
        info_name = resolved_ctx.info_name or "<missing>"
        same = "same" if resolved_ctx is ctx else "different"
        typer.echo(f"{info_name}:{same}")

    @app.command("context-service")
    @resolver_context.inject(scope=Scope.REQUEST)
    def context_service(
        ctx: typer.Context,
        service: Injected[_ContextInfoService],
    ) -> None:
        typer.echo(service.describe(ctx))

    return app


@pytest.fixture()
def runner() -> CliRunner:
    from typer.testing import CliRunner

    return CliRunner()


def test_context_resolve_for_direct_command(runner: CliRunner, app: typer.Typer) -> None:
    result = runner.invoke(app, ["context-direct"], prog_name="diwire")

    assert result.exit_code == 0
    assert result.stdout.strip() == "context-direct:same"


def test_context_resolve_in_service_for_command(runner: CliRunner, app: typer.Typer) -> None:
    result = runner.invoke(app, ["context-service"], prog_name="diwire")

    assert result.exit_code == 0
    assert result.stdout.strip() == "context-service:same"


def test_context_resolution_raises_when_not_invoked_by_typer() -> None:
    container = Container()
    container.add_factory(
        _get_typer_context,
        provides=typer.Context,
        lifetime=Lifetime.TRANSIENT,
    )

    with pytest.raises(DIWireIntegrationError, match="Typer context not available"):
        container.resolve(typer.Context)
