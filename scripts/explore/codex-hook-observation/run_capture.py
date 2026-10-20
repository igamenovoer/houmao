"""One-command scenario runner for the Codex hook-observation campaign.

Throwaway harness for
``context/campaigns/debug/2026-10-20-codex-hook-observation/iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md``.
Each run creates an isolated scratch ``CODEX_HOME`` under
``tmp/codex-hook-capture/<scenario>/run-<UTCts>/``, writes the trust preseed
and observer ``hooks.json``, starts the loopback collector, launches Codex in
a detached tmux session through a credential launcher (default
``~/.local/bin/codex-openlux-auto``),
drives one frozen scenario arm, records the pane at 5 fps with the repo's
terminal-record tool, and writes a labels template plus a ``launch.json``
manifest (versions, flags, ports, paths, UTC/monotonic pairs, and codex binary
SHA-256 values).

Nothing here is production code. ``--self-test`` is the provider-free G0 gate
and never launches Codex.

Credential hygiene: the provider API key is never read, printed, copied, or
embedded. The wrapper execs the selected launcher, which exports the key to
Codex itself. Only the per-run random bearer token appears in the mode-0600
wrapper (same convention as the Claude lane).
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

from houmao.agents.realm_controller.backends.tmux_runtime import run_tmux

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS_DIR = Path(__file__).resolve().parent
COLLECTOR_SCRIPT = HARNESS_DIR / "collector.py"
EMIT_HOOK_SCRIPT = HARNESS_DIR / "emit_hook.py"
OBSERVER_HOOKS_SCRIPT = HARNESS_DIR / "observer_hooks.py"
HASH_HOOK_SCRIPT = HARNESS_DIR / "hash_hook.py"
RUN_ROOT_BASE = REPO_ROOT / "tmp" / "codex-hook-capture"
DEFAULT_LAUNCHER = Path.home() / ".local" / "bin" / "codex-openlux-auto"
DEFAULT_LANE = "openlux-auto"
PANE_WIDTH = 220
PANE_HEIGHT = 56
RECORDER_INTERVAL_SECONDS = 0.2
HOOK_ROUTE = "/v1/hook"
COLLECTOR_FILENAME = "collector.json"
EVENTS_FILENAME = "events.ndjson"

EVENT_NAMES: tuple[str, ...] = (
    "PreModelRequest",
    "PostModelRequest",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "Interrupt",
)
SESSION_END_TIMEOUT_SECONDS = 2
DEFAULT_HOOK_TIMEOUT_SECONDS = 5

OPENLUX_PROFILE_CONTENT = """model_provider = "openlux"
disable_response_storage = true

[model_providers.openlux]
name = "OpenLux"
base_url = "https://api.openlux.ai/v1"
env_key = "OPENLUX_API_KEY"
env_http_headers = { "Authorization" = "OPENLUX_AUTHORIZATION" }
wire_api = "responses"
requires_openai_auth = false
stream_idle_timeout_ms = 120000
"""


@dataclass(frozen=True)
class LaneSpec:
    """One credential launcher and the profile it expects in ``CODEX_HOME``."""

    name: str
    launcher_name: str
    profile_name: str
    profile_content: str

    @property
    def profile_filename(self) -> str:
        """Return the profile filename Codex reads from ``CODEX_HOME``."""

        return f"{self.profile_name}.config.toml"


LANES: dict[str, LaneSpec] = {
    "openlux-auto": LaneSpec(
        name="openlux-auto",
        launcher_name="codex-openlux-auto",
        profile_name="openlux-auto",
        profile_content=OPENLUX_PROFILE_CONTENT,
    ),
}


def resolve_lane(launcher: Path, override: str = "auto") -> LaneSpec:
    """Select the credential lane for a launcher path.

    ``--lane`` wins when set. Otherwise the launcher basename selects the lane;
    an unknown custom launcher falls back to the default lane, which the
    manifest records.
    """

    if override != "auto":
        return LANES[override]
    if "openlux" in launcher.name:
        return LANES["openlux-auto"]
    return LANES[DEFAULT_LANE]


PROMPT_OK = "Reply with exactly: OK"
PROMPT_TOOL = (
    "Create a file named /tmp/houmao-codex-hook-s1.txt containing hello, then run `echo done`"
)
PROMPT_README = "Read README.md and summarize in one sentence."
PROMPT_ALLOW = "Create a file named /tmp/houmao-codex-hook-allow.txt containing hello"
PROMPT_DENY = "Create a file named /tmp/houmao-codex-hook-deny.txt containing hello"
PROMPT_RECURSION = "Write a long essay about recursion."
PROMPT_QUEUES = "Write a long essay about queues."
PROMPT_FAULTS = "Write a long essay about faults."

COMPOSER_PLACEHOLDER = "Ask Codex to do anything"
COMPOSER_TAIL_LINES = 8
COMPOSER_STABLE_SECONDS = 3.0
TRUST_MODAL_MARKERS = (
    # Source-derived selection modal (pre-0.163 layouts).
    "Trust all and continue",
    "Continue without trusting",
    "Review hooks",
    # Observed 0.163.0 startup surface: the Hooks browser opened on its Events page.
    "needs review before it can run",
    "Lifecycle hooks from config and enabled plugins",
    "Active/Installed",
)
HOOKS_BROWSER_MARKERS = (
    "needs review before it can run",
    "Lifecycle hooks from config and enabled plugins",
    "Active/Installed",
)
PERMISSION_MODAL_MARKERS = (
    "Would you like to run the following command",
    "Would you like to make the following edits",
    "Would you like to grant these permissions",
    "Do you want to approve",
    "Yes, proceed",
    "No, continue without running it",
    "No, and tell Codex what to do differently",
    "Yes, just this once",
)
BUSY_MARKERS = ("esc to interrupt",)

S4_README_TEXT = (
    "# Codex hook capture scratch project\n"
    "\n"
    "Temporary git-less workdir for the Codex hook-observation campaign.\n"
    "This file exists so s4 has a README to read and summarize.\n"
)

UTC_MS_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")


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
    """Quote one value for safe inclusion in a generated bash script.

    ``shlex.quote`` handles embedded single quotes via ``'"'"'``; this matters
    for the T2 session-flag arm, whose TOML value embeds the hook command.
    """

    return shlex.quote(value)


def _sha256_file(path: Path) -> str | None:
    """Return the SHA-256 hex digest of a file, or None when unreadable."""

    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _resolve_codex_binary() -> dict[str, Any]:
    """Resolve the codex launcher and native binary, with hashes and version."""

    info: dict[str, Any] = {
        "shim_path": None,
        "shim_sha256": None,
        "native_path": None,
        "native_sha256": None,
        "version": None,
        "resolution_notes": [],
    }
    which = shutil.which("codex")
    if which is None:
        info["resolution_notes"].append("codex not found on PATH")
        return info
    shim = Path(which)
    info["shim_path"] = str(shim)
    info["shim_sha256"] = _sha256_file(shim)
    resolved = shim.resolve()
    if resolved != shim:
        info["shim_resolved_path"] = str(resolved)
        info["shim_resolved_sha256"] = _sha256_file(resolved)

    machine = platform.machine().lower()
    triple_needle = {
        "aarch64": "aarch64",
        "arm64": "aarch64",
        "x86_64": "x86_64",
        "amd64": "x86_64",
    }.get(machine, machine)
    candidates: list[Path] = []
    for parent in resolved.parents:
        if parent.name != "node_modules":
            continue
        candidates.extend(sorted(parent.glob("@openai/codex-*/vendor/*/bin/codex")))
        break
    if not candidates:
        fallback = Path.home() / ".bun" / "install" / "global" / "node_modules"
        candidates.extend(sorted(fallback.glob("@openai/codex-*/vendor/*/bin/codex")))
    preferred = [
        item
        for item in candidates
        if item.is_file() and triple_needle and triple_needle in str(item)
    ]
    usable = [item for item in candidates if item.is_file()]
    chosen = (preferred or usable)[0] if (preferred or usable) else None
    if chosen is not None:
        info["native_path"] = str(chosen)
        info["native_sha256"] = _sha256_file(chosen)
    else:
        info["resolution_notes"].append(
            "native codex binary not found under node_modules/@openai/codex-*/vendor"
        )

    try:
        version_result = subprocess.run(
            [str(shim), "--version"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        info["version"] = version_result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired) as exc:
        info["resolution_notes"].append(f"codex --version failed: {exc!r}")
    return info


@dataclass(frozen=True)
class ScenarioSpec:
    """One frozen scenario arm from the campaign capture matrix."""

    name: str
    expectation: str
    hooks_json: bool = True
    bypass_hook_trust: bool = True
    pretrust: bool = False
    session_flags_hooks: bool = False
    requires_permission_lane: bool = False
    expects_session_start: bool = True
    extra_args: tuple[str, ...] = ()
    labels: tuple[tuple[str, str], ...] = ()


SCENARIOS: dict[str, ScenarioSpec] = {
    "s0": ScenarioSpec(
        name="s0",
        expectation=(
            "SessionStart + UserPromptSubmit + Stop arrive; no trust modal; "
            "ready composer reached with zero keypresses."
        ),
        labels=(
            ("s0-ready", "composer surface before the prompt"),
            ("s0-turn-ok", "span from prompt submit to visible OK answer"),
        ),
    ),
    "s1": ScenarioSpec(
        name="s1",
        expectation=(
            "Full turn cycle x2; Pre/PostModelRequest and Pre/PostToolUse with "
            "canonical tool names; SessionEnd on clean exit."
        ),
        labels=(
            ("s1-turn-1", "first turn (OK prompt)"),
            ("s1-turn-2", "second turn (file + echo prompt)"),
            ("s1-exit", "span around /quit and SessionEnd delivery"),
        ),
    ),
    "s2": ScenarioSpec(
        name="s2",
        expectation=(
            "Trust control without bypass or pre-trust: hooks trust modal "
            "(unattended hang) or silently skipped hooks documented."
        ),
        hooks_json=True,
        bypass_hook_trust=False,
        expects_session_start=False,
        labels=(
            ("s2-trust-surface", "startup surface showing trust review or composer"),
            ("s2-post-trust-composer", "composer after any interactive trust step"),
        ),
    ),
    "s3": ScenarioSpec(
        name="s3",
        expectation=(
            "PreToolUse precedes PermissionRequest, which precedes modal capture; "
            "allow (y) settles with PostToolUse using the same tool_use_id; deny "
            "(Escape in the sandbox-escalation modal) settles with Interrupt and no Stop."
        ),
        requires_permission_lane=True,
        # workspace-write always includes /tmp (protocol.rs get_writable_roots_with_cwd),
        # so the frozen /tmp writes would run without a prompt. read-only forces the
        # approval flow for every write, which is what S3 must capture.
        extra_args=(
            "-c",
            'approval_policy="on-request"',
            "-c",
            'sandbox_mode="read-only"',
        ),
        labels=(
            ("s3-permission-allow", "span from allow-prompt submit to post-allow settle"),
            ("s3-permission-deny", "span from deny-prompt submit to post-deny settle"),
        ),
    ),
    "s4": ScenarioSpec(
        name="s4",
        expectation=(
            "PreCompact/PostCompact(trigger=manual); SessionStart(source=compact); "
            "posture continuity."
        ),
        labels=(
            ("s4-readme-turn", "first turn (README summary)"),
            ("s4-compact", "span around /compact"),
            ("s4-post-compact-turn", "turn after compaction"),
        ),
    ),
    "s5": ScenarioSpec(
        name="s5",
        expectation="Interrupt fires on Esc mid-generation; Stop does not fire for the aborted turn.",
        labels=(
            ("s5-generation", "essay generation before Esc"),
            ("s5-post-escape", "span after Esc until settle"),
        ),
    ),
    "s6": ScenarioSpec(
        name="s6",
        expectation="Second UserPromptSubmit while busy; Stop ordering under queue drain.",
        labels=(
            ("s6-first-turn", "essay turn before queued input"),
            ("s6-queued-turn", "turn consuming the queued OK prompt"),
        ),
    ),
    "s7": ScenarioSpec(
        name="s7",
        expectation=(
            "SessionStart(source=resume) after relaunch; session_id semantics "
            "across generations; SessionEnd on each clean exit."
        ),
        labels=(
            ("s7-first-turn", "OK turn before exit"),
            ("s7-exit", "exit before resume relaunch"),
            ("s7-resume", "resume relaunch and post-resume turn"),
        ),
    ),
    "f1": ScenarioSpec(
        name="f1",
        expectation=(
            "Fault arm: kill -9 mid-turn records exactly which events do not "
            "arrive (expect no Stop, no SessionEnd)."
        ),
        labels=(
            ("f1-generation", "essay generation before kill"),
            ("f1-kill", "span around kill -9 and post-kill silence"),
        ),
    ),
    "t1": ScenarioSpec(
        name="t1",
        expectation=(
            "Pre-written [hooks.state] trusted_hash runs hooks without the "
            "bypass flag; SessionStart proves the hash is load-bearing."
        ),
        bypass_hook_trust=False,
        pretrust=True,
        labels=(
            ("t1-session-start", "unattended startup with pre-trusted hooks"),
            ("t1-turn", "OK turn under pre-trusted hooks"),
        ),
    ),
    "t2": ScenarioSpec(
        name="t2",
        expectation=(
            "Session-flags (-c hooks.<Event>=[...]) injection only, no hooks.json, "
            "with hook-trust bypass; SessionStart arrives."
        ),
        hooks_json=False,
        session_flags_hooks=True,
        labels=(
            ("t2-session-start", "startup with -c injected hooks"),
            ("t2-turn", "OK turn under -c injected hooks"),
        ),
    ),
}


class AbortRun(Exception):
    """Raised when a hard campaign gate fails; the run aborts before any prompt."""

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
        return result.stdout if result.returncode == 0 else ""

    def send_text(self, text: str) -> None:
        """Type literal text with tmux send-keys -l (no gateway record)."""

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


class RunState:
    """Per-run mutable state shared across scenario step functions."""

    def __init__(
        self,
        *,
        spec: ScenarioSpec,
        run_root: Path,
        workdir: Path,
        codex_home: Path,
        collector_store: Path,
        token: str,
        generation: int,
        hooks_enabled: bool,
    ) -> None:
        """Initialize state for one scenario run."""

        self.m_spec = spec
        self.m_scenario = spec.name
        self.m_run_root = run_root
        self.m_workdir = workdir
        self.m_codex_home = codex_home
        self.m_collector_store = collector_store
        self.m_token = token
        self.m_generation = generation
        self.m_hooks_enabled = hooks_enabled
        self.m_input_log = run_root / "driver-input-events.ndjson"
        self.m_events = EventStore(collector_store / EVENTS_FILENAME)
        self.m_notes: list[str] = []
        self.m_generations: list[dict[str, Any]] = []
        self.m_drivers: dict[str, PaneDriver] = {}
        self.m_aborted: str | None = None
        self.m_session_end_observed: bool | None = None
        self.m_permission_timings: list[dict[str, Any]] = []
        self.m_extra: dict[str, Any] = {}

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

    def save_surface_snapshot(self, name: str, text: str) -> Path:
        """Persist one visible-pane snapshot under notes/ for run evidence."""

        path = self.m_run_root / "notes" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


def _toml_inline_handler(command: str, timeout: int) -> str:
    """Render one command handler as a TOML inline table."""

    return '{type="command",command=' + json.dumps(command) + f",timeout={timeout},async=false}}"


def build_session_flags_hooks(command: str) -> list[str]:
    """Return repeated ``-c hooks.<Event>=[...]`` arguments for arm T2."""

    args: list[str] = []
    for event_name in EVENT_NAMES:
        timeout = (
            SESSION_END_TIMEOUT_SECONDS
            if event_name == "SessionEnd"
            else DEFAULT_HOOK_TIMEOUT_SECONDS
        )
        value = f"[{{hooks=[{_toml_inline_handler(command, timeout)}]}}]"
        args.extend(["-c", f"hooks.{event_name}={value}"])
    return args


def write_lane_profile(path: Path, lane: LaneSpec) -> None:
    """Write the secret-free profile exactly as the selected launcher template does."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lane.profile_content, encoding="utf-8")
    path.chmod(0o600)


def generate_observer_home(*, codex_home: Path, workdir: Path) -> tuple[Path, Path]:
    """Invoke observer_hooks.py to write hooks.json and config.toml."""

    hooks_json = codex_home / "hooks.json"
    config_toml = codex_home / "config.toml"
    result = subprocess.run(
        [
            sys.executable,
            str(OBSERVER_HOOKS_SCRIPT),
            "--out",
            str(hooks_json),
            "--config-out",
            str(config_toml),
            "--workdir",
            str(workdir),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"observer_hooks.py failed: {result.stderr.strip()}")
    return hooks_json, config_toml


def write_trust_state(*, hooks_json: Path, config_toml: Path, run_root: Path) -> Path:
    """Compute every handler hash and append the `[hooks.state]` block to config.toml."""

    result = subprocess.run(
        [sys.executable, str(HASH_HOOK_SCRIPT), "--hooks-json", str(hooks_json), "--emit-state"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"hash_hook.py --emit-state failed: {result.stderr.strip()}")
    block = result.stdout.strip()
    if not block:
        raise RuntimeError("hash_hook.py emitted no state blocks")
    with config_toml.open("a", encoding="utf-8") as handle:
        handle.write("\n" + block + "\n")
    state_path = run_root / "hooks-state.toml"
    state_path.write_text(block + "\n", encoding="utf-8")
    parsed = tomllib.loads(config_toml.read_text(encoding="utf-8"))
    states = parsed.get("hooks", {}).get("state", {})
    if len(states) != len(EVENT_NAMES):
        raise RuntimeError(f"expected {len(EVENT_NAMES)} hooks.state entries, found {len(states)}")
    return state_path


def _hook_command() -> str:
    """Return the command string used by generated hooks."""

    return (
        f"{_shell_single_quote(sys.executable)} "
        f"{_shell_single_quote(str(EMIT_HOOK_SCRIPT.resolve()))}"
    )


def write_wrapper(
    *,
    path: Path,
    codex_home: Path,
    token: str,
    port: int,
    store: Path,
    generation: int,
    launcher: Path,
    launcher_args: tuple[str, ...],
    refresh_profile: bool,
) -> Path:
    """Generate the mode-0600 launch wrapper for one collector generation."""

    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    lines.append(f"export CODEX_HOME={_shell_single_quote(str(codex_home))}")
    lines.append(f"export HOUMAO_HOOK_TOKEN={_shell_single_quote(token)}")
    lines.append(
        "export HOUMAO_HOOK_COLLECTOR_URL="
        + _shell_single_quote(f"http://127.0.0.1:{port}{HOOK_ROUTE}")
    )
    lines.append(f"export HOUMAO_HOOK_STORE={_shell_single_quote(str(store))}")
    lines.append(f"export HOUMAO_HOOK_GENERATION={_shell_single_quote(str(generation))}")
    lines.append("")
    exec_line = f"exec {_shell_single_quote(str(launcher))}"
    if refresh_profile:
        exec_line += " --refresh-profile"
    for arg in launcher_args:
        exec_line += " " + _shell_single_quote(arg)
    exec_line += ' "$@"'
    lines.append(exec_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


class LaunchEnv:
    """Current collector generation plus the wrapper derived from it."""

    def __init__(
        self,
        *,
        spec: ScenarioSpec,
        run_root: Path,
        codex_home: Path,
        collector_store: Path,
        token: str,
        launcher: Path,
        launcher_args: tuple[str, ...],
    ) -> None:
        """Record paths and the per-run token."""

        self.m_spec = spec
        self.m_run_root = run_root
        self.m_codex_home = codex_home
        self.m_collector_store = collector_store
        self.m_token = token
        self.m_launcher = launcher
        self.m_launcher_args = launcher_args
        self.m_collector: CollectorProcess | None = None
        self.m_port: int | None = None
        self.m_generation = 0
        self.m_wrapper: Path | None = None
        self.m_refresh_profile = True

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
            codex_home=self.m_codex_home,
            token=self.m_token,
            port=self.m_port,
            store=self.m_collector_store,
            generation=generation,
            launcher=self.m_launcher,
            launcher_args=self.m_launcher_args,
            refresh_profile=self.m_refresh_profile,
        )
        self.m_refresh_profile = False
        return self.m_port

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
            "codex",
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
    """SIGKILL one pid and every descendant; return the pids signalled.

    The ``~/.bun/bin/codex`` launcher is a Node shim that spawns the native
    Codex binary, so killing the pane pid alone can orphan the real process.
    """

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
        except ProcessLookupError:
            continue
        except PermissionError:
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


def composer_ready(text: str) -> bool:
    """Return True when the pane shows Codex's input composer.

    Codex history renders past user prompts with the same ``›`` glyph as the
    composer, so the glyph alone is not sufficient; accept the empty-composer
    placeholder anywhere, or ``›`` only in the bottom lines of the pane.
    """

    if COMPOSER_PLACEHOLDER in text:
        return True
    tail = "\n".join(text.splitlines()[-COMPOSER_TAIL_LINES:])
    return "›" in tail


def wait_for_startup_surface(
    driver: PaneDriver, *, timeout_seconds: float = 150.0, poll_seconds: float = 0.4
) -> tuple[str, str]:
    """Return ``("trust"|"composer"|"timeout", pane_text)`` for a startup surface.

    The 0.163.0 splash briefly renders the composer placeholder before the
    Hooks browser paints, so a composer is accepted only after it stays free of
    trust-surface markers for ``COMPOSER_STABLE_SECONDS``.
    """

    deadline = time.monotonic() + timeout_seconds
    composer_since: float | None = None
    text = ""
    while time.monotonic() < deadline:
        text = driver.visible_text()
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


def _interactive_trust_hooks_browser(state: RunState, driver: PaneDriver) -> None:
    """Press ``t`` on the 0.163.0 Hooks browser (Events page), then close it."""

    state.log("interactive-trust-mode", surface="hooks_browser", keys=["t", "Escape"])
    state.save_surface_snapshot("s2-hooks-browser-before.txt", driver.visible_text())
    driver.send_key("t")
    deadline = time.monotonic() + 8.0
    after = driver.visible_text()
    while "needs review before it can run" in after and time.monotonic() < deadline:
        time.sleep(0.5)
        after = driver.visible_text()
    review_gone = "needs review before it can run" not in after
    state.save_surface_snapshot("s2-hooks-browser-after-t.txt", after)
    state.log("interactive-trust-t-result", review_gone=review_gone)
    driver.send_key("Escape")
    time.sleep(1.0)
    state.save_surface_snapshot("s2-post-trust-attempt.txt", driver.visible_text())
    if not review_gone:
        raise AbortRun("'t' did not clear the hook review count on the Hooks browser")


def _selected_trust_row(text: str) -> str | None:
    """Return the trust-menu row carrying the ``›`` selection marker, if any."""

    for line in text.splitlines():
        if "›" not in line:
            continue
        for label in (
            "Review hooks",
            "Trust all and continue",
            "Continue without trusting",
        ):
            if label in line:
                return label
    return None


def interactive_trust_all(state: RunState, driver: PaneDriver, surface_text: str) -> None:
    """Trust all hooks on whichever startup trust surface is visible.

    At 0.163.0 the surface is the Hooks browser Events page ("t trust all");
    older layouts use a selection menu. The selection-menu path starts with no
    selection, so the first Down selects "Review hooks"; the helper re-reads
    the pane after every key and only confirms when the ``›`` marker sits on
    "Trust all and continue".
    """

    if any(marker in surface_text for marker in HOOKS_BROWSER_MARKERS):
        _interactive_trust_hooks_browser(state, driver)
        return

    keys_sent: list[str] = []
    for step in range(8):
        text = driver.visible_text()
        state.save_surface_snapshot(f"s2-trust-step{step}.txt", text)
        selected = _selected_trust_row(text)
        state.log("interactive-trust-step", step=step, selected=selected)
        if selected is None or selected == "Review hooks":
            key = "Down"
        elif selected == "Trust all and continue":
            key = "Enter"
        else:
            key = "Up"
        driver.send_key(key)
        keys_sent.append(key)
        time.sleep(0.6)
        if key == "Enter":
            state.log("interactive-trust-sequence", keys=keys_sent, confirmed_row=selected)
            break
    else:
        state.log("interactive-trust-sequence", keys=keys_sent, confirmed_row=None)
        raise AbortRun("could not place the trust marker on 'Trust all and continue'")
    time.sleep(1.0)
    state.save_surface_snapshot("s2-post-trust-attempt.txt", driver.visible_text())


def bootstrap_session(
    state: RunState,
    *,
    driver: PaneDriver,
    session_start_occurrence: int = 1,
    allow_interactive_trust: bool = False,
) -> None:
    """Wait for a ready composer without keypresses and enforce the hook gate.

    For s2 (no bypass, no pre-trust) a visible hooks trust modal is the
    documented control outcome: the run aborts unless interactive trust was
    explicitly requested. Every other arm treats a trust modal as a hard
    failure because unattended operation would hang.
    """

    surface, text = wait_for_startup_surface(driver, timeout_seconds=150.0)
    trust_visible = surface == "trust"
    if surface == "timeout":
        raise AbortRun("startup surface did not settle within 150s (no composer, no trust surface)")
    if trust_visible:
        snapshot = state.save_surface_snapshot(f"{state.m_scenario}-trust-modal.txt", text)
        state.log(
            "hooks-trust-modal-visible",
            snapshot=str(snapshot),
            hooks_browser=any(marker in text for marker in HOOKS_BROWSER_MARKERS),
        )
        state.note(f"hooks trust surface visible; surface saved to {snapshot}")
        if state.m_scenario != "s2":
            raise AbortRun("hooks trust modal appeared in an auto-trust arm; hooks are not trusted")
        if not allow_interactive_trust:
            raise AbortRun(
                "s2 control: trust surface would hang an unattended session; "
                "no keypress sent (rerun with --interactive-trust to exercise trust-all)"
            )
        interactive_trust_all(state, driver, text)

    composer_deadline = time.monotonic() + 90.0
    while time.monotonic() < composer_deadline:
        text = driver.visible_text()
        if composer_ready(text):
            break
        time.sleep(1.0)
    else:
        raise AbortRun("composer did not become ready within 90s of surface settle")

    state.save_surface_snapshot(f"{state.m_scenario}-bootstrap-surface.txt", driver.visible_text())
    state.log("composer-ready", zero_keypress=not trust_visible)

    if not state.m_spec.expects_session_start:
        observed = state.m_events.wait_for_count("SessionStart", 1, timeout_seconds=5.0)
        state.note(f"s2 SessionStart observed without auto-trust: {observed}")
        return

    # Codex 0.163 queues the startup SessionStart source when the session is
    # created and dispatches it only when the first turn starts
    # (core/src/session/turn.rs, run_pending_session_start_hooks). Observe the
    # pre-prompt surface briefly for the record, then enforce the hook gate at
    # the first frozen prompt instead of hanging before any input.
    pre_prompt = state.m_events.wait_for_count(
        "SessionStart", session_start_occurrence, timeout_seconds=3.0
    )
    state.log(
        "session-start-pre-prompt",
        found=pre_prompt,
        occurrence=session_start_occurrence,
    )
    if pre_prompt:
        state.note(
            f"SessionStart occurrence {session_start_occurrence} observed before the first prompt"
        )
    else:
        state.note(
            "SessionStart is first-turn scoped in codex 0.163; the gate moves to the "
            "first frozen prompt"
        )


def exit_codex(state: RunState, *, driver: PaneDriver, session_name: str) -> None:
    """Exit Codex via /quit, falling back to double Ctrl-C; record the path."""

    if not session_alive(session_name):
        state.note(f"tmux session {session_name} already gone before exit step")
        return
    driver.send_key("C-u")
    time.sleep(0.3)
    state.log("exit-via-slash-quit")
    driver.submit_text("/quit")
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        if not session_alive(session_name):
            state.note("codex exited via /quit")
            return
        time.sleep(1.0)
    state.log("exit-via-ctrl-c", keys=["C-c", "C-c"])
    driver.send_key("C-c")
    time.sleep(1.0)
    driver.send_key("C-c")
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if not session_alive(session_name):
            state.note("codex exited via double Ctrl-C")
            return
        time.sleep(1.0)
    state.note(f"WARNING: tmux session {session_name} still alive after exit attempts")


def _record_session_end(state: RunState, *, occurrence: int = 1) -> None:
    """Wait briefly for SessionEnd and record whether it arrived."""

    observed = state.m_events.wait_for_count("SessionEnd", occurrence, timeout_seconds=10.0)
    state.m_session_end_observed = observed
    state.note(f"SessionEnd occurrence {occurrence} observed after exit: {observed}")


def require_session_start_on_first_turn(
    state: RunState, *, occurrence: int = 1, timeout_seconds: float = 45.0
) -> None:
    """Enforce the hook gate at the first prompt, where Codex dispatches SessionStart."""

    found = wait_for_event(
        state, "SessionStart", timeout_seconds=timeout_seconds, occurrence=occurrence
    )
    if not found:
        raise AbortRun(
            "SessionStart did not arrive at first-turn start; hooks are not active "
            "(trust, config, or injection failed)"
        )


def run_s0(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S0/T1/T2 gate arm: one OK prompt; core events must arrive."""

    labels = state.m_spec.labels
    if labels:
        state.log("label-window", label_id=labels[0][0])
    driver.submit_text(PROMPT_OK)
    require_session_start_on_first_turn(state)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "Stop", timeout_seconds=120.0)
    if len(labels) > 1:
        state.log("label-window", label_id=labels[1][0])
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def _handler_hash(hooks_json: Path, event_name: str) -> dict[str, str]:
    """Return the ``key`` and ``hash`` hash_hook.py computes for one handler."""

    result = subprocess.run(
        [
            sys.executable,
            str(HASH_HOOK_SCRIPT),
            "--hooks-json",
            str(hooks_json),
            "--event",
            event_name,
            "--group",
            "0",
            "--handler",
            "0",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"hash_hook.py failed: {result.stderr.strip()}")
    key = None
    digest = None
    for line in result.stdout.splitlines():
        if line.startswith("key: "):
            key = line.removeprefix("key: ").strip()
        elif line.startswith("hash: "):
            digest = line.removeprefix("hash: ").strip()
    if key is None or digest is None:
        raise RuntimeError(f"unexpected hash_hook.py output: {result.stdout!r}")
    return {"key": key, "hash": digest}


def _perturb_session_start_handler(
    *, hooks_json: Path, config_toml: Path, run_root: Path
) -> dict[str, Any]:
    """Change the SessionStart command without changing its trusted hash.

    The suffix is a shell comment, so a still-trusted handler would execute
    identically; only the hash input differs. The original document and the
    perturbed copy are kept in the run root for evidence.
    """

    original_bytes = hooks_json.read_bytes()
    (run_root / "hooks.json.pre-perturbation").write_bytes(original_bytes)
    document = json.loads(original_bytes)
    handler = document["hooks"]["SessionStart"][0]["hooks"][0]
    before = _handler_hash(hooks_json, "SessionStart")
    command_before = handler["command"]
    handler["command"] = command_before + " # t1-perturbation"
    hooks_json.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    (run_root / "hooks.json.perturbed").write_text(
        hooks_json.read_text(encoding="utf-8"), encoding="utf-8"
    )
    after = _handler_hash(hooks_json, "SessionStart")
    parsed_config = tomllib.loads(config_toml.read_text(encoding="utf-8"))
    trusted_hash = (
        parsed_config.get("hooks", {}).get("state", {}).get(before["key"], {}).get("trusted_hash")
    )
    return {
        "event": "SessionStart",
        "state_key": before["key"],
        "trusted_hash": trusted_hash,
        "hash_before": before["hash"],
        "hash_after": after["hash"],
        "hash_changed": before["hash"] != after["hash"],
        "command_before": command_before,
        "command_after": handler["command"],
        "hooks_json_pre_perturbation": str(run_root / "hooks.json.pre-perturbation"),
        "hooks_json_perturbed": str(run_root / "hooks.json.perturbed"),
    }


def run_t1(
    state: RunState,
    driver: PaneDriver,
    session_name: str,
    *,
    env: LaunchEnv,
    register_session: Callable[[str, PaneDriver], None],
    recorder_roots: list[Path],
) -> None:
    """T1 hash arm: trusted-hash launch, then an in-place hash perturbation relaunch."""

    labels = state.m_spec.labels
    if labels:
        state.log("label-window", label_id=labels[0][0])
    driver.submit_text(PROMPT_OK)
    require_session_start_on_first_turn(state)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "Stop", timeout_seconds=120.0)
    if len(labels) > 1:
        state.log("label-window", label_id=labels[1][0])
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)

    hooks_json = state.m_codex_home / "hooks.json"
    config_toml = state.m_codex_home / "config.toml"
    perturbation = _perturb_session_start_handler(
        hooks_json=hooks_json, config_toml=config_toml, run_root=state.m_run_root
    )
    state.m_extra["t1_perturbation"] = perturbation
    state.note(
        "T1 perturbation: SessionStart command changed in place; trusted_hash unchanged "
        f"({perturbation['hash_before']} -> {perturbation['hash_after']})"
    )

    env.stop_collector()
    port = env.start_generation(2)
    state.m_generations.append(
        {
            "generation": 2,
            "port": port,
            "started_at_utc": utc_now_ms(),
            "started_monotonic": round(time.monotonic(), 6),
            "reason": "t1 perturbed-hash relaunch",
        }
    )
    perturb_session = f"codexhook-t1-perturb-{os.getpid()}"
    assert env.m_wrapper is not None
    perturb_pane = launch_tmux_session(
        session_name=perturb_session,
        workdir=state.m_workdir,
        wrapper=env.m_wrapper,
    )
    perturb_driver = PaneDriver(
        session_name=perturb_session, pane_id=perturb_pane, log_path=state.m_input_log
    )
    register_session(perturb_session, perturb_driver)
    perturb_recording_root = state.m_run_root / "pane-recording-perturbed"
    start_recorder(session_name=perturb_session, run_root=perturb_recording_root)
    recorder_roots.append(perturb_recording_root)

    launched = time.monotonic()
    settled, surface_text = wait_for_startup_surface(perturb_driver, timeout_seconds=90.0)
    surface = "trust_modal" if settled == "trust" else settled
    snapshot = state.save_surface_snapshot("t1-perturbation-surface.txt", surface_text)
    perturbation["surface"] = surface
    perturbation["surface_snapshot"] = str(snapshot)
    perturbation["surface_hooks_browser"] = any(
        marker in surface_text for marker in HOOKS_BROWSER_MARKERS
    )
    perturbation["surface_elapsed_seconds"] = round(time.monotonic() - launched, 3)
    state.log("t1-perturbation-surface", surface=surface, snapshot=str(snapshot))

    if surface == "composer":
        # No trust review was painted; only a first turn can prove whether the
        # modified SessionStart handler still runs.
        perturb_driver.submit_text(PROMPT_OK)
        observed = state.m_events.wait_for_count("SessionStart", 2, timeout_seconds=30.0)
        perturbation["session_start_after_prompt"] = observed
        perturbation["outcome"] = "STILL_TRUSTED" if observed else "silent_skip"
        exit_codex(state, driver=perturb_driver, session_name=perturb_session)
        _record_session_end(state, occurrence=2)
    elif surface == "trust_modal":
        perturbation["session_start_after_prompt"] = state.m_events.count("SessionStart") >= 2
        perturbation["outcome"] = (
            "hooks_browser_review"
            if perturbation.get("surface_hooks_browser")
            else "trust_modal_review"
        )
        state.note("T1 perturbation: trust surface painted; no keypress sent")
    else:
        perturbation["session_start_after_prompt"] = state.m_events.count("SessionStart") >= 2
        perturbation["outcome"] = "no_surface"
    state.note(f"T1 perturbation outcome: {perturbation['outcome']}")


def run_s1(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S1 normal arm: two turns including a tool-using prompt, then clean exit."""

    driver.submit_text(PROMPT_OK)
    require_session_start_on_first_turn(state)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "Stop", timeout_seconds=120.0)
    driver.submit_text(PROMPT_TOOL)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0, occurrence=2)
    wait_for_event(state, "Stop", timeout_seconds=300.0, occurrence=2)
    state.note(
        "event counts before exit: "
        + json.dumps(
            {
                name: state.m_events.count(name)
                for name in (
                    "PreModelRequest",
                    "PostModelRequest",
                    "PreToolUse",
                    "PostToolUse",
                    "UserPromptSubmit",
                    "Stop",
                )
            },
            sort_keys=True,
        )
    )
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s2(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S2 trust control: document the modal/silent-skip failure mode."""

    state.log("label-window", label_id="s2-trust-surface")
    state.save_surface_snapshot("s2-trust-surface.txt", driver.visible_text())
    driver.submit_text(PROMPT_OK)
    session_start_after_trust = state.m_events.wait_for_count(
        "SessionStart", 1, timeout_seconds=15.0
    )
    state.m_extra["s2_session_start_after_trust"] = session_start_after_trust
    state.note(f"SessionStart after interactive trust: {session_start_after_trust}")
    if session_start_after_trust:
        wait_for_event(state, "UserPromptSubmit", timeout_seconds=45.0)
        wait_for_event(state, "Stop", timeout_seconds=120.0)
    else:
        wait_for_event(state, "UserPromptSubmit", timeout_seconds=15.0)
        wait_for_event(state, "Stop", timeout_seconds=45.0)
    state.log("label-window", label_id="s2-post-trust-composer")
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def _permission_step(
    state: RunState,
    *,
    driver: PaneDriver,
    prompt: str,
    key: str,
    label_id: str,
    occurrence: int,
    snapshot_name: str,
) -> None:
    """Drive one allow/deny permission cycle and record timing evidence."""

    submitted_at_utc = utc_now_ms()
    submitted_monotonic = time.monotonic()
    driver.submit_text(prompt)
    if occurrence == 1:
        require_session_start_on_first_turn(state)
    request_seen = wait_for_event(
        state, "PermissionRequest", timeout_seconds=120.0, occurrence=occurrence
    )
    modal_seen = driver.wait_any(PERMISSION_MODAL_MARKERS, timeout_seconds=90.0)
    modal_text = driver.visible_text()
    snapshot = state.save_surface_snapshot(snapshot_name, modal_text)
    state.log("label-window", label_id=label_id)
    effective_key = key
    if modal_seen and key == "auto":
        # The 0.163.0 sandbox-escalation modal offers Accept / AcceptForPrefix /
        # Cancel (esc), not Decline, so "d" is unbound. Only use "d" when the
        # explicit "No, continue without running it" option is present.
        effective_key = "d" if "No, continue without running it" in modal_text else "Escape"
    if modal_seen:
        driver.send_key(effective_key)
        time.sleep(1.0)
    else:
        state.note(f"DEVIATION: no permission modal visible for {label_id}; key not pressed")
    state.m_permission_timings.append(
        {
            "label_id": label_id,
            "prompt": prompt,
            "key": effective_key if modal_seen else None,
            "permission_request_seen": request_seen,
            "modal_seen": modal_seen,
            "submitted_at_utc": submitted_at_utc,
            "submitted_monotonic": round(submitted_monotonic, 6),
            "settled_at_utc": utc_now_ms(),
            "settled_monotonic": round(time.monotonic(), 6),
            "snapshot": str(snapshot),
        }
    )


def run_s3(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S3 permissions lane: allow with y, then deny/cancel with Escape (auto key)."""

    _permission_step(
        state,
        driver=driver,
        prompt=PROMPT_ALLOW,
        key="y",
        label_id="s3-permission-allow",
        occurrence=1,
        snapshot_name="s3-allow-modal.txt",
    )
    allow_stop = wait_for_event(state, "Stop", timeout_seconds=180.0)
    state.note(f"Stop after allow: {allow_stop}")
    _permission_step(
        state,
        driver=driver,
        prompt=PROMPT_DENY,
        key="auto",
        label_id="s3-permission-deny",
        occurrence=2,
        snapshot_name="s3-deny-modal.txt",
    )
    # A canceled/denied approval aborts the turn with Interrupt; no Stop fires.
    deny_interrupt = state.m_events.wait_for_count("Interrupt", 1, timeout_seconds=120.0)
    deny_stop = state.m_events.wait_for_count("Stop", 2, timeout_seconds=5.0)
    state.note(f"deny settle: Interrupt={deny_interrupt} Stop#2_within_5s={deny_stop}")
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s4(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S4 compaction arm: README turn, /compact, then a post-compact turn."""

    driver.submit_text(PROMPT_README)
    require_session_start_on_first_turn(state)
    wait_for_event(state, "Stop", timeout_seconds=180.0)
    state.log("label-window", label_id="s4-compact")
    driver.submit_text("/compact")
    pre_compact = wait_for_event(state, "PreCompact", timeout_seconds=90.0)
    post_compact = wait_for_event(state, "PostCompact", timeout_seconds=180.0)
    # Codex queues SessionStartSource::Compact during compaction but dispatches
    # it from run_pending_session_start_hooks at the next turn start, so wait
    # for it after submitting the post-compact prompt (it may already be there).
    driver.submit_text(PROMPT_OK)
    session_start_2 = wait_for_event(state, "SessionStart", timeout_seconds=60.0, occurrence=2)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=60.0, occurrence=2)
    post_ok_stop = wait_for_event(state, "Stop", timeout_seconds=180.0, occurrence=2)
    state.note(
        f"PreCompact={pre_compact} PostCompact={post_compact} "
        f"SessionStart#2={session_start_2} Stop#2={post_ok_stop}"
    )
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s5(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S5 interrupt arm: Esc mid-generation; Interrupt must fire and Stop must not."""

    state.log("label-window", label_id="s5-generation")
    driver.submit_text(PROMPT_RECURSION)
    require_session_start_on_first_turn(state)
    driver.wait_any_lower(BUSY_MARKERS, timeout_seconds=90.0)
    # Escape while the turn is still generating; 2.5 s is enough for the busy
    # state to be real without risking a completed turn on a fast provider.
    time.sleep(2.5)
    stop_before = state.m_events.count("Stop")
    state.log("interrupt-escape", keys=["Escape"])
    driver.send_key("Escape")
    interrupt_seen = wait_for_event(state, "Interrupt", timeout_seconds=120.0)
    time.sleep(5.0)
    stop_after = state.m_events.count("Stop")
    state.note(
        f"Interrupt observed after Escape: {interrupt_seen}; "
        f"Stop count before={stop_before} after={stop_after}"
    )
    state.log("label-window", label_id="s5-post-escape")
    driver.wait_absence("esc to interrupt", timeout_seconds=30.0)
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s6(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S6 queue/steer arm: second prompt while busy; record Stop ordering."""

    driver.submit_text(PROMPT_QUEUES)
    require_session_start_on_first_turn(state)
    busy = driver.wait_any_lower(BUSY_MARKERS, timeout_seconds=90.0)
    state.note(f"busy marker visible before queued input: {busy}")
    # Submit the second prompt while the first turn is still generating.
    time.sleep(2.0)
    state.log("label-window", label_id="s6-queued-turn")
    driver.submit_text(PROMPT_OK)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0, occurrence=2)
    first_stop = wait_for_event(state, "Stop", timeout_seconds=240.0)
    # 0.163.0 steers the second prompt into the running turn instead of
    # queueing a new one; a second Stop only exists if a separate turn starts.
    second_stop = state.m_events.wait_for_count("Stop", 2, timeout_seconds=15.0)
    prompt_turns = [
        row.get("provider_event", {}).get("turn_id")
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "UserPromptSubmit"
    ]
    stop_turns = [
        row.get("provider_event", {}).get("turn_id")
        for row in state.m_events.rows()
        if row.get("provider_event", {}).get("hook_event_name") == "Stop"
    ]
    state.m_extra["s6_user_prompt_turn_ids"] = prompt_turns
    state.m_extra["s6_stop_turn_ids"] = stop_turns
    state.m_extra["s6_second_stop_within_15s"] = second_stop
    state.note(
        f"first Stop: {first_stop}; second Stop within 15s (steer->same turn): {second_stop}; "
        f"prompt turn_ids={prompt_turns}; stop turn_ids={stop_turns}"
    )
    state.log("s6-event-order-snapshot", sequence=state.m_events.event_names())
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)


def run_s7(
    state: RunState,
    driver: PaneDriver,
    session_name: str,
    *,
    env: LaunchEnv,
    register_session: Callable[[str, PaneDriver], None],
    recorder_roots: list[Path],
) -> None:
    """S7 resume arm: first turn, exit, relaunch with ``codex resume <id>``."""

    driver.submit_text(PROMPT_OK)
    require_session_start_on_first_turn(state)
    wait_for_event(state, "UserPromptSubmit", timeout_seconds=90.0)
    wait_for_event(state, "Stop", timeout_seconds=120.0)
    session_id = state.m_events.provider_field("SessionStart", "session_id")
    state.note(f"session id captured for resume: {session_id!r}")
    state.log("label-window", label_id="s7-exit")
    exit_codex(state, driver=driver, session_name=session_name)
    _record_session_end(state)

    state.note("relaunching with codex resume (collector generation bump)")
    env.stop_collector()
    port = env.start_generation(2)
    state.m_generations.append(
        {
            "generation": 2,
            "port": port,
            "started_at_utc": utc_now_ms(),
            "started_monotonic": round(time.monotonic(), 6),
            "reason": "s7 resume relaunch",
        }
    )
    resume_session = f"codexhook-s7-resume-{os.getpid()}"
    assert env.m_wrapper is not None
    if isinstance(session_id, str) and session_id:
        resume_args: tuple[str, ...] = ("resume", session_id)
    else:
        resume_args = ("resume", "--last")
        state.note("no SessionStart session_id captured; falling back to --last")
    resume_pane = launch_tmux_session(
        session_name=resume_session,
        workdir=state.m_workdir,
        wrapper=env.m_wrapper,
        extra_args=resume_args,
    )
    resume_driver = PaneDriver(
        session_name=resume_session, pane_id=resume_pane, log_path=state.m_input_log
    )
    register_session(resume_session, resume_driver)
    resume_recording_root = state.m_run_root / "pane-recording-resume"
    start_recorder(session_name=resume_session, run_root=resume_recording_root)
    recorder_roots.append(resume_recording_root)
    time.sleep(4.0)
    state.save_surface_snapshot("s7-resume-launch-surface.txt", resume_driver.visible_text())
    state.log("label-window", label_id="s7-resume")
    bootstrap_session(state, driver=resume_driver, session_start_occurrence=2)
    resume_driver.submit_text(PROMPT_OK)
    require_session_start_on_first_turn(state, occurrence=2)
    resume_stop = wait_for_event(state, "Stop", timeout_seconds=180.0, occurrence=2)
    state.note(f"Stop after post-resume OK prompt: {resume_stop}")
    exit_codex(state, driver=resume_driver, session_name=resume_session)
    _record_session_end(state, occurrence=2)


def run_f1(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """F1 fault arm: kill -9 the codex process tree mid-generation."""

    state.log("label-window", label_id="f1-generation")
    driver.submit_text(PROMPT_FAULTS)
    driver.wait_any_lower(BUSY_MARKERS, timeout_seconds=90.0)
    # Kill while the turn is generating; a 3 s lead keeps the fault mid-turn
    # even if the provider starts streaming quickly.
    time.sleep(3.0)
    pid = pane_pid(driver.pane_id)
    state.log("kill-process-tree", pane_pid=pid)
    signalled = kill_process_tree(pid) if pid is not None else []
    state.note(f"kill -9 signalled pids: {signalled}")
    baseline = state.m_events.snapshot_index()
    state.log("label-window", label_id="f1-kill")
    time.sleep(12.0)
    after = state.m_events.names_since(baseline)
    state.note(f"events after kill -9: {after or 'none'}")
    state.m_extra["f1_post_kill_events"] = after


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
    "t1": run_t1,
    "t2": run_s0,
}


def _default_run_root(scenario: str) -> Path:
    """Return the default run root for one scenario."""

    return RUN_ROOT_BASE / scenario / f"run-{utc_stamp()}"


def write_labels_template(state: RunState, labels_dir: Path) -> None:
    """Write the labels template mirroring the scenario's predeclared windows."""

    doc = {
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
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )


def write_raw_payload_log(state: RunState, run_root: Path) -> Path:
    """Write provider payloads without collector envelope metadata.

    This is the campaign's raw payload log: one pristine Codex hook payload
    per line, in collector receive order, suitable for the payload catalog.
    """

    path = run_root / "raw-provider-payloads.ndjson"
    with path.open("w", encoding="utf-8") as handle:
        for row in state.m_events.rows():
            provider = row.get("provider_event")
            if isinstance(provider, dict):
                handle.write(json.dumps(provider, sort_keys=True) + "\n")
    return path


def write_run_summary(state: RunState, run_root: Path, collector_store: Path) -> None:
    """Write run-summary.json with counts, ordering, and collected notes."""
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
        "codex_home": str(state.m_codex_home),
        "hooks_enabled": state.m_hooks_enabled,
        "aborted": state.m_aborted is not None,
        "abort_reason": state.m_aborted,
        "collector_generations": state.m_generations,
        "collector_final_status": final_status,
        "event_counts": dict(sorted(Counter(names).items())),
        "event_sequence": names,
        "session_end_observed": state.m_session_end_observed,
        "permission_timings": state.m_permission_timings,
        "extra": state.m_extra,
        "notes": state.m_notes,
        "finished_at_utc": utc_now_ms(),
        "finished_monotonic": round(time.monotonic(), 6),
    }
    (run_root / "run-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _load_hooks_event_names(hooks_json: Path) -> list[str]:
    """Return the event keys declared in a hooks.json file."""

    try:
        document = json.loads(hooks_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        return []
    return list(hooks)


def prepare_home(
    *,
    state: RunState,
    spec: ScenarioSpec,
    lane: LaneSpec,
) -> dict[str, Any]:
    """Create the scratch CODEX_HOME, lane profile, hooks, trust state, and config."""

    state.m_codex_home.mkdir(parents=True, exist_ok=True)
    state.m_workdir.mkdir(parents=True, exist_ok=True)
    if spec.name == "s4":
        (state.m_workdir / "README.md").write_text(S4_README_TEXT, encoding="utf-8")
    profile_path = state.m_codex_home / lane.profile_filename
    write_lane_profile(profile_path, lane)

    hooks_json = state.m_codex_home / "hooks.json"
    config_toml = state.m_codex_home / "config.toml"
    hooks_info: dict[str, Any] = {
        "lane": lane.name,
        "launcher_name": lane.launcher_name,
        "profile_name": lane.profile_name,
        "profile_path": str(profile_path),
        "profile_sha256": _sha256_file(profile_path),
        "hooks_json_path": str(hooks_json),
        "config_toml_path": str(config_toml),
        "state_block_path": None,
        "events": [],
        "session_flags_events": list(EVENT_NAMES) if spec.session_flags_hooks else [],
        "command": _hook_command(),
    }
    if spec.hooks_json:
        hooks_json, config_toml = generate_observer_home(
            codex_home=state.m_codex_home, workdir=state.m_workdir
        )
        hooks_info["events"] = _load_hooks_event_names(hooks_json)
        if spec.pretrust:
            state_block = write_trust_state(
                hooks_json=hooks_json, config_toml=config_toml, run_root=state.m_run_root
            )
            hooks_info["state_block_path"] = str(state_block)
    else:
        # Arm T2 injects hooks through session flags; no user hooks.json may exist.
        generate_observer_home(codex_home=state.m_codex_home, workdir=state.m_workdir)
        hooks_json.unlink(missing_ok=True)
        hooks_info["hooks_json_path"] = None
    hooks_info["hooks_json_sha256"] = _sha256_file(hooks_json) if hooks_json.is_file() else None
    hooks_info["config_toml_sha256"] = _sha256_file(config_toml)
    return hooks_info


def run_scenario(
    scenario: str,
    run_root_override: Path | None,
    *,
    launcher: Path,
    lane_override: str,
    allow_permission_lane: bool,
    interactive_trust: bool,
) -> int:
    """Run one scenario end to end with full teardown; return a process exit code."""

    spec = SCENARIOS[scenario]
    lane = resolve_lane(launcher, lane_override)
    if spec.requires_permission_lane and not allow_permission_lane:
        print(
            "ABORTED (s3): the default codex-openlux-auto launcher "
            "hardcodes --dangerously-bypass-approvals-and-sandbox, and that "
            "harness override wins over -c approval_policy, so PermissionRequest can "
            "never fire. Supply a custom launcher without the bypass via --launcher, "
            "name its lane with --lane, and add --allow-permission-lane.",
            file=sys.stderr,
        )
        return 0

    run_root = (run_root_override or _default_run_root(scenario)).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    workdir = (run_root / "workdir").resolve()
    codex_home = (run_root / "codex-home").resolve()
    collector_store = run_root / "collector"
    labels_dir = run_root / "labels"
    labels_dir.mkdir(exist_ok=True)

    token = secrets.token_hex(16)
    command = _hook_command()
    launcher_args: list[str] = list(spec.extra_args)
    if spec.bypass_hook_trust:
        launcher_args.append("--dangerously-bypass-hook-trust")
    if spec.session_flags_hooks:
        launcher_args.extend(build_session_flags_hooks(command))

    state = RunState(
        spec=spec,
        run_root=run_root,
        workdir=workdir,
        codex_home=codex_home,
        collector_store=collector_store,
        token=token,
        generation=1,
        hooks_enabled=spec.hooks_json or spec.session_flags_hooks,
    )
    env = LaunchEnv(
        spec=spec,
        run_root=run_root,
        codex_home=codex_home,
        collector_store=collector_store,
        token=token,
        launcher=launcher,
        launcher_args=tuple(launcher_args),
    )
    sessions: list[str] = []
    recorder_roots: list[Path] = []
    launched_monotonic = time.monotonic()
    launched_at_utc = utc_now_ms()
    codex_binary = _resolve_codex_binary()
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "scenario": scenario,
        "expectation": spec.expectation,
        "run_root": str(run_root),
        "workdir": str(workdir),
        "codex_home": str(codex_home),
        "runner_pid": os.getpid(),
        "launcher": {
            "path": str(launcher),
            "sha256": _sha256_file(launcher),
            "lane": lane.name,
            "profile_name": lane.profile_name,
            "profile_filename": lane.profile_filename,
            "lane_override": lane_override,
            "refresh_profile_first_generation": True,
            "args": launcher_args,
        },
        "codex": codex_binary,
        "collector": {
            "store": str(collector_store),
            "token_env": "HOUMAO_HOOK_TOKEN",
            "generations": state.m_generations,
        },
        "hooks": {},
        "time": {
            "launched_at_utc": launched_at_utc,
            "launched_monotonic": round(launched_monotonic, 6),
            "finished_at_utc": None,
            "finished_monotonic": None,
        },
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

        tmp_path = manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_path, manifest_path)

    def register_session(name: str, driver: PaneDriver) -> None:
        """Track one session and its driver for exit and teardown."""

        sessions.append(name)
        state.m_drivers[name] = driver

    try:
        hooks_info = prepare_home(state=state, spec=spec, lane=lane)
        manifest["hooks"] = hooks_info
        state.note(f"credential lane: {lane.name} (launcher {lane.launcher_name})")
        if spec.pretrust:
            state.note(
                "pre-trusted hashes written for all 14 handlers (arm T1); "
                "no --dangerously-bypass-hook-trust"
            )
        if spec.session_flags_hooks:
            state.note(
                "arm T2: hooks injected only through -c session flags; "
                "no hooks.json in the scratch CODEX_HOME"
            )
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
        manifest["collector"]["generations"] = state.m_generations
        session_name = f"codexhook-{scenario}-{os.getpid()}"
        assert env.m_wrapper is not None
        pane_id = launch_tmux_session(
            session_name=session_name, workdir=workdir, wrapper=env.m_wrapper
        )
        driver = PaneDriver(session_name=session_name, pane_id=pane_id, log_path=state.m_input_log)
        register_session(session_name, driver)
        manifest["tmux"] = {
            "session": session_name,
            "pane": pane_id,
            "pane_pid": pane_pid(pane_id),
            "width": PANE_WIDTH,
            "height": PANE_HEIGHT,
        }
        write_manifest()
        print(f"scenario {scenario}: tmux={session_name} pane={pane_id} port={port}")

        start_recorder(session_name=session_name, run_root=run_root / "pane-recording")
        recorder_roots.append(run_root / "pane-recording")
        bootstrap_session(
            state,
            driver=driver,
            allow_interactive_trust=interactive_trust,
        )
        step = STEPS[scenario]
        if scenario in ("s7", "t1"):
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
            (collector_store / EVENTS_FILENAME).touch(exist_ok=True)
            write_raw_payload_log(state, run_root)
            write_labels_template(state, labels_dir)
        except Exception as exc:  # teardown must not raise
            print(f"warning: labels template write failed: {exc!r}", file=sys.stderr)
        try:
            write_run_summary(state, run_root, collector_store)
        except Exception as exc:  # teardown must not raise
            print(f"warning: run summary write failed: {exc!r}", file=sys.stderr)
        manifest["collector"]["generations"] = state.m_generations
        manifest["time"]["finished_at_utc"] = utc_now_ms()
        manifest["time"]["finished_monotonic"] = round(time.monotonic(), 6)
        manifest["aborted"] = state.m_aborted is not None
        manifest["abort_reason"] = state.m_aborted
        try:
            write_manifest()
        except Exception as exc:  # teardown must not raise
            print(f"warning: launch manifest write failed: {exc!r}", file=sys.stderr)


def _curl_post(url: str, body: str, token: str) -> str:
    """POST one raw body with curl; return the HTTP status code as text."""

    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "-X",
            "POST",
            "-H",
            f"Authorization: Bearer {token}",
            "-H",
            "Content-Type: application/json",
            "--data-binary",
            body,
            url,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.stdout.strip()


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


def _count_event_lines(path: Path) -> int:
    """Count non-empty lines in events.ndjson (0 when absent)."""

    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def self_test() -> int:
    """Run the provider-free G0 harness self-test; non-zero exit on any FAIL."""

    checks: list[tuple[str, bool, str]] = []
    stamp = utc_stamp()
    root = RUN_ROOT_BASE / "self-test" / f"run-{stamp}"
    store = root / "collector"
    store.mkdir(parents=True, exist_ok=True)
    events_path = store / EVENTS_FILENAME
    collector_status_path = store / COLLECTOR_FILENAME
    token = secrets.token_hex(16)
    observer_root = root / "observer"
    observer_workdir = observer_root / "workdir"
    observer_workdir.mkdir(parents=True, exist_ok=True)
    observer_result = subprocess.run(
        [
            sys.executable,
            str(OBSERVER_HOOKS_SCRIPT),
            "--out",
            str(observer_root / "hooks.json"),
            "--config-out",
            str(observer_root / "config.toml"),
            "--workdir",
            str(observer_workdir),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    collector = CollectorProcess(
        store=store,
        token=token,
        generation=1,
        log_path=store / "collector.log",
        heartbeat_seconds=0.5,
    )
    try:
        port = collector.start()
        url = f"http://127.0.0.1:{port}{HOOK_ROUTE}"
        heartbeat_on_start = collector_status_path.is_file()
        checks.append(("collector-heartbeat-written-on-start", heartbeat_on_start, ""))

        status = _curl_post(
            f"{url}?event=G0CurlPost&seq=99",
            json.dumps({"hook_event_name": "G0CurlPost", "probe": "a"}),
            token,
        )
        found = _wait_for_event_name(events_path, "G0CurlPost", timeout_seconds=5.0)
        checks.append(
            ("curl-post-accepted", status == "204" and found, f"status={status} found={found}")
        )

        row = _find_event_row(events_path, "G0CurlPost")
        timestamp_ok = False
        delivery_ok = False
        if row is not None:
            timestamp_ok = bool(
                UTC_MS_PATTERN.match(str(row.get("received_at_utc")))
            ) and isinstance(row.get("received_at_monotonic"), float)
            delivery = row.get("delivery")
            delivery_ok = (
                isinstance(delivery, dict)
                and delivery.get("event") == "G0CurlPost"
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
            ("delivery-metadata", delivery_ok, json.dumps(row.get("delivery")) if row else "no row")
        )

        base_lines = _count_event_lines(events_path)
        wrong_status = _curl_post(
            url, json.dumps({"hook_event_name": "G0WrongToken"}), "wrong-token"
        )
        checks.append(
            (
                "wrong-token-rejected",
                wrong_status in ("401", "403") and _count_event_lines(events_path) == base_lines,
                f"status={wrong_status}",
            )
        )

        malformed_status = _curl_post(url, "{not-json", token)
        checks.append(
            (
                "malformed-json-rejected",
                malformed_status == "400",
                f"status={malformed_status}",
            )
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

        shell_env = os.environ.copy()
        shell_env["HOUMAO_HOOK_COLLECTOR_URL"] = url
        shell_env["HOUMAO_HOOK_TOKEN"] = token
        shell_env["HOUMAO_HOOK_STORE"] = str(store)
        shell_env["HOUMAO_HOOK_GENERATION"] = "1"
        try:
            hooks_document = json.loads((observer_root / "hooks.json").read_text(encoding="utf-8"))
            shell_command = hooks_document["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
            shell_result = subprocess.run(
                ["bash", "-c", shell_command],
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
        checks.append(("hooks-json-command-via-shell", shell_ok, shell_note))

        collector.stop()
        fallback_result = _run_emit_hook(
            {"hook_event_name": "SelfTestFallback", "probe": "c"},
            url=url,
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
                and fallback_row.get("sequence") is None,
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
    finally:
        collector.stop()

    observer_ok = False
    observer_note = observer_result.stderr.strip()
    try:
        document = json.loads((observer_root / "hooks.json").read_text(encoding="utf-8"))
        hooks = document["hooks"]
        events_ok = set(hooks) == set(EVENT_NAMES)
        handler_shapes_ok = True
        timeout_ok = True
        for event_name, groups in hooks.items():
            if len(groups) != 1 or len(groups[0].get("hooks", [])) != 1:
                handler_shapes_ok = False
                continue
            handler = groups[0]["hooks"][0]
            if (
                handler.get("type") != "command"
                or handler.get("async") is not False
                or "emit_hook.py" not in str(handler.get("command"))
            ):
                handler_shapes_ok = False
            expected = (
                SESSION_END_TIMEOUT_SECONDS
                if event_name == "SessionEnd"
                else DEFAULT_HOOK_TIMEOUT_SECONDS
            )
            if handler.get("timeout") != expected:
                timeout_ok = False
        config = tomllib.loads((observer_root / "config.toml").read_text(encoding="utf-8"))
        projects = config.get("projects", {})
        trust_ok = projects.get(str(observer_workdir.resolve()), {}).get("trust_level") == "trusted"
        notice_ok = config.get("notice", {}).get("hide_full_access_warning") is True
        observer_ok = (
            observer_result.returncode == 0
            and events_ok
            and handler_shapes_ok
            and timeout_ok
            and trust_ok
            and notice_ok
        )
        observer_note = (
            f"events={len(hooks)} shapes={handler_shapes_ok} timeouts={timeout_ok} "
            f"trust={trust_ok} notice={notice_ok}"
        )
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        observer_note = f"{observer_note} exception={exc!r}"
    checks.append(("observer-hooks-14-events-and-config", observer_ok, observer_note))

    prepared_root = root / "prepared-home"
    prepared_state = RunState(
        spec=SCENARIOS["t1"],
        run_root=prepared_root,
        workdir=prepared_root / "workdir",
        codex_home=prepared_root / "codex-home",
        collector_store=prepared_root / "collector",
        token="selftest-token",
        generation=1,
        hooks_enabled=True,
    )
    prepared_note = ""
    prepared_ok = False
    selftest_lane = LANES[DEFAULT_LANE]
    try:
        prepared_info = prepare_home(state=prepared_state, spec=SCENARIOS["t1"], lane=selftest_lane)
        prepared_config = tomllib.loads(
            (prepared_root / "codex-home" / "config.toml").read_text(encoding="utf-8")
        )
        prepared_states = prepared_config.get("hooks", {}).get("state", {})
        prepared_trust = (
            prepared_config.get("projects", {})
            .get(str((prepared_root / "workdir").resolve()), {})
            .get("trust_level")
            == "trusted"
        )
        wrapper_path = write_wrapper(
            path=prepared_root / "wrapper.sh",
            codex_home=prepared_root / "codex-home",
            token="selftest-token",
            port=1,
            store=prepared_root / "collector",
            generation=1,
            launcher=DEFAULT_LAUNCHER,
            launcher_args=("--dangerously-bypass-hook-trust",),
            refresh_profile=True,
        )
        wrapper_text = wrapper_path.read_text(encoding="utf-8")
        bash_check = subprocess.run(
            ["bash", "-n", str(wrapper_path)], capture_output=True, text=True, timeout=20
        )
        prepared_profile = prepared_root / "codex-home" / selftest_lane.profile_filename
        token_leak = "selftest-token" in (
            (prepared_root / "codex-home" / "hooks.json").read_text(encoding="utf-8")
            + (prepared_root / "codex-home" / "config.toml").read_text(encoding="utf-8")
            + prepared_profile.read_text(encoding="utf-8")
        )
        prepared_ok = (
            prepared_info.get("hooks_json_path") is not None
            and prepared_info.get("lane") == selftest_lane.name
            and prepared_profile.is_file()
            and prepared_profile.read_text(encoding="utf-8") == selftest_lane.profile_content
            and (prepared_profile.stat().st_mode & 0o777) == 0o600
            and len(prepared_states) == len(EVENT_NAMES)
            and prepared_trust
            and (wrapper_path.stat().st_mode & 0o777) == 0o600
            and bash_check.returncode == 0
            and "CODEX_HOME=" in wrapper_text
            and "HOUMAO_HOOK_TOKEN=" in wrapper_text
            and not token_leak
        )
        prepared_note = (
            f"lane={prepared_info.get('lane')} state_entries={len(prepared_states)} "
            f"trust={prepared_trust} profile={selftest_lane.profile_filename} "
            f"wrapper_mode={oct(wrapper_path.stat().st_mode & 0o777)} "
            f"bash_n={bash_check.returncode} token_in_config={token_leak}"
        )
    except Exception as exc:  # self-test must report, not crash
        prepared_note = f"exception={exc!r}"
    checks.append(("scratch-home-pretrust-and-wrapper", prepared_ok, prepared_note))

    lane_checks = (
        resolve_lane(Path("/x/codex-openlux-auto")).name == "openlux-auto",
        resolve_lane(Path("/x/custom-launcher")).name == DEFAULT_LANE,
        resolve_lane(Path("/x/custom-launcher"), "openlux-auto").name == "openlux-auto",
    )
    checks.append(
        (
            "lane-mapping",
            all(lane_checks),
            f"default={DEFAULT_LANE} openlux={lane_checks[0]} "
            f"fallback={lane_checks[1]} override={lane_checks[2]}",
        )
    )

    hash_self = subprocess.run(
        [sys.executable, str(HASH_HOOK_SCRIPT), "--self-test"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    checks.append(
        (
            "hash-fixtures-and-normalization",
            hash_self.returncode == 0 and "HASH SELF-TEST PASSED" in hash_self.stdout,
            hash_self.stdout.strip().splitlines()[-1]
            if hash_self.stdout.strip()
            else hash_self.stderr.strip(),
        )
    )

    state_result = subprocess.run(
        [
            sys.executable,
            str(HASH_HOOK_SCRIPT),
            "--hooks-json",
            str(observer_root / "hooks.json"),
            "--emit-state",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    state_blocks = [block for block in state_result.stdout.strip().split("\n\n") if block.strip()]
    try:
        tomllib.loads(state_result.stdout)
        state_parse_ok = True
    except tomllib.TOMLDecodeError:
        state_parse_ok = False
    checks.append(
        (
            "hash-emit-state-14-blocks-and-toml-parse",
            state_result.returncode == 0
            and len(state_blocks) == len(EVENT_NAMES)
            and state_parse_ok,
            f"blocks={len(state_blocks)} parse={state_parse_ok}",
        )
    )

    single_result = subprocess.run(
        [
            sys.executable,
            str(HASH_HOOK_SCRIPT),
            "--hooks-json",
            str(observer_root / "hooks.json"),
            "--event",
            "UserPromptSubmit",
            "--group",
            "0",
            "--handler",
            "0",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    single_lines = single_result.stdout.strip().splitlines()
    single_ok = (
        len(single_lines) == 2
        and single_lines[0].endswith(":user_prompt_submit:0:0")
        and single_lines[1].startswith("hash: sha256:")
    )
    checks.append(("hash-single-key-and-hash-output", single_ok, " | ".join(single_lines)))

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
        "--launcher",
        type=Path,
        default=DEFAULT_LAUNCHER,
        help="credential launcher (default: ~/.local/bin/codex-openlux-auto)",
    )
    parser.add_argument(
        "--lane",
        choices=("auto", *LANES),
        default="auto",
        help="credential lane/profile mapping (default: auto from launcher basename)",
    )
    parser.add_argument(
        "--allow-permission-lane",
        action="store_true",
        help="allow s3 with a custom launcher that does not hardcode the approvals bypass",
    )
    parser.add_argument(
        "--interactive-trust",
        action="store_true",
        help="s2 only: exercise the trust-all modal instead of aborting at it",
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
    # The wrapper is exec'd with the scratch workdir as cwd, so a relative
    # --launcher path would not resolve inside the tmux pane.
    launcher = args.launcher.expanduser().resolve()
    if not launcher.is_file():
        parser.error(f"--launcher does not resolve to a file: {launcher}")
    return run_scenario(
        args.scenario,
        args.run_root,
        launcher=launcher,
        lane_override=args.lane,
        allow_permission_lane=args.allow_permission_lane,
        interactive_trust=args.interactive_trust,
    )


if __name__ == "__main__":
    raise SystemExit(main())
