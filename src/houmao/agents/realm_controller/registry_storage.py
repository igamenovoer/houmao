"""Filesystem storage helpers for the shared live-agent registry."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Mapping

from houmao.owned_paths import resolve_registry_root
from pydantic import ValidationError

from houmao.agents.realm_controller.backends.tmux_runtime import tmux_session_exists
from houmao.agents.realm_controller.errors import SchemaValidationError, SessionManifestError
from houmao.agents.realm_controller.agent_identity import normalize_managed_agent_id
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    canonicalize_registry_agent_name,
    format_registry_validation_error,
)
from houmao.agents.realm_controller.schema_validation import validate_payload

DEFAULT_REGISTRY_LEASE_TTL = timedelta(hours=24)
JOINED_REGISTRY_SENTINEL_LEASE_TTL = timedelta(days=30)
DEFAULT_REGISTRY_CLEANUP_GRACE_PERIOD = timedelta(minutes=5)
LIVE_AGENT_REGISTRY_SCHEMA = "live_agent_registry_record.v2.schema.json"


@dataclass(frozen=True)
class GlobalRegistryPaths:
    """Resolved filesystem layout for the shared live-agent registry."""

    root: Path
    live_agents_dir: Path


@dataclass(frozen=True)
class RegistryCleanupResult:
    """Summary of one stale-registry cleanup pass."""

    registry_root: Path
    removed_agent_ids: tuple[str, ...]
    preserved_agent_ids: tuple[str, ...]
    failed_agent_ids: tuple[str, ...]
    planned_agent_ids: tuple[str, ...] = ()
    actions: tuple["RegistryCleanupAction", ...] = ()


@dataclass(frozen=True)
class RegistryCleanupAction:
    """One registry cleanup decision."""

    agent_id: str
    path: Path
    outcome: Literal["planned", "removed", "preserved", "failed"]
    reason: str


def resolve_global_registry_root(*, env: Mapping[str, str] | None = None) -> Path:
    """Resolve the effective shared-registry root."""

    try:
        return resolve_registry_root(env=env)
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc


def global_registry_paths(*, env: Mapping[str, str] | None = None) -> GlobalRegistryPaths:
    """Return the resolved shared-registry directory layout."""

    root = resolve_global_registry_root(env=env)
    return GlobalRegistryPaths(root=root, live_agents_dir=(root / "live_agents").resolve())


def new_registry_generation_id() -> str:
    """Return a new stable generation id for one live session."""

    return str(uuid.uuid4())


def record_path_for_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Return the shared-registry ``record.json`` path for one agent id."""

    normalized_agent_id = _normalize_agent_id_component(agent_id)
    paths = global_registry_paths(env=env)
    return (paths.live_agents_dir / normalized_agent_id / "record.json").resolve()


def load_live_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> LiveAgentRegistryRecordV2 | None:
    """Load one strict registry record regardless of freshness."""

    path = record_path_for_agent_id(agent_id, env=env)
    if not path.is_file():
        return None
    return _read_live_agent_record(path)


def resolve_live_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> LiveAgentRegistryRecordV2 | None:
    """Resolve one fresh registry record by authoritative ``agent_id``."""

    try:
        record = load_live_agent_record_by_agent_id(agent_id, env=env)
    except SessionManifestError:
        return None
    if record is None:
        return None
    if not is_live_agent_record_fresh(record, now=now):
        return None
    return record


def resolve_live_agent_records_by_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[LiveAgentRegistryRecordV2, ...]:
    """Resolve every fresh registry record that matches one canonical agent name."""

    canonical_name = canonicalize_registry_agent_name(agent_name)
    current_time = _coerce_now(now)
    paths = global_registry_paths(env=env)
    if not paths.live_agents_dir.exists():
        return ()

    matches: list[LiveAgentRegistryRecordV2] = []
    for candidate in sorted(paths.live_agents_dir.iterdir()):
        if not candidate.is_dir():
            continue
        record_path = candidate / "record.json"
        if not record_path.is_file():
            continue
        try:
            record = _read_live_agent_record(record_path)
        except SessionManifestError:
            continue
        if record.agent_name != canonical_name:
            continue
        if not is_live_agent_record_fresh(record, now=current_time):
            continue
        matches.append(record)
    return tuple(matches)


def resolve_live_agent_record(
    agent_identity: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> LiveAgentRegistryRecordV2 | None:
    """Resolve one fresh record by agent id or by unique canonical agent name."""

    direct_record = resolve_live_agent_record_by_agent_id(
        agent_identity,
        env=env,
        now=now,
    )
    if direct_record is not None:
        return direct_record

    matches = resolve_live_agent_records_by_name(
        agent_identity,
        env=env,
        now=now,
    )
    if len(matches) == 1:
        return matches[0]
    return None


def publish_live_agent_record(
    record: LiveAgentRegistryRecordV2,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> LiveAgentRegistryRecordV2:
    """Publish or refresh one shared live-agent record atomically."""

    current_time = _coerce_now(now)
    if not is_live_agent_record_fresh(record, now=current_time):
        raise SessionManifestError("Refusing to publish a record with an already-expired lease.")

    existing = load_live_agent_record_by_agent_id(record.agent_id, env=env)
    _raise_if_conflicting_fresh_generation(
        existing=existing,
        desired=record,
        now=current_time,
    )

    payload = record.model_dump(mode="json")
    try:
        LiveAgentRegistryRecordV2.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_registry_validation_error(
                "Shared registry record schema validation failed before publish for "
                f"`{record.agent_id}`",
                exc,
            )
        ) from exc
    try:
        validate_payload(payload, LIVE_AGENT_REGISTRY_SCHEMA)
    except SchemaValidationError as exc:
        raise SessionManifestError(
            "Shared registry record schema validation failed before publish for "
            f"`{record.agent_id}`: {exc}"
        ) from exc

    path = record_path_for_agent_id(record.agent_id, env=env)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomically(path, payload)

    observed = load_live_agent_record_by_agent_id(record.agent_id, env=env)
    if observed is None:
        raise SessionManifestError(
            f"Registry publish verification failed for agent_id `{record.agent_id}`."
        )
    _raise_if_conflicting_fresh_generation(
        existing=observed,
        desired=record,
        now=current_time,
        post_publish_check=True,
    )
    return observed


def remove_live_agent_record(
    agent_id: str,
    *,
    generation_id: str | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Remove one live-agent registry directory when it still belongs to the caller."""

    path = record_path_for_agent_id(agent_id, env=env)
    record_dir = path.parent

    if path.is_file():
        try:
            record = _read_live_agent_record(path)
        except SessionManifestError:
            record = None
        if (
            generation_id is not None
            and record is not None
            and record.generation_id != generation_id
        ):
            return False

    if not record_dir.exists():
        return False

    shutil.rmtree(record_dir, ignore_errors=False)
    return True


def cleanup_stale_live_agent_records(
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    grace_period: timedelta = DEFAULT_REGISTRY_CLEANUP_GRACE_PERIOD,
    dry_run: bool = False,
    probe_local_tmux: bool = False,
) -> RegistryCleanupResult:
    """Remove stale or malformed ``live_agents/`` directories beyond the grace period."""

    current_time = _coerce_now(now)
    paths = global_registry_paths(env=env)
    if not paths.live_agents_dir.exists():
        return RegistryCleanupResult(
            registry_root=paths.root,
            removed_agent_ids=(),
            preserved_agent_ids=(),
            failed_agent_ids=(),
            planned_agent_ids=(),
            actions=(),
        )

    removed: list[str] = []
    preserved: list[str] = []
    failed: list[str] = []
    planned: list[str] = []
    actions: list[RegistryCleanupAction] = []
    for candidate in sorted(paths.live_agents_dir.iterdir()):
        if not candidate.is_dir():
            continue

        record_path = candidate / "record.json"
        should_remove = False
        remove_reason = ""
        preserve_reason = "lease remains fresh"
        if not record_path.is_file():
            should_remove = True
            remove_reason = "shared-registry record.json is missing"
        else:
            try:
                record = _read_live_agent_record(record_path)
            except SessionManifestError:
                should_remove = True
                remove_reason = "shared-registry record.json is malformed"
            else:
                should_remove = _record_expired_beyond_grace(
                    record,
                    now=current_time,
                    grace_period=grace_period,
                )
                if should_remove:
                    remove_reason = "registry lease expired beyond the cleanup grace period"
                elif (
                    probe_local_tmux
                    and record.terminal.kind == "tmux"
                    and not tmux_session_exists(session_name=record.terminal.session_name)
                ):
                    should_remove = True
                    remove_reason = "local tmux liveness probe found no owning session"
                elif probe_local_tmux and record.terminal.kind == "tmux":
                    preserve_reason = "local tmux liveness probe confirmed the owning session"
                elif not probe_local_tmux:
                    preserve_reason = (
                        "lease remains fresh and local liveness probing was not requested"
                    )

        if should_remove:
            if dry_run:
                planned.append(candidate.name)
                actions.append(
                    RegistryCleanupAction(
                        agent_id=candidate.name,
                        path=candidate.resolve(),
                        outcome="planned",
                        reason=remove_reason,
                    )
                )
                continue
            try:
                shutil.rmtree(candidate, ignore_errors=False)
            except OSError as exc:
                failed.append(candidate.name)
                actions.append(
                    RegistryCleanupAction(
                        agent_id=candidate.name,
                        path=candidate.resolve(),
                        outcome="failed",
                        reason=f"{remove_reason}; removal failed: {exc}",
                    )
                )
            else:
                removed.append(candidate.name)
                actions.append(
                    RegistryCleanupAction(
                        agent_id=candidate.name,
                        path=candidate.resolve(),
                        outcome="removed",
                        reason=remove_reason,
                    )
                )
            continue

        preserved.append(candidate.name)
        actions.append(
            RegistryCleanupAction(
                agent_id=candidate.name,
                path=candidate.resolve(),
                outcome="preserved",
                reason=preserve_reason,
            )
        )

    return RegistryCleanupResult(
        registry_root=paths.root,
        removed_agent_ids=tuple(removed),
        preserved_agent_ids=tuple(preserved),
        failed_agent_ids=tuple(failed),
        planned_agent_ids=tuple(planned),
        actions=tuple(actions),
    )


def is_live_agent_record_fresh(
    record: LiveAgentRegistryRecordV2,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether a record's lease remains live at the provided time."""

    lease_expires_at = _parse_timestamp(record.lease_expires_at)
    return lease_expires_at >= _coerce_now(now)


def _raise_if_conflicting_fresh_generation(
    *,
    existing: LiveAgentRegistryRecordV2 | None,
    desired: LiveAgentRegistryRecordV2,
    now: datetime,
    post_publish_check: bool = False,
) -> None:
    """Reject a publish attempt when another fresh generation already owns the agent id."""

    if existing is None:
        return
    if not is_live_agent_record_fresh(existing, now=now):
        return
    if existing.generation_id == desired.generation_id:
        return

    conflict_context = "after publish verification" if post_publish_check else "before publish"
    raise SessionManifestError(
        "Shared-registry ownership conflict for "
        f"agent_id `{desired.agent_id}` {conflict_context}: fresh generation "
        f"`{existing.generation_id}` already owns that logical identity, "
        f"so generation `{desired.generation_id}` must stand down."
    )


def _record_expired_beyond_grace(
    record: LiveAgentRegistryRecordV2,
    *,
    now: datetime,
    grace_period: timedelta,
) -> bool:
    """Return whether a record lease expired earlier than the cleanup grace period."""

    return _parse_timestamp(record.lease_expires_at) + grace_period < now


def _normalize_agent_id_component(agent_id: str) -> str:
    """Validate and normalize one authoritative agent id path component."""

    return normalize_managed_agent_id(agent_id)


def _read_live_agent_record(path: Path) -> LiveAgentRegistryRecordV2:
    """Load and validate one registry record from disk."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise SessionManifestError(f"Invalid JSON in registry record `{path}`.") from exc

    try:
        return LiveAgentRegistryRecordV2.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_registry_validation_error(
                f"Invalid registry record `{path}`",
                exc,
            )
        ) from exc


def _write_json_atomically(path: Path, payload: dict[str, object]) -> None:
    """Persist one JSON payload atomically."""

    temp_path = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _parse_timestamp(value: str) -> datetime:
    """Parse a timezone-aware ISO-8601 timestamp."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SessionManifestError("Registry timestamp must be timezone-aware.")
    return parsed.astimezone(UTC)


def _coerce_now(now: datetime | None) -> datetime:
    """Normalize the reference time used by freshness checks."""

    current = now or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)
