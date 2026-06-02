"""Command-template declarations for this command family."""

from __future__ import annotations

from ..builders import (
    _choice,
    _conflict,
    _f,
    _flag,
    _int,
    _many,
    _req,
    _template,
)
from ..models import (
    CommandTemplate,
    _RELAUNCH_CHAT_SESSION_MODES,
)


def templates() -> list[CommandTemplate]:
    """Return managed-agent lifecycle command templates."""

    single_selector_fields = (
        _f(
            "agent_name",
            "--agent-name",
            "Friendly managed-agent name.",
            argv_insert_index=3,
        ),
        _f("agent_id", "--agent-id", "Managed-agent id.", argv_insert_index=3),
    )
    selector_conflicts = (
        _conflict("agent_name", "agent_id", message="Agent selectors are mutually exclusive."),
    )
    join_template = _template(
        "agents.self.join",
        ("agents", "self", "join"),
        "Adopt an existing tmux-backed session.",
        (
            _req("agent_name", "--agent-name", "Friendly managed-agent name."),
            _f("agent_id", "--agent-id", "Managed-agent id."),
            _flag("headless", "--headless", "Adopt as headless."),
            _f("provider", "--provider", "Provider id."),
            _many("launch_args", "--launch-args", "Provider launch argument."),
            _many("launch_env", "--launch-env", "Launch environment record."),
            _f("workdir", "--workdir", "Working directory."),
            _f("resume_id", "--resume-id", "Headless resume id."),
            _flag(
                "no_install_houmao_skills", "--no-install-houmao-skills", "Skip skill installation."
            ),
        ),
        family="agents.lifecycle",
        conflicts=(_conflict("agent_name", "agent_id", message="Use one primary join selector."),),
    )
    single_lifecycle_templates = [
        _template(
            "agents.single.state",
            ("agents", "single", "state"),
            "Show selected managed-agent state.",
            (*single_selector_fields, _int("port", "--port", "Houmao pair authority port.")),
            family="agents.lifecycle",
            required_one_of=(("agent_name", "agent_id"),),
            conflicts=selector_conflicts,
        ),
        _template(
            "agents.single.prompt",
            ("agents", "single", "prompt"),
            "Submit a prompt to one selected managed agent.",
            (
                *single_selector_fields,
                _f("prompt", "--prompt", "Prompt text."),
                _f("model", "--model", "Request-scoped headless model override."),
                _int("reasoning_level", "--reasoning-level", "Request-scoped reasoning preset."),
                _int("port", "--port", "Houmao pair authority port."),
            ),
            family="agents.lifecycle",
            required_one_of=(("agent_name", "agent_id"),),
            conflicts=selector_conflicts,
        ),
        _template(
            "agents.single.interrupt",
            ("agents", "single", "interrupt"),
            "Interrupt one selected managed agent.",
            (*single_selector_fields, _int("port", "--port", "Houmao pair authority port.")),
            family="agents.lifecycle",
            required_one_of=(("agent_name", "agent_id"),),
            conflicts=selector_conflicts,
        ),
        _template(
            "agents.single.stop",
            ("agents", "single", "stop"),
            "Stop one selected managed agent.",
            (*single_selector_fields, _int("port", "--port", "Houmao pair authority port.")),
            family="agents.lifecycle",
            required_one_of=(("agent_name", "agent_id"),),
            conflicts=selector_conflicts,
        ),
        _template(
            "agents.single.relaunch",
            ("agents", "single", "relaunch"),
            "Relaunch one selected tmux-backed managed agent.",
            (
                *single_selector_fields,
                _int("port", "--port", "Houmao pair authority port."),
                _choice(
                    "chat_session_mode",
                    "--chat-session-mode",
                    "Relaunch chat-session mode.",
                    _RELAUNCH_CHAT_SESSION_MODES,
                    default_action="omit-to-inherit",
                ),
                _f("chat_session_id", "--chat-session-id", "Provider chat-session id."),
            ),
            family="agents.lifecycle",
            required_one_of=(("agent_name", "agent_id"),),
            conflicts=selector_conflicts,
        ),
    ]
    self_lifecycle_templates = [
        _template(
            "agents.self.identity",
            ("agents", "self", "identity"),
            "Show current managed-session identity.",
            (),
            family="agents.lifecycle",
        ),
        _template(
            "agents.self.state",
            ("agents", "self", "state"),
            "Show current managed-session state.",
            (),
            family="agents.lifecycle",
        ),
        _template(
            "agents.self.prompt",
            ("agents", "self", "prompt"),
            "Submit a prompt to the current managed session.",
            (
                _f("prompt", "--prompt", "Prompt text."),
                _f("model", "--model", "Request-scoped headless model override."),
                _int("reasoning_level", "--reasoning-level", "Request-scoped reasoning preset."),
            ),
            family="agents.lifecycle",
        ),
        _template(
            "agents.self.interrupt",
            ("agents", "self", "interrupt"),
            "Interrupt the current managed session.",
            (),
            family="agents.lifecycle",
        ),
        _template(
            "agents.self.relaunch",
            ("agents", "self", "relaunch"),
            "Refresh the active tmux-backed current managed session.",
            (
                _choice(
                    "chat_session_mode",
                    "--chat-session-mode",
                    "Relaunch chat-session mode.",
                    _RELAUNCH_CHAT_SESSION_MODES,
                    default_action="omit-to-inherit",
                ),
                _f("chat_session_id", "--chat-session-id", "Provider chat-session id."),
            ),
            family="agents.lifecycle",
        ),
    ]
    global_list_template = _template(
        "agents.global.list",
        ("agents", "global", "list"),
        "List local managed agents from the shared registry.",
        (
            _int("port", "--port", "Houmao server port."),
            _choice(
                "state",
                "--state",
                "Lifecycle state filter.",
                ("active", "stopped", "relaunching", "retired", "all"),
            ),
        ),
        family="agents.lifecycle",
    )
    cleanup_templates = [
        _template(
            f"agents.single.cleanup.{kind}",
            ("agents", "single", "cleanup", kind),
            f"Clean managed-agent {kind} artifacts.",
            (
                *single_selector_fields,
                _f("manifest_path", "--manifest-path", "Session manifest path."),
                _f("session_root", "--session-root", "Session root path."),
                _flag("dry_run", "--dry-run", "Preview cleanup."),
                *(
                    (
                        _flag(
                            "purge_registry", "--purge-registry", "Purge matching registry record."
                        ),
                    )
                    if kind == "session"
                    else ()
                ),
            ),
            family="agents.lifecycle",
            required_one_of=(("agent_name", "agent_id"),),
            conflicts=selector_conflicts,
        )
        for kind in ("session", "logs")
    ]
    external_templates = [
        _template(
            "agents.external.register",
            ("agents", "external", "register"),
            "Register one external communication-only agent reference.",
            (
                _req("name", "--name", "Local external-agent alias."),
                _req("api_base_url", "--api-base-url", "Remote passive-server base URL."),
                _req("agent_ref", "--agent-ref", "Remote managed-agent id or name."),
                _flag("gateway_enabled", "--gateway-enabled", "Require remote gateway."),
                _flag("replace", "--replace", "Replace an existing external import."),
            ),
            family="agents.external",
        ),
        _template(
            "agents.external.list",
            ("agents", "external", "list"),
            "List external communication-only imports.",
            (),
            family="agents.external",
        ),
    ]
    for verb in ("get", "verify", "remove"):
        external_templates.append(
            _template(
                f"agents.external.{verb}",
                ("agents", "external", verb),
                f"{verb.title()} one external communication-only import.",
                (
                    _f("agent_name", "--agent-name", "Local external-agent alias."),
                    _f("agent_id", "--agent-id", "External agent id."),
                ),
                family="agents.external",
                required_one_of=(("agent_name", "agent_id"),),
                conflicts=selector_conflicts,
            )
        )
    return [
        global_list_template,
        join_template,
        *single_lifecycle_templates,
        *self_lifecycle_templates,
        *cleanup_templates,
        *external_templates,
    ]
