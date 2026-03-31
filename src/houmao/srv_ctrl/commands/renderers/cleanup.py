"""Curated cleanup renderers for ``houmao-mgr`` print styles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import click

_ACTION_BUCKETS: tuple[tuple[str, str], ...] = (
    ("planned_actions", "Planned Actions"),
    ("applied_actions", "Applied Actions"),
    ("blocked_actions", "Blocked Actions"),
    ("preserved_actions", "Preserved Actions"),
)


def render_cleanup_payload_plain(payload: object) -> None:
    """Render one cleanup payload as human-oriented plain text."""

    data = _as_dict(payload)
    if not data:
        click.echo("(no cleanup result)")
        return

    click.echo("Cleanup Plan:" if bool(data.get("dry_run")) else "Cleanup Result:")
    _render_detail_block_plain("Scope", _as_dict(data.get("scope")))
    _render_detail_block_plain("Resolution", _as_dict(data.get("resolution")))

    rendered_bucket = False
    for bucket_key, label in _ACTION_BUCKETS:
        actions = _as_action_rows(data.get(bucket_key))
        if not actions:
            continue
        rendered_bucket = True
        click.echo("")
        click.echo(f"{label} ({len(actions)}):")
        for action in actions:
            click.echo(f"  - {_format_action_line(action)}")

    if not rendered_bucket:
        click.echo("")
        click.echo("No cleanup actions.")

    summary = _as_dict(data.get("summary"))
    if summary:
        click.echo("")
        click.echo(f"Summary: {_format_summary(summary)}")


def render_cleanup_payload_fancy(payload: object) -> None:
    """Render one cleanup payload with rich tables."""

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    data = _as_dict(payload)
    if not data:
        console.print("[dim](no cleanup result)[/dim]")
        return

    header = Table(show_header=False, box=None, padding=(0, 2))
    header.add_column("Key", style="bold cyan", no_wrap=True)
    header.add_column("Value")
    header.add_row("mode", "dry-run" if bool(data.get("dry_run")) else "execute")

    scope = _as_dict(data.get("scope"))
    for key, value in scope.items():
        header.add_row(f"scope.{key}", _pv(value))

    resolution = _as_dict(data.get("resolution"))
    for key, value in resolution.items():
        header.add_row(f"resolution.{key}", _pv(value))

    console.print(Panel(header, title="[bold]Cleanup[/bold]"))

    rendered_bucket = False
    for bucket_key, label in _ACTION_BUCKETS:
        actions = _as_action_rows(data.get(bucket_key))
        if not actions:
            continue
        rendered_bucket = True
        table = Table(title=label)
        table.add_column("artifact_kind", no_wrap=True)
        table.add_column("path")
        table.add_column("reason")
        table.add_column("details")
        for action in actions:
            table.add_row(
                _pv(action.get("artifact_kind")),
                _pv(action.get("path")),
                _pv(action.get("reason")),
                _format_details(_as_dict(action.get("details"))),
            )
        console.print(table)

    if not rendered_bucket:
        console.print("[dim]No cleanup actions.[/dim]")

    summary = _as_dict(data.get("summary"))
    if summary:
        summary_table = Table(title="Summary")
        summary_table.add_column("key", style="bold cyan", no_wrap=True)
        summary_table.add_column("value")
        for key, value in summary.items():
            summary_table.add_row(str(key), _pv(value))
        console.print(summary_table)


def _render_detail_block_plain(title: str, data: dict[str, Any]) -> None:
    """Render one small metadata block for plain cleanup output."""

    if not data:
        return
    click.echo(f"{title}:")
    max_key_len = max(len(str(key)) for key in data)
    for key, value in data.items():
        click.echo(f"  {str(key):<{max_key_len}}  {_pv(value)}")


def _format_action_line(action: dict[str, Any]) -> str:
    """Format one cleanup action for plain text."""

    artifact_kind = _pv(action.get("artifact_kind"))
    path = _pv(action.get("path"))
    reason = _pv(action.get("reason"))
    details = _format_details(_as_dict(action.get("details")))
    line = f"[{artifact_kind}] {path} :: {reason}"
    if details:
        line = f"{line} ({details})"
    return line


def _format_summary(summary: dict[str, Any]) -> str:
    """Format the cleanup summary as compact key-value text."""

    return ", ".join(f"{key}={_pv(value)}" for key, value in summary.items())


def _format_details(details: dict[str, Any]) -> str:
    """Format cleanup action details as compact key-value text."""

    if not details:
        return ""
    return ", ".join(f"{key}={_pv(details[key])}" for key in sorted(details))


def _as_dict(payload: object) -> dict[str, Any]:
    """Normalize payload to a plain dict."""

    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _as_action_rows(payload: object) -> list[dict[str, Any]]:
    """Normalize one cleanup bucket to a list of action dicts."""

    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        return []
    rows: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, Mapping):
            rows.append(dict(item))
    return rows


def _pv(value: Any) -> str:
    """Format one cleanup renderer value."""

    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, dict):
        if not value:
            return "{}"
        return "{...}"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        return f"[{len(value)} items]"
    return str(value)
