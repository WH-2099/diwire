from __future__ import annotations

from typing import cast

import click
import typer

from diwire import Container, Injected, Lifetime, Scope, resolver_context
from diwire.exceptions import DIWireIntegrationError
from tests.e2e.typer.setup.services import ContextInfoService

app = typer.Typer()


def get_typer_context() -> typer.Context:
    try:
        return cast("typer.Context", click.get_current_context())
    except RuntimeError as error:
        msg = "Typer context not available. Ensure the command runs inside a Typer application."
        raise DIWireIntegrationError(msg) from error


container = Container()
container.add_factory(
    get_typer_context,
    provides=typer.Context,
    lifetime=Lifetime.TRANSIENT,
)
container.add(
    ContextInfoService,
    scope=Scope.REQUEST,
    lifetime=Lifetime.SCOPED,
)


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
    service: Injected[ContextInfoService],
) -> None:
    typer.echo(service.describe(ctx))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
