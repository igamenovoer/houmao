"""Mailbox config resolution and runtime-owned skill projection helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
import re
from typing import Any, cast

from houmao.owned_paths import resolve_mailbox_root
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.filesystem import resolve_active_mailbox_inbox_dir

from .mailbox_runtime_models import (
    MailboxDeclarativeConfig,
    MailboxResolvedConfig,
    MailboxTransport,
)

AGENT_NAMESPACE_PREFIX = "AGENTSYS-"
_SANITIZE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_COLLAPSE_DASH_RE = re.compile(r"-{2,}")
_COLLAPSE_UNDERSCORE_RE = re.compile(r"_{2,}")

MAILBOX_TRANSPORT_NONE = "none"
MAILBOX_TRANSPORT_FILESYSTEM = "filesystem"
MAILBOX_SYSTEM_NAMESPACE_DIR = ".system/mailbox"
MAILBOX_FILESYSTEM_SKILL_NAME = "email-via-filesystem"
MAILBOX_FILESYSTEM_SKILL_REFERENCE = (
    f"{MAILBOX_SYSTEM_NAMESPACE_DIR}/{MAILBOX_FILESYSTEM_SKILL_NAME}"
)
MAILBOX_SYSTEM_SKILL_REFERENCES = (MAILBOX_FILESYSTEM_SKILL_REFERENCE,)

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
)


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
    if transport != MAILBOX_TRANSPORT_FILESYSTEM:
        raise ValueError(
            f"{source}: unsupported mailbox.transport {transport!r}; only `filesystem` is implemented"
        )

    principal_id = _require_optional_non_blank_str(
        payload.get("principal_id"),
        field=f"{source}.principal_id",
    )
    address = _require_optional_non_blank_str(
        payload.get("address"),
        field=f"{source}.address",
    )
    filesystem_root = _require_optional_non_blank_str(
        payload.get("filesystem_root"),
        field=f"{source}.filesystem_root",
    )
    return MailboxDeclarativeConfig(
        transport=cast(MailboxTransport, transport),
        principal_id=principal_id,
        address=address,
        filesystem_root=filesystem_root,
    )


def serialize_declarative_mailbox_config(config: MailboxDeclarativeConfig) -> dict[str, Any]:
    """Serialize a declarative mailbox config for manifest persistence."""

    payload: dict[str, Any] = {"transport": config.transport}
    if config.principal_id is not None:
        payload["principal_id"] = config.principal_id
    if config.address is not None:
        payload["address"] = config.address
    if config.filesystem_root is not None:
        payload["filesystem_root"] = config.filesystem_root
    return payload


def resolved_mailbox_config_from_payload(payload: object) -> MailboxResolvedConfig | None:
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
    filesystem_root = _require_optional_non_blank_str(
        payload.get("filesystem_root"),
        field="launch_plan.mailbox.filesystem_root",
    )
    if None in {transport, principal_id, address, bindings_version, filesystem_root}:
        raise ValueError("persisted mailbox payload is missing required fields")
    if transport != MAILBOX_TRANSPORT_FILESYSTEM:
        raise ValueError(
            f"unsupported persisted mailbox transport {transport!r}; only `filesystem` is implemented"
        )
    assert principal_id is not None
    assert address is not None
    assert bindings_version is not None
    assert filesystem_root is not None

    return MailboxResolvedConfig(
        transport=cast(MailboxTransport, transport),
        principal_id=principal_id,
        address=address,
        filesystem_root=Path(filesystem_root).resolve(),
        bindings_version=bindings_version,
    )


def resolve_effective_mailbox_config(
    *,
    declared_config: MailboxDeclarativeConfig | None,
    runtime_root: Path,
    tool: str,
    role_name: str,
    agent_identity: str | None = None,
    transport_override: str | None = None,
    filesystem_root_override: Path | None = None,
    principal_id_override: str | None = None,
    address_override: str | None = None,
) -> MailboxResolvedConfig | None:
    """Resolve one effective mailbox configuration for a started session."""

    transport = transport_override or (
        declared_config.transport if declared_config is not None else None
    )
    if transport is None or transport == MAILBOX_TRANSPORT_NONE:
        return None
    if transport != MAILBOX_TRANSPORT_FILESYSTEM:
        raise ValueError(
            f"unsupported mailbox transport {transport!r}; only `filesystem` is implemented"
        )

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

    declared_root = _resolve_declared_mailbox_root(
        declared_root=(declared_config.filesystem_root if declared_config is not None else None),
        runtime_root=runtime_root,
    )
    filesystem_root = resolve_mailbox_root(
        explicit_root=filesystem_root_override or declared_root,
    )
    assert principal_id is not None
    assert address is not None

    return MailboxResolvedConfig(
        transport=cast(MailboxTransport, transport),
        principal_id=principal_id,
        address=address,
        filesystem_root=filesystem_root.resolve(),
        bindings_version=mailbox_bindings_version_now(),
    )


def refresh_filesystem_mailbox_config(
    config: MailboxResolvedConfig,
    *,
    filesystem_root: Path | None = None,
) -> MailboxResolvedConfig:
    """Return an updated filesystem mailbox binding with a fresh version stamp."""

    return MailboxResolvedConfig(
        transport=config.transport,
        principal_id=config.principal_id,
        address=config.address,
        filesystem_root=(filesystem_root or config.filesystem_root).resolve(),
        bindings_version=mailbox_bindings_version_now(),
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
        .replace(
            "+00:00",
            "Z",
        )
    )


def mailbox_env_bindings(config: MailboxResolvedConfig) -> dict[str, str]:
    """Return runtime-managed mailbox env bindings for a resolved config."""

    if config.transport != MAILBOX_TRANSPORT_FILESYSTEM:
        raise ValueError(
            f"unsupported mailbox transport {config.transport!r}; only `filesystem` is implemented"
        )

    mailbox_root = config.filesystem_root.resolve()
    inbox_dir = resolve_active_mailbox_inbox_dir(mailbox_root, address=config.address)
    return {
        "AGENTSYS_MAILBOX_TRANSPORT": config.transport,
        "AGENTSYS_MAILBOX_PRINCIPAL_ID": config.principal_id,
        "AGENTSYS_MAILBOX_ADDRESS": config.address,
        "AGENTSYS_MAILBOX_BINDINGS_VERSION": config.bindings_version,
        "AGENTSYS_MAILBOX_FS_ROOT": str(mailbox_root),
        "AGENTSYS_MAILBOX_FS_SQLITE_PATH": str(mailbox_root / "index.sqlite"),
        "AGENTSYS_MAILBOX_FS_INBOX_DIR": str(inbox_dir),
    }


def mailbox_env_var_names(config: MailboxResolvedConfig) -> tuple[str, ...]:
    """Return the runtime-owned env var names populated for the mailbox."""

    if config.transport != MAILBOX_TRANSPORT_FILESYSTEM:
        raise ValueError(
            f"unsupported mailbox transport {config.transport!r}; only `filesystem` is implemented"
        )
    return (*_MAILBOX_COMMON_ENV_VARS, *_MAILBOX_FILESYSTEM_ENV_VARS)


def bootstrap_resolved_mailbox(
    config: MailboxResolvedConfig,
    *,
    manifest_path_hint: Path | None,
    role_name: str,
) -> None:
    """Bootstrap the resolved filesystem mailbox root for one session principal."""

    if config.transport != MAILBOX_TRANSPORT_FILESYSTEM:
        raise ValueError(
            f"unsupported mailbox transport {config.transport!r}; only `filesystem` is implemented"
        )

    bootstrap_filesystem_mailbox(
        config.filesystem_root,
        principal=MailboxPrincipal(
            principal_id=config.principal_id,
            address=config.address,
            manifest_path_hint=(str(manifest_path_hint.resolve()) if manifest_path_hint else None),
            role=role_name,
        ),
    )


def project_runtime_mailbox_system_skills(destination_root: Path) -> tuple[str, ...]:
    """Project packaged runtime-owned mailbox skills into one brain home."""

    source_root = (
        resources.files("houmao.agents.realm_controller.assets")
        / "system_skills"
        / "mailbox"
    )
    namespace_root = destination_root / MAILBOX_SYSTEM_NAMESPACE_DIR
    _copy_resource_tree(source_root, namespace_root)
    return MAILBOX_SYSTEM_SKILL_REFERENCES


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


def _require_optional_non_blank_str(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string when set")
    return value.strip()


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
