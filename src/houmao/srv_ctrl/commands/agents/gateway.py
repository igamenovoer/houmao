"""Managed-agent gateway commands for `houmao-mgr agents`."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
from typing import Callable, Literal, TypeVar

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
    tmux_session_exists,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.registry_models import LiveAgentRegistryRecordV2
from houmao.agents.realm_controller.registry_storage import (
    resolve_live_agent_record_by_agent_id,
    resolve_live_agent_records_by_terminal_session_name,
)
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


def _target_tmux_session_option(function: _FunctionT) -> _FunctionT:
    """Attach the shared `--target-tmux-session` option decorator."""

    return click.option(
        "--target-tmux-session",
        default=None,
        help="Explicit local tmux session name to target from outside tmux.",
    )(function)


def _gateway_pair_port_option(
    *,
    help_text: str = "Houmao pair authority port to use for explicit managed-agent targeting",
) -> Callable[[_FunctionT], _FunctionT]:
    """Attach the gateway-family `--pair-port` option decorator."""

    return pair_port_option(help_text=help_text, option_name="--pair-port")


@gateway_group.command(name="attach")
@click.option(
    "--background",
    is_flag=True,
    help=(
        "Run the gateway as a detached background process instead of the default "
        "same-session auxiliary tmux window. Window `0` remains the agent surface "
        "when foreground mode is active."
    ),
)
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(help_text="Houmao pair authority port override for explicit attach")
@managed_agent_selector_options
def attach_gateway_command(
    background: bool,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Attach or reuse a live gateway for one managed agent, foreground by default."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="attach",
    )
    emit(attach_gateway(target, background=background))


@gateway_group.command(name="detach")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option()
@managed_agent_selector_options
def detach_gateway_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Detach the live gateway for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="detach",
    )
    emit(detach_gateway(target))


@gateway_group.command(name="status")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option()
@managed_agent_selector_options
def status_gateway_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show live gateway status, including foreground execution metadata when active."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
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
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit gateway prompt"
)
@managed_agent_selector_options
def prompt_gateway_command(
    force: bool,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    prompt: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway-mediated prompt path for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
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
@_target_tmux_session_option
@_gateway_pair_port_option()
@managed_agent_selector_options
def interrupt_gateway_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway-mediated interrupt path for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
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
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit gateway raw control input"
)
@managed_agent_selector_options
def send_keys_gateway_command(
    sequence: str,
    escape_special_keys: bool,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the explicit gateway raw control-input path for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
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
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit gateway TUI state"
)
@managed_agent_selector_options
def state_gateway_tui_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show raw gateway-owned live TUI state for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="tui state",
    )
    emit(gateway_tui_state(target))


@gateway_tui_group.command(name="history")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit gateway TUI history"
)
@managed_agent_selector_options
def history_gateway_tui_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show bounded raw gateway-owned TUI snapshot history for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
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
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit gateway TUI watch"
)
@managed_agent_selector_options
def watch_gateway_tui_command(
    interval_seconds: float,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Poll raw gateway-owned TUI state repeatedly for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
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
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit gateway TUI prompt note"
)
@managed_agent_selector_options
def note_prompt_gateway_tui_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    prompt: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Record prompt-note provenance without submitting a queued gateway request."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="tui note-prompt",
    )
    emit(gateway_tui_note_prompt(target, prompt=resolve_prompt_text(prompt=prompt)))


@gateway_group.group(name="mail-notifier")
def mail_notifier_gateway_group() -> None:
    """Gateway mail-notifier lifecycle and inspection commands."""


@mail_notifier_gateway_group.command(name="status")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit notifier status"
)
@managed_agent_selector_options
def status_gateway_mail_notifier_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show gateway mail-notifier status for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
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
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit notifier enable"
)
@managed_agent_selector_options
def enable_gateway_mail_notifier_command(
    interval_seconds: int,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Enable or reconfigure gateway mail-notifier behavior for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="mail-notifier enable",
    )
    emit(gateway_mail_notifier_enable(target, interval_seconds=interval_seconds))


@mail_notifier_gateway_group.command(name="disable")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit notifier disable"
)
@managed_agent_selector_options
def disable_gateway_mail_notifier_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Disable gateway mail-notifier behavior for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="mail-notifier disable",
    )
    emit(gateway_mail_notifier_disable(target))


@dataclass(frozen=True)
class _CurrentSessionManifestResolution:
    """Resolved manifest-backed authority for tmux-session targeting."""

    manifest_path: Path
    authority: ManifestSessionAuthority
    registry_record: LiveAgentRegistryRecordV2 | None = None


@dataclass(frozen=True)
class _TmuxSessionResolutionContext:
    """Resolution behavior and error labels for tmux-session targeting."""

    label: str
    registry_fallback_kind: Literal["agent_id", "terminal_session"]


_CURRENT_SESSION_RESOLUTION_CONTEXT = _TmuxSessionResolutionContext(
    label="Current-session attach",
    registry_fallback_kind="agent_id",
)
_TARGET_TMUX_SESSION_RESOLUTION_CONTEXT = _TmuxSessionResolutionContext(
    label="Tmux-session targeting",
    registry_fallback_kind="terminal_session",
)


def _resolve_gateway_command_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    pair_port: int | None,
    current_session: bool,
    target_tmux_session: str | None,
    operation_name: str,
) -> ManagedAgentTarget:
    """Resolve one gateway command target from explicit selectors or current-session metadata."""

    selected_agent_id, selected_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
        allow_missing=True,
    )
    selected_tmux_session = _normalize_optional_tmux_session_selector(
        option_name="--target-tmux-session",
        value=target_tmux_session,
    )
    explicit_managed_agent_target = selected_agent_id is not None or selected_agent_name is not None
    selector_count = (
        int(explicit_managed_agent_target)
        + int(selected_tmux_session is not None)
        + int(current_session)
    )
    if selector_count > 1:
        raise click.ClickException(
            "Use exactly one of `--agent-id`, `--agent-name`, `--target-tmux-session`, "
            "or `--current-session`."
        )

    if current_session:
        _raise_if_pair_port_without_explicit_selector(
            pair_port=pair_port,
            operation_name=operation_name,
        )
        return _resolve_gateway_current_session_target()

    if selected_tmux_session is not None:
        _raise_if_pair_port_without_explicit_selector(
            pair_port=pair_port,
            operation_name=operation_name,
        )
        return _resolve_gateway_target_tmux_session_target(session_name=selected_tmux_session)

    if explicit_managed_agent_target:
        return resolve_managed_agent_target(
            agent_id=selected_agent_id,
            agent_name=selected_agent_name,
            port=pair_port,
        )

    _raise_if_pair_port_without_explicit_selector(
        pair_port=pair_port,
        operation_name=operation_name,
    )

    session_name = _try_current_tmux_session_name()
    if session_name is None:
        raise click.ClickException(
            "Exactly one of `--agent-id`, `--agent-name`, or `--target-tmux-session` is "
            "required unless the command is run inside the target tmux session or "
            "`--current-session` is provided."
        )
    return _resolve_gateway_current_session_target(session_name=session_name)


def _resolve_gateway_current_session_target(
    *, session_name: str | None = None
) -> ManagedAgentTarget:
    """Resolve one managed-agent target from current-session tmux metadata."""

    resolved_session_name = session_name or _require_current_tmux_session_name()
    return _resolve_gateway_tmux_session_target(
        session_name=resolved_session_name,
        context=_CURRENT_SESSION_RESOLUTION_CONTEXT,
    )


def _resolve_gateway_target_tmux_session_target(*, session_name: str) -> ManagedAgentTarget:
    """Resolve one managed-agent target from an explicit tmux session selector."""

    try:
        session_exists = tmux_session_exists(session_name=session_name)
    except TmuxCommandError as exc:
        raise click.ClickException(str(exc)) from exc
    if not session_exists:
        raise click.ClickException(
            f"`--target-tmux-session` resolved no live local tmux session named `{session_name}`."
        )
    return _resolve_gateway_tmux_session_target(
        session_name=session_name,
        context=_TARGET_TMUX_SESSION_RESOLUTION_CONTEXT,
    )


def _resolve_gateway_tmux_session_target(
    *,
    session_name: str,
    context: _TmuxSessionResolutionContext,
) -> ManagedAgentTarget:
    """Resolve one managed-agent target from tmux-session metadata."""

    resolution = _resolve_tmux_session_manifest(
        session_name=session_name,
        context=context,
    )
    authority = resolution.authority

    try:
        if authority.backend == "houmao_server_rest":
            managed_agent_ref, identity, client = _resolve_tmux_session_pair_target(
                authority=authority,
                context=context,
            )
            return ManagedAgentTarget(
                mode="server",
                agent_ref=managed_agent_ref,
                identity=identity,
                client=client,
                record=resolution.registry_record,
            )

        agent_def_dir = _resolve_tmux_session_agent_def_dir(
            session_name=session_name,
            registry_record=resolution.registry_record,
            context=context,
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


def _resolve_tmux_session_pair_target(
    *,
    authority: ManifestSessionAuthority,
    context: _TmuxSessionResolutionContext,
) -> tuple[str, HoumaoManagedAgentIdentity, PairAuthorityClientProtocol]:
    """Resolve one pair-managed tmux session to a managed-agent ref and pair client."""

    try:
        api_base_url, managed_agent_ref = authority.attach.require_pair_target()
    except SessionManifestError as exc:
        raise click.ClickException(
            f"{context.label} metadata is invalid for `houmao_server_rest`: {exc}"
        ) from exc

    client = require_houmao_server_pair(base_url=api_base_url)
    resolved = resolve_managed_agent_identity(client, agent_ref=managed_agent_ref)
    if resolved.transport != "tui":
        raise click.ClickException(
            f"{context.label} resolved a non-TUI managed agent, which is invalid for a "
            "pair-managed tmux session."
        )
    if resolved.session_name != managed_agent_ref:
        raise click.ClickException(
            f"{context.label} metadata is stale: the persisted session alias no longer "
            "resolves to the expected managed agent."
        )
    return managed_agent_ref, resolved, client


def _resolve_tmux_session_manifest(
    *,
    session_name: str,
    context: _TmuxSessionResolutionContext,
) -> _CurrentSessionManifestResolution:
    """Resolve one tmux-session manifest from tmux env or shared-registry fallback."""

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
                context=context,
            )
            return _CurrentSessionManifestResolution(
                manifest_path=manifest_path,
                authority=_load_tmux_session_manifest_authority(
                    manifest_path=manifest_path,
                    session_name=session_name,
                    context=context,
                ),
            )
        except click.ClickException as exc:
            manifest_pointer_error = str(exc)

    registry_record = _resolve_tmux_session_registry_record(
        session_name=session_name,
        context=context,
    )
    if registry_record is not None:
        manifest_path = _require_registry_manifest_path(
            registry_record,
            context=context,
        )
        return _CurrentSessionManifestResolution(
            manifest_path=manifest_path,
            authority=_load_tmux_session_manifest_authority(
                manifest_path=manifest_path,
                session_name=session_name,
                context=context,
            ),
            registry_record=registry_record,
        )

    if manifest_pointer_error is not None:
        raise click.ClickException(
            f"{manifest_pointer_error} {_tmux_session_registry_fallback_unavailable_message(context)}"
        )
    raise click.ClickException(_tmux_session_missing_metadata_message(context=context))


def _resolve_current_session_manifest(*, session_name: str) -> _CurrentSessionManifestResolution:
    """Backward-compatible current-session manifest resolution wrapper."""

    return _resolve_tmux_session_manifest(
        session_name=session_name,
        context=_CURRENT_SESSION_RESOLUTION_CONTEXT,
    )


def _resolve_tmux_session_registry_record(
    *,
    session_name: str,
    context: _TmuxSessionResolutionContext,
) -> LiveAgentRegistryRecordV2 | None:
    """Resolve one tmux session through the shared registry."""

    if context.registry_fallback_kind == "agent_id":
        return _resolve_current_session_registry_record(session_name=session_name)
    return _resolve_target_tmux_session_registry_record(session_name=session_name)


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


def _resolve_target_tmux_session_registry_record(
    *,
    session_name: str,
) -> LiveAgentRegistryRecordV2 | None:
    """Resolve one explicit tmux-session selector through shared-registry session matching."""

    matches = resolve_live_agent_records_by_terminal_session_name(session_name)
    if len(matches) > 1:
        raise click.ClickException(
            _format_ambiguous_tmux_session_registry_matches(
                session_name=session_name,
                matches=matches,
            )
        )
    if len(matches) == 1:
        return matches[0]
    return None


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


def _load_tmux_session_manifest_authority(
    *,
    manifest_path: Path,
    session_name: str,
    context: _TmuxSessionResolutionContext,
) -> ManifestSessionAuthority:
    """Load one manifest authority and validate that it belongs to the target tmux session."""

    try:
        handle = load_session_manifest(manifest_path)
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        authority = resolve_manifest_session_authority(
            manifest_path=handle.path,
            payload=payload,
        )
    except SessionManifestError as exc:
        raise click.ClickException(f"{context.label} metadata is invalid: {exc}") from exc

    if authority.tmux_session_name != session_name:
        raise click.ClickException(
            f"{context.label} metadata is stale: the resolved manifest belongs to tmux session "
            f"`{authority.tmux_session_name}`, not `{session_name}`."
        )
    return authority


def _resolve_tmux_session_agent_def_dir(
    *,
    session_name: str,
    registry_record: LiveAgentRegistryRecordV2 | None,
    context: _TmuxSessionResolutionContext,
) -> Path:
    """Resolve local runtime authority needed to resume one tmux-targeted session."""

    env_value = _read_tmux_env_value(
        session_name=session_name,
        variable_name=AGENT_DEF_DIR_ENV_VAR,
    )
    if env_value is not None:
        return _require_directory_path(
            env_value,
            variable_name=AGENT_DEF_DIR_ENV_VAR,
            context=context,
        )

    if registry_record is not None and registry_record.runtime.agent_def_dir is not None:
        return _require_directory_path(
            registry_record.runtime.agent_def_dir,
            variable_name="runtime.agent_def_dir",
            context=context,
        )

    raise click.ClickException(
        f"{context.label} is unavailable for local tmux-backed control because neither "
        f"`{AGENT_DEF_DIR_ENV_VAR}` nor shared-registry `runtime.agent_def_dir` is available."
    )


def _resolve_current_session_agent_def_dir(
    *,
    session_name: str,
    registry_record: LiveAgentRegistryRecordV2 | None,
) -> Path:
    """Backward-compatible current-session agent-def resolution wrapper."""

    return _resolve_tmux_session_agent_def_dir(
        session_name=session_name,
        registry_record=registry_record,
        context=_CURRENT_SESSION_RESOLUTION_CONTEXT,
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


def _require_manifest_path(
    value: str,
    *,
    variable_name: str,
    context: _TmuxSessionResolutionContext,
) -> Path:
    """Validate one manifest pointer value read from tmux or shared registry."""

    path = Path(value)
    if not path.is_absolute():
        raise click.ClickException(
            f"{context.label} metadata is invalid: `{variable_name}` must be an "
            f"absolute path, got `{path}`."
        )
    resolved = path.resolve()
    if not resolved.is_file():
        raise click.ClickException(
            f"{context.label} metadata is stale: `{variable_name}` points to missing manifest "
            f"`{resolved}`."
        )
    return resolved


def _require_registry_manifest_path(
    record: LiveAgentRegistryRecordV2,
    *,
    context: _TmuxSessionResolutionContext,
) -> Path:
    """Validate the manifest path recovered from one shared-registry record."""

    return _require_manifest_path(
        record.runtime.manifest_path,
        variable_name="runtime.manifest_path",
        context=context,
    )


def _require_directory_path(
    value: str,
    *,
    variable_name: str,
    context: _TmuxSessionResolutionContext,
) -> Path:
    """Validate one directory pointer used for resumed local control."""

    path = Path(value)
    if not path.is_absolute():
        raise click.ClickException(
            f"{context.label} metadata is invalid: `{variable_name}` must be an "
            f"absolute path, got `{path}`."
        )
    resolved = path.resolve()
    if not resolved.is_dir():
        raise click.ClickException(
            f"{context.label} metadata is stale: `{variable_name}` points to missing directory "
            f"`{resolved}`."
        )
    return resolved


def _normalize_optional_tmux_session_selector(*, option_name: str, value: str | None) -> str | None:
    """Normalize one optional tmux session selector value."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise click.ClickException(f"`{option_name}` must not be empty.")
    return stripped


def _raise_if_pair_port_without_explicit_selector(
    *,
    pair_port: int | None,
    operation_name: str,
) -> None:
    """Reject `--pair-port` unless explicit managed-agent selectors are present."""

    if pair_port is None:
        return
    raise click.ClickException(
        "`--pair-port` is only supported with an explicit `--agent-id` or `--agent-name` "
        f"`{operation_name}` target."
    )


def _tmux_session_registry_fallback_unavailable_message(
    context: _TmuxSessionResolutionContext,
) -> str:
    """Return the registry fallback unavailability detail for one targeting mode."""

    if context.registry_fallback_kind == "agent_id":
        return f"Shared-registry fallback by `{AGENT_ID_ENV_VAR}` was unavailable."
    return "Shared-registry fallback by exact `terminal.session_name` was unavailable."


def _tmux_session_missing_metadata_message(*, context: _TmuxSessionResolutionContext) -> str:
    """Return the missing tmux metadata error for one targeting mode."""

    if context.registry_fallback_kind == "agent_id":
        return (
            "Current-session attach is unavailable because the tmux session does not publish "
            f"`{AGENT_MANIFEST_PATH_ENV_VAR}` or `{AGENT_ID_ENV_VAR}`."
        )
    return (
        "Tmux-session targeting is unavailable because the tmux session does not publish "
        f"`{AGENT_MANIFEST_PATH_ENV_VAR}` and no fresh shared-registry record matched "
        "`terminal.session_name`."
    )


def _format_ambiguous_tmux_session_registry_matches(
    *,
    session_name: str,
    matches: tuple[LiveAgentRegistryRecordV2, ...],
) -> str:
    """Format one ambiguity error for exact tmux-session registry lookup."""

    candidate_lines = "\n".join(
        (
            f"- agent_id={record.agent_id} "
            f"agent_name={record.agent_name} "
            f"tmux_session_name={record.terminal.session_name}"
        )
        for record in matches
    )
    return (
        "Local managed-agent resolution is ambiguous for `--target-tmux-session` "
        f"`{session_name}` (tmux session name).\nCandidates:\n{candidate_lines}\n"
        "Retry with `--agent-id <id>`."
    )
