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

    selector_fields = (
        _f("agent_name", "--agent-name", "Friendly managed-agent name."),
        _f("agent_id", "--agent-id", "Managed-agent id."),
    )
    launch_fields = (
        _f("agents", "--agents", "Native source selector."),
        _f("launch_profile", "--launch-profile", "Project launch profile."),
        *selector_fields,
        _f("auth", "--auth", "Auth override."),
        _f("model", "--model", "One-shot model override."),
        _int("reasoning_level", "--reasoning-level", "One-shot reasoning preset index."),
        _f("session_name", "--session-name", "tmux session name."),
        _flag("headless", "--headless", "Launch headless.", default_action="omit-to-inherit"),
        _flag(
            "managed_header",
            "--managed-header",
            "Managed-header posture.",
            negative_option="--no-managed-header",
            default_action="omit-to-inherit",
        ),
        _many(
            "managed_header_section", "--managed-header-section", "Managed-header section override."
        ),
        _f("workdir", "--workdir", "Runtime workdir."),
        _choice(
            "headless_display_style",
            "--headless-display-style",
            "Headless display style.",
            ("plain", "json", "fancy"),
        ),
        _choice(
            "headless_display_detail",
            "--headless-display-detail",
            "Headless display detail.",
            ("concise", "detail"),
        ),
        _f("provider", "--provider", "Provider id."),
        _flag("reuse_home", "--reuse-home", "Reuse compatible stopped home."),
        _choice("force", "--force", "Managed launch force mode.", ("reuse", "clean")),
    )
    launch_template = _template(
        "agents.launch",
        ("agents", "launch"),
        "Launch one managed agent.",
        launch_fields,
        family="agents.lifecycle",
        required_one_of=(("agents", "launch_profile"),),
        conflicts=(
            _conflict(
                "agents", "launch_profile", message="Direct source and launch profile conflict."
            ),
        ),
    )
    profile_launch_template = _template(
        "agents.launch-profile.launch",
        ("agents", "launch"),
        "Launch one managed agent from a project launch profile.",
        (_req("launch_profile", "--launch-profile", "Project launch profile."), *launch_fields[2:]),
        family="agents.lifecycle",
    )
    join_template = _template(
        "agents.join",
        ("agents", "join"),
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
    relaunch_template = _template(
        "agents.relaunch",
        ("agents", "relaunch"),
        "Relaunch one tmux-backed managed agent.",
        (
            *selector_fields,
            _int("port", "--port", "Houmao server port."),
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
        conflicts=(
            _conflict("agent_name", "agent_id", message="Agent selectors are mutually exclusive."),
        ),
    )
    cleanup_templates = [
        _template(
            f"agents.cleanup.{kind}",
            ("agents", "cleanup", kind),
            f"Clean managed-agent {kind} artifacts.",
            (
                _f("manifest_path", "--manifest-path", "Session manifest path."),
                _f("session_root", "--session-root", "Session root path."),
                *selector_fields,
                _flag("dry_run", "--dry-run", "Preview cleanup."),
                _flag("purge_registry", "--purge-registry", "Purge matching registry record."),
            ),
            family="agents.lifecycle",
            required_one_of=(("manifest_path", "session_root", "agent_name", "agent_id"),),
            conflicts=(
                _conflict(
                    "manifest_path",
                    "session_root",
                    "agent_name",
                    "agent_id",
                    message="Cleanup target selectors are mutually exclusive.",
                ),
            ),
        )
        for kind in ("session", "logs")
    ]
    return [
        launch_template,
        profile_launch_template,
        _template(
            "agents.launch.profile",
            ("agents", "launch"),
            "Alias for launch-profile launch.",
            profile_launch_template.fields,
            family="agents.lifecycle",
        ),
        join_template,
        relaunch_template,
        *cleanup_templates,
    ]
