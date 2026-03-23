from __future__ import annotations

from pathlib import Path

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


def test_load_role_package_reads_prompt(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    role_path = agent_def_dir / "roles/test-role/system-prompt.md"
    _write(role_path, "You are role test.\n")

    role = load_role_package(agent_def_dir, "test-role")

    assert role.role_name == "test-role"
    assert role.path == role_path
    assert "You are role test" in role.system_prompt


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

    assert codex.method == "native_developer_instructions"
    assert claude.method == "native_append_system_prompt"
    assert gemini.method == "bootstrap_message"
    assert gemini.bootstrap_message is not None


def test_backend_for_tool_defaults_to_codex_headless() -> None:
    assert backend_for_tool("codex") == "codex_headless"
    assert backend_for_tool("codex", prefer_cao=True) == "cao_rest"


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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY", "OPENAI_BASE_URL"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "launch_policy": {"operator_prompt_mode": "unattended"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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
    ("backend", "launch_args", "expected_arg"),
    [
        ("codex_app_server", ["--x"], "app-server"),
        ("claude_headless", ["-p", "--x"], "-p"),
        ("gemini_headless", ["--x"], "-p"),
    ],
)
def test_build_launch_plan_backend_args(
    tmp_path: Path,
    backend: str,
    launch_args: list[str],
    expected_arg: str,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("A=1\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = {
        "inputs": {"tool": "codex" if backend == "codex_app_server" else "claude"},
        "runtime": {
            "launch_executable": "tool",
            "launch_args": launch_args,
            "launch_home_selector": {
                "env_var": "HOME_VAR",
                "value": str(tmp_path / "home"),
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["A"],
            }
        },
    }

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


def test_build_launch_plan_rejects_claude_reserved_headless_args(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "vars.env"
    env_file.write_text("A=1\n", encoding="utf-8")
    _write(tmp_path / "repo/roles/r/system-prompt.md", "prompt")

    manifest = {
        "inputs": {"tool": "claude"},
        "runtime": {
            "launch_executable": "claude",
            "launch_args": ["-p", "--resume", "existing-session"],
            "launch_home_selector": {
                "env_var": "CLAUDE_CONFIG_DIR",
                "value": str(tmp_path / "home"),
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["A"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": ["exec", "--json"],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["A"],
            }
        },
    }

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
    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": ["--x"],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["A"],
            }
        },
    }
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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
            "cao": {"parsing_mode": "shadow_only"},
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
            "cao_parsing_mode": "hybrid",
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
            "cao": {
                "parsing_mode": "shadow_only",
                "shadow": {
                    "unknown_to_stalled_timeout_seconds": 7,
                    "completion_stability_seconds": 1.5,
                    "stalled_is_terminal": True,
                },
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
            "cao": {
                "shadow": {
                    "unknown_to_stalled_timeout_seconds": 0,
                }
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
            "cao": {
                "shadow": {
                    "unknown_to_stalled_timeout_seconds": 5,
                    "stalled_is_terminal": "yes",
                }
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
            "cao": {
                "shadow": {
                    "completion_stability_seconds": 0,
                }
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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

    manifest = {
        "inputs": {"tool": "codex"},
        "runtime": {
            "launch_executable": "codex",
            "launch_args": [],
            "launch_home_selector": {
                "env_var": "CODEX_HOME",
                "value": str(tmp_path / "home"),
            },
            "cao": {
                "shadow": {
                    "completion_stability_seconds": "fast",
                }
            },
        },
        "credentials": {
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": ["OPENAI_API_KEY"],
            }
        },
    }

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
