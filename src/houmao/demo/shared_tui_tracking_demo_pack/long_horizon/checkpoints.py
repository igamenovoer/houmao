"""Engineering checkpoint evaluation for copied long-horizon projects."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import save_json_atomic
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (
    QualificationVerdict,
    VerdictStatus,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.projects import tree_sha256


CheckpointStatus = Literal["pass", "fail"]


@dataclass(frozen=True)
class CheckpointResult:
    """Evidence-backed result for one engineering checkpoint."""

    evaluator: str
    status: CheckpointStatus
    description: str
    evidence: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible checkpoint result."""

        return asdict(self)


@dataclass(frozen=True)
class FinalProjectEvidence:
    """Final worktree and immutable-source evidence for one attempt."""

    schema_version: int
    procedure_id: str
    status: CheckpointStatus
    verdict_code: str
    changed_paths: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    status_text: str
    diff_sha256: str
    source_sha256_before: str
    source_sha256_after: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible final-project payload."""

        return asdict(self)


def evaluate_file_content(
    *,
    project_root: Path,
    relative_path: str,
    expected_text: str,
) -> CheckpointResult:
    """Evaluate exact UTF-8 file content inside the copied project."""

    target = _resolve_project_path(project_root=project_root, relative_path=relative_path)
    observed = target.read_text(encoding="utf-8") if target.is_file() else None
    passed = observed == expected_text
    return CheckpointResult(
        evaluator="file_content",
        status="pass" if passed else "fail",
        description=f"{relative_path} has exact expected content",
        evidence={"path": str(target), "observed": observed},
    )


def evaluate_command(
    *,
    project_root: Path,
    command: tuple[str, ...],
    expected_exit_code: int = 0,
    output_pattern: str | None = None,
) -> CheckpointResult:
    """Run and evaluate one deterministic harness command."""

    completed = subprocess.run(
        list(command),
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = f"{completed.stdout}{completed.stderr}"
    pattern_matches = output_pattern is None or re.search(output_pattern, combined) is not None
    passed = completed.returncode == expected_exit_code and pattern_matches
    return CheckpointResult(
        evaluator="command",
        status="pass" if passed else "fail",
        description="Command exits and emits the declared result",
        evidence={
            "command": list(command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    )


def evaluate_visible_pattern(*, visible_text: str, pattern: str) -> CheckpointResult:
    """Evaluate one visible native-TUI response pattern."""

    passed = re.search(pattern, visible_text, re.MULTILINE) is not None
    return CheckpointResult(
        evaluator="visible_pattern",
        status="pass" if passed else "fail",
        description=f"Visible pane matches {pattern!r}",
        evidence={"pattern": pattern, "visible_text": visible_text},
    )


def evaluate_pane_geometry(
    *, observed_columns: int, observed_rows: int, expected_columns: int, expected_rows: int
) -> CheckpointResult:
    """Evaluate exact tmux pane geometry."""

    passed = (observed_columns, observed_rows) == (expected_columns, expected_rows)
    return CheckpointResult(
        evaluator="pane_geometry",
        status="pass" if passed else "fail",
        description=f"Pane geometry is {expected_columns}x{expected_rows}",
        evidence={"columns": observed_columns, "rows": observed_rows},
    )


def evaluate_process_liveness(*, pid: int) -> CheckpointResult:
    """Evaluate whether one recorded provider process is alive."""

    alive = True
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        alive = False
    return CheckpointResult(
        evaluator="process_liveness",
        status="pass" if alive else "fail",
        description=f"Process {pid} is alive",
        evidence={"pid": pid, "alive": alive},
    )


def evaluate_operator_review(
    *, description: str, accepted: bool, evidence_path: str
) -> CheckpointResult:
    """Record one explicit operator-reviewed engineering assertion."""

    return CheckpointResult(
        evaluator="operator_review",
        status="pass" if accepted else "fail",
        description=description,
        evidence={"evidence_path": evidence_path, "accepted": accepted},
    )


def finalize_project_evidence(
    *,
    project_root: Path,
    source_root: Path,
    source_sha256_before: str,
    procedure_id: str,
    allowed_paths: tuple[str, ...],
    output_dir: Path,
) -> FinalProjectEvidence:
    """Persist final status/diff and judge mutation and source-integrity scope."""

    status_text = _run_git(project_root=project_root, args=["status", "--short"]).stdout
    tracked = _run_git(
        project_root=project_root,
        args=["diff", "--name-only", "houmao-baseline"],
    ).stdout.splitlines()
    untracked = _run_git(
        project_root=project_root,
        args=["ls-files", "--others", "--exclude-standard"],
    ).stdout.splitlines()
    changed_paths = tuple(sorted(set(tracked + untracked)))
    diff_text = _combined_diff(project_root=project_root, untracked=untracked)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "project-final-status.txt").write_text(status_text, encoding="utf-8")
    (output_dir / "project-final.diff").write_text(diff_text, encoding="utf-8")
    source_sha256_after = tree_sha256(source_root)
    allowed = tuple(sorted(allowed_paths))
    mutation_ok = changed_paths == allowed
    source_ok = source_sha256_after == source_sha256_before
    status: CheckpointStatus = "pass" if mutation_ok and source_ok else "fail"
    verdict_code = "pass"
    if not source_ok or not mutation_ok:
        verdict_code = "unsafe_mutation_scope"
    evidence = FinalProjectEvidence(
        schema_version=1,
        procedure_id=procedure_id,
        status=status,
        verdict_code=verdict_code,
        changed_paths=changed_paths,
        allowed_paths=allowed,
        status_text=status_text,
        diff_sha256=hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
        source_sha256_before=source_sha256_before,
        source_sha256_after=source_sha256_after,
    )
    save_json_atomic(output_dir / "final-project-evidence.json", evidence.to_payload())
    return evidence


def persist_engineering_verdict(
    *,
    output_dir: Path,
    checkpoint_results: tuple[CheckpointResult, ...],
    final_project: FinalProjectEvidence,
) -> QualificationVerdict:
    """Persist the engineering verdict without invoking tracker evaluation."""

    failed_checkpoints = tuple(result for result in checkpoint_results if result.status == "fail")
    if final_project.status == "fail":
        status: VerdictStatus = "fail"
        code = final_project.verdict_code
    elif failed_checkpoints:
        status = "fail"
        code = "scenario_task_divergence"
    else:
        status = "pass"
        code = "pass"
    checkpoint_path = output_dir / "checkpoint-results.json"
    save_json_atomic(
        checkpoint_path,
        {
            "schema_version": 1,
            "results": [item.to_payload() for item in checkpoint_results],
        },
    )
    verdict = QualificationVerdict(
        schema_version=1,
        domain="engineering",
        status=status,
        code=code,
        evidence_paths=(
            str(checkpoint_path),
            str(output_dir / "final-project-evidence.json"),
            str(output_dir / "project-final-status.txt"),
            str(output_dir / "project-final.diff"),
        ),
        notes=tuple(result.description for result in failed_checkpoints),
    )
    save_json_atomic(output_dir / "engineering-verdict.json", verdict.to_payload())
    return verdict


def _combined_diff(*, project_root: Path, untracked: list[str]) -> str:
    """Return tracked and no-index untracked diffs as retained text evidence."""

    tracked_diff = _run_git(
        project_root=project_root,
        args=["diff", "--binary", "houmao-baseline"],
    ).stdout
    parts = [tracked_diff]
    for relative_path in sorted(untracked):
        completed = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "/dev/null", relative_path],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError(f"Unable to diff untracked path {relative_path}: {completed.stderr}")
        parts.append(completed.stdout)
    return "".join(parts)


def _resolve_project_path(*, project_root: Path, relative_path: str) -> Path:
    """Resolve a checkpoint path without allowing project escape."""

    resolved_root = project_root.resolve()
    target = (resolved_root / relative_path).resolve()
    if target == resolved_root or not target.is_relative_to(resolved_root):
        raise ValueError(f"Checkpoint path escapes copied project: {relative_path}")
    return target


def _run_git(*, project_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one checked Git query in a copied project."""

    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
