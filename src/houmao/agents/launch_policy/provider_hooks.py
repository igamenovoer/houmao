"""Provider-specific launch-policy hooks for Codex and Claude."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, Mapping

from houmao.agents.launch_policy.models import LaunchPolicyError, LaunchPolicyRequest

_CLAUDE_RUNTIME_STATE_FILENAME = ".claude.json"
_CLAUDE_STATE_TEMPLATE_FILENAME = "claude_state.template.json"
_CLAUDE_SETTINGS_FILENAME = "settings.json"
_CLAUDE_API_KEY_SUFFIX_LEN = 20
_CODEX_AUTH_FILENAME = "auth.json"
_CODEX_CONFIG_FILENAME = "config.toml"


def run_provider_hook(*, hook_id: str, request: LaunchPolicyRequest) -> None:
    """Dispatch one stable provider hook id."""

    if hook_id == "claude.ensure_api_key_approval":
        _claude_ensure_api_key_approval(request)
        return
    if hook_id == "claude.ensure_project_trust":
        _claude_ensure_project_trust(request)
        return
    if hook_id == "codex.validate_minimal_inputs":
        _codex_validate_minimal_inputs(request)
        return
    if hook_id == "codex.ensure_project_trust":
        _codex_ensure_project_trust(request)
        return
    if hook_id == "codex.ensure_model_migration_state":
        _codex_ensure_model_migration_state(request)
        return
    raise LaunchPolicyError(f"Unknown provider hook `{hook_id}`.")


def load_json_state(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk, defaulting to an empty object."""

    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LaunchPolicyError(
            f"Malformed JSON state `{path}`: {exc.msg} (line {exc.lineno}, column {exc.colno})."
        ) from exc
    if not isinstance(payload, dict):
        raise LaunchPolicyError(f"JSON state `{path}` must contain a top-level object.")
    return payload


def write_json_state(path: Path, payload: dict[str, Any]) -> None:
    """Persist one JSON object with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def set_json_key(*, path: Path, key_path: tuple[str, ...], value: Any) -> None:
    """Set one nested JSON key path while preserving unrelated state."""

    payload = (
        _load_json_state_with_template(path)
        if path.name == _CLAUDE_RUNTIME_STATE_FILENAME
        else load_json_state(path)
    )
    target = payload
    for key in key_path[:-1]:
        existing = target.get(key)
        if not isinstance(existing, dict):
            existing = {}
            target[key] = existing
        target = existing
    target[key_path[-1]] = value
    write_json_state(path, payload)


def load_toml_state(path: Path) -> dict[str, Any]:
    """Load one TOML object from disk, defaulting to an empty object."""

    if not path.exists():
        return {}
    raw_text = path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return {}
    try:
        payload = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:
        raise LaunchPolicyError(f"Malformed TOML state `{path}`: {exc}.") from exc
    if not isinstance(payload, dict):
        raise LaunchPolicyError(f"TOML state `{path}` must contain a top-level table.")
    return payload


def set_toml_key(*, path: Path, key_path: tuple[str, ...], value: str | bool | int) -> None:
    """Set one TOML key path using a minimal writer."""

    payload = load_toml_state(path)
    target = payload
    for key in key_path[:-1]:
        existing = target.get(key)
        if not isinstance(existing, dict):
            existing = {}
            target[key] = existing
        target = existing
    target[key_path[-1]] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_toml_mapping(payload) + "\n", encoding="utf-8")


def _load_json_state_with_template(path: Path) -> dict[str, Any]:
    """Load one JSON object, seeding from Claude template when available."""

    if path.exists():
        return load_json_state(path)

    template_path = path.parent / _CLAUDE_STATE_TEMPLATE_FILENAME
    if template_path.exists():
        return load_json_state(template_path)
    return {}


def _claude_runtime_state_path(request: LaunchPolicyRequest) -> Path:
    """Return the runtime `.claude.json` path."""

    return request.home_path / _CLAUDE_RUNTIME_STATE_FILENAME


def _claude_settings_path(request: LaunchPolicyRequest) -> Path:
    """Return the runtime `settings.json` path."""

    return request.home_path / _CLAUDE_SETTINGS_FILENAME


def _codex_config_path(request: LaunchPolicyRequest) -> Path:
    """Return the runtime `config.toml` path."""

    return request.home_path / _CODEX_CONFIG_FILENAME


def _claude_ensure_api_key_approval(request: LaunchPolicyRequest) -> None:
    """Seed API-key approval state without storing the full key value."""

    api_key = request.env.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return

    state_path = _claude_runtime_state_path(request)
    payload = _load_json_state_with_template(state_path)
    payload["hasCompletedOnboarding"] = True
    payload["numStartups"] = 1
    payload["customApiKeyResponses"] = {
        "approved": [api_key[-_CLAUDE_API_KEY_SUFFIX_LEN:]],
        "rejected": [],
    }
    serialized = json.dumps(payload, sort_keys=True)
    if len(api_key) > _CLAUDE_API_KEY_SUFFIX_LEN and api_key in serialized:
        raise LaunchPolicyError(
            "Refusing to persist Claude runtime state because the full API key leaked "
            "into `.claude.json`."
        )
    write_json_state(state_path, payload)


def _claude_ensure_project_trust(request: LaunchPolicyRequest) -> None:
    """Seed Claude workspace-trust state for the resolved workdir."""

    state_path = _claude_runtime_state_path(request)
    payload = _load_json_state_with_template(state_path)
    payload["hasCompletedOnboarding"] = True
    payload["numStartups"] = 1

    projects = payload.get("projects")
    if not isinstance(projects, dict):
        projects = {}
        payload["projects"] = projects

    project_key = str(request.working_directory.resolve())
    project_payload = projects.get(project_key)
    if not isinstance(project_payload, dict):
        project_payload = {}
        projects[project_key] = project_payload

    project_payload["hasCompletedProjectOnboarding"] = True
    project_payload["hasTrustDialogAccepted"] = True
    project_payload["projectOnboardingSeenCount"] = 0

    write_json_state(state_path, payload)


def _codex_validate_minimal_inputs(request: LaunchPolicyRequest) -> None:
    """Require either auth.json or an env-backed custom-provider contract."""

    if _has_usable_auth_json(request.home_path / _CODEX_AUTH_FILENAME):
        return
    if request.env.get("OPENAI_API_KEY", "").strip():
        return

    config_payload = load_toml_state(_codex_config_path(request))
    model_provider_name = config_payload.get("model_provider")
    if not isinstance(model_provider_name, str) or not model_provider_name.strip():
        raise LaunchPolicyError(
            "Codex unattended launch requires `auth.json`, `OPENAI_API_KEY`, or a "
            "config-backed env-only provider with `requires_openai_auth = false`."
        )

    providers = config_payload.get("model_providers")
    if not isinstance(providers, dict):
        raise LaunchPolicyError(
            "Codex unattended launch requires `auth.json`, `OPENAI_API_KEY`, or a "
            "config-backed env-only provider with `requires_openai_auth = false`."
        )

    provider_payload = providers.get(model_provider_name)
    if not isinstance(provider_payload, dict):
        raise LaunchPolicyError(
            "Codex unattended launch requires `auth.json`, `OPENAI_API_KEY`, or a "
            "config-backed env-only provider with `requires_openai_auth = false`."
        )

    requires_auth = provider_payload.get("requires_openai_auth", True)
    wire_api = provider_payload.get("wire_api")
    env_key = provider_payload.get("env_key", "OPENAI_API_KEY")

    if requires_auth is not False or wire_api != "responses":
        raise LaunchPolicyError(
            "Codex unattended launch requires `auth.json`, `OPENAI_API_KEY`, or a "
            "config-backed env-only provider with `requires_openai_auth = false` "
            'and `wire_api = "responses"`.'
        )
    if not isinstance(env_key, str) or not env_key.strip():
        raise LaunchPolicyError(
            "Codex env-only provider config must declare a non-empty `env_key`."
        )
    if not request.env.get(env_key, "").strip():
        raise LaunchPolicyError(
            f"Codex env-only provider `{model_provider_name}` requires env var `{env_key}`."
        )


def _codex_ensure_project_trust(request: LaunchPolicyRequest) -> None:
    """Seed Codex project trust for the resolved working directory."""

    trust_target = _resolve_codex_trust_target(request.working_directory)
    set_toml_key(
        path=_codex_config_path(request),
        key_path=("projects", str(trust_target), "trust_level"),
        value="trusted",
    )


def _codex_ensure_model_migration_state(request: LaunchPolicyRequest) -> None:
    """Seed Codex startup migration state for the current supported version."""

    config_path = _codex_config_path(request)
    payload = load_toml_state(config_path)
    model_value = payload.get("model")
    if model_value is None or model_value == "gpt-5.3-codex":
        set_toml_key(path=config_path, key_path=("model",), value="gpt-5.4")
        set_toml_key(
            path=config_path,
            key_path=("notice", "model_migrations", "gpt-5.3-codex"),
            value="gpt-5.4",
        )


def _has_usable_auth_json(path: Path) -> bool:
    """Return whether `auth.json` contains a non-empty object."""

    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LaunchPolicyError(
            f"Malformed Codex auth file `{path}`: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})."
        ) from exc
    return isinstance(payload, dict) and bool(payload)


def _resolve_codex_trust_target(working_directory: Path) -> Path:
    """Resolve the Codex trust target using the repo root when available."""

    resolved = working_directory.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    return resolved


def _render_toml_mapping(payload: Mapping[str, Any], *, prefix: tuple[str, ...] = ()) -> str:
    """Render a nested mapping as a small TOML document."""

    scalar_lines: list[str] = []
    table_lines: list[str] = []

    for key, value in payload.items():
        if isinstance(value, dict):
            header = ".".join(_toml_key_literal(part) for part in (*prefix, key))
            child = _render_toml_mapping(value, prefix=(*prefix, key))
            if child.strip():
                table_lines.append(f"[{header}]\n{child}")
            continue
        scalar_lines.append(f"{_toml_key_literal(key)} = {_toml_value_literal(value)}")

    sections = []
    if scalar_lines:
        sections.append("\n".join(scalar_lines))
    if table_lines:
        sections.append("\n\n".join(table_lines))
    return "\n\n".join(section for section in sections if section)


def _toml_key_literal(value: str) -> str:
    """Render one TOML bare key when possible, otherwise use a quoted key."""

    if (
        value
        and value[0].isalpha()
        and all(character.isalnum() or character in {"_", "-"} for character in value)
    ):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_value_literal(value: object) -> str:
    """Render one supported TOML scalar."""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    raise LaunchPolicyError(f"Unsupported TOML scalar value: {value!r}")
