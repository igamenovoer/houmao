"""Tool/runtime helpers for the tracked-TUI demo pack."""

from __future__ import annotations

import os
import re
import shutil
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from houmao.agents.launch_overrides import LaunchOverrides
from houmao.agents.launch_policy.models import OperatorPromptMode
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    capture_tmux_pane,
    find_tmux_pane,
    list_tmux_panes,
    run_tmux,
    tmux_session_exists,
)
from houmao.shared_tui_tracking.models import RuntimeObservation

from .models import ToolName

if TYPE_CHECKING:
    from .config import ResolvedDemoConfig


_COMMANDS_BY_TOOL: dict[ToolName, tuple[list[str], ...]] = {
    "claude": (["claude", "--version"], ["claude-yunwu", "--version"]),
    "codex": (["codex", "--version"],),
}
_PROCESS_PATTERNS_BY_TOOL: dict[ToolName, tuple[re.Pattern[str], ...]] = {
    "claude": (
        re.compile(r"(^|/)(claude)(\s|$)"),
        re.compile(r"claude-yunwu"),
    ),
    "codex": (
        re.compile(r"(^|/)(codex)(\s|$)"),
        re.compile(r"codex-cli"),
    ),
}


@dataclass(frozen=True)
class ToolRuntimeMetadata:
    """Tool-specific launch and discovery metadata."""

    tool: ToolName
    interactive_watch_recipe_path: Path
    launch_overrides: LaunchOverrides | None
    operator_prompt_mode: OperatorPromptMode | None


def default_tool_runtime_metadata(
    *,
    repo_root: Path,
    tool: ToolName,
    demo_config: "ResolvedDemoConfig | None" = None,
) -> ToolRuntimeMetadata:
    """Return the default runtime metadata for one supported tool."""

    if demo_config is not None:
        tool_config = demo_config.tool_config(tool=tool)
        recipe_path = demo_config.resolve_repo_path(tool_config.recipe_path)
        launch_overrides = tool_config.launch_overrides
        operator_prompt_mode = tool_config.operator_prompt_mode
    else:
        recipe_path = (
            repo_root
            / "tests"
            / "fixtures"
            / "agents"
            / "brains"
            / "brain-recipes"
            / tool
            / "interactive-watch-default.yaml"
        ).resolve()
        if tool == "claude":
            launch_overrides = None
            operator_prompt_mode = "unattended"
        else:
            launch_overrides = None
            operator_prompt_mode = None
    return ToolRuntimeMetadata(
        tool=tool,
        interactive_watch_recipe_path=recipe_path,
        launch_overrides=launch_overrides,
        operator_prompt_mode=operator_prompt_mode,
    )


def detect_tool_version(*, tool: ToolName) -> str | None:
    """Return the observed tool version string when available."""

    for command in _COMMANDS_BY_TOOL[tool]:
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            return output
    return None


def ensure_command_available(command_name: str) -> None:
    """Fail fast when one external command is unavailable."""

    if shutil.which(command_name) is None:
        raise RuntimeError(f"`{command_name}` was not found on PATH")


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


def query_pane_state(*, session_name: str, pane_id: str) -> dict[str, Any] | None:
    """Return tmux pane state for one pane id when available."""

    pane = find_tmux_pane(session_name=session_name, pane_id=pane_id)
    if pane is None:
        return None
    return {
        "pane_dead": pane.pane_dead,
        "pane_pid": pane.pane_pid,
    }


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


def find_supported_process_pid(*, root_pid: int, tool: ToolName) -> int | None:
    """Return a descendant pid that looks like the selected tool."""

    if not process_is_alive(root_pid):
        return None
    tree = process_tree()
    queue = [root_pid]
    seen: set[int] = set()
    patterns = _PROCESS_PATTERNS_BY_TOOL[tool]
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        command = tree.get(current, {}).get("args", "")
        if any(pattern.search(command) for pattern in patterns):
            return current
        children = [pid for pid, payload in tree.items() if payload.get("ppid") == current]
        queue.extend(children)
    return None


def sample_runtime_observation(
    *,
    tool: ToolName,
    session_name: str,
    pane_id: str,
    recorder_started_at: datetime,
) -> RuntimeObservation:
    """Capture one runtime observation aligned to recorder time."""

    session_exists = tmux_session_exists(session_name=session_name)
    pane_exists = False
    pane_dead = False
    pane_pid: int | None = None
    pane_pid_alive = False
    supported_process_pid: int | None = None
    supported_process_alive = False
    if session_exists:
        pane_state = query_pane_state(session_name=session_name, pane_id=pane_id)
        if pane_state is not None:
            pane_exists = True
            pane_dead = bool(pane_state["pane_dead"])
            pane_pid = pane_state["pane_pid"]
            if pane_pid is not None:
                pane_pid_alive = process_is_alive(pane_pid)
                supported_process_pid = find_supported_process_pid(root_pid=pane_pid, tool=tool)
                if supported_process_pid is not None:
                    supported_process_alive = process_is_alive(supported_process_pid)
    return RuntimeObservation(
        ts_utc=now_utc_iso(),
        elapsed_seconds=max(
            0.0,
            (datetime.now(UTC) - recorder_started_at.astimezone(UTC)).total_seconds(),
        ),
        session_exists=session_exists,
        pane_exists=pane_exists,
        pane_dead=pane_dead,
        pane_pid=pane_pid,
        pane_pid_alive=pane_pid_alive,
        supported_process_pid=supported_process_pid,
        supported_process_alive=supported_process_alive,
    )


def capture_pane_text(*, pane_id: str) -> str:
    """Capture raw pane text from tmux."""

    return capture_tmux_pane(target=pane_id)


def capture_visible_pane_text(*, pane_id: str) -> str:
    """Capture only the currently visible tmux pane surface."""

    result = run_tmux(["capture-pane", "-p", "-e", "-t", pane_id])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown tmux error"
        raise TmuxCommandError(f"Failed to capture visible tmux pane `{pane_id}`: {detail}")
    return result.stdout


def now_utc_iso() -> str:
    """Return a UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def build_session_name(*, prefix: str, run_id: str) -> str:
    """Build one bounded tmux session name."""

    return f"{prefix}-{run_id}"[:60]


def build_tool_session_name(*, tool: ToolName, run_id: str) -> str:
    """Build the tmux session name for one tool-owned demo pane."""

    return build_session_name(prefix=f"shared-tui-{tool}", run_id=run_id)


def build_dashboard_session_name(*, tool: ToolName, run_id: str) -> str:
    """Build the tmux session name for one tool-scoped live-watch dashboard."""

    return build_session_name(prefix=f"shared-tui-{tool}-dashboard", run_id=run_id)


def write_command_script(*, script_path: Path, command: str) -> Path:
    """Write one shell script that executes a fixed command."""

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"exec bash -lc {shlex.quote(command)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def kill_tmux_session_if_exists(*, session_name: str) -> None:
    """Best-effort cleanup for one tmux session."""

    if not tmux_session_exists(session_name=session_name):
        return
    result = run_tmux(["kill-session", "-t", session_name])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown tmux error"
        raise TmuxCommandError(f"Failed to kill tmux session `{session_name}`: {detail}")


def kill_supported_process_for_pane(*, tool: ToolName, session_name: str, pane_id: str) -> None:
    """Terminate the supported tool process under one tmux pane while leaving the pane alive."""

    if not tmux_session_exists(session_name=session_name):
        raise RuntimeError(f"tmux session does not exist: {session_name}")
    pane_state = query_pane_state(session_name=session_name, pane_id=pane_id)
    if pane_state is None:
        raise RuntimeError(f"Failed to resolve pane state for {pane_id}")
    pane_pid = pane_state["pane_pid"]
    if pane_pid is None:
        raise RuntimeError(f"Pane `{pane_id}` has no pid")
    supported_process_pid = find_supported_process_pid(root_pid=pane_pid, tool=tool)
    if supported_process_pid is None:
        raise RuntimeError(
            f"Failed to resolve supported process under pane `{pane_id}` for tool `{tool}`"
        )
    os.kill(supported_process_pid, signal.SIGTERM)
    time.sleep(0.2)
    if process_is_alive(supported_process_pid):
        os.kill(supported_process_pid, signal.SIGKILL)
