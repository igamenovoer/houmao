"""Gateway storage, discovery, and capability-publication helpers."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Mapping, Protocol, Sequence, cast

from pydantic import ValidationError

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.gateway_models import (
    GATEWAY_PROTOCOL_VERSION,
    BlueprintGatewayDefaults,
    GatewayAttachBackendMetadataCaoV1,
    GatewayAttachBackendMetadataHoumaoServerV1,
    GatewayAttachBackendMetadataHeadlessV1,
    GatewayAttachContractV1,
    GatewayCurrentInstanceV1,
    GatewayDesiredConfigV1,
    GatewayHealthResponseV1,
    GatewayHost,
    GatewayJsonObject,
    GatewayJsonValue,
    GatewayAdmissionState,
    GatewayMailNotifierStatusV1,
    GatewayProtocolVersion,
    GatewayStatusV1,
    GatewayExecutionState,
    format_gateway_validation_error,
)
from houmao.agents.realm_controller.manifest import (
    default_session_root,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.agents.realm_controller.models import BackendKind, CaoParsingMode

AGENT_GATEWAY_ATTACH_PATH_ENV_VAR = "AGENTSYS_GATEWAY_ATTACH_PATH"
AGENT_GATEWAY_ROOT_ENV_VAR = "AGENTSYS_GATEWAY_ROOT"
AGENT_GATEWAY_HOST_ENV_VAR = "AGENTSYS_AGENT_GATEWAY_HOST"
AGENT_GATEWAY_PORT_ENV_VAR = "AGENTSYS_AGENT_GATEWAY_PORT"
AGENT_GATEWAY_STATE_PATH_ENV_VAR = "AGENTSYS_GATEWAY_STATE_PATH"
AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR = "AGENTSYS_GATEWAY_PROTOCOL_VERSION"

_LIVE_GATEWAY_ENV_VARS: tuple[str, ...] = (
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
)
_UNSET = object()


@dataclass(frozen=True)
class GatewayPaths:
    """Resolved filesystem layout for one session-owned gateway root."""

    session_root: Path
    gateway_root: Path
    attach_path: Path
    protocol_version_path: Path
    desired_config_path: Path
    state_path: Path
    queue_path: Path
    events_path: Path
    logs_dir: Path
    run_dir: Path
    current_instance_path: Path
    pid_path: Path
    log_path: Path


@dataclass(frozen=True)
class GatewayCapabilityPublication:
    """Inputs required to publish gateway capability for a tmux-backed session."""

    manifest_path: Path
    backend: BackendKind
    tool: str
    session_id: str
    tmux_session_name: str
    working_directory: Path
    backend_state: GatewayJsonObject
    agent_def_dir: Path | None = None
    blueprint_gateway_defaults: BlueprintGatewayDefaults | None = None


@dataclass(frozen=True)
class GatewayLiveBindings:
    """Live gateway listener bindings discovered from tmux env state."""

    host: GatewayHost
    port: int
    state_path: Path
    protocol_version: GatewayProtocolVersion


@dataclass(frozen=True)
class GatewayMailNotifierRecord:
    """Durable gateway-owned notifier configuration and runtime state."""

    enabled: bool
    interval_seconds: int | None
    last_poll_at_utc: str | None
    last_notification_at_utc: str | None
    last_notified_digest: str | None
    last_error: str | None


GatewayNotifierAuditOutcome = Literal[
    "empty",
    "dedup_skip",
    "busy_skip",
    "enqueued",
    "poll_error",
]


@dataclass(frozen=True)
class GatewayNotifierAuditUnreadMessage:
    """Compact unread-message summary stored in notifier audit history."""

    message_ref: str
    thread_ref: str | None
    created_at_utc: str
    subject: str


@dataclass(frozen=True)
class GatewayNotifierAuditRecord:
    """Durable per-poll gateway notifier audit record."""

    audit_id: int
    poll_time_utc: str
    unread_count: int | None
    unread_digest: str | None
    unread_summary: tuple[GatewayNotifierAuditUnreadMessage, ...]
    request_admission: GatewayAdmissionState | None
    active_execution: GatewayExecutionState | None
    queue_depth: int | None
    outcome: GatewayNotifierAuditOutcome
    enqueued_request_id: str | None
    detail: str | None


class _TmuxEnvSetter(Protocol):
    """Callable protocol for tmux session environment publishers."""

    def __call__(self, *, session_name: str, env_vars: dict[str, str]) -> None:
        """Publish environment variables into one tmux session."""


def default_gateway_paths(
    *,
    runtime_root: Path,
    backend: str,
    session_id: str,
) -> GatewayPaths:
    """Return the session-owned gateway layout for a runtime-owned session."""

    session_root = default_session_root(runtime_root, backend, session_id).resolve()
    return gateway_paths_from_session_root(session_root=session_root)


def gateway_paths_from_manifest_path(manifest_path: Path) -> GatewayPaths | None:
    """Return gateway paths when the manifest uses the runtime-owned session layout."""

    session_root = runtime_owned_session_root_from_manifest_path(manifest_path.resolve())
    if session_root is None:
        return None
    return gateway_paths_from_session_root(session_root=session_root)


def gateway_paths_from_session_root(*, session_root: Path) -> GatewayPaths:
    """Return gateway layout paths rooted under one runtime-owned session directory."""

    gateway_root = (session_root / "gateway").resolve()
    run_dir = (gateway_root / "run").resolve()
    logs_dir = (gateway_root / "logs").resolve()
    return GatewayPaths(
        session_root=session_root.resolve(),
        gateway_root=gateway_root,
        attach_path=(gateway_root / "attach.json").resolve(),
        protocol_version_path=(gateway_root / "protocol-version.txt").resolve(),
        desired_config_path=(gateway_root / "desired-config.json").resolve(),
        state_path=(gateway_root / "state.json").resolve(),
        queue_path=(gateway_root / "queue.sqlite").resolve(),
        events_path=(gateway_root / "events.jsonl").resolve(),
        logs_dir=logs_dir,
        run_dir=run_dir,
        current_instance_path=(run_dir / "current-instance.json").resolve(),
        pid_path=(run_dir / "gateway.pid").resolve(),
        log_path=(logs_dir / "gateway.log").resolve(),
    )


def ensure_gateway_capability(
    request: GatewayCapabilityPublication,
) -> GatewayPaths:
    """Materialize stable gateway assets for a runtime-owned tmux session."""

    paths = require_gateway_paths_for_runtime_owned_manifest(request.manifest_path)
    paths.gateway_root.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    _write_text(paths.protocol_version_path, GATEWAY_PROTOCOL_VERSION + "\n")
    _ensure_queue_database(paths.queue_path)
    if not paths.events_path.exists():
        _write_text(paths.events_path, "")

    attach_contract = build_attach_contract(request=request)
    write_attach_contract(paths.attach_path, attach_contract)

    desired_defaults = GatewayDesiredConfigV1(
        desired_host=request.blueprint_gateway_defaults.host
        if request.blueprint_gateway_defaults is not None
        else None,
        desired_port=request.blueprint_gateway_defaults.port
        if request.blueprint_gateway_defaults is not None
        else None,
    )
    if paths.desired_config_path.is_file():
        existing = load_gateway_desired_config(paths.desired_config_path)
        desired_defaults = GatewayDesiredConfigV1(
            desired_host=existing.desired_host
            if existing.desired_host is not None
            else desired_defaults.desired_host,
            desired_port=existing.desired_port
            if existing.desired_port is not None
            else desired_defaults.desired_port,
        )
    write_gateway_desired_config(paths.desired_config_path, desired_defaults)

    status = _status_to_seed(paths=paths, attach_contract=attach_contract)
    if status is not None:
        write_gateway_status(paths.state_path, status)
    return paths


def publish_stable_gateway_env(
    *,
    session_name: str,
    attach_path: Path,
    gateway_root: Path,
    set_env: _TmuxEnvSetter,
) -> None:
    """Publish stable gateway attachability pointers into tmux session env."""

    set_env(
        session_name=session_name,
        env_vars={
            AGENT_GATEWAY_ATTACH_PATH_ENV_VAR: str(attach_path.resolve()),
            AGENT_GATEWAY_ROOT_ENV_VAR: str(gateway_root.resolve()),
        },
    )


def publish_live_gateway_env(
    *,
    session_name: str,
    live_bindings: GatewayLiveBindings,
    set_env: _TmuxEnvSetter,
) -> None:
    """Publish live gateway listener bindings into tmux session env."""

    set_env(
        session_name=session_name,
        env_vars={
            AGENT_GATEWAY_HOST_ENV_VAR: live_bindings.host,
            AGENT_GATEWAY_PORT_ENV_VAR: str(live_bindings.port),
            AGENT_GATEWAY_STATE_PATH_ENV_VAR: str(live_bindings.state_path.resolve()),
            AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR: live_bindings.protocol_version,
        },
    )


def live_gateway_env_var_names() -> tuple[str, ...]:
    """Return the live gateway env variable names."""

    return _LIVE_GATEWAY_ENV_VARS


def build_attach_contract(
    *,
    request: GatewayCapabilityPublication,
) -> GatewayAttachContractV1:
    """Build a strict attach contract from runtime-owned session state."""

    backend_metadata: (
        GatewayAttachBackendMetadataHeadlessV1
        | GatewayAttachBackendMetadataCaoV1
        | GatewayAttachBackendMetadataHoumaoServerV1
    )
    if request.backend == "cao_rest":
        backend_metadata = GatewayAttachBackendMetadataCaoV1(
            api_base_url=_require_backend_state_string(
                request.backend_state,
                key="api_base_url",
            ),
            terminal_id=_require_backend_state_string(
                request.backend_state,
                key="terminal_id",
            ),
            profile_name=_require_backend_state_string(
                request.backend_state,
                key="profile_name",
            ),
            profile_path=_require_backend_state_string(
                request.backend_state,
                key="profile_path",
            ),
            parsing_mode=cast(
                CaoParsingMode,
                _require_backend_state_string(
                    request.backend_state,
                    key="parsing_mode",
                ),
            ),
            tmux_window_name=_optional_backend_state_string(
                request.backend_state,
                key="tmux_window_name",
            ),
        )
    elif request.backend == "houmao_server_rest":
        backend_metadata = GatewayAttachBackendMetadataHoumaoServerV1(
            api_base_url=_require_backend_state_string(
                request.backend_state,
                key="api_base_url",
            ),
            session_name=_require_backend_state_string(
                request.backend_state,
                key="session_name",
            ),
            terminal_id=_require_backend_state_string(
                request.backend_state,
                key="terminal_id",
            ),
            parsing_mode=cast(
                CaoParsingMode,
                _require_backend_state_string(
                    request.backend_state,
                    key="parsing_mode",
                ),
            ),
            tmux_window_name=_optional_backend_state_string(
                request.backend_state,
                key="tmux_window_name",
            ),
        )
    else:
        backend_metadata = GatewayAttachBackendMetadataHeadlessV1(
            session_id=_optional_backend_state_string(
                request.backend_state,
                key="session_id",
            ),
            tool=request.tool,
        )

    desired_host = None
    desired_port = None
    if request.blueprint_gateway_defaults is not None:
        desired_host = request.blueprint_gateway_defaults.host
        desired_port = request.blueprint_gateway_defaults.port

    return GatewayAttachContractV1(
        attach_identity=request.session_id,
        backend=request.backend,
        tmux_session_name=request.tmux_session_name,
        working_directory=str(request.working_directory.resolve()),
        backend_metadata=backend_metadata,
        manifest_path=str(request.manifest_path.resolve()),
        agent_def_dir=str(request.agent_def_dir.resolve())
        if request.agent_def_dir is not None
        else None,
        runtime_session_id=request.session_id,
        desired_host=desired_host,
        desired_port=desired_port,
    )


def require_gateway_paths_for_runtime_owned_manifest(manifest_path: Path) -> GatewayPaths:
    """Return gateway paths or raise when a manifest is not runtime-owned."""

    paths = gateway_paths_from_manifest_path(manifest_path)
    if paths is None:
        raise SessionManifestError(
            "Gateway capability publication requires a runtime-owned session manifest "
            f"layout rooted at `<session-root>/manifest.json`, got `{manifest_path}`."
        )
    return paths


def load_attach_contract(path: Path) -> GatewayAttachContractV1:
    """Load and validate a strict attach contract."""

    payload = _load_json_mapping(path, missing_prefix="Gateway attach contract not found")
    try:
        return GatewayAttachContractV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_gateway_validation_error(
                f"Gateway attach contract validation failed for {path}",
                exc,
            )
        ) from exc


def write_attach_contract(path: Path, contract: GatewayAttachContractV1) -> None:
    """Persist an attach contract atomically."""

    _write_json(path, contract.model_dump(mode="json"))


def load_gateway_status(path: Path) -> GatewayStatusV1:
    """Load a strict gateway status snapshot."""

    payload = _load_json_mapping(path, missing_prefix="Gateway state not found")
    try:
        return GatewayStatusV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_gateway_validation_error(
                f"Gateway status validation failed for {path}",
                exc,
            )
        ) from exc


def write_gateway_status(path: Path, status: GatewayStatusV1) -> None:
    """Persist the current gateway status atomically."""

    _write_json(path, status.model_dump(mode="json"))


def load_gateway_desired_config(path: Path) -> GatewayDesiredConfigV1:
    """Load persisted desired listener configuration."""

    payload = _load_json_mapping(path, missing_prefix="Gateway desired config not found")
    try:
        return GatewayDesiredConfigV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_gateway_validation_error(
                f"Gateway desired config validation failed for {path}",
                exc,
            )
        ) from exc


def write_gateway_desired_config(path: Path, config: GatewayDesiredConfigV1) -> None:
    """Persist desired listener configuration atomically."""

    _write_json(path, config.model_dump(mode="json"))


def load_gateway_current_instance(path: Path) -> GatewayCurrentInstanceV1:
    """Load current-instance run metadata."""

    payload = _load_json_mapping(path, missing_prefix="Gateway run state not found")
    try:
        return GatewayCurrentInstanceV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_gateway_validation_error(
                f"Gateway run-state validation failed for {path}",
                exc,
            )
        ) from exc


def write_gateway_current_instance(path: Path, payload: GatewayCurrentInstanceV1) -> None:
    """Persist current-instance run metadata atomically."""

    _write_json(path, payload.model_dump(mode="json"))
    _write_text(path.parent / "gateway.pid", f"{payload.pid}\n")


def delete_gateway_current_instance(paths: GatewayPaths) -> None:
    """Remove ephemeral current-instance files if they exist."""

    for candidate in (paths.current_instance_path, paths.pid_path):
        try:
            candidate.unlink()
        except FileNotFoundError:
            continue


def read_gateway_mail_notifier_record(sqlite_path: Path) -> GatewayMailNotifierRecord:
    """Load the durable gateway notifier record."""

    with sqlite3.connect(sqlite_path) as connection:
        return _read_gateway_mail_notifier_record(connection)


def write_gateway_mail_notifier_record(
    sqlite_path: Path,
    *,
    enabled: bool | object = _UNSET,
    interval_seconds: int | None | object = _UNSET,
    last_poll_at_utc: str | None | object = _UNSET,
    last_notification_at_utc: str | None | object = _UNSET,
    last_notified_digest: str | None | object = _UNSET,
    last_error: str | None | object = _UNSET,
) -> GatewayMailNotifierRecord:
    """Persist selected notifier fields and return the resulting durable record."""

    with sqlite3.connect(sqlite_path) as connection:
        record = _read_gateway_mail_notifier_record(connection)
        updated = GatewayMailNotifierRecord(
            enabled=record.enabled if enabled is _UNSET else bool(enabled),
            interval_seconds=(
                record.interval_seconds
                if interval_seconds is _UNSET
                else cast(int | None, interval_seconds)
            ),
            last_poll_at_utc=(
                record.last_poll_at_utc
                if last_poll_at_utc is _UNSET
                else cast(str | None, last_poll_at_utc)
            ),
            last_notification_at_utc=(
                record.last_notification_at_utc
                if last_notification_at_utc is _UNSET
                else cast(str | None, last_notification_at_utc)
            ),
            last_notified_digest=(
                record.last_notified_digest
                if last_notified_digest is _UNSET
                else cast(str | None, last_notified_digest)
            ),
            last_error=record.last_error if last_error is _UNSET else cast(str | None, last_error),
        )
        _write_gateway_mail_notifier_record(connection, updated)
        connection.commit()
        return updated


def build_gateway_mail_notifier_status(
    *,
    record: GatewayMailNotifierRecord,
    supported: bool,
    support_error: str | None,
) -> GatewayMailNotifierStatusV1:
    """Build the structured HTTP status payload for the gateway notifier."""

    return GatewayMailNotifierStatusV1(
        enabled=record.enabled,
        interval_seconds=record.interval_seconds,
        supported=supported,
        support_error=support_error,
        last_poll_at_utc=record.last_poll_at_utc,
        last_notification_at_utc=record.last_notification_at_utc,
        last_error=record.last_error,
    )


def append_gateway_notifier_audit_record(
    sqlite_path: Path,
    *,
    poll_time_utc: str,
    unread_count: int | None,
    unread_digest: str | None,
    unread_summary: Sequence[GatewayNotifierAuditUnreadMessage],
    request_admission: GatewayAdmissionState | None,
    active_execution: GatewayExecutionState | None,
    queue_depth: int | None,
    outcome: GatewayNotifierAuditOutcome,
    enqueued_request_id: str | None = None,
    detail: str | None = None,
) -> GatewayNotifierAuditRecord:
    """Append one notifier audit row and return the persisted record."""

    with sqlite3.connect(sqlite_path) as connection:
        _ensure_queue_schema(connection)
        connection.execute(
            """
            INSERT INTO gateway_notifier_audit (
                poll_time_utc,
                unread_count,
                unread_digest,
                unread_summary_json,
                request_admission,
                active_execution,
                queue_depth,
                outcome,
                enqueued_request_id,
                detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                poll_time_utc,
                unread_count,
                unread_digest,
                _serialize_gateway_notifier_unread_summary(unread_summary),
                request_admission,
                active_execution,
                queue_depth,
                outcome,
                enqueued_request_id,
                detail,
            ),
        )
        row = connection.execute("SELECT last_insert_rowid()").fetchone()
        connection.commit()
    if row is None:
        raise SessionManifestError(
            "Gateway notifier audit insert did not return a persistent audit row id."
        )
    return GatewayNotifierAuditRecord(
        audit_id=int(row[0]),
        poll_time_utc=poll_time_utc,
        unread_count=unread_count,
        unread_digest=unread_digest,
        unread_summary=tuple(unread_summary),
        request_admission=request_admission,
        active_execution=active_execution,
        queue_depth=queue_depth,
        outcome=outcome,
        enqueued_request_id=enqueued_request_id,
        detail=detail,
    )


def read_gateway_notifier_audit_records(
    sqlite_path: Path,
    *,
    limit: int | None = None,
) -> list[GatewayNotifierAuditRecord]:
    """Load notifier audit history in chronological order."""

    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided")
    if not sqlite_path.is_file():
        return []

    query = """
        SELECT
            audit_id,
            poll_time_utc,
            unread_count,
            unread_digest,
            unread_summary_json,
            request_admission,
            active_execution,
            queue_depth,
            outcome,
            enqueued_request_id,
            detail
        FROM gateway_notifier_audit
        ORDER BY audit_id DESC
    """
    parameters: tuple[int, ...] | tuple[()] = ()
    if limit is not None:
        query += " LIMIT ?"
        parameters = (limit,)

    with sqlite3.connect(sqlite_path) as connection:
        _ensure_queue_schema(connection)
        rows = connection.execute(query, parameters).fetchall()

    rows.reverse()
    return [_row_to_gateway_notifier_audit_record(row) for row in rows]


def build_offline_gateway_status(
    *,
    attach_contract: GatewayAttachContractV1,
    managed_agent_instance_epoch: int,
) -> GatewayStatusV1:
    """Build the offline or not-attached status snapshot for a gateway-capable session."""

    paths = require_gateway_paths_for_attach_contract(attach_contract)
    return GatewayStatusV1(
        attach_identity=attach_contract.attach_identity,
        backend=attach_contract.backend,
        tmux_session_name=attach_contract.tmux_session_name,
        gateway_health="not_attached",
        managed_agent_connectivity="unavailable",
        managed_agent_recovery="idle",
        request_admission="blocked_unavailable",
        terminal_surface_eligibility="unknown",
        active_execution="idle",
        queue_depth=queue_depth_from_sqlite(paths.queue_path),
        managed_agent_instance_epoch=managed_agent_instance_epoch,
    )


def build_live_gateway_bindings(
    *,
    host: GatewayHost,
    port: int,
    state_path: Path,
) -> GatewayLiveBindings:
    """Build a live-binding dataclass for tmux env publication."""

    return GatewayLiveBindings(
        host=host,
        port=port,
        state_path=state_path.resolve(),
        protocol_version=GATEWAY_PROTOCOL_VERSION,
    )


def queue_depth_from_sqlite(sqlite_path: Path) -> int:
    """Return the number of queued or active requests in durable storage."""

    if not sqlite_path.is_file():
        return 0
    with sqlite3.connect(sqlite_path) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM gateway_requests
            WHERE state IN ('accepted', 'running')
            """
        ).fetchone()
    if row is None:
        return 0
    return int(row[0])


def append_gateway_event(paths: GatewayPaths, payload: GatewayJsonObject) -> None:
    """Append one JSONL gateway event."""

    paths.events_path.parent.mkdir(parents=True, exist_ok=True)
    with paths.events_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def gateway_health_response() -> GatewayHealthResponseV1:
    """Return the static gateway health payload."""

    return GatewayHealthResponseV1()


def generate_gateway_request_id() -> str:
    """Return a stable durable request identifier."""

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
    return f"gwreq-{timestamp}-{uuid.uuid4().hex[:8]}"


def now_utc_iso() -> str:
    """Return the current UTC timestamp formatted for persisted artifacts."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def read_pid_file(path: Path) -> int | None:
    """Read a pidfile if present and valid."""

    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return value if value > 0 else None


def is_pid_running(pid: int) -> bool:
    """Return whether a process id currently exists."""

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def require_gateway_paths_for_attach_contract(contract: GatewayAttachContractV1) -> GatewayPaths:
    """Resolve gateway paths from a runtime-owned attach contract."""

    if contract.manifest_path is None:
        raise SessionManifestError(
            "Gateway attach contract is missing runtime-owned `manifest_path`."
        )
    paths = gateway_paths_from_manifest_path(Path(contract.manifest_path))
    if paths is None:
        raise SessionManifestError(
            "Gateway attach contract points to a manifest that does not use the "
            "runtime-owned session-root layout."
        )
    return paths


def _status_to_seed(
    *,
    paths: GatewayPaths,
    attach_contract: GatewayAttachContractV1,
) -> GatewayStatusV1 | None:
    """Return an offline status snapshot when gateway state should be seeded or refreshed."""

    if not paths.state_path.is_file():
        return build_offline_gateway_status(
            attach_contract=attach_contract,
            managed_agent_instance_epoch=0,
        )

    try:
        existing_status = load_gateway_status(paths.state_path)
    except SessionManifestError:
        return build_offline_gateway_status(
            attach_contract=attach_contract,
            managed_agent_instance_epoch=0,
        )

    live_pid = read_pid_file(paths.pid_path)
    if live_pid is not None and is_pid_running(live_pid):
        return None
    if existing_status.gateway_health == "not_attached":
        return None
    return build_offline_gateway_status(
        attach_contract=attach_contract,
        managed_agent_instance_epoch=existing_status.managed_agent_instance_epoch,
    )


def _ensure_queue_database(sqlite_path: Path) -> None:
    """Create the durable gateway queue schema when missing."""

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as connection:
        _ensure_queue_schema(connection)
        connection.commit()


def _ensure_queue_schema(connection: sqlite3.Connection) -> None:
    """Create or upgrade the durable gateway queue schema."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS gateway_requests (
            request_id TEXT PRIMARY KEY,
            request_kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            state TEXT NOT NULL,
            accepted_at_utc TEXT NOT NULL,
            started_at_utc TEXT,
            finished_at_utc TEXT,
            managed_agent_instance_epoch INTEGER NOT NULL,
            error_detail TEXT,
            result_json TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS gateway_mail_notifier (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_seconds INTEGER,
            last_poll_at_utc TEXT,
            last_notification_at_utc TEXT,
            last_notified_digest TEXT,
            last_error TEXT,
            updated_at_utc TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS gateway_notifier_audit (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_time_utc TEXT NOT NULL,
            unread_count INTEGER,
            unread_digest TEXT,
            unread_summary_json TEXT NOT NULL DEFAULT '[]',
            request_admission TEXT,
            active_execution TEXT,
            queue_depth INTEGER,
            outcome TEXT NOT NULL CHECK (
                outcome IN ('empty', 'dedup_skip', 'busy_skip', 'enqueued', 'poll_error')
            ),
            enqueued_request_id TEXT,
            detail TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO gateway_mail_notifier (
            singleton,
            enabled,
            interval_seconds,
            last_poll_at_utc,
            last_notification_at_utc,
            last_notified_digest,
            last_error,
            updated_at_utc
        )
        VALUES (1, 0, NULL, NULL, NULL, NULL, NULL, ?)
        """,
        (now_utc_iso(),),
    )


def _serialize_gateway_notifier_unread_summary(
    unread_summary: Sequence[GatewayNotifierAuditUnreadMessage],
) -> str:
    """Serialize unread-summary rows for SQLite persistence."""

    payload = [
        {
            "message_ref": item.message_ref,
            "thread_ref": item.thread_ref,
            "created_at_utc": item.created_at_utc,
            "subject": item.subject,
        }
        for item in unread_summary
    ]
    return json.dumps(payload, sort_keys=True)


def _row_to_gateway_notifier_audit_record(
    row: sqlite3.Row | tuple[object, ...],
) -> GatewayNotifierAuditRecord:
    """Convert one SQLite row into a notifier audit record."""

    payload = json.loads(str(row[4]))
    if not isinstance(payload, list):
        raise SessionManifestError(
            "Gateway notifier audit unread_summary_json must decode to a list."
        )
    unread_summary = tuple(
        GatewayNotifierAuditUnreadMessage(
            message_ref=_require_json_string(item, key="message_ref"),
            thread_ref=_optional_json_string(item, key="thread_ref"),
            created_at_utc=_require_json_string(item, key="created_at_utc"),
            subject=_require_json_string(item, key="subject"),
        )
        for item in payload
    )
    audit_id = _require_sqlite_int(row[0], field_name="audit_id")
    unread_count = (
        None if row[2] is None else _require_sqlite_int(row[2], field_name="unread_count")
    )
    queue_depth = None if row[7] is None else _require_sqlite_int(row[7], field_name="queue_depth")
    return GatewayNotifierAuditRecord(
        audit_id=audit_id,
        poll_time_utc=str(row[1]),
        unread_count=unread_count,
        unread_digest=None if row[3] is None else str(row[3]),
        unread_summary=unread_summary,
        request_admission=None if row[5] is None else cast(GatewayAdmissionState, str(row[5])),
        active_execution=None if row[6] is None else cast(GatewayExecutionState, str(row[6])),
        queue_depth=queue_depth,
        outcome=cast(GatewayNotifierAuditOutcome, str(row[8])),
        enqueued_request_id=None if row[9] is None else str(row[9]),
        detail=None if row[10] is None else str(row[10]),
    )


def _read_gateway_mail_notifier_record(connection: sqlite3.Connection) -> GatewayMailNotifierRecord:
    """Load the singleton gateway notifier row from durable storage."""

    _ensure_queue_schema(connection)
    row = connection.execute(
        """
        SELECT
            enabled,
            interval_seconds,
            last_poll_at_utc,
            last_notification_at_utc,
            last_notified_digest,
            last_error
        FROM gateway_mail_notifier
        WHERE singleton = 1
        """
    ).fetchone()
    if row is None:
        record = GatewayMailNotifierRecord(
            enabled=False,
            interval_seconds=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_notified_digest=None,
            last_error=None,
        )
        _write_gateway_mail_notifier_record(connection, record)
        return record
    return GatewayMailNotifierRecord(
        enabled=bool(int(row[0])),
        interval_seconds=None if row[1] is None else int(row[1]),
        last_poll_at_utc=None if row[2] is None else str(row[2]),
        last_notification_at_utc=None if row[3] is None else str(row[3]),
        last_notified_digest=None if row[4] is None else str(row[4]),
        last_error=None if row[5] is None else str(row[5]),
    )


def _write_gateway_mail_notifier_record(
    connection: sqlite3.Connection,
    record: GatewayMailNotifierRecord,
) -> None:
    """Persist the singleton gateway notifier row."""

    _ensure_queue_schema(connection)
    connection.execute(
        """
        INSERT INTO gateway_mail_notifier (
            singleton,
            enabled,
            interval_seconds,
            last_poll_at_utc,
            last_notification_at_utc,
            last_notified_digest,
            last_error,
            updated_at_utc
        )
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(singleton) DO UPDATE SET
            enabled = excluded.enabled,
            interval_seconds = excluded.interval_seconds,
            last_poll_at_utc = excluded.last_poll_at_utc,
            last_notification_at_utc = excluded.last_notification_at_utc,
            last_notified_digest = excluded.last_notified_digest,
            last_error = excluded.last_error,
            updated_at_utc = excluded.updated_at_utc
        """,
        (
            int(record.enabled),
            record.interval_seconds,
            record.last_poll_at_utc,
            record.last_notification_at_utc,
            record.last_notified_digest,
            record.last_error,
            now_utc_iso(),
        ),
    )


def _require_json_string(value: object, *, key: str) -> str:
    """Return one required JSON object string field."""

    if not isinstance(value, dict):
        raise SessionManifestError(
            "Gateway notifier audit unread_summary_json must contain JSON objects."
        )
    field_value = value.get(key)
    if not isinstance(field_value, str):
        raise SessionManifestError(
            f"Gateway notifier audit unread_summary_json is missing string field {key!r}."
        )
    return field_value


def _optional_json_string(value: object, *, key: str) -> str | None:
    """Return one optional JSON object string field."""

    if not isinstance(value, dict):
        raise SessionManifestError(
            "Gateway notifier audit unread_summary_json must contain JSON objects."
        )
    field_value = value.get(key)
    if field_value is None:
        return None
    if not isinstance(field_value, str):
        raise SessionManifestError(
            f"Gateway notifier audit unread_summary_json has non-string field {key!r}."
        )
    return field_value


def _require_sqlite_int(value: object, *, field_name: str) -> int:
    """Return one SQLite integer field with strict runtime validation."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise SessionManifestError(
            f"Gateway notifier audit field {field_name!r} must be stored as an integer."
        )
    return value


def _load_json_mapping(path: Path, *, missing_prefix: str) -> GatewayJsonObject:
    """Load one JSON object from disk.

    Parameters
    ----------
    path:
        File expected to contain a top-level JSON object.
    missing_prefix:
        Error-message prefix used when the file is absent.

    Returns
    -------
    GatewayJsonObject
        Parsed JSON object payload.
    """

    if not path.is_file():
        raise SessionManifestError(f"{missing_prefix}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SessionManifestError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SessionManifestError(f"Expected top-level object in {path}")
    return cast(GatewayJsonObject, payload)


def _write_json(path: Path, payload: GatewayJsonObject) -> None:
    """Atomically persist one JSON object to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _write_text(path: Path, text: str) -> None:
    """Atomically persist plain text to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def _require_backend_state_string(
    payload: Mapping[str, GatewayJsonValue],
    *,
    key: str,
    fallback: str | None = None,
) -> str:
    """Read one required string field from backend-state JSON."""

    value = payload.get(key, fallback)
    if not isinstance(value, str) or not value.strip():
        raise SessionManifestError(
            f"Gateway attach metadata requires non-empty backend_state.{key!r}."
        )
    return value.strip()


def _optional_backend_state_string(
    payload: Mapping[str, GatewayJsonValue],
    *,
    key: str,
) -> str | None:
    """Read one optional string field from backend-state JSON."""

    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SessionManifestError(
            f"Gateway attach metadata requires backend_state.{key!r} to be a non-empty "
            "string when present."
        )
    return value.strip()
