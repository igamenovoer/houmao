"""Tests for exact UC-02 operation compilation and capture driving."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon import capture
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.catalog import (
    expand_matrix,
    load_suite_catalog,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.operations import (
    CompiledOperation,
    compile_cell_operations,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]


def test_all_242_operations_compile_without_ad_hoc_fallback() -> None:
    """Every reviewed matrix operation compiles to a closed semantic action."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)
    plan = expand_matrix(suite=suite)
    compiled = tuple(
        operation
        for cell in plan.cells
        for operation in compile_cell_operations(
            cell=cell,
            safe_prefix=suite.safe_prefix,
            pane_id="%42",
            launch_command="/tmp/launch.sh",
        )
    )

    assert len(compiled) == 242
    assert all(
        item.action_kind in {"send_sequence", "tmux_control", "repeat_operation"}
        for item in compiled
    )
    assert not any("{{" in item.expanded_instruction for item in compiled)


def test_compiler_preserves_exact_prompt_keys_controls_and_restart() -> None:
    """Representative operations retain literal prompts and exact native controls."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)
    plan = expand_matrix(suite=suite)
    cells = {item.cell_id: item for item in plan.cells}
    st01 = compile_cell_operations(
        cell=cells["codex:st-01"],
        safe_prefix=suite.safe_prefix,
        pane_id="%9",
        launch_command="/tmp/codex-launch.sh",
    )
    st04 = compile_cell_operations(
        cell=cells["kimi:st-04"],
        safe_prefix=suite.safe_prefix,
        pane_id="%9",
        launch_command="/tmp/kimi-launch.sh",
    )
    st05 = compile_cell_operations(
        cell=cells["kimi:st-05"],
        safe_prefix=suite.safe_prefix,
        pane_id="%9",
        launch_command="/tmp/kimi-launch.sh",
    )

    assert st01[0].sequence is not None and st01[0].sequence.startswith(suite.safe_prefix)
    assert st01[2].sequence == "<[BSpace]>" * 9
    assert st01[12].action_kind == "repeat_operation"
    assert st01[12].repeat_operation_number == 11
    assert st04[6].tmux_commands == (("resize-window", "-t", "%9", "-x", "72", "-y", "24"),)
    assert st04[12].sequence == "/model<[Enter]>"
    assert st04[12].hold_after_seconds == 4.0
    assert st05[18].sequence == "<[C-d]>"
    assert st05[19].sequence == "/tmp/kimi-launch.sh<[Enter]>"
    assert st05[19].after_gate == "ready"


def test_execute_operations_persists_semantic_and_frame_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The driver correlates exact delivery, tmux control, gates, and visible frames."""

    attempt_root = tmp_path / "attempt"
    (attempt_root / "logs").mkdir(parents=True)
    sent: list[str] = []
    commands: list[list[str]] = []
    gates: list[str] = []
    monkeypatch.setattr(capture, "capture_visible_pane_text", lambda **_kwargs: "ready")
    monkeypatch.setattr(
        capture,
        "_send_recorded_sequence",
        lambda **kwargs: sent.append(str(kwargs["sequence"])),
    )
    monkeypatch.setattr(capture, "run_tmux", lambda command: commands.append(command))
    monkeypatch.setattr(
        capture,
        "_wait_for_gate",
        lambda **kwargs: gates.append(str(kwargs["gate"])) or "surface",
    )
    operations = (
        _compiled(number=1, sequence="prompt<[Enter]>", after_gate="ready"),
        _compiled(
            number=2,
            sequence=None,
            action_kind="tmux_control",
            commands=(("resize-window", "-t", "%1", "-x", "72", "-y", "24"),),
        ),
        _compiled(
            number=3,
            sequence=None,
            action_kind="repeat_operation",
            repeat_number=1,
        ),
    )

    result = capture.execute_operations(
        provider="codex",
        session_name="session",
        pane_id="%1",
        operations=operations,
        attempt_root=attempt_root,
        turn_timeout_seconds=1.0,
    )

    assert len(result) == 3
    assert sent == ["prompt<[Enter]>", "prompt<[Enter]>"]
    assert commands == [["resize-window", "-t", "%1", "-x", "72", "-y", "24"]]
    assert gates == ["ready"]
    rows = [
        json.loads(line)
        for line in (attempt_root / "expanded-operations.ndjson").read_text().splitlines()
    ]
    assert [item["event_id"] for item in rows] == ["event-1", "event-2", "event-3"]
    assert (attempt_root / "runtime/operation-frames/op-003-after.ansi.txt").is_file()


def test_confirmation_surface_aborts_operation(tmp_path: Path, monkeypatch) -> None:
    """An intervention surface fails capture before further operations are sent."""

    attempt_root = tmp_path / "attempt"
    (attempt_root / "logs").mkdir(parents=True)
    monkeypatch.setattr(
        capture,
        "capture_visible_pane_text",
        lambda **_kwargs: "Approval required: allow this command?",
    )
    monkeypatch.setattr(capture, "_send_recorded_sequence", lambda **_kwargs: None)

    with pytest.raises(capture.CaptureFailure, match="exposed intervention") as exc_info:
        capture.execute_operations(
            provider="kimi",
            session_name="session",
            pane_id="%1",
            operations=(_compiled(number=1, sequence="prompt"),),
            attempt_root=attempt_root,
            turn_timeout_seconds=1.0,
        )

    assert exc_info.value.code == "unattended_confirmation_violation"


def test_raw_active_timeout_is_stimulus_too_short(monkeypatch) -> None:
    """Missing raw active evidence is classified without inventing a prompt."""

    monkeypatch.setattr(capture, "capture_visible_pane_text", lambda **_kwargs: "ready")

    with pytest.raises(capture.CaptureFailure) as exc_info:
        capture._wait_for_gate(
            gate="active",
            provider="claude",
            pane_id="%1",
            baseline_text="ready",
            timeout_seconds=0.0,
        )

    assert exc_info.value.code == "stimulus_too_short"


def test_codex_active_requires_native_interrupt_marker() -> None:
    """A nonempty Codex editor is not mistaken for an active turn."""

    assert not capture._looks_active(provider="codex", visible_text="› unsent prompt")
    assert capture._looks_active(
        provider="codex",
        visible_text="• Working (1s • esc to interrupt)\n› queued steering",
    )


def test_codex_submit_waits_for_tui_paste_suppression(monkeypatch) -> None:
    """Codex gets a full processing delay between literal input and Enter."""

    delivered: list[str] = []
    sleeps: list[float] = []
    monkeypatch.setattr(
        capture,
        "send_tmux_control_input",
        lambda **kwargs: delivered.extend(segment.value for segment in kwargs["segments"]),
    )
    monkeypatch.setattr(
        capture, "append_managed_control_input_for_tmux_session", lambda **_kwargs: None
    )
    monkeypatch.setattr(capture.time, "sleep", sleeps.append)

    capture._send_recorded_sequence(
        provider="codex",
        session_name="session",
        pane_id="%1",
        sequence="prompt<[Enter]>",
    )

    assert delivered == ["prompt", "Enter"]
    assert sleeps == [1.0]


def _compiled(
    *,
    number: int,
    sequence: str | None,
    action_kind="send_sequence",
    commands: tuple[tuple[str, ...], ...] = (),
    repeat_number: int | None = None,
    after_gate="none",
) -> CompiledOperation:
    """Return one small compiled operation for driver tests."""

    return CompiledOperation(
        event_id=f"event-{number}",
        provider="codex",
        procedure_id="st-01",
        number=number,
        source_instruction="source",
        expanded_instruction="expanded",
        action_kind=action_kind,
        sequence=sequence,
        tmux_commands=commands,
        repeat_operation_number=repeat_number,
        before_gate="none",
        after_gate=after_gate,
        hold_after_seconds=0.0,
    )
