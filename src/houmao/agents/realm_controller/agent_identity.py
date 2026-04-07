"""Agent-identity parsing and managed-agent naming helpers.

This module provides the canonical parsing and validation rules for
runtime-facing agent identities.

Classes
-------
AgentIdentityNormalization
    Normalized tmux-facing identity metadata.

Functions
---------
is_path_like_agent_identity
    Determine whether an identity should be treated as a manifest path.
normalize_agent_identity_name
    Normalize and validate legacy tmux/runtime identities into `HOUMAO-...`.
normalize_managed_agent_name
    Validate a managed-agent friendly name without adding a prefix.
normalize_user_managed_agent_name
    Validate one user-provided managed-agent name that must stay unprefixed.
normalize_managed_agent_id
    Validate a managed-agent authoritative id without adding a prefix.
derive_auto_agent_name_base
    Build a short safe base for auto-generated identities.
derive_default_canonical_agent_name
    Build the default canonical managed-agent name for one tool and role.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Collection
from dataclasses import dataclass

from .errors import SessionManifestError

AGENT_NAMESPACE_PREFIX = "HOUMAO-"
AGENT_RESERVED_TOKEN = "HOUMAO"
AGENT_DEF_DIR_ENV_VAR = "HOUMAO_AGENT_DEF_DIR"
AGENT_MANIFEST_PATH_ENV_VAR = "HOUMAO_MANIFEST_PATH"
AGENT_ID_ENV_VAR = "HOUMAO_AGENT_ID"
AGENT_ID_HEXDIGEST_LENGTH = 32
SAFE_MANAGED_AGENT_COMPONENT_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
SAFE_MANAGED_AGENT_COMPONENT_DESCRIPTION = (
    "ASCII letters/digits plus `_` and `-`, starting with a letter or digit"
)

_ALLOWED_AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_LEADING_RESERVED_MANAGED_AGENT_PREFIX_RE = re.compile(r"^houmao(?=[^0-9A-Za-z])", re.IGNORECASE)
_STANDALONE_RESERVED_TOKEN_RE = re.compile(r"(^|[^0-9A-Za-z])HOUMAO($|[^0-9A-Za-z])")
_INEXACT_HOUMAO_RE = re.compile(r"houmao", re.IGNORECASE)
_SANITIZE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_COLLAPSE_DASH_RE = re.compile(r"-{2,}")
_COLLAPSE_UNDERSCORE_RE = re.compile(r"_{2,}")
_SAFE_MANAGED_AGENT_COMPONENT_RE = re.compile(SAFE_MANAGED_AGENT_COMPONENT_PATTERN)


@dataclass(frozen=True)
class AgentIdentityNormalization:
    """Normalized tmux-facing identity details.

    Parameters
    ----------
    canonical_name:
        Canonical tmux session identity (always `HOUMAO-...`).
    name_portion:
        Name portion after stripping an optional exact `HOUMAO-` prefix.
    warnings:
        Non-fatal warnings produced during normalization.
    """

    canonical_name: str
    name_portion: str
    warnings: tuple[str, ...] = ()


def is_path_like_agent_identity(value: str) -> bool:
    """Return whether an identity value should be treated as a manifest path.

    Parameters
    ----------
    value:
        Raw `--agent-identity` value.

    Returns
    -------
    bool
        `True` when the value is path-like (`/`, `\\`, or `.json` suffix).
    """

    return "/" in value or "\\" in value or value.endswith(".json")


def normalize_agent_identity_name(value: str) -> AgentIdentityNormalization:
    """Normalize and validate an agent-name identity.

    Parameters
    ----------
    value:
        Raw agent identity value interpreted as a name (not a path).

    Returns
    -------
    AgentIdentityNormalization
        Canonical identity and validation metadata.

    Raises
    ------
    SessionManifestError
        If the name is blank, reserved, or violates validation rules.
    """

    if not value or not value.strip():
        raise SessionManifestError("Agent identity must not be blank")
    if value == AGENT_RESERVED_TOKEN:
        raise SessionManifestError(
            "Agent identity `HOUMAO` is reserved; choose a different name."
        )

    warnings: list[str] = []
    has_exact_prefix = value.startswith(AGENT_NAMESPACE_PREFIX)
    if not has_exact_prefix and _INEXACT_HOUMAO_RE.search(value):
        warnings.append(
            "Agent identity contains `HOUMAO` but does not start with exact "
            "`HOUMAO-`; treating it as missing the namespace prefix."
        )

    name_portion = value[len(AGENT_NAMESPACE_PREFIX) :] if has_exact_prefix else value
    _validate_agent_name_portion(name_portion)

    canonical_name = value if has_exact_prefix else f"{AGENT_NAMESPACE_PREFIX}{value}"
    return AgentIdentityNormalization(
        canonical_name=canonical_name,
        name_portion=name_portion,
        warnings=tuple(warnings),
    )


def normalize_managed_agent_name(value: str) -> str:
    """Validate and normalize one friendly managed-agent name."""

    return _normalize_managed_agent_component(value, field_name="agent_name")


def normalize_user_managed_agent_name(value: str) -> str:
    """Validate one raw user-provided managed-agent name.

    This stricter variant reserves the leading `HOUMAO<separator>` namespace
    for runtime canonicalization and operator-facing tmux session handles.
    """

    normalized = normalize_managed_agent_name(value)
    if _LEADING_RESERVED_MANAGED_AGENT_PREFIX_RE.search(normalized):
        raise SessionManifestError(
            "Managed-agent names must not begin with reserved `HOUMAO` plus a separator. "
            "Use the raw creation-time name without the `HOUMAO-` prefix."
        )
    return normalized


def normalize_managed_agent_id(value: str) -> str:
    """Validate and normalize one authoritative managed-agent id."""

    return _normalize_managed_agent_component(value, field_name="agent_id")


def derive_auto_agent_name_base(*, tool: str, role_name: str) -> str:
    """Derive a short auto-name base from tool and role.

    Parameters
    ----------
    tool:
        Tool identity (`codex`, `claude`, ...).
    role_name:
        Selected role package name.

    Returns
    -------
    str
        Safe, short name portion suitable for canonical prefixing.
    """

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


def derive_default_canonical_agent_name(*, tool: str, role_name: str) -> str:
    """Return the default canonical managed-agent name for one launch."""

    normalized = normalize_agent_identity_name(
        derive_auto_agent_name_base(tool=tool, role_name=role_name)
    )
    return normalized.canonical_name


def derive_agent_id_from_name(value: str) -> str:
    """Derive the authoritative default agent id from a managed-agent name."""

    normalized_name = normalize_managed_agent_name(value)
    return hashlib.md5(normalized_name.encode("utf-8"), usedforsecurity=False).hexdigest()


def derive_tmux_session_name(
    *,
    canonical_agent_name: str,
    launch_epoch_ms: int,
    occupied_session_names: Collection[str] | None = None,
) -> str:
    """Derive one default tmux session name from canonical name and launch time.

    Parameters
    ----------
    canonical_agent_name:
        Managed-agent name used to derive the tmux session base.
    launch_epoch_ms:
        Launch timestamp expressed as Unix epoch milliseconds.
    occupied_session_names:
        Optional currently occupied tmux session names used to fail explicitly
        when the generated default candidate is already live.

    Returns
    -------
    str
        Tmux session name in `<canonical-agent-name>-<epoch-ms>` form.

    Raises
    ------
    SessionManifestError
        If the launch timestamp is invalid or the generated default name is
        already occupied.
    """

    normalized_name = normalize_managed_agent_name(canonical_agent_name)
    if launch_epoch_ms < 0:
        raise SessionManifestError("tmux session launch_epoch_ms must be non-negative.")

    occupied = {
        session_name.strip()
        for session_name in occupied_session_names or ()
        if isinstance(session_name, str) and session_name.strip()
    }
    candidate = f"{normalized_name}-{launch_epoch_ms}"
    if candidate in occupied:
        raise SessionManifestError(
            f"Generated default tmux session name `{candidate}` is already in use. "
            "Retry the launch or pass an explicit `--session-name`."
        )
    return candidate


def is_agent_id(value: str) -> bool:
    """Return whether the provided value looks like an authoritative agent id."""

    try:
        normalize_managed_agent_id(value)
    except SessionManifestError:
        return False
    return True


def _validate_agent_name_portion(name_portion: str) -> None:
    """Validate the namespace-free identity name portion."""

    if not name_portion:
        raise SessionManifestError(
            "Agent identity name portion must not be empty after `HOUMAO-`."
        )
    if not _ALLOWED_AGENT_NAME_RE.fullmatch(name_portion):
        raise SessionManifestError(
            "Invalid agent identity name portion. Allowed characters are ASCII "
            "letters/digits plus `_` and `-`, and the first character must be "
            "a letter or digit."
        )
    if _STANDALONE_RESERVED_TOKEN_RE.search(name_portion):
        raise SessionManifestError(
            "Invalid agent identity name portion: standalone token `HOUMAO` is reserved."
        )


def _sanitize_component(value: str, *, fallback: str) -> str:
    """Sanitize a free-form name component for identity generation."""

    cleaned = _SANITIZE_COMPONENT_RE.sub("-", value.strip()).strip("-_")
    cleaned = _COLLAPSE_DASH_RE.sub("-", cleaned)
    cleaned = _COLLAPSE_UNDERSCORE_RE.sub("_", cleaned)
    if not cleaned:
        return fallback
    if not cleaned[0].isalnum():
        return f"a{cleaned}"
    return cleaned


def _normalize_managed_agent_component(value: str, *, field_name: str) -> str:
    """Validate one shared managed-agent identity component."""

    stripped = value.strip()
    if not stripped:
        raise SessionManifestError(f"{field_name} must not be blank.")
    if stripped in {".", ".."}:
        raise SessionManifestError(f"{field_name} must not be `.` or `..`.")
    if "/" in stripped or "\\" in stripped:
        raise SessionManifestError(f"{field_name} must not contain path separators.")
    if not _SAFE_MANAGED_AGENT_COMPONENT_RE.fullmatch(stripped):
        raise SessionManifestError(
            f"{field_name} must use a filesystem-safe and URL-safe form "
            f"({SAFE_MANAGED_AGENT_COMPONENT_DESCRIPTION})."
        )
    return stripped
