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
    SessionManifestPayloadV2,
    SessionManifestPayloadV3,
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
    job_dir: Path | None = None
    agent_def_dir: Path | None = None
    agent_pid: int | None = None
    created_at_utc: str | None = None
    registry_generation_id: str | None = None
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"


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
    job_dir = _resolve_manifest_job_dir(
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
        "job_dir": str(job_dir.resolve()) if job_dir is not None else None,
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
        job_dir=job_dir,
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
    """Parse a manifest payload into a typed normalized Pydantic model."""

    schema_version = _schema_version_from_payload(payload)
    if schema_version == SESSION_MANIFEST_SCHEMA_VERSION:
        return _validate_session_manifest_payload(
            payload,
            context=f"session_manifest.v4 validation failed for {source}",
        )
    if schema_version == 3:
        legacy_v3_payload = _validate_session_manifest_payload_v3(
            payload,
            context=f"session_manifest.v3 validation failed for {source}",
        )
        upgraded_payload = _upgrade_v3_manifest_payload(payload=legacy_v3_payload)
        return _validate_session_manifest_payload(
            upgraded_payload,
            context=f"session_manifest.v4 validation failed for upgraded {source}",
        )
    if schema_version == 2:
        legacy_payload = _validate_session_manifest_payload_v2(
            payload,
            context=f"session_manifest.v2 validation failed for {source}",
        )
        upgraded_payload = _upgrade_legacy_manifest_payload(
            payload=legacy_payload,
            source=source,
        )
        return _validate_session_manifest_payload(
            upgraded_payload,
            context=f"session_manifest.v4 validation failed for upgraded {source}",
        )

    raise SessionManifestError(
        "Session manifest schema-version mismatch: "
        f"expected schema_version in {{2, 3, {SESSION_MANIFEST_SCHEMA_VERSION}}}, "
        f"got {schema_version!r} in `{source}`. "
        "Legacy CAO manifests are not supported; start a new session."
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
        raise SessionManifestError(format_pydantic_error(context, exc)) from exc


def _validate_session_manifest_payload_v3(
    payload: object, *, context: str
) -> SessionManifestPayloadV3:
    """Validate one legacy ``session_manifest.v3`` payload."""

    try:
        return SessionManifestPayloadV3.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(format_pydantic_error(context, exc)) from exc


def _validate_session_manifest_payload_v2(
    payload: object, *, context: str
) -> SessionManifestPayloadV2:
    """Validate one legacy ``session_manifest.v2`` payload."""

    try:
        return SessionManifestPayloadV2.model_validate(payload)
    except ValidationError as exc:
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


def _resolve_manifest_job_dir(
    *,
    request: SessionManifestRequest,
    agent_name: str | None,
    agent_id: str | None,
    tmux_session_name: str | None,
) -> Path | None:
    """Resolve the persisted job dir for one manifest request."""

    if request.job_dir is not None:
        return request.job_dir

    job_key = (
        _optional_non_empty_str(request.backend_state.get("session_id"))
        or _optional_non_empty_str(request.backend_state.get("session_name"))
        or tmux_session_name
        or agent_id
        or agent_name
    )
    if job_key is None:
        return None

    return (request.launch_plan.working_directory / ".houmao" / "jobs" / job_key).resolve()


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
    job_dir: Path | None,
) -> dict[str, Any]:
    """Build the normalized v4 runtime section."""

    agent_pid = request.agent_pid
    if agent_pid is None:
        raw_agent_pid = request.backend_state.get("pid")
        agent_pid = raw_agent_pid if isinstance(raw_agent_pid, int) and raw_agent_pid > 0 else None
    return {
        "session_id": session_id,
        "job_dir": str(job_dir.resolve()) if job_dir is not None else None,
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
            else None
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


def _upgrade_legacy_manifest_payload(
    *, payload: SessionManifestPayloadV2, source: str
) -> dict[str, Any]:
    """Upgrade one in-memory v2 manifest payload to the v4 shape."""

    upgraded = payload.model_dump(mode="json")
    upgraded["schema_version"] = 3
    upgraded["agent_name"] = None
    upgraded["agent_id"] = None
    upgraded["tmux_session_name"] = None
    upgraded["job_dir"] = _legacy_job_dir(payload=payload, source=source)
    upgraded["registry_launch_authority"] = "runtime"

    if payload.backend in {
        "local_interactive",
        "codex_headless",
        "claude_headless",
        "gemini_headless",
    }:
        tmux_session_name = _require_legacy_tmux_session_name(
            payload.backend_state,
            source=source,
        )
        upgraded["agent_name"] = tmux_session_name
        upgraded["agent_id"] = derive_agent_id_from_name(tmux_session_name)
        upgraded["tmux_session_name"] = tmux_session_name
        validated = _validate_session_manifest_payload_v3(
            upgraded,
            context=f"session_manifest.v3 validation failed for upgraded {source}",
        )
        return _upgrade_v3_manifest_payload(payload=validated)

    if payload.backend == "cao_rest":
        if payload.cao is None:
            raise SessionManifestError(f"Legacy CAO manifest is missing `cao` state in `{source}`.")
        tmux_session_name = payload.cao.session_name
        upgraded["agent_name"] = tmux_session_name
        upgraded["agent_id"] = derive_agent_id_from_name(tmux_session_name)
        upgraded["tmux_session_name"] = tmux_session_name
        validated = _validate_session_manifest_payload_v3(
            upgraded,
            context=f"session_manifest.v3 validation failed for upgraded {source}",
        )
        return _upgrade_v3_manifest_payload(payload=validated)

    validated = _validate_session_manifest_payload_v3(
        upgraded,
        context=f"session_manifest.v3 validation failed for upgraded {source}",
    )
    return _upgrade_v3_manifest_payload(payload=validated)


def _upgrade_v3_manifest_payload(*, payload: SessionManifestPayloadV3) -> dict[str, Any]:
    """Upgrade one in-memory v3 manifest payload to the v4 shape."""

    upgraded = payload.model_dump(mode="json")
    upgraded["schema_version"] = SESSION_MANIFEST_SCHEMA_VERSION
    session_id = (
        _optional_non_empty_str(payload.backend_state.get("session_id"))
        or _optional_non_empty_str(payload.backend_state.get("session_name"))
        or payload.tmux_session_name
        or payload.agent_id
        or payload.agent_name
    )
    upgraded["runtime"] = {
        "session_id": session_id,
        "job_dir": payload.job_dir,
        "agent_def_dir": None,
        "agent_pid": payload.codex.pid if payload.codex is not None else None,
        "registry_generation_id": payload.registry_generation_id,
        "registry_launch_authority": payload.registry_launch_authority,
    }
    upgraded["tmux"] = (
        {
            "session_name": payload.tmux_session_name,
            "primary_window_index": "0",
            "primary_window_role": "managed_agent_surface",
            "primary_window_name": _optional_non_empty_str(
                payload.backend_state.get("tmux_window_name")
            ),
        }
        if payload.tmux_session_name is not None
        else None
    )
    upgraded["interactive"] = {
        "turn_index": int(payload.backend_state.get("turn_index", 0)),
        "working_directory": str(
            payload.backend_state.get("working_directory", payload.working_directory)
        ),
        "role_bootstrap_applied": (
            bool(payload.backend_state.get("role_bootstrap_applied", False))
            if payload.backend
            in {"local_interactive", "codex_headless", "claude_headless", "gemini_headless"}
            else None
        ),
        "terminal_id": _optional_non_empty_str(payload.backend_state.get("terminal_id")),
        "parsing_mode": _optional_non_empty_str(payload.backend_state.get("parsing_mode")),
        "tmux_window_name": _optional_non_empty_str(payload.backend_state.get("tmux_window_name")),
    }
    upgraded["agent_launch_authority"] = (
        {
            "backend": payload.backend,
            "tool": payload.tool,
            "tmux_session_name": payload.tmux_session_name,
            "primary_window_index": "0",
            "working_directory": payload.working_directory,
            "session_id": session_id,
            "profile_name": _optional_non_empty_str(payload.backend_state.get("profile_name")),
            "profile_path": _optional_non_empty_str(payload.backend_state.get("profile_path")),
        }
        if payload.tmux_session_name is not None
        else None
    )
    attach = {
        "api_base_url": _optional_non_empty_str(payload.backend_state.get("api_base_url")),
        "managed_agent_ref": (
            _optional_non_empty_str(payload.backend_state.get("session_name"))
            if payload.backend == "houmao_server_rest"
            else None
        ),
        "terminal_id": _optional_non_empty_str(payload.backend_state.get("terminal_id")),
        "profile_name": _optional_non_empty_str(payload.backend_state.get("profile_name")),
        "profile_path": _optional_non_empty_str(payload.backend_state.get("profile_path")),
        "parsing_mode": _optional_non_empty_str(payload.backend_state.get("parsing_mode")),
        "tmux_window_name": _optional_non_empty_str(payload.backend_state.get("tmux_window_name")),
    }
    upgraded["gateway_authority"] = (
        {"attach": dict(attach), "control": dict(attach)}
        if payload.tmux_session_name is not None
        else None
    )
    return upgraded


def _require_legacy_tmux_session_name(backend_state: dict[str, Any], *, source: str) -> str:
    """Return the legacy persisted tmux session name from backend state."""

    tmux_session_name = backend_state.get("tmux_session_name")
    if not isinstance(tmux_session_name, str) or not tmux_session_name.strip():
        raise SessionManifestError(
            f"Legacy manifest `{source}` is missing non-empty `backend_state.tmux_session_name`."
        )
    return tmux_session_name.strip()


def _legacy_job_dir(*, payload: SessionManifestPayloadV2, source: str) -> str | None:
    """Best-effort job-dir derivation for addressed legacy manifests."""

    source_path = Path(source)
    if source_path.name != "manifest.json":
        return None

    session_root = runtime_owned_session_root_from_manifest_path(source_path)
    if session_root is None:
        return None

    session_id = session_root.name
    working_directory = Path(payload.working_directory).resolve()
    return str((working_directory / ".houmao" / "jobs" / session_id).resolve())


def _optional_non_empty_str(value: object) -> str | None:
    """Normalize one optional string value to a stripped non-empty string."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
