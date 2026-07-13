"""Tests for owned run paths and resumable numbered attempts."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.attempts import (
    create_attempt,
    load_attempt_state,
    select_attempt_for_aggregate,
    transition_attempt,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    initialize_owned_run_root,
    require_owned_descendant,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.orchestrator import cleanup_suite
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.planner import (
    create_or_resume_plan,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]


def test_run_root_must_be_proper_tmp_descendant(tmp_path: Path) -> None:
    """Path resolution rejects the tmp root and every outside path."""

    repo = tmp_path / "repo"
    (repo / "tmp").mkdir(parents=True)

    with pytest.raises(ValueError, match="proper descendant"):
        LongHorizonRunPaths.from_requested_root(repo_root=repo, requested_root=Path("tmp"))
    with pytest.raises(ValueError, match="proper descendant"):
        LongHorizonRunPaths.from_requested_root(
            repo_root=repo,
            requested_root=Path("../outside"),
        )


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    """A requested output symlink cannot redirect writes outside repo tmp."""

    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "tmp").mkdir(parents=True)
    (repo / "tmp" / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="proper descendant"):
        LongHorizonRunPaths.from_requested_root(
            repo_root=repo,
            requested_root=Path("tmp/escape/run"),
        )


def test_nonempty_unowned_root_is_rejected(tmp_path: Path) -> None:
    """Existing non-empty directories require matching ownership metadata."""

    repo = tmp_path / "repo"
    run = repo / "tmp" / "run"
    run.mkdir(parents=True)
    (run / "foreign.txt").write_text("foreign", encoding="utf-8")
    paths = LongHorizonRunPaths.from_requested_root(repo_root=repo, requested_root=run)

    with pytest.raises(ValueError, match="non-empty unowned"):
        initialize_owned_run_root(paths=paths, suite_id="suite")


def test_plan_resume_and_attempt_lifecycle(tmp_path: Path) -> None:
    """Planning is idempotent while attempts remain numbered and immutable."""

    repo = _seed_catalog_repo(tmp_path / "repo")
    paths, plan = create_or_resume_plan(
        repo_root=repo,
        requested_run_root=Path("tmp/run"),
        selected_cells=("codex:st-05",),
    )
    resumed_paths, resumed_plan = create_or_resume_plan(
        repo_root=repo,
        requested_run_root=Path("tmp/run"),
        selected_cells=("codex:st-05",),
    )

    assert resumed_paths == paths
    assert resumed_plan == plan
    first_root, first = create_attempt(paths=paths, cell_id="codex:st-05")
    second_root, second = create_attempt(paths=paths, cell_id="codex:st-05")
    assert first.attempt_id == "a001"
    assert second.attempt_id == "a002"
    assert first_root.is_dir() and second_root.is_dir()

    transition_attempt(
        attempt_root=first_root,
        expected_phase="planned",
        new_phase="preflight_passed",
        input_digests={"catalog": "abc"},
    )
    transition_attempt(
        attempt_root=first_root,
        expected_phase="preflight_passed",
        new_phase="capturing",
    )
    transition_attempt(
        attempt_root=first_root,
        expected_phase="capturing",
        new_phase="awaiting_manual_labels",
    )
    transition_attempt(
        attempt_root=first_root,
        expected_phase="awaiting_manual_labels",
        new_phase="labels_complete",
    )
    transition_attempt(
        attempt_root=first_root,
        expected_phase="labels_complete",
        new_phase="replaying",
    )
    transition_attempt(
        attempt_root=first_root,
        expected_phase="replaying",
        new_phase="reported",
    )
    selected = select_attempt_for_aggregate(
        paths=paths,
        cell_id="codex:st-05",
        attempt_root=first_root,
    )

    assert selected.selected_for_aggregate is True
    assert load_attempt_state(attempt_root=first_root).input_digests == {"catalog": "abc"}
    assert load_attempt_state(attempt_root=second_root).phase == "planned"
    with pytest.raises(ValueError, match="Invalid attempt transition"):
        transition_attempt(
            attempt_root=first_root,
            expected_phase="reported",
            new_phase="capturing",
        )


def test_cleanup_target_requires_ownership(tmp_path: Path) -> None:
    """Owned descendants pass while outside cleanup targets fail."""

    repo = tmp_path / "repo"
    paths = LongHorizonRunPaths.from_requested_root(
        repo_root=repo,
        requested_root=Path("tmp/run"),
    )
    initialize_owned_run_root(paths=paths, suite_id="suite")

    assert require_owned_descendant(paths=paths, target=paths.aggregate_dir) == (
        paths.aggregate_dir.resolve()
    )
    with pytest.raises(ValueError, match="escapes owned run root"):
        require_owned_descendant(paths=paths, target=tmp_path / "outside")


def test_long_horizon_cleanup_removes_only_sensitive_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owned cleanup reaps sessions and retains recording evidence."""

    repo = _seed_catalog_repo(tmp_path / "repo")
    paths, _plan = create_or_resume_plan(
        repo_root=repo,
        requested_run_root=Path("tmp/run"),
    )
    attempt_root, _state = create_attempt(paths=paths, cell_id="codex:st-01")
    provider_home = paths.provider_homes_dir / "codex-st-01-a001" / "homes" / "brain"
    provider_home.mkdir(parents=True)
    (provider_home / "auth.json").write_text("secret", encoding="utf-8")
    definition_workdir = attempt_root / "runtime" / "definition-workdir"
    definition_workdir.mkdir()
    (definition_workdir / "secret").write_text("secret", encoding="utf-8")
    (attempt_root / "runtime" / "owned-resources.json").write_text(
        '{"tmux_session_name":"shared-tui-codex-owned"}\n',
        encoding="utf-8",
    )
    recording_root = attempt_root / "recording" / "terminal-record"
    recording_root.mkdir()
    (recording_root / "manifest.json").write_text(
        '{"recorder_session_name":"HMREC-owned"}\n',
        encoding="utf-8",
    )
    (recording_root / "session.cast").write_text("evidence", encoding="utf-8")
    killed: list[str] = []
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.long_horizon.orchestrator."
        "kill_tmux_session_if_exists",
        lambda *, session_name: killed.append(session_name),
    )

    result = cleanup_suite(repo_root=repo, run_root=paths.run_root)

    assert result["provider_homes_removed"] is True
    assert result["definition_workdirs_removed"] == 1
    assert killed == ["shared-tui-codex-owned", "HMREC-owned"]
    assert not paths.provider_homes_dir.exists()
    assert not definition_workdir.exists()
    assert (recording_root / "session.cast").read_text(encoding="utf-8") == "evidence"


def _seed_catalog_repo(repo: Path) -> Path:
    """Copy the reviewed catalog and source document into a temporary repo."""

    catalog_relative = Path("scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json")
    source_relative = Path(
        "context/features/2026-07-11-tui-state-tracking-test-plan/usecases/"
        "uc-02-pressure-test-long-horizon-tui-state-tracking.md"
    )
    for relative in (catalog_relative, source_relative):
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_REPO_ROOT / relative, destination)
    return repo
