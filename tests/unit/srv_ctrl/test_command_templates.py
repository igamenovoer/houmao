from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click import ClickException
from click.testing import CliRunner

from houmao.srv_ctrl.command_templates import (
    build_template_registry,
    export_command_template_yaml,
    export_command_templates_yaml,
    get_command_template,
    show_command_template,
)
from houmao.srv_ctrl.command_templates.families import (
    agents_gateway,
    agents_lifecycle,
    credentials,
    mailbox,
    managed_agent_mail,
    project_agents,
    project_easy,
)
from houmao.srv_ctrl.commands.main import cli


REPO_ROOT = Path(__file__).resolve().parents[3]


def _json_result(args: list[str]) -> dict[str, object]:
    """Run one JSON CLI command and return the decoded payload."""

    result = CliRunner().invoke(cli, ["--print-json", *args])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, dict)
    return payload


def _render(template_id: str, fields: dict[str, object]) -> dict[str, object]:
    """Render one template from sparse fields."""

    return _json_result(
        [
            "internals",
            "command-templates",
            "render",
            "--id",
            template_id,
            "--intent",
            json.dumps({"fields": fields}),
        ]
    )


def _argv(payload: dict[str, object]) -> list[str]:
    """Return one rendered argv list."""

    value = payload["argv"]
    assert isinstance(value, list)
    return [str(item) for item in value]


def _skill_text(relative_path: str) -> str:
    """Return one packaged skill asset."""

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_command_template_list_covers_command_surfaces_and_excludes_skill_scaffolds() -> None:
    payload = _json_result(["internals", "command-templates", "list"])
    templates = payload["templates"]
    assert isinstance(templates, list)
    ids = {str(item["id"]) for item in templates if isinstance(item, dict)}
    families = {str(item["family"]) for item in templates if isinstance(item, dict)}

    assert "project.profile.create" in ids
    assert "internals.native-agent.recipes.add" in ids
    assert "internals.native-agent.brain.build" in ids
    assert "internals.native-agent.credentials.codex.add" in ids
    assert "project.credentials.codex.add" in ids
    assert "credentials.codex.add" not in ids
    assert "agents.gateway.reminders.create" in ids
    assert "project.mailbox.messages.get" in ids
    assert "agents.mail.send" in ids
    assert "loop-scaffold.pro.execplan-shell" not in ids
    assert "workspace-layout.in-repo" not in ids
    assert {
        "project.specialist",
        "project.profile",
        "project.agents",
        "internals.native-agent.recipes",
        "internals.native-agent.launch-dossiers",
        "internals.native-agent.brain",
        "internals.native-agent.credentials",
        "project.credentials",
        "agents.lifecycle",
        "agents.gateway",
        "mailbox",
        "project.mailbox",
        "agents.mailbox",
        "agents.mail",
    }.issubset(families)
    assert all(
        isinstance(item, dict) and item["target_argv"][0] == "houmao-mgr" for item in templates
    )


def test_show_reports_prompt_mode_as_omit_to_inherit() -> None:
    payload = _json_result(
        [
            "internals",
            "command-templates",
            "show",
            "--id",
            "project.profile.create",
        ]
    )
    fields = payload["fields"]
    assert isinstance(fields, list)
    prompt_mode = next(item for item in fields if item["name"] == "prompt_mode")
    assert prompt_mode["option"] == "--prompt-mode"
    assert prompt_mode["default_action"] == "omit-to-inherit"


def test_sparse_project_profile_render_omits_prompt_mode_and_headless() -> None:
    payload = _render(
        "project.profile.create",
        {"name": "reviewer-fast", "specialist": "reviewer"},
    )
    argv = _argv(payload)

    assert argv == [
        "houmao-mgr",
        "project",
        "profile",
        "create",
        "--name",
        "reviewer-fast",
        "--specialist",
        "reviewer",
    ]
    assert "--prompt-mode" not in argv
    assert "--headless" not in argv


def test_specialist_set_patch_preserves_prompt_mode_by_omission() -> None:
    payload = _render("project.specialist.set", {"name": "reviewer", "model": "gpt-5"})
    argv = _argv(payload)

    assert argv == [
        "houmao-mgr",
        "project",
        "specialist",
        "set",
        "--name",
        "reviewer",
        "--model",
        "gpt-5",
    ]
    assert "--prompt-mode" not in argv
    assert "--clear-prompt-mode" not in argv


def test_clear_prompt_mode_renders_only_when_explicit() -> None:
    payload = _render("project.specialist.set", {"name": "reviewer", "clear_prompt_mode": True})
    argv = _argv(payload)

    assert argv == [
        "houmao-mgr",
        "project",
        "specialist",
        "set",
        "--name",
        "reviewer",
        "--clear-prompt-mode",
    ]


def test_explicit_prompt_mode_renders_when_supplied() -> None:
    payload = _render("project.specialist.set", {"name": "reviewer", "prompt_mode": "as_is"})
    argv = _argv(payload)

    assert argv == [
        "houmao-mgr",
        "project",
        "specialist",
        "set",
        "--name",
        "reviewer",
        "--prompt-mode",
        "as_is",
    ]


def test_native_launch_dossier_patch_preserves_advanced_blocks() -> None:
    payload = _render(
        "internals.native-agent.launch-dossiers.set",
        {"name": "alice", "workdir": "/tmp/a"},
    )
    argv = _argv(payload)

    assert argv == [
        "houmao-mgr",
        "internals",
        "native-agent",
        "launch-dossiers",
        "set",
        "--name",
        "alice",
        "--workdir",
        "/tmp/a",
    ]
    assert "--prompt-mode" not in argv
    assert "--clear-prompt-mode" not in argv


def test_credential_template_is_tool_specific() -> None:
    payload = _json_result(
        [
            "internals",
            "command-templates",
            "show",
            "--id",
            "project.credentials.codex.add",
        ]
    )
    fields = payload["fields"]
    assert isinstance(fields, list)
    names = {str(item["name"]) for item in fields if isinstance(item, dict)}

    assert {"api_key", "base_url", "org_id", "auth_json"}.issubset(names)
    assert "project_dir" in names
    assert "claude_auth_token" not in names
    assert "google_api_key" not in names


def test_credential_source_conflict_blocks_rendering() -> None:
    payload = _render(
        "project.credentials.codex.add",
        {"name": "main", "api_key": "sk-placeholder", "auth_json": "/tmp/auth.json"},
    )

    assert _argv(payload) == []
    blockers = payload["blockers"]
    assert isinstance(blockers, list)
    assert blockers
    assert blockers[0]["kind"] == "conflicting_fields"


def test_project_dir_template_field_renders_after_project_group() -> None:
    payload = _render(
        "project.credentials.codex.list",
        {"project_dir": "/repo"},
    )

    assert _argv(payload) == [
        "houmao-mgr",
        "project",
        "--project-dir",
        "/repo",
        "credentials",
        "codex",
        "list",
    ]


def test_internal_native_credential_and_brain_templates_render_new_target_flags() -> None:
    credential_payload = _render(
        "internals.native-agent.credentials.codex.get",
        {"native_agent_root": "/native", "name": "work"},
    )
    brain_payload = _render(
        "internals.native-agent.brain.build",
        {"native_agent_root": "/native", "preset": "reviewer"},
    )

    assert _argv(credential_payload) == [
        "houmao-mgr",
        "internals",
        "native-agent",
        "credentials",
        "codex",
        "get",
        "--native-agent-root",
        "/native",
        "--name",
        "work",
    ]
    assert _argv(brain_payload) == [
        "houmao-mgr",
        "internals",
        "native-agent",
        "brain",
        "build",
        "--native-agent-root",
        "/native",
        "--preset",
        "reviewer",
    ]


def test_gateway_reminder_conflict_blocks_rendering() -> None:
    payload = _render(
        "agents.gateway.reminders.create",
        {
            "agent_name": "gpu",
            "title": "Check inbox",
            "mode": "one_off",
            "prompt": "Review now.",
            "sequence": "<[Escape]>",
            "ranking": 0,
        },
    )

    assert _argv(payload) == []
    blockers = payload["blockers"]
    assert isinstance(blockers, list)
    assert blockers
    assert blockers[0]["kind"] == "conflicting_fields"


def test_mailbox_export_template_uses_output_dir_and_blocks_scope_conflict() -> None:
    show_payload = _json_result(
        ["internals", "command-templates", "show", "--id", "mailbox.export"]
    )
    fields = show_payload["fields"]
    assert isinstance(fields, list)
    options = [item["option"] for item in fields if isinstance(item, dict) and "option" in item]
    assert "--output-dir" in options
    assert "--archive-dir" not in options
    assert options.count("--address") == 1

    rendered = _render(
        "mailbox.export",
        {
            "mailbox_root": "/tmp/mailbox",
            "output_dir": "/tmp/archive",
            "address": ["alice@houmao.localhost", "bob@houmao.localhost"],
        },
    )
    assert _argv(rendered) == [
        "houmao-mgr",
        "mailbox",
        "export",
        "--mailbox-root",
        "/tmp/mailbox",
        "--output-dir",
        "/tmp/archive",
        "--address",
        "alice@houmao.localhost",
        "--address",
        "bob@houmao.localhost",
    ]

    blocked = _render(
        "mailbox.export",
        {
            "output_dir": "/tmp/archive",
            "all_accounts": True,
            "address": ["alice@houmao.localhost"],
        },
    )
    assert _argv(blocked) == []
    blockers = blocked["blockers"]
    assert isinstance(blockers, list)
    assert blockers[0]["kind"] == "conflicting_fields"


def test_agent_launch_template_keeps_posture_absent_when_unspecified() -> None:
    payload = _render(
        "agents.launch-profile.launch", {"launch_profile": "nightly", "agent_name": "alice"}
    )
    argv = _argv(payload)

    assert argv == [
        "houmao-mgr",
        "agents",
        "launch",
        "--launch-profile",
        "nightly",
        "--agent-name",
        "alice",
    ]
    assert "--headless" not in argv


def test_managed_agent_mail_fallback_renders_command_shape_only() -> None:
    payload = _render(
        "agents.mail.send",
        {"to": ["bob@houmao.localhost"], "subject": "Hello", "body_content": "Hi"},
    )
    argv = _argv(payload)

    assert argv == [
        "houmao-mgr",
        "agents",
        "mail",
        "send",
        "--to",
        "bob@houmao.localhost",
        "--subject",
        "Hello",
        "--body-content",
        "Hi",
    ]


def test_packaged_skill_guidance_uses_cli_owned_templates() -> None:
    agent_definition = _skill_text(
        "src/houmao/agents/assets/system_skills/houmao-agent-definition/SKILL.md"
    )
    fast_forward = _skill_text(
        "src/houmao/agents/assets/system_skills/"
        "houmao-agent-definition/subskills/easy/create-agent-fast-forward.md"
    )
    credential = _skill_text(
        "src/houmao/agents/assets/system_skills/houmao-credential-mgr/SKILL.md"
    )
    instance = _skill_text("src/houmao/agents/assets/system_skills/houmao-agent-instance/SKILL.md")
    gateway = _skill_text("src/houmao/agents/assets/system_skills/houmao-agent-gateway/SKILL.md")
    mailbox = _skill_text("src/houmao/agents/assets/system_skills/houmao-mailbox-mgr/SKILL.md")
    email = _skill_text("src/houmao/agents/assets/system_skills/houmao-agent-email-comms/SKILL.md")
    memory = _skill_text("src/houmao/agents/assets/system_skills/houmao-memory-mgr/SKILL.md")
    specialist = _skill_text(
        "src/houmao/agents/assets/system_skills/houmao-specialist-mgr/SKILL.md"
    )

    assert "internals command-templates" in agent_definition
    assert "default to unattended" not in fast_forward
    assert "project.credentials.<tool>.<verb>" in credential
    assert "internals.native-agent.credentials.<tool>.<verb>" in credential
    assert "internals.native-agent.brain.build" in agent_definition
    assert "agents.launch-profile.launch" in instance
    assert "agents.gateway.reminders.list|get|create|set|remove" in gateway
    assert "mailbox.<verb>" in mailbox
    assert "agents.mail.<verb>" in email
    assert "project.profile.create" in memory
    assert "CLI template rendering" in specialist


def test_packaged_skill_guidance_avoids_covered_default_bearing_skeletons() -> None:
    mailbox_register = _skill_text(
        "src/houmao/agents/assets/system_skills/houmao-mailbox-mgr/actions/register.md"
    )
    email_send = _skill_text(
        "src/houmao/agents/assets/system_skills/houmao-agent-email-comms/actions/send.md"
    )

    assert "mailbox register --address" not in mailbox_register
    assert "project mailbox register --address" not in mailbox_register
    assert "houmao-mgr agents mail send --to" not in email_send


def test_family_modules_contribute_expected_template_inventory() -> None:
    family_ids = {
        project_easy: "project.agents.launch",
        project_agents: "internals.native-agent.brain.build",
        credentials: "project.credentials.codex.add",
        agents_lifecycle: "agents.launch-profile.launch",
        agents_gateway: "agents.gateway.reminders.create",
        mailbox: "project.mailbox.messages.get",
        managed_agent_mail: "agents.mail.send",
    }

    for family_module, expected_id in family_ids.items():
        templates = family_module.templates()
        assert templates
        assert expected_id in {template.template_id for template in templates}


def test_registry_rejects_duplicate_template_ids() -> None:
    template = get_command_template("project.profile.create")

    with pytest.raises(ClickException) as exc_info:
        build_template_registry((template, template))

    assert "Duplicate command-template id" in str(exc_info.value)
    assert "project.profile.create" in str(exc_info.value)


def test_single_template_yaml_export_matches_show_and_is_deterministic() -> None:
    first = export_command_template_yaml("project.agents.launch")
    second = export_command_template_yaml("project.agents.launch")

    assert first == second
    assert first.endswith("\n")
    assert yaml.safe_load(first) == show_command_template("project.agents.launch")


def test_all_template_yaml_export_is_sorted_and_complete() -> None:
    document = export_command_templates_yaml()
    payload = yaml.safe_load(document)
    assert isinstance(payload, dict)
    templates = payload["templates"]
    assert isinstance(templates, list)
    ids = [str(item["id"]) for item in templates if isinstance(item, dict)]

    list_payload = _json_result(["internals", "command-templates", "list"])
    assert ids == sorted(ids)
    assert len(ids) == list_payload["count"]
    assert "project.agents.launch" in ids
    assert "agents.mail.send" in ids


def test_cli_export_single_template_to_stdout_and_file(tmp_path: Path) -> None:
    stdout_result = CliRunner().invoke(
        cli, ["internals", "command-templates", "export", "--id", "project.profile.create"]
    )
    assert stdout_result.exit_code == 0, stdout_result.output
    assert yaml.safe_load(stdout_result.output) == show_command_template("project.profile.create")

    output_path = tmp_path / "profile-create.yaml"
    file_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "internals",
            "command-templates",
            "export",
            "--id",
            "project.profile.create",
            "--output",
            str(output_path),
        ],
    )
    assert file_result.exit_code == 0, file_result.output
    assert yaml.safe_load(output_path.read_text(encoding="utf-8")) == show_command_template(
        "project.profile.create"
    )
    assert json.loads(file_result.output)["written"] == str(output_path.resolve())


def test_cli_export_all_templates_to_stdout_and_directory(tmp_path: Path) -> None:
    stdout_result = CliRunner().invoke(cli, ["internals", "command-templates", "export", "--all"])
    assert stdout_result.exit_code == 0, stdout_result.output
    payload = yaml.safe_load(stdout_result.output)
    assert isinstance(payload, dict)
    assert (
        len(payload["templates"])
        == _json_result(["internals", "command-templates", "list"])["count"]
    )

    output_dir = tmp_path / "templates"
    dir_result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "internals",
            "command-templates",
            "export",
            "--all",
            "--output-dir",
            str(output_dir),
        ],
    )
    assert dir_result.exit_code == 0, dir_result.output
    result_payload = json.loads(dir_result.output)
    assert (
        result_payload["count"] == _json_result(["internals", "command-templates", "list"])["count"]
    )
    exported_path = output_dir / "project.agents.launch.yaml"
    assert yaml.safe_load(exported_path.read_text(encoding="utf-8")) == show_command_template(
        "project.agents.launch"
    )


def test_cli_export_rejects_ambiguous_selection_and_output_modes() -> None:
    runner = CliRunner()

    missing = runner.invoke(cli, ["internals", "command-templates", "export"])
    assert missing.exit_code != 0
    assert "Select exactly one command template" in missing.output

    both = runner.invoke(
        cli, ["internals", "command-templates", "export", "--id", "agents.mail.send", "--all"]
    )
    assert both.exit_code != 0
    assert "Select exactly one command template" in both.output

    wrong_output = runner.invoke(
        cli,
        [
            "internals",
            "command-templates",
            "export",
            "--id",
            "agents.mail.send",
            "--output-dir",
            "/tmp/templates",
        ],
    )
    assert wrong_output.exit_code != 0
    assert "`--output-dir` is only valid with `--all`" in wrong_output.output
