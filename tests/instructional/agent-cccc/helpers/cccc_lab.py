#!/usr/bin/env python3
"""Provision, inspect, and clean up a two-agent CCCC chat instructional run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MANAGER = Path.home() / ".local/share/uv/tools/houmao/bin/houmao-mgr"
DEFAULT_CCCC = Path.home() / ".local/share/uv/tools/houmao/bin/houmao-cccc"
_TMUX_ENV_KEYS = ("TMUX", "TMUX_PANE", "TMUX_TMPDIR")
_ROLES = ("a", "b")
_RECEIVER_PROTOCOL_VERSION = 2
_REQUEST_BEGIN = "<<< BEGIN CCCC REQUEST >>>"
_REQUEST_END = "<<< END CCCC REQUEST >>>"


class LabError(RuntimeError):
    """Report one actionable harness failure."""


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    """Read one JSON object without exposing its contents on failure."""
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise LabError(f"Cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise LabError(f"{label} is not a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    """Publish one owner-private JSON document atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".cccc-lab-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def manager_path() -> Path:
    """Resolve the explicitly selected manager."""
    selected = os.environ.get("HOUMAO_MGR")
    path = Path(selected).expanduser() if selected else DEFAULT_MANAGER
    if not path.is_file():
        raise LabError(f"Selected houmao-mgr is unavailable: {path}")
    return path


def cccc_path() -> Path:
    """Resolve the CCCC CLI installed beside the selected manager."""
    selected = os.environ.get("HOUMAO_CCCC")
    path = Path(selected).expanduser() if selected else manager_path().with_name("houmao-cccc")
    if not path.is_file():
        raise LabError(f"Selected houmao-cccc is unavailable: {path}")
    return path


def execution_identity() -> dict[str, Any]:
    """Capture checkout and installed-tool identity for evidence correlation."""

    def git_output(arguments: list[str]) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            raise LabError(f"git {arguments[0]} failed while recording run identity")
        return result.stdout.strip()

    manager_version = subprocess.run(
        [str(manager_path()), "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if manager_version.returncode != 0:
        raise LabError("Cannot record selected houmao-mgr version")
    return {
        "repo_root": str(REPO_ROOT),
        "branch": git_output(["branch", "--show-current"]),
        "commit_sha": git_output(["rev-parse", "HEAD"]),
        "dirty": bool(git_output(["status", "--porcelain"])),
        "manager_version": manager_version.stdout.strip(),
        "houmao_cccc_version": importlib.metadata.version("houmao-cccc"),
        "cccc_cli": str(cccc_path()),
    }


def command_identity(args: argparse.Namespace) -> int:
    """Print the current checkout and selected tool identity."""
    print(json.dumps(execution_identity(), indent=2, sort_keys=True))
    return 0


def run_env(run_dir: Path) -> dict[str, str]:
    """Build the isolated manager environment for one prepared fixture."""
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
            "HOUMAO_GLOBAL_MAILBOX_DIR": str(run_dir / "workdir/.houmao/mailbox"),
            "HOUMAO_CLI_PRINT_STYLE": "json",
        }
    )
    return env


def manager_json(
    env: dict[str, str], arguments: list[str], *, timeout: float = 420
) -> dict[str, Any]:
    """Run one manager operation and parse its safe JSON result."""
    try:
        result = subprocess.run(
            [str(manager_path()), "--print-json", *arguments],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise LabError(f"houmao-mgr timed out after {timeout}s") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "no output"
        raise LabError(f"houmao-mgr failed with exit {result.returncode}: {message}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LabError("houmao-mgr returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise LabError("houmao-mgr returned an unexpected JSON shape")
    return payload


def load_run(run_dir: Path) -> dict[str, Any]:
    """Require one launched managed fixture."""
    payload = read_json(run_dir / "run.json", label="fixture run")
    identity = payload.get("identity")
    if payload.get("status") != "launched" or not isinstance(identity, dict):
        raise LabError(f"Fixture is not launched: {run_dir}")
    if not identity.get("agent_id"):
        raise LabError(f"Fixture has no managed agent identity: {run_dir}")
    return payload


def load_meta(path: Path, *, complete: bool = True) -> dict[str, Any]:
    """Load the run handle and require configured identities when requested."""
    payload = read_json(path, label="run metadata")
    required = ["run_a", "run_b", "agent_a_id", "agent_b_id", "endpoint", "tag"]
    if complete:
        required.extend(["group_id", "actors", "bindings", "gateways", "plugin_configs"])
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise LabError(f"Run metadata is missing: {', '.join(missing)}")
    return payload


def role_run(meta: dict[str, Any], role: str) -> tuple[Path, str]:
    """Resolve one role's fixture and managed identity."""
    return Path(str(meta[f"run_{role}"])), str(meta[f"agent_{role}_id"])


def provider_client(meta: dict[str, Any]) -> httpx.Client:
    """Create an operator client for the selected CCCC service."""
    endpoint = str(meta["endpoint"]).rstrip("/")
    return httpx.Client(
        base_url=endpoint,
        headers={"Origin": endpoint, "Referer": endpoint + "/"},
        trust_env=False,
        follow_redirects=False,
        timeout=30,
    )


def provider_result(response: httpx.Response) -> dict[str, Any]:
    """Extract a provider result without reflecting sensitive response bodies."""
    if response.status_code != 200:
        raise LabError(f"CCCC operator request returned HTTP {response.status_code}")
    envelope = response.json()
    if not isinstance(envelope, dict) or not envelope.get("ok"):
        raise LabError("CCCC operator request returned an unsuccessful envelope")
    result = envelope.get("result")
    if not isinstance(result, dict):
        raise LabError("CCCC operator request returned an invalid result")
    return result


def gateway_get(meta: dict[str, Any], role: str, path: str) -> dict[str, Any]:
    """Read one public gateway route without ambient proxy or credentials."""
    base = str(meta["gateways"][role]).rstrip("/")
    try:
        response = httpx.get(base + path, trust_env=False, timeout=20)
    except httpx.HTTPError as exc:
        raise LabError(f"Gateway {role} is unavailable") from exc
    if response.status_code != 200:
        raise LabError(f"Gateway {role} {path} returned HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise LabError(f"Gateway {role} {path} returned an invalid response")
    return payload


def live_observation(meta: dict[str, Any], role: str) -> dict[str, Any]:
    """Project current Web or headless native readiness from public status."""
    state = gateway_get(meta, role, "/v1/status")
    web = state.get("web") if isinstance(state.get("web"), dict) else {}
    readiness: dict[str, Any] = {}
    if not web:
        readiness = gateway_get(meta, role, "/v1/control/headless/state")
    return {
        "availability": web.get("availability") or state.get("managed_agent_connectivity"),
        "active_execution": state.get("active_execution"),
        "request_admission": state.get("request_admission"),
        "gateway_health": state.get("gateway_health"),
        "native_surface_eligibility": state.get("native_surface_eligibility"),
        "host_process_alive": web.get("host_process_alive", state.get("host_process_alive")),
        "can_accept_prompt_now": web.get(
            "can_accept_prompt_now", readiness.get("can_accept_prompt_now")
        ),
    }


def cccc_json(meta: dict[str, Any], role: str, arguments: list[str]) -> dict[str, Any]:
    """Run one selected local CCCC CLI operation."""
    command = [str(cccc_path()), "--gateway-url", str(meta["gateways"][role]), *arguments]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    if result.returncode != 0:
        raise LabError(
            f"houmao-cccc {arguments[0]} failed for role {role}: {result.stdout.strip()}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LabError("houmao-cccc returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise LabError("houmao-cccc returned an unexpected JSON shape")
    return payload


def body_snapshot(run_dir: Path) -> dict[str, Any]:
    """Capture stable native-body and conversation identity from the manifest."""
    run = load_run(run_dir)
    manifest_path = Path(str(run["identity"]["manifest_path"]))
    manifest = read_json(manifest_path, label="managed session manifest")
    state = manifest.get("backend_state")
    if not isinstance(state, dict):
        raise LabError(f"Managed session has no native backend state: {manifest_path}")
    web_identity = state.get("web_identity") or {}
    return {
        "manifest_path": str(manifest_path),
        "native_pid": state.get("native_pid"),
        "native_birth_token": state.get("native_birth_token"),
        "supervisor_pid": state.get("supervisor_pid"),
        "supervisor_birth_token": state.get("supervisor_birth_token"),
        "native_session_id": state.get("native_session_id")
        or web_identity.get("native_session_id"),
    }


def assert_same_body(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Require attachment or reattachment to preserve the live native body."""
    keys = (
        "native_pid",
        "native_birth_token",
        "supervisor_pid",
        "supervisor_birth_token",
        "native_session_id",
    )
    changed = [key for key in keys if before.get(key) != after.get(key)]
    if changed or any(after.get(key) in (None, "") for key in keys):
        raise LabError(f"CCCC attachment changed native body identity: {', '.join(changed)}")


def session_files(run_dir: Path) -> list[Path]:
    """Return native DSH transcripts sorted by modification time."""
    homes = run_dir / "runtime" / "homes"
    if not homes.is_dir():
        return []
    return sorted(
        (path for path in homes.rglob("session.v4.jsonl") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
    )


def wait_binding(meta: dict[str, Any], role: str, *, timeout: float = 60) -> dict[str, Any]:
    """Wait for the selected Actor receiver to negotiate and acquire its lease."""
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            last = cccc_json(meta, role, ["binding"])
            if last.get("connection") == "connected":
                return last
        except LabError:
            pass
        time.sleep(0.25)
    raise LabError(f"CCCC receiver {role} did not connect; last phase={last.get('connection')}")


def update_gateway_run(run_dir: Path, attached: dict[str, Any]) -> str:
    """Persist the attached gateway coordinates for subsequent fixture prompts."""
    host = attached.get("gateway_host")
    port = attached.get("gateway_port")
    if not isinstance(host, str) or not isinstance(port, int):
        raise LabError("Gateway attachment returned invalid coordinates")
    run = load_run(run_dir)
    run["identity"]["gateway_host"] = host
    run["identity"]["gateway_port"] = port
    write_json(run_dir / "run.json", run)
    return f"http://{host}:{port}"


def service_identity(runtime_path: Path, binary_path: Path) -> dict[str, Any]:
    """Verify a selected local service process against its managed build receipt."""
    runtime_path = runtime_path.expanduser().resolve()
    binary_path = binary_path.expanduser().resolve()
    runtime = read_json(runtime_path, label="CCCC service runtime")
    build = read_json(runtime_path.with_name("build.json"), label="CCCC build receipt")
    pid = runtime.get("pid")
    if not isinstance(pid, int):
        raise LabError("CCCC service runtime has no PID")
    try:
        os.kill(pid, 0)
        executable = Path(f"/proc/{pid}/exe").resolve()
    except OSError as exc:
        raise LabError(f"CCCC service process is unavailable: {pid}") from exc
    if executable != binary_path:
        raise LabError("CCCC service process does not use the selected binary")
    digest = hashlib.sha256(binary_path.read_bytes()).hexdigest()
    if digest != build.get("binary_sha256") or build.get("binary_verified") is not True:
        raise LabError("CCCC binary does not match its verified build receipt")
    if build.get("receiver_protocol_version") != _RECEIVER_PROTOCOL_VERSION:
        raise LabError("CCCC build does not provide external-receiver protocol 2")
    patches = build.get("receiver_patches")
    required_patches = (
        "0001-external-receiver.patch",
        "0002-explicit-deferred-mail.patch",
        "0003-queued-receiver-v2.patch",
    )
    if not isinstance(patches, list) or not all(
        any(
            isinstance(item, dict) and str(item.get("path", "")).endswith(required)
            for item in patches
        )
        for required in required_patches
    ):
        raise LabError("CCCC build lacks the complete external-receiver patch series")
    return {
        "runtime_path": str(runtime_path),
        "binary_path": str(binary_path),
        "pid": pid,
        "source_revision": build.get("source_revision"),
        "receiver_protocol_version": build.get("receiver_protocol_version"),
        "receiver_patches": patches,
        "binary_sha256": digest,
    }


def command_configure(args: argparse.Namespace) -> int:
    """Provision one isolated Group and attach both real managed agents."""
    run_a = args.run_a.resolve()
    run_b = args.run_b.resolve()
    run = {"a": load_run(run_a), "b": load_run(run_b)}
    agent_ids = {role: str(run[role]["identity"]["agent_id"]) for role in _ROLES}
    if agent_ids["a"] == agent_ids["b"]:
        raise LabError("The two CCCC owners must be distinct")
    private_parent = args.private_root.expanduser().resolve()
    if private_parent.is_relative_to(REPO_ROOT):
        raise LabError("CCCC_PRIVATE_ROOT must be outside the checkout")
    tag = "cccc-" + secrets.token_hex(6)
    private_run = private_parent / tag
    if private_run.exists():
        raise LabError(f"Private run directory already exists: {private_run}")
    private_run.mkdir(parents=True, mode=0o700)
    private_run.chmod(0o700)
    meta: dict[str, Any] = {
        "schema_version": 1,
        "execution_identity": execution_identity(),
        "status": "provisioning",
        "tag": tag,
        "endpoint": args.endpoint.rstrip("/"),
        "run_a": str(run_a),
        "run_b": str(run_b),
        "agent_a_id": agent_ids["a"],
        "agent_b_id": agent_ids["b"],
        "actors": {"a": "agent-a", "b": "agent-b"},
        "group_id": None,
        "grants": {},
        "bindings": {},
        "gateways": {},
        "plugin_configs": {},
        "private_run": str(private_run),
        "evidence_root": str(args.evidence_root.resolve()),
        "tmux_sockets": {role: run[role].get("tmux_socket_path") for role in _ROLES},
        "body_before": {role: body_snapshot(Path(str(run[role]["run_dir"]))) for role in _ROLES},
    }
    write_json(args.run_meta, meta)
    try:
        if args.service_runtime or args.provider_binary:
            if not args.service_runtime or not args.provider_binary:
                raise LabError("Select both service runtime and provider binary, or neither")
            meta["service_identity"] = service_identity(args.service_runtime, args.provider_binary)
            write_json(args.run_meta, meta)
        with provider_client(meta) as provider:
            provider_result(provider.get("/api/v1/health"))
            group = provider_result(provider.post("/api/v1/groups", json={"title": tag}))
            group_id = group.get("group_id")
            if not isinstance(group_id, str) or not group_id:
                raise LabError("CCCC group creation returned no group_id")
            meta["group_id"] = group_id
            write_json(args.run_meta, meta)
            for role in _ROLES:
                run_dir, agent_id = role_run(meta, role)
                actor_id = str(meta["actors"][role])
                provider_result(
                    provider.post(
                        f"/api/v1/groups/{group_id}/actors",
                        json={"actor_id": actor_id, "runtime": "custom", "command": ["/bin/true"]},
                    )
                )
                credential = private_run / f"{role}.json"
                provision = subprocess.run(
                    [
                        sys.executable,
                        str(REPO_ROOT / "tools/cccc/provision.py"),
                        "--endpoint",
                        str(meta["endpoint"]),
                        "--group-id",
                        group_id,
                        "--actor-id",
                        actor_id,
                        "--agent-id",
                        agent_id,
                        "--output",
                        str(credential),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,
                )
                if provision.returncode != 0:
                    raise LabError(f"CCCC grant export failed for role {role}")
                grant = json.loads(provision.stdout)
                meta["grants"][role] = {
                    "grant_id": grant["grant_id"],
                    "credential_file": str(credential),
                    "actor_generation": grant["actor_generation"],
                }
                write_json(args.run_meta, meta)

                manager_json(run_env(run_dir), ["mailbox", "init"])
                offline = manager_json(
                    run_env(run_dir),
                    ["agents", "single", "--agent-id", agent_id, "mailbox", "offline", "status"],
                )
                if not offline.get("registered"):
                    offline = manager_json(
                        run_env(run_dir),
                        [
                            "agents",
                            "single",
                            "--agent-id",
                            agent_id,
                            "mailbox",
                            "offline",
                            "join",
                            "--address",
                            f"{actor_id}-{tag}@houmao.localhost",
                        ],
                    )
                meta.setdefault("offline_recovery", {})[role] = offline
                write_json(args.run_meta, meta)

                selection = run_dir / "cccc-plugins.json"
                write_json(
                    selection,
                    {
                        "schema_version": 1,
                        "gateway": {
                            "plugins": {
                                "cccc": {
                                    "implementation": "cccc",
                                    "credential_ref": {"file": str(credential)},
                                    "config": {
                                        "endpoint": meta["endpoint"],
                                        "group_id": group_id,
                                        "actor_id": actor_id,
                                        "actor_generation": grant["actor_generation"],
                                    },
                                }
                            }
                        },
                    },
                )
                meta["plugin_configs"][role] = str(selection)
                manager_json(
                    run_env(run_dir),
                    ["agents", "single", "--agent-id", agent_id, "gateway", "detach"],
                )
                attached = manager_json(
                    run_env(run_dir),
                    [
                        "agents",
                        "single",
                        "--agent-id",
                        agent_id,
                        "gateway",
                        "attach",
                        "--background",
                        "--plugins-config",
                        str(selection),
                    ],
                )
                meta["gateways"][role] = update_gateway_run(run_dir, attached)
                write_json(args.run_meta, meta)
                binding = wait_binding(meta, role)
                if (
                    binding.get("agent_id") != agent_id
                    or binding.get("group_id") != group_id
                    or binding.get("actor_id") != actor_id
                ):
                    raise LabError(f"CCCC binding identity mismatch for role {role}")
                meta["bindings"][role] = binding
                after = body_snapshot(run_dir)
                assert_same_body(meta["body_before"][role], after)
                meta.setdefault("body_after", {})[role] = after
                write_json(args.run_meta, meta)

        members = cccc_json(meta, "a", ["members"])
        member_ids = {
            item.get("id") for item in members.get("members", []) if isinstance(item, dict)
        }
        if member_ids != {"agent-a", "agent-b"}:
            raise LabError("CCCC Group membership does not contain exactly the two run Actors")
        for role in _ROLES:
            run_dir, _ = role_run(meta, role)
            peer = "b" if role == "a" else "a"
            write_json(
                run_dir / "workdir" / "cccc-brief.json",
                {
                    "cccc_cli": str(cccc_path()),
                    "gateway_url": meta["gateways"][role],
                    "plugin_instance": "cccc",
                    "binding_id": meta["bindings"][role]["binding_id"],
                    "group_id": meta["group_id"],
                    "actor_id": meta["actors"][role],
                    "peer_actor_id": meta["actors"][peer],
                    "protocol": "CCCC chat only; no mailbox channel",
                },
            )
        meta["status"] = "configured"
        meta["members"] = members
        write_json(args.run_meta, meta)
    except Exception:
        meta["status"] = "setup_failed"
        write_json(args.run_meta, meta)
        raise
    print(
        json.dumps(
            {
                "status": meta["status"],
                "tag": tag,
                "group_id": meta["group_id"],
                "agents": agent_ids,
                "bindings": meta["bindings"],
                "gateways": meta["gateways"],
                "body_preserved": meta["body_after"],
                "offline_recovery": meta["offline_recovery"],
                "run_meta": str(args.run_meta),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    """Verify provider, owners, native bodies, chat bindings, and recovery mail."""
    meta = load_meta(args.run_meta)
    if meta.get("status") != "configured":
        raise LabError(f"Run is not configured: {meta.get('status')}")
    service = meta.get("service_identity")
    if service:
        os.kill(int(service["pid"]), 0)
        if Path(f"/proc/{service['pid']}/exe").resolve() != Path(service["binary_path"]):
            raise LabError("CCCC service executable changed")
    with provider_client(meta) as provider:
        health = provider_result(provider.get("/api/v1/health"))
    result: dict[str, Any] = {"status": "healthy", "provider_health": health, "agents": {}}
    for role in _ROLES:
        run_dir, agent_id = role_run(meta, role)
        state = live_observation(meta, role)
        if (
            state.get("gateway_health") != "healthy"
            or state.get("native_surface_eligibility") != "ready"
            or state.get("host_process_alive") is not True
        ):
            raise LabError(f"Managed agent {role} is not healthy")
        binding = cccc_json(meta, role, ["binding"])
        expected = meta["bindings"][role]
        if (
            binding.get("connection") != "connected"
            or binding.get("binding_id") != expected.get("binding_id")
            or binding.get("agent_id") != agent_id
        ):
            raise LabError(f"CCCC binding {role} is not connected to the expected owner")
        capabilities = cccc_json(meta, role, ["capabilities"])
        members = cccc_json(meta, role, ["members"])
        current_body = body_snapshot(run_dir)
        assert_same_body(meta["body_before"][role], current_body)
        offline = manager_json(
            run_env(run_dir),
            ["agents", "single", "--agent-id", agent_id, "mailbox", "offline", "status"],
        )
        if not offline.get("registered"):
            raise LabError(f"Operator recovery mailbox {role} is not registered")
        result["agents"][role] = {
            "agent_id": agent_id,
            "availability": state.get("availability"),
            "active_execution": state.get("active_execution"),
            "binding": binding,
            "capabilities": capabilities,
            "members": members,
            "body": current_body,
            "offline_recovery": {
                "registered": offline.get("registered"),
                "binding_id": (offline.get("binding") or {}).get("binding_id"),
                "address": (offline.get("binding") or {}).get("address"),
            },
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_prompt(args: argparse.Namespace) -> int:
    """Submit one ordinary operator prompt through the managed gateway."""
    meta = load_meta(args.run_meta)
    run_dir, agent_id = role_run(meta, args.role)
    payload = manager_json(
        run_env(run_dir),
        ["agents", "single", "--agent-id", agent_id, "prompt", "--prompt", args.prompt],
        timeout=args.timeout,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_state(args: argparse.Namespace) -> int:
    """Read safe live readiness and execution state."""
    meta = load_meta(args.run_meta)
    state = live_observation(meta, args.role)
    print(json.dumps({"role": args.role, **state}, indent=2, sort_keys=True))
    return 0


def command_delivery(args: argparse.Namespace) -> int:
    """Set the run-owned receiver delivery policy and await its effective settings."""

    meta = load_meta(args.run_meta)
    path = "/v1/plugins/cccc/delivery"
    before = gateway_get(meta, args.role, path)
    settings: dict[str, Any] = {"transport": "pull"}
    if args.policy != "pull":
        settings = {"transport": "push", "push_policy": args.policy}
        if args.policy == "batch":
            settings.update(quiet_interval=args.quiet_interval, max_wait=args.max_wait)
    response = httpx.put(
        str(meta["gateways"][args.role]).rstrip("/") + path,
        json={"revision": before["revision"], "settings": settings},
        trust_env=False,
        timeout=20,
    )
    if response.status_code != 200:
        raise LabError(f"Setting receiver delivery returned HTTP {response.status_code}")
    revision = response.json()["revision"]
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        observed = gateway_get(meta, args.role, path)
        if observed.get("revision") != revision:
            raise LabError("Receiver delivery settings changed unexpectedly")
        if observed.get("transition") == "active" and observed.get("effective") == observed.get(
            "desired"
        ):
            print(json.dumps(observed, indent=2, sort_keys=True))
            return 0
        time.sleep(0.25)
    raise LabError("Timed out waiting for the receiver delivery policy")


def command_wait_execution(args: argparse.Namespace) -> int:
    """Wait for a real native execution or prompt-readiness transition."""
    meta = load_meta(args.run_meta)
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        state = live_observation(meta, args.role)
        if args.mode == "busy" and state.get("active_execution") == "running":
            print(json.dumps({"role": args.role, "state": "busy"}, indent=2))
            return 0
        if (
            args.mode == "ready"
            and state.get("can_accept_prompt_now") is True
            and (
                not args.require_open
                or (
                    state.get("active_execution") == "idle"
                    and state.get("request_admission") == "open"
                )
            )
        ):
            result = {"role": args.role, "state": "ready"}
            if args.require_open:
                result.update(active_execution="idle", request_admission="open")
            print(json.dumps(result, indent=2))
            return 0
        time.sleep(args.interval)
    raise LabError(f"Timed out waiting for role {args.role} to become {args.mode}")


def command_cccc(args: argparse.Namespace) -> int:
    """Run a whitelisted read-only CCCC inspection command."""
    meta = load_meta(args.run_meta)
    arguments = args.arguments
    allowed = (
        ["binding"],
        ["capabilities"],
        ["members"],
        ["chat", "history"],
        ["chat", "deliveries"],
    )
    if not any(arguments[: len(prefix)] == prefix for prefix in allowed):
        raise LabError(
            "Only binding, capabilities, members, chat history, and deliveries are read-only"
        )
    payload = cccc_json(meta, args.role, arguments)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def matching_events(
    history: dict[str, Any], meta: dict[str, Any], token: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select the exact agent-authored request and its threaded replies."""
    requests: list[dict[str, Any]] = []
    replies: list[dict[str, Any]] = []
    for event in history.get("messages", []):
        if not isinstance(event, dict):
            continue
        data = event.get("data") or {}
        text = data.get("text")
        if not isinstance(text, str) or token not in text:
            continue
        if (
            event.get("by") == meta["actors"]["a"]
            and data.get("message_mode") == "request_reply"
            and not data.get("reply_to")
        ):
            requests.append(event)
        if event.get("by") == meta["actors"]["b"] and data.get("reply_to"):
            replies.append(event)
    return requests, replies


def command_verify(args: argparse.Namespace) -> int:
    """Verify one native request/reply chain and its exact delivery attempts."""
    meta = load_meta(args.run_meta)
    deadline = time.monotonic() + args.timeout
    request: dict[str, Any] | None = None
    reply: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        history = cccc_json(meta, "a", ["chat", "history", "--limit", "100"])
        requests, replies = matching_events(history, meta, args.token)
        if len(requests) > 1:
            raise LabError(f"Expected one CCCC request for {args.token}, found {len(requests)}")
        request = requests[0] if requests else None
        if request is not None:
            matching_replies = [
                event
                for event in replies
                if (event.get("data") or {}).get("reply_to") == request.get("id")
            ]
            if len(matching_replies) > 1:
                raise LabError(f"Expected at most one CCCC reply for {args.token}")
            reply = matching_replies[0] if matching_replies else None
        if request is not None and (reply is not None or args.allow_no_reply):
            break
        time.sleep(args.interval)
    if request is None:
        raise LabError(f"No CCCC request found for {args.token}")
    if reply is None and not args.allow_no_reply:
        raise LabError(f"No CCCC reply found for {args.token}")
    request_data = request.get("data") or {}
    if request_data.get("message_mode") != "request_reply":
        raise LabError("The peer request did not use request_reply")
    if reply is not None:
        reply_data = reply.get("data") or {}
        if reply_data.get("message_mode") != "send":
            raise LabError("The CCCC reply did not use native send mode")
        if args.reply_contains and args.reply_contains not in str(reply_data.get("text", "")):
            raise LabError("The CCCC reply lacks the requested work result")
    event_ref = request.get("event_ref")
    if not isinstance(event_ref, str):
        raise LabError("The CCCC request has no scoped event_ref")
    deliveries = cccc_json(
        meta, "a", ["chat", "deliveries", "--event-ref", event_ref, "--limit", "100"]
    )
    attempts = deliveries.get("deliveries")
    if not isinstance(attempts, list):
        raise LabError("CCCC deliveries did not return an attempt list")
    provider_states = [item.get("state") for item in attempts if isinstance(item, dict)]
    states = list(reversed(provider_states))
    expected = args.expected_attempts.split(",")
    if states != expected:
        raise LabError(
            f"CCCC chronological delivery attempts were {states}, expected {expected}; "
            f"provider returned newest-first {provider_states}"
        )
    payload = {
        "status": "passed",
        "token": args.token,
        "request": request,
        "reply": reply,
        "delivery_attempts": attempts,
        "chronological_attempt_states": states,
        "provider_attempt_states_newest_first": provider_states,
        "native_reply_ancestry": None
        if reply is None
        else (reply.get("data") or {}).get("reply_to"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_scan(args: argparse.Namespace) -> int:
    """Check whether a native agent transcript contains a selected token."""
    meta = load_meta(args.run_meta)
    run_dir, _ = role_run(meta, args.role)
    files = session_files(run_dir)
    if not files:
        raise LabError(f"No native transcript found for role {args.role}")
    occurrences = sum(path.read_text().count(args.token) for path in files)
    if args.expect == "absent" and occurrences:
        raise LabError(f"Token unexpectedly reached role {args.role}: {occurrences} occurrences")
    if args.expect == "present" and not occurrences:
        raise LabError(f"Token did not reach role {args.role}")
    print(
        json.dumps(
            {
                "role": args.role,
                "token": args.token,
                "occurrences": occurrences,
                "expected": args.expect,
                "status": "passed",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_verify_batch(args: argparse.Namespace) -> int:
    """Verify the exact batch from the recipient's native user-message transcript."""

    meta = load_meta(args.run_meta)
    run_dir, _ = role_run(meta, "b")
    candidates: list[tuple[str, str]] = []
    for path in session_files(run_dir):
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("type") != "user/message":
                continue
            data = row["data"]
            if data.get("source", {}).get("kind") != "user":
                continue
            for content in data.get("content", []):
                text = content.get("text", "")
                if (
                    isinstance(text, str)
                    and _REQUEST_BEGIN in text
                    and any(token in text for token in args.tokens)
                ):
                    candidates.append((str(data["id"]), text))
    selected: list[tuple[str, str, str, list[dict[str, Any]]]] = []
    for native_id, text in candidates:
        if text.count(_REQUEST_BEGIN) != 1 or text.count(_REQUEST_END) != 1:
            continue
        header, _, content = text.partition(_REQUEST_BEGIN)
        try:
            entries = json.loads(content.split(_REQUEST_END, 1)[0])["messages"]
        except (TypeError, ValueError, KeyError):
            continue
        if not isinstance(entries, list) or not any(
            isinstance(entry, dict)
            and entry.get("mode") == "request_reply"
            and isinstance(entry.get("text"), str)
            and any(token in entry["text"] for token in args.tokens)
            for entry in entries
        ):
            continue
        selected.append((native_id, text, header, entries))
    if len(selected) != 1:
        raise LabError(f"Expected one native request for the selected batch, found {len(selected)}")
    native_id, text, header, entries = selected[0]
    binding = str(meta["bindings"]["b"]["binding_id"])
    private_markers = ("binding_id=", "event_id=", "event_ref=", "connection_token=")
    if (
        binding in text
        or any(marker in text for marker in private_markers)
        or header.count(str(meta["gateways"]["b"])) != 1
    ):
        raise LabError("The selected request header exposes private routing or repeats its URL")
    if not isinstance(entries, list) or len(entries) != len(args.tokens):
        raise LabError("The selected request fence does not contain the expected count")
    handles: set[str] = set()
    history = cccc_json(meta, "a", ["chat", "history", "--limit", "100"])
    proofs: list[dict[str, Any]] = []
    for entry, token in zip(entries, args.tokens, strict=True):
        requests, _ = matching_events(history, meta, token)
        if len(requests) != 1:
            raise LabError("Expected one original native request for each batch entry")
        request = requests[0]
        if (
            entry["text"] != request["data"]["text"]
            or entry["sender"] != meta["actors"]["a"]
            or entry["timestamp"] != request["ts"]
            or entry["mode"] != "request_reply"
            or not entry["handle"].startswith("msg_")
            or str(request.get("event_ref") or "") in text
            or str(request.get("id") or "") in text
        ):
            raise LabError("The selected batch has unexpected order, attribution, or handles")
        handles.add(entry["handle"])
        proofs.append(
            {
                "event_id": request["id"],
                "sender": entry["sender"],
                "timestamp": entry["timestamp"],
                "mode": entry["mode"],
                "handle": entry["handle"],
                "token": token,
            }
        )
    if len(handles) != len(entries):
        raise LabError("The batch reuses a message handle")
    print(
        json.dumps(
            {
                "status": "passed",
                "native_message_id": native_id,
                "fence_count": 1,
                "message_count": len(entries),
                "header": header.strip(),
                "entries": proofs,
            },
            indent=2,
        )
    )
    return 0


def command_transcript(args: argparse.Namespace) -> int:
    """Copy native transcripts into the selected surviving evidence directory."""
    meta = load_meta(args.run_meta)
    run_dir, _ = role_run(meta, args.role)
    files = session_files(run_dir)
    if not files:
        raise LabError(f"No native transcript found for role {args.role}")
    args.output.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for index, source in enumerate(files[-args.max_files :]):
        target = args.output / f"{args.role}-transcript-{index}{source.suffix}"
        shutil.copy2(source, target)
        copied.append(str(target))
    print(json.dumps({"role": args.role, "copied": copied}, indent=2, sort_keys=True))
    return 0


def audit_role(run_dir: Path) -> dict[str, Any]:
    """Inspect actual tool calls for forbidden peer-mail or provider-admin fallback."""
    commands: list[dict[str, Any]] = []
    for path in session_files(run_dir):
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "tool/call":
                continue
            data = event.get("data") or {}
            if data.get("name") != "bash":
                continue
            try:
                arguments = json.loads(data.get("arguments") or "{}")
            except json.JSONDecodeError:
                continue
            command = arguments.get("command")
            if isinstance(command, str):
                commands.append({"turn": data.get("turn"), "command": command})
    forbidden: list[dict[str, Any]] = []
    for item in commands:
        command = item["command"]
        lower = command.lower()
        reasons: list[str] = []
        if re.search(r"houmao-cccc[^\n]*\smail(?:\s|$)", lower):
            reasons.append("CCCC Mail")
        if re.search(r"agents\s+(?:self|single)[^\n]*\smail\s+(?:send|reply|post)(?:\s|$)", lower):
            reasons.append("Houmao peer mail")
        if "/v1/mail/" in lower or "houmao-agent-email-comms" in lower:
            reasons.append("mail channel")
        if "/api/v1/external-receiver/" in lower or "/api/v1/groups" in lower:
            reasons.append("CCCC provider administration")
        if reasons:
            forbidden.append({**item, "reasons": reasons})
    return {
        "bash_tool_calls": commands,
        "forbidden_calls": forbidden,
        "status": "passed" if not forbidden else "failed",
    }


def command_audit(args: argparse.Namespace) -> int:
    """Audit both native transcripts without grading assistant summaries."""
    meta = load_meta(args.run_meta)
    result = {role: audit_role(role_run(meta, role)[0]) for role in _ROLES}
    result["status"] = (
        "passed" if all(result[role]["status"] == "passed" for role in _ROLES) else "failed"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["status"] != "passed")


def command_detach(args: argparse.Namespace) -> int:
    """Detach only the selected gateway while preserving its native body."""
    meta = load_meta(args.run_meta)
    run_dir, agent_id = role_run(meta, args.role)
    receipt = manager_json(
        run_env(run_dir),
        ["agents", "single", "--agent-id", agent_id, "gateway", "detach"],
    )
    body = body_snapshot(run_dir)
    assert_same_body(meta["body_before"][args.role], body)
    meta.setdefault("detachments", {})[args.role] = {"receipt": receipt, "body": body}
    write_json(args.run_meta, meta)
    print(json.dumps({"role": args.role, "detached": True, "body": body}, indent=2, sort_keys=True))
    return 0


def command_attach(args: argparse.Namespace) -> int:
    """Reattach the same plugin selection and require reference continuity."""
    meta = load_meta(args.run_meta)
    role = args.role
    run_dir, agent_id = role_run(meta, role)
    attached = manager_json(
        run_env(run_dir),
        [
            "agents",
            "single",
            "--agent-id",
            agent_id,
            "gateway",
            "attach",
            "--background",
            "--plugins-config",
            str(meta["plugin_configs"][role]),
        ],
    )
    meta["gateways"][role] = update_gateway_run(run_dir, attached)
    write_json(args.run_meta, meta)
    binding = wait_binding(meta, role)
    if binding.get("binding_id") != meta["bindings"][role].get("binding_id"):
        raise LabError("Gateway reattachment changed the CCCC binding ID")
    body = body_snapshot(run_dir)
    assert_same_body(meta["body_before"][role], body)
    meta["bindings"][role] = binding
    peer = "b" if role == "a" else "a"
    write_json(
        run_dir / "workdir" / "cccc-brief.json",
        {
            "cccc_cli": str(cccc_path()),
            "gateway_url": meta["gateways"][role],
            "plugin_instance": "cccc",
            "binding_id": binding["binding_id"],
            "group_id": meta["group_id"],
            "actor_id": meta["actors"][role],
            "peer_actor_id": meta["actors"][peer],
            "protocol": "CCCC chat only; no mailbox channel",
        },
    )
    write_json(args.run_meta, meta)
    print(
        json.dumps(
            {"role": role, "attached": True, "binding": binding, "body": body},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_recovery_post(args: argparse.Namespace) -> int:
    """Post an operator-only filesystem-mail recovery note after explicit confirmation."""
    if not args.confirm_operator_recovery:
        raise LabError(
            "Recovery mail requires --confirm-operator-recovery and invalidates the graded flow"
        )
    meta = load_meta(args.run_meta)
    run_dir, agent_id = role_run(meta, args.role)
    offline = manager_json(
        run_env(run_dir),
        ["agents", "single", "--agent-id", agent_id, "mailbox", "offline", "status"],
    )
    binding_id = (offline.get("binding") or {}).get("binding_id")
    if not isinstance(binding_id, str):
        raise LabError("Operator recovery mailbox is not configured")
    payload = manager_json(
        run_env(run_dir),
        [
            "agents",
            "single",
            "--agent-id",
            agent_id,
            "mail",
            "post",
            "--channel",
            "offline",
            "--expected-binding-id",
            binding_id,
            "--reply-policy",
            "none",
            "--subject",
            args.subject,
            "--body-content",
            args.body,
        ],
    )
    print(
        json.dumps({"operator_recovery_only": True, "receipt": payload}, indent=2, sort_keys=True)
    )
    return 0


def kill_private_tmux(run_dir: Path, socket_path: str | None) -> dict[str, Any]:
    """Stop one verified fixture-owned tmux server and remove its stale socket."""
    if not socket_path:
        return {"status": "not_recorded"}
    run = read_json(run_dir / "run.json", label="fixture run")
    if run.get("tmux_server_mode") != "new" or run.get("tmux_socket_path") != socket_path:
        return {"status": "unverified", "socket": socket_path}
    socket = Path(socket_path)
    if not socket.exists():
        return {"status": "already_absent", "socket": socket_path}
    result = subprocess.run(
        ["tmux", "-S", str(socket), "kill-server"],
        env={key: value for key, value in os.environ.items() if key not in _TMUX_ENV_KEYS},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and "no server running" not in result.stderr.lower():
        return {"status": "failed", "socket": socket_path, "error": result.stderr.strip()}
    socket.unlink(missing_ok=True)
    return {"status": "killed", "socket": socket_path}


def command_stop(args: argparse.Namespace) -> int:
    """Stop owned agents, revoke grants, delete the Group, and preserve evidence."""
    meta = load_meta(args.run_meta, complete=False)
    result: dict[str, Any] = {"agents": {}, "disconnects": {}, "grants": {}, "credentials": {}}
    for role in _ROLES:
        if role not in meta.get("bindings", {}) or role not in meta.get("gateways", {}):
            continue
        try:
            result["disconnects"][role] = cccc_json(
                meta,
                role,
                [
                    "connection",
                    "disconnect",
                    "--binding-id",
                    str(meta["bindings"][role]["binding_id"]),
                ],
            )
        except (LabError, KeyError) as exc:
            result["disconnects"][role] = {"error": str(exc)}
    for role in _ROLES:
        run_key = f"run_{role}"
        agent_key = f"agent_{role}_id"
        if run_key not in meta or agent_key not in meta:
            continue
        run_dir = Path(str(meta[run_key]))
        try:
            receipt = manager_json(
                run_env(run_dir),
                ["agents", "single", "--agent-id", str(meta[agent_key]), "stop"],
                timeout=90,
            )
            result["agents"][role] = {"status": "stopped", "receipt": receipt}
        except LabError as exc:
            detail = str(exc)
            already_stopped = "relaunch" in detail and "cleanup" in detail
            result["agents"][role] = {
                "status": "already_stopped" if already_stopped else "error",
                "error": None if already_stopped else detail,
            }
        result["agents"][role]["tmux"] = kill_private_tmux(
            run_dir, (meta.get("tmux_sockets") or {}).get(role)
        )
    if meta.get("group_id"):
        try:
            with provider_client(meta) as provider:
                for role, grant in meta.get("grants", {}).items():
                    response = provider.delete(
                        f"/api/v1/external-receiver/v{_RECEIVER_PROTOCOL_VERSION}/grants/"
                        + str(grant["grant_id"])
                    )
                    result["grants"][role] = {"http_status": response.status_code}
                response = provider.delete(f"/api/v1/groups/{meta['group_id']}")
                result["group_delete_http_status"] = response.status_code
                verification = provider.get(f"/api/v1/groups/{meta['group_id']}")
                result["group_absent"] = verification.status_code == 404
        except (httpx.HTTPError, OSError) as exc:
            result["group_cleanup_error"] = str(exc)
    private_run = Path(str(meta.get("private_run", "")))
    if private_run and private_run.is_absolute() and not private_run.is_relative_to(REPO_ROOT):
        for role, grant in meta.get("grants", {}).items():
            credential = Path(str(grant["credential_file"]))
            if credential.parent != private_run:
                result["credentials"][role] = {"status": "unverified", "path": str(credential)}
                continue
            credential.unlink(missing_ok=True)
            result["credentials"][role] = {"absent": not credential.exists()}
        if not private_run.exists():
            result["private_run_absent"] = True
        else:
            try:
                private_run.rmdir()
                result["private_run_absent"] = not private_run.exists()
            except OSError:
                result["private_run_absent"] = False
    failures = []
    if any(item.get("status") == "error" for item in result["agents"].values()):
        failures.append("agent stop")
    if any(
        item.get("tmux", {}).get("status") in {"failed", "unverified"}
        for item in result["agents"].values()
    ):
        failures.append("tmux cleanup")
    if meta.get("group_id") and result.get("group_absent") is not True:
        failures.append("group cleanup")
    if any(item.get("absent") is not True for item in result["credentials"].values()):
        failures.append("credential cleanup")
    result["status"] = "cleanup-incomplete" if failures else "stopped"
    result["failures"] = failures
    result["evidence_root"] = meta.get("evidence_root")
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(bool(failures))


def build_parser() -> argparse.ArgumentParser:
    """Build the instructional harness command surface."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    identity = commands.add_parser("identity")
    identity.set_defaults(handler=command_identity)

    configure = commands.add_parser("configure")
    configure.add_argument("--run-a", type=Path, required=True)
    configure.add_argument("--run-b", type=Path, required=True)
    configure.add_argument("--endpoint", required=True)
    configure.add_argument("--private-root", type=Path, required=True)
    configure.add_argument("--service-runtime", type=Path)
    configure.add_argument("--provider-binary", type=Path)
    configure.add_argument("--run-meta", type=Path, required=True)
    configure.add_argument("--evidence-root", type=Path, required=True)
    configure.set_defaults(handler=command_configure)

    for name, handler in (
        ("doctor", command_doctor),
        ("verify", command_verify),
        ("audit", command_audit),
        ("stop", command_stop),
    ):
        command = commands.add_parser(name)
        command.add_argument("--run-meta", type=Path, required=True)
        if name == "verify":
            command.add_argument("--token", required=True)
            command.add_argument("--reply-contains")
            command.add_argument("--expected-attempts", default="accepted")
            command.add_argument("--allow-no-reply", action="store_true")
            command.add_argument("--timeout", type=float, default=300)
            command.add_argument("--interval", type=float, default=1)
        command.set_defaults(handler=handler)

    prompt = commands.add_parser("prompt")
    prompt.add_argument("--run-meta", type=Path, required=True)
    prompt.add_argument("--role", choices=_ROLES, required=True)
    prompt.add_argument("--prompt", required=True)
    prompt.add_argument("--timeout", type=float, default=420)
    prompt.set_defaults(handler=command_prompt)

    for name, handler in (
        ("state", command_state),
        ("detach", command_detach),
        ("attach", command_attach),
    ):
        command = commands.add_parser(name)
        command.add_argument("--run-meta", type=Path, required=True)
        command.add_argument("--role", choices=_ROLES, required=True)
        command.set_defaults(handler=handler)

    wait = commands.add_parser("wait-execution")
    wait.add_argument("--run-meta", type=Path, required=True)
    wait.add_argument("--role", choices=_ROLES, required=True)
    wait.add_argument("--mode", choices=("busy", "ready"), required=True)
    wait.add_argument("--require-open", action="store_true", help="Require idle and open admission")
    wait.add_argument("--timeout", type=float, default=60)
    wait.add_argument("--interval", type=float, default=0.25)
    wait.set_defaults(handler=command_wait_execution)

    delivery = commands.add_parser("delivery")
    delivery.add_argument("--run-meta", type=Path, required=True)
    delivery.add_argument("--role", choices=_ROLES, required=True)
    delivery.add_argument("--policy", choices=("pull", "asap", "batch"), required=True)
    delivery.add_argument("--quiet-interval", type=float, default=8)
    delivery.add_argument("--max-wait", type=float, default=20)
    delivery.add_argument("--timeout", type=float, default=60)
    delivery.set_defaults(handler=command_delivery)

    batch = commands.add_parser("verify-batch")
    batch.add_argument("--run-meta", type=Path, required=True)
    batch.add_argument("--tokens", nargs="+", required=True)
    batch.set_defaults(handler=command_verify_batch)

    inspect = commands.add_parser("cccc")
    inspect.add_argument("--run-meta", type=Path, required=True)
    inspect.add_argument("--role", choices=_ROLES, required=True)
    inspect.add_argument("arguments", nargs=argparse.REMAINDER)
    inspect.set_defaults(handler=command_cccc)

    scan = commands.add_parser("scan")
    scan.add_argument("--run-meta", type=Path, required=True)
    scan.add_argument("--role", choices=_ROLES, required=True)
    scan.add_argument("--token", required=True)
    scan.add_argument("--expect", choices=("present", "absent"), required=True)
    scan.set_defaults(handler=command_scan)

    transcript = commands.add_parser("transcript")
    transcript.add_argument("--run-meta", type=Path, required=True)
    transcript.add_argument("--role", choices=_ROLES, required=True)
    transcript.add_argument("--output", type=Path, required=True)
    transcript.add_argument("--max-files", type=int, default=3)
    transcript.set_defaults(handler=command_transcript)

    recovery = commands.add_parser("recovery-post")
    recovery.add_argument("--run-meta", type=Path, required=True)
    recovery.add_argument("--role", choices=_ROLES, required=True)
    recovery.add_argument("--subject", required=True)
    recovery.add_argument("--body", required=True)
    recovery.add_argument("--confirm-operator-recovery", action="store_true")
    recovery.set_defaults(handler=command_recovery_post)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Translate harness failures into a concise nonzero result."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (LabError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
