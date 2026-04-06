from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.explore.claude_code_state_tracking import cli as tracking_cli
from houmao.explore.claude_code_state_tracking.interactive_watch import (
    InteractiveWatchStartResult,
    inspect_interactive_watch,
    run_dashboard,
    start_interactive_watch,
    stop_interactive_watch,
)
from houmao.explore.claude_code_state_tracking.models import (
    InteractiveWatchLiveState,
    InteractiveWatchManifest,
    InteractiveWatchPaths,
    save_json,
)
from houmao.terminal_record.models import (
    TerminalRecordManifest,
    TerminalRecordTarget,
    save_manifest,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_preset(path: Path) -> None:
    _write(
        path,
        "\n".join(
            [
                "role: interactive-watch",
                "tool: claude",
                "setup: default",
                "skills:",
                "  - openspec-explore",
                "auth: personal-a-default",
                "launch:",
                "  prompt_mode: unattended",
            ]
        )
        + "\n",
    )


def _mock_terminal_record_start(paths: InteractiveWatchPaths) -> dict[str, str]:
    paths.terminal_record_run_root.mkdir(parents=True, exist_ok=True)
    _write(paths.terminal_record_run_root / "live_state.json", "{}\n")
    return {"run_root": str(paths.terminal_record_run_root)}


def _watch_manifest(paths: InteractiveWatchPaths) -> InteractiveWatchManifest:
    return InteractiveWatchManifest(
        schema_version=1,
        run_id=paths.run_root.name,
        repo_root="/repo",
        run_root=str(paths.run_root),
        runtime_root=str(paths.runtime_root),
        preset_path="/repo/tests/fixtures/agents/presets/interactive-watch-claude-default.yaml",
        brain_home_path=str(paths.runtime_root / "homes" / "claude-home"),
        brain_manifest_path=str(paths.runtime_root / "manifests" / "claude-home.yaml"),
        launch_helper_path=str(paths.runtime_root / "homes" / "claude-home" / "launch.sh"),
        workdir=str(paths.workdir),
        claude_session_name="claude-watch-session",
        claude_attach_command="tmux attach-session -t claude-watch-session",
        dashboard_session_name="claude-watch-dashboard",
        dashboard_attach_command="tmux attach-session -t claude-watch-dashboard",
        dashboard_command="pixi run python scripts/explore/claude-code-state-tracking/run.py dashboard --run-root /tmp/run",
        terminal_record_run_root=str(paths.terminal_record_run_root),
        sample_interval_seconds=0.2,
        settle_seconds=1.0,
        observed_version="2.1.80 (Claude Code)",
        trace_enabled=False,
        started_at_utc="2026-03-20T00:00:00+00:00",
        stopped_at_utc=None,
        stop_reason=None,
    )


def _watch_live_state(
    paths: InteractiveWatchPaths, *, status: str, stop_requested: bool = False
) -> InteractiveWatchLiveState:
    return InteractiveWatchLiveState(
        schema_version=1,
        run_id=paths.run_root.name,
        run_root=str(paths.run_root),
        status=status,  # type: ignore[arg-type]
        latest_state_path=str(paths.latest_state_path),
        stop_requested_at_utc="2026-03-20T00:00:10+00:00" if stop_requested else None,
        last_error=None,
        updated_at_utc="2026-03-20T00:00:00+00:00",
    )


def _save_watch_files(
    paths: InteractiveWatchPaths, *, status: str = "running", stop_requested: bool = False
) -> None:
    save_json(paths.watch_manifest_path, _watch_manifest(paths).to_payload())
    save_json(
        paths.live_state_path,
        _watch_live_state(paths, status=status, stop_requested=stop_requested).to_payload(),
    )


def _save_terminal_record_manifest(paths: InteractiveWatchPaths) -> None:
    manifest = TerminalRecordManifest(
        schema_version=1,
        run_id=paths.terminal_record_run_root.name,
        mode="passive",
        repo_root="/repo",
        run_root=str(paths.terminal_record_run_root),
        target=TerminalRecordTarget(
            session_name="claude-watch-session",
            pane_id="%1",
            window_id="@1",
            window_name="claude",
        ),
        tool="claude",
        sample_interval_seconds=0.2,
        visual_recording_kind="readonly_observer",
        input_capture_level="output_only",
        run_tainted=False,
        taint_reasons=(),
        recorder_session_name="terminal-record-session",
        attach_command=None,
        started_at_utc="2026-03-20T00:00:00+00:00",
        stopped_at_utc="2026-03-20T00:00:05+00:00",
        stop_reason="operator_requested",
    )
    save_manifest(
        Path(paths.terminal_record_run_root) / "manifest.json",
        manifest,
    )


def test_start_interactive_watch_builds_run_local_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset_path = tmp_path / "presets" / "interactive-watch-claude-default.yaml"
    _write_preset(preset_path)
    requested: dict[str, object] = {}

    def _fake_build(request):
        requested["runtime_root"] = request.runtime_root
        requested["launch_overrides"] = request.launch_overrides
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
        "houmao.explore.claude_code_state_tracking.interactive_watch.build_brain_home",
        _fake_build,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.launch_tmux_session",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.resolve_active_pane_id",
        lambda **_kwargs: "%1",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.start_terminal_record",
        lambda **_kwargs: {"run_root": str(tmp_path / "terminal-record")},
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.detect_claude_version",
        lambda: "2.1.80 (Claude Code)",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch._wait_for_dashboard_running",
        lambda **_kwargs: None,
    )

    run_root = tmp_path / "interactive-run"
    result = start_interactive_watch(
        repo_root=tmp_path,
        output_root=run_root,
        preset_path=preset_path,
        sample_interval_seconds=0.25,
        settle_seconds=1.5,
        trace_enabled=True,
    )

    manifest_payload = json.loads(
        (run_root / "artifacts" / "interactive_watch_manifest.json").read_text(encoding="utf-8")
    )
    dashboard_script = (run_root / "logs" / "dashboard_launch.sh").read_text(encoding="utf-8")
    assert result.run_root == run_root
    assert requested["runtime_root"] == run_root / "runtime"
    assert requested["launch_overrides"].to_payload() == {
        "args": {
            "mode": "replace",
            "values": ["--dangerously-skip-permissions"],
        }
    }
    assert manifest_payload["runtime_root"] == str(run_root / "runtime")
    assert manifest_payload["brain_home_path"].startswith(str(run_root / "runtime"))
    assert "exec bash -lc" in dashboard_script


def test_start_interactive_watch_cleans_up_after_dashboard_start_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset_path = tmp_path / "presets" / "interactive-watch-claude-default.yaml"
    _write_preset(preset_path)
    run_root = tmp_path / "interactive-run"
    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    cleaned_sessions: list[str] = []
    recorder_stop_calls: list[Path] = []

    def _fake_build(_request):
        home_path = paths.runtime_root / "homes" / "claude-home"
        manifest_path = paths.runtime_root / "manifests" / "claude-home.yaml"
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
        "houmao.explore.claude_code_state_tracking.interactive_watch.build_brain_home",
        _fake_build,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.launch_tmux_session",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.resolve_active_pane_id",
        lambda **_kwargs: "%1",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.start_terminal_record",
        lambda **_kwargs: _mock_terminal_record_start(paths),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.stop_terminal_record",
        lambda *, run_root: recorder_stop_calls.append(run_root) or {"status": "stopped"},
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.detect_claude_version",
        lambda: "2.1.80 (Claude Code)",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch._wait_for_dashboard_running",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("dashboard failed")),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.tmux_session_exists",
        lambda *, session_name: True,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.cleanup_tmux_session",
        lambda *, session_name: cleaned_sessions.append(session_name),
    )

    with pytest.raises(RuntimeError, match="dashboard failed"):
        start_interactive_watch(
            repo_root=tmp_path,
            output_root=run_root,
            preset_path=preset_path,
            sample_interval_seconds=0.25,
            settle_seconds=1.5,
            trace_enabled=True,
        )

    live_state_payload = json.loads(paths.live_state_path.read_text(encoding="utf-8"))
    assert recorder_stop_calls == [paths.terminal_record_run_root]
    assert set(cleaned_sessions) == {
        "cc-track-watch-interactive-run",
        "cc-track-dashboard-interactive-run",
        "HMREC-terminal-record-interactive-run",
    }
    assert live_state_payload["status"] == "failed"
    assert live_state_payload["last_error"] == "dashboard failed"


def test_start_interactive_watch_cleans_up_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset_path = tmp_path / "presets" / "interactive-watch-claude-default.yaml"
    _write_preset(preset_path)
    run_root = tmp_path / "interactive-run"
    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    cleaned_sessions: list[str] = []
    recorder_stop_calls: list[Path] = []

    def _fake_build(_request):
        home_path = paths.runtime_root / "homes" / "claude-home"
        manifest_path = paths.runtime_root / "manifests" / "claude-home.yaml"
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
        "houmao.explore.claude_code_state_tracking.interactive_watch.build_brain_home",
        _fake_build,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.launch_tmux_session",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.resolve_active_pane_id",
        lambda **_kwargs: "%1",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.start_terminal_record",
        lambda **_kwargs: _mock_terminal_record_start(paths),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.stop_terminal_record",
        lambda *, run_root: recorder_stop_calls.append(run_root) or {"status": "stopped"},
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.detect_claude_version",
        lambda: "2.1.80 (Claude Code)",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch._wait_for_dashboard_running",
        lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.tmux_session_exists",
        lambda *, session_name: True,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.cleanup_tmux_session",
        lambda *, session_name: cleaned_sessions.append(session_name),
    )

    with pytest.raises(KeyboardInterrupt):
        start_interactive_watch(
            repo_root=tmp_path,
            output_root=run_root,
            preset_path=preset_path,
            sample_interval_seconds=0.25,
            settle_seconds=1.5,
            trace_enabled=True,
        )

    live_state_payload = json.loads(paths.live_state_path.read_text(encoding="utf-8"))
    assert recorder_stop_calls == [paths.terminal_record_run_root]
    assert set(cleaned_sessions) == {
        "cc-track-watch-interactive-run",
        "cc-track-dashboard-interactive-run",
        "HMREC-terminal-record-interactive-run",
    }
    assert live_state_payload["status"] == "failed"
    assert live_state_payload["last_error"] == "KeyboardInterrupt"


def test_start_interactive_watch_falls_back_to_direct_recorder_session_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset_path = tmp_path / "presets" / "interactive-watch-claude-default.yaml"
    _write_preset(preset_path)
    run_root = tmp_path / "interactive-run"
    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    cleaned_sessions: list[str] = []

    def _fake_build(_request):
        home_path = paths.runtime_root / "homes" / "claude-home"
        manifest_path = paths.runtime_root / "manifests" / "claude-home.yaml"
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
        "houmao.explore.claude_code_state_tracking.interactive_watch.build_brain_home",
        _fake_build,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.launch_tmux_session",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.resolve_active_pane_id",
        lambda **_kwargs: "%1",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.start_terminal_record",
        lambda **_kwargs: _mock_terminal_record_start(paths),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.stop_terminal_record",
        lambda *, run_root: (_ for _ in ()).throw(RuntimeError("stop failed")),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.detect_claude_version",
        lambda: "2.1.80 (Claude Code)",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch._wait_for_dashboard_running",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("dashboard failed")),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.tmux_session_exists",
        lambda *, session_name: True,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.cleanup_tmux_session",
        lambda *, session_name: cleaned_sessions.append(session_name),
    )

    with pytest.raises(RuntimeError, match="dashboard failed"):
        start_interactive_watch(
            repo_root=tmp_path,
            output_root=run_root,
            preset_path=preset_path,
            sample_interval_seconds=0.25,
            settle_seconds=1.5,
            trace_enabled=True,
        )

    assert "HMREC-terminal-record-interactive-run" in cleaned_sessions


def test_inspect_interactive_watch_returns_latest_state_and_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / "interactive-run"
    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    _save_watch_files(paths)
    save_json(
        paths.latest_state_path,
        {
            "turn_phase": "ready",
            "last_turn_result": "success",
            "last_turn_source": "surface_inference",
            "diagnostics_availability": "available",
        },
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.tmux_session_exists",
        lambda *, session_name: session_name == "claude-watch-session",
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.status_terminal_record",
        lambda *, run_root: {"status": "running", "run_root": str(run_root)},
    )

    payload = inspect_interactive_watch(repo_root=tmp_path, run_root=run_root)

    assert payload["runtime_root"] == str(run_root / "runtime")
    assert payload["claude_session_running"] is True
    assert payload["dashboard_session_running"] is False
    assert payload["latest_state"]["last_turn_result"] == "success"
    assert payload["artifact_paths"]["state_samples"] == str(paths.state_samples_path)


def test_stop_interactive_watch_finalizes_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / "interactive-run"
    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    _save_watch_files(paths)

    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.stop_terminal_record",
        lambda *, run_root: {"status": "stopped", "run_root": str(run_root)},
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch._wait_for_dashboard_stop",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch._kill_tmux_session_if_exists",
        lambda **_kwargs: None,
    )

    def _fake_replay(**_kwargs) -> None:
        save_json(
            paths.analysis_dir / "comparison.json",
            {
                "mismatch_count": 0,
                "first_divergence_sample_id": None,
                "transition_order_matches": True,
            },
        )
        (paths.analysis_dir / "comparison.md").write_text("# Comparison\n", encoding="utf-8")

    monkeypatch.setattr(tracking_cli, "_run_replay_workflow", _fake_replay)

    payload = stop_interactive_watch(repo_root=tmp_path, run_root=run_root, stop_reason="manual")

    report_text = paths.report_path.read_text(encoding="utf-8")
    live_state_payload = json.loads(paths.live_state_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(paths.watch_manifest_path.read_text(encoding="utf-8"))
    assert payload["report_path"] == str(paths.report_path)
    assert "Verdict: `passed`" in report_text
    assert live_state_payload["status"] == "stopped"
    assert manifest_payload["stop_reason"] == "manual"


def test_run_dashboard_persists_live_state_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / "interactive-run"
    paths = InteractiveWatchPaths.from_run_root(run_root=run_root)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    paths.terminal_record_run_root.mkdir(parents=True, exist_ok=True)
    _save_watch_files(paths, status="starting", stop_requested=True)
    _save_terminal_record_manifest(paths)
    snapshot_path = paths.terminal_record_run_root / "pane_snapshots.ndjson"
    snapshot_path.write_text(
        json.dumps(
            {
                "sample_id": "s000001",
                "elapsed_seconds": 0.5,
                "ts_utc": "2026-03-20T00:00:01+00:00",
                "target_pane_id": "%1",
                "output_text": (
                    "❯ explain the repository carefully\n\n"
                    "✢ Unfurling…\n\n"
                    "────────────────────────────────────────────────────────────────\n"
                    "❯\n"
                    "────────────────────────────────────────────────────────────────\n"
                    "  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt\n"
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch._sample_runtime_observation",
        lambda **_kwargs: SimpleNamespace(
            to_payload=lambda: {
                "ts_utc": "2026-03-20T00:00:01+00:00",
                "elapsed_seconds": 0.4,
                "session_exists": True,
                "pane_exists": True,
                "pane_dead": False,
                "pane_pid": 123,
                "pane_pid_alive": True,
                "supported_process_pid": 456,
                "supported_process_alive": True,
            }
        ),
    )
    monkeypatch.setattr(
        "houmao.explore.claude_code_state_tracking.interactive_watch.status_terminal_record",
        lambda *, run_root: {"status": "stopped", "run_root": str(run_root)},
    )

    assert run_dashboard(run_root=run_root) == 0
    assert paths.latest_state_path.is_file()
    assert paths.state_samples_path.read_text(encoding="utf-8").strip()
    assert paths.transitions_path.read_text(encoding="utf-8").strip()


def test_cli_start_prints_json_payload(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_root = tmp_path / "interactive-run"
    manifest = _watch_manifest(InteractiveWatchPaths.from_run_root(run_root=run_root))
    monkeypatch.setattr(
        tracking_cli,
        "start_interactive_watch",
        lambda **_kwargs: InteractiveWatchStartResult(run_root=run_root, manifest=manifest),
    )

    assert tracking_cli.main(["start", "--json", "--output-root", str(run_root)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_root"] == str(run_root)
    assert payload["brain_home_path"] == manifest.brain_home_path
