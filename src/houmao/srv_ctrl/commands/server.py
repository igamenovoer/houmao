"""Server lifecycle commands for `houmao-mgr`."""

from __future__ import annotations

import click

from houmao.cao.rest_client import CaoApiError
from houmao.server.client import HoumaoServerClient

from .common import (
    emit_json,
    pair_port_option,
    require_supported_houmao_pair,
    resolve_server_base_url,
)
from ...server.commands.serve import run_server, server_serve_options


@click.group(name="server")
def server_group() -> None:
    """Manage the `houmao-server` lifecycle and server-owned sessions."""


@server_group.command(name="start")
@server_serve_options
def start_server_command(
    api_base_url: str,
    runtime_root: str | None,
    watch_poll_interval_seconds: float,
    recent_transition_limit: int,
    stability_threshold_seconds: float,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    supported_tui_processes: tuple[str, ...],
    compat_shell_ready_timeout_seconds: float,
    compat_shell_ready_poll_interval_seconds: float,
    compat_provider_ready_timeout_seconds: float,
    compat_provider_ready_poll_interval_seconds: float,
    compat_codex_warmup_seconds: float,
    startup_child: bool,
) -> None:
    """Start `houmao-server` through the shared startup path."""

    run_server(
        api_base_url=api_base_url,
        runtime_root=runtime_root,
        watch_poll_interval_seconds=watch_poll_interval_seconds,
        recent_transition_limit=recent_transition_limit,
        stability_threshold_seconds=stability_threshold_seconds,
        completion_stability_seconds=completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        supported_tui_processes=supported_tui_processes,
        compat_shell_ready_timeout_seconds=compat_shell_ready_timeout_seconds,
        compat_shell_ready_poll_interval_seconds=compat_shell_ready_poll_interval_seconds,
        compat_provider_ready_timeout_seconds=compat_provider_ready_timeout_seconds,
        compat_provider_ready_poll_interval_seconds=compat_provider_ready_poll_interval_seconds,
        compat_codex_warmup_seconds=compat_codex_warmup_seconds,
        startup_child=startup_child,
    )


@server_group.command(name="status")
@pair_port_option()
def status_server_command(port: int | None) -> None:
    """Show server health and a compact active-session summary."""

    base_url = resolve_server_base_url(port=port)
    client = HoumaoServerClient(base_url)
    try:
        health = client.health_extended()
    except Exception:
        emit_json(
            {
                "running": False,
                "api_base_url": base_url,
                "detail": "No houmao-server is running.",
            }
        )
        return

    if health.houmao_service != "houmao-server":
        raise click.ClickException(
            "The supported replacement is `houmao-server + houmao-mgr`; "
            "mixed usage with raw `cao-server` is unsupported."
        )

    try:
        instance = client.current_instance()
    except Exception:
        instance = None
    try:
        sessions = client.list_sessions()
    except Exception:
        sessions = []

    emit_json(
        {
            "running": True,
            "api_base_url": base_url,
            "health": health.model_dump(mode="json"),
            "current_instance": (
                instance.model_dump(mode="json") if instance is not None else None
            ),
            "active_session_count": len(sessions),
            "active_sessions": [session.model_dump(mode="json") for session in sessions],
        }
    )


@server_group.command(name="stop")
@pair_port_option()
def stop_server_command(port: int | None) -> None:
    """Request graceful shutdown of the running `houmao-server`."""

    base_url = resolve_server_base_url(port=port)
    client = HoumaoServerClient(base_url)
    try:
        health = client.health_extended()
    except Exception:
        emit_json(
            {
                "success": True,
                "running": False,
                "api_base_url": base_url,
                "detail": "No houmao-server is running to stop.",
            }
        )
        return

    if health.houmao_service != "houmao-server":
        raise click.ClickException(
            "The supported replacement is `houmao-server + houmao-mgr`; "
            "mixed usage with raw `cao-server` is unsupported."
        )

    response = client.shutdown_server()
    emit_json(
        {
            "success": response.success,
            "running": False,
            "api_base_url": base_url,
            "detail": "Shutdown request accepted.",
        }
    )


@click.group(name="sessions")
def server_sessions_group() -> None:
    """Inspect and control server-owned sessions."""


@server_sessions_group.command(name="list")
@pair_port_option()
def list_server_sessions_command(port: int | None) -> None:
    """List active sessions from the running server."""

    client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
    emit_json({"sessions": [session.model_dump(mode="json") for session in client.list_sessions()]})


@server_sessions_group.command(name="show")
@pair_port_option()
@click.argument("session")
def show_server_session_command(port: int | None, session: str) -> None:
    """Show one server-owned session payload."""

    client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
    emit_json(client.get_session(session).model_dump(mode="json"))


@server_sessions_group.command(name="shutdown")
@click.option("--all", "shutdown_all", is_flag=True, help="Shutdown all server sessions.")
@click.option("--session", help="Shutdown one specific session.")
@pair_port_option()
def shutdown_server_sessions_command(
    shutdown_all: bool,
    session: str | None,
    port: int | None,
) -> None:
    """Shutdown server-owned sessions through the server API."""

    if not shutdown_all and not session:
        raise click.ClickException("Must specify either --all or --session.")
    if shutdown_all and session:
        raise click.ClickException("Cannot use --all and --session together.")

    client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
    if shutdown_all:
        sessions_to_shutdown = [item.id for item in client.list_sessions()]
    else:
        sessions_to_shutdown = [session or ""]

    if not sessions_to_shutdown:
        emit_json({"success": True, "detail": "No server sessions found to shutdown."})
        return

    results: list[dict[str, object]] = []
    for session_name in sessions_to_shutdown:
        try:
            response = client.delete_session(session_name)
            results.append(
                {
                    "session": session_name,
                    "success": response.success,
                }
            )
        except CaoApiError as exc:
            results.append(
                {
                    "session": session_name,
                    "success": False,
                    "detail": exc.detail,
                }
            )
    emit_json({"results": results})


server_group.add_command(server_sessions_group)
