"""Shared tmux/runtime helpers for Claude Code state-tracking explore workflows."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.backends.tmux_runtime import (
    capture_tmux_pane,
    list_tmux_panes,
    run_tmux,
)
from houmao.explore.claude_code_state_tracking.detectors.base import BaseTurnSignalDetector


def launch_tmux_session(*, session_name: str, workdir: Path, launch_script: Path) -> None:
    """Launch one detached tmux session and keep the pane visible on exit."""

    result = run_tmux(
        [
            "new-session",
            "-d",
            "-s",
            session_name,
            "-c",
            str(workdir),
            str(launch_script),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "failed to launch tmux session")
    run_tmux(["set-option", "-t", session_name, "remain-on-exit", "on"])


def resolve_active_pane_id(*, session_name: str) -> str:
    """Return the active pane id for one tmux session."""

    panes = list_tmux_panes(session_name=session_name)
    for pane in panes:
        if pane.pane_active:
            return pane.pane_id
    raise RuntimeError(f"Failed to resolve active pane for {session_name}")


def send_text(*, pane_id: str, text: str, submit: bool) -> None:
    """Send literal text and optional submit to one tmux pane."""

    run_tmux(["send-keys", "-t", pane_id, "-l", text])
    if submit:
        run_tmux(["send-keys", "-t", pane_id, "Enter"])


def send_key(*, pane_id: str, key: str) -> None:
    """Send one tmux key token to one pane."""

    run_tmux(["send-keys", "-t", pane_id, key])


def wait_for_ready(*, pane_id: str, detector: BaseTurnSignalDetector, timeout_seconds: float) -> None:
    """Wait until the detector reports a ready posture."""

    deadline = _monotonic_deadline(timeout_seconds=timeout_seconds)
    while _monotonic_remaining(deadline=deadline):
        output = capture_tmux_pane(target=pane_id)
        signals = detector.detect(output_text=output)
        if signals.ready_posture == "yes":
            return
        _sleep_short()
    raise TimeoutError(f"Timed out waiting for ready posture in {pane_id}")


def wait_for_pattern(*, pane_id: str, pattern: str, timeout_seconds: float) -> None:
    """Wait until a stripped pane surface matches a regex pattern."""

    compiled = re.compile(pattern)
    deadline = _monotonic_deadline(timeout_seconds=timeout_seconds)
    while _monotonic_remaining(deadline=deadline):
        output = capture_tmux_pane(target=pane_id)
        stripped = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", output)
        if compiled.search(stripped):
            return
        _sleep_short()
    raise TimeoutError(f"Timed out waiting for pattern `{pattern}` in {pane_id}")


def query_pane_state(*, session_name: str, pane_id: str) -> dict[str, Any] | None:
    """Return pane state from tmux including `pane_dead` and `pane_pid`."""

    result = run_tmux(
        [
            "list-panes",
            "-t",
            session_name,
            "-F",
            "#{pane_id}\t#{pane_dead}\t#{pane_pid}",
        ]
    )
    if result.returncode != 0:
        return None
    for raw_line in result.stdout.splitlines():
        parts = raw_line.strip().split("\t")
        if len(parts) != 3:
            continue
        if parts[0] != pane_id:
            continue
        return {
            "pane_dead": parts[1] == "1",
            "pane_pid": int(parts[2]) if parts[2].isdigit() else None,
        }
    return None


def find_supported_process_pid(*, root_pid: int) -> int | None:
    """Return a descendant pid that looks like Claude or its wrapper."""

    if not process_is_alive(root_pid):
        return None
    tree = process_tree()
    queue = [root_pid]
    seen: set[int] = set()
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        command = tree.get(current, {}).get("args", "")
        if "claude-yunwu" in command or re.search(r"(^|/)(claude)(\s|$)", command):
            return current
        children = [pid for pid, payload in tree.items() if payload.get("ppid") == current]
        queue.extend(children)
    return None


def process_tree() -> dict[int, dict[str, Any]]:
    """Return one process table keyed by pid."""

    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,args="],
        check=True,
        capture_output=True,
        text=True,
    )
    payload: dict[int, dict[str, Any]] = {}
    for raw_line in result.stdout.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 2)
        if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        payload[int(parts[0])] = {
            "ppid": int(parts[1]),
            "args": parts[2] if len(parts) > 2 else "",
        }
    return payload


def process_is_alive(pid: int) -> bool:
    """Return whether one pid currently exists."""

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def detect_claude_version() -> str | None:
    """Return the observed Claude Code version string when available."""

    for command in (["claude", "--version"], ["claude-yunwu", "--version"]):
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            return output
    return None


def now_utc_iso() -> str:
    """Return a UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def ensure_command_available(command_name: str) -> None:
    """Fail fast when one external command is missing."""

    if shutil.which(command_name) is None:
        raise RuntimeError(f"`{command_name}` was not found on PATH")


def _monotonic_deadline(*, timeout_seconds: float) -> float:
    """Return one monotonic deadline timestamp."""

    import time

    return time.monotonic() + timeout_seconds


def _monotonic_remaining(*, deadline: float) -> bool:
    """Return whether the current monotonic time is still before the deadline."""

    import time

    return time.monotonic() < deadline


def _sleep_short() -> None:
    """Sleep for the standard short polling interval."""

    import time

    time.sleep(0.2)
