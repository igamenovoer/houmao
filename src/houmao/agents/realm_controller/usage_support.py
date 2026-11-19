"""Shared lifecycle, collection, and immutable accounting recovery support.

The service is owned by a runtime session rather than a gateway process. Public
reads use indexed finalized rows; native collection and artifact recovery run
on lifecycle boundaries or the service's cancellable background worker.
"""

from __future__ import annotations

import hashlib
import fcntl
import json
import logging
import os
import threading
import uuid
from datetime import UTC, datetime
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal, cast

from houmao.agents.realm_controller.models import LaunchPlan
from houmao.agents.realm_controller.dsh_web_usage import (
    assemble_web_usage,
    stage_web_evidence,
    web_identity,
)
from houmao.agents.realm_controller.usage_adapters import UsageAdapter
from houmao.agents.realm_controller.usage_adapters.codex_service import read_codex_service_usage
from houmao.agents.realm_controller.usage_adapters.dsh import (
    DshJournalError,
    dsh_cli_completion_evidence,
    read_dsh_interval,
)
from houmao.agents.realm_controller.usage_adapters.kimi_service import read_kimi_service_usage
from houmao.agents.realm_controller.usage_collection import (
    UsageCollector,
    complete_file_position,
    discover_usage_sources,
)
from houmao.agents.realm_controller.usage_models import (
    UsageCapability,
    UsageCheckpoint,
    UsageCollectionHealth,
    UsageFinalization,
    UsageObservation,
    UsagePage,
    UsageRecord,
    UsageSourceBinding,
    UsageTurnSnapshot,
    opaque_usage_reference,
)
from houmao.agents.realm_controller.usage_store import (
    UsageStore,
    UsageStoreError,
)
from houmao.hook_observation.reader import HookObservationReader

_LOGGER = logging.getLogger(__name__)
_PROVIDERS = {"claude", "codex", "kimi", "dsh"}
_SERVICE_JOURNAL_READERS = {
    "kimi_acp": ("kimi-native-turn.json", read_kimi_service_usage),
    "kimi_web": ("kimi-native-turn.json", read_kimi_service_usage),
    "codex_app_server": ("codex-native-turn.json", read_codex_service_usage),
}
_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


def _now() -> str:
    """Return an unambiguous timestamp for lifecycle evidence."""

    return datetime.now(UTC).isoformat()


def _artifact_accounting_backend(backend: str) -> bool:
    """Identify backends that settle usage through managed request artifacts."""

    return (
        backend.endswith("_headless") or backend == "dsh_acp" or backend in _SERVICE_JOURNAL_READERS
    )


def _dsh_link_descendant(
    item: UsageObservation, snapshot: UsageTurnSnapshot
) -> UsageObservation | None:
    """Associate only native child turns proven inside this managed ACP interval."""

    children = snapshot.metadata.get("native_descendant_turns", {})
    if not isinstance(children, dict):
        return None
    turns = children.get(item.provider_session_id)
    if not isinstance(turns, list) or item.provider_turn_id not in turns:
        return None
    return item.model_copy(
        update={
            "parent_turn_id": snapshot.turn_id,
            "turn_id": snapshot.turn_id,
            "is_sidechain": True,
            "metadata": {
                **item.metadata,
                "child_id": item.provider_session_id,
                "included_in_parent": False,
            },
        }
    )


def write_usage_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically persist private accounting state with durable replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    """Load a private JSON object without returning non-mapping content."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Accounting state must contain a JSON object")
    return value


@contextmanager
def _artifact_finalization_lock(turn_dir: Path) -> Iterator[None]:
    """Serialize sidecar cutoff/cache writes across independent controllers."""

    turn_dir.mkdir(parents=True, exist_ok=True)
    with (turn_dir / ".usage-finalization.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def persist_terminal_evidence(
    turn_dir: Path,
    *,
    returncode: int,
    completed_at_utc: str,
    wall_time_ms: float | None,
    interrupted: bool = False,
) -> None:
    """Preserve original terminal facts before an accounting store write."""

    if not (turn_dir / "usage-start.json").exists():
        return
    with _artifact_finalization_lock(turn_dir):
        path = turn_dir / "usage-final.json"
        if path.exists():
            return
        finalization = UsageFinalization(
            turn_id=turn_dir.name,
            outcome="completed" if returncode == 0 else "interrupted" if interrupted else "failed",
            completed_at_utc=completed_at_utc,
            wall_time_ms=wall_time_ms,
            returncode=returncode,
            interrupted=interrupted,
        )
        write_usage_json(path, finalization.model_dump(mode="json"))


def headless_artifact_process_alive(turn_dir: Path) -> bool:
    """Check recorded process liveness, rejecting obvious PID reuse on Linux."""

    if (turn_dir / "exitcode").exists():
        return False
    try:
        metadata = _read_json(turn_dir / "process.json")
        pid = metadata.get("child_pid")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            return False
        os.kill(pid, 0)
        birth = metadata.get("child_birth_token")
        if birth is not None:
            from houmao.agents.realm_controller.backends.dispatch_control import (
                _dispatch_origin_birth_token,
            )

            return isinstance(birth, str) and _dispatch_origin_birth_token(pid) == birth
        proc = Path(f"/proc/{pid}/stat")
        if proc.exists():
            fields = proc.read_text().rsplit(")", 1)[1].split()
            if fields[0] == "Z":
                return False
            launched = metadata.get("launched_at_utc")
            if isinstance(launched, str):
                boot = next(
                    int(line.split()[1])
                    for line in Path("/proc/stat").read_text().splitlines()
                    if line.startswith("btime ")
                )
                process_start = boot + int(fields[19]) / os.sysconf("SC_CLK_TCK")
                expected = datetime.fromisoformat(launched.replace("Z", "+00:00")).timestamp()
                if abs(process_start - expected) > 10:
                    return False
        return True
    except PermissionError:
        return True
    except (OSError, ValueError, KeyError, IndexError, StopIteration):
        return False


class UsageService:
    """Coordinate one manifest-owned accounting ledger and bound collector."""

    def __init__(self) -> None:
        """Initialize a service without performing source I/O."""

        self.m_manifest_path: Path = Path()
        self.m_session_root: Path = Path()
        self.m_runtime_session_id: str = ""
        self.m_agent_id: str = ""
        self.m_backend: str = ""
        self.m_provider: str = ""
        self.m_home_path: Path = Path()
        self.m_generation_id: str | None = None
        self.m_service_incarnation: str | None = None
        self.m_service_working_directory: str | None = None
        self.m_provider_session_id: str | None = None
        self.m_store: UsageStore | None = None
        self.m_capability: UsageCapability = UsageCapability(
            reasons=["provider_identity_unavailable"]
        )
        self.m_health: UsageCollectionHealth = UsageCollectionHealth(status="unavailable")
        self.m_stop: threading.Event = threading.Event()
        self.m_thread: threading.Thread | None = None
        self.m_lock: threading.RLock = threading.RLock()
        self.m_hook_reader: HookObservationReader | None = None
        self.m_hook_initial: bool = True
        self.m_active_binding_id: str | None = None
        self.m_hook_session_id: str | None = None
        self.m_native_caught_up: bool = True

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> UsageService:
        """Create a service using safe manifest-owned identity and source roots."""

        instance = cls()
        instance.m_manifest_path = Path(manifest_path).resolve()
        instance.m_session_root = instance.m_manifest_path.parent
        instance._refresh_manifest()
        return instance

    @classmethod
    def from_launch(
        cls, manifest_path: Path, launch_plan: LaunchPlan, provider_session_id: str | None
    ) -> UsageService:
        """Create execution support before a first manifest has been persisted."""

        instance = cls.from_manifest(manifest_path)
        instance.m_provider = launch_plan.tool
        instance.m_backend = launch_plan.backend
        instance.m_home_path = launch_plan.home_path.resolve()
        instance.m_provider_session_id = provider_session_id
        if not instance.m_runtime_session_id:
            instance.m_runtime_session_id = instance.m_session_root.name
        if not instance.m_agent_id:
            instance.m_agent_id = (
                launch_plan.env.get("HOUMAO_AGENT_ID") or instance.m_runtime_session_id
            )
        return instance

    @property
    def store_path(self) -> Path:
        """Return the independent runtime-owned ledger location."""

        return self.m_session_root / "usage" / "records.sqlite3"

    @property
    def store(self) -> UsageStore:
        """Open the supported current-schema ledger on first accounting access."""

        if not self.m_runtime_session_id:
            raise UsageStoreError("Runtime accounting identity is unavailable")
        if self.m_store is None:
            self.m_store = UsageStore.from_path(self.store_path, self.m_runtime_session_id)
        return self.m_store

    def _refresh_manifest(self) -> None:
        """Refresh only manifest identities, never provider-log data."""

        try:
            payload = _read_json(self.m_manifest_path)
        except (OSError, ValueError):
            return
        runtime = payload.get("runtime") or {}
        plan = payload.get("launch_plan") or {}
        state = payload.get("backend_state") or {}
        if (
            not isinstance(runtime, dict)
            or not isinstance(plan, dict)
            or not isinstance(state, dict)
        ):
            return
        selector = plan.get("home_selector") or {}
        self.m_provider = str(payload.get("tool", plan.get("tool", "")))
        self.m_backend = str(payload.get("backend", plan.get("backend", "")))
        runtime_id = str(runtime.get("session_id") or self.m_session_root.name)
        if self.m_store is not None and runtime_id != self.m_runtime_session_id:
            raise UsageStoreError("Manifest changed the runtime accounting identity")
        self.m_runtime_session_id = runtime_id
        self.m_agent_id = str(
            payload.get("agent_id") or payload.get("agent_name") or self.m_runtime_session_id
        )
        generation = payload.get("registry_generation_id") or runtime.get("registry_generation_id")
        self.m_generation_id = generation if isinstance(generation, str) else None
        web_identity = state.get("web_identity")
        incarnation = state.get("service_incarnation")
        if self.m_backend == "kimi_web" and isinstance(web_identity, dict):
            incarnation = web_identity.get("host_incarnation")
        self.m_service_incarnation = incarnation if isinstance(incarnation, str) else None
        workspace = payload.get("working_directory")
        self.m_service_working_directory = workspace if isinstance(workspace, str) else None
        provider_id = (
            state.get("session_id") or state.get("thread_id") or state.get("native_session_id")
        )
        if self.m_backend in {"dsh_web", "kimi_web"} and isinstance(web_identity, dict):
            provider_id = web_identity.get("native_session_id") or provider_id
        for section in ("headless", "local_interactive", "codex"):
            data = payload.get(section)
            if isinstance(data, dict):
                provider_id = provider_id or data.get("session_id") or data.get("thread_id")
        if isinstance(provider_id, str) and provider_id:
            self.m_provider_session_id = provider_id
        if isinstance(selector, dict) and isinstance(selector.get("home_path"), str):
            self.m_home_path = Path(selector["home_path"]).resolve()

    def get_usage(self, *, after: str | None = None, limit: int = 100) -> UsagePage:
        """Read bounded finalized rows without collecting or scanning sources."""

        if not 1 <= limit <= 500:
            raise ValueError("Usage page limit must be between 1 and 500")
        queryable = bool(self.m_runtime_session_id) and (
            self.store_path.exists() or _artifact_accounting_backend(self.m_backend)
        )
        if not queryable:
            if after is not None:
                raise ValueError("No accounting stream exists for this cursor")
            return UsagePage(
                runtime_session_id=self.m_runtime_session_id or None,
                capability=self.m_capability,
                collection=self.m_health,
            )
        health = self.store.get_collection_health()
        capability = self.m_capability
        if _artifact_accounting_backend(self.m_backend) and not capability.turn_recording:
            service_journal = self.m_backend in _SERVICE_JOURNAL_READERS
            verified_service = service_journal and health.status == "healthy"
            capability = UsageCapability(
                status="available" if verified_service else "partial",
                turn_recording=True,
                source_kinds=["native_session_log" if service_journal else "structured_output"],
                reasons=[] if verified_service else ["provider_metrics_depend_on_evidence"],
            )
        return self.store.read_page(
            after=after,
            limit=limit,
            capability=capability,
            collection=health if health.updated_at_utc is not None else self.m_health,
        )

    def start(self) -> None:
        """Start cancellable collection and recovery away from public reads."""

        if self.m_thread is not None and self.m_thread.is_alive():
            return
        if self.m_provider not in _PROVIDERS or not self.m_runtime_session_id:
            return
        self.m_stop.clear()
        self.m_thread = threading.Thread(
            target=self._run, daemon=True, name="houmao-usage-collector"
        )
        self.m_thread.start()

    def stop(self) -> None:
        """Stop this service's worker without deleting shared accounting state."""

        self.m_stop.set()
        if self.m_thread is not None and self.m_thread is not threading.current_thread():
            self.m_thread.join(timeout=5)

    def _run(self) -> None:
        """Recover once and then process bounded collection cycles."""

        try:
            self.reconcile()
        except (OSError, ValueError, UsageStoreError):
            self._degraded("usage_recovery_failed")
        while not self.m_stop.is_set():
            try:
                self.collect()
            except (OSError, ValueError, UsageStoreError):
                self._degraded("usage_collection_failed")
            self.m_stop.wait(0.25)

    def _degraded(self, diagnostic: str) -> None:
        """Expose safe collection diagnostics without leaking source paths."""

        self.m_health = UsageCollectionHealth(
            status="degraded", updated_at_utc=_now(), diagnostics=[diagnostic]
        )
        self.m_capability = self.m_capability.model_copy(
            update={"status": "partial", "reasons": [diagnostic]}
        )
        try:
            if self.store_path.exists():
                self.store.set_collection_health(self.m_health)
        except UsageStoreError:
            _LOGGER.warning("Usage collection health could not be persisted")

    def _binding(self, *, new_session: bool = False) -> UsageSourceBinding:
        """Resolve a stable provider-session binding and its initial source boundary."""

        active = (
            self.store.get_binding(self.m_active_binding_id) if self.m_active_binding_id else None
        )
        if active is not None and active.provider_session_id in {None, self.m_provider_session_id}:
            if active.provisional and self.m_provider_session_id:
                active = active.model_copy(
                    update={"provider_session_id": self.m_provider_session_id, "provisional": False}
                )
                self.store.put_binding(active)
            return active
        for binding in [] if new_session else self.store.list_bindings():
            if (
                binding.provider == self.m_provider
                and binding.provider_session_id == self.m_provider_session_id
            ):
                self.m_active_binding_id = binding.binding_id
                return binding
        provisional_key = "pending-" + uuid.uuid4().hex
        key = f"{self.m_runtime_session_id}:{self.m_provider}:{self.m_provider_session_id or provisional_key}"
        binding = UsageSourceBinding(
            binding_id="binding-" + hashlib.sha256(key.encode()).hexdigest()[:24],
            agent_id=self.m_agent_id,
            runtime_session_id=self.m_runtime_session_id,
            provider=self.m_provider,
            home_path=str(self.m_home_path),
            provider_session_id=self.m_provider_session_id,
            generation_id=self.m_generation_id,
            started_at_utc=_now(),
            provisional=self.m_provider_session_id is None,
            baseline={name: 0 for name in (*_TOKEN_FIELDS, "cost_usd", "duration_api_ms")}
            if new_session
            else {},
            metadata={"fresh_session": new_session},
        )
        if not new_session and self.m_backend not in _SERVICE_JOURNAL_READERS:
            binding.collection_boundary = {
                opaque_usage_reference(str(path)): complete_file_position(path)
                for path in discover_usage_sources(binding)
            }
        self.store.put_binding(binding)
        self.m_active_binding_id = binding.binding_id
        return binding

    def bind_dsh_web(
        self, *, identity: dict[str, Any], evidence_path: Path, new_session: bool = False
    ) -> UsageSourceBinding:
        """Persist the verified startup boundary before publishing browser authority.

        A restored conversation reuses its original binding and checkpoints.
        New host identities authorize additional metadata without moving that
        boundary or rewriting the generation of an existing usage record.
        """

        verified = web_identity(identity)
        with self.m_lock, _artifact_finalization_lock(self.m_session_root / "usage"):
            if (
                self.m_store is not None
                and self.m_runtime_session_id != verified["runtime_session_id"]
            ):
                raise UsageStoreError("Web binding changed the runtime accounting identity")
            self.m_runtime_session_id = verified["runtime_session_id"]
            self.m_agent_id = verified["agent_id"]
            self.m_generation_id = verified["generation"]
            self.m_backend = "dsh_web"
            self.m_provider = "dsh"
            self.m_provider_session_id = verified["native_session_id"]
            self.m_active_binding_id = None
            # Existing bindings always win on reconstruction, even if a caller
            # repeats the original create notification after a lost response.
            existing = any(
                item.provider == "dsh" and item.provider_session_id == self.m_provider_session_id
                for item in self.store.list_bindings()
            )
            binding = self._binding(new_session=new_session and not existing)
            if binding.agent_id != self.m_agent_id:
                raise UsageStoreError("Web binding changed the agent accounting identity")
            path = evidence_path.resolve()
            sources = list(binding.metadata.get("dsh_web_sources", []))
            source = next((item for item in sources if item["path"] == str(path)), None)
            if source is None:
                # Only an initial attachment excludes pre-existing work. A
                # restarted collector must retain the earlier durable boundary.
                source = {
                    "path": str(path),
                    # A replacement Host can write preactivation abandonment
                    # proof before bind returns. Existing native accounting
                    # boundaries already exclude historical consumption.
                    "boundary": 0 if sources else complete_file_position(path),
                    "identities": [],
                }
                sources.append(source)
            if verified not in source["identities"]:
                source["identities"].append(verified)
            binding = binding.model_copy(
                update={
                    "metadata": {
                        **binding.metadata,
                        "dsh_web_identity": verified,
                        "dsh_web_evidence_path": str(path),
                        "dsh_web_sources": sources,
                    }
                }
            )
            self.store.put_binding(binding)
            return binding

    def begin_dsh_web_turn(self, *, operation_id: str, turn_index: int) -> str:
        """Register an exact managed operation before its native input is admitted."""

        with self.m_lock:
            return self.register_managed_turn(
                turn_id=operation_id, turn_index=turn_index, refresh_manifest=False
            )

    def settle_dsh_web_turn(
        self,
        *,
        operation_id: str,
        receipt: dict[str, Any] | None = None,
        outcome: str | None = None,
    ) -> None:
        """Reconcile native proof, or close an explicitly refused, unclaimed attempt.

        An uncertain transport failure supplies no outcome and remains pending.
        A caller must never label a lost response as a definitive refusal.
        """

        with self.m_lock:
            self.collect(max_batches=32, refresh_manifest=False)
            pending = self.store.get_pending_turn(operation_id)
            if pending is None or pending.finalized or outcome is None:
                return
            if receipt is not None or pending.snapshot.provider_turn_id is not None:
                # Claimed work obtains its outcome only from the native journal.
                return
            if outcome not in {"failed", "interrupted"}:
                raise ValueError("An unclaimed Web operation cannot be completed")
            with _artifact_finalization_lock(self.m_session_root / "usage"):
                pending = self.store.get_pending_turn(operation_id)
                assert pending is not None
                if pending.finalized:
                    return
                from houmao.agents.realm_controller.usage_extraction import assemble_usage_record

                finalization = pending.finalization or UsageFinalization(
                    turn_id=operation_id,
                    outcome=cast(Any, outcome),
                    completed_at_utc=_now(),
                    metadata={"observation_ids": [], "dsh_web_dispatch_refused": True},
                )
                self.store.set_finalization(operation_id, finalization)
                self.store.finalize(
                    assemble_usage_record(
                        pending.snapshot,
                        [],
                        outcome=finalization.outcome,
                        completed_at_utc=finalization.completed_at_utc,
                    )
                )

    def reconcile_dsh_web(self) -> None:
        """Resume bounded journal and persisted-claim reconciliation without execution."""

        self.collect(max_batches=32)

    def register_managed_turn(
        self,
        *,
        turn_id: str | None = None,
        provider_turn_id: str | None = None,
        turn_index: int | None = None,
        new_session: bool = False,
        refresh_manifest: bool = True,
    ) -> str:
        """Register a submission before dispatch so native association cannot double it."""

        if refresh_manifest:
            self._refresh_manifest()
        if new_session:
            self.m_provider_session_id = None
            self.m_active_binding_id = None
        binding = self._binding(new_session=new_session)
        if not binding.provisional:
            self.collect(finalize_native=False, max_batches=32, refresh_manifest=False)
        baseline, baseline_ids = self._checkpoint_baseline(binding)
        if not binding.provisional and not self.m_native_caught_up:
            baseline = {key: None for key in baseline}
        resolved = turn_id or f"turn-{uuid.uuid4().hex[:12]}"
        if self.store.get_pending_turn(resolved) is not None:
            raise ValueError("Accounting turn ID has already been registered")
        snapshot = UsageTurnSnapshot(
            agent_id=self.m_agent_id,
            runtime_session_id=self.m_runtime_session_id,
            turn_id=resolved,
            backend=self.m_backend,
            provider=self.m_provider,
            generation_id=self.m_generation_id,
            provider_session_id=self.m_provider_session_id,
            provider_turn_id=provider_turn_id,
            turn_index=turn_index,
            started_at_utc=_now(),
            binding_id=binding.binding_id,
            baseline=baseline,
            counter_epoch=binding.counter_epoch,
            coverage="complete",
            metadata={
                "registered_headless": _artifact_accounting_backend(self.m_backend),
                "baseline_source_ids": baseline_ids,
                **(
                    {
                        "service_incarnation": self.m_service_incarnation,
                        "service_working_directory": self.m_service_working_directory,
                    }
                    if self.m_backend in _SERVICE_JOURNAL_READERS
                    else {}
                ),
            },
        )
        self.store.put_pending_turn(snapshot)
        return resolved

    def _checkpoint_baseline(
        self,
        binding: UsageSourceBinding,
    ) -> tuple[dict[str, int | float | None], dict[str, list[str]]]:
        """Read comparable committed endpoints, including pre-attachment context."""

        baseline = dict(binding.baseline)
        source_ids: dict[str, list[str]] = {}
        candidates: dict[str, list[tuple[int | float, str]]] = {}
        for checkpoint in self.store.list_checkpoints(binding_id=binding.binding_id):
            if checkpoint.counter_epoch != binding.counter_epoch:
                continue
            for key, value in checkpoint.baseline.items():
                if value is not None:
                    candidates.setdefault(key, []).append((value, checkpoint.source_id))
            refs = checkpoint.metadata.get("baseline_source_ids", {})
            if isinstance(refs, dict):
                for key, values in refs.items():
                    if isinstance(values, list):
                        source_ids.setdefault(key, []).extend(
                            value for value in values if isinstance(value, str)
                        )
        for key, values in candidates.items():
            measured = {value for value, _ in values}
            baseline[key] = measured.pop() if len(measured) == 1 else None
            if key not in source_ids:
                source_ids[key] = [source for _, source in values]
        return baseline, source_ids

    def abandon_managed_turn(self, turn_id: str) -> None:
        """Retain failed dispatch evidence without assigning a native measurement."""

        pending = self.store.get_pending_turn(turn_id)
        if pending is not None and not pending.finalized:
            snapshot = pending.snapshot.model_copy(
                update={"metadata": {**pending.snapshot.metadata, "dispatch_failed": True}}
            )
            self.store.put_pending_turn(snapshot)

    def note_provider_turn(
        self, turn_id: str, *, provider_turn_id: str, provider_session_id: str
    ) -> None:
        """Associate a pending submission only through explicit verified identity."""

        pending = self.store.get_pending_turn(turn_id)
        if pending is None or pending.snapshot.binding_id is None:
            raise ValueError("Accounting turn is not registered")
        self.store.associate_provider_turn(
            turn_id,
            binding_id=pending.snapshot.binding_id,
            provider_session_id=provider_session_id,
            provider_turn_id=provider_turn_id,
        )

    def _read_hooks(self) -> list[Any]:
        """Read the runtime-owned hook channel for verified session/turn identity."""

        if self.m_provider not in {"claude", "codex", "kimi"}:
            return []
        if self.m_hook_reader is None:
            adapter = cast(Literal["claude", "codex", "kimi"], self.m_provider)
            path = self.m_session_root / "hook-observation" / self.m_provider / "events.ndjson"
            self.m_hook_reader = HookObservationReader(path, adapter=adapter)
        batch = self.m_hook_reader.read_new()
        for observation in batch.observations:
            if observation.kind == "session_started" and observation.session_id:
                self.m_hook_session_id = observation.session_id
                if (
                    not _artifact_accounting_backend(self.m_backend)
                    or self.m_provider_session_id is None
                ):
                    self.m_provider_session_id = observation.session_id
        return list(batch.observations)

    def collect(
        self, *, finalize_native: bool = True, max_batches: int = 1, refresh_manifest: bool = True
    ) -> list[UsageObservation]:
        """Collect a bounded native batch and finalize only verified native turns."""

        if self.m_provider not in _PROVIDERS or not self.m_runtime_session_id:
            return []
        with self.m_lock:
            if refresh_manifest:
                self._refresh_manifest()
            if self.m_backend in _SERVICE_JOURNAL_READERS:
                if finalize_native:
                    self._recover_known_headless()
                return []
            hooks = self._read_hooks()
            if self.m_hook_session_id and not _artifact_accounting_backend(self.m_backend):
                self.m_provider_session_id = self.m_hook_session_id
            if _artifact_accounting_backend(self.m_backend) and self.m_active_binding_id is None:
                # Execution registers the source binding. A background reader
                # must not invent a competing provisional/attachment binding.
                existing = [
                    item
                    for item in self.store.list_bindings()
                    if item.provider == self.m_provider
                    and item.provider_session_id == self.m_provider_session_id
                    and not item.provisional
                ]
                if not existing:
                    self.m_capability = UsageCapability(
                        status="partial",
                        turn_recording=True,
                        source_kinds=["structured_output"],
                        reasons=["headless_execution_binding_pending"],
                    )
                    return []
                self.m_active_binding_id = existing[0].binding_id
            binding = self._binding()
            if binding.provisional:
                self.m_capability = UsageCapability(
                    status="partial"
                    if _artifact_accounting_backend(self.m_backend)
                    else "unavailable",
                    turn_recording=_artifact_accounting_backend(self.m_backend),
                    reasons=["provider_session_binding_pending"],
                )
                return []
            collector_binding = binding.model_copy(
                update={
                    "metadata": {
                        **binding.metadata,
                        "collection_generation_id": self.m_generation_id,
                    }
                }
            )
            collector = UsageCollector.from_binding(self.store, collector_binding)
            if self.m_backend == "dsh_web":
                try:
                    _proof, proof_caught_up = stage_web_evidence(self.store, binding)
                except (OSError, ValueError, UnicodeError):
                    self._degraded("dsh_web_claim_evidence_gap")
                    return []
            accepted = collector.collect(max_batches=max_batches)
            self.m_native_caught_up = collector.caught_up
            if self.m_backend == "dsh_web":
                try:
                    proof, proof_after_caught_up = stage_web_evidence(self.store, binding)
                except (OSError, ValueError, UnicodeError):
                    self._degraded("dsh_web_claim_evidence_gap")
                    return accepted
                accepted.extend(proof)
                self.m_native_caught_up &= proof_caught_up and proof_after_caught_up
            accepted.extend(self._stage_hooks(binding, hooks))
            all_observations = self.store.list_observations(binding_id=binding.binding_id)
            scopes = sorted({item.measurement_scope for item in all_observations if item.values})
            kinds = sorted({item.source_kind for item in all_observations})
            has_turns = any(
                item.provider_turn_id and item.source_kind == "native_session_log"
                for item in all_observations
            )
            self.m_capability = UsageCapability(
                status="available" if has_turns else "partial",
                turn_recording=has_turns or _artifact_accounting_backend(self.m_backend),
                source_kinds=kinds,
                observed_scopes=scopes,
                reasons=[] if has_turns else ["verified_turn_association_unavailable"],
            )
            diagnostics = collector.diagnostics
            if self.m_backend == "dsh_web" and not (proof_caught_up and proof_after_caught_up):
                diagnostics.append("dsh_web_claim_evidence_pending")
            self.m_health = UsageCollectionHealth(
                status="degraded" if diagnostics else "healthy",
                updated_at_utc=_now(),
                diagnostics=diagnostics,
            )
            if diagnostics:
                self.m_capability = self.m_capability.model_copy(
                    update={
                        "status": "partial",
                        "reasons": list(
                            dict.fromkeys(
                                [
                                    *self.m_capability.reasons,
                                    *diagnostics,
                                ]
                            )
                        ),
                    }
                )
            self.store.set_collection_health(self.m_health)
            if finalize_native:
                if self.m_backend == "dsh_web":
                    with _artifact_finalization_lock(self.m_session_root / "usage"):
                        assemble_web_usage(self, binding, all_observations)
                else:
                    self._assemble_native(binding, all_observations)
                if _artifact_accounting_backend(self.m_backend):
                    self._recover_known_headless()
            return accepted

    def _stage_hooks(self, binding: UsageSourceBinding, hooks: list[Any]) -> list[UsageObservation]:
        """Checkpoint hook lifecycle evidence without replaying pre-attachment turns."""

        reader = self.m_hook_reader
        if reader is None:
            return []
        source_id = opaque_usage_reference(str(reader.events_path))
        checkpoint = self.store.get_checkpoint(binding.binding_id, source_id)
        previous_key = tuple(checkpoint.metadata.get("last_key", [-1, -1])) if checkpoint else None
        accepted: list[UsageObservation] = []
        last_key: tuple[int, int] = cast(tuple[int, int], previous_key or (-1, -1))
        for hook in hooks:
            key = (hook.channel_generation, hook.sequence if hook.sequence is not None else -1)
            last_key = max(last_key, key)
            if previous_key is None or key <= previous_key:
                continue
            if hook.session_id != binding.provider_session_id:
                continue
            if binding.provider == "claude":
                # Claude hook prompt_id and native user-message UUID are distinct
                # namespaces in the qualified client. Session identity is useful
                # above, but timing alone cannot map these turn identities.
                continue
            provider_turn_id = hook.turn_id or hook.prompt_id
            lifecycle = {
                "prompt_submitted": "started",
                "turn_started": "started",
                "turn_completed": "completed",
                "turn_failed": "failed",
                "turn_interrupted": "interrupted",
            }.get(hook.kind)
            if not provider_turn_id or lifecycle is None:
                continue
            accepted.append(
                UsageObservation(
                    observation_id=f"hook-{binding.binding_id}-{key[0]}-{key[1]}",
                    provider=binding.provider,
                    provider_session_id=binding.provider_session_id,
                    provider_turn_id=provider_turn_id,
                    binding_id=binding.binding_id,
                    source_kind="houmao_runtime",
                    source_ref=source_id,
                    kind="lifecycle",
                    accounting_kind=f"turn_{lifecycle}",
                    lifecycle=cast(Any, lifecycle),
                    timestamp_utc=hook.received_at_utc,
                    profile_id=f"{binding.provider}-hooks-v1",
                    coverage="unknown",
                )
            )
        if hooks or checkpoint is None:
            self.store.ingest_batch(
                checkpoint=UsageCheckpoint(
                    binding_id=binding.binding_id,
                    source_id=source_id,
                    file_identity="hook-channel",
                    offset=reader.offset,
                    metadata={"last_key": list(last_key)},
                ),
                observations=accepted,
                expected_version=checkpoint.version if checkpoint else 0,
            )
        return accepted

    def _assemble_native(
        self, binding: UsageSourceBinding, observations: list[UsageObservation]
    ) -> None:
        """Finalize native turns once their structured association and outcome exist."""

        from houmao.agents.realm_controller.usage_extraction import assemble_usage_record

        if _artifact_accounting_backend(self.m_backend):
            # Headless lifecycle and its artifact cutoff are authoritative.
            # Native files supplement that managed row, never create another.
            for headless_pending in self.store.list_pending_turns(include_finalized=True):
                snapshot = headless_pending.snapshot
                native_turn_ids = snapshot.metadata.get("native_turn_ids", [])
                if (
                    not headless_pending.finalized
                    or snapshot.binding_id != binding.binding_id
                    or (snapshot.provider_turn_id is None and not native_turn_ids)
                ):
                    continue
                relevant = []
                for item in observations:
                    if item.source_kind != "native_session_log":
                        continue
                    if (
                        snapshot.provider == "dsh"
                        and item.provider_session_id != snapshot.provider_session_id
                    ):
                        child = _dsh_link_descendant(item, snapshot)
                        if child is not None:
                            relevant.append(child)
                    elif (
                        item.provider_turn_id == snapshot.provider_turn_id
                        or item.provider_turn_id in native_turn_ids
                    ):
                        relevant.append(item)
                self._check_late_native_evidence(snapshot, headless_pending.finalization, relevant)
            return
        turns = list(
            dict.fromkeys(item.provider_turn_id for item in observations if item.provider_turn_id)
        )
        for provider_turn_id in turns:
            relevant = [item for item in observations if item.provider_turn_id == provider_turn_id]
            if not any(item.source_kind == "native_session_log" for item in relevant):
                continue
            started = next((item for item in relevant if item.lifecycle == "started"), None)
            terminals = [
                item
                for item in relevant
                if item.lifecycle in {"completed", "failed", "interrupted"}
            ]
            terminal = terminals[-1] if terminals else None
            turn_id = self.store.resolve_turn_id(
                binding_id=binding.binding_id,
                provider_session_id=binding.provider_session_id,
                provider_turn_id=provider_turn_id,
            )
            if turn_id is None:
                unresolved = [
                    item
                    for item in self.store.list_pending_turns()
                    if item.snapshot.binding_id == binding.binding_id
                    and item.snapshot.turn_origin == "managed"
                    and item.snapshot.provider_turn_id is None
                    and not item.snapshot.metadata.get("dispatch_failed")
                ]
                if unresolved:
                    self._degraded("managed_native_association_pending")
                    continue
                key = f"{self.m_runtime_session_id}:{binding.binding_id}:{provider_turn_id}"
                turn_id = "native-" + hashlib.sha256(key.encode()).hexdigest()[:24]
                snapshot = UsageTurnSnapshot(
                    agent_id=binding.agent_id,
                    runtime_session_id=binding.runtime_session_id,
                    generation_id=(
                        started.metadata.get("generation_id")
                        if started and "generation_id" in started.metadata
                        else self.m_generation_id
                    ),
                    turn_id=turn_id,
                    backend=self.m_backend,
                    provider=binding.provider,
                    provider_session_id=binding.provider_session_id,
                    provider_turn_id=provider_turn_id,
                    turn_origin="native_observed",
                    started_at_utc=started.timestamp_utc if started else None,
                    binding_id=binding.binding_id,
                    baseline=dict(started.metadata.get("baseline", binding.baseline))
                    if started
                    else {},
                    counter_epoch=started.metadata.get("counter_epoch", binding.counter_epoch)
                    if started
                    else binding.counter_epoch,
                    coverage="complete"
                    if started and all(item.coverage != "partial" for item in relevant)
                    else "partial",
                    metadata={
                        "baseline_source_ids": started.metadata.get("baseline_source_ids", {})
                        if started
                        else {}
                    },
                )
                self.store.put_pending_turn(snapshot)
            pending = self.store.get_pending_turn(turn_id)
            if pending is None:
                continue
            if terminal is None:
                continue
            if not self.m_native_caught_up:
                continue
            if pending.finalized:
                self._check_late_native_evidence(pending.snapshot, pending.finalization, relevant)
                continue
            finalization = pending.finalization
            if finalization is None:
                finalization = UsageFinalization(
                    turn_id=turn_id,
                    outcome=cast(Any, terminal.lifecycle),
                    completed_at_utc=terminal.timestamp_utc,
                    metadata={"observation_ids": [item.observation_id for item in relevant]},
                )
                self.store.set_finalization(turn_id, finalization)
            cutoff = finalization.metadata.get("observation_ids", [])
            selected = [item for item in relevant if item.observation_id in cutoff]
            record = assemble_usage_record(
                pending.snapshot,
                selected,
                outcome=finalization.outcome,
                completed_at_utc=finalization.completed_at_utc,
                wall_time_ms=finalization.wall_time_ms,
            )
            self.store.finalize(record)

    def _check_late_native_evidence(
        self,
        snapshot: UsageTurnSnapshot,
        finalization: UsageFinalization | None,
        relevant: list[UsageObservation],
    ) -> None:
        """Report material accounting changes beyond an immutable native cutoff."""

        from houmao.agents.realm_controller.usage_extraction import assemble_usage_record

        if finalization is None:
            return
        cutoff = set(finalization.metadata.get("observation_ids", []))
        if all(item.observation_id in cutoff for item in relevant):
            return
        original = self.store.get_record(snapshot.turn_id)
        if original is None:
            return
        proposed_observations = relevant
        if _artifact_accounting_backend(snapshot.backend):
            original_observations = [
                UsageObservation.model_validate(item)
                for item in finalization.metadata.get("observations", [])
            ]
            proposed_observations = [*original_observations, *relevant]
        proposed = assemble_usage_record(
            snapshot,
            proposed_observations,
            outcome=finalization.outcome,
            completed_at_utc=finalization.completed_at_utc,
            wall_time_ms=finalization.wall_time_ms,
        )

        def accounting(record: UsageRecord) -> dict[str, Any]:
            """Compare accounting values while ignoring source-copy provenance."""

            payload = record.model_dump(mode="json", exclude={"sources", "diagnostics"})

            def strip(item: Any) -> Any:
                """Remove source IDs that do not change a measurement."""
                if isinstance(item, dict):
                    return {key: strip(value) for key, value in item.items() if key != "source_ids"}
                if isinstance(item, list):
                    return [strip(value) for value in item]
                return item

            return cast(dict[str, Any], strip(payload))

        if accounting(original) != accounting(proposed) or (
            "conflicting_request_evidence" in proposed.diagnostics
            and "conflicting_request_evidence" not in original.diagnostics
        ):
            self._degraded("late_accounting_evidence_conflict")

    def begin_headless_turn(
        self, *, turn_id: str, turn_dir: Path, turn_index: int, new_session: bool
    ) -> UsageTurnSnapshot:
        """Persist a turn-start snapshot and source boundary before provider launch."""

        if (turn_dir / "usage-start.json").exists():
            raise ValueError("Headless accounting turn ID has already been used")
        self.register_managed_turn(
            turn_id=turn_id,
            turn_index=turn_index,
            new_session=new_session,
            refresh_manifest=False,
        )
        pending = self.store.get_pending_turn(turn_id)
        assert pending is not None
        snapshot = pending.snapshot
        positions: dict[str, int] = {}
        if snapshot.binding_id and snapshot.backend not in _SERVICE_JOURNAL_READERS:
            binding = self.store.get_binding(snapshot.binding_id)
            if binding is not None:
                for path in discover_usage_sources(binding):
                    positions[opaque_usage_reference(str(path))] = complete_file_position(path)
        snapshot = snapshot.model_copy(
            update={
                "source_positions": positions,
                "metadata": {
                    **snapshot.metadata,
                    "artifact_dir": str(turn_dir),
                    "manifest_path": str(self.m_manifest_path),
                },
            }
        )
        self.store.put_pending_turn(snapshot)
        write_usage_json(turn_dir / "usage-start.json", snapshot.model_dump(mode="json"))
        return snapshot

    def finalize_headless_turn(
        self,
        turn_dir: Path,
        *,
        provider_session_id: str | None = None,
        events: list[Any] | None = None,
    ) -> UsageRecord | None:
        """Assemble original terminal evidence once, with an immutable source cutoff."""

        if (
            not (turn_dir / "usage-start.json").exists()
            or not (turn_dir / "usage-final.json").exists()
        ):
            return None
        with self.m_lock, _artifact_finalization_lock(turn_dir):
            return self._finalize_headless_turn(
                turn_dir, provider_session_id=provider_session_id, events=events
            )

    def _finalize_headless_turn(
        self,
        turn_dir: Path,
        *,
        provider_session_id: str | None,
        events: list[Any] | None,
    ) -> UsageRecord | None:
        """Finalize under the shared artifact lock using one recorded cutoff."""

        from houmao.agents.realm_controller.usage_extraction import assemble_usage_record

        start_path = turn_dir / "usage-start.json"
        final_path = turn_dir / "usage-final.json"
        if not start_path.exists() or not final_path.exists():
            return None
        snapshot = UsageTurnSnapshot.model_validate_json(start_path.read_text())
        finalization = UsageFinalization.model_validate_json(final_path.read_text())
        cached = turn_dir / "usage-record.json"
        if cached.exists():
            record = UsageRecord.model_validate_json(cached.read_text())
            self.store.finalize(record)
            return record
        original_binding = (
            self.store.get_binding(snapshot.binding_id) if snapshot.binding_id else None
        )
        original_session_id = snapshot.provider_session_id or (
            original_binding.provider_session_id if original_binding else None
        )
        if (
            original_session_id is not None
            and provider_session_id is not None
            and original_session_id != provider_session_id
        ):
            raise ValueError("Headless terminal evidence belongs to a different provider session")
        dsh_interval = None
        dsh_diagnostic = None
        if snapshot.provider == "dsh":
            try:
                dsh_interval = read_dsh_interval(turn_dir, snapshot)
                provider_session_id = dsh_interval.session_id
                if not dsh_interval.root_turn_ids:
                    dsh_diagnostic = "dsh_native_admission_unverified"
            except DshJournalError as exc:
                dsh_diagnostic = str(exc)
            snapshot = snapshot.model_copy(
                update={
                    **(
                        {"coverage": "partial"}
                        if dsh_interval is not None and not dsh_interval.coverage_complete
                        else {}
                    ),
                    "metadata": {
                        **snapshot.metadata,
                        "native_turn_ids": dsh_interval.root_turn_ids if dsh_interval else [],
                        "native_descendant_turns": dsh_interval.descendant_turn_ids
                        if dsh_interval
                        else {},
                        "native_descendant_parents": dsh_interval.descendant_parents
                        if dsh_interval
                        else {},
                        "native_interval_verified": bool(
                            dsh_interval and dsh_interval.root_turn_ids
                        ),
                        **({"dsh_accounting_limitation": dsh_diagnostic} if dsh_diagnostic else {}),
                    },
                }
            )
        output_turn_id: str | None
        service_journal = _SERVICE_JOURNAL_READERS.get(snapshot.backend)
        if service_journal is not None:
            receipt_name, read_usage = service_journal
            try:
                if original_binding is None:
                    raise ValueError("Service accounting binding is missing")
                output_turn_id, observed = read_usage(
                    snapshot=snapshot,
                    home=Path(original_binding.home_path),
                    receipt=_read_json(turn_dir / receipt_name),
                    process=_read_json(turn_dir / "process.json"),
                    outcome=finalization.outcome,
                )
            except (OSError, ValueError, KeyError):
                self._degraded(f"{snapshot.provider}_service_journal_evidence_unavailable")
                return None
            output_session_id, raw_count = snapshot.provider_session_id, len(observed)
        else:
            observed, output_session_id, output_turn_id, raw_count = self._headless_output(
                turn_dir,
                snapshot,
                original_session_id or provider_session_id,
                events,
            )
        session_id = original_session_id or provider_session_id or output_session_id
        if session_id is not None and output_session_id not in {None, session_id}:
            raise ValueError("Headless output belongs to a different provider session")
        self.m_provider_session_id = session_id
        self.m_active_binding_id = snapshot.binding_id
        native = self._binding(new_session=bool(snapshot.baseline))
        if dsh_interval is not None:
            native = native.model_copy(
                update={
                    "metadata": {
                        **native.metadata,
                        **(
                            {"persistence_root": dsh_interval.persistence_root}
                            if dsh_interval.persistence_root is not None
                            else {}
                        ),
                        **(
                            {"working_directory": dsh_interval.working_directory}
                            if dsh_interval.working_directory is not None
                            else {}
                        ),
                        "dsh_descendant_sessions": {
                            child: parent
                            for child, parent in dsh_interval.descendant_parents.items()
                            if dsh_interval.descendant_local.get(child)
                            and dsh_interval.descendant_turn_ids.get(child)
                        },
                    }
                }
            )
            self.store.put_binding(native)
        self.collect(finalize_native=False, max_batches=32, refresh_manifest=False)
        observed = [item.model_copy(update={"binding_id": native.binding_id}) for item in observed]
        native_observations = (
            []
            if service_journal is not None
            else self.store.list_observations(binding_id=native.binding_id)
        )
        # Cut source records at their pre-dispatch complete-record boundaries.
        candidates: list[UsageObservation] = []
        for item in native_observations:
            if item.source_kind == "houmao_runtime":
                continue
            prefix, _, position = item.source_ref.rpartition(":")
            boundary = snapshot.source_positions.get(prefix, 0)
            if position.isdigit() and int(position) < boundary:
                continue
            if item.provider_session_id in {None, session_id}:
                candidates.append(
                    item
                    if self.m_native_caught_up
                    else item.model_copy(update={"coverage": "partial"})
                )
            elif snapshot.provider == "dsh":
                child = _dsh_link_descendant(item, snapshot)
                if child is not None:
                    candidates.append(child)
        native_turns = {
            item.provider_turn_id
            for item in candidates
            if item.provider_turn_id and not item.is_sidechain
        }
        native_turn_id = output_turn_id or (
            next(iter(native_turns)) if len(native_turns) == 1 else None
        )
        if snapshot.provider == "dsh":
            owned = set(dsh_interval.root_turn_ids) if dsh_interval is not None else set()
            candidates = [
                item
                for item in candidates
                if item.provider_turn_id in owned or item.parent_turn_id == snapshot.turn_id
            ]
            native_turn_id = next(iter(owned)) if len(owned) == 1 else None
            if dsh_interval is not None:
                measured = {item.provider_session_id for item in candidates if item.parent_turn_id}
                for descendant_id in dsh_interval.descendant_parents:
                    if descendant_id in measured:
                        continue
                    source = opaque_usage_reference(
                        f"dsh-descendant:{snapshot.turn_id}:{descendant_id}"
                    )
                    candidates.append(
                        UsageObservation(
                            observation_id=source,
                            provider="dsh",
                            provider_session_id=descendant_id,
                            turn_id=snapshot.turn_id,
                            binding_id=native.binding_id,
                            parent_turn_id=snapshot.turn_id,
                            source_kind="houmao_runtime",
                            source_ref=source,
                            profile_id="dsh-native-descendant-v1",
                            is_sidechain=True,
                            metadata={
                                "child_id": descendant_id,
                                "limitation": "dsh_descendant_usage_unverified",
                            },
                        )
                    )
        if session_id is not None:
            snapshot = snapshot.model_copy(update={"provider_session_id": session_id})
        if native_turn_id is not None:
            snapshot = snapshot.model_copy(update={"provider_turn_id": native_turn_id})
            candidates = [
                item
                for item in candidates
                if item.provider_turn_id in {None, native_turn_id} or item.is_sidechain
            ]
        elif snapshot.provider != "dsh":
            candidates = []
        snapshot = snapshot.model_copy(update={"binding_id": native.binding_id})
        self.store.put_pending_turn(snapshot)
        if observed:
            source_id = f"headless-{snapshot.turn_id}"
            checkpoint = self.store.get_checkpoint(native.binding_id, source_id)
            self.store.ingest_batch(
                checkpoint=UsageCheckpoint(
                    binding_id=native.binding_id,
                    source_id=source_id,
                    file_identity=source_id,
                    offset=raw_count,
                ),
                observations=observed,
                expected_version=checkpoint.version if checkpoint else 0,
            )
        selected = [*observed, *candidates]
        if "observation_ids" not in finalization.metadata:
            finalization = finalization.model_copy(
                update={
                    "metadata": {
                        **finalization.metadata,
                        "observation_ids": [item.observation_id for item in selected],
                        "observations": [item.model_dump(mode="json") for item in selected],
                        "snapshot": snapshot.model_dump(mode="json"),
                    }
                }
            )
            write_usage_json(final_path, finalization.model_dump(mode="json"))
        else:
            selected = [
                UsageObservation.model_validate(item)
                for item in finalization.metadata.get("observations", [])
            ]
            snapshot = UsageTurnSnapshot.model_validate(finalization.metadata["snapshot"])
        self.store.set_finalization(snapshot.turn_id, finalization)
        record = assemble_usage_record(
            snapshot,
            selected,
            outcome=finalization.outcome,
            completed_at_utc=finalization.completed_at_utc,
            wall_time_ms=finalization.wall_time_ms,
        )
        limitation = snapshot.metadata.get("dsh_accounting_limitation")
        if isinstance(limitation, str) and limitation not in record.diagnostics:
            record.diagnostics.append(limitation)
        write_usage_json(cached, record.model_dump(mode="json"))
        self.store.finalize(record)
        if service_journal is not None:
            self.store.set_collection_health(
                UsageCollectionHealth(status="healthy", updated_at_utc=_now())
            )
        baseline = dict(native.baseline)
        for item in observed:
            if item.kind == "cumulative":
                baseline.update(
                    {key: value for key, value in item.values.items() if value is not None}
                )
        self.store.put_binding(native.model_copy(update={"baseline": baseline}))
        return record

    def _headless_output(
        self,
        turn_dir: Path,
        snapshot: UsageTurnSnapshot,
        provider_session_id: str | None,
        events: list[Any] | None,
    ) -> tuple[list[UsageObservation], str | None, str | None, int]:
        """Read independent output copies without losing valid crash-time stdout."""

        observations: list[UsageObservation] = []
        if self.m_provider == "dsh":
            # CLI step usage aggregates separately billed attempts and ACP reports
            # occupancy. Only the owned native journal contributes usage records.
            return [], None, None, 0
        session_ids: set[str] = set()
        turn_ids: set[str] = set()
        count = 0
        for name in ("stdout.jsonl", "canonical-events.jsonl", "event-fallback"):
            payloads: list[dict[str, Any]] = []
            if name == "event-fallback":
                if any(item.values for item in observations) or not events:
                    continue
                for event in events:
                    payload = getattr(event, "payload", None)
                    if isinstance(payload, dict):
                        candidate = payload.get("raw") or payload
                        if isinstance(candidate, dict):
                            payloads.append(candidate)
            else:
                path = turn_dir / name
                if not path.exists():
                    continue
                for line in path.read_text(encoding="utf-8").splitlines():
                    try:
                        payload = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(payload, dict):
                        payloads.append(payload)
            adapter = UsageAdapter.from_provider(self.m_provider, provider_session_id)
            for index, payload in enumerate(payloads):
                observations.extend(
                    adapter.parse(
                        payload,
                        source_ref=f"headless-{snapshot.turn_id}-{name}-{index}",
                        source_kind="structured_output",
                        turn_id=snapshot.turn_id,
                        binding_id=snapshot.binding_id,
                    )
                )
            count += len(payloads)
            if adapter.provider_session_id:
                session_ids.add(adapter.provider_session_id)
            if adapter.provider_turn_id:
                turn_ids.add(adapter.provider_turn_id)
        if len(session_ids) > 1 or len(turn_ids) > 1:
            raise ValueError("Headless output copies contain conflicting provider identities")
        return (
            observations,
            next(iter(session_ids), None),
            next(iter(turn_ids), None),
            count,
        )

    def reconcile(self) -> None:
        """Recover pending turns from their original artifacts outside API reads."""

        if self.m_provider not in _PROVIDERS or not self.m_runtime_session_id:
            return
        with self.m_lock:
            self._refresh_manifest()
            self._recover_known_headless()
            # Sidecars also recover a recorder failure before pending state committed.
            root = self.m_session_root / f"{self.m_manifest_path.stem}.turn-artifacts"
            if root.exists():
                for start_path in root.glob("*/usage-start.json"):
                    snapshot = UsageTurnSnapshot.model_validate_json(start_path.read_text())
                    if self.store.get_pending_turn(snapshot.turn_id) is None:
                        self.store.put_pending_turn(snapshot)
                        self.finalize_headless_turn(start_path.parent)
            self.collect()

    def _recover_known_headless(self) -> None:
        """Retry recorded terminal artifacts when a running recorder later recovers."""

        for pending in self.store.list_pending_turns():
            artifact_dir = pending.snapshot.metadata.get("artifact_dir")
            if not isinstance(artifact_dir, str):
                continue
            turn_dir = Path(artifact_dir)
            service_journal = _SERVICE_JOURNAL_READERS.get(pending.snapshot.backend)
            if service_journal is not None and not (turn_dir / "usage-final.json").exists():
                try:
                    receipt = _read_json(turn_dir / service_journal[0])
                    outcome = receipt["terminal"]
                    completed = receipt["settled_at_utc"]
                    if (
                        not isinstance(outcome, str)
                        or outcome not in {"completed", "failed", "interrupted"}
                        or not isinstance(completed, str)
                    ):
                        continue
                    persist_terminal_evidence(
                        turn_dir,
                        returncode=0 if outcome == "completed" else 1,
                        completed_at_utc=completed,
                        wall_time_ms=None,
                        interrupted=outcome == "interrupted",
                    )
                except (OSError, ValueError, KeyError):
                    continue
            if not (turn_dir / "usage-final.json").exists() and (turn_dir / "exitcode").exists():
                exit_path = turn_dir / "exitcode"
                returncode = int(exit_path.read_text().strip())
                if (
                    pending.snapshot.backend == "dsh_headless"
                    and returncode == 0
                    and not dsh_cli_completion_evidence(turn_dir, pending.snapshot)
                ):
                    self._degraded("dsh_native_closure_unverified")
                    continue
                completed = datetime.fromtimestamp(exit_path.stat().st_mtime, UTC).isoformat()
                persist_terminal_evidence(
                    turn_dir,
                    returncode=returncode,
                    completed_at_utc=completed,
                    wall_time_ms=None,
                    interrupted=(turn_dir / "usage-interrupt.json").exists(),
                )
            self.finalize_headless_turn(turn_dir)
