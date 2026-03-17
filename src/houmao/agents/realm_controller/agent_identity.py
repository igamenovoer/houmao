"""Agent-identity parsing and normalization helpers.

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
    Normalize and validate name-based identities into `AGENTSYS-...`.
derive_auto_agent_name_base
    Build a short safe base for auto-generated CAO identities.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Collection
from dataclasses import dataclass

from .errors import SessionManifestError

AGENT_NAMESPACE_PREFIX = "AGENTSYS-"
AGENT_RESERVED_TOKEN = "AGENTSYS"
AGENT_DEF_DIR_ENV_VAR = "AGENTSYS_AGENT_DEF_DIR"
AGENT_MANIFEST_PATH_ENV_VAR = "AGENTSYS_MANIFEST_PATH"
AGENT_ID_HEXDIGEST_LENGTH = 32
DEFAULT_TMUX_AGENT_ID_PREFIX_LENGTH = 6

_ALLOWED_AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_STANDALONE_RESERVED_TOKEN_RE = re.compile(r"(^|[^0-9A-Za-z])AGENTSYS($|[^0-9A-Za-z])")
_INEXACT_AGENTSYS_RE = re.compile(r"agentsys", re.IGNORECASE)
_SANITIZE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_COLLAPSE_DASH_RE = re.compile(r"-{2,}")
_COLLAPSE_UNDERSCORE_RE = re.compile(r"_{2,}")
_AGENT_ID_RE = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class AgentIdentityNormalization:
    """Normalized tmux-facing identity details.

    Parameters
    ----------
    canonical_name:
        Canonical tmux session identity (always `AGENTSYS-...`).
    name_portion:
        Name portion after stripping an optional exact `AGENTSYS-` prefix.
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
            "Agent identity `AGENTSYS` is reserved; choose a different name."
        )

    warnings: list[str] = []
    has_exact_prefix = value.startswith(AGENT_NAMESPACE_PREFIX)
    if not has_exact_prefix and _INEXACT_AGENTSYS_RE.search(value):
        warnings.append(
            "Agent identity contains `AGENTSYS` but does not start with exact "
            "`AGENTSYS-`; treating it as missing the namespace prefix."
        )

    name_portion = value[len(AGENT_NAMESPACE_PREFIX) :] if has_exact_prefix else value
    _validate_agent_name_portion(name_portion)

    canonical_name = value if has_exact_prefix else f"{AGENT_NAMESPACE_PREFIX}{value}"
    return AgentIdentityNormalization(
        canonical_name=canonical_name,
        name_portion=name_portion,
        warnings=tuple(warnings),
    )


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


def derive_agent_id_from_name(value: str) -> str:
    """Derive the authoritative default agent id from a canonical agent name."""

    canonical_name = normalize_agent_identity_name(value).canonical_name
    return hashlib.md5(canonical_name.encode("utf-8"), usedforsecurity=False).hexdigest()


def derive_tmux_session_name(
    *,
    canonical_agent_name: str,
    agent_id: str,
    prefix_length: int = DEFAULT_TMUX_AGENT_ID_PREFIX_LENGTH,
    occupied_session_names: Collection[str] | None = None,
) -> str:
    """Derive one tmux session name from canonical identity plus agent-id prefix.

    Parameters
    ----------
    canonical_agent_name:
        Canonical runtime identity in `AGENTSYS-...` form.
    agent_id:
        Authoritative agent identifier whose prefix will be embedded in the
        tmux session name.
    prefix_length:
        Initial prefix length to try before collision-driven extension.
    occupied_session_names:
        Optional currently occupied tmux session names used to extend the
        prefix until the candidate becomes unique.

    Returns
    -------
    str
        Tmux session name in `<canonical-agent-name>-<agent-id-prefix>` form.

    Raises
    ------
    SessionManifestError
        If the agent id is blank, the prefix length is invalid, or no unique
        tmux session name can be derived from the full authoritative agent id.
    """

    normalized = normalize_agent_identity_name(canonical_agent_name)
    stripped_agent_id = agent_id.strip()
    if not stripped_agent_id:
        raise SessionManifestError("Authoritative agent_id must not be blank.")
    if prefix_length < 1:
        raise SessionManifestError("tmux session-name prefix length must be at least 1.")

    occupied = {
        session_name.strip()
        for session_name in occupied_session_names or ()
        if isinstance(session_name, str) and session_name.strip()
    }
    candidate_length = min(prefix_length, len(stripped_agent_id))

    while True:
        candidate = f"{normalized.canonical_name}-{stripped_agent_id[:candidate_length]}"
        if candidate not in occupied:
            return candidate
        if candidate_length >= len(stripped_agent_id):
            break
        candidate_length += 1

    raise SessionManifestError(
        "Failed to derive a unique tmux session name for canonical agent name "
        f"`{normalized.canonical_name}` using authoritative agent_id "
        f"`{stripped_agent_id}`."
    )


def is_agent_id(value: str) -> bool:
    """Return whether the provided value looks like an authoritative agent id."""

    return bool(_AGENT_ID_RE.fullmatch(value.strip()))


def _validate_agent_name_portion(name_portion: str) -> None:
    """Validate the namespace-free identity name portion."""

    if not name_portion:
        raise SessionManifestError(
            "Agent identity name portion must not be empty after `AGENTSYS-`."
        )
    if not _ALLOWED_AGENT_NAME_RE.fullmatch(name_portion):
        raise SessionManifestError(
            "Invalid agent identity name portion. Allowed characters are ASCII "
            "letters/digits plus `_` and `-`, and the first character must be "
            "a letter or digit."
        )
    if _STANDALONE_RESERVED_TOKEN_RE.search(name_portion):
        raise SessionManifestError(
            "Invalid agent identity name portion: standalone token `AGENTSYS` is reserved."
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
