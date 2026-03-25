"""Unit coverage for the Houmao-server agent API demo pack."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import houmao.demo.houmao_server_agent_api_demo_pack.cli as demo_cli
import houmao.demo.houmao_server_agent_api_demo_pack.commands as demo_commands
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.demo.houmao_server_agent_api_demo_pack.provisioning import (
    ArtifactRecorder,
    FixturePaths,
    LaneDefinition,
    SuiteConfig,
    _is_observable_post_request_progress,
    _lane_fixture_report,
    _resolve_selected_lanes,
    _start_suite_server,
    _state_signature,
)
from houmao.demo.houmao_server_agent_api_demo_pack.reporting import (
    build_report,
    sanitize_report,
)


def test_resolve_selected_lanes_defaults_to_all_supported_lanes() -> None:
    """The demo pack should target all four supported lanes by default."""

    lane_ids = [lane.lane_id for lane in _resolve_selected_lanes(())]

    assert lane_ids == [
        "claude-tui",
        "codex-tui",
        "claude-headless",
        "codex-headless",
    ]


def test_lane_fixture_report_requires_codex_api_key(tmp_path: Path) -> None:
    """Codex lanes should require API-key mode in the tracked credential fixture."""

    fixture_paths = _seed_pack_fixture_tree(
        tmp_path,
        tool="codex",
        config_profile="yunwu-openai",
        credential_profile="yunwu-openai",
        env_lines=["OPENAI_BASE_URL=https://x"],
    )

    report, env_names, _env_values, missing = _lane_fixture_report(
        fixtures=fixture_paths,
        lane=LaneDefinition(
            lane_id="codex-tui",
            slug="cdxtui",
            tool="codex",
            transport="tui",
            compatibility_provider="codex",
            config_profile="yunwu-openai",
            credential_profile="yunwu-openai",
        ),
    )

    assert report["config_profile"] == "yunwu-openai"
    assert report["credential_profile"] == "yunwu-openai"
    assert env_names == ["OPENAI_BASE_URL"]
    assert any("OPENAI_API_KEY" in item for item in missing)


def test_start_suite_server_uses_pack_owned_agent_def_dir_and_timeout_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Server startup should inject the pack-owned selector root and timeout controls."""

    fixture_paths = FixturePaths(
        repo_root=tmp_path,
        pack_dir=tmp_path / "scripts" / "demo" / "houmao-server-agent-api-demo-pack",
        agent_def_dir=tmp_path
        / "scripts"
        / "demo"
        / "houmao-server-agent-api-demo-pack"
        / "agents",
        compatibility_profile_path=None,
        dummy_project_fixture=tmp_path
        / "scripts"
        / "demo"
        / "houmao-server-agent-api-demo-pack"
        / "inputs"
        / "project-template",
    )
    for path in (
        fixture_paths.pack_dir,
        fixture_paths.agent_def_dir,
        fixture_paths.dummy_project_fixture,
    ):
        path.mkdir(parents=True, exist_ok=True)

    paths = _suite_paths(tmp_path / "run")
    recorded: dict[str, object] = {}

    class _FakeClient:
        def __init__(
            self,
            base_url: str,
            timeout_seconds: float,
            create_timeout_seconds: float,
        ) -> None:
            recorded["client_init"] = {
                "base_url": base_url,
                "timeout_seconds": timeout_seconds,
                "create_timeout_seconds": create_timeout_seconds,
            }

        def current_instance(self) -> _FakeModel:
            return _FakeModel({"api_base_url": "http://127.0.0.1:43111", "pid": 1234})

    class _FakeProcess:
        pid = 1234

    def _fake_popen(args: list[str], **kwargs: object) -> _FakeProcess:
        recorded["popen_args"] = args
        recorded["popen_kwargs"] = kwargs
        return _FakeProcess()

    monkeypatch.setattr(
        demo_commands,
        "HoumaoServerClient",
        demo_commands.HoumaoServerClient,
    )
    monkeypatch.setattr(
        "houmao.demo.houmao_server_agent_api_demo_pack.provisioning.HoumaoServerClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.demo.houmao_server_agent_api_demo_pack.provisioning.subprocess.Popen",
        _fake_popen,
    )
    monkeypatch.setattr(
        "houmao.demo.houmao_server_agent_api_demo_pack.provisioning._choose_port",
        lambda requested_port: 43111 if requested_port is None else requested_port,
    )
    monkeypatch.setattr(
        "houmao.demo.houmao_server_agent_api_demo_pack.provisioning._wait_for_server_health",
        lambda **kwargs: _FakeModel({"status": "ok", "houmao_service": "houmao-server"}),
    )

    server_info = _start_suite_server(
        config=SuiteConfig(
            port=None,
            compat_http_timeout_seconds=21.0,
            compat_create_timeout_seconds=91.0,
            compat_provider_ready_timeout_seconds=92.0,
        ),
        fixtures=fixture_paths,
        paths=paths,
        suite_http_recorder=ArtifactRecorder(paths.suite_http_dir),
        credential_env={"OPENAI_API_KEY": "secret"},
    )

    assert server_info["api_base_url"] == "http://127.0.0.1:43111"
    assert recorded["client_init"] == {
        "base_url": "http://127.0.0.1:43111",
        "timeout_seconds": 21.0,
        "create_timeout_seconds": 91.0,
    }
    assert "--compat-provider-ready-timeout-seconds" in recorded["popen_args"]
    flag_index = recorded["popen_args"].index("--compat-provider-ready-timeout-seconds")
    assert recorded["popen_args"][flag_index + 1] == "92.0"
    popen_env = recorded["popen_kwargs"]["env"]
    assert isinstance(popen_env, dict)
    assert popen_env[AGENT_DEF_DIR_ENV_VAR] == str(fixture_paths.agent_def_dir)


def test_observable_post_request_progress_accepts_tui_anchor_transition() -> None:
    """TUI prompt verification should accept the transient active-turn anchor."""

    state_before = _managed_agent_state_payload(
        phase="ready",
        active_turn_id=None,
        last_turn_result="none",
    )
    state_after = _managed_agent_state_payload(
        phase="active",
        active_turn_id="tui-anchor:cao-server-api-smoke",
        last_turn_result="none",
    )

    assert _is_observable_post_request_progress(
        state_before=state_before,
        latest_state=state_after,
        baseline_signature=_state_signature(state_before),
    )


def test_resolve_demo_output_dir_reuses_current_run_root_for_follow_up_commands(
    tmp_path: Path,
) -> None:
    """Follow-up commands should reuse the persisted current run root."""

    repo_root = tmp_path / "repo"
    pack_dir = repo_root / "scripts" / "demo" / "houmao-server-agent-api-demo-pack"
    pack_paths = demo_commands.resolve_pack_paths(repo_root=repo_root, pack_dir=pack_dir)
    current_run_root = pack_paths.runs_dir / "20260325-120000Z"
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
            "/tmp/demo-pack-run",
            "--lane",
            "claude-tui",
            "--history-limit",
            "7",
            "--with-dialog-tail",
            "300",
        ]
    )

    assert args.command == "inspect"
    assert args.demo_output_dir == Path("/tmp/demo-pack-run")
    assert args.lane == ["claude-tui"]
    assert args.history_limit == 7
    assert args.with_dialog_tail == 300


def test_build_report_matches_tracked_expected_report_contract(tmp_path: Path) -> None:
    """The tracked expected report should match the sanitized canonical contract."""

    expected_report_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "demo"
        / "houmao-server-agent-api-demo-pack"
        / "expected_report"
        / "report.json"
    )

    actual = _canonical_sanitized_report(tmp_path)
    expected = json.loads(expected_report_path.read_text(encoding="utf-8"))

    assert actual == expected


def test_autotest_harness_preflight_dispatches_and_writes_result(tmp_path: Path) -> None:
    """The pack-local autotest harness should dispatch the preflight case contract."""

    repo_root = Path(__file__).resolve().parents[3]
    pack_dir = (repo_root / "scripts" / "demo" / "houmao-server-agent-api-demo-pack").resolve()
    harness_path = (pack_dir / "autotest" / "run_autotest.sh").resolve()
    fake_bin_dir = (tmp_path / "fake-bin").resolve()
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    command_log_path = (tmp_path / "pixi-command.log").resolve()
    _write_fake_pixi(fake_bin_dir / "pixi", command_log_path)
    demo_output_dir = (tmp_path / "autotest-demo").resolve()

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"

    result = subprocess.run(
        [
            str(harness_path),
            "--case",
            "real-agent-preflight",
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
            demo_output_dir / "control" / "autotest" / "case-real-agent-preflight.result.json"
        ).read_text(encoding="utf-8")
    )
    preflight_payload = json.loads(
        (
            demo_output_dir / "control" / "autotest" / "case-real-agent-preflight.preflight.json"
        ).read_text(encoding="utf-8")
    )

    assert case_result["status"] == "passed"
    assert preflight_payload["ok"] is True
    assert (
        demo_output_dir / "logs" / "autotest" / "real-agent-preflight" / "01-preflight.command.txt"
    ).is_file()
    command_log = command_log_path.read_text(encoding="utf-8").splitlines()
    helper_script = str(pack_dir / "scripts" / "demo_pack_helpers.py")
    assert any(f"run python {helper_script} preflight" in line for line in command_log)
    assert any("run python -" in line for line in command_log)


def test_autotest_harness_rejects_unsupported_case(tmp_path: Path) -> None:
    """The harness should fail fast when the caller selects an unsupported case."""

    repo_root = Path(__file__).resolve().parents[3]
    harness_path = (
        repo_root
        / "scripts"
        / "demo"
        / "houmao-server-agent-api-demo-pack"
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


class _FakeModel:
    """Small pydantic-like helper used by startup test doubles."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.m_payload = payload
        for key, value in payload.items():
            setattr(self, key, value)

    def model_dump(self, *, mode: str) -> dict[str, object]:
        del mode
        return dict(self.m_payload)

    def model_dump_json(self) -> str:
        return "{}"


def _seed_pack_fixture_tree(
    tmp_path: Path,
    *,
    tool: str,
    config_profile: str,
    credential_profile: str,
    env_lines: list[str],
) -> FixturePaths:
    """Create the minimal pack-owned fixture tree required by `_lane_fixture_report`."""

    repo_root = tmp_path
    pack_dir = repo_root / "scripts" / "demo" / "houmao-server-agent-api-demo-pack"
    agent_def_dir = pack_dir / "agents"
    dummy_project_fixture = pack_dir / "inputs" / "project-template"

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
    dummy_project_fixture.mkdir(parents=True, exist_ok=True)

    (agent_def_dir / "roles" / "server-api-smoke" / "system-prompt.md").write_text(
        "# role\n",
        encoding="utf-8",
    )
    (agent_def_dir / "blueprints" / f"server-api-smoke-{tool}.yaml").write_text(
        "schema_version: 1\n",
        encoding="utf-8",
    )
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
        (agent_def_dir / "brains" / "api-creds" / "claude" / credential_profile / "files").mkdir(
            parents=True, exist_ok=True
        )
        (
            agent_def_dir
            / "brains"
            / "api-creds"
            / "claude"
            / credential_profile
            / "files"
            / "claude_state.template.json"
        ).write_text("{}\n", encoding="utf-8")
        (
            agent_def_dir / "brains" / "cli-configs" / "claude" / config_profile / "settings.json"
        ).write_text(
            '{"skipDangerousModePermissionPrompt": true}\n',
            encoding="utf-8",
        )
    else:
        (
            agent_def_dir / "brains" / "cli-configs" / "codex" / config_profile / "config.toml"
        ).write_text(
            '[model_providers.openai]\nname = "fixture"\n',
            encoding="utf-8",
        )

    return FixturePaths(
        repo_root=repo_root,
        pack_dir=pack_dir,
        agent_def_dir=agent_def_dir,
        compatibility_profile_path=None,
        dummy_project_fixture=dummy_project_fixture,
    )


def _suite_paths(run_root: Path):
    """Build one suite-path namespace for startup tests."""

    class _Paths:
        def __init__(self) -> None:
            self.run_root = run_root
            self.control_dir = run_root / "control"
            self.runtime_root = run_root / "runtime"
            self.registry_root = run_root / "registry"
            self.jobs_root = run_root / "jobs"
            self.home_dir = run_root / "home"
            self.logs_dir = run_root / "logs"
            self.server_logs_dir = run_root / "logs" / "server"
            self.server_runtime_root = run_root / "server-runtime"
            self.suite_http_dir = run_root / "http"
            self.server_dir = run_root / "server"
            self.lanes_root = run_root / "lanes"
            for path in (
                self.run_root,
                self.control_dir,
                self.runtime_root,
                self.registry_root,
                self.jobs_root,
                self.home_dir,
                self.logs_dir,
                self.server_logs_dir,
                self.server_runtime_root,
                self.suite_http_dir,
                self.server_dir,
                self.lanes_root,
            ):
                path.mkdir(parents=True, exist_ok=True)

    return _Paths()


def _managed_agent_state_payload(
    *,
    phase: str,
    active_turn_id: str | None,
    last_turn_result: str,
) -> _FakeModel:
    """Build one minimal managed-agent state payload for progress checks."""

    return _FakeModel(
        {
            "turn": _FakeModel(
                {
                    "phase": phase,
                    "active_turn_id": active_turn_id,
                }
            ),
            "last_turn": _FakeModel(
                {
                    "result": last_turn_result,
                    "turn_id": None,
                    "turn_index": None,
                    "updated_at_utc": None,
                }
            ),
        }
    )


def _canonical_sanitized_report(tmp_path: Path) -> dict[str, object]:
    """Build the canonical sanitized report used by the tracked expected snapshot."""

    tracked_ids = {
        "claude-tui": "tracked-claude-tui",
        "codex-tui": "tracked-codex-tui",
        "claude-headless": "tracked-claude-headless",
        "codex-headless": "tracked-codex-headless",
    }
    root = tmp_path.resolve()
    report_path = root / "report.json"
    state_payload = {
        "active": True,
        "repo_root": str(root / "repo"),
        "pack_dir": str(root / "repo" / "scripts" / "demo" / "houmao-server-agent-api-demo-pack"),
        "run_root": str(root / "run"),
        "selected_lane_ids": list(tracked_ids.keys()),
        "started_at_utc": "2026-03-25T12:00:00+00:00",
        "updated_at_utc": "2026-03-25T12:01:00+00:00",
        "steps": {
            "start_complete": True,
            "inspect_complete": True,
            "prompt_complete": True,
            "interrupt_complete": False,
            "verify_complete": True,
            "stop_complete": False,
        },
        "preflight": {
            "executables": {
                "tmux": "/usr/bin/tmux",
                "claude": "/usr/local/bin/claude",
                "codex": "/usr/local/bin/codex",
            },
            "credential_env_var_names": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "missing": [],
        },
        "server": {
            "api_base_url": "http://127.0.0.1:43111",
            "pid": 4242,
            "health": {"status": "ok"},
            "credential_env_var_names": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
        },
        "shared_routes": {
            "listed_agent_ids": list(tracked_ids.values()),
            "expected_agent_ids": list(tracked_ids.values()),
            "missing_agent_ids": [],
            "history_limit": 20,
        },
        "lanes": {
            "claude-tui": {
                "tool": "claude",
                "transport": "tui",
                "route_verification": {
                    "identity": {"tracked_agent_id": tracked_ids["claude-tui"]},
                    "detail": {"detail": {"transport": "tui"}},
                    "history": {"entries": []},
                },
                "prompt_verification": {
                    "prompt": (
                        "Reply with one short sentence confirming the live suite request for "
                        "lane claude-tui using tool claude over tui."
                    ),
                    "accepted": {
                        "disposition": "accepted",
                        "request_kind": "submit_prompt",
                        "request_id": "req-claude-tui",
                        "headless_turn_id": None,
                    },
                    "state_after": {"turn_phase": "active"},
                    "headless_turn": None,
                },
            },
            "codex-tui": {
                "tool": "codex",
                "transport": "tui",
                "route_verification": {
                    "identity": {"tracked_agent_id": tracked_ids["codex-tui"]},
                    "detail": {"detail": {"transport": "tui"}},
                    "history": {"entries": []},
                },
                "prompt_verification": {
                    "prompt": (
                        "Reply with one short sentence confirming the live suite request for "
                        "lane codex-tui using tool codex over tui."
                    ),
                    "accepted": {
                        "disposition": "accepted",
                        "request_kind": "submit_prompt",
                        "request_id": "req-codex-tui",
                        "headless_turn_id": None,
                    },
                    "state_after": {"turn_phase": "active"},
                    "headless_turn": None,
                },
            },
            "claude-headless": {
                "tool": "claude",
                "transport": "headless",
                "route_verification": {
                    "identity": {"tracked_agent_id": tracked_ids["claude-headless"]},
                    "detail": {"detail": {"transport": "headless"}},
                    "history": {"entries": []},
                },
                "prompt_verification": {
                    "prompt": (
                        "Reply with one short sentence confirming the live suite request for "
                        "lane claude-headless using tool claude over headless."
                    ),
                    "accepted": {
                        "disposition": "accepted",
                        "request_kind": "submit_prompt",
                        "request_id": "req-claude-headless",
                        "headless_turn_id": "turn-claude-headless",
                    },
                    "state_after": {"turn_phase": "ready"},
                    "headless_turn": {"status": {"status": "completed"}},
                },
            },
            "codex-headless": {
                "tool": "codex",
                "transport": "headless",
                "route_verification": {
                    "identity": {"tracked_agent_id": tracked_ids["codex-headless"]},
                    "detail": {"detail": {"transport": "headless"}},
                    "history": {"entries": []},
                },
                "prompt_verification": {
                    "prompt": (
                        "Reply with one short sentence confirming the live suite request for "
                        "lane codex-headless using tool codex over headless."
                    ),
                    "accepted": {
                        "disposition": "accepted",
                        "request_kind": "submit_prompt",
                        "request_id": "req-codex-headless",
                        "headless_turn_id": "turn-codex-headless",
                    },
                    "state_after": {"turn_phase": "ready"},
                    "headless_turn": {"status": {"status": "completed"}},
                },
            },
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
                '  printf \'{"ok": true, "mode": "fake-preflight"}\\n\'',
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
