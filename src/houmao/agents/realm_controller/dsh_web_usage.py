"""Metadata-only Web claim collection and exact native accounting association.

The native journal supplies charges and outcomes. The companion supplies input
ownership, never a second usage measurement or a replayable prompt queue.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING, cast

from houmao.agents.realm_controller.usage_extraction import assemble_usage_record
from houmao.agents.realm_controller.usage_models import (
    UsageCheckpoint,
    UsageFinalization,
    UsageObservation,
    UsageSourceBinding,
    UsageTurnSnapshot,
    opaque_usage_reference,
)
from houmao.agents.realm_controller.usage_store import UsageCheckpointConflictError, UsageStore

if TYPE_CHECKING:
    from houmao.agents.realm_controller.usage_support import UsageService

WEB_IDENTITY_KEYS = (
    "agent_id",
    "runtime_session_id",
    "generation",
    "host_incarnation",
    "native_session_id",
    "agent_incarnation",
)
_EVENTS = {"inbox/inserted", "inbox/claimed", "turn/start", "turn/end", "reconciled"}
_MAX_BATCH = 4 << 20


def web_identity(value: dict[str, Any]) -> dict[str, str]:
    """Validate the verified live binding without admitting arbitrary metadata."""

    if value.get("protocol_version") != 1:
        raise ValueError("dsh_web_usage_identity_invalid")
    if any(not isinstance(value.get(key), str) or not value[key] for key in WEB_IDENTITY_KEYS):
        raise ValueError("dsh_web_usage_identity_invalid")
    return {key: value[key] for key in WEB_IDENTITY_KEYS}


def stage_web_evidence(
    store: UsageStore, binding: UsageSourceBinding
) -> tuple[list[UsageObservation], bool]:
    """Checkpoint complete bounded metadata rows, rejecting replaced or alien sources."""

    accepted: list[UsageObservation] = []
    caught_up = True
    for source in binding.metadata.get("dsh_web_sources", []):
        path = Path(source["path"])
        source_id = opaque_usage_reference("dsh-web:" + str(path))
        checkpoint = store.get_checkpoint(binding.binding_id, source_id)
        offset = checkpoint.offset if checkpoint else source["boundary"]
        stat = path.stat()
        file_id = f"{stat.st_dev}:{stat.st_ino}"
        if stat.st_size < offset or (checkpoint and checkpoint.file_identity != file_id):
            raise ValueError("dsh_web_usage_evidence_discontinuous")
        rows: list[UsageObservation] = []
        last_sequence = checkpoint.metadata.get("last_sequence") if checkpoint else None
        with path.open("rb") as handle:
            if checkpoint and checkpoint.metadata.get("prefix_hash"):
                handle.seek(max(0, offset - 4096))
                if (
                    hashlib.sha256(handle.read(min(offset, 4096))).hexdigest()
                    != checkpoint.metadata["prefix_hash"]
                ):
                    raise ValueError("dsh_web_usage_evidence_discontinuous")
            handle.seek(offset)
            end = min(stat.st_size, offset + _MAX_BATCH)
            while handle.tell() < end:
                start = handle.tell()
                line = handle.readline(65537)
                if len(line) > 65536:
                    raise ValueError("dsh_web_usage_evidence_exceeds_bound")
                if not line.endswith(b"\n"):
                    handle.seek(start)
                    caught_up = False
                    break
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("dsh_web_usage_evidence_invalid")
                row_sequence = row.get("sequence")
                if (
                    type(row_sequence) is not int
                    or row_sequence < 0
                    or (last_sequence is not None and row_sequence != last_sequence + 1)
                ):
                    raise ValueError("dsh_web_usage_evidence_gap")
                last_sequence = row_sequence
                event = row.get("event")
                identity = row.get("identity", {})
                if not isinstance(identity, dict):
                    raise ValueError("dsh_web_usage_evidence_invalid")
                # Startup and other conversations are not accounting evidence.
                if (
                    event not in _EVENTS
                    or identity.get("native_session_id") != binding.provider_session_id
                ):
                    continue
                verified = web_identity(identity)
                if verified not in source["identities"]:
                    raise ValueError("dsh_web_usage_evidence_identity_mismatch")
                turn = row.get("turn")
                if (
                    event != "reconciled"
                    and event != "inbox/inserted"
                    and (type(turn) is not int or turn < 0)
                ):
                    raise ValueError("dsh_web_usage_evidence_turn_invalid")
                sequence = row.get("native_sequence")
                if event != "reconciled" and (type(sequence) is not int or sequence < 0):
                    raise ValueError("dsh_web_usage_evidence_sequence_invalid")
                metadata: dict[str, Any] = {"web_identity": verified, "native_sequence": sequence}
                stamp = row.get("observed_at_utc")
                if (
                    not isinstance(stamp, str)
                    or datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo is None
                ):
                    raise ValueError("dsh_web_usage_evidence_timestamp_invalid")
                for key in ("message_id", "operation_id"):
                    value = row.get(key)
                    if value is not None and (
                        not isinstance(value, str) or not value or len(value) > 512
                    ):
                        raise ValueError("dsh_web_usage_evidence_input_invalid")
                    metadata[key] = value
                rows.append(
                    UsageObservation(
                        observation_id=f"{source_id}:{start}",
                        provider="dsh",
                        provider_session_id=binding.provider_session_id,
                        provider_turn_id=str(turn) if type(turn) is int else None,
                        binding_id=binding.binding_id,
                        source_kind="houmao_runtime",
                        source_ref=source_id,
                        profile_id="dsh-web-claims-v1",
                        kind="lifecycle",
                        accounting_kind="dsh_web_" + event,
                        timestamp_utc=stamp,
                        metadata=metadata,
                    )
                )
            position = handle.tell()
            caught_up = caught_up and position == stat.st_size
            handle.seek(max(0, position - 4096))
            prefix_hash = hashlib.sha256(handle.read(min(position, 4096))).hexdigest()
        if checkpoint and checkpoint.offset == position:
            continue
        try:
            store.ingest_batch(
                checkpoint=UsageCheckpoint(
                    binding_id=binding.binding_id,
                    source_id=source_id,
                    file_identity=file_id,
                    offset=position,
                    metadata={"prefix_hash": prefix_hash, "last_sequence": last_sequence},
                ),
                observations=rows,
                expected_version=checkpoint.version if checkpoint else 0,
            )
            accepted.extend(rows)
        except UsageCheckpointConflictError:
            # A competing runtime collector committed the same complete tail.
            caught_up = False
    return accepted, caught_up


def assemble_web_usage(
    service: UsageService, binding: UsageSourceBinding, observations: list[UsageObservation]
) -> None:
    """Associate by native input claims before any immutable native finalization."""

    turns = dict.fromkeys(item.provider_turn_id for item in observations if item.provider_turn_id)
    for native_turn in turns:
        relevant = [item for item in observations if item.provider_turn_id == native_turn]
        native = [item for item in relevant if item.source_kind == "native_session_log"]
        started = next((item for item in native if item.lifecycle == "started"), None)
        terminal = next(
            (
                item
                for item in reversed(native)
                if item.lifecycle in {"completed", "failed", "interrupted"}
            ),
            None,
        )
        proof_start = next(
            (item for item in relevant if item.accounting_kind == "dsh_web_turn/start"), None
        )
        proof_end = next(
            (item for item in relevant if item.accounting_kind == "dsh_web_turn/end"), None
        )
        claims = [item for item in relevant if item.accounting_kind == "dsh_web_inbox/claimed"]
        if not started or not terminal or not proof_start or not claims:
            continue
        # Native restore may close an interrupted turn before a new Agent exists.
        # The original start and exact claims still own that repaired terminal.
        if proof_end is None and terminal.lifecycle != "interrupted":
            continue
        if proof_start.metadata.get("native_sequence") != started.metadata.get(
            "native_sequence"
        ) or (
            proof_end is not None
            and proof_end.metadata.get("native_sequence")
            != terminal.metadata.get("native_sequence")
        ):
            service._degraded("dsh_web_usage_native_boundary_mismatch")
            continue
        inputs = {
            item.metadata["native_message_id"]
            for item in native
            if item.accounting_kind == "dsh_native_input"
        }
        claimed = {item.metadata["message_id"] for item in claims}
        if not inputs.issubset(claimed):
            service._degraded("dsh_web_usage_input_proof_pending")
            continue
        operations = list(
            dict.fromkeys(
                item.metadata["operation_id"]
                for item in sorted(claims, key=lambda item: item.metadata["native_sequence"])
                if item.metadata.get("operation_id") is not None
            )
        )
        turn_id = service.store.resolve_turn_id(
            binding_id=binding.binding_id,
            provider_session_id=binding.provider_session_id,
            provider_turn_id=native_turn,
        )
        operation_id = operations[0] if operations else None
        if any(
            item.metadata.get("operation_id") is not None
            and item.metadata["message_id"] not in inputs
            for item in claims
        ):
            service._degraded("dsh_web_usage_input_proof_pending")
            continue
        if operation_id is not None and turn_id not in {None, operation_id}:
            service._degraded("dsh_web_usage_association_conflict")
            continue
        turn_id = (
            operation_id
            or turn_id
            or "native-"
            + hashlib.sha256(f"{binding.binding_id}:{native_turn}".encode()).hexdigest()[:24]
        )
        pending = service.store.get_pending_turn(turn_id)
        identity = proof_start.metadata["web_identity"]
        mixed = bool(
            operation_id
            and any(
                item.metadata.get("operation_id") != operation_id
                and item.metadata["message_id"] in inputs
                for item in claims
            )
        )
        association = {"dsh_web_mixed_input": mixed, "dsh_web_operation_ids": operations}
        if pending is None:
            snapshot = UsageTurnSnapshot(
                agent_id=binding.agent_id,
                runtime_session_id=binding.runtime_session_id,
                generation_id=identity["generation"],
                turn_id=turn_id,
                backend="dsh_web",
                provider="dsh",
                provider_session_id=binding.provider_session_id,
                provider_turn_id=native_turn,
                turn_origin="managed" if operation_id else "native_observed",
                started_at_utc=started.timestamp_utc,
                binding_id=binding.binding_id,
                baseline=dict(binding.baseline),
                counter_epoch=binding.counter_epoch,
                coverage="complete",
                metadata=association,
            )
            service.store.put_pending_turn(snapshot)
        elif not pending.finalized:
            snapshot = pending.snapshot.model_copy(
                update={
                    "provider_turn_id": native_turn,
                    "metadata": {**pending.snapshot.metadata, **association},
                }
            )
            service.store.put_pending_turn(snapshot)
        pending = service.store.get_pending_turn(turn_id)
        assert pending is not None
        if pending.finalized:
            service._check_late_native_evidence(pending.snapshot, pending.finalization, relevant)
            _close_shared_operations(service, pending.snapshot, operations[1:], terminal)
            continue
        if not service.m_native_caught_up:
            continue
        finalization = pending.finalization or UsageFinalization(
            turn_id=turn_id,
            outcome=cast(Any, terminal.lifecycle),
            completed_at_utc=terminal.timestamp_utc,
            metadata={"observation_ids": [item.observation_id for item in relevant]},
        )
        if pending.finalization is None:
            service.store.set_finalization(turn_id, finalization)
        cutoff = set(finalization.metadata["observation_ids"])
        record = assemble_usage_record(
            pending.snapshot,
            [item for item in relevant if item.observation_id in cutoff],
            outcome=finalization.outcome,
            completed_at_utc=finalization.completed_at_utc,
        )
        if mixed:
            record.diagnostics.append("dsh_web_mixed_input")
        service.store.finalize(record)
        _close_shared_operations(service, pending.snapshot, operations[1:], terminal)
    for item in observations:
        if item.accounting_kind != "dsh_web_reconciled" or not item.metadata.get("operation_id"):
            continue
        pending = service.store.get_pending_turn(item.metadata["operation_id"])
        if pending is None or pending.finalized or pending.snapshot.provider_turn_id is not None:
            continue
        finalization = pending.finalization or UsageFinalization(
            turn_id=pending.snapshot.turn_id,
            outcome="failed",
            completed_at_utc=item.timestamp_utc,
            metadata={"observation_ids": [], "dsh_web_abandoned_before_claim": True},
        )
        service.store.set_finalization(pending.snapshot.turn_id, finalization)
        record = assemble_usage_record(
            pending.snapshot,
            [],
            outcome=finalization.outcome,
            completed_at_utc=finalization.completed_at_utc,
        )
        record.diagnostics.append("dsh_web_abandoned_before_claim")
        service.store.finalize(record)


def _close_shared_operations(
    service: UsageService,
    canonical: UsageTurnSnapshot,
    operations: list[str],
    terminal: UsageObservation,
) -> None:
    """Close co-consumed requests with an explicit unavailable sender allocation.

    Only the canonical record carries the native measurements. Secondary
    operation records retain outcome and an exact private reference to it.
    """

    for operation_id in operations:
        pending = service.store.get_pending_turn(operation_id)
        if pending is None:
            snapshot = canonical.model_copy(
                update={"turn_id": operation_id, "provider_turn_id": None}
            )
            service.store.put_pending_turn(snapshot)
            pending = service.store.get_pending_turn(operation_id)
        assert pending is not None
        if pending.finalized:
            continue
        snapshot = pending.snapshot.model_copy(
            update={
                "metadata": {
                    **pending.snapshot.metadata,
                    "dsh_web_shared_accounting_turn": canonical.turn_id,
                    "dsh_web_shared_native_turn": canonical.provider_turn_id,
                }
            }
        )
        service.store.put_pending_turn(snapshot)
        finalization = pending.finalization or UsageFinalization(
            turn_id=operation_id,
            outcome=cast(Any, terminal.lifecycle),
            completed_at_utc=terminal.timestamp_utc,
            metadata={"observation_ids": []},
        )
        service.store.set_finalization(operation_id, finalization)
        record = assemble_usage_record(
            snapshot,
            [],
            outcome=finalization.outcome,
            completed_at_utc=finalization.completed_at_utc,
        )
        record.diagnostics.append("dsh_web_usage_shared_with_another_operation")
        service.store.finalize(record)
