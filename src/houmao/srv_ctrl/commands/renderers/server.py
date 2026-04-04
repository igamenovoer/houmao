"""Curated server-domain renderers for ``houmao-mgr`` print styles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import click


# ---------------------------------------------------------------------------
# Server status
# ---------------------------------------------------------------------------


def render_server_status_plain(payload: object) -> None:
    """Render server status as a compact plain-text summary."""
    data = _as_dict(payload)
    if not data:
        click.echo("(no server status)")
        return

    running = data.get("running", False)
    click.echo("Server Status:")
    click.echo(f"  running:          {'yes' if running else 'no'}")
    click.echo(f"  api_base_url:     {data.get('api_base_url', '-')}")

    if not running:
        detail = data.get("detail")
        if detail:
            click.echo(f"  detail:           {detail}")
        return

    session_count = data.get("active_session_count")
    if session_count is not None:
        click.echo(f"  active_sessions:  {session_count}")

    health = data.get("health")
    if isinstance(health, dict):
        click.echo(f"  service:          {health.get('houmao_service', health.get('service', '-'))}")

    sessions = data.get("active_sessions")
    if isinstance(sessions, list) and sessions:
        click.echo("")
        _render_session_table_plain(sessions)


def render_server_status_fancy(payload: object) -> None:
    """Render server status as a rich panel with optional session table."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    data = _as_dict(payload)
    if not data:
        console.print("[dim](no server status)[/dim]")
        return

    running = data.get("running", False)
    kv = Table(show_header=False, box=None, padding=(0, 2))
    kv.add_column("Key", style="bold cyan", no_wrap=True)
    kv.add_column("Value")

    status_style = "green" if running else "red"
    kv.add_row("running", f"[{status_style}]{'yes' if running else 'no'}[/{status_style}]")
    kv.add_row("api_base_url", str(data.get("api_base_url", "-")))

    if not running:
        detail = data.get("detail")
        if detail:
            kv.add_row("detail", str(detail))
        console.print(Panel(kv, title="[bold]Server Status[/bold]"))
        return

    session_count = data.get("active_session_count")
    if session_count is not None:
        kv.add_row("active_sessions", str(session_count))

    health = data.get("health")
    if isinstance(health, dict):
        kv.add_row(
            "service",
            str(health.get("houmao_service", health.get("service", "-"))),
        )

    console.print(Panel(kv, title="[bold]Server Status[/bold]"))

    sessions = data.get("active_sessions")
    if isinstance(sessions, list) and sessions:
        _render_session_table_fancy(sessions, console=console)


# ---------------------------------------------------------------------------
# Session list helpers
# ---------------------------------------------------------------------------

_SESSION_COLUMNS = ("id", "agent_name", "backend", "status")


def _render_session_table_plain(sessions: list[dict[str, Any]]) -> None:
    """Render a list of sessions as aligned columns."""
    cols = _SESSION_COLUMNS
    widths = {c: len(c) for c in cols}
    rows: list[dict[str, str]] = []
    for s in sessions:
        row = {c: _pv(s.get(c)) for c in cols}
        for c in cols:
            widths[c] = max(widths[c], len(row[c]))
        rows.append(row)

    header = "  ".join(f"{c:<{widths[c]}}" for c in cols)
    click.echo(f"  {header}")
    for row in rows:
        line = "  ".join(f"{row[c]:<{widths[c]}}" for c in cols)
        click.echo(f"  {line}")


def _render_session_table_fancy(sessions: list[dict[str, Any]], *, console: Any) -> None:
    """Render a list of sessions as a rich table."""
    from rich.table import Table

    table = Table(title="Active Sessions")
    for col in _SESSION_COLUMNS:
        table.add_column(col, no_wrap=True)
    for s in sessions:
        table.add_row(*(_pv(s.get(c)) for c in _SESSION_COLUMNS))
    console.print(table)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_dict(payload: object) -> dict[str, Any]:
    """Normalize payload to dict."""
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _pv(value: Any) -> str:
    """Plain value formatter."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)
