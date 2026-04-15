"""Managed-agent memo-pages memory helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

HOUMAO_AGENT_MEMORY_DIR_ENV_VAR = "HOUMAO_AGENT_MEMORY_DIR"
HOUMAO_AGENT_MEMO_FILE_ENV_VAR = "HOUMAO_AGENT_MEMO_FILE"
HOUMAO_AGENT_PAGES_DIR_ENV_VAR = "HOUMAO_AGENT_PAGES_DIR"

_MEMORY_DIRNAME = "memory"
_AGENTS_DIRNAME = "agents"
_PAGES_DIRNAME = "pages"
_MEMO_FILENAME = "houmao-memo.md"


@dataclass(frozen=True)
class AgentMemoryPaths:
    """Resolved memo-pages memory paths for one managed agent."""

    memory_root: Path
    memo_file: Path
    pages_dir: Path


@dataclass(frozen=True)
class MemoryPageEntry:
    """One contained memory page entry."""

    path: str
    relative_link: str
    absolute_path: Path
    kind: Literal["file", "directory", "symlink", "other"]
    size_bytes: int | None = None


@dataclass(frozen=True)
class MemoryPagePathResolution:
    """One contained memory page path resolution."""

    path: str
    relative_link: str
    absolute_path: Path
    exists: bool
    kind: Literal["file", "directory", "symlink", "other"] | None = None
    size_bytes: int | None = None


def default_memory_root_for_agent(*, overlay_root: Path, agent_id: str) -> Path:
    """Return the default memory root for one managed agent id."""

    return (overlay_root.resolve() / _MEMORY_DIRNAME / _AGENTS_DIRNAME / agent_id).resolve()


def resolve_agent_memory(
    *,
    overlay_root: Path,
    agent_id: str,
    memory_root: Path | None = None,
    memo_file: Path | None = None,
    pages_dir: Path | None = None,
) -> AgentMemoryPaths:
    """Resolve a managed-agent memory root, memo file, and pages directory."""

    resolved_memory_root = (
        memory_root.resolve()
        if memory_root is not None
        else default_memory_root_for_agent(overlay_root=overlay_root, agent_id=agent_id)
    )
    resolved_memo_file = (
        memo_file.resolve() if memo_file is not None else resolved_memory_root / _MEMO_FILENAME
    )
    resolved_pages_dir = (
        pages_dir.resolve() if pages_dir is not None else resolved_memory_root / _PAGES_DIRNAME
    )
    return AgentMemoryPaths(
        memory_root=resolved_memory_root.resolve(),
        memo_file=resolved_memo_file.resolve(),
        pages_dir=resolved_pages_dir.resolve(),
    )


def ensure_agent_memory(paths: AgentMemoryPaths) -> None:
    """Create the memory root, fixed memo file, and pages directory."""

    paths.memory_root.mkdir(parents=True, exist_ok=True)
    paths.memo_file.parent.mkdir(parents=True, exist_ok=True)
    paths.memo_file.touch(exist_ok=True)
    paths.pages_dir.mkdir(parents=True, exist_ok=True)


def memory_env(paths: AgentMemoryPaths) -> dict[str, str]:
    """Return live-session environment values for one resolved memory root."""

    return {
        HOUMAO_AGENT_MEMORY_DIR_ENV_VAR: str(paths.memory_root.resolve()),
        HOUMAO_AGENT_MEMO_FILE_ENV_VAR: str(paths.memo_file.resolve()),
        HOUMAO_AGENT_PAGES_DIR_ENV_VAR: str(paths.pages_dir.resolve()),
    }


def memory_env_var_names(paths: AgentMemoryPaths) -> list[str]:
    """Return live-session environment variable names for one resolved memory root."""

    return sorted(memory_env(paths))


def contained_page_path(paths: AgentMemoryPaths, *, relative_path: str) -> Path:
    """Resolve a page-relative path and verify it stays inside the pages directory."""

    normalized = relative_path.strip()
    if not normalized:
        raise ValueError("Memory page path must not be empty.")
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Memory page paths must be relative and stay within pages/.")
    root = paths.pages_dir.resolve()
    target = (root / candidate).resolve(strict=False)
    if not _path_is_within(target, root):
        raise ValueError("Memory page path resolves outside pages/.")
    return target


def resolve_memory_page_path(
    paths: AgentMemoryPaths,
    *,
    relative_path: str,
) -> MemoryPagePathResolution:
    """Resolve contained page path metadata without requiring the page to exist."""

    target = contained_page_path(paths, relative_path=relative_path)
    _require_parent_within_pages(paths, target=target)
    normalized_path = _normalized_relative_page_path(paths, target=target)
    kind = _memory_page_kind(target) if target.exists() or target.is_symlink() else None
    stat = target.stat() if target.exists() and not target.is_dir() else None
    return MemoryPagePathResolution(
        path=normalized_path,
        relative_link=f"{_PAGES_DIRNAME}/{normalized_path}",
        absolute_path=target,
        exists=target.exists() or target.is_symlink(),
        kind=kind,
        size_bytes=stat.st_size if stat is not None else None,
    )


def list_memory_pages(
    paths: AgentMemoryPaths,
    *,
    relative_path: str = ".",
) -> list[MemoryPageEntry]:
    """List contained memory page entries under one pages-relative path."""

    root = paths.pages_dir.resolve()
    start = (
        root
        if relative_path in {"", "."}
        else contained_page_path(paths, relative_path=relative_path)
    )
    _require_path_within_pages(paths, target=start)
    if not start.exists():
        raise FileNotFoundError(f"Memory page path not found: {relative_path}")
    candidates = [start] if start.is_file() or start.is_symlink() else sorted(start.rglob("*"))
    entries: list[MemoryPageEntry] = []
    for candidate in candidates:
        _require_path_within_pages(paths, target=candidate)
        relative = _normalized_relative_page_path(paths, target=candidate)
        stat = candidate.stat() if candidate.exists() and not candidate.is_dir() else None
        entries.append(
            MemoryPageEntry(
                path=relative,
                relative_link=f"{_PAGES_DIRNAME}/{relative}",
                absolute_path=candidate.resolve(strict=False),
                kind=_memory_page_kind(candidate),
                size_bytes=stat.st_size if stat is not None else None,
            )
        )
    return entries


def read_memory_page(paths: AgentMemoryPaths, *, relative_path: str) -> str:
    """Read one contained memory page file."""

    target = contained_page_path(paths, relative_path=relative_path)
    if not target.is_file():
        raise FileNotFoundError(f"Memory page not found: {relative_path}")
    _require_path_within_pages(paths, target=target)
    return target.read_text(encoding="utf-8")


def write_memory_page(
    paths: AgentMemoryPaths,
    *,
    relative_path: str,
    content: str,
    append: bool = False,
) -> None:
    """Write or append text to one contained memory page file."""

    _require_text_content(content)
    target = contained_page_path(paths, relative_path=relative_path)
    _require_parent_within_pages(paths, target=target)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with target.open(mode, encoding="utf-8") as handle:
        handle.write(content)


def delete_memory_page(paths: AgentMemoryPaths, *, relative_path: str) -> None:
    """Delete one contained memory page file or directory."""

    target = contained_page_path(paths, relative_path=relative_path)
    _require_path_within_pages(paths, target=target)
    if target.is_dir() and not target.is_symlink():
        for child in sorted(target.rglob("*"), reverse=True):
            _require_path_within_pages(paths, target=child)
            if child.is_dir() and not child.is_symlink():
                child.rmdir()
            else:
                child.unlink(missing_ok=True)
        target.rmdir()
    else:
        target.unlink(missing_ok=True)


def read_memo(paths: AgentMemoryPaths) -> str:
    """Read the fixed memory memo file."""

    if not paths.memo_file.is_file():
        return ""
    return paths.memo_file.read_text(encoding="utf-8")


def write_memo(paths: AgentMemoryPaths, content: str, *, append: bool = False) -> None:
    """Write or append the fixed memory memo file."""

    _require_text_content(content)
    paths.memo_file.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with paths.memo_file.open(mode, encoding="utf-8") as handle:
        handle.write(content)


def _path_is_within(path: Path, root: Path) -> bool:
    """Return whether path is equal to or below root."""

    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _normalized_relative_page_path(paths: AgentMemoryPaths, *, target: Path) -> str:
    """Return one pages-relative path string for a contained target."""

    root = paths.pages_dir.resolve()
    return target.resolve(strict=False).relative_to(root).as_posix()


def _memory_page_kind(target: Path) -> Literal["file", "directory", "symlink", "other"]:
    """Return one memory page path kind."""

    if target.is_symlink():
        return "symlink"
    if target.is_dir():
        return "directory"
    if target.is_file():
        return "file"
    return "other"


def _require_path_within_pages(paths: AgentMemoryPaths, *, target: Path) -> None:
    """Require one existing path to stay inside pages after symlink resolution."""

    root = paths.pages_dir.resolve()
    resolved_target = target.resolve(strict=True)
    if not _path_is_within(resolved_target, root):
        raise ValueError("Memory page path resolves outside pages/.")


def _require_parent_within_pages(paths: AgentMemoryPaths, *, target: Path) -> None:
    """Require one target parent to stay inside pages after symlink resolution."""

    root = paths.pages_dir.resolve()
    existing_parent = target.parent
    while not existing_parent.exists() and existing_parent != root:
        existing_parent = existing_parent.parent
    resolved_parent = existing_parent.resolve(strict=True)
    if not _path_is_within(resolved_parent, root):
        raise ValueError("Memory page path resolves outside pages/.")


def _require_text_content(content: str) -> None:
    """Reject unsupported text content for memo and page writes."""

    if "\x00" in content:
        raise ValueError("Memory content must not contain NUL bytes.")
