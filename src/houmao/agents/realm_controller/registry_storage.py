"""Filesystem storage helpers for the shared live-agent registry."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Mapping

import platformdirs
from pydantic import ValidationError

from houmao.agents.realm_controller.errors import SchemaValidationError, SessionManifestError
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV1,
    canonicalize_registry_agent_name,
    derive_agent_key,
    format_registry_validation_error,
)
from houmao.agents.realm_controller.schema_validation import validate_payload

AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR = "AGENTSYS_GLOBAL_REGISTRY_DIR"
DEFAULT_REGISTRY_LEASE_TTL = timedelta(hours=24)
DEFAULT_REGISTRY_CLEANUP_GRACE_PERIOD = timedelta(minutes=5)
LIVE_AGENT_REGISTRY_SCHEMA = "live_agent_registry_record.v1.schema.json"


@dataclass(frozen=True)
class GlobalRegistryPaths:
    """Resolved filesystem layout for the shared live-agent registry."""

    root: Path
    live_agents_dir: Path


@dataclass(frozen=True)
class RegistryCleanupResult:
    """Summary of one stale-registry cleanup pass."""

    registry_root: Path
    removed_agent_keys: tuple[str, ...]
    preserved_agent_keys: tuple[str, ...]
    failed_agent_keys: tuple[str, ...]


def resolve_global_registry_root(*, env: Mapping[str, str] | None = None) -> Path:
    """Resolve the effective shared-registry root."""

    env_mapping = os.environ if env is None else env
    override = env_mapping.get(AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR)
    if override is not None and override.strip():
        override_path = Path(override)
        if not override_path.is_absolute():
            raise SessionManifestError(
                f"`{AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR}` must be an absolute path."
            )
        return override_path.resolve()

    return (_resolve_home_anchor_from_platformdirs() / ".houmao" / "registry").resolve()


def global_registry_paths(*, env: Mapping[str, str] | None = None) -> GlobalRegistryPaths:
    """Return the resolved shared-registry directory layout."""

    root = resolve_global_registry_root(env=env)
    return GlobalRegistryPaths(root=root, live_agents_dir=(root / "live_agents").resolve())


def new_registry_generation_id() -> str:
    """Return a new stable generation id for one live session."""

    return str(uuid.uuid4())


def record_path_for_agent_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Return the shared-registry `record.json` path for one agent name."""

    canonical_name = canonicalize_registry_agent_name(agent_name)
    key = derive_agent_key(canonical_name)
    paths = global_registry_paths(env=env)
    return (paths.live_agents_dir / key / "record.json").resolve()


def load_live_agent_record(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
) -> LiveAgentRegistryRecordV1 | None:
    """Load one strict registry record regardless of freshness."""

    path = record_path_for_agent_name(agent_name, env=env)
    if not path.is_file():
        return None
    return _read_live_agent_record(path)


def resolve_live_agent_record(
    agent_name: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> LiveAgentRegistryRecordV1 | None:
    """Resolve one fresh registry record by canonical or unprefixed agent name."""

    canonical_name = canonicalize_registry_agent_name(agent_name)
    try:
        record = load_live_agent_record(canonical_name, env=env)
    except SessionManifestError:
        return None
    if record is None:
        return None
    if record.agent_name != canonical_name:
        return None
    if not is_live_agent_record_fresh(record, now=now):
        return None
    return record


def publish_live_agent_record(
    record: LiveAgentRegistryRecordV1,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> LiveAgentRegistryRecordV1:
    """Publish or refresh one shared live-agent record atomically."""

    current_time = _coerce_now(now)
    if not is_live_agent_record_fresh(record, now=current_time):
        raise SessionManifestError("Refusing to publish a record with an already-expired lease.")

    existing = load_live_agent_record(record.agent_name, env=env)
    _raise_if_conflicting_fresh_generation(
        existing=existing,
        desired=record,
        now=current_time,
    )

    payload = record.model_dump(mode="json")
    try:
        validate_payload(payload, LIVE_AGENT_REGISTRY_SCHEMA)
    except SchemaValidationError as exc:
        raise SessionManifestError(
            "Shared registry record schema validation failed before publish for "
            f"`{record.agent_name}`: {exc}"
        ) from exc

    path = record_path_for_agent_name(record.agent_name, env=env)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomically(path, payload)

    observed = load_live_agent_record(record.agent_name, env=env)
    if observed is None:
        raise SessionManifestError(
            f"Registry publish verification failed for `{record.agent_name}`."
        )
    _raise_if_conflicting_fresh_generation(
        existing=observed,
        desired=record,
        now=current_time,
        post_publish_check=True,
    )
    return observed


def remove_live_agent_record(
    agent_name: str,
    *,
    generation_id: str | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Remove one live-agent registry directory when it still belongs to the caller."""

    path = record_path_for_agent_name(agent_name, env=env)
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
) -> RegistryCleanupResult:
    """Remove stale or malformed `live_agents/` directories beyond the grace period."""

    current_time = _coerce_now(now)
    paths = global_registry_paths(env=env)
    if not paths.live_agents_dir.exists():
        return RegistryCleanupResult(
            registry_root=paths.root,
            removed_agent_keys=(),
            preserved_agent_keys=(),
            failed_agent_keys=(),
        )

    removed: list[str] = []
    preserved: list[str] = []
    failed: list[str] = []
    for candidate in sorted(paths.live_agents_dir.iterdir()):
        if not candidate.is_dir():
            continue

        record_path = candidate / "record.json"
        should_remove = not record_path.is_file()
        if not should_remove:
            try:
                record = _read_live_agent_record(record_path)
            except SessionManifestError:
                should_remove = True
            else:
                should_remove = _record_expired_beyond_grace(
                    record,
                    now=current_time,
                    grace_period=grace_period,
                )

        if should_remove:
            try:
                shutil.rmtree(candidate, ignore_errors=False)
            except OSError:
                failed.append(candidate.name)
            else:
                removed.append(candidate.name)
            continue

        preserved.append(candidate.name)

    return RegistryCleanupResult(
        registry_root=paths.root,
        removed_agent_keys=tuple(removed),
        preserved_agent_keys=tuple(preserved),
        failed_agent_keys=tuple(failed),
    )


def is_live_agent_record_fresh(
    record: LiveAgentRegistryRecordV1,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether a record's lease remains live at the provided time."""

    lease_expires_at = _parse_timestamp(record.lease_expires_at)
    return lease_expires_at >= _coerce_now(now)


def _resolve_home_anchor_from_platformdirs() -> Path:
    """Infer the current user's home anchor from a platformdirs-managed path."""

    user_data_path = Path(platformdirs.user_data_path(appname="houmao", appauthor=False))
    parts = user_data_path.parts

    if "AppData" in parts:
        index = parts.index("AppData")
        return Path(*parts[:index]).resolve()

    if "Library" in parts:
        index = parts.index("Library")
        return Path(*parts[:index]).resolve()

    if ".local" in parts:
        index = parts.index(".local")
        return Path(*parts[:index]).resolve()

    return Path.home().expanduser().resolve()


def _raise_if_conflicting_fresh_generation(
    *,
    existing: LiveAgentRegistryRecordV1 | None,
    desired: LiveAgentRegistryRecordV1,
    now: datetime,
    post_publish_check: bool = False,
) -> None:
    """Reject a publish attempt when another fresh generation already owns the name."""

    if existing is None:
        return
    if not is_live_agent_record_fresh(existing, now=now):
        return
    if existing.generation_id == desired.generation_id:
        return

    conflict_context = "after publish verification" if post_publish_check else "before publish"
    raise SessionManifestError(
        "Shared-registry ownership conflict for "
        f"`{desired.agent_name}` {conflict_context}: fresh generation "
        f"`{existing.generation_id}` already owns that logical name, "
        f"so generation `{desired.generation_id}` must stand down."
    )


def _record_expired_beyond_grace(
    record: LiveAgentRegistryRecordV1,
    *,
    now: datetime,
    grace_period: timedelta,
) -> bool:
    """Return whether a record lease expired earlier than the cleanup grace period."""

    return _parse_timestamp(record.lease_expires_at) + grace_period < now


def _read_live_agent_record(path: Path) -> LiveAgentRegistryRecordV1:
    """Load and validate one registry record from disk."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise SessionManifestError(f"Invalid JSON in registry record `{path}`.") from exc

    try:
        return LiveAgentRegistryRecordV1.model_validate(payload)
    except ValidationError as exc:
        raise SessionManifestError(
            format_registry_validation_error(
                f"Shared registry record validation failed for {path}",
                exc,
            )
        ) from exc


def _write_json_atomically(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON payload atomically beneath the target directory."""

    temp_path = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        temp_path.replace(path)
    except OSError:
        temp_path.unlink(missing_ok=True)
        raise


def _parse_timestamp(value: str) -> datetime:
    """Parse one ISO-8601 timestamp into an aware UTC datetime."""

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _coerce_now(now: datetime | None) -> datetime:
    """Return an aware UTC timestamp for freshness checks."""

    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)
