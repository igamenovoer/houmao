"""Persist owner-bound gateway authority in bounded private files."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import secrets
import stat

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel

from houmao.gateway._access_sshsig import PrivateKey, load_private_key, public_key_text
from houmao.gateway.access_models import (
    MAX_ACCESS_DOCUMENT,
    GatewayAdminEnrollment,
    GatewayAdminState,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewaySelfKey,
    parse_access_document,
)

_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_STATE_FILE = "admin.json"
_SELF_FILE = "self.json"
_SIGNER_FILE = "self.key"
_LOCK_FILE = ".lock"
_INITIALIZED = b"houmao-gateway-access-v1\n"
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


class GatewayAccessStore:
    """Keep live enrollment state and generation signers under owner authority."""

    def __init__(self, root: Path, owner: GatewayOwner) -> None:
        """Bind a lexical private namespace to one agent and execution context."""

        self.m_root: Path = root
        self.m_owner: GatewayOwner = owner
        self.m_binding: str = hashlib.sha256(owner.model_dump_json().encode()).hexdigest()

    @classmethod
    def from_root(cls, root: Path, owner: GatewayOwner) -> GatewayAccessStore:
        """Select the private access namespace for the owner without creating it."""

        return cls(root, owner)

    @property
    def owner(self) -> GatewayOwner:
        """Return the owner required by this store."""

        return self.m_owner

    def initialize(self, seed: GatewayLaunchSeed) -> GatewayAdminState:
        """Initialize a new binding, or load the existing state without reseeding it."""

        try:
            with _private_directory(self.m_root, create=True) as root:
                with _file_lock(root, self.m_binding + ".lock", create=True):
                    try:
                        self._require_marker(root)
                    except FileNotFoundError:
                        # An existing state namespace without its marker is corrupt.
                        os.mkdir(self.m_binding, mode=0o700, dir_fd=root)
                    else:
                        return self.load()

                    # Publish the marker separately so deletion of the roster
                    # directory never enables initialization from the seed.
                    _write_file(root, self.m_binding + ".initialized", _INITIALIZED)
                    with self._open_owner() as directory:
                        descriptor = os.open(
                            _LOCK_FILE,
                            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                            0o600,
                            dir_fd=directory,
                        )
                        os.close(descriptor)
                        state = GatewayAdminState(
                            owner=self.m_owner,
                            revision=0,
                            keys=tuple(
                                GatewayAdminEnrollment(key=key, enrollment=0)
                                for key in seed.admin_keys
                            ),
                        )
                        _write_document(directory, _STATE_FILE, state)
                        return state
        except (OSError, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def load(self) -> GatewayAdminState:
        """Read the retained roster independently of live gateway discovery."""

        try:
            with self._open_owner() as directory:
                return self._load_state(directory)
        except (OSError, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    @contextmanager
    def read_locked(self) -> Iterator[GatewayAdminState]:
        """Keep membership stable through a proof admission decision."""

        try:
            with self._open_owner() as directory:
                with _file_lock(directory, _LOCK_FILE, exclusive=False):
                    yield self._load_state(directory)
        except (OSError, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def update(self, update: Callable[[GatewayAdminState], GatewayAdminState]) -> None:
        """Recheck membership and commit its replacement under the same file lock."""

        try:
            with self._open_owner() as directory:
                with _file_lock(directory, _LOCK_FILE):
                    current = self._load_state(directory)
                    candidate = update(current)
                    if (
                        candidate.owner != self.m_owner
                        or candidate.revision != current.revision + 1
                    ):
                        raise ValueError("invalid policy update")
                    _write_document(directory, _STATE_FILE, candidate)
        except (OSError, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def provision_self(self, generation_id: str) -> GatewaySelfKey:
        """Allocate a distinct Ed25519 credential for this managed generation."""

        generation_root = self._generation_root(generation_id)
        try:
            with self._open_owner() as directory:
                with _file_lock(directory, _LOCK_FILE):
                    self._load_state(directory)
                    try:
                        os.mkdir(generation_root.name, mode=0o700, dir_fd=directory)
                    except FileExistsError:
                        binding = self.load_self(generation_id)
                        signer = load_gateway_signer(self.self_signer_path(generation_id))
                        if public_key_text(signer.public_key()) != binding.public_key:
                            raise ValueError("invalid self signer binding")
                        return binding
                    os.fsync(directory)
                    with _private_directory(generation_root) as generation:
                        signer = Ed25519PrivateKey.generate()
                        private = signer.private_bytes(
                            serialization.Encoding.PEM,
                            serialization.PrivateFormat.OpenSSH,
                            serialization.NoEncryption(),
                        )
                        binding = GatewaySelfKey(
                            owner=self.m_owner,
                            generation_id=generation_id,
                            public_key=public_key_text(signer.public_key()),
                        )
                        _write_file(generation, _SIGNER_FILE, private)
                        _write_document(generation, _SELF_FILE, binding)
                        return binding
        except (OSError, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def load_self(self, generation_id: str) -> GatewaySelfKey:
        """Read one explicit generation's owner-bound verification key."""

        try:
            with _private_directory(self._generation_root(generation_id)) as generation:
                binding = parse_access_document(
                    GatewaySelfKey, _read_file(generation, _SELF_FILE, MAX_ACCESS_DOCUMENT)
                )
                if binding.owner != self.m_owner or binding.generation_id != generation_id:
                    raise ValueError("invalid self key binding")
                return binding
        except (OSError, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def self_signer_path(self, generation_id: str) -> Path:
        """Resolve the private source for an already verified current generation."""

        return self._generation_root(generation_id) / _SIGNER_FILE

    def _generation_root(self, generation_id: str) -> Path:
        """Select a generation without treating caller labels as path components."""

        generation = hashlib.sha256(generation_id.encode()).hexdigest()
        return self.m_root / self.m_binding / ("self-" + generation)

    @contextmanager
    def _open_owner(self) -> Iterator[int]:
        """Open the owner namespace as a checked directory descriptor."""

        with _private_directory(self.m_root) as root:
            self._require_marker(root)
            directory = os.open(self.m_binding, _DIR_FLAGS, dir_fd=root)
            try:
                _require_private_directory(directory)
                yield directory
            finally:
                os.close(directory)

    def _require_marker(self, directory: int) -> None:
        """Validate the marker distinguishing retained policy from first launch."""

        marker = _read_file(directory, self.m_binding + ".initialized", len(_INITIALIZED))
        if marker != _INITIALIZED:
            raise ValueError("invalid access initialization marker")

    def _load_state(self, directory: int) -> GatewayAdminState:
        """Validate the document and its precise owner binding."""

        state = parse_access_document(
            GatewayAdminState, _read_file(directory, _STATE_FILE, MAX_ACCESS_DOCUMENT)
        )
        if state.owner != self.m_owner:
            raise ValueError("invalid access owner binding")
        return state


def read_private_access_file(path: Path, *, limit: int = MAX_ACCESS_DOCUMENT) -> bytes:
    """Read one bounded owner-only regular source outside project checkouts."""

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
    descriptor = os.open(path.anchor, _DIR_FLAGS)
    try:
        _reject_checkout(descriptor)
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
            _reject_checkout(descriptor)
        yield descriptor
    finally:
        os.close(descriptor)


def _reject_checkout(directory: int) -> None:
    """Reject a worktree marker before reading or creating private sources."""

    try:
        os.stat(".git", dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
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


def _write_document(directory: int, name: str, value: BaseModel) -> None:
    """Write a bounded owner-only JSON record."""

    payload = (value.model_dump_json() + "\n").encode()
    if len(payload) > MAX_ACCESS_DOCUMENT:
        raise ValueError("private document exceeds its size limit")
    _write_file(directory, name, payload)


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
