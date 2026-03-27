"""Unit coverage for the passive-server parallel validation demo pack."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import houmao.demo.passive_server_parallel_validation_demo_pack.cli as demo_cli
import houmao.demo.passive_server_parallel_validation_demo_pack.commands as demo_commands
from houmao.demo.passive_server_parallel_validation_demo_pack.provisioning import (
    FixturePaths,
    ProviderFixture,
    _provider_fixture_report,
)
from houmao.demo.passive_server_parallel_validation_demo_pack.reporting import (
    build_report,
    sanitize_report,
)


def test_provider_fixture_report_requires_codex_api_key(tmp_path: Path) -> None:
    """Codex validation should require API-key mode in the tracked credential fixture."""

    fixture_paths = _seed_pack_fixture_tree(
        tmp_path,
        tool="codex",
        config_profile="yunwu-openai",
        credential_profile="yunwu-openai",
        env_lines=["OPENAI_BASE_URL=https://example.invalid"],
    )

    report, env_values, missing = _provider_fixture_report(
        fixtures=fixture_paths,
        fixture=ProviderFixture(
            provider="codex",
            tool="codex",
            config_profile="yunwu-openai",
            credential_profile="yunwu-openai",
            blueprint_name="server-api-smoke-codex.yaml",
        ),
    )

    assert report["config_profile"] == "yunwu-openai"
    assert report["credential_profile"] == "yunwu-openai"
    assert sorted(env_values) == ["OPENAI_BASE_URL"]
    assert any("OPENAI_API_KEY" in item for item in missing)


def test_resolve_demo_output_dir_reuses_current_run_root_for_follow_up_commands(
    tmp_path: Path,
) -> None:
    """Follow-up commands should reuse the persisted current run root."""

    repo_root = tmp_path / "repo"
    pack_dir = repo_root / "scripts" / "demo" / "passive-server-parallel-validation-demo-pack"
    pack_paths = demo_commands.resolve_pack_paths(repo_root=repo_root, pack_dir=pack_dir)
    current_run_root = pack_paths.runs_dir / "20260326T120000Z"
    current_run_root.mkdir(parents=True, exist_ok=True)
    pack_paths.current_run_root_path.parent.mkdir(parents=True, exist_ok=True)
    pack_paths.current_run_root_path.write_text(str(current_run_root) + "\n", encoding="utf-8")

    resolved = demo_commands.resolve_demo_output_dir(
        command_name="inspect",
        pack_paths=pack_paths,
        raw_demo_output_dir=None,
    )

    assert resolved == current_run_root.resolve()


def test_cli_parser_accepts_common_flags_after_subcommand() -> None:
    """Common options should remain valid after the selected subcommand."""

    args = demo_cli.build_parser().parse_args(
        [
            "inspect",
            "--demo-output-dir",
            "/tmp/passive-server-parallel-run",
            "--provider",
            "codex",
            "--history-limit",
            "7",
        ]
    )

    assert args.command == "inspect"
    assert args.demo_output_dir == Path("/tmp/passive-server-parallel-run")
    assert args.provider == "codex"
    assert args.history_limit == 7


def test_build_report_matches_tracked_expected_report_contract(tmp_path: Path) -> None:
    """The tracked expected report should match the sanitized canonical contract."""

    expected_report_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "demo"
        / "passive-server-parallel-validation-demo-pack"
        / "expected_report"
        / "report.json"
    )

    actual = _canonical_sanitized_report(tmp_path)
    expected = json.loads(expected_report_path.read_text(encoding="utf-8"))

    assert actual == expected


def test_autotest_harness_preflight_dispatches_and_writes_result(tmp_path: Path) -> None:
    """The pack-local autotest harness should dispatch the preflight case contract."""

    repo_root = Path(__file__).resolve().parents[3]
    pack_dir = (repo_root / "scripts" / "demo" / "passive-server-parallel-validation-demo-pack").resolve()
    harness_path = (pack_dir / "autotest" / "run_autotest.sh").resolve()
    fake_bin_dir = (tmp_path / "fake-bin").resolve()
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    command_log_path = (tmp_path / "pixi-command.log").resolve()
    _write_fake_pixi(fake_bin_dir / "pixi", command_log_path)
    demo_output_dir = (tmp_path / "autotest-preflight").resolve()

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"

    result = subprocess.run(
        [
            str(harness_path),
            "--case",
            "parallel-preflight",
            "--demo-output-dir",
            str(demo_output_dir),
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    case_result = json.loads(
        (
            demo_output_dir / "control" / "autotest" / "case-parallel-preflight.result.json"
        ).read_text(encoding="utf-8")
    )
    preflight_payload = json.loads(
        (
            demo_output_dir / "control" / "autotest" / "case-parallel-preflight.preflight.json"
        ).read_text(encoding="utf-8")
    )

    assert case_result["status"] == "passed"
    assert preflight_payload["mode"] == "fake-preflight"
    assert (
        demo_output_dir / "logs" / "autotest" / "parallel-preflight" / "01-preflight.command.txt"
    ).is_file()
    command_log = command_log_path.read_text(encoding="utf-8").splitlines()
    helper_script = str(pack_dir / "scripts" / "demo_pack_helpers.py")
    assert any(f"run python {helper_script} preflight" in line for line in command_log)
    assert any("run python -" in line for line in command_log)


def test_autotest_harness_auto_dispatches_and_writes_result(tmp_path: Path) -> None:
    """The pack-local autotest harness should dispatch the full auto case contract."""

    repo_root = Path(__file__).resolve().parents[3]
    pack_dir = (repo_root / "scripts" / "demo" / "passive-server-parallel-validation-demo-pack").resolve()
    harness_path = (pack_dir / "autotest" / "run_autotest.sh").resolve()
    fake_bin_dir = (tmp_path / "fake-bin").resolve()
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    command_log_path = (tmp_path / "pixi-command.log").resolve()
    _write_fake_pixi(fake_bin_dir / "pixi", command_log_path)
    demo_output_dir = (tmp_path / "autotest-auto").resolve()

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"

    result = subprocess.run(
        [
            str(harness_path),
            "--case",
            "parallel-all-phases-auto",
            "--demo-output-dir",
            str(demo_output_dir),
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    case_result = json.loads(
        (
            demo_output_dir / "control" / "autotest" / "case-parallel-all-phases-auto.result.json"
        ).read_text(encoding="utf-8")
    )
    stdout_path = (
        demo_output_dir / "logs" / "autotest" / "parallel-all-phases-auto" / "01-auto.stdout.txt"
    )

    assert case_result["status"] == "passed"
    assert case_result["artifact_refs"]["report_path"] == str((demo_output_dir / "report.json").resolve())
    assert json.loads(stdout_path.read_text(encoding="utf-8"))["mode"] == "fake-auto"
    command_log = command_log_path.read_text(encoding="utf-8").splitlines()
    helper_script = str(pack_dir / "scripts" / "demo_pack_helpers.py")
    assert any(f"run python {helper_script} auto" in line for line in command_log)


def test_autotest_harness_rejects_unsupported_case(tmp_path: Path) -> None:
    """The harness should fail fast when the caller selects an unsupported case."""

    repo_root = Path(__file__).resolve().parents[3]
    harness_path = (
        repo_root
        / "scripts"
        / "demo"
        / "passive-server-parallel-validation-demo-pack"
        / "autotest"
        / "run_autotest.sh"
    ).resolve()

    result = subprocess.run(
        [
            str(harness_path),
            "--case",
            "not-a-real-case",
            "--demo-output-dir",
            str(tmp_path / "demo-output"),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "unsupported case: not-a-real-case" in result.stderr


def _seed_pack_fixture_tree(
    tmp_path: Path,
    *,
    tool: str,
    config_profile: str,
    credential_profile: str,
    env_lines: list[str],
) -> FixturePaths:
    """Create the minimal pack-owned fixture tree required by `_provider_fixture_report`."""

    repo_root = tmp_path
    pack_dir = repo_root / "scripts" / "demo" / "passive-server-parallel-validation-demo-pack"
    agent_def_dir = pack_dir / "agents"
    project_template_dir = pack_dir / "inputs" / "project-template"
    shared_prompt_path = pack_dir / "inputs" / "shared_prompt.txt"
    gateway_prompt_path = pack_dir / "inputs" / "gateway_prompt.txt"
    headless_prompt_path = pack_dir / "inputs" / "headless_prompt.txt"

    (agent_def_dir / "roles" / "server-api-smoke").mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "blueprints").mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "brains" / "brain-recipes" / tool).mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "brains" / "api-creds" / tool / credential_profile / "env").mkdir(
        parents=True,
        exist_ok=True,
    )
    (agent_def_dir / "brains" / "cli-configs" / tool / config_profile).mkdir(
        parents=True,
        exist_ok=True,
    )
    project_template_dir.mkdir(parents=True, exist_ok=True)
    shared_prompt_path.parent.mkdir(parents=True, exist_ok=True)

    (agent_def_dir / "roles" / "server-api-smoke" / "system-prompt.md").write_text(
        "# role\n",
        encoding="utf-8",
    )
    (
        agent_def_dir
        / "blueprints"
        / ("server-api-smoke-claude.yaml" if tool == "claude" else "server-api-smoke-codex.yaml")
    ).write_text("schema_version: 1\n", encoding="utf-8")
    (
        agent_def_dir / "brains" / "brain-recipes" / tool / "server-api-smoke-default.yaml"
    ).write_text(
        (
            "schema_version: 1\n"
            "name: server-api-smoke-default\n"
            f"tool: {tool}\n"
            "skills: []\n"
            f"config_profile: {config_profile}\n"
            f"credential_profile: {credential_profile}\n"
            "launch_policy:\n"
            "  operator_prompt_mode: unattended\n"
        ),
        encoding="utf-8",
    )
    (
        agent_def_dir / "brains" / "api-creds" / tool / credential_profile / "env" / "vars.env"
    ).write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    if tool == "claude":
        (
            agent_def_dir / "brains" / "cli-configs" / "claude" / config_profile / "settings.json"
        ).write_text('{"skipDangerousModePermissionPrompt": true}\n', encoding="utf-8")
    else:
        (
            agent_def_dir / "brains" / "cli-configs" / "codex" / config_profile / "config.toml"
        ).write_text('[model_providers.openai]\nname = "fixture"\n', encoding="utf-8")

    project_template_dir.joinpath("README.txt").write_text("fixture\n", encoding="utf-8")
    shared_prompt_path.write_text("shared prompt\n", encoding="utf-8")
    gateway_prompt_path.write_text("gateway prompt\n", encoding="utf-8")
    headless_prompt_path.write_text("headless prompt\n", encoding="utf-8")

    return FixturePaths(
        repo_root=repo_root,
        pack_dir=pack_dir,
        agent_def_dir=agent_def_dir,
        project_template_dir=project_template_dir,
        shared_prompt_path=shared_prompt_path,
        gateway_prompt_path=gateway_prompt_path,
        headless_prompt_path=headless_prompt_path,
    )


def _canonical_sanitized_report(tmp_path: Path) -> dict[str, object]:
    """Build the canonical sanitized report used by the tracked expected snapshot."""

    root = tmp_path.resolve()
    report_path = root / "report.json"
    state_payload = {
        "active": False,
        "repo_root": str(root / "repo"),
        "pack_dir": str(root / "repo" / "scripts" / "demo" / "passive-server-parallel-validation-demo-pack"),
        "run_root": str(root / "run"),
        "provider": "claude_code",
        "tool": "claude",
        "agent_profile": "server-api-smoke",
        "steps": {
            "start": True,
            "inspect": True,
            "gateway": True,
            "headless": True,
            "stop": True,
            "verify": True,
        },
        "preflight": {
            "executables": {
                "pixi": "/usr/bin/pixi",
                "git": "/usr/bin/git",
                "tmux": "/usr/bin/tmux",
                "claude": "/usr/local/bin/claude",
            },
            "missing": [],
        },
        "config": {
            "ports": {
                "old_server": 9889,
                "passive_server": 9891,
            }
        },
        "authorities": {
            "old_server": {
                "api_base_url": "http://127.0.0.1:9889",
                "houmao_service": "houmao-server",
                "pid": 4242,
                "health": {"status": "ok"},
            },
            "passive_server": {
                "api_base_url": "http://127.0.0.1:9891",
                "houmao_service": "houmao-passive-server",
                "pid": 4343,
                "health": {"status": "ok"},
            },
        },
        "shared_agent": {
            "agent_id": "published-shared",
            "agent_name": "AGENTSYS-shared",
            "tmux_session_name": "AGENTSYS-shared",
            "manifest_path": str(root / "run" / "runtime" / "shared" / "manifest.json"),
        },
        "headless_agent": {
            "agent_id": "published-headless",
            "agent_name": "AGENTSYS-headless",
            "manifest_path": str(root / "run" / "runtime" / "headless" / "manifest.json"),
        },
        "inspect_result": {
            "ok": True,
            "list_ok": True,
            "resolve_ok": True,
            "comparison_summary": {
                "identity": True,
                "state": True,
                "detail": True,
                "history": True,
            },
            "old_history_normalized": {
                "entry_count": 1,
                "latest_turn_phase": "ready",
                "latest_last_turn_result": "success",
                "latest_summary": "shared prompt handled",
            },
            "passive_history_normalized": {
                "entry_count": 1,
                "latest_turn_phase": "ready",
                "latest_last_turn_result": "success",
                "latest_summary": "shared prompt handled",
            },
        },
        "gateway_result": {
            "ok": True,
            "gateway_attached": True,
            "accepted": {"request_id": "request-0001"},
            "old_progress_observed": True,
            "passive_progress_observed": True,
        },
        "headless_result": {
            "ok": True,
            "launch_ok": True,
            "old_visibility_ok": True,
        },
        "stop_result": {
            "ok": True,
            "passive_absent": True,
            "old_absent": True,
            "registry_absent": True,
            "tmux_absent": True,
        },
    }
    raw_report = build_report(state_payload=state_payload, report_path=report_path)
    return sanitize_report(raw_report)


def _write_fake_pixi(path: Path, command_log_path: Path) -> None:
    """Write one fake pixi wrapper for autotest harness dispatch tests."""

    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf '%s\\n' \"$*\" >> {command_log_path}",
                'if [[ "${1:-}" == "run" && "${2:-}" == "python" && "${3:-}" == "-" ]]; then',
                "  shift 2",
                f'  exec {sys.executable} "$@"',
                "fi",
                'if [[ "${1:-}" == "run" && "${2:-}" == "python" && "${3:-}" == *"/scripts/demo_pack_helpers.py" && "${4:-}" == "preflight" ]]; then',
                '  printf \'{"status": "ok", "mode": "fake-preflight"}\\n\'',
                "  exit 0",
                "fi",
                'if [[ "${1:-}" == "run" && "${2:-}" == "python" && "${3:-}" == *"/scripts/demo_pack_helpers.py" && "${4:-}" == "auto" ]]; then',
                '  printf \'{"status": "ok", "mode": "fake-auto"}\\n\'',
                "  exit 0",
                "fi",
                'if [[ "${1:-}" == "run" && "${2:-}" == "python" && "${3:-}" == *"/scripts/demo_pack_helpers.py" && "${4:-}" == "stop" ]]; then',
                '  printf \'{"status": "ok", "mode": "fake-stop"}\\n\'',
                "  exit 0",
                "fi",
                'echo "unsupported fake pixi invocation: $*" >&2',
                "exit 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
