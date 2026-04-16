"""Session manifest read/write helpers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from houmao.agents.realm_controller.agent_identity import (
    derive_agent_id_from_name,
)

from .boundary_models import (
    LaunchPlanPayloadV1,
    RegistryLaunchAuthorityV1,
    SessionManifestAgentLaunchAuthorityV1,
    SessionManifestPayloadV4,
    format_pydantic_error,
)
from .errors import SessionManifestError
from .models import LaunchPlan, SessionManifestHandle

LAUNCH_PLAN_SCHEMA = "launch_plan.v1.schema.json"
SESSION_MANIFEST_SCHEMA = "session_manifest.v4.schema.json"
SESSION_MANIFEST_SCHEMA_VERSION = 4


@dataclass(frozen=True)
class SessionManifestRequest:
    """Inputs for creating a session manifest payload."""

    launch_plan: LaunchPlan
    role_name: str
    brain_manifest_path: Path
    backend_state: dict[str, Any]
    agent_name: str | None = None
    agent_id: str | None = None
    tmux_session_name: str | None = None
    session_id: str | None = None
    memory_root: Path | None = None
    memo_file: Path | None = None
    pages_dir: Path | None = None
    agent_def_dir: Path | None = None
    agent_pid: int | None = None
    created_at_utc: str | None = None
    registry_generation_id: str | None = None
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"
    agent_launch_authority: SessionManifestAgentLaunchAuthorityV1 | dict[str, Any] | None = None


def generate_session_id(prefix: str = "session") -> str:
    """Generate a stable session identifier.

    Parameters
    ----------
    prefix:
        Prefix for the generated identifier.

    Returns
    -------
    str
        Unique session id.
    """

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:8]}"


def default_session_root(runtime_root: Path, backend: str, session_id: str) -> Path:
    """Resolve the runtime-owned session root directory."""

    return runtime_root / "sessions" / backend / session_id


def default_manifest_path(runtime_root: Path, backend: str, session_id: str) -> Path:
    """Resolve a default manifest path under the runtime root."""

    return default_session_root(runtime_root, backend, session_id) / "manifest.json"


def runtime_owned_session_root_from_manifest_path(manifest_path: Path) -> Path | None:
    """Return the session root for runtime-owned manifests using the nested layout."""

    resolved = manifest_path.resolve()
    if resolved.name != "manifest.json":
        return None
    return resolved.parent


def build_session_manifest_payload(request: SessionManifestRequest) -> dict[str, Any]:
    """Build a schema-valid session manifest payload.

    Parameters
    ----------
    request:
        Manifest creation input.

    Returns
    -------
    dict[str, Any]
        Session manifest payload.
    """

    launch_payload = _validate_launch_plan_payload(
        request.launch_plan.redacted_payload(),
        context="launch_plan.v1 validation failed",
    ).model_dump(mode="json")
    agent_name, agent_id, tmux_session_name = _resolve_manifest_identity(request)
    session_id = _resolve_manifest_session_id(
        request=request,
        agent_name=agent_name,
        agent_id=agent_id,
        tmux_session_name=tmux_session_name,
    )

    payload: dict[str, Any] = {
        "schema_version": SESSION_MANIFEST_SCHEMA_VERSION,
        "backend": request.launch_plan.backend,
        "tool": request.launch_plan.tool,
        "role_name": request.role_name,
        "created_at_utc": request.created_at_utc or datetime.now(UTC).isoformat(timespec="seconds"),
        "working_directory": str(request.launch_plan.working_directory),
        "brain_manifest_path": str(request.brain_manifest_path),
        "agent_name": agent_name,
        "agent_id": agent_id,
        "tmux_session_name": tmux_session_name,
        "registry_generation_id": request.registry_generation_id,
        "registry_launch_authority": request.registry_launch_authority,
        "launch_plan": launch_payload,
        "launch_policy_provenance": (
            request.launch_plan.launch_policy_provenance.to_payload()
            if request.launch_plan.launch_policy_provenance is not None
            else None
        ),
        "backend_state": dict(request.backend_state),
    }

    if request.launch_plan.backend == "codex_app_server":
        payload["codex"] = {
            "thread_id": request.backend_state.get("thread_id"),
            "turn_index": int(request.backend_state.get("turn_index", 0)),
            "pid": request.backend_state.get("pid"),
            "process_started_at_utc": request.backend_state.get("process_started_at_utc"),
        }
    elif request.launch_plan.backend in {
        "codex_headless",
        "claude_headless",
        "gemini_headless",
    }:
        payload["headless"] = {
            "session_id": request.backend_state.get("session_id"),
            "turn_index": int(request.backend_state.get("turn_index", 0)),
            "role_bootstrap_applied": bool(
                request.backend_state.get("role_bootstrap_applied", False)
            ),
            "working_directory": str(
                request.backend_state.get(
                    "working_directory", request.launch_plan.working_directory
                )
            ),
            "resume_selection_kind": str(
                request.backend_state.get("resume_selection_kind", "none")
            ),
            "resume_selection_value": _optional_non_empty_str(
                request.backend_state.get("resume_selection_value")
            ),
        }
    elif request.launch_plan.backend == "local_interactive":
        payload["local_interactive"] = {
            "turn_index": int(request.backend_state.get("turn_index", 0)),
            "role_bootstrap_applied": bool(
                request.backend_state.get("role_bootstrap_applied", False)
            ),
            "working_directory": str(
                request.backend_state.get(
                    "working_directory", request.launch_plan.working_directory
                )
            ),
        }
    elif request.launch_plan.backend == "cao_rest":
        payload["cao"] = {
            "api_base_url": str(request.backend_state.get("api_base_url", "")),
            "session_name": str(request.backend_state.get("session_name", "")),
            "terminal_id": str(request.backend_state.get("terminal_id", "")),
            "profile_name": str(request.backend_state.get("profile_name", "")),
            "profile_path": str(request.backend_state.get("profile_path", "")),
            "tmux_window_name": request.backend_state.get("tmux_window_name"),
            "parsing_mode": str(request.backend_state.get("parsing_mode", "")),
            "turn_index": int(request.backend_state.get("turn_index", 0)),
        }
    elif request.launch_plan.backend == "houmao_server_rest":
        payload["houmao_server"] = {
            "api_base_url": str(request.backend_state.get("api_base_url", "")),
            "session_name": str(request.backend_state.get("session_name", "")),
            "terminal_id": str(request.backend_state.get("terminal_id", "")),
            "parsing_mode": str(request.backend_state.get("parsing_mode", "")),
            "tmux_window_name": request.backend_state.get("tmux_window_name"),
            "turn_index": int(request.backend_state.get("turn_index", 0)),
        }

    payload["runtime"] = _build_manifest_runtime_section(
        request=request,
        session_id=session_id,
    )
    payload["tmux"] = _build_manifest_tmux_section(
        request=request,
        tmux_session_name=tmux_session_name,
    )
    payload["interactive"] = _build_manifest_interactive_section(request=request)
    payload["agent_launch_authority"] = _build_manifest_agent_launch_authority(
        request=request,
        session_id=session_id,
        tmux_session_name=tmux_session_name,
    )
    payload["gateway_authority"] = _build_manifest_gateway_authority(request=request)

    return _validate_session_manifest_payload(
        payload,
        context="session_manifest.v4 validation failed",
    ).model_dump(mode="json")


def write_session_manifest(path: Path, payload: dict[str, Any]) -> SessionManifestHandle:
    """Validate and persist a session manifest.

    Parameters
    ----------
    path:
        Target manifest file path.
    payload:
        Manifest payload.

    Returns
    -------
    SessionManifestHandle
        Saved manifest handle.
    """

    validated = _validate_session_manifest_payload(
        payload,
        context=f"session_manifest.v4 validation failed for {path}",
    ).model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(validated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return SessionManifestHandle(path=path, payload=validated)


def load_session_manifest(path: Path) -> SessionManifestHandle:
    """Load and validate a session manifest payload.

    Parameters
    ----------
    path:
        Existing manifest file path.

    Returns
    -------
    SessionManifestHandle
        Loaded manifest handle.
    """

    if not path.is_file():
        raise SessionManifestError(f"Session manifest not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SessionManifestError(f"Invalid JSON in session manifest: {path}") from exc

    model = parse_session_manifest_payload(payload, source=str(path))

    return SessionManifestHandle(path=path, payload=model.model_dump(mode="json"))


def parse_session_manifest_payload(payload: object, *, source: str) -> SessionManifestPayloadV4:
    """Parse a current session manifest payload into a typed Pydantic model."""

    schema_version = _schema_version_from_payload(payload)
    if schema_version != SESSION_MANIFEST_SCHEMA_VERSION:
        raise SessionManifestError(
            "Session manifest schema-version mismatch: "
            f"expected schema_version={SESSION_MANIFEST_SCHEMA_VERSION}, "
            f"got {schema_version!r} in `{source}`. "
            "Start a fresh runtime session; in-memory upgrades from older manifests are "
            "not supported before 1.0."
        )
    return _validate_session_manifest_payload(
        payload,
        context=f"session_manifest.v4 validation failed for {source}",
    )


def update_session_manifest(path: Path, updates: dict[str, Any]) -> SessionManifestHandle:
    """Apply top-level updates to a persisted session manifest.

    Parameters
    ----------
    path:
        Existing manifest file path.
    updates:
        Top-level keys to merge into the manifest payload.

    Returns
    -------
    SessionManifestHandle
        Updated manifest handle.
    """

    handle = load_session_manifest(path)
    payload = dict(handle.payload)
    payload.update(updates)
    return write_session_manifest(path, payload)


def _validate_launch_plan_payload(payload: object, *, context: str) -> LaunchPlanPayloadV1:
    try:
        return LaunchPlanPayloadV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(format_pydantic_error(context, exc)) from exc


def _validate_session_manifest_payload(
    payload: object, *, context: str
) -> SessionManifestPayloadV4:
    try:
        return SessionManifestPayloadV4.model_validate(payload)
    except ValidationError as exc:
        if "gateway_authority is required" in str(exc):
            raise SessionManifestError(
                f"{format_pydantic_error(context, exc)}. Start a fresh runtime session; "
                "legacy backend-specific authority synthesis is not supported before 1.0."
            ) from exc
        raise SessionManifestError(format_pydantic_error(context, exc)) from exc


def _resolve_manifest_identity(
    request: SessionManifestRequest,
) -> tuple[str | None, str | None, str | None]:
    """Resolve manifest identity metadata from explicit values and backend state."""

    agent_name = request.agent_name
    tmux_session_name = request.tmux_session_name

    if request.launch_plan.backend in {
        "codex_headless",
        "claude_headless",
        "gemini_headless",
    }:
        if tmux_session_name is None:
            tmux_session_name = _optional_non_empty_str(
                request.backend_state.get("tmux_session_name")
            )
    elif request.launch_plan.backend == "cao_rest":
        backend_session_name = _optional_non_empty_str(request.backend_state.get("session_name"))
        if tmux_session_name is None:
            tmux_session_name = backend_session_name
    elif request.launch_plan.backend == "houmao_server_rest":
        backend_session_name = _optional_non_empty_str(request.backend_state.get("session_name"))
        if tmux_session_name is None:
            tmux_session_name = backend_session_name

    if tmux_session_name is None:
        tmux_session_name = agent_name

    agent_id = request.agent_id
    if agent_id is None and agent_name is not None:
        agent_id = derive_agent_id_from_name(agent_name)

    return agent_name, agent_id, tmux_session_name


def _resolve_manifest_session_id(
    *,
    request: SessionManifestRequest,
    agent_name: str | None,
    agent_id: str | None,
    tmux_session_name: str | None,
) -> str | None:
    """Resolve the persisted session identifier for one manifest request."""

    return (
        request.session_id
        or _optional_non_empty_str(request.backend_state.get("session_id"))
        or _optional_non_empty_str(request.backend_state.get("session_name"))
        or tmux_session_name
        or agent_id
        or agent_name
    )


def _build_manifest_runtime_section(
    *,
    request: SessionManifestRequest,
    session_id: str | None,
) -> dict[str, Any]:
    """Build the normalized v4 runtime section."""

    agent_pid = request.agent_pid
    if agent_pid is None:
        raw_agent_pid = request.backend_state.get("pid")
        agent_pid = raw_agent_pid if isinstance(raw_agent_pid, int) and raw_agent_pid > 0 else None
    return {
        "session_id": session_id,
        "memory_root": (
            str(request.memory_root.resolve()) if request.memory_root is not None else None
        ),
        "memo_file": str(request.memo_file.resolve()) if request.memo_file is not None else None,
        "pages_dir": (str(request.pages_dir.resolve()) if request.pages_dir is not None else None),
        "agent_def_dir": (
            str(request.agent_def_dir.resolve()) if request.agent_def_dir is not None else None
        ),
        "agent_pid": agent_pid,
        "registry_generation_id": request.registry_generation_id,
        "registry_launch_authority": request.registry_launch_authority,
    }


def _build_manifest_tmux_section(
    *,
    request: SessionManifestRequest,
    tmux_session_name: str | None,
) -> dict[str, Any] | None:
    """Build the normalized v4 tmux section for tmux-backed sessions."""

    if tmux_session_name is None:
        return None
    return {
        "session_name": tmux_session_name,
        "primary_window_index": "0",
        "primary_window_role": "managed_agent_surface",
        "primary_window_name": request.backend_state.get("tmux_window_name"),
    }


def _build_manifest_interactive_section(
    *,
    request: SessionManifestRequest,
) -> dict[str, Any] | None:
    """Build the normalized v4 interactive/control section."""

    if request.launch_plan.backend not in {
        "local_interactive",
        "codex_headless",
        "claude_headless",
        "gemini_headless",
        "cao_rest",
        "houmao_server_rest",
    }:
        return None
    return {
        "turn_index": int(request.backend_state.get("turn_index", 0)),
        "working_directory": str(
            request.backend_state.get("working_directory", request.launch_plan.working_directory)
        ),
        "role_bootstrap_applied": (
            bool(request.backend_state.get("role_bootstrap_applied", False))
            if request.launch_plan.backend
            in {"local_interactive", "codex_headless", "claude_headless", "gemini_headless"}
            else None
        ),
        "terminal_id": _optional_non_empty_str(request.backend_state.get("terminal_id")),
        "parsing_mode": _optional_non_empty_str(request.backend_state.get("parsing_mode")),
        "tmux_window_name": _optional_non_empty_str(request.backend_state.get("tmux_window_name")),
    }


def _build_manifest_agent_launch_authority(
    *,
    request: SessionManifestRequest,
    session_id: str | None,
    tmux_session_name: str | None,
) -> dict[str, Any] | None:
    """Build the normalized v4 relaunch posture section."""

    if request.agent_launch_authority is not None:
        authority = request.agent_launch_authority
        if isinstance(authority, SessionManifestAgentLaunchAuthorityV1):
            return authority.model_dump(mode="json")
        validated = SessionManifestAgentLaunchAuthorityV1.model_validate(authority)
        return validated.model_dump(mode="json")
    if tmux_session_name is None:
        return None
    return {
        "backend": request.launch_plan.backend,
        "tool": request.launch_plan.tool,
        "tmux_session_name": tmux_session_name,
        "primary_window_index": "0",
        "working_directory": str(request.launch_plan.working_directory),
        "session_id": session_id,
        "profile_name": _optional_non_empty_str(request.backend_state.get("profile_name")),
        "profile_path": _optional_non_empty_str(request.backend_state.get("profile_path")),
        "posture_kind": "runtime_launch_plan",
    }


def _build_manifest_gateway_authority(
    *,
    request: SessionManifestRequest,
) -> dict[str, Any] | None:
    """Build the normalized v4 gateway attach/control authority section."""

    if request.launch_plan.backend not in {
        "local_interactive",
        "codex_headless",
        "claude_headless",
        "gemini_headless",
        "cao_rest",
        "houmao_server_rest",
    }:
        return None

    api_base_url = _optional_non_empty_str(request.backend_state.get("api_base_url"))
    terminal_id = _optional_non_empty_str(request.backend_state.get("terminal_id"))
    profile_name = _optional_non_empty_str(request.backend_state.get("profile_name"))
    profile_path = _optional_non_empty_str(request.backend_state.get("profile_path"))
    parsing_mode = _optional_non_empty_str(request.backend_state.get("parsing_mode"))
    tmux_window_name = _optional_non_empty_str(request.backend_state.get("tmux_window_name"))
    attach = {
        "api_base_url": api_base_url,
        "managed_agent_ref": (
            _optional_non_empty_str(request.backend_state.get("session_name"))
            if request.launch_plan.backend == "houmao_server_rest"
            else _optional_non_empty_str(request.backend_state.get("managed_agent_ref"))
        ),
        "terminal_id": terminal_id,
        "profile_name": profile_name,
        "profile_path": profile_path,
        "parsing_mode": parsing_mode,
        "tmux_window_name": tmux_window_name,
    }
    return {
        "attach": dict(attach),
        "control": dict(attach),
    }


def _schema_version_from_payload(payload: object) -> int | None:
    """Read the manifest schema version when the payload is a mapping."""

    if not isinstance(payload, dict):
        return None
    schema_version = payload.get("schema_version")
    return schema_version if isinstance(schema_version, int) else None


def _optional_non_empty_str(value: object) -> str | None:
    """Normalize one optional string value to a stripped non-empty string."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
