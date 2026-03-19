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
    recent_transition_limit: int,
    supported_tui_processes: tuple[str, ...],
    startup_child: bool,
) -> HoumaoServerConfig:
    """Build one validated server config from CLI inputs."""

    resolved_runtime_root = (
        resolve_runtime_root(explicit_root=runtime_root) if runtime_root else resolve_runtime_root()
    )
    if supported_tui_processes:
        return HoumaoServerConfig(
            api_base_url=api_base_url,
            runtime_root=resolved_runtime_root,
            watch_poll_interval_seconds=watch_poll_interval_seconds,
            recent_transition_limit=recent_transition_limit,
            supported_tui_processes=_parse_supported_tui_processes(supported_tui_processes),
            startup_child=startup_child,
        )
    return HoumaoServerConfig(
        api_base_url=api_base_url,
        runtime_root=resolved_runtime_root,
        watch_poll_interval_seconds=watch_poll_interval_seconds,
        recent_transition_limit=recent_transition_limit,
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


def _parse_supported_tui_processes(values: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """Parse repeated `tool=name1,name2` CLI overrides."""

    if not values:
        return {}

    parsed: dict[str, tuple[str, ...]] = {}
    for value in values:
        tool, separator, names_payload = value.partition("=")
        if not separator:
            raise click.ClickException(
                "Invalid `--supported-tui-process` value. Expected `tool=name1,name2`."
            )
        normalized_tool = tool.strip()
        names = tuple(name.strip() for name in names_payload.split(",") if name.strip())
        if not normalized_tool or not names:
            raise click.ClickException(
                "Invalid `--supported-tui-process` value. Expected `tool=name1,name2`."
            )
        parsed[normalized_tool] = names
    return parsed
