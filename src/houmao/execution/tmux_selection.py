"""Resolve launch-time tmux selectors and persist the owner default address."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import stat
import sys
from tempfile import mkstemp
from typing import Literal, get_args
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, model_validator

from houmao.execution.context import current_execution_binding, execution_is_read_only
from houmao.execution.models import ExecutionBindingV1
from houmao.execution.tmux import (
    TmuxCommandError,
    TmuxServer,
    capture_tmux_socket_path,
    current_tmux_allow_start,
    current_tmux_socket_path,
    native_default_tmux_socket_path,
    validate_tmux_socket_path,
)
from houmao.owned_paths import resolve_registry_root

TmuxServerMode = Literal["user-default", "houmao-default", "new", "socket"]
TMUX_SERVER_MODES: tuple[TmuxServerMode, ...] = get_args(TmuxServerMode)
_MAX_RECORD_BYTES = 4096
_SOCKET_PATH_MAX_BYTES = 107 if sys.platform.startswith("linux") else 103


class TmuxServerSelector(BaseModel):
    """Describe a launch-time choice without inspecting the selected owner's host."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server: TmuxServerMode
    socket_path: str | None = None

    @model_validator(mode="after")
    def _validate_socket_mode(self) -> TmuxServerSelector:
        """Allow a socket path exactly when the selected mode requires it."""

        if self.server == "socket":
            if self.socket_path is None:
                raise ValueError("socket_path is required for tmux server mode `socket`")
            validate_tmux_socket_path(self.socket_path)
        elif self.socket_path is not None:
            raise ValueError("socket_path is only allowed for tmux server mode `socket`")
        return self


@dataclass(frozen=True)
class ResolvedTmuxServer:
    """Bind a planned tmux launch to one concrete owner-local socket."""

    socket_path: str
    allow_start: bool


class _OwnerScope(BaseModel):
    """Identify the OS owner and socket domain independently of agent or project."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    uid: int
    host_id: str
    container_id: str | None = None

    @property
    def key(self) -> str:
        """Return a filesystem-safe scoped identifier."""

        return sha256(f"{self.uid}:{self.host_id}:{self.container_id or ''}".encode()).hexdigest()

    @property
    def socket_directory(self) -> Path:
        """Return this owner's short, private socket directory."""

        return _managed_socket_directory(self.uid) / self.key[:24]


class _DefaultRecord(BaseModel):
    """Store a stable owner socket address independently of tmux liveness."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    owner: _OwnerScope
    socket_path: str


def resolve_tmux_server(
    selector: TmuxServerSelector | None,
    *,
    registry_root: Path | None = None,
    execution_binding: ExecutionBindingV1 | None = None,
    environment: Mapping[str, str] | None = None,
) -> ResolvedTmuxServer:
    """Resolve and validate a server in the admitted execution owner's context."""

    binding = current_execution_binding() if execution_binding is None else execution_binding
    pinned = binding.tmux_socket if binding is not None else None
    if selector is None:
        selected = pinned if pinned is not None else capture_tmux_socket_path(environment)
        permission = current_tmux_allow_start() if current_tmux_socket_path() == selected else None
        return ResolvedTmuxServer(selected, allow_start=permission is not False)
    if selector.server == "user-default":
        selected = native_default_tmux_socket_path(environment)
        _require_admitted_socket(selected, pinned)
        _check_socket_length(selected)
        _prepare_native_default_directory(Path(selected).parent, create=False)
        return ResolvedTmuxServer(selected, allow_start=True)
    if selector.server == "socket":
        assert selector.socket_path is not None
        selected = selector.socket_path
        _require_admitted_socket(selected, pinned)
        _check_socket_length(selected)
        try:
            TmuxServer(selected, allow_start=False).list_sessions()
        except TmuxCommandError as exc:
            raise ValueError(f"Existing tmux server is unavailable at {selected}: {exc}") from None
        return ResolvedTmuxServer(selected, allow_start=False)

    if selector.server == "new":
        if pinned is not None:
            raise ValueError(
                f"Execution owner pinned to {pinned} cannot select tmux server mode `new`"
            )
        if execution_is_read_only():
            raise ValueError("Allocating a new tmux server address requires a launch")
        owner = _observed_owner_scope(binding)
        socket = owner.socket_directory / f"{uuid4().hex}.sock"
        _check_socket_length(str(socket))
        if _prepare_managed_socket(socket, owner, create=True):
            raise ValueError(f"New tmux socket address is already in use: {socket}")
        return ResolvedTmuxServer(str(socket), allow_start=True)

    owner = _observed_owner_scope(binding)
    registry = resolve_registry_root(
        explicit_root=binding.registry_root if binding is not None else registry_root,
        env=environment,
    )
    selected = _resolve_houmao_default(registry, owner, pinned)
    return ResolvedTmuxServer(selected, allow_start=True)


def prepare_tmux_start_path(socket_path: Path) -> None:
    """Prepare only a managed, native default, or admitted pinned startup directory."""

    binding = current_execution_binding()
    if socket_path.name == "default" and socket_path.parent.name == f"tmux-{os.getuid()}":
        _prepare_native_default_directory(socket_path.parent, create=True)
    elif socket_path.parent.parent == _managed_socket_directory(os.geteuid()):
        owner = _observed_owner_scope(binding)
        _prepare_managed_socket(socket_path, owner, create=True)
    elif (
        binding is not None
        and binding.tmux_socket == str(socket_path)
        and not socket_path.parent.exists()
    ):
        socket_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)


def _prepare_native_default_directory(path: Path, *, create: bool) -> None:
    """Check or prepare the tmux-owned leaf of a captured native default address."""

    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if not create:
            return
        raise
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & stat.S_IRWXO
    ):
        raise ValueError(f"Unsafe native tmux socket directory: {path}")


def _observed_owner_scope(binding: ExecutionBindingV1 | None) -> _OwnerScope:
    """Use the effective OS identity and the admitted container when available."""

    from houmao.execution.owner import _host_identity

    uid = os.geteuid()
    host_id = _host_identity()
    if binding is not None and (binding.uid != uid or binding.host_id != host_id):
        raise ValueError("Tmux selection requires the observed execution owner")
    return _OwnerScope(
        uid=uid,
        host_id=host_id,
        container_id=binding.container_id if binding is not None else None,
    )


def _managed_socket_directory(uid: int) -> Path:
    """Return the fixed host-local base for the UID's managed socket addresses."""

    return Path("/tmp") / f"houmao-tmux-{uid}"


def _require_admitted_socket(selected: str, pinned: str | None) -> None:
    """Reject a selection that differs from the admitted execution owner's socket."""

    if pinned is not None and selected != pinned:
        raise ValueError(
            f"Selected tmux socket {selected} differs from admitted owner socket {pinned}"
        )


def _check_socket_length(path: str) -> None:
    """Check the platform's Unix socket address limit before allocation."""

    if len(os.fsencode(path)) > _SOCKET_PATH_MAX_BYTES:
        raise ValueError(f"Tmux socket path is too long for this host: {path}")


def _ensure_private_directory(path: Path, *, uid: int, create: bool) -> None:
    """Use a real owner-only directory or allow an absent path on a read."""

    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if not create:
            return
        raise
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != uid
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ValueError(f"Unsafe owner-private tmux directory: {path}")


def _prepare_managed_socket(socket_path: Path, owner: _OwnerScope, *, create: bool) -> bool:
    """Validate the managed namespace and any existing socket before use."""

    expected_directory = owner.socket_directory
    if socket_path.parent != expected_directory or socket_path.name in {"", ".", ".."}:
        raise ValueError(f"Tmux socket is outside the owner-private namespace: {socket_path}")
    _ensure_private_directory(expected_directory.parent, uid=owner.uid, create=create)
    _ensure_private_directory(expected_directory, uid=owner.uid, create=create)
    try:
        metadata = socket_path.lstat()
    except FileNotFoundError:
        return False
    mode = stat.S_IMODE(metadata.st_mode)
    if (
        not stat.S_ISSOCK(metadata.st_mode)
        or metadata.st_uid != owner.uid
        or mode & 0o077
        or mode & 0o600 != 0o600
    ):
        raise ValueError(f"Unsafe object at the owner-private tmux socket: {socket_path}")
    return True


def _resolve_houmao_default(registry: Path, owner: _OwnerScope, pinned: str | None) -> str:
    """Read the default or atomically initialize it for an admitted launch."""

    directory = registry / f"tmux-default-{owner.key}"
    record_path = directory / "record.json"
    _ensure_private_directory(directory, uid=owner.uid, create=False)
    record = _read_default(record_path, owner)
    if record is not None:
        return _use_default_record(record, owner, pinned)
    if execution_is_read_only():
        raise ValueError(f"Houmao default tmux record is uninitialized: {record_path}")

    selected = str(owner.socket_directory / "default.sock")
    _require_admitted_socket(selected, pinned)
    _check_socket_length(selected)
    registry.mkdir(mode=0o700, parents=True, exist_ok=True)
    _ensure_private_directory(directory, uid=owner.uid, create=True)
    with _default_record_lock(directory / "record.lock", owner.uid):
        record = _read_default(record_path, owner)
        if record is None:
            _prepare_managed_socket(Path(selected), owner, create=True)
            record = _publish_default(
                record_path, _DefaultRecord(schema_version=1, owner=owner, socket_path=selected)
            )
        return _use_default_record(record, owner, pinned)


def _use_default_record(record: _DefaultRecord, owner: _OwnerScope, pinned: str | None) -> str:
    """Check a record's exact socket against admission and the managed namespace."""

    if record.owner != owner:
        raise ValueError("Houmao default tmux record belongs to a different execution owner")
    selected = validate_tmux_socket_path(record.socket_path)
    _require_admitted_socket(selected, pinned)
    _check_socket_length(selected)
    _prepare_managed_socket(Path(selected), owner, create=False)
    return selected


def _read_default(path: Path, owner: _OwnerScope) -> _DefaultRecord | None:
    """Load a bounded private record without following filesystem aliases."""

    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            _require_private_file(os.fstat(stream.fileno()), path=path, uid=owner.uid)
            payload = stream.read(_MAX_RECORD_BYTES + 1)
        if len(payload) > _MAX_RECORD_BYTES:
            raise ValueError("Record exceeds the size limit")
        return _DefaultRecord.model_validate_json(payload)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise ValueError(f"Houmao default tmux record is malformed or unsafe: {path}") from None


def _require_private_file(metadata: os.stat_result, *, path: Path, uid: int) -> None:
    """Check the type, owner, and permissions of an opened registry file."""

    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != uid
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise ValueError(f"Unsafe owner-private tmux registry file: {path}")


@contextmanager
def _default_record_lock(path: Path, uid: int) -> Iterator[None]:
    """Serialize owner default initialization using a stable private key lock."""

    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        _require_private_file(os.fstat(descriptor), path=path, uid=uid)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _publish_default(path: Path, record: _DefaultRecord) -> _DefaultRecord:
    """Commit an owner record atomically without replacing an existing winner."""

    descriptor, temporary = mkstemp(prefix=".record-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write((record.model_dump_json() + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            winner = _read_default(path, record.owner)
            if winner is None:
                raise ValueError(
                    f"Houmao default tmux record changed during bootstrap: {path}"
                ) from None
            return winner
        return record
    finally:
        os.unlink(temporary)
