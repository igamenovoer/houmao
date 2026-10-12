"""Tracker-blind tmux driving for campaign session operations.

Implements the operation vocabulary declared in the iteration-1 session specs
(``type_text``, ``submit_text``, ``send_key``, ``wait_seconds``,
``wait_for_pattern``). Input is delivered through maintained tmux helpers and
every send is logged as a managed input event so the frozen recording keeps
authoritative input timing. No detector-owned readiness gates are used.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.backends.tmux_runtime import (
    parse_tmux_control_input,
    run_tmux,
    send_tmux_control_input,
)
from houmao.terminal_record.runtime_bridge import append_managed_control_input_for_tmux_session

_KEY_MAP = {
    "Enter": "Enter",
    "Escape": "Escape",
    "Backspace": "BSpace",
    "BSpace": "BSpace",
    "C-c": "C-c",
    "C-d": "C-d",
    "C-u": "C-u",
    "Tab": "Tab",
    "BTab": "BTab",
    "Up": "Up",
    "Down": "Down",
    "F2": "F2",
}


class DriveError(RuntimeError):
    """Raised when one drive operation cannot complete as declared."""


class TmuxDriver:
    """Drive one recorded kimi tmux pane through tracker-blind operations."""

    def __init__(
        self,
        *,
        session_name: str,
        pane_id: str,
        drive_log_path: Path,
        record_started_at_utc: str,
    ) -> None:
        """Initialize the driver for one pane of one recorded session."""

        self.m_session_name = session_name
        self.m_pane_id = pane_id
        self.m_drive_log_path = drive_log_path
        self.m_record_started_at = datetime.fromisoformat(record_started_at_utc)
        drive_log_path.parent.mkdir(parents=True, exist_ok=True)

    def run_op(self, *, case_id: str, op: dict[str, Any]) -> None:
        """Execute one expanded operation and append drive evidence."""

        kind = str(op["kind"])
        name = str(op.get("name") or kind)
        self._log(case_id=case_id, name=name, phase="started", detail=_op_detail(op))
        try:
            if kind == "type_text":
                self.type_text(str(op["text"]))
            elif kind == "submit_text":
                self.submit_text(str(op["text"]))
            elif kind == "send_key":
                self.send_key(str(op["key"]), repeat=int(op.get("repeat") or 1))
            elif kind == "wait_seconds":
                time.sleep(float(op["seconds"]))
            elif kind == "wait_for_pattern":
                self.wait_for_pattern(
                    str(op["pattern"]), timeout_seconds=float(op.get("timeout_s") or 60)
                )
            elif kind == "wait_for_absence":
                self.wait_for_absence(
                    str(op["pattern"]), timeout_seconds=float(op.get("timeout_s") or 60)
                )
            else:
                raise DriveError(f"Unsupported expanded op kind {kind!r}")
        except Exception as exc:
            self._log(case_id=case_id, name=name, phase="failed", detail=repr(exc))
            raise
        self._log(case_id=case_id, name=name, phase="finished", detail="")

    def type_text(self, text: str) -> None:
        """Type literal text without submitting."""

        segments = parse_tmux_control_input(sequence=text, escape_special_keys=True)
        send_tmux_control_input(target=self.m_pane_id, segments=segments)
        self._log_input(sequence=f"literal:{text[:80]}")

    def submit_text(self, text: str) -> None:
        """Type literal text and press Enter with the kimi Enter pre-delay."""

        self.type_text(text)
        time.sleep(0.15)
        self._send_special("Enter")
        self._log_input(sequence="<[Enter]>")

    def send_key(self, key: str, *, repeat: int = 1) -> None:
        """Send one named key, ``repeat`` times, with managed-input logging."""

        tmux_key = _KEY_MAP.get(key)
        if tmux_key is None:
            if len(key) == 1:
                for _ in range(repeat):
                    send_tmux_control_input(
                        target=self.m_pane_id,
                        segments=parse_tmux_control_input(sequence=key, escape_special_keys=True),
                    )
                    self._log_input(sequence=f"literal:{key}")
                    time.sleep(0.05)
                return
            raise DriveError(f"Unsupported key name {key!r}")
        for _ in range(repeat):
            if tmux_key == "Enter":
                time.sleep(0.15)
            self._send_special(tmux_key)
            self._log_input(sequence=f"<[{tmux_key}]>")
            if repeat > 1:
                time.sleep(0.05)

    def wait_for_pattern(self, pattern: str, *, timeout_seconds: float) -> None:
        """Poll the plain visible pane for one documented literal pattern."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            capture = run_tmux(["capture-pane", "-p", "-t", self.m_pane_id])
            if capture.returncode == 0 and pattern in capture.stdout:
                return
            time.sleep(0.4)
        raise DriveError(f"Pattern {pattern!r} not visible within {timeout_seconds}s")

    def wait_for_absence(self, pattern: str, *, timeout_seconds: float) -> None:
        """Poll the plain visible pane until one documented pattern disappears."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            capture = run_tmux(["capture-pane", "-p", "-t", self.m_pane_id])
            if capture.returncode == 0 and pattern not in capture.stdout:
                return
            time.sleep(0.4)
        raise DriveError(f"Pattern {pattern!r} still visible after {timeout_seconds}s")

    def capture_visible_text(self) -> str:
        """Return the current plain visible pane text (diagnostics only)."""

        capture = run_tmux(["capture-pane", "-p", "-t", self.m_pane_id])
        return capture.stdout if capture.returncode == 0 else ""

    def _send_special(self, tmux_key: str) -> None:
        """Send one special key name through tmux send-keys."""

        result = run_tmux(["send-keys", "-t", self.m_pane_id, tmux_key])
        if result.returncode != 0:
            raise DriveError(f"tmux send-keys {tmux_key} failed: {result.stderr.strip()}")

    def _log_input(self, *, sequence: str) -> None:
        """Append one managed input event to the active recorder, when present."""

        append_managed_control_input_for_tmux_session(
            session_name=self.m_session_name,
            sequence=sequence,
            escape_special_keys=False,
            tmux_target=self.m_pane_id,
        )

    def _log(self, *, case_id: str, name: str, phase: str, detail: str) -> None:
        """Append one drive-event row correlated to recorder elapsed time."""

        elapsed = max((datetime.now(UTC) - self.m_record_started_at).total_seconds(), 0.0)
        row = {
            "case_id": case_id,
            "op_name": name,
            "phase": phase,
            "elapsed_seconds": round(elapsed, 3),
            "ts_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "detail": detail,
        }
        with self.m_drive_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _op_detail(op: dict[str, Any]) -> str:
    """Render a compact non-secret op summary for the drive log."""

    parts = [f"kind={op['kind']}"]
    if op.get("meaning"):
        parts.append(f"meaning={op['meaning']}")
    if op.get("catalog_ref"):
        parts.append(f"ref={op['catalog_ref']}")
    if op["kind"] in {"wait_for_pattern", "wait_for_absence"}:
        parts.append(f"pattern={op.get('pattern')!r}")
    if op["kind"] == "wait_seconds":
        parts.append(f"seconds={op.get('seconds')}")
    return "; ".join(str(part) for part in parts)
