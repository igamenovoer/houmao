"""Managed-agent memory-directory binding helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

HOUMAO_MEMORY_DIR_ENV_VAR = "HOUMAO_MEMORY_DIR"
ResolvedMemoryBindingKind = Literal["auto", "exact", "disabled"]
StoredMemoryBindingKind = Literal["inherit", "exact", "disabled"]

_MEMORY_DIRNAME = "memory"
_AGENTS_DIRNAME = "agents"


@dataclass(frozen=True)
class StoredMemoryBinding:
    """Stored launch-profile memory binding intent."""

    kind: StoredMemoryBindingKind
    directory: Path | None = None

    def __post_init__(self) -> None:
        """Validate one stored memory binding."""

        if self.kind == "exact":
            if self.directory is None:
                raise ValueError("Stored exact memory binding requires a directory.")
            return
        if self.directory is not None:
            raise ValueError("Non-exact stored memory binding must not include a directory.")


@dataclass(frozen=True)
class ResolvedMemoryBinding:
    """Resolved runtime memory binding for one managed session."""

    kind: ResolvedMemoryBindingKind
    directory: Path | None = None

    def __post_init__(self) -> None:
        """Validate one resolved runtime binding."""

        if self.kind in {"auto", "exact"}:
            if self.directory is None:
                raise ValueError("Enabled memory binding requires a directory.")
            return
        if self.directory is not None:
            raise ValueError("Disabled memory binding must not include a directory.")


def normalize_memory_dir_path(value: str | Path) -> Path:
    """Resolve one memory-directory path to an absolute path."""

    return Path(value).expanduser().resolve()


def stored_memory_binding_kind(
    *,
    memory_dir: str | Path | None,
    memory_disabled: bool,
) -> StoredMemoryBindingKind:
    """Return the stored launch-profile memory intent kind."""

    return resolve_stored_memory_binding(
        memory_dir=memory_dir,
        memory_disabled=memory_disabled,
    ).kind


def resolve_stored_memory_binding(
    *,
    memory_dir: str | Path | None,
    memory_disabled: bool,
) -> StoredMemoryBinding:
    """Resolve one launch-profile memory configuration into a typed binding."""

    if memory_disabled:
        if memory_dir is not None:
            raise ValueError("Stored memory_dir and disabled memory binding cannot both be set.")
        return StoredMemoryBinding(kind="disabled")
    if memory_dir is not None:
        return StoredMemoryBinding(kind="exact", directory=normalize_memory_dir_path(memory_dir))
    return StoredMemoryBinding(kind="inherit")


def default_memory_dir_for_agent(*, overlay_root: Path, agent_id: str) -> Path:
    """Return the conservative default memory directory for one agent id."""

    return (overlay_root.resolve() / _MEMORY_DIRNAME / _AGENTS_DIRNAME / agent_id).resolve()


def resolve_effective_memory_binding(
    *,
    overlay_root: Path,
    agent_id: str,
    explicit_memory_dir: str | Path | None,
    disable_memory_dir: bool,
    stored_memory_dir: str | Path | None = None,
    stored_memory_disabled: bool = False,
) -> ResolvedMemoryBinding:
    """Resolve the effective runtime memory binding for one managed session."""

    if explicit_memory_dir is not None and disable_memory_dir:
        raise ValueError("`--memory-dir` and `--no-memory-dir` are mutually exclusive.")
    if explicit_memory_dir is not None:
        return ResolvedMemoryBinding(
            kind="exact",
            directory=normalize_memory_dir_path(explicit_memory_dir),
        )
    if disable_memory_dir:
        return ResolvedMemoryBinding(kind="disabled")

    stored = resolve_stored_memory_binding(
        memory_dir=stored_memory_dir,
        memory_disabled=stored_memory_disabled,
    )
    if stored.kind == "exact":
        return ResolvedMemoryBinding(kind="exact", directory=stored.directory)
    if stored.kind == "disabled":
        return ResolvedMemoryBinding(kind="disabled")
    return ResolvedMemoryBinding(
        kind="auto",
        directory=default_memory_dir_for_agent(
            overlay_root=overlay_root,
            agent_id=agent_id,
        ),
    )


def ensure_memory_dir(binding: ResolvedMemoryBinding) -> None:
    """Create one enabled memory directory when it does not yet exist."""

    if binding.directory is None:
        return
    binding.directory.mkdir(parents=True, exist_ok=True)
