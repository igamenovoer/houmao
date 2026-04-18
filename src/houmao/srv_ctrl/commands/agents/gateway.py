"""Managed-agent gateway commands for `houmao-mgr agents`."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, Literal, TypeVar

import click
from pydantic import ValidationError

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
from houmao.agents.realm_controller.gateway_models import (
    GatewayMailNotifierMode,
    GatewayReminderCreateBatchV1,
    GatewayReminderDefinitionV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
    GatewayTuiTrackingTimingOverridesV1,
)
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
    render_reminder_detail_fancy,
    render_reminder_detail_plain,
    render_reminder_list_fancy,
    render_reminder_list_plain,
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
    gateway_create_reminders,
    gateway_delete_reminder,
    gateway_get_reminder,
    gateway_list_reminders,
    gateway_mail_notifier_disable,
    gateway_mail_notifier_enable,
    gateway_mail_notifier_status,
    gateway_interrupt,
    gateway_put_reminder,
    gateway_prompt,
    gateway_send_keys,
    gateway_status,
    gateway_tui_history,
    gateway_tui_note_prompt,
    gateway_tui_state,
    resolve_managed_agent_target,
)


_FunctionT = TypeVar("_FunctionT", bound=Callable[..., object])
_ReminderModelT = TypeVar(
    "_ReminderModelT",
    GatewayReminderDefinitionV1,
    GatewayReminderPutV1,
)


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


def _gateway_tui_tracking_timing_options(function: _FunctionT) -> _FunctionT:
    """Attach gateway TUI tracking timing override options."""

    for option_name, help_text in reversed(
        (
            (
                "--gateway-tui-watch-poll-interval-seconds",
                "Override gateway-owned TUI watch poll interval seconds for this attach.",
            ),
            (
                "--gateway-tui-stability-threshold-seconds",
                "Override gateway-owned TUI stability threshold seconds for this attach.",
            ),
            (
                "--gateway-tui-completion-stability-seconds",
                "Override gateway-owned TUI completion stability seconds for this attach.",
            ),
            (
                "--gateway-tui-unknown-to-stalled-timeout-seconds",
                "Override gateway-owned TUI unknown-to-stalled timeout seconds for this attach.",
            ),
            (
                "--gateway-tui-stale-active-recovery-seconds",
                "Override gateway-owned TUI stale-active recovery seconds for this attach.",
            ),
            (
                "--gateway-tui-final-stable-active-recovery-seconds",
                "Override gateway-owned TUI final stable-active recovery seconds for this attach.",
            ),
        )
    ):
        function = click.option(
            option_name,
            type=click.FloatRange(min=0.0, min_open=True),
            default=None,
            help=help_text,
        )(function)
    return function


def _gateway_tui_tracking_timing_overrides_or_none(
    *,
    gateway_tui_watch_poll_interval_seconds: float | None,
    gateway_tui_stability_threshold_seconds: float | None,
    gateway_tui_completion_stability_seconds: float | None,
    gateway_tui_unknown_to_stalled_timeout_seconds: float | None,
    gateway_tui_stale_active_recovery_seconds: float | None,
    gateway_tui_final_stable_active_recovery_seconds: float | None,
) -> GatewayTuiTrackingTimingOverridesV1 | None:
    """Build gateway TUI timing overrides only when at least one option is present."""

    overrides = GatewayTuiTrackingTimingOverridesV1(
        watch_poll_interval_seconds=gateway_tui_watch_poll_interval_seconds,
        stability_threshold_seconds=gateway_tui_stability_threshold_seconds,
        completion_stability_seconds=gateway_tui_completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=gateway_tui_unknown_to_stalled_timeout_seconds,
        stale_active_recovery_seconds=gateway_tui_stale_active_recovery_seconds,
        final_stable_active_recovery_seconds=gateway_tui_final_stable_active_recovery_seconds,
    )
    return overrides if overrides.has_values() else None


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
@_gateway_tui_tracking_timing_options
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(help_text="Houmao pair authority port override for explicit attach")
@managed_agent_selector_options
def attach_gateway_command(
    background: bool,
    gateway_tui_watch_poll_interval_seconds: float | None,
    gateway_tui_stability_threshold_seconds: float | None,
    gateway_tui_completion_stability_seconds: float | None,
    gateway_tui_unknown_to_stalled_timeout_seconds: float | None,
    gateway_tui_stale_active_recovery_seconds: float | None,
    gateway_tui_final_stable_active_recovery_seconds: float | None,
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
    emit(
        attach_gateway(
            target,
            background=background,
            tui_tracking_timing_overrides=_gateway_tui_tracking_timing_overrides_or_none(
                gateway_tui_watch_poll_interval_seconds=(gateway_tui_watch_poll_interval_seconds),
                gateway_tui_stability_threshold_seconds=gateway_tui_stability_threshold_seconds,
                gateway_tui_completion_stability_seconds=(gateway_tui_completion_stability_seconds),
                gateway_tui_unknown_to_stalled_timeout_seconds=(
                    gateway_tui_unknown_to_stalled_timeout_seconds
                ),
                gateway_tui_stale_active_recovery_seconds=(
                    gateway_tui_stale_active_recovery_seconds
                ),
                gateway_tui_final_stable_active_recovery_seconds=(
                    gateway_tui_final_stable_active_recovery_seconds
                ),
            ),
        )
    )


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
@click.option(
    "--model",
    default=None,
    help="Request-scoped headless execution model override.",
)
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Request-scoped headless tool/model-specific reasoning preset index override (>=0).",
)
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit gateway prompt"
)
@managed_agent_selector_options
def prompt_gateway_command(
    force: bool,
    model: str | None,
    reasoning_level: int | None,
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
            gateway_prompt(
                target,
                prompt=resolve_prompt_text(prompt=prompt),
                force=force,
                model=model,
                reasoning_level=reasoning_level,
            ),
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
    help="Mailbox polling interval in seconds.",
)
@click.option(
    "--mode",
    "notifier_mode",
    default="any_inbox",
    show_default=True,
    type=click.Choice(["any_inbox", "unread_only"]),
    help="Mailbox notification mode.",
)
@click.option(
    "--appendix-text",
    default=None,
    help="Runtime guidance appended to each generated mail-notifier prompt. Use an empty value to clear it.",
)
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(
    help_text="Houmao pair authority port override for explicit notifier enable"
)
@managed_agent_selector_options
def enable_gateway_mail_notifier_command(
    interval_seconds: int,
    notifier_mode: GatewayMailNotifierMode,
    appendix_text: str | None,
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
    emit(
        gateway_mail_notifier_enable(
            target,
            interval_seconds=interval_seconds,
            mode=notifier_mode,
            appendix_text=appendix_text,
        )
    )


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


@gateway_group.group(name="reminders")
def reminders_gateway_group() -> None:
    """Gateway reminder lifecycle and inspection commands."""


@reminders_gateway_group.command(name="list")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(help_text="Houmao pair authority port override for reminder listing")
@managed_agent_selector_options
def list_gateway_reminders_command(
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show the live gateway reminder set for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="reminders list",
    )
    emit(
        gateway_list_reminders(target),
        plain_renderer=render_reminder_list_plain,
        fancy_renderer=render_reminder_list_fancy,
    )


@reminders_gateway_group.command(name="get")
@click.option("--reminder-id", required=True, help="Reminder id to inspect.")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(help_text="Houmao pair authority port override for reminder lookup")
@managed_agent_selector_options
def get_gateway_reminder_command(
    reminder_id: str,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show one live gateway reminder for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="reminders get",
    )
    reminder = gateway_get_reminder(target, reminder_id=reminder_id)
    effective_reminder_id = gateway_list_reminders(target).effective_reminder_id
    _emit_reminder_detail(reminder, effective_reminder_id=effective_reminder_id)


@reminders_gateway_group.command(name="create")
@click.option("--title", required=True, help="Reminder title used for inspection and reporting.")
@click.option(
    "--mode",
    required=True,
    type=click.Choice(("one_off", "repeat"), case_sensitive=False),
    help="Reminder mode.",
)
@click.option("--prompt", default=None, help="Prompt text to submit when the reminder fires.")
@click.option("--sequence", default=None, help="Raw send-keys sequence for reminder delivery.")
@click.option(
    "--ensure-enter/--no-ensure-enter",
    default=True,
    show_default=True,
    help="For send-keys reminders, ensure one trailing Enter unless explicitly disabled.",
)
@click.option(
    "--ranking",
    default=None,
    type=int,
    help="Explicit numeric ranking. Lower numbers win.",
)
@click.option(
    "--before-all",
    is_flag=True,
    help="Compute ranking as one less than the smallest current reminder ranking.",
)
@click.option(
    "--after-all",
    is_flag=True,
    help="Compute ranking as one more than the largest current reminder ranking.",
)
@click.option(
    "--paused/--no-paused",
    default=False,
    show_default=True,
    help="Create the reminder paused or active.",
)
@click.option(
    "--start-after-seconds",
    default=None,
    type=click.FloatRange(min=0.0, min_open=True),
    help="Relative delivery delay in seconds.",
)
@click.option(
    "--deliver-at-utc",
    default=None,
    help="Absolute UTC delivery timestamp.",
)
@click.option(
    "--interval-seconds",
    default=None,
    type=click.FloatRange(min=0.0, min_open=True),
    help="Repeat cadence in seconds. Required for repeat reminders.",
)
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(help_text="Houmao pair authority port override for reminder creation")
@managed_agent_selector_options
def create_gateway_reminder_command(
    title: str,
    mode: str,
    prompt: str | None,
    sequence: str | None,
    ensure_enter: bool,
    ranking: int | None,
    before_all: bool,
    after_all: bool,
    paused: bool,
    start_after_seconds: float | None,
    deliver_at_utc: str | None,
    interval_seconds: float | None,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Create one live gateway reminder for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="reminders create",
    )
    live_reminders = gateway_list_reminders(target)
    ranking_value = _resolve_reminder_ranking_value(
        live_reminders,
        ranking=ranking,
        before_all=before_all,
        after_all=after_all,
        require_choice=True,
    )
    assert ranking_value is not None
    definition = _build_create_reminder_definition(
        title=title,
        mode=mode,
        prompt=prompt,
        sequence=sequence,
        ensure_enter=ensure_enter,
        ranking=ranking_value,
        paused=paused,
        start_after_seconds=start_after_seconds,
        deliver_at_utc=deliver_at_utc,
        interval_seconds=interval_seconds,
    )
    emit(
        gateway_create_reminders(
            target,
            payload=GatewayReminderCreateBatchV1(reminders=[definition]),
        ),
        plain_renderer=render_reminder_list_plain,
        fancy_renderer=render_reminder_list_fancy,
    )


@reminders_gateway_group.command(name="set")
@click.option("--reminder-id", required=True, help="Reminder id to update.")
@click.option("--title", default=None, help="Replacement reminder title.")
@click.option(
    "--mode",
    default=None,
    type=click.Choice(("one_off", "repeat"), case_sensitive=False),
    help="Replacement reminder mode.",
)
@click.option("--prompt", default=None, help="Replacement prompt text.")
@click.option("--sequence", default=None, help="Replacement send-keys sequence.")
@click.option(
    "--ensure-enter/--no-ensure-enter",
    default=None,
    help="For send-keys reminders, override the trailing Enter behavior.",
)
@click.option(
    "--ranking",
    default=None,
    type=int,
    help="Replacement numeric ranking. Lower numbers win.",
)
@click.option(
    "--before-all",
    is_flag=True,
    help="Recompute ranking as one less than the smallest competing reminder ranking.",
)
@click.option(
    "--after-all",
    is_flag=True,
    help="Recompute ranking as one more than the largest competing reminder ranking.",
)
@click.option(
    "--paused/--no-paused",
    default=None,
    help="Override the paused state without restating the full reminder.",
)
@click.option(
    "--start-after-seconds",
    default=None,
    type=click.FloatRange(min=0.0, min_open=True),
    help="Reset next delivery to a relative delay in seconds.",
)
@click.option(
    "--deliver-at-utc",
    default=None,
    help="Reset next delivery to an absolute UTC timestamp.",
)
@click.option(
    "--interval-seconds",
    default=None,
    type=click.FloatRange(min=0.0, min_open=True),
    help="Replacement repeat cadence in seconds.",
)
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(help_text="Houmao pair authority port override for reminder update")
@managed_agent_selector_options
def set_gateway_reminder_command(
    reminder_id: str,
    title: str | None,
    mode: str | None,
    prompt: str | None,
    sequence: str | None,
    ensure_enter: bool | None,
    ranking: int | None,
    before_all: bool,
    after_all: bool,
    paused: bool | None,
    start_after_seconds: float | None,
    deliver_at_utc: str | None,
    interval_seconds: float | None,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Update one live gateway reminder for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="reminders set",
    )
    existing = gateway_get_reminder(target, reminder_id=reminder_id)
    live_reminders = gateway_list_reminders(target)
    ranking_value = _resolve_reminder_ranking_value(
        live_reminders,
        ranking=ranking,
        before_all=before_all,
        after_all=after_all,
        require_choice=False,
        exclude_reminder_id=reminder_id,
    )
    payload = _build_put_reminder_payload(
        existing,
        title=title,
        mode=mode,
        prompt=prompt,
        sequence=sequence,
        ensure_enter=ensure_enter,
        ranking=ranking_value,
        paused=paused,
        start_after_seconds=start_after_seconds,
        deliver_at_utc=deliver_at_utc,
        interval_seconds=interval_seconds,
    )
    updated = gateway_put_reminder(target, reminder_id=reminder_id, payload=payload)
    effective_reminder_id = gateway_list_reminders(target).effective_reminder_id
    _emit_reminder_detail(updated, effective_reminder_id=effective_reminder_id)


@reminders_gateway_group.command(name="remove")
@click.option("--reminder-id", required=True, help="Reminder id to delete.")
@_current_session_option
@_target_tmux_session_option
@_gateway_pair_port_option(help_text="Houmao pair authority port override for reminder deletion")
@managed_agent_selector_options
def remove_gateway_reminder_command(
    reminder_id: str,
    current_session: bool,
    target_tmux_session: str | None,
    pair_port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Delete one live gateway reminder for one managed agent."""

    target = _resolve_gateway_command_target(
        agent_id=agent_id,
        agent_name=agent_name,
        pair_port=pair_port,
        current_session=current_session,
        target_tmux_session=target_tmux_session,
        operation_name="reminders remove",
    )
    emit(gateway_delete_reminder(target, reminder_id=reminder_id))


def _resolve_reminder_ranking_value(
    live_reminders: GatewayReminderListV1,
    *,
    ranking: int | None,
    before_all: bool,
    after_all: bool,
    require_choice: bool,
    exclude_reminder_id: str | None = None,
) -> int | None:
    """Resolve one concrete reminder ranking from CLI inputs and live reminder state."""

    mode_count = int(ranking is not None) + int(before_all) + int(after_all)
    if require_choice and mode_count != 1:
        raise click.ClickException(
            "Use exactly one of `--ranking`, `--before-all`, or `--after-all`."
        )
    if not require_choice and mode_count > 1:
        raise click.ClickException(
            "Use at most one of `--ranking`, `--before-all`, or `--after-all`."
        )
    if ranking is not None:
        return ranking
    if mode_count == 0:
        return None

    rankings = [
        reminder.ranking
        for reminder in live_reminders.reminders
        if reminder.reminder_id != exclude_reminder_id
    ]
    if not rankings:
        return 0
    if before_all:
        return min(rankings) - 1
    return max(rankings) + 1


def _build_create_reminder_definition(
    *,
    title: str,
    mode: str,
    prompt: str | None,
    sequence: str | None,
    ensure_enter: bool,
    ranking: int,
    paused: bool,
    start_after_seconds: float | None,
    deliver_at_utc: str | None,
    interval_seconds: float | None,
) -> GatewayReminderDefinitionV1:
    """Build and validate one create payload from CLI fields."""

    payload: dict[str, Any] = {
        "title": title,
        "mode": mode,
        "ranking": ranking,
        "paused": paused,
        "start_after_seconds": start_after_seconds,
        "deliver_at_utc": deliver_at_utc,
        "interval_seconds": interval_seconds,
    }
    if sequence is not None:
        payload["send_keys"] = {
            "sequence": sequence,
            "ensure_enter": ensure_enter,
        }
    else:
        payload["prompt"] = prompt
    return _validate_gateway_model(GatewayReminderDefinitionV1, payload)


def _build_put_reminder_payload(
    existing: GatewayReminderV1,
    *,
    title: str | None,
    mode: str | None,
    prompt: str | None,
    sequence: str | None,
    ensure_enter: bool | None,
    ranking: int | None,
    paused: bool | None,
    start_after_seconds: float | None,
    deliver_at_utc: str | None,
    interval_seconds: float | None,
) -> GatewayReminderPutV1:
    """Build and validate one patch-like reminder update payload."""

    if prompt is not None and sequence is not None:
        raise click.ClickException("Use exactly one of `--prompt` or `--sequence`.")

    payload = _mutable_reminder_payload(existing)
    if title is not None:
        payload["title"] = title
    if mode is not None:
        payload["mode"] = mode
    if ranking is not None:
        payload["ranking"] = ranking
    if paused is not None:
        payload["paused"] = paused

    if prompt is not None:
        payload["prompt"] = prompt
        payload["send_keys"] = None
    elif sequence is not None:
        resolved_ensure_enter = (
            ensure_enter
            if ensure_enter is not None
            else (existing.send_keys.ensure_enter if existing.send_keys is not None else True)
        )
        payload["prompt"] = None
        payload["send_keys"] = {
            "sequence": sequence,
            "ensure_enter": resolved_ensure_enter,
        }
    elif ensure_enter is not None:
        if not isinstance(payload.get("send_keys"), dict):
            raise click.ClickException(
                "`--ensure-enter/--no-ensure-enter` only applies to send-keys reminders."
            )
        payload["send_keys"] = {
            **dict(payload["send_keys"]),
            "ensure_enter": ensure_enter,
        }

    if start_after_seconds is not None:
        payload["start_after_seconds"] = start_after_seconds
        payload["deliver_at_utc"] = None
    elif deliver_at_utc is not None:
        payload["start_after_seconds"] = None
        payload["deliver_at_utc"] = deliver_at_utc

    resolved_mode = str(payload["mode"])
    if resolved_mode == "one_off" and interval_seconds is None:
        payload["interval_seconds"] = None
    elif interval_seconds is not None:
        payload["interval_seconds"] = interval_seconds

    return _validate_gateway_model(GatewayReminderPutV1, payload)


def _mutable_reminder_payload(existing: GatewayReminderV1) -> dict[str, Any]:
    """Project one live reminder into its mutable PUT shape."""

    payload: dict[str, Any] = {
        "mode": existing.mode,
        "title": existing.title,
        "prompt": existing.prompt,
        "send_keys": (
            existing.send_keys.model_dump(mode="json") if existing.send_keys is not None else None
        ),
        "ranking": existing.ranking,
        "paused": existing.paused,
        "start_after_seconds": None,
        "deliver_at_utc": existing.next_due_at_utc,
        "interval_seconds": existing.interval_seconds,
    }
    return payload


def _emit_reminder_detail(
    reminder: GatewayReminderV1,
    *,
    effective_reminder_id: str | None,
) -> None:
    """Emit one reminder detail while preserving raw JSON output for `--print-json`."""

    if _output_style() == "json":
        emit(reminder)
        return
    emit(
        {
            "effective_reminder_id": effective_reminder_id,
            "reminder": reminder.model_dump(mode="json"),
        },
        plain_renderer=render_reminder_detail_plain,
        fancy_renderer=render_reminder_detail_fancy,
    )


def _output_style() -> str:
    """Return the active CLI print style."""

    ctx = click.get_current_context(silent=True)
    if ctx is None or not isinstance(ctx.obj, dict):
        return "plain"
    output_context = ctx.obj.get("output")
    style = getattr(output_context, "style", None)
    return style if isinstance(style, str) else "plain"


def _validate_gateway_model(
    model_class: type[_ReminderModelT],
    payload: dict[str, Any],
) -> _ReminderModelT:
    """Validate one reminder payload and translate pydantic errors into Click errors."""

    try:
        return model_class.model_validate(payload)
    except ValidationError as exc:
        raise click.ClickException(_format_validation_error(exc)) from exc


def _format_validation_error(exc: ValidationError) -> str:
    """Render one compact Click-facing validation error."""

    messages: list[str] = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ()))
        message = str(error.get("msg", "invalid value"))
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages)


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
