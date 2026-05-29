"""Filesystem storage helpers for the shared managed-agent registry."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Literal, Mapping

from pydantic import ValidationError

from houmao.owned_mutation import remove_tree_or_path
from houmao.owned_paths import resolve_registry_root

from houmao.agents.realm_controller.agent_identity import (
    normalize_managed_agent_id,
    normalize_user_managed_agent_name,
)
from houmao.agents.realm_controller.backends.tmux_runtime import tmux_session_exists
from houmao.agents.realm_controller.errors import SchemaValidationError, SessionManifestError
from houmao.agents.realm_controller.registry_models import (
    ExternalManagedAgentRegistryRecordV1,
    LiveAgentRegistryRecordV2,
    ManagedAgentRegistryRecordV3,
    canonicalize_registry_agent_name,
    format_registry_validation_error,
    parse_managed_agent_registry_record,
)
from houmao.agents.realm_controller.schema_validation import validate_payload

DEFAULT_REGISTRY_LEASE_TTL = timedelta(hours=24)
TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL = timedelta(days=36500)
JOINED_REGISTRY_SENTINEL_LEASE_TTL = timedelta(days=30)
DEFAULT_REGISTRY_CLEANUP_GRACE_PERIOD = timedelta(minutes=5)
MANAGED_AGENT_REGISTRY_SCHEMA = "managed_agent_registry_record.v3.schema.json"
LIVE_AGENT_REGISTRY_SCHEMA = MANAGED_AGENT_REGISTRY_SCHEMA
EXTERNAL_MANAGED_AGENT_REGISTRY_SCHEMA = "external_managed_agent_registry_record.v1.schema.json"


@dataclass(frozen=True)
class GlobalRegistryPaths:
    """Resolved filesystem layout for the shared managed-agent registry."""

    root: Path
    live_agents_dir: Path
    external_agents_dir: Path | None = None

    def __post_init__(self) -> None:
        """Fill newer registry subdirectories for older test fixtures."""

        if self.external_agents_dir is None:
            object.__setattr__(self, "external_agents_dir", self.root / "external_agents")


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
    return GlobalRegistryPaths(
        root=root,
        live_agents_dir=root / "live_agents",
        external_agents_dir=root / "external_agents",
    )


def new_registry_generation_id() -> str:
    """Return a new stable generation id for one registry record publication."""

    return str(uuid.uuid4())


def new_external_agent_id() -> str:
    """Return a new local id for one external communication-only record."""

    return f"external-{uuid.uuid4().hex}"


def record_path_for_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Return the shared-registry ``record.json`` path for one agent id."""

    normalized_agent_id = _normalize_agent_id_component(agent_id)
    paths = global_registry_paths(env=env)
    return paths.live_agents_dir / normalized_agent_id / "record.json"


def external_record_path_for_agent_id(
    external_agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Return the external-registry ``record.json`` path for one external id."""

    normalized_agent_id = _normalize_agent_id_component(external_agent_id)
    paths = global_registry_paths(env=env)
    assert paths.external_agents_dir is not None
    return paths.external_agents_dir / normalized_agent_id / "record.json"


def load_managed_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Load one strict registry record regardless of lifecycle state or freshness."""

    path = record_path_for_agent_id(agent_id, env=env)
    if path.parent.is_symlink() or path.is_symlink():
        return None
    if not path.is_file():
        return None
    return _read_managed_agent_record(path)


def load_external_managed_agent_record_by_agent_id(
    external_agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> ExternalManagedAgentRegistryRecordV1 | None:
    """Load one external communication-only record by local external id."""

    path = external_record_path_for_agent_id(external_agent_id, env=env)
    if path.parent.parent.is_symlink() or path.parent.is_symlink() or path.is_symlink():
        return None
    if not path.is_file():
        return None
    return _read_external_managed_agent_record(path)


def list_external_managed_agent_records(
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[ExternalManagedAgentRegistryRecordV1, ...]:
    """Return every valid external communication-only registry record."""

    paths = global_registry_paths(env=env)
    assert paths.external_agents_dir is not None
    if paths.external_agents_dir.is_symlink() or not paths.external_agents_dir.exists():
        return ()

    records: list[ExternalManagedAgentRegistryRecordV1] = []
    for candidate in sorted(paths.external_agents_dir.iterdir()):
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        record_path = candidate / "record.json"
        if record_path.is_symlink() or not record_path.is_file():
            continue
        try:
            records.append(_read_external_managed_agent_record(record_path))
        except SessionManifestError:
            continue
    return tuple(records)


def resolve_external_managed_agent_records_by_name(
    local_name: str,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[ExternalManagedAgentRegistryRecordV1, ...]:
    """Resolve external communication-only records by local user-facing name."""

    try:
        normalized_name = canonicalize_external_registry_agent_name(local_name)
    except SessionManifestError:
        return ()
    return tuple(
        record
        for record in list_external_managed_agent_records(env=env)
        if record.local_name == normalized_name
    )


def resolve_external_managed_agent_record(
    agent_identity: str,
    *,
    env: Mapping[str, str] | None = None,
) -> ExternalManagedAgentRegistryRecordV1 | None:
    """Resolve one external record by local id or unique local name."""

    direct_record = load_external_managed_agent_record_by_agent_id(agent_identity, env=env)
    if direct_record is not None:
        return direct_record
    matches = resolve_external_managed_agent_records_by_name(agent_identity, env=env)
    if len(matches) == 1:
        return matches[0]
    return None


def resolve_active_managed_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Resolve one active fresh registry record by authoritative ``agent_id``."""

    try:
        record = load_managed_agent_record_by_agent_id(agent_id, env=env)
    except SessionManifestError:
        return None
    if record is None:
        return None
    if not is_managed_agent_record_active(record, now=now):
        return None
    return record


def resolve_relaunchable_managed_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Resolve one relaunchable registry record by authoritative ``agent_id``."""

    try:
        record = load_managed_agent_record_by_agent_id(agent_id, env=env)
    except SessionManifestError:
        return None
    if record is None:
        return None
    if not is_managed_agent_record_relaunchable(record, now=now):
        return None
    return record


def resolve_cleanup_managed_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Resolve one cleanup-capable registry record by authoritative ``agent_id``."""

    try:
        record = load_managed_agent_record_by_agent_id(agent_id, env=env)
    except SessionManifestError:
        return None
    if record is None:
        return None
    if not is_managed_agent_record_cleanup_candidate(record):
        return None
    return record


def resolve_managed_agent_records_by_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Resolve every registry record that matches one canonical agent name."""

    return _resolve_records_by_name(
        agent_name=agent_name,
        env=env,
        include=lambda record: True,
    )


def resolve_active_managed_agent_records_by_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Resolve every active fresh record that matches one canonical agent name."""

    current_time = _coerce_now(now)
    return _resolve_records_by_name(
        agent_name=agent_name,
        env=env,
        include=lambda record: is_managed_agent_record_active(record, now=current_time),
    )


def resolve_relaunchable_managed_agent_records_by_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Resolve every relaunchable record that matches one canonical agent name."""

    current_time = _coerce_now(now)
    return _resolve_records_by_name(
        agent_name=agent_name,
        env=env,
        include=lambda record: is_managed_agent_record_relaunchable(record, now=current_time),
    )


def resolve_cleanup_managed_agent_records_by_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Resolve every cleanup-capable record that matches one canonical agent name."""

    return _resolve_records_by_name(
        agent_name=agent_name,
        env=env,
        include=is_managed_agent_record_cleanup_candidate,
    )


def resolve_active_managed_agent_records_by_terminal_session_name(
    session_name: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Resolve every active fresh record that matches one exact live tmux session name."""

    candidate_session_name = session_name.strip()
    if not candidate_session_name:
        return ()

    current_time = _coerce_now(now)
    paths = global_registry_paths(env=env)
    if not paths.live_agents_dir.exists():
        return ()

    matches: list[ManagedAgentRegistryRecordV3] = []
    for candidate in sorted(paths.live_agents_dir.iterdir()):
        if not candidate.is_dir():
            continue
        record_path = candidate / "record.json"
        if not record_path.is_file():
            continue
        try:
            record = _read_managed_agent_record(record_path)
        except SessionManifestError:
            continue
        if record.terminal.current_session_name != candidate_session_name:
            continue
        if not is_managed_agent_record_active(record, now=current_time):
            continue
        matches.append(record)
    return tuple(matches)


def resolve_active_managed_agent_record(
    agent_identity: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Resolve one active fresh record by agent id or by unique canonical agent name."""

    direct_record = resolve_active_managed_agent_record_by_agent_id(
        agent_identity,
        env=env,
        now=now,
    )
    if direct_record is not None:
        return direct_record

    matches = resolve_active_managed_agent_records_by_name(
        agent_identity,
        env=env,
        now=now,
    )
    if len(matches) == 1:
        return matches[0]
    return None


def publish_managed_agent_record(
    record: ManagedAgentRegistryRecordV3 | LiveAgentRegistryRecordV2,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ManagedAgentRegistryRecordV3:
    """Publish or refresh one shared managed-agent record atomically."""

    current_time = _coerce_now(now)
    try:
        publish_record = _coerce_publish_record(record)
    except ValidationError as exc:
        agent_id = getattr(record, "agent_id", "<unknown>")
        raise SessionManifestError(
            format_registry_validation_error(
                f"Shared registry record schema validation failed before publish for `{agent_id}`",
                exc,
            )
        ) from exc
    if publish_record.lifecycle.state in {
        "active",
        "relaunching",
    } and not is_managed_agent_record_fresh(
        publish_record,
        now=current_time,
    ):
        raise SessionManifestError("Refusing to publish an active record with an expired lease.")

    existing = load_managed_agent_record_by_agent_id(publish_record.agent_id, env=env)
    _raise_if_conflicting_active_generation(
        existing=existing,
        desired=publish_record,
        now=current_time,
    )

    payload = publish_record.model_dump(mode="json")
    try:
        ManagedAgentRegistryRecordV3.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_registry_validation_error(
                "Shared registry record schema validation failed before publish for "
                f"`{publish_record.agent_id}`",
                exc,
            )
        ) from exc
    try:
        validate_payload(payload, MANAGED_AGENT_REGISTRY_SCHEMA)
    except SchemaValidationError as exc:
        raise SessionManifestError(
            "Shared registry record schema validation failed before publish for "
            f"`{publish_record.agent_id}`: {exc}"
        ) from exc

    path = record_path_for_agent_id(publish_record.agent_id, env=env)
    live_agents_dir = global_registry_paths(env=env).live_agents_dir
    if live_agents_dir.is_symlink():
        remove_tree_or_path(live_agents_dir, allowed_roots=(global_registry_paths(env=env).root,))
    if path.parent.is_symlink():
        remove_tree_or_path(path.parent, allowed_roots=(live_agents_dir,))
    live_agents_dir.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomically(path, payload)

    observed = load_managed_agent_record_by_agent_id(publish_record.agent_id, env=env)
    if observed is None:
        raise SessionManifestError(
            f"Registry publish verification failed for agent_id `{publish_record.agent_id}`."
        )
    _raise_if_conflicting_active_generation(
        existing=observed,
        desired=publish_record,
        now=current_time,
        post_publish_check=True,
    )
    return observed


def publish_external_managed_agent_record(
    record: ExternalManagedAgentRegistryRecordV1,
    *,
    env: Mapping[str, str] | None = None,
) -> ExternalManagedAgentRegistryRecordV1:
    """Publish or refresh one external communication-only record atomically."""

    try:
        publish_record = ExternalManagedAgentRegistryRecordV1.model_validate(
            record.model_dump(mode="json")
        )
    except ValidationError as exc:
        agent_id = getattr(record, "external_agent_id", "<unknown>")
        raise SessionManifestError(
            format_registry_validation_error(
                "External managed-agent registry record schema validation failed before "
                f"publish for `{agent_id}`",
                exc,
            )
        ) from exc

    payload = publish_record.model_dump(mode="json")
    try:
        validate_payload(payload, EXTERNAL_MANAGED_AGENT_REGISTRY_SCHEMA)
    except SchemaValidationError as exc:
        raise SessionManifestError(
            "External managed-agent registry record schema validation failed before publish for "
            f"`{publish_record.external_agent_id}`: {exc}"
        ) from exc

    _raise_if_external_name_conflicts_with_different_record(publish_record, env=env)

    path = external_record_path_for_agent_id(publish_record.external_agent_id, env=env)
    paths = global_registry_paths(env=env)
    assert paths.external_agents_dir is not None
    if paths.external_agents_dir.is_symlink():
        remove_tree_or_path(paths.external_agents_dir, allowed_roots=(paths.root,))
    if path.parent.is_symlink():
        remove_tree_or_path(path.parent, allowed_roots=(paths.external_agents_dir,))
    paths.external_agents_dir.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomically(path, payload)

    observed = load_external_managed_agent_record_by_agent_id(
        publish_record.external_agent_id,
        env=env,
    )
    if observed is None:
        raise SessionManifestError(
            "External registry publish verification failed for "
            f"external_agent_id `{publish_record.external_agent_id}`."
        )
    return observed


def remove_external_managed_agent_record(
    external_agent_id: str,
    *,
    generation_id: str | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Remove one external communication-only registry record."""

    path = external_record_path_for_agent_id(external_agent_id, env=env)
    record_dir = path.parent

    if path.is_file():
        try:
            record = _read_external_managed_agent_record(path)
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

    paths = global_registry_paths(env=env)
    assert paths.external_agents_dir is not None
    remove_tree_or_path(record_dir, allowed_roots=(paths.external_agents_dir,))
    return True


def remove_managed_agent_record(
    agent_id: str,
    *,
    generation_id: str | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Remove one registry directory when it still belongs to the caller."""

    path = record_path_for_agent_id(agent_id, env=env)
    record_dir = path.parent

    if path.is_file():
        try:
            record = _read_managed_agent_record(path)
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

    remove_tree_or_path(record_dir, allowed_roots=(global_registry_paths(env=env).live_agents_dir,))
    return True


def cleanup_stale_managed_agent_records(
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    grace_period: timedelta = DEFAULT_REGISTRY_CLEANUP_GRACE_PERIOD,
    dry_run: bool = False,
    probe_local_tmux: bool = True,
) -> RegistryCleanupResult:
    """Remove malformed or stale active ``live_agents/`` directories beyond the grace period."""

    current_time = _coerce_now(now)
    paths = global_registry_paths(env=env)
    if paths.live_agents_dir.is_symlink():
        action = RegistryCleanupAction(
            agent_id="live_agents",
            path=paths.live_agents_dir,
            outcome="planned" if dry_run else "removed",
            reason="shared-registry live_agents root is a symlink",
        )
        if dry_run:
            return RegistryCleanupResult(
                registry_root=paths.root,
                removed_agent_ids=(),
                preserved_agent_ids=(),
                failed_agent_ids=(),
                planned_agent_ids=("live_agents",),
                actions=(action,),
            )
        remove_tree_or_path(paths.live_agents_dir, allowed_roots=(paths.root,))
        return RegistryCleanupResult(
            registry_root=paths.root,
            removed_agent_ids=("live_agents",),
            preserved_agent_ids=(),
            failed_agent_ids=(),
            planned_agent_ids=(),
            actions=(action,),
        )
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
        if candidate.is_symlink():
            should_remove = True
            remove_reason = "shared-registry entry is a symlink"
            preserve_reason = ""
            record_path = candidate / "record.json"
        elif not candidate.is_dir():
            continue
        else:
            record_path = candidate / "record.json"
            should_remove = False
            remove_reason = ""
            preserve_reason = "registry record remains valid"
            if record_path.is_symlink():
                should_remove = True
                remove_reason = "shared-registry record.json is a symlink"
            elif not record_path.is_file():
                should_remove = True
                remove_reason = "shared-registry record.json is missing"
            else:
                try:
                    record = _read_managed_agent_record(record_path)
                except SessionManifestError:
                    should_remove = True
                    remove_reason = "shared-registry record.json is malformed"
                else:
                    if record.lifecycle.state in {"stopped", "retired"}:
                        preserve_reason = f"lifecycle state `{record.lifecycle.state}` is durable"
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
                            and record.terminal.current_session_name is not None
                            and not tmux_session_exists(
                                session_name=record.terminal.current_session_name,
                            )
                        ):
                            should_remove = True
                            remove_reason = "local tmux liveness probe found no owning session"
                        elif probe_local_tmux and record.terminal.current_session_name is not None:
                            preserve_reason = (
                                "local tmux liveness probe confirmed the owning session"
                            )
                        elif not probe_local_tmux:
                            preserve_reason = (
                                "lease remains fresh and local tmux checking was disabled"
                            )

        if should_remove:
            if dry_run:
                planned.append(candidate.name)
                actions.append(
                    RegistryCleanupAction(
                        agent_id=candidate.name,
                        path=candidate,
                        outcome="planned",
                        reason=remove_reason,
                    )
                )
                continue
            try:
                remove_tree_or_path(candidate, allowed_roots=(paths.live_agents_dir,))
            except OSError as exc:
                failed.append(candidate.name)
                actions.append(
                    RegistryCleanupAction(
                        agent_id=candidate.name,
                        path=candidate,
                        outcome="failed",
                        reason=f"{remove_reason}; removal failed: {exc}",
                    )
                )
            else:
                removed.append(candidate.name)
                actions.append(
                    RegistryCleanupAction(
                        agent_id=candidate.name,
                        path=candidate,
                        outcome="removed",
                        reason=remove_reason,
                    )
                )
            continue

        preserved.append(candidate.name)
        actions.append(
            RegistryCleanupAction(
                agent_id=candidate.name,
                path=candidate,
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


def is_managed_agent_record_fresh(
    record: ManagedAgentRegistryRecordV3,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether a record's active lease remains live at the provided time."""

    if record.liveness is None:
        return False
    lease_expires_at = _parse_timestamp(record.liveness.lease_expires_at)
    return lease_expires_at >= _coerce_now(now)


def is_managed_agent_record_active(
    record: ManagedAgentRegistryRecordV3,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether a record is a live active registry target."""

    return record.lifecycle.state == "active" and is_managed_agent_record_fresh(record, now=now)


def is_managed_agent_record_relaunchable(
    record: ManagedAgentRegistryRecordV3,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether a record can be addressed by relaunch resolution."""

    if not record.lifecycle.relaunchable:
        return False
    if record.lifecycle.state == "stopped":
        return True
    if record.lifecycle.state == "active":
        return is_managed_agent_record_active(record, now=now)
    return False


def is_managed_agent_record_cleanup_candidate(record: ManagedAgentRegistryRecordV3) -> bool:
    """Return whether a record retains runtime authority useful for cleanup."""

    return (
        record.runtime.manifest_path.strip() != ""
        and record.runtime.session_root is not None
        and record.runtime.session_root.strip() != ""
    )


def canonicalize_external_registry_agent_name(value: str) -> str:
    """Validate and normalize an external registry local alias."""

    try:
        return normalize_user_managed_agent_name(value)
    except SessionManifestError:
        raise


def _resolve_records_by_name(
    *,
    agent_name: str,
    env: Mapping[str, str] | None,
    include: Callable[[ManagedAgentRegistryRecordV3], bool],
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Resolve registry records by canonical agent name with one inclusion predicate."""

    canonical_name = canonicalize_registry_agent_name(agent_name)
    paths = global_registry_paths(env=env)
    if not paths.live_agents_dir.exists():
        return ()

    matches: list[ManagedAgentRegistryRecordV3] = []
    for candidate in sorted(paths.live_agents_dir.iterdir()):
        if not candidate.is_dir():
            continue
        record_path = candidate / "record.json"
        if not record_path.is_file():
            continue
        try:
            record = _read_managed_agent_record(record_path)
        except SessionManifestError:
            continue
        if record.agent_name != canonical_name:
            continue
        if not include(record):
            continue
        matches.append(record)
    return tuple(matches)


def _raise_if_conflicting_active_generation(
    *,
    existing: ManagedAgentRegistryRecordV3 | None,
    desired: ManagedAgentRegistryRecordV3,
    now: datetime,
    post_publish_check: bool = False,
) -> None:
    """Reject a publish attempt when another active generation already owns the agent id."""

    if existing is None:
        return
    if not is_managed_agent_record_active(existing, now=now):
        return
    if existing.generation_id == desired.generation_id:
        return

    conflict_context = "after publish verification" if post_publish_check else "before publish"
    raise SessionManifestError(
        "Shared-registry ownership conflict for "
        f"agent_id `{desired.agent_id}` {conflict_context}: active generation "
        f"`{existing.generation_id}` already owns that logical identity, "
        f"so generation `{desired.generation_id}` must stand down."
    )


def _raise_if_external_name_conflicts_with_different_record(
    desired: ExternalManagedAgentRegistryRecordV1,
    *,
    env: Mapping[str, str] | None,
) -> None:
    """Reject duplicate external local aliases owned by another external id."""

    for existing in resolve_external_managed_agent_records_by_name(desired.local_name, env=env):
        if existing.external_agent_id == desired.external_agent_id:
            continue
        raise SessionManifestError(
            "External managed-agent registry name conflict: local_name "
            f"`{desired.local_name}` is already owned by external_agent_id "
            f"`{existing.external_agent_id}`."
        )


def _record_expired_beyond_grace(
    record: ManagedAgentRegistryRecordV3,
    *,
    now: datetime,
    grace_period: timedelta,
) -> bool:
    """Return whether an active record lease expired earlier than the cleanup grace period."""

    if record.liveness is None:
        return False
    return _parse_timestamp(record.liveness.lease_expires_at) + grace_period < now


def _normalize_agent_id_component(agent_id: str) -> str:
    """Validate and normalize one authoritative agent id path component."""

    return normalize_managed_agent_id(agent_id)


def _read_managed_agent_record(path: Path) -> ManagedAgentRegistryRecordV3:
    """Load and validate one managed-agent registry record from disk."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise SessionManifestError(f"Invalid JSON in registry record `{path}`.") from exc

    try:
        return parse_managed_agent_registry_record(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_registry_validation_error(
                f"Invalid registry record `{path}`",
                exc,
            )
        ) from exc


def _read_external_managed_agent_record(path: Path) -> ExternalManagedAgentRegistryRecordV1:
    """Load and validate one external managed-agent registry record from disk."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise SessionManifestError(f"Invalid JSON in external registry record `{path}`.") from exc

    try:
        validate_payload(payload, EXTERNAL_MANAGED_AGENT_REGISTRY_SCHEMA)
    except SchemaValidationError as exc:
        raise SessionManifestError(f"Invalid external registry record `{path}`: {exc}") from exc

    try:
        return ExternalManagedAgentRegistryRecordV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_registry_validation_error(
                f"Invalid external registry record `{path}`",
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


def load_live_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Compatibility wrapper for lifecycle-aware registry loading."""

    return load_managed_agent_record_by_agent_id(agent_id, env=env)


def resolve_live_agent_record_by_agent_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Compatibility wrapper for active record resolution by authoritative id."""

    return resolve_active_managed_agent_record_by_agent_id(agent_id, env=env, now=now)


def resolve_live_agent_records_by_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Compatibility wrapper for active record resolution by friendly name."""

    return resolve_active_managed_agent_records_by_name(agent_name, env=env, now=now)


def resolve_live_agent_records_by_terminal_session_name(
    session_name: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[ManagedAgentRegistryRecordV3, ...]:
    """Compatibility wrapper for active record resolution by live tmux session."""

    return resolve_active_managed_agent_records_by_terminal_session_name(
        session_name,
        env=env,
        now=now,
    )


def resolve_live_agent_record(
    agent_identity: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Compatibility wrapper for active record resolution by id or unique name."""

    return resolve_active_managed_agent_record(agent_identity, env=env, now=now)


def publish_live_agent_record(
    record: ManagedAgentRegistryRecordV3 | LiveAgentRegistryRecordV2,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ManagedAgentRegistryRecordV3:
    """Compatibility wrapper for active record publication."""

    return publish_managed_agent_record(record, env=env, now=now)


def remove_live_agent_record(
    agent_id: str,
    *,
    generation_id: str | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Compatibility wrapper for registry record deletion."""

    return remove_managed_agent_record(agent_id, generation_id=generation_id, env=env)


def cleanup_stale_live_agent_records(
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    grace_period: timedelta = DEFAULT_REGISTRY_CLEANUP_GRACE_PERIOD,
    dry_run: bool = False,
    probe_local_tmux: bool = True,
) -> RegistryCleanupResult:
    """Compatibility wrapper for lifecycle-aware stale-record cleanup."""

    return cleanup_stale_managed_agent_records(
        env=env,
        now=now,
        grace_period=grace_period,
        dry_run=dry_run,
        probe_local_tmux=probe_local_tmux,
    )


def is_live_agent_record_fresh(
    record: ManagedAgentRegistryRecordV3,
    *,
    now: datetime | None = None,
) -> bool:
    """Compatibility wrapper for active lease freshness checks."""

    return is_managed_agent_record_fresh(record, now=now)


def _coerce_publish_record(
    record: ManagedAgentRegistryRecordV3 | LiveAgentRegistryRecordV2,
) -> ManagedAgentRegistryRecordV3:
    """Normalize one publish request onto the lifecycle-aware registry model."""

    if isinstance(record, ManagedAgentRegistryRecordV3):
        return record
    payload = record.model_dump(mode="json")
    return parse_managed_agent_registry_record(payload)
