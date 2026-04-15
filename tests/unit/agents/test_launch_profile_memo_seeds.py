from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.agent_workspace import resolve_agent_memory
from houmao.agents.launch_profile_memo_seeds import (
    LaunchProfileMemoSeedError,
    apply_launch_profile_memo_seed,
)
from houmao.project.catalog import ManagedContentRef
from houmao.project.launch_profiles import ResolvedLaunchProfileMemoSeed


def _resolved_memo_seed(*, source_kind: str, policy: str, source_path: Path) -> ResolvedLaunchProfileMemoSeed:
    return ResolvedLaunchProfileMemoSeed(
        source_kind=source_kind,
        policy=policy,
        content_ref=ManagedContentRef(
            content_kind="memo_seed",
            storage_kind="tree" if source_kind == "tree" else "file",
            relative_path="memo-seeds/tests/seed",
        ),
        source_path=source_path.resolve(),
    )


def test_apply_launch_profile_memo_seed_initializes_empty_memory_tree(tmp_path: Path) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path, agent_id="agent-1")
    seed_root = (tmp_path / "seed").resolve()
    (seed_root / "pages" / "checklists").mkdir(parents=True, exist_ok=True)
    (seed_root / "pages" / "empty").mkdir(parents=True, exist_ok=True)
    (seed_root / "houmao-memo.md").write_text("Read the checklist first.\n", encoding="utf-8")
    (seed_root / "pages" / "checklists" / "launch.md").write_text(
        "Confirm repo cleanliness.\n",
        encoding="utf-8",
    )

    result = apply_launch_profile_memo_seed(
        paths=paths,
        memo_seed=_resolved_memo_seed(
            source_kind="tree",
            policy="initialize",
            source_path=seed_root,
        ),
    )

    assert result.to_payload() == {
        "status": "applied",
        "source_kind": "tree",
        "policy": "initialize",
        "memo_written": True,
        "page_file_count": 1,
        "page_directory_count": 2,
    }
    assert paths.memo_file.read_text(encoding="utf-8") == "Read the checklist first.\n"
    assert (paths.pages_dir / "checklists" / "launch.md").read_text(encoding="utf-8") == (
        "Confirm repo cleanliness.\n"
    )
    assert (paths.pages_dir / "empty").is_dir()


def test_apply_launch_profile_memo_seed_initialize_skips_when_memory_is_nonempty(
    tmp_path: Path,
) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path, agent_id="agent-1")
    paths.memo_file.parent.mkdir(parents=True, exist_ok=True)
    paths.memo_file.write_text("Existing memo.\n", encoding="utf-8")
    seed_path = (tmp_path / "seed.md").resolve()
    seed_path.write_text("New memo.\n", encoding="utf-8")

    result = apply_launch_profile_memo_seed(
        paths=paths,
        memo_seed=_resolved_memo_seed(
            source_kind="memo",
            policy="initialize",
            source_path=seed_path,
        ),
    )

    assert result.to_payload() == {
        "status": "skipped",
        "source_kind": "memo",
        "policy": "initialize",
        "memo_written": False,
        "page_file_count": 0,
        "page_directory_count": 0,
        "reason": "existing memo state present",
    }
    assert paths.memo_file.read_text(encoding="utf-8") == "Existing memo.\n"


def test_apply_launch_profile_memo_seed_replace_rewrites_memo_and_pages(tmp_path: Path) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path, agent_id="agent-1")
    paths.memo_file.parent.mkdir(parents=True, exist_ok=True)
    paths.memo_file.write_text("Existing memo.\n", encoding="utf-8")
    (paths.pages_dir / "old.md").parent.mkdir(parents=True, exist_ok=True)
    (paths.pages_dir / "old.md").write_text("Old page.\n", encoding="utf-8")
    seed_root = (tmp_path / "seed").resolve()
    (seed_root / "pages" / "new.md").parent.mkdir(parents=True, exist_ok=True)
    (seed_root / "pages" / "new.md").write_text("New page.\n", encoding="utf-8")

    result = apply_launch_profile_memo_seed(
        paths=paths,
        memo_seed=_resolved_memo_seed(
            source_kind="tree",
            policy="replace",
            source_path=seed_root,
        ),
    )

    assert result.to_payload() == {
        "status": "applied",
        "source_kind": "tree",
        "policy": "replace",
        "memo_written": True,
        "page_file_count": 1,
        "page_directory_count": 0,
    }
    assert paths.memo_file.read_text(encoding="utf-8") == ""
    assert not (paths.pages_dir / "old.md").exists()
    assert (paths.pages_dir / "new.md").read_text(encoding="utf-8") == "New page.\n"


def test_apply_launch_profile_memo_seed_fail_if_nonempty_aborts_without_mutation(
    tmp_path: Path,
) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path, agent_id="agent-1")
    (paths.pages_dir / "existing.md").parent.mkdir(parents=True, exist_ok=True)
    (paths.pages_dir / "existing.md").write_text("Existing page.\n", encoding="utf-8")
    seed_path = (tmp_path / "seed.md").resolve()
    seed_path.write_text("New memo.\n", encoding="utf-8")

    with pytest.raises(
        LaunchProfileMemoSeedError,
        match="policy `fail-if-nonempty` aborted launch because existing memo state is present",
    ):
        apply_launch_profile_memo_seed(
            paths=paths,
            memo_seed=_resolved_memo_seed(
                source_kind="memo",
                policy="fail-if-nonempty",
                source_path=seed_path,
            ),
        )

    assert not paths.memo_file.exists()
    assert (paths.pages_dir / "existing.md").read_text(encoding="utf-8") == "Existing page.\n"
