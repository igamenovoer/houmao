"""Launch kimi-code under tmux per ``houmao-dev-launch-agents`` contracts.

Implements the ``launch-kimi-code`` command page and the common launch
contract as executable campaign tooling: resolve the executable, validate
non-secret credential posture, launch one detached tmux session with a pinned
``KIMI_CODE_HOME``, verify bounded startup, and write secret-free launch
metadata under ``<run-root>/launch/``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.backends.tmux_runtime import run_tmux

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_KIMI_HOME = REPO_ROOT / ".kimi-code"
PANE_WIDTH = 220
PANE_HEIGHT = 50

_SURFACE_MARKERS = ("context:", "Trust this folder?", "Kimi", "kimi", ">")


def launch_kimi(
    *,
    run_root: Path,
    workdir: Path,
    session_name: str,
    unattended: bool,
    kimi_home: Path = DEFAULT_KIMI_HOME,
    timeout_seconds: float = 90.0,
) -> dict[str, Any]:
    """Launch one kimi TUI in detached tmux and write launch metadata.

    Parameters
    ----------
    run_root:
        Fresh campaign run root; launch artifacts land in ``launch/``.
    workdir:
        Trusted or deliberately untrusted working directory for the session.
    session_name:
        Unique tmux session name; must not already exist.
    unattended:
        When true, launch with ``--auto``; otherwise bare (as_is posture).
    kimi_home:
        Pinned ``KIMI_CODE_HOME`` so provider credentials resolve
        deterministically.
    timeout_seconds:
        Bounded startup verification window.

    Returns
    -------
    dict
        Launch metadata also persisted to ``launch/launch.json``.
    """

    launch_dir = run_root / "launch"
    launch_dir.mkdir(parents=True, exist_ok=True)

    executable = shutil.which("kimi") or shutil.which("kimi-code")
    if executable is None:
        raise RuntimeError("Neither `kimi` nor `kimi-code` resolves on PATH")
    version = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, timeout=30
    ).stdout.strip()

    env = {**os.environ, "KIMI_CODE_HOME": str(kimi_home)}
    doctor = subprocess.run(
        [executable, "doctor", "config"], capture_output=True, text=True, timeout=60, env=env
    )
    if doctor.returncode != 0:
        raise RuntimeError(f"`kimi doctor config` failed: {doctor.stdout[-400:]}")

    if run_tmux(["has-session", "-t", session_name]).returncode == 0:
        raise RuntimeError(f"tmux session `{session_name}` already exists")

    posture_args = ["--auto"] if unattended else []
    pane_command = " ".join(
        ["exec", "env", f"KIMI_CODE_HOME={kimi_home}", executable, *posture_args]
    )
    result = run_tmux(
        [
            "new-session",
            "-d",
            "-s",
            session_name,
            "-x",
            str(PANE_WIDTH),
            "-y",
            str(PANE_HEIGHT),
            "-c",
            str(workdir),
            pane_command,
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {result.stderr.strip()}")

    pane_id = ""
    surface_text = ""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        panes = run_tmux(["list-panes", "-t", session_name, "-F", "#{pane_id}"])
        if panes.returncode == 0 and panes.stdout.strip():
            pane_id = panes.stdout.splitlines()[0].strip()
            capture = run_tmux(["capture-pane", "-p", "-t", pane_id])
            surface_text = capture.stdout if capture.returncode == 0 else ""
            if any(marker in surface_text for marker in _SURFACE_MARKERS):
                break
        time.sleep(1.0)
    else:
        raise RuntimeError(
            f"kimi surface did not stabilize within {timeout_seconds}s in `{session_name}`"
        )

    pane_pid_row = run_tmux(["display-message", "-p", "-t", pane_id, "#{pane_pid}"])
    pane_pid = int(pane_pid_row.stdout.strip()) if pane_pid_row.returncode == 0 else None

    metadata: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_root.name,
        "provider": "kimi",
        "provider_version": version,
        "workdir": str(workdir),
        "run_root": str(run_root),
        "tmux_session": session_name,
        "tmux_pane": pane_id,
        "pane_pid": pane_pid,
        "pane_width": PANE_WIDTH,
        "pane_height": PANE_HEIGHT,
        "launcher_command": Path(executable).name,
        "launcher_path": executable,
        "credential_strategy": "native KIMI_CODE_HOME config (OAuth), validated by kimi doctor",
        "credential_source_path": str(kimi_home),
        "posture": "unattended" if unattended else "as_is",
        "provider_arguments": posture_args,
        "launched_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "startup_verification": "surface marker observed in bounded poll",
    }
    (launch_dir / "launch.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (launch_dir / "launch-report.md").write_text(
        "\n".join(
            [
                f"# Launch Report: {session_name}",
                "",
                f"- provider: kimi {version} (`{executable}`)",
                f"- posture: {metadata['posture']} (`{' '.join(posture_args) or 'bare'}`)",
                f"- workdir: `{workdir}`",
                f"- tmux: session `{session_name}`, pane `{pane_id}`, {PANE_WIDTH}x{PANE_HEIGHT}",
                f"- attach: `tmux attach-session -t {session_name}`",
                "- credential check: `kimi doctor config` exit 0 (KIMI_CODE_HOME pinned, values not read)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return metadata


def kill_session(*, session_name: str) -> None:
    """Tear down the campaign-owned tmux session."""

    run_tmux(["kill-session", "-t", session_name])
