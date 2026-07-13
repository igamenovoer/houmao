"""Typed boundary models for long-horizon TUI qualification.

The models in this module represent the reviewed operation catalog, expanded
provider matrix, persisted attempt state, and independent verdict documents.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


ProviderName = Literal["claude", "codex", "kimi"]
ProcedureId = Literal["st-01", "st-02", "st-03", "st-04", "st-05"]
OperationKind = Literal[
    "type_text",
    "submit_text",
    "send_keys",
    "repeat_operation",
    "tmux_control",
    "restart_provider",
]
AttemptPhase = Literal[
    "planned",
    "preflight_passed",
    "capturing",
    "awaiting_manual_labels",
    "labels_complete",
    "replaying",
    "reported",
    "failed",
]
VerdictStatus = Literal["pass", "fail", "not_qualified", "incomplete"]


@dataclass(frozen=True)
class CheckpointDefinition:
    """One reviewed checkpoint attached to a user operation."""

    description: str
    evaluator: str = "operator_review"

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible checkpoint payload."""

        return asdict(self)


@dataclass(frozen=True)
class OperationDefinition:
    """One exact UC-02 user operation and its two checkpoint domains."""

    number: int
    kind: OperationKind
    instruction: str
    engineering_checkpoint: CheckpointDefinition
    tracker_checkpoint: CheckpointDefinition

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible operation payload."""

        return asdict(self)


@dataclass(frozen=True)
class ProcedureDefinition:
    """One reviewed long-horizon procedure shared by selected providers."""

    procedure_id: ProcedureId
    title: str
    providers: tuple[ProviderName, ...]
    allowed_final_paths: tuple[str, ...]
    transition_families: tuple[str, ...]
    operations: tuple[OperationDefinition, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible procedure payload."""

        return asdict(self)


@dataclass(frozen=True)
class FixtureContract:
    """Pinned vendored-project contract for every qualification attempt."""

    path: str
    upstream_revision: str
    expected_collection_count: int

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible fixture payload."""

        return asdict(self)


@dataclass(frozen=True)
class LongHorizonSuite:
    """Validated machine-readable UC-02 suite catalog."""

    schema_version: int
    suite_id: str
    source_path: str
    source_sha256: str
    fixture: FixtureContract
    safe_prefix: str
    allowed_tokens: tuple[str, ...]
    capture_sample_interval_seconds: float
    procedures: tuple[ProcedureDefinition, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible suite payload."""

        return asdict(self)


@dataclass(frozen=True)
class PlannedOperation:
    """One operation expanded for a concrete provider/procedure cell."""

    event_id: str
    provider: ProviderName
    procedure_id: ProcedureId
    number: int
    kind: OperationKind
    instruction: str
    engineering_checkpoint: CheckpointDefinition
    tracker_checkpoint: CheckpointDefinition

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible planned-operation payload."""

        return asdict(self)


@dataclass(frozen=True)
class PlannedCell:
    """One concrete provider/procedure matrix cell."""

    cell_id: str
    provider: ProviderName
    procedure_id: ProcedureId
    allowed_final_paths: tuple[str, ...]
    transition_families: tuple[str, ...]
    operations: tuple[PlannedOperation, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible planned-cell payload."""

        return asdict(self)


@dataclass(frozen=True)
class SuitePlan:
    """Expanded full or diagnostic subset of the qualification matrix."""

    suite_id: str
    source_sha256: str
    cells: tuple[PlannedCell, ...]
    total_operations: int
    complete_matrix: bool

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible plan payload."""

        return asdict(self)


@dataclass(frozen=True)
class AttemptState:
    """Persisted resumable phase state for one numbered cell attempt."""

    schema_version: int
    cell_id: str
    attempt_id: str
    phase: AttemptPhase
    input_digests: dict[str, str]
    selected_for_aggregate: bool
    failure_code: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible attempt-state payload."""

        return asdict(self)


@dataclass(frozen=True)
class QualificationVerdict:
    """Independent engineering or tracker verdict for one attempt."""

    schema_version: int
    domain: Literal["engineering", "tracker"]
    status: VerdictStatus
    code: str
    evidence_paths: tuple[str, ...]
    notes: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible verdict payload."""

        return asdict(self)


@dataclass(frozen=True)
class AggregateResult:
    """Suite-level qualification result derived from selected attempts."""

    schema_version: int
    status: VerdictStatus
    qualified_cells: int
    required_cells: int
    completed_operations: int
    required_operations: int
    missing_obligations: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible aggregate payload."""

        return asdict(self)
