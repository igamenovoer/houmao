"""Command-template declarations for this command family."""

from __future__ import annotations

from ..builders import (
    _choice,
    _conflict,
    _f,
    _flag,
    _int,
    _number,
    _req,
    _req_int,
    _template,
)
from ..models import (
    CommandTemplate,
    TemplateField,
)


def templates() -> list[CommandTemplate]:
    """Return gateway command templates."""

    selector_fields = (
        _f("agent_name", "--agent-name", "Friendly managed-agent name."),
        _f("agent_id", "--agent-id", "Managed-agent id."),
        _int("pair_port", "--pair-port", "Houmao pair authority port."),
        _f("target_tmux_session", "--target-tmux-session", "Target tmux session."),
        _flag("current_session", "--current-session", "Resolve from the current tmux session."),
    )
    selector_conflicts = (
        _conflict(
            "agent_name",
            "agent_id",
            "target_tmux_session",
            "current_session",
            message=(
                "Gateway targets accept one of agent_name, agent_id, target_tmux_session, "
                "or current_session."
            ),
        ),
        _conflict(
            "pair_port",
            "target_tmux_session",
            "current_session",
            message="Pair authority port is only valid with an explicit agent selector.",
        ),
    )
    attach_timing_fields = (
        _number(
            "gateway_tui_watch_poll_interval_seconds",
            "--gateway-tui-watch-poll-interval-seconds",
            "Gateway TUI watch poll interval seconds.",
        ),
        _number(
            "gateway_tui_stability_threshold_seconds",
            "--gateway-tui-stability-threshold-seconds",
            "Gateway TUI stability threshold seconds.",
        ),
        _number(
            "gateway_tui_completion_stability_seconds",
            "--gateway-tui-completion-stability-seconds",
            "Gateway TUI completion stability seconds.",
        ),
        _number(
            "gateway_tui_unknown_to_stalled_timeout_seconds",
            "--gateway-tui-unknown-to-stalled-timeout-seconds",
            "Gateway TUI unknown-to-stalled timeout seconds.",
        ),
        _number(
            "gateway_tui_stale_active_recovery_seconds",
            "--gateway-tui-stale-active-recovery-seconds",
            "Gateway TUI stale-active recovery seconds.",
        ),
        _number(
            "gateway_tui_final_stable_active_recovery_seconds",
            "--gateway-tui-final-stable-active-recovery-seconds",
            "Gateway TUI final stable-active recovery seconds.",
        ),
    )
    templates: list[CommandTemplate] = []
    for verb in ("status", "detach"):
        templates.append(
            _template(
                f"agents.gateway.{verb}",
                ("agents", "gateway", verb),
                f"Gateway {verb}.",
                selector_fields,
                family="agents.gateway",
                conflicts=selector_conflicts,
            )
        )
    templates.append(
        _template(
            "agents.gateway.attach",
            ("agents", "gateway", "attach"),
            "Gateway attach.",
            (
                *selector_fields,
                _flag("background", "--background", "Run the gateway as a background process."),
                *attach_timing_fields,
            ),
            family="agents.gateway",
            conflicts=selector_conflicts,
        )
    )
    templates.extend(
        (
            _template(
                "agents.gateway.prompt",
                ("agents", "gateway", "prompt"),
                "Submit a direct gateway prompt.",
                (
                    *selector_fields,
                    _f("prompt", "--prompt", "Prompt text."),
                    _flag("force", "--force", "Send even when the target is not prompt-ready."),
                    _f("model", "--model", "Request-scoped headless model override."),
                    _int(
                        "reasoning_level",
                        "--reasoning-level",
                        "Request-scoped reasoning preset index.",
                    ),
                ),
                family="agents.gateway",
                conflicts=selector_conflicts,
            ),
            _template(
                "agents.gateway.interrupt",
                ("agents", "gateway", "interrupt"),
                "Interrupt through gateway.",
                selector_fields,
                family="agents.gateway",
                conflicts=selector_conflicts,
            ),
            _template(
                "agents.gateway.send-keys",
                ("agents", "gateway", "send-keys"),
                "Send raw keys through gateway.",
                (
                    *selector_fields,
                    _req("sequence", "--sequence", "Raw key sequence."),
                    _flag(
                        "escape_special_keys",
                        "--escape-special-keys",
                        "Treat the sequence literally instead of parsing special-key tokens.",
                    ),
                ),
                family="agents.gateway",
                conflicts=selector_conflicts,
            ),
        )
    )
    for verb in ("state", "history", "watch", "note-prompt"):
        tui_fields: tuple[TemplateField, ...] = selector_fields
        if verb == "watch":
            tui_fields = (
                *selector_fields,
                _number("interval_seconds", "--interval-seconds", "Watch poll interval seconds."),
            )
        if verb == "note-prompt":
            tui_fields = (*selector_fields, _req("prompt", "--prompt", "Prompt note."))
        templates.append(
            _template(
                f"agents.gateway.tui.{verb}",
                ("agents", "gateway", "tui", verb),
                f"Gateway TUI {verb}.",
                tui_fields,
                family="agents.gateway",
                conflicts=selector_conflicts,
            )
        )
    templates.extend(
        [
            _template(
                f"agents.gateway.mail-notifier.{verb}",
                ("agents", "gateway", "mail-notifier", verb),
                f"Gateway mail notifier {verb}.",
                selector_fields
                if verb != "enable"
                else (
                    *selector_fields,
                    _req_int("interval_seconds", "--interval-seconds", "Polling interval seconds."),
                    _choice(
                        "mode",
                        "--mode",
                        "Notifier mode.",
                        ("any_inbox", "unread_only"),
                    ),
                    _f("appendix_text", "--appendix-text", "Notifier prompt appendix."),
                    _choice(
                        "context_error_policy",
                        "--context-error-policy",
                        "Context error policy.",
                        ("continue_current", "clear_context"),
                    ),
                    _choice(
                        "pre_notification_context_action",
                        "--pre-notification-context-action",
                        "Pre-notification context action.",
                        ("none", "compact"),
                    ),
                ),
                family="agents.gateway",
                conflicts=selector_conflicts,
            )
            for verb in ("status", "enable", "disable")
        ]
    )
    reminder_payload_fields = (
        _f("title", "--title", "Reminder title."),
        _choice("mode", "--mode", "Reminder mode.", ("one_off", "repeat")),
        _f("prompt", "--prompt", "Prompt delivery text."),
        _f("sequence", "--sequence", "Raw key sequence delivery."),
        _flag(
            "ensure_enter",
            "--ensure-enter",
            "Ensure Enter after sequence.",
            negative_option="--no-ensure-enter",
        ),
        _int("ranking", "--ranking", "Explicit numeric ranking."),
        _flag("before_all", "--before-all", "Insert above the current minimum ranking."),
        _flag("after_all", "--after-all", "Append below the current maximum ranking."),
        _flag("paused", "--paused", "Pause reminder.", negative_option="--no-paused"),
        _number("start_after_seconds", "--start-after-seconds", "Relative start delay."),
        _f("deliver_at_utc", "--deliver-at-utc", "Absolute delivery time."),
        _number("interval_seconds", "--interval-seconds", "Repeat interval seconds."),
    )
    reminder_conflicts = (
        *selector_conflicts,
        _conflict(
            "prompt",
            "sequence",
            message="Reminder prompt and send-keys sequence conflict.",
        ),
        _conflict(
            "start_after_seconds",
            "deliver_at_utc",
            message="Reminder relative and absolute scheduling fields conflict.",
        ),
        _conflict(
            "ranking",
            "before_all",
            "after_all",
            message="Reminder ranking fields conflict.",
        ),
    )
    reminder_fields_by_verb: dict[str, tuple[TemplateField, ...]] = {
        "list": selector_fields,
        "get": (*selector_fields, _req("reminder_id", "--reminder-id", "Reminder id.")),
        "create": (
            *selector_fields,
            _req("title", "--title", "Reminder title."),
            _choice(
                "mode",
                "--mode",
                "Reminder mode.",
                ("one_off", "repeat"),
                default_action="required",
            ),
            *reminder_payload_fields[2:],
        ),
        "set": (
            *selector_fields,
            _req("reminder_id", "--reminder-id", "Reminder id."),
            *reminder_payload_fields,
        ),
        "remove": (*selector_fields, _req("reminder_id", "--reminder-id", "Reminder id.")),
    }
    for verb, reminder_fields in reminder_fields_by_verb.items():
        templates.append(
            _template(
                f"agents.gateway.reminders.{verb}",
                ("agents", "gateway", "reminders", verb),
                f"Gateway reminders {verb}.",
                reminder_fields,
                family="agents.gateway",
                conflicts=reminder_conflicts,
                required_one_of=(
                    (("prompt", "sequence"), ("ranking", "before_all", "after_all"))
                    if verb == "create"
                    else ()
                ),
            )
        )
    return templates
