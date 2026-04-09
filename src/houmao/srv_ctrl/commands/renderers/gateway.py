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
# Reminder views
# ---------------------------------------------------------------------------


_REMINDER_TABLE_COLUMNS = (
    "reminder_id",
    "ranking",
    "selection_state",
    "delivery_state",
    "paused",
    "mode",
    "delivery_kind",
    "next_due_at_utc",
    "title",
)


def render_reminder_list_plain(payload: object) -> None:
    """Render one reminder-set view as aligned plain text."""

    data = _as_dict(payload)
    reminders = _reminder_rows(data)
    effective_reminder_id = data.get("effective_reminder_id")
    click.echo("Gateway Reminders:")
    click.echo(f"  effective_reminder_id  {_pv(effective_reminder_id)}")
    if not reminders:
        click.echo("  reminders              (empty)")
        return
    _render_plain_reminder_table(reminders)


def render_reminder_list_fancy(payload: object) -> None:
    """Render one reminder-set view as a rich table."""

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    data = _as_dict(payload)
    reminders = _reminder_rows(data)
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("effective_reminder_id", _pv(data.get("effective_reminder_id")))
    if reminders:
        table.add_row("count", str(len(reminders)))
    else:
        table.add_row("reminders", "[dim](empty)[/dim]")
        Console().print(Panel(table, title="[bold]Gateway Reminders[/bold]"))
        return

    reminder_table = Table(show_header=True)
    for column in _REMINDER_TABLE_COLUMNS:
        reminder_table.add_column(column, no_wrap=column not in {"title"})
    for row in reminders:
        reminder_table.add_row(*[_pv(row.get(column)) for column in _REMINDER_TABLE_COLUMNS])
    table.add_row("reminders", reminder_table)
    Console().print(Panel(table, title="[bold]Gateway Reminders[/bold]"))


def render_reminder_detail_plain(payload: object) -> None:
    """Render one reminder plus effective reminder context as aligned plain text."""

    data = _as_dict(payload)
    reminder = _reminder_detail(data)
    if not reminder:
        click.echo("(no reminder)")
        return

    click.echo("Gateway Reminder:")
    click.echo(f"  effective_reminder_id  {_pv(data.get('effective_reminder_id'))}")
    max_k = max(len(key) for key in _REMINDER_TABLE_COLUMNS)
    for key in _REMINDER_TABLE_COLUMNS:
        click.echo(f"  {key:<{max_k}}  {_pv(reminder.get(key))}")
    if reminder.get("prompt") is not None:
        click.echo(f"  {'prompt':<{max_k}}  {_pv(reminder.get('prompt'))}")
    if isinstance(reminder.get("send_keys"), dict):
        click.echo(f"  {'send_keys':<{max_k}}  {json_like(reminder.get('send_keys'))}")
    if reminder.get("blocked_by_reminder_id") is not None:
        click.echo(
            f"  {'blocked_by_reminder_id':<{max_k}}  {_pv(reminder.get('blocked_by_reminder_id'))}"
        )


def render_reminder_detail_fancy(payload: object) -> None:
    """Render one reminder plus effective reminder context as rich output."""

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    data = _as_dict(payload)
    reminder = _reminder_detail(data)
    if not reminder:
        Console().print("[dim](no reminder)[/dim]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("effective_reminder_id", _pv(data.get("effective_reminder_id")))
    for key in _REMINDER_TABLE_COLUMNS:
        table.add_row(key, _pv(reminder.get(key)))
    if reminder.get("prompt") is not None:
        table.add_row("prompt", _pv(reminder.get("prompt")))
    if isinstance(reminder.get("send_keys"), dict):
        table.add_row("send_keys", json_like(reminder.get("send_keys")))
    if reminder.get("blocked_by_reminder_id") is not None:
        table.add_row("blocked_by_reminder_id", _pv(reminder.get("blocked_by_reminder_id")))
    Console().print(Panel(table, title="[bold]Gateway Reminder[/bold]"))


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


def _reminder_rows(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return normalized reminder rows from one reminder-set payload."""

    reminders = data.get("reminders")
    if not isinstance(reminders, list):
        return []
    return [dict(item) for item in reminders if isinstance(item, Mapping)]


def _reminder_detail(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return one normalized reminder from either a wrapper or a raw reminder payload."""

    reminder = data.get("reminder")
    if isinstance(reminder, Mapping):
        return dict(reminder)
    if "reminder_id" in data:
        return dict(data)
    return {}


def _render_plain_reminder_table(reminders: list[dict[str, Any]]) -> None:
    """Render a compact reminder table for plain output."""

    widths = {column: len(column) for column in _REMINDER_TABLE_COLUMNS}
    string_rows: list[dict[str, str]] = []
    for reminder in reminders:
        rendered_row: dict[str, str] = {}
        for column in _REMINDER_TABLE_COLUMNS:
            value = _pv(reminder.get(column))
            rendered_row[column] = value
            widths[column] = max(widths[column], len(value))
        string_rows.append(rendered_row)

    header = "  ".join(f"{column:<{widths[column]}}" for column in _REMINDER_TABLE_COLUMNS)
    click.echo(f"  {header}")
    for row in string_rows:
        line = "  ".join(f"{row[column]:<{widths[column]}}" for column in _REMINDER_TABLE_COLUMNS)
        click.echo(f"  {line}")


def json_like(value: object) -> str:
    """Render one nested payload compactly for reminder detail views."""

    if isinstance(value, Mapping):
        parts = ", ".join(f"{key}={_pv(item)}" for key, item in value.items())
        return f"{{{parts}}}"
    return _pv(value)
