"""Read-only query commands for `houmao-server`."""

from __future__ import annotations

import click

from .common import client_for_base_url, echo_json


@click.group(name="sessions")
def sessions_group() -> None:
    """Query compatible session routes."""


@sessions_group.command(name="list")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
def list_sessions_command(api_base_url: str) -> None:
    """List child-backed sessions through `houmao-server`."""

    client = client_for_base_url(api_base_url)
    echo_json({"sessions": client.list_sessions()})


@sessions_group.command(name="get")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
@click.argument("session_name")
def get_session_command(api_base_url: str, session_name: str) -> None:
    """Get one session payload."""

    client = client_for_base_url(api_base_url)
    echo_json(client.get_session(session_name))


@click.group(name="terminals")
def terminals_group() -> None:
    """Query terminal compatibility and extension routes."""


@terminals_group.command(name="state")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
@click.argument("terminal_id")
def terminal_state_command(api_base_url: str, terminal_id: str) -> None:
    """Read the latest Houmao terminal-state view."""

    client = client_for_base_url(api_base_url)
    echo_json(client.terminal_state(terminal_id).model_dump(mode="json"))


@terminals_group.command(name="history")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
@click.option("--limit", default=100, type=int, show_default=True)
@click.argument("terminal_id")
def terminal_history_command(api_base_url: str, limit: int, terminal_id: str) -> None:
    """Read append-only Houmao terminal history."""

    client = client_for_base_url(api_base_url)
    echo_json(client.terminal_history(terminal_id, limit=limit).model_dump(mode="json"))


@click.command(name="health")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
def health_command(api_base_url: str) -> None:
    """Read the compatibility-safe health payload."""

    client = client_for_base_url(api_base_url)
    echo_json(client.health_extended().model_dump(mode="json"))


@click.command(name="current-instance")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
def current_instance_command(api_base_url: str) -> None:
    """Read Houmao current-instance metadata."""

    client = client_for_base_url(api_base_url)
    echo_json(client.current_instance().model_dump(mode="json"))

