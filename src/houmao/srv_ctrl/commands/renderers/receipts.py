"""Output formatting for compact command receipts."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.text import Text

from ..output import emit


def emit_receipt(payload: object) -> None:
    """Emit the same complete receipt fields in all output modes."""

    emit(payload, plain_renderer=_render_plain, fancy_renderer=_render_fancy)


def _receipt_rows(payload: object) -> list[tuple[str, str]]:
    """Render arrays in full and escape control characters in string values."""

    if not isinstance(payload, dict):
        return []
    return [
        (key, value if isinstance(value, str) and value.isprintable() else json.dumps(value))
        for key, value in payload.items()
    ]


def _render_plain(payload: object) -> None:
    """Print each receipt field as a complete value."""

    rows = _receipt_rows(payload)
    width = max((len(key) for key, _ in rows), default=0)
    for key, value in rows:
        click.echo(f"  {key:<{width}}  {value}")


def _render_fancy(payload: object) -> None:
    """Style receipt keys and preserve unwrapped opaque references."""

    rows = _receipt_rows(payload)
    width = max((len(key) for key, _ in rows), default=0)
    console = Console()
    for key, value in rows:
        line = Text(f"  {key:<{width}}", style="bold cyan")
        line.append(f"  {value}")
        console.print(line, soft_wrap=True)
