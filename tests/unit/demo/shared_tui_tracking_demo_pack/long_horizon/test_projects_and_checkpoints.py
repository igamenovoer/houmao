"""Tests for Boltons preparation and engineering checkpoint evidence."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.attempts import create_attempt
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.catalog import load_suite_catalog
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.checkpoints import (
    evaluate_command,
    evaluate_file_content,
    evaluate_operator_review,
    evaluate_pane_geometry,
    evaluate_process_liveness,
    evaluate_visible_pattern,
    finalize_project_evidence,
    persist_engineering_verdict,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.planner import create_or_resume_plan
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.projects import (
    prepare_boltons_project,
    tree_sha256,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]


def test_prepare_real_boltons_fixture_and_preserve_source(tmp_path: Path) -> None:
    """A fresh attempt copy has the pinned baseline and 437 collected tests."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)
    source_root = (_REPO_ROOT / suite.fixture.path).resolve()
    source_before = tree_sha256(source_root)
    paths, _ = _create_repo_local_plan(tmp_path=tmp_path)
    create_attempt(paths=paths, cell_id="codex:st-05")

    manifest = prepare_boltons_project(
        repo_root=_REPO_ROOT,
        paths=paths,
        fixture=suite.fixture,
        cell_id="codex:st-05",
        attempt_number=1,
        python_executable=Path(sys.executable),
    )

    assert manifest.collection_count == 437
    assert manifest.initial_status == ""
    assert len(manifest.baseline_commit) == 40
    assert manifest.source_sha256 == manifest.copied_sha256 == source_before
    assert tree_sha256(source_root) == source_before


def test_checkpoint_evaluators_and_final_scope(tmp_path: Path) -> None:
    """Checkpoint primitives retain evidence and enforce exact changed paths."""

    paths, project_root, source_root, source_digest = _prepared_project(tmp_path=tmp_path)
    target = project_root / "houmao_artifacts" / "st05.txt"
    target.parent.mkdir()
    target.write_text("boltons long horizon state\n", encoding="utf-8")

    assert (
        evaluate_file_content(
            project_root=project_root,
            relative_path="houmao_artifacts/st05.txt",
            expected_text="boltons long horizon state\n",
        ).status
        == "pass"
    )
    assert (
        evaluate_command(
            project_root=project_root,
            command=(sys.executable, "-c", "print('OK')"),
            output_pattern="OK",
        ).status
        == "pass"
    )
    assert evaluate_visible_pattern(visible_text="ready ST05-H", pattern="ST05-H").status == (
        "pass"
    )
    assert (
        evaluate_pane_geometry(
            observed_columns=88,
            observed_rows=28,
            expected_columns=88,
            expected_rows=28,
        ).status
        == "pass"
    )
    assert evaluate_process_liveness(pid=os.getpid()).status == "pass"
    assert (
        evaluate_operator_review(
            description="response is exact",
            accepted=False,
            evidence_path="recording/frame-1",
        ).status
        == "fail"
    )

    evidence = finalize_project_evidence(
        project_root=project_root,
        source_root=source_root,
        source_sha256_before=source_digest,
        procedure_id="st-05",
        allowed_paths=("houmao_artifacts/st05.txt",),
        output_dir=paths.attempt_root(cell_id="codex:st-05", attempt_number=1) / "engineering",
    )
    assert evidence.status == "pass"
    assert evidence.changed_paths == ("houmao_artifacts/st05.txt",)
    assert (
        paths.attempt_root(cell_id="codex:st-05", attempt_number=1)
        / "engineering/project-final.diff"
    ).is_file()
    verdict = persist_engineering_verdict(
        output_dir=paths.attempt_root(cell_id="codex:st-05", attempt_number=1) / "engineering",
        checkpoint_results=(
            evaluate_operator_review(
                description="provider response checkpoint",
                accepted=False,
                evidence_path="recording/frame-1",
            ),
        ),
        final_project=evidence,
    )
    assert verdict.status == "fail"
    assert verdict.code == "scenario_task_divergence"


def test_undeclared_project_path_fails_scope(tmp_path: Path) -> None:
    """An extra changed file produces unsafe mutation evidence."""

    paths, project_root, source_root, source_digest = _prepared_project(tmp_path=tmp_path)
    (project_root / "pyproject.toml").write_text("changed\n", encoding="utf-8")

    evidence = finalize_project_evidence(
        project_root=project_root,
        source_root=source_root,
        source_sha256_before=source_digest,
        procedure_id="st-01",
        allowed_paths=(),
        output_dir=paths.attempt_root(cell_id="codex:st-05", attempt_number=1) / "engineering",
    )

    assert evidence.status == "fail"
    assert evidence.verdict_code == "unsafe_mutation_scope"
    assert evidence.changed_paths == ("pyproject.toml",)


def _create_repo_local_plan(tmp_path: Path):
    """Create a plan beneath a hermetic temporary repository."""

    repo_root = tmp_path / "repo"
    for relative in (
        Path("scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json"),
        Path(
            "context/features/2026-07-11-tui-state-tracking-test-plan/usecases/"
            "uc-02-pressure-test-long-horizon-tui-state-tracking.md"
        ),
    ):
        destination = repo_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_REPO_ROOT / relative, destination)
    return create_or_resume_plan(
        repo_root=repo_root,
        requested_run_root=Path("tmp/run"),
        selected_cells=("codex:st-05",),
    )


def _prepared_project(tmp_path: Path):
    """Return one real prepared project and its immutable source evidence."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)
    source_root = (_REPO_ROOT / suite.fixture.path).resolve()
    paths, _ = _create_repo_local_plan(tmp_path=tmp_path)
    create_attempt(paths=paths, cell_id="codex:st-05")
    manifest = prepare_boltons_project(
        repo_root=_REPO_ROOT,
        paths=paths,
        fixture=suite.fixture,
        cell_id="codex:st-05",
        attempt_number=1,
        python_executable=Path(sys.executable),
    )
    return paths, Path(manifest.copied_project_path), source_root, manifest.source_sha256
