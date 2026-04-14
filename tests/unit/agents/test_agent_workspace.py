from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.agent_workspace import (
    clear_workspace_lane,
    contained_lane_path,
    delete_workspace_path,
    ensure_agent_workspace,
    list_workspace_tree,
    read_memo,
    read_workspace_file,
    resolve_agent_workspace,
    write_memo,
    write_workspace_file,
)


def test_auto_workspace_creates_memo_scratch_and_persist_without_overwriting_memo(
    tmp_path: Path,
) -> None:
    overlay_root = tmp_path / ".houmao"
    paths = resolve_agent_workspace(
        overlay_root=overlay_root,
        agent_id="agent-123",
        explicit_persist_dir=None,
        disable_persist_dir=False,
    )
    paths.memo_file.parent.mkdir(parents=True, exist_ok=True)
    paths.memo_file.write_text("keep me\n", encoding="utf-8")

    ensure_agent_workspace(paths)

    assert paths.workspace_root == (overlay_root / "memory" / "agents" / "agent-123").resolve()
    assert paths.memo_file == (paths.workspace_root / "houmao-memo.md").resolve()
    assert paths.scratch_dir == (paths.workspace_root / "scratch").resolve()
    assert paths.persist_binding == "auto"
    assert paths.persist_dir == (paths.workspace_root / "persist").resolve()
    assert paths.scratch_dir.is_dir()
    assert paths.persist_dir.is_dir()
    assert read_memo(paths) == "keep me\n"


def test_exact_and_disabled_persist_binding_behaviors(tmp_path: Path) -> None:
    exact_dir = (tmp_path / "shared-persist").resolve()
    exact = resolve_agent_workspace(
        overlay_root=tmp_path / ".houmao",
        agent_id="agent-123",
        explicit_persist_dir=exact_dir,
        disable_persist_dir=False,
    )
    ensure_agent_workspace(exact)

    assert exact.persist_binding == "exact"
    assert exact.persist_dir == exact_dir
    assert exact_dir.is_dir()

    disabled = resolve_agent_workspace(
        overlay_root=tmp_path / ".houmao",
        agent_id="agent-456",
        explicit_persist_dir=None,
        disable_persist_dir=True,
    )
    ensure_agent_workspace(disabled)

    assert disabled.persist_binding == "disabled"
    assert disabled.persist_dir is None
    assert disabled.scratch_dir.is_dir()
    with pytest.raises(ValueError, match="persist lane is disabled"):
        list_workspace_tree(disabled, lane="persist")


def test_lane_operations_round_trip_and_clear_preserves_lane_root(tmp_path: Path) -> None:
    paths = resolve_agent_workspace(
        overlay_root=tmp_path / ".houmao",
        agent_id="agent-123",
        explicit_persist_dir=None,
        disable_persist_dir=False,
    )
    ensure_agent_workspace(paths)

    write_workspace_file(paths, lane="scratch", relative_path="notes/todo.txt", content="one")
    write_workspace_file(
        paths,
        lane="scratch",
        relative_path="notes/todo.txt",
        content="\ntwo",
        append=True,
    )
    write_memo(paths, "memo")
    write_memo(paths, "\nappend", append=True)

    assert read_workspace_file(paths, lane="scratch", relative_path="notes/todo.txt") == "one\ntwo"
    assert read_memo(paths) == "memo\nappend"
    assert [entry.path for entry in list_workspace_tree(paths, lane="scratch")] == [
        "notes",
        "notes/todo.txt",
    ]

    delete_workspace_path(paths, lane="scratch", relative_path="notes/todo.txt")
    assert not (paths.scratch_dir / "notes" / "todo.txt").exists()

    write_workspace_file(paths, lane="scratch", relative_path="tmp/file.txt", content="x")
    clear_workspace_lane(paths, lane="scratch")
    assert paths.scratch_dir.is_dir()
    assert list(paths.scratch_dir.iterdir()) == []


def test_lane_paths_reject_absolute_and_traversal(tmp_path: Path) -> None:
    paths = resolve_agent_workspace(
        overlay_root=tmp_path / ".houmao",
        agent_id="agent-123",
        explicit_persist_dir=None,
        disable_persist_dir=False,
    )
    ensure_agent_workspace(paths)

    with pytest.raises(ValueError, match="relative"):
        contained_lane_path(paths, lane="scratch", relative_path="/tmp/outside")
    with pytest.raises(ValueError, match="relative"):
        contained_lane_path(paths, lane="scratch", relative_path="../outside")


def test_lane_operations_reject_symlink_escape_attempts(tmp_path: Path) -> None:
    paths = resolve_agent_workspace(
        overlay_root=tmp_path / ".houmao",
        agent_id="agent-123",
        explicit_persist_dir=None,
        disable_persist_dir=False,
    )
    ensure_agent_workspace(paths)
    outside_dir = (tmp_path / "outside").resolve()
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")
    (paths.scratch_dir / "escape-file").symlink_to(outside_file)
    (paths.scratch_dir / "escape-dir").symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(ValueError, match="outside the selected lane"):
        read_workspace_file(paths, lane="scratch", relative_path="escape-file")
    with pytest.raises(ValueError, match="outside the selected lane"):
        write_workspace_file(
            paths,
            lane="scratch",
            relative_path="escape-dir/new.txt",
            content="nope",
        )
    with pytest.raises(ValueError, match="outside the selected lane"):
        list_workspace_tree(paths, lane="scratch")
