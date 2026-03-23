"""Shared mailbox runtime dataclasses used across build and runtime flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeAlias

MailboxTransport = Literal["filesystem", "stalwart"]


@dataclass(frozen=True)
class FilesystemMailboxDeclarativeConfig:
    """Declarative mailbox config for the filesystem transport."""

    transport: Literal["filesystem"]
    principal_id: str | None = None
    address: str | None = None
    filesystem_root: str | None = None


@dataclass(frozen=True)
class StalwartMailboxDeclarativeConfig:
    """Declarative mailbox config for the Stalwart transport."""

    transport: Literal["stalwart"]
    principal_id: str | None = None
    address: str | None = None
    base_url: str | None = None
    jmap_url: str | None = None
    management_url: str | None = None


MailboxDeclarativeConfig: TypeAlias = (
    FilesystemMailboxDeclarativeConfig | StalwartMailboxDeclarativeConfig
)


@dataclass(frozen=True)
class FilesystemMailboxResolvedConfig:
    """Resolved mailbox binding for one filesystem-backed session."""

    transport: Literal["filesystem"]
    principal_id: str
    address: str
    filesystem_root: Path
    bindings_version: str

    def redacted_payload(self) -> dict[str, Any]:
        """Return a secret-free payload suitable for persistence."""

        return {
            "transport": self.transport,
            "principal_id": self.principal_id,
            "address": self.address,
            "filesystem_root": str(self.filesystem_root),
            "bindings_version": self.bindings_version,
        }


@dataclass(frozen=True)
class StalwartMailboxResolvedConfig:
    """Resolved mailbox binding for one Stalwart-backed session."""

    transport: Literal["stalwart"]
    principal_id: str
    address: str
    jmap_url: str
    management_url: str
    login_identity: str
    credential_ref: str
    bindings_version: str
    credential_file: Path | None = None

    def redacted_payload(self) -> dict[str, Any]:
        """Return a secret-free payload suitable for persistence."""

        return {
            "transport": self.transport,
            "principal_id": self.principal_id,
            "address": self.address,
            "jmap_url": self.jmap_url,
            "management_url": self.management_url,
            "login_identity": self.login_identity,
            "credential_ref": self.credential_ref,
            "bindings_version": self.bindings_version,
        }


MailboxResolvedConfig: TypeAlias = FilesystemMailboxResolvedConfig | StalwartMailboxResolvedConfig
