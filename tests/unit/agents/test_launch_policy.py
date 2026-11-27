from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from houmao.agents.launch_policy import apply_launch_policy, detect_tool_version
from houmao.agents.launch_policy.engine import load_registry_documents, resolve_strategy
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
    _stub_version(monkeypatch, output="codex-cli 0.162.1")
    workspace = tmp_path / "workspace"
    (workspace / ".git").mkdir(parents=True)
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
            working_directory=workspace,
            home_path=home,
            env={},
        )
    )

    payload = _load_toml(home / "config.toml")
    assert result.provenance is not None
    assert result.provenance.selection_source == "registry"
    assert result.provenance.selected_strategy_id == "codex-unattended-0.162-plus"
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
    assert payload["projects"][str(workspace.resolve())]["trust_level"] == "trusted"


def test_codex_unattended_strategy_supports_env_only_custom_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.162.1")
    workspace = tmp_path / "workspace"
    (workspace / ".git").mkdir(parents=True)
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
            working_directory=workspace,
            home_path=home,
            env={"OPENAI_API_KEY": "sk-test"},
        )
    )

    payload = _load_toml(home / "config.toml")
    assert result.provenance is not None
    assert result.provenance.selected_strategy_id == "codex-unattended-0.162-plus"
    assert "sk-test" not in " ".join(result.args)
    assert payload["model_provider"] == "yunwu-openai"
    assert "model" not in payload
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert payload["tui"]["show_tooltips"] is False
    assert payload["projects"][str(workspace.resolve())]["trust_level"] == "trusted"


def test_codex_unattended_strategy_preserves_explicit_model_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.162.1")
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


@pytest.mark.parametrize("prompt_mode", ["unattended", "as_is"])
def test_codex_projects_resolved_permission_settings_above_project_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prompt_mode: str,
) -> None:
    """Set both native precedence boundaries while preserving unrelated TOML."""

    _stub_version(monkeypatch, output="codex-cli 0.169.0")
    workspace = tmp_path / "workspace"
    project_config = workspace / ".codex" / "config.toml"
    project_config.parent.mkdir(parents=True)
    project_content = 'sandbox_mode = "danger-full-access"\napproval_policy = "never"\n'
    project_config.write_text(project_content, encoding="utf-8")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")
    config_path = home / "config.toml"
    config_path.write_text(
        'model = "gpt-5.4-mini"\n'
        'model_provider = "test"\n'
        'sandbox_mode = "workspace-write"\n\n'
        '[model_providers.test]\nname = "Test"\n\n'
        '[[hooks.SessionStart]]\nmatcher = "resume"\n',
        encoding="utf-8",
    )

    approval, sandbox = (
        ("never", "danger-full-access")
        if prompt_mode == "unattended"
        else ("on-request", "read-only")
    )
    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=(),
            requested_operator_prompt_mode=prompt_mode,
            working_directory=workspace,
            home_path=home,
            env={},
            tool_params={"approval_policy": approval, "sandbox_mode": sandbox},
        )
    )

    effective = _load_toml(config_path)
    assert effective["sandbox_mode"] == sandbox
    assert effective["approval_policy"] == approval
    assert effective["model"] == "gpt-5.4-mini"
    assert effective["model_provider"] == "test"
    assert effective["model_providers"] == {"test": {"name": "Test"}}
    assert effective["hooks"] == {"SessionStart": [{"matcher": "resume"}]}
    assert f'--config=approval_policy="{approval}"' in result.args
    assert f'--config=sandbox_mode="{sandbox}"' in result.args
    assert project_config.read_text(encoding="utf-8") == project_content
    assert ("notice" in effective) == (prompt_mode == "unattended")


def test_codex_unattended_strategy_resolves_authored_permission_aliases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.162.1")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="codex_headless",
            executable="codex",
            base_args=(
                "--yolo",
                "-a",
                "on-request",
                "--ask-for-approval=on-failure",
                "-s",
                "workspace-write",
                "--sandbox=read-only",
                "-c",
                'approval_policy="never"',
                "--config",
                'sandbox_mode="danger-full-access"',
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
    assert result.permission_sources == {
        "approval_policy": "strategy:codex-unattended-0.162-plus",
        "sandbox_mode": "strategy:codex-unattended-0.162-plus",
    }


def test_reused_codex_home_restores_native_permission_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An as-is provider start discards earlier permission projections only."""

    _stub_version(monkeypatch, output="codex-cli 0.169.0")
    home = tmp_path / "home"
    home.mkdir()
    config = home / "config.toml"
    config.write_text('sandbox_mode = "read-only"\nmodel = "gpt-5.4-mini"\n')
    auth = home / "auth.json"
    auth.write_text('{"session_id":"test"}\n')
    request = LaunchPolicyRequest(
        tool="codex",
        backend="codex_headless",
        executable="codex",
        base_args=(),
        requested_operator_prompt_mode="unattended",
        working_directory=tmp_path,
        home_path=home,
        env={},
        tool_params={"sandbox_mode": "danger-full-access"},
        tool_param_sources={"sandbox_mode": "direct"},
    )
    first = apply_launch_policy(request)
    assert first.permissions == {"sandbox_mode": "danger-full-access", "approval_policy": "never"}
    assert first.permission_sources["sandbox_mode"].startswith("strategy:")
    assert first.permission_sources["approval_policy"].startswith("strategy:")
    assert apply_launch_policy(request).permissions == first.permissions

    observed = apply_launch_policy(
        replace(
            request,
            application_kind="resume_control",
            requested_operator_prompt_mode="as_is",
            tool_params={"sandbox_mode": "workspace-write"},
        )
    )
    assert observed.permissions == {"sandbox_mode": "workspace-write"}
    assert _load_toml(config)["approval_policy"] == "never"
    result = apply_launch_policy(
        replace(
            request,
            requested_operator_prompt_mode="as_is",
            tool_params={},
            tool_param_sources={},
        )
    )
    restored = _load_toml(config)
    assert result.permissions == {}
    assert restored["sandbox_mode"] == "read-only"
    assert "approval_policy" not in restored
    assert restored["model"] == "gpt-5.4-mini"
    assert auth.read_text() == '{"session_id":"test"}\n'


def test_codex_unattended_strategy_rejects_api_key_only_without_provider_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.162.1")
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


@pytest.mark.parametrize("version_output", ["2.1.296 (Claude Code)", "2.1.300 (Claude Code)"])
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
    assert result.provenance.selected_strategy_id == "claude-unattended-2.1.296"
    assert settings_payload["skipDangerousModePermissionPrompt"] is True
    assert settings_payload["permissions"]["defaultMode"] == "bypassPermissions"
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


@pytest.mark.parametrize("prompt_mode", ["unattended", "as_is"])
def test_claude_projects_authored_permission_mode_without_bypass_warning_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prompt_mode: str,
) -> None:
    """Use the resolved mode in both Claude's settings file and startup command."""

    _stub_version(monkeypatch, output="2.1.296 (Claude Code)")
    home = tmp_path / "claude-home"
    home.mkdir()
    settings_path = home / "settings.json"
    settings_path.write_text(
        json.dumps({"permissions": {"defaultMode": "acceptEdits", "deny": ["Bash(curl *)"]}}),
        encoding="utf-8",
    )
    expected_mode = "bypassPermissions" if prompt_mode == "unattended" else "dontAsk"
    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="claude",
            backend="claude_headless",
            executable="claude",
            base_args=("-p", "--include-partial-messages"),
            requested_operator_prompt_mode=prompt_mode,
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"ANTHROPIC_API_KEY": "sk-test"},
            tool_params={"permission_mode": expected_mode},
        )
    )

    permission_args = (
        ("--dangerously-skip-permissions",)
        if prompt_mode == "unattended"
        else ("--permission-mode", "dontAsk")
    )
    assert result.args == ("-p", "--include-partial-messages", *permission_args)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["permissions"] == {"defaultMode": expected_mode, "deny": ["Bash(curl *)"]}
    assert (home / ".claude.json").exists() == (prompt_mode == "unattended")


def test_claude_unattended_strategy_deduplicates_owned_launch_arg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.296 (Claude Code)")
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
    _stub_version(monkeypatch, output="2.1.296 (Claude Code)")
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
    _stub_version(monkeypatch, output="2.1.296 (Claude Code)")
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
    _stub_version(monkeypatch, output="2.1.296 (Claude Code)")
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
    _stub_version(monkeypatch, output="2.1.296 (Claude Code)")
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
        "permissions": {"defaultMode": "bypassPermissions"},
        "skipDangerousModePermissionPrompt": True,
    }
    state_payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_payload["hasCompletedOnboarding"] is True
    assert settings_path in replace_targets
    assert state_path in replace_targets


def test_codex_provider_start_repairs_blank_owned_toml_via_atomic_replace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="codex-cli 0.162.1")
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
    strategies = {item.strategy_id: item for item in documents[0].strategies}
    strategy = strategies["codex-unattended-0.162-plus"]
    assert any("--config" in note for note in strategy.minimal_inputs.notes)
    assert strategy.actions[-1].kind == "provider_hook.call"
    assert strategy.actions[-1].params == {"hook_id": "codex.append_unattended_cli_overrides"}
    service = strategies["codex-app-server-unattended-0.169.0"]
    assert service.backends == ("codex_app_server",)
    assert service.supported_versions.to_payload() == ">=0.169.0"
    assert service.system_prompt.owned_surface == "developerInstructions"
    assert all(action.params != strategy.actions[-1].params for action in service.actions)


def test_kimi_registry_declares_native_home_system_prompt() -> None:
    documents = load_registry_documents(tool="kimi")

    assert len(documents) == 1
    supported_versions = {
        "kimi-unattended-2.1-plus": ">=2.1.1",
        "kimi-tui-unattended-2.1-plus": ">=2.1.1",
        "kimi-acp-unattended-2.6.0": ">=2.6.0",
        "kimi-web-unattended-2.6.0": ">=2.6.0",
    }
    assert {strategy.strategy_id for strategy in documents[0].strategies} == set(supported_versions)
    for strategy in documents[0].strategies:
        contract = strategy.system_prompt
        assert contract.method == "native_home_system_prompt"
        assert contract.owned_surface == "SYSTEM.md"
        assert contract.required_engine_env == {"KIMI_CODE_LEGACY_FLAG": "0"}
        assert contract.evidence
        assert strategy.supported_versions.to_payload() == supported_versions[strategy.strategy_id]
        assert strategy.to_metadata_payload()["system_prompt"] == contract.to_payload()


@pytest.mark.parametrize("tool", ["dsh", "kimi", "claude", "codex"])
def test_packaged_strategies_use_inclusive_minimums(tool: str, tmp_path: Path) -> None:
    """Each packaged backend selects one strategy at its minimum and on later builds."""

    (document,) = load_registry_documents(tool=tool)
    for strategy in document.strategies:
        minimum = strategy.supported_versions.to_payload()
        assert minimum.startswith(">=")
        floor = ToolVersion.parse(minimum.removeprefix(">="))
        for backend in strategy.backends:
            request = LaunchPolicyRequest(
                tool=tool,
                backend=backend,
                executable=tool,
                base_args=(),
                requested_operator_prompt_mode=strategy.operator_prompt_mode,
                working_directory=tmp_path,
                home_path=tmp_path / "home",
                env={},
            )
            assert resolve_strategy(request=request, detected_version=floor) == (
                strategy,
                "registry",
            )
            assert resolve_strategy(
                request=request, detected_version=ToolVersion.parse("9.9.9")
            ) == (strategy, "registry")
            with pytest.raises(LaunchPolicyError, match="No compatible unattended launch strategy"):
                resolve_strategy(request=request, detected_version=ToolVersion.parse("0.0.0"))


@pytest.mark.parametrize("tool", ["claude", "codex"])
def test_native_prompt_registries_declare_explicit_native_method(tool: str) -> None:
    documents = load_registry_documents(tool=tool)

    assert len(documents) == 1
    for strategy in documents[0].strategies:
        assert strategy.system_prompt.method in {
            "native_developer_instructions",
            "native_append_system_prompt",
        }
        assert strategy.system_prompt.owned_surface


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


def test_kimi_unattended_strategy_uses_native_prompt_permissions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.1")
    home = tmp_path / "kimi-home"
    home.mkdir()

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="kimi",
            backend="kimi_headless",
            executable="/opt/kimi/bin/kimi",
            base_args=(
                "--auto",
                "--model",
                "kimi-code/kimi-for-coding",
            ),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"KIMI_CODE_LEGACY_FLAG": "0"},
        )
    )

    assert result.args == ("--model", "kimi-code/kimi-for-coding")
    assert result.provenance is not None
    assert result.provenance.selected_strategy_id == "kimi-unattended-2.1-plus"
    assert result.strategy is not None
    assert result.strategy.backends == ("kimi_headless",)
    assert [action.kind for action in result.strategy.actions] == [
        "provider_hook.call",
        "provider_hook.call",
    ]
    assert not (home / "config.toml").exists()


@pytest.mark.parametrize(
    ("authored_mode", "expected_mode", "expected_flags"),
    [(None, "auto", ("--auto",)), ("manual", "manual", ()), ("yolo", "yolo", ("--yolo",))],
)
def test_kimi_raw_launch_projects_resolved_mode_and_preserves_other_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    authored_mode: str | None,
    expected_mode: str,
    expected_flags: tuple[str, ...],
) -> None:
    _stub_version(monkeypatch, output="2.1.1")
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
                "--plan",
                "--model",
                "kimi-code/kimi-for-coding",
                "--temperature",
                "0",
            ),
            requested_operator_prompt_mode="unattended" if authored_mode is None else "as_is",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"KIMI_CODE_LEGACY_FLAG": "0"},
            tool_params={"permission_mode": authored_mode} if authored_mode else {},
        )
    )

    payload = _load_toml(home / "config.toml")
    assert result.args == (
        "--plan",
        "--model",
        "kimi-code/kimi-for-coding",
        "--temperature",
        "0",
        *expected_flags,
    )
    assert (result.provenance is None) == (authored_mode is not None)
    assert (home / ".skip-migration-from-kimi-cli").is_file() == (authored_mode is None)
    assert payload["default_permission_mode"] == expected_mode
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
            base_args=("--model", "kimi-code"),
            requested_operator_prompt_mode="as_is",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    assert result.args == ("--model", "kimi-code")
    assert result.provenance is None
    assert result.strategy is None
    assert config_path.read_text(encoding="utf-8") == original_config


def test_kimi_registry_declares_separate_mode_strategies() -> None:
    documents = load_registry_documents(tool="kimi")

    strategies = {strategy.strategy_id: strategy for strategy in documents[0].strategies}
    assert strategies["kimi-unattended-2.1-plus"].backends == ("kimi_headless",)
    assert strategies["kimi-tui-unattended-2.1-plus"].backends == ("raw_launch",)
    assert strategies["kimi-acp-unattended-2.6.0"].backends == ("kimi_acp",)
    assert strategies["kimi-web-unattended-2.6.0"].backends == ("kimi_web",)
    assert [action.kind for action in strategies["kimi-tui-unattended-2.1-plus"].actions] == [
        "provider_hook.call",
        "provider_hook.call",
        "provider_hook.call",
    ]


@pytest.mark.parametrize("version", ["2.1.1", "2.2.0", "7.2.1"])
def test_kimi_minimum_only_strategy_accepts_baseline_and_newer_versions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    version: str,
) -> None:
    """The Kimi strategy has a floor and intentionally has no upper bound."""

    _stub_version(monkeypatch, output=version)
    home = tmp_path / "kimi-home"
    home.mkdir()

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="kimi",
            backend="kimi_headless",
            executable="kimi",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path,
            home_path=home,
            env={"KIMI_CODE_LEGACY_FLAG": "0"},
        )
    )

    assert result.provenance is not None
    assert result.provenance.detected_tool_version == version
    assert result.provenance.selected_strategy_id == "kimi-unattended-2.1-plus"


def test_kimi_native_prompt_hook_rejects_engine_and_agent_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Provider-start hooks fail before a selector or legacy engine bypasses SYSTEM.md."""

    _stub_version(monkeypatch, output="2.1.1")
    home = tmp_path / "kimi-home"
    home.mkdir()

    with pytest.raises(LaunchPolicyError, match="legacy engine"):
        apply_launch_policy(
            LaunchPolicyRequest(
                tool="kimi",
                backend="kimi_headless",
                executable="kimi",
                base_args=(),
                requested_operator_prompt_mode="unattended",
                working_directory=tmp_path,
                home_path=home,
                env={"KIMI_CODE_LEGACY_FLAG": "1"},
            )
        )

    with pytest.raises(LaunchPolicyError, match="higher-priority launch option"):
        apply_launch_policy(
            LaunchPolicyRequest(
                tool="kimi",
                backend="kimi_headless",
                executable="kimi",
                base_args=("--agent-file=other.md",),
                requested_operator_prompt_mode="unattended",
                working_directory=tmp_path,
                home_path=home,
                env={"KIMI_CODE_LEGACY_FLAG": "0"},
            )
        )


def test_kimi_unattended_strategy_fails_closed_for_unknown_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_version(monkeypatch, output="2.1.0")
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


@pytest.mark.parametrize(
    ("output", "reported", "eligible"),
    [
        ("dsh 0.2.2-rc.2", "0.2.2-rc.2", False),
        ("dsh v0.2.2-rc.3", "0.2.2-rc.3", True),
        ("dsh 0.2.2rc4", "0.2.2rc4", True),
        ("0.2.2-rc.4+local", "0.2.2-rc.4+local", True),
        ("codex-cli 0.171.0 (local build)", "0.171.0", True),
        ("2.1.330 (Claude Code)", "2.1.330", True),
        ("2.7.2", "2.7.2", True),
        ("2.7.2a1", "2.7.2a1", False),
        ("2.7.2-beta.1", "2.7.2-beta.1", False),
        ("2.7.2.dev1", "2.7.2.dev1", False),
    ],
)
def test_detect_tool_version_preserves_release_channels(
    monkeypatch: pytest.MonkeyPatch, output: str, reported: str, eligible: bool
) -> None:
    """Apply channel and ordering rules to the full native version token."""

    _stub_version(monkeypatch, output=output)

    observed = detect_tool_version(executable="selected-cli")

    assert observed.raw == reported
    assert SupportedVersionSpec.parse(">=0.2.2rc3").contains(observed) is eligible


@pytest.mark.parametrize("output", ["git build", "2.7.2invalid", "2.7.2-"])
def test_detect_tool_version_rejects_malformed_output(
    monkeypatch: pytest.MonkeyPatch, output: str
) -> None:
    """A malformed suffix cannot turn into an allowed stable release."""

    _stub_version(monkeypatch, output=output)

    with pytest.raises(LaunchPolicyError, match="version"):
        detect_tool_version(executable="selected-cli")


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
                "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY": "codex-unattended-0.162-plus",
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


def test_codex_canonicalization_preserves_hook_config_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The owned-surface deny-list never strips launch-owned or caller hook config."""

    _stub_version(monkeypatch, output="codex-cli 0.162.1")
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text('{"session_id":"abc"}\n', encoding="utf-8")
    state_override = 'hooks.state."/runtime/home/hooks.json:stop:0:0".trusted_hash="sha256:abc"'
    hooks_override = 'hooks.SessionStart=[{"hooks":[{"type":"command","command":"audit"}]}]'

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool="codex",
            backend="raw_launch",
            executable="codex",
            base_args=(
                "-c",
                state_override,
                "--config",
                hooks_override,
                "-c",
                'approval_policy="never"',
            ),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={},
        )
    )

    assert state_override in result.args
    assert hooks_override in result.args
    assert '--config=approval_policy="never"' in result.args
    assert 'approval_policy="never"' not in result.args
    assert "--dangerously-bypass-hook-trust" not in result.args


@pytest.mark.parametrize(
    ("profile", "expected_error"),
    [
        (":read-only", "sandbox_mode=danger-full-access.*launch args.*sandbox_mode=read-only"),
        ("custom", "default_permissions.*cannot qualify"),
    ],
)
def test_codex_unattended_validates_native_permission_profiles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: str, expected_error: str
) -> None:
    """A native profile selector cannot replace the qualified sandbox."""

    _stub_version(monkeypatch, output="codex-cli 0.172.0")
    home = tmp_path / "home"
    request = LaunchPolicyRequest(
        tool="codex",
        backend="raw_launch",
        executable="codex",
        base_args=(f'--config=default_permissions="{profile}"',),
        requested_operator_prompt_mode=None,
        working_directory=tmp_path,
        home_path=home,
        env={},
    )
    with pytest.raises(LaunchPolicyError, match=expected_error + ".*as_is"):
        apply_launch_policy(request)
    assert not home.exists()

    custom = apply_launch_policy(replace(request, requested_operator_prompt_mode="as_is"))
    assert custom.args == request.base_args


def test_codex_registry_documents_hook_observation_owned_surfaces() -> None:
    documents = load_registry_documents(tool="codex")

    strategy = next(
        item
        for item in documents[0].strategies
        if item.strategy_id == "codex-unattended-0.162-plus"
    )
    owned = {spec.path: spec.keys for spec in strategy.owned_paths}
    config_keys = owned["config.toml"]
    assert any("hooks.state." in key and "trusted_hash" in key for key in config_keys)
    assert len(owned["hooks.json"]) == 1
    assert "hooks.<Event>" in owned["hooks.json"][0]

    notes = "\n".join(strategy.minimal_inputs.notes)
    assert "hooks are stable" in notes
    assert ">=0.162.1" in notes
    assert "HOUMAO_HOOK_OBSERVATION_CODEX=1" in notes
    assert "--dangerously-bypass-hook-trust" in notes

    evidence_refs = [item.ref for item in strategy.evidence]
    assert any(
        "context/campaigns/debug/2026-10-20-codex-hook-observation/" in ref for ref in evidence_refs
    )
    assert any("extern/orphan/codex/codex-rs/hooks/" in ref for ref in evidence_refs)


def test_kimi_permission_projection_preserves_native_config_hooks(tmp_path: Path) -> None:
    home = tmp_path / "kimi-home"
    home.mkdir()
    config_path = home / "config.toml"
    original_config = (
        'default_permission_mode = "manual"\n'
        "\n[[hooks]]\n"
        'event = "Stop"\n'
        'command = "houmao-emitter --generation 1"\n'
        "timeout = 5\n"
    )
    config_path.write_text(original_config, encoding="utf-8")

    headless_args = ["--auto", "--session", "session-1", "--model", "kimi-code"]
    provider_hooks.run_provider_hook(
        hook_id="kimi.canonicalize_unattended_launch_inputs",
        request=LaunchPolicyRequest(
            tool="kimi",
            backend="kimi_headless",
            executable="kimi",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"KIMI_CODE_LEGACY_FLAG": "0"},
        ),
        args=headless_args,
    )

    assert headless_args == ["--model", "kimi-code"]
    assert config_path.read_text(encoding="utf-8") == original_config

    tui_args = ["--model", "kimi-code"]
    provider_hooks.run_provider_hook(
        hook_id="kimi.project_tui_permission",
        request=LaunchPolicyRequest(
            tool="kimi",
            backend="raw_launch",
            executable="kimi",
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=tmp_path / "workspace",
            home_path=home,
            env={"KIMI_CODE_LEGACY_FLAG": "0"},
            tool_params={"permission_mode": "yolo"},
        ),
        args=tui_args,
    )

    assert tui_args == ["--model", "kimi-code", "--yolo"]
    assert _load_toml(config_path) == {
        **tomllib.loads(original_config),
        "default_permission_mode": "yolo",
    }


def test_kimi_policy_toml_writer_cannot_serialize_an_existing_hooks_array(
    tmp_path: Path,
) -> None:
    """Pin the constraint behind installing the observer block last."""

    config_path = tmp_path / "config.toml"
    original_config = (
        'default_model = "kimi-code/kimi-for-coding"\n'
        "\n[[hooks]]\n"
        'event = "Stop"\n'
        'command = "houmao-emitter --generation 1"\n'
        "timeout = 5\n"
    )
    config_path.write_text(original_config, encoding="utf-8")

    with pytest.raises(LaunchPolicyError, match="Unsupported TOML scalar value"):
        provider_hooks.set_toml_key(
            path=config_path,
            key_path=("default_permission_mode",),
            value="auto",
        )

    assert config_path.read_text(encoding="utf-8") == original_config


def test_kimi_registry_documents_hook_observation_owned_surfaces() -> None:
    documents = load_registry_documents(tool="kimi")

    for strategy in documents[0].strategies:
        config_keys = [
            key for spec in strategy.owned_paths if spec.path == "config.toml" for key in spec.keys
        ]
        if strategy.backends in {("kimi_acp",), ("kimi_web",)}:
            assert set(config_keys) == {"default_model", "default_permission_mode"}
            continue
        assert any(
            "hooks." in key and "event, matcher, command, timeout" in key for key in config_keys
        )

        notes = "\n".join(strategy.minimal_inputs.notes)
        assert "hooks are stable" in notes
        assert ">=2.1.1" in notes
        assert "0.32.0" in notes
        assert "HOUMAO_HOOK_OBSERVATION_KIMI=1" in notes
        assert "[[hooks]]" in notes

        evidence_refs = [item.ref for item in strategy.evidence]
        assert any(
            "context/campaigns/debug/2026-10-20-kimi-hook-observation/" in ref
            for ref in evidence_refs
        )
        assert any("extern/orphan/kimi-code/" in ref for ref in evidence_refs)
