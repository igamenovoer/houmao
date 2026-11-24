from __future__ import annotations

import pytest

from houmao.agents.managed_prompt_header import (
    MANAGED_PROMPT_HEADER_VERSION,
    ResolvedManagedLaunchIdentity,
    compose_managed_launch_prompt,
    compose_managed_launch_prompt_payload,
    managed_prompt_header_metadata,
    render_managed_prompt_header,
    resolve_managed_prompt_header_decision,
    resolve_managed_prompt_header_section_decisions,
)

_MEMO_FILE = "/tmp/houmao/memory/agents/agent-alice/houmao-memo.md"


def test_compose_managed_launch_prompt_payload_renders_structured_sections_in_order() -> None:
    payload = compose_managed_launch_prompt_payload(
        base_prompt="You are a precise repo researcher.",
        overlay_mode="append",
        overlay_text="Prefer Alice repository conventions.",
        appendix_text="Treat gateway diagnostics as high priority.",
        managed_header_enabled=True,
        agent_name="alice",
        agent_id="agent-alice",
        memo_file=_MEMO_FILE,
    )

    assert payload.prompt.startswith('<houmao_system_prompt version="1">\n\n<managed_header>\n\n')
    assert payload.prompt.endswith(
        "</launch_appendix>\n\n</prompt_body>\n\n</houmao_system_prompt>"
    )
    assert payload.prompt.index("<managed_header>") < payload.prompt.index("<prompt_body>")
    assert payload.prompt.index("<identity>") < payload.prompt.index("<memo_cue>")
    assert payload.prompt.index("<memo_cue>") < payload.prompt.index("<houmao_runtime_guidance>")
    assert payload.prompt.index("<houmao_runtime_guidance>") < payload.prompt.index(
        "<automation_notice>"
    )
    assert "</identity>\n\n<memo_cue>" in payload.prompt
    assert "</memo_cue>\n\n<houmao_runtime_guidance>" in payload.prompt
    assert "</houmao_runtime_guidance>\n\n<automation_notice>" in payload.prompt
    assert "</automation_notice>\n\n</managed_header>\n\n<prompt_body>\n\n<role_prompt>" in (
        payload.prompt
    )
    assert '</role_prompt>\n\n<launch_profile_overlay mode="append">' in payload.prompt
    assert '</launch_profile_overlay>\n\n<launch_appendix source="launch_option">' in payload.prompt
    assert "<task_reminder>" not in payload.prompt
    assert "<mail_ack>" not in payload.prompt
    assert "Agent type: Houmao-managed agent" in payload.prompt
    assert "Agent name: alice" in payload.prompt
    assert "Agent ID: agent-alice" in payload.prompt
    assert f"Memo file: {_MEMO_FILE}" in payload.prompt
    assert "- Read every turn: Read this file before planning or acting." in payload.prompt
    assert "unless system, developer, or user instructions override them" in payload.prompt
    assert "Open linked `pages/` notes when relevant" in payload.prompt
    assert "without merely stating that you read it" in payload.prompt
    assert (
        "- Write sparingly: Update this file only when asked or when an entry is clearly outdated."
        in payload.prompt
    )
    assert "current facts, standing rules, and links to `pages/` notes" in payload.prompt
    assert (
        "1. Look for installed `houmao-*` skills (especially entrypoint skills) for guidance first."
        in payload.prompt
    )
    assert (
        "2. Use `houmao-mgr` as the canonical CLI, and rely on Houmao manifests and service APIs."
        in payload.prompt
    )
    assert (
        "3. Do not probe raw `tmux` sessions or internal runtime files when a supported Houmao "
        "skill or command exists." in payload.prompt
    )
    assert payload.prompt.index("houmao-*") < payload.prompt.index("houmao-mgr")
    assert "houmao-agent-entrypoint" not in payload.prompt
    assert "houmao-admin-entrypoint" not in payload.prompt
    assert "Execution mode: Unattended (no human at the terminal)." in payload.prompt
    assert "DO NOT call Claude's `AskUserQuestion`" in payload.prompt
    assert "- Normal tasks: Decide on your own using available context." in payload.prompt
    assert "- Mailbox tasks (reply-enabled thread): Reply to that thread" in payload.prompt
    assert "- Mailbox tasks (no-reply thread): Decide on your own using available context." in (
        payload.prompt
    )
    assert payload.prompt.index("<role_prompt>") < payload.prompt.index("<launch_profile_overlay")
    assert payload.prompt.index("<launch_profile_overlay") < payload.prompt.index(
        "<launch_appendix"
    )
    header_only = render_managed_prompt_header(
        agent_name="alice",
        agent_id="agent-alice",
        memo_file=_MEMO_FILE,
    )
    assert "</identity>\n\n<memo_cue>" in header_only
    header_metadata = managed_prompt_header_metadata(
        decision=resolve_managed_prompt_header_decision(launch_override=None, stored_policy=None),
        identity=ResolvedManagedLaunchIdentity(agent_name="alice", agent_id="agent-alice"),
    )
    assert MANAGED_PROMPT_HEADER_VERSION == 2
    assert header_metadata["version"] == 2
    assert payload.layout == {
        "version": 1,
        "root_tag": "houmao_system_prompt",
        "sections": [
            {
                "kind": "managed_header",
                "sections": [
                    {"kind": "identity"},
                    {"kind": "memo_cue"},
                    {"kind": "houmao_runtime_guidance"},
                    {"kind": "automation_notice"},
                ],
            },
            {
                "kind": "prompt_body",
                "sections": [
                    {"kind": "role_prompt"},
                    {
                        "kind": "launch_profile_overlay",
                        "attributes": {"mode": "append"},
                    },
                    {
                        "kind": "launch_appendix",
                        "attributes": {"source": "launch_option"},
                    },
                ],
            },
        ],
        "managed_header": {
            "enabled": True,
            "sections": {
                "identity": {
                    "tag": "identity",
                    "enabled": True,
                    "rendered": True,
                    "resolution_source": "default",
                    "stored_policy": None,
                    "default_enabled": True,
                },
                "memo-cue": {
                    "tag": "memo_cue",
                    "enabled": True,
                    "rendered": True,
                    "resolution_source": "default",
                    "stored_policy": None,
                    "default_enabled": True,
                },
                "houmao-runtime-guidance": {
                    "tag": "houmao_runtime_guidance",
                    "enabled": True,
                    "rendered": True,
                    "resolution_source": "default",
                    "stored_policy": None,
                    "default_enabled": True,
                },
                "automation-notice": {
                    "tag": "automation_notice",
                    "enabled": True,
                    "rendered": True,
                    "resolution_source": "default",
                    "stored_policy": None,
                    "default_enabled": True,
                },
                "task-reminder": {
                    "tag": "task_reminder",
                    "enabled": False,
                    "rendered": False,
                    "resolution_source": "default",
                    "stored_policy": None,
                    "default_enabled": False,
                },
                "mail-ack": {
                    "tag": "mail_ack",
                    "enabled": False,
                    "rendered": False,
                    "resolution_source": "default",
                    "stored_policy": None,
                    "default_enabled": False,
                },
            },
        },
    }


def test_compose_managed_launch_prompt_replace_overlay_omits_role_section() -> None:
    prompt = compose_managed_launch_prompt(
        base_prompt="You are a precise repo researcher.",
        overlay_mode="replace",
        overlay_text="Work only on Alice-owned repositories.",
        appendix_text="Escalate unexpected gateway failures.",
        managed_header_enabled=True,
        agent_name="alice",
        agent_id="agent-alice",
        memo_file=_MEMO_FILE,
    )

    assert "<role_prompt>" not in prompt
    assert '<launch_profile_overlay mode="replace">' in prompt
    assert '<launch_appendix source="launch_option">' in prompt


def test_compose_managed_launch_prompt_can_enable_default_off_sections() -> None:
    section_decisions = resolve_managed_prompt_header_section_decisions(
        launch_overrides={
            "automation-notice": "disabled",
            "task-reminder": "enabled",
            "mail-ack": "enabled",
        },
        stored_policy=None,
    )

    payload = compose_managed_launch_prompt_payload(
        base_prompt="",
        overlay_mode=None,
        overlay_text=None,
        managed_header_enabled=True,
        agent_name="alice",
        agent_id="agent-alice",
        memo_file=_MEMO_FILE,
        managed_header_section_decisions=section_decisions,
    )

    assert "<automation_notice>" not in payload.prompt
    assert payload.prompt.index("<identity>") < payload.prompt.index("<memo_cue>")
    assert payload.prompt.index("<memo_cue>") < payload.prompt.index("<houmao_runtime_guidance>")
    assert payload.prompt.index("<houmao_runtime_guidance>") < payload.prompt.index(
        "<task_reminder>"
    )
    assert payload.prompt.index("<task_reminder>") < payload.prompt.index("<mail_ack>")
    assert "explicitly asked for a self-reminder" in payload.prompt
    assert "concrete supervision or finalization check" in payload.prompt
    assert (
        "sending a required reply, writing a required file, or verifying agent or loop health"
        in payload.prompt
    )
    assert "Name the exact check the reminder guards, and delete the reminder once satisfied." in (
        payload.prompt
    )
    assert "keep using your local todo list, memo, or working state" in payload.prompt
    assert "10 seconds" not in payload.prompt
    assert "potentially long-running work" not in payload.prompt
    assert "send a concise acknowledgement reply" in payload.prompt
    assert payload.layout["managed_header"]["sections"]["automation-notice"] == {
        "tag": "automation_notice",
        "enabled": False,
        "rendered": False,
        "resolution_source": "launch_override",
        "stored_policy": None,
        "default_enabled": True,
    }
    assert payload.layout["managed_header"]["sections"]["task-reminder"] == {
        "tag": "task_reminder",
        "enabled": True,
        "rendered": True,
        "resolution_source": "launch_override",
        "stored_policy": None,
        "default_enabled": False,
    }


def test_compose_managed_launch_prompt_can_disable_memo_cue_without_memo_file() -> None:
    section_decisions = resolve_managed_prompt_header_section_decisions(
        launch_overrides={"memo-cue": "disabled"},
        stored_policy=None,
    )

    prompt = compose_managed_launch_prompt(
        base_prompt="You are a precise repo researcher.",
        overlay_mode=None,
        overlay_text=None,
        managed_header_enabled=True,
        agent_name="alice",
        agent_id="agent-alice",
        managed_header_section_decisions=section_decisions,
    )

    assert "<memo_cue>" not in prompt
    assert "<houmao_runtime_guidance>" in prompt


def test_compose_managed_launch_prompt_requires_memo_file_for_default_memo_cue() -> None:
    with pytest.raises(ValueError, match="memo-cue"):
        compose_managed_launch_prompt(
            base_prompt="You are a precise repo researcher.",
            overlay_mode=None,
            overlay_text=None,
            managed_header_enabled=True,
            agent_name="alice",
            agent_id="agent-alice",
        )


def test_whole_header_disable_suppresses_enabled_section_policy() -> None:
    section_decisions = resolve_managed_prompt_header_section_decisions(
        launch_overrides={"task-reminder": "enabled", "mail-ack": "enabled"},
        stored_policy={"automation-notice": "enabled"},
    )

    payload = compose_managed_launch_prompt_payload(
        base_prompt="Body only.",
        overlay_mode=None,
        overlay_text=None,
        managed_header_enabled=False,
        agent_name="alice",
        agent_id="agent-alice",
        managed_header_section_decisions=section_decisions,
    )

    assert "<managed_header>" not in payload.prompt
    assert "<prompt_body>" in payload.prompt
    assert payload.layout["sections"] == [
        {"kind": "prompt_body", "sections": [{"kind": "role_prompt"}]}
    ]
    assert payload.layout["managed_header"]["enabled"] is False
    assert all(
        not section["rendered"] for section in payload.layout["managed_header"]["sections"].values()
    )


def test_section_resolution_prefers_launch_override_over_stored_policy() -> None:
    decisions = resolve_managed_prompt_header_section_decisions(
        launch_overrides={"automation-notice": "enabled"},
        stored_policy={"automation-notice": "disabled", "mail-ack": "enabled"},
    )

    assert decisions["automation-notice"].enabled is True
    assert decisions["automation-notice"].resolution_source == "launch_override"
    assert decisions["automation-notice"].stored_policy == "disabled"
    assert decisions["mail-ack"].enabled is True
    assert decisions["mail-ack"].resolution_source == "launch_profile"
