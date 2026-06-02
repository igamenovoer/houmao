from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click import ClickException
from click.testing import CliRunner

from houmao.srv_ctrl.commands.main import cli
from houmao.srv_ctrl.config_drafts import (
    ConfigDraft,
    DraftField,
    build_config_draft_registry,
    generate_config_draft,
    list_config_drafts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _json_result(args: list[str]) -> dict[str, object]:
    """Run one JSON CLI command and return the decoded payload."""

    result = CliRunner().invoke(cli, ["--print-json", *args])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, dict)
    return payload


def _skill_text(relative_path: str) -> str:
    """Return one packaged skill asset."""

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_config_draft_list_is_compact_and_contains_initial_ids() -> None:
    payload = list_config_drafts()
    drafts = payload["drafts"]
    assert isinstance(drafts, list)
    ids = {str(item["id"]) for item in drafts if isinstance(item, dict)}

    assert ids == {
        "project.easy.specialist",
        "project.easy.profile",
        "project.agents.launch-profile",
    }
    assert payload["count"] == 3
    for item in drafts:
        assert isinstance(item, dict)
        assert "required_intent_keys" in item
        assert "target_argv" not in item
        assert "fields" not in item
        assert "omitted_fields" not in item
    required_keys = {
        str(item["id"]): item["required_intent_keys"] for item in drafts if isinstance(item, dict)
    }
    assert required_keys == {
        "project.easy.specialist": ["name", "tool", "credential"],
        "project.easy.profile": ["name", "specialist", "credential"],
        "project.agents.launch-profile": ["name", "recipe", "credential"],
    }


def test_config_draft_registry_rejects_duplicates() -> None:
    draft = ConfigDraft(
        draft_id="project.easy.profile",
        description="Draft profile.",
        config_kind="project.easy.profile",
        fields=(DraftField(name="name", required=True),),
        render=lambda fields: {"name": fields["name"]},
    )

    with pytest.raises(ClickException) as exc_info:
        build_config_draft_registry([draft, draft])

    assert "Duplicate config-draft id" in str(exc_info.value)
    assert "project.easy.profile" in str(exc_info.value)


def test_unknown_config_draft_id_fails_clearly() -> None:
    with pytest.raises(ClickException) as exc_info:
        generate_config_draft("project.easy.unknown", {"fields": {}})

    assert "Config draft id `project.easy.unknown` is not registered" in str(exc_info.value)


def test_easy_profile_draft_uses_fixed_lane_source_and_omits_schema_metadata() -> None:
    result = generate_config_draft(
        "project.easy.profile",
        {
            "fields": {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
            }
        },
    )
    payload = yaml.safe_load(result.yaml)

    assert payload == {
        "name": "reviewer-fast",
        "profile_lane": "easy_profile",
        "source": {"kind": "specialist", "name": "reviewer"},
        "defaults": {"auth": "reviewer-creds"},
    }
    assert "target_argv" not in result.yaml
    assert "omitted_fields" not in result.yaml
    assert "fields" not in result.yaml


def test_raw_launch_profile_draft_uses_recipe_source() -> None:
    result = generate_config_draft(
        "project.agents.launch-profile",
        {
            "fields": {
                "name": "alice",
                "recipe": "reviewer-codex",
                "credential": "alice-creds",
            }
        },
    )
    payload = yaml.safe_load(result.yaml)

    assert payload["name"] == "alice"
    assert payload["profile_lane"] == "launch_profile"
    assert payload["source"] == {"kind": "recipe", "name": "reviewer-codex"}
    assert payload["defaults"] == {"auth": "alice-creds"}


def test_specialist_draft_uses_high_level_specialist_shape() -> None:
    result = generate_config_draft(
        "project.easy.specialist",
        {
            "fields": {
                "name": "reviewer",
                "tool": "codex",
                "credential": "reviewer-creds",
            }
        },
    )
    payload = yaml.safe_load(result.yaml)

    assert payload["config_kind"] == "project.easy.specialist"
    assert payload["name"] == "reviewer"
    assert payload["tool"] == "codex"
    assert payload["credential"] == {"name": "reviewer-creds"}
    assert payload["setup"] == "default"
    assert payload["launch"] == {"prompt_mode": "unattended"}
    assert "model" not in result.yaml
    assert "env" not in result.yaml
    assert "mailbox" not in result.yaml
    assert "skills" not in result.yaml
    assert "prompt:" not in result.yaml


def test_config_draft_reports_missing_invalid_and_unsupported_fields() -> None:
    missing = generate_config_draft(
        "project.easy.profile",
        {"fields": {"name": "reviewer-fast", "specialist": "reviewer"}},
    )
    assert missing.has_blockers
    assert missing.blockers[0].kind == "missing_required_field"
    assert missing.blockers[0].field == "credential"

    invalid = generate_config_draft(
        "project.easy.profile",
        {"fields": {"name": "reviewer-fast", "specialist": "reviewer", "credential": 2}},
    )
    assert invalid.has_blockers
    assert invalid.blockers[0].kind == "invalid_field_value"

    for draft_id, fields, hidden_field in (
        (
            "project.easy.profile",
            {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
                "model": "gpt-5",
            },
            "model",
        ),
        (
            "project.easy.specialist",
            {
                "name": "reviewer",
                "tool": "codex",
                "credential": "reviewer-creds",
                "api_key": "secret",
            },
            "api_key",
        ),
        (
            "project.agents.launch-profile",
            {
                "name": "reviewer-raw",
                "recipe": "reviewer-codex",
                "credential": "reviewer-creds",
                "profile_lane": "easy_profile",
            },
            "profile_lane",
        ),
        (
            "project.easy.profile",
            {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
                "env": {"A": "1"},
            },
            "env",
        ),
        (
            "project.easy.profile",
            {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
                "memo_seed_text": "memo",
            },
            "memo_seed_text",
        ),
        (
            "project.easy.profile",
            {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
                "mail_address": "agent@example.com",
            },
            "mail_address",
        ),
    ):
        unsupported = generate_config_draft(draft_id, {"fields": fields})
        assert unsupported.has_blockers
        assert unsupported.blockers[0].kind == "unsupported_fields"
        assert hidden_field in unsupported.blockers[0].fields


def test_config_drafts_cli_list_generate_json_and_blockers() -> None:
    list_payload = _json_result(["internals", "config-drafts", "list"])
    assert list_payload["count"] == 3

    yaml_result = CliRunner().invoke(
        cli,
        [
            "--print-plain",
            "internals",
            "config-drafts",
            "generate",
            "--id",
            "project.easy.profile",
            "--intent",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}',
        ],
    )
    assert yaml_result.exit_code == 0, yaml_result.output
    assert yaml.safe_load(yaml_result.output)["profile_lane"] == "easy_profile"
    assert yaml.safe_load(yaml_result.output)["defaults"] == {"auth": "reviewer-creds"}

    json_payload = _json_result(
        [
            "internals",
            "config-drafts",
            "generate",
            "--id",
            "project.easy.profile",
            "--intent",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}',
        ]
    )
    assert json_payload["draft_id"] == "project.easy.profile"
    assert yaml.safe_load(str(json_payload["yaml"]))["source"]["kind"] == "specialist"

    blocked = CliRunner().invoke(
        cli,
        [
            "internals",
            "config-drafts",
            "generate",
            "--id",
            "project.easy.profile",
            "--intent",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer"}}',
        ],
    )
    assert blocked.exit_code != 0
    assert "Required field `credential` was not supplied" in blocked.output


def test_command_template_rendering_remains_available_for_command_workflows() -> None:
    payload = _json_result(
        [
            "internals",
            "command-templates",
            "render",
            "--id",
            "project.agents.recipes.add",
            "--intent",
            '{"fields":{"name":"reviewer-codex","role":"reviewer","tool":"codex"}}',
        ]
    )

    assert payload["argv"] == [
        "houmao-mgr",
        "project",
        "agents",
        "recipes",
        "add",
        "--name",
        "reviewer-codex",
        "--role",
        "reviewer",
        "--tool",
        "codex",
    ]


def test_packaged_skills_route_config_authoring_to_config_drafts() -> None:
    agent_definition = _skill_text(
        "src/houmao/agents/assets/system_skills/houmao-agent-definition/SKILL.md"
    )
    specialists = _skill_text(
        "src/houmao/agents/assets/system_skills/"
        "houmao-agent-definition/subskills/easy/specialists.md"
    )
    profiles = _skill_text(
        "src/houmao/agents/assets/system_skills/houmao-agent-definition/subskills/easy/profiles.md"
    )
    raw_profiles = _skill_text(
        "src/houmao/agents/assets/system_skills/"
        "houmao-agent-definition/subskills/low-level/raw-profiles.md"
    )
    memory = _skill_text("src/houmao/agents/assets/system_skills/houmao-memory-mgr/SKILL.md")

    assert "internals config-drafts generate" in agent_definition
    assert "project.easy.specialist" in specialists
    assert "project.easy.profile" in profiles
    assert "project.agents.launch-profile" in raw_profiles
    assert "intent fields are only `name`, `tool`, and `credential`" in specialists
    assert "intent fields are only `name`, `specialist`, and `credential`" in profiles
    assert "intent fields are only `name`, `recipe`, and `credential`" in raw_profiles
    assert "Do not pass memo seed fields to `internals config-drafts generate`" in memory
    assert "use maintained profile `set` memo-seed fields" in memory
    assert "command-templates show" not in agent_definition
    assert "command-templates show" not in specialists
    assert "command-templates show" not in profiles
    assert "project.easy.specialist.create" not in specialists
    assert "project.easy.profile.create" not in profiles
    assert "project.agents.launch-profiles.add --intent" not in raw_profiles
    assert "api_key" not in specialists
    assert "memo_seed_text" not in profiles
    assert "memo_seed_text" not in raw_profiles
