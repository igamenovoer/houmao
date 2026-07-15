from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.shadow_parser_stack import ShadowParserStack
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError, TmuxPaneRecord
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
    derive_terminal_record_stream,
    parse_asciinema_cast_input_events,
    resolve_terminal_record_target,
    start_terminal_record,
    status_terminal_record,
    stop_terminal_record,
    validate_terminal_record,
)


def _target() -> TerminalRecordTarget:
    return TerminalRecordTarget(
        session_name="HOUMAO-gpu",
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
        target_session_name="HOUMAO-gpu",
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
        "resolve_tmux_pane_shared",
        lambda *, session_name, pane_id: (_ for _ in ()).throw(
            TmuxCommandError(
                f"Ambiguous tmux pane target for `{session_name}`: 2 panes matched; "
                "provide pane_id, window_id, window_index, or window_name."
            )
        ),
    )

    with pytest.raises(TerminalRecordError, match="multiple panes; provide --target-pane"):
        resolve_terminal_record_target(target_session="HOUMAO-gpu", target_pane=None)


def test_resolve_terminal_record_target_accepts_explicit_pane_in_non_current_window(
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
        "resolve_tmux_pane_shared",
        lambda *, session_name, pane_id: TmuxPaneRecord(
            pane_id=pane_id or "%9",
            session_name=session_name,
            window_id="@9",
            window_index="2",
            window_name="gateway",
            pane_index="0",
            pane_active=False,
            pane_dead=False,
            pane_pid=4242,
        ),
    )

    target = resolve_terminal_record_target(target_session="HOUMAO-gpu", target_pane="%9")

    assert target == TerminalRecordTarget(
        session_name="HOUMAO-gpu",
        pane_id="%9",
        window_id="@9",
        window_name="gateway",
    )


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
        target_session="HOUMAO-gpu",
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


def test_start_terminal_record_accepts_kimi_tool_and_duration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "kimi-run-001"

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

    monkeypatch.setattr(terminal_record_service, "ensure_tmux_available", lambda: None)
    monkeypatch.setattr(terminal_record_service, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        terminal_record_service,
        "resolve_terminal_record_target",
        lambda *, target_session, target_pane: _target(),
    )
    monkeypatch.setattr(terminal_record_service, "_wait_for_controller", _fake_wait)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *args, **kwargs: _DummyProcess(),
    )

    result = start_terminal_record(
        mode="passive",
        target_session="HOUMAO-kimi",
        target_pane="%1",
        tool="kimi",
        run_root=run_root,
        sample_interval_seconds=0.1,
        duration_seconds=12.5,
    )

    manifest = load_manifest(run_root / "manifest.json")
    assert result["status"] == "running"
    assert manifest.tool == "kimi"
    assert manifest.sample_interval_seconds == 0.1
    assert manifest.duration_seconds == 12.5


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
    assert "attach-session -d -t HOUMAO-gpu" in active_command
    assert "select-pane -t %1" in active_command

    assert "pixi run asciinema record" in passive_command
    assert "--capture-input" not in passive_command
    assert "attach-session -r -t HOUMAO-gpu" in passive_command


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
    monkeypatch.setattr(
        terminal_record_service,
        "_target_pane_dimensions",
        lambda *, target: (120, 40),
    )

    controller._capture_snapshot()
    controller._capture_snapshot()

    snapshots = _read_ndjson(paths.pane_snapshots_path)
    assert [item["sample_id"] for item in snapshots] == ["s000001", "s000002"]
    assert [item["output_text"] for item in snapshots] == ["first frame", "second frame"]
    assert snapshots[0]["target_pane_width"] == 120
    assert snapshots[0]["target_pane_height"] == 40
    assert snapshots[0]["capture_command"] == "tmux capture-pane -p -e -S -"
    assert snapshots[0]["stream_kind"] == "source"
    assert snapshots[0]["output_text_sha256"] is not None


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

    assert calls == ["capture", "stop", "merge", "clear:HOUMAO-gpu"]
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
    assert state_payload["surface_pending_input"] == "no"
    assert state_payload["turn_phase"] == "ready"
    assert state_payload["last_turn_result"] == "none"
    assert state_payload["last_turn_source"] == "none"
    assert state_payload["readiness_state"] == "ready"
    assert state_payload["completion_state"] == "inactive"
    assert state_payload["sample_id"] == "s000001"


def test_analyze_terminal_record_accepts_experimental_detector_override(tmp_path: Path) -> None:
    run_root = tmp_path / "run-codex-experimental"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="codex")
    paths.pane_snapshots_path.write_text(
        json.dumps(
            {
                "sample_id": "s000001",
                "elapsed_seconds": 0.0,
                "ts_utc": "2026-07-13T00:00:00+00:00",
                "target_pane_id": "%1",
                "output_text": "• Waiting for Robie [explorer]\n\n› \n",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    analyze_terminal_record(
        run_root=run_root,
        tool=None,
        observed_version="0.144.1",
        detector_version_override="0.144.x",
    )

    state_payload = _read_ndjson(paths.state_observed_path)[0]
    assert state_payload["detector_version"] == "0.144.x"
    assert state_payload["turn_phase"] == "active"


def test_analyze_terminal_record_accepts_kimi_snapshots(tmp_path: Path) -> None:
    run_root = tmp_path / "run-kimi-analyze"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="kimi")
    fixture_text = (
        "╭────────────────────╮\n"
        "│ >                  │\n"
        "╰────────────────────╯\n"
        "Kimi-k2.6 thinking  /model: switch model\n"
        "context: 0.0%\n"
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

    assert result["tool"] == "kimi"
    assert parser_payload["business_state"] == "idle"
    assert parser_payload["input_mode"] == "freeform"
    assert parser_payload["ui_context"] == "normal_prompt"
    assert parser_payload["footer_model_thinking"] is True
    assert state_payload["detector_name"] == "kimi_code"


def test_analyze_terminal_record_selects_versioned_kimi_profile(tmp_path: Path) -> None:
    run_root = tmp_path / "recording"
    paths = _write_run_artifacts(
        run_root=run_root,
        mode="passive",
        status="stopped",
        tool="kimi",
    )
    output_text = (
        "🌗 · Tip: ctrl+s: steer mid-turn\n\n"
        "● Finished.\n\n"
        "╭────────────────────────────────────────╮\n"
        "│ >                                      │\n"
        "╰────────────────────────────────────────╯\n"
        "auto  kimi-for-coding-highspeed thinking\n"
    )
    paths.pane_snapshots_path.write_text(
        json.dumps(
            {
                "sample_id": "s000001",
                "elapsed_seconds": 0.0,
                "ts_utc": "2026-07-11T00:00:00+00:00",
                "target_pane_id": "%1",
                "output_text": output_text,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    analyze_terminal_record(run_root=run_root, tool=None, observed_version="0.23.4")

    state_payload = _read_ndjson(paths.state_observed_path)[0]
    assert state_payload["detector_version"] == "0.23.x"
    assert state_payload["turn_phase"] == "ready"
    assert state_payload["surface_accepting_input"] == "yes"
    assert state_payload["surface_ready_posture"] == "yes"
    assert state_payload["surface_pending_input"] == "no"
    assert state_payload["turn_phase"] == "ready"


def test_derive_terminal_record_stream_preserves_source_mapping(tmp_path: Path) -> None:
    run_root = tmp_path / "run-derive"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="kimi")
    rows = []
    for index in range(10):
        rows.append(
            {
                "sample_id": f"s{index + 1:06d}",
                "elapsed_seconds": index / 10,
                "ts_utc": "2026-03-19T00:00:00+00:00",
                "target_pane_id": "%1",
                "output_text": f"frame {index + 1}",
            }
        )
    paths.pane_snapshots_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = derive_terminal_record_stream(run_root=run_root, target_sample_interval_seconds=0.5)
    derived_rows = _read_ndjson(paths.derived_2fps_snapshots_path)

    assert result["derived_sample_count"] == 3
    assert [item["sample_id"] for item in derived_rows] == ["d000001", "d000002", "d000003"]
    assert [item["source_sample_id"] for item in derived_rows] == [
        "s000001",
        "s000006",
        "s000010",
    ]
    assert all(item["stream_kind"] == "derived" for item in derived_rows)


def test_derive_terminal_record_stream_supports_deterministic_irregular_schedules(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-irregular-derive"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="kimi")
    rows = [
        {
            "sample_id": f"s{index + 1:06d}",
            "elapsed_seconds": index / 20,
            "ts_utc": "2026-07-11T00:00:00+00:00",
            "target_pane_id": "%1",
            "output_text": f"frame {index + 1}",
        }
        for index in range(101)
    ]
    paths.pane_snapshots_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    source_sequences: dict[str, list[str]] = {}
    for mode in ("jitter", "drop", "burst"):
        output_path = run_root / f"pane_snapshots_{mode}.ndjson"
        result = derive_terminal_record_stream(
            run_root=run_root,
            output_path=output_path,
            target_sample_interval_seconds=0.5,
            sampling_mode=mode,
            seed=17,
        )
        derived_rows = _read_ndjson(output_path)
        source_sequences[mode] = [str(item["source_sample_id"]) for item in derived_rows]
        assert result["sampling_mode"] == mode
        assert all(item["source_elapsed_seconds"] is not None for item in derived_rows)

    repeated_path = run_root / "pane_snapshots_jitter_repeat.ndjson"
    derive_terminal_record_stream(
        run_root=run_root,
        output_path=repeated_path,
        target_sample_interval_seconds=0.5,
        sampling_mode="jitter",
        seed=17,
    )
    assert source_sequences["jitter"] == [
        str(item["source_sample_id"]) for item in _read_ndjson(repeated_path)
    ]
    assert source_sequences["burst"] != source_sequences["drop"]


def test_derive_terminal_record_stream_supports_required_fixed_cadences(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-fixed-cadences"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="kimi")
    rows = [
        {
            "sample_id": f"s{index + 1:06d}",
            "elapsed_seconds": index / 20,
            "ts_utc": "2026-07-11T00:00:00+00:00",
            "target_pane_id": "%1",
            "output_text": f"frame {index + 1}",
        }
        for index in range(101)
    ]
    source_payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
    paths.pane_snapshots_path.write_text(source_payload, encoding="utf-8")

    for hz, expected_count in ((10, 51), (5, 26), (2, 11)):
        output_path = run_root / f"pane_snapshots_{hz}hz.ndjson"
        result = derive_terminal_record_stream(
            run_root=run_root,
            output_path=output_path,
            target_sample_interval_seconds=1.0 / hz,
        )
        assert result["derived_sample_count"] == expected_count
        assert all(row["source_sample_id"] for row in _read_ndjson(output_path))

    assert paths.pane_snapshots_path.read_text(encoding="utf-8") == source_payload


def test_validate_terminal_record_compares_labels_to_observed_state(tmp_path: Path) -> None:
    run_root = tmp_path / "run-validate"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="kimi")
    paths.state_observed_path.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in [
                {
                    "sample_id": "s000001",
                    "elapsed_seconds": 0.0,
                    "source_sample_id": None,
                    "diagnostics_availability": "available",
                    "surface_accepting_input": "yes",
                    "surface_editing_input": "no",
                    "surface_ready_posture": "yes",
                    "surface_pending_input": "no",
                    "turn_phase": "ready",
                    "last_turn_result": "none",
                    "last_turn_source": "none",
                    "business_state": "idle",
                    "input_mode": "freeform",
                    "ui_context": "normal_prompt",
                },
                {
                    "sample_id": "s000002",
                    "elapsed_seconds": 0.1,
                    "source_sample_id": None,
                    "diagnostics_availability": "available",
                    "surface_accepting_input": "no",
                    "surface_editing_input": "no",
                    "surface_ready_posture": "no",
                    "surface_pending_input": "no",
                    "turn_phase": "active",
                    "last_turn_result": "none",
                    "last_turn_source": "surface_inference",
                    "business_state": "working",
                    "input_mode": "none",
                    "ui_context": "normal_prompt",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths.parser_observed_path.write_text("", encoding="utf-8")
    add_terminal_record_label(
        run_root=run_root,
        output_dir=None,
        label_id="ready",
        sample_id="s000001",
        sample_end_id=None,
        scenario_id="kimi-validation",
        expectations={
            "diagnostics_availability": "available",
            "surface_pending_input": "no",
            "turn_phase": "ready",
            "business_state": "idle",
        },
        note="ready editor",
        evidence={"notes": ["editor box and empty prompt"]},
    )

    result = validate_terminal_record(run_root=run_root)

    assert result["passed"] is True
    assert result["failure_count"] == 0
    assert result["checked_sample_count"] == 1


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
            "surface_pending_input": "unknown",
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
            "surface_pending_input": "unknown",
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
                    "surface_pending_input": "unknown",
                    "last_turn_source": "none",
                },
                note=None,
            ),
        ),
    )


def test_terminal_record_labels_require_pending_input_expectation(tmp_path: Path) -> None:
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps(
            {
                "schema_version": TERMINAL_RECORD_SCHEMA_VERSION,
                "labels": [
                    {
                        "label_id": "legacy",
                        "scenario_id": None,
                        "sample_id": "s000001",
                        "sample_end_id": None,
                        "expectations": {"turn_phase": "ready"},
                        "note": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="surface_pending_input"):
        load_labels(labels_path)
    with pytest.raises(TerminalRecordError, match="surface_pending_input"):
        add_terminal_record_label(
            run_root=tmp_path,
            output_dir=None,
            label_id="legacy",
            sample_id="s000001",
            sample_end_id=None,
            scenario_id=None,
            expectations={"turn_phase": "ready"},
            note=None,
        )


def test_validate_terminal_record_groups_pending_mismatches_by_contiguous_range(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-pending-range"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="kimi")
    paths.state_observed_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "sample_id": f"d{index:06d}",
                    "source_sample_id": f"s{index + 1:06d}",
                    "elapsed_seconds": (index - 1) * 0.5,
                    "surface_pending_input": "no",
                },
                sort_keys=True,
            )
            for index in range(1, 4)
        )
        + "\n",
        encoding="utf-8",
    )
    paths.parser_observed_path.write_text("", encoding="utf-8")
    add_terminal_record_label(
        run_root=run_root,
        output_dir=None,
        label_id="pending-span",
        sample_id="s000002",
        sample_end_id="s000004",
        scenario_id="pending-range",
        expectations={"surface_pending_input": "yes"},
        note="Audited queued span",
    )

    result = validate_terminal_record(run_root=run_root)

    assert result["passed"] is False
    assert result["failure_count"] == 3
    assert result["mismatch_ranges"] == [
        {
            "label_id": "pending-span",
            "field": "surface_pending_input",
            "expected": "yes",
            "actual": "no",
            "sample_id": "d000001",
            "sample_end_id": "d000003",
            "source_sample_id": "s000002",
            "source_sample_end_id": "s000004",
            "sample_count": 3,
        }
    ]


def test_validate_derived_stream_skips_unretained_labels_and_reports_pending_drift(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-derived-validation"
    paths = _write_run_artifacts(run_root=run_root, mode="passive", status="stopped", tool="kimi")
    rows = [
        {
            "sample_id": "d000001",
            "source_sample_id": "s000001",
            "elapsed_seconds": 0.0,
            "surface_pending_input": "no",
        },
        {
            "sample_id": "d000002",
            "source_sample_id": "s000003",
            "elapsed_seconds": 0.5,
            "surface_pending_input": "unknown",
        },
        {
            "sample_id": "d000003",
            "source_sample_id": "s000005",
            "elapsed_seconds": 1.0,
            "surface_pending_input": "yes",
        },
    ]
    paths.state_observed_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    paths.parser_observed_path.write_text("", encoding="utf-8")
    for label_id, sample_id, pending in (
        ("ready", "s000001", "no"),
        ("pending-onset", "s000003", "yes"),
        ("pending-stable", "s000005", "yes"),
        ("unretained-transition", "s000004", "no"),
    ):
        add_terminal_record_label(
            run_root=run_root,
            output_dir=None,
            label_id=label_id,
            sample_id=sample_id,
            sample_end_id=None,
            scenario_id="derived",
            expectations={"surface_pending_input": pending},
            note="Audited source label",
        )

    result = validate_terminal_record(run_root=run_root)

    assert result["skipped_unobserved_label_count"] == 1
    assert result["skipped_unobserved_labels"][0]["label_id"] == "unretained-transition"
    cadence = result["pending_cadence"]
    assert cadence["retained_sample_count"] == 3
    assert cadence["transition_drift_within_bound"] is True
    assert cadence["transition_drift"] == [
        {
            "expected_sample_id": "d000002",
            "actual_sample_id": "d000003",
            "value": "yes",
            "drift_seconds": 0.5,
            "bound_seconds": 0.5,
            "within_bound": True,
        }
    ]
    assert cadence["cadence_only_yes_no_oscillation_samples"] == []


def test_analyze_terminal_record_keeps_state_fields_consistent(tmp_path: Path) -> None:
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

    assert state_payload["diagnostics_availability"] == "available"
    assert state_payload["surface_accepting_input"] == "yes"
    assert state_payload["surface_ready_posture"] == "yes"
    assert state_payload["surface_pending_input"] == "no"
    assert state_payload["turn_phase"] == "ready"
    assert state_payload["last_turn_result"] == "none"
    assert state_payload["last_turn_source"] == "none"
    assert state_payload["readiness_state"] == "ready"
    assert state_payload["completion_state"] == "inactive"
    assert state_payload["business_state"] == assessment.business_state
    assert state_payload["input_mode"] == assessment.input_mode
    assert state_payload["ui_context"] == assessment.ui_context
