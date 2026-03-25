"""Unit coverage for the manual houmao-server API live suite helpers."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

_MANUAL_ROOT = Path(__file__).resolve().parents[2] / "manual"
if str(_MANUAL_ROOT) not in sys.path:
    sys.path.insert(0, str(_MANUAL_ROOT))

from houmao_server_agent_api_live_suite.suite import (  # noqa: E402
    ArtifactRecorder,
    FixturePaths,
    LaneDefinition,
    SuiteConfig,
    _is_observable_post_request_progress,
    _lane_fixture_report,
    _resolve_selected_lanes,
    _state_signature,
    _start_suite_server,
)


def test_resolve_selected_lanes_defaults_to_all_supported_lanes() -> None:
    """The live suite should run all four lanes when none are selected."""

    lane_ids = [lane.lane_id for lane in _resolve_selected_lanes(())]

    assert lane_ids == [
        "claude-tui",
        "codex-tui",
        "claude-headless",
        "codex-headless",
    ]


def test_lane_fixture_report_requires_codex_api_key(tmp_path: Path) -> None:
    """Codex lanes should require API-key mode in the tracked credential fixture."""

    fixture_paths = _seed_fixture_tree(
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


def test_start_suite_server_uses_configurable_timeout_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Server startup should forward the new compatibility timeout control."""

    fixture_paths = FixturePaths(
        repo_root=tmp_path,
        agent_def_dir=tmp_path / "tests" / "fixtures" / "agents",
        compatibility_profile_path=tmp_path / "tests" / "fixtures" / "agents" / "profile.md",
        dummy_project_fixture=tmp_path / "tests" / "fixtures" / "dummy-project",
    )
    for path in (
        fixture_paths.agent_def_dir,
        fixture_paths.compatibility_profile_path.parent,
        fixture_paths.dummy_project_fixture,
    ):
        path.mkdir(parents=True, exist_ok=True)
    fixture_paths.compatibility_profile_path.write_text("# profile\n", encoding="utf-8")

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

        def health_extended(self):
            return _FakeModel({"status": "ok", "houmao_service": "houmao-server"})

        def current_instance(self):
            return _FakeModel({"api_base_url": "http://127.0.0.1:43111", "pid": 1234})

    class _FakeProcess:
        pid = 1234

    def _fake_popen(args: list[str], **kwargs: object) -> _FakeProcess:
        recorded["popen_args"] = args
        recorded["popen_kwargs"] = kwargs
        return _FakeProcess()

    monkeypatch.setattr(
        "houmao_server_agent_api_live_suite.suite.HoumaoServerClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao_server_agent_api_live_suite.suite.subprocess.Popen",
        _fake_popen,
    )
    monkeypatch.setattr(
        "houmao_server_agent_api_live_suite.suite._choose_port",
        lambda requested_port: 43111 if requested_port is None else requested_port,
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


class _FakeModel:
    """Small pydantic-like helper used by the startup test doubles."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.m_payload = payload
        for key, value in payload.items():
            setattr(self, key, value)

    def model_dump(self, *, mode: str) -> dict[str, object]:
        del mode
        return dict(self.m_payload)

    def model_dump_json(self) -> str:
        return "{}"


def _seed_fixture_tree(
    tmp_path: Path,
    *,
    tool: str,
    config_profile: str,
    credential_profile: str,
    env_lines: list[str],
) -> FixturePaths:
    """Create the minimal fixture tree required by `_lane_fixture_report`."""

    repo_root = tmp_path
    agent_def_dir = repo_root / "tests" / "fixtures" / "agents"
    compatibility_profile_path = agent_def_dir / "compatibility-profiles" / "server-api-smoke.md"
    dummy_project_fixture = (
        repo_root / "tests" / "fixtures" / "dummy-projects" / "mailbox-demo-python"
    )

    (agent_def_dir / "compatibility-profiles").mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "roles" / "server-api-smoke").mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "blueprints").mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "brains" / "brain-recipes" / tool).mkdir(parents=True, exist_ok=True)
    (agent_def_dir / "brains" / "api-creds" / tool / credential_profile / "env").mkdir(
        parents=True, exist_ok=True
    )
    (agent_def_dir / "brains" / "cli-configs" / tool / config_profile).mkdir(
        parents=True, exist_ok=True
    )
    dummy_project_fixture.mkdir(parents=True, exist_ok=True)

    compatibility_profile_path.write_text("# server-api-smoke\n", encoding="utf-8")
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
        (agent_def_dir / "brains" / "cli-configs" / "claude" / config_profile / "settings.json").write_text(
            '{"skipDangerousModePermissionPrompt": true}\n',
            encoding="utf-8",
        )
    else:
        (agent_def_dir / "brains" / "cli-configs" / "codex" / config_profile / "config.toml").write_text(
            "[model_providers.openai]\nname = \"fixture\"\n",
            encoding="utf-8",
        )

    return FixturePaths(
        repo_root=repo_root,
        agent_def_dir=agent_def_dir,
        compatibility_profile_path=compatibility_profile_path,
        dummy_project_fixture=dummy_project_fixture,
    )


def _suite_paths(run_root: Path):
    """Build one suite-path namespace for the startup test."""

    class _Paths:
        def __init__(self) -> None:
            self.run_root = run_root
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
):
    """Build a minimal managed-agent state payload for helper tests."""

    from houmao.server.models import HoumaoManagedAgentStateResponse

    return HoumaoManagedAgentStateResponse.model_validate(
        {
            "tracked_agent_id": "cao-server-api-smoke",
            "identity": {
                "tracked_agent_id": "cao-server-api-smoke",
                "transport": "tui",
                "tool": "claude",
                "session_name": "cao-server-api-smoke",
                "terminal_id": "abcd1234",
                "runtime_session_id": None,
                "tmux_session_name": "cao-server-api-smoke",
                "tmux_window_name": "server-api-smoke-1",
                "manifest_path": "/tmp/manifest.json",
                "session_root": "/tmp/session-root",
                "agent_name": "AGENTSYS-cao-server-api-smoke",
                "agent_id": "agent-1234",
            },
            "availability": "available",
            "turn": {"phase": phase, "active_turn_id": active_turn_id},
            "last_turn": {
                "result": last_turn_result,
                "turn_id": None,
                "turn_index": None,
                "updated_at_utc": None,
            },
            "diagnostics": [],
            "mailbox": None,
            "gateway": None,
        }
    )
