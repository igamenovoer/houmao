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
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert payload["model"] == "gpt-5.4"
    assert payload["notice"]["hide_full_access_warning"] is True
    assert payload["notice"]["model_migrations"]["gpt-5.3-codex"] == "gpt-5.4"
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
model = "gpt-5.4"
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
    assert payload["model_provider"] == "yunwu-openai"
    assert payload["approval_policy"] == "never"
    assert payload["sandbox_mode"] == "danger-full-access"
    assert payload["projects"][str((tmp_path / "workspace").resolve())]["trust_level"] == "trusted"


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
