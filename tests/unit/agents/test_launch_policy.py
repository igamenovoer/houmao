from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from houmao.agents.launch_policy import apply_launch_policy, detect_tool_version
from houmao.agents.launch_policy.engine import load_registry_documents
from houmao.agents.launch_policy import provider_hooks
from houmao.agents.launch_policy.models import (
    LaunchPolicyError,
    LaunchPolicyRequest,
    SupportedVersionSpec,
    ToolVersion,
)


def _stub_version(
    monkeypatch: pytest.MonkeyPatch,
    *,
    output: str,
) -> None:
    def _fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.subprocess.run",
        _fake_run,
    )


def _load_toml(path: Path) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_as_is_launch_policy_bypasses_strategy_resolution(tmp_path: Path) -> None:
    home = tmp_path / "codex-home"
    home.mkdir()

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=("--foo",),
            requested_operator_prompt_mode="as_is",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    assert result.args == ("--foo",)
    assert result.provenance is None
    assert result.strategy is None


def test_codex_unattended_strategy_supports_auth_json_fresh_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.116.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    payload = _load_toml(home / "config.toml")
    assert result.provenance is not None
    assert result.provenance.selection_source == "registry"
    assert result.provenance.selected_strategy_id == "codex-unattended-0.116.x"
    assert result.args == (
        '--config=approval_policy="never"',
        '--config=sandbox_mode="danger-full-access"',
        "--config=notice.hide_full_access_warning=true",
        "--config=tui.show_tooltips=false",
    )
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert "model" not in payload
    assert payload["notice"]["hide_full_access_warning"] is True
    assert payload["notice"].get("model_migrations") is None
    assert payload["tui"]["show_tooltips"] is False
    assert payload["projects"][str((tmp_path / "workspace").resolve())]["trust_level"] == "trusted"


def test_codex_unattended_strategy_supports_env_only_custom_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.116.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text(
        """
model_provider = "yunwu-openai"

[model_providers.yunwu-openai]
name = "Yunwu OpenAI-compatible endpoint"
base_url = "https://api.example.test/v1"
env_key = "OPENAI_API_KEY"
requires_openai_auth = false
wire_api = "responses"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="cao_rest",
            executable="codex",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"OPENAI_API_KEY": "sk-test"},
        )
    )

    payload = _load_toml(home / "config.toml")
    assert result.provenance is not None
    assert result.provenance.selected_strategy_id == "codex-unattended-0.116.x"
    assert "sk-test" not in " ".join(result.args)
    assert payload["model_provider"] == "yunwu-openai"
    assert "model" not in payload
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert payload["tui"]["show_tooltips"] is False
    assert payload["projects"][str((tmp_path / "workspace").resolve())]["trust_level"] == "trusted"


def test_codex_unattended_strategy_preserves_explicit_model_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.116.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")
    (home / "config.toml").write_text('model = "gpt-5.4-mini"\n', encoding="utf-8")

    apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    payload = _load_toml(home / "config.toml")
    assert payload["model"] == "gpt-5.4-mini"
    assert payload.get("notice", {}).get("model_migrations") is None


def test_codex_unattended_strategy_canonicalizes_conflicting_launch_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.116.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=(
                "--full-auto",
                "--yolo",
                "-a",
                "on-request",
                "--ask-for-approval=on-failure",
                "-s",
                "workspace-write",
                "--sandbox=read-only",
                "-c",
                'approval_policy="on-request"',
                "--config",
                'sandbox_mode="workspace-write"',
                "--config=notice.hide_full_access_warning=false",
                "--config=tui.show_tooltips=true",
                "-c",
                'notice.model_migrations.gpt-5.3-codex="skip"',
                "--config",
                'projects.repo.trust_level="untrusted"',
                "-m",
                "gpt-5.2",
                "--config",
                'model_provider="yunwu-openai"',
            ),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    assert result.args == (
        "-m",
        "gpt-5.2",
        "--config",
        'model_provider="yunwu-openai"',
        '--config=approval_policy="never"',
        '--config=sandbox_mode="danger-full-access"',
        "--config=notice.hide_full_access_warning=true",
        "--config=tui.show_tooltips=false",
    )


def test_codex_unattended_strategy_rejects_api_key_only_without_provider_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.116.0")
    home = tmp_path / "codex-home"
    home.mkdir()

    with pytest.raises(LaunchPolicyError, match="Codex credential readiness requires"):
        apply_launch_policy(
            LaunchPolicyRequest(
                tool="codex",
                backend="codex_headless",
                executable="codex",
                base_args=(),
                requested_operator_prompt_mode="unattended",
                working_directory=tmp_path / "workspace",
                home_path=home,
                env={"OPENAI_API_KEY": "sk-test"},
            )
        )


@pytest.mark.parametrize("version_output", ["2.1.81 (Claude Code)", "2.1.83 (Claude Code)"])
def test_claude_unattended_strategy_synthesizes_runtime_state_from_api_key_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    version_output: str,
) -> None:
    _stub_version(monkeypatch, output=version_output)
    home = tmp_path / "claude-home"
    api_key = "sk-live-abcdefghijklmnopqrstuvwxyz1234567890"

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="claude",
            backend="claude_headless",
            executable="claude",
            base_args=("-p",),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"ANTHROPIC_API_KEY": api_key},
        )
    )

    settings_payload = json.loads((home / "settings.json").read_text(encoding="utf-8"))
    state_text = (home / ".claude.json").read_text(encoding="utf-8")
    state_payload = json.loads(state_text)

    assert result.args == ("-p", "--dangerously-skip-permissions")
    assert result.provenance is not None
    assert result.provenance.selected_strategy_id == "claude-unattended-2.1.81"
    assert settings_payload["skipDangerousModePermissionPrompt"] is True
    assert state_payload["hasCompletedOnboarding"] is True
    assert state_payload["numStartups"] == 1
    assert state_payload["customApiKeyResponses"] == {
        "approved": [api_key[-20:]],
        "rejected": [],
    }
    assert (
        state_payload["projects"][str((tmp_path / "workspace").resolve())][
            "hasCompletedProjectOnboarding"
        ]
        is True
    )
    assert (
        state_payload["projects"][str((tmp_path / "workspace").resolve())]["hasTrustDialogAccepted"]
        is True
    )
    assert api_key not in state_text


def test_claude_unattended_strategy_deduplicates_owned_launch_arg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.83 (Claude Code)")
    home = tmp_path / "claude-home"

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="claude",
            backend="claude_headless",
            executable="claude",
            base_args=("-p", "--dangerously-skip-permissions", "--dangerously-skip-permissions"),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"ANTHROPIC_API_KEY": "sk-test"},
        )
    )

    assert result.args == ("-p", "--dangerously-skip-permissions")


def test_claude_unattended_strategy_accepts_minimal_projected_vendor_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.83 (Claude Code)")
    home = tmp_path / "claude-home"
    home.mkdir()
    credentials_path = home / ".credentials.json"
    state_path = home / ".claude.json"
    credentials_path.write_text(
        '{"claudeAiOauth": {"accessToken": "vendor-access-token"}}\n',
        encoding="utf-8",
    )
    state_path.write_text("{}\n", encoding="utf-8")

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="claude",
            backend="claude_headless",
            executable="claude",
            base_args=("-p",),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    state_payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert result.args == ("-p", "--dangerously-skip-permissions")
    assert state_payload["hasCompletedOnboarding"] is True
    assert state_payload["numStartups"] == 1
    assert (
        state_payload["projects"][str((tmp_path / "workspace").resolve())][
            "hasCompletedProjectOnboarding"
        ]
        is True
    )
    assert (
        state_payload["projects"][str((tmp_path / "workspace").resolve())]["hasTrustDialogAccepted"]
        is True
    )
    assert credentials_path.read_text(encoding="utf-8") == (
        '{"claudeAiOauth": {"accessToken": "vendor-access-token"}}\n'
    )


def test_claude_resume_control_preserves_cli_args_without_touching_owned_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.83 (Claude Code)")
    home = tmp_path / "claude-home"
    home.mkdir()
    settings_path = home / "settings.json"
    state_path = home / ".claude.json"
    settings_path.write_text("", encoding="utf-8")
    state_path.write_text("", encoding="utf-8")

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="claude",
            backend="claude_headless",
            executable="claude",
            base_args=("-p",),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"ANTHROPIC_API_KEY": "sk-test"},
            application_kind="resume_control",
        )
    )

    assert result.args == ("-p", "--dangerously-skip-permissions")
    assert settings_path.read_text(encoding="utf-8") == ""
    assert state_path.read_text(encoding="utf-8") == ""


def test_concurrent_claude_resume_control_requests_do_not_observe_malformed_owned_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.83 (Claude Code)")
    home = tmp_path / "claude-home"
    home.mkdir()
    settings_path = home / "settings.json"
    state_path = home / ".claude.json"
    settings_path.write_text("", encoding="utf-8")
    state_path.write_text("", encoding="utf-8")

    request = LaunchPolicyRequest(
        tool="claude",
        backend="claude_headless",
        executable="claude",
        base_args=("-p",),
        requested_operator_prompt_mode="unattended",
        working_directory=tmp_path / "workspace",
        home_path=home,
        env={"ANTHROPIC_API_KEY": "sk-test"},
        application_kind="resume_control",
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: apply_launch_policy(request), range(2)))

    assert [result.args for result in results] == [
        ("-p", "--dangerously-skip-permissions"),
        ("-p", "--dangerously-skip-permissions"),
    ]
    assert settings_path.read_text(encoding="utf-8") == ""
    assert state_path.read_text(encoding="utf-8") == ""


def test_claude_provider_start_repairs_blank_owned_files_via_atomic_replace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.83 (Claude Code)")
    home = tmp_path / "claude-home"
    home.mkdir()
    settings_path = home / "settings.json"
    state_path = home / ".claude.json"
    settings_path.write_text("", encoding="utf-8")
    state_path.write_text("", encoding="utf-8")
    replace_targets: list[Path] = []
    original_replace = provider_hooks.os.replace

    def _record_replace(src: str | Path, dst: str | Path) -> None:
        replace_targets.append(Path(dst))
        original_replace(src, dst)

    monkeypatch.setattr(provider_hooks.os, "replace", _record_replace)

    apply_launch_policy(
        LaunchPolicyRequest(
            tool="claude",
            backend="claude_headless",
            executable="claude",
            base_args=("-p",),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"ANTHROPIC_API_KEY": "sk-test"},
        )
    )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "skipDangerousModePermissionPrompt": True
    }
    state_payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_payload["hasCompletedOnboarding"] is True
    assert settings_path in replace_targets
    assert state_path in replace_targets


def test_codex_provider_start_repairs_blank_owned_toml_via_atomic_replace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.116.0")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")
    config_path = home / "config.toml"
    config_path.write_text("", encoding="utf-8")
    replace_targets: list[Path] = []
    original_replace = provider_hooks.os.replace

    def _record_replace(src: str | Path, dst: str | Path) -> None:
        replace_targets.append(Path(dst))
        original_replace(src, dst)

    monkeypatch.setattr(provider_hooks.os, "replace", _record_replace)

    apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    payload = _load_toml(config_path)
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert config_path in replace_targets


def test_codex_registry_declares_final_cli_config_override_hook() -> None:
    documents = load_registry_documents(tool="codex")

    assert len(documents) == 1
    assert len(documents[0].strategies) == 1
    strategy = documents[0].strategies[0]
    assert strategy.strategy_id == "codex-unattended-0.116.x"
    assert any("--config" in note for note in strategy.minimal_inputs.notes)
    assert strategy.actions[-1].kind == "provider_hook.call"
    assert strategy.actions[-1].params == {"hook_id": "codex.append_unattended_cli_overrides"}


def test_kimi_registry_declares_startup_visible_auto_skill_bootstrap() -> None:
    documents = load_registry_documents(tool="kimi")

    assert len(documents) == 1
    assert {strategy.strategy_id for strategy in documents[0].strategies} == {
        "kimi-unattended-0.23.x",
        "kimi-tui-unattended-0.23.x",
    }
    for strategy in documents[0].strategies:
        capabilities = strategy.system_prompt_bootstrap
        assert capabilities.native_system_prompt is False
        assert capabilities.provider_skills is True
        assert capabilities.startup_visible_skill_metadata is True
        assert capabilities.evidence
        assert any("skill" in item.note.lower() for item in capabilities.evidence)
        assert strategy.to_metadata_payload()["system_prompt_bootstrap"] == (
            capabilities.to_payload()
        )


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_native_prompt_registries_declare_native_bootstrap(tool: str) -> None:
    documents = load_registry_documents(tool=tool)

    assert len(documents) == 1
    for strategy in documents[0].strategies:
        assert strategy.system_prompt_bootstrap.native_system_prompt is True
        assert strategy.system_prompt_bootstrap.startup_visible_skill_metadata is False


def test_toml_rewrite_preserves_float_scalars(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[loop_control]
compaction_trigger_ratio = 0.85
""".lstrip(),
        encoding="utf-8",
    )

    provider_hooks.set_toml_key(
        path=config_path,
        key_path=("extra_skill_dirs",),
        value=[str(tmp_path / "skills")],
    )

    payload = _load_toml(config_path)
    loop_control = payload["loop_control"]
    assert isinstance(loop_control, dict)
    assert loop_control["compaction_trigger_ratio"] == 0.85
    assert payload["extra_skill_dirs"] == [str(tmp_path / "skills")]


def test_kimi_unattended_strategy_canonicalizes_prompt_mode_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="0.23.4")
    home = tmp_path / "kimi-home"
    home.mkdir()

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="kimi",
            backend="kimi_headless",
            executable="/opt/kimi/bin/kimi",
            base_args=(
                "--auto",
                "--yolo",
                "--plan",
                "--session",
                "session-1",
                "-p",
                "bad prompt",
                "--output-format",
                "text",
                "--skills-dir",
                "/tmp/global-skills",
                "--model",
                "kimi-code/kimi-for-coding",
            ),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    assert result.args == ("--model", "kimi-code/kimi-for-coding")
    assert result.provenance is not None
    assert result.provenance.selected_strategy_id == "kimi-unattended-0.23.x"
    assert result.strategy is not None
    assert result.strategy.backends == ("kimi_headless",)
    assert [action.kind for action in result.strategy.actions] == ["provider_hook.call"]
    assert not (home / "config.toml").exists()


def test_kimi_raw_launch_unattended_sets_auto_config_and_strips_tui_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="0.23.4")
    home = tmp_path / "kimi-home"
    home.mkdir()
    (home / "config.toml").write_text(
        """
default_permission_mode = "manual"
default_model = "kimi-code/kimi-for-coding"
extra_skill_dirs = ["/opt/project-skills"]

[providers."managed:kimi-code"]
type = "moonshot"

[telemetry]
enabled = false
""".lstrip(),
        encoding="utf-8",
    )

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="kimi",
            backend="raw_launch",
            executable="kimi",
            base_args=(
                "--auto",
                "--yolo",
                "-y",
                "--plan",
                "--continue",
                "--session",
                "session-1",
                "-S=session-2",
                "-r",
                "session-3",
                "--model",
                "kimi-code/kimi-for-coding",
                "--temperature",
                "0",
            ),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    payload = _load_toml(home / "config.toml")
    assert result.args == (
        "--model",
        "kimi-code/kimi-for-coding",
        "--temperature",
        "0",
        "--auto",
    )
    assert result.provenance is not None
    assert result.provenance.selected_strategy_id == "kimi-tui-unattended-0.23.x"
    assert result.strategy is not None
    assert result.strategy.backends == ("raw_launch",)
    assert result.strategy.owned_paths[0].path == "config.toml"
    assert result.strategy.owned_paths[0].keys == ("default_permission_mode",)
    assert result.strategy.owned_paths[1].path == ".skip-migration-from-kimi-cli"
    assert (home / ".skip-migration-from-kimi-cli").is_file()
    assert payload["default_permission_mode"] == "auto"
    assert payload["default_model"] == "kimi-code/kimi-for-coding"
    assert payload["extra_skill_dirs"] == ["/opt/project-skills"]
    assert payload["providers"]["managed:kimi-code"]["type"] == "moonshot"
    assert payload["telemetry"]["enabled"] is False


def test_kimi_raw_launch_as_is_leaves_args_and_config_untouched(tmp_path: Path) -> None:
    home = tmp_path / "kimi-home"
    home.mkdir()
    config_path = home / "config.toml"
    original_config = 'default_permission_mode = "manual"\nextra_skill_dirs = ["/skills"]\n'
    config_path.write_text(original_config, encoding="utf-8")

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="kimi",
            backend="raw_launch",
            executable="kimi",
            base_args=("--auto", "--session", "session-1", "--model", "kimi-code"),
            requested_operator_prompt_mode="as_is",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    assert result.args == ("--auto", "--session", "session-1", "--model", "kimi-code")
    assert result.provenance is None
    assert result.strategy is None
    assert config_path.read_text(encoding="utf-8") == original_config


def test_kimi_registry_declares_separate_headless_and_tui_unattended_strategies() -> None:
    documents = load_registry_documents(tool="kimi")

    strategies = {strategy.strategy_id: strategy for strategy in documents[0].strategies}
    assert strategies["kimi-unattended-0.23.x"].backends == ("kimi_headless",)
    assert strategies["kimi-tui-unattended-0.23.x"].backends == ("raw_launch",)
    assert [action.kind for action in strategies["kimi-tui-unattended-0.23.x"].actions] == [
        "provider_hook.call",
        "toml.set",
    ]


def test_kimi_unattended_strategy_fails_closed_for_unknown_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="0.24.0")
    home = tmp_path / "kimi-home"
    home.mkdir()

    with pytest.raises(LaunchPolicyError, match="No compatible unattended launch strategy"):
        apply_launch_policy(
            LaunchPolicyRequest(
                tool="kimi",
                backend="kimi_headless",
                executable="kimi",
                base_args=(),
                requested_operator_prompt_mode="unattended",
                working_directory=tmp_path / "workspace",
                home_path=home,
                env={},
            )
        )


def test_detect_tool_version_uses_absolute_executable_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = list(command)
        del check, capture_output, text
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="0.10.1", stderr="")

    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.subprocess.run",
        _fake_run,
    )

    detected_version = detect_tool_version(executable="/home/user/.kimi-code/bin/kimi")

    assert captured["command"] == ["/home/user/.kimi-code/bin/kimi", "--version"]
    assert detected_version.raw == "0.10.1"


def test_supported_version_spec_uses_dependency_style_matching() -> None:
    spec = SupportedVersionSpec.parse(">=2.1.81")

    assert spec.contains(ToolVersion.parse("2.1.81"))
    assert spec.contains(ToolVersion.parse("2.1.83"))
    assert spec.contains(ToolVersion.parse("2.1.84"))


def test_supported_version_spec_rejects_invalid_specifier() -> None:
    with pytest.raises(LaunchPolicyError, match="Unsupported supported_versions specifier"):
        SupportedVersionSpec.parse("latest")


def test_unattended_strategy_override_is_transient(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 9.9.9")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={
                "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY": "codex-unattended-0.116.x",
            },
        )
    )

    assert result.provenance is not None
    assert result.provenance.selection_source == "env_override"
    assert result.provenance.override_env_var_name == "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY"


def test_unattended_launch_fails_closed_for_older_than_supported_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.115.9")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")

    with pytest.raises(LaunchPolicyError, match="No compatible unattended launch strategy"):
        apply_launch_policy(
            LaunchPolicyRequest(
                tool="codex",
                backend="codex_headless",
                executable="codex",
                base_args=(),
                requested_operator_prompt_mode="unattended",
                working_directory=tmp_path / "workspace",
                home_path=home,
                env={},
            )
        )


@pytest.mark.parametrize("backend", ["raw_launch", "claude_headless"])
def test_installed_claude_version_is_covered_by_declared_supported_versions_when_available(
    backend: str,
) -> None:
    if shutil.which("claude") is None:
        pytest.skip("claude is not available on PATH")

    detected_version = detect_tool_version(executable="claude")
    matches = [
        strategy
        for document in load_registry_documents(tool="claude")
        for strategy in document.strategies
        if strategy.operator_prompt_mode == "unattended"
        and backend in strategy.backends
        and strategy.supported_versions.contains(detected_version)
    ]

    assert len(matches) == 1, (
        "Installed Claude version is not covered by exactly one declared unattended strategy "
        f"for backend={backend!r}: version={detected_version.raw!r}, "
        f"matches={[item.strategy_id for item in matches]!r}"
    )
