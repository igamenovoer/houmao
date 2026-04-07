"""Managed launch prompt-header helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from houmao.agents.realm_controller.agent_identity import (
    derive_agent_id_from_name,
    derive_default_canonical_agent_name,
    normalize_managed_agent_id,
    normalize_user_managed_agent_name,
)

ManagedHeaderPolicy = Literal["inherit", "enabled", "disabled"]
ManagedHeaderResolutionSource = Literal["default", "launch_profile", "launch_override"]
MANAGED_PROMPT_HEADER_VERSION = 1


@dataclass(frozen=True)
class ResolvedManagedLaunchIdentity:
    """Resolved managed identity used for prompt-header rendering."""

    agent_name: str
    agent_id: str


@dataclass(frozen=True)
class ManagedPromptHeaderDecision:
    """Resolved managed-header policy for one launch."""

    enabled: bool
    resolution_source: ManagedHeaderResolutionSource
    stored_policy: ManagedHeaderPolicy | None


def normalize_managed_header_policy(
    value: str | None,
    *,
    source: str,
) -> ManagedHeaderPolicy | None:
    """Validate one optional managed-header policy value."""

    if value is None:
        return None
    if value not in {"inherit", "enabled", "disabled"}:
        raise ValueError(
            f"{source} stores invalid managed-header policy {value!r}; expected "
            "`inherit`, `enabled`, or `disabled`."
        )
    return value


def resolve_managed_prompt_header_decision(
    *,
    launch_override: bool | None,
    stored_policy: ManagedHeaderPolicy | None,
    default_enabled: bool = True,
) -> ManagedPromptHeaderDecision:
    """Resolve whether the managed prompt header is enabled for one launch."""

    if launch_override is not None:
        return ManagedPromptHeaderDecision(
            enabled=launch_override,
            resolution_source="launch_override",
            stored_policy=stored_policy,
        )
    if stored_policy in {"enabled", "disabled"}:
        return ManagedPromptHeaderDecision(
            enabled=stored_policy == "enabled",
            resolution_source="launch_profile",
            stored_policy=stored_policy,
        )
    return ManagedPromptHeaderDecision(
        enabled=default_enabled,
        resolution_source="default",
        stored_policy=stored_policy,
    )


def resolve_managed_launch_identity(
    *,
    tool: str,
    role_name: str,
    requested_agent_name: str | None,
    requested_agent_id: str | None,
) -> ResolvedManagedLaunchIdentity:
    """Resolve managed identity for launch-prompt rendering and build metadata."""

    if requested_agent_name is not None:
        agent_name = normalize_user_managed_agent_name(requested_agent_name)
    else:
        agent_name = derive_default_canonical_agent_name(tool=tool, role_name=role_name)
    agent_id = (
        normalize_managed_agent_id(requested_agent_id)
        if requested_agent_id is not None
        else derive_agent_id_from_name(agent_name)
    )
    return ResolvedManagedLaunchIdentity(
        agent_name=agent_name,
        agent_id=agent_id,
    )


def compose_prompt_overlay(
    *,
    base_prompt: str,
    overlay_mode: str | None,
    overlay_text: str | None,
) -> str:
    """Compose one effective prompt from the base prompt and optional overlay."""

    if overlay_mode is None or overlay_text is None:
        return base_prompt
    if overlay_mode == "replace":
        return overlay_text.rstrip()
    if overlay_mode != "append":
        raise ValueError(
            f"Unsupported prompt-overlay mode {overlay_mode!r}; expected `append` or `replace`."
        )
    if not base_prompt:
        return overlay_text.rstrip()
    return f"{base_prompt.rstrip()}\n\n{overlay_text.rstrip()}".rstrip()


def render_managed_prompt_header(
    *,
    agent_name: str,
    agent_id: str,
) -> str:
    """Render the Houmao-managed prompt header for one managed launch."""

    return (
        "[HOUMAO MANAGED HEADER]\n\n"
        "You are running as a Houmao-managed agent.\n"
        f"Managed agent name: {agent_name}\n"
        f"Managed agent id: {agent_id}\n\n"
        "When work involves Houmao-managed runtime behavior, managed services, agent "
        "coordination, lifecycle control, mailbox or gateway access, reminders, or system "
        "state discovery:\n"
        "- prefer bundled Houmao guidance for the workflow\n"
        "- use `houmao-mgr` as the canonical direct interface for interacting with the Houmao system\n"
        "- treat Houmao-managed manifests, runtime metadata, and supported service interfaces as authoritative\n"
        "- avoid relying on ad hoc probing of tmux state, random files, or unsupported internal "
        "paths when a supported Houmao interface exists\n\n"
        "For ordinary domain work, follow the task normally. Use Houmao-specific guidance and "
        "interfaces when the task is actually about Houmao-managed capabilities.\n\n"
        "[HOUMAO MANAGED HEADER END]"
    )


def compose_managed_launch_prompt(
    *,
    base_prompt: str,
    overlay_mode: str | None,
    overlay_text: str | None,
    managed_header_enabled: bool,
    agent_name: str,
    agent_id: str,
) -> str:
    """Compose the effective launch prompt for one managed launch."""

    effective_prompt = compose_prompt_overlay(
        base_prompt=base_prompt,
        overlay_mode=overlay_mode,
        overlay_text=overlay_text,
    )
    if not managed_header_enabled:
        return effective_prompt
    header = render_managed_prompt_header(
        agent_name=agent_name,
        agent_id=agent_id,
    )
    if not effective_prompt:
        return header
    return f"{header}\n\n{effective_prompt}".rstrip()


def managed_prompt_header_metadata(
    *,
    decision: ManagedPromptHeaderDecision,
    identity: ResolvedManagedLaunchIdentity,
) -> dict[str, Any]:
    """Return structured managed-header metadata for manifest persistence."""

    return {
        "version": MANAGED_PROMPT_HEADER_VERSION,
        "enabled": decision.enabled,
        "resolution_source": decision.resolution_source,
        "stored_policy": decision.stored_policy,
        "agent_name": identity.agent_name,
        "agent_id": identity.agent_id,
    }
