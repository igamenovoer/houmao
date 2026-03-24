"""Pair-owned managed-agent gateway commands for `houmao-srv-ctrl`."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import click

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    read_tmux_session_environment_value,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataHoumaoServerV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
    AGENT_GATEWAY_ROOT_ENV_VAR,
    load_attach_contract,
    require_gateway_paths_for_attach_contract,
)
from houmao.cao.rest_client import CaoApiError

from .common import require_supported_houmao_pair, resolve_server_base_url


@click.group(name="agent-gateway")
def agent_gateway_group() -> None:
    """Manage pair-owned gateway lifecycle for managed agents."""


@click.command(name="attach")
@click.option("--agent", "agent_ref", help="Managed-agent reference to attach explicitly")
@click.option(
    "--port",
    default=None,
    type=int,
    help="Houmao server port to use for explicit `--agent` attach",
)
def attach_agent_gateway_command(agent_ref: str | None, port: int | None) -> None:
    """Attach a managed-agent gateway through the Houmao pair authority."""

    if agent_ref is not None:
        status = _attach_explicit(agent_ref=agent_ref, port=port)
    else:
        if port is not None:
            raise click.ClickException(
                "`--port` is only supported with `--agent`; current-session attach uses "
                "the persisted `api_base_url` from the tmux-published attach contract."
            )
        status = _attach_current_session()
    click.echo(json.dumps(status.model_dump(mode="json"), indent=2, sort_keys=True))


def _attach_explicit(*, agent_ref: str, port: int | None) -> GatewayStatusV1:
    """Attach by resolving one explicit managed-agent reference first."""

    candidate = agent_ref.strip()
    if not candidate:
        raise click.ClickException("`--agent` must not be empty.")

    base_url = resolve_server_base_url(port=port)
    client = require_supported_houmao_pair(base_url=base_url)
    try:
        resolved = client.get_managed_agent(candidate)
        return client.attach_managed_agent_gateway(resolved.tracked_agent_id)
    except CaoApiError as exc:
        raise click.ClickException(exc.detail) from exc


def _attach_current_session() -> GatewayStatusV1:
    """Attach by resolving the current tmux session's persisted pair metadata."""

    session_name = _require_current_tmux_session_name()
    attach_path = _require_tmux_pointer(
        session_name=session_name,
        variable_name=AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
    )
    gateway_root = _require_tmux_pointer(
        session_name=session_name,
        variable_name=AGENT_GATEWAY_ROOT_ENV_VAR,
    )
    if not attach_path.is_file():
        raise click.ClickException(
            f"Current-session attach metadata is stale: `{attach_path}` does not exist."
        )
    if not gateway_root.is_dir():
        raise click.ClickException(
            f"Current-session gateway root is stale: `{gateway_root}` does not exist."
        )

    try:
        attach_contract = load_attach_contract(attach_path)
        resolved_paths = require_gateway_paths_for_attach_contract(attach_contract)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if resolved_paths.attach_path.resolve() != attach_path:
        raise click.ClickException(
            "Current-session attach metadata is stale: tmux-published attach path does not "
            "match the runtime-owned attach contract."
        )
    if resolved_paths.gateway_root.resolve() != gateway_root:
        raise click.ClickException(
            "Current-session attach metadata is stale: tmux-published gateway root does not "
            "match the runtime-owned attach contract."
        )
    if attach_contract.tmux_session_name != session_name:
        raise click.ClickException(
            "Current-session attach metadata is stale: the persisted attach contract belongs "
            f"to tmux session `{attach_contract.tmux_session_name}`, not `{session_name}`."
        )
    if attach_contract.backend != "houmao_server_rest":
        raise click.ClickException(
            "Current-session attach only supports pair-managed `houmao_server_rest` sessions."
        )

    metadata = attach_contract.backend_metadata
    if not isinstance(metadata, GatewayAttachBackendMetadataHoumaoServerV1):
        raise click.ClickException(
            "Current-session attach metadata is invalid for `houmao_server_rest`."
        )

    client = require_supported_houmao_pair(base_url=metadata.api_base_url)
    try:
        resolved = client.get_managed_agent(metadata.session_name)
    except CaoApiError as exc:
        raise click.ClickException(exc.detail) from exc

    if resolved.transport != "tui":
        raise click.ClickException(
            "Current-session attach resolved a non-TUI managed agent, which is invalid for "
            "a pair-managed tmux session."
        )
    if resolved.session_name != metadata.session_name:
        raise click.ClickException(
            "Current-session attach metadata is stale: the persisted session alias no longer "
            "resolves to the expected managed agent."
        )
    try:
        return client.attach_managed_agent_gateway(metadata.session_name)
    except CaoApiError as exc:
        raise click.ClickException(exc.detail) from exc


def _require_current_tmux_session_name() -> str:
    """Return the current tmux session name or fail clearly."""

    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True,
            check=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise click.ClickException(
            "Current-session attach must be run from inside the target tmux session."
        ) from exc
    session_name = result.stdout.strip()
    if not session_name:
        raise click.ClickException(
            "Current-session attach could not determine the current tmux session name."
        )
    return session_name


def _require_tmux_pointer(*, session_name: str, variable_name: str) -> Path:
    """Return one absolute tmux-published gateway pointer or fail explicitly."""

    try:
        value = read_tmux_session_environment_value(
            session_name=session_name,
            variable_name=variable_name,
        )
    except TmuxCommandError as exc:
        raise click.ClickException(str(exc)) from exc
    if value is None:
        raise click.ClickException(
            "Current-session attach is unavailable because the tmux session does not publish "
            f"`{variable_name}`."
        )
    path = Path(value)
    if not path.is_absolute():
        raise click.ClickException(
            f"Current-session attach metadata is invalid: `{variable_name}` must be an "
            f"absolute path, got `{value}`."
        )
    return path.resolve()


agent_gateway_group.add_command(attach_agent_gateway_command)
