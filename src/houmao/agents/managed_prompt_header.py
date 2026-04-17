"""Managed launch prompt-composition helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from houmao.agents.realm_controller.agent_identity import (
    derive_agent_id_from_name,
    derive_default_canonical_agent_name,
    normalize_managed_agent_id,
    normalize_user_managed_agent_name,
)

ManagedHeaderPolicy = Literal["inherit", "enabled", "disabled"]
ManagedHeaderResolutionSource = Literal["default", "launch_profile", "launch_override"]
ManagedHeaderSectionName = Literal[
    "identity",
    "memo-cue",
    "houmao-runtime-guidance",
    "automation-notice",
    "task-reminder",
    "mail-ack",
]
ManagedHeaderSectionPolicy = Literal["enabled", "disabled"]
ManagedHeaderSectionResolutionSource = Literal["default", "launch_profile", "launch_override"]
MANAGED_PROMPT_HEADER_VERSION = 1
HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION = 1
MANAGED_HEADER_SECTION_ORDER: tuple[ManagedHeaderSectionName, ...] = (
    "identity",
    "memo-cue",
    "houmao-runtime-guidance",
    "automation-notice",
    "task-reminder",
    "mail-ack",
)
MANAGED_HEADER_SECTION_DEFAULTS: dict[ManagedHeaderSectionName, bool] = {
    "identity": True,
    "memo-cue": True,
    "houmao-runtime-guidance": True,
    "automation-notice": True,
    "task-reminder": False,
    "mail-ack": False,
}
MANAGED_HEADER_SECTION_TAGS: dict[ManagedHeaderSectionName, str] = {
    "identity": "identity",
    "memo-cue": "memo_cue",
    "houmao-runtime-guidance": "houmao_runtime_guidance",
    "automation-notice": "automation_notice",
    "task-reminder": "task_reminder",
    "mail-ack": "mail_ack",
}
MANAGED_HEADER_SECTION_POLICIES: frozenset[ManagedHeaderSectionPolicy] = frozenset(
    {"enabled", "disabled"}
)


@dataclass(frozen=True)
class ManagedLaunchPromptSection:
    """One rendered prompt section within the Houmao system-prompt layout."""

    tag: str
    text: str
    attributes: dict[str, str] = field(default_factory=dict)
    children: tuple["ManagedLaunchPromptSection", ...] = ()


@dataclass(frozen=True)
class ManagedLaunchPromptPayload:
    """Rendered prompt text plus secret-free layout metadata."""

    prompt: str
    layout: dict[str, Any]


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


@dataclass(frozen=True)
class ManagedHeaderSectionDecision:
    """Resolved policy for one managed-header subsection."""

    name: ManagedHeaderSectionName
    tag: str
    enabled: bool
    resolution_source: ManagedHeaderSectionResolutionSource
    stored_policy: ManagedHeaderSectionPolicy | None


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
    return cast(ManagedHeaderPolicy, value)


def normalize_managed_header_section_name(
    value: str,
    *,
    source: str,
) -> ManagedHeaderSectionName:
    """Validate one managed-header section identifier."""

    candidate = value.strip()
    if candidate not in MANAGED_HEADER_SECTION_ORDER:
        expected = ", ".join(f"`{section}`" for section in MANAGED_HEADER_SECTION_ORDER)
        raise ValueError(
            f"{source} uses unsupported managed-header section {value!r}; expected one of "
            f"{expected}."
        )
    return cast(ManagedHeaderSectionName, candidate)


def normalize_managed_header_section_policy(
    value: str | None,
    *,
    source: str,
) -> ManagedHeaderSectionPolicy | None:
    """Validate one optional managed-header section policy value."""

    if value is None:
        return None
    candidate = value.strip()
    if candidate not in MANAGED_HEADER_SECTION_POLICIES:
        expected = ", ".join(f"`{policy}`" for policy in sorted(MANAGED_HEADER_SECTION_POLICIES))
        raise ValueError(
            f"{source} uses unsupported managed-header section policy {value!r}; "
            f"expected {expected}."
        )
    return cast(ManagedHeaderSectionPolicy, candidate)


def normalize_managed_header_section_policy_mapping(
    value: Mapping[Any, Any] | None,
    *,
    source: str,
) -> dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy]:
    """Validate one stored or one-shot managed-header section policy mapping."""

    if value is None:
        return {}
    normalized: dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy] = {}
    for raw_name, raw_policy in value.items():
        if not isinstance(raw_name, str):
            raise ValueError(f"{source} stores a non-string managed-header section name.")
        if not isinstance(raw_policy, str):
            raise ValueError(
                f"{source} stores non-string policy for managed-header section {raw_name!r}."
            )
        section_name = normalize_managed_header_section_name(raw_name, source=source)
        section_policy = normalize_managed_header_section_policy(
            raw_policy,
            source=f"{source}.{section_name}",
        )
        assert section_policy is not None
        normalized[section_name] = section_policy
    return normalized


def parse_managed_header_section_policy_assignment(
    value: str,
    *,
    source: str,
) -> tuple[ManagedHeaderSectionName, ManagedHeaderSectionPolicy]:
    """Parse one ``SECTION=STATE`` managed-header section policy assignment."""

    section_text, separator, policy_text = value.partition("=")
    if separator != "=" or not section_text.strip() or not policy_text.strip():
        raise ValueError(f"{source} must use SECTION=STATE syntax.")
    section_name = normalize_managed_header_section_name(section_text, source=source)
    section_policy = normalize_managed_header_section_policy(
        policy_text,
        source=f"{source} `{section_name}`",
    )
    assert section_policy is not None
    return section_name, section_policy


def parse_managed_header_section_policy_assignments(
    values: tuple[str, ...],
    *,
    source: str,
) -> dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy]:
    """Parse repeatable ``SECTION=STATE`` managed-header section policy inputs."""

    parsed: dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy] = {}
    for raw_value in values:
        section_name, section_policy = parse_managed_header_section_policy_assignment(
            raw_value,
            source=source,
        )
        if section_name in parsed:
            raise ValueError(
                f"{source} repeats managed-header section `{section_name}`; provide each "
                "section at most once."
            )
        parsed[section_name] = section_policy
    return parsed


def parse_managed_header_section_names(
    values: tuple[str, ...],
    *,
    source: str,
) -> tuple[ManagedHeaderSectionName, ...]:
    """Parse repeatable managed-header section identifiers."""

    parsed: list[ManagedHeaderSectionName] = []
    seen: set[ManagedHeaderSectionName] = set()
    for raw_value in values:
        section_name = normalize_managed_header_section_name(raw_value, source=source)
        if section_name in seen:
            raise ValueError(
                f"{source} repeats managed-header section `{section_name}`; provide each "
                "section at most once."
            )
        seen.add(section_name)
        parsed.append(section_name)
    return tuple(parsed)


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


def resolve_managed_prompt_header_section_decisions(
    *,
    launch_overrides: Mapping[Any, Any] | None,
    stored_policy: Mapping[Any, Any] | None,
) -> dict[ManagedHeaderSectionName, ManagedHeaderSectionDecision]:
    """Resolve managed-header subsection policy for one launch."""

    normalized_launch_overrides = normalize_managed_header_section_policy_mapping(
        launch_overrides,
        source="launch managed-header section overrides",
    )
    normalized_stored_policy = normalize_managed_header_section_policy_mapping(
        stored_policy,
        source="stored managed-header section policy",
    )
    decisions: dict[ManagedHeaderSectionName, ManagedHeaderSectionDecision] = {}
    for section_name in MANAGED_HEADER_SECTION_ORDER:
        stored_section_policy = normalized_stored_policy.get(section_name)
        if section_name in normalized_launch_overrides:
            section_policy = normalized_launch_overrides[section_name]
            enabled = section_policy == "enabled"
            resolution_source: ManagedHeaderSectionResolutionSource = "launch_override"
        elif stored_section_policy is not None:
            section_policy = stored_section_policy
            enabled = section_policy == "enabled"
            resolution_source = "launch_profile"
        else:
            enabled = MANAGED_HEADER_SECTION_DEFAULTS[section_name]
            resolution_source = "default"
        decisions[section_name] = ManagedHeaderSectionDecision(
            name=section_name,
            tag=MANAGED_HEADER_SECTION_TAGS[section_name],
            enabled=enabled,
            resolution_source=resolution_source,
            stored_policy=stored_section_policy,
        )
    return decisions


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


def _normalize_prompt_text(value: str | None) -> str | None:
    """Return one prompt fragment with trailing space trimmed when non-empty."""

    if value is None:
        return None
    normalized = value.rstrip()
    if not normalized.strip():
        return None
    return normalized


def _escape_xml_attribute(value: str) -> str:
    """Escape one XML attribute value for deterministic prompt rendering."""

    return (
        value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _render_prompt_section(section: ManagedLaunchPromptSection) -> str:
    """Render one section into the Houmao-owned XML-like prompt layout."""

    attributes = "".join(
        f' {key}="{_escape_xml_attribute(value)}"'
        for key, value in sorted(section.attributes.items())
    )
    opening_tag = f"<{section.tag}{attributes}>"
    if section.children:
        content = "\n".join(_render_prompt_section(child) for child in section.children)
    else:
        content = section.text.rstrip()
    return f"{opening_tag}\n{content}\n</{section.tag}>"


def _layout_metadata_for_section(section: ManagedLaunchPromptSection) -> dict[str, Any]:
    """Return one secret-free metadata payload for a rendered prompt section."""

    payload: dict[str, Any] = {"kind": section.tag}
    if section.attributes:
        payload["attributes"] = dict(sorted(section.attributes.items()))
    if section.children:
        payload["sections"] = [_layout_metadata_for_section(child) for child in section.children]
    return payload


def _ordered_section_decisions(
    decisions: Mapping[ManagedHeaderSectionName, ManagedHeaderSectionDecision] | None,
) -> tuple[ManagedHeaderSectionDecision, ...]:
    """Return section decisions in deterministic render order."""

    if decisions is None:
        decisions = resolve_managed_prompt_header_section_decisions(
            launch_overrides=None,
            stored_policy=None,
        )
    return tuple(decisions[section_name] for section_name in MANAGED_HEADER_SECTION_ORDER)


def _identity_section(*, agent_name: str, agent_id: str) -> ManagedLaunchPromptSection:
    """Render the identity managed-header subsection."""

    return ManagedLaunchPromptSection(
        tag="identity",
        text=(
            "You are running as a Houmao-managed agent.\n"
            f"Managed agent name: {agent_name}\n"
            f"Managed agent id: {agent_id}"
        ),
    )


def _memo_cue_section(*, memo_file: str) -> ManagedLaunchPromptSection:
    """Render the managed-agent memo cue subsection."""

    normalized_memo_file = memo_file.strip()
    if not normalized_memo_file:
        raise ValueError("Managed prompt-header `memo-cue` requires a memo file path.")
    return ManagedLaunchPromptSection(
        tag="memo_cue",
        text=(
            "Mandatory: before planning or acting, read this Houmao-managed agent memo at "
            "every prompt turn, new dialog, topic change, after compaction, or cleared "
            "context:\n"
            f"{normalized_memo_file}\n\n"
            "Use it only for concise working rules, standing constraints, and current "
            "facts; never as a log, journal, transcript, or scratchpad. Put long details "
            "in `pages/`, keeping only a short memo note with a memo-relative link such as "
            "`pages/notes/todo.md`. Update it only when explicitly asked (`add to memo`, "
            "`update the houmao memo`) or when changed facts make existing content "
            "obviously stale."
        ),
    )


def _houmao_runtime_guidance_section() -> ManagedLaunchPromptSection:
    """Render the Houmao runtime guidance managed-header subsection."""

    return ManagedLaunchPromptSection(
        tag="houmao_runtime_guidance",
        text=(
            "When work involves Houmao-managed runtime behavior, managed services, agent "
            "coordination, lifecycle control, mailbox or gateway access, reminders, or system "
            "state discovery:\n"
            "- prefer bundled Houmao guidance for the workflow\n"
            "- use `houmao-mgr` as the canonical direct interface for interacting with the Houmao system\n"
            "- treat Houmao-managed manifests, runtime metadata, and supported service interfaces as authoritative\n"
            "- avoid relying on ad hoc probing of tmux state, random files, or unsupported internal "
            "paths when a supported Houmao interface exists\n\n"
            "For ordinary domain work, follow the task normally. Use Houmao-specific guidance and "
            "interfaces when the task is actually about Houmao-managed capabilities."
        ),
    )


def _automation_notice_section() -> ManagedLaunchPromptSection:
    """Render the automation notice managed-header subsection."""

    return ManagedLaunchPromptSection(
        tag="automation_notice",
        text=(
            "You are running in fully automated mode.\n\n"
            "DO NOT call Claude's AskUserQuestion tool. DO NOT use any equivalent interactive "
            "user-question tool that would open or focus an operator TUI panel.\n\n"
            "Make decisions on your own with available context, including when clarification is unavailable.\n\n"
            "For mailbox-driven work, DO NOT ask the interactive operator for clarification. If "
            "the relevant mailbox thread is reply-enabled, reply to that thread with a focused "
            "clarification question. If the thread is not reply-enabled, decide on your own with "
            "available context. This applies both when the ambiguity is in the message itself and "
            "when it appears while carrying out work requested by that message. Treat the mailbox "
            "sender as the likely upstream coordinator, often another agent."
        ),
    )


def _task_reminder_section() -> ManagedLaunchPromptSection:
    """Render the task reminder managed-header subsection."""

    return ManagedLaunchPromptSection(
        tag="task_reminder",
        text=(
            "When starting potentially long-running work, such as processing email, create a "
            "one-off reminder on the live gateway to remind yourself to verify final output "
            "actions are complete before finishing. Use a default notification check delay of "
            "10 seconds. The reminder should name the expected final action, such as replying "
            "to mail or writing a required file. Delete or otherwise turn off that reminder "
            "when the task is done."
        ),
    )


def _mail_ack_section() -> ManagedLaunchPromptSection:
    """Render the mail acknowledgement managed-header subsection."""

    return ManagedLaunchPromptSection(
        tag="mail_ack",
        text=(
            "For mailbox-driven work, always send a concise acknowledgement to the "
            "reply-enabled address before doing substantive work."
        ),
    )


def _render_section_for_decision(
    *,
    decision: ManagedHeaderSectionDecision,
    agent_name: str,
    agent_id: str,
    memo_file: str | None,
) -> ManagedLaunchPromptSection:
    """Render one enabled managed-header subsection for a resolved decision."""

    if decision.name == "identity":
        return _identity_section(agent_name=agent_name, agent_id=agent_id)
    if decision.name == "memo-cue":
        if memo_file is None:
            raise ValueError("Managed prompt-header `memo-cue` requires a memo file path.")
        return _memo_cue_section(memo_file=memo_file)
    if decision.name == "houmao-runtime-guidance":
        return _houmao_runtime_guidance_section()
    if decision.name == "automation-notice":
        return _automation_notice_section()
    if decision.name == "task-reminder":
        return _task_reminder_section()
    if decision.name == "mail-ack":
        return _mail_ack_section()
    raise ValueError(f"Unsupported managed-header section decision: {decision.name!r}")


def _managed_prompt_header_sections(
    *,
    agent_name: str,
    agent_id: str,
    memo_file: str | None,
    section_decisions: Mapping[ManagedHeaderSectionName, ManagedHeaderSectionDecision] | None,
) -> tuple[ManagedLaunchPromptSection, ...]:
    """Render enabled managed-header subsections in deterministic order."""

    sections: list[ManagedLaunchPromptSection] = []
    for decision in _ordered_section_decisions(section_decisions):
        if not decision.enabled:
            continue
        sections.append(
            _render_section_for_decision(
                decision=decision,
                agent_name=agent_name,
                agent_id=agent_id,
                memo_file=memo_file,
            )
        )
    return tuple(sections)


def render_managed_prompt_header(
    *,
    agent_name: str,
    agent_id: str,
    memo_file: str | None = None,
    section_decisions: Mapping[ManagedHeaderSectionName, ManagedHeaderSectionDecision]
    | None = None,
) -> str:
    """Render the Houmao-managed prompt header for one managed launch."""

    return "\n".join(
        _render_prompt_section(section)
        for section in _managed_prompt_header_sections(
            agent_name=agent_name,
            agent_id=agent_id,
            memo_file=memo_file,
            section_decisions=section_decisions,
        )
    )


def _section_decision_metadata(
    *,
    decision: ManagedHeaderSectionDecision,
    header_enabled: bool,
) -> dict[str, Any]:
    """Return secret-free metadata for one section decision."""

    return {
        "tag": decision.tag,
        "enabled": decision.enabled,
        "rendered": header_enabled and decision.enabled,
        "resolution_source": decision.resolution_source,
        "stored_policy": decision.stored_policy,
        "default_enabled": MANAGED_HEADER_SECTION_DEFAULTS[decision.name],
    }


def _section_decisions_metadata(
    *,
    section_decisions: Mapping[ManagedHeaderSectionName, ManagedHeaderSectionDecision] | None,
    header_enabled: bool,
) -> dict[str, Any]:
    """Return secret-free metadata for every managed-header section decision."""

    return {
        decision.name: _section_decision_metadata(
            decision=decision,
            header_enabled=header_enabled,
        )
        for decision in _ordered_section_decisions(section_decisions)
    }


def compose_managed_launch_prompt_payload(
    *,
    base_prompt: str,
    overlay_mode: str | None,
    overlay_text: str | None,
    appendix_text: str | None = None,
    managed_header_enabled: bool,
    agent_name: str,
    agent_id: str,
    memo_file: str | None = None,
    managed_header_section_decisions: Mapping[
        ManagedHeaderSectionName, ManagedHeaderSectionDecision
    ]
    | None = None,
) -> ManagedLaunchPromptPayload:
    """Compose the structured effective launch prompt for one managed launch."""

    normalized_base_prompt = _normalize_prompt_text(base_prompt)
    normalized_overlay_text = _normalize_prompt_text(overlay_text)
    normalized_appendix_text = _normalize_prompt_text(appendix_text)

    body_sections: list[ManagedLaunchPromptSection] = []
    if overlay_mode == "replace" and normalized_overlay_text is not None:
        body_sections.append(
            ManagedLaunchPromptSection(
                tag="launch_profile_overlay",
                text=normalized_overlay_text,
                attributes={"mode": "replace"},
            )
        )
    else:
        if normalized_base_prompt is not None:
            body_sections.append(
                ManagedLaunchPromptSection(
                    tag="role_prompt",
                    text=normalized_base_prompt,
                )
            )
        if normalized_overlay_text is not None:
            overlay_attributes = {"mode": "append"} if overlay_mode == "append" else {}
            body_sections.append(
                ManagedLaunchPromptSection(
                    tag="launch_profile_overlay",
                    text=normalized_overlay_text,
                    attributes=overlay_attributes,
                )
            )
    if normalized_appendix_text is not None:
        body_sections.append(
            ManagedLaunchPromptSection(
                tag="launch_appendix",
                text=normalized_appendix_text,
                attributes={"source": "launch_option"},
            )
        )

    root_sections: list[ManagedLaunchPromptSection] = []
    managed_header_sections: tuple[ManagedLaunchPromptSection, ...] = ()
    if managed_header_enabled:
        managed_header_sections = _managed_prompt_header_sections(
            agent_name=agent_name,
            agent_id=agent_id,
            memo_file=memo_file,
            section_decisions=managed_header_section_decisions,
        )
    if managed_header_sections:
        root_sections.append(
            ManagedLaunchPromptSection(
                tag="managed_header",
                text="",
                children=managed_header_sections,
            )
        )
    if body_sections:
        root_sections.append(
            ManagedLaunchPromptSection(
                tag="prompt_body",
                text="",
                children=tuple(body_sections),
            )
        )

    layout = {
        "version": HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION,
        "root_tag": "houmao_system_prompt",
        "sections": [_layout_metadata_for_section(section) for section in root_sections],
        "managed_header": {
            "enabled": managed_header_enabled,
            "sections": _section_decisions_metadata(
                section_decisions=managed_header_section_decisions,
                header_enabled=managed_header_enabled,
            ),
        },
    }
    if not root_sections:
        return ManagedLaunchPromptPayload(prompt="", layout=layout)

    root = ManagedLaunchPromptSection(
        tag="houmao_system_prompt",
        text="",
        attributes={"version": str(HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION)},
        children=tuple(root_sections),
    )
    return ManagedLaunchPromptPayload(
        prompt=_render_prompt_section(root).rstrip(),
        layout=layout,
    )


def compose_managed_launch_prompt(
    *,
    base_prompt: str,
    overlay_mode: str | None,
    overlay_text: str | None,
    appendix_text: str | None = None,
    managed_header_enabled: bool,
    agent_name: str,
    agent_id: str,
    memo_file: str | None = None,
    managed_header_section_decisions: Mapping[
        ManagedHeaderSectionName, ManagedHeaderSectionDecision
    ]
    | None = None,
) -> str:
    """Compose the effective launch prompt for one managed launch."""

    return compose_managed_launch_prompt_payload(
        base_prompt=base_prompt,
        overlay_mode=overlay_mode,
        overlay_text=overlay_text,
        appendix_text=appendix_text,
        managed_header_enabled=managed_header_enabled,
        agent_name=agent_name,
        agent_id=agent_id,
        memo_file=memo_file,
        managed_header_section_decisions=managed_header_section_decisions,
    ).prompt


def managed_prompt_header_metadata(
    *,
    decision: ManagedPromptHeaderDecision,
    identity: ResolvedManagedLaunchIdentity,
    section_decisions: Mapping[ManagedHeaderSectionName, ManagedHeaderSectionDecision]
    | None = None,
) -> dict[str, Any]:
    """Return structured managed-header metadata for manifest persistence."""

    return {
        "version": MANAGED_PROMPT_HEADER_VERSION,
        "enabled": decision.enabled,
        "resolution_source": decision.resolution_source,
        "stored_policy": decision.stored_policy,
        "agent_name": identity.agent_name,
        "agent_id": identity.agent_id,
        "sections": _section_decisions_metadata(
            section_decisions=section_decisions,
            header_enabled=decision.enabled,
        ),
    }
