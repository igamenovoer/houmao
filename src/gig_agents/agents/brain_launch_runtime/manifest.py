"""Session manifest read/write helpers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .boundary_models import (
    LaunchPlanPayloadV1,
    SessionManifestPayloadV2,
    format_pydantic_error,
)
from .errors import SessionManifestError
from .models import LaunchPlan, SessionManifestHandle

LAUNCH_PLAN_SCHEMA = "launch_plan.v1.schema.json"
SESSION_MANIFEST_SCHEMA = "session_manifest.v2.schema.json"
SESSION_MANIFEST_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class SessionManifestRequest:
    """Inputs for creating a session manifest payload."""

    launch_plan: LaunchPlan
    role_name: str
    brain_manifest_path: Path
    backend_state: dict[str, Any]
    created_at_utc: str | None = None


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


def default_manifest_path(runtime_root: Path, backend: str, session_id: str) -> Path:
    """Resolve a default manifest path under the runtime root."""

    return runtime_root / "sessions" / backend / f"{session_id}.json"


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

    payload: dict[str, Any] = {
        "schema_version": SESSION_MANIFEST_SCHEMA_VERSION,
        "backend": request.launch_plan.backend,
        "tool": request.launch_plan.tool,
        "role_name": request.role_name,
        "created_at_utc": request.created_at_utc
        or datetime.now(UTC).isoformat(timespec="seconds"),
        "working_directory": str(request.launch_plan.working_directory),
        "brain_manifest_path": str(request.brain_manifest_path),
        "launch_plan": launch_payload,
        "backend_state": dict(request.backend_state),
    }

    if request.launch_plan.backend == "codex_app_server":
        payload["codex"] = {
            "thread_id": request.backend_state.get("thread_id"),
            "turn_index": int(request.backend_state.get("turn_index", 0)),
            "pid": request.backend_state.get("pid"),
            "process_started_at_utc": request.backend_state.get(
                "process_started_at_utc"
            ),
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
    elif request.launch_plan.backend == "cao_rest":
        payload["cao"] = {
            "api_base_url": str(request.backend_state.get("api_base_url", "")),
            "session_name": str(request.backend_state.get("session_name", "")),
            "terminal_id": str(request.backend_state.get("terminal_id", "")),
            "profile_name": str(request.backend_state.get("profile_name", "")),
            "profile_path": str(request.backend_state.get("profile_path", "")),
            "parsing_mode": str(request.backend_state.get("parsing_mode", "")),
            "turn_index": int(request.backend_state.get("turn_index", 0)),
        }

    return _validate_session_manifest_payload(
        payload,
        context="session_manifest.v2 validation failed",
    ).model_dump(mode="json")


def write_session_manifest(
    path: Path, payload: dict[str, Any]
) -> SessionManifestHandle:
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
        context=f"session_manifest.v2 validation failed for {path}",
    ).model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(validated, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
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

    _ensure_session_manifest_schema_version(payload, source=str(path))
    model = _validate_session_manifest_payload(
        payload,
        context=f"session_manifest.v2 validation failed for {path}",
    )

    return SessionManifestHandle(path=path, payload=model.model_dump(mode="json"))


def parse_session_manifest_payload(
    payload: object, *, source: str
) -> SessionManifestPayloadV2:
    """Parse a manifest payload into a typed Pydantic model."""

    _ensure_session_manifest_schema_version(payload, source=source)
    return _validate_session_manifest_payload(
        payload,
        context=f"session_manifest.v2 validation failed for {source}",
    )


def update_session_manifest(
    path: Path, updates: dict[str, Any]
) -> SessionManifestHandle:
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


def _validate_launch_plan_payload(
    payload: object, *, context: str
) -> LaunchPlanPayloadV1:
    try:
        return LaunchPlanPayloadV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(format_pydantic_error(context, exc)) from exc


def _validate_session_manifest_payload(
    payload: object, *, context: str
) -> SessionManifestPayloadV2:
    try:
        return SessionManifestPayloadV2.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(format_pydantic_error(context, exc)) from exc


def _ensure_session_manifest_schema_version(payload: object, *, source: str) -> None:
    if not isinstance(payload, dict):
        return

    schema_version = payload.get("schema_version")
    if schema_version == SESSION_MANIFEST_SCHEMA_VERSION:
        return

    raise SessionManifestError(
        "Session manifest schema-version mismatch: "
        f"expected schema_version={SESSION_MANIFEST_SCHEMA_VERSION}, "
        f"got {schema_version!r} in `{source}`. "
        "Legacy CAO manifests are not supported; start a new session."
    )
