from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.demo.shared_tui_tracking_demo_pack import live_watch, recorded
from houmao.demo.shared_tui_tracking_demo_pack.config import (
    DemoEvidenceConfig,
    DemoPathsConfig,
    DemoPresentationConfig,
    DemoReviewVideoConfig,
    DemoSemanticsConfig,
    DemoToolConfig,
    ResolvedDemoConfig,
)
from houmao.demo.shared_tui_tracking_demo_pack.models import RecordedFixtureManifest
from houmao.demo.shared_tui_tracking_demo_pack.scenario import (
    ScenarioDefinition,
    ScenarioLaunchSpec,
)


_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_DEMO_INPUTS_SOURCE = _WORKSPACE_ROOT / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents"
_FIXTURE_AUTH_RELATIVE_BY_TOOL = {
    "claude": Path("tests/fixtures/agents/tools/claude/auth/kimi-coding"),
    "codex": Path("tests/fixtures/agents/tools/codex/auth/yunwu-openai"),
}


def _seed_demo_repo(repo_root: Path) -> None:
    destination = repo_root / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_DEMO_INPUTS_SOURCE, destination)


def _seed_fixture_auth_bundle(repo_root: Path, *, tool: str) -> None:
    fixture_root = repo_root / _FIXTURE_AUTH_RELATIVE_BY_TOOL[tool]
    env_dir = fixture_root / "env"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_path = env_dir / "vars.env"
    if tool == "claude":
        env_path.write_text("ANTHROPIC_API_KEY=test-key\n", encoding="utf-8")
    else:
        env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")


def _build_demo_config(repo_root: Path) -> ResolvedDemoConfig:
    return ResolvedDemoConfig(
        schema_version=1,
        demo_id="shared-tui-tracking-demo-pack",
        repo_root=str(repo_root),
        source_config_path=str(
            repo_root / "scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml"
        ),
        selected_profile=None,
        selected_scenario_id=None,
        tools={
            "claude": DemoToolConfig(
                recipe_path=(
                    "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/presets/"
                    "interactive-watch-claude-default.yaml"
                ),
                launch_overrides=None,
                operator_prompt_mode="unattended",
            ),
            "codex": DemoToolConfig(
                recipe_path=(
                    "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/presets/"
                    "interactive-watch-codex-default.yaml"
                ),
                launch_overrides=None,
                operator_prompt_mode="unattended",
            ),
        },
        paths=DemoPathsConfig(
            fixtures_root="tests/fixtures/shared_tui_tracking/recorded",
            recorded_root="tmp/demo/shared-tui-tracking-demo-pack/recorded",
            live_root="tmp/demo/shared-tui-tracking-demo-pack/live",
            sweeps_root="tmp/demo/shared-tui-tracking-demo-pack/sweeps",
        ),
        evidence=DemoEvidenceConfig(
            sample_interval_seconds=0.2,
            runtime_observer_interval_seconds=0.2,
            ready_timeout_seconds=45.0,
            cleanup_session=True,
            live_watch_recorder_enabled=False,
        ),
        semantics=DemoSemanticsConfig(settle_seconds=1.0),
        presentation=DemoPresentationConfig(
            review_video=DemoReviewVideoConfig(
                width=1920,
                height=1080,
                match_capture_cadence=True,
                fps=None,
                codec="libx264",
                pixel_format="yuv420p",
                keep_frames=True,
            )
        ),
        sweeps={},
    )


def test_start_live_watch_builds_from_generated_demo_local_agent_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_demo_repo(repo_root)
    _seed_fixture_auth_bundle(repo_root, tool="claude")
    demo_config = _build_demo_config(repo_root)
    run_root = tmp_path / "live-run"
    build_requests: list[object] = []

    def fake_build_brain_home(request: object) -> SimpleNamespace:
        build_requests.append(request)
        return SimpleNamespace(
            home_path=run_root / "runtime/brain-home",
            manifest_path=run_root / "runtime/brain-manifest.json",
            launch_helper_path=run_root / "runtime/launch.sh",
        )

    monkeypatch.setattr(live_watch, "ensure_tmux_available", lambda: None)
    monkeypatch.setattr(live_watch, "initialize_demo_session_ownership", lambda **_: None)
    monkeypatch.setattr(live_watch, "build_brain_home", fake_build_brain_home)
    monkeypatch.setattr(live_watch, "detect_tool_version", lambda **_: "claude 1.0.0")
    monkeypatch.setattr(live_watch, "launch_tmux_session", lambda **_: None)
    monkeypatch.setattr(live_watch, "upsert_demo_owned_resource", lambda **_: None)
    monkeypatch.setattr(live_watch, "publish_demo_session_recovery_pointers", lambda **_: None)
    monkeypatch.setattr(live_watch, "resolve_active_pane_id", lambda **_: "%1")
    monkeypatch.setattr(live_watch, "_wait_for_dashboard_running", lambda **_: None)
    monkeypatch.setattr(live_watch, "set_demo_session_ownership_status", lambda **_: None)

    result = live_watch.start_live_watch(
        repo_root=repo_root,
        demo_config=demo_config,
        tool="claude",
        output_root=run_root,
        recipe_path=None,
        sample_interval_seconds=0.2,
        runtime_observer_interval_seconds=0.2,
        settle_seconds=1.0,
        trace_enabled=False,
    )

    assert result.run_root == run_root.resolve()
    assert len(build_requests) == 1
    build_request = build_requests[0]
    generated_agent_def_dir = (run_root / "workdir/.houmao/agents").resolve()
    assert build_request.agent_def_dir == generated_agent_def_dir
    assert (
        build_request.recipe_path
        == (
            repo_root
            / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/presets/interactive-watch-claude-default.yaml"
        ).resolve()
    )
    assert (generated_agent_def_dir / "tools/claude/auth/default").is_symlink()


def test_run_recorded_capture_builds_from_generated_demo_local_agent_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_demo_repo(repo_root)
    _seed_fixture_auth_bundle(repo_root, tool="codex")
    demo_config = _build_demo_config(repo_root)
    run_root = tmp_path / "recorded-run"
    build_requests: list[object] = []

    def fake_build_brain_home(request: object) -> SimpleNamespace:
        build_requests.append(request)
        return SimpleNamespace(
            home_path=run_root / "runtime/brain-home",
            manifest_path=run_root / "runtime/brain-manifest.json",
            launch_helper_path=run_root / "runtime/launch.sh",
        )

    class _Observer:
        def __init__(self, **_: object) -> None:
            pass

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

    monkeypatch.setattr(recorded, "ensure_tmux_available", lambda: None)
    monkeypatch.setattr(recorded, "initialize_demo_session_ownership", lambda **_: None)
    monkeypatch.setattr(recorded, "build_brain_home", fake_build_brain_home)
    monkeypatch.setattr(recorded, "detect_tool_version", lambda **_: "codex 1.0.0")
    monkeypatch.setattr(recorded, "launch_tmux_session", lambda **_: None)
    monkeypatch.setattr(recorded, "upsert_demo_owned_resource", lambda **_: None)
    monkeypatch.setattr(recorded, "publish_demo_session_recovery_pointers", lambda **_: None)
    monkeypatch.setattr(recorded, "set_demo_session_recorder_run_root", lambda **_: None)
    monkeypatch.setattr(recorded, "resolve_active_pane_id", lambda **_: "%1")
    monkeypatch.setattr(recorded, "start_terminal_record", lambda **_: {"mode": "active"})
    monkeypatch.setattr(
        recorded,
        "load_manifest",
        lambda _path: SimpleNamespace(
            started_at_utc=datetime.now(UTC).isoformat(),
            recorder_session_name="recorder-session",
            sample_interval_seconds=0.2,
        ),
    )
    monkeypatch.setattr(recorded, "RuntimeObserver", _Observer)
    monkeypatch.setattr(recorded, "_execute_scenario", lambda **_: None)
    monkeypatch.setattr(recorded, "set_demo_session_ownership_status", lambda **_: None)
    monkeypatch.setattr(recorded, "resolve_demo_owned_resources", lambda **_: object())
    monkeypatch.setattr(recorded, "reap_demo_owned_resources", lambda **_: None)

    scenario = ScenarioDefinition(
        scenario_id="codex-explicit-success",
        tool="codex",
        description="Synthetic recorded capture test",
        launch=ScenarioLaunchSpec(),
        steps=(),
    )
    result = recorded.run_recorded_capture(
        repo_root=repo_root,
        scenario=scenario,
        demo_config=demo_config,
        output_root=run_root,
        cleanup_session=False,
    )

    assert result.run_root == run_root.resolve()
    assert len(build_requests) == 1
    build_request = build_requests[0]
    generated_agent_def_dir = (run_root / "workdir/.houmao/agents").resolve()
    assert build_request.agent_def_dir == generated_agent_def_dir
    assert (
        build_request.recipe_path
        == (
            repo_root
            / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/presets/interactive-watch-codex-default.yaml"
        ).resolve()
    )
    assert (generated_agent_def_dir / "tools/codex/auth/default").is_symlink()


def test_validate_recorded_fixture_persists_validation_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_root = tmp_path / "fixture-root"
    recording_root = fixture_root / "recording"
    recording_root.mkdir(parents=True)
    fixture_manifest = RecordedFixtureManifest(
        schema_version=1,
        case_id="claude-explicit-success",
        tool="claude",
        observed_version="claude 1.0.0",
        settle_seconds=1.0,
        description="Synthetic validation fixture",
    )
    (fixture_root / "fixture_manifest.json").write_text(
        json.dumps(fixture_manifest.to_payload(), indent=2) + "\n",
        encoding="utf-8",
    )

    class _TimelineRow:
        def __init__(self, sample_id: str) -> None:
            self.m_sample_id = sample_id

        def to_payload(self) -> dict[str, object]:
            return {"sample_id": self.m_sample_id}

    class _Comparison:
        def to_payload(self) -> dict[str, object]:
            return {"mismatches": 0}

    monkeypatch.setattr(
        recorded,
        "_load_recorder_manifest",
        lambda _path: SimpleNamespace(sample_interval_seconds=0.2),
    )
    monkeypatch.setattr(
        recorded,
        "load_fixture_inputs",
        lambda **_: SimpleNamespace(observations=[], snapshots=[]),
    )
    monkeypatch.setattr(
        recorded,
        "expand_labels_to_groundtruth_timeline",
        lambda **_: [_TimelineRow("groundtruth-sample")],
    )
    monkeypatch.setattr(recorded, "load_input_events", lambda _path: [])
    monkeypatch.setattr(
        recorded,
        "replay_timeline",
        lambda **_: ([_TimelineRow("replay-sample")], []),
    )
    monkeypatch.setattr(
        recorded,
        "compare_timelines",
        lambda **_: (_Comparison(), "comparison markdown\n"),
    )
    monkeypatch.setattr(recorded, "build_recorded_run_issues", lambda **_: [])
    monkeypatch.setattr(recorded, "write_issue_documents", lambda **_: [])
    monkeypatch.setattr(recorded, "build_recorded_summary_report", lambda **_: "summary report\n")

    result = recorded.validate_recorded_fixture(
        repo_root=tmp_path,
        demo_config=_build_demo_config(tmp_path),
        fixture_root=fixture_root,
        output_root=tmp_path / "validation-run",
        render_review_video=False,
    )

    assert result.run_root == (tmp_path / "validation-run").resolve()
    assert (result.run_root / "artifacts/recorded_validation_manifest.json").is_file()
    assert (result.run_root / "analysis/groundtruth_timeline.ndjson").is_file()
    assert (result.run_root / "analysis/replay_timeline.ndjson").is_file()
    assert (result.run_root / "analysis/comparison.json").is_file()
    assert (result.run_root / "analysis/summary_report.md").is_file()


@pytest.mark.parametrize(
    ("prepare_root", "message"),
    [
        (lambda path: None, "Committed recorded fixture root is missing"),
        (
            lambda path: path.mkdir(parents=True, exist_ok=True),
            "Committed recorded fixture root is empty",
        ),
    ],
)
def test_validate_fixture_corpus_preflights_missing_or_empty_committed_root(
    tmp_path: Path,
    prepare_root,
    message: str,
) -> None:
    fixtures_root = tmp_path / "fixtures-root"
    prepare_root(fixtures_root)

    with pytest.raises(RuntimeError, match=message):
        recorded.validate_fixture_corpus(
            repo_root=tmp_path,
            demo_config=_build_demo_config(tmp_path),
            fixtures_root=fixtures_root,
            output_root=None,
            render_review_video=False,
            review_video_fps=None,
        )
