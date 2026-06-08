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


def _config_draft_generate_result(draft_id: str, intent: str) -> object:
    """Run one config-draft generate CLI call."""

    return CliRunner().invoke(
        cli,
        [
            "--print-plain",
            "internals",
            "config-drafts",
            "generate",
            "--id",
            draft_id,
            "--intent",
            intent,
        ],
    )


def _assert_fix_guide(output: str, *, draft_id: str, example_payload: str) -> None:
    """Assert common config-draft fix-guide output."""

    assert "Fix guide:" in output
    assert f"houmao-mgr internals config-drafts generate --id {draft_id}" in output
    assert "- input: --intent" in output
    assert "inline JSON object, `-` for stdin, or path to a JSON file" in output
    assert "expected JSON shape" in output
    assert '"required": [' in output
    assert '"fields"' in output
    assert example_payload in output


def _skill_text(relative_path: str) -> str:
    """Return one packaged skill asset."""

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_config_draft_list_is_compact_and_contains_initial_ids() -> None:
    payload = list_config_drafts()
    drafts = payload["drafts"]
    assert isinstance(drafts, list)
    ids = {str(item["id"]) for item in drafts if isinstance(item, dict)}

    assert ids == {
        "project.specialist",
        "project.profile",
        "internals.native-agent.launch-dossier",
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
        "project.specialist": ["name", "tool", "credential"],
        "project.profile": ["name", "specialist", "credential"],
        "internals.native-agent.launch-dossier": ["name", "recipe", "credential"],
    }


def test_config_draft_registry_rejects_duplicates() -> None:
    draft = ConfigDraft(
        draft_id="project.profile",
        description="Draft profile.",
        config_kind="project.profile",
        fields=(DraftField(name="name", required=True),),
        render=lambda fields: {"name": fields["name"]},
    )

    with pytest.raises(ClickException) as exc_info:
        build_config_draft_registry([draft, draft])

    assert "Duplicate config-draft id" in str(exc_info.value)
    assert "project.profile" in str(exc_info.value)


def test_unknown_config_draft_id_fails_clearly() -> None:
    with pytest.raises(ClickException) as exc_info:
        generate_config_draft("project.unknown", {"fields": {}})

    assert "Config draft id `project.unknown` is not registered" in str(exc_info.value)


def test_project_profile_draft_uses_fixed_lane_source_and_omits_command_metadata() -> None:
    result = generate_config_draft(
        "project.profile",
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
        "config_kind": "project.profile",
        "name": "reviewer-fast",
        "profile_lane": "profile",
        "source": {"kind": "specialist", "name": "reviewer"},
        "defaults": {"auth": "reviewer-creds"},
    }
    assert "target_argv" not in result.yaml
    assert "omitted_fields" not in result.yaml
    assert "fields" not in result.yaml


def test_native_launch_dossier_draft_uses_recipe_source() -> None:
    result = generate_config_draft(
        "internals.native-agent.launch-dossier",
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
    assert payload["config_kind"] == "internals.native-agent.launch-dossier"
    assert payload["resource_kind"] == "launch_dossier"
    assert payload["source"] == {"kind": "recipe", "name": "reviewer-codex"}
    assert payload["defaults"] == {"auth": "alice-creds"}


def test_specialist_draft_uses_high_level_specialist_shape() -> None:
    result = generate_config_draft(
        "project.specialist",
        {
            "fields": {
                "name": "reviewer",
                "tool": "codex",
                "credential": "reviewer-creds",
            }
        },
    )
    payload = yaml.safe_load(result.yaml)

    assert payload["config_kind"] == "project.specialist"
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
        "project.profile",
        {"fields": {"name": "reviewer-fast", "specialist": "reviewer"}},
    )
    assert missing.has_blockers
    assert missing.blockers[0].kind == "missing_required_field"
    assert missing.blockers[0].field == "credential"

    invalid = generate_config_draft(
        "project.profile",
        {"fields": {"name": "reviewer-fast", "specialist": "reviewer", "credential": 2}},
    )
    assert invalid.has_blockers
    assert invalid.blockers[0].kind == "invalid_field_value"

    for draft_id, fields, hidden_field in (
        (
            "project.profile",
            {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
                "model": "gpt-5",
            },
            "model",
        ),
        (
            "project.specialist",
            {
                "name": "reviewer",
                "tool": "codex",
                "credential": "reviewer-creds",
                "api_key": "secret",
            },
            "api_key",
        ),
        (
            "internals.native-agent.launch-dossier",
            {
                "name": "reviewer-raw",
                "recipe": "reviewer-codex",
                "credential": "reviewer-creds",
                "profile_lane": "profile",
            },
            "profile_lane",
        ),
        (
            "project.profile",
            {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
                "env": {"A": "1"},
            },
            "env",
        ),
        (
            "project.profile",
            {
                "name": "reviewer-fast",
                "specialist": "reviewer",
                "credential": "reviewer-creds",
                "memo_seed_text": "memo",
            },
            "memo_seed_text",
        ),
        (
            "project.profile",
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
            "project.profile",
            "--intent",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}',
        ],
    )
    assert yaml_result.exit_code == 0, yaml_result.output
    assert yaml.safe_load(yaml_result.output)["profile_lane"] == "profile"
    assert yaml.safe_load(yaml_result.output)["defaults"] == {"auth": "reviewer-creds"}

    json_payload = _json_result(
        [
            "internals",
            "config-drafts",
            "generate",
            "--id",
            "project.profile",
            "--intent",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}',
        ]
    )
    assert json_payload["draft_id"] == "project.profile"
    assert yaml.safe_load(str(json_payload["yaml"]))["source"]["kind"] == "specialist"

    blocked = CliRunner().invoke(
        cli,
        [
            "internals",
            "config-drafts",
            "generate",
            "--id",
            "project.profile",
            "--intent",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer"}}',
        ],
    )
    assert blocked.exit_code != 0
    assert "Required field `credential` was not supplied" in blocked.output
    _assert_fix_guide(
        blocked.output,
        draft_id="project.profile",
        example_payload=(
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer",'
            '"credential":"reviewer-creds"}}'
        ),
    )


def test_config_drafts_cli_flat_intent_reports_fields_wrapper() -> None:
    result = _config_draft_generate_result(
        "project.specialist",
        '{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}',
    )

    assert result.exit_code != 0
    assert "draft fields at the top level" in result.output
    assert "top-level `fields` object" in result.output
    assert "fields.name, fields.tool, fields.credential" in result.output
    assert '"enum": [' in result.output
    assert '"claude"' in result.output
    assert '"codex"' in result.output
    assert '"gemini"' in result.output
    assert "shell quoting" not in result.output
    _assert_fix_guide(
        result.output,
        draft_id="project.specialist",
        example_payload=(
            '{"fields":{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}}'
        ),
    )


def test_config_drafts_cli_shape_and_parse_failures_include_fix_guides() -> None:
    cases = (
        (
            "project.profile",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer"}}',
            "Required field `credential` was not supplied",
            "fields.name, fields.specialist, fields.credential",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer",'
            '"credential":"reviewer-creds"}}',
        ),
        (
            "project.specialist",
            '{"fields":{"name":"reviewer","tool":"openai","credential":"reviewer-creds"}}',
            "Field `tool` must be one of: claude, codex, gemini, kimi",
            "fields.name, fields.tool, fields.credential",
            '{"fields":{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}}',
        ),
        (
            "project.profile",
            '{"fields":["name"]}',
            "Intent JSON must contain an object-valued `fields` mapping",
            "fields.name, fields.specialist, fields.credential",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer",'
            '"credential":"reviewer-creds"}}',
        ),
        (
            "project.profile",
            '["name"]',
            "Intent JSON must be an object",
            "fields.name, fields.specialist, fields.credential",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer",'
            '"credential":"reviewer-creds"}}',
        ),
        (
            "project.profile",
            '{"fields":',
            "Invalid intent JSON",
            "fields.name, fields.specialist, fields.credential",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer",'
            '"credential":"reviewer-creds"}}',
        ),
    )

    for draft_id, intent, message, paths, example_payload in cases:
        result = _config_draft_generate_result(draft_id, intent)
        assert result.exit_code != 0
        assert message in result.output
        assert paths in result.output
        _assert_fix_guide(result.output, draft_id=draft_id, example_payload=example_payload)


def test_config_drafts_cli_valid_generation_stays_unchanged_for_registered_drafts() -> None:
    cases = (
        (
            "project.specialist",
            '{"fields":{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}}',
            {
                "config_kind": "project.specialist",
                "name": "general-kimi",
                "tool": "kimi",
                "credential": {"name": "kimi-coding"},
                "setup": "default",
                "launch": {"prompt_mode": "unattended"},
            },
        ),
        (
            "project.profile",
            '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}',
            {
                "config_kind": "project.profile",
                "name": "reviewer-fast",
                "profile_lane": "profile",
                "source": {"kind": "specialist", "name": "reviewer"},
                "defaults": {"auth": "reviewer-creds"},
            },
        ),
        (
            "internals.native-agent.launch-dossier",
            '{"fields":{"name":"reviewer-native","recipe":"reviewer-codex","credential":"reviewer-creds"}}',
            {
                "config_kind": "internals.native-agent.launch-dossier",
                "name": "reviewer-native",
                "resource_kind": "launch_dossier",
                "source": {"kind": "recipe", "name": "reviewer-codex"},
                "defaults": {"auth": "reviewer-creds"},
            },
        ),
    )

    for draft_id, intent, expected in cases:
        result = _config_draft_generate_result(draft_id, intent)
        assert result.exit_code == 0, result.output
        assert yaml.safe_load(result.output) == expected


def test_config_drafts_cli_fix_guide_omits_secret_values() -> None:
    result = _config_draft_generate_result(
        "project.specialist",
        (
            '{"fields":{"name":"reviewer","tool":"codex","credential":"reviewer-creds",'
            '"api_key":"sk-super-secret"}}'
        ),
    )

    assert result.exit_code != 0
    assert "Intent supplied fields that this config draft does not support" in result.output
    assert "api_key" in result.output
    assert "sk-super-secret" not in result.output
    _assert_fix_guide(
        result.output,
        draft_id="project.specialist",
        example_payload=(
            '{"fields":{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}}'
        ),
    )


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
    launch_dossiers = _skill_text(
        "src/houmao/agents/assets/system_skills/"
        "houmao-agent-definition/subskills/low-level/launch-dossiers.md"
    )
    memory = _skill_text("src/houmao/agents/assets/system_skills/houmao-memory-mgr/SKILL.md")

    assert "internals config-drafts generate" in agent_definition
    assert "project.specialist" in specialists
    assert "project.profile" in profiles
    assert "internals.native-agent.launch-dossier" in launch_dossiers
    assert '{"fields":{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}}' in (
        specialists
    )
    assert (
        '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}'
    ) in profiles
    assert (
        '{"fields":{"name":"reviewer-native","recipe":"reviewer-codex",'
        '"credential":"reviewer-creds"}}'
    ) in launch_dossiers
    assert "top-level `fields` object" in specialists
    assert "top-level `fields` object" in profiles
    assert "top-level `fields` object" in launch_dossiers
    assert "Do not pass memo seed fields to `internals config-drafts generate`" in memory
    assert "use maintained profile `set` memo-seed fields" in memory
    assert "command-templates" not in agent_definition
    assert "command-templates" not in specialists
    assert "command-templates" not in profiles
    assert "project.specialist.create" not in specialists
    assert "project.profile.create" not in profiles
    assert "internals native-agent launch-dossiers add --intent" not in launch_dossiers
    assert "api_key" not in specialists
    assert "memo_seed_text" not in profiles
    assert "memo_seed_text" not in launch_dossiers
