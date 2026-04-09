from __future__ import annotations

from houmao.agents.managed_prompt_header import (
    compose_managed_launch_prompt,
    compose_managed_launch_prompt_payload,
)


def test_compose_managed_launch_prompt_payload_renders_structured_sections_in_order() -> None:
    payload = compose_managed_launch_prompt_payload(
        base_prompt="You are a precise repo researcher.",
        overlay_mode="append",
        overlay_text="Prefer Alice repository conventions.",
        appendix_text="Treat gateway diagnostics as high priority.",
        managed_header_enabled=True,
        agent_name="alice",
        agent_id="agent-alice",
    )

    assert payload.prompt.startswith('<houmao_system_prompt version="1">')
    assert payload.prompt.index("<managed_header>") < payload.prompt.index("<prompt_body>")
    assert payload.prompt.index("<role_prompt>") < payload.prompt.index("<launch_profile_overlay")
    assert payload.prompt.index("<launch_profile_overlay") < payload.prompt.index(
        "<launch_appendix"
    )
    assert payload.layout == {
        "version": 1,
        "root_tag": "houmao_system_prompt",
        "sections": [
            {"kind": "managed_header"},
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
    )

    assert "<role_prompt>" not in prompt
    assert '<launch_profile_overlay mode="replace">' in prompt
    assert '<launch_appendix source="launch_option">' in prompt
