"""Shared CLI helpers for `houmao-server`."""

from __future__ import annotations

import json
from typing import Any

import click

from houmao.owned_paths import resolve_runtime_root
from houmao.server.client import HoumaoServerClient
from houmao.server.config import HoumaoServerConfig


def build_config(
    *,
    api_base_url: str,
    runtime_root: str | None,
    watch_poll_interval_seconds: float,
    startup_child: bool,
) -> HoumaoServerConfig:
    """Build one validated server config from CLI inputs."""

    return HoumaoServerConfig(
        api_base_url=api_base_url,
        runtime_root=resolve_runtime_root(explicit_root=runtime_root) if runtime_root else resolve_runtime_root(),
        watch_poll_interval_seconds=watch_poll_interval_seconds,
        startup_child=startup_child,
    )


def client_for_base_url(api_base_url: str) -> HoumaoServerClient:
    """Return a client for one server base URL."""

    return HoumaoServerClient(api_base_url)


def echo_json(payload: dict[str, Any]) -> None:
    """Pretty-print one JSON payload."""

    click.echo(json.dumps(payload, indent=2, sort_keys=True))


def path_option_help() -> str:
    """Return shared runtime-root help text."""

    return "Optional runtime root override for Houmao-owned server artifacts."
