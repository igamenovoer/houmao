"""Load, validate, and expand the reviewed UC-02 execution catalog."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (
    CheckpointDefinition,
    FixtureContract,
    LongHorizonSuite,
    OperationDefinition,
    OperationKind,
    PlannedCell,
    PlannedOperation,
    ProcedureDefinition,
    ProcedureId,
    ProviderName,
    SuitePlan,
)


_CATALOG_RELATIVE_PATH = Path("scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json")
_ALLOWED_PROVIDERS: tuple[ProviderName, ...] = ("claude", "codex", "kimi")
_ALLOWED_PROCEDURES: tuple[ProcedureId, ...] = (
    "st-01",
    "st-02",
    "st-03",
    "st-04",
    "st-05",
)
_ALLOWED_OPERATION_KINDS: tuple[OperationKind, ...] = (
    "type_text",
    "submit_text",
    "send_keys",
    "repeat_operation",
    "tmux_control",
    "restart_provider",
)
_EXPECTED_PROVIDERS: dict[ProcedureId, tuple[ProviderName, ...]] = {
    "st-01": ("claude", "codex"),
    "st-02": ("claude", "codex"),
    "st-03": ("claude", "codex", "kimi"),
    "st-04": ("claude", "codex", "kimi"),
    "st-05": ("codex", "kimi"),
}
_EXPECTED_OPERATION_COUNTS: dict[ProcedureId, int] = {
    "st-01": 20,
    "st-02": 20,
    "st-03": 20,
    "st-04": 20,
    "st-05": 21,
}
_EXPECTED_TOKENS = ("SAFE", "PLACEHOLDER_LITERAL", "PANE", "LAUNCH_COMMAND")
_TOKEN_PATTERN = re.compile(r"\{\{([A-Z_]+)\}\}")


def default_catalog_path(*, repo_root: Path) -> Path:
    """Return the checked-in long-horizon catalog path."""

    return (repo_root / _CATALOG_RELATIVE_PATH).resolve()


def load_suite_catalog(
    *,
    repo_root: Path,
    catalog_path: Path | None = None,
    validate_source_digest: bool = True,
) -> LongHorizonSuite:
    """Load and validate one long-horizon suite catalog.

    Parameters
    ----------
    repo_root : Path
        Repository root used to resolve catalog and source paths.
    catalog_path : Path or None
        Optional alternate catalog used by hermetic tests.
    validate_source_digest : bool
        Whether to require the current UC-02 source digest.

    Returns
    -------
    LongHorizonSuite
        Validated suite definition.
    """

    selected_path = (catalog_path or default_catalog_path(repo_root=repo_root)).resolve()
    payload = _require_mapping(json.loads(selected_path.read_text(encoding="utf-8")), "catalog")
    suite = _parse_suite(payload)
    _validate_suite(suite=suite)
    if validate_source_digest:
        source_path = (repo_root / suite.source_path).resolve()
        observed_digest = _sha256_file(source_path)
        if observed_digest != suite.source_sha256:
            raise ValueError(
                "UC-02 source digest differs from the reviewed catalog: "
                f"expected {suite.source_sha256}, observed {observed_digest}"
            )
    return suite


def expand_matrix(
    *,
    suite: LongHorizonSuite,
    selected_cells: tuple[str, ...] = (),
    attempt_number: int = 1,
) -> SuitePlan:
    """Expand the provider/procedure catalog into stable matrix cells."""

    if attempt_number < 1:
        raise ValueError("attempt_number must be positive")
    requested = set(selected_cells)
    cells: list[PlannedCell] = []
    known_cell_ids: set[str] = set()
    for procedure in suite.procedures:
        for provider in procedure.providers:
            cell_id = f"{provider}:{procedure.procedure_id}"
            known_cell_ids.add(cell_id)
            if requested and cell_id not in requested:
                continue
            operations = tuple(
                PlannedOperation(
                    event_id=(
                        f"{provider}:{procedure.procedure_id}:"
                        f"attempt-{attempt_number:03d}:op-{item.number:03d}"
                    ),
                    provider=provider,
                    procedure_id=procedure.procedure_id,
                    number=item.number,
                    kind=item.kind,
                    instruction=item.instruction,
                    engineering_checkpoint=item.engineering_checkpoint,
                    tracker_checkpoint=item.tracker_checkpoint,
                )
                for item in procedure.operations
            )
            cells.append(
                PlannedCell(
                    cell_id=cell_id,
                    provider=provider,
                    procedure_id=procedure.procedure_id,
                    allowed_final_paths=procedure.allowed_final_paths,
                    transition_families=procedure.transition_families,
                    operations=operations,
                )
            )
    unknown = requested - known_cell_ids
    if unknown:
        raise ValueError(f"Unknown long-horizon cells: {', '.join(sorted(unknown))}")
    complete_matrix = not requested or requested == known_cell_ids
    return SuitePlan(
        suite_id=suite.suite_id,
        source_sha256=suite.source_sha256,
        cells=tuple(cells),
        total_operations=sum(len(item.operations) for item in cells),
        complete_matrix=complete_matrix,
    )


def expand_prompt_tokens(*, text: str, values: dict[str, str]) -> str:
    """Expand only the four reviewed UC-02 prompt tokens."""

    tokens = tuple(_TOKEN_PATTERN.findall(text))
    unknown = sorted(set(tokens) - set(_EXPECTED_TOKENS))
    if unknown:
        raise ValueError(f"Unknown long-horizon prompt tokens: {', '.join(unknown)}")
    missing = sorted(set(tokens) - set(values))
    if missing:
        raise ValueError(f"Missing long-horizon prompt token values: {', '.join(missing)}")
    expanded = text
    for token in tokens:
        expanded = expanded.replace(f"{{{{{token}}}}}", values[token])
    remaining = _TOKEN_PATTERN.findall(expanded)
    if remaining:
        raise ValueError(f"Unexpanded long-horizon prompt tokens: {', '.join(remaining)}")
    return expanded


def _parse_suite(payload: dict[str, Any]) -> LongHorizonSuite:
    """Parse one suite payload into typed models."""

    fixture_payload = _require_mapping(payload.get("fixture"), "fixture")
    procedures_payload = _require_list(payload.get("procedures"), "procedures")
    return LongHorizonSuite(
        schema_version=int(payload["schema_version"]),
        suite_id=str(payload["suite_id"]),
        source_path=str(payload["source_path"]),
        source_sha256=str(payload["source_sha256"]),
        fixture=FixtureContract(
            path=str(fixture_payload["path"]),
            upstream_revision=str(fixture_payload["upstream_revision"]),
            expected_collection_count=int(fixture_payload["expected_collection_count"]),
        ),
        safe_prefix=str(payload["safe_prefix"]),
        allowed_tokens=tuple(str(item) for item in _require_sequence(payload, "allowed_tokens")),
        capture_sample_interval_seconds=float(payload["capture_sample_interval_seconds"]),
        procedures=tuple(_parse_procedure(item) for item in procedures_payload),
    )


def _parse_procedure(payload: dict[str, Any]) -> ProcedureDefinition:
    """Parse one procedure payload."""

    procedure_id = cast(ProcedureId, str(payload["id"]))
    return ProcedureDefinition(
        procedure_id=procedure_id,
        title=str(payload["title"]),
        providers=tuple(
            cast(ProviderName, str(item)) for item in _require_sequence(payload, "providers")
        ),
        allowed_final_paths=tuple(
            str(item) for item in _require_sequence(payload, "allowed_final_paths")
        ),
        transition_families=tuple(
            str(item) for item in _require_sequence(payload, "transition_families")
        ),
        operations=tuple(
            _parse_operation(item)
            for item in _require_list(payload.get("operations"), "operations")
        ),
    )


def _parse_operation(payload: dict[str, Any]) -> OperationDefinition:
    """Parse one operation payload."""

    return OperationDefinition(
        number=int(payload["number"]),
        kind=cast(OperationKind, str(payload["kind"])),
        instruction=str(payload["instruction"]),
        engineering_checkpoint=CheckpointDefinition(
            description=str(payload["engineering_checkpoint"])
        ),
        tracker_checkpoint=CheckpointDefinition(description=str(payload["tracker_checkpoint"])),
    )


def _validate_suite(*, suite: LongHorizonSuite) -> None:
    """Validate exact matrix, operation, provider, and token obligations."""

    if suite.schema_version != 1:
        raise ValueError(f"Unsupported long-horizon schema version: {suite.schema_version}")
    if suite.allowed_tokens != _EXPECTED_TOKENS:
        raise ValueError(f"allowed_tokens must equal {_EXPECTED_TOKENS!r}")
    if suite.capture_sample_interval_seconds != 0.05:
        raise ValueError("capture_sample_interval_seconds must equal 0.05")
    procedure_ids = tuple(item.procedure_id for item in suite.procedures)
    if procedure_ids != _ALLOWED_PROCEDURES:
        raise ValueError(f"Procedures must appear exactly as {_ALLOWED_PROCEDURES!r}")
    for procedure in suite.procedures:
        if procedure.providers != _EXPECTED_PROVIDERS[procedure.procedure_id]:
            raise ValueError(
                f"{procedure.procedure_id} providers must equal "
                f"{_EXPECTED_PROVIDERS[procedure.procedure_id]!r}"
            )
        expected_count = _EXPECTED_OPERATION_COUNTS[procedure.procedure_id]
        if len(procedure.operations) != expected_count:
            raise ValueError(f"{procedure.procedure_id} must contain {expected_count} operations")
        numbers = tuple(item.number for item in procedure.operations)
        if numbers != tuple(range(1, expected_count + 1)):
            raise ValueError(f"{procedure.procedure_id} operation numbers are not contiguous")
        for operation in procedure.operations:
            if operation.kind not in _ALLOWED_OPERATION_KINDS:
                raise ValueError(f"Unsupported operation kind: {operation.kind}")
            unknown_tokens = set(_TOKEN_PATTERN.findall(operation.instruction)) - set(
                suite.allowed_tokens
            )
            if unknown_tokens:
                raise ValueError(
                    f"{procedure.procedure_id} operation {operation.number} uses unknown tokens: "
                    f"{', '.join(sorted(unknown_tokens))}"
                )
    plan = expand_matrix(suite=suite)
    if len(plan.cells) != 12 or plan.total_operations != 242:
        raise ValueError("Full long-horizon matrix must contain 12 cells and 242 operations")
    if any(item.provider not in _ALLOWED_PROVIDERS for item in plan.cells):
        raise ValueError("Long-horizon matrix contains an unsupported provider")


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_mapping(value: object, context: str) -> dict[str, Any]:
    """Return one validated string-key mapping."""

    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{context} must be an object")
    return cast(dict[str, Any], value)


def _require_list(value: object, context: str) -> list[dict[str, Any]]:
    """Return one validated list of mappings."""

    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{context} must be a list of objects")
    return cast(list[dict[str, Any]], value)


def _require_sequence(payload: dict[str, Any], key: str) -> list[object]:
    """Return one validated JSON list."""

    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return cast(list[object], value)
