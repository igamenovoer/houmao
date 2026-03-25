"""Explicit CAO-compatibility command namespace for `houmao-mgr`."""

from __future__ import annotations

from pathlib import Path
import subprocess

import click

from houmao.cao.rest_client import CaoApiError

from .common import (
    compatibility_launch_timeout_options,
    require_supported_houmao_pair,
    resolve_server_base_url,
)
from .launch import (
    _launch_session_backed_pair_command,
)
from .local_compat import flow_group, init_command, mcp_server_command

_DEFAULT_PROVIDER = "kiro_cli"
_PROVIDERS = frozenset(
    {
        "kiro_cli",
        "claude_code",
        "codex",
        "gemini_cli",
        "kimi_cli",
        "q_cli",
    }
)
_PROVIDERS_REQUIRING_WORKSPACE_ACCESS = frozenset(
    {
        "claude_code",
        "codex",
        "kiro_cli",
        "kimi_cli",
        "gemini_cli",
    }
)
_SESSION_PREFIX = "cao-"
_UPSTREAM_DATABASE_FILE = "/tmp/cao.db"


@click.group(name="cao")
def cao_group() -> None:
    """Explicit CAO-compatible command namespace."""


@click.command(name="launch")
@click.option("--agents", required=True, help="Native launch selector to launch")
@click.option("--session-name", help="Name of the session (default: auto-generated)")
@click.option("--headless", is_flag=True, help="Launch in detached mode")
@click.option(
    "--provider",
    default=_DEFAULT_PROVIDER,
    help=f"Provider to use (default: {_DEFAULT_PROVIDER})",
)
@click.option("--port", default=None, type=int, help="Server port to use")
@click.option("--yolo", is_flag=True, help="Skip workspace trust confirmation")
@compatibility_launch_timeout_options
def cao_launch_command(
    agents: str,
    session_name: str | None,
    headless: bool,
    provider: str,
    port: int | None,
    yolo: bool,
    compat_http_timeout_seconds: float | None,
    compat_create_timeout_seconds: float | None,
) -> None:
    """Launch one CAO-compatible session through the supported Houmao pair."""

    if provider not in _PROVIDERS:
        raise click.ClickException(
            f"Invalid provider '{provider}'. Available providers: {', '.join(sorted(_PROVIDERS))}"
        )

    working_directory = Path.cwd().resolve()
    if provider in _PROVIDERS_REQUIRING_WORKSPACE_ACCESS and not yolo:
        click.echo(
            f"The underlying provider ({provider}) will be trusted to perform all actions "
            f"(read, write, and execute) in:\n"
            f"  {working_directory}\n\n"
            f"To skip this confirmation, use: houmao-mgr cao launch --yolo\n"
        )
        if not click.confirm("Do you trust all the actions in this folder?", default=True):
            raise click.ClickException("Launch cancelled by user")

    _launch_session_backed_pair_command(
        agents=agents,
        session_name=session_name,
        provider=provider,
        port=port,
        working_directory=working_directory,
        attach_to_tmux=not headless,
        emit_created_messages=True,
        compat_http_timeout_seconds=compat_http_timeout_seconds,
        compat_create_timeout_seconds=compat_create_timeout_seconds,
    )


@click.command(name="info")
@click.option("--port", default=None, type=int, hidden=True)
def cao_info_command(port: int | None) -> None:
    """Display CAO-compatible information about the current tmux session."""

    base_url = resolve_server_base_url(port=port)
    client = require_supported_houmao_pair(base_url=base_url)

    click.echo(f"Database path: {_UPSTREAM_DATABASE_FILE}")

    session_name: str | None = None
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True,
            text=True,
            check=True,
        )
        session_name = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        session_name = None

    if session_name and session_name.startswith(_SESSION_PREFIX):
        try:
            data = client.get_session(session_name)
            click.echo(f"Session ID: {session_name}")
            click.echo(f"Active terminals: {len(data.terminals)}")
        except CaoApiError:
            click.echo(f"Session ID: {session_name} (Warning: Session not found in CAO server)")
        return

    click.echo("Not currently in a CAO session.")


@click.command(name="shutdown")
@click.option("--all", "shutdown_all", is_flag=True, help="Shutdown all cao sessions")
@click.option("--session", help="Shutdown specific session")
@click.option("--port", default=None, type=int, hidden=True)
def cao_shutdown_command(
    shutdown_all: bool,
    session: str | None,
    port: int | None,
) -> None:
    """Shutdown tmux sessions and cleanup terminal records."""

    if not shutdown_all and not session:
        raise click.ClickException("Must specify either --all or --session")
    if shutdown_all and session:
        raise click.ClickException("Cannot use --all and --session together")

    base_url = resolve_server_base_url(port=port)
    client = require_supported_houmao_pair(base_url=base_url)

    sessions_to_shutdown: list[str]
    if shutdown_all:
        sessions_to_shutdown = [item.id for item in client.list_sessions()]
    else:
        sessions_to_shutdown = [session or ""]

    if not sessions_to_shutdown:
        click.echo("No cao sessions found to shutdown")
        return

    for session_name in sessions_to_shutdown:
        try:
            client.delete_session(session_name)
            click.echo(f"✓ Shutdown session '{session_name}'")
        except CaoApiError as exc:
            click.echo(f"Error shutting down session '{session_name}': {exc.detail}", err=True)


cao_group.add_command(cao_launch_command)
cao_group.add_command(flow_group)
cao_group.add_command(cao_info_command)
cao_group.add_command(init_command)
cao_group.add_command(mcp_server_command)
cao_group.add_command(cao_shutdown_command)
