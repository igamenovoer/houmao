"""Mailbox config resolution and runtime-owned skill projection helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib import resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path
import os
import re
import sys
from typing import Any, Callable, Literal, Mapping, cast

from houmao.mailbox import MailboxBootstrapError, bootstrap_filesystem_mailbox
from houmao.mailbox.filesystem import (
    resolve_active_mailbox_dir,
    resolve_active_mailbox_inbox_dir,
    resolve_active_mailbox_local_sqlite_path,
    resolve_filesystem_mailbox_paths,
)
from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox
from houmao.mailbox.stalwart import (
    STALWART_BASE_URL_ENV_VAR,
    StalwartError,
    build_stalwart_credential_ref,
    ensure_stalwart_mailbox,
    materialize_stalwart_session_credential,
)
from houmao.owned_paths import resolve_mailbox_root
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

from .mailbox_runtime_models import (
    FilesystemMailboxDeclarativeConfig,
    FilesystemMailboxResolvedConfig,
    MailboxDeclarativeConfig,
    MailboxResolvedConfig,
    StalwartMailboxDeclarativeConfig,
    StalwartMailboxResolvedConfig,
)

AGENT_NAMESPACE_PREFIX = "AGENTSYS-"
_SANITIZE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_COLLAPSE_DASH_RE = re.compile(r"-{2,}")
_COLLAPSE_UNDERSCORE_RE = re.compile(r"_{2,}")

MAILBOX_TRANSPORT_NONE = "none"
MAILBOX_TRANSPORT_FILESYSTEM = "filesystem"
MAILBOX_TRANSPORT_STALWART = "stalwart"
MAILBOX_PRIMARY_NAMESPACE_DIR = "mailbox"
MAILBOX_FILESYSTEM_SKILL_NAME = "email-via-filesystem"
MAILBOX_STALWART_SKILL_NAME = "email-via-stalwart"
MAILBOX_FILESYSTEM_SKILL_REFERENCE = (
    f"{MAILBOX_PRIMARY_NAMESPACE_DIR}/{MAILBOX_FILESYSTEM_SKILL_NAME}"
)
MAILBOX_STALWART_SKILL_REFERENCE = f"{MAILBOX_PRIMARY_NAMESPACE_DIR}/{MAILBOX_STALWART_SKILL_NAME}"
MAILBOX_PRIMARY_SKILL_REFERENCES = (
    MAILBOX_FILESYSTEM_SKILL_REFERENCE,
    MAILBOX_STALWART_SKILL_REFERENCE,
)

_MAILBOX_COMMON_ENV_VARS = (
    "AGENTSYS_MAILBOX_TRANSPORT",
    "AGENTSYS_MAILBOX_PRINCIPAL_ID",
    "AGENTSYS_MAILBOX_ADDRESS",
    "AGENTSYS_MAILBOX_BINDINGS_VERSION",
)
_MAILBOX_FILESYSTEM_ENV_VARS = (
    "AGENTSYS_MAILBOX_FS_ROOT",
    "AGENTSYS_MAILBOX_FS_SQLITE_PATH",
    "AGENTSYS_MAILBOX_FS_INBOX_DIR",
    "AGENTSYS_MAILBOX_FS_MAILBOX_DIR",
    "AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH",
)
_MAILBOX_EMAIL_ENV_VARS = (
    "AGENTSYS_MAILBOX_EMAIL_JMAP_URL",
    "AGENTSYS_MAILBOX_EMAIL_MANAGEMENT_URL",
    "AGENTSYS_MAILBOX_EMAIL_LOGIN_IDENTITY",
    "AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_REF",
    "AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE",
)
MailboxBindingSource = Literal["manifest_binding"]
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
        if None in {jmap_url, management_url, login_identity, credential_ref}:
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
            management_url=cast(str, management_url),
            login_identity=cast(str, login_identity),
            credential_ref=cast(str, credential_ref),
            bindings_version=bindings_version,
            credential_file=credential_file,
        )

    raise ValueError(f"unsupported persisted mailbox transport {transport!r}")


def resolve_effective_mailbox_config(
    *,
    declared_config: MailboxDeclarativeConfig | None,
    runtime_root: Path,
    tool: str,
    role_name: str,
    agent_identity: str | None = None,
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
        principal_id = default_mailbox_principal_id(
            tool=tool,
            role_name=role_name,
            agent_identity=agent_identity,
        )

    address = address_override or (declared_config.address if declared_config is not None else None)
    if address is None:
        address = f"{principal_id}@agents.localhost"

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
            mailbox_kind="symlink" if mailbox_account_dir is not None else "in_root",
            mailbox_path=(
                mailbox_account_dir
                if mailbox_account_dir is not None
                else mailbox_paths.mailbox_entry_path(address)
            ),
        )

    if transport == MAILBOX_TRANSPORT_STALWART:
        base_url, jmap_url, management_url = _resolve_stalwart_endpoints(
            declared_config=declared_config
            if isinstance(declared_config, StalwartMailboxDeclarativeConfig)
            else None,
            base_url_override=stalwart_base_url_override,
            jmap_url_override=stalwart_jmap_url_override,
            management_url_override=stalwart_management_url_override,
        )
        login_identity = stalwart_login_identity_override or address
        return StalwartMailboxResolvedConfig(
            transport="stalwart",
            principal_id=principal_id,
            address=address,
            jmap_url=jmap_url,
            management_url=management_url,
            login_identity=login_identity,
            credential_ref=build_stalwart_credential_ref(address=address, jmap_url=jmap_url),
            bindings_version=mailbox_bindings_version_now(),
            credential_file=None,
        )

    raise ValueError(
        f"unsupported mailbox transport {transport!r}; expected one of "
        f"{MAILBOX_TRANSPORT_FILESYSTEM!r} or {MAILBOX_TRANSPORT_STALWART!r}"
    )


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


def mailbox_bindings_version_now() -> str:
    """Return a monotonic-enough timestamp label for mailbox bindings."""

    return (
        datetime.now(UTC)
        .replace(tzinfo=UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


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
            "AGENTSYS_MAILBOX_TRANSPORT": config.transport,
            "AGENTSYS_MAILBOX_PRINCIPAL_ID": config.principal_id,
            "AGENTSYS_MAILBOX_ADDRESS": config.address,
            "AGENTSYS_MAILBOX_BINDINGS_VERSION": config.bindings_version,
            "AGENTSYS_MAILBOX_FS_ROOT": str(mailbox_root),
            "AGENTSYS_MAILBOX_FS_SQLITE_PATH": str(mailbox_root / "index.sqlite"),
            "AGENTSYS_MAILBOX_FS_INBOX_DIR": str(inbox_dir),
            "AGENTSYS_MAILBOX_FS_MAILBOX_DIR": str(mailbox_dir),
            "AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH": str(local_sqlite_path),
        }

    credential_file = config.credential_file
    if credential_file is None:
        raise ValueError(
            "stalwart mailbox env bindings require a materialized credential file for this session"
        )
    return {
        "AGENTSYS_MAILBOX_TRANSPORT": config.transport,
        "AGENTSYS_MAILBOX_PRINCIPAL_ID": config.principal_id,
        "AGENTSYS_MAILBOX_ADDRESS": config.address,
        "AGENTSYS_MAILBOX_BINDINGS_VERSION": config.bindings_version,
        "AGENTSYS_MAILBOX_EMAIL_JMAP_URL": config.jmap_url,
        "AGENTSYS_MAILBOX_EMAIL_MANAGEMENT_URL": config.management_url,
        "AGENTSYS_MAILBOX_EMAIL_LOGIN_IDENTITY": config.login_identity,
        "AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_REF": config.credential_ref,
        "AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE": str(credential_file.resolve()),
    }


def mailbox_env_var_names(config: MailboxResolvedConfig) -> tuple[str, ...]:
    """Return the runtime-owned env var names populated for the mailbox."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        return (*_MAILBOX_COMMON_ENV_VARS, *_MAILBOX_FILESYSTEM_ENV_VARS)
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
) -> LiveMailboxBindingResolution:
    """Resolve one live mailbox binding starting from a runtime-owned manifest path."""
    handle, durable_mailbox, tmux_session_name = _load_live_mailbox_manifest_context(manifest_path)
    mailbox_resolution = resolve_live_mailbox_binding(durable_mailbox=durable_mailbox)
    resolved_gateway = resolve_live_gateway_binding_from_manifest_path(
        manifest_path=handle.path,
        tmux_session_name=tmux_session_name,
        source=(
            gateway_source
            if gateway_source is not None
            else "current_instance_record"
        ),
        process_env_reader=process_env_reader,
        tmux_env_reader=tmux_env_reader,
        gateway_client_factory=gateway_client_factory,
    )
    return LiveMailboxBindingResolution(
        mailbox=mailbox_resolution.mailbox,
        source=mailbox_resolution.source,
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
) -> LiveMailboxBindingResolution:
    """Resolve one live mailbox binding through shared-registry manifest discovery."""

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
            mailbox_dir = resolve_active_mailbox_dir(mailbox_root, address=mailbox.address).resolve()
            inbox_dir = resolve_active_mailbox_inbox_dir(mailbox_root, address=mailbox.address).resolve()
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
        if config.mailbox_kind == "symlink":
            try:
                config.mailbox_path.relative_to(resolved_root)
            except ValueError:
                pass
            else:
                raise ValueError(
                    "filesystem private mailbox directory must live outside the shared mailbox root"
                )
        bootstrap_filesystem_mailbox(resolved_root)
        register_mailbox(
            resolved_root,
            RegisterMailboxRequest(
                mode="safe",
                address=config.address,
                owner_principal_id=config.principal_id,
                mailbox_kind=config.mailbox_kind,
                mailbox_path=config.mailbox_path,
                manifest_path_hint=(
                    str(manifest_path_hint.resolve()) if manifest_path_hint is not None else None
                ),
                role=role_name,
            ),
        )
        return config

    if manifest_path_hint is None:
        raise ValueError(
            "stalwart mailbox bootstrap requires a runtime-owned session manifest path"
        )
    session_root = manifest_path_hint.resolve().parent
    runtime_root = _runtime_root_from_session_root(session_root)
    binding = ensure_stalwart_mailbox(
        runtime_root=runtime_root,
        session_root=session_root,
        principal_id=config.principal_id,
        address=config.address,
        jmap_url=config.jmap_url,
        management_url=config.management_url,
        login_identity=config.login_identity,
    )
    return replace(
        config,
        jmap_url=binding.jmap_url,
        management_url=binding.management_url,
        login_identity=binding.login_identity,
        credential_ref=binding.credential_ref,
        credential_file=binding.credential_file,
        bindings_version=mailbox_bindings_version_now(),
    )


def mailbox_skill_reference(config: MailboxResolvedConfig) -> str:
    """Return the primary projected mailbox skill reference for one transport."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        return MAILBOX_FILESYSTEM_SKILL_REFERENCE
    return MAILBOX_STALWART_SKILL_REFERENCE


def mailbox_skill_name(config: MailboxResolvedConfig) -> str:
    """Return the stable transport-specific mailbox skill name."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        return MAILBOX_FILESYSTEM_SKILL_NAME
    return MAILBOX_STALWART_SKILL_NAME


def mailbox_skill_document_path(
    config: MailboxResolvedConfig,
    *,
    skills_destination: str = "skills",
) -> str:
    """Return the primary mailbox skill document path for the active skill destination."""

    return f"{skills_destination}/{mailbox_skill_reference(config)}/SKILL.md"


def project_runtime_mailbox_system_skills(destination_root: Path) -> tuple[str, ...]:
    """Project packaged runtime-owned mailbox skills into one brain home.

    Project the packaged mailbox skill tree only into the visible mailbox path.
    """

    source_root = (
        resources.files("houmao.agents.realm_controller.assets") / "system_skills" / "mailbox"
    )
    primary_root = destination_root / MAILBOX_PRIMARY_NAMESPACE_DIR
    _copy_resource_tree(source_root, primary_root)
    return MAILBOX_PRIMARY_SKILL_REFERENCES


def _copy_resource_tree(source_root: Traversable, destination_root: Path) -> None:
    """Copy packaged text resources into a destination tree."""

    for child in source_root.iterdir():
        destination_path = destination_root / child.name
        if child.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            _copy_resource_tree(child, destination_path)
            continue

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(child.read_text(encoding="utf-8"), encoding="utf-8")


def _resolve_declared_mailbox_root(*, declared_root: str | None, runtime_root: Path) -> Path | None:
    if declared_root is None:
        return None
    candidate = Path(declared_root)
    if candidate.is_absolute():
        return candidate.resolve()
    return (runtime_root.resolve() / candidate).resolve()


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
        jmap_url = f"{base_url.rstrip('/')}/jmap"
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
    *,
    manifest_path: Path | None,
    credential_ref: str,
) -> Path | None:
    if manifest_path is None:
        return None
    session_root = manifest_path.resolve().parent
    runtime_root = _runtime_root_from_session_root(session_root)
    try:
        return materialize_stalwart_session_credential(
            runtime_root=runtime_root,
            session_root=session_root,
            credential_ref=credential_ref,
        )
    except StalwartError as exc:
        raise ValueError(
            f"failed to materialize session credential for `{credential_ref}`: {exc}"
        ) from exc


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
) -> tuple[Any, MailboxResolvedConfig, str | None]:
    """Load manifest-backed mailbox config and tmux session authority."""

    from houmao.agents.realm_controller.manifest import (
        load_session_manifest,
        parse_session_manifest_payload,
    )
    from houmao.agents.realm_controller.session_authority import resolve_manifest_session_authority

    handle = load_session_manifest(manifest_path.resolve())
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    durable_mailbox = resolved_mailbox_config_from_payload(
        payload.launch_plan.mailbox,
        manifest_path=handle.path,
    )
    if durable_mailbox is None:
        raise ValueError(
            "runtime-owned session manifest launch plan has no mailbox binding; live mailbox "
            "resolution is unavailable"
        )
    authority = resolve_manifest_session_authority(
        manifest_path=handle.path,
        payload=payload,
    )
    return handle, durable_mailbox, authority.tmux_session_name


def _resolve_live_mailbox_binding_with_fallbacks(
    *,
    durable_mailbox: MailboxResolvedConfig,
    tmux_session_name: str | None,
    source: ResolveLiveSource,
    process_env_reader: Callable[[str], str | None] | None,
    tmux_env_reader: Callable[[str], str | None] | None,
) -> LiveMailboxBindingResolution:
    """Resolve live mailbox bindings with the runtime-owned same-session order."""

    if source == "process_env":
        return resolve_live_mailbox_binding(
            durable_mailbox=durable_mailbox,
            source="process_env",
            env_reader=process_env_reader or _optional_env,
        )
    if source == "tmux_session_env":
        return resolve_live_mailbox_binding(
            durable_mailbox=durable_mailbox,
            tmux_session_name=tmux_session_name,
            source="tmux_session_env",
            env_reader=(
                tmux_env_reader
                or (
                    _tmux_mailbox_env_reader(tmux_session_name.strip())
                    if tmux_session_name is not None and tmux_session_name.strip()
                    else None
                )
            ),
        )

    process_error: ValueError | None = None
    try:
        return resolve_live_mailbox_binding(
            durable_mailbox=durable_mailbox,
            source="process_env",
            env_reader=process_env_reader or _optional_env,
        )
    except ValueError as exc:
        process_error = exc

    try:
        return resolve_live_mailbox_binding(
            durable_mailbox=durable_mailbox,
            tmux_session_name=tmux_session_name,
            source="tmux_session_env",
            env_reader=(
                tmux_env_reader
                or (
                    _tmux_mailbox_env_reader(tmux_session_name.strip())
                    if tmux_session_name is not None and tmux_session_name.strip()
                    else None
                )
            ),
        )
    except ValueError as exc:
        raise ValueError(
            "current live mailbox projection could not be resolved automatically: "
            f"process_env failed with {process_error}; "
            f"tmux_session_env failed with {exc}"
        ) from exc


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


def _read_live_mailbox_env_bindings(
    *,
    durable_mailbox: MailboxResolvedConfig,
    env_reader: Callable[[str], str | None],
) -> dict[str, str]:
    env_bindings: dict[str, str] = {}
    missing_names: list[str] = []
    for variable_name in mailbox_env_var_names(durable_mailbox):
        try:
            value = env_reader(variable_name)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"failed to query the live mailbox projection for `{variable_name}`: {exc}"
            ) from exc
        if value is None:
            missing_names.append(variable_name)
            continue
        env_bindings[variable_name] = value
    if missing_names:
        missing = ", ".join(missing_names)
        raise ValueError(f"current live mailbox projection is missing required env vars: {missing}")
    return env_bindings


def _mailbox_config_from_live_env_bindings(
    *,
    durable_mailbox: MailboxResolvedConfig,
    env_bindings: dict[str, str],
) -> MailboxResolvedConfig:
    transport = env_bindings["AGENTSYS_MAILBOX_TRANSPORT"]
    if transport != durable_mailbox.transport:
        raise ValueError(
            "current live mailbox projection transport "
            f"{transport!r} does not match durable mailbox transport {durable_mailbox.transport!r}"
        )

    principal_id = env_bindings["AGENTSYS_MAILBOX_PRINCIPAL_ID"]
    address = env_bindings["AGENTSYS_MAILBOX_ADDRESS"]
    bindings_version = env_bindings["AGENTSYS_MAILBOX_BINDINGS_VERSION"]
    if principal_id != durable_mailbox.principal_id:
        raise ValueError(
            "current live mailbox principal_id "
            f"{principal_id!r} does not match durable mailbox principal_id "
            f"{durable_mailbox.principal_id!r}"
        )
    if address != durable_mailbox.address:
        raise ValueError(
            "current live mailbox address "
            f"{address!r} does not match durable mailbox address {durable_mailbox.address!r}"
        )
    if bindings_version != durable_mailbox.bindings_version:
        raise ValueError(
            "current live mailbox bindings_version "
            f"{bindings_version!r} does not match durable mailbox bindings_version "
            f"{durable_mailbox.bindings_version!r}"
        )

    if isinstance(durable_mailbox, FilesystemMailboxResolvedConfig):
        filesystem_root = Path(env_bindings["AGENTSYS_MAILBOX_FS_ROOT"]).resolve()
        mailbox_dir = Path(env_bindings["AGENTSYS_MAILBOX_FS_MAILBOX_DIR"]).resolve()
        expected_in_root_path = resolve_filesystem_mailbox_paths(
            filesystem_root
        ).mailbox_entry_path(address)
        mailbox = FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id=principal_id,
            address=address,
            filesystem_root=filesystem_root,
            bindings_version=bindings_version,
            mailbox_kind="in_root" if mailbox_dir == expected_in_root_path else "symlink",
            mailbox_path=mailbox_dir,
        )
        expected_bindings = mailbox_env_bindings(mailbox)
        _validate_live_env_bindings_match_expected(
            expected_bindings=expected_bindings,
            actual_bindings=env_bindings,
        )
        return mailbox

    credential_file = Path(env_bindings["AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE"]).resolve()
    if not credential_file.is_file():
        raise ValueError(
            "current live mailbox projection points at a missing Stalwart credential file: "
            f"{credential_file}"
        )
    stalwart_mailbox = StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id=principal_id,
        address=address,
        jmap_url=env_bindings["AGENTSYS_MAILBOX_EMAIL_JMAP_URL"],
        management_url=env_bindings["AGENTSYS_MAILBOX_EMAIL_MANAGEMENT_URL"],
        login_identity=env_bindings["AGENTSYS_MAILBOX_EMAIL_LOGIN_IDENTITY"],
        credential_ref=env_bindings["AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_REF"],
        bindings_version=bindings_version,
        credential_file=credential_file,
    )
    expected_bindings = mailbox_env_bindings(stalwart_mailbox)
    _validate_live_env_bindings_match_expected(
        expected_bindings=expected_bindings,
        actual_bindings=env_bindings,
    )
    return stalwart_mailbox


def _validate_live_env_bindings_match_expected(
    *,
    expected_bindings: dict[str, str],
    actual_bindings: dict[str, str],
) -> None:
    mismatches: list[str] = []
    for key, expected_value in expected_bindings.items():
        actual_value = actual_bindings.get(key)
        if actual_value != expected_value:
            mismatches.append(f"{key} expected {expected_value!r} but got {actual_value!r}")
    if mismatches:
        raise ValueError(
            "current live mailbox projection is internally inconsistent: " + "; ".join(mismatches)
        )


def _resolve_live_manifest_path(value: str | None) -> Path:
    from houmao.agents.realm_controller.agent_identity import AGENT_MANIFEST_PATH_ENV_VAR

    manifest_path_value = value or _optional_env(AGENT_MANIFEST_PATH_ENV_VAR)
    if manifest_path_value is None:
        raise ValueError(
            "resolve-live requires --manifest-path or the AGENTSYS_MANIFEST_PATH env var"
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
        help="Absolute runtime-owned session manifest path. Defaults to AGENTSYS_MANIFEST_PATH.",
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
