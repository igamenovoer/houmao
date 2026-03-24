"""Managed-agent gateway commands for `houmao-srv-ctrl agents`."""

from __future__ import annotations

from pathlib import Path
import subprocess

import click

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    read_tmux_session_environment_value,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataHoumaoServerV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
    AGENT_GATEWAY_ROOT_ENV_VAR,
    load_attach_contract,
    require_gateway_paths_for_attach_contract,
)
from houmao.server.models import HoumaoManagedAgentGatewayRequestCreate

from ..common import (
    emit_json,
    pair_port_option,
    pair_request,
    require_supported_houmao_pair,
    resolve_managed_agent_identity,
    resolve_pair_client,
    resolve_prompt_text,
)


@click.group(name="gateway")
def gateway_group() -> None:
    """Server-backed gateway lifecycle plus explicit live-gateway request commands."""


@gateway_group.command(name="attach")
@click.argument("agent_ref", required=False)
@pair_port_option(help_text="Houmao server port to use for explicit attach")
def attach_gateway_command(agent_ref: str | None, port: int | None) -> None:
    """Attach or reuse a live gateway for one managed agent."""

    if agent_ref is None:
        if port is not None:
            raise click.ClickException(
                "`--port` is only supported with an explicit `<agent-ref>` attach target."
            )
        emit_json(_attach_current_session())
        return

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(pair_request(client.attach_managed_agent_gateway, resolved.tracked_agent_id))


@gateway_group.command(name="detach")
@pair_port_option()
@click.argument("agent_ref")
def detach_gateway_command(port: int | None, agent_ref: str) -> None:
    """Detach the live gateway for one managed agent through `houmao-server`."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(pair_request(client.detach_managed_agent_gateway, resolved.tracked_agent_id))


@gateway_group.command(name="status")
@pair_port_option()
@click.argument("agent_ref")
def status_gateway_command(port: int | None, agent_ref: str) -> None:
    """Show live gateway status for one managed agent."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(pair_request(client.get_managed_agent_gateway_status, resolved.tracked_agent_id))


@gateway_group.command(name="prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@pair_port_option(help_text="Houmao server port to use for the explicit gateway prompt path")
@click.argument("agent_ref")
def prompt_gateway_command(port: int | None, prompt: str | None, agent_ref: str) -> None:
    """Submit the explicit gateway-mediated prompt path for one managed agent."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(
        pair_request(
            client.submit_managed_agent_gateway_request,
            resolved.tracked_agent_id,
            HoumaoManagedAgentGatewayRequestCreate(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(
                    prompt=resolve_prompt_text(prompt=prompt)
                ),
            ),
        )
    )


@gateway_group.command(name="interrupt")
@pair_port_option()
@click.argument("agent_ref")
def interrupt_gateway_command(port: int | None, agent_ref: str) -> None:
    """Submit the explicit gateway-mediated interrupt path for one managed agent."""

    client = resolve_pair_client(port=port)
    resolved = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    emit_json(
        pair_request(
            client.submit_managed_agent_gateway_request,
            resolved.tracked_agent_id,
            HoumaoManagedAgentGatewayRequestCreate(
                kind="interrupt",
                payload=GatewayRequestPayloadInterruptV1(),
            ),
        )
    )


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
    resolved = resolve_managed_agent_identity(client, agent_ref=metadata.session_name)
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
    return pair_request(client.attach_managed_agent_gateway, metadata.session_name)


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
