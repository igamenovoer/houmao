"""Provider-specific launch-policy hooks for Claude, Codex, and Gemini."""

from __future__ import annotations

import json
import os
import tempfile
import tomllib
from contextlib import contextmanager
import fcntl
from pathlib import Path
from typing import Any, Iterator, Mapping

from houmao.agents.codex_cli_config import (
    CodexCliConfigOverride,
    append_or_replace_codex_config_overrides,
)
from houmao.agents.launch_policy.models import LaunchPolicyError, LaunchPolicyRequest

_CLAUDE_RUNTIME_STATE_FILENAME = ".claude.json"
_CLAUDE_STATE_TEMPLATE_FILENAME = "claude_state.template.json"
_CLAUDE_SETTINGS_FILENAME = "settings.json"
_CLAUDE_API_KEY_SUFFIX_LEN = 20
_CODEX_AUTH_FILENAME = "auth.json"
_CODEX_CONFIG_FILENAME = "config.toml"
_CODEX_UNATTENDED_APPROVAL_POLICY = "never"
_CODEX_UNATTENDED_SANDBOX_MODE = "danger-full-access"
_CODEX_MODEL_MIGRATION_SOURCE = "gpt-5.3-codex"
_CODEX_MODEL_MIGRATION_TARGET = "gpt-5.4"
_GEMINI_SETTINGS_PATH = Path(".gemini") / "settings.json"
_PROVIDER_STATE_LOCK_FILENAME = ".houmao-launch-policy.lock"


def run_provider_hook(
    *,
    hook_id: str,
    request: LaunchPolicyRequest,
    args: list[str] | None = None,
) -> None:
    """Dispatch one stable provider hook id."""

    if hook_id == "claude.ensure_api_key_approval":
        _claude_ensure_api_key_approval(request)
        return
    if hook_id == "claude.ensure_project_trust":
        _claude_ensure_project_trust(request)
        return
    if hook_id == "codex.canonicalize_unattended_launch_inputs":
        _codex_canonicalize_unattended_launch_inputs(args)
        return
    if hook_id == "codex.validate_credential_readiness":
        _codex_validate_credential_readiness(request)
        return
    if hook_id == "codex.ensure_project_trust":
        _codex_ensure_project_trust(request)
        return
    if hook_id == "codex.ensure_model_migration_state":
        _codex_ensure_model_migration_state(request)
        return
    if hook_id == "codex.append_unattended_cli_overrides":
        _codex_append_unattended_cli_overrides(args)
        return
    if hook_id == "gemini.canonicalize_unattended_launch_inputs":
        _gemini_canonicalize_unattended_launch_inputs(args)
        return
    if hook_id == "gemini.ensure_unattended_runtime_state":
        _gemini_ensure_unattended_runtime_state(request)
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

    _atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def set_json_key(
    *,
    path: Path,
    key_path: tuple[str, ...],
    value: Any,
    repair_invalid: bool = False,
) -> None:
    """Set one nested JSON key path while preserving unrelated state."""

    payload = (
        _load_json_state_with_template(path, repair_invalid=repair_invalid)
        if path.name == _CLAUDE_RUNTIME_STATE_FILENAME
        else _load_json_state_with_repair(path, repair_invalid=repair_invalid)
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


def delete_json_key(
    *,
    path: Path,
    key_path: tuple[str, ...],
    repair_invalid: bool = False,
) -> None:
    """Delete one nested JSON key path while preserving unrelated state."""

    payload = (
        _load_json_state_with_template(path, repair_invalid=repair_invalid)
        if path.name == _CLAUDE_RUNTIME_STATE_FILENAME
        else _load_json_state_with_repair(path, repair_invalid=repair_invalid)
    )
    _delete_nested_json_key(payload, key_path)
    write_json_state(path, payload)


def load_toml_state(path: Path, *, repair_invalid: bool = False) -> dict[str, Any]:
    """Load one TOML object from disk, defaulting to an empty object."""

    if not path.exists():
        return {}
    raw_text = path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return {}
    try:
        payload = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:
        if repair_invalid:
            return {}
        raise LaunchPolicyError(f"Malformed TOML state `{path}`: {exc}.") from exc
    if not isinstance(payload, dict):
        raise LaunchPolicyError(f"TOML state `{path}` must contain a top-level table.")
    return payload


def set_toml_key(
    *,
    path: Path,
    key_path: tuple[str, ...],
    value: str | bool | int,
    repair_invalid: bool = False,
) -> None:
    """Set one TOML key path using a minimal writer."""

    payload = load_toml_state(path, repair_invalid=repair_invalid)
    target = payload
    for key in key_path[:-1]:
        existing = target.get(key)
        if not isinstance(existing, dict):
            existing = {}
            target[key] = existing
        target = existing
    target[key_path[-1]] = value
    _atomic_write_text(path, _render_toml_mapping(payload) + "\n")


def _load_json_state_with_template(path: Path, *, repair_invalid: bool = False) -> dict[str, Any]:
    """Load one JSON object, seeding from Claude template when available."""

    if path.exists():
        return _load_json_state_with_repair(path, repair_invalid=repair_invalid)

    template_path = path.parent / _CLAUDE_STATE_TEMPLATE_FILENAME
    if template_path.exists():
        return _load_json_state_with_repair(template_path, repair_invalid=repair_invalid)
    return {}


def _load_json_state_with_repair(path: Path, *, repair_invalid: bool) -> dict[str, Any]:
    """Load one JSON object and optionally fall back to an empty baseline."""

    try:
        return load_json_state(path)
    except LaunchPolicyError:
        if not repair_invalid:
            raise
        return {}


@contextmanager
def provider_state_mutation_lock(home_path: Path) -> Iterator[None]:
    """Serialize provider-state mutation across one runtime home."""

    home_path.mkdir(parents=True, exist_ok=True)
    lock_path = home_path / _PROVIDER_STATE_LOCK_FILENAME
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_write_text(path: Path, text: str) -> None:
    """Write one text file through atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _claude_runtime_state_path(request: LaunchPolicyRequest) -> Path:
    """Return the runtime `.claude.json` path."""

    return request.home_path / _CLAUDE_RUNTIME_STATE_FILENAME


def _claude_settings_path(request: LaunchPolicyRequest) -> Path:
    """Return the runtime `settings.json` path."""

    return request.home_path / _CLAUDE_SETTINGS_FILENAME


def _codex_config_path(request: LaunchPolicyRequest) -> Path:
    """Return the runtime `config.toml` path."""

    return request.home_path / _CODEX_CONFIG_FILENAME


def _gemini_settings_path(request: LaunchPolicyRequest) -> Path:
    """Return the runtime Gemini settings path."""

    return request.home_path / _GEMINI_SETTINGS_PATH


def validate_codex_credential_readiness(
    *,
    home_path: Path,
    env: Mapping[str, str],
    error_factory: type[Exception] | None = None,
) -> None:
    """Validate that Codex has credentials for the resolved provider contract."""

    message = _codex_credential_readiness_error(home_path=home_path, env=env)
    if message is None:
        return
    factory = error_factory or LaunchPolicyError
    raise factory(message)


def ensure_codex_unattended_runtime_state(
    *,
    home_path: Path,
    working_directory: Path,
    repair_invalid: bool = False,
) -> None:
    """Force strategy-owned unattended Codex state into the runtime home."""

    config_path = home_path / _CODEX_CONFIG_FILENAME
    set_toml_key(
        path=config_path,
        key_path=("approval_policy",),
        value=_CODEX_UNATTENDED_APPROVAL_POLICY,
        repair_invalid=repair_invalid,
    )
    set_toml_key(
        path=config_path,
        key_path=("sandbox_mode",),
        value=_CODEX_UNATTENDED_SANDBOX_MODE,
        repair_invalid=repair_invalid,
    )
    set_toml_key(
        path=config_path,
        key_path=("notice", "hide_full_access_warning"),
        value=True,
        repair_invalid=repair_invalid,
    )
    set_toml_key(
        path=config_path,
        key_path=("projects", str(_resolve_codex_trust_target(working_directory)), "trust_level"),
        value="trusted",
        repair_invalid=repair_invalid,
    )
    _ensure_codex_model_migration_state(
        config_path=config_path,
        repair_invalid=repair_invalid,
    )


def canonicalize_codex_unattended_launch_args(args: list[str]) -> None:
    """Strip caller overrides that target Codex unattended-owned launch surfaces."""

    canonicalized: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        next_token = args[index + 1] if index + 1 < len(args) else None

        if token in {
            "--full-auto",
            "--dangerously-bypass-approvals-and-sandbox",
            "--yolo",
        }:
            index += 1
            continue
        if token.startswith("--ask-for-approval=") or token.startswith("--sandbox="):
            index += 1
            continue
        if token in {"-a", "--ask-for-approval", "-s", "--sandbox"}:
            index += 1
            if next_token is not None and not next_token.startswith("-"):
                index += 1
            continue
        if token.startswith("--config="):
            if _codex_override_targets_owned_surface(token.partition("=")[2]):
                index += 1
                continue
        if token in {"-c", "--config"} and next_token is not None:
            if _codex_override_targets_owned_surface(next_token):
                index += 2
                continue

        canonicalized.append(token)
        index += 1

    args[:] = canonicalized


def canonicalize_gemini_unattended_launch_args(args: list[str]) -> None:
    """Strip caller overrides that target Gemini unattended-owned launch surfaces."""

    canonicalized: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        next_token = args[index + 1] if index + 1 < len(args) else None

        if token in {"-y", "--yolo"}:
            index += 1
            continue
        if token.startswith("--approval-mode=") or token.startswith("--sandbox="):
            index += 1
            continue
        if token in {"--approval-mode", "--sandbox"}:
            index += 1
            if next_token is not None and not next_token.startswith("-"):
                index += 1
            continue

        canonicalized.append(token)
        index += 1

    args[:] = canonicalized


def _claude_ensure_api_key_approval(request: LaunchPolicyRequest) -> None:
    """Seed API-key approval state without storing the full key value."""

    api_key = request.env.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return

    state_path = _claude_runtime_state_path(request)
    payload = _load_json_state_with_template(
        state_path,
        repair_invalid=request.application_kind == "provider_start",
    )
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
    payload = _load_json_state_with_template(
        state_path,
        repair_invalid=request.application_kind == "provider_start",
    )
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


def _codex_canonicalize_unattended_launch_inputs(args: list[str] | None) -> None:
    """Canonicalize caller launch args for the Codex unattended strategy."""

    if args is None:
        return
    canonicalize_codex_unattended_launch_args(args)


def _gemini_canonicalize_unattended_launch_inputs(args: list[str] | None) -> None:
    """Canonicalize caller launch args for the Gemini unattended strategy."""

    if args is None:
        return
    canonicalize_gemini_unattended_launch_args(args)


def _codex_validate_credential_readiness(request: LaunchPolicyRequest) -> None:
    """Require either Codex auth state or an env-only provider contract."""

    validate_codex_credential_readiness(
        home_path=request.home_path,
        env=request.env,
    )


def _codex_ensure_project_trust(request: LaunchPolicyRequest) -> None:
    """Seed Codex project trust for the resolved working directory."""

    set_toml_key(
        path=_codex_config_path(request),
        key_path=(
            "projects",
            str(_resolve_codex_trust_target(request.working_directory)),
            "trust_level",
        ),
        value="trusted",
        repair_invalid=request.application_kind == "provider_start",
    )


def _codex_ensure_model_migration_state(request: LaunchPolicyRequest) -> None:
    """Seed Codex startup migration state for the current supported version."""

    _ensure_codex_model_migration_state(
        config_path=_codex_config_path(request),
        repair_invalid=request.application_kind == "provider_start",
    )


def _codex_append_unattended_cli_overrides(args: list[str] | None) -> None:
    """Append final Codex unattended CLI config overrides."""

    if args is None:
        return
    append_or_replace_codex_config_overrides(
        args,
        (
            CodexCliConfigOverride(
                ("approval_policy",),
                _CODEX_UNATTENDED_APPROVAL_POLICY,
            ),
            CodexCliConfigOverride(
                ("sandbox_mode",),
                _CODEX_UNATTENDED_SANDBOX_MODE,
            ),
            CodexCliConfigOverride(("notice", "hide_full_access_warning"), True),
        ),
    )


def _gemini_ensure_unattended_runtime_state(request: LaunchPolicyRequest) -> None:
    """Repair or sanitize Gemini runtime-home settings for unattended launch."""

    settings_path = _gemini_settings_path(request)
    if not settings_path.exists():
        return

    payload = _load_json_state_with_repair(
        settings_path,
        repair_invalid=request.application_kind == "provider_start",
    )
    _set_nested_json_value(payload, ("tools", "sandbox"), False)
    _delete_nested_json_key(payload, ("tools", "core"))
    _delete_nested_json_key(payload, ("tools", "exclude"))
    _set_nested_json_value(payload, ("security", "disableYoloMode"), False)
    _set_nested_json_value(payload, ("security", "toolSandboxing"), False)
    _set_nested_json_value(payload, ("admin", "secureModeEnabled"), False)
    _prune_empty_mappings(payload)
    write_json_state(settings_path, payload)


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


def _codex_credential_readiness_error(
    *,
    home_path: Path,
    env: Mapping[str, str],
) -> str | None:
    """Return one operator-facing Codex credential-readiness failure message."""

    if _has_usable_auth_json(home_path / _CODEX_AUTH_FILENAME):
        return None

    config_payload = load_toml_state(home_path / _CODEX_CONFIG_FILENAME)
    model_provider_name = config_payload.get("model_provider")
    if not isinstance(model_provider_name, str) or not model_provider_name.strip():
        return (
            "Codex credential readiness requires `auth.json` or a config-backed env-only "
            'provider with `requires_openai_auth = false` and `wire_api = "responses"`.'
        )

    providers = config_payload.get("model_providers")
    if not isinstance(providers, dict):
        return (
            "Codex credential readiness requires `auth.json` or a config-backed env-only "
            'provider with `requires_openai_auth = false` and `wire_api = "responses"`.'
        )

    provider_payload = providers.get(model_provider_name)
    if not isinstance(provider_payload, dict):
        return (
            "Codex credential readiness requires `auth.json` or a config-backed env-only "
            'provider with `requires_openai_auth = false` and `wire_api = "responses"`.'
        )

    requires_auth = provider_payload.get("requires_openai_auth", True)
    wire_api = provider_payload.get("wire_api")
    env_key = provider_payload.get("env_key", "OPENAI_API_KEY")

    if requires_auth is not False or wire_api != "responses":
        return (
            "Codex credential readiness requires `auth.json` or a config-backed env-only "
            'provider with `requires_openai_auth = false` and `wire_api = "responses"`.'
        )
    if not isinstance(env_key, str) or not env_key.strip():
        return "Codex env-only provider config must declare a non-empty `env_key`."
    if not env.get(env_key, "").strip():
        return f"Codex env-only provider `{model_provider_name}` requires env var `{env_key}`."
    return None


def _codex_override_targets_owned_surface(raw_override: str) -> bool:
    """Return whether one `-c key=value` override targets unattended-owned state."""

    key, separator, _ = raw_override.partition("=")
    if not separator:
        return False
    normalized = key.strip()
    if not normalized:
        return False
    if normalized in {
        "approval_policy",
        "sandbox_mode",
        "notice.hide_full_access_warning",
    }:
        return True
    if normalized.startswith("notice.model_migrations.") and normalized.endswith(
        _CODEX_MODEL_MIGRATION_SOURCE
    ):
        return True
    return normalized.startswith("projects.") and normalized.endswith(".trust_level")


def _set_nested_json_value(
    payload: dict[str, Any],
    key_path: tuple[str, ...],
    value: Any,
) -> None:
    """Set one nested JSON key while preserving sibling content."""

    target: dict[str, Any] = payload
    for key in key_path[:-1]:
        existing = target.get(key)
        if not isinstance(existing, dict):
            existing = {}
            target[key] = existing
        target = existing
    target[key_path[-1]] = value


def _delete_nested_json_key(payload: dict[str, Any], key_path: tuple[str, ...]) -> None:
    """Delete one nested JSON key when present."""

    target: dict[str, Any] | None = payload
    parents: list[tuple[dict[str, Any], str]] = []
    for key in key_path[:-1]:
        if not isinstance(target, dict):
            return
        existing = target.get(key)
        if not isinstance(existing, dict):
            return
        parents.append((target, key))
        target = existing
    if not isinstance(target, dict):
        return
    target.pop(key_path[-1], None)
    for parent, key in reversed(parents):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key, None)


def _prune_empty_mappings(payload: dict[str, Any]) -> None:
    """Remove empty nested mappings created during Gemini settings repair."""

    for value in payload.values():
        if isinstance(value, dict):
            _prune_empty_mappings(value)
    empty_keys = [key for key, value in payload.items() if isinstance(value, dict) and not value]
    for key in empty_keys:
        payload.pop(key, None)


def _ensure_codex_model_migration_state(*, config_path: Path, repair_invalid: bool) -> None:
    """Seed Codex model-migration state in the runtime config."""

    payload = load_toml_state(
        config_path,
        repair_invalid=repair_invalid,
    )
    model_value = payload.get("model")
    if model_value is None or model_value == _CODEX_MODEL_MIGRATION_SOURCE:
        set_toml_key(
            path=config_path,
            key_path=("model",),
            value=_CODEX_MODEL_MIGRATION_TARGET,
            repair_invalid=repair_invalid,
        )
    if model_value is None or model_value == _CODEX_MODEL_MIGRATION_SOURCE:
        set_toml_key(
            path=config_path,
            key_path=("notice", "model_migrations", _CODEX_MODEL_MIGRATION_SOURCE),
            value=_CODEX_MODEL_MIGRATION_TARGET,
            repair_invalid=repair_invalid,
        )


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
