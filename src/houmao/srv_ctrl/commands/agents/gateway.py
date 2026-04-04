"""Managed-agent gateway commands for `houmao-mgr agents`."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
from typing import Callable, TypeVar

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
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.server.pair_client import PairAuthorityClientProtocol

from ..common import (
    managed_agent_selector_options,
    pair_port_option,
    require_houmao_server_pair,
    resolve_managed_agent_selector,
    resolve_managed_agent_identity,
    resolve_prompt_text,
)
from ..output import emit
from ..renderers.gateway import (
    render_gateway_status_fancy,
    render_gateway_status_plain,
    render_prompt_result_fancy,
    render_prompt_result_plain,
)
from ..managed_agents import (
    GatewayPromptControlCliError,
    ManagedAgentTarget,
    _identity_from_controller,
    attach_gateway,
    detach_gateway,
    gateway_mail_notifier_disable,
    gateway_mail_notifier_enable,
    gateway_mail_notifier_status,
    gateway_interrupt,
    gateway_prompt,
    gateway_send_keys,
    gateway_status,
    gateway_tui_history,
    gateway_tui_note_prompt,
    gateway_tui_state,
    resolve_managed_agent_target,
)


_FunctionT = TypeVar("_FunctionT", bound=Callable[..., object])


@click.group(name="gateway")
def gateway_group() -> None:
    """Gateway lifecycle and explicit live-gateway request commands for managed agents."""


def _current_session_option(function: _FunctionT) -> _FunctionT:
    """Attach the shared `--current-session` option decorator."""

    return click.option(
        "--current-session",
        is_flag=True,
        help=(
            "Resolve the target from the current tmux session's managed-agent metadata. "
            "Implied when no selector is provided inside tmux."
        ),
    )(function)


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
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit attach")
@managed_agent_selector_options
def attach_gateway_command(
    foreground: bool,
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Attach or reuse a live gateway for one managed agent, including serverless local TUIs."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="attach",
    )
    emit(attach_gateway(target, foreground=foreground))


@gateway_group.command(name="detach")
@_current_session_option
@pair_port_option()
@managed_agent_selector_options
def detach_gateway_command(
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Detach the live gateway for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="detach",
    )
    emit(detach_gateway(target))


@gateway_group.command(name="status")
@_current_session_option
@pair_port_option()
@managed_agent_selector_options
def status_gateway_command(
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show live gateway status, including foreground execution-mode metadata when present."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="status",
    )
    emit(
        gateway_status(target),
        plain_renderer=render_gateway_status_plain,
        fancy_renderer=render_gateway_status_fancy,
    )


@gateway_group.command(name="prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Send the prompt even when the gateway does not judge the target prompt-ready.",
)
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit gateway prompt")
@managed_agent_selector_options
def prompt_gateway_command(
    force: bool,
    current_session: bool,
    port: int | None,
    prompt: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway-mediated prompt path for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="prompt",
    )
    try:
        emit(
            gateway_prompt(target, prompt=resolve_prompt_text(prompt=prompt), force=force),
            plain_renderer=render_prompt_result_plain,
            fancy_renderer=render_prompt_result_fancy,
        )
    except GatewayPromptControlCliError as exc:
        click.echo(
            json.dumps(exc.payload.model_dump(mode="json"), indent=2, sort_keys=True), err=True
        )
        raise SystemExit(1)


@gateway_group.command(name="interrupt")
@_current_session_option
@pair_port_option()
@managed_agent_selector_options
def interrupt_gateway_command(
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway-mediated interrupt path for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="interrupt",
    )
    emit(gateway_interrupt(target))


@gateway_group.command(name="send-keys")
@click.option(
    "--sequence",
    required=True,
    help="Raw control-input sequence to deliver through the live gateway.",
)
@click.option(
    "--escape-special-keys",
    is_flag=True,
    help="Treat the entire sequence literally instead of parsing `<[key-name]>` tokens.",
)
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit gateway raw control input")
@managed_agent_selector_options
def send_keys_gateway_command(
    sequence: str,
    escape_special_keys: bool,
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway raw control-input path for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="send-keys",
    )
    emit(
        gateway_send_keys(
            target,
            sequence=sequence,
            escape_special_keys=escape_special_keys,
        )
    )


@gateway_group.group(name="tui")
def gateway_tui_group() -> None:
    """Raw gateway-owned TUI tracking commands."""


@gateway_tui_group.command(name="state")
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit gateway TUI state")
@managed_agent_selector_options
def state_gateway_tui_command(
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show raw gateway-owned live TUI state for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="tui state",
    )
    emit(gateway_tui_state(target))


@gateway_tui_group.command(name="history")
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit gateway TUI history")
@managed_agent_selector_options
def history_gateway_tui_command(
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show bounded raw gateway-owned TUI snapshot history for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="tui history",
    )
    emit(gateway_tui_history(target))


@gateway_tui_group.command(name="watch")
@click.option(
    "--interval-seconds",
    default=1.0,
    type=click.FloatRange(min=0.0, min_open=True),
    show_default=True,
    help="Polling interval for repeated raw gateway TUI state inspection.",
)
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit gateway TUI watch")
@managed_agent_selector_options
def watch_gateway_tui_command(
    interval_seconds: float,
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Poll raw gateway-owned TUI state repeatedly for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="tui watch",
    )
    stdout = click.get_text_stream("stdout")
    try:
        while True:
            state = gateway_tui_state(target)
            if stdout.isatty():
                click.clear()
                emit(state)
            else:
                click.echo(json.dumps(state.model_dump(mode="json"), sort_keys=True))
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        return


@gateway_tui_group.command(name="note-prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to record in the gateway-owned tracker. If omitted, piped stdin is used.",
)
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit gateway TUI prompt note")
@managed_agent_selector_options
def note_prompt_gateway_tui_command(
    current_session: bool,
    port: int | None,
    prompt: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Record prompt-note provenance without submitting a queued gateway request."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="tui note-prompt",
    )
    emit(gateway_tui_note_prompt(target, prompt=resolve_prompt_text(prompt=prompt)))


@gateway_group.group(name="mail-notifier")
def mail_notifier_gateway_group() -> None:
    """Gateway mail-notifier lifecycle and inspection commands."""


@mail_notifier_gateway_group.command(name="status")
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit notifier status")
@managed_agent_selector_options
def status_gateway_mail_notifier_command(
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show gateway mail-notifier status for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="mail-notifier status",
    )
    emit(gateway_mail_notifier_status(target))


@mail_notifier_gateway_group.command(name="enable")
@click.option(
    "--interval-seconds",
    required=True,
    type=click.IntRange(min=1),
    help="Unread-mail polling interval in seconds.",
)
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit notifier enable")
@managed_agent_selector_options
def enable_gateway_mail_notifier_command(
    interval_seconds: int,
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Enable or reconfigure gateway mail-notifier behavior for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="mail-notifier enable",
    )
    emit(gateway_mail_notifier_enable(target, interval_seconds=interval_seconds))


@mail_notifier_gateway_group.command(name="disable")
@_current_session_option
@pair_port_option(help_text="Houmao server port override for explicit notifier disable")
@managed_agent_selector_options
def disable_gateway_mail_notifier_command(
    current_session: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Disable gateway mail-notifier behavior for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        current_session=current_session,
        operation_name="mail-notifier disable",
    )
    emit(gateway_mail_notifier_disable(target))


@dataclass(frozen=True)
class _CurrentSessionManifestResolution:
    """Resolved manifest-backed authority for current-session attach."""

    manifest_path: Path
    authority: ManifestSessionAuthority
    registry_record: LiveAgentRegistryRecordV2 | None = None


def _resolve_gateway_command_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    port: int | None,
    current_session: bool,
    operation_name: str,
) -> ManagedAgentTarget:
    """Resolve one gateway command target from explicit selectors or current-session metadata."""

    selected_agent_id, selected_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
        allow_missing=True,
    )
    if current_session:
        if selected_agent_id is not None or selected_agent_name is not None:
            raise click.ClickException(
                "`--current-session` cannot be combined with `--agent-id` or `--agent-name`."
            )
        if port is not None:
            raise click.ClickException(
                "`--port` is only supported with an explicit `--agent-id` or `--agent-name` "
                f"`{operation_name}` target."
            )
        return _resolve_gateway_current_session_target()

    if selected_agent_id is not None or selected_agent_name is not None:
        return resolve_managed_agent_target(
            agent_id=selected_agent_id,
            agent_name=selected_agent_name,
            port=port,
        )

    if port is not None:
        raise click.ClickException(
            "`--port` is only supported with an explicit `--agent-id` or `--agent-name` "
            f"`{operation_name}` target."
        )

    session_name = _try_current_tmux_session_name()
    if session_name is None:
        raise click.ClickException(
            "Exactly one of `--agent-id` or `--agent-name` is required unless the command is "
            "run inside the target tmux session or `--current-session` is provided."
        )
    return _resolve_gateway_current_session_target(session_name=session_name)


def _resolve_gateway_current_session_target(
    *, session_name: str | None = None
) -> ManagedAgentTarget:
    """Resolve one managed-agent target from current-session tmux metadata."""

    resolved_session_name = session_name or _require_current_tmux_session_name()
    resolution = _resolve_current_session_manifest(session_name=resolved_session_name)
    authority = resolution.authority

    try:
        if authority.backend == "houmao_server_rest":
            managed_agent_ref, identity, client = _resolve_current_session_pair_target(
                authority=authority
            )
            return ManagedAgentTarget(
                mode="server",
                agent_ref=managed_agent_ref,
                identity=identity,
                client=client,
                record=resolution.registry_record,
            )

        agent_def_dir = _resolve_current_session_agent_def_dir(
            session_name=resolved_session_name,
            registry_record=resolution.registry_record,
        )
        controller = resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=resolution.manifest_path,
        )
        return ManagedAgentTarget(
            mode="local",
            agent_ref=controller.agent_id
            or controller.agent_identity
            or controller.manifest_path.parent.name,
            identity=_identity_from_controller(controller),
            controller=controller,
            record=resolution.registry_record,
        )
    except (OSError, RuntimeError, SessionManifestError) as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_current_session_pair_target(
    *,
    authority: ManifestSessionAuthority,
) -> tuple[str, HoumaoManagedAgentIdentity, PairAuthorityClientProtocol]:
    """Resolve one pair-managed current session to a managed-agent ref and pair client."""

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
    return managed_agent_ref, resolved, client


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


def _try_current_tmux_session_name() -> str | None:
    """Return the current tmux session name, or `None` when not in tmux."""

    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True,
            check=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    session_name = result.stdout.strip()
    return session_name or None


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
