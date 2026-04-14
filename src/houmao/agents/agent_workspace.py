"""Managed-agent workspace path and file-operation helpers."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

HOUMAO_AGENT_STATE_DIR_ENV_VAR = "HOUMAO_AGENT_STATE_DIR"
HOUMAO_AGENT_MEMO_FILE_ENV_VAR = "HOUMAO_AGENT_MEMO_FILE"
HOUMAO_AGENT_SCRATCH_DIR_ENV_VAR = "HOUMAO_AGENT_SCRATCH_DIR"
HOUMAO_AGENT_PERSIST_DIR_ENV_VAR = "HOUMAO_AGENT_PERSIST_DIR"

PersistBindingKind = Literal["auto", "exact", "disabled"]
StoredPersistBindingKind = Literal["inherit", "exact", "disabled"]
WorkspaceLane = Literal["scratch", "persist"]

_MEMORY_DIRNAME = "memory"
_AGENTS_DIRNAME = "agents"
_SCRATCH_DIRNAME = "scratch"
_PERSIST_DIRNAME = "persist"
_MEMO_FILENAME = "houmao-memo.md"


@dataclass(frozen=True)
class StoredPersistBinding:
    """Stored launch-profile persist-lane binding intent."""

    kind: StoredPersistBindingKind
    directory: Path | None = None

    def __post_init__(self) -> None:
        """Validate one stored persist binding."""

        if self.kind == "exact":
            if self.directory is None:
                raise ValueError("Stored exact persist binding requires a directory.")
            return
        if self.directory is not None:
            raise ValueError("Non-exact stored persist binding must not include a directory.")


@dataclass(frozen=True)
class ResolvedPersistBinding:
    """Resolved runtime persist-lane binding for one managed session."""

    kind: PersistBindingKind
    directory: Path | None = None

    def __post_init__(self) -> None:
        """Validate one resolved runtime persist binding."""

        if self.kind in {"auto", "exact"}:
            if self.directory is None:
                raise ValueError("Enabled persist binding requires a directory.")
            return
        if self.directory is not None:
            raise ValueError("Disabled persist binding must not include a directory.")


@dataclass(frozen=True)
class AgentWorkspacePaths:
    """Resolved workspace envelope and lane paths for one managed agent."""

    workspace_root: Path
    memo_file: Path
    scratch_dir: Path
    persist_binding: PersistBindingKind
    persist_dir: Path | None = None

    @property
    def persist(self) -> ResolvedPersistBinding:
        """Return the resolved persist binding as a standalone value."""

        return ResolvedPersistBinding(kind=self.persist_binding, directory=self.persist_dir)


@dataclass(frozen=True)
class WorkspaceTreeEntry:
    """One contained workspace tree entry."""

    path: str
    kind: Literal["file", "directory", "symlink", "other"]
    size_bytes: int | None = None


def normalize_persist_dir_path(value: str | Path) -> Path:
    """Resolve one persist-lane path to an absolute path."""

    return Path(value).expanduser().resolve()


def stored_persist_binding_kind(
    *,
    persist_dir: str | Path | None,
    persist_disabled: bool,
) -> StoredPersistBindingKind:
    """Return the stored launch-profile persist intent kind."""

    return resolve_stored_persist_binding(
        persist_dir=persist_dir,
        persist_disabled=persist_disabled,
    ).kind


def resolve_stored_persist_binding(
    *,
    persist_dir: str | Path | None,
    persist_disabled: bool,
) -> StoredPersistBinding:
    """Resolve one launch-profile persist configuration into a typed binding."""

    if persist_disabled:
        if persist_dir is not None:
            raise ValueError("Stored persist_dir and disabled persist binding cannot both be set.")
        return StoredPersistBinding(kind="disabled")
    if persist_dir is not None:
        return StoredPersistBinding(kind="exact", directory=normalize_persist_dir_path(persist_dir))
    return StoredPersistBinding(kind="inherit")


def default_workspace_root_for_agent(*, overlay_root: Path, agent_id: str) -> Path:
    """Return the default workspace root for one managed agent id."""

    return (overlay_root.resolve() / _MEMORY_DIRNAME / _AGENTS_DIRNAME / agent_id).resolve()


def default_persist_dir_for_agent(*, overlay_root: Path, agent_id: str) -> Path:
    """Return the default persist lane for one managed agent id."""

    return (
        default_workspace_root_for_agent(overlay_root=overlay_root, agent_id=agent_id)
        / _PERSIST_DIRNAME
    ).resolve()


def resolve_effective_persist_binding(
    *,
    overlay_root: Path,
    agent_id: str,
    explicit_persist_dir: str | Path | None,
    disable_persist_dir: bool,
    stored_persist_dir: str | Path | None = None,
    stored_persist_disabled: bool = False,
) -> ResolvedPersistBinding:
    """Resolve the effective runtime persist binding for one managed session."""

    if explicit_persist_dir is not None and disable_persist_dir:
        raise ValueError("`--persist-dir` and `--no-persist-dir` are mutually exclusive.")
    if explicit_persist_dir is not None:
        return ResolvedPersistBinding(
            kind="exact",
            directory=normalize_persist_dir_path(explicit_persist_dir),
        )
    if disable_persist_dir:
        return ResolvedPersistBinding(kind="disabled")

    stored = resolve_stored_persist_binding(
        persist_dir=stored_persist_dir,
        persist_disabled=stored_persist_disabled,
    )
    if stored.kind == "exact":
        return ResolvedPersistBinding(kind="exact", directory=stored.directory)
    if stored.kind == "disabled":
        return ResolvedPersistBinding(kind="disabled")
    return ResolvedPersistBinding(
        kind="auto",
        directory=default_persist_dir_for_agent(
            overlay_root=overlay_root,
            agent_id=agent_id,
        ),
    )


def resolve_agent_workspace(
    *,
    overlay_root: Path,
    agent_id: str,
    explicit_persist_dir: str | Path | None,
    disable_persist_dir: bool,
    stored_persist_dir: str | Path | None = None,
    stored_persist_disabled: bool = False,
    workspace_root: Path | None = None,
    memo_file: Path | None = None,
    scratch_dir: Path | None = None,
    persist_binding: ResolvedPersistBinding | None = None,
) -> AgentWorkspacePaths:
    """Resolve a managed-agent workspace root, memo file, scratch lane, and persist lane."""

    resolved_workspace_root = (
        workspace_root.resolve()
        if workspace_root is not None
        else default_workspace_root_for_agent(overlay_root=overlay_root, agent_id=agent_id)
    )
    resolved_memo_file = (
        memo_file.resolve() if memo_file is not None else resolved_workspace_root / _MEMO_FILENAME
    )
    resolved_scratch_dir = (
        scratch_dir.resolve()
        if scratch_dir is not None
        else resolved_workspace_root / _SCRATCH_DIRNAME
    )
    resolved_persist = persist_binding or resolve_effective_persist_binding(
        overlay_root=overlay_root,
        agent_id=agent_id,
        explicit_persist_dir=explicit_persist_dir,
        disable_persist_dir=disable_persist_dir,
        stored_persist_dir=stored_persist_dir,
        stored_persist_disabled=stored_persist_disabled,
    )
    return AgentWorkspacePaths(
        workspace_root=resolved_workspace_root.resolve(),
        memo_file=resolved_memo_file.resolve(),
        scratch_dir=resolved_scratch_dir.resolve(),
        persist_binding=resolved_persist.kind,
        persist_dir=resolved_persist.directory.resolve()
        if resolved_persist.directory is not None
        else None,
    )


def ensure_agent_workspace(paths: AgentWorkspacePaths) -> None:
    """Create the workspace root, memo file, scratch lane, and enabled persist lane."""

    paths.workspace_root.mkdir(parents=True, exist_ok=True)
    paths.scratch_dir.mkdir(parents=True, exist_ok=True)
    paths.memo_file.parent.mkdir(parents=True, exist_ok=True)
    paths.memo_file.touch(exist_ok=True)
    if paths.persist_dir is not None:
        paths.persist_dir.mkdir(parents=True, exist_ok=True)


def workspace_env(paths: AgentWorkspacePaths) -> dict[str, str]:
    """Return live-session environment values for one resolved workspace."""

    env = {
        HOUMAO_AGENT_STATE_DIR_ENV_VAR: str(paths.workspace_root.resolve()),
        HOUMAO_AGENT_MEMO_FILE_ENV_VAR: str(paths.memo_file.resolve()),
        HOUMAO_AGENT_SCRATCH_DIR_ENV_VAR: str(paths.scratch_dir.resolve()),
    }
    if paths.persist_dir is not None:
        env[HOUMAO_AGENT_PERSIST_DIR_ENV_VAR] = str(paths.persist_dir.resolve())
    return env


def workspace_env_var_names(paths: AgentWorkspacePaths) -> list[str]:
    """Return live-session environment variable names for one resolved workspace."""

    return sorted(workspace_env(paths))


def lane_root(paths: AgentWorkspacePaths, lane: str) -> Path:
    """Return a workspace lane root or fail when the lane is unsupported or disabled."""

    if lane == "scratch":
        return paths.scratch_dir.resolve()
    if lane == "persist":
        if paths.persist_dir is None:
            raise ValueError("The persist lane is disabled for this managed agent.")
        return paths.persist_dir.resolve()
    raise ValueError(f"Unsupported workspace lane `{lane}`; expected `scratch` or `persist`.")


def contained_lane_path(paths: AgentWorkspacePaths, *, lane: str, relative_path: str) -> Path:
    """Resolve a lane-relative path and verify it remains inside the selected lane."""

    normalized = relative_path.strip()
    if not normalized:
        raise ValueError("Workspace path must not be empty.")
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Workspace paths must be relative and stay within the selected lane.")
    root = lane_root(paths, lane)
    target = (root / candidate).resolve(strict=False)
    if not _path_is_within(target, root):
        raise ValueError("Workspace path resolves outside the selected lane.")
    return target


def read_workspace_file(paths: AgentWorkspacePaths, *, lane: str, relative_path: str) -> str:
    """Read one contained workspace lane file."""

    target = contained_lane_path(paths, lane=lane, relative_path=relative_path)
    if not target.is_file():
        raise FileNotFoundError(f"Workspace file not found: {relative_path}")
    _require_path_within_resolved_lane(paths, lane=lane, target=target)
    return target.read_text(encoding="utf-8")


def write_workspace_file(
    paths: AgentWorkspacePaths,
    *,
    lane: str,
    relative_path: str,
    content: str,
    append: bool = False,
) -> None:
    """Write or append text to one contained workspace lane file."""

    target = contained_lane_path(paths, lane=lane, relative_path=relative_path)
    _require_parent_within_resolved_lane(paths, lane=lane, target=target)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with target.open(mode, encoding="utf-8") as handle:
        handle.write(content)


def delete_workspace_path(paths: AgentWorkspacePaths, *, lane: str, relative_path: str) -> None:
    """Delete one contained workspace lane file or directory."""

    target = contained_lane_path(paths, lane=lane, relative_path=relative_path)
    _require_path_within_resolved_lane(paths, lane=lane, target=target)
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
        return
    target.unlink(missing_ok=True)


def clear_workspace_lane(paths: AgentWorkspacePaths, *, lane: str) -> None:
    """Clear the contents of one workspace lane while preserving the lane directory."""

    root = lane_root(paths, lane)
    root.mkdir(parents=True, exist_ok=True)
    for child in root.iterdir():
        _require_path_within_resolved_lane(paths, lane=lane, target=child)
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)


def list_workspace_tree(
    paths: AgentWorkspacePaths,
    *,
    lane: str,
    relative_path: str = ".",
) -> list[WorkspaceTreeEntry]:
    """List contained workspace tree entries under one lane path."""

    root = lane_root(paths, lane)
    start = (
        root
        if relative_path in {"", "."}
        else contained_lane_path(
            paths,
            lane=lane,
            relative_path=relative_path,
        )
    )
    _require_path_within_resolved_lane(paths, lane=lane, target=start)
    if not start.exists():
        raise FileNotFoundError(f"Workspace path not found: {relative_path}")
    candidates = [start] if start.is_file() or start.is_symlink() else sorted(start.rglob("*"))
    entries: list[WorkspaceTreeEntry] = []
    for candidate in candidates:
        _require_path_within_resolved_lane(paths, lane=lane, target=candidate)
        relative = candidate.resolve(strict=False).relative_to(root).as_posix()
        stat = candidate.stat() if candidate.exists() and not candidate.is_dir() else None
        if candidate.is_symlink():
            kind: Literal["file", "directory", "symlink", "other"] = "symlink"
        elif candidate.is_dir():
            kind = "directory"
        elif candidate.is_file():
            kind = "file"
        else:
            kind = "other"
        entries.append(
            WorkspaceTreeEntry(
                path=relative,
                kind=kind,
                size_bytes=stat.st_size if stat is not None else None,
            )
        )
    return entries


def read_memo(paths: AgentWorkspacePaths) -> str:
    """Read the fixed workspace memo file."""

    if not paths.memo_file.is_file():
        return ""
    return paths.memo_file.read_text(encoding="utf-8")


def write_memo(paths: AgentWorkspacePaths, content: str, *, append: bool = False) -> None:
    """Write or append the fixed workspace memo file."""

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


def _require_path_within_resolved_lane(
    paths: AgentWorkspacePaths,
    *,
    lane: str,
    target: Path,
) -> None:
    """Require one existing path to stay inside its selected lane after symlink resolution."""

    root = lane_root(paths, lane)
    resolved_target = target.resolve(strict=True)
    if not _path_is_within(resolved_target, root):
        raise ValueError("Workspace path resolves outside the selected lane.")


def _require_parent_within_resolved_lane(
    paths: AgentWorkspacePaths,
    *,
    lane: str,
    target: Path,
) -> None:
    """Require one target parent to stay inside its selected lane after symlink resolution."""

    root = lane_root(paths, lane)
    existing_parent = target.parent
    while not existing_parent.exists() and existing_parent != root:
        existing_parent = existing_parent.parent
    resolved_parent = existing_parent.resolve(strict=True)
    if not _path_is_within(resolved_parent, root):
        raise ValueError("Workspace path resolves outside the selected lane.")
