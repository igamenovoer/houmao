"""Unit tests for the shared tracked-TUI demo pack."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from houmao.demo.shared_tui_tracking_demo_pack.config import (
    ResolvedDemoConfig,
    resolve_demo_config,
)
from houmao.demo.shared_tui_tracking_demo_pack.groundtruth import (
    expand_labels_to_groundtruth_timeline,
)
from houmao.demo.shared_tui_tracking_demo_pack.live_watch import start_live_watch
from houmao.demo.shared_tui_tracking_demo_pack.models import (
    LiveWatchManifest,
    LiveWatchPaths,
    RecordedValidationPaths,
)
from houmao.demo.shared_tui_tracking_demo_pack import recorded as recorded_module
from houmao.demo.shared_tui_tracking_demo_pack.recorded import validate_recorded_fixture
from houmao.demo.shared_tui_tracking_demo_pack.review_video import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    build_ffmpeg_command,
    render_review_frames,
)
from houmao.demo.shared_tui_tracking_demo_pack.sweep import run_recorded_sweep
from houmao.demo.shared_tui_tracking_demo_pack.tooling import default_tool_runtime_metadata


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _write(path: Path, content: str) -> None:
    """Write one UTF-8 text file, creating parent directories first."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON file."""

    _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _demo_config() -> ResolvedDemoConfig:
    """Return the checked-in resolved demo config."""

    return resolve_demo_config(repo_root=_repo_root())


def _watch_manifest(paths: LiveWatchPaths) -> LiveWatchManifest:
    """Return one deterministic live-watch manifest for tests."""

    return LiveWatchManifest(
        schema_version=1,
        run_id=paths.run_root.name,
        tool="claude",
        repo_root="/repo",
        run_root=str(paths.run_root),
        runtime_root=str(paths.runtime_root),
        recipe_path="/repo/tests/fixtures/agents/brains/brain-recipes/claude/interactive-watch-default.yaml",
        brain_home_path=str(paths.runtime_root / "homes" / "claude-home"),
        brain_manifest_path=str(paths.runtime_root / "manifests" / "claude-home.yaml"),
        launch_helper_path=str(paths.runtime_root / "homes" / "claude-home" / "launch.sh"),
        workdir=str(paths.workdir),
        tool_session_name="shared-tui-claude-demo",
        tool_attach_command="tmux attach-session -t shared-tui-claude-demo",
        dashboard_session_name="shared-tui-dashboard-demo",
        dashboard_attach_command="tmux attach-session -t shared-tui-dashboard-demo",
        dashboard_command="pixi run python scripts/demo/shared-tui-tracking-demo-pack/scripts/demo_driver.py dashboard --run-root /tmp/run",
        terminal_record_run_root=str(paths.terminal_record_run_root),
        resolved_config_path=str(paths.resolved_config_path),
        sample_interval_seconds=0.2,
        runtime_observer_interval_seconds=0.2,
        settle_seconds=1.0,
        observed_version="2.1.80 (Claude Code)",
        trace_enabled=False,
        started_at_utc="2026-03-20T00:00:00+00:00",
        stopped_at_utc=None,
        stop_reason=None,
    )


def test_recorded_and_live_paths_resolve_expected_layout() -> None:
    """The demo-pack layouts should derive stable subpaths from one run root."""

    recorded_run_root = Path(
        "/repo-root/tmp/demo/shared-tui-tracking-demo-pack/recorded/claude/demo"
    )
    live_run_root = Path("/repo-root/tmp/demo/shared-tui-tracking-demo-pack/live/codex/demo")

    recorded_paths = RecordedValidationPaths.from_run_root(run_root=recorded_run_root)
    live_paths = LiveWatchPaths.from_run_root(run_root=live_run_root)

    assert recorded_paths.analysis_dir == recorded_run_root / "analysis"
    assert recorded_paths.review_video_path == recorded_run_root / "review" / "review.mp4"
    assert live_paths.runtime_root == live_run_root / "runtime"
    assert live_paths.state_samples_path == live_run_root / "artifacts" / "state_samples.ndjson"
    assert (
        live_paths.terminal_record_run_root
        == live_run_root / f"terminal-record-{live_run_root.name}"
    )


def test_default_tool_runtime_metadata_uses_permissive_launch_posture() -> None:
    """Claude should use the explicit permissive flag, while Codex uses config posture."""

    repo_root = _repo_root()

    claude_metadata = default_tool_runtime_metadata(repo_root=repo_root, tool="claude")
    codex_metadata = default_tool_runtime_metadata(repo_root=repo_root, tool="codex")

    assert claude_metadata.launch_args_override == ["--dangerously-skip-permissions"]
    assert codex_metadata.launch_args_override is None
    assert claude_metadata.interactive_watch_recipe_path.name == "interactive-watch-default.yaml"
    assert codex_metadata.interactive_watch_recipe_path.name == "interactive-watch-default.yaml"


def test_expand_labels_to_groundtruth_timeline_requires_full_coverage(tmp_path: Path) -> None:
    """Ground-truth expansion should fail when labels do not cover every sample."""

    recording_root = tmp_path / "recording"
    _write(
        recording_root / "pane_snapshots.ndjson",
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": "s000001",
                        "elapsed_seconds": 0.0,
                        "ts_utc": "2026-03-20T00:00:00+00:00",
                        "target_pane_id": "%1",
                        "output_text": "› \n",
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "s000002",
                        "elapsed_seconds": 1.0,
                        "ts_utc": "2026-03-20T00:00:01+00:00",
                        "target_pane_id": "%1",
                        "output_text": "› \n",
                    }
                ),
            ]
        )
        + "\n",
    )
    _write_json(
        recording_root / "labels.json",
        {
            "schema_version": 1,
            "labels": [
                {
                    "label_id": "only-first",
                    "scenario_id": None,
                    "sample_id": "s000001",
                    "sample_end_id": None,
                    "expectations": {
                        "diagnostics_availability": "available",
                        "surface_accepting_input": "yes",
                        "surface_editing_input": "no",
                        "surface_ready_posture": "yes",
                        "turn_phase": "ready",
                        "last_turn_result": "none",
                        "last_turn_source": "none",
                    },
                    "note": None,
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="do not cover all samples"):
        expand_labels_to_groundtruth_timeline(recording_root=recording_root)


def test_render_review_frames_creates_1080p_pngs(tmp_path: Path) -> None:
    """Rendered review frames should be persisted at 1080p."""

    fixture_root = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "shared_tui_tracking"
        / "recorded"
        / "claude"
        / "claude_explicit_success"
    )
    result = validate_recorded_fixture(
        repo_root=_repo_root(),
        demo_config=_demo_config(),
        fixture_root=fixture_root,
        output_root=tmp_path / "recorded-run",
        render_review_video=False,
    )
    frames_dir = tmp_path / "frames"
    from houmao.demo.shared_tui_tracking_demo_pack.groundtruth import load_fixture_inputs

    inputs = load_fixture_inputs(
        recording_root=fixture_root / "recording",
        runtime_observations_path=fixture_root / "runtime_observations.ndjson",
    )
    frame_paths = render_review_frames(
        snapshots=inputs.snapshots,
        groundtruth_timeline=expand_labels_to_groundtruth_timeline(
            recording_root=fixture_root / "recording"
        ),
        output_dir=frames_dir,
        fps=5.0,
    )

    assert result.comparison.mismatch_count == 0
    assert frame_paths
    with Image.open(frame_paths[0]) as image:
        assert image.size == (FRAME_WIDTH, FRAME_HEIGHT)


def test_build_ffmpeg_command_uses_libx264_and_yuv420p(tmp_path: Path) -> None:
    """The review-video encode command should lock the requested codec settings."""

    command = build_ffmpeg_command(
        frames_dir=tmp_path / "frames",
        output_path=tmp_path / "review.mp4",
        fps=5.0,
    )

    assert command[:5] == ["ffmpeg", "-y", "-framerate", "5", "-i"]
    assert "libx264" in command
    assert "yuv420p" in command


def test_send_text_submits_as_separate_managed_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed text submission should emit a delayed Enter as a separate event."""

    captured_sequences: list[str] = []
    sleep_calls: list[float] = []

    def _fake_send_sequence(*, session_name: str, pane_id: str, sequence: str) -> None:
        del session_name, pane_id
        captured_sequences.append(sequence)

    monkeypatch.setattr(recorded_module, "_send_sequence", _fake_send_sequence)
    monkeypatch.setattr(recorded_module.time, "sleep", sleep_calls.append)

    recorded_module._send_text(
        session_name="shared-tui-codex-demo",
        pane_id="%1",
        text="Reply with the single word READY and stop.",
        submit=True,
    )

    assert captured_sequences == [
        "Reply with the single word READY and stop.",
        "<[Enter]>",
    ]
    assert sleep_calls == [recorded_module._SUBMIT_KEY_DELAY_SECONDS]


def test_start_live_watch_builds_run_local_runtime_and_cleanup_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Live watch should build run-local runtime and clean up sessions after dashboard failure."""

    recipe_path = tmp_path / "recipe.yaml"
    _write(
        recipe_path,
        "\n".join(
            [
                "schema_version: 1",
                "name: interactive-watch-default",
                "tool: claude",
                "skills:",
                "  - openspec-explore",
                "config_profile: default",
                "credential_profile: personal-a-default",
            ]
        )
        + "\n",
    )
    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    requested: dict[str, object] = {}
    cleaned_sessions: list[str] = []

    def _fake_build(request):
        requested["runtime_root"] = request.runtime_root
        requested["launch_args_override"] = request.launch_args_override
        home_path = Path(request.runtime_root) / "homes" / "claude-home"  # type: ignore[arg-type]
        manifest_path = Path(request.runtime_root) / "manifests" / "claude-home.yaml"  # type: ignore[arg-type]
        launch_path = home_path / "launch.sh"
        home_path.mkdir(parents=True, exist_ok=True)
        launch_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("schema_version: 1\n", encoding="utf-8")
        return SimpleNamespace(
            home_path=home_path,
            manifest_path=manifest_path,
            launch_helper_path=launch_path,
        )

    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.build_brain_home",
        _fake_build,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.launch_tmux_session",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.resolve_active_pane_id",
        lambda **_kwargs: "%1",
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.start_terminal_record",
        lambda **_kwargs: {"run_root": str(paths.terminal_record_run_root)},
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.detect_tool_version",
        lambda *, tool: "2.1.80 (Claude Code)" if tool == "claude" else None,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch._wait_for_dashboard_running",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("dashboard failed")),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.stop_terminal_record",
        lambda *, run_root: {"status": "stopped", "run_root": str(run_root)},
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.kill_tmux_session_if_exists",
        lambda *, session_name: cleaned_sessions.append(session_name),
    )

    with pytest.raises(RuntimeError, match="dashboard failed"):
        start_live_watch(
            repo_root=tmp_path,
            demo_config=_demo_config(),
            tool="claude",
            output_root=run_root,
            recipe_path=recipe_path,
            sample_interval_seconds=0.25,
            runtime_observer_interval_seconds=0.2,
            settle_seconds=1.0,
            trace_enabled=False,
        )

    live_state_payload = json.loads(paths.live_state_path.read_text(encoding="utf-8"))
    assert requested["runtime_root"] == run_root / "runtime"
    assert requested["launch_args_override"] == ["--dangerously-skip-permissions"]
    assert set(cleaned_sessions) == {
        "shared-tui-claude-live-run",
        "shared-tui-dashboard-live-run",
    }
    assert live_state_payload["status"] == "failed"
    assert live_state_payload["last_error"] == "dashboard failed"


def test_demo_config_resolution_honors_profile_and_cli_precedence(tmp_path: Path) -> None:
    """CLI overrides should win over profile defaults during config resolution."""

    config_path = tmp_path / "demo-config.toml"
    _write(
        config_path,
        "\n".join(
            [
                'schema_version = 1',
                'demo_id = "shared-tui-tracking-demo-pack"',
                "",
                "[paths]",
                'fixtures_root = "tests/fixtures/shared_tui_tracking/recorded"',
                'recorded_root = "tmp/demo/shared-tui-tracking-demo-pack/recorded"',
                'live_root = "tmp/demo/shared-tui-tracking-demo-pack/live"',
                'sweeps_root = "tmp/demo/shared-tui-tracking-demo-pack/sweeps"',
                "",
                "[tools.claude]",
                'recipe_path = "tests/fixtures/agents/brains/brain-recipes/claude/interactive-watch-default.yaml"',
                'launch_args_override = ["--dangerously-skip-permissions"]',
                "",
                "[tools.codex]",
                'recipe_path = "tests/fixtures/agents/brains/brain-recipes/codex/interactive-watch-default.yaml"',
                "launch_args_override = []",
                "",
                "[evidence]",
                "sample_interval_seconds = 0.2",
                "runtime_observer_interval_seconds = 0.2",
                "ready_timeout_seconds = 45.0",
                "cleanup_session = true",
                "",
                "[semantics]",
                "settle_seconds = 1.0",
                "",
                "[presentation.review_video]",
                "match_capture_cadence = true",
                "width = 1920",
                "height = 1080",
                'codec = "libx264"',
                'pixel_format = "yuv420p"',
                "keep_frames = true",
                "",
                "[profiles.fast_local.evidence]",
                "sample_interval_seconds = 0.4",
                "runtime_observer_interval_seconds = 0.4",
                "",
                "[scenario_overrides.demo_case.evidence]",
                "ready_timeout_seconds = 21.0",
            ]
        )
        + "\n",
    )

    resolved = resolve_demo_config(
        repo_root=_repo_root(),
        config_path=config_path,
        profile_name="fast_local",
        scenario_id="demo_case",
        cli_overrides={
            "evidence": {
                "sample_interval_seconds": 0.6,
            },
            "presentation": {
                "review_video": {
                    "match_capture_cadence": False,
                    "fps": 4.0,
                }
            },
        },
    )

    assert resolved.evidence.sample_interval_seconds == 0.6
    assert resolved.evidence.runtime_observer_interval_seconds == 0.4
    assert resolved.evidence.ready_timeout_seconds == 21.0
    assert resolved.presentation.review_video.fps == 4.0


def test_run_recorded_sweep_writes_summary_and_variant_verdicts(tmp_path: Path) -> None:
    """A recorded sweep should write its report and per-variant verdict artifacts."""

    fixture_root = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "shared_tui_tracking"
        / "recorded"
        / "claude"
        / "claude_explicit_success"
    )

    result = run_recorded_sweep(
        repo_root=_repo_root(),
        demo_config=_demo_config(),
        sweep_name="capture_frequency",
        fixture_root=fixture_root,
        output_root=tmp_path / "sweep-run",
    )

    source_verdict = json.loads(
        (result.run_root / "variants" / "source" / "verdict.json").read_text(encoding="utf-8")
    )

    assert result.summary_path.is_file()
    assert result.outcome_count == 3
    assert source_verdict["passed"] is True
