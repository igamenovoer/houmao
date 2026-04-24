"""Helpers for symlink-safe mutation of Houmao-owned filesystem paths."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Sequence


def lexical_absolute_path(path: Path) -> Path:
    """Return one absolute path without resolving symlink targets."""

    return path.absolute()


def path_is_within_root(*, path: Path, root: Path) -> bool:
    """Return whether one lexical path is equal to or nested under one lexical root."""

    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def require_owned_mutation_path(*, path: Path, allowed_roots: Sequence[Path]) -> None:
    """Require one mutation target to stay under the selected managed roots."""

    lexical_path = lexical_absolute_path(path)
    lexical_roots = tuple(lexical_absolute_path(root) for root in allowed_roots)
    if any(path_is_within_root(path=lexical_path, root=root) for root in lexical_roots):
        return
    allowed_display = ", ".join(str(root) for root in lexical_roots)
    raise ValueError(
        "Refusing to mutate non-Houmao-managed path "
        f"`{lexical_path}`. Allowed roots: {allowed_display}"
    )


def remove_tree_or_path(path: Path, *, allowed_roots: Sequence[Path] | None = None) -> None:
    """Remove one file, symlink, or directory path when present."""

    if allowed_roots is not None:
        require_owned_mutation_path(path=path, allowed_roots=allowed_roots)
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    shutil.rmtree(path)


def replace_symlink(
    *,
    target: Path,
    destination: Path,
    allowed_roots: Sequence[Path] | None = None,
) -> None:
    """Replace one path with a symlink to the selected target."""

    remove_tree_or_path(destination, allowed_roots=allowed_roots)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(target)


def replace_tree(
    *,
    source: Path,
    destination: Path,
    allowed_roots: Sequence[Path] | None = None,
) -> None:
    """Replace one directory tree atomically enough for local overlay use."""

    remove_tree_or_path(destination, allowed_roots=allowed_roots)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)


def replace_path_with_text(
    *,
    destination: Path,
    text: str,
    allowed_roots: Sequence[Path] | None = None,
) -> None:
    """Replace one file-or-tree destination with UTF-8 text content."""

    remove_tree_or_path(destination, allowed_roots=allowed_roots)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def replace_file(
    *,
    source: Path,
    destination: Path,
    allowed_roots: Sequence[Path] | None = None,
) -> None:
    """Replace one file destination with a copy of the selected source file."""

    remove_tree_or_path(destination, allowed_roots=allowed_roots)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
