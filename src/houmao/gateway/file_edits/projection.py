"""Prepare owner-private immutable file revisions for a native mount adapter."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile

from houmao.gateway._access_storage import _file_lock, _private_directory, _read_file, _write_file
from houmao.gateway.file_edits.contracts import MAX_FILE_BYTES

_REVISION = re.compile(r"[a-f0-9]{40}")
_MOUNT = re.compile(r"[a-f0-9]{32}")
_OPERATION = re.compile(r"[A-Za-z0-9_.:-]{1,128}")


class ProjectionConflict(ValueError):
    """The owner-managed native projection differs from the expected revision."""


class FileProjection:
    """Prepare complete trees without changing the active projection."""

    def __init__(self, root: Path) -> None:
        """Bind the private path supplied by the owner provisioner."""

        self.m_root: Path = root

    @property
    def root(self) -> Path:
        """Expose the selected private root to its native adapter."""

        return self.m_root

    def initialize(self, mount_id: str, revision: str, files: Mapping[str, bytes]) -> None:
        """Initialize the first projection or verify the established mount binding."""

        if not _MOUNT.fullmatch(mount_id):
            raise ProjectionConflict("Invalid managed mount identity.")
        self.prepare(revision, files)
        with _private_directory(self.m_root) as directory:
            with _file_lock(directory, ".projection.lock", create=True):
                mount_record = (mount_id + "\n").encode("ascii")
                try:
                    recorded = _read_file(directory, "mount-id", len(mount_record))
                except FileNotFoundError:
                    try:
                        existing = _read_file(directory, "published", 41)
                    except FileNotFoundError:
                        _write_file(directory, "published", (revision + "\n").encode("ascii"))
                    else:
                        if existing != (revision + "\n").encode("ascii"):
                            raise ProjectionConflict("Unbound native projection has changed.")
                    _write_file(directory, "mount-id", mount_record)
                else:
                    if recorded != mount_record or self.published_marker() != revision:
                        raise ProjectionConflict("Managed native projection has changed.")

    def published_marker(self) -> str:
        """Read the exact revision made visible by the native adapter."""

        return self.publication_identity()[0]

    def publication_identity(self) -> tuple[str, str | None]:
        """Read the revision and exact operation atomically selected by native publication."""

        try:
            with _private_directory(self.m_root) as directory:
                marker = _read_file(directory, "published", 170).decode("ascii")
        except (OSError, UnicodeError, ValueError):
            raise ProjectionConflict("Managed native publication is unavailable.") from None
        revision, separator, operation = marker[:-1].partition("\n")
        if (
            not marker.endswith("\n")
            or not _REVISION.fullmatch(revision)
            or (separator and not _OPERATION.fullmatch(operation))
        ):
            raise ProjectionConflict("Managed native publication marker is invalid.")
        return revision, operation or None

    def prepare(self, revision: str, files: Mapping[str, bytes]) -> None:
        """Write and verify one immutable revision before acquiring maintenance."""

        destination = self._revision_path(revision)
        with _private_directory(self.m_root, create=True) as directory:
            with _file_lock(directory, ".projection.lock", create=True):
                with _private_directory(destination.parent, create=True) as revisions:
                    if destination.exists() or destination.is_symlink():
                        self.verify_revision(revision, files)
                        return
                    staging = Path(tempfile.mkdtemp(prefix=".prepare-", dir=destination.parent))
                    try:
                        for logical, content in sorted(files.items()):
                            parts = _logical_parts(logical)
                            if len(content) > MAX_FILE_BYTES:
                                raise ProjectionConflict("A projection file exceeds its bound.")
                            with _private_directory(
                                staging.joinpath(*parts[:-1]), create=True
                            ) as parent:
                                _write_file(parent, parts[-1], content)
                        os.rename(staging, destination)
                        os.fsync(revisions)
                    finally:
                        if staging.exists():
                            shutil.rmtree(staging)

    def verify_revision(self, revision: str, files: Mapping[str, bytes]) -> None:
        """Reject missing, altered, or extra files within a managed revision."""

        expected_directories = {
            str(parent)
            for name in files
            for parent in PurePosixPath(name).parents
            if str(parent) != "."
        }
        path = self._revision_path(revision)
        found_files: set[str] = set()
        try:
            with _private_directory(path):
                for entry in path.rglob("*"):
                    relative = entry.relative_to(path).as_posix()
                    info = entry.lstat()
                    if stat.S_ISDIR(info.st_mode) and relative in expected_directories:
                        continue
                    if stat.S_ISREG(info.st_mode) and relative in files:
                        with _private_directory(entry.parent) as parent:
                            data = _read_file(parent, entry.name, MAX_FILE_BYTES)
                        if data == files[relative]:
                            found_files.add(relative)
                            continue
                    raise ProjectionConflict("Managed revision contains foreign changes.")
        except OSError:
            raise ProjectionConflict("Managed revision is unavailable.") from None
        if found_files != files.keys():
            raise ProjectionConflict("Managed revision is incomplete.")

    def _revision_path(self, revision: str) -> Path:
        """Resolve a fixed Git object ID below the owner-selected projection."""

        if not _REVISION.fullmatch(revision):
            raise ProjectionConflict("Invalid managed revision identity.")
        return self.m_root / "revisions" / revision


def _logical_parts(logical: str) -> tuple[str, ...]:
    """Refuse a noncanonical logical path before joining filesystem components."""

    parts = tuple(logical.split("/"))
    if any(
        part in {"", ".", ".."} or part.casefold() == ".git" or "\\" in part or "\x00" in part
        for part in parts
    ):
        raise ProjectionConflict("Invalid managed projection path.")
    return parts
