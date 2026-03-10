"""Shared Claude home bootstrap helpers for non-interactive launches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final, Mapping

from ..errors import BackendExecutionError

_API_KEY_SUFFIX_LEN: Final[int] = 20
_RUNTIME_STATE_FILENAME: Final[str] = ".claude.json"
_STATE_TEMPLATE_FILENAME: Final[str] = "claude_state.template.json"
_SETTINGS_FILENAME: Final[str] = "settings.json"


def ensure_claude_home_bootstrap(
    *,
    home_path: Path,
    env: Mapping[str, str],
    working_directory: Path | None = None,
) -> None:
    """Ensure Claude runtime-home bootstrap invariants before launch.

    Parameters
    ----------
    home_path:
        Runtime Claude home path (`CLAUDE_CONFIG_DIR`).
    env:
        Effective launch environment values used to derive API-key approval state.
    working_directory:
        Optional working directory that should be pre-trusted to avoid blocking
        trust prompts in non-interactive tmux sessions.
    """

    _validate_settings_json(home_path)

    runtime_state_path = home_path / _RUNTIME_STATE_FILENAME
    if runtime_state_path.exists():
        return

    template = _load_template_json(home_path)
    materialized = _overlay_runtime_enforced_keys(
        template=template,
        env=env,
        working_directory=working_directory,
    )

    runtime_state_path.write_text(
        json.dumps(materialized, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_template_json(home_path: Path) -> dict[str, Any]:
    template_path = home_path / _STATE_TEMPLATE_FILENAME
    if not template_path.is_file():
        raise BackendExecutionError(
            "Missing Claude bootstrap template "
            f"`{template_path}`. Ensure the selected credential profile "
            f"provides `files/{_STATE_TEMPLATE_FILENAME}` and the Claude tool "
            "adapter projects it into the runtime home."
        )

    try:
        payload = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackendExecutionError(
            "Malformed Claude bootstrap template "
            f"`{template_path}`: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})."
        ) from exc

    if not isinstance(payload, dict):
        raise BackendExecutionError(
            f"Claude bootstrap template `{template_path}` must contain "
            "a top-level JSON object."
        )

    return payload


def _validate_settings_json(home_path: Path) -> None:
    settings_path = home_path / _SETTINGS_FILENAME
    if not settings_path.is_file():
        raise BackendExecutionError(
            f"Missing required Claude settings file `{settings_path}`. "
            "Configure a Claude config profile that projects `settings.json` "
            "with `skipDangerousModePermissionPrompt: true`."
        )

    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackendExecutionError(
            f"Malformed Claude settings file `{settings_path}`: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})."
        ) from exc

    if not isinstance(payload, dict):
        raise BackendExecutionError(
            f"Claude settings file `{settings_path}` must contain "
            "a top-level JSON object."
        )

    if payload.get("skipDangerousModePermissionPrompt") is not True:
        raise BackendExecutionError(
            f"Claude settings file `{settings_path}` must set "
            "`skipDangerousModePermissionPrompt` to true for non-interactive "
            "launches."
        )


def _overlay_runtime_enforced_keys(
    *,
    template: dict[str, Any],
    env: Mapping[str, str],
    working_directory: Path | None,
) -> dict[str, Any]:
    materialized = dict(template)
    materialized["hasCompletedOnboarding"] = True
    materialized["numStartups"] = 1

    # Claude Code shows a blocking "trust this folder" prompt on first launch
    # unless a trust decision is persisted. Seed a global trust entry so CAO
    # tmux sessions can start non-interactively inside ephemeral worktrees.
    projects = materialized.get("projects")
    if not isinstance(projects, dict):
        projects = {}
        materialized["projects"] = projects

    def _trust_project(project_key: str) -> None:
        record = projects.get(project_key)
        if not isinstance(record, dict):
            record = {}
            projects[project_key] = record
        record.setdefault("hasTrustDialogAccepted", True)

    _trust_project("/")
    if working_directory is not None:
        _trust_project(str(working_directory.resolve()))

    api_key = env.get("ANTHROPIC_API_KEY", "")
    if api_key:
        materialized["customApiKeyResponses"] = {
            "approved": [api_key[-_API_KEY_SUFFIX_LEN:]],
            "rejected": [],
        }
        if len(api_key) > _API_KEY_SUFFIX_LEN:
            serialized = json.dumps(materialized, sort_keys=True)
            if api_key in serialized:
                raise BackendExecutionError(
                    "Refusing to materialize `.claude.json`: the full "
                    "`ANTHROPIC_API_KEY` value appears in the resulting state. "
                    "Remove full API key values from the template input."
                )

    return materialized
