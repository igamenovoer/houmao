"""Curated agent-domain renderers for ``houmao-mgr`` print styles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import click


# ---------------------------------------------------------------------------
# Agent list
# ---------------------------------------------------------------------------

_AGENT_LIST_COLUMNS = (
    "agent_name",
    "tracked_agent_id",
    "tool",
    "transport",
    "lifecycle_state",
    "management_kind",
    "lifecycle_owner",
    "remote_agent_ref",
    "tmux_session_name",
)


def render_agent_list_plain(payload: object) -> None:
    """Render agent list as aligned columns."""
    agents = _extract_agents(payload)
    if not agents:
        click.echo("No managed agents.")
        return

    cols = _AGENT_LIST_COLUMNS
    widths = {c: len(c) for c in cols}
    rows: list[dict[str, str]] = []
    for agent in agents:
        row = {c: _pv(agent.get(c)) for c in cols}
        for c in cols:
            widths[c] = max(widths[c], len(row[c]))
        rows.append(row)

    click.echo(f"Managed Agents ({len(agents)}):")
    header = "  ".join(f"{c:<{widths[c]}}" for c in cols)
    click.echo(f"  {header}")
    for row in rows:
        line = "  ".join(f"{row[c]:<{widths[c]}}" for c in cols)
        click.echo(f"  {line}")


def render_agent_list_fancy(payload: object) -> None:
    """Render agent list as a rich table."""
    from rich.console import Console
    from rich.table import Table

    agents = _extract_agents(payload)
    if not agents:
        Console().print("[dim]No managed agents.[/dim]")
        return

    table = Table(title=f"Managed Agents ({len(agents)})")
    for col in _AGENT_LIST_COLUMNS:
        table.add_column(col, no_wrap=True)
    for agent in agents:
        table.add_row(*(_pv(agent.get(c)) for c in _AGENT_LIST_COLUMNS))
    Console().print(table)


# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------

_STATE_ESSENTIAL = (
    "tracked_agent_id",
    "availability",
)


def render_agent_state_plain(payload: object) -> None:
    """Render agent state as key-value lines with essential fields first."""
    data = _as_dict(payload)
    if not data:
        click.echo("(no state)")
        return

    identity = data.get("identity")
    if isinstance(identity, dict):
        agent_name = identity.get("agent_name") or identity.get("tracked_agent_id", "")
        tool = identity.get("tool", "")
        click.echo(f"Agent: {agent_name}  (tool={tool})")
        _render_external_identity_plain(identity)

    avail = data.get("availability", "unknown")
    click.echo(f"  availability:  {avail}")

    turn = data.get("turn")
    if isinstance(turn, dict):
        click.echo(f"  turn_active:   {_pv(turn.get('active'))}")
        click.echo(f"  turn_id:       {_pv(turn.get('turn_id'))}")

    last_turn = data.get("last_turn")
    if isinstance(last_turn, dict):
        click.echo(f"  last_status:   {_pv(last_turn.get('status'))}")
        click.echo(f"  last_turn_id:  {_pv(last_turn.get('turn_id'))}")

    gateway = data.get("gateway")
    if isinstance(gateway, dict):
        click.echo(f"  gateway:       {_pv(gateway.get('health'))}")

    mailbox = data.get("mailbox")
    if isinstance(mailbox, dict):
        click.echo(f"  mailbox:       {_pv(mailbox.get('status'))}")

    click.echo(f"  memory:        {_pv(data.get('memory_root'))}")
    click.echo(f"  memo_file:     {_pv(data.get('memo_file'))}")
    click.echo(f"  pages_dir:     {_pv(data.get('pages_dir'))}")

    diags = data.get("diagnostics")
    if isinstance(diags, list) and diags:
        click.echo(f"  diagnostics:   {len(diags)} issue(s)")


def render_agent_state_fancy(payload: object) -> None:
    """Render agent state as a rich panel."""
    from rich.console import Console
    from rich.table import Table

    data = _as_dict(payload)
    if not data:
        Console().print("[dim](no state)[/dim]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")

    identity = data.get("identity")
    if isinstance(identity, dict):
        table.add_row("agent_name", str(identity.get("agent_name", "-")))
        table.add_row("tool", str(identity.get("tool", "-")))
        _render_external_identity_fancy(table, identity)

    avail = data.get("availability", "unknown")
    style = "green" if avail == "available" else "red" if avail == "error" else "yellow"
    table.add_row("availability", f"[{style}]{avail}[/{style}]")

    turn = data.get("turn")
    if isinstance(turn, dict):
        table.add_row("turn_active", _pv(turn.get("active")))
        table.add_row("turn_id", _pv(turn.get("turn_id")))

    last_turn = data.get("last_turn")
    if isinstance(last_turn, dict):
        table.add_row("last_status", _pv(last_turn.get("status")))

    gateway = data.get("gateway")
    if isinstance(gateway, dict):
        table.add_row("gateway", _pv(gateway.get("health")))

    mailbox = data.get("mailbox")
    if isinstance(mailbox, dict):
        table.add_row("mailbox", _pv(mailbox.get("status")))

    table.add_row("memory_root", _pv(data.get("memory_root")))
    table.add_row("memo_file", _pv(data.get("memo_file")))
    table.add_row("pages_dir", _pv(data.get("pages_dir")))

    Console().print(table)


# ---------------------------------------------------------------------------
# Launch / join completion
# ---------------------------------------------------------------------------


def render_launch_completion_plain(payload: object) -> None:
    """Render launch or join completion as key-value lines."""
    data = _as_dict(payload)
    status = data.pop("status", None)
    if status:
        click.echo(f"{status}:")
    max_k = max((len(str(k)) for k in data), default=0)
    for k, v in data.items():
        click.echo(f"  {str(k):<{max_k}}  {_pv(v)}")


def render_launch_completion_fancy(payload: object) -> None:
    """Render launch or join completion as a rich panel."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    data = _as_dict(payload)
    status = data.pop("status", "Complete")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(str(k), _pv(v))
    Console().print(Panel(table, title=f"[bold green]{status}[/bold green]"))


# ---------------------------------------------------------------------------
# External managed-agent registry
# ---------------------------------------------------------------------------

_EXTERNAL_AGENT_COLUMNS = (
    "local_name",
    "external_agent_id",
    "lifecycle_owner",
    "pair_api_base_url",
    "remote_agent_ref",
    "gateway_expected",
    "verified_at_utc",
)


def render_external_agent_list_plain(payload: object) -> None:
    """Render external managed-agent records as aligned columns."""

    agents = _extract_external_agents(payload)
    if not agents:
        click.echo("No external managed agents.")
        return
    _render_table_plain("External Managed Agents", agents, _EXTERNAL_AGENT_COLUMNS)


def render_external_agent_list_fancy(payload: object) -> None:
    """Render external managed-agent records as a rich table."""

    agents = _extract_external_agents(payload)
    if not agents:
        from rich.console import Console

        Console().print("[dim]No external managed agents.[/dim]")
        return
    _render_table_fancy(
        title=f"External Managed Agents ({len(agents)})",
        rows=agents,
        columns=_EXTERNAL_AGENT_COLUMNS,
    )


def render_external_agent_detail_plain(payload: object) -> None:
    """Render one external managed-agent record or action result."""

    data = _as_dict(payload)
    action = data.get("action")
    if action is not None:
        click.echo(f"action: {_pv(action)}")
    if "removed" in data:
        click.echo(f"removed: {_pv(data.get('removed'))}")
    if "remote_lifecycle_untouched" in data:
        click.echo(f"remote_lifecycle_untouched: {_pv(data.get('remote_lifecycle_untouched'))}")
    if "gateway_available" in data:
        click.echo(f"gateway_available: {_pv(data.get('gateway_available'))}")

    record = _extract_external_agent(payload)
    if record is None:
        click.echo("(no external agent)")
        return
    _render_key_values_plain(record, title="external_agent")


def render_external_agent_detail_fancy(payload: object) -> None:
    """Render one external managed-agent record or action result as a rich panel."""

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    data = _as_dict(payload)
    record = _extract_external_agent(payload)
    if record is None:
        Console().print("[dim](no external agent)[/dim]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    for key in ("action", "removed", "remote_lifecycle_untouched", "gateway_available"):
        if key in data:
            table.add_row(key, _pv(data.get(key)))
    for key in _EXTERNAL_AGENT_COLUMNS:
        table.add_row(key, _pv(record.get(key)))
    Console().print(Panel(table, title="[bold green]External Managed Agent[/bold green]"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_agents(payload: object) -> list[dict[str, Any]]:
    """Extract the agent list from various payload shapes."""
    if isinstance(payload, Mapping):
        agents = payload.get("agents")
        if isinstance(agents, list):
            return [a if isinstance(a, dict) else {} for a in agents]
    return []


def _extract_external_agents(payload: object) -> list[dict[str, Any]]:
    """Extract external-agent rows from a list payload."""

    if isinstance(payload, Mapping):
        agents = payload.get("external_agents")
        if isinstance(agents, list):
            return [a if isinstance(a, dict) else {} for a in agents]
    return []


def _extract_external_agent(payload: object) -> dict[str, Any] | None:
    """Extract one external-agent record from supported payload shapes."""

    if not isinstance(payload, Mapping):
        return None
    record = payload.get("external_agent")
    if isinstance(record, dict):
        return dict(record)
    return None


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


def _render_table_plain(
    title: str,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> None:
    """Render selected columns from rows as a plain table."""

    widths = {column: len(column) for column in columns}
    rendered_rows: list[dict[str, str]] = []
    for row in rows:
        rendered = {column: _pv(row.get(column)) for column in columns}
        for column in columns:
            widths[column] = max(widths[column], len(rendered[column]))
        rendered_rows.append(rendered)

    click.echo(f"{title} ({len(rows)}):")
    click.echo("  " + "  ".join(f"{column:<{widths[column]}}" for column in columns))
    for row in rendered_rows:
        click.echo("  " + "  ".join(f"{row[column]:<{widths[column]}}" for column in columns))


def _render_table_fancy(
    *,
    title: str,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> None:
    """Render selected columns from rows as a rich table."""

    from rich.console import Console
    from rich.table import Table

    table = Table(title=title)
    for column in columns:
        table.add_column(column, no_wrap=True)
    for row in rows:
        table.add_row(*(_pv(row.get(column)) for column in columns))
    Console().print(table)


def _render_key_values_plain(data: dict[str, Any], *, title: str | None = None) -> None:
    """Render a shallow mapping as plain key-value lines."""

    if title is not None:
        click.echo(f"{title}:")
    visible = {
        key: value
        for key, value in data.items()
        if key != "cached_identity" and not isinstance(value, dict)
    }
    max_key = max((len(key) for key in visible), default=0)
    for key, value in visible.items():
        click.echo(f"  {key:<{max_key}}  {_pv(value)}")
    cached_identity = data.get("cached_identity")
    if isinstance(cached_identity, dict):
        click.echo("  cached_identity:")
        identity_visible = {
            key: value
            for key, value in cached_identity.items()
            if key
            in {
                "agent_name",
                "agent_id",
                "tracked_agent_id",
                "tool",
                "transport",
                "remote_pair_api_base_url",
                "remote_agent_ref",
            }
        }
        identity_max_key = max((len(key) for key in identity_visible), default=0)
        for key, value in identity_visible.items():
            click.echo(f"    {key:<{identity_max_key}}  {_pv(value)}")


def _render_external_identity_plain(identity: dict[str, Any]) -> None:
    """Render external identity metadata when present."""

    if identity.get("management_kind") != "external_communication_only":
        return
    click.echo(f"  management:    {_pv(identity.get('management_kind'))}")
    click.echo(f"  lifecycle:     {_pv(identity.get('lifecycle_owner'))}")
    click.echo(f"  external_id:   {_pv(identity.get('external_agent_id'))}")
    click.echo(f"  remote_pair:   {_pv(identity.get('remote_pair_api_base_url'))}")
    click.echo(f"  remote_ref:    {_pv(identity.get('remote_agent_ref'))}")


def _render_external_identity_fancy(table: Any, identity: dict[str, Any]) -> None:
    """Add external identity metadata rows to a rich table when present."""

    if identity.get("management_kind") != "external_communication_only":
        return
    table.add_row("management_kind", _pv(identity.get("management_kind")))
    table.add_row("lifecycle_owner", _pv(identity.get("lifecycle_owner")))
    table.add_row("external_agent_id", _pv(identity.get("external_agent_id")))
    table.add_row("remote_pair_api_base_url", _pv(identity.get("remote_pair_api_base_url")))
    table.add_row("remote_agent_ref", _pv(identity.get("remote_agent_ref")))
