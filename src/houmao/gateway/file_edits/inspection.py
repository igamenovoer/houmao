"""Build bounded logical directory and change pages."""

from __future__ import annotations

from collections.abc import Mapping
from difflib import unified_diff
import hashlib
from typing import Literal

from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.file_edits.contracts import (
    FileDiffEntry,
    FileDiffResponse,
    FileEntry,
    FileListResponse,
)
from houmao.gateway.file_edits.paths import logical_path

_PATCH_BYTES_PER_PAGE = 48 * 1024
_PATCH_INPUT_BYTES_PER_FILE = 16 * 1024
_PATCH_LINES_PER_FILE = 400


def list_page(
    entries: Mapping[str, bytes | None],
    revision: str,
    directory: str | None,
    after: str | None,
    limit: int,
) -> FileListResponse:
    """Return ordered immediate children from one pinned logical tree."""

    if after is not None:
        logical_path(after)
    prefix = ""
    if directory is not None:
        directory = logical_path(directory)
        if directory not in entries or entries[directory] is not None:
            raise GatewayAccessError(404, "unknown_path")
        prefix = directory + "/"
    children = sorted(
        path
        for path in entries
        if path.startswith(prefix)
        and "/" not in path[len(prefix) :]
        and (after is None or path > after)
    )
    page = [
        FileEntry(
            path=path,
            kind="directory" if data is None else "file",
            size=len(data) if data is not None else None,
        )
        for path in children[:limit]
        for data in (entries[path],)
    ]
    return FileListResponse(
        revision=revision,
        entries=page,
        next_after=page[-1].path if len(children) > limit else None,
    )


def diff_page(
    before: Mapping[str, bytes],
    after: Mapping[str, bytes],
    base: str | None,
    cursor: str | None,
    limit: int,
) -> FileDiffResponse:
    """Return changed files with exact digests and bounded text previews."""

    if cursor is not None:
        logical_path(cursor)
    paths = sorted(
        path
        for path in before.keys() | after.keys()
        if (cursor is None or path > cursor) and before.get(path) != after.get(path)
    )
    changes: list[FileDiffEntry] = []
    budget = _PATCH_BYTES_PER_PAGE
    for path in paths[:limit]:
        old = before.get(path)
        new = after.get(path)
        change: Literal["added", "modified", "deleted"] = (
            "added" if old is None else ("deleted" if new is None else "modified")
        )
        patch = _text_patch(path, old, new, budget)
        if patch is not None:
            budget -= len(patch.encode("utf-8"))
        changes.append(
            FileDiffEntry(
                path=path,
                change=change,
                before_sha256=hashlib.sha256(old).hexdigest() if old is not None else None,
                after_sha256=hashlib.sha256(new).hexdigest() if new is not None else None,
                patch=patch,
                patch_truncated=patch is None,
            )
        )
    return FileDiffResponse(
        base_commit=base,
        changes=changes,
        next_after=changes[-1].path if len(paths) > limit else None,
    )


def _text_patch(path: str, before: bytes | None, after: bytes | None, budget: int) -> str | None:
    """Generate a preview only when UTF-8 decoding and diffing fit the limits."""

    a, b = before or b"", after or b""
    if not budget or len(a) + len(b) > _PATCH_INPUT_BYTES_PER_FILE or b"\0" in a or b"\0" in b:
        return None
    try:
        old = a.decode("utf-8").splitlines(keepends=True)
        new = b.decode("utf-8").splitlines(keepends=True)
    except UnicodeError:
        return None
    if len(old) + len(new) > _PATCH_LINES_PER_FILE:
        return None
    patch = "".join(
        unified_diff(
            old,
            new,
            fromfile=f"a/{path}" if before is not None else "/dev/null",
            tofile=f"b/{path}" if after is not None else "/dev/null",
        )
    )
    return patch if len(patch.encode("utf-8")) <= budget else None
