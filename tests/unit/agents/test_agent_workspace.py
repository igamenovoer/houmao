from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.agent_workspace import (
    contained_page_path,
    delete_memory_page,
    ensure_agent_memory,
    list_memory_pages,
    read_memo,
    read_memory_page,
    resolve_agent_memory,
    resolve_memory_page_path,
    write_memo,
    write_memory_page,
)


def test_memory_creates_memo_and_pages_without_overwriting_memo(tmp_path: Path) -> None:
    overlay_root = tmp_path / ".houmao"
    paths = resolve_agent_memory(overlay_root=overlay_root, agent_id="agent-123")
    paths.memo_file.parent.mkdir(parents=True, exist_ok=True)
    paths.memo_file.write_text("keep me\n", encoding="utf-8")

    ensure_agent_memory(paths)

    assert paths.memory_root == (overlay_root / "memory" / "agents" / "agent-123").resolve()
    assert paths.memo_file == (paths.memory_root / "houmao-memo.md").resolve()
    assert paths.pages_dir == (paths.memory_root / "pages").resolve()
    assert paths.pages_dir.is_dir()
    assert read_memo(paths) == "keep me\n"


def test_page_operations_round_trip_without_mutating_memo(tmp_path: Path) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path / ".houmao", agent_id="agent-123")
    ensure_agent_memory(paths)
    write_memo(paths, "# Memo\nKeep this authored text.\n")

    write_memory_page(paths, relative_path="notes/todo.txt", content="one")
    write_memory_page(paths, relative_path="notes/todo.txt", content="\ntwo", append=True)

    assert read_memory_page(paths, relative_path="notes/todo.txt") == "one\ntwo"
    entries = list_memory_pages(paths)
    assert [entry.path for entry in entries] == ["notes", "notes/todo.txt"]
    assert entries[1].relative_link == "pages/notes/todo.txt"
    assert entries[1].absolute_path == (paths.pages_dir / "notes" / "todo.txt").resolve()
    assert read_memo(paths) == "# Memo\nKeep this authored text.\n"

    delete_memory_page(paths, relative_path="notes/todo.txt")
    assert not (paths.pages_dir / "notes" / "todo.txt").exists()
    assert read_memo(paths) == "# Memo\nKeep this authored text.\n"


def test_page_path_resolution_reports_contained_metadata(tmp_path: Path) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path / ".houmao", agent_id="agent-123")
    ensure_agent_memory(paths)
    write_memory_page(paths, relative_path="notes/todo.txt", content="one")

    existing = resolve_memory_page_path(paths, relative_path="notes/todo.txt")
    assert existing.path == "notes/todo.txt"
    assert existing.relative_link == "pages/notes/todo.txt"
    assert existing.absolute_path == (paths.pages_dir / "notes" / "todo.txt").resolve()
    assert existing.exists is True
    assert existing.kind == "file"
    assert existing.size_bytes == 3

    missing = resolve_memory_page_path(paths, relative_path="notes/later.md")
    assert missing.path == "notes/later.md"
    assert missing.relative_link == "pages/notes/later.md"
    assert missing.absolute_path == (paths.pages_dir / "notes" / "later.md").resolve()
    assert missing.exists is False
    assert missing.kind is None


def test_page_paths_reject_absolute_and_traversal(tmp_path: Path) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path / ".houmao", agent_id="agent-123")
    ensure_agent_memory(paths)

    with pytest.raises(ValueError, match="relative"):
        contained_page_path(paths, relative_path="/tmp/outside")
    with pytest.raises(ValueError, match="relative"):
        contained_page_path(paths, relative_path="../outside")
    with pytest.raises(ValueError, match="relative"):
        resolve_memory_page_path(paths, relative_path="../outside")


def test_page_operations_reject_symlink_escape_attempts(tmp_path: Path) -> None:
    paths = resolve_agent_memory(overlay_root=tmp_path / ".houmao", agent_id="agent-123")
    ensure_agent_memory(paths)
    outside_dir = (tmp_path / "outside").resolve()
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")
    (paths.pages_dir / "escape-file").symlink_to(outside_file)
    (paths.pages_dir / "escape-dir").symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(ValueError, match="outside pages"):
        read_memory_page(paths, relative_path="escape-file")
    with pytest.raises(ValueError, match="outside pages"):
        write_memory_page(paths, relative_path="escape-dir/new.txt", content="nope")
    with pytest.raises(ValueError, match="outside pages"):
        list_memory_pages(paths)
