from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_ENABLED_ENV = "TYPER_E2E_ENABLED"
_REPO_ROOT = Path(__file__).resolve().parents[4]

if os.getenv(_ENABLED_ENV) != "1":
    pytest.skip(
        f"{_ENABLED_ENV} is not set to 1; skipping docker-compose Typer e2e tests.",
        allow_module_level=True,
    )


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    # Safe static command invocation for local test fixture module.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "tests.e2e.typer.setup.app", *args],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_context_direct_returns_current_command_context() -> None:
    result = _run_cli("context-direct")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "context-direct:same"


def test_context_service_returns_current_command_context() -> None:
    result = _run_cli("context-service")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "context-service:same"
