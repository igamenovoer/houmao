"""Local-only CAO-compatibility helpers for `houmao-srv-ctrl cao ...`."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

import click
import yaml

from houmao.owned_paths import resolve_runtime_root

_FLOW_STATE_DIRNAME = "cao_compat"
_FLOW_STATE_FILENAME = "flows.json"


@dataclass
class _FlowRecord:
    """Minimal persisted flow record for local compatibility helpers."""

    name: str
    schedule: str
    agent_profile: str
    file_path: str
    enabled: bool = True
    last_run: str | None = None
    next_run: str | None = None


@click.group(name="flow")
def flow_group() -> None:
    """Manage local scheduled agent flows through Houmao-owned helpers."""


@flow_group.command(
    name="list",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def flow_list_command(ctx: click.Context) -> None:
    """List locally persisted compatibility flows."""

    del ctx
    flows = _load_flows()
    if not flows:
        click.echo("No flows found")
        return

    click.echo(
        f"{'Name':<20} {'Schedule':<15} {'Agent':<20} {'Last Run':<20} {'Next Run':<20} {'Enabled':<8}"
    )
    click.echo("-" * 115)
    for flow in flows:
        click.echo(
            f"{flow.name:<20} {flow.schedule:<15} {flow.agent_profile:<20} "
            f"{(flow.last_run or 'Never'):<20} {(flow.next_run or 'N/A'):<20} "
            f"{('Yes' if flow.enabled else 'No'):<8}"
        )


@flow_group.command(name="add")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def flow_add_command(file_path: Path) -> None:
    """Add one flow from a YAML or JSON file."""

    payload = _load_flow_definition(file_path.resolve())
    name = _required_string(payload, "name", source=file_path)
    schedule = _required_string(payload, "schedule", source=file_path)
    agent_profile = _required_string(payload, "agent_profile", source=file_path)
    enabled = bool(payload.get("enabled", True))

    flows = _load_flows()
    flows = [flow for flow in flows if flow.name != name]
    flows.append(
        _FlowRecord(
            name=name,
            schedule=schedule,
            agent_profile=agent_profile,
            file_path=str(file_path.resolve()),
            enabled=enabled,
        )
    )
    _write_flows(flows)
    click.echo(f"Flow '{name}' added successfully")
    click.echo(f"  Schedule: {schedule}")
    click.echo(f"  Agent: {agent_profile}")
    click.echo("  Next run: N/A")


@flow_group.command(name="remove")
@click.argument("name")
def flow_remove_command(name: str) -> None:
    """Remove one locally persisted compatibility flow."""

    flows = _load_flows()
    remaining = [flow for flow in flows if flow.name != name]
    if len(remaining) == len(flows):
        raise click.ClickException(f"Flow '{name}' not found")
    _write_flows(remaining)
    click.echo(f"Flow '{name}' removed successfully")


@flow_group.command(name="disable")
@click.argument("name")
def flow_disable_command(name: str) -> None:
    """Disable one locally persisted compatibility flow."""

    _set_flow_enabled(name=name, enabled=False)
    click.echo(f"Flow '{name}' disabled")


@flow_group.command(name="enable")
@click.argument("name")
def flow_enable_command(name: str) -> None:
    """Enable one locally persisted compatibility flow."""

    _set_flow_enabled(name=name, enabled=True)
    click.echo(f"Flow '{name}' enabled")


@flow_group.command(name="run")
@click.argument("name")
def flow_run_command(name: str) -> None:
    """Mark one locally persisted compatibility flow as executed."""

    flows = _load_flows()
    for flow in flows:
        if flow.name != name:
            continue
        if not flow.enabled:
            click.echo(f"Flow '{name}' skipped (execute=false)")
            return
        flow.last_run = datetime.now(UTC).isoformat(timespec="seconds")
        _write_flows(flows)
        click.echo(f"Flow '{name}' executed successfully")
        return
    raise click.ClickException(f"Flow '{name}' not found")


@click.command(name="init")
def init_command() -> None:
    """Initialize the local CAO-compatibility helper state."""

    _state_root().mkdir(parents=True, exist_ok=True)
    if not _flow_state_path().exists():
        _write_flows([])
    click.echo("CLI Agent Orchestrator initialized successfully")


@click.command(name="mcp-server")
def mcp_server_command() -> None:
    """Fail explicitly for the retired standalone CAO MCP helper."""

    raise click.ClickException(
        "The standalone CAO MCP helper is not part of the supported Houmao pair. "
        "Use `houmao-server` with `houmao-srv-ctrl launch` or `agents gateway` instead."
    )


def _state_root() -> Path:
    """Return the local compatibility-helper state root."""

    return (resolve_runtime_root() / _FLOW_STATE_DIRNAME).resolve()


def _flow_state_path() -> Path:
    """Return the persisted flow-state snapshot path."""

    return (_state_root() / _FLOW_STATE_FILENAME).resolve()


def _load_flows() -> list[_FlowRecord]:
    """Read the current flow snapshot from disk."""

    path = _flow_state_path()
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_flows = payload.get("flows", [])
    if not isinstance(raw_flows, list):
        raise click.ClickException(f"Invalid local compatibility flow state at `{path}`.")
    return [_FlowRecord(**item) for item in raw_flows if isinstance(item, dict)]


def _write_flows(flows: list[_FlowRecord]) -> None:
    """Persist the current flow snapshot."""

    _state_root().mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "flows": [asdict(flow) for flow in flows]}
    _flow_state_path().write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _set_flow_enabled(*, name: str, enabled: bool) -> None:
    """Update the enabled flag for one persisted flow."""

    flows = _load_flows()
    for flow in flows:
        if flow.name == name:
            flow.enabled = enabled
            _write_flows(flows)
            return
    raise click.ClickException(f"Flow '{name}' not found")


def _load_flow_definition(path: Path) -> dict[str, object]:
    """Load one flow definition file."""

    suffix = path.suffix.lower()
    raw_text = path.read_text(encoding="utf-8")
    if suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(raw_text)
    elif suffix == ".json":
        payload = json.loads(raw_text)
    else:
        raise click.ClickException(
            f"Unsupported flow file `{path}`. Expected `.yaml`, `.yml`, or `.json`."
        )
    if not isinstance(payload, dict):
        raise click.ClickException(f"Flow file `{path}` must decode to a mapping.")
    return payload


def _required_string(payload: dict[str, object], key: str, *, source: Path) -> str:
    """Return one required non-empty string field from a flow definition."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise click.ClickException(f"Flow file `{source}` is missing required string `{key}`.")
    return value.strip()
