"""Print-style output engine for ``houmao-mgr``.

Provides three output modes — *plain*, *json*, and *fancy* — controlled by
``--print-plain`` / ``--print-json`` / ``--print-fancy`` CLI flags or the
``HOUMAO_CLI_PRINT_STYLE`` environment variable.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from typing import Any, Literal

import click
from pydantic import BaseModel

PrintStyle = Literal["plain", "json", "fancy"]
"""Supported output styles for ``houmao-mgr``."""

PRINT_STYLE_ENV_VAR = "HOUMAO_CLI_PRINT_STYLE"
"""Environment variable for persistent print-style preference."""

_VALID_STYLES: frozenset[str] = frozenset({"plain", "json", "fancy"})


# ---------------------------------------------------------------------------
# OutputContext
# ---------------------------------------------------------------------------


class OutputContext:
    """Holds the resolved print style and an optional lazy ``rich.Console``.

    Stored in ``click.Context.obj["output"]`` by the root group.
    """

    def __init__(self, style: PrintStyle = "plain") -> None:
        self.style: PrintStyle = style
        self._console: Any | None = None

    @property
    def console(self) -> Any:
        """Return a ``rich.Console`` instance, created on first access."""
        if self._console is None:
            from rich.console import Console

            self._console = Console()
        return self._console

    # -- dispatch ------------------------------------------------------------

    def emit(
        self,
        payload: object,
        *,
        plain_renderer: Callable[[object], None] | None = None,
        fancy_renderer: Callable[[object], None] | None = None,
    ) -> None:
        """Dispatch *payload* to the active print-style renderer."""
        if self.style == "json":
            _render_json(payload)
        elif self.style == "fancy":
            if fancy_renderer is not None:
                fancy_renderer(payload)
            else:
                _render_fancy(payload, console=self.console)
        else:
            if plain_renderer is not None:
                plain_renderer(payload)
            else:
                _render_plain(payload)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def resolve_print_style(explicit: str | None) -> PrintStyle:
    """Resolve the active print style: flag → env var → default ``plain``."""
    if explicit is not None and explicit in _VALID_STYLES:
        return explicit  # type: ignore[return-value]
    env_val = os.environ.get(PRINT_STYLE_ENV_VAR, "").strip().lower()
    if env_val in _VALID_STYLES:
        return env_val  # type: ignore[return-value]
    return "plain"


def output_options(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Click decorator that adds ``--print-plain/--print-json/--print-fancy``."""
    fn = click.option(
        "--print-fancy",
        "print_style",
        flag_value="fancy",
        help="Rich-formatted output with tables and colors.",
    )(fn)
    fn = click.option(
        "--print-json",
        "print_style",
        flag_value="json",
        help="Machine-readable JSON output.",
    )(fn)
    fn = click.option(
        "--print-plain",
        "print_style",
        flag_value="plain",
        help="Plain text output (default).",
    )(fn)
    return fn


# ---------------------------------------------------------------------------
# Top-level emit() — reads OutputContext from click context
# ---------------------------------------------------------------------------


def emit(
    payload: object,
    *,
    plain_renderer: Callable[[object], None] | None = None,
    fancy_renderer: Callable[[object], None] | None = None,
) -> None:
    """Central output dispatcher.

    Reads the ``OutputContext`` from the current click context and delegates
    to the matching renderer.  Falls back to ``plain`` when called outside
    a click context (e.g. in tests).
    """
    ctx = click.get_current_context(silent=True)
    if ctx is not None and isinstance(ctx.obj, dict) and "output" in ctx.obj:
        output_ctx: OutputContext = ctx.obj["output"]
    else:
        output_ctx = OutputContext()
    output_ctx.emit(payload, plain_renderer=plain_renderer, fancy_renderer=fancy_renderer)


# ---------------------------------------------------------------------------
# Generic JSON renderer
# ---------------------------------------------------------------------------


def _normalize_payload(payload: object) -> object:
    """Normalize a payload to a JSON-compatible Python object."""
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    return payload


def _render_json(payload: object) -> None:
    """Emit *payload* as JSON with stable formatting."""
    click.echo(json.dumps(_normalize_payload(payload), indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Generic plain renderer
# ---------------------------------------------------------------------------


def _render_plain(payload: object) -> None:
    """Emit *payload* as aligned plain text via ``click.echo()``."""
    normalized = _normalize_payload(payload)

    if isinstance(normalized, dict):
        _render_plain_dict(normalized)
    elif isinstance(normalized, (list, tuple)):
        _render_plain_sequence(normalized)
    else:
        click.echo(str(normalized))


def _render_plain_dict(data: dict[str, Any]) -> None:
    """Render a dict as aligned ``key:  value`` lines.

    If the dict has exactly one key whose value is a list of dicts,
    render it as a columnar table instead.
    """
    list_key, list_items = _detect_single_list_key(data)
    if list_key is not None and list_items is not None:
        _render_plain_table(list_items, title=list_key)
        return

    if not data:
        click.echo("{}")
        return

    max_key_len = max(len(str(k)) for k in data)
    for key, value in data.items():
        formatted = _plain_value(value)
        click.echo(f"  {str(key):<{max_key_len}}  {formatted}")


def _render_plain_sequence(items: Sequence[Any]) -> None:
    """Render a list — delegate to table if items are dicts."""
    if items and isinstance(items[0], dict):
        _render_plain_table(list(items))
    else:
        for item in items:
            click.echo(f"  - {item}")


def _render_plain_table(rows: list[dict[str, Any]], *, title: str | None = None) -> None:
    """Render a list of dicts as an aligned columnar table."""
    if not rows:
        click.echo("  (empty)")
        return

    columns = list(rows[0].keys())
    col_widths = {col: len(str(col)) for col in columns}
    str_rows: list[dict[str, str]] = []
    for row in rows:
        str_row: dict[str, str] = {}
        for col in columns:
            val = _plain_value(row.get(col, ""))
            str_row[col] = val
            col_widths[col] = max(col_widths[col], len(val))
        str_rows.append(str_row)

    if title:
        click.echo(f"{title} ({len(rows)}):")

    header = "  ".join(f"{col:<{col_widths[col]}}" for col in columns)
    click.echo(f"  {header}")
    for str_row in str_rows:
        line = "  ".join(f"{str_row[col]:<{col_widths[col]}}" for col in columns)
        click.echo(f"  {line}")


def _plain_value(value: Any) -> str:
    """Format one value for plain-text display."""
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


def _detect_single_list_key(
    data: dict[str, Any],
) -> tuple[str | None, list[dict[str, Any]] | None]:
    """Detect a dict with one key whose value is a list of dicts."""
    list_keys = [k for k, v in data.items() if isinstance(v, list)]
    if len(list_keys) == 1:
        items = data[list_keys[0]]
        if items and isinstance(items[0], dict):
            return list_keys[0], items
    return None, None


# ---------------------------------------------------------------------------
# Generic fancy renderer
# ---------------------------------------------------------------------------


def _render_fancy(payload: object, *, console: Any) -> None:
    """Emit *payload* using ``rich`` tables and panels."""
    from rich.tree import Tree

    normalized = _normalize_payload(payload)

    if isinstance(normalized, dict):
        list_key, list_items = _detect_single_list_key(normalized)
        if list_key is not None and list_items is not None:
            _render_fancy_table(list_items, title=list_key, console=console)
            return
        _render_fancy_dict(normalized, console=console)
    elif isinstance(normalized, (list, tuple)):
        if normalized and isinstance(normalized[0], dict):
            _render_fancy_table(list(normalized), console=console)
        else:
            tree = Tree("items")
            for item in normalized:
                tree.add(str(item))
            console.print(tree)
    else:
        console.print(str(normalized))


def _render_fancy_dict(data: dict[str, Any], *, console: Any) -> None:
    """Render a flat dict as a rich key-value table."""
    from rich.table import Table

    if not data:
        console.print("[dim](empty)[/dim]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(str(key), _fancy_value(value))
    console.print(table)


def _render_fancy_table(
    rows: list[dict[str, Any]], *, title: str | None = None, console: Any
) -> None:
    """Render a list of dicts as a rich table."""
    from rich.table import Table

    if not rows:
        console.print("[dim](empty)[/dim]")
        return

    table = Table(title=title, show_lines=False)
    columns = list(rows[0].keys())
    for col in columns:
        table.add_column(str(col), no_wrap=True)
    for row in rows:
        table.add_row(*(str(_fancy_value(row.get(col, ""))) for col in columns))
    console.print(table)


def _fancy_value(value: Any) -> str:
    """Format one value for rich-text display."""
    if value is None:
        return "[dim]-[/dim]"
    if isinstance(value, bool):
        return "[green]yes[/green]" if value else "[red]no[/red]"
    if isinstance(value, dict):
        if not value:
            return "[dim]{}[/dim]"
        return "[dim]{...}[/dim]"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[dim][][/dim]"
        return f"[dim][{len(value)} items][/dim]"
    return str(value)
