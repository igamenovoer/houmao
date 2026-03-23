"""Mailbox config resolution and runtime-owned skill projection helpers."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
import os
import re
from typing import Any, cast

from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.filesystem import (
    resolve_active_mailbox_dir,
    resolve_active_mailbox_inbox_dir,
    resolve_active_mailbox_local_sqlite_path,
)
from houmao.mailbox.stalwart import (
    STALWART_BASE_URL_ENV_VAR,
    StalwartError,
    build_stalwart_credential_ref,
    ensure_stalwart_mailbox,
    materialize_stalwart_session_credential,
)
from houmao.owned_paths import resolve_mailbox_root

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
MAILBOX_SYSTEM_NAMESPACE_DIR = ".system/mailbox"
MAILBOX_FILESYSTEM_SKILL_NAME = "email-via-filesystem"
MAILBOX_STALWART_SKILL_NAME = "email-via-stalwart"
MAILBOX_FILESYSTEM_SKILL_REFERENCE = (
    f"{MAILBOX_SYSTEM_NAMESPACE_DIR}/{MAILBOX_FILESYSTEM_SKILL_NAME}"
)
MAILBOX_STALWART_SKILL_REFERENCE = f"{MAILBOX_SYSTEM_NAMESPACE_DIR}/{MAILBOX_STALWART_SKILL_NAME}"
MAILBOX_SYSTEM_SKILL_REFERENCES = (
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
        return FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id=principal_id,
            address=address,
            filesystem_root=Path(filesystem_root).resolve(),
            bindings_version=bindings_version,
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
        return FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id=principal_id,
            address=address,
            filesystem_root=filesystem_root.resolve(),
            bindings_version=mailbox_bindings_version_now(),
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

    return FilesystemMailboxResolvedConfig(
        transport="filesystem",
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
        .replace("+00:00", "Z")
    )


def mailbox_env_bindings(config: MailboxResolvedConfig) -> dict[str, str]:
    """Return runtime-managed mailbox env bindings for a resolved config."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        mailbox_root = config.filesystem_root.resolve()
        mailbox_dir = resolve_active_mailbox_dir(mailbox_root, address=config.address)
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


def bootstrap_resolved_mailbox(
    config: MailboxResolvedConfig,
    *,
    manifest_path_hint: Path | None,
    role_name: str,
) -> MailboxResolvedConfig:
    """Bootstrap or materialize one resolved mailbox binding for a session."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        bootstrap_filesystem_mailbox(
            config.filesystem_root,
            principal=MailboxPrincipal(
                principal_id=config.principal_id,
                address=config.address,
                manifest_path_hint=(
                    str(manifest_path_hint.resolve()) if manifest_path_hint else None
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
    """Return the projected mailbox system-skill reference for one transport."""

    if isinstance(config, FilesystemMailboxResolvedConfig):
        return MAILBOX_FILESYSTEM_SKILL_REFERENCE
    return MAILBOX_STALWART_SKILL_REFERENCE


def project_runtime_mailbox_system_skills(destination_root: Path) -> tuple[str, ...]:
    """Project packaged runtime-owned mailbox skills into one brain home."""

    source_root = (
        resources.files("houmao.agents.realm_controller.assets") / "system_skills" / "mailbox"
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
