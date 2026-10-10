"""Runtime liveness observer for recorded campaign sessions.

Samples tmux session/pane posture and supported-process liveness at a fixed
interval into ``capture/runtime_observations.ndjson`` using the shared
``RuntimeObservation`` payload shape, so labels and replay can adjudicate
``tui_down`` from runtime evidence rather than from a quiet pane alone.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.realm_controller.backends.tmux_runtime import run_tmux


class RuntimeObserver:
    """Background sampler writing ``RuntimeObservation``-shaped rows."""

    def __init__(
        self,
        *,
        session_name: str,
        pane_id: str,
        output_path: Path,
        record_started_at_utc: str,
        process_marker: str = "kimi",
        interval_seconds: float = 1.0,
    ) -> None:
        """Initialize the observer for one recorded pane."""

        self.m_session_name = session_name
        self.m_pane_id = pane_id
        self.m_output_path = output_path
        self.m_started_at = datetime.fromisoformat(record_started_at_utc)
        self.m_process_marker = process_marker
        self.m_interval_seconds = interval_seconds
        self.m_stop = threading.Event()
        self.m_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the sampling thread."""

        self.m_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.m_thread = threading.Thread(target=self._loop, daemon=True)
        self.m_thread.start()

    def stop(self) -> None:
        """Stop sampling and join the thread."""

        self.m_stop.set()
        if self.m_thread is not None:
            self.m_thread.join(timeout=10)

    def _loop(self) -> None:
        """Sample until stopped."""

        while not self.m_stop.is_set():
            self._sample_once()
            time.sleep(self.m_interval_seconds)

    def _sample_once(self) -> None:
        """Write one runtime observation row."""

        session_exists = run_tmux(["has-session", "-t", self.m_session_name]).returncode == 0
        pane_exists = False
        pane_dead = False
        pane_pid: int | None = None
        pane_pid_alive = False
        if session_exists:
            panes = run_tmux(
                [
                    "list-panes",
                    "-t",
                    self.m_session_name,
                    "-F",
                    "#{pane_id} #{pane_dead} #{pane_pid}",
                ]
            )
            if panes.returncode == 0:
                for row in panes.stdout.splitlines():
                    parts = row.split()
                    if parts and parts[0] == self.m_pane_id:
                        pane_exists = True
                        pane_dead = len(parts) > 1 and parts[1] == "1"
                        if len(parts) > 2 and parts[2].isdigit():
                            pane_pid = int(parts[2])
                            pane_pid_alive = _pid_alive(pane_pid)
                        break
        supported_pid, supported_alive = _find_supported_process(
            pane_pid=pane_pid, marker=self.m_process_marker
        )
        elapsed = max((datetime.now(UTC) - self.m_started_at).total_seconds(), 0.0)
        payload = {
            "ts_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "elapsed_seconds": round(elapsed, 3),
            "session_exists": session_exists,
            "pane_exists": pane_exists,
            "pane_dead": pane_dead,
            "pane_pid": pane_pid,
            "pane_pid_alive": pane_pid_alive,
            "supported_process_pid": supported_pid,
            "supported_process_alive": supported_alive,
        }
        with self.m_output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _pid_alive(pid: int) -> bool:
    """Return whether one pid exists."""

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _find_supported_process(*, pane_pid: int | None, marker: str) -> tuple[int | None, bool]:
    """Find one live descendant of the pane process matching the marker."""

    if pane_pid is None:
        return None, False
    try:
        listing = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, False
    if listing.returncode != 0:
        return None, False
    children: dict[int, list[tuple[int, str]]] = {}
    for line in listing.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) != 3:
            continue
        pid_text, ppid_text, args = parts
        if not (pid_text.isdigit() and ppid_text.isdigit()):
            continue
        children.setdefault(int(ppid_text), []).append((int(pid_text), args))
    # The pane command is exec'd, so the pane process itself may be the tool.
    own_args = _read_proc_args(pane_pid)
    if own_args and marker in own_args:
        return pane_pid, True
    stack = [pane_pid]
    while stack:
        current = stack.pop()
        for child_pid, args in children.get(current, []):
            if marker in args:
                return child_pid, True
            stack.append(child_pid)
    return None, False


def _read_proc_args(pid: int) -> str | None:
    """Return one process's command line from /proc, when readable."""

    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return None
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip() or None
