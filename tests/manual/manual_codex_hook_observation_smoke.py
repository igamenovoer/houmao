"""Manual live qualification for Codex hook observation through the managed path.

This script drives real Codex TUI sessions in tmux through the realm-controller
compatibility CLI (``start-session``, ``send-keys``, ``attach-gateway``,
``gateway-status``, ``stop-session``) with the Codex hook observation channel
opted in (``HOUMAO_HOOK_OBSERVATION_CODEX=1``). It covers the OpenSpec
``add-codex-hook-observation`` live smoke scenarios:

- multi-turn success with hook-settled turns;
- approval-modal allow (blocked -> active -> success);
- approval-modal deny (blocked -> interrupted);
- Escape interrupt mid-turn (hook-derived interrupted);
- manual compaction followed by a post-compact turn in a new epoch;
- provider ``kill -9`` mid-turn (presence lost, truthful unknown, terminal gap).

Every scenario uses an isolated scratch ``CODEX_HOME`` under
``tmp/codex-hook-smoke/`` and the ``codex-openlux-auto`` credential lane. The
lane API key and authorization header are extracted from the operator launcher
inside the generated wrapper at process time; this script never prints or logs
them, and teardown removes Codex's ``shell_snapshots/`` and any stray
``auth.json`` from the scratch home because Codex snapshots its environment
there. Each checkpoint writes the raw gateway status, tracked TUI state,
channel status, and event summary under the run directory.

Usage::

    pixi run python tests/manual/manual_codex_hook_observation_smoke.py \
        --scenario multi-turn
    pixi run python tests/manual/manual_codex_hook_observation_smoke.py --scenario all
    pixi run python tests/manual/manual_codex_hook_observation_smoke.py \
        --scenario floor --codex-bin tmp/codex-floor/node_modules/.bin/codex

The script is not part of CI. It spends real provider credit per turn.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_DEF_DIR = REPO_ROOT / "tests" / "fixtures" / "plain-agent-def"
DEFAULT_RUN_ROOT = REPO_ROOT / "tmp" / "codex-hook-smoke"
DEFAULT_LAUNCHER = Path.home() / ".local" / "bin" / "codex-openlux-auto"
ROLE_NAME = "gpu-kernel-coder"
PROFILE_NAME = "openlux-auto"
PROFILE_FILENAME = f"{PROFILE_NAME}.config.toml"

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

PROMPT_OK = "Reply with exactly: OK"
PROMPT_DONE = "Reply with exactly: DONE"
PROMPT_ALLOW = "Create a file named /tmp/houmao-smoke-allow.txt containing hello"
PROMPT_DENY = "Create a file named /tmp/houmao-smoke-deny.txt containing hello"
PROMPT_ESSAY = "Write a long essay about faults."
PROMPT_README = "Read README.md and summarize in one sentence."

S4_README_TEXT = """# Smoke README

This file exists so the compaction scenario has a small, deterministic
document to summarize before the manual ``/compact`` command.
"""

TERMINAL_GAP_COUNTER = "terminal_gaps"
HOOK_CHANNEL_PROVIDER = "codex"


@dataclass(frozen=True)
class Scenario:
    """One qualification scenario and the lane flags it requires."""

    name: str
    lane: str
    kind: str


SCENARIOS: dict[str, Scenario] = {
    "multi-turn": Scenario(name="multi-turn", lane="bypass", kind="multi_turn"),
    "permission-allow": Scenario(
        name="permission-allow", lane="permission", kind="permission_allow"
    ),
    "permission-deny": Scenario(name="permission-deny", lane="permission", kind="permission_deny"),
    "esc-interrupt": Scenario(name="esc-interrupt", lane="bypass", kind="esc_interrupt"),
    "compaction": Scenario(name="compaction", lane="bypass", kind="compaction"),
    "kill-gap": Scenario(name="kill-gap", lane="bypass", kind="kill_gap"),
    "floor": Scenario(name="floor", lane="bypass", kind="multi_turn"),
}

ALL_ORDER = (
    "multi-turn",
    "permission-allow",
    "permission-deny",
    "esc-interrupt",
    "compaction",
    "kill-gap",
)


class ScenarioFailure(RuntimeError):
    """Raised when a scenario cannot meet its predeclared expectation."""


@dataclass
class RunContext:
    """Paths and process coordinates for one scenario run."""

    scenario: Scenario
    run_dir: Path
    workdir: Path
    codex_home: Path
    wrapper: Path
    manifest: Path
    env_file: Path
    agent_name: str
    launcher: Path
    codex_bin: Path
    env: dict[str, str]

    @property
    def evidence_dir(self) -> Path:
        """Return the evidence directory for this run."""

        return self.run_dir / "evidence"

    @property
    def session_manifest(self) -> Path:
        """Return the session manifest path recorded by ``start-session``."""

        return self.run_dir / "session-manifest.txt"


@dataclass
class SessionState:
    """Live session coordinates recorded from the managed CLI payloads."""

    manifest_path: Path
    session_root: Path
    tmux_session_name: str
    gateway_host: str
    gateway_port: int
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    evidence_files: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _utc_stamp() -> str:
    """Return a filename-safe UTC timestamp."""

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _utc_now() -> str:
    """Return the current UTC time in ISO-8601 form."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_json(path: Path, payload: Any) -> None:
    """Write one JSON artifact with a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    """Read one JSON artifact, returning ``None`` when it is missing."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _controller_command(*args: str) -> list[str]:
    """Return one realm-controller compatibility CLI command."""

    return ["pixi", "run", "python", "-m", "houmao.agents.realm_controller", *args]


def _cli(
    *args: str,
    env: dict[str, str] | None = None,
    timeout: float = 180.0,
) -> subprocess.CompletedProcess[str]:
    """Run one managed CLI command from the repository root."""

    return subprocess.run(
        _controller_command(*args),
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _cli_json(
    *args: str,
    env: dict[str, str] | None = None,
    timeout: float = 180.0,
) -> dict[str, Any]:
    """Run one managed CLI command and parse its JSON payload."""

    process = _cli(*args, env=env, timeout=timeout)
    if process.returncode != 0:
        raise ScenarioFailure(
            f"command failed ({process.returncode}): {' '.join(args)}\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise ScenarioFailure(
            f"command did not emit JSON: {' '.join(args)}\nstdout:\n{process.stdout}"
        ) from exc
    if not isinstance(payload, dict):
        raise ScenarioFailure(f"command emitted a non-object payload: {' '.join(args)}")
    return payload


def _tmux(*args: str) -> subprocess.CompletedProcess[str]:
    """Run one tmux command without a shell."""

    return subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _session_root(manifest_path: Path) -> Path:
    """Return the runtime session root that owns the manifest."""

    return manifest_path.resolve().parent


def _codex_channel_dir(session_root: Path) -> Path:
    """Return the Codex hook artifact directory for one session."""

    return session_root / "hook-observation" / "codex"


def _channel_status(session_root: Path) -> dict[str, Any] | None:
    """Read the secret-free channel status document."""

    payload = _read_json(_codex_channel_dir(session_root) / "channel.json")
    return payload if isinstance(payload, dict) else None


def _event_rows(session_root: Path) -> list[dict[str, Any]]:
    """Return parsed event store rows, skipping malformed lines."""

    path = _codex_channel_dir(session_root) / "events.ndjson"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows


def _event_summary(session_root: Path) -> list[dict[str, Any]]:
    """Return the name/turn/session fields of every provider event."""

    summary: list[dict[str, Any]] = []
    for row in _event_rows(session_root):
        provider = row.get("provider_event")
        if not isinstance(provider, dict):
            continue
        summary.append(
            {
                "hook_event_name": provider.get("hook_event_name"),
                "turn_id": provider.get("turn_id"),
                "session_id": provider.get("session_id"),
                "tool_use_id": provider.get("tool_use_id"),
                "tool_name": provider.get("tool_name"),
            }
        )
    return summary


def _event_count(session_root: Path, name: str) -> int:
    """Count provider events with one name."""

    return sum(1 for item in _event_summary(session_root) if item["hook_event_name"] == name)


def _turn_ids(session_root: Path, name: str) -> list[str]:
    """Return the ordered turn ids of one event family."""

    return [
        str(item["turn_id"])
        for item in _event_summary(session_root)
        if item["hook_event_name"] == name and item["turn_id"]
    ]


def _wait_for(
    predicate: Callable[[], Any],
    *,
    timeout_seconds: float,
    poll_seconds: float = 0.5,
    description: str,
) -> Any:
    """Poll ``predicate`` until it returns a truthy value or the timeout elapses."""

    deadline = time.monotonic() + timeout_seconds
    last: Any = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(poll_seconds)
    raise ScenarioFailure(f"timed out after {timeout_seconds:.0f}s waiting for {description}")


def _tracked_state(host: str, port: int, *, timeout: float = 10.0) -> dict[str, Any]:
    """Fetch the live tracked TUI state from the attached gateway."""

    url = f"http://{host}:{port}/v1/control/tui/state"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ScenarioFailure(f"tracked state unavailable at {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ScenarioFailure(f"tracked state payload is not an object: {url}")
    return payload


def _channel_entry(tracked: dict[str, Any]) -> dict[str, Any] | None:
    """Return the hook observation channel entry from tracked state."""

    channels = tracked.get("observation_channels")
    if not isinstance(channels, list):
        return None
    for channel in channels:
        if isinstance(channel, dict) and channel.get("provider") == HOOK_CHANNEL_PROVIDER:
            return channel
    return None


def _tracked_facts(tracked: dict[str, Any]) -> dict[str, Any]:
    """Return the tracked-state fields the qualification cares about."""

    diagnostics = tracked.get("diagnostics") if isinstance(tracked, dict) else None
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    channel = _channel_entry(tracked)
    return {
        "turn_phase": (tracked.get("turn") or {}).get("phase"),
        "last_turn_result": (tracked.get("last_turn") or {}).get("result"),
        "last_turn_source": (tracked.get("last_turn") or {}).get("source"),
        "work": tracked.get("work"),
        "settled": tracked.get("settled"),
        "hook_channel_state": diagnostics.get("hook_channel_state"),
        "hook_counters": diagnostics.get("hook_counters"),
        "hook_conflict_reasons": diagnostics.get("hook_conflict_reasons"),
        "channel_state": (channel or {}).get("state"),
        "channel_generation": (channel or {}).get("generation"),
        "channel_last_event_name": (channel or {}).get("last_event_name"),
        "channel_counters": (channel or {}).get("counters"),
        "surface": tracked.get("surface"),
        "parsed_accepted": (tracked.get("parsed_surface") or {}).get("accepted_input"),
    }


def _gateway_status(ctx: RunContext, session: SessionState) -> dict[str, Any]:
    """Run the managed ``gateway-status`` command and return the payload."""

    return _cli_json(
        "gateway-status",
        "--agent-def-dir",
        str(AGENT_DEF_DIR),
        "--agent-identity",
        str(session.manifest_path),
        env=ctx.env,
        timeout=120.0,
    )


def _pane_list(tmux_session: str) -> list[dict[str, str]]:
    """Return pane id/pid/command rows for one tmux session."""

    result = _tmux(
        "list-panes",
        "-t",
        tmux_session,
        "-F",
        "#{pane_id}\t#{pane_pid}\t#{pane_current_command}",
    )
    if result.returncode != 0:
        return []
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        rows.append({"pane_id": parts[0], "pid": parts[1], "command": parts[2]})
    return rows


def _capture_pane(tmux_session: str) -> str:
    """Capture the visible agent pane text, preferring a Codex-running pane."""

    panes = _pane_list(tmux_session)
    candidate = next(
        (pane for pane in panes if "codex" in pane["command"].lower()),
        panes[0] if panes else None,
    )
    if candidate is None:
        return ""
    result = _tmux("capture-pane", "-p", "-t", candidate["pane_id"])
    return result.stdout if result.returncode == 0 else ""


def _secret_values(launcher: Path) -> tuple[str, ...]:
    """Extract lane secret values from the launcher without emitting them.

    The values stay in this process's memory and are used only to scan public
    artifacts for accidental leakage.
    """

    try:
        text = launcher.read_text(encoding="utf-8")
    except OSError:
        return ()
    values: list[str] = []
    pattern = re.compile(r"^export OPENLUX_(?:API_KEY|AUTHORIZATION)=(.+)$", re.MULTILINE)
    for match in pattern.finditer(text):
        raw = match.group(1).strip()
        if raw.startswith(("'", '"')) and raw[-1:] == raw[:1]:
            raw = raw[1:-1]
        if raw:
            values.append(raw)
    return tuple(values)


def _secret_free_check(
    *,
    ctx: RunContext,
    session: SessionState,
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    """Scan public artifacts for lane secrets and other credential markers."""

    files = [path for path in session.evidence_files if path.is_file()]
    files.extend(
        [
            _codex_channel_dir(session.session_root) / "channel.json",
            ctx.run_dir / "start.json",
            ctx.run_dir / "manifest-preview.json",
        ]
    )
    hit_files: list[str] = []
    markers = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        found = False
        for value in secrets:
            if value and value in text:
                found = True
        for marker in ("OPENLUX_API_KEY=", "OPENLUX_AUTHORIZATION=", "Bearer "):
            if marker in text:
                found = True
                markers += 1
        if found:
            hit_files.append(str(path.relative_to(ctx.run_dir)))
    channel = _read_json(_codex_channel_dir(session.session_root) / "channel.json")
    token_keys = 0
    if isinstance(channel, dict):
        token_keys = sum(1 for key in channel if "token" in str(key).lower())
    return {
        "checked_files": len(files),
        "secret_hits": len(hit_files),
        "hit_files": sorted(set(hit_files)),
        "marker_occurrences": markers,
        "channel_token_keys": token_keys,
        "pass": not hit_files and token_keys == 0,
    }


def _record_checkpoint(
    ctx: RunContext,
    session: SessionState,
    label: str,
    *,
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    """Capture gateway status, tracked state, and channel status for one label."""

    evidence = ctx.evidence_dir
    gateway = _gateway_status(ctx, session)
    _write_json(evidence / f"gateway-status-{label}.json", gateway)
    session.evidence_files.append(evidence / f"gateway-status-{label}.json")

    tracked = _tracked_state(session.gateway_host, session.gateway_port)
    _write_json(evidence / f"tracked-state-{label}.json", tracked)
    session.evidence_files.append(evidence / f"tracked-state-{label}.json")

    channel = _channel_status(session.session_root)
    if channel is not None:
        _write_json(evidence / f"channel-{label}.json", channel)
        session.evidence_files.append(evidence / f"channel-{label}.json")

    summary = _event_summary(session.session_root)
    _write_json(evidence / f"events-summary-{label}.json", summary)
    session.evidence_files.append(evidence / f"events-summary-{label}.json")

    pane = _capture_pane(session.tmux_session_name)
    if pane:
        (evidence / f"pane-{label}.txt").write_text(pane, encoding="utf-8")
        session.evidence_files.append(evidence / f"pane-{label}.txt")

    secret_check = _secret_free_check(ctx=ctx, session=session, secrets=secrets)
    facts = _tracked_facts(tracked)
    record = {
        "label": label,
        "observed_at_utc": _utc_now(),
        "tracked": facts,
        "channel_state": (channel or {}).get("channel_state"),
        "channel_status": (channel or {}).get("status"),
        "gateway_health": gateway.get("gateway_health"),
        "gateway_request_admission": gateway.get("request_admission"),
        "gateway_observation_channels": gateway.get("observation_channels"),
        "secret_free": secret_check,
    }
    session.checkpoints.append(record)
    return record


def _wait_tracked(
    session: SessionState,
    *,
    predicate: Callable[[dict[str, Any]], bool],
    timeout_seconds: float,
    description: str,
) -> dict[str, Any]:
    """Poll live tracked state until ``predicate`` accepts it."""

    def attempt() -> dict[str, Any] | None:
        tracked = _tracked_state(session.gateway_host, session.gateway_port)
        return tracked if predicate(tracked) else None

    return _wait_for(
        attempt,
        timeout_seconds=timeout_seconds,
        poll_seconds=0.5,
        description=description,
    )


def _submit_text(ctx: RunContext, session: SessionState, text: str) -> None:
    """Type one literal prompt and press Enter through ``send-keys``."""

    typed = _cli(
        "send-keys",
        "--agent-def-dir",
        str(AGENT_DEF_DIR),
        "--agent-identity",
        str(session.manifest_path),
        "--sequence",
        text,
        "--escape-special-keys",
        env=ctx.env,
        timeout=60.0,
    )
    if typed.returncode != 0:
        raise ScenarioFailure(f"send-keys literal failed: {typed.stderr.strip()}")
    time.sleep(0.2)
    entered = _cli(
        "send-keys",
        "--agent-def-dir",
        str(AGENT_DEF_DIR),
        "--agent-identity",
        str(session.manifest_path),
        "--sequence",
        "<[Enter]>",
        env=ctx.env,
        timeout=60.0,
    )
    if entered.returncode != 0:
        raise ScenarioFailure(f"send-keys Enter failed: {entered.stderr.strip()}")


def _send_key(ctx: RunContext, session: SessionState, key: str) -> None:
    """Send one named tmux key through ``send-keys``."""

    result = _cli(
        "send-keys",
        "--agent-def-dir",
        str(AGENT_DEF_DIR),
        "--agent-identity",
        str(session.manifest_path),
        "--sequence",
        f"<[{key}]>",
        env=ctx.env,
        timeout=60.0,
    )
    if result.returncode != 0:
        raise ScenarioFailure(
            f"send-keys {key} failed: {result.stderr.strip()} {result.stdout.strip()}"
        )


def _send_literal(ctx: RunContext, session: SessionState, text: str) -> None:
    """Send literal text without pressing Enter through ``send-keys``."""

    result = _cli(
        "send-keys",
        "--agent-def-dir",
        str(AGENT_DEF_DIR),
        "--agent-identity",
        str(session.manifest_path),
        "--sequence",
        text,
        "--escape-special-keys",
        env=ctx.env,
        timeout=60.0,
    )
    if result.returncode != 0:
        raise ScenarioFailure(
            f"send-keys literal {text!r} failed: {result.stderr.strip()} {result.stdout.strip()}"
        )


def _prepare_run(
    *,
    scenario: Scenario,
    run_root: Path,
    launcher: Path,
    codex_bin: Path,
    stamp: str,
) -> RunContext:
    """Create the scratch home, wrapper, env file, and brain manifest."""

    run_dir = run_root / f"{scenario.name}-{stamp}"
    workdir = run_dir / "workdir"
    codex_home = run_dir / "codex-home"
    evidence = run_dir / "evidence"
    for path in (workdir, codex_home, evidence):
        path.mkdir(parents=True, exist_ok=True)
    (workdir / "README.md").write_text(S4_README_TEXT, encoding="utf-8")
    (codex_home / PROFILE_FILENAME).write_text(OPENLUX_PROFILE_CONTENT, encoding="utf-8")

    if scenario.lane == "permission":
        lane_lines = [
            f"exec {shlex.quote(str(codex_bin))} --profile {PROFILE_NAME} \\",
            "  -c 'approval_policy=\"on-request\"' \\",
            "  -c 'sandbox_mode=\"read-only\"' \\",
            '  "$@"',
        ]
    else:
        lane_lines = [
            f"exec {shlex.quote(str(codex_bin))} --profile {PROFILE_NAME} \\",
            "  --dangerously-bypass-approvals-and-sandbox \\",
            '  "$@"',
        ]
    wrapper = run_dir / "launch-wrapper.sh"
    wrapper.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f'launcher="${{HOUMAO_SMOKE_LAUNCHER:-{launcher}}}"',
                'eval "$(grep -E \'^export OPENLUX_(API_KEY|AUTHORIZATION)=\' "$launcher")"',
                *lane_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    wrapper.chmod(0o700)

    env_file = run_dir / "vars.env"
    env_file.write_text("HOUMAO_SMOKE_LANE=openlux-auto\n", encoding="utf-8")
    manifest = run_dir / "brain.yaml"
    manifest.write_text(
        "\n".join(
            [
                "schema_version: 3",
                "inputs:",
                "  tool: codex",
                "  skills: []",
                "  setup: default",
                "  auth: default",
                "  adapter_path: /tmp/codex-smoke-adapter.yaml",
                "  preset_path: null",
                "runtime:",
                f"  runtime_root: {run_dir}",
                f"  home_id: codex-hook-smoke-{scenario.name}",
                f"  home_path: {codex_home}",
                f"  launch_helper: {wrapper}",
                f"  launch_executable: {wrapper}",
                "  launch_home_selector:",
                "    env_var: CODEX_HOME",
                f"    value: {codex_home}",
                "  launch_contract:",
                "    adapter_defaults:",
                "      args: []",
                "      tool_params: {}",
                "    requested_overrides:",
                "      preset: null",
                "      direct: null",
                "    tool_metadata:",
                "      tool_params: {}",
                "    construction_provenance:",
                "      adapter_path: /tmp/codex-smoke-adapter.yaml",
                "      preset_path: null",
                "      preset_overrides_present: false",
                "      direct_overrides_present: false",
                "credentials:",
                f"  auth_path: {run_dir / 'auth'}",
                "  projected_files: []",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - HOUMAO_SMOKE_LANE",
                "launch_policy:",
                "  operator_prompt_mode: as_is",
                "",
            ]
        ),
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["HOUMAO_HOOK_OBSERVATION_CODEX"] = "1"
    env["HOUMAO_GLOBAL_REGISTRY_DIR"] = str(run_dir / "registry")
    env["HOUMAO_SMOKE_LAUNCHER"] = str(launcher)

    agent_name = f"codex-hook-{scenario.name.replace('_', '-')}-{os.getpid()}"
    return RunContext(
        scenario=scenario,
        run_dir=run_dir,
        workdir=workdir,
        codex_home=codex_home,
        wrapper=wrapper,
        manifest=manifest,
        env_file=env_file,
        agent_name=agent_name,
        launcher=launcher,
        codex_bin=codex_bin,
        env=env,
    )


def _start_session(ctx: RunContext) -> SessionState:
    """Start the managed session, attach the gateway, and verify the install."""

    start = _cli_json(
        "start-session",
        "--agent-def-dir",
        str(AGENT_DEF_DIR),
        "--runtime-root",
        str(ctx.run_dir / "runtime"),
        "--brain-manifest",
        str(ctx.manifest),
        "--role",
        ROLE_NAME,
        "--backend",
        "local_interactive",
        "--workdir",
        str(ctx.workdir),
        "--agent-identity",
        ctx.agent_name,
        env=ctx.env,
        timeout=180.0,
    )
    _write_json(ctx.run_dir / "start.json", start)
    manifest_path = Path(str(start["session_manifest"])).resolve()
    ctx.session_manifest.write_text(str(manifest_path) + "\n", encoding="utf-8")
    tmux_session = str(start.get("tmux_session_name") or "")
    if not tmux_session:
        raise ScenarioFailure("start-session did not report a tmux_session_name")

    session_root = _session_root(manifest_path)
    channel = _channel_status(session_root)
    if channel is None:
        raise ScenarioFailure("start-session did not write a Codex channel.json")
    install = channel.get("install") if isinstance(channel.get("install"), dict) else {}
    if install.get("path") != "managed_home":
        raise ScenarioFailure(f"hook observation install path is {install.get('path')!r}")
    hooks_path = ctx.codex_home / "hooks.json"
    config_text = (ctx.codex_home / "config.toml").read_text(encoding="utf-8")
    if not hooks_path.is_file():
        raise ScenarioFailure("managed launch did not install hooks.json")
    if "# >>> houmao hook observation" not in config_text:
        raise ScenarioFailure("managed launch did not merge the pre-trust block")
    if not (ctx.codex_home / PROFILE_FILENAME).is_file():
        raise ScenarioFailure("scratch CODEX_HOME lost the openlux profile")

    attach = _cli_json(
        "attach-gateway",
        "--agent-def-dir",
        str(AGENT_DEF_DIR),
        "--agent-identity",
        str(manifest_path),
        env=ctx.env,
        timeout=120.0,
    )
    _write_json(ctx.run_dir / "attach.json", attach)
    host = str(attach.get("gateway_host") or "")
    port_value = attach.get("gateway_port")
    if attach.get("status") != "ok" or not host or not isinstance(port_value, int):
        raise ScenarioFailure(f"attach-gateway failed: {attach}")
    port = int(port_value)

    session = SessionState(
        manifest_path=manifest_path,
        session_root=session_root,
        tmux_session_name=tmux_session,
        gateway_host=host,
        gateway_port=port,
    )
    _write_json(
        ctx.run_dir / "manifest-preview.json",
        {
            "session_manifest": str(manifest_path),
            "session_root": str(session_root),
            "tmux_session_name": tmux_session,
            "gateway_host": host,
            "gateway_port": port,
            "codex_home": str(ctx.codex_home),
            "wrapper": str(ctx.wrapper),
            "codex_bin": str(ctx.codex_bin),
            "scenario": ctx.scenario.name,
        },
    )
    _wait_for(
        lambda: _tracked_state(host, port),
        timeout_seconds=30.0,
        description="live gateway tracked state",
    )
    return session


def _await_composer(ctx: RunContext, session: SessionState, *, secrets: tuple[str, ...]) -> None:
    """Accept the one-time workspace-trust modal and wait for the composer.

    Managed ``local_interactive`` launches use ``operator_prompt_mode: as_is``,
    so no launch-policy trust preseed exists for the new scratch workdir. Codex
    paints ``Trust this folder?`` before the composer on first use; the operator
    accepts it once. A hooks trust review is never expected and fails the run.
    """

    deadline = time.monotonic() + 150.0
    while time.monotonic() < deadline:
        pane = _capture_pane(session.tmux_session_name)
        if "Trust all and continue" in pane or "Hooks" in pane and "trust" in pane.lower():
            (ctx.evidence_dir / "unexpected-hooks-trust-review.txt").write_text(
                pane, encoding="utf-8"
            )
            raise ScenarioFailure("unexpected hook trust review despite pre-trust block")
        if "Trust this folder?" in pane:
            (ctx.evidence_dir / "workspace-trust-modal.txt").write_text(pane, encoding="utf-8")
            _send_key(ctx, session, "Enter")
            time.sleep(1.0)
            continue
        tracked = _tracked_state(session.gateway_host, session.gateway_port)
        surface = tracked.get("surface") if isinstance(tracked, dict) else None
        pane_composer_ready = (
            "Ask Codex to do anything" in pane and "Trust this folder?" not in pane
        )
        if (
            (surface or {}).get("ready_posture") == "yes"
            or _tracked_facts(tracked)["turn_phase"] == "ready"
            or pane_composer_ready
        ):
            _record_checkpoint(ctx, session, "ready", secrets=secrets)
            return
        time.sleep(1.0)
    (ctx.evidence_dir / "composer-timeout-pane.txt").write_text(
        _capture_pane(session.tmux_session_name), encoding="utf-8"
    )
    raise ScenarioFailure("timed out waiting for the Codex ready composer")


def _await_hook_settlement(
    ctx: RunContext,
    session: SessionState,
    *,
    result: str,
    terminal_event: str,
    terminal_baseline: int,
    timeout_seconds: float,
    description: str,
) -> dict[str, Any]:
    """Wait for a new terminal event and its hook-settled result.

    A latched outcome from an earlier turn is not evidence for the current
    turn, so the wait requires the terminal event count to move past the
    baseline captured before the provoking input.
    """

    def settled(tracked: dict[str, Any]) -> bool:
        facts = _tracked_facts(tracked)
        if facts["last_turn_result"] != result:
            return False
        return _event_count(session.session_root, terminal_event) > terminal_baseline

    _ = ctx
    return _wait_tracked(
        session,
        predicate=settled,
        timeout_seconds=timeout_seconds,
        description=description,
    )


def _submit_and_await(
    ctx: RunContext,
    session: SessionState,
    text: str,
    *,
    result: str,
    timeout_seconds: float,
    description: str,
) -> dict[str, Any]:
    """Submit one prompt and wait for its own terminal settlement."""

    event = "Stop" if result == "success" else "Interrupt"
    baseline = _event_count(session.session_root, event)
    _submit_text(ctx, session, text)
    return _await_hook_settlement(
        ctx,
        session,
        result=result,
        terminal_event=event,
        terminal_baseline=baseline,
        timeout_seconds=timeout_seconds,
        description=description,
    )


def _drive_multi_turn(ctx: RunContext, session: SessionState, secrets: tuple[str, ...]) -> None:
    """Scenario 1: two short prompts settle success from hook evidence."""

    _submit_and_await(
        ctx,
        session,
        PROMPT_OK,
        result="success",
        timeout_seconds=150.0,
        description="first OK turn success",
    )
    first = _record_checkpoint(ctx, session, "turn-1-success", secrets=secrets)
    if first["tracked"]["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"first turn not hook-settled: {first['tracked']}")
    if first["tracked"]["turn_phase"] != "ready":
        raise ScenarioFailure(f"first turn phase is not ready: {first['tracked']}")

    _submit_and_await(
        ctx,
        session,
        PROMPT_DONE,
        result="success",
        timeout_seconds=150.0,
        description="second DONE turn success",
    )
    second = _record_checkpoint(ctx, session, "turn-2-success", secrets=secrets)
    if second["tracked"]["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"second turn not hook-settled: {second['tracked']}")
    if second["tracked"]["turn_phase"] != "ready":
        raise ScenarioFailure(f"second turn phase is not ready: {second['tracked']}")
    if _event_count(session.session_root, "Stop") < 2:
        raise ScenarioFailure("expected at least two Stop events")
    prompts = _turn_ids(session.session_root, "UserPromptSubmit")
    stops = _turn_ids(session.session_root, "Stop")
    if len(prompts) < 2 or not set(prompts[-2:]).issubset(set(stops)):
        raise ScenarioFailure(f"turn ids do not correlate: prompts={prompts} stops={stops}")
    if not any(item["session_id"] for item in _event_summary(session.session_root)):
        raise ScenarioFailure("no session_id in provider events")


def _wait_permission_modal(
    ctx: RunContext,
    session: SessionState,
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    """Wait for the tracked blocked phase and record the modal checkpoint."""

    _wait_tracked(
        session,
        predicate=lambda tracked: _tracked_facts(tracked)["turn_phase"] == "blocked",
        timeout_seconds=150.0,
        description="approval modal blocked phase",
    )
    record = _record_checkpoint(ctx, session, "blocked", secrets=secrets)
    if record["tracked"]["turn_phase"] != "blocked":
        raise ScenarioFailure(f"tracked state did not show blocked: {record['tracked']}")
    if _event_count(session.session_root, "PermissionRequest") < 1:
        raise ScenarioFailure("no PermissionRequest hook event before the modal")
    return record


def _drive_permission_allow(
    ctx: RunContext, session: SessionState, secrets: tuple[str, ...]
) -> None:
    """Scenario 2: approval allow settles blocked -> active -> success."""

    _submit_text(ctx, session, PROMPT_ALLOW)
    _wait_permission_modal(ctx, session, secrets)
    allow_path = Path("/tmp/houmao-smoke-allow.txt")
    allow_path.unlink(missing_ok=True)
    stop_baseline = _event_count(session.session_root, "Stop")
    _send_literal(ctx, session, "y")
    _await_hook_settlement(
        ctx,
        session,
        result="success",
        terminal_event="Stop",
        terminal_baseline=stop_baseline,
        timeout_seconds=150.0,
        description="allow-path turn success",
    )
    final = _record_checkpoint(ctx, session, "allowed-success", secrets=secrets)
    if final["tracked"]["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"allow turn not hook-settled: {final['tracked']}")
    if not allow_path.is_file():
        raise ScenarioFailure("allowed command did not create /tmp/houmao-smoke-allow.txt")
    if _event_count(session.session_root, "Interrupt") != 0:
        raise ScenarioFailure("allow path produced an Interrupt event")


def _drive_permission_deny(
    ctx: RunContext, session: SessionState, secrets: tuple[str, ...]
) -> None:
    """Scenario 3: approval deny settles blocked -> interrupted."""

    _submit_text(ctx, session, PROMPT_DENY)
    _wait_permission_modal(ctx, session, secrets)
    stops_before = _event_count(session.session_root, "Stop")
    post_tool_baseline = _event_count(session.session_root, "PostToolUse")
    interrupt_baseline = _event_count(session.session_root, "Interrupt")
    _send_key(ctx, session, "Escape")
    _await_hook_settlement(
        ctx,
        session,
        result="interrupted",
        terminal_event="Interrupt",
        terminal_baseline=interrupt_baseline,
        timeout_seconds=150.0,
        description="deny-path interrupted settlement",
    )
    final = _record_checkpoint(ctx, session, "denied-interrupted", secrets=secrets)
    facts = final["tracked"]
    if facts["last_turn_result"] != "interrupted":
        raise ScenarioFailure(f"deny path did not settle interrupted: {facts}")
    if facts["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"deny path interrupted is not hook-derived: {facts}")
    if _event_count(session.session_root, "Stop") != stops_before:
        raise ScenarioFailure("deny path produced a Stop event")
    if _event_count(session.session_root, "PostToolUse") != post_tool_baseline:
        raise ScenarioFailure("deny path settled the denied tool with a PostToolUse event")
    if Path("/tmp/houmao-smoke-deny.txt").exists():
        raise ScenarioFailure("denied command created /tmp/houmao-smoke-deny.txt")


def _drive_esc_interrupt(ctx: RunContext, session: SessionState, secrets: tuple[str, ...]) -> None:
    """Scenario 4: Escape mid-generation settles hook-derived interrupted."""

    _submit_text(ctx, session, PROMPT_ESSAY)
    _wait_tracked(
        session,
        predicate=lambda tracked: _tracked_facts(tracked)["turn_phase"] == "active",
        timeout_seconds=120.0,
        description="active essay turn",
    )
    stops_before = _event_count(session.session_root, "Stop")
    interrupt_baseline = _event_count(session.session_root, "Interrupt")
    time.sleep(2.5)
    _send_key(ctx, session, "Escape")
    _await_hook_settlement(
        ctx,
        session,
        result="interrupted",
        terminal_event="Interrupt",
        terminal_baseline=interrupt_baseline,
        timeout_seconds=150.0,
        description="Esc interrupt settlement",
    )
    final = _record_checkpoint(ctx, session, "esc-interrupted", secrets=secrets)
    facts = final["tracked"]
    if facts["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"Esc interrupt is not hook-derived: {facts}")
    if _event_count(session.session_root, "Interrupt") < 1:
        raise ScenarioFailure("no Interrupt hook event after Escape")
    if _event_count(session.session_root, "Stop") != stops_before:
        raise ScenarioFailure("Esc turn produced a Stop event")


def _drive_compaction(ctx: RunContext, session: SessionState, secrets: tuple[str, ...]) -> None:
    """Scenario 5: manual compaction is held, and the next turn is a new epoch."""

    _submit_and_await(
        ctx,
        session,
        PROMPT_README,
        result="success",
        timeout_seconds=150.0,
        description="pre-compact README turn success",
    )
    pre_compact_turn_ids = _turn_ids(session.session_root, "UserPromptSubmit")
    _submit_text(ctx, session, "/compact")
    _wait_for(
        lambda: _event_count(session.session_root, "PreCompact") >= 1,
        timeout_seconds=120.0,
        description="PreCompact hook event",
    )
    _wait_for(
        lambda: _event_count(session.session_root, "PostCompact") >= 1,
        timeout_seconds=180.0,
        description="PostCompact hook event",
    )
    during = _record_checkpoint(ctx, session, "post-compact-window", secrets=secrets)
    _submit_and_await(
        ctx,
        session,
        PROMPT_OK,
        result="success",
        timeout_seconds=150.0,
        description="post-compact OK turn success",
    )
    final = _record_checkpoint(ctx, session, "post-compact-turn", secrets=secrets)
    if final["tracked"]["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"post-compact turn not hook-settled: {final['tracked']}")
    if _event_count(session.session_root, "SessionStart") < 2:
        raise ScenarioFailure("compaction did not dispatch a second SessionStart")
    new_turn_ids = _turn_ids(session.session_root, "UserPromptSubmit")[len(pre_compact_turn_ids) :]
    if not new_turn_ids:
        raise ScenarioFailure("post-compact turn has no UserPromptSubmit turn id")
    if new_turn_ids[0] in pre_compact_turn_ids:
        raise ScenarioFailure(f"post-compact turn reused the old epoch: {new_turn_ids[0]}")
    counters = final["tracked"]["channel_counters"] or {}
    if int(counters.get("compaction_boundaries", 0)) < 1:
        raise ScenarioFailure(f"compaction boundary counter missing: {counters}")
    if during["tracked"]["turn_phase"] == "unknown":
        raise ScenarioFailure("posture was not held through the compaction window")


def _descendants(pid: int, table: dict[int, list[int]]) -> list[int]:
    """Return one pid and all of its descendants."""

    ordered: list[int] = []
    stack = [pid]
    while stack:
        current = stack.pop()
        ordered.append(current)
        stack.extend(table.get(current, []))
    return ordered


def _process_table() -> tuple[dict[int, list[int]], dict[int, str]]:
    """Return the parent map and command lines for all visible processes."""

    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,args="],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    children: dict[int, list[int]] = {}
    commands: dict[int, str] = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 2:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        commands[pid] = parts[2] if len(parts) > 2 else ""
        children.setdefault(ppid, []).append(pid)
    return children, commands


def _kill_codex_provider(session: SessionState, *, codex_bin: Path) -> list[int]:
    """SIGKILL the Codex process tree under the agent pane, never the collector."""

    panes = _pane_list(session.tmux_session_name)
    if not panes:
        raise ScenarioFailure("no tmux panes to locate the Codex provider")
    children, commands = _process_table()
    targets: list[int] = []
    binary_text = str(codex_bin)
    for pane in panes:
        try:
            pane_pid = int(pane["pid"])
        except ValueError:
            continue
        for candidate in _descendants(pane_pid, children)[1:]:
            command = commands.get(candidate, "")
            if "hook_observation.collector" in command or "launch-wrapper.sh" in command:
                continue
            is_codex = (
                binary_text in command
                or command.startswith("codex ")
                or ("codex" in command and "--profile openlux-auto" in command)
            )
            if is_codex:
                targets.append(candidate)
                break
    if not targets:
        raise ScenarioFailure("could not locate the Codex provider process")
    kill_roots = sorted(set(targets))
    signalled: list[int] = []
    table, _ = _process_table()
    for root in kill_roots:
        for target in reversed(_descendants(root, table)):
            try:
                os.kill(target, signal.SIGKILL)
                signalled.append(target)
            except ProcessLookupError:
                continue
            except PermissionError:
                continue
    return signalled


def _drive_kill_gap(ctx: RunContext, session: SessionState, secrets: tuple[str, ...]) -> None:
    """Scenario 6: provider kill yields presence loss and a truthful terminal gap."""

    _submit_text(ctx, session, PROMPT_ESSAY)
    _wait_tracked(
        session,
        predicate=lambda tracked: _tracked_facts(tracked)["turn_phase"] == "active",
        timeout_seconds=120.0,
        description="active essay turn before kill",
    )
    time.sleep(3.0)
    stopped_collector_before = _channel_status(session.session_root) or {}
    collector_pid = (stopped_collector_before.get("install") or {}).get("collector_pid")
    signalled = _kill_codex_provider(session, codex_bin=ctx.codex_bin)
    if collector_pid in signalled:
        raise ScenarioFailure("kill targeted the hook collector")
    _write_json(ctx.run_dir / "kill-pids.json", {"signalled": signalled})

    def gap_visible(tracked: dict[str, Any]) -> bool:
        facts = _tracked_facts(tracked)
        counters = facts["channel_counters"] or {}
        return (
            facts["turn_phase"] == "unknown"
            and facts["last_turn_result"] == "none"
            and int(counters.get(TERMINAL_GAP_COUNTER, 0)) >= 1
        )

    _wait_tracked(
        session,
        predicate=gap_visible,
        timeout_seconds=120.0,
        description="terminal gap in tracked state",
    )
    final = _record_checkpoint(ctx, session, "kill-gap", secrets=secrets)
    facts = final["tracked"]
    if facts["last_turn_result"] == "success":
        raise ScenarioFailure("kill-gap reported success")
    if facts["turn_phase"] != "unknown":
        raise ScenarioFailure(f"kill-gap phase is not unknown: {facts}")
    if facts["last_turn_result"] != "none":
        raise ScenarioFailure(f"kill-gap last_turn is not none: {facts}")
    reasons = facts["hook_conflict_reasons"] or []
    if "hook_terminal_gap" not in reasons:
        raise ScenarioFailure(f"terminal gap diagnostic missing: {reasons}")
    if _event_count(session.session_root, "Stop") != 0:
        raise ScenarioFailure("kill-gap turn produced a Stop event")
    if _event_count(session.session_root, "SessionEnd") != 0:
        raise ScenarioFailure("kill-gap turn produced a SessionEnd event")


DRIVERS: dict[str, Callable[[RunContext, SessionState, tuple[str, ...]], None]] = {
    "multi_turn": _drive_multi_turn,
    "permission_allow": _drive_permission_allow,
    "permission_deny": _drive_permission_deny,
    "esc_interrupt": _drive_esc_interrupt,
    "compaction": _drive_compaction,
    "kill_gap": _drive_kill_gap,
}


def _copy_archival_evidence(ctx: RunContext, session: SessionState) -> None:
    """Copy the final event stream and channel status into the evidence tree."""

    evidence = ctx.evidence_dir
    channel_dir = _codex_channel_dir(session.session_root)
    for name in ("channel.json", "events.ndjson", "collector.json"):
        source = channel_dir / name
        if source.is_file():
            target = evidence / f"final-{name}"
            shutil.copyfile(source, target)
            session.evidence_files.append(target)
    manifest_copy = evidence / "final-session-manifest.json"
    if session.manifest_path.is_file():
        shutil.copyfile(session.manifest_path, manifest_copy)
        session.evidence_files.append(manifest_copy)


def _teardown(ctx: RunContext, session: SessionState | None) -> None:
    """Stop the managed session and ensure its tmux session is gone."""

    tmux_session = session.tmux_session_name if session is not None else ""
    manifest = session.manifest_path if session is not None else None
    if manifest is not None:
        result = _cli(
            "stop-session",
            "--agent-def-dir",
            str(AGENT_DEF_DIR),
            "--agent-identity",
            str(manifest),
            "--force-cleanup",
            env=ctx.env,
            timeout=120.0,
        )
        if result.returncode != 0:
            (ctx.run_dir / "stop-session.stderr.txt").write_text(result.stderr, encoding="utf-8")
    if tmux_session:
        for _ in range(10):
            if _tmux("has-session", "-t", tmux_session).returncode != 0:
                break
            _tmux("kill-session", "-t", tmux_session)
            time.sleep(0.5)
    _scrub_private_env_artifacts(ctx)


def _scrub_private_env_artifacts(ctx: RunContext) -> None:
    """Remove Codex artifacts that snapshot the lane environment.

    Codex writes ``shell_snapshots/`` from the provider process environment,
    which includes the exported lane credentials. The scratch home is
    disposable, so the snapshot and any stray auth file are removed at
    teardown instead of being retained as evidence.
    """

    shutil.rmtree(ctx.codex_home / "shell_snapshots", ignore_errors=True)
    (ctx.codex_home / "auth.json").unlink(missing_ok=True)


def _run_scenario(
    name: str,
    *,
    run_root: Path,
    launcher: Path,
    codex_bin: Path,
    stamp: str,
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    """Run one scenario end to end and return its report record."""

    scenario = SCENARIOS[name]
    ctx = _prepare_run(
        scenario=scenario,
        run_root=run_root,
        launcher=launcher,
        codex_bin=codex_bin,
        stamp=stamp,
    )
    session: SessionState | None = None
    status = "FAIL"
    error: str | None = None
    try:
        session = _start_session(ctx)
        _await_composer(ctx, session, secrets=secrets)
        driver = DRIVERS[scenario.kind]
        driver(ctx, session, secrets)
        _copy_archival_evidence(ctx, session)
        status = "PASS"
    except ScenarioFailure as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 - manual harness records any failure
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if status != "PASS" and session is not None:
            try:
                (ctx.evidence_dir / "failure-pane.txt").write_text(
                    _capture_pane(session.tmux_session_name), encoding="utf-8"
                )
            except Exception:  # noqa: BLE001 - failure capture is best-effort
                pass
            try:
                _record_checkpoint(ctx, session, "failure", secrets=secrets)
            except Exception:  # noqa: BLE001 - failure capture is best-effort
                pass
        try:
            _teardown(ctx, session)
        except Exception as exc:  # noqa: BLE001 - cleanup must not mask the result
            if error is None:
                error = f"teardown: {type(exc).__name__}: {exc}"
                status = "FAIL"

    checkpoints = session.checkpoints if session is not None else []
    final_secret_free = (
        _secret_free_check(ctx=ctx, session=session, secrets=secrets)
        if session is not None
        else {"pass": True}
    )
    _write_json(ctx.run_dir / "secret-free-final.json", final_secret_free)
    report = {
        "scenario": name,
        "status": status,
        "error": error,
        "run_dir": str(ctx.run_dir),
        "evidence_dir": str(ctx.evidence_dir),
        "checkpoints": checkpoints,
        "final_secret_free": final_secret_free,
        "tmux_session": session.tmux_session_name if session is not None else None,
    }
    _write_json(ctx.run_dir / "scenario-report.json", report)
    if status == "PASS" and checkpoints:
        last = checkpoints[-1]["secret_free"]
        if not last.get("pass") or not final_secret_free.get("pass"):
            report["status"] = "FAIL"
            report["error"] = f"secret leak detected: checkpoint={last} final={final_secret_free}"
            _write_json(ctx.run_dir / "scenario-report.json", report)
    return report


def _resolve_codex_bin(value: str | None) -> Path:
    """Resolve the Codex binary to launch."""

    if value:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        if not path.is_file():
            raise ScenarioFailure(f"codex binary not found: {path}")
        return path
    found = shutil.which("codex")
    if not found:
        raise ScenarioFailure("codex binary not found on PATH")
    return Path(found)


def main(argv: list[str] | None = None) -> int:
    """Run the requested qualification scenarios."""

    parser = argparse.ArgumentParser(
        description="Manual live Codex hook-observation smoke through the managed launch path."
    )
    parser.add_argument(
        "--scenario",
        choices=[*SCENARIOS, "all"],
        default="multi-turn",
        help="Scenario to run; 'all' runs the non-floor matrix.",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=DEFAULT_RUN_ROOT,
        help="Scratch root for runs and evidence (default: tmp/codex-hook-smoke).",
    )
    parser.add_argument(
        "--launcher",
        type=Path,
        default=DEFAULT_LAUNCHER,
        help="Credential launcher whose OPENLUX exports feed the wrapper.",
    )
    parser.add_argument(
        "--codex-bin",
        default=None,
        help="Codex binary override (use for the side-by-side floor install).",
    )
    args = parser.parse_args(argv)

    if shutil.which("tmux") is None:
        raise ScenarioFailure("tmux not found on PATH")
    launcher = args.launcher.expanduser().resolve()
    if not launcher.is_file():
        raise ScenarioFailure(f"launcher not found: {launcher}")
    codex_bin = _resolve_codex_bin(args.codex_bin)
    run_root = args.run_root.expanduser().resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    secrets = _secret_values(launcher)

    stamp = _utc_stamp()
    names = list(ALL_ORDER) if args.scenario == "all" else [args.scenario]
    reports: list[dict[str, Any]] = []
    for name in names:
        print(f"[{name}] starting", flush=True)
        report = _run_scenario(
            name,
            run_root=run_root,
            launcher=launcher,
            codex_bin=codex_bin,
            stamp=stamp,
            secrets=secrets,
        )
        reports.append(report)
        print(f"[{name}] {report['status']} {report.get('error') or ''}", flush=True)
        for checkpoint in report.get("checkpoints", []):
            tracked = checkpoint.get("tracked", {})
            print(
                f"  {checkpoint['label']}: phase={tracked.get('turn_phase')} "
                f"last_turn={tracked.get('last_turn_result')}/"
                f"{tracked.get('last_turn_source')} "
                f"channel={checkpoint.get('channel_state')} "
                f"secret_free={checkpoint.get('secret_free', {}).get('pass')}",
                flush=True,
            )

    summary = {
        "generated_at_utc": _utc_now(),
        "codex_bin": str(codex_bin),
        "reports": reports,
    }
    summary_path = run_root / f"summary-{stamp}.json"
    _write_json(summary_path, summary)
    print(json.dumps({"summary": str(summary_path)}, indent=2))
    return 0 if all(report["status"] == "PASS" for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
