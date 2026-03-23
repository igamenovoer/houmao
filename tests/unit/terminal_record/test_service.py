from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.shadow_parser_stack import ShadowParserStack
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxPaneRecord
from houmao.demo.cao_dual_shadow_watch.models import AgentSessionState, MonitorObservation
from houmao.demo.cao_dual_shadow_watch.monitor import AgentStateTracker
from houmao.terminal_record import service as terminal_record_service
from houmao.terminal_record.models import (
    DEFAULT_SAMPLE_INTERVAL_SECONDS,
    TERMINAL_RECORD_SCHEMA_VERSION,
    TerminalRecordLabel,
    TerminalRecordLabels,
    TerminalRecordLiveState,
    TerminalRecordManifest,
    TerminalRecordPaths,
    TerminalRecordTarget,
    load_labels,
    load_live_state,
    load_manifest,
    now_utc_iso,
    save_live_state,
    save_manifest,
)
from houmao.terminal_record.service import (
    TerminalRecordController,
    TerminalRecordError,
    _build_recorder_shell_command,
    add_terminal_record_label,
    analyze_terminal_record,
    parse_asciinema_cast_input_events,
    resolve_terminal_record_target,
    start_terminal_record,
    status_terminal_record,
    stop_terminal_record,
)


def _target() -> TerminalRecordTarget:
    return TerminalRecordTarget(
        session_name="AGENTSYS-gpu",
        pane_id="%1",
        window_id="@2",
        window_name="developer-1",
    )


def _manifest(
    *,
    run_root: Path,
    mode: str = "active",
    tool: str | None = "codex",
    input_capture_level: str | None = None,
) -> TerminalRecordManifest:
    capture_level = input_capture_level or (
        "authoritative_managed" if mode == "active" else "output_only"
    )
    return TerminalRecordManifest(
        schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
        run_id=run_root.name,
        mode=mode,
        repo_root=str(run_root.parent),
        run_root=str(run_root),
        target=_target(),
        tool=tool,
        sample_interval_seconds=DEFAULT_SAMPLE_INTERVAL_SECONDS,
        visual_recording_kind=("interactive_client" if mode == "active" else "readonly_observer"),
        input_capture_level=capture_level,
        run_tainted=False,
        taint_reasons=(),
        recorder_session_name=f"HMREC-{run_root.name}",
        attach_command=(
            f"env -u TMUX tmux attach-session -t HMREC-{run_root.name}"
            if mode == "active"
            else None
        ),
        started_at_utc="2026-03-19T00:00:00+00:00",
        stopped_at_utc=None,
        stop_reason=None,
    )


def _live_state(
    *, run_root: Path, mode: str = "active", status: str = "running"
) -> TerminalRecordLiveState:
    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    return TerminalRecordLiveState(
        schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
        run_id=run_root.name,
        mode=mode,
        status=status,
        repo_root=str(run_root.parent),
        run_root=str(run_root),
        manifest_path=str(paths.manifest_path),
        controller_pid=None,
        target_session_name="AGENTSYS-gpu",
        target_pane_id="%1",
        stop_requested_at_utc=None,
        last_error=None,
        updated_at_utc=now_utc_iso(),
    )


def _write_run_artifacts(
    *,
    run_root: Path,
    mode: str = "active",
    status: str = "running",
    tool: str | None = "codex",
) -> TerminalRecordPaths:
    paths = TerminalRecordPaths.from_run_root(run_root=run_root)
    save_manifest(paths.manifest_path, _manifest(run_root=run_root, mode=mode, tool=tool))
    save_live_state(paths.live_state_path, _live_state(run_root=run_root, mode=mode, status=status))
    return paths


def _read_ndjson(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _demo_session(*, tool: str, session_name: str) -> AgentSessionState:
    return AgentSessionState(
        slot="recorded",
        tool=tool,
        blueprint_path="recorded",
        brain_recipe_path="recorded",
        role_name="recorded",
        workdir="recorded",
        brain_home_path="recorded",
        brain_manifest_path="recorded",
        launch_helper_path="recorded",
        session_manifest_path="recorded",
        agent_identity="recorded",
        agent_id="recorded",
        tmux_session_name=session_name,
        cao_session_name="recorded",
        terminal_id="recorded",
        parsing_mode="shadow_only",
    )


def test_resolve_terminal_record_target_rejects_ambiguous_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        terminal_record_service,
        "has_tmux_session",
        lambda *, session_name: subprocess.CompletedProcess(
            args=["tmux", "has-session", "-t", session_name],
            returncode=0,
            stdout="",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        terminal_record_service,
        "list_tmux_panes",
        lambda *, session_name: (
            TmuxPaneRecord("%1", session_name, "@2", "developer-1", "0", True),
            TmuxPaneRecord("%2", session_name, "@2", "developer-1", "1", False),
        ),
    )

    with pytest.raises(TerminalRecordError, match="provide --target-pane"):
        resolve_terminal_record_target(target_session="AGENTSYS-gpu", target_pane=None)


def test_start_terminal_record_persists_manifest_and_attach_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-001"
    observed: dict[str, object] = {}

    class _DummyProcess:
        def __init__(self) -> None:
            self.pid = 4321

    def _fake_wait(live_state_path: Path) -> None:
        state = load_live_state(live_state_path)
        save_live_state(
            live_state_path,
            TerminalRecordLiveState(
                schema_version=state.schema_version,
                run_id=state.run_id,
                mode=state.mode,
                status="running",
                repo_root=state.repo_root,
                run_root=state.run_root,
                manifest_path=state.manifest_path,
                controller_pid=4321,
                target_session_name=state.target_session_name,
                target_pane_id=state.target_pane_id,
                stop_requested_at_utc=state.stop_requested_at_utc,
                last_error=None,
                updated_at_utc=now_utc_iso(),
            ),
        )

    def _fake_popen(
        cmd: list[str],
        *,
        cwd: Path,
        stdout: object,
        stderr: int,
        start_new_session: bool,
        text: bool,
    ) -> _DummyProcess:
        observed["cmd"] = cmd
        observed["cwd"] = cwd
        observed["stdout_name"] = getattr(stdout, "name", None)
        observed["stderr"] = stderr
        observed["start_new_session"] = start_new_session
        observed["text"] = text
        return _DummyProcess()

    monkeypatch.setattr(terminal_record_service, "ensure_tmux_available", lambda: None)
    monkeypatch.setattr(terminal_record_service, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        terminal_record_service,
        "resolve_terminal_record_target",
        lambda *, target_session, target_pane: _target(),
    )
    monkeypatch.setattr(terminal_record_service, "_wait_for_controller", _fake_wait)
    monkeypatch.setattr(subprocess, "Popen", _fake_popen)

    result = start_terminal_record(
        mode="active",
        target_session="AGENTSYS-gpu",
        target_pane=None,
        tool="codex",
        run_root=run_root,
        sample_interval_seconds=0.1,
    )

    manifest = load_manifest(run_root / "manifest.json")

    assert result["status"] == "running"
    assert result["run_root"] == str(run_root.resolve())
    assert result["attach_command"] == f"env -u TMUX tmux attach-session -t HMREC-{run_root.name}"
    assert manifest.input_capture_level == "authoritative_managed"
    assert manifest.visual_recording_kind == "interactive_client"
    assert observed["cwd"] == run_root.parent
    assert observed["stdout_name"] == str((run_root / "controller.log").resolve())
    assert observed["cmd"] == [
        os.sys.executable,
        "-m",
        "houmao.terminal_record.cli",
        "_controller-run",
        "--live-state-path",
        str((run_root / "live_state.json").resolve()),
    ]


def test_status_terminal_record_reports_controller_liveness(tmp_path: Path) -> None:
    run_root = tmp_path / "run-002"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="running")
    state = load_live_state(paths.live_state_path)
    save_live_state(
        paths.live_state_path,
        TerminalRecordLiveState(
            schema_version=state.schema_version,
            run_id=state.run_id,
            mode=state.mode,
            status=state.status,
            repo_root=state.repo_root,
            run_root=state.run_root,
            manifest_path=state.manifest_path,
            controller_pid=os.getpid(),
            target_session_name=state.target_session_name,
            target_pane_id=state.target_pane_id,
            stop_requested_at_utc=state.stop_requested_at_utc,
            last_error=state.last_error,
            updated_at_utc=state.updated_at_utc,
        ),
    )

    status = status_terminal_record(run_root=run_root)

    assert status["status"] == "running"
    assert status["controller_alive"] is True
    assert status["mode"] == "passive"
    assert status["input_capture_level"] == "output_only"


def test_stop_terminal_record_requests_orderly_shutdown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-003"
    paths = _write_run_artifacts(run_root=run_root, mode="active", status="running")

    def _fake_wait(live_state_path: Path) -> None:
        current = load_live_state(live_state_path)
        assert current.stop_requested_at_utc is not None
        save_live_state(
            live_state_path,
            TerminalRecordLiveState(
                schema_version=current.schema_version,
                run_id=current.run_id,
                mode=current.mode,
                status="stopped",
                repo_root=current.repo_root,
                run_root=current.run_root,
                manifest_path=current.manifest_path,
                controller_pid=current.controller_pid,
                target_session_name=current.target_session_name,
                target_pane_id=current.target_pane_id,
                stop_requested_at_utc=current.stop_requested_at_utc,
                last_error=None,
                updated_at_utc=now_utc_iso(),
            ),
        )
        manifest = load_manifest(paths.manifest_path)
        save_manifest(
            paths.manifest_path,
            TerminalRecordManifest(
                schema_version=manifest.schema_version,
                run_id=manifest.run_id,
                mode=manifest.mode,
                repo_root=manifest.repo_root,
                run_root=manifest.run_root,
                target=manifest.target,
                tool=manifest.tool,
                sample_interval_seconds=manifest.sample_interval_seconds,
                visual_recording_kind=manifest.visual_recording_kind,
                input_capture_level=manifest.input_capture_level,
                run_tainted=manifest.run_tainted,
                taint_reasons=manifest.taint_reasons,
                recorder_session_name=manifest.recorder_session_name,
                attach_command=manifest.attach_command,
                started_at_utc=manifest.started_at_utc,
                stopped_at_utc=now_utc_iso(),
                stop_reason="stop_requested",
            ),
        )

    monkeypatch.setattr(terminal_record_service, "_wait_for_final_status", _fake_wait)

    result = stop_terminal_record(run_root=run_root)

    assert result["status"] == "stopped"
    assert result["stop_reason"] == "stop_requested"
    assert result["run_root"] == str(run_root.resolve())


def test_build_recorder_shell_command_changes_by_mode(tmp_path: Path) -> None:
    active_manifest = _manifest(run_root=tmp_path / "active-run", mode="active")
    passive_manifest = _manifest(run_root=tmp_path / "passive-run", mode="passive")

    active_command = _build_recorder_shell_command(active_manifest)
    passive_command = _build_recorder_shell_command(passive_manifest)

    assert "pixi run asciinema record" in active_command
    assert "--capture-input" in active_command
    assert "attach-session -d -t AGENTSYS-gpu" in active_command
    assert "select-pane -t %1" in active_command

    assert "pixi run asciinema record" in passive_command
    assert "--capture-input" not in passive_command
    assert "attach-session -r -t AGENTSYS-gpu" in passive_command


def test_capture_snapshot_appends_incrementing_samples(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-004"
    paths = _write_run_artifacts(run_root=run_root, mode="active", status="running")
    controller = TerminalRecordController(live_state_path=paths.live_state_path)
    outputs = iter(["first frame", "second frame"])

    monkeypatch.setattr(
        terminal_record_service,
        "capture_tmux_pane",
        lambda *, target: next(outputs),
    )

    controller._capture_snapshot()
    controller._capture_snapshot()

    snapshots = _read_ndjson(paths.pane_snapshots_path)
    assert [item["sample_id"] for item in snapshots] == ["s000001", "s000002"]
    assert [item["output_text"] for item in snapshots] == ["first frame", "second frame"]


def test_finalize_active_controller_updates_manifest_and_live_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-005"
    paths = _write_run_artifacts(run_root=run_root, mode="active", status="running")
    controller = TerminalRecordController(live_state_path=paths.live_state_path)
    calls: list[str] = []

    monkeypatch.setattr(controller, "_capture_snapshot", lambda: calls.append("capture"))
    monkeypatch.setattr(controller, "_stop_recorder_session", lambda: calls.append("stop"))
    monkeypatch.setattr(controller, "_merge_cast_input_events", lambda: calls.append("merge"))
    monkeypatch.setattr(
        terminal_record_service,
        "clear_active_terminal_record_session",
        lambda *, session_name: calls.append(f"clear:{session_name}"),
    )

    controller._finalize(stop_reason="stop_requested")

    manifest = load_manifest(paths.manifest_path)
    live_state = load_live_state(paths.live_state_path)

    assert calls == ["capture", "stop", "merge", "clear:AGENTSYS-gpu"]
    assert manifest.stop_reason == "stop_requested"
    assert manifest.stopped_at_utc is not None
    assert live_state.status == "stopped"


def test_taint_run_degrades_active_capture_level(tmp_path: Path) -> None:
    run_root = tmp_path / "run-006"
    paths = _write_run_artifacts(run_root=run_root, mode="active", status="running")
    controller = TerminalRecordController(live_state_path=paths.live_state_path)

    controller._taint_run("multiple_clients_attached")

    manifest = load_manifest(paths.manifest_path)
    assert manifest.run_tainted is True
    assert manifest.input_capture_level == "managed_only"
    assert manifest.taint_reasons == ("multiple_clients_attached",)


def test_parse_asciinema_cast_input_events_reads_v3_input_frames(tmp_path: Path) -> None:
    cast_path = tmp_path / "session.cast"
    cast_path.write_text(
        "\n".join(
            [
                '{"version": 3, "width": 120, "height": 40, "timestamp": 1710000000}',
                '[0.125, "o", "frame"]',
                '[0.5, "i", "/model"]',
                '[0.75, "i", "\\r"]',
                '[1.0, "x", 0]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    events = parse_asciinema_cast_input_events(
        cast_path=cast_path,
        started_at_utc="2026-03-19T00:00:00+00:00",
    )

    assert [item.source for item in events] == ["asciinema_input", "asciinema_input"]
    assert [item.sequence for item in events] == ["/model", "\r"]
    assert [item.event_id for item in events] == ["i000001", "i000002"]


def test_analyze_terminal_record_emits_parser_and_state_observations(tmp_path: Path) -> None:
    run_root = tmp_path / "run-007"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="codex")
    fixture_text = Path("tests/fixtures/shadow_parser/codex/tui_completed.txt").read_text(
        encoding="utf-8"
    )
    paths.pane_snapshots_path.write_text(
        json.dumps(
            {
                "sample_id": "s000001",
                "elapsed_seconds": 0.0,
                "ts_utc": "2026-03-19T00:00:00+00:00",
                "target_pane_id": "%1",
                "output_text": fixture_text,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = analyze_terminal_record(run_root=run_root, tool=None)

    parser_payload = _read_ndjson(paths.parser_observed_path)[0]
    state_payload = _read_ndjson(paths.state_observed_path)[0]

    assert result["sample_count"] == 1
    assert parser_payload["sample_id"] == "s000001"
    assert parser_payload["business_state"] == "idle"
    assert parser_payload["input_mode"] == "freeform"
    assert parser_payload["ui_context"] == "normal_prompt"
    assert state_payload["diagnostics_availability"] == "available"
    assert state_payload["surface_accepting_input"] == "yes"
    assert state_payload["surface_ready_posture"] == "yes"
    assert state_payload["turn_phase"] == "ready"
    assert state_payload["last_turn_result"] == "none"
    assert state_payload["last_turn_source"] == "none"
    assert state_payload["readiness_state"] == "ready"
    assert state_payload["completion_state"] == "inactive"
    assert state_payload["sample_id"] == "s000001"


def test_add_terminal_record_label_writes_exportable_structured_labels(tmp_path: Path) -> None:
    run_root = tmp_path / "run-008"
    output_dir = tmp_path / "exported-fixture"
    run_root.mkdir(parents=True, exist_ok=True)

    first = add_terminal_record_label(
        run_root=run_root,
        output_dir=output_dir,
        label_id="trust-prompt-blocked",
        sample_id="s000021",
        sample_end_id=None,
        scenario_id="trust-prompt-recovery",
        expectations={
            "business_state": "awaiting_operator",
            "diagnostics_availability": "available",
            "turn_phase": "unknown",
        },
        note="Operator approval requested",
    )
    second = add_terminal_record_label(
        run_root=run_root,
        output_dir=output_dir,
        label_id="trust-prompt-blocked",
        sample_id="s000021",
        sample_end_id="s000025",
        scenario_id="trust-prompt-recovery",
        expectations={
            "business_state": "awaiting_operator",
            "surface_accepting_input": "no",
            "last_turn_source": "none",
        },
        note=None,
    )

    labels = load_labels(output_dir / "labels.json")

    assert first["label_count"] == 1
    assert second["label_count"] == 1
    assert labels == TerminalRecordLabels(
        schema_version=TERMINAL_RECORD_SCHEMA_VERSION,
        labels=(
            TerminalRecordLabel(
                label_id="trust-prompt-blocked",
                scenario_id="trust-prompt-recovery",
                sample_id="s000021",
                sample_end_id="s000025",
                expectations={
                    "business_state": "awaiting_operator",
                    "surface_accepting_input": "no",
                    "last_turn_source": "none",
                },
                note=None,
            ),
        ),
    )


def test_analyze_terminal_record_keeps_demo_tracker_as_reference_only(tmp_path: Path) -> None:
    run_root = tmp_path / "run-009"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="codex")
    fixture_text = Path("tests/fixtures/shadow_parser/codex/tui_completed.txt").read_text(
        encoding="utf-8"
    )
    paths.pane_snapshots_path.write_text(
        json.dumps(
            {
                "sample_id": "s000001",
                "elapsed_seconds": 0.0,
                "ts_utc": "2026-03-19T00:00:00+00:00",
                "target_pane_id": "%1",
                "output_text": fixture_text,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    analyze_terminal_record(run_root=run_root, tool=None)
    state_payload = _read_ndjson(paths.state_observed_path)[0]

    parser_stack = ShadowParserStack(tool="codex")
    parsed = parser_stack.parse_snapshot(fixture_text, baseline_pos=0)
    assessment = parsed.surface_assessment
    projection = parsed.dialog_projection
    tracker = AgentStateTracker(
        session=_demo_session(tool="codex", session_name=_target().session_name),
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    reference_state, _ = tracker.observe(
        MonitorObservation(
            slot="recorded",
            tool="codex",
            terminal_id=_target().pane_id,
            tmux_session_name=_target().session_name,
            cao_status="recorded",
            parser_family=parser_stack.parser_family,
            parser_preset_id=assessment.parser_metadata.parser_preset_id,
            parser_preset_version=assessment.parser_metadata.parser_preset_version,
            availability=assessment.availability,
            business_state=assessment.business_state,
            input_mode=assessment.input_mode,
            ui_context=assessment.ui_context,
            normalized_projection_text=projection.normalized_text,
            dialog_tail=projection.tail,
            operator_blocked_excerpt=assessment.operator_blocked_excerpt,
            anomaly_codes=tuple(
                anomaly.code
                for anomaly in (
                    *assessment.parser_metadata.anomalies,
                    *assessment.anomalies,
                    *projection.anomalies,
                )
            ),
            baseline_invalidated=assessment.parser_metadata.baseline_invalidated,
            monotonic_ts=0.0,
            error_detail=None,
        )
    )

    assert state_payload["readiness_state"] == reference_state.readiness_state
    assert state_payload["completion_state"] == reference_state.completion_state
