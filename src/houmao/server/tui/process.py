"""Live process-tree inspection for tracked tmux panes."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from houmao.server.models import ProcessState


@dataclass(frozen=True)
class PaneProcessMatch:
    """One matched process from the tracked pane tree."""

    pid: int
    command_name: str
    argv0: str


@dataclass(frozen=True)
class PaneProcessInspection:
    """Result of inspecting one tracked pane process tree."""

    process_state: ProcessState
    matched_process_names: tuple[str, ...]
    matched_processes: tuple[PaneProcessMatch, ...]
    error_message: str | None = None


@dataclass(frozen=True)
class _ProcessRecord:
    """One parsed process-table record."""

    pid: int
    ppid: int
    command_name: str
    args: str


class PaneProcessInspector:
    """Inspect supported tool-process liveliness from a tmux pane pid."""

    def __init__(self, *, supported_processes: dict[str, tuple[str, ...]]) -> None:
        """Initialize the inspector."""

        self.m_supported_processes = {
            tool: tuple(name.lower() for name in names)
            for tool, names in supported_processes.items()
        }

    def inspect(self, *, tool: str, pane_pid: int | None) -> PaneProcessInspection:
        """Inspect whether the supported TUI process is live for one pane."""

        expected_names = self.m_supported_processes.get(tool)
        if expected_names is None:
            return PaneProcessInspection(
                process_state="unsupported_tool",
                matched_process_names=(),
                matched_processes=(),
            )
        if pane_pid is None or pane_pid <= 0:
            return PaneProcessInspection(
                process_state="probe_error",
                matched_process_names=(),
                matched_processes=(),
                error_message="Tracked tmux pane is missing a valid pane_pid.",
            )

        try:
            process_records = _read_process_table()
        except OSError as exc:
            return PaneProcessInspection(
                process_state="probe_error",
                matched_process_names=(),
                matched_processes=(),
                error_message=f"Failed to inspect the live process table: {exc}",
            )

        descendants = _descendants_for_pid(process_records=process_records, root_pid=pane_pid)
        matches: list[PaneProcessMatch] = []
        for record in descendants:
            normalized_command = record.command_name.lower()
            normalized_argv0 = (
                Path(record.args.split(maxsplit=1)[0]).name.lower() if record.args else ""
            )
            if normalized_command not in expected_names and normalized_argv0 not in expected_names:
                continue
            matches.append(
                PaneProcessMatch(
                    pid=record.pid,
                    command_name=record.command_name,
                    argv0=normalized_argv0 or record.command_name,
                )
            )

        if not matches:
            return PaneProcessInspection(
                process_state="tui_down",
                matched_process_names=(),
                matched_processes=(),
            )

        matched_process_names = tuple(sorted({match.command_name for match in matches}))
        return PaneProcessInspection(
            process_state="tui_up",
            matched_process_names=matched_process_names,
            matched_processes=tuple(matches),
        )


def _read_process_table() -> tuple[_ProcessRecord, ...]:
    """Return the current process table parsed from `ps` output."""

    result = subprocess.run(
        ["ps", "-ax", "-o", "pid=", "-o", "ppid=", "-o", "comm=", "-o", "args="],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or "unknown ps error"
        raise OSError(detail)

    records: list[_ProcessRecord] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=3)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        command_name = parts[2]
        args = parts[3] if len(parts) > 3 else command_name
        records.append(
            _ProcessRecord(
                pid=pid,
                ppid=ppid,
                command_name=command_name,
                args=args,
            )
        )
    return tuple(records)


def _descendants_for_pid(
    *,
    process_records: tuple[_ProcessRecord, ...],
    root_pid: int,
) -> tuple[_ProcessRecord, ...]:
    """Return the pane-root process plus all descendants."""

    by_parent: dict[int, list[_ProcessRecord]] = {}
    by_pid: dict[int, _ProcessRecord] = {}
    for record in process_records:
        by_pid[record.pid] = record
        by_parent.setdefault(record.ppid, []).append(record)

    pending = [root_pid]
    visited: set[int] = set()
    descendants: list[_ProcessRecord] = []
    while pending:
        current_pid = pending.pop()
        if current_pid in visited:
            continue
        visited.add(current_pid)
        current_record = by_pid.get(current_pid)
        if current_record is not None:
            descendants.append(current_record)
        for child in by_parent.get(current_pid, []):
            pending.append(child.pid)
    return tuple(descendants)
