"""Mailbox config resolution and runtime-owned skill projection helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
from pathlib import Path
import os
import re
import sys
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4
from typing import Any, Callable, Literal, Mapping, cast

from houmao.mailbox import (
    MailboxBootstrapError,
    bootstrap_filesystem_mailbox,
    load_active_mailbox_registration,
)
from houmao.mailbox.filesystem import (
    resolve_active_mailbox_dir,
    resolve_active_mailbox_inbox_dir,
    resolve_active_mailbox_local_sqlite_path,
    resolve_filesystem_mailbox_paths,
)
from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox
from houmao.mailbox.protocol import HOUMAO_MAILBOX_DOMAIN, is_houmao_reserved_mailbox_local_part
from houmao.mailbox.stalwart import (
    STALWART_BASE_URL_ENV_VAR,
    StalwartError,
    build_stalwart_credential_ref,
    ensure_stalwart_mailbox,
    jmap_origin,
    normalize_jmap_origins,
    session_stalwart_credential_path,
)
from houmao.owned_paths import resolve_mailbox_root, resolve_registry_root
from houmao.mailbox.registry_config import verify_selected_registry_store
from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GATEWAY_PROTOCOL_VERSION,
    GatewayCurrentInstanceV1,
    GatewayHost,
    GatewayProtocolVersion,
)
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    gateway_paths_from_manifest_path,
    load_gateway_current_instance,
)
from houmao.agents.system_skills import (
    SYSTEM_SKILL_AGENT_ENTRYPOINT,
    SYSTEM_SKILL_PACK_AGENT,
    SYSTEM_SKILL_SHARED_ROUTINES,
    install_system_skills_for_home,
    project_system_skills_to_destination,
    system_skills_destination_for_tool,
)

from .mailbox_runtime_models import (
    FilesystemMailboxDeclarativeConfig,
    FilesystemMailboxResolvedConfig,
    MailboxDeclarativeConfig,
    MailboxResolvedConfig,
    MailboxSlotConfig,
    MailboxesDeclarativeConfig,
    MailboxesResolvedConfig,
    RemoteRegistryMailboxResolvedConfig,
    StalwartMailboxDeclarativeConfig,
    StalwartMailboxResolvedConfig,
)

AGENT_NAMESPACE_PREFIX = "HOUMAO-"
_SANITIZE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_COLLAPSE_DASH_RE = re.compile(r"-{2,}")
_COLLAPSE_UNDERSCORE_RE = re.compile(r"_{2,}")

MAILBOX_TRANSPORT_NONE = "none"
MAILBOX_TRANSPORT_FILESYSTEM = "filesystem"
MAILBOX_TRANSPORT_STALWART = "stalwart"
MAILBOX_PROCESSING_ROUTE_NAME = "process-emails-via-gateway"
MAILBOX_COMMS_ROUTE_NAME = "agent-email-comms"
MAILBOX_AGENT_ENTRYPOINT_NAME = SYSTEM_SKILL_AGENT_ENTRYPOINT
MAILBOX_SHARED_ROUTINES_NAME = SYSTEM_SKILL_SHARED_ROUTINES
MAILBOX_PRIMARY_SKILL_REFERENCES = (
    MAILBOX_AGENT_ENTRYPOINT_NAME,
    MAILBOX_SHARED_ROUTINES_NAME,
)

_MAILBOX_COMMON_ENV_VARS = (
    "HOUMAO_MAILBOX_TRANSPORT",
    "HOUMAO_MAILBOX_PRINCIPAL_ID",
    "HOUMAO_MAILBOX_ADDRESS",
    "HOUMAO_MAILBOX_BINDINGS_VERSION",
)
_MAILBOX_FILESYSTEM_ENV_VARS = (
    "HOUMAO_MAILBOX_FS_ROOT",
    "HOUMAO_MAILBOX_FS_SQLITE_PATH",
    "HOUMAO_MAILBOX_FS_INBOX_DIR",
    "HOUMAO_MAILBOX_FS_MAILBOX_DIR",
    "HOUMAO_MAILBOX_FS_LOCAL_SQLITE_PATH",
)
_MAILBOX_EMAIL_ENV_VARS = (
    "HOUMAO_MAILBOX_EMAIL_JMAP_URL",
    "HOUMAO_MAILBOX_EMAIL_MANAGEMENT_URL",
    "HOUMAO_MAILBOX_EMAIL_LOGIN_IDENTITY",
    "HOUMAO_MAILBOX_EMAIL_CREDENTIAL_REF",
    "HOUMAO_MAILBOX_EMAIL_CREDENTIAL_FILE",
)
MailboxBindingSource = Literal["manifest_binding", "process_env", "tmux_session_env"]
ResolveLiveSource = Literal["auto", "tmux_session_env", "process_env"]
LiveGatewayBindingSource = Literal[
    "process_env",
    "tmux_session_env",
    "current_instance_record",
]
ResolveLiveGatewaySource = Literal[
    "auto",
    "process_env",
    "tmux_session_env",
    "current_instance_record",
]


@dataclass(frozen=True)
class LiveGatewayBindingResolution:
    """Validated live gateway endpoint surfaced through the mailbox resolver."""

    host: GatewayHost
    port: int
    base_url: str
    state_path: Path
    protocol_version: GatewayProtocolVersion
    source: LiveGatewayBindingSource

    def payload(self) -> dict[str, Any]:
        """Return a JSON-safe gateway payload."""

        return {
            "source": self.source,
            "host": self.host,
            "port": self.port,
            "base_url": self.base_url,
            "protocol_version": self.protocol_version,
            "state_path": str(self.state_path.resolve()),
        }


@dataclass(frozen=True)
class LiveMailboxBindingResolution:
    """Normalized live mailbox binding resolved through a runtime-owned helper."""

    mailbox: MailboxResolvedConfig
    source: MailboxBindingSource
    gateway: LiveGatewayBindingResolution | None = None

    def payload(self) -> dict[str, Any]:
        """Return a JSON-safe payload for helper and diagnostic surfaces."""

        mailbox_payload = _structured_live_mailbox_payload(self.mailbox)
        return {
            "source": self.source,
            "transport": self.mailbox.transport,
            "principal_id": self.mailbox.principal_id,
            "address": self.mailbox.address,
            "bindings_version": self.mailbox.bindings_version,
            "mailbox": mailbox_payload,
            "gateway": self.gateway.payload() if self.gateway is not None else None,
        }


@dataclass(frozen=True)
class LiveMailboxesBindingResolution:
    """Manifest-backed summary that preserves each channel independently."""

    mailboxes: MailboxesResolvedConfig
    source: MailboxBindingSource = "manifest_binding"
    gateway: LiveGatewayBindingResolution | None = None

    def payload(self) -> dict[str, Any]:
        """Report configured scope and local availability without credential references."""

        channels: dict[str, Any] = {}
        for channel in ("offline", "online"):
            slot = self.mailboxes.slot_for(channel)
            binding = slot.binding
            summary: dict[str, Any] = {"revision": slot.revision, "binding": None}
            if binding is not None:
                summary["binding"] = {
                    "agent_id": binding.agent_id,
                    "channel": channel,
                    "binding_id": binding.binding_id,
                    "address": binding.address,
                    "transport": binding.transport,
                }
                try:
                    _structured_live_mailbox_payload(binding)
                except (ValueError, OSError, MailboxBootstrapError):
                    summary["availability"] = "unavailable"
                else:
                    summary["availability"] = "configured"
            else:
                summary["availability"] = "absent"
            channels[channel] = summary
        return {
            "source": self.source,
            "mailboxes": channels,
            "canonical_mail_identity": self.mailboxes.canonical_mail_identity,
            "gateway": self.gateway.payload() if self.gateway is not None else None,
        }


def parse_declarative_mailboxes_config(
    payload: object, *, source: str
) -> MailboxesDeclarativeConfig:
    """Parse two explicit launch slots, rejecting the former transport union."""

    if payload is None:
        return MailboxesDeclarativeConfig()
    if not isinstance(payload, dict) or set(payload).difference({"offline", "online"}):
        raise ValueError(f"{source}: expected offline/online mailboxes mapping")
    offline = parse_declarative_mailbox_config(payload.get("offline"), source=f"{source}.offline")
    online = parse_declarative_mailbox_config(payload.get("online"), source=f"{source}.online")
    if offline is not None and not isinstance(offline, FilesystemMailboxDeclarativeConfig):
        raise ValueError(f"{source}.offline requires a filesystem mailbox")
    if online is not None and not isinstance(online, StalwartMailboxDeclarativeConfig):
        raise ValueError(f"{source}.online requires an online provider")
    return MailboxesDeclarativeConfig(offline=offline, online=online)


def serialize_declarative_mailboxes_config(config: MailboxesDeclarativeConfig) -> dict[str, Any]:
    """Serialize independent launch slots without selecting a preferred channel."""

    return {
        "offline": serialize_declarative_mailbox_config(config.offline) if config.offline else None,
        "online": serialize_declarative_mailbox_config(config.online) if config.online else None,
    }


def mailboxes_resolved_config_from_payload(
    payload: object, *, manifest_path: Path | None = None
) -> MailboxesResolvedConfig:
    """Decode both required slot envelopes, including empty revision authority."""

    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict) or set(payload) != {"offline", "online"}:
        raise ValueError("persisted mailboxes require offline and online slot envelopes")
    slots: dict[str, MailboxSlotConfig] = {}
    for channel in ("offline", "online"):
        raw_slot = payload[channel]
        if not isinstance(raw_slot, dict) or set(raw_slot) != {"revision", "binding"}:
            raise ValueError(f"persisted {channel} slot requires revision and binding")
        revision = _require_optional_non_blank_str(raw_slot["revision"], field="slot.revision")
        if revision is None:
            raise ValueError("persisted mailbox slot revision is required")
        binding = resolved_mailbox_config_from_payload(
            raw_slot["binding"], manifest_path=manifest_path
        )
        if binding is not None and binding.bindings_version != revision:
            raise ValueError("mailbox binding revision differs from its slot authority")
        slots[channel] = MailboxSlotConfig(revision=revision, binding=binding)
    return MailboxesResolvedConfig(offline=slots["offline"], online=slots["online"])


def safe_registry_mailboxes_projection(mailboxes: MailboxesResolvedConfig) -> dict[str, Any]:
    """Project channel identity without credential references or private backend paths."""

    result: dict[str, Any] = {}
    for channel in ("offline", "online"):
        slot = mailboxes.slot_for(channel)
        binding = slot.binding
        result[channel] = {
            "revision": slot.revision,
            "binding": None
            if binding is None
            else {
                "agent_id": binding.agent_id,
                "channel": channel,
                "binding_id": binding.binding_id,
                "address": binding.address,
                "transport": binding.transport,
                "availability": "unknown",
            },
        }
    return result


def parse_declarative_mailbox_config(
    payload: object,
    *,
    source: str,
) -> MailboxDeclarativeConfig | None:
    """Parse a declarative mailbox configuration payload."""

    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError(f"{source}: mailbox must be a mapping when present")

    transport = _require_optional_non_blank_str(
        payload.get("transport"),
        field=f"{source}.transport",
    )
    if transport is None:
        raise ValueError(f"{source}: mailbox.transport is required when mailbox is present")

    principal_id = _require_optional_non_blank_str(
        payload.get("principal_id"),
        field=f"{source}.principal_id",
    )
    address = _require_optional_non_blank_str(
        payload.get("address"),
        field=f"{source}.address",
    )
    if transport == MAILBOX_TRANSPORT_NONE:
        return None

    if transport == MAILBOX_TRANSPORT_FILESYSTEM:
        filesystem_root = _require_optional_non_blank_str(
            payload.get("filesystem_root"),
            field=f"{source}.filesystem_root",
        )
        return FilesystemMailboxDeclarativeConfig(
            transport="filesystem",
            principal_id=principal_id,
            address=address,
            filesystem_root=filesystem_root,
        )

    if transport == MAILBOX_TRANSPORT_STALWART:
        base_url = _require_optional_non_blank_str(
            payload.get("base_url"),
            field=f"{source}.base_url",
        )
        jmap_url = _require_optional_non_blank_str(
            payload.get("jmap_url"),
            field=f"{source}.jmap_url",
        )
        management_url = _require_optional_non_blank_str(
            payload.get("management_url"),
            field=f"{source}.management_url",
        )
        return StalwartMailboxDeclarativeConfig(
            transport="stalwart",
            principal_id=principal_id,
            address=address,
            base_url=base_url,
            jmap_url=jmap_url,
            management_url=management_url,
            trusted_jmap_origins=_parse_trusted_jmap_origins(payload, source=source),
        )

    raise ValueError(
        f"{source}: unsupported mailbox.transport {transport!r}; expected one of "
        f"{MAILBOX_TRANSPORT_FILESYSTEM!r}, {MAILBOX_TRANSPORT_STALWART!r}, or "
        f"{MAILBOX_TRANSPORT_NONE!r}"
    )


def serialize_declarative_mailbox_config(config: MailboxDeclarativeConfig) -> dict[str, Any]:
    """Serialize a declarative mailbox config for manifest persistence."""

    payload: dict[str, Any] = {"transport": config.transport}
    if config.principal_id is not None:
        payload["principal_id"] = config.principal_id
    if config.address is not None:
        payload["address"] = config.address
    if isinstance(config, FilesystemMailboxDeclarativeConfig):
        if config.filesystem_root is not None:
            payload["filesystem_root"] = config.filesystem_root
        return payload

    if config.base_url is not None:
        payload["base_url"] = config.base_url
    if config.jmap_url is not None:
        payload["jmap_url"] = config.jmap_url
    if config.management_url is not None:
        payload["management_url"] = config.management_url
    if config.trusted_jmap_origins:
        payload["trusted_jmap_origins"] = list(config.trusted_jmap_origins)
    return payload


def resolved_mailbox_config_from_payload(
    payload: object,
    *,
    manifest_path: Path | None = None,
) -> MailboxResolvedConfig | None:
    """Convert a persisted launch-plan mailbox payload back into a dataclass."""

    if payload is None:
        return None
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict):
        raise ValueError("persisted mailbox payload must be a mapping")

    transport = _require_optional_non_blank_str(
        payload.get("transport"),
        field="launch_plan.mailbox.transport",
    )
    principal_id = _require_optional_non_blank_str(
        payload.get("principal_id"),
        field="launch_plan.mailbox.principal_id",
    )
    address = _require_optional_non_blank_str(
        payload.get("address"),
        field="launch_plan.mailbox.address",
    )
    bindings_version = _require_optional_non_blank_str(
        payload.get("bindings_version"),
        field="launch_plan.mailbox.bindings_version",
    )
    if None in {transport, principal_id, address, bindings_version}:
        raise ValueError("persisted mailbox payload is missing required common fields")

    assert transport is not None
    assert principal_id is not None
    assert address is not None
    assert bindings_version is not None
    expected_channel = "online" if transport == "stalwart" else "offline"
    if payload.get("channel") != expected_channel:
        raise ValueError("persisted mailbox channel differs from its backend transport")
    if transport == "stalwart" and payload.get("provider") != "stalwart":
        raise ValueError("persisted online mailbox requires its explicit provider")
    agent_id = _require_optional_non_blank_str(payload.get("agent_id"), field="mailbox.agent_id")
    binding_id = _require_optional_non_blank_str(
        payload.get("binding_id"), field="mailbox.binding_id"
    )
    if agent_id is None or binding_id is None:
        raise ValueError("persisted mailbox requires agent_id and binding_id")

    if transport == MAILBOX_TRANSPORT_FILESYSTEM:
        filesystem_root = _require_optional_non_blank_str(
            payload.get("filesystem_root"),
            field="launch_plan.mailbox.filesystem_root",
        )
        if filesystem_root is None:
            raise ValueError("persisted filesystem mailbox payload is missing filesystem_root")
        mailbox_kind = _require_optional_non_blank_str(
            payload.get("mailbox_kind"),
            field="launch_plan.mailbox.mailbox_kind",
        )
        mailbox_path = _require_optional_non_blank_str(
            payload.get("mailbox_path"),
            field="launch_plan.mailbox.mailbox_path",
        )
        return FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id=principal_id,
            address=address,
            filesystem_root=Path(filesystem_root).resolve(),
            bindings_version=bindings_version,
            agent_id=agent_id,
            binding_id=binding_id,
            registry_root=(
                Path(payload["registry_root"]) if payload.get("registry_root") else None
            ),
            mailbox_kind=cast(Literal["in_root", "symlink"], mailbox_kind or "in_root"),
            mailbox_path=None if mailbox_path is None else Path(mailbox_path).resolve(),
        )

    if transport == MAILBOX_TRANSPORT_STALWART:
        jmap_url = _require_optional_non_blank_str(
            payload.get("jmap_url"),
            field="launch_plan.mailbox.jmap_url",
        )
        management_url = _require_optional_non_blank_str(
            payload.get("management_url"),
            field="launch_plan.mailbox.management_url",
        )
        login_identity = _require_optional_non_blank_str(
            payload.get("login_identity"),
            field="launch_plan.mailbox.login_identity",
        )
        credential_ref = _require_optional_non_blank_str(
            payload.get("credential_ref"),
            field="launch_plan.mailbox.credential_ref",
        )
        if None in {jmap_url, login_identity, credential_ref}:
            raise ValueError("persisted stalwart mailbox payload is missing required fields")
        credential_file = _resolved_stalwart_credential_file(
            manifest_path=manifest_path,
            credential_ref=cast(str, credential_ref),
        )
        return StalwartMailboxResolvedConfig(
            transport="stalwart",
            principal_id=principal_id,
            address=address,
            jmap_url=cast(str, jmap_url),
            management_url=management_url,
            login_identity=cast(str, login_identity),
            credential_ref=cast(str, credential_ref),
            bindings_version=bindings_version,
            agent_id=agent_id,
            binding_id=binding_id,
            credential_file=credential_file,
            account_id=payload.get("account_id"),
            identity_id=payload.get("identity_id"),
            credential_source_ref=payload.get("credential_source_ref"),
            trusted_jmap_origins=_parse_trusted_jmap_origins(
                payload, source="launch_plan.mailboxes.online"
            ),
            api_origin=payload.get("api_origin"),
        )

    if transport == "registry":
        registry_url = _require_optional_non_blank_str(
            payload.get("registry_url"), field="mailbox.registry_url"
        )
        credential_ref = _require_optional_non_blank_str(
            payload.get("credential_ref"), field="mailbox.credential_ref"
        )
        if registry_url is None or credential_ref is None:
            raise ValueError("remote offline binding requires registry_url and credential_ref")
        return RemoteRegistryMailboxResolvedConfig(
            transport="registry",
            agent_id=agent_id,
            binding_id=binding_id,
            principal_id=principal_id,
            address=address,
            bindings_version=bindings_version,
            registry_url=registry_url,
            credential_ref=credential_ref,
            credential_file=Path(credential_ref).expanduser().resolve()
            if Path(credential_ref).is_absolute()
            else None,
        )

    raise ValueError(f"unsupported persisted mailbox transport {transport!r}")


def resolve_effective_mailbox_config(
    *,
    declared_config: MailboxDeclarativeConfig | None,
    runtime_root: Path,
    tool: str,
    role_name: str,
    agent_identity: str | None = None,
    agent_id: str,
    transport_override: str | None = None,
    filesystem_root_override: Path | None = None,
    filesystem_account_dir_override: Path | None = None,
    principal_id_override: str | None = None,
    address_override: str | None = None,
    stalwart_base_url_override: str | None = None,
    stalwart_jmap_url_override: str | None = None,
    stalwart_management_url_override: str | None = None,
    stalwart_login_identity_override: str | None = None,
) -> MailboxResolvedConfig | None:
    """Resolve one effective mailbox configuration for a started session."""

    transport = transport_override or (
        declared_config.transport if declared_config is not None else None
    )
    if transport is None or transport == MAILBOX_TRANSPORT_NONE:
        return None

    principal_id = principal_id_override or (
        declared_config.principal_id if declared_config is not None else None
    )
    if principal_id is None:
        principal_id = agent_id
    if principal_id != agent_id:
        raise ValueError("mailbox principal_id must equal the persisted owning agent_id")

    address = address_override or (declared_config.address if declared_config is not None else None)
    if address is None:
        address = default_mailbox_address(
            tool=tool,
            role_name=role_name,
            agent_identity=agent_identity,
        )

    if transport == MAILBOX_TRANSPORT_FILESYSTEM:
        declared_root = _resolve_declared_mailbox_root(
            declared_root=(
                declared_config.filesystem_root
                if isinstance(declared_config, FilesystemMailboxDeclarativeConfig)
                else None
            ),
            runtime_root=runtime_root,
        )
        filesystem_root = resolve_mailbox_root(
            explicit_root=filesystem_root_override or declared_root,
        )
        mailbox_paths = resolve_filesystem_mailbox_paths(filesystem_root)
        mailbox_account_dir = (
            filesystem_account_dir_override.resolve()
            if filesystem_account_dir_override is not None
            else None
        )
        return FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id=principal_id,
            address=address,
            filesystem_root=filesystem_root.resolve(),
            bindings_version=mailbox_bindings_version_now(),
            agent_id=agent_id,
            binding_id=uuid4().hex,
            registry_root=resolve_registry_root(),
            mailbox_kind="symlink" if mailbox_account_dir is not None else "in_root",
            mailbox_path=(
                mailbox_account_dir
                if mailbox_account_dir is not None
                else mailbox_paths.mailbox_entry_path(address)
            ),
        )

    if transport == MAILBOX_TRANSPORT_STALWART:
        stalwart_config = (
            declared_config
            if isinstance(declared_config, StalwartMailboxDeclarativeConfig)
            else None
        )
        _, jmap_url, management_url = _resolve_stalwart_endpoints(
            declared_config=stalwart_config,
            base_url_override=stalwart_base_url_override,
            jmap_url_override=stalwart_jmap_url_override,
            management_url_override=stalwart_management_url_override,
        )
        login_identity = stalwart_login_identity_override or principal_id
        return StalwartMailboxResolvedConfig(
            transport="stalwart",
            principal_id=principal_id,
            address=address,
            jmap_url=jmap_url,
            management_url=management_url,
            login_identity=login_identity,
            credential_ref=build_stalwart_credential_ref(address=address, jmap_url=jmap_url),
            bindings_version=mailbox_bindings_version_now(),
            agent_id=agent_id,
            binding_id=uuid4().hex,
            credential_file=None,
            trusted_jmap_origins=(
                stalwart_config.trusted_jmap_origins if stalwart_config is not None else ()
            ),
        )

    raise ValueError(
        f"unsupported mailbox transport {transport!r}; expected one of "
        f"{MAILBOX_TRANSPORT_FILESYSTEM!r} or {MAILBOX_TRANSPORT_STALWART!r}"
    )


def resolve_effective_mailboxes_config(
    *,
    declared_config: MailboxesDeclarativeConfig,
    agent_id: str,
    runtime_root: Path,
    tool: str,
    role_name: str,
    agent_identity: str | None = None,
    manifest_path_hint: Path | None = None,
    offline_overrides: dict[str, Any] | None = None,
    online_overrides: dict[str, Any] | None = None,
) -> MailboxesResolvedConfig:
    """Resolve and prepare both launch slots before publishing runtime authority.

    Each override mapping contains backend resolver keyword arguments. Channel
    types are checked after resolution; neither slot selects or replaces the other.
    """

    resolved: dict[str, MailboxSlotConfig] = {}
    for channel, declaration, overrides in (
        ("offline", declared_config.offline, offline_overrides),
        ("online", declared_config.online, online_overrides),
    ):
        binding = resolve_effective_mailbox_config(
            declared_config=declaration,
            agent_id=agent_id,
            runtime_root=runtime_root,
            tool=tool,
            role_name=role_name,
            agent_identity=agent_identity,
            **(overrides or {}),
        )
        if binding is not None:
            binding = bootstrap_resolved_mailbox(
                binding, manifest_path_hint=manifest_path_hint, role_name=role_name
            )
        resolved[channel] = MailboxSlotConfig(binding=binding)
    return MailboxesResolvedConfig(offline=resolved["offline"], online=resolved["online"])


def refresh_filesystem_mailbox_config(
    config: FilesystemMailboxResolvedConfig,
    *,
    filesystem_root: Path | None = None,
) -> FilesystemMailboxResolvedConfig:
    """Return an updated filesystem mailbox binding with a fresh version stamp."""

    next_root = (filesystem_root or config.filesystem_root).resolve()
    next_mailbox_path = (
        config.mailbox_path
        if config.mailbox_kind == "symlink"
        else resolve_filesystem_mailbox_paths(next_root).mailbox_entry_path(config.address)
    )
    return FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id=config.principal_id,
        address=config.address,
        filesystem_root=next_root,
        bindings_version=mailbox_bindings_version_now(),
        agent_id=config.agent_id,
        binding_id=config.binding_id,
        registry_root=config.registry_root,
        mailbox_kind=config.mailbox_kind,
        mailbox_path=next_mailbox_path,
    )


def default_mailbox_principal_id(
    *,
    tool: str,
    role_name: str,
    agent_identity: str | None,
) -> str:
    """Return the default mailbox principal id for a session."""

    if agent_identity is not None and agent_identity.strip():
        if _is_path_like_agent_identity(agent_identity):
            return (
                f"{AGENT_NAMESPACE_PREFIX}"
                f"{_derive_auto_agent_name_base(tool=tool, role_name=role_name)}"
            )
        stripped = agent_identity.strip()
        return (
            stripped
            if stripped.startswith(AGENT_NAMESPACE_PREFIX)
            else f"{AGENT_NAMESPACE_PREFIX}{stripped}"
        )
    base = _derive_auto_agent_name_base(tool=tool, role_name=role_name)
    return f"{AGENT_NAMESPACE_PREFIX}{base}"


def default_mailbox_address(
    *,
    tool: str,
    role_name: str,
    agent_identity: str | None,
) -> str:
    """Return the default mailbox address for one session."""

    local_part = _derive_default_mailbox_local_part(
        tool=tool,
        role_name=role_name,
        agent_identity=agent_identity,
    )
    return f"{local_part}@{HOUMAO_MAILBOX_DOMAIN}"


def mailbox_bindings_version_now() -> str:
    """Return a monotonic-enough timestamp label for mailbox bindings."""

    return (
        datetime.now(UTC)
        .replace(tzinfo=UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def replaceable_mailbox_cleanup_paths(config: MailboxResolvedConfig | None) -> tuple[Path, ...]:
    """Return mailbox artifacts that are safe to remove during force-clean takeover."""

    if config is None:
        return ()
    if isinstance(config, FilesystemMailboxResolvedConfig):
        if config.mailbox_kind != "symlink":
            return ()
        mailbox_path = config.mailbox_path
        if mailbox_path is None:
            return ()
        return (mailbox_path.resolve(),)
    if config.credential_file is None:
        return ()
    return (config.credential_file.resolve(),)


def mailbox_env_bindings(config: MailboxResolvedConfig) -> dict[str, str]:
    """Return runtime-managed mailbox env bindings for a resolved config."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        mailbox_root = config.filesystem_root.resolve()
        mailbox_dir = resolve_active_mailbox_dir(mailbox_root, address=config.address)
        if mailbox_dir.resolve() != config.mailbox_path:
            raise ValueError(
                "filesystem mailbox binding does not match the active mailbox registration "
                f"for `{config.address}`: expected `{config.mailbox_path}`, found `{mailbox_dir}`"
            )
        inbox_dir = resolve_active_mailbox_inbox_dir(mailbox_root, address=config.address)
        local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
            mailbox_root, address=config.address
        )
        return {
            "HOUMAO_MAILBOX_TRANSPORT": config.transport,
            "HOUMAO_MAILBOX_PRINCIPAL_ID": config.principal_id,
            "HOUMAO_MAILBOX_ADDRESS": config.address,
            "HOUMAO_MAILBOX_BINDINGS_VERSION": config.bindings_version,
            "HOUMAO_MAILBOX_FS_ROOT": str(mailbox_root),
            "HOUMAO_MAILBOX_FS_SQLITE_PATH": str(mailbox_root / "index.sqlite"),
            "HOUMAO_MAILBOX_FS_INBOX_DIR": str(inbox_dir),
            "HOUMAO_MAILBOX_FS_MAILBOX_DIR": str(mailbox_dir),
            "HOUMAO_MAILBOX_FS_LOCAL_SQLITE_PATH": str(local_sqlite_path),
        }

    if isinstance(config, RemoteRegistryMailboxResolvedConfig):
        return {
            "HOUMAO_MAILBOX_TRANSPORT": config.transport,
            "HOUMAO_MAILBOX_PRINCIPAL_ID": config.principal_id,
            "HOUMAO_MAILBOX_ADDRESS": config.address,
            "HOUMAO_MAILBOX_BINDINGS_VERSION": config.bindings_version,
            "HOUMAO_MAILBOX_REGISTRY_URL": config.registry_url,
        }
    credential_file = config.credential_file
    if credential_file is None:
        raise ValueError(
            "stalwart mailbox env bindings require a materialized credential file for this session"
        )
    return {
        "HOUMAO_MAILBOX_TRANSPORT": config.transport,
        "HOUMAO_MAILBOX_PRINCIPAL_ID": config.principal_id,
        "HOUMAO_MAILBOX_ADDRESS": config.address,
        "HOUMAO_MAILBOX_BINDINGS_VERSION": config.bindings_version,
        "HOUMAO_MAILBOX_EMAIL_JMAP_URL": config.jmap_url,
        **(
            {"HOUMAO_MAILBOX_EMAIL_MANAGEMENT_URL": config.management_url}
            if config.management_url is not None
            else {}
        ),
        "HOUMAO_MAILBOX_EMAIL_LOGIN_IDENTITY": config.login_identity,
        "HOUMAO_MAILBOX_EMAIL_CREDENTIAL_REF": config.credential_ref,
        "HOUMAO_MAILBOX_EMAIL_CREDENTIAL_FILE": str(credential_file.resolve()),
    }


def mailbox_env_var_names(config: MailboxResolvedConfig) -> tuple[str, ...]:
    """Return the runtime-owned env var names populated for the mailbox."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        return (*_MAILBOX_COMMON_ENV_VARS, *_MAILBOX_FILESYSTEM_ENV_VARS)
    if isinstance(config, RemoteRegistryMailboxResolvedConfig):
        return (*_MAILBOX_COMMON_ENV_VARS, "HOUMAO_MAILBOX_REGISTRY_URL")
    return (*_MAILBOX_COMMON_ENV_VARS, *_MAILBOX_EMAIL_ENV_VARS)


def resolve_live_mailbox_binding(
    *,
    durable_mailbox: MailboxResolvedConfig,
    tmux_session_name: str | None = None,
    source: MailboxBindingSource = "manifest_binding",
    env_reader: Callable[[str], str | None] | None = None,
) -> LiveMailboxBindingResolution:
    """Resolve actionable mailbox state from the durable manifest-backed binding."""

    del tmux_session_name, env_reader
    _structured_live_mailbox_payload(durable_mailbox)
    return LiveMailboxBindingResolution(mailbox=durable_mailbox, source=source)


def resolve_live_mailbox_binding_from_manifest_path(
    *,
    manifest_path: Path,
    source: ResolveLiveSource = "auto",
    process_env_reader: Callable[[str], str | None] | None = None,
    tmux_env_reader: Callable[[str], str | None] | None = None,
    gateway_client_factory: Callable[[GatewayEndpoint], Any] | None = None,
    gateway_source: ResolveLiveGatewaySource | None = None,
) -> LiveMailboxesBindingResolution:
    """Resolve both mailbox slots starting from a runtime-owned manifest path."""
    handle, mailboxes, tmux_session_name = _load_live_mailbox_manifest_context(manifest_path)
    resolved_gateway = resolve_live_gateway_binding_from_manifest_path(
        manifest_path=handle.path,
        tmux_session_name=tmux_session_name,
        source=(gateway_source if gateway_source is not None else "current_instance_record"),
        process_env_reader=process_env_reader,
        tmux_env_reader=tmux_env_reader,
        gateway_client_factory=gateway_client_factory,
    )
    return LiveMailboxesBindingResolution(
        mailboxes=mailboxes,
        gateway=resolved_gateway,
    )


def resolve_live_mailbox_binding_from_agent_identity(
    *,
    agent_identity: str,
    source: ResolveLiveSource = "auto",
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    process_env_reader: Callable[[str], str | None] | None = None,
    tmux_env_reader: Callable[[str], str | None] | None = None,
    gateway_client_factory: Callable[[GatewayEndpoint], Any] | None = None,
) -> LiveMailboxesBindingResolution:
    """Resolve both mailbox slots through shared-registry manifest discovery."""

    manifest_path = _resolve_manifest_path_from_agent_identity(
        agent_identity=agent_identity,
        env=env,
        now=now,
    )
    return resolve_live_mailbox_binding_from_manifest_path(
        manifest_path=manifest_path,
        source=source,
        process_env_reader=process_env_reader,
        tmux_env_reader=tmux_env_reader,
        gateway_client_factory=gateway_client_factory,
        gateway_source="current_instance_record",
    )


def _structured_live_mailbox_payload(mailbox: MailboxResolvedConfig) -> dict[str, Any]:
    """Return one structured, actionable mailbox payload derived from the durable binding."""

    if isinstance(mailbox, FilesystemMailboxResolvedConfig):
        mailbox_root = mailbox.filesystem_root.resolve()
        try:
            registration = load_active_mailbox_registration(mailbox_root, address=mailbox.address)
        except MailboxBootstrapError as exc:
            raise ValueError(str(exc)) from exc
        if (
            registration.owner_principal_id != mailbox.agent_id
            or registration.registration_id != mailbox.binding_id
        ):
            raise ValueError("offline registration owner or binding identity differs from manifest")
        try:
            mailbox_dir = resolve_active_mailbox_dir(
                mailbox_root, address=mailbox.address
            ).resolve()
            inbox_dir = resolve_active_mailbox_inbox_dir(
                mailbox_root, address=mailbox.address
            ).resolve()
            local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
                mailbox_root,
                address=mailbox.address,
            ).resolve()
        except MailboxBootstrapError as exc:
            raise ValueError(str(exc)) from exc
        if mailbox_dir != mailbox.mailbox_path:
            raise ValueError(
                "manifest-backed filesystem mailbox binding does not match the current active "
                f"mailbox registration for `{mailbox.address}`: expected `{mailbox.mailbox_path}`, "
                f"found `{mailbox_dir}`"
            )
        return {
            "transport": mailbox.transport,
            "principal_id": mailbox.principal_id,
            "address": mailbox.address,
            "bindings_version": mailbox.bindings_version,
            "filesystem": {
                "root": str(mailbox_root),
                "mailbox_kind": mailbox.mailbox_kind,
                "mailbox_path": str(mailbox_dir),
                "inbox_path": str(inbox_dir),
                "sqlite_path": str((mailbox_root / "index.sqlite").resolve()),
                "local_sqlite_path": str(local_sqlite_path),
            },
        }

    if isinstance(mailbox, RemoteRegistryMailboxResolvedConfig):
        return {
            "transport": "registry",
            "agent_id": mailbox.agent_id,
            "binding_id": mailbox.binding_id,
            "principal_id": mailbox.principal_id,
            "address": mailbox.address,
            "bindings_version": mailbox.bindings_version,
            "registry_url": mailbox.registry_url,
        }

    credential_file = mailbox.credential_file
    if credential_file is None or not credential_file.is_file():
        raise ValueError(
            "stalwart mailbox binding is missing the session credential file required for "
            "current mailbox work"
        )
    return {
        "transport": mailbox.transport,
        "principal_id": mailbox.principal_id,
        "address": mailbox.address,
        "bindings_version": mailbox.bindings_version,
        "stalwart": {
            "jmap_url": mailbox.jmap_url,
            "management_url": mailbox.management_url,
            "login_identity": mailbox.login_identity,
            "credential_ref": mailbox.credential_ref,
            "credential_file": str(credential_file.resolve()),
        },
    }


def resolve_live_gateway_binding_from_manifest_path(
    *,
    manifest_path: Path,
    tmux_session_name: str | None,
    source: ResolveLiveGatewaySource = "auto",
    process_env_reader: Callable[[str], str | None] | None = None,
    tmux_env_reader: Callable[[str], str | None] | None = None,
    gateway_client_factory: Callable[[GatewayEndpoint], Any] | None = None,
) -> LiveGatewayBindingResolution | None:
    """Resolve an attached live gateway endpoint from one runtime-owned manifest path."""

    paths = gateway_paths_from_manifest_path(manifest_path.resolve())
    if paths is None:
        return None
    current_instance = _load_optional_gateway_current_instance(paths.current_instance_path)
    if current_instance is None:
        return None

    sources: tuple[ResolveLiveGatewaySource, ...]
    if source == "auto":
        sources = ("process_env", "tmux_session_env")
    else:
        sources = (source,)
    for candidate_source in sources:
        if candidate_source == "current_instance_record":
            return _resolve_gateway_from_current_instance_record(
                current_instance=current_instance,
                state_path=paths.state_path,
                gateway_client_factory=gateway_client_factory,
            )
        if candidate_source == "process_env":
            resolved = _resolve_gateway_from_env_reader(
                source="process_env",
                env_reader=process_env_reader or _optional_env,
                current_instance=current_instance,
                state_path=paths.state_path,
                gateway_client_factory=gateway_client_factory,
            )
            if resolved is not None:
                return resolved
            continue
        if tmux_session_name is None or not tmux_session_name.strip():
            continue
        resolved = _resolve_gateway_from_env_reader(
            source="tmux_session_env",
            env_reader=tmux_env_reader or _tmux_mailbox_env_reader(tmux_session_name.strip()),
            current_instance=current_instance,
            state_path=paths.state_path,
            gateway_client_factory=gateway_client_factory,
        )
        if resolved is not None:
            return resolved
    return None


def publish_tmux_live_mailbox_projection(
    *,
    session_name: str,
    previous_mailbox: MailboxResolvedConfig | None,
    mailbox: MailboxResolvedConfig | None,
    set_env: Callable[[str, dict[str, str]], None],
    unset_env: Callable[[str, list[str]], None],
) -> None:
    """Refresh targeted mailbox vars in one tmux session environment."""

    if not session_name.strip():
        raise ValueError("tmux-backed live mailbox projection requires a non-empty session name")

    previous_names = (
        set(mailbox_env_var_names(previous_mailbox)) if previous_mailbox is not None else set()
    )
    next_bindings = mailbox_env_bindings(mailbox) if mailbox is not None else {}
    if next_bindings:
        set_env(session_name.strip(), dict(next_bindings))
    stale_names = sorted(previous_names.difference(next_bindings))
    if stale_names:
        unset_env(session_name.strip(), stale_names)


def bootstrap_resolved_mailbox(
    config: MailboxResolvedConfig,
    *,
    manifest_path_hint: Path | None,
    role_name: str,
) -> MailboxResolvedConfig:
    """Bootstrap or materialize one resolved mailbox binding for a session."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        resolved_root = config.filesystem_root.resolve()
        verify_selected_registry_store(resolved_root, registry_root=config.registry_root)
        mailbox_path = config.mailbox_path
        assert mailbox_path is not None
        if config.mailbox_kind == "symlink":
            try:
                mailbox_path.relative_to(resolved_root)
            except ValueError:
                pass
            else:
                raise ValueError(
                    "filesystem private mailbox directory must live outside the shared mailbox root"
                )
        bootstrap_filesystem_mailbox(resolved_root)
        registration = register_mailbox(
            resolved_root,
            RegisterMailboxRequest(
                mode="safe",
                address=config.address,
                owner_principal_id=config.principal_id,
                mailbox_kind=config.mailbox_kind,
                mailbox_path=mailbox_path,
                manifest_path_hint=(
                    str(manifest_path_hint.resolve()) if manifest_path_hint is not None else None
                ),
                role=role_name,
            ),
        )
        return replace(config, binding_id=str(registration["active_registration_id"]))

    if isinstance(config, RemoteRegistryMailboxResolvedConfig):
        return config
    if manifest_path_hint is None:
        raise ValueError(
            "stalwart mailbox bootstrap requires a runtime-owned session manifest path"
        )
    session_root = manifest_path_hint.resolve().parent
    runtime_root = _runtime_root_from_session_root(session_root)
    if config.management_url is None:
        return config
    binding = ensure_stalwart_mailbox(
        runtime_root=runtime_root,
        session_root=session_root,
        principal_id=config.principal_id,
        address=config.address,
        jmap_url=config.jmap_url,
        management_url=config.management_url,
        login_identity=config.login_identity,
        trusted_jmap_origins=config.trusted_jmap_origins,
    )
    return replace(
        config,
        jmap_url=binding.jmap_url,
        management_url=binding.management_url,
        login_identity=binding.login_identity,
        credential_ref=binding.credential_ref,
        credential_file=binding.credential_file,
        account_id=binding.account_id,
        identity_id=binding.identity_id,
        api_origin=binding.api_origin,
        bindings_version=mailbox_bindings_version_now(),
    )


def mailbox_skill_reference(config: MailboxResolvedConfig, *, tool: str | None = None) -> str:
    """Return the public managed-agent entrypoint reference for mailbox work."""

    del config
    return _mailbox_entrypoint_reference(tool=tool)


def mailbox_skill_name(config: MailboxResolvedConfig) -> str:
    """Return the public entrypoint name used for ordinary mailbox work."""

    del config
    return MAILBOX_AGENT_ENTRYPOINT_NAME


def mailbox_gateway_skill_reference(*, tool: str | None = None) -> str:
    """Return the public entrypoint reference for ordinary mailbox work."""

    return _mailbox_entrypoint_reference(tool=tool)


def mailbox_processing_skill_reference(*, tool: str | None = None) -> str:
    """Return the public entrypoint reference for notifier mail rounds."""

    return _mailbox_entrypoint_reference(tool=tool)


def mailbox_shared_skill_reference(*, tool: str | None = None) -> str:
    """Return the required public shared-routines sibling reference."""

    if tool is not None:
        system_skills_destination_for_tool(tool)
    return MAILBOX_SHARED_ROUTINES_NAME


def mailbox_gateway_skill_name() -> str:
    """Return the public entrypoint name for ordinary mailbox work."""

    return MAILBOX_AGENT_ENTRYPOINT_NAME


def mailbox_processing_skill_name() -> str:
    """Return the public entrypoint name for notifier mail rounds."""

    return MAILBOX_AGENT_ENTRYPOINT_NAME


def mailbox_gateway_route_name() -> str:
    """Return the parent-scoped ordinary-mailbox route argument."""

    return MAILBOX_COMMS_ROUTE_NAME


def mailbox_processing_route_name() -> str:
    """Return the parent-scoped notifier-round route argument."""

    return MAILBOX_PROCESSING_ROUTE_NAME


def mailbox_skill_document_path(
    config: MailboxResolvedConfig,
    *,
    skills_destination: str = "skills",
    tool: str | None = None,
) -> str:
    """Return the primary mailbox skill document path for the active skill destination."""

    return f"{skills_destination}/{mailbox_skill_reference(config, tool=tool)}/SKILL.md"


def mailbox_gateway_skill_document_path(
    *,
    skills_destination: str = "skills",
    tool: str | None = None,
) -> str:
    """Return the primary gateway mailbox skill document path."""

    return f"{skills_destination}/{mailbox_gateway_skill_reference(tool=tool)}/SKILL.md"


def mailbox_processing_skill_document_path(
    *,
    skills_destination: str = "skills",
    tool: str | None = None,
) -> str:
    """Return the primary gateway email-processing skill document path."""

    return f"{skills_destination}/{mailbox_processing_skill_reference(tool=tool)}/SKILL.md"


def mailbox_shared_skill_document_path(
    *,
    skills_destination: str = "skills",
    tool: str | None = None,
) -> str:
    """Return the required shared-routines sibling document path."""

    return f"{skills_destination}/{mailbox_shared_skill_reference(tool=tool)}/SKILL.md"


def mailbox_skills_destination_for_tool(tool: str) -> str:
    """Return the active runtime-owned skill destination for one supported tool."""

    return system_skills_destination_for_tool(tool)


def mailbox_primary_skill_references(*, tool: str | None = None) -> tuple[str, ...]:
    """Return both top-level skills required for managed mailbox routing."""

    return (
        mailbox_processing_skill_reference(tool=tool),
        mailbox_shared_skill_reference(tool=tool),
    )


def projected_mailbox_skill_document_path(
    *,
    tool: str,
    home_path: Path,
    skill_reference: str,
) -> Path:
    """Return one installed mailbox skill document path for a specific tool home."""

    return (
        home_path.resolve()
        / mailbox_skills_destination_for_tool(tool)
        / skill_reference
        / "SKILL.md"
    ).resolve()


def install_runtime_mailbox_system_skills_for_tool(
    *, tool: str, home_path: Path
) -> tuple[str, ...]:
    """Install the complete managed-agent pack into one concrete tool home."""

    result = install_system_skills_for_home(
        tool=tool,
        home_path=home_path,
        pack_ids=(SYSTEM_SKILL_PACK_AGENT,),
    )
    return result.standalone_skill_names


def project_runtime_mailbox_system_skills(
    destination_root: Path,
    *,
    tool: str | None = None,
) -> tuple[str, ...]:
    """Copy the complete managed-agent pack into an explicit skill root."""

    return project_system_skills_to_destination(
        destination_root,
        pack_id=SYSTEM_SKILL_PACK_AGENT,
    )


def _mailbox_entrypoint_reference(*, tool: str | None = None) -> str:
    """Return the projected public managed-agent entrypoint reference."""

    if tool is not None:
        system_skills_destination_for_tool(tool)
    return MAILBOX_AGENT_ENTRYPOINT_NAME


def _resolve_declared_mailbox_root(*, declared_root: str | None, runtime_root: Path) -> Path | None:
    if declared_root is None:
        return None
    candidate = Path(declared_root)
    if candidate.is_absolute():
        return candidate.resolve()
    return (runtime_root.resolve() / candidate).resolve()


def stalwart_discovery_url(base_url: str) -> str:
    """Derive the JMAP session endpoint from a server base, preserving its path prefix."""
    jmap_origin(base_url)
    parsed = urlsplit(base_url)
    if "?" in base_url:
        raise ValueError("JMAP base URL cannot contain a query.")
    return urlunsplit(parsed._replace(path=parsed.path.rstrip("/") + "/.well-known/jmap"))


def _parse_trusted_jmap_origins(payload: dict[str, Any], *, source: str) -> tuple[str, ...]:
    """Read persisted and declarative approvals in their JSON array form."""
    origins = payload.get("trusted_jmap_origins", [])
    if not isinstance(origins, list) or any(not isinstance(origin, str) for origin in origins):
        raise ValueError(f"{source}.trusted_jmap_origins must be a list of JMAP origins")
    try:
        return normalize_jmap_origins(origins)
    except StalwartError as exc:
        raise ValueError(f"{source}.trusted_jmap_origins: {exc}") from None


def _resolve_stalwart_endpoints(
    *,
    declared_config: StalwartMailboxDeclarativeConfig | None,
    base_url_override: str | None,
    jmap_url_override: str | None,
    management_url_override: str | None,
) -> tuple[str | None, str, str]:
    base_url = (
        base_url_override
        or (declared_config.base_url if declared_config is not None else None)
        or _optional_env(STALWART_BASE_URL_ENV_VAR)
    )
    jmap_url = jmap_url_override or (
        declared_config.jmap_url if declared_config is not None else None
    )
    management_url = management_url_override or (
        declared_config.management_url if declared_config is not None else None
    )
    if jmap_url is None and base_url is not None:
        jmap_url = stalwart_discovery_url(base_url)
    if management_url is None and base_url is not None:
        management_url = f"{base_url.rstrip('/')}/api"
    if jmap_url is None or management_url is None:
        raise ValueError(
            "stalwart mailbox transport requires either mailbox.base_url or both mailbox.jmap_url "
            f"and mailbox.management_url. The `{STALWART_BASE_URL_ENV_VAR}` env var may also "
            "provide the base URL."
        )
    return base_url, jmap_url, management_url


def _resolved_stalwart_credential_file(
    *, manifest_path: Path | None, credential_ref: str
) -> Path | None:
    """Resolve a private locator without reading or materializing credential state."""

    if manifest_path is None:
        return None
    return session_stalwart_credential_path(manifest_path.resolve().parent, credential_ref)


def _runtime_root_from_session_root(session_root: Path) -> Path:
    try:
        return session_root.resolve().parents[2]
    except IndexError as exc:
        raise ValueError(
            f"runtime-owned session root `{session_root}` does not match <runtime>/sessions/<backend>/<session>"
        ) from exc


def _require_optional_non_blank_str(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string when set")
    return value.strip()


def _optional_env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


def _tmux_mailbox_env_reader(session_name: str) -> Callable[[str], str | None]:
    from houmao.agents.realm_controller.backends.tmux_runtime import (
        read_tmux_session_environment_value,
    )

    def _reader(variable_name: str) -> str | None:
        return read_tmux_session_environment_value(
            session_name=session_name,
            variable_name=variable_name,
        )

    return _reader


def _load_live_mailbox_manifest_context(
    manifest_path: Path,
) -> tuple[Any, MailboxesResolvedConfig, str | None]:
    """Load manifest-backed mailbox config and tmux session authority."""

    from houmao.agents.realm_controller.manifest import (
        load_session_manifest,
        parse_session_manifest_payload,
    )
    from houmao.agents.realm_controller.session_authority import resolve_manifest_session_authority

    handle = load_session_manifest(manifest_path.resolve())
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    mailboxes = mailboxes_resolved_config_from_payload(
        payload.launch_plan.mailboxes,
        manifest_path=handle.path,
    )
    authority = resolve_manifest_session_authority(
        manifest_path=handle.path,
        payload=payload,
    )
    return handle, mailboxes, authority.tmux_session_name


def _load_optional_gateway_current_instance(path: Path) -> GatewayCurrentInstanceV1 | None:
    """Load the live gateway current-instance record when available."""

    try:
        return load_gateway_current_instance(path)
    except SessionManifestError:
        return None


def _resolve_gateway_from_current_instance_record(
    *,
    current_instance: GatewayCurrentInstanceV1,
    state_path: Path,
    gateway_client_factory: Callable[[GatewayEndpoint], Any] | None,
) -> LiveGatewayBindingResolution | None:
    """Resolve and validate the authoritative current-instance gateway record."""

    try:
        return _validate_live_gateway_binding(
            source="current_instance_record",
            host=current_instance.host,
            port=current_instance.port,
            protocol_version=current_instance.protocol_version,
            state_path=state_path,
            expected_state_path=state_path,
            current_instance=current_instance,
            gateway_client_factory=gateway_client_factory,
        )
    except ValueError:
        return None


def _resolve_gateway_from_env_reader(
    *,
    source: Literal["process_env", "tmux_session_env"],
    env_reader: Callable[[str], str | None],
    current_instance: GatewayCurrentInstanceV1,
    state_path: Path,
    gateway_client_factory: Callable[[GatewayEndpoint], Any] | None,
) -> LiveGatewayBindingResolution | None:
    """Resolve a live gateway endpoint candidate from one env source."""

    env_bindings = _read_optional_gateway_env_bindings(env_reader=env_reader)
    if env_bindings is None:
        return None
    try:
        return _validate_live_gateway_binding(
            source=source,
            host=cast(GatewayHost, env_bindings[AGENT_GATEWAY_HOST_ENV_VAR]),
            port=int(env_bindings[AGENT_GATEWAY_PORT_ENV_VAR]),
            protocol_version=cast(
                GatewayProtocolVersion,
                env_bindings[AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR],
            ),
            state_path=Path(env_bindings[AGENT_GATEWAY_STATE_PATH_ENV_VAR]),
            expected_state_path=state_path,
            current_instance=current_instance,
            gateway_client_factory=gateway_client_factory,
        )
    except (ValueError, TypeError):
        return None


def _read_optional_gateway_env_bindings(
    *,
    env_reader: Callable[[str], str | None],
) -> dict[str, str] | None:
    """Read live gateway env vars when a complete set is available."""

    env_bindings: dict[str, str] = {}
    for variable_name in (
        AGENT_GATEWAY_HOST_ENV_VAR,
        AGENT_GATEWAY_PORT_ENV_VAR,
        AGENT_GATEWAY_STATE_PATH_ENV_VAR,
        AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    ):
        try:
            raw = env_reader(variable_name)
        except Exception:  # noqa: BLE001
            return None
        value = _normalize_optional_value(raw)
        if value is None:
            return None
        env_bindings[variable_name] = value
    return env_bindings


def _validate_live_gateway_binding(
    *,
    source: LiveGatewayBindingSource,
    host: GatewayHost,
    port: int,
    protocol_version: GatewayProtocolVersion,
    state_path: Path,
    expected_state_path: Path,
    current_instance: GatewayCurrentInstanceV1,
    gateway_client_factory: Callable[[GatewayEndpoint], Any] | None,
) -> LiveGatewayBindingResolution:
    """Validate one live gateway endpoint structurally and via `/health`."""

    if host not in {"127.0.0.1", "0.0.0.0"}:
        raise ValueError(f"unsupported gateway host {host!r}")
    if port < 1 or port > 65535:
        raise ValueError(f"unsupported gateway port {port!r}")
    if protocol_version != GATEWAY_PROTOCOL_VERSION:
        raise ValueError(
            f"unsupported gateway protocol {protocol_version!r}; expected {GATEWAY_PROTOCOL_VERSION!r}"
        )
    if current_instance.protocol_version != GATEWAY_PROTOCOL_VERSION:
        raise ValueError(
            "gateway current-instance record published an incompatible protocol version "
            f"{current_instance.protocol_version!r}"
        )
    if current_instance.host != host or current_instance.port != port:
        raise ValueError("gateway binding does not match the authoritative current-instance record")
    if not state_path.is_absolute() or state_path.resolve() != expected_state_path.resolve():
        raise ValueError("gateway state_path does not match the runtime-owned gateway state path")

    endpoint = GatewayEndpoint(host=host, port=port)
    client = (
        gateway_client_factory(endpoint)
        if gateway_client_factory is not None
        else GatewayClient(endpoint=endpoint)
    )
    try:
        health = client.health()
    except GatewayHttpError as exc:
        raise ValueError("gateway health probe failed") from exc
    if health.protocol_version != GATEWAY_PROTOCOL_VERSION:
        raise ValueError(
            f"gateway health reported incompatible protocol {health.protocol_version!r}"
        )
    return LiveGatewayBindingResolution(
        host=host,
        port=port,
        base_url=f"http://{host}:{port}",
        state_path=state_path.resolve(),
        protocol_version=protocol_version,
        source=source,
    )


def _resolve_manifest_path_from_agent_identity(
    *,
    agent_identity: str,
    env: Mapping[str, str] | None,
    now: datetime | None,
) -> Path:
    """Resolve a runtime-owned manifest path through the shared live-agent registry."""

    from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record

    record = resolve_live_agent_record(
        agent_identity,
        env=env,
        now=now,
    )
    if record is None:
        raise ValueError(
            f"resolve-live could not find a fresh shared-registry record for `{agent_identity}`"
        )
    manifest_path = Path(record.runtime.manifest_path).expanduser()
    if not manifest_path.is_absolute():
        raise ValueError(
            f"shared-registry manifest path for `{agent_identity}` is not absolute: {manifest_path}"
        )
    return manifest_path.resolve()


def _normalize_optional_value(value: str | None) -> str | None:
    """Normalize env-reader output to stripped non-empty strings."""

    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _resolve_live_manifest_path(value: str | None) -> Path:
    from houmao.agents.realm_controller.agent_identity import AGENT_MANIFEST_PATH_ENV_VAR

    manifest_path_value = value or _optional_env(AGENT_MANIFEST_PATH_ENV_VAR)
    if manifest_path_value is None:
        raise ValueError(
            "resolve-live requires --manifest-path or the HOUMAO_MANIFEST_PATH env var"
        )
    manifest_path = Path(manifest_path_value).expanduser()
    if not manifest_path.is_absolute():
        raise ValueError("resolve-live requires an absolute runtime-owned manifest path")
    return manifest_path.resolve()


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m houmao.agents.mailbox_runtime_support",
        description=(
            "Resolve runtime-owned live mailbox bindings and the optional attached gateway "
            "mail-facade endpoint for a managed session."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_live = subparsers.add_parser(
        "resolve-live",
        help="Resolve current live mailbox bindings and optional gateway endpoint as JSON.",
    )
    target_group = resolve_live.add_mutually_exclusive_group()
    target_group.add_argument(
        "--manifest-path",
        help="Absolute runtime-owned session manifest path. Defaults to HOUMAO_MANIFEST_PATH.",
    )
    target_group.add_argument(
        "--agent-identity",
        help="Agent id or unique agent name resolved through the shared live-agent registry.",
    )
    resolve_live.add_argument(
        "--source",
        choices=("auto", "tmux_session_env", "process_env"),
        default="auto",
        help=(
            "Mailbox discovery source. `auto` prefers current process env and falls back to "
            "the owning tmux session env."
        ),
    )
    return parser


def _run_cli(argv: list[str] | None = None) -> int:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    if args.command != "resolve-live":
        parser.error(f"unsupported command: {args.command}")

    try:
        if args.agent_identity:
            resolution = resolve_live_mailbox_binding_from_agent_identity(
                agent_identity=args.agent_identity,
                source=cast(ResolveLiveSource, args.source),
            )
        else:
            resolution = resolve_live_mailbox_binding_from_manifest_path(
                manifest_path=_resolve_live_manifest_path(args.manifest_path),
                source=cast(ResolveLiveSource, args.source),
            )
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(resolution.payload(), indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the lightweight live-mailbox helper CLI."""

    return _run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())


def _derive_auto_agent_name_base(*, tool: str, role_name: str) -> str:
    tool_component = _sanitize_component(tool, fallback="tool")
    role_component = _sanitize_component(role_name, fallback="role")
    combined = f"{tool_component}-{role_component}".strip("-_")
    if not combined:
        return "agent"
    short = combined[:40].strip("-_")
    if not short:
        return "agent"
    if not short[0].isalnum():
        return f"a{short}"
    return short


def _derive_default_mailbox_local_part(
    *,
    tool: str,
    role_name: str,
    agent_identity: str | None,
) -> str:
    """Return the default mailbox local part for one managed agent."""

    fallback = _derive_auto_agent_name_base(tool=tool, role_name=role_name)
    if agent_identity is None or not agent_identity.strip():
        candidate = fallback
    elif _is_path_like_agent_identity(agent_identity):
        candidate = fallback
    else:
        stripped = agent_identity.strip()
        if stripped.startswith(AGENT_NAMESPACE_PREFIX):
            stripped = stripped[len(AGENT_NAMESPACE_PREFIX) :]
        candidate = _sanitize_component(stripped, fallback=fallback)
    if is_houmao_reserved_mailbox_local_part(candidate):
        raise ValueError(
            "default mailbox address local parts beginning with `HOUMAO-` are reserved for "
            "Houmao-owned system principals"
        )
    return candidate


def _is_path_like_agent_identity(value: str) -> bool:
    return "/" in value or "\\" in value or value.endswith(".json")


def _sanitize_component(value: str, *, fallback: str) -> str:
    cleaned = _SANITIZE_COMPONENT_RE.sub("-", value.strip()).strip("-_")
    cleaned = _COLLAPSE_DASH_RE.sub("-", cleaned)
    cleaned = _COLLAPSE_UNDERSCORE_RE.sub("_", cleaned)
    if not cleaned:
        return fallback
    if not cleaned[0].isalnum():
        return f"a{cleaned}"
    return cleaned
