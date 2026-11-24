"""Keep owner-side authorization and selected signing sources private."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import secrets
import stat

from houmao.gateway._access_sshsig import PrivateKey, load_private_key
from houmao.gateway.access_models import MAX_ACCESS_DOCUMENT

_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_ERRORS = {
    401: "Valid gateway proof is required.",
    403: "The verified caller lacks authority for this operation.",
    404: "The selected gateway access resource was not found.",
    409: "Gateway access changed or the requested update conflicts.",
    413: "The gateway request exceeds its size limit.",
    422: "The gateway request is invalid.",
    429: "Gateway challenge capacity is currently exhausted.",
    503: "Gateway access policy is unavailable.",
}


class GatewayAccessError(RuntimeError):
    """A typed access failure with safe transport diagnostics."""

    def __init__(self, status_code: int, code: str) -> None:
        """Keep policy failure categories separate from source data."""

        self.m_status_code: int = status_code
        self.m_code: str = code
        self.m_detail: str = _ERRORS[status_code]
        super().__init__(self.m_detail)

    @property
    def status_code(self) -> int:
        """Return the protocol status for this access failure."""

        return self.m_status_code

    @property
    def code(self) -> str:
        """Return the stable diagnostic category."""

        return self.m_code

    @property
    def detail(self) -> str:
        """Return a safe message without source paths or policy data."""

        return self.m_detail


def read_private_access_file(path: Path, *, limit: int = MAX_ACCESS_DOCUMENT) -> bytes:
    """Read one bounded owner-only regular source from approved private storage."""

    try:
        with _open_directory(path.parent) as parent:
            return _read_file(parent, path.name, min(limit, MAX_ACCESS_DOCUMENT))
    except FileNotFoundError:
        raise FileNotFoundError("private gateway source is missing") from None
    except (OSError, ValueError):
        raise ValueError("private gateway source is unavailable or unsafe") from None


def load_gateway_signer(path: Path) -> PrivateKey:
    """Load the explicitly selected private signing key from safe storage."""

    return load_private_key(read_private_access_file(path))


@contextmanager
def _open_directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Traverse the lexical directory path using no-follow descriptors."""

    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("invalid private directory")
    current = Path(path.anchor)
    descriptor = os.open(path.anchor, _DIR_FLAGS)
    try:
        _reject_checkout(descriptor, checkout_root=current, destination=path)
        for part in path.parts[1:]:
            try:
                child = os.open(part, _DIR_FLAGS, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                    os.fsync(descriptor)
                except FileExistsError:
                    pass
                child = os.open(part, _DIR_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            current = current / part
            _reject_checkout(descriptor, checkout_root=current, destination=path)
        yield descriptor
    finally:
        os.close(descriptor)


def _reject_checkout(directory: int, *, checkout_root: Path, destination: Path) -> None:
    """Reject worktrees except for purpose-specific subdirectories of their tmp root."""

    try:
        os.stat(".git", dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    scratch = checkout_root / "tmp"
    if destination == scratch or not destination.is_relative_to(scratch):
        raise ValueError("private access source is in a checkout")


@contextmanager
def _private_directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Require the selected state directory to be owned by this effective UID."""

    with _open_directory(path, create=create) as directory:
        _require_private_directory(directory)
        yield directory


def _require_private_directory(descriptor: int) -> None:
    """Require a directory inode private to this effective UID."""

    metadata = os.fstat(descriptor)
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError("unsafe private directory")


@contextmanager
def _file_lock(
    directory: int, name: str, *, exclusive: bool = True, create: bool = False
) -> Iterator[None]:
    """Hold the retained private membership lock across a bounded state operation."""

    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
    if create:
        flags |= os.O_CREAT
    descriptor = os.open(name, flags, 0o600, dir_fd=directory)
    try:
        _require_private_file(descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        os.close(descriptor)


def _require_private_file(descriptor: int) -> None:
    """Validate the opened inode's type, ownership, permissions, and links."""

    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
        or metadata.st_nlink > 1
    ):
        raise ValueError("unsafe private file")


def _read_file(directory: int, name: str, limit: int) -> bytes:
    """Read at most the requested byte ceiling from the validated open inode."""

    descriptor = os.open(name, _FILE_FLAGS, dir_fd=directory)
    with os.fdopen(descriptor, "rb") as source:
        _require_private_file(source.fileno())
        payload = source.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("private file exceeds its size limit")
    return payload


def _write_file(directory: int, name: str, payload: bytes) -> None:
    """Replace a file atomically and flush the new directory entry."""

    temporary = f".access-{secrets.token_hex(16)}"
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
    )
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass
