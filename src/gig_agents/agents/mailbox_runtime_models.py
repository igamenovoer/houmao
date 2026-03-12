"""Shared mailbox runtime dataclasses used across build and runtime flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

MailboxTransport = Literal["filesystem"]


@dataclass(frozen=True)
class MailboxDeclarativeConfig:
    """Declarative mailbox config carried in recipes and brain manifests."""

    transport: MailboxTransport
    principal_id: str | None = None
    address: str | None = None
    filesystem_root: str | None = None


@dataclass(frozen=True)
class MailboxResolvedConfig:
    """Resolved mailbox binding for one started or resumed session."""

    transport: MailboxTransport
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
