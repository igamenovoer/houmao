"""Owner-local one-use gateway relay and passive backing authority."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import secrets
import stat
import time
from urllib.parse import quote, urlsplit

from pydantic import BaseModel, ConfigDict, Field

from houmao.gateway.access import (
    AccessClass,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayGrant,
    GatewayRequestBinding,
    GatewayTarget,
    parse_access_document,
)

RELAY_HEADER = "Houmao-Relay"
BACKING_HEADER = "Houmao-Backing"
_RELAY_DIR = "gateway-relay"
_BACKING_DIR = "passive-backing"
_BINDING_FILE = "binding.json"
_TOKEN = re.compile(r"[0-9a-f]{64}\Z")
_MAX_RECORD_BYTES = 8192
_MAX_TOKENS = 128
_LIFETIME_SECONDS = 15
_BACKING_ROUTES = {
    ("GET", "inspect"),
    ("POST", "headless-prompt"),
    ("POST", "interrupt"),
}


class PassiveBackingBinding(BaseModel):
    """Configured owner-service authority for one managed body and ingress."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    target: GatewayTarget
    api_base_url: str = Field(min_length=1, max_length=2048)
    tracked_agent_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,128}$")

    def allows(self, request: GatewayRequestBinding) -> bool:
        """Check the exact backing route and permit no alternate query."""

        prefix = f"/houmao/agents/{quote(self.tracked_agent_id, safe='')}/gateway/internal/"
        if not request.path.startswith(prefix) or request.query:
            return False
        return (request.method, request.path.removeprefix(prefix)) in _BACKING_ROUTES


class _RelayRecord(BaseModel):
    """A single admitted caller's authority for a transformed request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    grant: GatewayGrant
    request: GatewayRequestBinding
    expires_at: float


class _BackingRecord(BaseModel):
    """A single request made by the configured server-managed backing client."""

    model_config = ConfigDict(extra="forbid", strict=True)

    binding: PassiveBackingBinding
    request: GatewayRequestBinding
    expires_at: float


@contextmanager
def _authority_directory(root: Path, name: str, *, create: bool) -> Iterator[int]:
    """Open and lock the designated private token directory by descriptor."""

    flags = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    root_fd = os.open(root, flags)
    try:
        _require_private(os.fstat(root_fd), directory=True)
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=root_fd)
            except FileExistsError:
                pass
        descriptor = os.open(name, flags, dir_fd=root_fd)
        try:
            _require_private(os.fstat(descriptor), directory=True)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield descriptor
        finally:
            os.close(descriptor)
    finally:
        os.close(root_fd)


def _require_private(info: os.stat_result, *, directory: bool = False) -> None:
    """Reject non-owner and shared files before reading authority data."""

    correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (
        not correct_type
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) & 0o077
        or (not directory and (info.st_size > _MAX_RECORD_BYTES or info.st_nlink != 1))
    ):
        raise ValueError("unsafe authority source")


def _read_record(descriptor: int, name: str) -> bytes:
    """Read one bounded, private record beneath the locked directory."""

    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    source = os.open(name, flags, dir_fd=descriptor)
    with os.fdopen(source, "rb") as stream:
        _require_private(os.fstat(stream.fileno()))
        content = stream.read(_MAX_RECORD_BYTES + 1)
    if len(content) > _MAX_RECORD_BYTES:
        raise ValueError("authority record exceeds limit")
    return content


def _write_record(descriptor: int, name: str, document: BaseModel) -> None:
    """Create a private record before releasing the directory lock."""

    content = document.model_dump_json().encode("utf-8")
    if len(content) > _MAX_RECORD_BYTES:
        raise ValueError("authority record exceeds limit")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    output = os.open(name, flags, mode=0o600, dir_fd=descriptor)
    try:
        with os.fdopen(output, "wb") as stream:
            stream.write(content)
    except OSError:
        os.unlink(name, dir_fd=descriptor)
        raise


def _issue_token(descriptor: int, document: BaseModel) -> str:
    """Collect expired records and publish a bounded one-use token."""

    cutoff = time.time() - _LIFETIME_SECONDS
    pending = 0
    with os.scandir(descriptor) as files:
        for entry in files:
            if not _TOKEN.fullmatch(entry.name):
                continue
            if entry.stat(follow_symlinks=False).st_mtime < cutoff:
                os.unlink(entry.name, dir_fd=descriptor)
            else:
                pending += 1
    if pending >= _MAX_TOKENS:
        raise GatewayAccessError(503, "policy_unavailable")
    token = secrets.token_hex(32)
    _write_record(descriptor, token, document)
    return token


def _take_token(descriptor: int, token: str) -> bytes:
    """Remove one credential while holding the issuer and consumer lock."""

    if not _TOKEN.fullmatch(token):
        raise ValueError("invalid authority token")
    record = _read_record(descriptor, token)
    os.unlink(token, dir_fd=descriptor)
    return record


def issue_gateway_relay(root: Path, *, grant: GatewayGrant, request: GatewayRequestBinding) -> str:
    """Relay only an already verified caller to an exact downstream request."""

    if grant.role not in {"admin", "self"}:
        raise GatewayAccessError(403, "insufficient_authority")
    try:
        with _authority_directory(root, _RELAY_DIR, create=True) as descriptor:
            return _issue_token(
                descriptor,
                _RelayRecord(
                    grant=grant, request=request, expires_at=time.time() + _LIFETIME_SECONDS
                ),
            )
    except (OSError, ValueError):
        raise GatewayAccessError(503, "policy_unavailable") from None


def consume_gateway_relay(
    root: Path,
    *,
    target: GatewayTarget,
    request: GatewayRequestBinding,
    token: str,
    policy: GatewayAccessPolicy,
    access: AccessClass,
) -> GatewayGrant:
    """Consume relay proof and check current caller enrollment and scope."""

    policy.m_store.load()
    try:
        with _authority_directory(root, _RELAY_DIR, create=False) as descriptor:
            record = parse_access_document(_RelayRecord, _take_token(descriptor, token))
    except (OSError, ValueError):
        raise GatewayAccessError(401, "invalid_proof") from None
    grant = record.grant
    if (
        record.expires_at <= time.time()
        or record.request != request
        or grant.target != target
        or grant.role not in {"self", "admin"}
        or not policy.revalidate(grant)
    ):
        raise GatewayAccessError(401, "invalid_proof")
    if access == "public" or (
        access == "admin" and grant.role == "self" and grant.revision is None
    ):
        raise GatewayAccessError(403, "insufficient_authority")
    return grant


def provision_passive_backing(root: Path, binding: PassiveBackingBinding) -> None:
    """Persist the selected passive service authority during owner launch."""

    parts = urlsplit(binding.api_base_url)
    if (
        parts.scheme != "http"
        or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parts.username is not None
        or parts.password is not None
        or parts.path
        or parts.query
        or parts.fragment
    ):
        raise GatewayAccessError(503, "policy_unavailable")
    temp_name = f".binding-{secrets.token_hex(16)}"
    try:
        with _authority_directory(root, _BACKING_DIR, create=True) as descriptor:
            _write_record(descriptor, temp_name, binding)
            try:
                os.replace(temp_name, _BINDING_FILE, src_dir_fd=descriptor, dst_dir_fd=descriptor)
            finally:
                try:
                    os.unlink(temp_name, dir_fd=descriptor)
                except FileNotFoundError:
                    pass
    except (OSError, ValueError):
        raise GatewayAccessError(503, "policy_unavailable") from None


def issue_passive_backing(
    root: Path, *, binding: PassiveBackingBinding, request: GatewayRequestBinding
) -> str:
    """Issue service proof for an operation allowed by the saved binding."""

    try:
        with _authority_directory(root, _BACKING_DIR, create=False) as descriptor:
            saved = parse_access_document(
                PassiveBackingBinding, _read_record(descriptor, _BINDING_FILE)
            )
            if binding != saved or not binding.allows(request):
                raise GatewayAccessError(403, "insufficient_authority")
            return _issue_token(
                descriptor,
                _BackingRecord(
                    binding=binding, request=request, expires_at=time.time() + _LIFETIME_SECONDS
                ),
            )
    except (OSError, ValueError):
        raise GatewayAccessError(503, "policy_unavailable") from None


def consume_passive_backing(
    root: Path, *, binding: PassiveBackingBinding, request: GatewayRequestBinding, token: str
) -> None:
    """Admit one exact backing operation from its current configured service."""

    if not binding.allows(request):
        raise GatewayAccessError(403, "insufficient_authority")
    try:
        with _authority_directory(root, _BACKING_DIR, create=False) as descriptor:
            saved = parse_access_document(
                PassiveBackingBinding, _read_record(descriptor, _BINDING_FILE)
            )
            record = parse_access_document(_BackingRecord, _take_token(descriptor, token))
    except (OSError, ValueError):
        raise GatewayAccessError(401, "invalid_proof") from None
    if (
        record.expires_at <= time.time()
        or record.binding != binding
        or saved != binding
        or record.request != request
    ):
        raise GatewayAccessError(401, "invalid_proof")
