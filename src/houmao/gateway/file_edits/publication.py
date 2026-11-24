"""Authorize, settle, and recover exact owner-side file publication attempts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
import time
from typing import Protocol

from houmao.agents.realm_controller.owner_admission import (
    OwnerAdmissionError,
    OwnerMaintenanceClaim,
    load_owner_maintenance,
    reserve_owner_maintenance,
)
from houmao.gateway.access import GatewayAccessError, GatewayAccessPolicy
from houmao.gateway.access_models import GatewayTarget
from houmao.gateway.authorization_models import AuthorizationDecision
from houmao.gateway.file_edits.contracts import FileActor, FilePushReceipt, FilePushRequest
from houmao.gateway.file_edits.journal import PushJournal, PushRecord
from houmao.gateway.file_edits.projection import FileProjection, ProjectionConflict
from houmao.gateway.file_edits.storage import MountStorage

_PUSH_BUDGET_SECONDS = 15.0
_UNSETTLED = {"pending", "unknown"}


class NativeFileTransaction(Protocol):
    """The exact native maintenance transaction for one prepared revision."""

    @property
    def settlement(self) -> Mapping[str, object] | None:
        """Return attributable readiness and settlement after closing maintenance."""

    def publish(self) -> Mapping[str, object]:
        """Switch the marker and activate this mount after owner authorization."""


class NativeFileMount(Protocol):
    """A provisioned mount adapter tied to the exact selected native execution."""

    @property
    def storage(self) -> MountStorage:
        """Return retained owner-private Git and draft state for the mount."""

    @property
    def projection(self) -> FileProjection:
        """Return the validated native projection selected at launch."""

    def validate(self, files: dict[str, bytes]) -> None:
        """Validate logical candidate content for this mount."""

    def native_transaction(
        self, operation_id: str, candidate: str, expected: str, *, deadline_monotonic: float
    ) -> AbstractContextManager[NativeFileTransaction]:
        """Acquire immediate native maintenance and release it on context exit."""

    def native_status(self, operation_id: str) -> Mapping[str, object]:
        """Read settlement for the exact attempt without dispatching work."""


def reconcile_projection_index(
    storage: MountStorage,
    projection: FileProjection,
    *,
    handoff_evidence: Callable[[str], AuthorizationDecision | None],
) -> None:
    """Recover a complete publication from retained owner and disk evidence."""

    journal = PushJournal(storage.root)
    with journal.dispatch_guard() as held:
        if held:
            _reconcile_under_dispatch(storage, projection, journal, handoff_evidence)


def _reconcile_under_dispatch(
    storage: MountStorage,
    projection: FileProjection,
    journal: PushJournal,
    handoff_evidence: Callable[[str], AuthorizationDecision | None],
) -> None:
    """Persist exact publication evidence before advancing the repairable index."""

    base = storage.published_commit()
    try:
        marker, operation = projection.publication_identity()
        if marker == base:
            return
        record = journal.for_marker(base, marker, operation)
        if not _matches_handoff(record, handoff_evidence(record.handoff_id)):
            raise GatewayAccessError(409, "file_projection_conflict")
        projection.verify_revision(marker, storage.candidate(marker).files)
        if record.receipt.published_commit != marker:
            journal.save(
                record,
                record.receipt.model_copy(
                    update={
                        "outcome": "published",
                        "published_commit": marker,
                        "activation": "unknown",
                        "reason": "activation_unconfirmed",
                    }
                ),
            )
        storage.advance_published(base, marker)
    except ProjectionConflict:
        raise GatewayAccessError(409, "file_projection_conflict") from None


class FilePublication:
    """Coordinate an existing file mount with retained owner and caller authority."""

    def __init__(
        self,
        mount: NativeFileMount,
        policy: GatewayAccessPolicy,
        manifest_path: Path,
        target: GatewayTarget,
        *,
        listener_is_current: Callable[[], bool],
    ) -> None:
        """Bind the coordinator to the currently selected verified owner."""

        self.m_mount: NativeFileMount = mount
        self.m_policy: GatewayAccessPolicy = policy
        self.m_manifest_path: Path = manifest_path
        self.m_target: GatewayTarget = target
        self.m_listener_is_current: Callable[[], bool] = listener_is_current
        self.m_journal: PushJournal = PushJournal(mount.storage.root)

    def push(
        self, request: FilePushRequest, decision: AuthorizationDecision, publisher: FileActor
    ) -> FilePushReceipt:
        """Dispatch at most one exact rendition of a push operation ID."""

        if request.when_idle and decision.actor.kind != "self":
            raise GatewayAccessError(403, "file_scheduling_requires_managed_self")
        if request.when_idle:
            candidate = self.m_mount.storage.candidate(request.commit_id)
            if candidate.base_commit != request.expected_base:
                raise GatewayAccessError(409, "published_base_changed")
        with self.m_journal.dispatch_guard() as held:
            record, created = self.m_journal.begin(request, decision, publisher)
            if not created:
                receipt = self._recover(record) if held else record.receipt
            elif request.when_idle:
                receipt = record.receipt
            elif not held:
                receipt = self._finish_without_handoff(record, "busy", "mount_publication_busy")
            else:
                receipt = self._schedule(record)
            self._require_current(decision)
            return receipt

    def dispatch_scheduled(self) -> None:
        """Try the oldest admitted work without replaying any interrupted dispatch."""

        with self.m_journal.dispatch_guard() as held:
            if not held or not self.m_listener_is_current():
                return
            for record in self.m_journal.scheduled(self.m_target.incarnation):
                if not self.m_listener_is_current():
                    return
                if record.receipt.outcome != "queued":
                    self._recover(record)
                    continue
                if record.request.target != self.m_target:
                    self._finish_without_handoff(record, "refused", "file_target_changed")
                    continue
                if not self.m_policy.revalidate(record.decision):
                    self._finish_without_handoff(record, "refused", "insufficient_authority")
                    continue
                record = self.m_journal.start_scheduled(record)
                if record.receipt.outcome == "pending":
                    self._schedule(record)
                return

    def status(self, operation_id: str, decision: AuthorizationDecision) -> FilePushReceipt:
        """Recover attributable evidence without issuing a publication request."""

        with self.m_journal.dispatch_guard() as held:
            record = self.m_journal.read(operation_id)
            receipt = self._recover(record) if held else record.receipt
            self._require_current(decision)
            return receipt

    def reconcile_visible_revision(self) -> None:
        """Repair the logical published index after a native marker switch."""

        reconcile_projection_index(
            self.m_mount.storage,
            self.m_mount.projection,
            handoff_evidence=self.m_policy.handoff_evidence,
        )

    def _schedule(self, record: PushRecord) -> FilePushReceipt:
        """Prepare off-path, claim the owner and native execution, then order revocation."""

        request = record.request
        mount = self.m_mount
        claim: OwnerMaintenanceClaim | None = None
        authorized = False
        activated: Mapping[str, object] = {}
        transaction: NativeFileTransaction | None = None
        try:
            _reconcile_under_dispatch(
                mount.storage, mount.projection, self.m_journal, self.m_policy.handoff_evidence
            )
            candidate = mount.storage.candidate(request.commit_id)
            base = mount.storage.published_commit()
            if candidate.base_commit != request.expected_base or base != request.expected_base:
                return self._finish_without_handoff(
                    record, "conflict", "published_base_changed", published_commit=base
                )
            mount.validate(candidate.files)
            self._verify_preconditions(record)
            mount.projection.prepare(candidate.commit_id, candidate.files)
            claim = reserve_owner_maintenance(
                self.m_manifest_path, request.target.incarnation, operation_id=record.handoff_id
            )
            with mount.native_transaction(
                record.handoff_id,
                request.commit_id,
                request.expected_base,
                deadline_monotonic=time.monotonic() + _PUSH_BUDGET_SECONDS,
            ) as active:
                transaction = active
                self._verify_preconditions(record)
                mount.projection.verify_revision(candidate.commit_id, candidate.files)
                if request.when_idle and not self.m_listener_is_current():
                    raise GatewayAccessError(403, "file_target_changed")
                if not claim.active():
                    raise GatewayAccessError(409, "owner_maintenance_changed")
                self.m_policy.handoff(record.decision, operation_id=record.handoff_id)
                authorized = True
                claim.handoff()
                activated = active.publish()
        except OwnerAdmissionError as error:
            if not authorized:
                state = "busy" if error.code in {"not_ready", "uncertain"} else "unavailable"
                return self._finish_pre_handoff(
                    record, claim, transaction, state, "owner_maintenance_unavailable"
                )
            if claim is not None:
                claim.retain_before_handoff(evidence="file_owner_handoff_unconfirmed")
        except GatewayAccessError as error:
            if not authorized:
                if error.status_code in {401, 403}:
                    self._finish_pre_handoff(record, claim, transaction, "refused", error.code)
                    raise
                state = (
                    "busy"
                    if error.code in {"native_busy", "file_native_busy"}
                    else ("conflict" if error.status_code == 409 else "unavailable")
                )
                return self._finish_pre_handoff(record, claim, transaction, state, error.code)
        except ProjectionConflict:
            if not authorized:
                return self._finish_pre_handoff(
                    record, claim, transaction, "conflict", "file_projection_conflict"
                )
        except (OSError, TimeoutError, RuntimeError, ValueError):
            if not authorized:
                return self._finish_pre_handoff(
                    record, claim, transaction, "unavailable", "file_publication_unavailable"
                )
        return self._settle(
            record,
            claim,
            activated,
            transaction.settlement if transaction is not None else None,
        )

    def _verify_preconditions(self, record: PushRecord) -> None:
        """Ensure the owner still publishes the exact candidate base on disk."""

        base = record.request.expected_base
        mount = self.m_mount
        if mount.storage.published_commit() != base or mount.projection.published_marker() != base:
            raise ProjectionConflict("Managed publication changed.")
        mount.projection.verify_revision(base, mount.storage.published_files(base))

    def _recover(self, record: PushRecord) -> FilePushReceipt:
        """Compare independent evidence from owner policy, projection, and native execution."""

        receipt = record.receipt
        if receipt.outcome not in _UNSETTLED and (
            receipt.outcome != "published" or (receipt.native_settled and receipt.native_ready)
        ):
            if (
                receipt.native_settled
                and receipt.native_ready
                and record.request.target == self.m_target
            ):
                claim = load_owner_maintenance(
                    self.m_manifest_path, record.request.target.incarnation, record.handoff_id
                )
                if claim is not None:
                    self._finish_owner_claim(claim, receipt.model_dump())
            return receipt
        decision = self.m_policy.handoff_evidence(record.handoff_id)
        if decision is None:
            claim = load_owner_maintenance(
                self.m_manifest_path, record.request.target.incarnation, record.handoff_id
            )
            if claim is None:
                return self._finish_without_handoff(
                    record, "unavailable", "publication_preparation_interrupted"
                )
            # No publication was authorized. A lost reservation still needs native evidence.
            evidence = self._read_native_evidence(record)
            released = (
                record.request.target == self.m_target
                and bool(evidence)
                and (self._finish_owner_claim(claim, evidence))
            )
            return self._finish_without_handoff(
                record, "unavailable" if released else "unknown", "publication_handoff_not_recorded"
            )
        if not _matches_handoff(record, decision):
            raise GatewayAccessError(409, "file_handoff_conflict")
        claim = load_owner_maintenance(
            self.m_manifest_path, record.request.target.incarnation, record.handoff_id
        )
        evidence = self._read_native_evidence(record)
        return self._settle(record, claim, evidence, evidence)

    def _read_native_evidence(self, record: PushRecord) -> Mapping[str, object]:
        """Read only the exact current native target's attributable settlement."""

        if record.request.target != self.m_target:
            return {}
        try:
            return self.m_mount.native_status(record.handoff_id)
        except (GatewayAccessError, OSError, RuntimeError, ValueError):
            return {}

    def _settle(
        self,
        record: PushRecord,
        claim: OwnerMaintenanceClaim | None,
        activated: Mapping[str, object],
        settlement: Mapping[str, object] | None,
    ) -> FilePushReceipt:
        """Reconcile the published marker even when native completion is unconfirmed."""

        mount = self.m_mount
        request = record.request
        native = settlement or {}
        previous = record.receipt
        published = previous.published_commit == request.commit_id
        marker: str | None = None
        verified_switch = False
        try:
            marker, operation = mount.projection.publication_identity()
            if marker == request.commit_id and operation == record.handoff_id:
                candidate = mount.storage.candidate(request.commit_id)
                mount.projection.verify_revision(request.commit_id, candidate.files)
                verified_switch = published = True
        except (GatewayAccessError, ProjectionConflict, OSError, ValueError):
            marker = None
        effective = published and (
            activated.get("effective_commit") == request.commit_id
            or native.get("effective_commit") == request.commit_id
            or previous.effective_commit == request.commit_id
        )
        partial = activated.get("outcome") == "partial" or native.get("outcome") == "partial"
        stopped_at_base = (
            not published
            and marker == request.expected_base
            and native.get("native_settled") is True
            and native.get("native_ready") is True
        )
        receipt = previous.model_copy(
            update={
                "outcome": "published"
                if published
                else "refused"
                if stopped_at_base
                else "unknown",
                "published_commit": (
                    request.commit_id
                    if published
                    else marker
                    if stopped_at_base
                    else previous.published_commit
                ),
                "effective_commit": request.commit_id if effective else None,
                "activation": "effective" if effective else "partial" if partial else "unknown",
                "native_settled": _native_flag(native, "native_settled", previous.native_settled),
                "native_ready": _native_flag(native, "native_ready", previous.native_ready),
                "reason": (
                    None
                    if effective
                    else "publication_not_observed"
                    if stopped_at_base
                    else "publication_or_activation_unconfirmed"
                ),
            }
        )
        saved = self.m_journal.save(record, receipt)
        if verified_switch:
            try:
                mount.storage.advance_published(request.expected_base, request.commit_id)
            except (GatewayAccessError, OSError, ValueError):
                # A later read repairs the index from the durable receipt and marker.
                pass
        if claim is not None and record.request.target == self.m_target:
            self._finish_owner_claim(claim, native)
        return saved

    def _finish_without_handoff(
        self, record: PushRecord, outcome: str, reason: str, *, published_commit: str | None = None
    ) -> FilePushReceipt:
        """Retain a fixed refusal without changing native files."""

        receipt = record.receipt.model_copy(
            update={"outcome": outcome, "reason": reason, "published_commit": published_commit}
        )
        return self.m_journal.save(record, receipt)

    def _finish_pre_handoff(
        self,
        record: PushRecord,
        claim: OwnerMaintenanceClaim | None,
        transaction: NativeFileTransaction | None,
        outcome: str,
        reason: str,
    ) -> FilePushReceipt:
        """Keep admission closed if the earlier native attempt may still hold it."""

        if claim is None:
            return self._finish_before_dispatch(record, outcome, reason)
        native = (transaction.settlement or {}) if transaction is not None else {}
        if reason == "file_native_admission_unconfirmed" or (
            transaction is not None
            and not (native.get("native_settled") is True and native.get("native_ready") is True)
        ):
            claim.retain_before_handoff(evidence="file_native_admission_unconfirmed")
            return self._finish_without_handoff(
                record, "unknown", "file_native_admission_unconfirmed"
            )
        claim.release_before_handoff(evidence="file_publication_refused")
        return self._finish_before_dispatch(record, outcome, reason)

    def _finish_before_dispatch(
        self, record: PushRecord, outcome: str, reason: str
    ) -> FilePushReceipt:
        """Retain an idle retry only after establishing that native handoff did not occur."""

        if outcome == "busy" and record.request.when_idle:
            outcome = "queued"
        return self._finish_without_handoff(record, outcome, reason)

    @staticmethod
    def _finish_owner_claim(claim: OwnerMaintenanceClaim, evidence: Mapping[str, object]) -> bool:
        """Retain the guard until the exact native operation is settled and ready."""

        settled = evidence.get("native_settled") is True
        ready = evidence.get("native_ready") is True
        try:
            return claim.finish(
                evidence="file_publication_settlement", settled=settled, ready=ready
            )
        except OwnerAdmissionError:
            # A replacement generation may only fence this claim via owner recovery.
            return False

    def _require_current(self, decision: AuthorizationDecision) -> None:
        """Refuse disclosure through superseded caller authority."""

        if not self.m_policy.revalidate(decision):
            raise GatewayAccessError(403, "insufficient_authority")


def _native_flag(evidence: Mapping[str, object], name: str, previous: bool | None) -> bool | None:
    """Preserve attributable flags across incidental native observation loss."""

    value = evidence.get(name)
    return value if isinstance(value, bool) else previous


def _matches_handoff(record: PushRecord, evidence: AuthorizationDecision | None) -> bool:
    """Compare the full original authority with the result of its current recheck."""

    return (
        evidence is not None
        and evidence.model_copy(update={"policy_revision": record.decision.policy_revision})
        == record.decision
    )
