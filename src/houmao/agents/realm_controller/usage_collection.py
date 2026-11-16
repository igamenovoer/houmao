"""Bound, restartable native JSONL accounting collection.

Discovery verifies provider ownership. Collection restores parser context before
the attachment boundary without charging it, and commits complete-record source
progress with accepted observations. Safe diagnostics expose coverage gaps.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, BinaryIO

from houmao.agents.realm_controller.usage_adapters import UsageAdapter
from houmao.agents.realm_controller.usage_adapters.dsh import (
    DshJournalError,
    inspect_dsh_journal,
    select_dsh_journal,
)
from houmao.agents.realm_controller.usage_models import (
    UsageCheckpoint,
    UsageCollectionHealth,
    UsageObservation,
    UsageSourceBinding,
    opaque_usage_reference,
)
from houmao.agents.realm_controller.usage_store import (
    UsageCheckpointConflictError,
    UsageStore,
)

USAGE_READ_BATCH_BYTES = 1 << 20
USAGE_MAX_SOURCE_BYTES = 4 << 20
_GUARD_BYTES = 4096


def complete_file_position(path: Path) -> int:
    """Return the byte boundary after the last complete JSONL record."""

    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        if not size:
            return 0
        handle.seek(max(0, size - USAGE_MAX_SOURCE_BYTES))
        tail = handle.read()
    index = tail.rfind(b"\n")
    return max(0, size - len(tail) + index + 1) if index >= 0 else 0


def source_file_identity(path: Path) -> str:
    """Identify a physical source without depending on its unfinished header."""

    stat = path.stat()
    return f"{stat.st_dev}:{stat.st_ino}"


def _physical_identity(value: str) -> str:
    """Accept earlier header-qualified identities when checking physical continuity."""

    return ":".join(value.split(":")[:2])


def _record_session(payload: dict[str, Any], provider: str) -> str | None:
    """Read explicit provider session identity without modifying parser state."""

    candidate = payload.get("sessionId") or payload.get("session_id")
    if provider == "dsh" and payload.get("type") == "session":
        candidate = payload.get("id")
    if provider == "codex":
        data = payload.get("payload")
        if payload.get("type") == "session_meta" and isinstance(data, dict):
            candidate = data.get("id") or data.get("thread_id")
        elif payload.get("type") == "token_usage_record" and isinstance(data, dict):
            candidate = data.get("thread_id")
        elif payload.get("type") == "thread.started":
            candidate = payload.get("thread_id")
    return candidate if isinstance(candidate, str) and candidate else None


def _kimi_owned(path: Path, root: Path, session_id: str) -> bool:
    """Match the session's exact role in qualified legacy or current layouts."""

    parts = path.relative_to(root).parts
    return (len(parts) == 3 and parts[1] == session_id and parts[2] == "wire.jsonl") or (
        len(parts) == 5
        and parts[1] == session_id
        and parts[2] == "agents"
        and parts[4] == "wire.jsonl"
    )


def discover_usage_sources(
    binding: UsageSourceBinding, *, diagnostics: list[str] | None = None
) -> list[Path]:
    """Discover verified session-owned JSONL files inside the bound provider home."""

    if not binding.provider_session_id:
        return []
    notices = diagnostics if diagnostics is not None else []
    home = Path(binding.home_path).resolve()
    if binding.provider == "dsh":
        configured_root = binding.metadata.get("persistence_root")
        root = (
            Path(configured_root).resolve()
            if isinstance(configured_root, str)
            else home / "sessions"
        )
        if not root.is_relative_to(home):
            notices.append("dsh_journal_source_outside_bound_root")
            return []
        try:
            path = select_dsh_journal(root, binding.provider_session_id)
            dsh_paths = [path] if path is not None else []
            descendants = binding.metadata.get("dsh_descendant_sessions", {})
            if isinstance(descendants, dict):
                for child, parent in descendants.items():
                    if not isinstance(child, str) or not isinstance(parent, str):
                        continue
                    try:
                        child_path = select_dsh_journal(root, child)
                        if child_path is None:
                            notices.append("dsh_descendant_journal_unavailable")
                            continue
                        info = inspect_dsh_journal(child_path, child)
                    except DshJournalError as exc:
                        notices.append(str(exc))
                        continue
                    if info.origin != "subagent" or info.parent_session_id != parent:
                        notices.append("dsh_descendant_journal_lineage_mismatch")
                        continue
                    dsh_paths.append(child_path)
            return dsh_paths
        except DshJournalError as exc:
            notices.append(str(exc))
            return []
        except OSError:
            notices.append("native_source_discovery_unreadable")
            return []
    roots = {
        "claude": (home / "projects",),
        "codex": (home / "sessions", home / "archived_sessions"),
        "kimi": (home / "sessions",),
    }.get(binding.provider, ())
    candidates: list[tuple[int, str, Path]] = []
    for rank, root in enumerate(roots):
        if not root.is_dir():
            continue
        try:
            for path in root.rglob("*.jsonl"):
                resolved = path.resolve()
                if not resolved.is_relative_to(home) or not resolved.is_file():
                    continue
                if binding.provider == "kimi":
                    if _kimi_owned(path, root, binding.provider_session_id):
                        candidates.append((rank, str(path.relative_to(root)), resolved))
                    continue
                try:
                    with resolved.open("rb") as handle:
                        remaining = USAGE_MAX_SOURCE_BYTES
                        for _ in range(128):
                            line = handle.readline(min(remaining, USAGE_READ_BATCH_BYTES))
                            remaining -= len(line)
                            if not line or not remaining:
                                break
                            try:
                                payload = json.loads(line)
                            except (ValueError, UnicodeError):
                                continue
                            if not isinstance(payload, dict):
                                continue
                            identity = _record_session(payload, binding.provider)
                            if identity is not None:
                                if identity == binding.provider_session_id:
                                    candidates.append((rank, str(path.relative_to(root)), resolved))
                                break
                except OSError:
                    notices.append("native_source_discovery_unreadable")
        except OSError:
            notices.append("native_source_discovery_unreadable")
    # An active rollout wins over the same relative path in archived_sessions.
    selected: dict[str, Path] = {}
    for _, relative, path in sorted(candidates):
        key = relative if binding.provider == "codex" else str(path)
        selected.setdefault(key, path)
    return list(dict.fromkeys(selected.values()))


def _guard_state(handle: BinaryIO, offset: int) -> dict[str, Any]:
    """Fingerprint fixed accepted prefix/tail bytes to detect in-place rewrites."""

    prefix_size = min(offset, _GUARD_BYTES)
    tail_start = max(0, offset - _GUARD_BYTES)
    handle.seek(0)
    prefix = handle.read(prefix_size)
    handle.seek(tail_start)
    tail = handle.read(offset - tail_start)
    return {
        "prefix_size": prefix_size,
        "prefix_hash": hashlib.sha256(prefix).hexdigest(),
        "tail_start": tail_start,
        "tail_size": len(tail),
        "tail_hash": hashlib.sha256(tail).hexdigest(),
    }


def _guards_match(handle: BinaryIO, checkpoint: UsageCheckpoint) -> bool:
    """Check accepted boundary bytes without hashing an unfinished first line."""

    guard = checkpoint.metadata.get("continuity_guard")
    if not isinstance(guard, dict):
        # Earlier checkpoints used a complete first-line hash in file_identity.
        pieces = checkpoint.file_identity.split(":", 2)
        if len(pieces) == 3 and pieces[2] != "partial":
            handle.seek(0)
            return hashlib.sha256(handle.readline(USAGE_READ_BATCH_BYTES)).hexdigest() == pieces[2]
        return True
    for start, size, name in (
        (0, guard.get("prefix_size"), "prefix_hash"),
        (guard.get("tail_start"), guard.get("tail_size"), "tail_hash"),
    ):
        if not isinstance(start, int) or not isinstance(size, int) or size < 0:
            return False
        handle.seek(start)
        data = handle.read(size)
        if len(data) != size or hashlib.sha256(data).hexdigest() != guard.get(name):
            return False
    return True


def _string_set(value: Any) -> set[str]:
    """Restore a validated set of private historical identity hashes."""

    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


def _key(*values: Any) -> str:
    """Hash logical accounting identities independently of source byte locations."""

    data = json.dumps(values, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def _turn_key(item: UsageObservation) -> str | None:
    """Identify a native turn only when the provider supplies an explicit key."""

    return (
        None
        if item.provider_turn_id is None
        else _key(item.provider, item.provider_session_id, item.provider_turn_id)
    )


def _request_key(item: UsageObservation) -> str | None:
    """Identify historical requests without assuming equal counters imply equality."""

    return (
        None
        if item.request_id is None
        else _key(item.provider, item.provider_session_id, item.provider_turn_id, item.request_id)
    )


def _variant_key(item: UsageObservation) -> str:
    """Recognize exact copied native evidence without losing improved snapshots."""

    return _key(
        item.provider,
        item.provider_session_id,
        item.provider_turn_id,
        item.kind,
        item.accounting_kind,
        item.request_id,
        item.lifecycle,
        item.values,
        item.coverage,
        None if item.request_id else item.timestamp_utc,
    )


def _parsed_time(value: str | None) -> datetime | None:
    """Parse an explicit timestamp for attachment-boundary exclusion only."""

    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except ValueError:
        return None


class UsageCollector:
    """Read a bound family while preserving transactional parser and source state."""

    def __init__(self) -> None:
        """Initialize an unbound collector."""

        self.m_store: UsageStore | None = None
        self.m_binding: UsageSourceBinding | None = None
        self.m_diagnostics: list[str] = []
        self.m_checkpoints: list[UsageCheckpoint] = []
        self.m_excluded_requests: set[str] = set()
        self.m_excluded_turns: set[str] = set()
        self.m_partial_turns: set[str] = set()
        self.m_seen_variants: set[str] = set()
        self.m_caught_up: bool = True
        self.m_source_pending: bool = False

    @classmethod
    def from_binding(cls, store: UsageStore, binding: UsageSourceBinding) -> UsageCollector:
        """Create a collector for a persisted binding in the same runtime."""

        if binding.runtime_session_id != store.runtime_session_id:
            raise ValueError("Usage source binding belongs to another runtime")
        instance = cls()
        instance.m_store = store
        instance.m_binding = binding
        persisted = store.get_binding(binding.binding_id)
        if persisted is None:
            store.put_binding(binding)
        elif (
            any(
                getattr(persisted, field) != getattr(binding, field)
                for field in (
                    "runtime_session_id",
                    "agent_id",
                    "provider",
                    "provider_session_id",
                    "collection_boundary",
                )
            )
            or Path(persisted.home_path).resolve() != Path(binding.home_path).resolve()
        ):
            raise ValueError("Usage source binding conflicts with durable ownership or boundary")
        return instance

    @property
    def diagnostics(self) -> list[str]:
        """Return safe diagnostics from the latest collection pass."""

        return list(dict.fromkeys(self.m_diagnostics))

    @property
    def caught_up(self) -> bool:
        """Return whether the last pass consumed all selected source evidence."""

        return self.m_caught_up

    def _load_family(self) -> None:
        """Restore cross-file exclusion evidence and committed native variants."""

        assert self.m_store is not None and self.m_binding is not None
        self.m_checkpoints = self.m_store.list_checkpoints(binding_id=self.m_binding.binding_id)
        self.m_excluded_requests = set()
        self.m_excluded_turns = set()
        self.m_partial_turns = set()
        for checkpoint in self.m_checkpoints:
            self.m_excluded_requests.update(
                _string_set(checkpoint.metadata.get("excluded_request_keys"))
            )
            self.m_excluded_turns.update(_string_set(checkpoint.metadata.get("excluded_turn_keys")))
            self.m_partial_turns.update(_string_set(checkpoint.metadata.get("partial_turn_keys")))
        self.m_seen_variants = {
            _variant_key(item)
            for item in self.m_store.list_observations(binding_id=self.m_binding.binding_id)
            if item.source_kind == "native_session_log"
        }

    def collect(self, *, max_batches: int = 1) -> list[UsageObservation]:
        """Collect bounded complete batches and retain explicit source limitations."""

        if isinstance(max_batches, bool) or max_batches < 1:
            raise ValueError("Usage collection requires a positive batch bound")
        assert self.m_store is not None and self.m_binding is not None
        self.m_diagnostics = []
        self.m_caught_up = True
        self._load_family()
        paths = discover_usage_sources(self.m_binding, diagnostics=self.m_diagnostics)
        if not paths:
            self.m_diagnostics.append("native_source_unavailable")
            self.m_caught_up = False
        accepted: list[UsageObservation] = []
        for path in paths:
            batches = 0
            retries = 0
            advanced = False
            while batches < max_batches:
                self.m_source_pending = False
                try:
                    batch, advanced = self._read_source(path)
                except UsageCheckpointConflictError:
                    retries += 1
                    if retries > 2:
                        self.m_diagnostics.append("native_checkpoint_contention")
                        self.m_source_pending = True
                        break
                    self._load_family()
                    continue
                except OSError:
                    self.m_diagnostics.append("native_source_unreadable")
                    self.m_source_pending = True
                    break
                accepted.extend(batch)
                batches += 1
                if not advanced:
                    break
            if advanced and batches >= max_batches:
                self.m_diagnostics.append("native_collection_backlog")
                self.m_caught_up = False
            if self.m_source_pending:
                self.m_caught_up = False
        if self.m_diagnostics:
            self.m_store.set_collection_health(
                UsageCollectionHealth(
                    status="degraded",
                    updated_at_utc=datetime.now(UTC).isoformat(),
                    diagnostics=self.diagnostics,
                )
            )
        return accepted

    def _read_source(self, path: Path) -> tuple[list[UsageObservation], bool]:
        """Parse and atomically checkpoint one source batch."""

        assert self.m_store is not None and self.m_binding is not None
        binding = self.m_binding
        source_id = opaque_usage_reference(str(path))
        current = self.m_store.get_checkpoint(binding.binding_id, source_id)
        with path.open("rb") as handle:
            stat = os.fstat(handle.fileno())
            identity = f"{stat.st_dev}:{stat.st_ino}"
            previous = current
            if previous is None:
                aliases = [
                    checkpoint
                    for checkpoint in self.m_checkpoints
                    if _physical_identity(checkpoint.file_identity) == identity
                    and stat.st_size >= checkpoint.offset
                    and _guards_match(handle, checkpoint)
                ]
                previous = max(aliases, key=lambda item: item.offset, default=None)
            replaced = previous is not None and (
                _physical_identity(previous.file_identity) != identity
                or stat.st_size < previous.offset
                or not _guards_match(handle, previous)
            )
            if previous is not None:
                skipped = previous.metadata.get("oversized_scan_offset")
                if isinstance(skipped, int) and skipped > stat.st_size:
                    replaced = True
            notices = list(previous.diagnostics) if previous is not None else []
            metadata = dict(previous.metadata) if previous is not None else {}
            epoch = previous.counter_epoch if previous is not None else binding.counter_epoch
            offset = previous.offset if previous is not None and not replaced else 0
            if replaced:
                notices.append("native_source_replaced_or_truncated")
                epoch = (
                    "discontinuous-"
                    + _key(
                        identity,
                        previous.version if previous else 0,
                        previous.counter_epoch if previous else binding.counter_epoch,
                    )[:24]
                )
                metadata.pop("oversized_scan_offset", None)
            adapter = UsageAdapter.from_provider(
                binding.provider,
                provider_session_id=binding.provider_session_id,
                profile_id=binding.profile_id if binding.profile_id != "unknown" else None,
            )
            source_session_id = binding.provider_session_id
            if binding.provider == "dsh":
                try:
                    info = inspect_dsh_journal(path, None)
                except DshJournalError as exc:
                    self.m_diagnostics.append(str(exc))
                    self.m_source_pending = True
                    return [], False
                if info.session_id != binding.provider_session_id:
                    descendants = binding.metadata.get("dsh_descendant_sessions", {})
                    if (
                        not isinstance(descendants, dict)
                        or info.origin != "subagent"
                        or descendants.get(info.session_id) != info.parent_session_id
                    ):
                        self.m_diagnostics.append("dsh_descendant_journal_lineage_mismatch")
                        return [], False
                    source_session_id = info.session_id
                    adapter = UsageAdapter.from_provider(
                        binding.provider,
                        provider_session_id=source_session_id,
                        profile_id=binding.profile_id if binding.profile_id != "unknown" else None,
                    )
            if previous is not None and not replaced:
                state = metadata.get("adapter_state")
                if isinstance(state, dict):
                    try:
                        adapter.restore_state(state)
                    except ValueError:
                        notices.append("native_checkpoint_state_invalid")
                        epoch = "discontinuous-" + _key(identity, previous.version, "state")[:24]
                        offset = 0
                        replaced = True
            if replaced:
                metadata.pop("oversized_scan_offset", None)
                for key in (
                    "baseline_source_ids",
                    "baseline_observations",
                    "attachment_baseline",
                    "attachment_baseline_source_ids",
                    "attachment_baseline_observations",
                ):
                    metadata.pop(key, None)
            try:
                adapter.configure_native_source(path)
            except DshJournalError as exc:
                self.m_diagnostics.append(str(exc))
                self.m_source_pending = True
                return [], False
            # Complete records are bounded. An oversized record is skipped in
            # bounded scans, retaining the last complete checkpoint until its LF.
            scan = metadata.get("oversized_scan_offset")
            scan_offset = scan if isinstance(scan, int) and scan >= offset else offset
            handle.seek(scan_offset)
            data = handle.read(USAGE_READ_BATCH_BYTES)
            if b"\n" not in data and len(data) == USAGE_READ_BATCH_BYTES:
                data += handle.read(max(0, USAGE_MAX_SOURCE_BYTES - len(data)))
            end = data.rfind(b"\n")
            if end < 0:
                if not data:
                    self.m_source_pending = scan_offset > offset
                    self.m_diagnostics.extend(notices)
                    return [], False
                if len(data) == USAGE_MAX_SOURCE_BYTES or scan_offset > offset:
                    notices.append("native_record_exceeds_read_bound")
                    metadata["oversized_scan_offset"] = scan_offset + len(data)
                    metadata["coverage_gap"] = True
                    metadata["adapter_state"] = adapter.snapshot_state()
                    checkpoint = UsageCheckpoint(
                        binding_id=binding.binding_id,
                        source_id=source_id,
                        file_identity=identity,
                        offset=offset,
                        counter_epoch=epoch,
                        baseline=dict(adapter.snapshot_state().get("previous_totals", {})),
                        diagnostics=list(dict.fromkeys(notices)),
                        metadata=metadata,
                    )
                    self.m_store.ingest_batch(
                        checkpoint=checkpoint,
                        observations=[],
                        expected_version=current.version if current else 0,
                    )
                    self.m_diagnostics.extend(notices)
                    self._load_family()
                    self.m_source_pending = True
                    return [], bool(data)
                self.m_source_pending = True
                self.m_diagnostics.append("native_source_partial_record")
                self.m_diagnostics.extend(notices)
                return [], False
            complete = data[: end + 1]
            position = scan_offset
            if scan_offset > offset:
                first_lf = complete.index(b"\n") + 1
                position += first_lf
                complete = complete[first_lf:]
                notices.append("native_record_exceeds_read_bound")
                metadata.pop("oversized_scan_offset", None)
            boundary = binding.collection_boundary.get(source_id, 0)
            if previous is not None:
                saved = previous.metadata.get("attachment_boundary")
                if isinstance(saved, int):
                    boundary = saved
            if replaced:
                boundary = 0
            established = (
                source_id in binding.collection_boundary
                or previous is not None
                or bool(binding.metadata.get("fresh_session"))
                or (binding.provider == "dsh" and source_session_id != binding.provider_session_id)
            )
            excluded_requests = set(self.m_excluded_requests)
            excluded_turns = set(self.m_excluded_turns)
            partial_turns = set(self.m_partial_turns)
            new_variants: set[str] = set()
            observations: list[UsageObservation] = []
            attachment_baseline = metadata.get("attachment_baseline")
            baseline_sources = dict(metadata.get("baseline_source_ids", {}))
            baseline_observations = dict(metadata.get("baseline_observations", {}))
            gap = bool(metadata.get("coverage_gap")) or replaced
            for line in complete.splitlines(keepends=True):
                start = position
                position += len(line)
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        raise ValueError("not an object")
                    session = _record_session(payload, binding.provider)
                    if session is not None and session != source_session_id:
                        notices.append("native_session_identity_mismatch")
                        gap = True
                        continue
                    parsed = adapter.parse(
                        payload,
                        source_ref=f"{source_id}:{start}",
                        source_kind="native_session_log",
                        binding_id=binding.binding_id,
                    )
                except (ValueError, UnicodeError):
                    notices.append("native_accounting_record_invalid")
                    gap = True
                    continue
                for observation in parsed:
                    if observation.provider_session_id not in {None, source_session_id}:
                        notices.append("native_session_identity_mismatch")
                        gap = True
                        continue
                    turn_key = _turn_key(observation)
                    request_key = _request_key(observation)
                    if (
                        observation.kind == "cumulative"
                        and observation.measurement_scope == "session_cumulative"
                    ):
                        for metric, value in observation.values.items():
                            if value is not None:
                                baseline_sources[metric] = [f"{source_id}:{start}"]
                                baseline_observations[metric] = observation.model_dump(mode="json")
                    historical = start < boundary
                    if not established and not historical:
                        started = _parsed_time(binding.started_at_utc)
                        recorded = _parsed_time(observation.timestamp_utc)
                        if started is not None and recorded is not None:
                            historical = recorded < started
                        elif (
                            request_key not in excluded_requests and turn_key not in excluded_turns
                        ):
                            notices.append("native_attachment_boundary_unverified")
                            # Keep evidence unchargeable when a newly discovered
                            # copy lacks an established attachment boundary.
                            historical = True
                    if historical:
                        if request_key is not None:
                            excluded_requests.add(request_key)
                        if turn_key is not None:
                            if observation.lifecycle == "started":
                                partial_turns.add(turn_key)
                            elif observation.lifecycle in {"completed", "failed", "interrupted"}:
                                partial_turns.discard(turn_key)
                                excluded_turns.add(turn_key)
                        continue
                    if request_key in excluded_requests or turn_key in excluded_turns:
                        continue
                    if observation.lifecycle == "started":
                        gap = False
                    updates: dict[str, Any] = {
                        "source_ref": f"{source_id}:{start}",
                        "metadata": {
                            **observation.metadata,
                            "source_id": source_id,
                            "source_offset": start,
                            "source_end": position,
                            "counter_epoch": epoch,
                            "generation_id": binding.metadata.get(
                                "collection_generation_id", binding.generation_id
                            ),
                        },
                    }
                    if observation.lifecycle == "started":
                        updates["metadata"]["baseline"] = {
                            **(binding.baseline if epoch == binding.counter_epoch else {}),
                            **dict(adapter.snapshot_state().get("previous_totals", {})),
                        }
                        updates["metadata"]["baseline_source_ids"] = dict(baseline_sources)
                    if gap or turn_key in partial_turns:
                        updates["coverage"] = "partial"
                    accepted = observation.model_copy(update=updates)
                    fingerprint = _variant_key(accepted)
                    covered_variants = {fingerprint}
                    stronger = {
                        "unknown": ("partial", "complete"),
                        "partial": ("complete",),
                    }.get(accepted.coverage, ())
                    covered_variants.update(
                        _variant_key(accepted.model_copy(update={"coverage": coverage}))
                        for coverage in stronger
                    )
                    if covered_variants.intersection(self.m_seen_variants | new_variants):
                        continue
                    observations.append(accepted)
                    new_variants.add(fingerprint)
                if attachment_baseline is None and position >= boundary and start < boundary:
                    attachment_baseline = dict(adapter.snapshot_state().get("previous_totals", {}))
                    metadata["attachment_baseline_source_ids"] = dict(baseline_sources)
                    metadata["attachment_baseline_observations"] = dict(baseline_observations)
            state = adapter.snapshot_state()
            metadata.update(
                {
                    "adapter_state": state,
                    "attachment_boundary": boundary,
                    "attachment_baseline": attachment_baseline,
                    "baseline_source_ids": baseline_sources,
                    "baseline_observations": baseline_observations,
                    "continuity_guard": _guard_state(handle, position),
                    "coverage_gap": gap,
                    "excluded_request_keys": sorted(excluded_requests),
                    "excluded_turn_keys": sorted(excluded_turns),
                    "partial_turn_keys": sorted(partial_turns),
                }
            )
            current_size = os.fstat(handle.fileno()).st_size
        checkpoint = UsageCheckpoint(
            binding_id=binding.binding_id,
            source_id=source_id,
            file_identity=identity,
            offset=position,
            counter_epoch=epoch,
            baseline=dict(state.get("previous_totals", {})),
            diagnostics=list(dict.fromkeys(notices)),
            metadata=metadata,
        )
        self.m_store.ingest_batch(
            checkpoint=checkpoint,
            observations=observations,
            expected_version=current.version if current else 0,
        )
        if isinstance(attachment_baseline, dict) and attachment_baseline:
            saved_binding = self.m_store.get_binding(binding.binding_id)
            if saved_binding is not None and not saved_binding.baseline:
                self.m_store.put_binding(
                    saved_binding.model_copy(update={"baseline": attachment_baseline})
                )
        self.m_diagnostics.extend(notices)
        self._load_family()
        return observations, position < current_size
