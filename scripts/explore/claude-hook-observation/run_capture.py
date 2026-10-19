"""One-command scenario runner for the 2026-10-19 hook-observation campaign.

Throwaway harness (see
context/campaigns/debug/2026-10-19-claude-hook-observation/iterations/2026-10-19-plan-1-hook-capture-matrix.md).
Launches Claude Code in a detached tmux session through the deepseek launcher
lane with session-scoped observer settings, drives one frozen scenario arm
(S0-S7 or the hooks-off S1 control) with tracker-blind tmux send-keys, records
the pane at 5 fps, and writes launch metadata, a managed input-event log, and
a labels template. Stdlib-only imports plus the repo's ``run_tmux`` helper.

Nothing here is production code. No live provider session is started by the
``--self-test`` gate (G0), which is provider-free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from houmao.agents.realm_controller.backends.tmux_runtime import run_tmux

REPO_ROOT = Path(__file__).resolve().parents[3]
HARNESS_DIR = Path(__file__).resolve().parent
OBSERVER_SETTINGS_SCRIPT = HARNESS_DIR / "observer_settings.py"
COLLECTOR_SCRIPT = HARNESS_DIR / "collector.py"
EMIT_HOOK_SCRIPT = HARNESS_DIR / "emit_hook.py"
RUN_ROOT_BASE = REPO_ROOT / "tmp" / "hook-capture"
LAUNCHER = Path.home() / ".local" / "bin" / "claude-deepseek"
PANE_WIDTH = 220
PANE_HEIGHT = 56
RECORDER_INTERVAL_SECONDS = 0.2

TRUST_DIALOG_PATTERN = "Quick safety check"
COMPOSER_MARKERS = ("bypass permissions on", "for shortcuts", "❯")
# 2.1.303 renders the raw launcher-pinned model id in the banner
# ("deepseek-flash[1m] with max effort · API Usage Billing"); the friendly
# name pin (ANTHROPIC_DEFAULT_SONNET_MODEL_NAME) does not apply there. Accept
# either form so the gate checks the launcher pin, not the rendering.
MODEL_GATE_NEEDLES = ("deepseek-flash[1m]", "DeepSeek Flash")
BUSY_MARKERS = ("esc to interrupt",)
PERMISSION_MODAL_MARKERS = ("Do you want", "Permission")
RESUME_PICKER_NEEDLE = "resume"

# Optional scratch-binary override for floor checks (set by --claude-bin or
# the HOOKCAP_CLAUDE_BIN env var). When set, the normal lane wrapper
# replicates the launcher environment inline and execs this binary instead
# of the host-resolved one; the host install is never touched.
_CLAUDE_BIN_OVERRIDE: Path | None = None

# Injection mode: "settings" (session-scoped --settings, default) or "home"
# (marker-merged observer block in a scratch managed home's settings.json via
# CLAUDE_CONFIG_DIR; no --settings flag is passed at all).
_INJECT_VIA = "settings"

PROMPT_OK = "Reply with exactly: OK"
PROMPT_2PLUS2 = "What is 2+2? Reply with just the number."
PROMPT_ALLOW = "Create a file named /tmp/houmao-hook-allow.txt containing hello"
PROMPT_DENY = "Create a file named /tmp/houmao-hook-deny.txt containing hello"
PROMPT_README = "Read README.md and summarize in one sentence."
PROMPT_BG = "Run `sleep 90` in the background with run_in_background, then reply with exactly: DONE"
PROMPT_RECURSION = "Write a long essay about recursion."
PROMPT_QUEUES = "Write a long essay about queues."

SCENARIO_NAMES = ("s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s1-control")

SCENARIOS: dict[str, dict[str, Any]] = {
    "s0": {
        "hooks": True,
        "expectation": (
            "SessionStart + UserPromptSubmit + Stop arrive; provider behavior unchanged."
        ),
    },
    "s1": {
        "hooks": True,
        "expectation": "full turn cycle x2; SessionEnd on exit if supported.",
    },
    "s2": {
        "hooks": True,
        "expectation": "UserPromptSubmit fires without any gateway submission record.",
    },
    "s3": {
        "hooks": True,
        "permissions_lane": True,
        "expectation": (
            "PermissionRequest before modal paint; resolution event on allow; "
            "silence on deny per design Gap 4."
        ),
    },
    "s4": {
        "hooks": True,
        "expectation": "PreCompact/PostCompact payloads; turn identity continuity.",
    },
    "s5": {
        "hooks": True,
        "expectation": (
            "Stop with background_tasks; whatever fires at sleep completion; "
            "any task/notification events recorded."
        ),
    },
    "s6": {
        "hooks": True,
        "expectation": "whether Esc emits Stop; best-effort StopFailure arm.",
    },
    "s7": {
        "hooks": True,
        "expectation": "event ordering at queue consumption; new SessionStart with resume source.",
    },
    "s1-control": {
        "hooks": False,
        "expectation": (
            "hooks-off matched control for P2.3: identical prompts to s1 with "
            "pane + wall-clock timing only."
        ),
    },
}

LABEL_SLOTS: dict[str, list[dict[str, str]]] = {
    "s0": [
        {"label_id": "s0-composer-ready", "note": "post-trust composer surface before the prompt"},
        {"label_id": "s0-turn-ok", "note": "span from prompt submit to visible OK answer"},
    ],
    "s1": [
        {"label_id": "s1-turn-1", "note": "first turn (OK prompt)"},
        {"label_id": "s1-turn-2", "note": "second turn (2+2 prompt)"},
        {"label_id": "s1-exit", "note": "span around /exit and any SessionEnd evidence"},
    ],
    "s2": [
        {"label_id": "s2-direct-input", "note": "span from raw send-keys prompt to visible answer"},
    ],
    "s3": [
        {
            "label_id": "s3-permission-allow",
            "note": "span from allow-prompt submit to post-allow settle",
        },
        {
            "label_id": "s3-permission-deny",
            "note": "span from deny-prompt submit to post-deny settle",
        },
    ],
    "s4": [
        {"label_id": "s4-readme-turn", "note": "first turn (README summary)"},
        {"label_id": "s4-compact", "note": "span around /compact (PreCompact/PostCompact)"},
        {"label_id": "s4-post-compact-turn", "note": "turn after compaction"},
    ],
    "s5": [
        {"label_id": "s5-background-turn", "note": "turn that starts the background sleep"},
        {
            "label_id": "s5-idle-wait",
            "note": "idle span after Stop while sleep 90 runs to completion",
        },
    ],
    "s6": [
        {"label_id": "s6-generation", "note": "essay generation before Esc"},
        {"label_id": "s6-post-escape", "note": "span after Esc until settle"},
    ],
    "s7": [
        {"label_id": "s7-first-turn", "note": "essay turn before queued input"},
        {"label_id": "s7-queued-turn", "note": "turn consuming the queued OK prompt"},
        {"label_id": "s7-resume", "note": "relaunch with --resume (picker + new SessionStart)"},
    ],
    "s1-control": [
        {"label_id": "s1c-turn-1", "note": "hooks-off first turn (P2.3 timing)"},
        {"label_id": "s1c-turn-2", "note": "hooks-off second turn (P2.3 timing)"},
    ],
}

S4_README_TEXT = (
    "# Hook capture scratch project\n"
    "\n"
    "Temporary git-less workdir for the hook-observation campaign.\n"
    "This file exists so s4 has a README to read and summarize.\n"
)


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON line, creating parent directories on demand."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _shell_single_quote(value: str) -> str:
    """Quote one value for safe inclusion in a generated bash script."""

    if "'" in value:
        raise ValueError(f"refusing to quote value containing a single quote: {value!r}")
    return f"'{value}'"


class AbortRun(Exception):
    """Raised when a hard campaign gate fails; the run aborts before any prompt."""

    def __init__(self, reason: str) -> None:
        """Store the human-readable abort reason."""

        super().__init__(reason)
        self.m_reason = reason


class CollectorProcess:
    """Started collector subprocess; parses the ``PORT <n>`` startup line."""

    def __init__(self, *, store: Path, token: str, generation: int, log_path: Path) -> None:
        """Record launch parameters without starting the process."""

        self.m_store = store
        self.m_token = token
        self.m_generation = generation
        self.m_log_path = log_path
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
            "ts_utc": _utc_now_iso(),
            "monotonic": round(time.monotonic(), 6),
            "action": action,
        }
        if detail:
            row["detail"] = detail
        _append_jsonl(self.m_log_path, row)

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

    def wait_absence(self, pattern: str, *, timeout_seconds: float) -> bool:
        """Poll until one literal pattern disappears; False on timeout."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if pattern not in self.visible_text():
                return True
            time.sleep(0.4)
        return False

    def wait_for_answer(
        self, snapshot_digest: str, *, stable_seconds: float, timeout_seconds: float
    ) -> bool:
        """Wait for pane change after submission, then stability (hooks-off heuristic).

        ``snapshot_digest`` is the sha256 of the visible pane captured right
        before submitting the prompt; generation must change first, then hold
        still for ``stable_seconds``.
        """

        deadline = time.monotonic() + timeout_seconds
        changed = False
        previous_digest = snapshot_digest
        last_change = time.monotonic()
        while time.monotonic() < deadline:
            now = time.monotonic()
            digest = hashlib.sha256(self.visible_text().encode("utf-8")).hexdigest()
            if digest != snapshot_digest:
                changed = True
            if digest != previous_digest:
                # Pane is still mutating; restart the stability clock.
                last_change = now
                previous_digest = digest
            elif changed and now - last_change >= stable_seconds:
                return True
            time.sleep(1.0)
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

    def event_names(self) -> list[str]:
        """Return the hook_event_name of every recorded event in order."""

        names: list[str] = []
        for row in self.rows():
            provider = row.get("provider_event")
            if isinstance(provider, dict):
                names.append(str(provider.get("hook_event_name") or "unknown"))
            else:
                names.append("unknown")
        return names

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


class RunState:
    """Per-run mutable state shared across scenario step functions."""

    def __init__(
        self,
        *,
        scenario: str,
        run_root: Path,
        workdir: Path,
        collector_store: Path,
        token: str,
        generation: int,
        hooks_enabled: bool,
    ) -> None:
        """Initialize state for one scenario run."""

        self.m_scenario = scenario
        self.m_run_root = run_root
        self.m_workdir = workdir
        self.m_collector_store = collector_store
        self.m_token = token
        self.m_generation = generation
        self.m_hooks_enabled = hooks_enabled
        self.m_input_log = run_root / "driver-input-events.ndjson"
        self.m_events = EventStore(collector_store / "events.ndjson")
        self.m_notes: list[str] = []
        self.m_generations: list[dict[str, Any]] = []
        self.m_drivers: dict[str, PaneDriver] = {}
        self.m_aborted: str | None = None
        self.m_session_end_observed: bool | None = None
        self.m_p23_timings: list[dict[str, Any]] = []
        self.m_s5_post_stop_events: list[str] = []
        self.m_s6_stop_after_escape: bool | None = None

    def note(self, text: str) -> None:
        """Append one run-note line echoed into run-summary.json."""

        self.m_notes.append(text)

    def log(self, action: str, **detail: Any) -> None:
        """Append one timestamped runner-level action to the input-event log."""

        row: dict[str, Any] = {
            "ts_utc": _utc_now_iso(),
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


class LaunchEnv:
    """Current collector generation plus the settings/wrapper derived from it."""

    def __init__(self, *, run_root: Path, collector_store: Path, token: str, scenario: str) -> None:
        """Record paths and the per-run token."""

        self.m_run_root = run_root
        self.m_collector_store = collector_store
        self.m_token = token
        self.m_scenario = scenario
        self.m_collector: CollectorProcess | None = None
        self.m_port: int | None = None
        self.m_generation = 0
        self.m_wrapper: Path | None = None
        self.m_observer: Path | None = None

    def start_generation(self, generation: int) -> int:
        """Start collector generation N and regenerate settings plus wrapper."""

        self.m_generation = generation
        log_path = self.m_collector_store / f"collector-gen{generation}.log"
        self.m_collector = CollectorProcess(
            store=self.m_collector_store,
            token=self.m_token,
            generation=generation,
            log_path=log_path,
        )
        self.m_port = self.m_collector.start()
        hooks_enabled = SCENARIOS[self.m_scenario]["hooks"]
        self.m_observer = None
        claude_home = None
        if hooks_enabled and _INJECT_VIA == "home":
            EMIT_HOOK_SCRIPT.chmod(0o755)
            claude_home = self.m_run_root / "claude-home"
            operator_hook = write_operator_hook_script(run_root=self.m_run_root)
            seed_claude_home(
                home_dir=claude_home,
                settings=build_home_settings(port=self.m_port, operator_hook=operator_hook),
            )
        elif hooks_enabled:
            EMIT_HOOK_SCRIPT.chmod(0o755)
            self.m_observer = self.m_run_root / f"observer-settings-gen{generation}.json"
            generate_observer_settings(
                port=self.m_port, emitter=EMIT_HOOK_SCRIPT, out=self.m_observer
            )
        self.m_wrapper = self.m_run_root / f"launch-wrapper-gen{generation}.sh"
        write_wrapper(
            path=self.m_wrapper,
            token=self.m_token,
            port=self.m_port,
            store=self.m_collector_store,
            generation=generation,
            observer_settings=self.m_observer,
            permissions_lane=bool(SCENARIOS[self.m_scenario].get("permissions_lane")),
            claude_home=claude_home,
        )
        return self.m_port

    def stop_collector(self) -> None:
        """Stop the current collector, if any."""

        if self.m_collector is not None:
            self.m_collector.stop()
            self.m_collector = None


def generate_observer_settings(*, port: int, emitter: Path, out: Path) -> None:
    """Invoke observer_settings.py to write one secret-free settings file."""

    result = subprocess.run(
        [
            sys.executable,
            str(OBSERVER_SETTINGS_SCRIPT),
            "--port",
            str(port),
            "--emitter",
            str(emitter),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"observer_settings.py failed: {result.stderr.strip()}")


_S3_ENV_LANE_LINES = [
    'key_file="$HOME/.local/bin/deepseek-api-key"',
    'deepseek_key="${DEEPSEEK_API_KEY:-}"',
    'if [[ -z "$deepseek_key" && -r "$key_file" ]]; then',
    '  deepseek_key="$(cat -- "$key_file")"',
    "fi",
    'if [[ -z "$deepseek_key" ]]; then',
    '  echo "hookcap: DEEPSEEK_API_KEY unset and key file unreadable" >&2',
    "  exit 2",
    "fi",
    'export ANTHROPIC_AUTH_TOKEN="$deepseek_key"',
    "export ANTHROPIC_BASE_URL='https://api.deepseek.com/anthropic'",
    "unset ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN",
    "export ANTHROPIC_MODEL='deepseek-flash[1m]'",
    'export ANTHROPIC_DEFAULT_MODEL="$ANTHROPIC_MODEL"',
    "export ANTHROPIC_DEFAULT_OPUS_MODEL='deepseek-v4-pro[1m]'",
    "export ANTHROPIC_DEFAULT_OPUS_MODEL_NAME='DeepSeek Pro'",
    "export ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION='DeepSeek V4 Pro with 1M context'",
    'export ANTHROPIC_DEFAULT_SONNET_MODEL="$ANTHROPIC_MODEL"',
    "export ANTHROPIC_DEFAULT_SONNET_MODEL_NAME='DeepSeek Flash'",
    "export ANTHROPIC_DEFAULT_SONNET_MODEL_DESCRIPTION='DeepSeek Flash with 1M context (default)'",
    'export ANTHROPIC_DEFAULT_FABLE_MODEL="$ANTHROPIC_MODEL"',
    "export ANTHROPIC_DEFAULT_HAIKU_MODEL='deepseek-flash'",
    "export CLAUDE_CODE_SUBAGENT_MODEL='deepseek-flash'",
    'export CLAUDE_CODE_EFFORT_LEVEL="${CLAUDE_CODE_EFFORT_LEVEL:-max}"',
    'export CLAUDE_CODE_AUTO_COMPACT_WINDOW="${CLAUDE_CODE_AUTO_COMPACT_WINDOW:-786432}"',
    'export API_TIMEOUT_MS="${API_TIMEOUT_MS:-600000}"',
    'export DISABLE_AUTOUPDATER="${DISABLE_AUTOUPDATER:-1}"',
    'claude_bin="$HOME/.bun/bin/claude"',
    'if [[ ! -x "$claude_bin" ]]; then',
    '  claude_bin="$(command -v claude || true)"',
    "fi",
    'if [[ -z "$claude_bin" ]]; then',
    '  echo "hookcap: claude binary not found" >&2',
    "  exit 127",
    "fi",
]


def _hook_env_lines(token: str, port: int, store: Path, generation: int) -> list[str]:
    """Render the HOUMAO_HOOK_* exports shared by every generated wrapper."""

    return [
        f"export HOUMAO_HOOK_TOKEN={_shell_single_quote(token)}",
        "export HOUMAO_HOOK_COLLECTOR_URL="
        + _shell_single_quote(f"http://127.0.0.1:{port}/v1/hook"),
        f"export HOUMAO_HOOK_STORE={_shell_single_quote(str(store))}",
        f"export HOUMAO_HOOK_GENERATION={_shell_single_quote(str(generation))}",
    ]


OPERATOR_HOOK_SCRIPT = "operator_hook.sh"
OPERATOR_MARKER_FILENAME = "operator-hook-marker.txt"
_HOME_SETTINGS_FILENAME = "settings.json"
_HOME_STATE_FILENAME = ".claude.json"


def write_operator_hook_script(*, run_root: Path) -> Path:
    """Write the dummy operator-authored hook script for the home-injection arm.

    It discards stdin, appends one line to the run-root operator marker file,
    writes nothing to stdout, and exits 0. It stands in for operator entries
    that a settings merge must preserve.
    """

    path = run_root / OPERATOR_HOOK_SCRIPT
    marker = run_root / OPERATOR_MARKER_FILENAME
    path.write_text(
        "#!/usr/bin/env bash\n"
        "# Dummy operator-authored hook for the home-injection coexistence arm.\n"
        "cat > /dev/null\n"
        f"printf 'operator-hook fired\\n' >> {_shell_single_quote(str(marker))}\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def build_home_settings(*, port: int, operator_hook: Path) -> dict[str, Any]:
    """Build the scratch managed home's settings.json for the home arm.

    Mirrors the managed-home bootstrap (`skipDangerousModePermissionPrompt`)
    and merges the observer hook block (same 9-event shape as the --settings
    arm) with the dummy operator hook, operator entries first.
    """

    import importlib.util

    spec = importlib.util.spec_from_file_location("observer_settings", OBSERVER_SETTINGS_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    observer_hooks = module.build_observer_settings(port=port, emitter=EMIT_HOOK_SCRIPT)["hooks"]
    operator_command = f"bash {_shell_single_quote(str(operator_hook))}"
    merged: dict[str, Any] = {"skipDangerousModePermissionPrompt": True, "hooks": {}}
    for event, groups in observer_hooks.items():
        merged["hooks"][event] = list(groups)
    merged["hooks"]["UserPromptSubmit"] = [
        {
            "hooks": [
                {"type": "command", "command": operator_command, "timeout": 2},
            ]
        }
    ] + merged["hooks"]["UserPromptSubmit"]
    return merged


def seed_claude_home(*, home_dir: Path, settings: dict[str, Any]) -> None:
    """Seed a scratch Claude home: merged settings.json plus minimal state."""

    home_dir.mkdir(parents=True, exist_ok=True)
    (home_dir / _HOME_SETTINGS_FILENAME).write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )
    (home_dir / _HOME_STATE_FILENAME).write_text(
        json.dumps({"hasCompletedOnboarding": True, "numStartups": 1}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_wrapper(
    *,
    path: Path,
    token: str,
    port: int,
    store: Path,
    generation: int,
    observer_settings: Path | None,
    permissions_lane: bool,
    claude_home: Path | None = None,
) -> Path:
    """Generate the mode-0600 launch wrapper for one collector generation.

    The normal lane execs ``claude-deepseek --settings <observer.json>``; the
    s3 permissions lane replicates the launcher environment inline (runtime
    key read, same model pins, no ``--dangerously-skip-permissions``), pins
    ``--permission-mode manual`` (without it 2.1.303 boots this lane into
    ``auto`` mode, which auto-allows tool calls with no modal and no
    ``PermissionRequest`` — observed 2026-10-19), and execs the resolved
    claude binary directly. When ``_CLAUDE_BIN_OVERRIDE`` is set (floor
    check), the normal lane instead replicates the launcher environment
    inline and execs the scratch binary with the same pins and the same
    bypass posture. When ``claude_home`` is set (home-injection arm), the
    wrapper exports ``CLAUDE_CONFIG_DIR`` and passes no ``--settings`` at
    all; the observer block lives in the home's settings.json.
    """

    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    lines += _hook_env_lines(token, port, store, generation)
    if claude_home is not None:
        lines.append(f"export CLAUDE_CONFIG_DIR={_shell_single_quote(str(claude_home))}")
    lines.append("")
    if permissions_lane:
        lines += _S3_ENV_LANE_LINES
        lines.append("")
        exec_line = 'exec "$claude_bin" --permission-mode manual '
        if observer_settings is not None:
            exec_line += f"--settings {_shell_single_quote(str(observer_settings))} "
        exec_line += '"$@"'
        lines.append(exec_line)
    elif _CLAUDE_BIN_OVERRIDE is not None:
        lines += _S3_ENV_LANE_LINES
        lines.append("")
        exec_line = (
            f"exec {_shell_single_quote(str(_CLAUDE_BIN_OVERRIDE))} --dangerously-skip-permissions "
        )
        if observer_settings is not None:
            exec_line += f"--settings {_shell_single_quote(str(observer_settings))} "
        exec_line += '"$@"'
        lines.append(exec_line)
    else:
        exec_line = f"exec {_shell_single_quote(str(LAUNCHER))} "
        if observer_settings is not None:
            exec_line += f"--settings {_shell_single_quote(str(observer_settings))} "
        exec_line += '"$@"'
        lines.append(exec_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
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
            "claude",
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


def bootstrap_session(
    state: RunState,
    *,
    driver: PaneDriver,
    timeout_seconds: float = 150.0,
    check_model: bool = True,
) -> None:
    """Handle the trust dialog, wait for the composer, and enforce the model gate.

    Raises
    ------
    AbortRun
        If the composer never settles or the visible model is not the
        launcher-pinned one. The abort happens before any prompt is sent.

    ``check_model=False`` is for the s7 resume phase: the resumed TUI does not
    re-render the model banner (it scrolls off behind the restored
    transcript), and the relaunch uses the identical wrapper/model pins that
    already passed the gate in generation 1.
    """

    deadline = time.monotonic() + timeout_seconds
    accepted_trust = False
    while time.monotonic() < deadline:
        text = driver.visible_text()
        if TRUST_DIALOG_PATTERN in text:
            state.log("trust-dialog-accept", keys=["Down", "Enter"])
            driver.send_key("Down")
            time.sleep(0.5)
            driver.send_key("Enter")
            accepted_trust = True
            driver.wait_absence(TRUST_DIALOG_PATTERN, timeout_seconds=30.0)
            break
        if any(marker in text for marker in COMPOSER_MARKERS):
            break
        time.sleep(1.0)
    state.note(f"trust dialog accepted: {accepted_trust}")

    composer_deadline = time.monotonic() + 90.0
    while time.monotonic() < composer_deadline:
        text = driver.visible_text()
        if any(marker in text for marker in COMPOSER_MARKERS):
            break
        time.sleep(1.0)
    else:
        raise AbortRun("composer did not become ready within 90s of surface settle")

    if not check_model:
        state.log("model-gate-skipped", reason="resume phase: banner not re-rendered")
        return
    text = driver.visible_text()
    if not any(needle in text for needle in MODEL_GATE_NEEDLES):
        snippet = " | ".join(line for line in text.splitlines() if line.strip())[-400:]
        raise AbortRun(
            "model gate failed: TUI shows none of "
            f"{MODEL_GATE_NEEDLES!r}; visible tail: {snippet!r}"
        )
    matched = next(needle for needle in MODEL_GATE_NEEDLES if needle in text)
    state.log("model-gate-passed", needle=matched)


def exit_claude(state: RunState, *, session_name: str) -> None:
    """Exit claude via /exit, falling back to double Ctrl-C; log the outcome."""

    if not session_alive(session_name):
        state.note(f"tmux session {session_name} already gone before exit step")
        return
    driver = state.m_drivers[session_name]
    state.log("exit-via-slash-exit")
    # Clear any restored/interrupted draft first: after an Esc abort the
    # interrupted prompt sits in the composer, and a bare "/exit" would
    # append to it (observed S6: draft + "/exit" submitted as one prompt).
    driver.send_key("C-u")
    time.sleep(0.3)
    driver.submit_text("/exit")
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        if not session_alive(session_name):
            state.note("claude exited via /exit")
            return
        time.sleep(1.0)
    state.log("exit-via-ctrl-c", keys=["C-c", "C-c"])
    driver.send_key("C-c")
    time.sleep(1.0)
    driver.send_key("C-c")
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if not session_alive(session_name):
            state.note("claude exited via double Ctrl-C")
            return
        time.sleep(1.0)
    state.note(f"WARNING: tmux session {session_name} still alive after exit attempts")


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


def run_s0(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S0 gate arm: single OK prompt; Stop must arrive within 60 s."""

    driver.submit_text(PROMPT_OK)
    wait_for_event(state, "Stop", timeout_seconds=60.0)


def run_s1(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S1 normal arm: two turn cycles then /exit; SessionEnd recorded post-exit."""

    driver.submit_text(PROMPT_OK)
    wait_for_event(state, "Stop", timeout_seconds=120.0)
    driver.submit_text(PROMPT_2PLUS2)
    wait_for_event(state, "Stop", timeout_seconds=120.0, occurrence=2)
    exit_claude(state, session_name=session_name)
    observed = state.m_events.wait_for_count("SessionEnd", 1, timeout_seconds=5.0)
    state.m_session_end_observed = observed
    state.note(
        f"SessionEnd observed after exit: {observed} "
        "(SessionEnd is not in the v1 subscribed event set)"
    )


def run_s1_control(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S1 hooks-off control: identical prompts, pane-settle timing for P2.3."""

    for prompt in (PROMPT_OK, PROMPT_2PLUS2):
        snapshot = hashlib.sha256(driver.visible_text().encode("utf-8")).hexdigest()
        submitted_at_utc = _utc_now_iso()
        submitted_monotonic = time.monotonic()
        driver.submit_text(prompt)
        settled = driver.wait_for_answer(snapshot, stable_seconds=6.0, timeout_seconds=150.0)
        state.m_p23_timings.append(
            {
                "prompt": prompt,
                "submitted_at_utc": submitted_at_utc,
                "submitted_monotonic": round(submitted_monotonic, 6),
                "answer_complete_at_utc": _utc_now_iso(),
                "answer_complete_monotonic": round(time.monotonic(), 6),
                "settle_detected": settled,
                "heuristic": (
                    "hooks-off: pane changed after submission then stayed "
                    "stable for 6s (no Stop event available)"
                ),
            }
        )
        state.note(f"p2.3 control prompt {prompt!r} settle_detected={settled}")
    exit_claude(state, session_name=session_name)


def run_s2(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S2 direct-input arm: raw send-keys prompt proves UserPromptSubmit fires."""

    state.note("s2 input delivered via raw tmux send-keys; no gateway record exists")
    driver.submit_text(PROMPT_OK)
    wait_for_event(state, "Stop", timeout_seconds=60.0)


def _press_permission_key(state: RunState, driver: PaneDriver, key: str) -> None:
    """Press one permission-modal key and follow with Enter if the modal persists."""

    state.log("permission-modal-key", keys=[key])
    driver.send_key(key)
    time.sleep(2.0)
    text = driver.visible_text()
    if any(marker in text for marker in PERMISSION_MODAL_MARKERS):
        state.log("permission-modal-followup", keys=["Enter"])
        driver.send_key("Enter")
        time.sleep(1.0)


def run_s3(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S3 permissions lane: allow then deny at the modal; keys recorded.

    Keys are pressed only after the modal is actually visible; when no modal
    renders (e.g. the session is not in a permission-asking mode) the key is
    NOT pressed, so the composer draft stays uncontaminated.
    """

    driver.submit_text(PROMPT_ALLOW)
    modal_shown = driver.wait_any(PERMISSION_MODAL_MARKERS, timeout_seconds=90.0)
    state.note(f"permission modal visible after allow prompt: {modal_shown}")
    state.save_surface_snapshot("s3-allow-modal.txt", driver.visible_text())
    if modal_shown:
        # Verified 2.1.303 modal: "1. Yes" / "2. Yes + switch modes" / "3. No".
        _press_permission_key(state, driver, "1")
    else:
        state.note("DEVIATION: no allow-modal visible; key not pressed")
    allow_stop = wait_for_event(state, "Stop", timeout_seconds=150.0)
    state.note(f"Stop after allow: {allow_stop}")

    driver.submit_text(PROMPT_DENY)
    modal_shown = driver.wait_any(PERMISSION_MODAL_MARKERS, timeout_seconds=90.0)
    state.note(f"permission modal visible after deny prompt: {modal_shown}")
    state.save_surface_snapshot("s3-deny-modal.txt", driver.visible_text())
    if modal_shown:
        # Option 3 is "No" on the 2.1.303 modal; option 2 is a broad allow.
        _press_permission_key(state, driver, "3")
    else:
        state.note("DEVIATION: no deny-modal visible; key not pressed")
    deny_stop = wait_for_event(state, "Stop", timeout_seconds=90.0, occurrence=2)
    state.note(f"Stop after deny: {deny_stop}")


def run_s4(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S4 compaction arm: README turn, /compact, then a post-compact turn."""

    driver.submit_text(PROMPT_README)
    wait_for_event(state, "Stop", timeout_seconds=150.0)
    state.log("send-slash-compact", text="/compact")
    driver.send_text("/compact")
    time.sleep(0.3)
    driver.send_key("Enter")
    pre_compact = wait_for_event(state, "PreCompact", timeout_seconds=60.0)
    post_compact = wait_for_event(state, "PostCompact", timeout_seconds=120.0)
    state.note(f"PreCompact observed: {pre_compact}; PostCompact observed: {post_compact}")
    driver.submit_text(PROMPT_OK)
    # Second Stop: the README turn already produced the first one.
    post_ok_stop = wait_for_event(state, "Stop", timeout_seconds=90.0, occurrence=2)
    state.note(f"Stop after post-compact OK prompt: {post_ok_stop}")


def run_s5(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S5 background arm: background sleep turn, then a bounded idle event watch."""

    driver.submit_text(PROMPT_BG)
    stop = wait_for_event(state, "Stop", timeout_seconds=300.0)
    state.note(f"Stop after background prompt: {stop}")
    if not stop:
        return
    baseline = len(state.m_events.rows())
    deadline = time.monotonic() + 150.0
    while time.monotonic() < deadline:
        rows = state.m_events.rows()
        if len(rows) > baseline:
            for row in rows[baseline:]:
                provider = row.get("provider_event")
                name = "unknown"
                if isinstance(provider, dict):
                    name = str(provider.get("hook_event_name") or "unknown")
                state.m_s5_post_stop_events.append(name)
                state.log("s5-idle-event", event=name)
            baseline = len(rows)
        time.sleep(2.0)
    state.note(f"events during 150s idle wait: {state.m_s5_post_stop_events or 'none'}")


def run_s6(state: RunState, driver: PaneDriver, session_name: str) -> None:
    """S6 interrupt arm: Esc mid-generation; record whether Stop fires."""

    driver.submit_text(PROMPT_RECURSION)
    time.sleep(8.0)
    state.log("interrupt-escape", keys=["Escape"])
    driver.send_key("Escape")
    stop = wait_for_event(state, "Stop", timeout_seconds=90.0)
    state.m_s6_stop_after_escape = stop
    state.note(f"Stop fired after Escape: {stop}")
    driver.wait_absence("esc to interrupt", timeout_seconds=30.0)


def run_s7(
    state: RunState,
    driver: PaneDriver,
    session_name: str,
    env: LaunchEnv,
    register_session: Callable[[str, PaneDriver], None],
    recorder_roots: list[Path],
) -> None:
    """S7 queue+resume arm: queued input, exit, relaunch with --resume."""

    driver.submit_text(PROMPT_QUEUES)
    busy = driver.wait_any(BUSY_MARKERS, timeout_seconds=90.0)
    state.note(f"busy marker visible before queued input: {busy}")
    time.sleep(5.0)
    driver.submit_text(PROMPT_OK)
    first_stop = wait_for_event(state, "Stop", timeout_seconds=240.0)
    second_stop = wait_for_event(state, "Stop", timeout_seconds=240.0, occurrence=2)
    state.note(f"first Stop: {first_stop}; second Stop after queued input: {second_stop}")
    state.log("s7-event-order-snapshot", sequence=state.m_events.event_names())
    exit_claude(state, session_name=session_name)

    state.note("relaunching with --resume (collector generation bump)")
    # Resume by explicit session id (captured from the gen-1 SessionStart
    # payload) so the cross-project picker is skipped deterministically; the
    # picker path below remains as fallback. The 2.1.303 picker shows
    # auto-titled entries across projects and its rows match the bare "❯"
    # composer marker, which aborts the model gate (observed run-135152Z).
    resume_session_id = None
    for row in state.m_events.rows():
        provider = row.get("provider_event")
        if (
            isinstance(provider, dict)
            and provider.get("hook_event_name") == "SessionStart"
            and row.get("channel_generation") == 1
            and provider.get("session_id")
        ):
            resume_session_id = str(provider["session_id"])
    env.stop_collector()
    env.start_generation(env.m_generation + 1)
    state.m_generations.append(
        {
            "generation": env.m_generation,
            "port": env.m_port,
            "started_at_utc": _utc_now_iso(),
            "started_monotonic": round(time.monotonic(), 6),
            "reason": "s7 resume relaunch",
        }
    )
    resume_session = f"hookcap-s7-resume-{os.getpid()}"
    assert env.m_wrapper is not None
    extra_args = ("--resume", resume_session_id) if resume_session_id else ("--resume",)
    resume_pane = launch_tmux_session(
        session_name=resume_session,
        workdir=state.m_workdir,
        wrapper=env.m_wrapper,
        extra_args=extra_args,
    )
    resume_driver = PaneDriver(
        session_name=resume_session, pane_id=resume_pane, log_path=state.m_input_log
    )
    register_session(resume_session, resume_driver)
    resume_recording_root = state.m_run_root / "pane-recording-resume"
    start_recorder(session_name=resume_session, run_root=resume_recording_root)
    recorder_roots.append(resume_recording_root)

    time.sleep(6.0)
    picker_text = resume_driver.visible_text()
    picker_snapshot = state.save_surface_snapshot("s7-resume-launch-surface.txt", picker_text)
    picker_visible = RESUME_PICKER_NEEDLE in picker_text.lower() and "❯" in picker_text
    state.note(f"resume picker visible: {picker_visible} (surface saved to {picker_snapshot})")
    if picker_visible:
        state.log("resume-picker-select", keys=["Enter"], assumption="most recent entry")
        resume_driver.send_key("Enter")
        # The picker's "❯" rows match the bare-composer marker; wait for the
        # picker to actually dismiss before running the model gate.
        resume_driver.wait_absence("Type to search", timeout_seconds=30.0)
    bootstrap_session(state, driver=resume_driver, check_model=False)
    resumed = wait_for_event(state, "SessionStart", timeout_seconds=90.0, occurrence=2)
    state.note(f"SessionStart after --resume relaunch: {resumed}")
    exit_claude(state, session_name=resume_session)


STEPS: dict[str, Callable[..., None]] = {
    "s0": run_s0,
    "s1": run_s1,
    "s1-control": run_s1_control,
    "s2": run_s2,
    "s3": run_s3,
    "s4": run_s4,
    "s5": run_s5,
    "s6": run_s6,
    "s7": run_s7,
}


def _default_run_root(scenario: str) -> Path:
    """Return the default run root for one scenario."""

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return RUN_ROOT_BASE / scenario / f"run-{stamp}"


def write_labels_template(state: RunState, labels_dir: Path) -> None:
    """Write the labels template mirroring the recorder label subset."""

    slots = LABEL_SLOTS[state.m_scenario]
    doc = {
        "schema_version": 1,
        "scenario": state.m_scenario,
        "predeclared_expectation": SCENARIOS[state.m_scenario]["expectation"],
        "hooks_enabled": state.m_hooks_enabled,
        "time_base": {
            "run_launched_monotonic": state.m_generations[0]["started_monotonic"]
            if state.m_generations
            else None,
            "collector_generations": state.m_generations,
            "note": (
                "collector started_monotonic shares this runner's monotonic clock; "
                "align pane frames via the recorder run metadata and these UTC pairs"
            ),
        },
        "labels": [
            {
                "label_id": slot["label_id"],
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
                "note": slot["note"],
                "evidence": {},
            }
            for slot in slots
        ],
    }
    labels_dir.mkdir(parents=True, exist_ok=True)
    (labels_dir / "labels-template.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )


def write_run_summary(state: RunState, run_root: Path, collector_store: Path) -> None:
    """Write run-summary.json with counts, ordering, and collected notes."""

    names = state.m_events.event_names()
    channel_path = collector_store / "channel.json"
    final_status: dict[str, Any] | None = None
    if channel_path.is_file():
        try:
            final_status = json.loads(channel_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            final_status = None
    summary: dict[str, Any] = {
        "schema_version": 1,
        "scenario": state.m_scenario,
        "run_root": str(run_root),
        "workdir": str(state.m_workdir),
        "hooks_enabled": state.m_hooks_enabled,
        "aborted": state.m_aborted is not None,
        "abort_reason": state.m_aborted,
        "collector_generations": state.m_generations,
        "collector_final_status": final_status,
        "event_counts": dict(sorted(__import__("collections").Counter(names).items())),
        "event_sequence": names,
        "session_end_observed": state.m_session_end_observed,
        "s6_stop_after_escape": state.m_s6_stop_after_escape,
        "s5_post_stop_events": state.m_s5_post_stop_events,
        "p23_timings": state.m_p23_timings,
        "notes": state.m_notes,
        "finished_at_utc": _utc_now_iso(),
    }
    (run_root / "run-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_scenario(scenario: str, run_root: Path | None) -> int:
    """Run one scenario end to end with full teardown; return a process exit code."""

    meta = SCENARIOS[scenario]
    run_root = run_root or _default_run_root(scenario)
    run_root.mkdir(parents=True, exist_ok=True)
    workdir = run_root / "workdir"
    workdir.mkdir(exist_ok=True)
    if scenario == "s4":
        (workdir / "README.md").write_text(S4_README_TEXT, encoding="utf-8")
    collector_store = run_root / "collector"
    pane_recording = run_root / "pane-recording"
    labels_dir = run_root / "labels"
    labels_dir.mkdir(exist_ok=True)

    token = secrets.token_hex(16)
    env = LaunchEnv(
        run_root=run_root, collector_store=collector_store, token=token, scenario=scenario
    )
    state = RunState(
        scenario=scenario,
        run_root=run_root,
        workdir=workdir,
        collector_store=collector_store,
        token=token,
        generation=1,
        hooks_enabled=bool(meta["hooks"]),
    )
    sessions: list[str] = []
    recorder_roots: list[Path] = []
    launched_monotonic = time.monotonic()
    if _CLAUDE_BIN_OVERRIDE is not None:
        state.note(
            "FLOOR LANE: execs scratch claude binary "
            f"{_CLAUDE_BIN_OVERRIDE} (host install untouched); env/pins identical "
            "to the launcher lane"
        )

    def register_session(name: str, driver: PaneDriver) -> None:
        """Track one session and its driver for exit and teardown."""

        sessions.append(name)
        state.m_drivers[name] = driver

    try:
        if _INJECT_VIA == "home":
            state.note(
                "HOME INJECTION ARM: observer block marker-merged into scratch managed home "
                f"{run_root / 'claude-home'} (CLAUDE_CONFIG_DIR); no --settings passed"
            )
        port = env.start_generation(1)
        state.m_generations.append(
            {
                "generation": 1,
                "port": port,
                "started_at_utc": _utc_now_iso(),
                "started_monotonic": round(time.monotonic(), 6),
                "reason": "initial launch",
            }
        )
        session_name = f"hookcap-{scenario}-{os.getpid()}"
        assert env.m_wrapper is not None
        pane_id = launch_tmux_session(
            session_name=session_name, workdir=workdir, wrapper=env.m_wrapper
        )
        driver = PaneDriver(session_name=session_name, pane_id=pane_id, log_path=state.m_input_log)
        register_session(session_name, driver)
        launch_metadata = {
            "schema_version": 1,
            "scenario": scenario,
            "hooks_enabled": bool(meta["hooks"]),
            "inject_via": _INJECT_VIA,
            "claude_home": str(run_root / "claude-home") if _INJECT_VIA == "home" else None,
            "tmux_session": session_name,
            "tmux_pane": pane_id,
            "pane_pid": pane_pid(pane_id),
            "runner_pid": os.getpid(),
            "workdir": str(workdir),
            "run_root": str(run_root),
            "launcher": str(LAUNCHER),
            "claude_bin_override": str(_CLAUDE_BIN_OVERRIDE) if _CLAUDE_BIN_OVERRIDE else None,
            "floor_lane": _CLAUDE_BIN_OVERRIDE is not None,
            "permissions_lane": bool(meta.get("permissions_lane")),
            "observer_settings": str(env.m_observer) if env.m_observer else None,
            "wrapper": str(env.m_wrapper),
            "collector_port": port,
            "token_env": "HOUMAO_HOOK_TOKEN",
            "launched_at_utc": _utc_now_iso(),
            "launched_monotonic": round(launched_monotonic, 6),
        }
        (run_root / "launch.json").write_text(
            json.dumps(launch_metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        start_recorder(session_name=session_name, run_root=pane_recording)
        recorder_roots.append(pane_recording)
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
        elif scenario in ("s1", "s1-control"):
            step(state, driver, session_name)
        else:
            step(state, driver, session_name)
            exit_claude(state, session_name=session_name)
        print(f"scenario {scenario} finished; run root: {run_root}")
        return 0
    except AbortRun as exc:
        state.m_aborted = exc.m_reason
        state.log("run-aborted", reason=exc.m_reason)
        print(f"ABORTED ({scenario}): {exc.m_reason}")
        return 0
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
            write_labels_template(state, labels_dir)
        except Exception as exc:  # teardown must not raise
            print(f"warning: labels template write failed: {exc!r}", file=sys.stderr)
        try:
            write_run_summary(state, run_root, collector_store)
        except Exception as exc:  # teardown must not raise
            print(f"warning: run summary write failed: {exc!r}", file=sys.stderr)


def _post_json(url: str, payload: dict[str, Any], token: str) -> tuple[int, str]:
    """POST one JSON payload with a bearer token; return (status, error note)."""

    import urllib.error
    import urllib.request

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, ""
    except urllib.error.HTTPError as exc:
        return exc.code, str(exc)
    except OSError as exc:
        return -1, str(exc)


def _count_event_lines(path: Path) -> int:
    """Count non-empty lines in events.ndjson (0 when absent)."""

    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


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


def self_test() -> int:
    """Run the provider-free G0 harness self-test; non-zero exit on any FAIL."""

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    store = RUN_ROOT_BASE / "self-test" / f"run-{stamp}"
    store.mkdir(parents=True, exist_ok=True)
    events_path = store / "events.ndjson"
    token = secrets.token_hex(16)
    collector = CollectorProcess(
        store=store, token=token, generation=1, log_path=store / "collector.log"
    )
    checks: list[tuple[str, bool, str]] = []
    try:
        port = collector.start()
        url = f"http://127.0.0.1:{port}/v1/hook"
        base_lines = _count_event_lines(events_path)

        status, note = _post_json(url, {"hook_event_name": "SelfTestDirect", "probe": "a"}, token)
        ok = status == 204 and _wait_for_event_name(
            events_path, "SelfTestDirect", timeout_seconds=5.0
        )
        checks.append(("collector-accepts-post", ok, f"status={status} {note}"))

        wrong_status, wrong_note = _post_json(
            url, {"hook_event_name": "SelfTestWrongToken", "probe": "d"}, "wrong-token"
        )
        ok = wrong_status != 204 and _count_event_lines(events_path) == base_lines + 1
        checks.append(("wrong-token-rejected", ok, f"status={wrong_status} {wrong_note}"))

        emit_result = _run_emit_hook(
            {"hook_event_name": "SelfTestEmitter", "probe": "b"},
            url=url,
            token=token,
            store=store,
            generation=1,
        )
        ok = (
            emit_result.returncode == 0
            and emit_result.stdout == ""
            and _wait_for_event_name(events_path, "SelfTestEmitter", timeout_seconds=5.0)
        )
        checks.append(
            (
                "emitter-posts-to-collector",
                ok,
                f"rc={emit_result.returncode} stdout={emit_result.stdout!r}",
            )
        )

        collector.stop()
        fallback_result = _run_emit_hook(
            {"hook_event_name": "SelfTestFallback", "probe": "c"},
            url=url,
            token=token,
            store=store,
            generation=1,
        )
        fallback_ok = False
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
                        fallback_ok = True
        ok = fallback_result.returncode == 0 and fallback_ok
        checks.append(
            (
                "emitter-file-fallback",
                ok,
                f"rc={fallback_result.returncode} fallback_row={fallback_ok}",
            )
        )
    finally:
        collector.stop()

    print(f"SELF-TEST store={store}")
    failed = 0
    for name, ok, note in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name} ({note})")
        if not ok:
            failed += 1
    print(f"SELF-TEST {'PASSED' if failed == 0 else f'{failed} CHECK(S) FAILED'}")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: one scenario or the provider-free self-test."""

    global _CLAUDE_BIN_OVERRIDE, _INJECT_VIA

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIO_NAMES)
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument(
        "--claude-bin",
        type=Path,
        default=None,
        help="scratch claude binary for floor checks (also via HOOKCAP_CLAUDE_BIN); "
        "the wrapper execs this instead of the launcher-resolved host binary",
    )
    parser.add_argument(
        "--inject-via",
        choices=("settings", "home"),
        default="settings",
        help="settings: session-scoped --settings (default); home: marker-merged "
        "observer block in a scratch managed home's settings.json via "
        "CLAUDE_CONFIG_DIR, no --settings flag",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the provider-free G0 harness check and exit",
    )
    args = parser.parse_args(argv)
    bin_flag = args.claude_bin or (
        Path(os.environ["HOOKCAP_CLAUDE_BIN"]) if "HOOKCAP_CLAUDE_BIN" in os.environ else None
    )
    if bin_flag is not None:
        resolved = bin_flag.expanduser().resolve()
        if not resolved.is_file():
            parser.error(f"--claude-bin does not resolve to a file: {resolved}")
        _CLAUDE_BIN_OVERRIDE = resolved
    _INJECT_VIA = args.inject_via
    if args.self_test:
        return self_test()
    if not args.scenario:
        parser.error("--scenario is required unless --self-test is given")
    return run_scenario(args.scenario, args.run_root)


if __name__ == "__main__":
    raise SystemExit(main())
