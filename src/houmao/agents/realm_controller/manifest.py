"""Session manifest read/write helpers."""

from __future__ import annotations

import json
import uuid
import fcntl
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import hashlib
from typing import Any, Iterator

from pydantic import ValidationError

from houmao.execution.tmux import capture_tmux_socket_path, validate_tmux_socket_path

from .boundary_models import (
    LaunchPlanPayloadV1,
    RegistryLaunchAuthorityV1,
    SessionManifestAgentLaunchAuthorityV1,
    SessionManifestPayloadV4,
    format_pydantic_error,
)
from .errors import SessionManifestError
from .models import LaunchPlan, SessionManifestHandle
from houmao.agents.mailbox_runtime_models import MailboxChannel, MailboxResolvedConfig
from houmao.agents.realm_controller.native_surface import (
    TerminalNativeSurfaceV1,
    WebNativeSurfaceV1,
)

LAUNCH_PLAN_SCHEMA = "launch_plan.v2.schema.json"
SESSION_MANIFEST_SCHEMA = "session_manifest.v5.schema.json"
SESSION_MANIFEST_SCHEMA_VERSION = 5


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
        "system_prompt": _build_manifest_system_prompt_section(request=request),
        "backend_state": dict(request.backend_state),
        "native_surface": _build_manifest_native_surface(
            request=request, tmux_session_name=tmux_session_name
        ),
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
        "kimi_headless",
        "dsh_acp",
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


def _build_manifest_native_surface(
    *,
    request: SessionManifestRequest,
    tmux_session_name: str | None,
) -> dict[str, Any] | None:
    """Describe the native human interface independently of process supervision."""

    if request.launch_plan.backend == "dsh_web":
        identity = request.backend_state.get("web_identity")
        if not isinstance(identity, dict):
            raise SessionManifestError("DSH Web manifest requires a native execution binding")
        try:
            return WebNativeSurfaceV1(
                origin=request.backend_state["origin"],
                native_session_id=identity["native_session_id"],
            ).model_dump(mode="json")
        except (KeyError, ValidationError) as exc:
            raise SessionManifestError(
                "DSH Web manifest requires a verified token-free native surface"
            ) from exc
    if (
        request.launch_plan.backend in {"local_interactive", "cao_rest", "houmao_server_rest"}
        and tmux_session_name is not None
    ):
        return TerminalNativeSurfaceV1(
            tmux_session_name=tmux_session_name,
            pane_id=_optional_non_empty_str(request.backend_state.get("tmux_pane_id")),
        ).model_dump(mode="json")
    return None


def _build_manifest_system_prompt_section(
    *,
    request: SessionManifestRequest,
) -> dict[str, str]:
    """Build the read-only effective system-prompt manifest section."""

    prompt = request.launch_plan.role_injection.prompt
    return {
        "format": "text",
        "role_name": request.launch_plan.role_injection.role_name,
        "text": prompt,
        "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "source": "launch_plan.role_injection.prompt",
    }


def write_session_manifest(
    path: Path,
    payload: dict[str, Any],
    *,
    expected_web_identity: dict[str, Any] | None = None,
    expected_registry_generation_id: str | None = None,
) -> SessionManifestHandle:
    """Validate and persist a session manifest.

    Parameters
    ----------
    path:
        Target manifest file path.
    payload:
        Manifest payload.
    expected_web_identity:
        Exact previously published Web execution for an intentional lifecycle change.
    expected_registry_generation_id:
        Captured generation authorizing a deliberate execution-bound replacement.

    Returns
    -------
    SessionManifestHandle
        Saved manifest handle.
    """

    with _session_manifest_lock(path):
        proposed = dict(payload)
        if path.exists():
            current = load_session_manifest(path).payload
            _require_same_manifest_owner(current, proposed)
            current_binding = current["runtime"].get("execution_binding")
            if current_binding is not None:
                accepted_generations = {
                    proposed.get("registry_generation_id"),
                    expected_registry_generation_id,
                }
                if (
                    proposed["runtime"].get("execution_binding") != current_binding
                    or current.get("registry_generation_id") not in accepted_generations
                ):
                    raise SessionManifestError(
                        "Runtime execution generation changed; resolve the current manifest again"
                    )
            if current.get("backend") == "dsh_web":
                current_identity = current["backend_state"].get("web_identity")
                proposed_identity = proposed["backend_state"].get("web_identity")
                expected = expected_web_identity or proposed_identity
                if proposed.get("backend") != "dsh_web" or current_identity != expected:
                    raise SessionManifestError(
                        "DSH Web execution binding changed; resolve the current manifest again"
                    )
                if current_identity == proposed_identity:
                    proposed["backend_state"] = {
                        **proposed["backend_state"],
                        "turn_index": max(
                            current["backend_state"].get("turn_index", 0),
                            proposed["backend_state"].get("turn_index", 0),
                        ),
                    }
            launch_plan = dict(proposed["launch_plan"])
            launch_plan["mailboxes"] = current["launch_plan"]["mailboxes"]
            proposed["launch_plan"] = launch_plan
            _preserve_headless_server_authority(current, proposed)
        return _write_session_manifest_locked(path, proposed)


def _preserve_headless_server_authority(current: dict[str, Any], proposed: dict[str, Any]) -> None:
    """Preserve server-owned endpoint fields while the manifest lock is held."""

    if current.get("backend") not in {
        "codex_headless",
        "claude_headless",
        "kimi_headless",
        "dsh_acp",
        "dsh_web",
    }:
        return
    current_authority = current.get("gateway_authority")
    proposed_authority = proposed.get("gateway_authority")
    if not isinstance(current_authority, dict) or not isinstance(proposed_authority, dict):
        return
    merged_authority = dict(proposed_authority)
    for name in ("attach", "control"):
        current_endpoint = current_authority.get(name)
        proposed_endpoint = proposed_authority.get(name)
        if not isinstance(current_endpoint, dict) or not isinstance(proposed_endpoint, dict):
            continue
        merged_endpoint = dict(proposed_endpoint)
        for field_name in ("api_base_url", "managed_agent_ref"):
            merged_endpoint[field_name] = current_endpoint.get(field_name)
        merged_authority[name] = merged_endpoint
    proposed["gateway_authority"] = merged_authority


class MailboxBindingConflict(SessionManifestError):
    """A mailbox mutation targets stale slot or session authority."""


@contextmanager
def _session_manifest_lock(path: Path) -> Iterator[None]:
    """Serialize participating processes without holding a replaceable inode lock."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _require_same_manifest_owner(current: dict[str, Any], proposed: dict[str, Any]) -> None:
    """Prevent an ordinary writer replacing another logical agent's authority."""

    if current.get("agent_id") != proposed.get("agent_id"):
        raise MailboxBindingConflict("manifest agent_id differs from current authority")


def _write_session_manifest_locked(path: Path, payload: dict[str, Any]) -> SessionManifestHandle:
    """Validate, flush, and atomically replace a snapshot under its held lock."""

    validated = _validate_session_manifest_payload(
        payload, context=f"session_manifest.v5 validation failed for {path}"
    ).model_dump(mode="json")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(validated, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary_path.unlink(missing_ok=True)
    return SessionManifestHandle(path=path, payload=validated)


def mutate_session_mailbox_binding(
    path: Path,
    *,
    channel: MailboxChannel,
    expected_revision: str,
    binding: MailboxResolvedConfig | None,
    agent_id: str,
    session_id: str | None,
) -> SessionManifestHandle:
    """Compare and replace one slot, retaining the other and empty-slot revisions.

    Preparation and network work must finish before entering this function. A
    stale expected revision or session owner fails without modifying the file.
    """

    from houmao.agents.mailbox_runtime_support import mailboxes_resolved_config_from_payload

    with _session_manifest_lock(path):
        current = load_session_manifest(path).payload
        if current.get("agent_id") != agent_id or current["runtime"]["session_id"] != session_id:
            raise MailboxBindingConflict("mailbox mutation targets a different agent or session")
        mailboxes = mailboxes_resolved_config_from_payload(
            current["launch_plan"]["mailboxes"], manifest_path=path
        )
        if mailboxes.slot_for(channel).revision != expected_revision:
            raise MailboxBindingConflict("mailbox slot revision changed; resolve status again")
        if binding is not None and binding.agent_id != agent_id:
            raise MailboxBindingConflict("mailbox binding belongs to a different agent")
        updated = mailboxes.with_binding(channel, binding)
        current["launch_plan"]["mailboxes"] = updated.redacted_payload()
        return _write_session_manifest_locked(path, current)


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

    with _session_manifest_lock(path):
        handle = load_session_manifest(path)
        payload = dict(handle.payload)
        payload.update(updates)
        _require_same_manifest_owner(handle.payload, payload)
        if "launch_plan" in updates:
            launch_plan = dict(payload["launch_plan"])
            launch_plan["mailboxes"] = handle.payload["launch_plan"]["mailboxes"]
            payload["launch_plan"] = launch_plan
        return _write_session_manifest_locked(path, payload)


def update_session_server_gateway_authority(
    path: Path,
    *,
    agent_id: str,
    session_id: str | None,
    api_base_url: str,
    managed_agent_ref: str,
) -> SessionManifestHandle:
    """Merge server-owned routing fields without restoring stale runtime endpoint state."""

    with _session_manifest_lock(path):
        payload = load_session_manifest(path).payload
        if payload["agent_id"] != agent_id or payload["runtime"]["session_id"] != session_id:
            raise MailboxBindingConflict("gateway publication targets a different agent or session")
        authority = payload.get("gateway_authority")
        if not isinstance(authority, dict):
            raise SessionManifestError("gateway publication requires existing runtime authority")
        for name in ("attach", "control"):
            endpoint = authority.get(name)
            if not isinstance(endpoint, dict):
                raise SessionManifestError(
                    "gateway publication requires complete endpoint authority"
                )
            endpoint["api_base_url"] = api_base_url
            endpoint["managed_agent_ref"] = managed_agent_ref
        return _write_session_manifest_locked(path, payload)


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
        "kimi_headless",
        "dsh_acp",
        "dsh_web",
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
        raise SessionManifestError("Agent manifest is missing required resolved agent_id.")

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
        "execution_binding": (
            request.launch_plan.execution_binding.model_dump(mode="json")
            if request.launch_plan.execution_binding is not None
            else None
        ),
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
    selected_socket = request.backend_state.get(
        "tmux_socket_path"
    ) or request.launch_plan.metadata.get("tmux_socket_path")
    socket_path = (
        validate_tmux_socket_path(str(selected_socket))
        if selected_socket is not None
        else capture_tmux_socket_path()
    )
    return {
        "session_name": tmux_session_name,
        "socket_path": socket_path,
        "primary_window_index": "0",
        "primary_window_role": "supervisor_logs"
        if request.launch_plan.backend == "dsh_web"
        else "managed_agent_surface",
        "primary_window_name": request.backend_state.get("tmux_window_name"),
        "primary_window_id": _optional_non_empty_str(request.backend_state.get("tmux_window_id")),
        "primary_pane_id": _optional_non_empty_str(request.backend_state.get("tmux_pane_id")),
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
        "kimi_headless",
        "dsh_acp",
        "dsh_web",
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
            in {
                "local_interactive",
                "codex_headless",
                "claude_headless",
                "kimi_headless",
                "dsh_acp",
            }
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
        "primary_window_id": _optional_non_empty_str(request.backend_state.get("tmux_window_id")),
        "primary_pane_id": _optional_non_empty_str(request.backend_state.get("tmux_pane_id")),
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
        "kimi_headless",
        "dsh_acp",
        "dsh_web",
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
