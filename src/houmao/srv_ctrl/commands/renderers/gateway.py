"""Curated gateway-domain renderers for ``houmao-mgr`` print styles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import click


# ---------------------------------------------------------------------------
# Gateway status
# ---------------------------------------------------------------------------

_STATUS_ESSENTIAL = (
    "attach_identity",
    "backend",
    "gateway_health",
    "gateway_host",
    "gateway_port",
    "managed_agent_connectivity",
    "request_admission",
    "execution_mode",
    "gateway_tmux_window_index",
    "active_execution",
    "queue_depth",
)


def render_gateway_status_plain(payload: object) -> None:
    """Render gateway status as aligned key-value lines."""
    data = _as_dict(payload)
    if not data:
        click.echo("(no gateway status)")
        return

    click.echo("Gateway Status:")
    max_k = max(len(k) for k in _STATUS_ESSENTIAL)
    for key in _STATUS_ESSENTIAL:
        click.echo(f"  {key:<{max_k}}  {_pv(data.get(key))}")


def render_gateway_status_fancy(payload: object) -> None:
    """Render gateway status as a rich panel."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    data = _as_dict(payload)
    if not data:
        Console().print("[dim](no gateway status)[/dim]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")

    for key in _STATUS_ESSENTIAL:
        val = data.get(key)
        styled = _fancy_status_value(key, val)
        table.add_row(key, styled)

    Console().print(Panel(table, title="[bold]Gateway Status[/bold]"))


# ---------------------------------------------------------------------------
# Prompt result
# ---------------------------------------------------------------------------


def render_prompt_result_plain(payload: object) -> None:
    """Render prompt control result as a compact summary."""
    data = _as_dict(payload)
    status = data.get("status", "unknown")
    detail = data.get("detail", "")
    forced = data.get("forced", False)
    click.echo(f"Prompt: {status}  forced={_pv(forced)}  {detail}")


def render_prompt_result_fancy(payload: object) -> None:
    """Render prompt control result as rich output."""
    from rich.console import Console

    data = _as_dict(payload)
    status = data.get("status", "unknown")
    detail = data.get("detail", "")
    forced = data.get("forced", False)
    style = "green" if status == "ok" else "red"
    Console().print(
        f"[{style}]Prompt: {status}[/{style}]  forced={'yes' if forced else 'no'}  {detail}"
    )


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


def _fancy_status_value(key: str, value: Any) -> str:
    """Colorize known status fields."""
    s = _pv(value)
    if key == "gateway_health":
        return f"[green]{s}[/green]" if s == "healthy" else f"[red]{s}[/red]"
    if key == "managed_agent_connectivity":
        return f"[green]{s}[/green]" if s == "connected" else f"[yellow]{s}[/yellow]"
    if key == "active_execution":
        return f"[cyan]{s}[/cyan]" if s == "idle" else f"[yellow]{s}[/yellow]"
    return s
