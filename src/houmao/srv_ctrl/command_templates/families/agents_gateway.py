"""Command-template declarations for managed-agent gateway commands."""

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
    FieldConflict,
    TemplateField,
)


def templates() -> list[CommandTemplate]:
    """Return scoped gateway command templates."""

    templates: list[CommandTemplate] = []
    for scope in ("single", "self"):
        target_fields = _gateway_target_fields(scope=scope)
        target_conflicts = _gateway_target_conflicts(scope=scope)
        target_required = (("agent_name", "agent_id"),) if scope == "single" else ()
        family = f"agents.{scope}.gateway"
        template_prefix = f"agents.{scope}.gateway"
        target_prefix = ("agents", scope, "gateway")

        for verb in ("status", "detach"):
            templates.append(
                _template(
                    f"{template_prefix}.{verb}",
                    (*target_prefix, verb),
                    f"Gateway {verb}.",
                    target_fields,
                    family=family,
                    conflicts=target_conflicts,
                    required_one_of=target_required,
                )
            )
        templates.append(
            _template(
                f"{template_prefix}.attach",
                (*target_prefix, "attach"),
                "Gateway attach.",
                (
                    *target_fields,
                    _flag("background", "--background", "Run the gateway as a background process."),
                    *_attach_timing_fields(),
                ),
                family=family,
                conflicts=target_conflicts,
                required_one_of=target_required,
            )
        )
        templates.extend(
            (
                _template(
                    f"{template_prefix}.prompt",
                    (*target_prefix, "prompt"),
                    "Submit a direct gateway prompt.",
                    (
                        *target_fields,
                        _f("prompt", "--prompt", "Prompt text."),
                        _flag("force", "--force", "Send even when the target is not prompt-ready."),
                        _f("model", "--model", "Request-scoped headless model override."),
                        _int(
                            "reasoning_level",
                            "--reasoning-level",
                            "Request-scoped reasoning preset index.",
                        ),
                    ),
                    family=family,
                    conflicts=target_conflicts,
                    required_one_of=target_required,
                ),
                _template(
                    f"{template_prefix}.interrupt",
                    (*target_prefix, "interrupt"),
                    "Interrupt through gateway.",
                    target_fields,
                    family=family,
                    conflicts=target_conflicts,
                    required_one_of=target_required,
                ),
                _template(
                    f"{template_prefix}.send-keys",
                    (*target_prefix, "send-keys"),
                    "Send raw keys through gateway.",
                    (
                        *target_fields,
                        _req("sequence", "--sequence", "Raw key sequence."),
                        _flag(
                            "escape_special_keys",
                            "--escape-special-keys",
                            "Treat the sequence literally instead of parsing special-key tokens.",
                        ),
                    ),
                    family=family,
                    conflicts=target_conflicts,
                    required_one_of=target_required,
                ),
            )
        )
        _append_tui_templates(
            templates=templates,
            template_prefix=template_prefix,
            target_prefix=target_prefix,
            family=family,
            target_fields=target_fields,
            target_conflicts=target_conflicts,
            target_required=target_required,
        )
        _append_mail_notifier_templates(
            templates=templates,
            template_prefix=template_prefix,
            target_prefix=target_prefix,
            family=family,
            target_fields=target_fields,
            target_conflicts=target_conflicts,
            target_required=target_required,
        )
        _append_reminder_templates(
            templates=templates,
            template_prefix=template_prefix,
            target_prefix=target_prefix,
            family=family,
            target_fields=target_fields,
            target_conflicts=target_conflicts,
            target_required=target_required,
        )
    return templates


def _gateway_target_fields(*, scope: str) -> tuple[TemplateField, ...]:
    """Return target fields for one gateway scope."""

    if scope == "self":
        return ()
    return (
        _f(
            "agent_name",
            "--agent-name",
            "Friendly managed-agent name.",
            argv_insert_index=3,
        ),
        _f("agent_id", "--agent-id", "Managed-agent id.", argv_insert_index=3),
        _int("pair_port", "--pair-port", "Houmao pair authority port."),
    )


def _gateway_target_conflicts(*, scope: str) -> tuple[FieldConflict, ...]:
    """Return target-field conflicts for one gateway scope."""

    if scope == "self":
        return ()
    return (_conflict("agent_name", "agent_id", message="Agent selectors are mutually exclusive."),)


def _attach_timing_fields() -> tuple[TemplateField, ...]:
    """Return gateway attach timing override fields."""

    return (
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


def _append_tui_templates(
    *,
    templates: list[CommandTemplate],
    template_prefix: str,
    target_prefix: tuple[str, ...],
    family: str,
    target_fields: tuple[TemplateField, ...],
    target_conflicts: tuple[FieldConflict, ...],
    target_required: tuple[tuple[str, ...], ...],
) -> None:
    """Append scoped gateway TUI templates."""

    for verb in ("state", "history", "watch", "note-prompt"):
        tui_fields: tuple[TemplateField, ...] = target_fields
        if verb == "watch":
            tui_fields = (
                *target_fields,
                _number("interval_seconds", "--interval-seconds", "Watch poll interval seconds."),
            )
        if verb == "note-prompt":
            tui_fields = (*target_fields, _req("prompt", "--prompt", "Prompt note."))
        templates.append(
            _template(
                f"{template_prefix}.tui.{verb}",
                (*target_prefix, "tui", verb),
                f"Gateway TUI {verb}.",
                tui_fields,
                family=family,
                conflicts=target_conflicts,
                required_one_of=target_required,
            )
        )


def _append_mail_notifier_templates(
    *,
    templates: list[CommandTemplate],
    template_prefix: str,
    target_prefix: tuple[str, ...],
    family: str,
    target_fields: tuple[TemplateField, ...],
    target_conflicts: tuple[FieldConflict, ...],
    target_required: tuple[tuple[str, ...], ...],
) -> None:
    """Append scoped gateway mail-notifier templates."""

    for verb in ("status", "enable", "disable"):
        fields = (
            target_fields
            if verb != "enable"
            else (
                *target_fields,
                _req_int("interval_seconds", "--interval-seconds", "Polling interval seconds."),
                _choice("mode", "--mode", "Notifier mode.", ("any_inbox", "unread_only")),
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
            )
        )
        templates.append(
            _template(
                f"{template_prefix}.mail-notifier.{verb}",
                (*target_prefix, "mail-notifier", verb),
                f"Gateway mail notifier {verb}.",
                fields,
                family=family,
                conflicts=target_conflicts,
                required_one_of=target_required,
            )
        )


def _append_reminder_templates(
    *,
    templates: list[CommandTemplate],
    template_prefix: str,
    target_prefix: tuple[str, ...],
    family: str,
    target_fields: tuple[TemplateField, ...],
    target_conflicts: tuple[FieldConflict, ...],
    target_required: tuple[tuple[str, ...], ...],
) -> None:
    """Append scoped gateway reminder templates."""

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
        *target_conflicts,
        _conflict("prompt", "sequence", message="Reminder prompt and send-keys sequence conflict."),
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
        "list": target_fields,
        "get": (*target_fields, _req("reminder_id", "--reminder-id", "Reminder id.")),
        "create": (
            *target_fields,
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
            *target_fields,
            _req("reminder_id", "--reminder-id", "Reminder id."),
            *reminder_payload_fields,
        ),
        "remove": (*target_fields, _req("reminder_id", "--reminder-id", "Reminder id.")),
    }
    for verb, reminder_fields in reminder_fields_by_verb.items():
        templates.append(
            _template(
                f"{template_prefix}.reminders.{verb}",
                (*target_prefix, "reminders", verb),
                f"Gateway reminders {verb}.",
                reminder_fields,
                family=family,
                conflicts=reminder_conflicts,
                required_one_of=(
                    *target_required,
                    *(
                        (("prompt", "sequence"), ("ranking", "before_all", "after_all"))
                        if verb == "create"
                        else ()
                    ),
                ),
            )
        )
