"""Unit tests for the shared tracked-TUI demo pack."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from houmao.demo.shared_tui_tracking_demo_pack import driver as demo_driver
from houmao.demo.shared_tui_tracking_demo_pack import ownership as ownership_module
from houmao.demo.shared_tui_tracking_demo_pack import recorded as recorded_module
from houmao.demo.shared_tui_tracking_demo_pack.boundary_models import DemoConfigDocumentV1
from houmao.demo.shared_tui_tracking_demo_pack.config import (
    ResolvedDemoConfig,
    resolve_demo_config,
)
from houmao.demo.shared_tui_tracking_demo_pack.groundtruth import (
    expand_labels_to_groundtruth_timeline,
)
from houmao.demo.shared_tui_tracking_demo_pack.live_watch import (
    inspect_live_watch,
    start_live_watch,
    stop_live_watch,
)
from houmao.demo.shared_tui_tracking_demo_pack.models import (
    DemoOwnedResource,
    DemoSessionOwnership,
    LiveWatchManifest,
    LiveWatchPaths,
    RecordedValidationPaths,
    load_session_ownership,
    save_session_ownership,
    session_ownership_path,
)
from houmao.demo.shared_tui_tracking_demo_pack.ownership import ResolvedDemoOwnedResources
from houmao.demo.shared_tui_tracking_demo_pack.recorded import validate_recorded_fixture
from houmao.demo.shared_tui_tracking_demo_pack.scenario import load_scenario
from houmao.demo.shared_tui_tracking_demo_pack.review_video import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    build_ffmpeg_command,
    render_review_frames,
)
from houmao.demo.shared_tui_tracking_demo_pack.schema_validation import load_schema
from houmao.demo.shared_tui_tracking_demo_pack.sweep import (
    _match_required_sequence,
    run_recorded_sweep,
)
from houmao.demo.shared_tui_tracking_demo_pack.tooling import (
    build_dashboard_session_name,
    build_tool_session_name,
    default_tool_runtime_metadata,
)
from houmao.shared_tui_tracking.apps.codex_tui.profile import CodexTuiSignalDetector
from houmao.shared_tui_tracking.models import RuntimeObservation


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


def _write_terminal_record_manifest(
    run_root: Path,
    *,
    recorder_session_name: str = "terminal-record-demo",
    target_session_name: str = "shared-tui-claude-demo",
    pane_id: str = "%1",
) -> None:
    """Write one minimal terminal-recorder manifest for tests."""

    _write_json(
        run_root / "manifest.json",
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "mode": "passive",
            "repo_root": str(_repo_root()),
            "run_root": str(run_root.resolve()),
            "target": {
                "session_name": target_session_name,
                "pane_id": pane_id,
                "window_id": "@1",
                "window_name": "main",
            },
            "tool": "claude",
            "sample_interval_seconds": 0.2,
            "visual_recording_kind": "readonly_observer",
            "input_capture_level": "output_only",
            "run_tainted": False,
            "taint_reasons": [],
            "recorder_session_name": recorder_session_name,
            "attach_command": None,
            "started_at_utc": "2026-03-22T00:00:00+00:00",
            "stopped_at_utc": None,
            "stop_reason": None,
        },
    )


def _demo_session_ownership(
    run_root: Path,
    *,
    workflow_kind: str = "live_watch",
    status: str = "starting",
    recorder_run_root: Path | None = None,
    owned_resources: tuple[DemoOwnedResource, ...] = (),
) -> DemoSessionOwnership:
    """Return one demo-run ownership payload for tests."""

    return DemoSessionOwnership(
        schema_version=1,
        demo_id="shared-tui-tracking-demo-pack",
        workflow_kind=workflow_kind,  # type: ignore[arg-type]
        run_root=str(run_root.resolve()),
        tool="claude",
        status=status,  # type: ignore[arg-type]
        recorder_run_root=(
            str(recorder_run_root.resolve()) if recorder_run_root is not None else None
        ),
        owned_resources=owned_resources,
        started_at_utc="2026-03-22T00:00:00+00:00",
        updated_at_utc="2026-03-22T00:00:00+00:00",
        stopped_at_utc=None,
        last_error=None,
    )


def _demo_config() -> ResolvedDemoConfig:
    """Return the checked-in resolved demo config."""

    return resolve_demo_config(repo_root=_repo_root())


def _default_demo_config_text() -> str:
    """Return the checked-in demo config text."""

    path = _repo_root() / "scripts" / "demo" / "shared-tui-tracking-demo-pack" / "demo-config.toml"
    return path.read_text(encoding="utf-8")


def _write_demo_config_copy(path: Path, *, replacements: dict[str, str] | None = None) -> None:
    """Write a copy of the checked-in demo config with optional replacements."""

    content = _default_demo_config_text()
    for source, target in (replacements or {}).items():
        content = content.replace(source, target)
    _write(path, content)


def _watch_manifest(
    paths: LiveWatchPaths,
    *,
    recorder_enabled: bool = True,
) -> LiveWatchManifest:
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
        recorder_enabled=recorder_enabled,
        terminal_record_run_root=(
            str(paths.terminal_record_run_root) if recorder_enabled else None
        ),
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


def test_demo_session_ownership_round_trips_and_saves_atomically(tmp_path: Path) -> None:
    """Ownership artifacts should round-trip cleanly without leaving temp files behind."""

    run_root = tmp_path / "live-run"
    ownership = _demo_session_ownership(
        run_root,
        owned_resources=(DemoOwnedResource(role="tool", session_name="shared-tui-claude-demo"),),
    )
    path = session_ownership_path(run_root=run_root)

    save_session_ownership(path, ownership)

    assert load_session_ownership(path) == ownership
    assert list(run_root.glob("*.tmp")) == []


def test_live_watch_session_names_associate_tool_and_dashboard_without_cross_tool_collision() -> None:
    """Tool and dashboard session names should stay associated and tool-scoped for one run id."""

    run_id = "20260323T140207"

    claude_tool = build_tool_session_name(tool="claude", run_id=run_id)
    claude_dashboard = build_dashboard_session_name(tool="claude", run_id=run_id)
    codex_tool = build_tool_session_name(tool="codex", run_id=run_id)
    codex_dashboard = build_dashboard_session_name(tool="codex", run_id=run_id)

    assert claude_tool == "shared-tui-claude-20260323T140207"
    assert claude_dashboard == "shared-tui-claude-dashboard-20260323T140207"
    assert codex_tool == "shared-tui-codex-20260323T140207"
    assert codex_dashboard == "shared-tui-codex-dashboard-20260323T140207"
    assert claude_tool != codex_tool
    assert claude_dashboard != codex_dashboard
    assert claude_dashboard.startswith("shared-tui-claude-")
    assert codex_dashboard.startswith("shared-tui-codex-")


def test_publish_demo_session_recovery_pointers_sets_tmux_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ownership publication should tag tmux sessions with run-local recovery pointers."""

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        ownership_module,
        "set_tmux_session_environment",
        lambda *, session_name, env_vars: captured.update(
            {"session_name": session_name, "env_vars": env_vars}
        ),
    )

    ownership_module.publish_demo_session_recovery_pointers(
        demo_id="shared-tui-tracking-demo-pack",
        run_root=tmp_path / "live-run",
        session_name="shared-tui-claude-demo",
        role="tool",
    )

    assert captured["session_name"] == "shared-tui-claude-demo"
    assert captured["env_vars"] == {
        ownership_module.DEMO_SESSION_ID_ENV_VAR: "shared-tui-tracking-demo-pack",
        ownership_module.DEMO_SESSION_RUN_ROOT_ENV_VAR: str((tmp_path / "live-run").resolve()),
        ownership_module.DEMO_SESSION_OWNERSHIP_PATH_ENV_VAR: str(
            session_ownership_path(run_root=tmp_path / "live-run")
        ),
        ownership_module.DEMO_SESSION_ROLE_ENV_VAR: "tool",
    }


def test_resolve_demo_owned_resources_prefers_ownership_then_manifest_then_tmux_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discovery should combine ownership, final manifests, and tmux-env fallback per role."""

    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    save_session_ownership(
        paths.session_ownership_path,
        _demo_session_ownership(
            run_root,
            owned_resources=(DemoOwnedResource(role="tool", session_name="owned-tool"),),
        ),
    )
    _write_json(paths.watch_manifest_path, _watch_manifest(paths).to_payload())
    monkeypatch.setattr(
        ownership_module,
        "_tmux_session_is_live",
        lambda session_name: (
            session_name in {"owned-tool", "shared-tui-dashboard-demo", "recovered-recorder"}
        ),
    )
    monkeypatch.setattr(
        ownership_module,
        "_list_tmux_session_names",
        lambda: ("recovered-recorder",),
    )
    monkeypatch.setattr(
        ownership_module,
        "read_demo_session_recovery_pointers",
        lambda *, session_name: (
            ownership_module.DemoSessionRecoveryPointers(
                run_root=run_root.resolve(),
                ownership_path=paths.session_ownership_path,
                role="recorder",
            )
            if session_name == "recovered-recorder"
            else None
        ),
    )

    resolved = ownership_module.resolve_demo_owned_resources(run_root=run_root)

    assert resolved.known_session_name(role="tool") == "owned-tool"
    assert resolved.known_session_name(role="dashboard") == "shared-tui-dashboard-demo"
    assert resolved.known_session_name(role="recorder") == "recovered-recorder"
    assert resolved.recorder_run_root == paths.terminal_record_run_root
    assert [item.role for item in resolved.owned_resources] == ["tool", "dashboard", "recorder"]


def test_reap_demo_owned_resources_stops_recorder_before_tmux_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup should stop the recorder service before direct tmux cleanup for remaining sessions."""

    recorder_run_root = tmp_path / "recording"
    kill_calls: list[str] = []
    stop_calls: list[Path] = []
    monkeypatch.setattr(
        ownership_module,
        "stop_terminal_record",
        lambda *, run_root: stop_calls.append(run_root) or {"status": "stopped"},
    )
    monkeypatch.setattr(
        ownership_module,
        "_tmux_session_is_live",
        lambda _session_name: True,
    )
    monkeypatch.setattr(
        ownership_module,
        "kill_tmux_session_if_exists",
        lambda *, session_name: kill_calls.append(session_name),
    )

    resolved = ResolvedDemoOwnedResources(
        run_root=tmp_path / "live-run",
        ownership_path=session_ownership_path(run_root=tmp_path / "live-run"),
        ownership=None,
        recorder_run_root=recorder_run_root,
        owned_resources=(
            DemoOwnedResource(role="tool", session_name="tool-session"),
            DemoOwnedResource(role="dashboard", session_name="dashboard-session"),
            DemoOwnedResource(role="recorder", session_name="recorder-session"),
        ),
        live_resources=(
            DemoOwnedResource(role="tool", session_name="tool-session"),
            DemoOwnedResource(role="dashboard", session_name="dashboard-session"),
            DemoOwnedResource(role="recorder", session_name="recorder-session"),
        ),
    )

    payload = ownership_module.reap_demo_owned_resources(
        resolved_resources=resolved,
        include_roles={"tool", "dashboard", "recorder"},
        stop_recorder=True,
        best_effort=False,
    )

    assert stop_calls == [recorder_run_root]
    assert kill_calls == ["tool-session", "dashboard-session", "recorder-session"]
    assert payload["recorder_stop"] == {"status": "stopped"}


def test_default_tool_runtime_metadata_uses_permissive_launch_posture() -> None:
    """Claude should request unattended launch policy, while Codex uses config posture."""

    repo_root = _repo_root()

    claude_metadata = default_tool_runtime_metadata(repo_root=repo_root, tool="claude")
    codex_metadata = default_tool_runtime_metadata(repo_root=repo_root, tool="codex")

    assert claude_metadata.launch_overrides is None
    assert claude_metadata.operator_prompt_mode == "unattended"
    assert codex_metadata.launch_overrides is None
    assert codex_metadata.operator_prompt_mode is None
    assert claude_metadata.interactive_watch_recipe_path.name == "interactive-watch-default.yaml"
    assert codex_metadata.interactive_watch_recipe_path.name == "interactive-watch-default.yaml"


def test_default_capture_frequency_sweep_respects_two_hz_floor() -> None:
    """The checked-in robustness sweep should not claim sub-2 Hz support."""

    sweep = _demo_config().sweeps["capture_frequency"]
    intervals = [
        variant.sample_interval_seconds
        for variant in sweep.variants
        if variant.sample_interval_seconds is not None
    ]

    assert intervals
    assert 0.5 in intervals
    assert all(value <= 0.5 for value in intervals)


def test_repeated_interrupt_scenario_uses_semantic_actions() -> None:
    """The repeated lifecycle scenario should wait for true interrupted-ready posture."""

    scenario = load_scenario(
        _repo_root()
        / "scripts"
        / "demo"
        / "shared-tui-tracking-demo-pack"
        / "scenarios"
        / "claude-double-interrupt-then-close.json"
    )

    actions = [step.action for step in scenario.steps]

    assert "interrupt_turn" in actions
    assert "wait_for_interrupted_ready" in actions
    assert "close_tool" in actions
    assert actions.count("interrupt_turn") == 2
    assert actions.count("wait_for_interrupted_ready") == 2


def test_claude_complex_scenario_waits_for_detector_active() -> None:
    """The Claude complex scenario should wait on detector-owned active posture."""

    scenario = load_scenario(
        _repo_root()
        / "scripts"
        / "demo"
        / "shared-tui-tracking-demo-pack"
        / "scenarios"
        / "claude-success-interrupt-success-complex.json"
    )

    actions = [step.action for step in scenario.steps]

    assert actions.count("wait_for_active") == 2
    assert actions.count("wait_for_interrupted_signal") == 2


def test_codex_detector_recognizes_wrapped_interrupted_banner() -> None:
    """Wrapped Codex interrupted banners should still count as interrupted-ready."""

    detector = CodexTuiSignalDetector()
    output_text = "\n".join(
        [
            "› Search this repository for files related to tmux and prepare a grouped summary.",
            "",
            "■ Conversation interrupted - tell the model what to do",
            "differently. Something went wrong? Hit `/feedback` to",
            "report the issue.",
            "",
            "› Write tests for @filename",
        ]
    )

    signals = detector.detect(output_text=output_text)

    assert signals.interrupted is True
    assert signals.ready_posture == "yes"
    assert signals.active_evidence is False


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


def test_wait_for_active_requires_spinner_evidence_for_claude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claude active waits should key off spinner evidence, not summary-only activity."""

    surfaces = iter(["summary-only", "spinner-active"])

    monkeypatch.setattr(
        recorded_module,
        "capture_visible_pane_text",
        lambda *, pane_id: next(surfaces),
    )
    monkeypatch.setattr(recorded_module.time, "sleep", lambda _seconds: None)

    class _FakeDetector:
        def detect(self, *, output_text: str):
            if output_text == "summary-only":
                return SimpleNamespace(
                    detector_name="claude_code",
                    active_evidence=True,
                    active_reasons=("active_block",),
                )
            return SimpleNamespace(
                detector_name="claude_code",
                active_evidence=True,
                active_reasons=("thinking_line",),
            )

    recorded_module._wait_for_active(
        pane_id="%1",
        detector=_FakeDetector(),
        timeout_seconds=1.0,
    )


def test_wait_for_interrupted_signal_accepts_first_interrupted_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interrupted transition waits should not require a second identical sample."""

    surfaces = iter(["active", "interrupted"])

    monkeypatch.setattr(
        recorded_module,
        "capture_visible_pane_text",
        lambda *, pane_id: next(surfaces),
    )
    monkeypatch.setattr(recorded_module.time, "sleep", lambda _seconds: None)

    class _FakeDetector:
        def detect(self, *, output_text: str):
            if output_text == "active":
                return SimpleNamespace(
                    interrupted=False,
                    ready_posture="unknown",
                    active_evidence=True,
                )
            return SimpleNamespace(
                interrupted=True,
                ready_posture="yes",
                active_evidence=False,
            )

    recorded_module._wait_for_interrupted_signal(
        pane_id="%1",
        detector=_FakeDetector(),
        timeout_seconds=1.0,
    )


def test_start_live_watch_builds_run_local_runtime_and_cleanup_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default live watch should skip recorder startup and still clean up on failure."""

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
    recorder_start_calls: list[dict[str, object]] = []

    def _fake_build(request):
        requested["runtime_root"] = request.runtime_root
        requested["launch_overrides"] = request.launch_overrides
        requested["operator_prompt_mode"] = request.operator_prompt_mode
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
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.publish_demo_session_recovery_pointers",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.start_terminal_record",
        lambda **kwargs: recorder_start_calls.append(kwargs),
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
        ownership_module,
        "_list_tmux_session_names",
        lambda: (),
    )
    monkeypatch.setattr(
        ownership_module,
        "_tmux_session_is_live",
        lambda _session_name: True,
    )
    monkeypatch.setattr(
        ownership_module,
        "kill_tmux_session_if_exists",
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
    manifest_payload = json.loads(paths.watch_manifest_path.read_text(encoding="utf-8"))
    assert requested["runtime_root"] == run_root / "runtime"
    assert requested["launch_overrides"] is None
    assert requested["operator_prompt_mode"] == "unattended"
    assert recorder_start_calls == []
    assert set(cleaned_sessions) == {
        "shared-tui-claude-live-run",
        "shared-tui-claude-dashboard-live-run",
    }
    assert manifest_payload["tool_session_name"] == "shared-tui-claude-live-run"
    assert manifest_payload["dashboard_session_name"] == "shared-tui-claude-dashboard-live-run"
    assert manifest_payload["recorder_enabled"] is False
    assert manifest_payload["terminal_record_run_root"] is None
    assert live_state_payload["status"] == "failed"
    assert live_state_payload["last_error"] == "dashboard failed"
    ownership_payload = json.loads(paths.session_ownership_path.read_text(encoding="utf-8"))
    assert ownership_payload["status"] == "failed"


def test_start_live_watch_starts_recorder_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recorder-enabled live watch should start and clean up passive recorder state."""

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
    recorder_start_calls: list[dict[str, object]] = []
    recorder_stop_calls: list[Path] = []

    def _fake_build(request):
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
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.publish_demo_session_recovery_pointers",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.start_terminal_record",
        lambda **kwargs: (
            recorder_start_calls.append(kwargs),
            Path(kwargs["run_root"]).mkdir(parents=True, exist_ok=True),
            _write_terminal_record_manifest(
                Path(kwargs["run_root"]),
                recorder_session_name="terminal-record-live-run",
            ),
            {"status": "running"},
        )[-1],
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
        ownership_module,
        "_list_tmux_session_names",
        lambda: (),
    )
    monkeypatch.setattr(
        ownership_module,
        "_tmux_session_is_live",
        lambda _session_name: True,
    )
    monkeypatch.setattr(
        ownership_module,
        "stop_terminal_record",
        lambda *, run_root: recorder_stop_calls.append(run_root) or {"status": "stopped"},
    )
    monkeypatch.setattr(
        ownership_module,
        "kill_tmux_session_if_exists",
        lambda **_kwargs: None,
    )

    demo_config = resolve_demo_config(
        repo_root=_repo_root(),
        cli_overrides={"evidence": {"live_watch_recorder_enabled": True}},
    )

    with pytest.raises(RuntimeError, match="dashboard failed"):
        start_live_watch(
            repo_root=tmp_path,
            demo_config=demo_config,
            tool="claude",
            output_root=run_root,
            recipe_path=recipe_path,
            sample_interval_seconds=0.25,
            runtime_observer_interval_seconds=0.2,
            settle_seconds=1.0,
            trace_enabled=False,
        )

    manifest_payload = json.loads(paths.watch_manifest_path.read_text(encoding="utf-8"))
    assert len(recorder_start_calls) == 1
    assert recorder_start_calls[0]["run_root"] == paths.terminal_record_run_root
    assert recorder_stop_calls == [paths.terminal_record_run_root]
    assert manifest_payload["recorder_enabled"] is True
    assert manifest_payload["terminal_record_run_root"] == str(paths.terminal_record_run_root)
    ownership_payload = json.loads(paths.session_ownership_path.read_text(encoding="utf-8"))
    assert ownership_payload["owned_resources"][-1]["session_name"] == "terminal-record-live-run"


def test_stop_live_watch_accepts_older_manifest_without_resolved_config_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stopping a pre-config-reference live-watch run should not crash on manifest load."""

    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    paths.issues_dir.mkdir(parents=True, exist_ok=True)
    manifest_payload = _watch_manifest(paths).to_payload()
    manifest_payload.pop("resolved_config_path")
    manifest_payload.pop("recorder_enabled")
    _write_json(paths.watch_manifest_path, manifest_payload)
    _write_json(
        paths.live_state_path,
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "status": "running",
            "latest_state_path": str(paths.latest_state_path),
            "stop_requested_at_utc": None,
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:00+00:00",
        },
    )
    _write_json(
        paths.terminal_record_run_root / "live_state.json",
        {
            "schema_version": 1,
            "run_id": f"terminal-record-{run_root.name}",
            "mode": "passive",
            "status": "stopped",
            "repo_root": str(tmp_path),
            "run_root": str(paths.terminal_record_run_root),
            "manifest_path": str(paths.terminal_record_run_root / "manifest.json"),
            "controller_pid": None,
            "target_session_name": "shared-tui-claude-demo",
            "target_pane_id": "%1",
            "stop_requested_at_utc": "2026-03-22T00:00:01+00:00",
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:02+00:00",
        },
    )

    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.stop_terminal_record",
        lambda *, run_root: {"status": "stopped", "run_root": str(run_root)},
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch._wait_for_dashboard_stop",
        lambda **_kwargs: None,
    )
    cleaned_sessions: list[str] = []
    monkeypatch.setattr(
        ownership_module,
        "_list_tmux_session_names",
        lambda: (),
    )
    monkeypatch.setattr(
        ownership_module,
        "_tmux_session_is_live",
        lambda session_name: (
            session_name in {"shared-tui-claude-demo", "shared-tui-dashboard-demo"}
        ),
    )
    monkeypatch.setattr(
        ownership_module,
        "kill_tmux_session_if_exists",
        lambda *, session_name: cleaned_sessions.append(session_name),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch._finalize_live_replay",
        lambda **_kwargs: SimpleNamespace(mismatch_count=0),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.build_live_run_issues",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.write_issue_documents",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.build_live_summary_report",
        lambda **_kwargs: "summary\n",
    )
    timestamps = iter(["2026-03-22T00:00:03+00:00", "2026-03-22T00:00:04+00:00"])
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.now_utc_iso",
        lambda: next(timestamps),
    )

    payload = stop_live_watch(
        repo_root=tmp_path,
        demo_config=_demo_config(),
        run_root=run_root,
        stop_reason="operator_requested",
    )

    updated_manifest = json.loads(paths.watch_manifest_path.read_text(encoding="utf-8"))
    updated_live_state = json.loads(paths.live_state_path.read_text(encoding="utf-8"))

    assert payload["run_root"] == str(run_root.resolve())
    assert payload["recorder_enabled"] is True
    assert set(cleaned_sessions) == {"shared-tui-claude-demo", "shared-tui-dashboard-demo"}
    assert updated_manifest["resolved_config_path"] == str(paths.resolved_config_path)
    assert updated_manifest["stop_reason"] == "operator_requested"
    assert updated_live_state["status"] == "stopped"


def test_stop_live_watch_without_recorder_skips_recorder_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recorder-disabled live watch should stop cleanly without recorder artifacts."""

    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    paths.issues_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        paths.watch_manifest_path, _watch_manifest(paths, recorder_enabled=False).to_payload()
    )
    _write_json(
        paths.live_state_path,
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "status": "running",
            "latest_state_path": str(paths.latest_state_path),
            "stop_requested_at_utc": None,
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:00+00:00",
        },
    )

    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.stop_terminal_record",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("recorder should not stop")),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch._wait_for_dashboard_stop",
        lambda **_kwargs: None,
    )
    cleaned_sessions: list[str] = []
    monkeypatch.setattr(
        ownership_module,
        "_list_tmux_session_names",
        lambda: (),
    )
    monkeypatch.setattr(
        ownership_module,
        "_tmux_session_is_live",
        lambda session_name: (
            session_name in {"shared-tui-claude-demo", "shared-tui-dashboard-demo"}
        ),
    )
    monkeypatch.setattr(
        ownership_module,
        "kill_tmux_session_if_exists",
        lambda *, session_name: cleaned_sessions.append(session_name),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.build_live_run_issues",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.write_issue_documents",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.build_live_summary_report",
        lambda **kwargs: "summary\n" if kwargs["recorder_enabled"] is False else "",
    )
    timestamps = iter(["2026-03-22T00:00:03+00:00", "2026-03-22T00:00:04+00:00"])
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.now_utc_iso",
        lambda: next(timestamps),
    )

    payload = stop_live_watch(
        repo_root=tmp_path,
        demo_config=_demo_config(),
        run_root=run_root,
        stop_reason="operator_requested",
    )

    updated_manifest = json.loads(paths.watch_manifest_path.read_text(encoding="utf-8"))
    assert payload["comparison_path"] is None
    assert payload["recorder_stop"] is None
    assert payload["recorder_enabled"] is False
    assert set(cleaned_sessions) == {"shared-tui-claude-demo", "shared-tui-dashboard-demo"}
    assert updated_manifest["recorder_enabled"] is False
    assert updated_manifest["terminal_record_run_root"] is None


def test_stop_live_watch_uses_recovered_owned_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stop should use recovered ownership metadata when manifest session names are stale."""

    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    paths.issues_dir.mkdir(parents=True, exist_ok=True)
    manifest = _watch_manifest(paths)
    _write_json(
        paths.watch_manifest_path,
        LiveWatchManifest(
            schema_version=manifest.schema_version,
            run_id=manifest.run_id,
            tool=manifest.tool,
            repo_root=manifest.repo_root,
            run_root=manifest.run_root,
            runtime_root=manifest.runtime_root,
            recipe_path=manifest.recipe_path,
            brain_home_path=manifest.brain_home_path,
            brain_manifest_path=manifest.brain_manifest_path,
            launch_helper_path=manifest.launch_helper_path,
            workdir=manifest.workdir,
            tool_session_name="manifest-tool-session",
            tool_attach_command=manifest.tool_attach_command,
            dashboard_session_name="manifest-dashboard-session",
            dashboard_attach_command=manifest.dashboard_attach_command,
            dashboard_command=manifest.dashboard_command,
            recorder_enabled=manifest.recorder_enabled,
            terminal_record_run_root=manifest.terminal_record_run_root,
            resolved_config_path=manifest.resolved_config_path,
            sample_interval_seconds=manifest.sample_interval_seconds,
            runtime_observer_interval_seconds=manifest.runtime_observer_interval_seconds,
            settle_seconds=manifest.settle_seconds,
            observed_version=manifest.observed_version,
            trace_enabled=manifest.trace_enabled,
            started_at_utc=manifest.started_at_utc,
            stopped_at_utc=manifest.stopped_at_utc,
            stop_reason=manifest.stop_reason,
        ).to_payload(),
    )
    _write_json(
        paths.live_state_path,
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "status": "running",
            "latest_state_path": str(paths.latest_state_path),
            "stop_requested_at_utc": None,
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:00+00:00",
        },
    )
    recovered = ResolvedDemoOwnedResources(
        run_root=run_root.resolve(),
        ownership_path=session_ownership_path(run_root=run_root),
        ownership=None,
        recorder_run_root=paths.terminal_record_run_root,
        owned_resources=(
            DemoOwnedResource(role="tool", session_name="recovered-tool-session"),
            DemoOwnedResource(role="dashboard", session_name="recovered-dashboard-session"),
            DemoOwnedResource(role="recorder", session_name="terminal-record-live-run"),
        ),
        live_resources=(
            DemoOwnedResource(role="tool", session_name="recovered-tool-session"),
            DemoOwnedResource(role="dashboard", session_name="recovered-dashboard-session"),
            DemoOwnedResource(role="recorder", session_name="terminal-record-live-run"),
        ),
    )
    recorder_stop_calls: list[Path] = []
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.resolve_demo_owned_resources",
        lambda *, run_root: recovered,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.stop_terminal_record",
        lambda *, run_root: recorder_stop_calls.append(run_root) or {"status": "stopped"},
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch._wait_for_dashboard_stop",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.reap_demo_owned_resources",
        lambda *, resolved_resources, **_kwargs: {
            "cleaned_sessions": [
                resolved_resources.known_session_name(role="tool"),
                resolved_resources.known_session_name(role="dashboard"),
            ],
        },
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch._finalize_live_replay",
        lambda **_kwargs: SimpleNamespace(mismatch_count=0),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.build_live_run_issues",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.write_issue_documents",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.build_live_summary_report",
        lambda **_kwargs: "summary\n",
    )
    timestamps = iter(["2026-03-22T00:00:03+00:00", "2026-03-22T00:00:04+00:00"])
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.now_utc_iso",
        lambda: next(timestamps),
    )

    payload = stop_live_watch(
        repo_root=tmp_path,
        demo_config=_demo_config(),
        run_root=run_root,
        stop_reason="operator_requested",
    )

    assert recorder_stop_calls == [paths.terminal_record_run_root]
    assert payload["cleaned_sessions"] == [
        "recovered-tool-session",
        "recovered-dashboard-session",
    ]


def test_run_dashboard_uses_direct_visible_pane_capture_without_recorder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recorder-disabled dashboard runs should derive observations from visible tmux text."""

    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        paths.watch_manifest_path, _watch_manifest(paths, recorder_enabled=False).to_payload()
    )
    _write_json(
        paths.live_state_path,
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "status": "starting",
            "latest_state_path": str(paths.latest_state_path),
            "stop_requested_at_utc": "2026-03-22T00:00:01+00:00",
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:00+00:00",
        },
    )

    class _FakeReducer:
        def __init__(self, **_kwargs) -> None:
            self.latest_observation = None
            self.latest_signals = SimpleNamespace(
                accepting_input="yes",
                editing_input="no",
                ready_posture="yes",
                detector_name="fake-detector",
                detector_version="1",
                active_reasons=(),
                notes=(),
            )

        def process_observation(self, observation):
            self.latest_observation = observation
            return SimpleNamespace(
                diagnostics_availability="available",
                surface_accepting_input="yes",
                surface_editing_input="no",
                surface_ready_posture="yes",
                turn_phase="ready",
                last_turn_result="none",
                last_turn_source="none",
                detector_name="fake-detector",
                detector_version="1",
                active_reasons=(),
                notes=(),
            )

        def drain_events(self):
            return []

    class _FakeLive:
        def __init__(self, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def update(self, _panel) -> None:
            return None

    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.StreamStateReducer",
        _FakeReducer,
    )
    monkeypatch.setattr("houmao.demo.shared_tui_tracking_demo_pack.live_watch.Live", _FakeLive)
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.resolve_active_pane_id",
        lambda **_kwargs: "%1",
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.sample_runtime_observation",
        lambda **_kwargs: RuntimeObservation(
            ts_utc="2026-03-22T00:00:02+00:00",
            elapsed_seconds=0.2,
            session_exists=True,
            pane_exists=True,
            pane_dead=False,
            pane_pid=123,
            pane_pid_alive=True,
            supported_process_pid=456,
            supported_process_alive=True,
        ),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.capture_visible_pane_text",
        lambda **_kwargs: "› READY\n",
    )

    assert demo_driver.main(["dashboard", "--run-root", str(run_root)]) == 0

    latest_state = json.loads(paths.latest_state_path.read_text(encoding="utf-8"))
    state_samples = paths.state_samples_path.read_text(encoding="utf-8").strip().splitlines()

    assert latest_state["sample_id"] == "s000001"
    assert latest_state["detector_name"] == "fake-detector"
    assert len(state_samples) == 1


def test_demo_config_resolution_honors_profile_and_cli_precedence(tmp_path: Path) -> None:
    """CLI overrides should win over profile defaults during config resolution."""

    config_path = tmp_path / "demo-config.toml"
    _write(
        config_path,
        "\n".join(
            [
                "schema_version = 1",
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
                'operator_prompt_mode = "unattended"',
                "",
                "[tools.codex]",
                'recipe_path = "tests/fixtures/agents/brains/brain-recipes/codex/interactive-watch-default.yaml"',
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


def test_demo_config_resolution_preserves_runtime_interval_fallback_after_profile_merge(
    tmp_path: Path,
) -> None:
    """Runtime cadence should still fall back to the merged sample cadence when omitted."""

    config_path = tmp_path / "demo-config.toml"
    _write(
        config_path,
        "\n".join(
            [
                "[paths]",
                'fixtures_root = "tests/fixtures/shared_tui_tracking/recorded"',
                'recorded_root = "tmp/demo/shared-tui-tracking-demo-pack/recorded"',
                'live_root = "tmp/demo/shared-tui-tracking-demo-pack/live"',
                'sweeps_root = "tmp/demo/shared-tui-tracking-demo-pack/sweeps"',
                "",
                "[tools.claude]",
                'recipe_path = "tests/fixtures/agents/brains/brain-recipes/claude/interactive-watch-default.yaml"',
                "",
                "[tools.codex]",
                'recipe_path = "tests/fixtures/agents/brains/brain-recipes/codex/interactive-watch-default.yaml"',
                "",
                "[evidence]",
                "sample_interval_seconds = 0.2",
                "",
                "[semantics]",
                "settle_seconds = 1.0",
                "",
                "[presentation.review_video]",
                "match_capture_cadence = true",
                "",
                "[profiles.fast_local.evidence]",
                "sample_interval_seconds = 0.4",
            ]
        )
        + "\n",
    )

    resolved = resolve_demo_config(
        repo_root=_repo_root(),
        config_path=config_path,
        profile_name="fast_local",
    )

    assert resolved.evidence.sample_interval_seconds == 0.4
    assert resolved.evidence.runtime_observer_interval_seconds == 0.4


def test_packaged_demo_config_schema_matches_boundary_model() -> None:
    """The packaged demo-config schema should match the boundary model exactly."""

    assert load_schema() == DemoConfigDocumentV1.model_json_schema()


def test_resolve_demo_config_reports_parse_error_with_selected_path(tmp_path: Path) -> None:
    """Malformed TOML should fail with the selected config path in the error."""

    config_path = tmp_path / "broken.toml"
    _write(config_path, "[paths\n")

    with pytest.raises(ValueError, match=str(config_path)):
        resolve_demo_config(repo_root=_repo_root(), config_path=config_path)


def test_resolve_demo_config_rejects_unknown_top_level_field(tmp_path: Path) -> None:
    """Unknown top-level fields should fail validation."""

    config_path = tmp_path / "unknown-top-level.toml"
    _write(config_path, "unsupported_flag = true\n\n" + _default_demo_config_text())

    with pytest.raises(ValueError, match=r"\$\.unsupported_flag"):
        resolve_demo_config(repo_root=_repo_root(), config_path=config_path)


def test_resolve_demo_config_rejects_missing_required_section(tmp_path: Path) -> None:
    """Missing required top-level sections should fail validation."""

    config_path = tmp_path / "missing-presentation.toml"
    _write(
        config_path,
        "\n".join(
            [
                "schema_version = 1",
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
                'operator_prompt_mode = "unattended"',
                "",
                "[tools.codex]",
                'recipe_path = "tests/fixtures/agents/brains/brain-recipes/codex/interactive-watch-default.yaml"',
                "",
                "[evidence]",
                "sample_interval_seconds = 0.2",
                "",
                "[semantics]",
                "settle_seconds = 1.0",
            ]
        )
        + "\n",
    )

    with pytest.raises(ValueError, match=r"\$\.presentation"):
        resolve_demo_config(repo_root=_repo_root(), config_path=config_path)


def test_resolve_demo_config_rejects_invalid_profile_structure(tmp_path: Path) -> None:
    """Unknown fields inside profile overrides should fail validation."""

    config_path = tmp_path / "invalid-profile.toml"
    _write(
        config_path,
        _default_demo_config_text() + "\n[profiles.fast_local.unexpected]\nvalue = 1\n",
    )

    with pytest.raises(ValueError, match=r"\$\.profiles\.fast_local\.unexpected"):
        resolve_demo_config(repo_root=_repo_root(), config_path=config_path)


def test_resolve_demo_config_rejects_invalid_sweep_variant(tmp_path: Path) -> None:
    """Sweep variants must declare source cadence or an explicit interval."""

    config_path = tmp_path / "invalid-sweep.toml"
    _write_demo_config_copy(
        config_path,
        replacements={"use_source_cadence = true": "use_source_cadence = false"},
    )

    with pytest.raises(ValueError, match=r"\$\.sweeps\.capture_frequency\.variants\[0\]"):
        resolve_demo_config(repo_root=_repo_root(), config_path=config_path)


def test_resolve_demo_config_accepts_required_sequence_sweep_contract(tmp_path: Path) -> None:
    """Sweep contracts may declare a repeated ordered required sequence."""

    config_path = tmp_path / "sequence-sweep.toml"
    _write(
        config_path,
        _default_demo_config_text()
        + "\n".join(
            [
                "",
                "[sweeps.capture_frequency.contracts.synthetic_sequence_case]",
                'required_sequence = ["active", "ready_interrupted", "active"]',
                'forbidden_terminal_results = ["success", "known_failure"]',
                "max_first_occurrence_drift_seconds = 2.0",
                "",
            ]
        ),
    )

    resolved = resolve_demo_config(repo_root=_repo_root(), config_path=config_path)
    contract = resolved.sweeps["capture_frequency"].contracts["synthetic_sequence_case"]

    assert contract.required_labels == ()
    assert contract.required_sequence == ("active", "ready_interrupted", "active")


def test_resolve_demo_config_rejects_invalid_cli_override() -> None:
    """Invalid CLI override fragments should fail before merge."""

    with pytest.raises(ValueError, match=r"cli_overrides"):
        resolve_demo_config(
            repo_root=_repo_root(),
            cli_overrides={"tools": {"claude": {"unexpected": "value"}}},
        )


def test_driver_validate_corpus_uses_fixtures_root_from_selected_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The driver should use config-derived fixture roots when no CLI root is provided."""

    fixtures_root = tmp_path / "alt-fixtures-root"
    config_path = tmp_path / "alternate.toml"
    _write_demo_config_copy(
        config_path,
        replacements={
            'fixtures_root = "tests/fixtures/shared_tui_tracking/recorded"': f'fixtures_root = "{fixtures_root}"',
        },
    )
    captured: dict[str, Path] = {}

    def _fake_validate_fixture_corpus(**kwargs):
        captured["fixtures_root"] = kwargs["fixtures_root"]
        return []

    monkeypatch.setattr(demo_driver, "validate_fixture_corpus", _fake_validate_fixture_corpus)

    assert (
        demo_driver.main(
            [
                "recorded-validate-corpus",
                "--demo-config",
                str(config_path),
                "--skip-video",
                "--json",
            ]
        )
        == 0
    )
    assert captured["fixtures_root"] == fixtures_root.resolve()


def test_driver_configures_shared_tui_logging_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The demo driver should expose shared tracker debug logs through one env var."""

    monkeypatch.setenv("HOUMAO_SHARED_TUI_TRACKING_LOG_LEVEL", "DEBUG")
    logging.getLogger("houmao.shared_tui_tracking").setLevel(logging.NOTSET)
    logging.getLogger("houmao.demo.shared_tui_tracking_demo_pack").setLevel(logging.NOTSET)

    demo_driver._configure_logging_from_env()

    assert logging.getLogger("houmao.shared_tui_tracking").isEnabledFor(logging.DEBUG)
    assert logging.getLogger("houmao.demo.shared_tui_tracking_demo_pack").isEnabledFor(
        logging.DEBUG
    )


def test_driver_rejects_invalid_shared_tui_log_level_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid debug-level env values should fail fast."""

    monkeypatch.setenv("HOUMAO_SHARED_TUI_TRACKING_LOG_LEVEL", "LOUD")

    with pytest.raises(ValueError, match=r"HOUMAO_SHARED_TUI_TRACKING_LOG_LEVEL"):
        demo_driver._configure_logging_from_env()


def test_inspect_live_watch_uses_selected_live_root_when_run_root_is_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Live inspection should resolve runs from the selected config-derived live root."""

    live_root = tmp_path / "alt-live-root"
    run_root = live_root / "claude" / "20260322T000000"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    _write_json(paths.watch_manifest_path, _watch_manifest(paths).to_payload())
    _write_json(
        paths.live_state_path,
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "status": "running",
            "latest_state_path": str(paths.latest_state_path),
            "stop_requested_at_utc": None,
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:00+00:00",
        },
    )
    _write_json(
        paths.latest_state_path,
        {
            "sample_id": "s000001",
            "elapsed_seconds": 0.0,
            "diagnostics_availability": "available",
            "turn_phase": "ready",
            "last_turn_result": "none",
            "last_turn_source": "none",
            "surface_accepting_input": "yes",
            "surface_editing_input": "no",
            "surface_ready_posture": "yes",
        },
    )
    config_path = tmp_path / "alternate.toml"
    _write_demo_config_copy(
        config_path,
        replacements={
            'live_root = "tmp/demo/shared-tui-tracking-demo-pack/live"': f'live_root = "{live_root}"',
        },
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.tmux_session_exists",
        lambda *, session_name: session_name == "shared-tui-claude-demo",
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.status_terminal_record",
        lambda *, run_root: {"status": "running", "run_root": str(run_root)},
    )

    payload = inspect_live_watch(
        repo_root=_repo_root(),
        demo_config=resolve_demo_config(repo_root=_repo_root(), config_path=config_path),
        run_root=None,
    )

    assert payload["run_root"] == str(run_root.resolve())


def test_inspect_live_watch_reports_recorder_disabled_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inspection should make recorder absence explicit for recorder-disabled runs."""

    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        paths.watch_manifest_path, _watch_manifest(paths, recorder_enabled=False).to_payload()
    )
    _write_json(
        paths.live_state_path,
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "status": "running",
            "latest_state_path": str(paths.latest_state_path),
            "stop_requested_at_utc": None,
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:00+00:00",
        },
    )
    _write_json(
        paths.latest_state_path,
        {
            "sample_id": "s000001",
            "elapsed_seconds": 0.0,
            "diagnostics_availability": "available",
            "turn_phase": "ready",
            "last_turn_result": "none",
            "last_turn_source": "none",
            "surface_accepting_input": "yes",
            "surface_editing_input": "no",
            "surface_ready_posture": "yes",
        },
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.tmux_session_exists",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.status_terminal_record",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("recorder status should not load")),
    )

    payload = inspect_live_watch(
        repo_root=_repo_root(),
        demo_config=_demo_config(),
        run_root=run_root,
    )

    assert payload["recorder_enabled"] is False
    assert payload["recorder_root"] is None
    assert payload["recorder_status"] is None


def test_inspect_live_watch_reports_recovered_session_liveness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inspect should report liveness from recovered ownership metadata, not only manifest names."""

    run_root = tmp_path / "live-run"
    paths = LiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    manifest = _watch_manifest(paths, recorder_enabled=False)
    _write_json(
        paths.watch_manifest_path,
        LiveWatchManifest(
            schema_version=manifest.schema_version,
            run_id=manifest.run_id,
            tool=manifest.tool,
            repo_root=manifest.repo_root,
            run_root=manifest.run_root,
            runtime_root=manifest.runtime_root,
            recipe_path=manifest.recipe_path,
            brain_home_path=manifest.brain_home_path,
            brain_manifest_path=manifest.brain_manifest_path,
            launch_helper_path=manifest.launch_helper_path,
            workdir=manifest.workdir,
            tool_session_name="manifest-tool-session",
            tool_attach_command=manifest.tool_attach_command,
            dashboard_session_name="manifest-dashboard-session",
            dashboard_attach_command=manifest.dashboard_attach_command,
            dashboard_command=manifest.dashboard_command,
            recorder_enabled=manifest.recorder_enabled,
            terminal_record_run_root=manifest.terminal_record_run_root,
            resolved_config_path=manifest.resolved_config_path,
            sample_interval_seconds=manifest.sample_interval_seconds,
            runtime_observer_interval_seconds=manifest.runtime_observer_interval_seconds,
            settle_seconds=manifest.settle_seconds,
            observed_version=manifest.observed_version,
            trace_enabled=manifest.trace_enabled,
            started_at_utc=manifest.started_at_utc,
            stopped_at_utc=manifest.stopped_at_utc,
            stop_reason=manifest.stop_reason,
        ).to_payload(),
    )
    _write_json(
        paths.live_state_path,
        {
            "schema_version": 1,
            "run_id": run_root.name,
            "run_root": str(run_root),
            "status": "running",
            "latest_state_path": str(paths.latest_state_path),
            "stop_requested_at_utc": None,
            "last_error": None,
            "updated_at_utc": "2026-03-22T00:00:00+00:00",
        },
    )
    _write_json(
        paths.latest_state_path,
        {
            "sample_id": "s000001",
            "elapsed_seconds": 0.0,
            "diagnostics_availability": "available",
            "turn_phase": "ready",
            "last_turn_result": "none",
            "last_turn_source": "none",
            "surface_accepting_input": "yes",
            "surface_editing_input": "no",
            "surface_ready_posture": "yes",
        },
    )
    recovered = ResolvedDemoOwnedResources(
        run_root=run_root.resolve(),
        ownership_path=session_ownership_path(run_root=run_root),
        ownership=None,
        recorder_run_root=None,
        owned_resources=(
            DemoOwnedResource(role="tool", session_name="recovered-tool-session"),
            DemoOwnedResource(role="dashboard", session_name="recovered-dashboard-session"),
        ),
        live_resources=(
            DemoOwnedResource(role="dashboard", session_name="recovered-dashboard-session"),
        ),
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.resolve_demo_owned_resources",
        lambda *, run_root: recovered,
    )
    monkeypatch.setattr(
        "houmao.demo.shared_tui_tracking_demo_pack.live_watch.tmux_session_exists",
        lambda *, session_name: session_name == "recovered-tool-session",
    )

    payload = inspect_live_watch(
        repo_root=_repo_root(),
        demo_config=_demo_config(),
        run_root=run_root,
    )

    assert payload["tool_session_running"] is True
    assert payload["dashboard_session_running"] is True
    assert payload["owned_resources"] == [
        {"role": "tool", "session_name": "recovered-tool-session"},
        {"role": "dashboard", "session_name": "recovered-dashboard-session"},
    ]
    assert payload["ownership_path"] == str(paths.session_ownership_path)


def test_driver_start_supports_with_recorder_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The driver should expose an explicit live-watch recorder opt-in flag."""

    captured: dict[str, object] = {}

    def _fake_start_live_watch(**kwargs):
        captured["recorder_enabled"] = kwargs["demo_config"].evidence.live_watch_recorder_enabled
        return SimpleNamespace(
            run_root=tmp_path / "live-run",
            manifest=SimpleNamespace(
                runtime_root=str(tmp_path / "live-run" / "runtime"),
                brain_home_path=str(tmp_path / "live-run" / "runtime" / "home"),
                brain_manifest_path=str(tmp_path / "live-run" / "runtime" / "manifest.yaml"),
                tool_attach_command="tmux attach-session -t tool",
                dashboard_attach_command="tmux attach-session -t dashboard",
            ),
        )

    monkeypatch.setattr(demo_driver, "start_live_watch", _fake_start_live_watch)

    assert demo_driver.main(["start", "--tool", "claude", "--with-recorder", "--json"]) == 0
    capsys.readouterr()
    assert captured["recorder_enabled"] is True


def test_driver_cleanup_command_reports_forceful_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The driver should expose the forceful cleanup command with machine-readable output."""

    captured: dict[str, object] = {}

    def _fake_cleanup_demo_run(**kwargs):
        captured["run_root"] = kwargs["run_root"]
        return {
            "run_root": str(tmp_path / "live-run"),
            "cleanup_kind": "forceful",
            "finalized_analysis": False,
            "cleaned_sessions": ["shared-tui-claude-demo"],
        }

    monkeypatch.setattr(demo_driver, "cleanup_demo_run", _fake_cleanup_demo_run)

    assert demo_driver.main(["cleanup", "--run-root", str(tmp_path / "live-run"), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert captured["run_root"] == (tmp_path / "live-run").resolve()
    assert payload["cleanup_kind"] == "forceful"
    assert payload["finalized_analysis"] is False


def test_run_recorded_capture_failure_after_tmux_launch_remains_recoverable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recorded-capture failures after tmux launch should still clean up through ownership metadata."""

    recipe_path = tmp_path / "recipe.yaml"
    _write(
        recipe_path,
        "\n".join(
            [
                "schema_version: 1",
                "name: recorded-default",
                "tool: claude",
                "skills: []",
                "config_profile: default",
                "credential_profile: personal-a-default",
            ]
        )
        + "\n",
    )
    scenario = load_scenario(
        _repo_root()
        / "scripts"
        / "demo"
        / "shared-tui-tracking-demo-pack"
        / "scenarios"
        / "claude-explicit-success.json"
    )
    run_root = tmp_path / "recorded-run"
    cleaned_sessions: list[str] = []
    recorder_stop_calls: list[Path] = []

    def _fake_build(request):
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

    class _FakeObserver:
        def __init__(self, **_kwargs) -> None:
            pass

        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

    monkeypatch.setattr(recorded_module, "build_brain_home", _fake_build)
    monkeypatch.setattr(
        recorded_module,
        "_resolve_scenario_launch",
        lambda **_kwargs: SimpleNamespace(
            settle_seconds=1.0,
            sample_interval_seconds=0.2,
            runtime_observer_interval_seconds=0.2,
            ready_timeout_seconds=45.0,
            recipe_path=recipe_path,
        ),
    )
    monkeypatch.setattr(
        recorded_module,
        "load_brain_recipe",
        lambda _path: SimpleNamespace(
            tool="claude",
            skills=[],
            config_profile="default",
            credential_profile="personal-a-default",
            mailbox=None,
            default_agent_name="claude-home",
            operator_prompt_mode=None,
        ),
    )
    monkeypatch.setattr(recorded_module, "launch_tmux_session", lambda **_kwargs: None)
    monkeypatch.setattr(
        recorded_module, "publish_demo_session_recovery_pointers", lambda **_kwargs: None
    )
    monkeypatch.setattr(recorded_module, "resolve_active_pane_id", lambda **_kwargs: "%1")
    monkeypatch.setattr(
        recorded_module,
        "detect_tool_version",
        lambda *, tool: "2.1.80" if tool == "claude" else None,
    )
    monkeypatch.setattr(
        recorded_module,
        "start_terminal_record",
        lambda **kwargs: (
            Path(kwargs["run_root"]).mkdir(parents=True, exist_ok=True),
            _write_terminal_record_manifest(
                Path(kwargs["run_root"]),
                recorder_session_name="terminal-record-recorded-run",
                target_session_name=kwargs["target_session"],
            ),
            {"status": "running", "run_root": str(kwargs["run_root"])},
        )[-1],
    )
    monkeypatch.setattr(recorded_module, "RuntimeObserver", _FakeObserver)
    monkeypatch.setattr(
        recorded_module,
        "_execute_scenario",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("drive failure")),
    )
    monkeypatch.setattr(ownership_module, "_list_tmux_session_names", lambda: ())
    monkeypatch.setattr(ownership_module, "_tmux_session_is_live", lambda _session_name: True)
    monkeypatch.setattr(
        ownership_module,
        "stop_terminal_record",
        lambda *, run_root: recorder_stop_calls.append(run_root) or {"status": "stopped"},
    )
    monkeypatch.setattr(
        ownership_module,
        "kill_tmux_session_if_exists",
        lambda *, session_name: cleaned_sessions.append(session_name),
    )

    with pytest.raises(RuntimeError, match="drive failure"):
        recorded_module.run_recorded_capture(
            repo_root=tmp_path,
            scenario=scenario,
            demo_config=_demo_config(),
            output_root=run_root,
            cleanup_session=False,
        )

    ownership = load_session_ownership(session_ownership_path(run_root=run_root))
    assert ownership is not None
    assert ownership.status == "failed"
    assert [item.role for item in ownership.owned_resources] == ["tool", "recorder"]
    assert recorder_stop_calls == [run_root / "recording"]
    assert set(cleaned_sessions) == {
        "shared-tui-claude-recorded-run",
        "terminal-record-recorded-run",
    }
    assert not (run_root / "capture_manifest.json").exists()


def test_validate_recorded_fixture_persists_selected_source_config_path(tmp_path: Path) -> None:
    """Recorded validation should persist the selected config path in resolved config artifacts."""

    fixture_root = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "shared_tui_tracking"
        / "recorded"
        / "claude"
        / "claude_explicit_success"
    )
    config_path = tmp_path / "alternate.toml"
    _write_demo_config_copy(config_path)

    validate_recorded_fixture(
        repo_root=_repo_root(),
        demo_config=resolve_demo_config(repo_root=_repo_root(), config_path=config_path),
        fixture_root=fixture_root,
        output_root=tmp_path / "recorded-validation",
        render_review_video=False,
    )

    payload = json.loads(
        (tmp_path / "recorded-validation" / "artifacts" / "resolved_demo_config.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["source_config_path"] == str(config_path.resolve())


@pytest.mark.parametrize(
    ("tool", "case_id"),
    [
        ("claude", "claude_success_interrupt_success_complex"),
        ("codex", "codex_success_interrupt_success_complex"),
    ],
)
def test_complex_recorded_fixtures_validate_without_mismatches(
    tmp_path: Path,
    tool: str,
    case_id: str,
) -> None:
    """Maintained complex fixtures should replay cleanly against committed labels."""

    fixture_root = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "shared_tui_tracking"
        / "recorded"
        / tool
        / case_id
    )

    result = validate_recorded_fixture(
        repo_root=_repo_root(),
        demo_config=_demo_config(),
        fixture_root=fixture_root,
        output_root=tmp_path / case_id,
        render_review_video=False,
    )

    assert result.comparison.mismatch_count == 0
    assert result.comparison.transition_order_matches is True


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


@pytest.mark.parametrize(
    ("tool", "case_id"),
    [
        ("claude", "claude_success_interrupt_success_complex"),
        ("codex", "codex_success_interrupt_success_complex"),
    ],
)
def test_complex_recorded_sweep_contracts_pass(
    tmp_path: Path,
    tool: str,
    case_id: str,
) -> None:
    """Complex maintained fixtures should satisfy the repeated lifecycle sweep contract."""

    fixture_root = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "shared_tui_tracking"
        / "recorded"
        / tool
        / case_id
    )

    result = run_recorded_sweep(
        repo_root=_repo_root(),
        demo_config=_demo_config(),
        sweep_name="capture_frequency",
        fixture_root=fixture_root,
        output_root=tmp_path / f"{case_id}-sweep",
    )

    source_verdict = json.loads(
        (result.run_root / "variants" / "source" / "verdict.json").read_text(encoding="utf-8")
    )

    assert source_verdict["required_sequence"] == [
        "ready_success",
        "active",
        "ready_interrupted",
        "active",
        "ready_interrupted",
        "ready_success",
    ]
    assert source_verdict["sequence_matches"] is True
    assert source_verdict["actual_terminal_result"] == "success"
    assert source_verdict["passed"] is True


def test_match_required_sequence_supports_repeated_labels() -> None:
    """Ordered sequence matching should support duplicate labels."""

    matches, missing, matched_times = _match_required_sequence(
        required_sequence=("active", "ready_interrupted", "active", "ready_interrupted"),
        transition_events=[
            ("ready", 0.0),
            ("active", 1.0),
            ("ready_interrupted", 2.0),
            ("active", 3.0),
            ("ready_interrupted", 4.0),
            ("tui_down", 5.0),
        ],
    )

    assert matches is True
    assert missing == ()
    assert matched_times == {
        "active#1": 1.0,
        "ready_interrupted#1": 2.0,
        "active#2": 3.0,
        "ready_interrupted#2": 4.0,
    }


def test_run_recorded_sweep_supports_required_sequence_contract(tmp_path: Path) -> None:
    """Sweep evaluation should enforce ordered required-sequence contracts."""

    config_path = tmp_path / "sequence-config.toml"
    _write(
        config_path,
        "\n".join(
            [
                "schema_version = 1",
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
                'operator_prompt_mode = "unattended"',
                "",
                "[tools.codex]",
                'recipe_path = "tests/fixtures/agents/brains/brain-recipes/codex/interactive-watch-default.yaml"',
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
                "[sweeps.capture_frequency]",
                'description = "Sequence-only sweep for repeated transitions."',
                'baseline_variant = "source"',
                "",
                "[[sweeps.capture_frequency.variants]]",
                'name = "source"',
                "use_source_cadence = true",
                "",
                "[sweeps.capture_frequency.contracts.claude_tui_down_after_active]",
                'required_sequence = ["active", "tui_down"]',
                'forbidden_terminal_results = ["success"]',
                "max_first_occurrence_drift_seconds = 2.0",
            ]
        )
        + "\n",
    )
    fixture_root = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "shared_tui_tracking"
        / "recorded"
        / "claude"
        / "claude_tui_down_after_active"
    )

    result = run_recorded_sweep(
        repo_root=_repo_root(),
        demo_config=resolve_demo_config(repo_root=_repo_root(), config_path=config_path),
        sweep_name="capture_frequency",
        fixture_root=fixture_root,
        output_root=tmp_path / "sweep-sequence-run",
    )

    verdict = json.loads(
        (result.run_root / "variants" / "source" / "verdict.json").read_text(encoding="utf-8")
    )

    assert result.outcome_count == 1
    assert verdict["required_sequence"] == ["active", "tui_down"]
    assert verdict["sequence_matches"] is True
    assert verdict["passed"] is True


def test_run_recorded_sweep_persists_selected_source_config_path(tmp_path: Path) -> None:
    """Recorded sweep should persist the selected config path in resolved config artifacts."""

    fixture_root = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "shared_tui_tracking"
        / "recorded"
        / "claude"
        / "claude_explicit_success"
    )
    config_path = tmp_path / "alternate.toml"
    _write_demo_config_copy(config_path)

    run_recorded_sweep(
        repo_root=_repo_root(),
        demo_config=resolve_demo_config(repo_root=_repo_root(), config_path=config_path),
        sweep_name="capture_frequency",
        fixture_root=fixture_root,
        output_root=tmp_path / "sweep-run",
    )

    payload = json.loads(
        (tmp_path / "sweep-run" / "artifacts" / "resolved_demo_config.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["source_config_path"] == str(config_path.resolve())
