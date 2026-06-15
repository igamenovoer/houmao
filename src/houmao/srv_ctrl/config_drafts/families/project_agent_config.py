"""Config drafts for project and native-agent documents."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from houmao.srv_ctrl.config_drafts.models import ConfigDraft, DraftField

_TOOL_CHOICES: tuple[str, ...] = ("claude", "codex", "gemini", "kimi")
_EASY_SPECIALIST_SETUP = "default"
_EASY_SPECIALIST_PROMPT_MODE = "unattended"


def drafts() -> list[ConfigDraft]:
    """Return maintained project and native-agent config drafts."""

    return [
        ConfigDraft(
            draft_id="project.specialist",
            description="Draft project specialist configuration.",
            config_kind="project.specialist",
            fields=(
                _required("name"),
                _required("tool", choices=_TOOL_CHOICES),
                _required("credential"),
            ),
            render=_specialist_payload,
        ),
        ConfigDraft(
            draft_id="project.profile",
            description="Draft specialist-backed project profile configuration.",
            config_kind="project.profile",
            fields=(
                _required("name"),
                _required("specialist"),
                _required("credential"),
            ),
            render=_easy_profile_payload,
        ),
        ConfigDraft(
            draft_id="internals.native-agent.launch-dossier",
            description="Draft recipe-backed native launch-dossier configuration.",
            config_kind="internals.native-agent.launch-dossier",
            fields=(
                _required("name"),
                _required("recipe"),
                _required("credential"),
            ),
            render=_native_launch_dossier_payload,
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
        "config_kind": "project.specialist",
        "name": _str_value(fields, "name"),
        "tool": _str_value(fields, "tool"),
        "credential": {"name": _str_value(fields, "credential")},
        "setup": _EASY_SPECIALIST_SETUP,
        "launch": {"prompt_mode": _EASY_SPECIALIST_PROMPT_MODE},
    }


def _easy_profile_payload(fields: Mapping[str, object]) -> Mapping[str, Any]:
    """Return one specialist-backed project profile draft payload."""

    return {
        "config_kind": "project.profile",
        "name": _str_value(fields, "name"),
        "profile_lane": "profile",
        "source": {
            "kind": "specialist",
            "name": _str_value(fields, "specialist"),
        },
        "defaults": {"auth": _str_value(fields, "credential")},
    }


def _native_launch_dossier_payload(fields: Mapping[str, object]) -> Mapping[str, Any]:
    """Return one recipe-backed native launch-dossier draft payload."""

    return {
        "config_kind": "internals.native-agent.launch-dossier",
        "name": _str_value(fields, "name"),
        "resource_kind": "launch_dossier",
        "source": {
            "kind": "recipe",
            "name": _str_value(fields, "recipe"),
        },
        "defaults": {"auth": _str_value(fields, "credential")},
    }


def _str_value(fields: Mapping[str, object], name: str) -> str:
    """Return one validated string value from fields."""

    value = fields[name]
    if not isinstance(value, str):
        raise TypeError(f"Expected string field `{name}`.")
    return value
