"""One-command scenario runner for the Kimi hook-observation campaign's Phase A harness.

Throwaway harness for the iteration-1 capture-matrix plan under
``context/campaigns/debug/2026-10-20-kimi-hook-observation/iterations/``.
Each run creates an isolated scratch ``KIMI_CODE_HOME`` under
``tmp/kimi-hook-capture/<scenario>/run-<UTCts>/`` by copying the operator's
real ``~/.kimi-code`` files at runtime (``config.toml``, ``credentials/``,
``oauth/``, ``device_id`` and two optional migration files), merges the 20-event
``[[hooks]]`` observer block, pre-seeds the workspace-trust record, starts the
loopback collector, launches ``kimi`` in a detached tmux session, drives one
frozen scenario arm tracker-blind with ``tmux send-keys``, records the pane at
5 fps with the repo's terminal-record tool, and writes a labels template,
driver-input log, raw-provider-payload log, run summary, and secret-free
``launch.json`` manifest.

Nothing here is production code. ``--self-test`` is the provider-free G0 gate
and never launches Kimi or reads credentials.

Credential hygiene: the harness copies credential files byte-for-byte with
``shutil`` and never reads, prints, or embeds their contents. Only the per-run
random bearer token appears in artifacts, inside the mode-0600 launch wrapper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import tomllib
import traceback
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HARNESS_DIR = Path(__file__).resolve().parent
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

import kimi_hooks  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
COLLECTOR_SCRIPT = HARNESS_DIR / "collector.py"
EMIT_HOOK_SCRIPT = HARNESS_DIR / "emit_hook.py"
KIMI_HOOKS_SCRIPT = HARNESS_DIR / "kimi_hooks.py"
RUN_ROOT_BASE = REPO_ROOT / "tmp" / "kimi-hook-capture"
DEFAULT_KIMI_HOME_SOURCE = Path.home() / ".kimi-code"
DEFAULT_KIMI_BINARY = "kimi"
PANE_WIDTH = 220
PANE_HEIGHT = 56
RECORDER_INTERVAL_SECONDS = 0.2
HOOK_ROUTE = "/v1/hook"
COLLECTOR_FILENAME = "collector.json"
EVENTS_FILENAME = "events.ndjson"
HEARTBEAT_HOLD_SECONDS = 70.0
F1_POST_KILL_OBSERVATION_SECONDS = 70.0
DEFAULT_HOOK_TIMEOUT_SECONDS = 5
SLOW_HOOK_PREFIX = "sleep 3; "
SLOW_HOOK_EVENTS = ("SessionStart", "SessionEnd")

PROMPT_OK = "Reply with exactly: OK"
PROMPT_TOOL = "Run the shell command `echo hi` and report its output, then reply with exactly: DONE"
PROMPT_README = "Read the file README.md in the current directory and summarize it in one sentence."
PROMPT_ALLOW = "Create a file named /tmp/houmao-kimi-hook-allow.txt containing hello"
PROMPT_DENY = "Create a file named /tmp/houmao-kimi-hook-deny.txt containing hello"
PROMPT_RECURSION = "Write a long essay about recursion."
PROMPT_QUEUES = "Write a long essay about queues."
PROMPT_FAULTS = "Write a long essay about faults."
PROMPT_SUBAGENT = "Use the Agent tool to launch a subagent that replies with exactly: OK"

# TUI surface strings discovered from the Kimi 2.2.0 docs and TUI source in
# extern/orphan/kimi-code (2026-10-20) and corrected live during the S0 gate.
# Keep them as constants so the campaign can correct them without touching
# scenario logic. Live correction 2026-10-20: the TUI is inline/top-anchored,
# so readiness must scan the whole pane, not the last N lines.
COMPOSER_WELCOME_MARKERS = ("Welcome to Kimi Code!",)
COMPOSER_DIRECTORY_MARKER = "Directory:"
COMPOSER_FOOTER_MARKER = "context:"
COMPOSER_EDITOR_BORDER = "─" * 20
COMPOSER_STABLE_SECONDS = 2.0
TRUST_MODAL_MARKERS = (
    "Trust this folder?",
    "Trust and continue",
    "↑↓ navigate · Enter select · Esc exit",
)
PERMISSION_PROMPT_MARKERS = (
    "Run this command?",
    "Write this file?",
    "Apply these edits?",
    "Ready to build with this plan?",
    "Stop this task?",
    "Approve ",
    "↑/↓ select ·",
)
PERMISSION_OPTION_PATTERN = re.compile(r"^\s*(?:▶\s*)?(\d+)\.\s+(.+?)\s*$")
PERMISSION_OPTION_SCAN_LINES = 40
EXIT_COMMAND = "/exit"
EXIT_FALLBACK_SEQUENCES: tuple[tuple[str, ...], ...] = (
    ("C-c", "C-c"),
    ("C-d", "C-d"),
)
SESSION_GONE_TIMEOUT_SECONDS = 25.0
S4_README_TEXT = (
    "# Kimi hook capture scratch project\n"
    "\n"
    "Temporary git-less workdir for the Kimi hook-observation campaign.\n"
    "This file exists so s4 has a README to read and summarize.\n"
)
S2_MALFORMED_ENTRY = (
    '[[hooks]]\nevent = "Notification"\ncommand = "true"\ntimeout = 5\ncwd = "/tmp"\n'
)
UTC_MS_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")
SEED_REQUIRED_FILES = ("config.toml",)
SEED_OPTIONAL_FILES = ("device_id", ".skip-migration-from-kimi-cli", "migrations-effort.json")
SEED_DIRS = ("credentials", "oauth")


def utc_now_ms() -> str:
    """Return the current UTC time as an ISO-8601 string with milliseconds."""

    return datetime.now(UTC).isoformat(timespec="milliseconds")


def utc_stamp() -> str:
    """Return the compact UTC stamp used in run-root directory names."""

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON line, creating parent directories on demand."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _shell_single_quote(value: str) -> str:
    """Quote one value for safe inclusion in a generated bash script."""

    return shlex.quote(value)


def _sha256_file(path: Path) -> str | None:
    """Return the SHA-256 hex digest of a file, or None when unreadable."""

    return kimi_hooks.sha256_file(path)


def run_tmux(args: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    """Run one tmux command and return its completed process.

    The Kimi lane is stdlib-only, so it does not import houmao's tmux runtime;
    this mirrors the small subset of that helper the campaign needs.
    """

    return subprocess.run(
        ["tmux", *args], capture_output=True, text=True, timeout=timeout, check=False
    )


def _resolve_kimi_binary(spec: str) -> dict[str, Any]:
    """Resolve the Kimi binary, its SHA-256, and its reported version.

    This runs ``kimi --version`` only; no session or prompt is launched. It is
    called from matching scenario runs, never from ``--self-test``.
    """

    candidate = Path(spec).expanduser()
    if candidate.is_file():
        path = candidate.resolve()
    else:
        which = shutil.which(spec)
        if which is None:
            raise FileNotFoundError(f"kimi binary not found: {spec}")
        path = Path(which).resolve()
    info: dict[str, Any] = {
        "requested": spec,
        "path": str(path),
        "sha256": _sha256_file(path),
        "version": None,
        "resolution_notes": [],
    }
    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        info["version"] = result.stdout.strip() or result.stderr.strip() or None
    except (OSError, subprocess.TimeoutExpired) as exc:
        info["resolution_notes"].append(f"kimi --version failed: {exc!r}")
    return info


@dataclass(frozen=True)
class ScenarioSpec:
    """One frozen scenario arm from the campaign capture matrix."""

    name: str
    expectation: str
    labels: tuple[tuple[str, str], ...] = ()
    auto: bool = True
    permission_lane: bool = False
    malformed_hooks: bool = False
    slow_lifecycle_hooks: bool = False
    headless: bool = False
    optional: bool = False


SCENARIOS: dict[str, ScenarioSpec] = {
    "s0": ScenarioSpec(
        name="s0",
        expectation=(
            "SessionStart arrives awaited before any prompt; UserPromptSubmit + Stop "
            "arrive; ready composer reached with zero keypresses and no modal."
        ),
        labels=(
            ("s0-ready", "composer surface before the prompt"),
            ("s0-turn-ok", "span from prompt submit to visible OK answer"),
        ),
    ),
    "s1": ScenarioSpec(
        name="s1",
        expectation=(
            "Three turn cycles including a Bash call; SessionHeartbeat after >=65 s; "
            "mid-session marker hook does NOT fire (load-once); clean SessionEnd."
        ),
        labels=(
            ("s1-turn-1", "first turn (OK prompt)"),
            ("s1-turn-2", "second turn (echo hi)"),
            ("s1-heartbeat-hold", "hold window covering the heartbeat interval"),
            ("s1-hot-reload-probe", "marker append and third prompt"),
            ("s1-exit", "span around /exit and SessionEnd delivery"),
        ),
    ),
    "s2": ScenarioSpec(
        name="s2",
        expectation=(
            "One hooks entry with an extra cwd key drops the whole section: zero events, "
            "TUI session otherwise normal, warning visible in -p stderr."
        ),
        malformed_hooks=True,
        labels=(
            ("s2-startup", "startup surface with the malformed hooks section"),
            ("s2-print-probe", "headless -p probe capturing the config warning"),
        ),
    ),
    "s3": ScenarioSpec(
        name="s3",
        expectation=(
            "PermissionRequest/PermissionResult fire in ask mode; driver approves once "
            "and denies once; tool_call_id pairing and settle events recorded."
        ),
        auto=False,
        permission_lane=True,
        labels=(
            ("s3-permission-allow", "span from allow-prompt submit to post-allow settle"),
            ("s3-permission-deny", "span from deny-prompt submit to post-deny settle"),
        ),
    ),
    "s4": ScenarioSpec(
        name="s4",
        expectation=(
            "Manual /compact emits PreCompact and PostCompact(trigger=manual) with token "
            "fields; posture continues into the post-compact turn."
        ),
        labels=(
            ("s4-readme-turn", "first turn (README summary)"),
            ("s4-compact", "span around /compact"),
            ("s4-post-compact-turn", "turn after compaction"),
        ),
    ),
    "s5": ScenarioSpec(
        name="s5",
        expectation="Esc mid-generation emits Interrupt; Stop does not fire for the aborted turn.",
        labels=(
            ("s5-generation", "essay generation before Esc"),
            ("s5-post-escape", "span after Esc until settle"),
        ),
    ),
    "s6": ScenarioSpec(
        name="s6",
        expectation=(
            "A prompt typed while busy emits UserPromptQueued; drain ordering and the "
            "eventual UserPromptSubmit is_steer field are recorded."
        ),
        labels=(
            ("s6-first-turn", "essay turn before queued input"),
            ("s6-queued-turn", "turn consuming the queued OK prompt"),
        ),
    ),
    "s7": ScenarioSpec(
        name="s7",
        expectation=(
            "Clean exit then `kimi --continue` on the same home: SessionStart(source=resume); "
            "the H1 marker hook appended between generations fires only after restart."
        ),
        labels=(
            ("s7-first-turn", "OK turn before exit"),
            ("s7-exit", "exit before resume relaunch"),
            ("s7-resume", "resume relaunch and post-resume turn"),
        ),
    ),
    "s8": ScenarioSpec(
        name="s8",
        expectation=(
            "Headless `kimi -p` fires hooks; record which events appear and capture stderr."
        ),
        headless=True,
        labels=(
            ("s8-headless-start", "headless process launch"),
            ("s8-headless-end", "headless process exit and SessionEnd"),
        ),
    ),
    "f1": ScenarioSpec(
        name="f1",
        expectation=(
            "kill -9 the Kimi process tree mid-turn: record exactly which events do not "
            "arrive (expect no Stop, no Interrupt, no SessionEnd)."
        ),
        labels=(
            ("f1-generation", "essay generation before kill"),
            ("f1-kill", "span around kill -9 and post-kill silence"),
        ),
    ),
    "d1": ScenarioSpec(
        name="d1",
        expectation=(
            "Kill the collector after SessionStart: emitter file fallback engages, the "
            "session is unaffected, and fallback emitter_seq preserves order."
        ),
        labels=(
            ("d1-session-start", "SessionStart delivered over HTTP before the kill"),
            ("d1-fallback-turn", "OK turn delivered only through the file fallback"),
        ),
    ),
    "t1": ScenarioSpec(
        name="t1",
        expectation=(
            "SessionStart/SessionEnd hooks prefixed with `sleep 3` delay ready and exit "
            "relative to the S0 baseline; zero model cost."
        ),
        slow_lifecycle_hooks=True,
        labels=(
            ("t1-ready-delay", "time from launch to ready composer"),
            ("t1-exit-delay", "time from /exit to process exit and SessionEnd"),
        ),
    ),
    "s9": ScenarioSpec(
        name="s9",
        expectation=(
            "Optional subagent arm: SubagentStart/SubagentStop and TaskStarted(kind=agent) "
            "are captured if the provider and tooling cooperate."
        ),
        optional=True,
        labels=(
            ("s9-subagent-start", "subagent launch"),
            ("s9-subagent-stop", "subagent completion"),
        ),
    ),
}


class AbortRun(Exception):
    """Raised when a hard campaign gate fails; the run aborts with an explanation."""

    def __init__(self, reason: str) -> None:
        """Store the human-readable abort reason."""

        super().__init__(reason)
        self.m_reason = reason


class CollectorProcess:
    """Started collector subprocess; parses the ``PORT <n>`` startup line."""

    def __init__(
        self,
        *,
        store: Path,
        token: str,
        generation: int,
        log_path: Path,
        heartbeat_seconds: float = 2.0,
    ) -> None:
        """Record launch parameters without starting the process."""

        self.m_store = store
        self.m_token = token
        self.m_generation = generation
        self.m_log_path = log_path
        self.m_heartbeat_seconds = heartbeat_seconds
        self.m_port: int | None = None
        self.m_process: subprocess.Popen[str] | None = None
        self.m_port_event = threading.Event()

    def start(self) -> int:
        """Start the collector and return the chosen loopback port."""

        self.m_store.mkdir(parents=True, exist_ok=True)
        log_handle = self.m_log_path.open("a", encoding="utf-8")
        self.m_process = subprocess.Popen(
            [
                sys.executable,
                str(COLLECTOR_SCRIPT),
                "--store",
                str(self.m_store),
                "--token",
                self.m_token,
                "--generation",
                str(self.m_generation),
                "--heartbeat-seconds",
                str(self.m_heartbeat_seconds),
            ],
            stdout=subprocess.PIPE,
            stderr=log_handle,
            text=True,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        if not self.m_port_event.wait(timeout=15.0):
            raise RuntimeError("collector did not report PORT within 15s")
        assert self.m_port is not None
        return self.m_port

    def _read_stdout(self) -> None:
        """Consume collector stdout until the PORT line arrives."""

        assert self.m_process is not None and self.m_process.stdout is not None
        for line in self.m_process.stdout:
            text = line.strip()
            if text.startswith("PORT "):
                try:
                    self.m_port = int(text.split()[1])
                except (IndexError, ValueError):
                    continue
                self.m_port_event.set()

    def stop(self) -> None:
        """SIGTERM the collector and wait for it to drain and exit."""

        process = self.m_process
        self.m_process = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)


class PaneDriver:
    """Tracker-blind tmux driver; every action lands in the input-event log."""

    def __init__(self, *, session_name: str, pane_id: str, log_path: Path) -> None:
        """Bind the driver to one pane and one log file."""

        self.m_session_name = session_name
        self.m_pane_id = pane_id
        self.m_log_path = log_path

    def log(self, action: str, **detail: Any) -> None:
        """Append one timestamped action row to the managed input-event log."""

        row: dict[str, Any] = {
            "ts_utc": utc_now_ms(),
            "monotonic": round(time.monotonic(), 6),
            "action": action,
        }
        if detail:
            row["detail"] = detail
        _append_jsonl(self.m_log_path, row)

    @property
    def pane_id(self) -> str:
        """Return the tmux pane id bound to this driver."""

        return self.m_pane_id

    def visible_text(self) -> str:
        """Return the current plain visible pane text (empty on tmux failure)."""

        result = run_tmux(["capture-pane", "-p", "-t", self.m_pane_id])
        if result.returncode != 0:
            self.log(
                "capture-pane-failed",
                returncode=result.returncode,
                stderr=result.stderr.strip()[-500:],
            )
            return ""
        return result.stdout

    def send_text(self, text: str) -> None:
        """Type literal text with tmux send-keys -l."""

        result = run_tmux(["send-keys", "-t", self.m_pane_id, "-l", text])
        if result.returncode != 0:
            raise RuntimeError(f"send-keys literal failed: {result.stderr.strip()}")
        self.log("send_text", text=text)

    def send_key(self, key: str) -> None:
        """Send one named tmux key (Enter, Escape, Down, C-c, ...)."""

        result = run_tmux(["send-keys", "-t", self.m_pane_id, key])
        if result.returncode != 0:
            raise RuntimeError(f"send-keys {key} failed: {result.stderr.strip()}")
        self.log("send_key", key=key)

    def submit_text(self, text: str) -> None:
        """Type literal text and press Enter."""

        self.send_text(text)
        time.sleep(0.15)
        self.send_key("Enter")

    def wait_pattern(self, pattern: str, *, timeout_seconds: float) -> bool:
        """Poll until one literal pattern is visible; False on timeout."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if pattern in self.visible_text():
                return True
            time.sleep(0.4)
        return False

    def wait_any(self, patterns: tuple[str, ...], *, timeout_seconds: float) -> bool:
        """Poll until any of several literal patterns is visible; False on timeout."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            text = self.visible_text()
            if any(pattern in text for pattern in patterns):
                return True
            time.sleep(0.4)
        return False

    def wait_any_lower(self, patterns: tuple[str, ...], *, timeout_seconds: float) -> bool:
        """Case-insensitive variant of :meth:`wait_any`."""

        deadline = time.monotonic() + timeout_seconds
        lowered = tuple(pattern.lower() for pattern in patterns)
        while time.monotonic() < deadline:
            text = self.visible_text().lower()
            if any(pattern in text for pattern in lowered):
                return True
            time.sleep(0.4)
        return False

    def wait_absence(self, pattern: str, *, timeout_seconds: float) -> bool:
        """Poll until one literal pattern disappears; False on timeout."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if pattern not in self.visible_text():
                return True
            time.sleep(0.4)
        return False

    def wait_until(self, predicate: Callable[[str], bool], *, timeout_seconds: float) -> bool:
        """Poll until ``predicate(visible_text)`` is true; False on timeout."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if predicate(self.visible_text()):
                return True
            time.sleep(0.4)
        return False


class EventStore:
    """Read-side view of the collector's events.ndjson."""

    def __init__(self, path: Path) -> None:
        """Bind to one events file (which may not exist yet)."""

        self.m_path = path

    def rows(self) -> list[dict[str, Any]]:
        """Return all parsed envelope rows, skipping corrupt lines."""

        if not self.m_path.is_file():
            return []
        parsed: list[dict[str, Any]] = []
        with self.m_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    parsed.append(row)
        return parsed

    def provider_events(self) -> list[dict[str, Any]]:
        """Return every provider payload in order."""

        events: list[dict[str, Any]] = []
        for row in self.rows():
            provider = row.get("provider_event")
            if isinstance(provider, dict):
                events.append(provider)
        return events

    def event_names(self) -> list[str]:
        """Return the hook_event_name of every recorded event in order."""

        return [str(event.get("hook_event_name") or "unknown") for event in self.provider_events()]

    def count(self, name: str) -> int:
        """Count recorded events with one hook_event_name."""

        return sum(1 for item in self.event_names() if item == name)

    def wait_for_count(self, name: str, target: int, *, timeout_seconds: float) -> bool:
        """Poll until ``target`` events with ``name`` exist; False on timeout."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.count(name) >= target:
                return True
            time.sleep(0.5)
        return False

    def provider_field(self, event_name: str, field_name: str, *, occurrence: int = -1) -> Any:
        """Return one field from the Nth provider payload of an event, or None."""

        matches = [
            event for event in self.provider_events() if event.get("hook_event_name") == event_name
        ]
        if not matches:
            return None
        try:
            event = matches[occurrence]
        except IndexError:
            return None
        return event.get(field_name)

    def snapshot_index(self) -> int:
        """Return the current number of envelope rows."""

        return len(self.rows())

    def names_since(self, index: int) -> list[str]:
        """Return event names recorded at or after one row index."""

        return [
            str(row.get("provider_event", {}).get("hook_event_name") or "unknown")
            for row in self.rows()[index:]
            if isinstance(row.get("provider_event"), dict)
        ]

    def rows_since(self, index: int) -> list[dict[str, Any]]:
        """Return envelope rows recorded at or after one row index."""

        return self.rows()[index:]


class RunState:
    """Per-run mutable state shared across scenario step functions."""

    def __init__(
        self,
        *,
        spec: ScenarioSpec,
        run_root: Path,
        workdir: Path,
        kimi_home: Path,
        collector_store: Path,
        token: str,
        generation: int,
        hooks_enabled: bool,
        kimi_binary_info: dict[str, Any],
    ) -> None:
        """Initialize state for one scenario run."""

        self.m_spec = spec
        self.m_scenario = spec.name
        self.m_run_root = run_root
        self.m_workdir = workdir
        self.m_kimi_home = kimi_home
        self.m_collector_store = collector_store
        self.m_token = token
        self.m_generation = generation
        self.m_hooks_enabled = hooks_enabled
        self.m_kimi_binary_info = kimi_binary_info
        self.m_input_log = run_root / "driver-input-events.ndjson"
        self.m_events = EventStore(collector_store / EVENTS_FILENAME)
        self.m_notes: list[str] = []
        self.m_generations: list[dict[str, Any]] = []
        self.m_drivers: dict[str, PaneDriver] = {}
        self.m_aborted: str | None = None
        self.m_session_end_observed: bool | None = None
        self.m_permission_timings: list[dict[str, Any]] = []
        self.m_extra: dict[str, Any] = {}
        self.m_times: dict[str, dict[str, Any]] = {}
        self.m_exit_attempts: list[dict[str, Any]] = []
        self.m_launched_monotonic: float | None = None
        self.m_launched_at_utc: str | None = None
        self.m_launch_env: Any | None = None
        self.m_hook_info: dict[str, Any] | None = None

    def note(self, text: str) -> None:
        """Append one run-note line echoed into run-summary.json."""

        self.m_notes.append(text)

    def log(self, action: str, **detail: Any) -> None:
        """Append one timestamped runner-level action to the input-event log."""

        row: dict[str, Any] = {
            "ts_utc": utc_now_ms(),
            "monotonic": round(time.monotonic(), 6),
            "scenario": self.m_scenario,
            "action": action,
        }
        if detail:
            row["detail"] = detail
        _append_jsonl(self.m_input_log, row)

    def mark_time(self, name: str) -> dict[str, Any]:
        """Record one named UTC plus monotonic stamp."""

        stamp = {"utc": utc_now_ms(), "monotonic": round(time.monotonic(), 6)}
        self.m_times[name] = stamp
        return stamp

    def mark_launch(self) -> None:
        """Record the launch instant used for time-to-ready measurements."""

        self.m_launched_monotonic = time.monotonic()
        self.m_launched_at_utc = utc_now_ms()
        self.m_times["launch"] = {
            "utc": self.m_launched_at_utc,
            "monotonic": round(self.m_launched_monotonic, 6),
        }

    def save_surface_snapshot(self, name: str, text: str) -> Path:
        """Persist one visible-pane snapshot under notes/ for run evidence."""

        path = self.m_run_root / "notes" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


def start_recorder(*, session_name: str, run_root: Path) -> None:
    """Start a 5 fps active pane recording for one tmux session."""

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.terminal_record",
            "start",
            "--mode",
            "active",
            "--target-session",
            session_name,
            "--tool",
            "kimi",
            "--run-root",
            str(run_root),
            "--sample-interval-seconds",
            str(RECORDER_INTERVAL_SECONDS),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"terminal_record start failed: {result.stderr.strip()}")


def stop_recorder(*, run_root: Path) -> None:
    """Stop one recorder run, tolerating an already-stopped recorder."""

    subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.terminal_record",
            "stop",
            "--run-root",
            str(run_root),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )


def launch_tmux_session(
    *, session_name: str, workdir: Path, wrapper: Path, extra_args: tuple[str, ...] = ()
) -> str:
    """Launch the wrapper in a detached 220x56 tmux session; return the pane id."""

    if run_tmux(["has-session", "-t", session_name]).returncode == 0:
        raise RuntimeError(f"tmux session {session_name} already exists")
    pane_command = "bash " + _shell_single_quote(str(wrapper))
    for arg in extra_args:
        pane_command += " " + _shell_single_quote(arg)
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
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        panes = run_tmux(["list-panes", "-t", session_name, "-F", "#{pane_id}"])
        if panes.returncode == 0 and panes.stdout.strip():
            pane_id = panes.stdout.splitlines()[0].strip()
            break
        time.sleep(0.5)
    if not pane_id:
        raise RuntimeError(f"no pane found for tmux session {session_name}")
    return pane_id


def pane_pid(pane_id: str) -> int | None:
    """Return the pane's shell pid, or None when tmux cannot report it."""

    result = run_tmux(["display-message", "-p", "-t", pane_id, "#{pane_pid}"])
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def kill_tmux_session(session_name: str) -> None:
    """Kill one campaign-owned tmux session, ignoring absence."""

    run_tmux(["kill-session", "-t", session_name])


def session_alive(session_name: str) -> bool:
    """Return True while the tmux session still exists."""

    return run_tmux(["has-session", "-t", session_name]).returncode == 0


def kill_process_tree(pid: int) -> list[int]:
    """SIGKILL one pid and every descendant; return the pids signalled."""

    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid="], capture_output=True, text=True, timeout=20, check=False
    )
    children: dict[int, list[int]] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            child_pid, parent_pid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        children.setdefault(parent_pid, []).append(child_pid)
    ordered: list[int] = []
    stack = [pid]
    while stack:
        current = stack.pop()
        ordered.append(current)
        stack.extend(children.get(current, []))
    signalled: list[int] = []
    for target in reversed(ordered):
        try:
            os.kill(target, signal.SIGKILL)
            signalled.append(target)
        except (ProcessLookupError, PermissionError):
            continue
    return signalled


def _wait_for_event_name(path: Path, name: str, *, timeout_seconds: float) -> bool:
    """Poll events.ndjson until one hook_event_name appears; False on timeout."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    provider = row.get("provider_event")
                    if isinstance(provider, dict) and provider.get("hook_event_name") == name:
                        return True
        time.sleep(0.3)
    return False


def _find_event_row(path: Path, name: str) -> dict[str, Any] | None:
    """Return the first envelope whose provider payload has this event name."""

    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            provider = row.get("provider_event")
            if isinstance(provider, dict) and provider.get("hook_event_name") == name:
                return row
    return None


def _count_event_lines(path: Path) -> int:
    """Count non-empty lines in events.ndjson (0 when absent)."""

    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def wait_for_event(
    state: RunState, name: str, *, timeout_seconds: float, occurrence: int = 1
) -> bool:
    """Wait for the Nth occurrence of one event; log and return the result."""

    found = state.m_events.wait_for_count(name, occurrence, timeout_seconds=timeout_seconds)
    state.log(
        "wait-event-result",
        event=name,
        occurrence=occurrence,
        found=found,
        timeout_seconds=timeout_seconds,
    )
    return found


def wait_for_any_event(
    state: RunState, names: tuple[str, ...], *, timeout_seconds: float, occurrence: int = 1
) -> str | None:
    """Wait until any named event reaches the requested count; return its name."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for name in names:
            if state.m_events.count(name) >= occurrence:
                state.log("wait-any-event-result", event=name, occurrence=occurrence, found=True)
                return name
        time.sleep(0.5)
    state.log("wait-any-event-result", events=list(names), occurrence=occurrence, found=False)
    return None


def composer_ready(text: str) -> bool:
    """Return True when the pane shows Kimi's idle composer surface.

    Kimi 2.2.0 renders the TUI inline from the top of the pane, not
    bottom-anchored: the welcome box, the session-less notice, the editor, and
    the ``context:`` footer all sit in the first ~22 rows of a 56-row pane,
    with blank rows below. Readiness therefore scans the whole visible pane for
    the footer plus one companion marker; the startup waiter adds a stability
    window so a transient splash is not mistaken for a ready composer.
    """

    if COMPOSER_FOOTER_MARKER not in text:
        return False
    return (
        any(marker in text for marker in COMPOSER_WELCOME_MARKERS)
        or COMPOSER_DIRECTORY_MARKER in text
        or COMPOSER_EDITOR_BORDER in text
    )


def wait_for_startup_surface(
    driver: PaneDriver,
    *,
    timeout_seconds: float = 150.0,
    poll_seconds: float = 0.4,
    on_poll: Callable[[str, bool], None] | None = None,
) -> tuple[str, str]:
    """Return ``("trust"|"composer"|"timeout", pane_text)`` for a startup surface."""

    deadline = time.monotonic() + timeout_seconds
    composer_since: float | None = None
    text = ""
    while time.monotonic() < deadline:
        text = driver.visible_text()
        if on_poll is not None:
            on_poll(text, composer_ready(text))
        if any(marker in text for marker in TRUST_MODAL_MARKERS):
            return "trust", text
        if composer_ready(text):
            if composer_since is None:
                composer_since = time.monotonic()
            elif time.monotonic() - composer_since >= COMPOSER_STABLE_SECONDS:
                text = driver.visible_text()
                if any(marker in text for marker in TRUST_MODAL_MARKERS):
                    return "trust", text
                return "composer", text
        else:
            composer_since = None
        time.sleep(poll_seconds)
    return "timeout", text


def bootstrap_session(state: RunState, *, driver: PaneDriver, launch_mark: str = "launch") -> None:
    """Wait for a ready composer without keypresses; abort on a trust modal.

    Parameters
    ----------
    state:
        Per-run state.
    driver:
        Pane driver for the launching session.
    launch_mark:
        Name of the ``state.m_times`` stamp to measure readiness against.
        The S7 resume generation uses ``resume_launch`` so its ready time is
        not polluted by the first generation's lifetime.
    """

    poll_log: list[dict[str, Any]] = []

    def _poll(text: str, ready: bool) -> None:
        """Record periodic surface diagnostics without spamming the input log."""

        poll_log.append({"chars": len(text), "ready": ready})
        if len(poll_log) % 25 == 0:
            state.log(
                "startup-surface-poll",
                poll=len(poll_log),
                chars=len(text),
                ready=ready,
                tail=text[-200:],
            )

    surface, text = wait_for_startup_surface(driver, timeout_seconds=150.0, on_poll=_poll)
    if surface == "trust":
        snapshot = state.save_surface_snapshot(f"{state.m_scenario}-trust-modal.txt", text)
        state.log("workspace-trust-modal-visible", snapshot=str(snapshot))
        state.note(f"workspace trust surface visible; snapshot saved to {snapshot}")
        raise AbortRun(
            "workspace trust modal appeared despite a pre-seeded trust record; "
            "inspect the record shape before running the matrix"
        )
    if surface == "timeout":
        snapshot = state.save_surface_snapshot(f"{state.m_scenario}-startup-timeout.txt", text)
        state.log(
            "startup-surface-timeout",
            chars=len(text),
            polls=len(poll_log),
            last_polls=poll_log[-5:],
            snapshot=str(snapshot),
        )
        raise AbortRun("startup surface did not settle within 150s (no composer)")
    state.mark_time("ready")
    launch = state.m_times.get(launch_mark)
    if launch is not None:
        state.m_extra["ready_seconds"] = round(time.monotonic() - float(launch["monotonic"]), 3)
        state.m_extra["ready_launch_mark"] = launch_mark
    state.save_surface_snapshot(f"{state.m_scenario}-bootstrap-surface.txt", driver.visible_text())
    state.log(
        "composer-ready",
        zero_keypress=True,
        ready_seconds=state.m_extra.get("ready_seconds"),
        launch_mark=launch_mark,
    )


def require_session_start(
    state: RunState, *, occurrence: int = 1, timeout_seconds: float = 30.0
) -> None:
    """Require the Nth SessionStart without submitting a prompt.

    Kept for the resume generation, where ``--continue`` creates or restores
    the session at launch. Fresh TUI lanes must use
    :func:`require_session_start_after_prompt` instead.
    """

    found = wait_for_event(
        state, "SessionStart", timeout_seconds=timeout_seconds, occurrence=occurrence
    )
    if not found:
        raise AbortRun(
            f"SessionStart occurrence {occurrence} did not arrive within "
            f"{timeout_seconds:.0f}s; hooks are not active"
        )
    state.mark_time(f"session_start_{occurrence}")
    if state.m_launched_monotonic is not None:
        state.m_extra[f"session_start_{occurrence}_seconds"] = round(
            time.monotonic() - state.m_launched_monotonic, 3
        )
    source = state.m_events.provider_field("SessionStart", "source", occurrence=occurrence - 1)
    state.note(f"SessionStart occurrence {occurrence} source={source!r}")


def session_start_evidence(
    state: RunState, *, occurrence: int, since_monotonic: float
) -> dict[str, Any]:
    """Return delay and source of the Nth SessionStart relative to a stamp."""

    rows = [
        row
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "SessionStart"
    ]
    index = occurrence - 1
    seconds: float | None = None
    if 0 <= index < len(rows):
        seconds = round(float(rows[index]["received_at_monotonic"]) - since_monotonic, 3)
    source = state.m_events.provider_field("SessionStart", "source", occurrence=index)
    payload = {
        "occurrence": occurrence,
        "seconds_after_prompt": seconds,
        "source": source,
        "received_at_utc": rows[index].get("received_at_utc") if 0 <= index < len(rows) else None,
    }
    state.m_extra[f"session_start_{occurrence}_after_prompt_seconds"] = seconds
    state.m_extra[f"session_start_{occurrence}_source"] = source
    return payload


def require_session_start_after_prompt(
    state: RunState,
    driver: PaneDriver,
    prompt: str,
    *,
    occurrence: int = 1,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Submit the session-creating prompt, then require SessionStart within 15 s."""

    stamp = state.mark_time(f"prompt_submit_{occurrence}")
    since = float(stamp["monotonic"])
    driver.submit_text(prompt)
    found = wait_for_event(
        state, "SessionStart", timeout_seconds=timeout_seconds, occurrence=occurrence
    )
    evidence = session_start_evidence(state, occurrence=occurrence, since_monotonic=since)
    if not found:
        raise AbortRun(
            f"SessionStart occurrence {occurrence} did not arrive within "
            f"{timeout_seconds:.0f}s of the session-creating prompt"
        )
    state.note(
        f"SessionStart occurrence {occurrence} after prompt: "
        f"{evidence['seconds_after_prompt']}s source={evidence['source']!r}"
    )
    return evidence


def _record_session_end(
    state: RunState, *, occurrence: int = 1, timeout_seconds: float = 15.0
) -> bool:
    """Wait briefly for SessionEnd and record whether it arrived."""

    observed = state.m_events.wait_for_count(
        "SessionEnd", occurrence, timeout_seconds=timeout_seconds
    )
    state.m_session_end_observed = observed
    state.mark_time(f"session_end_{occurrence}")
    state.note(f"SessionEnd occurrence {occurrence} observed after exit: {observed}")
    return observed


def exit_kimi(
    state: RunState, *, driver: PaneDriver, session_name: str, occurrence: int = 1
) -> dict[str, Any]:
    """Exit Kimi through a clean path, falling back to documented key sequences.

    The primary path is ``/exit`` (idle-only slash command), which lets
    ``SessionEnd(reason=exit)`` fire. Fallbacks are the documented double-press
    ``Ctrl-C`` and ``Ctrl-D`` sequences. The successful mechanism is recorded.
    """

    attempt: dict[str, Any] = {
        "occurrence": occurrence,
        "started_at_utc": utc_now_ms(),
        "started_monotonic": round(time.monotonic(), 6),
        "session": session_name,
        "path": None,
        "duration_seconds": None,
    }
    if not session_alive(session_name):
        attempt["path"] = "already_gone"
        attempt["duration_seconds"] = 0.0
        state.m_exit_attempts.append(attempt)
        state.note(f"tmux session {session_name} already gone before exit step")
        return attempt

    started = time.monotonic()
    driver.send_key("C-u")
    time.sleep(0.3)
    state.log("exit-via-slash-exit", command=EXIT_COMMAND)
    driver.submit_text(EXIT_COMMAND)
    if _wait_session_gone(session_name, SESSION_GONE_TIMEOUT_SECONDS):
        attempt["path"] = "slash_exit"
    else:
        for keys in EXIT_FALLBACK_SEQUENCES:
            state.log("exit-fallback-keys", keys=list(keys))
            for key in keys:
                driver.send_key(key)
                time.sleep(0.8)
            if _wait_session_gone(session_name, 12.0):
                attempt["path"] = "keys:" + "+".join(keys)
                break
    if attempt["path"] is None:
        attempt["path"] = "still_alive"
        state.note(f"WARNING: tmux session {session_name} still alive after exit attempts")
    attempt["duration_seconds"] = round(time.monotonic() - started, 3)
    attempt["finished_at_utc"] = utc_now_ms()
    attempt["finished_monotonic"] = round(time.monotonic(), 6)
    state.m_exit_attempts.append(attempt)
    state.note(
        f"exit occurrence {occurrence} via {attempt['path']} in {attempt['duration_seconds']}s"
    )
    return attempt


def _wait_session_gone(session_name: str, timeout_seconds: float) -> bool:
    """Poll until the tmux session disappears; False on timeout."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not session_alive(session_name):
            return True
        time.sleep(0.5)
    return False


def _permission_options(text: str) -> list[dict[str, str]]:
    """Parse numbered approval-panel options from the bottom of the pane."""

    options: list[dict[str, str]] = []
    tail = "\n".join(text.splitlines()[-PERMISSION_OPTION_SCAN_LINES:])
    for line in tail.splitlines():
        match = PERMISSION_OPTION_PATTERN.match(line)
        if match is None:
            continue
        options.append({"index": match.group(1), "label": match.group(2).strip()})
    return options


def _pick_approve_key(options: list[dict[str, str]]) -> tuple[str, str | None]:
    """Choose the numbered approve key from runtime-discovered option labels."""

    exact = [option for option in options if option["label"].strip().lower() == "approve"]
    if exact:
        return exact[0]["index"], exact[0]["label"]
    loose = [
        option
        for option in options
        if option["label"].strip().lower().startswith("approve")
        and "session" not in option["label"].lower()
    ]
    if loose:
        return loose[0]["index"], loose[0]["label"]
    if options:
        return options[0]["index"], options[0]["label"]
    return "1", None


def _permission_step(
    state: RunState,
    *,
    driver: PaneDriver,
    prompt: str,
    label_id: str,
    occurrence: int,
    snapshot_name: str,
    mode: str,
) -> dict[str, Any]:
    """Drive one allow or deny permission cycle and record timing evidence.

    Approve keys are discovered from the pane's numbered options. Deny uses
    ``Escape``, which the Kimi keyboard reference documents as a direct reject
    without entering the feedback-input state some Reject options require.
    """

    submitted_at_utc = utc_now_ms()
    submitted_monotonic = time.monotonic()
    driver.submit_text(prompt)
    request_seen = wait_for_event(
        state, "PermissionRequest", timeout_seconds=120.0, occurrence=occurrence
    )
    modal_seen = driver.wait_any(PERMISSION_PROMPT_MARKERS, timeout_seconds=90.0)
    modal_text = driver.visible_text()
    snapshot = state.save_surface_snapshot(snapshot_name, modal_text)
    options = _permission_options(modal_text)
    key: str | None = None
    chosen_label: str | None = None
    if modal_seen and mode == "allow":
        key, chosen_label = _pick_approve_key(options)
        driver.send_key(key)
        time.sleep(1.0)
    elif modal_seen and mode == "deny":
        key = "Escape"
        chosen_label = next(
            (
                option["label"]
                for option in options
                if "reject" in option["label"].lower() or "deny" in option["label"].lower()
            ),
            None,
        )
        driver.send_key(key)
        time.sleep(1.0)
    else:
        state.note(f"DEVIATION: no permission modal visible for {label_id}; key not pressed")
        raise AbortRun(
            f"permission prompt not detected for {label_id}; surface snapshot saved to {snapshot}"
        )

    timing = {
        "label_id": label_id,
        "mode": mode,
        "prompt": prompt,
        "key": key,
        "chosen_label": chosen_label,
        "detected_options": options,
        "permission_request_seen": request_seen,
        "modal_seen": modal_seen,
        "submitted_at_utc": submitted_at_utc,
        "submitted_monotonic": round(submitted_monotonic, 6),
        "settled_at_utc": utc_now_ms(),
        "settled_monotonic": round(time.monotonic(), 6),
        "snapshot": str(snapshot),
    }
    state.m_permission_timings.append(timing)
    state.log("label-window", label_id=label_id)
    return timing


def _hot_reload_marker_entry(marker_path: Path) -> str:
    """Render the H1 marker hook entry for one run."""

    return kimi_hooks.render_hook_entry(
        event="UserPromptSubmit",
        command=f"touch {shlex.quote(str(marker_path))}",
        timeout=DEFAULT_HOOK_TIMEOUT_SECONDS,
    )


def _append_hot_reload_marker(state: RunState, *, reason: str) -> Path:
    """Append the H1 marker hook to the scratch config without validation."""

    marker_path = state.m_run_root / "hot-reload-marker"
    config_path = state.m_kimi_home / "config.toml"
    kimi_hooks.append_raw_toml_block(
        config_path,
        _hot_reload_marker_entry(marker_path),
        reason=reason,
    )
    state.m_extra.setdefault("hot_reload_appends", []).append(
        {
            "at_utc": utc_now_ms(),
            "reason": reason,
            "marker_path": str(marker_path),
            "config_sha256": _sha256_file(config_path),
            "validated": False,
        }
    )
    state.note(f"appended H1 marker hook without validation ({reason})")
    return marker_path


def run_s0(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S0 gate arm (amended G1): prompt creates the session, then SS/UPS/Stop."""

    state.log("label-window", label_id="s0-ready")
    prompt_stamp = state.mark_time("prompt_submit")
    prompt_monotonic = float(prompt_stamp["monotonic"])
    driver.submit_text(PROMPT_OK)
    session_start_seen = wait_for_event(state, "SessionStart", timeout_seconds=15.0)
    session_start_source = state.m_events.provider_field("SessionStart", "source", occurrence=0)
    ss_rows = [
        row
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "SessionStart"
    ]
    session_start_seconds_after_prompt = (
        round(float(ss_rows[0]["received_at_monotonic"]) - prompt_monotonic, 3) if ss_rows else None
    )
    if not session_start_seen:
        state.m_extra["g1"] = {
            "ready_seconds": state.m_extra.get("ready_seconds"),
            "prompt_submit_monotonic": prompt_monotonic,
            "session_start_seen": False,
            "session_start_seconds_after_prompt": None,
        }
        state.note("S0 amended G1: SessionStart absent within 15s of the frozen prompt")
        raise AbortRun(
            "SessionStart did not arrive within 15s of the frozen prompt; hooks are not active"
        )
    if session_start_source != "startup":
        state.note(f"DEVIATION: SessionStart source={session_start_source!r}, expected 'startup'")

    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    state.log("label-window", label_id="s0-turn-ok")
    stop_seen = wait_for_event(state, "Stop", timeout_seconds=120.0)
    ups_deliveries = state.m_events.count("UserPromptSubmit")
    names = state.m_events.event_names()

    def first_index(name: str) -> int | None:
        """Return the first sequence index of one event name."""

        return names.index(name) if name in names else None

    ss_index = first_index("SessionStart")
    ups_index = first_index("UserPromptSubmit")
    stop_index = first_index("Stop")
    ordered_before_turn = (
        ss_index is not None
        and ups_index is not None
        and stop_index is not None
        and ss_index <= ups_index
        and ss_index <= stop_index
    )
    ready_seconds = state.m_extra.get("ready_seconds")
    g1_checks = {
        "ready_within_15s": isinstance(ready_seconds, (int, float)) and ready_seconds <= 15.0,
        "session_start_within_15s_of_prompt": isinstance(
            session_start_seconds_after_prompt, (int, float)
        )
        and session_start_seconds_after_prompt <= 15.0,
        "session_start_source_startup": session_start_source == "startup",
        "session_start_no_later_than_turn_events": ordered_before_turn,
        "stop_seen": stop_seen,
    }
    g1_passed = all(g1_checks.values())
    hook_info = state.m_hook_info or {}
    state.m_extra["g1"] = {
        "amended": True,
        "passed": g1_passed,
        "checks": g1_checks,
        "ready_seconds": ready_seconds,
        "prompt_submit_monotonic": prompt_monotonic,
        "session_start_seen": session_start_seen,
        "session_start_source": session_start_source,
        "session_start_seconds_after_prompt": session_start_seconds_after_prompt,
        "event_order_indices": {
            "SessionStart": ss_index,
            "UserPromptSubmit": ups_index,
            "Stop": stop_index,
        },
        "stop_seen": stop_seen,
        "user_prompt_submit_deliveries": ups_deliveries,
        "dedup_holds": ups_deliveries == 1,
        "dedup_probe": hook_info.get("dedup_probe"),
    }
    state.note(
        "S0 amended G1: ready="
        f"{ready_seconds}s, SessionStart={session_start_seconds_after_prompt}s after prompt, "
        f"source={session_start_source!r}, Stop={stop_seen}, "
        f"UserPromptSubmit deliveries={ups_deliveries} (dedup holds={ups_deliveries == 1})"
    )
    if not g1_passed:
        raise AbortRun(f"S0 amended G1 failed: {g1_checks}")
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s1(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S1 normal arm: three turns, heartbeat hold, mid-session load-once probe."""

    require_session_start_after_prompt(state, driver, PROMPT_OK)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "Stop", timeout_seconds=120.0)
    state.log("label-window", label_id="s1-turn-1")

    driver.submit_text(PROMPT_TOOL)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0, occurrence=2)
    wait_for_event(state, "Stop", timeout_seconds=300.0, occurrence=2)
    state.log("label-window", label_id="s1-turn-2")

    if state.m_launched_monotonic is not None:
        remaining = HEARTBEAT_HOLD_SECONDS - (time.monotonic() - state.m_launched_monotonic)
        if remaining > 0:
            state.log("heartbeat-hold", seconds=round(remaining, 3))
            time.sleep(remaining)
    state.log("label-window", label_id="s1-heartbeat-hold")
    state.m_extra["session_heartbeat_count"] = state.m_events.count("SessionHeartbeat")
    state.m_extra["session_heartbeat_uptime_ms"] = [
        event.get("uptime_ms")
        for event in state.m_events.provider_events()
        if event.get("hook_event_name") == "SessionHeartbeat"
    ]

    marker_path = _append_hot_reload_marker(state, reason="S1 mid-session H1 probe")
    state.m_extra["hot_reload_marker_present_before_prompt"] = marker_path.exists()
    state.log("label-window", label_id="s1-hot-reload-probe")
    driver.submit_text(PROMPT_OK)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0, occurrence=3)
    time.sleep(2.0)
    marker_fired = marker_path.exists()
    state.m_extra["hot_reload_marker_fired_mid_session"] = marker_fired
    state.note(
        "H1 mid-session probe: marker "
        f"{'FIRED (load-once violated)' if marker_fired else 'absent (load-once holds)'}"
    )
    wait_for_event(state, "Stop", timeout_seconds=180.0, occurrence=3)

    tool_ids: dict[str, list[str]] = {"PreToolUse": [], "PostToolUse": []}
    for event in state.m_events.provider_events():
        name = str(event.get("hook_event_name") or "")
        if name in tool_ids:
            value = event.get("tool_call_id")
            tool_ids[name].append(str(value) if value is not None else "")
    state.m_extra["tool_call_ids"] = tool_ids
    state.note(
        "tool events: PreToolUse="
        f"{len(tool_ids['PreToolUse'])} PostToolUse={len(tool_ids['PostToolUse'])}"
    )

    state.log("label-window", label_id="s1-exit")
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s2(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S2 malformed control: the whole hooks section must be dead."""

    state.log("label-window", label_id="s2-startup")
    state.save_surface_snapshot("s2-startup-surface.txt", driver.visible_text())
    driver.submit_text(PROMPT_OK)
    wait_for_event(state, "Stop", timeout_seconds=10.0)
    # The frozen prompt itself contains "OK", so a single occurrence is echoed
    # input. A completed answer adds a second occurrence in the transcript.
    answered = driver.wait_until(lambda text: text.count("OK") >= 2, timeout_seconds=180.0)
    state.save_surface_snapshot("s2-post-answer-surface.txt", driver.visible_text())
    state.m_extra["s2_pane_answer_visible"] = answered
    before_probe = len(state.m_events.rows())
    state.m_extra["s2_event_count_before_probe"] = before_probe
    if before_probe:
        state.note(f"DEVIATION: {before_probe} events arrived despite the malformed hooks entry")
    state.note(f"S2 TUI: answer visible={answered}; events collected={before_probe}")
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state, timeout_seconds=5.0)

    state.log("label-window", label_id="s2-print-probe")
    probe = _run_s2_print_probe(state)
    state.m_extra["s2_print_probe"] = probe
    after_probe = len(state.m_events.rows())
    state.m_extra["s2_event_count_after_probe"] = after_probe
    if after_probe:
        state.note(f"DEVIATION: {after_probe} events arrived after the malformed -p probe")
    state.note(
        f"S2 -p probe rc={probe.get('returncode')} "
        f"warning_mentions_hooks={probe.get('warning_mentions_hooks')}"
    )


def _run_s2_print_probe(state: RunState) -> dict[str, Any]:
    """Run the paired ``kimi -p`` stderr probe against the malformed home."""

    stdout_path = state.m_run_root / "s2-print-probe.stdout.txt"
    stderr_path = state.m_run_root / "s2-print-probe.stderr.txt"
    env = os.environ.copy()
    env["KIMI_CODE_HOME"] = str(state.m_kimi_home)
    env["KIMI_CODE_NO_AUTO_UPDATE"] = "1"
    env["HOUMAO_HOOK_COLLECTOR_URL"] = ""
    env["HOUMAO_HOOK_TOKEN"] = ""
    env["HOUMAO_HOOK_STORE"] = str(state.m_collector_store)
    env["HOUMAO_HOOK_GENERATION"] = "1"
    started = time.monotonic()
    result: dict[str, Any] = {
        "command": [state.m_kimi_binary_info["path"], "-p", PROMPT_OK],
        "started_at_utc": utc_now_ms(),
        "started_monotonic": round(started, 6),
        "returncode": None,
        "timed_out": False,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "warning_lines": [],
        "warning_mentions_hooks": False,
    }
    try:
        completed = subprocess.run(
            [state.m_kimi_binary_info["path"], "-p", PROMPT_OK],
            cwd=str(state.m_workdir),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        result["returncode"] = completed.returncode
        warning_lines = [
            line[:500]
            for line in completed.stderr.splitlines()
            if re.search(r"hook|config", line, re.IGNORECASE)
        ][:20]
        result["warning_lines"] = warning_lines
        result["warning_mentions_hooks"] = any("hook" in line.lower() for line in warning_lines)
    except subprocess.TimeoutExpired as exc:
        result["timed_out"] = True
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
    result["finished_at_utc"] = utc_now_ms()
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result


def run_s3(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S3 permission lane: approve once, deny once, record runtime-discovered keys."""

    allow = _permission_step(
        state,
        driver=driver,
        prompt=PROMPT_ALLOW,
        label_id="s3-permission-allow",
        occurrence=1,
        snapshot_name="s3-allow-modal.txt",
        mode="allow",
    )
    ss_seen = wait_for_event(state, "SessionStart", timeout_seconds=15.0)
    ss_evidence = session_start_evidence(
        state, occurrence=1, since_monotonic=float(allow["submitted_monotonic"])
    )
    if not ss_seen:
        raise AbortRun("SessionStart did not arrive within 15s of the allow prompt")
    state.note(
        f"S3 SessionStart after allow prompt: {ss_evidence['seconds_after_prompt']}s "
        f"source={ss_evidence['source']!r}"
    )
    permission_result_1 = wait_for_event(
        state, "PermissionResult", timeout_seconds=90.0, occurrence=1
    )
    stop_after_allow = wait_for_event(state, "Stop", timeout_seconds=180.0)
    state.m_extra["s3_allow"] = {
        **allow,
        "session_start": ss_evidence,
        "permission_result_seen": permission_result_1,
        "decision": state.m_events.provider_field("PermissionResult", "decision", occurrence=0),
        "tool_call_id": state.m_events.provider_field(
            "PermissionResult", "tool_call_id", occurrence=0
        ),
        "stop_after_allow": stop_after_allow,
    }

    deny = _permission_step(
        state,
        driver=driver,
        prompt=PROMPT_DENY,
        label_id="s3-permission-deny",
        occurrence=2,
        snapshot_name="s3-deny-modal.txt",
        mode="deny",
    )
    permission_result_2 = wait_for_event(
        state, "PermissionResult", timeout_seconds=90.0, occurrence=2
    )
    settle_name = wait_for_any_event(
        state, ("Interrupt", "Stop"), timeout_seconds=30.0, occurrence=2
    )
    state.m_extra["s3_deny"] = {
        **deny,
        "permission_result_seen": permission_result_2,
        "decision": state.m_events.provider_field("PermissionResult", "decision", occurrence=1),
        "tool_call_id": state.m_events.provider_field(
            "PermissionResult", "tool_call_id", occurrence=1
        ),
        "settle_event": settle_name,
    }
    state.note(
        "S3 deny settle event: "
        f"{settle_name or 'none within 30s'}; approve key={allow.get('key')!r}"
    )
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s4(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S4 compaction arm: README turn, /compact, post-compact turn."""

    require_session_start_after_prompt(state, driver, PROMPT_README)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "Stop", timeout_seconds=180.0)
    state.log("label-window", label_id="s4-readme-turn")

    state.log("label-window", label_id="s4-compact")
    driver.submit_text("/compact")
    pre_compact = wait_for_event(state, "PreCompact", timeout_seconds=90.0)
    post_compact = wait_for_event(state, "PostCompact", timeout_seconds=240.0)
    state.m_extra["s4_compact"] = {
        "pre_compact": pre_compact,
        "post_compact": post_compact,
        "pre_trigger": state.m_events.provider_field("PreCompact", "trigger"),
        "post_trigger": state.m_events.provider_field("PostCompact", "trigger"),
        "pre_fields": _event_field_names(state, "PreCompact"),
        "post_fields": _event_field_names(state, "PostCompact"),
    }
    state.note(f"S4 compaction: PreCompact={pre_compact} PostCompact={post_compact}")

    driver.submit_text(PROMPT_OK)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0, occurrence=2)
    stop_2 = wait_for_event(state, "Stop", timeout_seconds=180.0, occurrence=2)
    state.log("label-window", label_id="s4-post-compact-turn")
    state.note(f"S4 post-compact Stop: {stop_2}")
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def _event_field_names(state: RunState, event_name: str) -> list[str]:
    """Return sorted top-level field names for the first payload of an event."""

    for event in state.m_events.provider_events():
        if event.get("hook_event_name") == event_name:
            return sorted(event)
    return []


def run_s5(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S5 interrupt arm: Esc mid-generation; Interrupt should replace Stop."""

    state.log("label-window", label_id="s5-generation")
    require_session_start_after_prompt(state, driver, PROMPT_RECURSION)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    turn_started = wait_for_event(state, "TurnStarted", timeout_seconds=30.0)
    time.sleep(2.5)
    stop_before = state.m_events.count("Stop")
    state.log("interrupt-escape", keys=["Escape"], turn_started=turn_started)
    driver.send_key("Escape")
    interrupt_seen = wait_for_event(state, "Interrupt", timeout_seconds=120.0)
    time.sleep(5.0)
    stop_after = state.m_events.count("Stop")
    state.m_extra["s5_interrupt"] = {
        "turn_started": turn_started,
        "interrupt_seen": interrupt_seen,
        "stop_count_before": stop_before,
        "stop_count_after": stop_after,
        "interrupt_fields": _event_field_names(state, "Interrupt"),
        "interrupt_reason": state.m_events.provider_field("Interrupt", "reason"),
    }
    state.note(f"S5 Interrupt={interrupt_seen}; Stop count before={stop_before} after={stop_after}")
    state.log("label-window", label_id="s5-post-escape")
    time.sleep(3.0)
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s6(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S6 queue/steer arm: second prompt while busy; record drain ordering."""

    require_session_start_after_prompt(state, driver, PROMPT_QUEUES)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "TurnStarted", timeout_seconds=30.0)
    time.sleep(2.0)
    state.log("label-window", label_id="s6-queued-turn")
    driver.send_text(PROMPT_OK)
    time.sleep(0.2)
    driver.send_key("C-s")
    queued = wait_for_event(state, "UserPromptQueued", timeout_seconds=60.0)
    first_stop = wait_for_event(state, "Stop", timeout_seconds=300.0)
    second_prompt = wait_for_event(state, "UserPromptSubmit", timeout_seconds=120.0, occurrence=2)
    second_stop = state.m_events.wait_for_count("Stop", 2, timeout_seconds=120.0)
    event_order = state.m_events.event_names()
    prompt_turns = [
        row.get("provider_event", {}).get("turn_id")
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "UserPromptSubmit"
    ]
    queue_payload = [
        row.get("provider_event", {})
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "UserPromptQueued"
    ]
    state.m_extra["s6"] = {
        "second_input_key": "C-s",
        "queued_event_seen": queued,
        "queued_payloads": queue_payload,
        "first_stop": first_stop,
        "second_prompt": second_prompt,
        "second_stop": second_stop,
        "event_order": event_order,
        "prompt_turn_ids": prompt_turns,
        "user_prompt_is_steer": [
            row.get("provider_event", {}).get("is_steer")
            for row in state.m_events.rows()
            if row.get("provider_event", {}).get("hook_event_name") == "UserPromptSubmit"
        ],
    }
    state.note(
        f"S6 UserPromptQueued={queued} Stop#1={first_stop} "
        f"UserPromptSubmit#2={second_prompt} Stop#2={second_stop}"
    )
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s7(
    state: RunState,
    driver: PaneDriver,
    session_name: str,
    *,
    env: "LaunchEnv",
    register_session: Callable[[str, PaneDriver], None],
    recorder_roots: list[Path],
) -> None:
    """S7 resume arm: first turn, exit, H1 marker append, ``kimi --continue``."""

    require_session_start_after_prompt(state, driver, PROMPT_OK, occurrence=1)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "Stop", timeout_seconds=120.0)
    session_id = state.m_events.provider_field("SessionStart", "session_id")
    state.m_extra["s7_session_id_generation_1"] = session_id
    state.log("label-window", label_id="s7-first-turn")

    state.log("label-window", label_id="s7-exit")
    exit_kimi(state, driver=driver, session_name=session_name, occurrence=1)
    _record_session_end(state, occurrence=1)

    marker_path = _append_hot_reload_marker(state, reason="S7 between-generation H1 probe")
    state.m_extra["hot_reload_marker_present_before_resume"] = marker_path.exists()

    state.note("relaunching with `kimi --continue` (collector generation bump)")
    env.stop_collector()
    port = env.start_generation(2)
    state.m_generations.append(
        {
            "generation": 2,
            "port": port,
            "started_at_utc": utc_now_ms(),
            "started_monotonic": round(time.monotonic(), 6),
            "reason": "s7 --continue relaunch",
        }
    )
    resume_session = f"kimihook-s7-resume-{os.getpid()}"
    assert env.m_wrapper is not None
    state.mark_time("resume_launch")
    resume_pane = launch_tmux_session(
        session_name=resume_session,
        workdir=state.m_workdir,
        wrapper=env.m_wrapper,
        extra_args=("--continue",),
    )
    resume_driver = PaneDriver(
        session_name=resume_session, pane_id=resume_pane, log_path=state.m_input_log
    )
    register_session(resume_session, resume_driver)
    resume_recording_root = state.m_run_root / "pane-recording-resume"
    start_recorder(session_name=resume_session, run_root=resume_recording_root)
    recorder_roots.append(resume_recording_root)
    state.save_surface_snapshot("s7-resume-launch-surface.txt", resume_driver.visible_text())
    state.log("label-window", label_id="s7-resume")
    bootstrap_session(state, driver=resume_driver, launch_mark="resume_launch")
    resume_launch_monotonic = float(state.m_times["resume_launch"]["monotonic"])
    pre_prompt_session_start = wait_for_event(
        state, "SessionStart", timeout_seconds=15.0, occurrence=2
    )
    if pre_prompt_session_start:
        resume_ss = session_start_evidence(
            state, occurrence=2, since_monotonic=resume_launch_monotonic
        )
        resume_ss["before_prompt"] = True
        state.note(
            "S7 resume SessionStart arrived before the post-resume prompt: "
            f"{resume_ss['seconds_after_prompt']}s after resume launch, "
            f"source={resume_ss['source']!r}"
        )
    else:
        resume_ss = require_session_start_after_prompt(
            state, resume_driver, PROMPT_OK, occurrence=2
        )
        resume_ss["before_prompt"] = False
        state.note("S7 resume SessionStart arrived only after the post-resume prompt")
    state.m_extra["s7_resume_session_start"] = resume_ss
    state.m_extra["s7_resume_source"] = resume_ss.get("source")
    state.m_extra["s7_hot_reload_marker_present_before_prompt"] = marker_path.exists()
    if pre_prompt_session_start:
        resume_driver.submit_text(PROMPT_OK)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0, occurrence=2)
    marker_deadline = time.monotonic() + 20.0
    while time.monotonic() < marker_deadline and not marker_path.exists():
        time.sleep(0.5)
    marker_fired = marker_path.exists()
    state.m_extra["s7_hot_reload_marker_fired_after_restart"] = marker_fired
    state.note(
        "H1 restart probe: marker "
        f"{'FIRED after --continue' if marker_fired else 'did NOT fire after --continue'}"
    )
    resume_stop = wait_for_event(state, "Stop", timeout_seconds=180.0, occurrence=2)
    state.note(f"S7 Stop after post-resume OK prompt: {resume_stop}")
    exit_kimi(state, driver=resume_driver, session_name=resume_session, occurrence=2)
    _record_session_end(state, occurrence=2)


def run_f1(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """F1 fault arm: kill -9 the Kimi process tree mid-generation."""

    state.log("label-window", label_id="f1-generation")
    require_session_start_after_prompt(state, driver, PROMPT_FAULTS)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "TurnStarted", timeout_seconds=30.0)
    time.sleep(3.0)
    pid = pane_pid(driver.pane_id)
    state.log("kill-process-tree", pane_pid=pid)
    signalled = kill_process_tree(pid) if pid is not None else []
    state.note(f"kill -9 signalled pids: {signalled}")
    baseline = state.m_events.snapshot_index()
    state.log("label-window", label_id="f1-kill")
    time.sleep(F1_POST_KILL_OBSERVATION_SECONDS)
    after = state.m_events.names_since(baseline)
    state.m_extra["f1_post_kill_events"] = after
    state.m_extra["f1_killed_pids"] = signalled
    state.m_extra["f1_pane_pid"] = pid
    state.m_extra["f1_post_kill_observation_seconds"] = F1_POST_KILL_OBSERVATION_SECONDS
    state.note(
        f"events in {F1_POST_KILL_OBSERVATION_SECONDS:.0f}s after kill -9: {after or 'none'}"
    )
    state.m_session_end_observed = False


def run_d1(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """D1 transport fault: kill the collector after SessionStart, use file fallback."""

    state.log("label-window", label_id="d1-session-start")
    state.mark_time("prompt_submit_1")
    driver.submit_text(PROMPT_OK)
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline and state.m_events.count("SessionStart") < 1:
        time.sleep(0.05)
    if state.m_events.count("SessionStart") < 1:
        raise AbortRun("SessionStart did not arrive within 15s of the D1 prompt")
    baseline = state.m_events.snapshot_index()
    state.m_extra["d1_collector_killed_after_rows"] = baseline
    assert state.m_launch_env is not None
    state.m_launch_env.stop_collector()
    state.log("collector-killed", after_rows=baseline)
    state.note("collector stopped immediately after SessionStart; observing HTTP vs fallback split")

    state.log("label-window", label_id="d1-fallback-turn")
    ups = wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    stop = wait_for_event(state, "Stop", timeout_seconds=180.0)
    all_rows = state.m_events.rows()
    fallback_rows = [row for row in all_rows if row.get("via") == "command_fallback"]
    http_rows = [row for row in all_rows if row.get("via") == "http"]
    emitter_seqs = [
        row.get("emitter_seq") for row in fallback_rows if isinstance(row.get("emitter_seq"), int)
    ]
    state.m_extra["d1"] = {
        "user_prompt_submit": ups,
        "stop": stop,
        "http_row_count": len(http_rows),
        "fallback_row_count": len(fallback_rows),
        "http_event_names": [
            row.get("provider_event", {}).get("hook_event_name") for row in http_rows
        ],
        "fallback_sequences_null": all(row.get("sequence") is None for row in fallback_rows),
        "emitter_seqs": emitter_seqs,
        "emitter_seqs_increasing": emitter_seqs == sorted(emitter_seqs),
        "fallback_event_names": [
            row.get("provider_event", {}).get("hook_event_name") for row in fallback_rows
        ],
    }
    state.note(
        f"D1 fallback rows={len(fallback_rows)} http rows={len(http_rows)} "
        f"seqs_increasing={state.m_extra['d1']['emitter_seqs_increasing']}"
    )
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state, timeout_seconds=10.0)


def run_t1(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """T1 slow-hook arm: quantify awaited SessionStart/SessionEnd delays.

    The amended kimi TUI reality requires one short prompt to create the
    session, so this arm is no longer strictly zero-model-cost; the prompt is
    the cheapest available session trigger.
    """

    ready_seconds = state.m_extra.get("ready_seconds")
    ss_evidence = require_session_start_after_prompt(state, driver, PROMPT_OK, timeout_seconds=45.0)
    stop_seen = wait_for_event(state, "Stop", timeout_seconds=180.0)
    baseline = _load_s0_ready_baseline()
    prompt_monotonic = float(state.m_times["prompt_submit_1"]["monotonic"])
    stop_rows = [
        row
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "Stop"
    ]
    prompt_to_stop_seconds = (
        round(float(stop_rows[0]["received_at_monotonic"]) - prompt_monotonic, 3)
        if stop_rows
        else None
    )
    state.log("label-window", label_id="t1-ready-delay")
    state.m_extra["t1"] = {
        "ready_seconds": ready_seconds,
        "s0_baseline": baseline,
        "ready_delay_vs_s0_seconds": (
            round(ready_seconds - baseline["ready_seconds"], 3)
            if isinstance(ready_seconds, (int, float)) and baseline is not None
            else None
        ),
        "session_start_after_prompt_seconds": ss_evidence["seconds_after_prompt"],
        "session_start_source": ss_evidence["source"],
        "session_start_delay_vs_s0_seconds": (
            round(
                ss_evidence["seconds_after_prompt"]
                - float(baseline.get("session_start_after_prompt_seconds") or 0.0),
                3,
            )
            if baseline is not None
            and isinstance(ss_evidence.get("seconds_after_prompt"), (int, float))
            and isinstance(baseline.get("session_start_after_prompt_seconds"), (int, float))
            else None
        ),
        "stop_seen": stop_seen,
        "prompt_to_stop_seconds": prompt_to_stop_seconds,
        "model_prompt_sent": True,
        "model_cost_note": "one short OK turn; required to create the session in the TUI lane",
    }
    state.note(
        f"T1 ready in {ready_seconds}s; SessionStart {ss_evidence['seconds_after_prompt']}s "
        f"after prompt; S0 baseline {baseline}"
    )
    state.log("label-window", label_id="t1-exit-delay")
    exit_info = exit_kimi(state, driver=driver, session_name=session_name)
    session_end_observed = _record_session_end(state, timeout_seconds=20.0)
    session_end_rows = [
        row
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "SessionEnd"
    ]
    session_end_delay_seconds = (
        round(
            float(session_end_rows[0]["received_at_monotonic"])
            - float(exit_info["started_monotonic"]),
            3,
        )
        if session_end_rows and isinstance(exit_info.get("started_monotonic"), (int, float))
        else None
    )
    state.m_extra["t1"].update(
        {
            "exit_path": exit_info.get("path"),
            "exit_seconds": exit_info.get("duration_seconds"),
            "session_end_observed": session_end_observed,
            "session_end_delay_after_exit_start_seconds": session_end_delay_seconds,
            "exit_delay_vs_s0_seconds": (
                round(exit_info["duration_seconds"] - baseline["exit_seconds"], 3)
                if baseline is not None
                and isinstance(baseline.get("exit_seconds"), (int, float))
                and isinstance(exit_info.get("duration_seconds"), (int, float))
                else None
            ),
        }
    )


def run_s9(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """Optional S9 subagent arm: launch a subagent and record its events."""

    require_session_start_after_prompt(state, driver, PROMPT_SUBAGENT)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    state.log("label-window", label_id="s9-subagent-start")
    started_name = wait_for_any_event(
        state, ("SubagentStart", "TaskStarted"), timeout_seconds=180.0
    )
    stop = wait_for_event(state, "Stop", timeout_seconds=300.0)
    state.log("label-window", label_id="s9-subagent-stop")
    state.m_extra["s9"] = {
        "started_event": started_name,
        "stop": stop,
        "subagent_start_count": state.m_events.count("SubagentStart"),
        "subagent_stop_count": state.m_events.count("SubagentStop"),
        "task_started_count": state.m_events.count("TaskStarted"),
        "supplemental": True,
    }
    state.note(
        f"S9 subagent start={started_name} SubagentStop count="
        f"{state.m_events.count('SubagentStop')} Stop={stop}"
    )
    exit_kimi(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s8(state: RunState, env: "LaunchEnv") -> None:
    """S8 headless probe: ``kimi -p`` with no tmux and captured stderr."""

    state.mark_launch()
    state.log("label-window", label_id="s8-headless-start")
    stdout_path = state.m_run_root / "s8-headless.stdout.txt"
    stderr_path = state.m_run_root / "s8-headless.stderr.txt"
    process_env = env.process_env()
    result: dict[str, Any] = {
        "command": [state.m_kimi_binary_info["path"], "-p", PROMPT_OK],
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [state.m_kimi_binary_info["path"], "-p", PROMPT_OK],
            cwd=str(state.m_workdir),
            env=process_env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        result["returncode"] = completed.returncode
        result["stdout_bytes"] = len(completed.stdout.encode("utf-8"))
        result["stderr_bytes"] = len(completed.stderr.encode("utf-8"))
    except subprocess.TimeoutExpired as exc:
        result["timed_out"] = True
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    state.log("label-window", label_id="s8-headless-end")
    session_end = state.m_events.wait_for_count("SessionEnd", 1, timeout_seconds=30.0)
    result["session_end_observed"] = session_end
    result["event_names"] = state.m_events.event_names()
    result["event_counts"] = dict(sorted(Counter(result["event_names"]).items()))
    state.m_extra["s8"] = result
    state.note(f"S8 headless rc={result.get('returncode')} events={result['event_counts']}")


STEPS: dict[str, Callable[..., None]] = {
    "s0": run_s0,
    "s1": run_s1,
    "s2": run_s2,
    "s3": run_s3,
    "s4": run_s4,
    "s5": run_s5,
    "s6": run_s6,
    "s7": run_s7,
    "f1": run_f1,
    "d1": run_d1,
    "t1": run_t1,
    "s9": run_s9,
}


def _default_run_root(scenario: str) -> Path:
    """Return the default run root for one scenario."""

    return RUN_ROOT_BASE / scenario / f"run-{utc_stamp()}"


def _load_s0_ready_baseline() -> dict[str, Any] | None:
    """Return the latest amended-gate S0 ready/exit/session-start baseline."""

    candidates = sorted((RUN_ROOT_BASE / "s0").glob("run-*/launch.json"), reverse=True)
    for manifest_path in candidates:
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        timing = document.get("timing", {})
        ready_seconds = timing.get("ready_seconds")
        if not isinstance(ready_seconds, (int, float)):
            continue
        summary_path = manifest_path.with_name("run-summary.json")
        session_start_after_prompt = None
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        g1 = summary.get("extra", {}).get("g1", {})
        if not g1.get("passed"):
            continue
        session_start_after_prompt = g1.get("session_start_seconds_after_prompt")
        exit_seconds = None
        for attempt in timing.get("exit_attempts", []):
            if isinstance(attempt, dict) and isinstance(
                attempt.get("duration_seconds"), (int, float)
            ):
                exit_seconds = attempt["duration_seconds"]
                break
        return {
            "launch_json": str(manifest_path),
            "ready_seconds": ready_seconds,
            "exit_seconds": exit_seconds,
            "session_start_after_prompt_seconds": session_start_after_prompt,
        }
    return None


def write_labels_template(state: RunState, labels_dir: Path) -> None:
    """Write the labels template mirroring the scenario's predeclared windows."""

    document = {
        "schema_version": 1,
        "scenario": state.m_scenario,
        "predeclared_expectation": state.m_spec.expectation,
        "hooks_enabled": state.m_hooks_enabled,
        "time_base": {
            "collector_generations": state.m_generations,
            "note": (
                "collector started_monotonic and per-event received_at_monotonic "
                "share the system monotonic clock with the recorder and runner; "
                "pair them with the UTC stamps for pane-frame alignment"
            ),
        },
        "labels": [
            {
                "label_id": label_id,
                "scenario_id": state.m_scenario,
                "sample_id": None,
                "sample_end_id": None,
                "expectations": {
                    "surface_accepting_input": None,
                    "surface_editing_input": None,
                    "surface_ready_posture": None,
                    "surface_pending_input": "unknown",
                    "turn_phase": None,
                },
                "note": note,
                "evidence": {},
            }
            for label_id, note in state.m_spec.labels
        ],
    }
    labels_dir.mkdir(parents=True, exist_ok=True)
    (labels_dir / "labels-template.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )


def write_raw_payload_log(state: RunState, run_root: Path) -> Path:
    """Write provider payloads without collector envelope metadata."""

    path = run_root / "raw-provider-payloads.ndjson"
    with path.open("w", encoding="utf-8") as handle:
        for row in state.m_events.rows():
            provider = row.get("provider_event")
            if isinstance(provider, dict):
                handle.write(json.dumps(provider, sort_keys=True) + "\n")
    return path


def _timing_payload(state: RunState) -> dict[str, Any]:
    """Build the derived timing block for run-summary.json and launch.json."""

    payload: dict[str, Any] = {
        "ready_seconds": state.m_extra.get("ready_seconds"),
        "ready_launch_mark": state.m_extra.get("ready_launch_mark"),
        "session_start_1_seconds": state.m_extra.get("session_start_1_seconds"),
        "session_start_2_seconds": state.m_extra.get("session_start_2_seconds"),
        "exit_attempts": state.m_exit_attempts,
        "times": state.m_times,
    }
    return payload


def write_run_summary(state: RunState, run_root: Path, collector_store: Path) -> None:
    """Write run-summary.json with counts, ordering, timings, and notes."""

    names = state.m_events.event_names()
    status_path = collector_store / COLLECTOR_FILENAME
    final_status: dict[str, Any] | None = None
    if status_path.is_file():
        try:
            final_status = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            final_status = None
    summary: dict[str, Any] = {
        "schema_version": 1,
        "scenario": state.m_scenario,
        "run_root": str(run_root),
        "workdir": str(state.m_workdir),
        "kimi_home": str(state.m_kimi_home),
        "hooks_enabled": state.m_hooks_enabled,
        "aborted": state.m_aborted is not None,
        "abort_reason": state.m_aborted,
        "collector_generations": state.m_generations,
        "collector_final_status": final_status,
        "event_counts": dict(sorted(Counter(names).items())),
        "event_sequence": names,
        "session_end_observed": state.m_session_end_observed,
        "permission_timings": state.m_permission_timings,
        "exit_attempts": state.m_exit_attempts,
        "hooks": state.m_hook_info,
        "timing": _timing_payload(state),
        "extra": state.m_extra,
        "notes": state.m_notes,
        "finished_at_utc": utc_now_ms(),
        "finished_monotonic": round(time.monotonic(), 6),
    }
    (run_root / "run-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _seed_inventory(path: Path, *, kind: str) -> dict[str, Any]:
    """Describe one copied seed entry without reading its contents."""

    if kind == "file":
        stat = path.stat()
        return {
            "name": path.name,
            "kind": "file",
            "size": stat.st_size,
            "mode": oct(stat.st_mode & 0o777),
        }
    return {
        "name": path.name,
        "kind": "dir",
        "file_count": sum(1 for item in path.rglob("*") if item.is_file()),
    }


def seed_kimi_home(*, source: Path, dest: Path) -> dict[str, Any]:
    """Copy the operator's real Kimi home into an isolated scratch home.

    Required: ``config.toml``. Optional: ``credentials/``, ``oauth/``,
    ``device_id``, ``.skip-migration-from-kimi-cli``, and
    ``migrations-effort.json``. Files are copied byte-for-byte; this function
    never reads, prints, hashes, or logs their contents.
    """

    if not source.is_dir():
        raise RuntimeError(f"Kimi home source does not exist: {source}")
    if dest.exists():
        raise RuntimeError(f"scratch Kimi home already exists: {dest}")
    dest.mkdir(parents=True, exist_ok=False)
    copied: list[dict[str, Any]] = []
    missing: list[str] = []
    for name in SEED_REQUIRED_FILES:
        src = source / name
        if not src.is_file():
            raise RuntimeError(f"required Kimi home file is missing: {src}")
        shutil.copy2(src, dest / name)
        copied.append(_seed_inventory(dest / name, kind="file"))
    for name in SEED_OPTIONAL_FILES:
        src = source / name
        if src.is_file():
            shutil.copy2(src, dest / name)
            copied.append(_seed_inventory(dest / name, kind="file"))
        else:
            missing.append(name)
    for name in SEED_DIRS:
        src = source / name
        if src.is_dir():
            shutil.copytree(src, dest / name, symlinks=True)
            copied.append(_seed_inventory(dest / name, kind="dir"))
        else:
            missing.append(name)
    return {
        "source": str(source),
        "dest": str(dest),
        "copied": copied,
        "missing_optional": missing,
        "contents_recorded": False,
    }


def kimi_workdir_slug(name: str) -> str:
    """Mirror Kimi's ``slugifyWorkDirName`` for one path basename."""

    slug = re.sub(r"[^a-z0-9._-]+", "-", name.lower())
    slug = re.sub(r"^-+|-+$", "", slug)
    slug = slug[:40]
    slug = re.sub(r"^-+|-+$", "", slug)
    if slug in {"", ".", ".."}:
        return "workspace"
    return slug


def kimi_workdir_key(workdir: Path) -> str:
    """Mirror Kimi's ``encodeWorkDirKey`` for one working directory."""

    normalized = str(workdir).replace("\\", "/").rstrip("/")
    parts = normalized.split("/")
    base = parts[-1] if parts else normalized
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"wd_{kimi_workdir_slug(base)}_{digest}"


def seed_workspace_trust(*, kimi_home: Path, workdir: Path) -> dict[str, Any]:
    """Pre-seed Kimi's workspace-trust record in the scratch home.

    Houmao's production pre-seed
    (``src/houmao/agents/kimi_workspace_trust.py``) writes
    ``workspace-trust/<encodeWorkDirKey(cwd)>`` containing compact JSON
    ``{"root": "<absolute workdir>", "trustedAt": <epoch ms>}``. The record is
    presence-only at runtime, but the payload is kept faithful so the campaign
    can diff it against a live trust write.
    """

    resolved = workdir.resolve()
    key = kimi_workdir_key(resolved)
    target = kimi_home / "workspace-trust" / key
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"root": str(resolved), "trustedAt": int(time.time() * 1000)},
        separators=(",", ":"),
    )
    target.write_text(payload, encoding="utf-8")
    target.chmod(0o600)
    parsed = json.loads(target.read_text(encoding="utf-8"))
    if parsed.get("root") != str(resolved):
        raise RuntimeError("workspace-trust record read-back mismatch")
    return {
        "state": "projected",
        "path": str(target),
        "workspace_key": key,
        "root": str(resolved),
        "fields": sorted(parsed),
        "env_fallback_used": False,
    }


def ensure_top_level_string(config_path: Path, key: str, value: str) -> dict[str, Any]:
    """Ensure one top-level string key in a scratch TOML config.

    Used by S3 to force ``default_permission_mode = "manual"`` when the
    operator's config leaves the mode unset. The write happens before the
    observer block is appended so the key remains top-level.
    """

    text = config_path.read_text(encoding="utf-8")
    document = tomllib.loads(text)
    if key in document:
        if document[key] == value:
            return {"key": key, "value": value, "state": "unchanged"}
        pattern = re.compile(rf"^\s*{re.escape(key)}\s*=.*$", re.MULTILINE)
        updated, count = pattern.subn(f"{key} = {json.dumps(value)}", text, count=1)
        if count != 1:
            raise RuntimeError(f"could not replace top-level key {key!r}")
        config_path.write_text(updated, encoding="utf-8")
        if tomllib.loads(config_path.read_text(encoding="utf-8")).get(key) != value:
            raise RuntimeError(f"top-level key {key!r} did not update")
        return {"key": key, "value": value, "state": "replaced"}
    config_path.write_text(f"{key} = {json.dumps(value)}\n" + text, encoding="utf-8")
    if tomllib.loads(config_path.read_text(encoding="utf-8")).get(key) != value:
        raise RuntimeError(f"top-level key {key!r} did not insert")
    return {"key": key, "value": value, "state": "prepended"}


def prepare_home(
    *,
    state: RunState,
    spec: ScenarioSpec,
    kimi_home_source: Path,
) -> dict[str, Any]:
    """Create the scratch home, merge hooks, and pre-seed workspace trust."""

    state.m_workdir.mkdir(parents=True, exist_ok=True)
    if spec.name == "s4":
        (state.m_workdir / "README.md").write_text(S4_README_TEXT, encoding="utf-8")
    seed_info = seed_kimi_home(source=kimi_home_source, dest=state.m_kimi_home)
    config_toml = state.m_kimi_home / "config.toml"
    seeded_sha = _sha256_file(config_toml)
    seeded_bytes = config_toml.stat().st_size

    permission_info: dict[str, Any] | None = None
    if spec.permission_lane:
        permission_info = ensure_top_level_string(config_toml, "default_permission_mode", "manual")
    pre_text = config_toml.read_text(encoding="utf-8")
    pre_sha = _sha256_file(config_toml)
    pre_bytes = config_toml.stat().st_size

    prefixes = (
        {event: SLOW_HOOK_PREFIX for event in SLOW_HOOK_EVENTS}
        if spec.slow_lifecycle_hooks
        else None
    )
    report = kimi_hooks.merge_observer_hooks(
        config_toml,
        emitter=EMIT_HOOK_SCRIPT.resolve(),
        python_executable=sys.executable,
        timeout=DEFAULT_HOOK_TIMEOUT_SECONDS,
        command_prefix_by_event=prefixes,
    )
    post_text = config_toml.read_text(encoding="utf-8")
    preserved = post_text.startswith(pre_text.rstrip("\n"))
    if not preserved:
        raise RuntimeError("hook merge did not preserve the pre-existing config prefix")
    if spec.malformed_hooks:
        kimi_hooks.append_raw_toml_block(
            config_toml,
            S2_MALFORMED_ENTRY,
            reason="S2 malformed-entry control (extra cwd key)",
        )
        state.note("S2: appended one malformed [[hooks]] entry with an extra cwd key")

    dedup_probe: dict[str, Any] | None = None
    if spec.name == "s0":
        duplicate_command = kimi_hooks.build_command(
            python_executable=sys.executable, emitter=EMIT_HOOK_SCRIPT.resolve()
        )
        kimi_hooks.append_raw_toml_block(
            config_toml,
            kimi_hooks.render_hook_entry(
                event="UserPromptSubmit",
                command=duplicate_command,
                timeout=DEFAULT_HOOK_TIMEOUT_SECONDS,
            ),
            reason="S0 deliberate duplicate UserPromptSubmit entry (P3.5 dedup probe)",
        )
        report = kimi_hooks.validate_hooks_file(
            config_toml, require_all_events=True, require_timeout=True
        )
        dedup_probe = {
            "duplicate_event": "UserPromptSubmit",
            "duplicate_command": duplicate_command,
            "entry_count_after_append": report.entry_count,
            "validated": True,
            "expectation": "exactly one UserPromptSubmit delivery for one prompt (first-wins)",
        }
        state.note(
            "S0: appended one deliberate duplicate UserPromptSubmit [[hooks]] entry "
            f"(entries now {report.entry_count}) to settle P3.5 dedup live"
        )

    trust_info = seed_workspace_trust(kimi_home=state.m_kimi_home, workdir=state.m_workdir)
    post_sha = _sha256_file(config_toml)
    return {
        "events": list(report.events),
        "entry_count": report.entry_count,
        "timeouts": list(report.timeouts),
        "command": kimi_hooks.build_command(
            python_executable=sys.executable, emitter=EMIT_HOOK_SCRIPT.resolve()
        ),
        "python_executable": sys.executable,
        "emitter": str(EMIT_HOOK_SCRIPT.resolve()),
        "config_toml_path": str(config_toml),
        "config_toml_seeded_sha256": seeded_sha,
        "config_toml_seeded_bytes": seeded_bytes,
        "config_toml_pre_hooks_sha256": pre_sha,
        "config_toml_post_hooks_sha256": post_sha,
        "config_toml_pre_hooks_bytes": pre_bytes,
        "config_toml_post_hooks_bytes": config_toml.stat().st_size,
        "existing_prefix_preserved": preserved,
        "malformed_entry_appended": spec.malformed_hooks,
        "dedup_probe": dedup_probe,
        "slow_lifecycle_prefixes": prefixes or {},
        "permission_mode_override": permission_info,
        "home_seed": seed_info,
        "workspace_trust": trust_info,
    }


class LaunchEnv:
    """Current collector generation plus the wrapper derived from it."""

    def __init__(
        self,
        *,
        run_root: Path,
        kimi_home: Path,
        collector_store: Path,
        token: str,
        kimi_binary: Path,
        launcher_args: tuple[str, ...],
    ) -> None:
        """Record paths and the per-run bearer token."""

        self.m_run_root = run_root
        self.m_kimi_home = kimi_home
        self.m_collector_store = collector_store
        self.m_token = token
        self.m_kimi_binary = kimi_binary
        self.m_launcher_args = launcher_args
        self.m_collector: CollectorProcess | None = None
        self.m_port: int | None = None
        self.m_generation = 0
        self.m_wrapper: Path | None = None

    def start_generation(self, generation: int) -> int:
        """Start collector generation N and regenerate the launch wrapper."""

        self.m_generation = generation
        log_path = self.m_collector_store / f"collector-gen{generation}.log"
        self.m_collector = CollectorProcess(
            store=self.m_collector_store,
            token=self.m_token,
            generation=generation,
            log_path=log_path,
        )
        self.m_port = self.m_collector.start()
        self.m_wrapper = self.m_run_root / f"launch-wrapper-gen{generation}.sh"
        write_wrapper(
            path=self.m_wrapper,
            kimi_home=self.m_kimi_home,
            token=self.m_token,
            port=self.m_port,
            store=self.m_collector_store,
            generation=generation,
            kimi_binary=self.m_kimi_binary,
            launcher_args=self.m_launcher_args,
        )
        return self.m_port

    def process_env(self) -> dict[str, str]:
        """Return the hook environment for a direct (headless) launch."""

        assert self.m_port is not None
        env = os.environ.copy()
        env["KIMI_CODE_HOME"] = str(self.m_kimi_home)
        env["KIMI_CODE_NO_AUTO_UPDATE"] = "1"
        env["HOUMAO_HOOK_TOKEN"] = self.m_token
        env["HOUMAO_HOOK_COLLECTOR_URL"] = f"http://127.0.0.1:{self.m_port}{HOOK_ROUTE}"
        env["HOUMAO_HOOK_STORE"] = str(self.m_collector_store)
        env["HOUMAO_HOOK_GENERATION"] = str(self.m_generation)
        return env

    def stop_collector(self) -> None:
        """Stop the current collector and archive its status file."""

        if self.m_collector is None:
            return
        self.m_collector.stop()
        self.m_collector = None
        status_path = self.m_collector_store / COLLECTOR_FILENAME
        if status_path.is_file() and self.m_generation > 0:
            archive = self.m_collector_store / f"{COLLECTOR_FILENAME}.gen{self.m_generation}"
            archive.write_bytes(status_path.read_bytes())


def write_wrapper(
    *,
    path: Path,
    kimi_home: Path,
    token: str,
    port: int,
    store: Path,
    generation: int,
    kimi_binary: Path,
    launcher_args: tuple[str, ...],
) -> Path:
    """Generate the mode-0600 launch wrapper for one collector generation."""

    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    lines.append(f"export KIMI_CODE_HOME={_shell_single_quote(str(kimi_home))}")
    lines.append("export KIMI_CODE_NO_AUTO_UPDATE=1")
    lines.append(f"export HOUMAO_HOOK_TOKEN={_shell_single_quote(token)}")
    lines.append(
        "export HOUMAO_HOOK_COLLECTOR_URL="
        + _shell_single_quote(f"http://127.0.0.1:{port}{HOOK_ROUTE}")
    )
    lines.append(f"export HOUMAO_HOOK_STORE={_shell_single_quote(str(store))}")
    lines.append(f"export HOUMAO_HOOK_GENERATION={_shell_single_quote(str(generation))}")
    lines.append("")
    exec_line = f"exec {_shell_single_quote(str(kimi_binary))}"
    for arg in launcher_args:
        exec_line += " " + _shell_single_quote(arg)
    exec_line += ' "$@"'
    lines.append(exec_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def _hook_env_overrides(*, state: RunState, env: LaunchEnv) -> dict[str, str]:
    """Return the env keys the wrapper exports, for manifest records (no token)."""

    return {
        "KIMI_CODE_HOME": str(state.m_kimi_home),
        "KIMI_CODE_NO_AUTO_UPDATE": "1",
        "HOUMAO_HOOK_COLLECTOR_URL": f"http://127.0.0.1:{env.m_port}{HOOK_ROUTE}",
        "HOUMAO_HOOK_STORE": str(state.m_collector_store),
        "HOUMAO_HOOK_GENERATION": str(env.m_generation),
        "HOUMAO_HOOK_TOKEN": "<redacted>",
    }


def run_scenario(
    scenario: str,
    run_root_override: Path | None,
    *,
    kimi_binary_spec: str,
    kimi_home_source: Path,
) -> int:
    """Run one scenario end to end with full teardown; return an exit code."""

    spec = SCENARIOS[scenario]
    kimi_binary_info = _resolve_kimi_binary(kimi_binary_spec)
    kimi_binary = Path(str(kimi_binary_info["path"]))
    run_root = (run_root_override or _default_run_root(scenario)).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    workdir = (run_root / "workdir").resolve()
    kimi_home = (run_root / "kimi-home").resolve()
    collector_store = run_root / "collector"
    labels_dir = run_root / "labels"
    labels_dir.mkdir(exist_ok=True)

    token = secrets.token_hex(16)
    launcher_args: tuple[str, ...] = ("--auto",) if spec.auto and not spec.headless else ()
    state = RunState(
        spec=spec,
        run_root=run_root,
        workdir=workdir,
        kimi_home=kimi_home,
        collector_store=collector_store,
        token=token,
        generation=1,
        hooks_enabled=True,
        kimi_binary_info=kimi_binary_info,
    )
    env = LaunchEnv(
        run_root=run_root,
        kimi_home=kimi_home,
        collector_store=collector_store,
        token=token,
        kimi_binary=kimi_binary,
        launcher_args=launcher_args,
    )
    state.m_launch_env = env
    sessions: list[str] = []
    recorder_roots: list[Path] = []
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "scenario": scenario,
        "expectation": spec.expectation,
        "run_root": str(run_root),
        "workdir": str(workdir),
        "kimi_home": str(kimi_home),
        "runner_pid": os.getpid(),
        "kimi": kimi_binary_info,
        "launch": {
            "args": list(launcher_args),
            "auto": spec.auto,
            "headless": spec.headless,
            "optional": spec.optional,
            "wrapper": None,
        },
        "collector": {
            "store": str(collector_store),
            "token_env": "HOUMAO_HOOK_TOKEN",
            "generations": state.m_generations,
        },
        "hooks": {},
        "workspace_trust": {},
        "home_seed": {},
        "hook_env": {},
        "tui_surface": {
            "composer_welcome_markers": list(COMPOSER_WELCOME_MARKERS),
            "composer_directory_marker": COMPOSER_DIRECTORY_MARKER,
            "composer_footer_marker": COMPOSER_FOOTER_MARKER,
            "composer_editor_border": COMPOSER_EDITOR_BORDER,
            "composer_stable_seconds": COMPOSER_STABLE_SECONDS,
            "trust_modal_markers": list(TRUST_MODAL_MARKERS),
            "permission_prompt_markers": list(PERMISSION_PROMPT_MARKERS),
            "exit_command": EXIT_COMMAND,
            "exit_fallback_sequences": [list(item) for item in EXIT_FALLBACK_SEQUENCES],
        },
        "time": {
            "launched_at_utc": None,
            "launched_monotonic": None,
            "finished_at_utc": None,
            "finished_monotonic": None,
        },
        "timing": {},
        "artifacts": {
            "events_ndjson": str(collector_store / EVENTS_FILENAME),
            "collector_json": str(collector_store / COLLECTOR_FILENAME),
            "raw_provider_payloads": str(run_root / "raw-provider-payloads.ndjson"),
            "driver_input_events": str(state.m_input_log),
            "pane_recording": str(run_root / "pane-recording"),
            "labels": str(labels_dir / "labels-template.json"),
            "run_summary": str(run_root / "run-summary.json"),
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    manifest_path = run_root / "launch.json"

    def write_manifest() -> None:
        """Persist the current manifest atomically."""

        manifest["timing"] = _timing_payload(state)
        manifest["collector"]["generations"] = state.m_generations
        manifest["time"]["launched_at_utc"] = state.m_launched_at_utc
        manifest["time"]["launched_monotonic"] = (
            round(state.m_launched_monotonic, 6) if state.m_launched_monotonic is not None else None
        )
        if env.m_wrapper is not None:
            manifest["launch"]["wrapper"] = str(env.m_wrapper)
        if env.m_port is not None:
            manifest["hook_env"] = _hook_env_overrides(state=state, env=env)
        tmp_path = manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_path, manifest_path)

    def register_session(name: str, driver: PaneDriver) -> None:
        """Track one session and its driver for exit and teardown."""

        sessions.append(name)
        state.m_drivers[name] = driver

    try:
        home_info = prepare_home(state=state, spec=spec, kimi_home_source=kimi_home_source)
        manifest["hooks"] = home_info
        manifest["workspace_trust"] = home_info["workspace_trust"]
        manifest["home_seed"] = home_info["home_seed"]
        state.m_hook_info = home_info
        state.note(
            f"seeded scratch home from {kimi_home_source} "
            f"(contents copied, never read by the harness)"
        )
        if spec.permission_lane:
            state.note("S3: forced default_permission_mode=manual before hook merge")
        if spec.slow_lifecycle_hooks:
            state.note("T1: SessionStart/SessionEnd commands prefixed with `sleep 3; `")

        port = env.start_generation(1)
        state.m_generations.append(
            {
                "generation": 1,
                "port": port,
                "started_at_utc": utc_now_ms(),
                "started_monotonic": round(time.monotonic(), 6),
                "reason": "initial launch",
            }
        )
        manifest["launch"]["wrapper"] = str(env.m_wrapper)
        manifest["hook_env"] = _hook_env_overrides(state=state, env=env)
        manifest["collector"]["generations"] = state.m_generations
        write_manifest()
        print(
            f"scenario {scenario}: kimi_home={kimi_home} port={port} "
            f"hooks={home_info['entry_count']}"
        )

        if spec.headless:
            run_s8(state, env)
        else:
            session_name = f"kimihook-{scenario}-{os.getpid()}"
            assert env.m_wrapper is not None
            state.mark_launch()
            manifest["time"]["launched_at_utc"] = state.m_launched_at_utc
            manifest["time"]["launched_monotonic"] = round(state.m_launched_monotonic or 0.0, 6)
            pane_id = launch_tmux_session(
                session_name=session_name, workdir=workdir, wrapper=env.m_wrapper
            )
            driver = PaneDriver(
                session_name=session_name, pane_id=pane_id, log_path=state.m_input_log
            )
            register_session(session_name, driver)
            manifest["tmux"] = {
                "session": session_name,
                "pane": pane_id,
                "pane_pid": pane_pid(pane_id),
                "width": PANE_WIDTH,
                "height": PANE_HEIGHT,
            }
            write_manifest()
            print(f"scenario {scenario}: tmux={session_name} pane={pane_id}")

            start_recorder(session_name=session_name, run_root=run_root / "pane-recording")
            recorder_roots.append(run_root / "pane-recording")
            bootstrap_session(state, driver=driver)
            step = STEPS[scenario]
            if scenario == "s7":
                step(
                    state,
                    driver,
                    session_name,
                    env=env,
                    register_session=register_session,
                    recorder_roots=recorder_roots,
                )
            else:
                step(state, driver, session_name)
        print(f"scenario {scenario} finished")
        return 0
    except AbortRun as exc:
        state.m_aborted = exc.m_reason
        state.log("run-aborted", reason=exc.m_reason)
        print(f"ABORTED ({scenario}): {exc.m_reason}")
        return 0
    except Exception as exc:  # unexpected runner failure: record, finalize, nonzero
        state.m_aborted = f"runner exception: {exc!r}"
        state.log("run-exception", error=repr(exc))
        print(f"ERROR ({scenario}): {exc!r}", file=sys.stderr)
        traceback.print_exc()
        return 1
    finally:
        for root in recorder_roots:
            try:
                stop_recorder(run_root=root)
            except Exception as exc:  # teardown must not raise
                state.note(f"recorder stop failed for {root}: {exc!r}")
        for name in sessions:
            try:
                kill_tmux_session(name)
            except Exception as exc:  # teardown must not raise
                state.note(f"tmux kill failed for {name}: {exc!r}")
        env.stop_collector()
        try:
            collector_store.mkdir(parents=True, exist_ok=True)
            (collector_store / EVENTS_FILENAME).touch(exist_ok=True)
            write_raw_payload_log(state, run_root)
            write_labels_template(state, labels_dir)
        except Exception as exc:  # teardown must not raise
            print(f"warning: labels template write failed: {exc!r}", file=sys.stderr)
        try:
            write_run_summary(state, run_root, collector_store)
        except Exception as exc:  # teardown must not raise
            print(f"warning: run summary write failed: {exc!r}", file=sys.stderr)
        manifest["time"]["finished_at_utc"] = utc_now_ms()
        manifest["time"]["finished_monotonic"] = round(time.monotonic(), 6)
        manifest["aborted"] = state.m_aborted is not None
        manifest["abort_reason"] = state.m_aborted
        try:
            write_manifest()
        except Exception as exc:  # teardown must not raise
            print(f"warning: launch manifest write failed: {exc!r}", file=sys.stderr)


def _urllib_post(url: str, body: str, token: str) -> int:
    """POST one raw body with urllib; return the HTTP status code."""

    request = Request(
        url,
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)


def _run_emit_hook(
    payload: dict[str, Any], *, url: str, token: str, store: Path, generation: int
) -> subprocess.CompletedProcess[str]:
    """Run emit_hook.py with piped stdin and hook env; capture both streams."""

    env = os.environ.copy()
    env["HOUMAO_HOOK_COLLECTOR_URL"] = url
    env["HOUMAO_HOOK_TOKEN"] = token
    env["HOUMAO_HOOK_STORE"] = str(store)
    env["HOUMAO_HOOK_GENERATION"] = str(generation)
    return subprocess.run(
        [sys.executable, str(EMIT_HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def _self_test_hooks_config(root: Path, checks: list[tuple[str, bool, str]]) -> Path:
    """Generate, duplicate, validate, and exercise a hooks config for G0."""

    hooks_root = root / "hooks-home"
    hooks_root.mkdir(parents=True, exist_ok=True)
    config_path = hooks_root / "config.toml"
    original = (
        "# synthetic self-test config (no provider credentials)\n"
        'default_model = "selftest-model"\n'
        "\n"
        "[providers.selftest]\n"
        'base_url = "http://127.0.0.1:1"\n'
    )
    config_path.write_text(original, encoding="utf-8")
    try:
        report = kimi_hooks.merge_observer_hooks(
            config_path,
            emitter=EMIT_HOOK_SCRIPT.resolve(),
            python_executable=sys.executable,
        )
    except Exception as exc:
        checks.append(("hooks-config-generated", False, repr(exc)))
        return config_path

    merged = config_path.read_text(encoding="utf-8")
    checks.append(
        (
            "hooks-config-generated-and-prefix-preserved",
            report.entry_count == len(kimi_hooks.EVENT_NAMES)
            and set(report.events) == set(kimi_hooks.EVENT_NAMES)
            and all(timeout == DEFAULT_HOOK_TIMEOUT_SECONDS for timeout in report.timeouts)
            and merged.startswith(original.rstrip("\n")),
            f"entries={report.entry_count}",
        )
    )
    checks.append(
        (
            "hooks-config-all-20-events",
            len(kimi_hooks.EVENT_NAMES) == 20 and set(report.events) == set(kimi_hooks.EVENT_NAMES),
            f"events={len(set(report.events))}",
        )
    )

    try:
        valid = kimi_hooks.validate_hooks_file(
            config_path, require_all_events=True, require_timeout=True
        )
        checks.append(("hooks-config-read-back-valid", True, f"entries={valid.entry_count}"))
    except Exception as exc:
        checks.append(("hooks-config-read-back-valid", False, repr(exc)))

    duplicate = kimi_hooks.render_hook_entry(
        event="UserPromptSubmit",
        command=kimi_hooks.build_command(
            python_executable=sys.executable, emitter=EMIT_HOOK_SCRIPT.resolve()
        ),
        timeout=DEFAULT_HOOK_TIMEOUT_SECONDS,
    )
    kimi_hooks.append_raw_toml_block(config_path, duplicate, reason="self-test duplicate")
    try:
        duplicate_report = kimi_hooks.validate_hooks_file(
            config_path, require_all_events=True, require_timeout=True
        )
        checks.append(
            (
                "duplicate-hooks-entry-validates",
                duplicate_report.entry_count == len(kimi_hooks.EVENT_NAMES) + 1,
                f"entries={duplicate_report.entry_count}",
            )
        )
    except Exception as exc:
        checks.append(("duplicate-hooks-entry-validates", False, repr(exc)))

    malformed_root = root / "malformed-home"
    malformed_root.mkdir(parents=True, exist_ok=True)
    malformed_config = malformed_root / "config.toml"
    malformed_config.write_text(original, encoding="utf-8")
    try:
        kimi_hooks.merge_observer_hooks(
            malformed_config,
            emitter=EMIT_HOOK_SCRIPT.resolve(),
            python_executable=sys.executable,
        )
        kimi_hooks.append_raw_toml_block(
            malformed_config, S2_MALFORMED_ENTRY, reason="self-test malformed control"
        )
        raw_text = malformed_config.read_text(encoding="utf-8")
        raw_parse_ok = True
        try:
            tomllib.loads(raw_text)
        except tomllib.TOMLDecodeError:
            raw_parse_ok = False
        guard_refused = False
        try:
            kimi_hooks.validate_hooks_file(malformed_config)
        except kimi_hooks.HookConfigError:
            guard_refused = True
        checks.append(
            (
                "malformed-helper-writes-without-validation",
                'cwd = "/tmp"' in raw_text and raw_parse_ok,
                f"toml_parse={raw_parse_ok}",
            )
        )
        checks.append(
            (
                "malformed-entry-refused-by-installer-guard",
                guard_refused,
                "validate_hooks_file raised HookConfigError"
                if guard_refused
                else "validator accepted the malformed entry",
            )
        )
    except Exception as exc:
        checks.append(("malformed-helper-writes-without-validation", False, repr(exc)))
        checks.append(("malformed-entry-refused-by-installer-guard", False, repr(exc)))

    bad_root = root / "bad-home"
    bad_root.mkdir(parents=True, exist_ok=True)
    bad_config = bad_root / "config.toml"
    bad_config.write_text(
        '[[hooks]]\nevent = "NotAnEvent"\ncommand = "true"\ntimeout = 5\n',
        encoding="utf-8",
    )
    try:
        kimi_hooks.validate_hooks_file(bad_config)
        checks.append(("unknown-event-refused", False, "validator accepted NotAnEvent"))
    except kimi_hooks.HookConfigError:
        checks.append(("unknown-event-refused", True, "HookConfigError"))
    return config_path


def _self_test_emit_chain(
    *, store: Path, token: str, port: int, events_path: Path
) -> list[tuple[str, bool, str]]:
    """Exercise the collector and emitter on both delivery paths."""

    checks: list[tuple[str, bool, str]] = []
    url = f"http://127.0.0.1:{port}{HOOK_ROUTE}"
    status = _urllib_post(
        f"{url}?event=G0UrllibPost&seq=99",
        json.dumps({"hook_event_name": "G0UrllibPost", "probe": "a"}),
        token,
    )
    found = _wait_for_event_name(events_path, "G0UrllibPost", timeout_seconds=5.0)
    checks.append(
        ("urllib-post-accepted", status == 204 and found, f"status={status} found={found}")
    )

    row = _find_event_row(events_path, "G0UrllibPost")
    timestamp_ok = False
    delivery_ok = False
    if row is not None:
        timestamp_ok = bool(UTC_MS_PATTERN.match(str(row.get("received_at_utc")))) and isinstance(
            row.get("received_at_monotonic"), float
        )
        delivery = row.get("delivery")
        delivery_ok = (
            isinstance(delivery, dict)
            and delivery.get("event") == "G0UrllibPost"
            and bool(delivery.get("client_seq"))
        )
    checks.append(
        (
            "millisecond-utc-and-monotonic-stamp",
            timestamp_ok,
            str(row.get("received_at_utc")) if row else "no row",
        )
    )
    checks.append(
        (
            "delivery-metadata",
            delivery_ok,
            json.dumps(row.get("delivery")) if row else "no row",
        )
    )

    base_lines = _count_event_lines(events_path)
    wrong_status = _urllib_post(url, json.dumps({"hook_event_name": "G0WrongToken"}), "wrong-token")
    after_wrong_lines = _count_event_lines(events_path)
    checks.append(
        (
            "wrong-token-rejected",
            wrong_status in (401, 403) and after_wrong_lines == base_lines,
            f"status={wrong_status} before={base_lines} after={after_wrong_lines}",
        )
    )

    malformed_status = _urllib_post(url, "{not-json", token)
    checks.append(
        ("malformed-json-rejected", malformed_status == 400, f"status={malformed_status}")
    )

    emit_result = _run_emit_hook(
        {"hook_event_name": "SelfTestEmitter", "probe": "b"},
        url=url,
        token=token,
        store=store,
        generation=1,
    )
    emitter_found = _wait_for_event_name(events_path, "SelfTestEmitter", timeout_seconds=5.0)
    emitter_row = _find_event_row(events_path, "SelfTestEmitter")
    emitter_delivery = emitter_row.get("delivery") if emitter_row else None
    emitter_delivery_ok = isinstance(emitter_delivery, dict) and (
        emitter_delivery.get("event") == "SelfTestEmitter"
        and bool(emitter_delivery.get("client_seq"))
    )
    checks.append(
        (
            "emitter-posts-to-collector",
            emit_result.returncode == 0
            and emit_result.stdout == ""
            and emitter_found
            and emitter_delivery_ok,
            f"rc={emit_result.returncode} stdout={emit_result.stdout!r} "
            f"found={emitter_found} delivery={emitter_delivery}",
        )
    )
    return checks


def self_test() -> int:
    """Run the provider-free G0 harness self-test; non-zero exit on any FAIL."""

    checks: list[tuple[str, bool, str]] = []
    root = RUN_ROOT_BASE / "self-test" / f"run-{utc_stamp()}"
    root.mkdir(parents=True, exist_ok=True)
    store = root / "collector"
    store.mkdir(parents=True, exist_ok=True)
    events_path = store / EVENTS_FILENAME
    collector_status_path = store / COLLECTOR_FILENAME
    token = secrets.token_hex(16)
    collector = CollectorProcess(
        store=store,
        token=token,
        generation=1,
        log_path=store / "collector.log",
        heartbeat_seconds=0.5,
    )
    config_path = _self_test_hooks_config(root, checks)
    try:
        port = collector.start()
        checks.append(("collector-heartbeat-written-on-start", collector_status_path.is_file(), ""))
        checks.extend(
            _self_test_emit_chain(store=store, token=token, port=port, events_path=events_path)
        )

        heartbeat_before = json.loads(collector_status_path.read_text(encoding="utf-8"))
        time.sleep(1.3)
        heartbeat_after = json.loads(collector_status_path.read_text(encoding="utf-8"))
        heartbeat_ok = (
            heartbeat_after.get("status") == "running"
            and float(heartbeat_after.get("last_heartbeat_monotonic", 0))
            > float(heartbeat_before.get("last_heartbeat_monotonic", 0))
            and bool(UTC_MS_PATTERN.match(str(heartbeat_after.get("last_heartbeat_at_utc"))))
            and "token" not in json.dumps(heartbeat_after).lower()
        )
        checks.append(
            (
                "collector-heartbeat-periodic-and-secret-free",
                heartbeat_ok,
                f"interval={heartbeat_after.get('heartbeat_interval_seconds')}",
            )
        )

        shell_env = os.environ.copy()
        shell_env["HOUMAO_HOOK_COLLECTOR_URL"] = f"http://127.0.0.1:{port}{HOOK_ROUTE}"
        shell_env["HOUMAO_HOOK_TOKEN"] = token
        shell_env["HOUMAO_HOOK_STORE"] = str(store)
        shell_env["HOUMAO_HOOK_GENERATION"] = "1"
        try:
            document = tomllib.loads(config_path.read_text(encoding="utf-8"))
            entries = document.get("hooks", [])
            command = next(
                entry["command"] for entry in entries if entry.get("event") == "UserPromptSubmit"
            )
            shell_result = subprocess.run(
                ["bash", "-c", command],
                input=json.dumps(
                    {
                        "hook_event_name": "SelfTestHookCommand",
                        "session_id": "s",
                        "turn_id": "t",
                    }
                ),
                capture_output=True,
                text=True,
                timeout=60,
                env=shell_env,
            )
            shell_found = _wait_for_event_name(
                events_path, "SelfTestHookCommand", timeout_seconds=5.0
            )
            shell_ok = shell_result.returncode == 0 and shell_result.stdout == "" and shell_found
            shell_note = (
                f"rc={shell_result.returncode} stdout={shell_result.stdout!r} found={shell_found}"
            )
        except Exception as exc:  # self-test must report, not crash
            shell_ok = False
            shell_note = f"exception={exc!r}"
        checks.append(("generated-hook-command-via-shell", shell_ok, shell_note))

        collector.stop()
        fallback_result = _run_emit_hook(
            {"hook_event_name": "SelfTestFallback", "probe": "c"},
            url=f"http://127.0.0.1:{port}{HOOK_ROUTE}",
            token=token,
            store=store,
            generation=1,
        )
        fallback_row = None
        if events_path.is_file():
            with events_path.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    try:
                        row = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    provider = row.get("provider_event")
                    if (
                        row.get("via") == "command_fallback"
                        and isinstance(provider, dict)
                        and provider.get("hook_event_name") == "SelfTestFallback"
                    ):
                        fallback_row = row
                        break
        checks.append(
            (
                "emitter-file-fallback-after-collector-death",
                fallback_result.returncode == 0
                and fallback_result.stdout == ""
                and fallback_row is not None
                and fallback_row.get("sequence") is None
                and isinstance(fallback_row.get("emitter_seq"), int),
                f"rc={fallback_result.returncode} stdout={fallback_result.stdout!r}",
            )
        )
        stopped_status = json.loads(collector_status_path.read_text(encoding="utf-8"))
        checks.append(
            (
                "collector-status-stopped",
                stopped_status.get("status") == "stopped",
                str(stopped_status.get("status")),
            )
        )
        checks.append(
            (
                "collector-status-secret-free",
                "token" not in json.dumps(stopped_status).lower(),
                "token absent",
            )
        )
    finally:
        collector.stop()

    print(f"SELF-TEST root={root}")
    failed = 0
    for name, ok, note in checks:
        suffix = f" ({note})" if note else ""
        print(f"{'PASS' if ok else 'FAIL'} {name}{suffix}")
        if not ok:
            failed += 1
    print(f"SELF-TEST {'PASSED' if failed == 0 else f'{failed} CHECK(S) FAILED'}")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: one scenario or the provider-free self-test."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=tuple(SCENARIOS))
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument(
        "--kimi-binary",
        default=DEFAULT_KIMI_BINARY,
        help="kimi executable name or absolute path (default: kimi on PATH)",
    )
    parser.add_argument(
        "--kimi-home-source",
        type=Path,
        default=DEFAULT_KIMI_HOME_SOURCE,
        help="real Kimi home copied into each scratch home (default: ~/.kimi-code)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the provider-free G0 harness check and exit",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.scenario:
        parser.error("--scenario is required unless --self-test is given")
    return run_scenario(
        args.scenario,
        args.run_root,
        kimi_binary_spec=args.kimi_binary,
        kimi_home_source=args.kimi_home_source.expanduser().resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
