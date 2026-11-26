"""Shared mailbox runtime dataclasses used across build and runtime flows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, TypeAlias
from uuid import uuid4

from houmao.mailbox.stalwart import jmap_origin, normalize_jmap_origins

MailboxTransport = Literal["filesystem", "registry", "stalwart"]
MailboxChannel = Literal["offline", "online"]


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
    trusted_jmap_origins: tuple[str, ...] = ()


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
    agent_id: str
    binding_id: str
    registry_root: Path | None = None
    mailbox_kind: Literal["in_root", "symlink"] = "in_root"
    mailbox_path: Path | None = None

    def __post_init__(self) -> None:
        """Normalize and validate filesystem mailbox binding fields."""

        if self.principal_id != self.agent_id:
            raise ValueError("offline principal_id must equal owning agent_id")
        resolved_root = self.filesystem_root.resolve()
        object.__setattr__(self, "filesystem_root", resolved_root)

        expected_in_root_path = (resolved_root / "mailboxes" / self.address).resolve()
        resolved_mailbox_path = (
            self.mailbox_path.resolve() if self.mailbox_path is not None else expected_in_root_path
        )
        if self.mailbox_kind == "in_root" and resolved_mailbox_path != expected_in_root_path:
            raise ValueError(
                "filesystem in_root mailbox bindings must use the shared-root mailbox path "
                f"`{expected_in_root_path}`"
            )
        if self.mailbox_kind == "symlink" and self.mailbox_path is None:
            raise ValueError("filesystem symlink mailbox bindings require an explicit mailbox_path")
        object.__setattr__(self, "mailbox_path", resolved_mailbox_path)

    def redacted_payload(self) -> dict[str, Any]:
        """Return a secret-free payload suitable for persistence."""

        return {
            "transport": self.transport,
            "principal_id": self.principal_id,
            "address": self.address,
            "filesystem_root": str(self.filesystem_root),
            "bindings_version": self.bindings_version,
            "agent_id": self.agent_id,
            "binding_id": self.binding_id,
            "channel": "offline",
            "registry_root": str(self.registry_root) if self.registry_root is not None else None,
            "mailbox_kind": self.mailbox_kind,
            "mailbox_path": str(self.mailbox_path),
        }


@dataclass(frozen=True)
class StalwartMailboxResolvedConfig:
    """Resolved mailbox binding for one Stalwart-backed session."""

    transport: Literal["stalwart"]
    principal_id: str
    address: str
    jmap_url: str
    management_url: str | None
    login_identity: str
    credential_ref: str
    bindings_version: str
    agent_id: str
    binding_id: str
    credential_file: Path | None = None
    provider: Literal["stalwart"] = "stalwart"
    account_id: str | None = None
    identity_id: str | None = None
    credential_source_ref: str | None = None
    trusted_jmap_origins: tuple[str, ...] = ()
    api_origin: str | None = None

    def __post_init__(self) -> None:
        """Keep the Houmao owner separate from the provider login and account."""

        if self.principal_id != self.agent_id:
            raise ValueError("mailbox principal_id must equal owning agent_id")

    @property
    def pinned_api_origin(self) -> str | None:
        """Resolve the pin, including the implicit origin of validated older bindings."""
        if self.api_origin is not None:
            return normalize_jmap_origins((self.api_origin,))[0]
        if self.account_id is not None and self.identity_id is not None:
            return jmap_origin(self.jmap_url)
        return None

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
            "agent_id": self.agent_id,
            "binding_id": self.binding_id,
            "channel": "online",
            "provider": self.provider,
            "account_id": self.account_id,
            "identity_id": self.identity_id,
            "credential_source_ref": self.credential_source_ref,
            "trusted_jmap_origins": list(self.trusted_jmap_origins),
            "api_origin": self.api_origin,
        }


@dataclass(frozen=True)
class RemoteRegistryMailboxResolvedConfig:
    """Offline binding accessed through its owning registry's member API."""

    transport: Literal["registry"]
    agent_id: str
    binding_id: str
    principal_id: str
    address: str
    bindings_version: str
    registry_url: str
    credential_ref: str
    credential_file: Path | None = None

    def __post_init__(self) -> None:
        """Keep remote member authorization and offline ownership in one scope."""

        if self.principal_id != self.agent_id:
            raise ValueError("offline principal_id must equal owning agent_id")

    def redacted_payload(self) -> dict[str, Any]:
        """Return protected references without copying credential content."""

        return {
            "transport": self.transport,
            "channel": "offline",
            "agent_id": self.agent_id,
            "binding_id": self.binding_id,
            "principal_id": self.principal_id,
            "address": self.address,
            "bindings_version": self.bindings_version,
            "registry_url": self.registry_url,
            "credential_ref": self.credential_ref,
        }


MailboxResolvedConfig: TypeAlias = (
    FilesystemMailboxResolvedConfig
    | RemoteRegistryMailboxResolvedConfig
    | StalwartMailboxResolvedConfig
)


@dataclass(frozen=True)
class MailboxSlotConfig:
    """One revision authority, retained even while its binding is absent."""

    revision: str = field(default_factory=lambda: uuid4().hex)
    binding: MailboxResolvedConfig | None = None

    def __post_init__(self) -> None:
        """Reject blank revisions and stamp the immutable binding snapshot."""

        if not self.revision.strip():
            raise ValueError("mailbox slot revision must not be empty")
        if self.binding is not None:
            if not self.binding.agent_id.strip() or not self.binding.binding_id.strip():
                raise ValueError("mail binding requires agent_id and binding_id")
            object.__setattr__(
                self, "binding", replace(self.binding, bindings_version=self.revision)
            )

    def redacted_payload(self) -> dict[str, Any]:
        """Return the complete revision authority and optional binding."""

        return {
            "revision": self.revision,
            "binding": self.binding.redacted_payload() if self.binding is not None else None,
        }


@dataclass(frozen=True)
class MailboxesResolvedConfig:
    """Independent optional offline and online slots belonging to one agent."""

    offline: MailboxSlotConfig = field(default_factory=MailboxSlotConfig)
    online: MailboxSlotConfig = field(default_factory=MailboxSlotConfig)

    def __post_init__(self) -> None:
        """Enforce channel types and shared stable ownership."""

        if isinstance(self.offline.binding, StalwartMailboxResolvedConfig):
            raise ValueError("offline slot cannot contain an online provider")
        if self.online.binding is not None and not isinstance(
            self.online.binding, StalwartMailboxResolvedConfig
        ):
            raise ValueError("online slot requires an online provider")
        owners = {
            binding.agent_id
            for binding in (self.offline.binding, self.online.binding)
            if binding is not None
        }
        if len(owners) > 1:
            raise ValueError("both mailbox slots must belong to the same agent_id")

    def binding_for(self, channel: MailboxChannel) -> MailboxResolvedConfig | None:
        """Select one explicit channel without fallback."""

        return self.slot_for(channel).binding

    def slot_for(self, channel: MailboxChannel) -> MailboxSlotConfig:
        """Return the requested channel's revision authority."""

        if channel == "offline":
            return self.offline
        if channel == "online":
            return self.online
        raise ValueError(f"unsupported mail channel: {channel!r}")

    @property
    def canonical_mail_identity(self) -> dict[str, str] | None:
        """Derive configured online-first identity independently of health."""

        for channel in ("online", "offline"):
            binding = self.binding_for(channel)
            if binding is not None:
                return {"channel": channel, "address": binding.address}
        return None

    def with_binding(
        self, channel: MailboxChannel, binding: MailboxResolvedConfig | None
    ) -> MailboxesResolvedConfig:
        """Return a new selected slot revision while preserving the other slot."""

        slot = MailboxSlotConfig(binding=binding)
        return replace(self, **{channel: slot})

    def redacted_payload(self) -> dict[str, Any]:
        """Return both slot envelopes without deriving mutable authority."""

        return {
            "offline": self.offline.redacted_payload(),
            "online": self.online.redacted_payload(),
        }


@dataclass(frozen=True)
class MailboxesDeclarativeConfig:
    """Launch configuration for both independent mailbox channels."""

    offline: FilesystemMailboxDeclarativeConfig | None = None
    online: StalwartMailboxDeclarativeConfig | None = None
