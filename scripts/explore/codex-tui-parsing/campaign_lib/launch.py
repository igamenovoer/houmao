"""Launch codex under tmux per ``houmao-dev-launch-agents`` contracts.

Implements the ``launch-codex`` command page and the common launch contract as
executable campaign tooling: resolve the executable, validate non-secret
credential posture (``codex login status`` against the pinned ``CODEX_HOME``),
launch one detached tmux session, verify bounded startup, and write secret-free
launch metadata under ``<run-root>/launch/``.
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
DEFAULT_CODEX_HOME = REPO_ROOT / ".codex"
DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_EFFORT = "medium"
PANE_WIDTH = 220
PANE_HEIGHT = 50

_SURFACE_MARKERS = (
    "Ask Codex to do anything",
    "for shortcuts",
    "Trust this folder?",
    "Would you like",
)


def launch_codex(
    *,
    run_root: Path,
    workdir: Path,
    session_name: str,
    posture: str,
    codex_home: Path = DEFAULT_CODEX_HOME,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    timeout_seconds: float = 90.0,
) -> dict[str, Any]:
    """Launch one codex TUI in detached tmux and write launch metadata.

    Parameters
    ----------
    run_root:
        Fresh campaign run root; launch artifacts land in ``launch/``.
    workdir:
        Working directory for the session (trusted or deliberately untrusted).
    session_name:
        Unique tmux session name; must not already exist.
    posture:
        ``unattended`` launches with ``--dangerously-bypass-approvals-and-sandbox``;
        ``as_is`` launches with ``-a untrusted -s read-only`` so approval
        surfaces render deterministically without bypass.
    codex_home:
        Pinned ``CODEX_HOME`` so provider credentials resolve deterministically.
    model:
        Codex model selector (campaign default ``gpt-6.1-sol``).
    effort:
        Reasoning effort override (campaign default ``medium``).
    timeout_seconds:
        Bounded startup verification window.

    Returns
    -------
    dict
        Launch metadata also persisted to ``launch/launch.json``.
    """

    launch_dir = run_root / "launch"
    launch_dir.mkdir(parents=True, exist_ok=True)

    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("`codex` does not resolve on PATH")
    version = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, timeout=30
    ).stdout.strip()

    env = {**os.environ, "CODEX_HOME": str(codex_home)}
    login = subprocess.run(
        [executable, "login", "status"], capture_output=True, text=True, timeout=60, env=env
    )
    if login.returncode != 0:
        raise RuntimeError("`codex login status` failed for the pinned CODEX_HOME")

    if run_tmux(["has-session", "-t", session_name]).returncode == 0:
        raise RuntimeError(f"tmux session `{session_name}` already exists")

    posture_args = (
        ["--dangerously-bypass-approvals-and-sandbox"]
        if posture == "unattended"
        else ["-a", "on-request", "-s", "read-only"]
    )
    provider_args = [
        *posture_args,
        "-m",
        model,
        "-c",
        f'model_reasoning_effort="{effort}"',
        "-C",
        str(workdir),
    ]
    pane_command = " ".join(["exec", "env", f"CODEX_HOME={codex_home}", executable, *provider_args])
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
            f"codex surface did not stabilize within {timeout_seconds}s in `{session_name}`"
        )

    pane_pid_row = run_tmux(["display-message", "-p", "-t", pane_id, "#{pane_pid}"])
    pane_pid = int(pane_pid_row.stdout.strip()) if pane_pid_row.returncode == 0 else None

    metadata: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_root.name,
        "provider": "codex",
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
        "credential_strategy": "native CODEX_HOME config (ChatGPT login), validated by codex login status",
        "credential_source_path": str(codex_home),
        "posture": posture,
        "model": model,
        "reasoning_effort": effort,
        "provider_arguments": provider_args,
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
                f"- provider: codex {version} (`{executable}`)",
                f"- posture: {posture} (`{' '.join(posture_args)}`)",
                f"- model: {model}, effort: {effort}",
                f"- workdir: `{workdir}`",
                f"- tmux: session `{session_name}`, pane `{pane_id}`, {PANE_WIDTH}x{PANE_HEIGHT}",
                f"- attach: `tmux attach-session -t {session_name}`",
                "- credential check: `codex login status` exit 0 (CODEX_HOME pinned, values not read)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return metadata


def kill_session(*, session_name: str) -> None:
    """Tear down the campaign-owned tmux session."""

    run_tmux(["kill-session", "-t", session_name])
