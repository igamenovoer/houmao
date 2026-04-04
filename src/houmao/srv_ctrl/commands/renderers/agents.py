"""Curated agent-domain renderers for ``houmao-mgr`` print styles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import click


# ---------------------------------------------------------------------------
# Agent list
# ---------------------------------------------------------------------------

_AGENT_LIST_COLUMNS = ("agent_name", "tracked_agent_id", "tool", "transport", "tmux_session_name")


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
# Helpers
# ---------------------------------------------------------------------------


def _extract_agents(payload: object) -> list[dict[str, Any]]:
    """Extract the agent list from various payload shapes."""
    if isinstance(payload, Mapping):
        agents = payload.get("agents")
        if isinstance(agents, list):
            return [a if isinstance(a, dict) else {} for a in agents]
    return []


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
