"""Canonical paths and memory bounds shared by logical file mounts."""

from __future__ import annotations

from collections.abc import Mapping
import unicodedata

from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.file_edits.contracts import MAX_FILE_BYTES

MAX_ENTRIES = 1024
MAX_TREE_BYTES = 16 * 1024 * 1024
_MAX_PATH_BYTES = 1024
_MAX_PATH_DEPTH = 32
_RESERVED_NAMES = frozenset({".", "..", ".git"})


def logical_path(value: str) -> str:
    """Require a canonical, relative UTF-8 POSIX path."""

    try:
        data = value.encode("utf-8")
    except UnicodeError:
        raise GatewayAccessError(422, "invalid_logical_path") from None
    parts = data.split(b"/")
    if (
        not data
        or len(data) > _MAX_PATH_BYTES
        or len(parts) > _MAX_PATH_DEPTH
        or any(not part or len(part) > 255 for part in parts)
        or "\\" in value
        or unicodedata.normalize("NFC", value) != value
        or any(unicodedata.category(char).startswith("C") for char in value)
        or any(part.casefold() in _RESERVED_NAMES for part in value.split("/"))
    ):
        raise GatewayAccessError(422, "invalid_logical_path")
    return value


def parents(path: str) -> tuple[str, ...]:
    """Return logical parents from the root down."""

    return tuple(path[:index] for index, char in enumerate(path) if char == "/")


def check_tree(entries: Mapping[str, bytes | None]) -> None:
    """Check the total number of entries and bytes retained in one tree."""

    if len(entries) > MAX_ENTRIES:
        raise GatewayAccessError(413, "draft_limit")
    size = 0
    for path, data in entries.items():
        logical_path(path)
        if data is None:
            continue
        if len(data) > MAX_FILE_BYTES:
            raise GatewayAccessError(413, "file_too_large")
        size += len(data)
    if size > MAX_TREE_BYTES:
        raise GatewayAccessError(413, "draft_limit")


def insert_parents(entries: dict[str, bytes | None], path: str) -> None:
    """Make missing directories and refuse to treat a file as a directory."""

    for parent in parents(path):
        if entries.setdefault(parent, None) is not None:
            raise GatewayAccessError(409, "path_conflict")
