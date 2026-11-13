"""Qualify Kimi hook scenarios with explicitly imported external credentials.

Use --auth-bundle NAME after discovery/import with the shared fixture helper.
Every scenario owns a unique private run and uses current manager creation and
scoped cleanup. Source auth homes and reusable bundles remain unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/agents/test-fixtures"))
from fixturelib.auth import bundle_path, external_root, validate_external_path  # noqa: E402
from fixturelib.config import ResolvedConfig  # noqa: E402
from fixturelib.launch import launch_run, run_environment, stop_run  # noqa: E402
from fixturelib.prepare import prepare_run  # noqa: E402

AGENT_DEF_DIR = REPO_ROOT / "tests" / "fixtures" / "plain-agent-def"
DEFAULT_RUN_ROOT = Path.home() / ".local/state/houmao/test-fixtures/kimi-hook-smoke"
ROLE_NAME = "gpu-kernel-coder"

KIMI_BUNDLE_CONFIG = Path("files") / "config.toml"
KIMI_BUNDLE_CREDENTIALS = Path("files") / "credentials" / "kimi-code.json"
KIMI_BUNDLE_ENV = Path("env") / "vars.env"

PROMPT_OK = "Reply with exactly: OK"
PROMPT_DONE = "Reply with exactly: DONE"
PROMPT_ESSAY = "Write a long essay about faults."
PROMPT_README = "Read README.md and summarize in one sentence."

S4_README_TEXT = """# Smoke README

This file exists so the compaction scenario has a small, deterministic
document to summarize before the manual ``/compact`` command.
"""

HOOK_CHANNEL_PROVIDER = "kimi"
KIMI_OBSERVER_MARKER = "# >>> houmao kimi hook observation"
KIMI_HOOK_EVENT_COUNT = 20
TERMINAL_GAP_COUNTER = "terminal_gaps"

SECRET_MARKERS = ("access_token", "refresh_token", "Bearer ", "KIMI_MODEL_API_KEY=")


@dataclass(frozen=True)
class Scenario:
    """One qualification scenario and the driver it selects."""

    name: str
    kind: str


SCENARIOS: dict[str, Scenario] = {
    "multi-turn": Scenario(name="multi-turn", kind="multi_turn"),
    "esc-interrupt": Scenario(name="esc-interrupt", kind="esc_interrupt"),
    "compaction": Scenario(name="compaction", kind="compaction"),
    "kill-gap": Scenario(name="kill-gap", kind="kill_gap"),
    "floor": Scenario(name="floor", kind="multi_turn"),
}

ALL_ORDER = (
    "multi-turn",
    "esc-interrupt",
    "compaction",
    "kill-gap",
)


class ScenarioFailure(RuntimeError):
    """Raised when a scenario cannot meet its predeclared expectation."""


@dataclass
class BundleProvenance:
    """Explicit credential-bundle origin and external storage check, never contents."""

    lane: str
    path: Path
    storage_check: dict[str, Any]
    files: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RunContext:
    """Paths and process coordinates for one scenario run."""

    scenario: Scenario
    run_dir: Path
    workdir: Path
    kimi_home: Path
    manifest: Path
    env_file: Path
    agent_name: str
    kimi_bin: Path
    kimi_version: str | None
    bundle: BundleProvenance
    env: dict[str, str]

    @property
    def evidence_dir(self) -> Path:
        """Return the evidence directory for this run."""

        return self.run_dir / "evidence"

    @property
    def session_manifest(self) -> Path:
        """Return the session manifest path recorded by the manager."""

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


def _kimi_channel_dir(session_root: Path) -> Path:
    """Return the Kimi hook artifact directory for one session."""

    return session_root / "hook-observation" / "kimi"


def _channel_status(session_root: Path) -> dict[str, Any] | None:
    """Read the secret-free channel status document."""

    payload = _read_json(_kimi_channel_dir(session_root) / "channel.json")
    return payload if isinstance(payload, dict) else None


def _event_rows(session_root: Path) -> list[dict[str, Any]]:
    """Return parsed event store rows, skipping malformed lines."""

    path = _kimi_channel_dir(session_root) / "events.ndjson"
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
    """Return the correlation fields of every provider event."""

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
                "source": provider.get("source"),
                "origin_kind": provider.get("origin_kind"),
                "tool_name": provider.get("tool_name"),
                "tool_call_id": provider.get("tool_call_id"),
            }
        )
    return summary


def _event_count(session_root: Path, name: str) -> int:
    """Count provider events with one name."""

    return sum(1 for item in _event_summary(session_root) if item["hook_event_name"] == name)


def _event_count_matching(session_root: Path, name: str, **fields: Any) -> int:
    """Count provider events with one name and matching provider fields."""

    return sum(
        1
        for item in _event_summary(session_root)
        if item["hook_event_name"] == name
        and all(item.get(key) == value for key, value in fields.items())
    )


def _user_turn_ids(session_root: Path) -> list[int]:
    """Return ordered integer turn ids bound by user-origin ``TurnStarted``."""

    values: list[int] = []
    for item in _event_summary(session_root):
        if item["hook_event_name"] != "TurnStarted" or item["origin_kind"] != "user":
            continue
        raw = item["turn_id"]
        try:
            values.append(int(str(raw)))
        except (TypeError, ValueError):
            continue
    return values


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
    """Read current gateway status from the captured authority."""

    return _gateway_request(session, "/v1/status")


def _gateway_request(
    session: SessionState, path: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call the captured local gateway without logging private request diagnostics."""

    request = urllib.request.Request(
        f"http://{session.gateway_host}:{session.gateway_port}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


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
    """Capture visible agent pane text, preferring the Kimi process pane."""

    panes = _pane_list(tmux_session)
    candidate = next(
        (pane for pane in panes if "kimi" in pane["command"].lower()),
        panes[0] if panes else None,
    )
    if candidate is None:
        return ""
    result = _tmux("capture-pane", "-p", "-t", candidate["pane_id"])
    return result.stdout if result.returncode == 0 else ""


def _bundle_files(bundle: Path) -> list[dict[str, Any]]:
    """Return secret-free name/size/mode records for bundle files."""

    rows: list[dict[str, Any]] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        rows.append(
            {
                "relative_path": str(path.relative_to(bundle)),
                "size": stat.st_size,
                "mode": oct(stat.st_mode & 0o777),
            }
        )
    return rows


def _ensure_bundle(run_root: Path, selected: Path) -> BundleProvenance:
    """Require explicitly imported external state without ambient-home fallback."""

    selected = validate_external_path(selected)
    if (
        not (selected / "import.json").is_file()
        or not (selected / KIMI_BUNDLE_CREDENTIALS).is_file()
    ):
        raise ScenarioFailure("Import a Kimi native bundle explicitly before running this smoke")
    provenance = BundleProvenance(
        lane="explicit-imported-bundle",
        path=selected,
        storage_check={"outside_checkout": True},
        files=_bundle_files(selected),
    )
    _write_bundle_provenance(run_root, provenance)
    return provenance


def _write_bundle_provenance(run_root: Path, provenance: BundleProvenance) -> None:
    """Write one secret-free bundle-provenance artifact."""

    payload = {
        "lane": provenance.lane,
        "path": str(provenance.path),
        "storage_check": provenance.storage_check,
        "files": provenance.files,
        "recorded_at_utc": _utc_now(),
    }
    _write_json(run_root / "bundle-provenance.json", payload)


def _secret_values(bundle: BundleProvenance) -> tuple[str, ...]:
    """Extract credential values in memory for leak scanning only.

    The returned values are never logged or written; they are compared
    against public artifacts to detect accidental projection.
    """

    credentials_path = bundle.path / KIMI_BUNDLE_CREDENTIALS
    try:
        payload = json.loads(credentials_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    values: list[str] = []
    if isinstance(payload, dict):
        for key in ("access_token", "refresh_token"):
            value = payload.get(key)
            if isinstance(value, str) and len(value) >= 8:
                values.append(value)
    return tuple(values)


def _secret_free_check(
    *,
    ctx: RunContext,
    session: SessionState,
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    """Scan public artifacts for credential values and marker strings."""

    files = [path for path in session.evidence_files if path.is_file()]
    files.extend(
        [
            _kimi_channel_dir(session.session_root) / "channel.json",
            ctx.run_dir / "start.json",
            ctx.run_dir / "manifest-preview.json",
        ]
    )
    hit_files: list[str] = []
    markers = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found = False
        for value in secrets:
            if value and value in text:
                found = True
        for marker in SECRET_MARKERS:
            if marker in text:
                found = True
                markers += 1
        if found:
            hit_files.append(str(path.relative_to(ctx.run_dir)))
    channel = _read_json(_kimi_channel_dir(session.session_root) / "channel.json")
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
        "channel_install": (channel or {}).get("install"),
        "channel_events_by_name": (channel or {}).get("events_by_name"),
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
    """Send literal text and Enter through maintained gateway control."""

    _gateway_request(
        session, "/v1/control/send-keys", {"sequence": text, "escape_special_keys": True}
    )
    time.sleep(0.2)
    _gateway_request(session, "/v1/control/send-keys", {"sequence": "<[Enter]>"})


def _send_key(ctx: RunContext, session: SessionState, key: str) -> None:
    """Send one named key through the captured gateway."""

    _gateway_request(session, "/v1/control/send-keys", {"sequence": f"<[{key}]>"})


def _prepare_run(
    *,
    scenario: Scenario,
    run_root: Path,
    kimi_bin: Path,
    kimi_version: str | None,
    bundle: BundleProvenance,
    stamp: str,
) -> RunContext:
    """Prepare one real private project through the shared fixture helper."""

    config = ResolvedConfig(
        client="kimi",
        mode="tui",
        surface="manager",
        auth_method="native-login",
        native_bundle=bundle.path,
    )
    run = prepare_run(config, run_root=run_root, role=ROLE_NAME, executable=str(kimi_bin))
    run_dir = Path(run["run_dir"])
    (run_dir / "evidence").mkdir(mode=0o700)
    workdir = Path(run["workdir"])
    (workdir / "README.md").write_text(S4_README_TEXT)
    return RunContext(
        scenario=scenario,
        run_dir=run_dir,
        workdir=workdir,
        kimi_home=Path(run["home_path"]),
        manifest=run_dir / "run.json",
        env_file=run_dir / "private-env.json",
        agent_name=run_dir.name,
        kimi_bin=kimi_bin,
        kimi_version=kimi_version,
        bundle=bundle,
        env=run_environment(run),
    )


def _verify_install(ctx: RunContext, session_root: Path) -> dict[str, Any]:
    """Assert the managed Kimi observer install is present and validated."""

    channel = _channel_status(session_root)
    if channel is None:
        raise ScenarioFailure("start-session did not write a Kimi channel.json")
    install = channel.get("install") if isinstance(channel.get("install"), dict) else {}
    if install.get("path") != "managed_home":
        raise ScenarioFailure(f"hook observation install path is {install.get('path')!r}")
    config_path = ctx.kimi_home / "config.toml"
    if not config_path.is_file():
        raise ScenarioFailure("managed launch did not leave a runtime-home config.toml")
    config_text = config_path.read_text(encoding="utf-8")
    if KIMI_OBSERVER_MARKER not in config_text:
        raise ScenarioFailure("managed launch did not merge the Kimi observer block")
    try:
        payload = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as exc:
        raise ScenarioFailure(f"managed config.toml does not parse: {exc}") from exc
    hooks = payload.get("hooks")
    if not isinstance(hooks, list) or len(hooks) != KIMI_HOOK_EVENT_COUNT:
        raise ScenarioFailure(
            f"managed config.toml carries {len(hooks) if isinstance(hooks, list) else 'no'} "
            f"hooks entries, expected {KIMI_HOOK_EVENT_COUNT}"
        )
    if not (ctx.kimi_home / "SYSTEM.md").is_file():
        raise ScenarioFailure("managed launch did not project SYSTEM.md")
    return {
        "install_path": install.get("path"),
        "settings_path": install.get("settings_path"),
        "hook_entries": len(hooks),
        "observer_marker": True,
        "system_prompt": True,
    }


def _start_session(ctx: RunContext) -> SessionState:
    """Launch through the project manager and retain its authoritative coordinates."""

    result = launch_run(ctx.run_dir)
    identity = result["identity"]
    manifest_path = Path(identity["manifest_path"])
    ctx.session_manifest.write_text(str(manifest_path) + "\n")
    manifest = json.loads(manifest_path.read_text())
    ctx.kimi_home = Path(manifest["launch_plan"]["home_path"])
    session = SessionState(
        manifest_path=manifest_path,
        session_root=_session_root(manifest_path),
        tmux_session_name=identity["tmux_session_name"],
        gateway_host=identity["gateway_host"],
        gateway_port=identity["gateway_port"],
    )
    _write_json(ctx.run_dir / "start.json", result)
    _write_json(ctx.run_dir / "install-verify.json", _verify_install(ctx, session.session_root))
    _wait_for(
        lambda: _tracked_state(session.gateway_host, session.gateway_port),
        timeout_seconds=30.0,
        description="live gateway tracked state",
    )
    return session


def _await_composer(ctx: RunContext, session: SessionState, *, secrets: tuple[str, ...]) -> None:
    """Wait for the Kimi welcome/composer surface.

    Managed unattended launches pre-seed Kimi's workspace trust, so the
    ``Trust this folder?`` modal must never paint. Its presence is a failure,
    not something the operator accepts.
    """

    deadline = time.monotonic() + 180.0
    while time.monotonic() < deadline:
        pane = _capture_pane(session.tmux_session_name)
        if "Trust this folder?" in pane or "Trust and continue" in pane:
            (ctx.evidence_dir / "unexpected-workspace-trust-modal.txt").write_text(
                pane, encoding="utf-8"
            )
            raise ScenarioFailure("unexpected workspace trust modal despite the managed pre-seed")
        tracked = _tracked_state(session.gateway_host, session.gateway_port)
        pane_ready = (
            "Welcome to Kimi Code!" in pane
            and "context:" in pane
            and "Trust this folder?" not in pane
        )
        surface = tracked.get("surface") if isinstance(tracked, dict) else None
        if (
            pane_ready
            or (surface or {}).get("ready_posture") == "yes"
            or _tracked_facts(tracked)["turn_phase"] == "ready"
        ):
            _record_checkpoint(ctx, session, "ready", secrets=secrets)
            return
        time.sleep(1.0)
    (ctx.evidence_dir / "composer-timeout-pane.txt").write_text(
        _capture_pane(session.tmux_session_name), encoding="utf-8"
    )
    raise ScenarioFailure("timed out waiting for the Kimi ready composer")


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


def _assert_channel_active(record: dict[str, Any], *, label: str) -> None:
    """Assert tracked and on-disk channel health are active."""

    facts = record["tracked"]
    if facts["channel_state"] != "active":
        raise ScenarioFailure(f"{label}: tracked channel state is {facts['channel_state']!r}")
    if facts["hook_channel_state"] != "active":
        raise ScenarioFailure(
            f"{label}: diagnostics hook_channel_state is {facts['hook_channel_state']!r}"
        )
    if record["channel_state"] != "active":
        raise ScenarioFailure(f"{label}: channel.json state is {record['channel_state']!r}")


def _drive_multi_turn(ctx: RunContext, session: SessionState, secrets: tuple[str, ...]) -> None:
    """Scenario 1: two short prompts settle success from hook evidence."""

    _submit_and_await(
        ctx,
        session,
        PROMPT_OK,
        result="success",
        timeout_seconds=180.0,
        description="first OK turn success",
    )
    first = _record_checkpoint(ctx, session, "turn-1-success", secrets=secrets)
    if first["tracked"]["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"first turn not hook-settled: {first['tracked']}")
    if first["tracked"]["turn_phase"] != "ready":
        raise ScenarioFailure(f"first turn phase is not ready: {first['tracked']}")
    _assert_channel_active(first, label="first turn")

    _submit_and_await(
        ctx,
        session,
        PROMPT_DONE,
        result="success",
        timeout_seconds=180.0,
        description="second DONE turn success",
    )
    second = _record_checkpoint(ctx, session, "turn-2-success", secrets=secrets)
    if second["tracked"]["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"second turn not hook-settled: {second['tracked']}")
    if second["tracked"]["turn_phase"] != "ready":
        raise ScenarioFailure(f"second turn phase is not ready: {second['tracked']}")
    _assert_channel_active(second, label="second turn")
    if _event_count(session.session_root, "Stop") < 2:
        raise ScenarioFailure("expected at least two Stop events")
    if _event_count(session.session_root, "UserPromptSubmit") < 2:
        raise ScenarioFailure("expected at least two UserPromptSubmit events")
    turn_ids = _user_turn_ids(session.session_root)
    if len(turn_ids) < 2:
        raise ScenarioFailure(f"expected two user TurnStarted ids, got {turn_ids}")
    if turn_ids[-1] <= turn_ids[-2]:
        raise ScenarioFailure(f"turn ids are not increasing: {turn_ids}")
    if not any(item["session_id"] for item in _event_summary(session.session_root)):
        raise ScenarioFailure("no session_id in provider events")
    if not second["tracked"]["channel_counters"]:
        raise ScenarioFailure("tracked channel counters are missing")
    events_seen = int(second["tracked"]["channel_counters"].get("events_seen", 0))
    if events_seen < 8:
        raise ScenarioFailure(f"channel saw too few events: {events_seen}")
    if second["tracked"]["channel_last_event_name"] not in {"Stop", "SessionHeartbeat"}:
        raise ScenarioFailure(
            f"channel last event is {second['tracked']['channel_last_event_name']!r}, "
            "expected Stop or SessionHeartbeat"
        )


def _drive_esc_interrupt(ctx: RunContext, session: SessionState, secrets: tuple[str, ...]) -> None:
    """Scenario 2: Escape mid-generation settles hook-derived interrupted."""

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
        timeout_seconds=180.0,
        description="Esc interrupt settlement",
    )
    final = _record_checkpoint(ctx, session, "esc-interrupted", secrets=secrets)
    facts = final["tracked"]
    if facts["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"Esc interrupt is not hook-derived: {facts}")
    if facts["turn_phase"] != "ready":
        raise ScenarioFailure(f"Esc interrupt did not settle ready: {facts}")
    if _event_count(session.session_root, "Interrupt") < 1:
        raise ScenarioFailure("no Interrupt hook event after Escape")
    if _event_count(session.session_root, "Stop") != stops_before:
        raise ScenarioFailure("Esc turn produced a Stop event")
    _assert_channel_active(final, label="Esc interrupt")


def _drive_compaction(ctx: RunContext, session: SessionState, secrets: tuple[str, ...]) -> None:
    """Scenario 3: manual compaction is held, and the next turn is a new epoch."""

    _submit_and_await(
        ctx,
        session,
        PROMPT_README,
        result="success",
        timeout_seconds=180.0,
        description="pre-compact README turn success",
    )
    pre_compact_turn_ids = _user_turn_ids(session.session_root)
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
    if during["tracked"]["turn_phase"] == "unknown":
        raise ScenarioFailure("posture was not held through the compaction window")
    _submit_and_await(
        ctx,
        session,
        PROMPT_OK,
        result="success",
        timeout_seconds=180.0,
        description="post-compact OK turn success",
    )
    final = _record_checkpoint(ctx, session, "post-compact-turn", secrets=secrets)
    if final["tracked"]["last_turn_source"] != "hook_observation":
        raise ScenarioFailure(f"post-compact turn not hook-settled: {final['tracked']}")
    counters = final["tracked"]["channel_counters"] or {}
    if int(counters.get("compaction_boundaries", 0)) < 1:
        raise ScenarioFailure(f"compaction boundary counter missing: {counters}")
    if _event_count_matching(session.session_root, "SessionStart", source="compact") != 0:
        raise ScenarioFailure("Kimi emitted an unexpected SessionStart(source=compact)")
    new_turn_ids = _user_turn_ids(session.session_root)[len(pre_compact_turn_ids) :]
    if not new_turn_ids:
        raise ScenarioFailure("post-compact turn has no user TurnStarted turn id")
    if new_turn_ids[0] in pre_compact_turn_ids:
        raise ScenarioFailure(f"post-compact turn reused the old epoch: {new_turn_ids[0]}")
    _assert_channel_active(final, label="post-compact turn")


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


def _kill_kimi_provider(session: SessionState, *, kimi_bin: Path) -> list[int]:
    """SIGKILL the Kimi process tree under the agent pane, never the collector."""

    panes = _pane_list(session.tmux_session_name)
    if not panes:
        raise ScenarioFailure("no tmux panes to locate the Kimi provider")
    children, commands = _process_table()
    targets: list[int] = []
    binary_text = str(kimi_bin)
    for pane in panes:
        try:
            pane_pid = int(pane["pid"])
        except ValueError:
            continue
        for candidate in _descendants(pane_pid, children)[1:]:
            command = commands.get(candidate, "")
            if "hook_observation.collector" in command:
                continue
            is_kimi = (
                binary_text in command
                or command.startswith("kimi ")
                or "kimi-code" in command
                or ("kimi" in command and "--auto" in command)
            )
            if is_kimi:
                targets.append(candidate)
                break
    if not targets:
        raise ScenarioFailure("could not locate the Kimi provider process")
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
    """Scenario 4: provider kill yields presence loss and a truthful terminal gap."""

    _submit_text(ctx, session, PROMPT_ESSAY)
    _wait_tracked(
        session,
        predicate=lambda tracked: _tracked_facts(tracked)["turn_phase"] == "active",
        timeout_seconds=120.0,
        description="active essay turn before kill",
    )
    time.sleep(3.0)
    channel_before = _channel_status(session.session_root) or {}
    collector_pid = (channel_before.get("install") or {}).get("collector_pid")
    signalled = _kill_kimi_provider(session, kimi_bin=ctx.kimi_bin)
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
    "esc_interrupt": _drive_esc_interrupt,
    "compaction": _drive_compaction,
    "kill_gap": _drive_kill_gap,
}


def _copy_archival_evidence(ctx: RunContext, session: SessionState) -> None:
    """Copy the final event stream and channel status into the evidence tree."""

    evidence = ctx.evidence_dir
    channel_dir = _kimi_channel_dir(session.session_root)
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
    """Stop only the managed identity recorded in the selected private run."""

    stop_run(ctx.run_dir)


def _run_scenario(
    name: str,
    *,
    run_root: Path,
    kimi_bin: Path,
    kimi_version: str | None,
    bundle: BundleProvenance,
    stamp: str,
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    """Run one scenario end to end and return its report record."""

    scenario = SCENARIOS[name]
    ctx = _prepare_run(
        scenario=scenario,
        run_root=run_root,
        kimi_bin=kimi_bin,
        kimi_version=kimi_version,
        bundle=bundle,
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
        "tool": "kimi",
        "kimi_bin": str(kimi_bin),
        "kimi_version": kimi_version,
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


def _resolve_kimi_bin(value: str | None) -> tuple[Path, str | None]:
    """Resolve the Kimi binary and its reported version."""

    if value:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        if not path.is_file():
            raise ScenarioFailure(f"kimi binary not found: {path}")
    else:
        found = shutil.which("kimi")
        if not found:
            raise ScenarioFailure("kimi binary not found on PATH")
        path = Path(found).resolve()
    result = subprocess.run(
        [str(path), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    version = result.stdout.strip().splitlines()[0] if result.stdout.strip() else None
    return path, version


def _ledger_path(run_root: Path) -> Path:
    """Return the accumulated qualification ledger path."""

    return run_root / "qualification-ledger.json"


def _update_ledger(
    run_root: Path,
    reports: list[dict[str, Any]],
    *,
    stamp: str,
    bundle: BundleProvenance,
) -> None:
    """Merge this invocation's reports into the qualification ledger."""

    ledger = _read_json(_ledger_path(run_root))
    if not isinstance(ledger, dict) or not isinstance(ledger.get("entries"), list):
        ledger = {"entries": []}
    entries: list[dict[str, Any]] = [
        entry for entry in ledger["entries"] if isinstance(entry, dict)
    ]
    for report in reports:
        entry = {
            "leg": report["scenario"],
            "kimi_bin": report["kimi_bin"],
            "kimi_version": report["kimi_version"],
            "status": report["status"],
            "error": report["error"],
            "run_dir": report["run_dir"],
            "evidence_dir": report["evidence_dir"],
            "recorded_at_utc": _utc_now(),
            "bundle_lane": bundle.lane,
            "checkpoints": [
                {
                    "label": checkpoint["label"],
                    "phase": checkpoint["tracked"]["turn_phase"],
                    "last_turn_result": checkpoint["tracked"]["last_turn_result"],
                    "last_turn_source": checkpoint["tracked"]["last_turn_source"],
                    "channel_state": checkpoint["channel_state"],
                    "terminal_gaps": (checkpoint["tracked"]["channel_counters"] or {}).get(
                        "terminal_gaps"
                    ),
                    "secret_free": checkpoint["secret_free"]["pass"],
                }
                for checkpoint in report["checkpoints"]
            ],
        }
        entries = [
            existing
            for existing in entries
            if not (
                existing.get("leg") == entry["leg"]
                and existing.get("kimi_bin") == entry["kimi_bin"]
            )
        ]
        entries.append(entry)
    ledger = {
        "schema_version": 1,
        "generated_at_utc": _utc_now(),
        "bundle": {
            "lane": bundle.lane,
            "path": str(bundle.path),
            "storage_check": bundle.storage_check,
        },
        "entries": entries,
        "stamps": [*ledger.get("stamps", []), stamp],
    }
    _write_json(_ledger_path(run_root), ledger)
    _render_qualification(run_root, ledger)


def _render_qualification(run_root: Path, ledger: dict[str, Any]) -> None:
    """Render the secret-free ``QUALIFICATION.md`` summary from the ledger."""

    bundle = ledger.get("bundle", {})
    storage = bundle.get("storage_check", {})
    lines = [
        "# Kimi Hook Observation Live Qualification",
        "",
        f"Generated at {ledger.get('generated_at_utc', '')}.",
        "",
        "These verdicts come from live managed Kimi sessions driven by "
        "`tests/manual/manual_kimi_hook_observation_smoke.py`. Each leg asserts "
        "tracked state, hook-channel health, and a secret-free public projection.",
        "",
        "## Credential Bundle Provenance",
        "",
        f"- Lane: `{bundle.get('lane', 'unknown')}`",
        f"- Path: `{bundle.get('path', 'unknown')}`",
        f"- External private storage: `{storage.get('outside_checkout', False)}`",
        "",
        "## Verdicts",
        "",
        "| Leg | Kimi binary | Version | Verdict | Error |",
        "| --- | --- | --- | --- | --- |",
    ]
    entries = [entry for entry in ledger.get("entries", []) if isinstance(entry, dict)]
    for entry in sorted(entries, key=lambda item: (item.get("leg", ""), item.get("kimi_bin", ""))):
        error = str(entry.get("error") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {entry.get('leg')} | `{entry.get('kimi_bin')}` | "
            f"{entry.get('kimi_version')} | **{entry.get('status')}** | {error} |"
        )
    lines.extend(["", "## Per-Leg Evidence", ""])
    for entry in sorted(entries, key=lambda item: (item.get("leg", ""), item.get("kimi_bin", ""))):
        lines.extend(
            [
                f"### {entry.get('leg')} — {entry.get('status')}",
                "",
                f"- Kimi: `{entry.get('kimi_bin')}` ({entry.get('kimi_version')})",
                f"- Run directory: `{entry.get('run_dir')}`",
                f"- Evidence directory: `{entry.get('evidence_dir')}`",
                "",
                "| Checkpoint | Phase | Last turn | Source | Channel | Terminal gaps | Secret-free |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for checkpoint in entry.get("checkpoints", []):
            lines.append(
                f"| {checkpoint.get('label')} | {checkpoint.get('phase')} | "
                f"{checkpoint.get('last_turn_result')} | {checkpoint.get('last_turn_source')} | "
                f"{checkpoint.get('channel_state')} | {checkpoint.get('terminal_gaps')} | "
                f"{checkpoint.get('secret_free')} |"
            )
        lines.append("")
    (run_root / "QUALIFICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the requested qualification scenarios."""

    parser = argparse.ArgumentParser(
        description="Manual live Kimi hook-observation smoke through the managed launch path."
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
        help="External private parent for unique scenario runs.",
    )
    parser.add_argument(
        "--kimi-bin",
        default=None,
        help="Kimi binary override (use for the side-by-side floor install).",
    )
    parser.add_argument("--auth-bundle", required=True)
    parser.add_argument("--auth-root", type=Path)
    args = parser.parse_args(argv)

    if shutil.which("tmux") is None:
        raise ScenarioFailure("tmux not found on PATH")
    run_root = external_root("run", override=args.run_root, create=True)

    try:
        bundle = _ensure_bundle(
            run_root,
            bundle_path(external_root("auth", override=args.auth_root), "kimi", args.auth_bundle),
        )
        kimi_bin, kimi_version = _resolve_kimi_bin(args.kimi_bin)
    except ScenarioFailure as exc:
        stamp = _utc_stamp()
        _write_json(
            run_root / f"gap-{stamp}.json",
            {
                "status": "GAP",
                "reason": str(exc),
                "scenario": args.scenario,
                "recorded_at_utc": _utc_now(),
            },
        )
        print(f"[preflight] GAP {exc}", flush=True)
        return 2

    secrets = _secret_values(bundle)
    stamp = _utc_stamp()
    names = list(ALL_ORDER) if args.scenario == "all" else [args.scenario]
    reports: list[dict[str, Any]] = []
    for name in names:
        print(f"[{name}] starting", flush=True)
        report = _run_scenario(
            name,
            run_root=run_root,
            kimi_bin=kimi_bin,
            kimi_version=kimi_version,
            bundle=bundle,
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
        "kimi_bin": str(kimi_bin),
        "kimi_version": kimi_version,
        "bundle_lane": bundle.lane,
        "reports": reports,
    }
    summary_path = run_root / f"summary-{stamp}.json"
    _write_json(summary_path, summary)
    _update_ledger(run_root, reports, stamp=stamp, bundle=bundle)
    print(json.dumps({"summary": str(summary_path)}, indent=2))
    return 0 if all(report["status"] == "PASS" for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
