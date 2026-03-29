from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller.launch_plan import (
    LaunchPlanRequest,
    backend_for_tool,
    build_launch_plan,
    configured_cao_parsing_mode,
    configured_cao_shadow_policy,
    plan_role_injection,
    resolve_cao_parsing_mode,
    tool_supports_cao_shadow_parser,
)
from houmao.agents.realm_controller.errors import LaunchPlanError
from houmao.agents.realm_controller.loaders import (
    load_role_package,
    parse_allowlisted_env,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest(
    *,
    tool: str,
    executable: str,
    home_env_var: str,
    home_path: Path,
    env_file: Path,
    allowlisted_env_vars: list[str],
    launch_args: list[str] | None = None,
    launch_policy: dict[str, Any] | None = None,
    runtime_extra: dict[str, Any] | None = None,
    recipe_overrides: dict[str, Any] | None = None,
    direct_overrides: dict[str, Any] | None = None,
    tool_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adapter_path = "/tmp/tool-adapter.yaml"
    runtime: dict[str, Any] = {
        "runtime_root": str(home_path.parent),
        "home_id": "test-home",
        "home_path": str(home_path),
        "launch_helper": str(home_path / "launch.sh"),
        "launch_executable": executable,
        "launch_home_selector": {
            "env_var": home_env_var,
            "value": str(home_path),
        },
        "launch_contract": {
            "adapter_defaults": {
                "args": list(launch_args or []),
                "tool_params": {},
            },
            "requested_overrides": {
                "preset": recipe_overrides,
                "direct": direct_overrides,
            },
            "tool_metadata": tool_metadata or {"tool_params": {}},
            "construction_provenance": {
                "adapter_path": adapter_path,
                "preset_path": None,
                "preset_overrides_present": recipe_overrides is not None,
                "direct_overrides_present": direct_overrides is not None,
            },
        },
    }
    if runtime_extra is not None:
        runtime.update(runtime_extra)

    manifest: dict[str, Any] = {
        "schema_version": 3,
        "inputs": {
            "tool": tool,
            "skills": [],
            "setup": "default",
            "auth": "default",
            "adapter_path": adapter_path,
            "preset_path": None,
        },
        "runtime": runtime,
        "credentials": {
            "auth_path": str(home_path.parent / "auth"),
            "projected_files": [],
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": allowlisted_env_vars,
            },
        },
    }
    manifest["launch_policy"] = (
        launch_policy if launch_policy is not None else {"operator_prompt_mode": "as_is"}
    )
    return manifest


def test_load_role_package_reads_prompt(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    role_path = agent_def_dir / "roles/test-role/system-prompt.md"
    _write(role_path, "You are role test.\n")

    role = load_role_package(agent_def_dir, "test-role")

    assert role.role_name == "test-role"
    assert role.path == role_path
    assert "You are role test" in role.system_prompt


def test_load_role_package_allows_empty_prompt(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    role_path = agent_def_dir / "roles/test-role/system-prompt.md"
    _write(role_path, "")

    role = load_role_package(agent_def_dir, "test-role")

    assert role.path == role_path
    assert role.system_prompt == ""


def test_plan_role_injection_native_vs_bootstrap() -> None:
    codex = plan_role_injection(
        backend="codex_headless",
        role_name="r",
        role_prompt="prompt",
    )
    claude = plan_role_injection(
        backend="claude_headless",
        role_name="r",
        role_prompt="prompt",
    )
    gemini = plan_role_injection(
        backend="gemini_headless",
        role_name="r",
        role_prompt="prompt",
    )
    claude_local = plan_role_injection(
        backend="local_interactive",
        tool="claude",
        role_name="r",
        role_prompt="prompt",
    )

    assert codex.method == "native_developer_instructions"
    assert claude.method == "native_append_system_prompt"
    assert gemini.method == "bootstrap_message"
    assert gemini.bootstrap_message is not None
    assert claude_local.method == "native_append_system_prompt"


def test_plan_role_injection_empty_prompt_skips_bootstrap_message() -> None:
    claude = plan_role_injection(
        backend="claude_headless",
        role_name="r",
        role_prompt="",
    )
    gemini = plan_role_injection(
        backend="gemini_headless",
        role_name="r",
        role_prompt="",
    )
    claude_local = plan_role_injection(
        backend="local_interactive",
        tool="claude",
        role_name="r",
        role_prompt="",
    )

    assert claude.bootstrap_message == ""
    assert gemini.bootstrap_message == ""
    assert claude_local.bootstrap_message == ""


def test_backend_for_tool_defaults_to_codex_headless() -> None:
    assert backend_for_tool("codex") == "codex_headless"
    assert backend_for_tool("codex", prefer_cao=True) == "cao_rest"
    assert backend_for_tool("codex", prefer_local_interactive=True) == "local_interactive"


def test_build_launch_plan_uses_allowlisted_env_and_redacts_values(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text(
        "OPENAI_API_KEY=sk-secret\nOPENAI_BASE_URL=https://api.example\nEXTRA=nope\n",
        encoding="utf-8",
    )
    role_prompt_path = tmp_path / "repo/roles/test-role/system-prompt.md"
    _write(role_prompt_path, "Test role prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY", "OPENAI_BASE_URL"],
    )

    role = load_role_package(tmp_path / "repo", "test-role")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="codex_app_server",
            working_directory=tmp_path,
        )
    )

    assert plan.env["OPENAI_API_KEY"] == "sk-secret"
    assert "EXTRA" not in plan.env

    redacted = plan.redacted_payload()
    assert redacted["env_var_names"] == ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    assert "sk-secret" not in str(redacted)


def test_build_launch_plan_populates_mailbox_env_bindings(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    role_prompt_path = tmp_path / "repo/roles/test-role/system-prompt.md"
    _write(role_prompt_path, "Test role prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
    )

    role = load_role_package(tmp_path / "repo", "test-role")
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=(tmp_path / "shared-mail").resolve(),
        bindings_version="2026-03-12T05:00:00.000001Z",
    )
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="codex_headless",
            working_directory=tmp_path,
            mailbox=mailbox,
        )
    )

    assert plan.mailbox == mailbox
    assert plan.env["AGENTSYS_MAILBOX_TRANSPORT"] == "filesystem"
    assert plan.env["AGENTSYS_MAILBOX_FS_ROOT"] == str(mailbox.filesystem_root)
    assert plan.env["AGENTSYS_MAILBOX_FS_SQLITE_PATH"] == str(
        mailbox.filesystem_root / "index.sqlite"
    )
    assert plan.env["AGENTSYS_MAILBOX_FS_INBOX_DIR"] == str(
        mailbox.filesystem_root / "mailboxes" / "AGENTSYS-research@agents.localhost" / "inbox"
    )
    assert plan.env["AGENTSYS_MAILBOX_FS_MAILBOX_DIR"] == str(
        mailbox.filesystem_root / "mailboxes" / "AGENTSYS-research@agents.localhost"
    )
    assert plan.env["AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH"] == str(
        mailbox.filesystem_root
        / "mailboxes"
        / "AGENTSYS-research@agents.localhost"
        / "mailbox.sqlite"
    )
    assert "AGENTSYS_MAILBOX_FS_ROOT" in plan.env_var_names
    assert plan.redacted_payload()["mailbox"]["principal_id"] == "AGENTSYS-research"


def test_build_launch_plan_resolves_launch_policy_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    def _fake_version(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> object:
        del check, capture_output, text
        return type(
            "_Completed",
            (),
            {"stdout": "codex-cli 0.116.0", "stderr": "", "args": command},
        )()

    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.subprocess.run",
        _fake_version,
    )

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        launch_policy={"operator_prompt_mode": "unattended"},
    )

    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="codex_headless",
            working_directory=tmp_path,
        )
    )

    assert plan.launch_policy_provenance is not None
    assert plan.launch_policy_provenance.selected_strategy_id == "codex-unattended-0.116.x"
    assert plan.redacted_payload()["launch_policy_provenance"]["selection_source"] == "registry"


def test_build_launch_plan_honors_process_env_strategy_override_without_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    def _fake_version(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> object:
        del check, capture_output, text
        return type(
            "_Completed",
            (),
            {"stdout": "codex-cli 9.9.9", "stderr": "", "args": command},
        )()

    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.subprocess.run",
        _fake_version,
    )
    monkeypatch.setenv(
        "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY",
        "codex-unattended-0.116.x",
    )

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        launch_policy={"operator_prompt_mode": "unattended"},
    )

    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="codex_headless",
            working_directory=tmp_path,
        )
    )

    assert plan.launch_policy_provenance is not None
    assert plan.launch_policy_provenance.selection_source == "env_override"
    assert plan.launch_policy_provenance.override_env_var_name == (
        "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY"
    )
    assert plan.env["OPENAI_API_KEY"] == "sk-secret"
    assert "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY" not in plan.env
    assert "HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY" not in plan.env_var_names


def test_parse_allowlisted_env_selects_claude_model_selection_vars(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text(
        (
            "ANTHROPIC_MODEL=opus\n"
            "ANTHROPIC_SMALL_FAST_MODEL=claude-3-5-haiku-latest\n"
            "CLAUDE_CODE_SUBAGENT_MODEL=sonnet\n"
            "ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-1-20250805\n"
            "UNALLOWLISTED=value\n"
        ),
        encoding="utf-8",
    )

    selected, selected_names = parse_allowlisted_env(
        env_file,
        [
            "ANTHROPIC_MODEL",
            "ANTHROPIC_SMALL_FAST_MODEL",
            "CLAUDE_CODE_SUBAGENT_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
        ],
    )

    assert selected == {
        "ANTHROPIC_MODEL": "opus",
        "ANTHROPIC_SMALL_FAST_MODEL": "claude-3-5-haiku-latest",
        "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-1-20250805",
    }
    assert selected_names == [
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
    ]


@pytest.mark.parametrize(
    ("tool", "backend", "launch_args", "expected_arg", "protocol_arg"),
    [
        ("codex", "codex_app_server", ["--x"], "--x", "app-server"),
        ("claude", "claude_headless", ["--x"], "--x", "-p"),
        ("gemini", "gemini_headless", ["--x"], "--x", "-p"),
    ],
)
def test_build_launch_plan_keeps_optional_args_separate_from_protocol_args(
    tmp_path: Path,
    tool: str,
    backend: str,
    launch_args: list[str],
    expected_arg: str,
    protocol_arg: str,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("A=1\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool=tool,
        executable="tool",
        home_env_var="HOME_VAR",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["A"],
        launch_args=launch_args,
    )

    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend=backend,  # type: ignore[arg-type]
            working_directory=tmp_path,
        )
    )

    assert expected_arg in plan.args
    protocol_args = plan.metadata["launch_overrides"]["backend_resolution"][
        "protocol_reserved_args"
    ]
    assert protocol_arg in protocol_args
    assert protocol_arg not in plan.args


def test_build_launch_plan_rejects_claude_reserved_headless_args(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("A=1\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="claude",
        executable="claude",
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["A"],
        launch_args=["-p", "--resume", "existing-session"],
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="backend-reserved argument"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="claude_headless",
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_rejects_codex_headless_reserved_args(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("A=1\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["A"],
        launch_args=["exec", "--json"],
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="backend-reserved argument"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="codex_headless",
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_codex_headless_sets_cli_mode_metadata(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("A=1\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")
    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["A"],
        launch_args=["--x"],
    )
    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="codex_headless",
            working_directory=tmp_path,
        )
    )

    assert "app-server" not in plan.args
    assert plan.metadata["codex_headless_cli_mode"] == "exec_json_resume"


@pytest.mark.parametrize(
    ("tool", "expected"),
    [
        ("codex", "shadow_only"),
        ("claude", "shadow_only"),
    ],
)
def test_resolve_cao_parsing_mode_uses_tool_defaults(tool: str, expected: str) -> None:
    assert (
        resolve_cao_parsing_mode(
            tool=tool,
            requested_mode=None,
            configured_mode=None,
        )
        == expected
    )


def test_resolve_cao_parsing_mode_rejects_unknown_value() -> None:
    with pytest.raises(LaunchPlanError, match="Unsupported CAO parsing mode"):
        resolve_cao_parsing_mode(
            tool="codex",
            requested_mode="hybrid",
            configured_mode=None,
        )


def test_resolve_cao_parsing_mode_accepts_explicit_cao_only_without_shadow_parser_support() -> None:
    assert (
        resolve_cao_parsing_mode(
            tool="gemini",
            requested_mode="cao_only",
            configured_mode=None,
        )
        == "cao_only"
    )


def test_resolve_cao_parsing_mode_rejects_shadow_only_without_shadow_parser_support() -> None:
    with pytest.raises(LaunchPlanError, match="no runtime shadow parser is available"):
        resolve_cao_parsing_mode(
            tool="gemini",
            requested_mode="shadow_only",
            configured_mode=None,
        )


@pytest.mark.parametrize(
    ("tool", "expected"),
    [
        ("claude", True),
        ("codex", True),
        ("gemini", False),
    ],
)
def test_tool_supports_cao_shadow_parser(tool: str, expected: bool) -> None:
    assert tool_supports_cao_shadow_parser(tool) is expected


def test_build_launch_plan_records_configured_cao_parsing_mode(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        runtime_extra={"cao": {"parsing_mode": "shadow_only"}},
    )

    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="cao_rest",
            working_directory=tmp_path,
        )
    )

    assert configured_cao_parsing_mode(plan) == "shadow_only"


def test_build_launch_plan_rejects_unknown_cao_parsing_mode(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        runtime_extra={"cao_parsing_mode": "hybrid"},
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="Unsupported CAO parsing mode"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="cao_rest",
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_records_shadow_stall_policy_config(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        runtime_extra={
            "cao": {
                "parsing_mode": "shadow_only",
                "shadow": {
                    "unknown_to_stalled_timeout_seconds": 7,
                    "completion_stability_seconds": 1.5,
                    "stalled_is_terminal": True,
                },
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="cao_rest",
            working_directory=tmp_path,
        )
    )

    assert configured_cao_shadow_policy(plan) == {
        "unknown_to_stalled_timeout_seconds": 7.0,
        "completion_stability_seconds": 1.5,
        "stalled_is_terminal": True,
    }


def test_build_launch_plan_rejects_invalid_shadow_unknown_timeout(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        runtime_extra={
            "cao": {
                "shadow": {
                    "unknown_to_stalled_timeout_seconds": 0,
                }
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="must be > 0"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="cao_rest",
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_rejects_invalid_shadow_terminality_type(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        runtime_extra={
            "cao": {
                "shadow": {
                    "unknown_to_stalled_timeout_seconds": 5,
                    "stalled_is_terminal": "yes",
                }
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="Expected boolean"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="cao_rest",
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_rejects_invalid_completion_stability_timeout(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        runtime_extra={
            "cao": {
                "shadow": {
                    "completion_stability_seconds": 0,
                }
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="must be > 0"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="cao_rest",
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_rejects_invalid_completion_stability_type(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        runtime_extra={
            "cao": {
                "shadow": {
                    "completion_stability_seconds": "fast",
                }
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="Expected number"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="cao_rest",
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_resolves_claude_typed_launch_param(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="claude",
        executable="claude",
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["ANTHROPIC_API_KEY"],
        recipe_overrides={"tool_params": {"include_partial_messages": True}},
        tool_metadata={
            "tool_params": {
                "include_partial_messages": {
                    "type": "boolean",
                    "backends": {
                        "claude_headless": {
                            "args_when_true": ["--include-partial-messages"],
                        }
                    },
                }
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="claude_headless",
            working_directory=tmp_path,
        )
    )

    assert "--include-partial-messages" in plan.args
    assert "-p" not in plan.args
    assert plan.metadata["launch_overrides"]["backend_resolution"]["translated_args"] == [
        "--include-partial-messages"
    ]


def test_build_launch_plan_local_interactive_uses_raw_launch_surface(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="claude",
        executable="claude",
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["ANTHROPIC_API_KEY"],
        recipe_overrides={"tool_params": {"include_partial_messages": True}},
        tool_metadata={
            "tool_params": {
                "include_partial_messages": {
                    "type": "boolean",
                    "backends": {
                        "raw_launch": {
                            "args_when_true": ["--include-partial-messages"],
                        }
                    },
                }
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="local_interactive",
            working_directory=tmp_path,
        )
    )

    assert plan.role_injection.method == "native_append_system_prompt"
    assert "--include-partial-messages" in plan.args
    assert plan.metadata["launch_overrides"]["backend_resolution"]["backend"] == "raw_launch"
    assert plan.metadata["launch_overrides"]["backend_resolution"]["protocol_reserved_args"] == []


def test_build_launch_plan_rejects_codex_partial_streaming_tool_param(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
        direct_overrides={"tool_params": {"include_partial_messages": True}},
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="tool `codex` exposes no supported"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="codex_headless",
                working_directory=tmp_path,
            )
        )


@pytest.mark.parametrize("backend", ["cao_rest", "houmao_server_rest"])
def test_build_launch_plan_rejects_rest_backends_that_cannot_honor_overrides(
    tmp_path: Path,
    backend: str,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="claude",
        executable="claude",
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["ANTHROPIC_API_KEY"],
        recipe_overrides={"tool_params": {"include_partial_messages": True}},
        tool_metadata={
            "tool_params": {
                "include_partial_messages": {
                    "type": "boolean",
                    "backends": {
                        "claude_headless": {
                            "args_when_true": ["--include-partial-messages"],
                        }
                    },
                }
            }
        },
    )

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="cannot honor launch overrides"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend=backend,  # type: ignore[arg-type]
                working_directory=tmp_path,
            )
        )


def test_build_launch_plan_rejects_schema_version_1_manifest(tmp_path: Path) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("OPENAI_API_KEY=sk-secret\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = _manifest(
        tool="codex",
        executable="codex",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env_file=env_file,
        allowlisted_env_vars=["OPENAI_API_KEY"],
    )
    manifest["schema_version"] = 1

    role = load_role_package(tmp_path / "repo", "r")
    with pytest.raises(LaunchPlanError, match="Rebuild the affected brain home"):
        build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role,
                backend="codex_headless",
                working_directory=tmp_path,
            )
        )
