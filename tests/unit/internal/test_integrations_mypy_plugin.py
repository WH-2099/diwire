from __future__ import annotations

import textwrap
from pathlib import Path

from mypy import api as mypy_api

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_PATH = _REPO_ROOT / "src"


def _run_mypy_check(tmp_path: Path, *, source: str, enable_plugin: bool) -> tuple[int, str]:
    source_path = tmp_path / "snippet.py"
    source_path.write_text(textwrap.dedent(source), encoding="utf-8")

    config_lines = [
        "[mypy]",
        "python_version = 3.10",
        "strict = true",
        "ignore_missing_imports = true",
        f"mypy_path = {_SRC_PATH}",
    ]
    if enable_plugin:
        config_lines.append("plugins = diwire.integrations.mypy_plugin")

    config_path = tmp_path / "mypy.ini"
    config_path.write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    stdout, stderr, exit_code = mypy_api.run(
        [
            "--config-file",
            str(config_path),
            "--no-incremental",
            "--cache-dir",
            str(tmp_path / ".mypy_cache"),
            str(source_path),
        ],
    )

    assert stderr == ""
    return exit_code, stdout


def _count_mypy_errors(output: str) -> int:
    return output.count(": error:")


def test_mypy_plugin_direct_decorator_restores_precise_injection_types(tmp_path: Path) -> None:
    exit_code, output = _run_mypy_check(
        tmp_path,
        enable_plugin=True,
        source="""
            from typing import cast

            from diwire import Injected, ResolverProtocol, resolver_context


            class Service: ...


            @resolver_context.inject
            def handler(required: int, service: Injected[Service]) -> str:
                return "ok"


            resolver = cast(ResolverProtocol, object())
            ok_result: str = handler(1)
            ok_override: str = handler(1, service=Service())
            ok_with_resolver: str = handler(1, diwire_resolver=resolver)

            handler("bad")
            handler(1, service=1)
            handler(1, diwire_resolver=1)
            wrong_return: int = handler(1)
        """,
    )

    assert exit_code == 1
    assert _count_mypy_errors(output) == 4
    assert 'Argument 1 to "handler" has incompatible type "str"; expected "int"' in output
    assert (
        'Argument "service" to "handler" has incompatible type "int"; expected "Service"' in output
    )
    assert (
        'Argument "diwire_resolver" to "handler" has incompatible type "int"; '
        'expected "ResolverProtocol"'
    ) in output
    assert (
        'Incompatible types in assignment (expression has type "str", variable has type "int")'
        in output
    )


def test_mypy_plugin_factory_decorator_restores_precise_injection_types(tmp_path: Path) -> None:
    exit_code, output = _run_mypy_check(
        tmp_path,
        enable_plugin=True,
        source="""
            from diwire import Injected, Scope, resolver_context


            class Service: ...


            @resolver_context.inject()
            def handler(required: int, service: Injected[Service]) -> str:
                return "ok"


            @resolver_context.inject(scope=Scope.REQUEST)
            def scoped_handler(required: int, service: Injected[Service]) -> str:
                return "ok"


            handler(1)
            scoped_handler(1)
            handler(1, service=Service())
            scoped_handler(1, service=Service())

            handler("bad")
            scoped_handler("bad")
            handler(1, service=1)
            scoped_handler(1, service=1)
            handler(1, diwire_resolver=1)
            scoped_handler(1, diwire_resolver=1)
        """,
    )

    assert exit_code == 1
    assert _count_mypy_errors(output) == 6
    assert output.count('expected "int"') == 2
    assert output.count('expected "Service"') == 2
    assert output.count('expected "ResolverProtocol"') == 2


def test_mypy_without_plugin_uses_permissive_arguments_and_strict_return_type(
    tmp_path: Path,
) -> None:
    exit_code, output = _run_mypy_check(
        tmp_path,
        enable_plugin=False,
        source="""
            from diwire import Injected, resolver_context


            class Service: ...


            @resolver_context.inject
            def handler(required: int, service: Injected[Service]) -> int:
                return required


            ok_value: int = handler(1)
            handler("bad")
            handler(1, service=1)
            wrong_return: str = handler(1)
        """,
    )

    assert exit_code == 1
    assert _count_mypy_errors(output) == 1
    assert (
        'Incompatible types in assignment (expression has type "int", variable has type "str")'
        in output
    )
    assert (
        'Argument "service" to "handler" has incompatible type "int"; expected "Service"'
        not in output
    )
    assert 'Argument 1 to "handler" has incompatible type "str"; expected "int"' not in output
