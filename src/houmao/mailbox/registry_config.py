"""Private configuration linking one selected registry to its offline mail store."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import ipaddress
import json
import os
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from houmao.owned_paths import resolve_registry_root


class OfflineRegistryConfigurationError(ValueError):
    """An offline registry configuration is missing, unsafe, or inconsistent."""


class OfflineRegistryConfig(BaseModel):
    """Explicit filesystem authority and private administrative credential reference."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: int = Field(default=1, ge=1, le=1)
    registry_root: Path
    mailbox_root: Path
    admin_credential_file: Path
    public_url: str = "http://127.0.0.1:9892"
    max_attachment_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)

    @field_validator("registry_root", "mailbox_root", "admin_credential_file")
    @classmethod
    def _resolve_path(cls, value: Path) -> Path:
        """Resolve explicitly selected local paths."""

        return value.expanduser().resolve()

    @field_validator("public_url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        """Refuse to advertise credential-bearing non-loopback plaintext access."""

        return validate_registry_url(value)

    @classmethod
    def from_file(cls, path: Path) -> OfflineRegistryConfig:
        """Load a private JSON service configuration."""

        require_private_file(path)
        try:
            return cls.model_validate_json(path.read_bytes())
        except ValidationError as exc:
            fields = ", ".join(
                ".".join(str(part) for part in error["loc"]) for error in exc.errors()
            )
            raise OfflineRegistryConfigurationError(
                f"invalid offline registry configuration fields: {fields}"
            ) from None


def validate_registry_url(value: str) -> str:
    """Validate an explicit HTTPS endpoint or loopback HTTP tunnel endpoint."""

    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise OfflineRegistryConfigurationError("registry URL must use HTTP or HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise OfflineRegistryConfigurationError("registry URL cannot contain credentials or query")
    loopback = parsed.hostname == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        pass
    if parsed.scheme == "http" and not loopback:
        raise OfflineRegistryConfigurationError(
            "non-loopback registry credentials require HTTPS or an SSH loopback tunnel"
        )
    return value.rstrip("/")


def require_private_file(path: Path) -> None:
    """Require a regular owner-only credential/configuration file."""

    metadata = path.stat()
    if not path.is_file() or metadata.st_mode & 0o077 or metadata.st_uid != os.getuid():
        raise OfflineRegistryConfigurationError(f"file must be owner-private (0600): {path}")


def read_private_credential(path: Path) -> str:
    """Read a bearer credential without exposing its content in diagnostics."""

    require_private_file(path)
    credential = path.read_text(encoding="utf-8").strip()
    if len(credential) < 32 or any(character.isspace() for character in credential):
        raise OfflineRegistryConfigurationError(
            "credential must contain at least 32 non-space characters"
        )
    return credential


@contextmanager
def _association_lock(root: Path) -> Iterator[None]:
    """Serialize explicit local registry/store initialization."""

    root.mkdir(parents=True, exist_ok=True)
    with (root / ".offline-mail.lock").open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def associate_registry_store(registry_root: Path, mailbox_root: Path) -> Path:
    """Initialize an association once, or verify an existing matching selection."""

    root = registry_root.resolve()
    store = mailbox_root.resolve()
    with _association_lock(root):
        target = root / "offline-mail.json"
        if target.exists():
            existing = configured_registry_store(root)
            if existing != store:
                raise OfflineRegistryConfigurationError(
                    f"selected mailbox root {store} differs from registry store {existing}; "
                    "select the configured store or another registry"
                )
            return store
        payload = json.dumps({"schema_version": 1, "mailbox_root": str(store)}) + "\n"
        temporary = root / f".offline-mail.{os.getpid()}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return store


def configured_registry_store(registry_root: Path | None = None) -> Path:
    """Load the selected registry's store without creating or changing authority."""

    root = resolve_registry_root(explicit_root=registry_root)
    target = root / "offline-mail.json"
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OfflineRegistryConfigurationError(
            f"registry {root} has no offline store; initialize it with houmao-mgr mailbox init"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise OfflineRegistryConfigurationError("unsupported offline registry configuration")
    value = payload.get("mailbox_root")
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise OfflineRegistryConfigurationError("registry mailbox_root must be an absolute path")
    return Path(value).resolve()


def verify_selected_registry_store(mailbox_root: Path, registry_root: Path | None = None) -> Path:
    """Reject membership mutations against a different maintenance root."""

    selected = mailbox_root.resolve()
    configured = configured_registry_store(registry_root)
    if selected != configured:
        raise OfflineRegistryConfigurationError(
            f"selected mailbox root {selected} differs from registry store {configured}; "
            "select the configured store or explicitly initialize another registry"
        )
    return selected


def validate_registry_listener(host: str, public_url: str) -> None:
    """Require protected public access before binding a non-loopback HTTP listener."""

    loopback = host == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if not loopback and urlsplit(public_url).scheme != "https":
        raise OfflineRegistryConfigurationError(
            "non-loopback registry listener requires an explicit HTTPS public_url and TLS termination"
        )
