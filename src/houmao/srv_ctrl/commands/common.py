"""Shared helpers for `houmao-srv-ctrl`."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Sequence

import click

from houmao.server.client import HoumaoServerClient

_CAO_DEFAULT_PORT = int(os.environ.get("CAO_PORT", "9889"))


def require_cao_executable() -> str:
    """Return the installed `cao` executable or raise."""

    executable = shutil.which("cao")
    if executable is None:
        raise click.ClickException("`cao` is not available on PATH.")
    return executable


def resolve_server_base_url(*, port: int | None = None) -> str:
    """Return the Houmao server base URL for CAO-compatible delegation."""

    return f"http://127.0.0.1:{port or _CAO_DEFAULT_PORT}"


def require_supported_houmao_pair(*, base_url: str) -> HoumaoServerClient:
    """Ensure the target server is a real `houmao-server`."""

    client = HoumaoServerClient(base_url)
    try:
        health = client.health_extended()
    except Exception as exc:
        raise click.ClickException(f"Failed to reach `houmao-server` at {base_url}: {exc}") from exc
    if health.houmao_service != "houmao-server":
        raise click.ClickException(
            "The supported replacement is `houmao-server + houmao-srv-ctrl`; "
            "mixed usage with raw `cao-server` is unsupported."
        )
    return client


def run_passthrough(
    *,
    command_name: str,
    extra_args: Sequence[str],
) -> subprocess.CompletedProcess[bytes]:
    """Delegate one CAO-compatible command to the installed `cao` executable."""

    executable = require_cao_executable()
    return subprocess.run([executable, command_name, *extra_args], check=False)


def extract_option_value(args: Sequence[str], option_name: str) -> str | None:
    """Extract one CLI option value from passthrough args."""

    prefix = f"{option_name}="
    for index, value in enumerate(args):
        if value == option_name:
            if index + 1 < len(args):
                return args[index + 1]
            return None
        if value.startswith(prefix):
            return value[len(prefix) :]
    return None


def has_flag(args: Sequence[str], flag_name: str) -> bool:
    """Return whether a passthrough flag is present."""

    return any(value == flag_name for value in args)
