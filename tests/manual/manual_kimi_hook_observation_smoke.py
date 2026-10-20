"""Manual live qualification for Kimi hook observation through the managed path.

This script drives real Kimi Code TUI sessions in tmux through the
realm-controller compatibility CLI (``start-session``, ``send-keys``,
``attach-gateway``, ``gateway-status``, ``stop-session``) with the Kimi hook
observation channel opted in (``HOUMAO_HOOK_OBSERVATION_KIMI=1``). It covers
the OpenSpec ``add-kimi-hook-observation`` live smoke scenarios:

- multi-turn success with hook-settled turns;
- Escape interrupt mid-generation (hook-derived ``interrupted``);
- manual compaction followed by a post-compact turn;
- provider ``kill -9`` mid-turn (presence lost, truthful unknown, terminal gap);
- the same multi-turn leg against a side-by-side floor install (``--scenario
  floor --kimi-bin <path>``).

Every scenario uses an isolated scratch ``KIMI_CODE_HOME`` under
``tmp/kimi-hook-smoke/`` seeded from the host-local auth bundle at
``tests/fixtures/auth-bundles/kimi/personal-a-default/``. When that bundle is
absent, the script creates it by copying the operator's real ``~/.kimi-code``
state at runtime, after proving with ``git check-ignore`` that the bundle path
is ignored. Credential files are copied byte-for-byte with :mod:`shutil`; this
script never prints, embeds, or logs their contents. Only file names, sizes,
and modes are recorded.

Each checkpoint writes the raw gateway status, tracked TUI state, channel
status, and event summary under the run directory. ``QUALIFICATION.md`` is
rendered from an accumulated ledger so repeated invocations (for example an
``all`` run followed by a ``floor`` run) keep every verdict.

Usage::

    pixi run python tests/manual/manual_kimi_hook_observation_smoke.py \
        --scenario multi-turn
    pixi run python tests/manual/manual_kimi_hook_observation_smoke.py --scenario all
    pixi run python tests/manual/manual_kimi_hook_observation_smoke.py \
        --scenario floor --kimi-bin tmp/kimi-floor/node_modules/.bin/kimi

The script is not part of CI. It spends real provider credit per turn; the
prompts are frozen and short.
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
AGENT_DEF_DIR = REPO_ROOT / "tests" / "fixtures" / "plain-agent-def"
DEFAULT_RUN_ROOT = REPO_ROOT / "tmp" / "kimi-hook-smoke"
KIMI_BUNDLE_DIR = REPO_ROOT / "tests" / "fixtures" / "auth-bundles" / "kimi" / "personal-a-default"
OPERATOR_KIMI_HOME = Path.home() / ".kimi-code"
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
    """Credential-bundle origin and gitignore proof, never file contents."""

    lane: str
    path: Path
    gitignore_check: dict[str, Any]
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


def _gitignore_check(path: Path) -> dict[str, Any]:
    """Return the ``git check-ignore`` verdict for one repository path."""

    try:
        relative = str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        relative = str(path.resolve())
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "-v", relative],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return {
        "path": relative,
        "command": f"git -C <repo> check-ignore -v {relative}",
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "ignored": result.returncode == 0,
    }


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


def _ensure_bundle(run_root: Path) -> BundleProvenance:
    """Resolve the credential bundle, creating the host-local copy when absent.

    The creation lane copies the operator's ``~/.kimi-code`` credential files
    byte-for-byte after proving the destination is gitignored. File contents
    are never read into Python, printed, or embedded in an artifact.
    """

    if KIMI_BUNDLE_CONFIG.is_file() and KIMI_BUNDLE_CREDENTIALS.is_file():
        provenance = BundleProvenance(
            lane="existing-host-local-bundle",
            path=KIMI_BUNDLE_DIR,
            gitignore_check=_gitignore_check(KIMI_BUNDLE_DIR),
            files=_bundle_files(KIMI_BUNDLE_DIR),
        )
        _write_bundle_provenance(run_root, provenance)
        return provenance

    source_config = OPERATOR_KIMI_HOME / "config.toml"
    source_credentials = OPERATOR_KIMI_HOME / "credentials" / "kimi-code.json"
    if not source_config.is_file() or not source_credentials.is_file():
        raise ScenarioFailure(
            "named gap: no Kimi credential source. Expected the host-local bundle at "
            f"`{KIMI_BUNDLE_DIR}` or a usable `{OPERATOR_KIMI_HOME}` with config.toml "
            "and credentials/kimi-code.json."
        )

    ignore = _gitignore_check(KIMI_BUNDLE_DIR)
    if not ignore["ignored"]:
        raise ScenarioFailure(
            "refusing to create the host-local Kimi bundle because the destination is not "
            f"gitignored: {ignore}"
        )

    (KIMI_BUNDLE_DIR / "files" / "credentials").mkdir(parents=True, exist_ok=True)
    (KIMI_BUNDLE_DIR / "env").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_config, KIMI_BUNDLE_DIR / KIMI_BUNDLE_CONFIG)
    shutil.copy2(source_credentials, KIMI_BUNDLE_DIR / KIMI_BUNDLE_CREDENTIALS)
    optional_sources = (
        (OPERATOR_KIMI_HOME / "oauth" / "kimi-code", Path("files") / "oauth" / "kimi-code"),
        (OPERATOR_KIMI_HOME / "device_id", Path("files") / "device_id"),
    )
    for source, relative in optional_sources:
        if not source.is_file():
            continue
        destination = KIMI_BUNDLE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    (KIMI_BUNDLE_DIR / KIMI_BUNDLE_ENV).write_text(
        "# Host-local Kimi auth bundle created by the hook-observation smoke.\n"
        "# Credential material lives in files/ and stays untracked.\n",
        encoding="utf-8",
    )

    provenance = BundleProvenance(
        lane="created-from-operator-home",
        path=KIMI_BUNDLE_DIR,
        gitignore_check=ignore,
        files=_bundle_files(KIMI_BUNDLE_DIR),
    )
    _write_bundle_provenance(run_root, provenance)
    return provenance


def _write_bundle_provenance(run_root: Path, provenance: BundleProvenance) -> None:
    """Write one secret-free bundle-provenance artifact."""

    payload = {
        "lane": provenance.lane,
        "path": str(provenance.path),
        "gitignore_check": provenance.gitignore_check,
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


def _prepare_run(
    *,
    scenario: Scenario,
    run_root: Path,
    kimi_bin: Path,
    kimi_version: str | None,
    bundle: BundleProvenance,
    stamp: str,
) -> RunContext:
    """Create the scratch home, env file, workdir, and brain manifest."""

    run_dir = run_root / f"{scenario.name}-{stamp}"
    workdir = run_dir / "workdir"
    kimi_home = run_dir / "kimi-home"
    evidence = run_dir / "evidence"
    for path in (workdir, kimi_home, evidence):
        path.mkdir(parents=True, exist_ok=True)
    (workdir / "README.md").write_text(S4_README_TEXT, encoding="utf-8")

    files_root = bundle.path / "files"
    for source in sorted(files_root.rglob("*")):
        if not source.is_file():
            continue
        destination = kimi_home / source.relative_to(files_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    env_file = run_dir / "vars.env"
    env_file.write_text("KIMI_SMOKE_LANE=host-local-bundle\n", encoding="utf-8")
    manifest = run_dir / "brain.yaml"
    manifest.write_text(
        "\n".join(
            [
                "schema_version: 3",
                "inputs:",
                "  tool: kimi",
                "  skills: []",
                "  setup: default",
                "  auth: default",
                "  adapter_path: /tmp/kimi-smoke-adapter.yaml",
                "  preset_path: null",
                "runtime:",
                f"  runtime_root: {run_dir}",
                f"  home_id: kimi-hook-smoke-{scenario.name}",
                f"  home_path: {kimi_home}",
                f"  launch_helper: {kimi_bin}",
                f"  launch_executable: {kimi_bin}",
                "  launch_home_selector:",
                "    env_var: KIMI_CODE_HOME",
                f"    value: {kimi_home}",
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
                "      adapter_path: /tmp/kimi-smoke-adapter.yaml",
                "      preset_path: null",
                "      preset_overrides_present: false",
                "      direct_overrides_present: false",
                "credentials:",
                f"  auth_path: {run_dir / 'auth'}",
                "  projected_files: []",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - KIMI_SMOKE_LANE",
                "launch_policy:",
                "  operator_prompt_mode: unattended",
                "",
            ]
        ),
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["HOUMAO_HOOK_OBSERVATION_KIMI"] = "1"
    env["HOUMAO_GLOBAL_REGISTRY_DIR"] = str(run_dir / "registry")

    agent_name = f"kimi-hook-{scenario.name.replace('_', '-')}-{os.getpid()}"
    return RunContext(
        scenario=scenario,
        run_dir=run_dir,
        workdir=workdir,
        kimi_home=kimi_home,
        manifest=manifest,
        env_file=env_file,
        agent_name=agent_name,
        kimi_bin=kimi_bin,
        kimi_version=kimi_version,
        bundle=bundle,
        env=env,
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
        timeout=240.0,
    )
    _write_json(ctx.run_dir / "start.json", start)
    manifest_path = Path(str(start["session_manifest"])).resolve()
    ctx.session_manifest.write_text(str(manifest_path) + "\n", encoding="utf-8")
    tmux_session = str(start.get("tmux_session_name") or "")
    if not tmux_session:
        raise ScenarioFailure("start-session did not report a tmux_session_name")

    session_root = _session_root(manifest_path)
    install = _verify_install(ctx, session_root)
    _write_json(ctx.run_dir / "install-verify.json", install)

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
            "kimi_home": str(ctx.kimi_home),
            "kimi_bin": str(ctx.kimi_bin),
            "kimi_version": ctx.kimi_version,
            "scenario": ctx.scenario.name,
            "bundle_lane": ctx.bundle.lane,
        },
    )
    _wait_for(
        lambda: _tracked_state(host, port),
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
            "gitignore_check": bundle.gitignore_check,
        },
        "entries": entries,
        "stamps": [*ledger.get("stamps", []), stamp],
    }
    _write_json(_ledger_path(run_root), ledger)
    _render_qualification(run_root, ledger)


def _render_qualification(run_root: Path, ledger: dict[str, Any]) -> None:
    """Render the secret-free ``QUALIFICATION.md`` summary from the ledger."""

    bundle = ledger.get("bundle", {})
    gitignore = bundle.get("gitignore_check", {})
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
        f"- Gitignore proof: `{gitignore.get('command', '')}` exited "
        f"{gitignore.get('exit_code')} (`{gitignore.get('stdout', '')}`)",
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
        help="Scratch root for runs and evidence (default: tmp/kimi-hook-smoke).",
    )
    parser.add_argument(
        "--kimi-bin",
        default=None,
        help="Kimi binary override (use for the side-by-side floor install).",
    )
    args = parser.parse_args(argv)

    if shutil.which("tmux") is None:
        raise ScenarioFailure("tmux not found on PATH")
    run_root = args.run_root.expanduser().resolve()
    run_root.mkdir(parents=True, exist_ok=True)

    try:
        bundle = _ensure_bundle(run_root)
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
