#!/usr/bin/env python3
"""Instructional harness helper for the managed Hermes verification suite.

Wraps maintained ``houmao-mgr`` commands, read-only native-home and artifact
inspection, redaction audits, local filesystem (``offline``) mailbox workflows,
and optional Stalwart JMAP (``online``) shared-service provisioning and
observation. Never starts, stops, resets, or reconfigures external model or
Stalwart services, and never prints credential contents.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import closing
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any
import urllib.error
import urllib.request

import yaml

from houmao.mailbox import resolve_active_mailbox_local_sqlite_path
from houmao.mailbox.stalwart import (
    StalwartError,
    StalwartJmapClient,
    StalwartManagementClient,
    build_stalwart_credential_ref,
    ensure_stalwart_mailbox,
    jmap_origin,
    normalize_jmap_origins,
    runtime_stalwart_credential_path,
)
from houmao.mailbox.stalwart_models import JmapMetadataQuery

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_SCRIPT = REPO_ROOT / "scripts/agents/test-fixtures/fixture.py"
DEFAULT_MANAGER = REPO_ROOT / ".pixi/envs/default/bin/houmao-mgr"
_TMUX_ENV_KEYS = ("TMUX", "TMUX_PANE", "TMUX_TMPDIR")
_STATIC_SECRET_MARKERS = (
    "ws://127.0.0.1",
    "wss://127.0.0.1",
    "hermes-gateway-ticket.",
)


class LabError(RuntimeError):
    """Report one actionable, secret-free harness failure."""


def utc_now() -> str:
    """Return a compact UTC timestamp for run artifacts."""

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def manager_path() -> Path:
    """Resolve the selected ``houmao-mgr`` executable."""

    configured = os.environ.get("HOUMAO_MGR")
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path
        raise LabError(f"HOUMAO_MGR is not a file: {path}")
    if DEFAULT_MANAGER.is_file():
        return DEFAULT_MANAGER
    found = shutil.which("houmao-mgr")
    if found:
        return Path(found)
    raise LabError("Set HOUMAO_MGR to the workspace houmao-mgr executable.")


def run_env(run_dir: Path, *, mailbox_root: Path | None = None) -> dict[str, str]:
    """Build an isolated manager environment for one fixture run."""

    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("HOUMAO_") and key not in _TMUX_ENV_KEYS
    }
    env.update(
        {
            "HOUMAO_GLOBAL_REGISTRY_DIR": str(run_dir / "registry"),
            "HOUMAO_GLOBAL_RUNTIME_DIR": str(run_dir / "runtime"),
            "HOUMAO_PROJECT_OVERLAY_DIR": str(run_dir / "workdir/.houmao"),
            "HOUMAO_GLOBAL_MAILBOX_DIR": str(
                mailbox_root.resolve()
                if mailbox_root is not None
                else (run_dir / "workdir/.houmao/mailbox")
            ),
            "HOUMAO_CLI_PRINT_STYLE": "json",
        }
    )
    return env


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    """Read one JSON object from disk with a descriptive error label."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LabError(f"Cannot read {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LabError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise LabError(f"{label} must be a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    """Write one owner-private JSON file atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        try:
            temporary.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            temporary.flush()
            os.chmod(temporary.name, mode)
            Path(temporary.name).replace(path)
        finally:
            Path(temporary.name).unlink(missing_ok=True)


def load_run(run_dir: Path, *, require_launched: bool = True) -> dict[str, Any]:
    """Load one fixture ``run.json`` and optionally require a launched agent ID."""

    payload = read_json(run_dir / "run.json", label="fixture run")
    if require_launched:
        identity = payload.get("identity")
        if not isinstance(identity, dict) or not identity.get("agent_id"):
            raise LabError(f"Fixture run is not launched: {run_dir}")
    return payload


def manager_call(
    env: dict[str, str], arguments: list[str], *, allow_error: bool = False
) -> dict[str, Any]:
    """Run ``houmao-mgr --print-json`` and return parsed output or structured failure."""

    command = [str(manager_path()), "--print-json", *arguments]
    result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    parsed: Any = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed = None
    if result.returncode != 0:
        if allow_error:
            return {
                "ok": False,
                "returncode": result.returncode,
                "stdout": parsed if parsed is not None else result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "no output"
        raise LabError(f"houmao-mgr failed (exit {result.returncode}): {message}")
    if not isinstance(parsed, dict):
        raise LabError("houmao-mgr did not return a JSON object")
    return parsed


def _pid_alive(pid: int | None) -> bool:
    """Return whether a process ID currently exists on this host."""

    if not isinstance(pid, int) or pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _proc_start_time(pid: int | None) -> int | None:
    """Read Linux ``/proc/<pid>/stat`` start time ticks if the process is alive."""

    if not isinstance(pid, int) or pid <= 1:
        return None
    try:
        stat_text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = stat_text.rsplit(")", 1)[1].split()
        return int(fields[19])
    except (OSError, IndexError, ValueError):
        return None


def _resolve_manifest(run: dict[str, Any]) -> tuple[Path | None, dict[str, Any]]:
    """Load the runtime session manifest referenced by a launched fixture run."""

    identity = run.get("identity")
    if not isinstance(identity, dict) or not isinstance(identity.get("manifest_path"), str):
        return None, {}
    path = Path(identity["manifest_path"])
    if not path.is_file():
        return path, {}
    return path, read_json(path, label="session manifest")


def _resolve_managed_home(run_dir: Path, run: dict[str, Any], manifest: dict[str, Any]) -> Path:
    """Locate the actual managed launch home (distinct from the preview home)."""

    launch_plan = manifest.get("launch_plan")
    if isinstance(launch_plan, dict) and isinstance(launch_plan.get("home_path"), str):
        return Path(launch_plan["home_path"])
    homes_dir = run_dir / "runtime/homes"
    if homes_dir.is_dir():
        candidates = sorted(path for path in homes_dir.iterdir() if path.is_dir())
        if len(candidates) == 1:
            return candidates[0]
    return Path(str(run["home_path"]))


def _read_yaml_file(path: Path) -> dict[str, Any] | None:
    """Read one YAML mapping if present."""

    if not path.is_file():
        return None
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def _inspect_single_run(run_dir: Path) -> dict[str, Any]:
    """Collect a secret-free second-view snapshot of one launched Hermes run."""

    run = load_run(run_dir)
    manifest_path, manifest = _resolve_manifest(run)
    managed_home = _resolve_managed_home(run_dir, run, manifest)
    config = _read_yaml_file(managed_home / "config.yaml")
    skills_dir = managed_home / "skills"
    skills = (
        sorted(p.name for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []
    )
    brain_manifests = sorted((run_dir / "runtime/manifests").glob("*.yaml"))
    reasoning_provenance: Any = None
    if brain_manifests:
        bm = _read_yaml_file(brain_manifests[-1]) or {}
        launch_contract = bm.get("launch_contract", {})
        ms = launch_contract.get("model_selection") if isinstance(launch_contract, dict) else None
        if isinstance(ms, dict):
            np = ms.get("native_projection")
            if isinstance(np, dict):
                reasoning_provenance = np.get("reasoning")

    daemon_files = sorted((run_dir / "runtime").rglob("hermes-daemon.json"))
    daemon_records: list[dict[str, Any]] = []
    for path in daemon_files:
        record = read_json(path, label="hermes-daemon.json")
        pid = record.get("pid")
        daemon_records.append(
            {
                "path": str(path),
                "home": record.get("home"),
                "workspace": record.get("workspace"),
                "pid": pid,
                "pid_alive": _pid_alive(pid),
                "proc_start_time": _proc_start_time(pid),
                "birth_token": record.get("birth_token"),
                "instance_id": record.get("instance_id"),
                "authority_epoch": record.get("authority_epoch"),
            }
        )

    acp_bindings = [
        read_json(path, label="hermes-acp-binding.json")
        for path in sorted((run_dir / "runtime").rglob("hermes-acp-binding.json"))
    ]
    tui_admissions: list[dict[str, Any]] = []
    for path in sorted((run_dir / "runtime").rglob("hermes-native-admission.json")):
        rec = read_json(path, label="hermes-native-admission.json")
        tui_admissions.append(
            {
                "path": str(path),
                "request_id": rec.get("request_id"),
                "native_session_id": rec.get("native_session_id"),
                "daemon_instance_id": rec.get("daemon_instance_id"),
                "native_admission_id": rec.get("native_admission_id"),
                "native_admission_sequence": rec.get("native_admission_sequence"),
                "native_authority_epoch": rec.get("native_authority_epoch"),
                "native_execution_generation": rec.get("native_execution_generation"),
                "status": rec.get("status"),
                "native_outcome": rec.get("native_outcome"),
                "replay_gap": rec.get("replay_gap"),
            }
        )

    headless_turns: list[dict[str, Any]] = []
    for path in sorted((run_dir / "runtime").rglob("hermes-request.json")):
        turn_dir = path.parent
        req = read_json(path, label="hermes-request.json")
        exitcode_path = turn_dir / "exitcode"
        exitcode = (
            int(exitcode_path.read_text(encoding="ascii").strip())
            if exitcode_path.is_file()
            else None
        )
        stdout_path = turn_dir / "stdout.jsonl"
        stderr_path = turn_dir / "stderr.log"
        result_frame: dict[str, Any] | None = None
        if stdout_path.is_file():
            for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    frame = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(frame, dict) and frame.get("type") == "result":
                    result_frame = {
                        "session_id": frame.get("session_id"),
                        "exit_code": frame.get("exit_code"),
                        "error": frame.get("error"),
                        "replay_gap": frame.get("replay_gap"),
                        "text_length": len(frame.get("text", ""))
                        if isinstance(frame.get("text"), str)
                        else 0,
                    }
        headless_turns.append(
            {
                "turn_id": req.get("turn_id"),
                "turn_index": req.get("turn_index"),
                "session_id": req.get("session_id"),
                "exitcode": exitcode,
                "stdout_exists": stdout_path.is_file(),
                "stderr_exists": stderr_path.is_file(),
                "result_frame": result_frame,
            }
        )

    return {
        "observed_at_utc": utc_now(),
        "run_dir": str(run_dir.resolve()),
        "agent_id": run["identity"]["agent_id"],
        "backend": run.get("backend"),
        "manifest_path": str(manifest_path) if manifest_path else None,
        "managed_home": str(managed_home),
        "config_yaml": config,
        "soul_md_present": (managed_home / "SOUL.md").is_file(),
        "projected_skills": skills,
        "reasoning_provenance": reasoning_provenance,
        "daemons": daemon_records,
        "acp_bindings": acp_bindings,
        "tui_admissions": tui_admissions,
        "headless_turns": headless_turns,
    }


def _private_file(path: Path, *, label: str) -> Path:
    """Require an existing regular file with owner-only permissions."""

    resolved = path.resolve()
    if not resolved.is_file():
        raise LabError(f"{label} is not a file: {resolved}")
    info = resolved.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise LabError(f"{label} needs mode 0600 (owner-only): {resolved}")
    return resolved


def _load_mail_config(path: Path, *, require_accounts: bool = True) -> dict[str, Any]:
    """Load owner-private Stalwart service or provisioned-account config."""

    resolved = _private_file(path, label="Mail service config")
    config = read_json(resolved, label="mail service config")
    endpoint = config.get("jmap_url")
    if not isinstance(endpoint, str):
        raise LabError("Mail service config requires jmap_url.")
    jmap_origin(endpoint)
    origins = config.get("trusted_jmap_origins", [])
    if not isinstance(origins, list) or not all(isinstance(o, str) for o in origins):
        raise LabError("trusted_jmap_origins must be a list of origin strings.")
    config["trusted_jmap_origins"] = list(normalize_jmap_origins(origins))
    if config.get("admin_credential_file") is not None:
        if not isinstance(config.get("management_url"), str):
            raise LabError("management_url is required when admin_credential_file is set.")
        jmap_origin(config["management_url"])
        admin_path = Path(str(config["admin_credential_file"])).expanduser()
        config["admin_credential_file"] = str(
            _private_file(resolved.parent / admin_path, label="Admin credential")
        )
    if require_accounts:
        accounts = config.get("accounts")
        if not isinstance(accounts, dict):
            raise LabError("Mail config requires accounts a and b.")
        for role in ("a", "b"):
            acct = accounts.get(role)
            if not isinstance(acct, dict) or not all(
                isinstance(acct.get(k), str) and acct[k] for k in ("login", "address")
            ):
                raise LabError(f"Account {role} requires login, address, and credential_file.")
            cred_path = Path(str(acct.get("credential_file", ""))).expanduser()
            acct["credential_file"] = str(
                _private_file(resolved.parent / cred_path, label=f"Account {role} credential")
            )
    return config


def _admin_headers(mail: dict[str, Any]) -> dict[str, str]:
    """Build HTTP Basic authorization headers for Stalwart management."""

    source = mail.get("admin_credential_file")
    if not source:
        raise LabError("Stalwart provisioning requires admin_credential_file.")
    admin = read_json(Path(source), label="admin credential")
    if not all(isinstance(admin.get(k), str) and admin[k] for k in ("user", "password")):
        raise LabError("Admin credential requires nonempty user and password.")
    token = base64.b64encode(f"{admin['user']}:{admin['password']}".encode()).decode("ascii")
    return {"Accept": "application/json", "Authorization": f"Basic {token}"}


def _jmap_client(mail: dict[str, Any], role: str) -> StalwartJmapClient:
    """Create a Stalwart JMAP client for role ``a`` or ``b``."""

    acct = mail["accounts"][role]
    return StalwartJmapClient(
        jmap_url=mail["jmap_url"],
        login_identity=acct["login"],
        credential_file=Path(acct["credential_file"]),
        timeout_seconds=15.0,
        sender_address=acct["address"],
        account_id=acct.get("account_id"),
        identity_id=acct.get("identity_id"),
        allowed_api_origins=tuple(mail["trusted_jmap_origins"]),
        api_origin=acct.get("api_origin"),
    )


def _http_status(url: str) -> int:
    """Return the HTTP status code for a read-only liveness probe."""

    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LabError(f"Cannot reach {url}: {exc}") from exc


def cmd_doctor(args: argparse.Namespace) -> None:
    """Verify checkout, Hermes binary, managed agent health, reasoning config, and mail."""

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    mgr_ver = subprocess.run(
        [str(manager_path()), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    hermes_path = shutil.which("hermes")
    if not hermes_path:
        raise LabError("`hermes` is not on PATH.")
    hermes_ver = subprocess.run(
        [hermes_path, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()

    report: dict[str, Any] = {
        "observed_at_utc": utc_now(),
        "repo_head": head,
        "houmao_mgr": str(manager_path()),
        "houmao_mgr_version": mgr_ver,
        "hermes_executable": hermes_path,
        "hermes_version": hermes_ver,
        "runs": {},
    }
    failures: list[str] = []
    mailbox_root = Path(args.mailbox_root).resolve() if args.mailbox_root else None

    for item in args.run_dir:
        run_dir = Path(item).resolve()
        snap = _inspect_single_run(run_dir)
        agent_id = snap["agent_id"]
        env = run_env(run_dir, mailbox_root=mailbox_root)
        state = manager_call(env, ["agents", "single", "--agent-id", agent_id, "state"])
        gateway = manager_call(
            env, ["agents", "single", "--agent-id", agent_id, "gateway", "status"], allow_error=True
        )
        cfg = snap.get("config_yaml") or {}
        agent_cfg = cfg.get("agent") if isinstance(cfg, dict) else {}
        actual_effort = agent_cfg.get("reasoning_effort") if isinstance(agent_cfg, dict) else None
        disabled = agent_cfg.get("disabled_toolsets") if isinstance(agent_cfg, dict) else None
        if args.expected_effort and actual_effort != args.expected_effort:
            failures.append(
                f"{run_dir.name}: expected agent.reasoning_effort={args.expected_effort!r}, "
                f"got {actual_effort!r}"
            )
        if disabled != ["browser", "computer_use"]:
            failures.append(f"{run_dir.name}: unexpected disabled_toolsets={disabled!r}")
        if state.get("availability") != "available":
            failures.append(f"{run_dir.name}: availability={state.get('availability')!r}")
        if not any(d["pid_alive"] for d in snap["daemons"]):
            failures.append(f"{run_dir.name}: no live verified Hermes daemon recorded")
        if mailbox_root is not None:
            offline = manager_call(
                env, ["agents", "single", "--agent-id", agent_id, "mailbox", "offline", "status"]
            )
            snap["offline_mailbox"] = offline
        report["runs"][run_dir.name] = {
            "snapshot": snap,
            "state": state,
            "gateway": gateway,
        }

    if args.mail_config:
        mail = _load_mail_config(Path(args.mail_config), require_accounts=True)
        jmap_status = _http_status(mail["jmap_url"])
        accounts_check: dict[str, Any] = {}
        for role in ("a", "b"):
            client = _jmap_client(mail, role)
            account_id = client.primary_account_id()
            page = client.query_metadata_page(
                query=JmapMetadataQuery(
                    box="inbox", read_state="any", answered_state="any", archived=False, since=None
                ),
                limit=10,
            )
            accounts_check[role] = {
                "address": mail["accounts"][role]["address"],
                "account_id": account_id,
                "inbox_count": len(page.messages),
            }
        report["stalwart"] = {"jmap_http_status": jmap_status, "accounts": accounts_check}

    report["healthy"] = not failures
    report["failures"] = failures
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        raise LabError("; ".join(failures))


def cmd_inspect_home(args: argparse.Namespace) -> None:
    """Print the read-only second-view snapshot for one launched Hermes run."""

    print(json.dumps(_inspect_single_run(Path(args.run_dir).resolve()), indent=2, sort_keys=True))


def cmd_state(args: argparse.Namespace) -> None:
    """Query ``houmao-mgr`` state and gateway status for one run."""

    run_dir = Path(args.run_dir).resolve()
    run = load_run(run_dir)
    agent_id = run["identity"]["agent_id"]
    mailbox_root = Path(args.mailbox_root).resolve() if args.mailbox_root else None
    env = run_env(run_dir, mailbox_root=mailbox_root)
    payload = {
        "observed_at_utc": utc_now(),
        "agent_id": agent_id,
        "state": manager_call(env, ["agents", "single", "--agent-id", agent_id, "state"]),
        "gateway": manager_call(
            env,
            ["agents", "single", "--agent-id", agent_id, "gateway", "status"],
            allow_error=True,
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_manager(args: argparse.Namespace) -> None:
    """Execute an arbitrary ``agents single --agent-id <id> ...`` command in run env."""

    run_dir = Path(args.run_dir).resolve()
    run = load_run(run_dir)
    agent_id = run["identity"]["agent_id"]
    mailbox_root = Path(args.mailbox_root).resolve() if args.mailbox_root else None
    env = run_env(run_dir, mailbox_root=mailbox_root)
    extra = list(args.mgr_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    payload = manager_call(
        env,
        ["agents", "single", "--agent-id", agent_id, *extra],
        allow_error=args.allow_error,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_audit_redaction(args: argparse.Namespace) -> None:
    """Verify public evidence files contain zero credentials, WS origins, or native tickets."""

    run_dir = Path(args.run_dir).resolve()
    priv = read_json(run_dir / "private-env.json", label="private-env.json")
    api_key = priv.get("HERMES_MANAGED_API_KEY", "")
    markers: list[tuple[str, str]] = [(m, m) for m in _STATIC_SECRET_MARKERS]
    if isinstance(api_key, str) and api_key:
        markers.append(("HERMES_MANAGED_API_KEY", api_key))

    findings: list[dict[str, str]] = []
    scanned: list[str] = []
    for raw_target in args.paths:
        target = Path(raw_target)
        files = sorted(p for p in target.rglob("*") if p.is_file()) if target.is_dir() else [target]
        for file_path in files:
            if file_path.name == "private-env.json":
                continue
            scanned.append(str(file_path))
            text = file_path.read_text(encoding="utf-8", errors="replace")
            for label, needle in markers:
                if needle in text:
                    findings.append({"file": str(file_path), "marker": label})
    result = {
        "observed_at_utc": utc_now(),
        "scanned_count": len(scanned),
        "leak_count": len(findings),
        "findings": findings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if findings:
        raise LabError(f"Redaction audit failed with {len(findings)} leak(s).")


def cmd_offline_setup(args: argparse.Namespace) -> None:
    """Initialize a shared run-local filesystem mailbox and join one or more runs."""

    mailbox_root = Path(args.mailbox_root).resolve()
    mailbox_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    initialized: dict[str, Any] = {}
    joined: dict[str, Any] = {}
    for spec in args.binding:
        run_raw, address = spec.split("=", 1)
        run_dir = Path(run_raw).resolve()
        run = load_run(run_dir)
        agent_id = run["identity"]["agent_id"]
        env = run_env(run_dir, mailbox_root=mailbox_root)
        registry = env["HOUMAO_GLOBAL_REGISTRY_DIR"]
        if registry not in initialized:
            initialized[registry] = manager_call(env, ["mailbox", "init"])
        status = manager_call(
            env, ["agents", "single", "--agent-id", agent_id, "mailbox", "offline", "status"]
        )
        if not status.get("registered"):
            status = manager_call(
                env,
                [
                    "agents",
                    "single",
                    "--agent-id",
                    agent_id,
                    "mailbox",
                    "offline",
                    "join",
                    "--mailbox-root",
                    str(mailbox_root),
                    "--address",
                    address,
                ],
            )
        joined[address] = {"run_dir": str(run_dir), "agent_id": agent_id, "status": status}
    print(
        json.dumps(
            {"mailbox_root": str(mailbox_root), "init": initialized, "bindings": joined},
            indent=2,
            sort_keys=True,
        )
    )


def _offline_sqlite_thread_summary(mailbox_root: Path, address: str) -> list[dict[str, Any]]:
    """Read recipient-local SQLite thread unread summaries for independent verification."""

    db_path = resolve_active_mailbox_local_sqlite_path(mailbox_root, address=address)
    try:
        with closing(sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            return [
                {"db": str(db_path), "table": "thread_summaries", "row": dict(row)}
                for row in conn.execute("SELECT * FROM thread_summaries ORDER BY thread_id")
            ]
    except sqlite3.Error as exc:
        raise LabError(f"Cannot read thread summaries for {address}: {exc}") from exc


def cmd_offline_observe(args: argparse.Namespace) -> None:
    """Inspect a local filesystem mailbox address via ``houmao-mgr`` and SQLite summaries."""

    mailbox_root = Path(args.mailbox_root).resolve()
    run_dir = Path(args.run_dir).resolve()
    env = run_env(run_dir, mailbox_root=mailbox_root)
    listed = manager_call(
        env,
        [
            "mailbox",
            "messages",
            "list",
            "--mailbox-root",
            str(mailbox_root),
            "--address",
            args.address,
        ],
    )
    payload = {
        "observed_at_utc": utc_now(),
        "mailbox_root": str(mailbox_root),
        "address": args.address,
        "messages": listed,
        "thread_summaries": _offline_sqlite_thread_summary(mailbox_root, args.address),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_offline_wait(args: argparse.Namespace) -> None:
    """Wait until a matching message appears (or clears from inbox) in the offline store."""

    mailbox_root = Path(args.mailbox_root).resolve()
    run_dir = Path(args.run_dir).resolve()
    env = run_env(run_dir, mailbox_root=mailbox_root)
    deadline = time.monotonic() + args.timeout
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        listed = manager_call(
            env,
            [
                "mailbox",
                "messages",
                "list",
                "--mailbox-root",
                str(mailbox_root),
                "--address",
                args.address,
            ],
        )
        items = listed.get("messages") or listed.get("items") or []
        matching = [
            m
            for m in items
            if isinstance(m, dict)
            and args.tag in str(m.get("subject", ""))
            and (args.box is None or str(m.get("box", m.get("folder", ""))).lower() == args.box)
        ]
        last_payload = {
            "observed_at_utc": utc_now(),
            "address": args.address,
            "tag": args.tag,
            "box": args.box,
            "matching": matching,
            "thread_summaries": _offline_sqlite_thread_summary(mailbox_root, args.address),
        }
        if args.expect_absent and not matching:
            print(json.dumps(last_payload, indent=2, sort_keys=True))
            return
        if not args.expect_absent and matching:
            print(json.dumps(last_payload, indent=2, sort_keys=True))
            return
        time.sleep(2.0)
    print(json.dumps(last_payload, indent=2, sort_keys=True))
    raise LabError(
        f"Timed out waiting for tag={args.tag!r} (box={args.box!r}, "
        f"expect_absent={args.expect_absent}) on {args.address}"
    )


def cmd_notifier(args: argparse.Namespace) -> None:
    """Configure or inspect ``gateway mail-notifier`` on ``offline`` or ``online``."""

    run_dir = Path(args.run_dir).resolve()
    run = load_run(run_dir)
    agent_id = run["identity"]["agent_id"]
    mailbox_root = Path(args.mailbox_root).resolve() if args.mailbox_root else None
    env = run_env(run_dir, mailbox_root=mailbox_root)
    cmd = [
        "agents",
        "single",
        "--agent-id",
        agent_id,
        "gateway",
        "mail-notifier",
        args.action,
        "--channel",
        args.channel,
    ]
    if args.action == "enable":
        cmd.extend(["--interval-seconds", str(args.interval_seconds), "--mode", args.mode])
        if args.appendix_text is not None:
            cmd.extend(["--appendix-text", args.appendix_text])
        if args.pre_notification_context_action is not None:
            cmd.extend(["--pre-notification-context-action", args.pre_notification_context_action])
    payload = manager_call(env, cmd, allow_error=args.allow_error)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _stalwart_deprovision_impl(mail: dict[str, Any]) -> dict[str, Any]:
    """Delete confirmed or pending run-owned Stalwart principals and verify absence."""

    confirmed = mail.get("provisioned_accounts") or []
    pending = mail.get("pending_accounts") or []
    if not confirmed and not pending:
        return {"status": "skipped", "reason": "no provisioned accounts", "verified_absent": True}
    management = StalwartManagementClient(
        base_url=mail["management_url"], auth_headers=_admin_headers(mail)
    )
    index = {
        p["name"].casefold(): p
        for p in management.list_principals(types=("individual",))
        if isinstance(p.get("name"), str)
    }
    results: dict[str, Any] = {}
    for entry in [*confirmed, *pending]:
        name = entry["name"]
        address = entry["address"].lower()
        found = index.get(name.casefold())
        if found is None:
            results[name] = {"status": "already-absent"}
            continue
        emails = found.get("emails")
        expected_id = entry.get("principal_id")
        if (
            not isinstance(emails, list)
            or [str(e).lower() for e in emails] != [address]
            or (expected_id is not None and str(found.get("id")) != str(expected_id))
        ):
            raise LabError(f"Refusing to delete Stalwart principal {name}: ownership mismatch.")
        management.delete_mailbox_account(name=found["name"], provider_id=str(found["id"]))
        results[name] = {"status": "deleted", "address": address}
    after = {
        p["name"].casefold()
        for p in management.list_principals(types=("individual",))
        if isinstance(p.get("name"), str)
    }
    remaining = [e["name"] for e in [*confirmed, *pending] if e["name"].casefold() in after]
    return {
        "observed_at_utc": utc_now(),
        "deleted": results,
        "verified_absent": not remaining,
        "remaining": remaining,
    }


def cmd_stalwart_provision(args: argparse.Namespace) -> None:
    """Provision two run-owned Stalwart accounts using Houmao's product provisioner."""

    service = _load_mail_config(Path(args.mail_config), require_accounts=False)
    admin_headers = _admin_headers(service)
    management = StalwartManagementClient(
        base_url=service["management_url"], auth_headers=admin_headers
    )
    domain = args.domain.strip().lower()
    prefix = args.prefix.strip()
    output_path = Path(args.output_config).resolve()
    if output_path.exists():
        raise LabError("Output config already exists; choose a fresh path.")

    existing = {
        p["name"].casefold()
        for p in management.list_principals(types=("individual",))
        if isinstance(p.get("name"), str)
    }
    names = {role: f"{prefix}-{role}" for role in ("a", "b")}
    if any(name.casefold() in existing for name in names.values()):
        raise LabError("Select a unique prefix for the run-owned Stalwart accounts.")
    domain_present = any(
        p.get("name") == domain for p in management.list_principals(types=("domain",))
    )

    runtime_root = Path(args.accounts_dir).resolve()
    runtime_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(runtime_root, 0o700)

    output_payload: dict[str, Any] = {
        "jmap_url": service["jmap_url"],
        "management_url": service["management_url"],
        "admin_credential_file": service["admin_credential_file"],
        "trusted_jmap_origins": service["trusted_jmap_origins"],
        "domain": domain,
        "domain_created": not domain_present,
        "prefix": prefix,
        "accounts": {},
        "provisioned_accounts": [],
        "pending_accounts": [],
    }
    write_json(output_path, output_payload, mode=0o600)
    try:
        for role, name in names.items():
            address = f"{name.lower()}@{domain}"
            cred_ref = build_stalwart_credential_ref(address=address, jmap_url=service["jmap_url"])
            output_payload["pending_accounts"] = [
                {
                    "name": name,
                    "address": address,
                    "credential_file": str(
                        runtime_stalwart_credential_path(runtime_root, cred_ref)
                    ),
                }
            ]
            write_json(output_path, output_payload, mode=0o600)
            binding = ensure_stalwart_mailbox(
                runtime_root=runtime_root,
                session_root=runtime_root / role,
                principal_id=name,
                address=address,
                jmap_url=service["jmap_url"],
                management_url=service["management_url"],
                trusted_jmap_origins=tuple(service["trusted_jmap_origins"]),
                allow_create_domain=not args.require_existing_domain,
                management_auth_headers=admin_headers,
            )
            output_payload["provisioned_accounts"].append(
                {
                    "role": role,
                    "name": binding.principal_name,
                    "address": address,
                    "principal_id": binding.management_principal_id,
                }
            )
            output_payload["pending_accounts"] = []
            output_payload["accounts"][role] = {
                "login": binding.login_identity,
                "address": address,
                "credential_file": str(binding.credential_file),
                "account_id": binding.account_id,
                "identity_id": binding.identity_id,
                "api_origin": binding.api_origin,
                "mailbox_roles": dict(binding.mailbox_roles),
            }
            write_json(output_path, output_payload, mode=0o600)
    except (LabError, OSError, StalwartError):
        _stalwart_deprovision_impl(output_payload)
        raise

    print(
        json.dumps(
            {
                "output_config": str(output_path),
                "domain": domain,
                "domain_created": output_payload["domain_created"],
                "accounts": {
                    role: {k: v for k, v in info.items() if k != "credential_file"}
                    for role, info in output_payload["accounts"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


def cmd_stalwart_attach(args: argparse.Namespace) -> None:
    """Attach a provisioned Stalwart account to one managed Hermes agent."""

    mail = _load_mail_config(Path(args.mail_config), require_accounts=True)
    acct = mail["accounts"][args.role]
    run_dir = Path(args.run_dir).resolve()
    run = load_run(run_dir)
    agent_id = run["identity"]["agent_id"]
    mailbox_root = Path(args.mailbox_root).resolve() if args.mailbox_root else None
    env = run_env(run_dir, mailbox_root=mailbox_root)
    cmd = [
        "agents",
        "single",
        "--agent-id",
        agent_id,
        "mailbox",
        "online",
        "attach",
        "--provider",
        "stalwart",
        "--address",
        acct["address"],
        "--login-identity",
        acct["login"],
        "--credential-source",
        acct["credential_file"],
        "--jmap-url",
        mail["jmap_url"],
    ]
    if acct.get("account_id"):
        cmd.extend(["--account-id", acct["account_id"]])
    for origin in mail["trusted_jmap_origins"]:
        cmd.extend(["--trust-jmap-origin", origin])
    result = manager_call(env, cmd)
    print(json.dumps(result, indent=2, sort_keys=True))


def cmd_stalwart_peer_send(args: argparse.Namespace) -> None:
    """Send one real JMAP message directly from one provisioned account to the other."""

    mail = _load_mail_config(Path(args.mail_config), require_accounts=True)
    sender = _jmap_client(mail, args.sender)
    sender_addr = str(mail["accounts"][args.sender]["address"])
    recipient_addr = str(mail["accounts"][args.recipient]["address"])
    subject = f"[{args.tag}] {args.subject}" if args.tag else args.subject
    receipt = sender.send(
        sender_address=sender_addr,
        to_addresses=[recipient_addr],
        cc_addresses=[],
        subject=subject,
        body_content=args.body,
        attachments=[],
    )
    print(
        json.dumps(
            {
                "observed_at_utc": utc_now(),
                "sender": sender_addr,
                "recipient": recipient_addr,
                "subject": subject,
                "id": receipt.get("id"),
                "messageId": receipt.get("messageId"),
                "threadId": receipt.get("threadId"),
                "mutation_receipt": receipt.get("mutation_receipt"),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _jmap_messages_matching(
    mail: dict[str, Any], role: str, *, box: str, tag: str
) -> list[dict[str, Any]]:
    """Query Stalwart JMAP for messages matching ``tag`` in ``box``."""

    client = _jmap_client(mail, role)
    page = client.query_metadata_page(
        query=JmapMetadataQuery(
            box=box,
            read_state="any",
            answered_state="any",
            archived=(box == "archive"),
            since=None,
        ),
        limit=50,
    )
    matches: list[dict[str, Any]] = []
    for msg in page.messages:
        subject = str(msg.get("subject") or "")
        if tag and tag not in subject:
            continue
        matches.append(
            {
                "id": msg.get("id"),
                "threadId": msg.get("threadId"),
                "messageId": msg.get("messageId"),
                "subject": subject,
                "from": msg.get("from"),
                "to": msg.get("to"),
                "read": msg.get("read"),
                "answered": msg.get("answered"),
                "archived": msg.get("archived"),
                "inReplyTo": msg.get("inReplyTo"),
                "references": msg.get("references"),
                "preview": msg.get("preview"),
                "box": box,
            }
        )
    return matches


def cmd_stalwart_observe(args: argparse.Namespace) -> None:
    """Read provider-side Stalwart mailbox state via JMAP."""

    mail = _load_mail_config(Path(args.mail_config), require_accounts=True)
    matches = _jmap_messages_matching(mail, args.role, box=args.box, tag=args.tag or "")
    print(
        json.dumps(
            {
                "observed_at_utc": utc_now(),
                "role": args.role,
                "address": mail["accounts"][args.role]["address"],
                "box": args.box,
                "tag": args.tag,
                "count": len(matches),
                "messages": matches,
            },
            indent=2,
            sort_keys=True,
        )
    )


def cmd_stalwart_content(args: argparse.Namespace) -> None:
    """Read one selected Stalwart message body via JMAP for evidence."""

    mail = _load_mail_config(Path(args.mail_config), require_accounts=True)
    client = _jmap_client(mail, args.role)
    content = client.get_content(
        email_id=args.email_id,
        max_body_value_bytes=args.max_body_value_bytes,
    )
    print(
        json.dumps(
            {
                "observed_at_utc": utc_now(),
                "role": args.role,
                "id": content.get("id"),
                "subject": content.get("subject"),
                "from": content.get("from"),
                "to": content.get("to"),
                "body": content.get("body"),
                "content_complete": content.get("content_complete"),
            },
            indent=2,
            sort_keys=True,
        )
    )


def cmd_stalwart_wait(args: argparse.Namespace) -> None:
    """Poll Stalwart JMAP until a matching message arrives or leaves the selected box."""

    mail = _load_mail_config(Path(args.mail_config), require_accounts=True)
    deadline = time.monotonic() + args.timeout
    last: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        last = _jmap_messages_matching(mail, args.role, box=args.box, tag=args.tag)
        if args.expect_absent and not last:
            print(
                json.dumps(
                    {
                        "observed_at_utc": utc_now(),
                        "role": args.role,
                        "box": args.box,
                        "tag": args.tag,
                        "count": 0,
                        "messages": [],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        if not args.expect_absent and last:
            print(
                json.dumps(
                    {
                        "observed_at_utc": utc_now(),
                        "role": args.role,
                        "box": args.box,
                        "tag": args.tag,
                        "count": len(last),
                        "messages": last,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        time.sleep(3.0)
    raise LabError(
        f"Timed out waiting on Stalwart role={args.role} box={args.box} tag={args.tag!r}"
    )


def cmd_stalwart_deprovision(args: argparse.Namespace) -> None:
    """Delete only recorded run-owned Stalwart principals and verify their absence."""

    mail = _load_mail_config(Path(args.mail_config), require_accounts=False)
    result = _stalwart_deprovision_impl(mail)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result.get("verified_absent"):
        raise LabError(f"Stalwart principals still present: {result.get('remaining')}")


def cmd_capture_transcript(args: argparse.Namespace) -> None:
    """Copy sanitized Hermes session logs and turn artifacts into an evidence directory."""

    run_dir = Path(args.run_dir).resolve()
    dest = Path(args.output).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    priv = read_json(run_dir / "private-env.json", label="private-env.json")
    api_key = priv.get("HERMES_MANAGED_API_KEY", "")
    snap = _inspect_single_run(run_dir)
    write_json(dest / "home-snapshot.json", snap, mode=0o600)

    copied: list[str] = []
    for pattern in (
        "stdout.jsonl",
        "stderr.log",
        "hermes-request.json",
        "hermes-native-admission.json",
    ):
        for src in sorted((run_dir / "runtime").rglob(pattern)):
            rel = src.relative_to(run_dir / "runtime")
            out_path = dest / "runtime-artifacts" / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            text = src.read_text(encoding="utf-8", errors="replace")
            if isinstance(api_key, str) and api_key:
                text = text.replace(api_key, "[REDACTED]")
            out_path.write_text(text, encoding="utf-8")
            copied.append(str(out_path))
    print(
        json.dumps(
            {"observed_at_utc": utc_now(), "output": str(dest), "copied_files": copied},
            indent=2,
            sort_keys=True,
        )
    )


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop recorded fixture runs, verify daemon exit, and optionally clean Stalwart accounts."""

    stopped: dict[str, Any] = {}
    for raw in args.run_dir:
        run_dir = Path(raw).resolve()
        before_daemons = [
            d["pid"] for d in _inspect_single_run(run_dir)["daemons"] if d["pid_alive"]
        ]
        env = {k: v for k, v in os.environ.items() if k not in _TMUX_ENV_KEYS}
        proc = subprocess.run(
            [sys.executable, str(FIXTURE_SCRIPT), "stop", "--run-dir", str(run_dir)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        still_alive = [pid for pid in before_daemons if _pid_alive(pid)]
        stopped[run_dir.name] = {
            "returncode": proc.returncode,
            "previous_live_daemon_pids": before_daemons,
            "surviving_daemon_pids": still_alive,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }

    stalwart_cleanup: dict[str, Any] | None = None
    if args.mail_config and not args.keep_accounts:
        mail = _load_mail_config(Path(args.mail_config), require_accounts=False)
        stalwart_cleanup = _stalwart_deprovision_impl(mail)

    evidence_files = (
        len(list(Path(args.evidence_root).rglob("*")))
        if args.evidence_root and Path(args.evidence_root).is_dir()
        else None
    )
    print(
        json.dumps(
            {
                "observed_at_utc": utc_now(),
                "stopped": stopped,
                "stalwart_cleanup": stalwart_cleanup,
                "surviving_evidence_entries": evidence_files,
            },
            indent=2,
            sort_keys=True,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ``hermes_lab.py``."""

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="Verify Hermes runs, reasoning config, and mail health.")
    p_doc.add_argument("--run-dir", action="append", default=[], help="Launched fixture run dir.")
    p_doc.add_argument(
        "--expected-effort", default="xhigh", help="Expected agent.reasoning_effort."
    )
    p_doc.add_argument("--mailbox-root", default=None, help="Shared offline mailbox root.")
    p_doc.add_argument("--mail-config", default=None, help="Provisioned Stalwart mail config JSON.")
    p_doc.set_defaults(func=cmd_doctor)

    p_ins = sub.add_parser("inspect-home", help="Inspect managed home, daemons, and artifacts.")
    p_ins.add_argument("--run-dir", required=True)
    p_ins.set_defaults(func=cmd_inspect_home)

    p_st = sub.add_parser("state", help="Read houmao-mgr agent state and gateway status.")
    p_st.add_argument("--run-dir", required=True)
    p_st.add_argument("--mailbox-root", default=None)
    p_st.set_defaults(func=cmd_state)

    p_mgr = sub.add_parser("manager", help="Run `agents single --agent-id <id> ...` in run env.")
    p_mgr.add_argument("--run-dir", required=True)
    p_mgr.add_argument("--mailbox-root", default=None)
    p_mgr.add_argument("--allow-error", action="store_true")
    p_mgr.add_argument("mgr_args", nargs=argparse.REMAINDER)
    p_mgr.set_defaults(func=cmd_manager)

    p_red = sub.add_parser("audit-redaction", help="Verify zero secret or ticket leaks in files.")
    p_red.add_argument("--run-dir", required=True)
    p_red.add_argument("paths", nargs="+")
    p_red.set_defaults(func=cmd_audit_redaction)

    p_off_s = sub.add_parser("offline-setup", help="Init local FS mailbox and join runs.")
    p_off_s.add_argument("--mailbox-root", required=True)
    p_off_s.add_argument("--binding", action="append", required=True, help="RUN_DIR=ADDRESS")
    p_off_s.set_defaults(func=cmd_offline_setup)

    p_off_o = sub.add_parser("offline-observe", help="Inspect local FS messages and SQLite state.")
    p_off_o.add_argument("--mailbox-root", required=True)
    p_off_o.add_argument("--run-dir", required=True)
    p_off_o.add_argument("--address", required=True)
    p_off_o.set_defaults(func=cmd_offline_observe)

    p_off_w = sub.add_parser("offline-wait", help="Wait for tag arrival or absence in local FS.")
    p_off_w.add_argument("--mailbox-root", required=True)
    p_off_w.add_argument("--run-dir", required=True)
    p_off_w.add_argument("--address", required=True)
    p_off_w.add_argument("--tag", required=True)
    p_off_w.add_argument("--box", default=None)
    p_off_w.add_argument("--expect-absent", action="store_true")
    p_off_w.add_argument("--timeout", type=float, default=240.0)
    p_off_w.set_defaults(func=cmd_offline_wait)

    p_not = sub.add_parser("notifier", help="Control gateway mail-notifier on offline or online.")
    p_not.add_argument("--run-dir", required=True)
    p_not.add_argument("--channel", choices=("offline", "online"), required=True)
    p_not.add_argument("--action", choices=("status", "enable", "disable"), required=True)
    p_not.add_argument("--interval-seconds", type=int, default=20)
    p_not.add_argument("--mode", choices=("any_inbox", "unread_only"), default="unread_only")
    p_not.add_argument("--appendix-text", default=None)
    p_not.add_argument(
        "--pre-notification-context-action", choices=("none", "compact"), default=None
    )
    p_not.add_argument("--mailbox-root", default=None)
    p_not.add_argument("--allow-error", action="store_true")
    p_not.set_defaults(func=cmd_notifier)

    p_sp = sub.add_parser("stalwart-provision", help="Provision two run-owned Stalwart accounts.")
    p_sp.add_argument("--mail-config", required=True)
    p_sp.add_argument("--accounts-dir", required=True)
    p_sp.add_argument("--output-config", required=True)
    p_sp.add_argument("--domain", required=True)
    p_sp.add_argument("--prefix", required=True)
    p_sp.add_argument("--require-existing-domain", action="store_true")
    p_sp.set_defaults(func=cmd_stalwart_provision)

    p_sa = sub.add_parser("stalwart-attach", help="Attach a provisioned Stalwart account.")
    p_sa.add_argument("--mail-config", required=True)
    p_sa.add_argument("--run-dir", required=True)
    p_sa.add_argument("--role", choices=("a", "b"), required=True)
    p_sa.add_argument("--mailbox-root", default=None)
    p_sa.set_defaults(func=cmd_stalwart_attach)

    p_ss = sub.add_parser("stalwart-peer-send", help="Send a direct JMAP message between accounts.")
    p_ss.add_argument("--mail-config", required=True)
    p_ss.add_argument("--sender", choices=("a", "b"), required=True)
    p_ss.add_argument("--recipient", choices=("a", "b"), required=True)
    p_ss.add_argument("--subject", required=True)
    p_ss.add_argument("--body", required=True)
    p_ss.add_argument("--tag", default="")
    p_ss.set_defaults(func=cmd_stalwart_peer_send)

    p_so = sub.add_parser("stalwart-observe", help="Read Stalwart JMAP mailbox state.")
    p_so.add_argument("--mail-config", required=True)
    p_so.add_argument("--role", choices=("a", "b"), required=True)
    p_so.add_argument("--box", default="inbox")
    p_so.add_argument("--tag", default="")
    p_so.set_defaults(func=cmd_stalwart_observe)

    p_sc = sub.add_parser("stalwart-content", help="Read one Stalwart message body via JMAP.")
    p_sc.add_argument("--mail-config", required=True)
    p_sc.add_argument("--role", choices=("a", "b"), required=True)
    p_sc.add_argument("--email-id", required=True)
    p_sc.add_argument("--max-body-value-bytes", type=int, default=65536)
    p_sc.set_defaults(func=cmd_stalwart_content)

    p_sw = sub.add_parser("stalwart-wait", help="Poll Stalwart JMAP for arrival or absence.")
    p_sw.add_argument("--mail-config", required=True)
    p_sw.add_argument("--role", choices=("a", "b"), required=True)
    p_sw.add_argument("--box", default="inbox")
    p_sw.add_argument("--tag", required=True)
    p_sw.add_argument("--expect-absent", action="store_true")
    p_sw.add_argument("--timeout", type=float, default=240.0)
    p_sw.set_defaults(func=cmd_stalwart_wait)

    p_sd = sub.add_parser("stalwart-deprovision", help="Delete run-owned Stalwart principals.")
    p_sd.add_argument("--mail-config", required=True)
    p_sd.set_defaults(func=cmd_stalwart_deprovision)

    p_cap = sub.add_parser("capture-transcript", help="Copy sanitized Hermes run artifacts.")
    p_cap.add_argument("--run-dir", required=True)
    p_cap.add_argument("--output", required=True)
    p_cap.set_defaults(func=cmd_capture_transcript)

    p_stop = sub.add_parser("stop", help="Stop recorded runs and clean Stalwart principals.")
    p_stop.add_argument("--run-dir", action="append", default=[])
    p_stop.add_argument("--mail-config", default=None)
    p_stop.add_argument("--keep-accounts", action="store_true")
    p_stop.add_argument("--evidence-root", default=None)
    p_stop.set_defaults(func=cmd_stop)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Hermes instructional test helper."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (LabError, StalwartError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
