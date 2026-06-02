"""Config drafts for project-local agent definition documents."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from houmao.project.config_payloads import build_launch_profile_config_payload
from houmao.srv_ctrl.config_drafts.models import ConfigDraft, DraftField

_TOOL_CHOICES: tuple[str, ...] = ("claude", "codex", "gemini")
_EASY_SPECIALIST_SETUP = "default"
_EASY_SPECIALIST_PROMPT_MODE = "unattended"


def drafts() -> list[ConfigDraft]:
    """Return project agent-definition config drafts."""

    return [
        ConfigDraft(
            draft_id="project.easy.specialist",
            description="Draft high-level project-easy specialist configuration.",
            config_kind="project.easy.specialist",
            fields=(
                _required("name"),
                _required("tool", choices=_TOOL_CHOICES),
                _required("credential"),
            ),
            render=_specialist_payload,
        ),
        ConfigDraft(
            draft_id="project.easy.profile",
            description="Draft specialist-backed easy profile configuration.",
            config_kind="project.easy.profile",
            fields=(
                _required("name"),
                _required("specialist"),
                _required("credential"),
            ),
            render=_easy_profile_payload,
        ),
        ConfigDraft(
            draft_id="project.agents.launch-profile",
            description="Draft recipe-backed raw launch-profile configuration.",
            config_kind="project.agents.launch-profile",
            fields=(
                _required("name"),
                _required("recipe"),
                _required("credential"),
            ),
            render=_raw_launch_profile_payload,
        ),
    ]


def _required(
    name: str,
    *,
    choices: tuple[str, ...] = (),
) -> DraftField:
    """Build one required string field."""

    return DraftField(name=name, required=True, choices=choices)


def _specialist_payload(fields: Mapping[str, object]) -> Mapping[str, Any]:
    """Return one high-level specialist draft payload."""

    return {
        "config_kind": "project.easy.specialist",
        "name": _str_value(fields, "name"),
        "tool": _str_value(fields, "tool"),
        "credential": {"name": _str_value(fields, "credential")},
        "setup": _EASY_SPECIALIST_SETUP,
        "launch": {"prompt_mode": _EASY_SPECIALIST_PROMPT_MODE},
    }


def _easy_profile_payload(fields: Mapping[str, object]) -> Mapping[str, Any]:
    """Return one specialist-backed easy profile draft payload."""

    return _launch_profile_payload(
        name=_str_value(fields, "name"),
        profile_lane="easy_profile",
        source_kind="specialist",
        source_name=_str_value(fields, "specialist"),
        credential=_str_value(fields, "credential"),
    )


def _raw_launch_profile_payload(fields: Mapping[str, object]) -> Mapping[str, Any]:
    """Return one recipe-backed raw launch-profile draft payload."""

    return _launch_profile_payload(
        name=_str_value(fields, "name"),
        profile_lane="launch_profile",
        source_kind="recipe",
        source_name=_str_value(fields, "recipe"),
        credential=_str_value(fields, "credential"),
    )


def _launch_profile_payload(
    *,
    name: str,
    profile_lane: str,
    source_kind: str,
    source_name: str,
    credential: str,
) -> Mapping[str, Any]:
    """Return the shared launch-profile draft payload."""

    return build_launch_profile_config_payload(
        name=name,
        profile_lane=profile_lane,
        source_kind=source_kind,
        source_name=source_name,
        defaults={"auth": credential},
    )


def _str_value(fields: Mapping[str, object], name: str) -> str:
    """Return one validated string value from fields."""

    value = fields[name]
    if not isinstance(value, str):
        raise TypeError(f"Expected string field `{name}`.")
    return value
