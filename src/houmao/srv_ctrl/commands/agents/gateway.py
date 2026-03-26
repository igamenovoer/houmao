"""Managed-agent gateway commands for `houmao-mgr agents`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

import click

from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    normalize_managed_agent_id,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    read_tmux_session_environment_value,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.registry_models import LiveAgentRegistryRecordV2
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record_by_agent_id
from houmao.agents.realm_controller.runtime import resume_runtime_session
from houmao.agents.realm_controller.session_authority import (
    ManifestSessionAuthority,
    resolve_manifest_session_authority,
)

from ..common import (
    emit_json,
    managed_agent_selector_options,
    pair_port_option,
    require_houmao_server_pair,
    resolve_managed_agent_selector,
    resolve_managed_agent_identity,
    resolve_prompt_text,
)
from ..managed_agents import (
    attach_gateway,
    detach_gateway,
    gateway_interrupt,
    gateway_prompt,
    gateway_status,
    resolve_managed_agent_target,
)


@click.group(name="gateway")
def gateway_group() -> None:
    """Gateway lifecycle and explicit live-gateway request commands for managed agents."""


@gateway_group.command(name="attach")
@click.option(
    "--foreground",
    is_flag=True,
    help=(
        "Run the gateway in an auxiliary tmux window inside the managed session. "
        "Window `0` remains the agent surface; inspect status for the authoritative "
        "non-zero gateway window index."
    ),
)
@pair_port_option(help_text="Houmao server port override for explicit attach")
@managed_agent_selector_options
def attach_gateway_command(
    foreground: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Attach or reuse a live gateway for one managed agent, including serverless local TUIs."""

    selected_agent_id, selected_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
        allow_missing=True,
    )
    if selected_agent_id is None and selected_agent_name is None:
        if port is not None:
            raise click.ClickException(
                "`--port` is only supported with an explicit `--agent-id` or `--agent-name` attach target."
            )
        emit_json(_attach_current_session(foreground=foreground))
        return

    target = resolve_managed_agent_target(
        agent_id=selected_agent_id,
        agent_name=selected_agent_name,
        port=port,
    )
    emit_json(attach_gateway(target, foreground=foreground))


@gateway_group.command(name="detach")
@pair_port_option()
@managed_agent_selector_options
def detach_gateway_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Detach the live gateway for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(detach_gateway(target))


@gateway_group.command(name="status")
@pair_port_option()
@managed_agent_selector_options
def status_gateway_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show live gateway status, including foreground execution-mode metadata when present."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(gateway_status(target))


@gateway_group.command(name="prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@pair_port_option(help_text="Houmao server port override for explicit gateway prompt")
@managed_agent_selector_options
def prompt_gateway_command(
    port: int | None,
    prompt: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway-mediated prompt path for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(gateway_prompt(target, prompt=resolve_prompt_text(prompt=prompt)))


@gateway_group.command(name="interrupt")
@pair_port_option()
@managed_agent_selector_options
def interrupt_gateway_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway-mediated interrupt path for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(gateway_interrupt(target))


@dataclass(frozen=True)
class _CurrentSessionManifestResolution:
    """Resolved manifest-backed authority for current-session attach."""

    manifest_path: Path
    authority: ManifestSessionAuthority
    registry_record: LiveAgentRegistryRecordV2 | None = None


def _attach_current_session(*, foreground: bool) -> GatewayStatusV1:
    """Attach by resolving the current tmux session's manifest-backed authority."""

    session_name = _require_current_tmux_session_name()
    resolution = _resolve_current_session_manifest(session_name=session_name)
    authority = resolution.authority

    try:
        if authority.backend == "houmao_server_rest":
            return _attach_current_pair_session(authority=authority)

        agent_def_dir = _resolve_current_session_agent_def_dir(
            session_name=session_name,
            registry_record=resolution.registry_record,
        )
        controller = resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=resolution.manifest_path,
        )
        result = controller.attach_gateway(
            execution_mode_override="tmux_auxiliary_window" if foreground else None
        )
        if result.status != "ok":
            raise click.ClickException(result.detail)
        return controller.gateway_status()
    except (OSError, RuntimeError, SessionManifestError) as exc:
        raise click.ClickException(str(exc)) from exc


def _attach_current_pair_session(*, authority: ManifestSessionAuthority) -> GatewayStatusV1:
    """Attach one pair-managed current session using manifest-declared authority."""

    try:
        api_base_url, managed_agent_ref = authority.attach.require_pair_target()
    except SessionManifestError as exc:
        raise click.ClickException(
            f"Current-session attach metadata is invalid for `houmao_server_rest`: {exc}"
        ) from exc

    client = require_houmao_server_pair(base_url=api_base_url)
    resolved = resolve_managed_agent_identity(client, agent_ref=managed_agent_ref)
    if resolved.transport != "tui":
        raise click.ClickException(
            "Current-session attach resolved a non-TUI managed agent, which is invalid for "
            "a pair-managed tmux session."
        )
    if resolved.session_name != managed_agent_ref:
        raise click.ClickException(
            "Current-session attach metadata is stale: the persisted session alias no longer "
            "resolves to the expected managed agent."
        )
    return client.attach_managed_agent_gateway(managed_agent_ref)


def _resolve_current_session_manifest(*, session_name: str) -> _CurrentSessionManifestResolution:
    """Resolve the current session manifest from tmux env or shared-registry fallback."""

    manifest_pointer_error: str | None = None
    manifest_path_value = _read_tmux_env_value(
        session_name=session_name,
        variable_name=AGENT_MANIFEST_PATH_ENV_VAR,
    )
    if manifest_path_value is not None:
        try:
            manifest_path = _require_manifest_path(
                manifest_path_value,
                variable_name=AGENT_MANIFEST_PATH_ENV_VAR,
            )
            return _CurrentSessionManifestResolution(
                manifest_path=manifest_path,
                authority=_load_current_session_manifest_authority(
                    manifest_path=manifest_path,
                    session_name=session_name,
                ),
            )
        except click.ClickException as exc:
            manifest_pointer_error = str(exc)

    registry_record = _resolve_current_session_registry_record(session_name=session_name)
    if registry_record is not None:
        manifest_path = _require_registry_manifest_path(registry_record)
        return _CurrentSessionManifestResolution(
            manifest_path=manifest_path,
            authority=_load_current_session_manifest_authority(
                manifest_path=manifest_path,
                session_name=session_name,
            ),
            registry_record=registry_record,
        )

    if manifest_pointer_error is not None:
        raise click.ClickException(
            f"{manifest_pointer_error} Shared-registry fallback by `{AGENT_ID_ENV_VAR}` was unavailable."
        )
    raise click.ClickException(
        "Current-session attach is unavailable because the tmux session does not publish "
        f"`{AGENT_MANIFEST_PATH_ENV_VAR}` or `{AGENT_ID_ENV_VAR}`."
    )


def _resolve_current_session_registry_record(
    *,
    session_name: str,
) -> LiveAgentRegistryRecordV2 | None:
    """Resolve the current session through shared registry using tmux-published agent id."""

    agent_id = _read_current_session_agent_id(session_name=session_name)
    if agent_id is None:
        return None
    record = resolve_live_agent_record_by_agent_id(agent_id)
    if record is None:
        raise click.ClickException(
            "Current-session attach metadata is stale: "
            f"`{AGENT_ID_ENV_VAR}` resolved no fresh shared-registry record."
        )
    return record


def _read_current_session_agent_id(*, session_name: str) -> str | None:
    """Return the optional authoritative current-session agent id."""

    agent_id = _read_tmux_env_value(
        session_name=session_name,
        variable_name=AGENT_ID_ENV_VAR,
    )
    if agent_id is None:
        return None
    try:
        return normalize_managed_agent_id(agent_id)
    except SessionManifestError as exc:
        raise click.ClickException(
            "Current-session attach metadata is invalid: "
            f"`{AGENT_ID_ENV_VAR}` is not a valid authoritative agent id."
        ) from exc


def _load_current_session_manifest_authority(
    *, manifest_path: Path, session_name: str
) -> ManifestSessionAuthority:
    """Load one manifest authority and validate that it belongs to the current tmux session."""

    try:
        handle = load_session_manifest(manifest_path)
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        authority = resolve_manifest_session_authority(
            manifest_path=handle.path,
            payload=payload,
        )
    except SessionManifestError as exc:
        raise click.ClickException(f"Current-session attach metadata is invalid: {exc}") from exc

    if authority.tmux_session_name != session_name:
        raise click.ClickException(
            "Current-session attach metadata is stale: the resolved manifest belongs to tmux "
            f"session `{authority.tmux_session_name}`, not `{session_name}`."
        )
    return authority


def _resolve_current_session_agent_def_dir(
    *,
    session_name: str,
    registry_record: LiveAgentRegistryRecordV2 | None,
) -> Path:
    """Resolve local runtime authority needed to resume the current session."""

    env_value = _read_tmux_env_value(
        session_name=session_name,
        variable_name=AGENT_DEF_DIR_ENV_VAR,
    )
    if env_value is not None:
        return _require_directory_path(env_value, variable_name=AGENT_DEF_DIR_ENV_VAR)

    if registry_record is not None and registry_record.runtime.agent_def_dir is not None:
        return _require_directory_path(
            registry_record.runtime.agent_def_dir,
            variable_name="runtime.agent_def_dir",
        )

    raise click.ClickException(
        "Current-session attach is unavailable for local tmux-backed control because neither "
        f"`{AGENT_DEF_DIR_ENV_VAR}` nor shared-registry `runtime.agent_def_dir` is available."
    )


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


def _read_tmux_env_value(*, session_name: str, variable_name: str) -> str | None:
    """Return one optional tmux session env value or fail on tmux errors."""

    try:
        return read_tmux_session_environment_value(
            session_name=session_name,
            variable_name=variable_name,
        )
    except TmuxCommandError as exc:
        raise click.ClickException(str(exc)) from exc


def _require_manifest_path(value: str, *, variable_name: str) -> Path:
    """Validate one manifest pointer value read from tmux or shared registry."""

    path = Path(value)
    if not path.is_absolute():
        raise click.ClickException(
            f"Current-session attach metadata is invalid: `{variable_name}` must be an "
            f"absolute path, got `{path}`."
        )
    resolved = path.resolve()
    if not resolved.is_file():
        raise click.ClickException(
            f"Current-session attach metadata is stale: `{variable_name}` points to missing "
            f"manifest `{resolved}`."
        )
    return resolved


def _require_registry_manifest_path(record: LiveAgentRegistryRecordV2) -> Path:
    """Validate the manifest path recovered from one shared-registry record."""

    return _require_manifest_path(
        record.runtime.manifest_path,
        variable_name="runtime.manifest_path",
    )


def _require_directory_path(value: str, *, variable_name: str) -> Path:
    """Validate one directory pointer used for resumed local control."""

    path = Path(value)
    if not path.is_absolute():
        raise click.ClickException(
            f"Current-session attach metadata is invalid: `{variable_name}` must be an "
            f"absolute path, got `{path}`."
        )
    resolved = path.resolve()
    if not resolved.is_dir():
        raise click.ClickException(
            f"Current-session attach metadata is stale: `{variable_name}` points to missing "
            f"directory `{resolved}`."
        )
    return resolved
