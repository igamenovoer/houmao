#!/usr/bin/env python3
"""Provision, inspect, verify, and clean up a four-agent CCCC CUDA cooperation run."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.metadata
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any

import httpx

BUNDLE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MANIFEST = BUNDLE_ROOT / "manifest.toml"
DEFAULT_MANAGER = REPO_ROOT / ".pixi/envs/default/bin/houmao-mgr"
DEFAULT_CCCC = REPO_ROOT / ".pixi/envs/default/bin/houmao-cccc"
_TMUX_ENV_KEYS = ("TMUX", "TMUX_PANE", "TMUX_TMPDIR")
_PEERS = ("peer-a", "peer-b", "peer-c", "peer-d")
_RECEIVER_PROTOCOL_VERSION = 2


class LabError(RuntimeError):
    """Report one actionable four-agent harness failure."""


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    """Read one JSON object without reflecting sensitive contents on failure."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LabError(f"Cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise LabError(f"{label} is not a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    """Publish one owner-private JSON document atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".cuda-coop-", dir=path.parent)
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
    """Resolve the selected houmao-mgr executable."""
    selected = os.environ.get("HOUMAO_MGR")
    path = Path(selected).expanduser() if selected else DEFAULT_MANAGER
    if not path.is_file():
        raise LabError(f"Selected houmao-mgr is unavailable: {path}")
    return path


def cccc_path() -> Path:
    """Resolve the houmao-cccc executable beside the selected manager."""
    selected = os.environ.get("HOUMAO_CCCC")
    path = Path(selected).expanduser() if selected else manager_path().with_name("houmao-cccc")
    if not path.is_file():
        raise LabError(f"Selected houmao-cccc is unavailable: {path}")
    return path


def detect_gpu_arch(configured_arch: str) -> dict[str, Any]:
    """Resolve CUDA sm_XX target architecture from manifest or nvidia-smi."""
    if configured_arch and configured_arch != "auto":
        return {"arch": configured_arch, "source": "manifest", "gpu_name": None}
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,compute_cap", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise LabError("Unable to detect local NVIDIA GPU via nvidia-smi")
    first_line = result.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in first_line.split(",")]
    if len(parts) < 2 or "." not in parts[1]:
        raise LabError(f"Unexpected nvidia-smi compute_cap output: {first_line}")
    major, minor = parts[1].split(".", 1)
    return {
        "arch": f"sm_{major}{minor}",
        "source": "nvidia-smi",
        "gpu_name": parts[0],
        "compute_cap": parts[1],
    }


def load_manifest(manifest_path: Path, problem_override: str | None = None) -> dict[str, Any]:
    """Load manifest.toml and resolve the selected problem definition."""
    resolved_manifest = manifest_path.expanduser().resolve()
    try:
        raw = tomllib.loads(resolved_manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise LabError(f"Cannot parse manifest TOML: {resolved_manifest}") from exc
    if raw.get("schema_version") != 1:
        raise LabError(f"Unsupported manifest schema_version: {raw.get('schema_version')}")
    problems = raw.get("problems")
    if not isinstance(problems, dict) or not problems:
        raise LabError("Manifest defines no [problems.<id>] entries")
    selected_id = problem_override or raw.get("default_problem")
    if not isinstance(selected_id, str) or selected_id not in problems:
        valid = ", ".join(sorted(problems.keys()))
        raise LabError(f"Unknown problem '{selected_id}'. Available in manifest: {valid}")
    problem = dict(problems[selected_id])
    workloads = problem.get("expected_workloads")
    if not (
        isinstance(workloads, list)
        and workloads
        and all(isinstance(name, str) and name for name in workloads)
        and len(set(workloads)) == len(workloads)
    ):
        raise LabError(f"Problem '{selected_id}' must declare distinct expected_workloads")
    source_rel = problem.get("source_dir")
    if not isinstance(source_rel, str):
        raise LabError(f"Problem '{selected_id}' is missing source_dir")
    source_dir = (resolved_manifest.parent / source_rel).resolve()
    required_files = (
        "kernel_api.cuh",
        "driver.cu",
        "solution_starter.cu",
        "Makefile",
        "design-brief.md",
    )
    missing = [name for name in required_files if not (source_dir / name).is_file()]
    if missing:
        raise LabError(f"Problem source_dir {source_dir} is missing: {', '.join(missing)}")
    team = raw.get("team") or {}
    team_model = team.get("model")
    if not isinstance(team_model, str) or not team_model.strip():
        raise LabError("Manifest team.model must name the model for all four peers")
    peers = tuple(team.get("peers") or _PEERS)
    if peers != _PEERS:
        raise LabError(f"Manifest team.peers must be {list(_PEERS)}, got {list(peers)}")
    if team.get("duration_seconds") != 300:
        raise LabError("The team shares one 300-second window")
    actors = {peer: peer for peer in _PEERS}
    cuda_cfg = raw.get("cuda") or {}
    delivery_cfg = raw.get("delivery") or {}
    return {
        "manifest_path": str(resolved_manifest),
        "default_problem": str(raw.get("default_problem")),
        "problem_override": problem_override,
        "selected_problem": selected_id,
        "available_problems": sorted(problems.keys()),
        "problem": {**problem, "source_dir": str(source_dir)},
        "cuda": {
            "arch_config": str(cuda_cfg.get("arch", "auto")),
            "nvcc": str(cuda_cfg.get("nvcc", "nvcc")),
        },
        "delivery": {
            "default_policy": str(delivery_cfg.get("default_policy", "batch")),
            "quiet_interval_seconds": float(delivery_cfg.get("quiet_interval_seconds", 6.0)),
            "max_wait_seconds": float(delivery_cfg.get("max_wait_seconds", 15.0)),
        },
        "peers": list(_PEERS),
        "team_model": team_model,
        "actors": actors,
        "duration_seconds": team["duration_seconds"],
    }


def execution_identity() -> dict[str, Any]:
    """Capture checkout and selected-tool identity for evidence correlation."""

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
    """Run one houmao-mgr operation and parse its JSON response."""
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


def pool_selection(
    run: dict[str, Any], *, peer: str, mode: str, expected_model: str
) -> dict[str, str]:
    """Check the prepared fixture's slot and model against the team manifest."""
    config = run.get("configuration")
    if not isinstance(config, dict) or (config.get("mode"), config.get("surface")) != (
        mode,
        "manager",
    ):
        raise LabError(f"Peer {peer} requires a manager fixture in {mode} mode")
    key = run.get("pool_key")
    if not isinstance(key, str) or not key or run.get("pool_slot") != peer:
        raise LabError(f"Prepare peer {peer} with fixture.py prepare --pool-slot {peer}")
    model = config.get("model")
    if not isinstance(model, str) or model != expected_model:
        raise LabError(
            f"Peer {peer} uses model {model!r} from pool key {key!r}, expected {expected_model!r}"
        )
    return {"pool_key": key, "pool_slot": peer, "model": model}


def load_meta(path: Path, *, complete: bool = True) -> dict[str, Any]:
    """Load run metadata and require configured identities when complete."""
    payload = read_json(path, label="run metadata")
    required = ["runs", "agent_ids", "endpoint", "tag", "manifest", "workspaces"]
    if complete:
        required.extend(["group_id", "actors", "bindings", "gateways", "plugin_configs"])
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise LabError(f"Run metadata is missing: {', '.join(missing)}")
    return payload


def peer_run(meta: dict[str, Any], peer: str) -> tuple[Path, str]:
    """Resolve one peer's fixture directory and managed agent ID."""
    return Path(str(meta["runs"][peer])), str(meta["agent_ids"][peer])


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
    """Extract one CCCC operator response envelope safely."""
    if response.status_code != 200:
        raise LabError(f"CCCC operator request returned HTTP {response.status_code}")
    envelope = response.json()
    if not isinstance(envelope, dict) or not envelope.get("ok"):
        raise LabError("CCCC operator request returned an unsuccessful envelope")
    result = envelope.get("result")
    if not isinstance(result, dict):
        raise LabError("CCCC operator request returned an invalid result")
    return result


def gateway_get(meta: dict[str, Any], peer: str, path: str) -> dict[str, Any]:
    """Read one public gateway route without ambient proxy or credentials."""
    base = str(meta["gateways"][peer]).rstrip("/")
    try:
        response = httpx.get(base + path, trust_env=False, timeout=20)
    except httpx.HTTPError as exc:
        raise LabError(f"Gateway {peer} is unavailable") from exc
    if response.status_code != 200:
        raise LabError(f"Gateway {peer} {path} returned HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise LabError(f"Gateway {peer} {path} returned an invalid response")
    return payload


def live_observation(meta: dict[str, Any], peer: str) -> dict[str, Any]:
    """Project current Web or headless native readiness from public status."""
    state = gateway_get(meta, peer, "/v1/status")
    web = state.get("web")
    if not isinstance(web, dict):
        web = {}
    readiness: dict[str, Any] = {}
    if not web:
        readiness = gateway_get(meta, peer, "/v1/control/headless/state")
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


def cccc_json(meta: dict[str, Any], peer: str, arguments: list[str]) -> dict[str, Any]:
    """Run one local houmao-cccc CLI command against a peer's gateway."""
    run_dir, _ = peer_run(meta, peer)
    command = [str(cccc_path()), "--gateway-url", str(meta["gateways"][peer]), *arguments]
    result = subprocess.run(
        command, env=run_env(run_dir), capture_output=True, text=True, check=False, timeout=60
    )
    if result.returncode != 0:
        raise LabError(
            f"houmao-cccc {arguments[0]} failed for peer {peer}: "
            f"{(result.stdout or result.stderr).strip()}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LabError("houmao-cccc returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise LabError("houmao-cccc returned an unexpected JSON shape")
    return payload


def iter_history(meta: dict[str, Any], peer: str, *, limit: int = 20) -> Iterator[dict[str, Any]]:
    """Read one Actor's history newest first, keeping its cursor and page size together."""
    query = ["chat", "history", "--limit", str(limit)]
    arguments = query
    seen_cursors: set[str] = set()
    while True:
        page = cccc_json(meta, peer, arguments)
        messages = page.get("messages")
        if not isinstance(messages, list) or not isinstance(page.get("has_more"), bool):
            raise LabError(f"Invalid CCCC history page for {peer}")
        for message in messages:
            event_id = message.get("event_id") if isinstance(message, dict) else None
            if not isinstance(event_id, str) or not event_id:
                raise LabError(f"CCCC history for {peer} contains a message without an event ID")
            yield message
        if not page["has_more"]:
            return
        cursor = page.get("cursor")
        if not messages or not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
            raise LabError(f"CCCC history pagination did not advance for {peer}")
        seen_cursors.add(cursor)
        arguments = [*query, "--cursor", cursor]


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
    """Require attachment to preserve the live native body."""
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


def session_files(run_dir: Path, *, client: str, before_kickoff: bool = False) -> list[Path]:
    """Return native Web journals from this fixture's managed homes."""
    journal = {"dsh": "session.v4.jsonl", "kimi": "wire.jsonl"}.get(client)
    if journal is None:
        raise LabError(f"Native transcript capture is unavailable for Web client {client}")
    homes = (run_dir / "runtime" / "homes").resolve()
    files = sorted(
        (path for path in homes.rglob(journal) if path.is_file() and path.resolve() == path),
        key=lambda path: path.stat().st_mtime,
    )
    if before_kickoff and not files:
        return []
    if client == "kimi":
        run = load_run(run_dir)
        manifest = read_json(
            Path(run["identity"]["manifest_path"]), label="managed session manifest"
        )
        evidence = (manifest.get("backend_state") or {}).get("evidence_path")
        main = Path(evidence) if isinstance(evidence, str) else None
        if main is None or main not in files or main.parts[-3:] != ("agents", "main", "wire.jsonl"):
            raise LabError("Kimi Web manifest does not select a main journal in the fixture home")
        files.remove(main)
        files.append(main)
    return files


def wait_binding(meta: dict[str, Any], peer: str, *, timeout: float = 60) -> dict[str, Any]:
    """Wait for the selected Actor receiver to negotiate and acquire its lease."""
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            last = cccc_json(meta, peer, ["binding"])
            if last.get("connection") == "connected":
                return last
        except LabError:
            pass
        time.sleep(0.25)
    raise LabError(f"CCCC receiver {peer} did not connect; last phase={last.get('connection')}")


def update_gateway_run(run_dir: Path, attached: dict[str, Any]) -> str:
    """Persist attached gateway coordinates in run.json."""
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
    """Verify a selected local CCCC service process against its build receipt."""
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
        "0004-gateway-queue-reads.patch",
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


def workspace_makefile(source_dir: Path, arch: str) -> bytes:
    """Render the locked Makefile bytes for the selected GPU architecture."""
    template = (source_dir / "Makefile").read_text(encoding="utf-8")
    return re.sub(r"^ARCH\s*\?=.*$", f"ARCH ?= {arch}", template, flags=re.MULTILINE).encode()


def seed_cuda_workspace(source_dir: Path, workspace_dir: Path, arch: str) -> None:
    """Copy neutral problem files into the peer working directory."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    copies = {
        "kernel_api.cuh": "kernel_api.cuh",
        "driver.cu": "driver.cu",
        "solution_starter.cu": "solution.cu",
        "design-brief.md": "design-brief.md",
    }
    for src_name, dst_name in copies.items():
        shutil.copy2(source_dir / src_name, workspace_dir / dst_name)
    (workspace_dir / "Makefile").write_bytes(workspace_makefile(source_dir, arch))


def check_cuda_toolchain(cuda_cfg: dict[str, Any]) -> dict[str, Any]:
    """Verify nvcc and local GPU visibility without writing to repo."""
    gpu = detect_gpu_arch(str(cuda_cfg.get("arch_config", "auto")))
    nvcc = str(cuda_cfg["nvcc"])
    result = subprocess.run([nvcc, "--version"], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise LabError(f"{nvcc} failed --version")
    return {"gpu": gpu, "tools": {"nvcc": result.stdout.strip()}}


def command_show_manifest(args: argparse.Namespace) -> int:
    """Resolve and print manifest.toml and GPU arch as JSON."""
    manifest = load_manifest(args.manifest, args.problem)
    manifest["resolved_gpu"] = detect_gpu_arch(manifest["cuda"]["arch_config"])
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def command_configure(args: argparse.Namespace) -> int:
    """Provision one 4-actor CCCC Group, seed the CUDA workspace, and attach gateways."""
    manifest = load_manifest(args.manifest, args.problem)
    gpu_info = detect_gpu_arch(manifest["cuda"]["arch_config"])
    manifest["resolved_gpu"] = gpu_info

    run_dirs = {
        peer: Path(
            read_json(args.evidence_root / f"{peer}-prepare.json", label="fixture receipt")[
                "run_dir"
            ]
        ).resolve()
        for peer in _PEERS
    }
    runs = {peer: load_run(path) for peer, path in run_dirs.items()}
    model_pool = {
        peer: pool_selection(
            runs[peer],
            peer=peer,
            mode="web",
            expected_model=manifest["team_model"],
        )
        for peer in _PEERS
    }
    agent_ids = {peer: str(runs[peer]["identity"]["agent_id"]) for peer in _PEERS}
    if len(set(agent_ids.values())) != len(_PEERS):
        raise LabError("All four managed CCCC owners must have distinct agent IDs")

    if len({entry["pool_key"] for entry in model_pool.values()}) != 1:
        raise LabError("Use the same Web model pool entry for all peers")
    workspaces = {peer: Path(run["workdir"]).resolve() for peer, run in runs.items()}
    if len(set(workspaces.values())) != len(_PEERS) or any(
        path != run_dirs[peer] / "workdir" for peer, path in workspaces.items()
    ):
        raise LabError("Each fixture needs its own physical working directory")
    private_parent = args.private_root.expanduser().resolve()
    if private_parent.is_relative_to(REPO_ROOT):
        raise LabError("CCCC_PRIVATE_ROOT must be outside the checkout")
    tag = "cuda-coop-" + secrets.token_hex(6)
    private_run = private_parent / tag
    if private_run.exists():
        raise LabError(f"Private run directory already exists: {private_run}")

    for workspace in workspaces.values():
        seed_cuda_workspace(Path(manifest["problem"]["source_dir"]), workspace, gpu_info["arch"])

    meta: dict[str, Any] = {
        "schema_version": 1,
        "execution_identity": execution_identity(),
        "status": "provisioning",
        "tag": tag,
        "endpoint": args.endpoint.rstrip("/"),
        "manifest": manifest,
        "workspaces": {peer: str(path) for peer, path in workspaces.items()},
        "runs": {peer: str(path) for peer, path in run_dirs.items()},
        "model_pool": model_pool,
        "agent_ids": agent_ids,
        "actors": manifest["actors"],
        "group_id": None,
        "grants": {},
        "bindings": {},
        "gateways": {},
        "plugin_configs": {},
        "private_run": str(private_run),
        "evidence_root": str(args.evidence_root.resolve()),
        "tmux_sockets": {peer: runs[peer].get("tmux_socket_path") for peer in _PEERS},
        "body_before": {peer: body_snapshot(run_dirs[peer]) for peer in _PEERS},
    }
    write_json(args.run_meta, meta)

    try:
        private_run.mkdir(parents=True, mode=0o700)
        private_run.chmod(0o700)
        if args.service_runtime or args.provider_binary:
            if not args.service_runtime or not args.provider_binary:
                raise LabError("Select both --service-runtime and --provider-binary, or neither")
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

            for peer in _PEERS:
                run_dir, agent_id = peer_run(meta, peer)
                actor_id = str(meta["actors"][peer])
                provider_result(
                    provider.post(
                        f"/api/v1/groups/{group_id}/actors",
                        json={"actor_id": actor_id, "runtime": "custom", "command": ["/bin/true"]},
                    )
                )
                credential = private_run / f"{peer}.json"
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
                    raise LabError(f"CCCC grant export failed for peer {peer}")
                grant = json.loads(provision.stdout)
                meta["grants"][peer] = {
                    "grant_id": grant["grant_id"],
                    "credential_file": str(credential),
                    "actor_generation": grant["actor_generation"],
                }
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
                meta["plugin_configs"][peer] = str(selection)
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
                meta["gateways"][peer] = update_gateway_run(run_dir, attached)
                write_json(args.run_meta, meta)
                binding = wait_binding(meta, peer)
                if (
                    binding.get("agent_id") != agent_id
                    or binding.get("group_id") != group_id
                    or binding.get("actor_id") != actor_id
                ):
                    raise LabError(f"CCCC binding identity mismatch for peer {peer}")
                meta["bindings"][peer] = binding
                after = body_snapshot(run_dir)
                assert_same_body(meta["body_before"][peer], after)
                meta.setdefault("body_after", {})[peer] = after
                write_json(args.run_meta, meta)

        members = cccc_json(meta, _PEERS[0], ["members", "--group", str(meta["group_id"])])
        expected_actors = set(meta["actors"].values())
        member_ids = {
            item.get("id") for item in members.get("members", []) if isinstance(item, dict)
        }
        if member_ids != expected_actors:
            raise LabError(
                f"CCCC Group membership mismatch: expected {sorted(expected_actors)}, "
                f"got {sorted(str(x) for x in member_ids)}"
            )

        for peer in _PEERS:
            run_dir, _ = peer_run(meta, peer)
            peers = {r: meta["actors"][r] for r in _PEERS if r != peer}
            workdir = run_dir / "workdir"
            write_json(
                workdir / "cccc-brief.json",
                {
                    "cccc_cli": str(cccc_path()),
                    "gateway_url": meta["gateways"][peer],
                    "plugin_instance": "cccc",
                    "binding_id": meta["bindings"][peer]["binding_id"],
                    "group_id": meta["group_id"],
                    "actor_id": meta["actors"][peer],
                    "peer": peer,
                    "peers": peers,
                    "workspace_dir": ".",
                    "cuda_arch": gpu_info["arch"],
                    "protocol": "Use CCCC chat for team discussion",
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
                "problem_override": manifest["problem_override"],
                "selected_problem": manifest["selected_problem"],
                "workspaces": meta["workspaces"],
                "gpu": gpu_info,
                "agents": agent_ids,
                "model_pool": model_pool,
                "actors": meta["actors"],
                "gateways": meta["gateways"],
                "run_meta": str(args.run_meta),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    """Verify CUDA toolchain, provider, 4 gateways, native bodies, bindings, and private working directories."""
    meta = load_meta(args.run_meta)
    if meta.get("status") != "configured":
        raise LabError(f"Run is not configured: {meta.get('status')}")
    model_pool = meta.get("model_pool")
    if not isinstance(model_pool, dict) or set(model_pool) != set(_PEERS):
        raise LabError("Run metadata is missing model pool selections for the four peers")
    cuda_health = check_cuda_toolchain(meta["manifest"]["cuda"])

    service = meta.get("service_identity")
    if service:
        os.kill(int(service["pid"]), 0)
        if Path(f"/proc/{service['pid']}/exe").resolve() != Path(service["binary_path"]):
            raise LabError("CCCC service executable changed")

    with provider_client(meta) as provider:
        health = provider_result(provider.get("/api/v1/health"))

    result: dict[str, Any] = {
        "status": "healthy",
        "group_id": meta["group_id"],
        "selected_problem": meta["manifest"]["selected_problem"],
        "cuda": cuda_health,
        "provider_health": health,
        "agents": {},
    }
    expected_actors = set(meta["actors"].values())
    for peer in _PEERS:
        run_dir, agent_id = peer_run(meta, peer)
        workdir = run_dir / "workdir"
        brief = read_json(workdir / "cccc-brief.json", label=f"{peer} workspace brief")
        if brief.get("workspace_dir") != "." or workdir != Path(meta["workspaces"][peer]):
            raise LabError(f"Invalid working directory for {peer}")
        for filename in (
            "kernel_api.cuh",
            "driver.cu",
            "solution.cu",
            "Makefile",
            "design-brief.md",
        ):
            if not (workdir / filename).is_file():
                raise LabError(f"Seeded workspace for {peer} is missing {filename}")
        selection = pool_selection(
            load_run(run_dir),
            peer=peer,
            mode="web",
            expected_model=meta["manifest"]["team_model"],
        )
        if selection != model_pool[peer]:
            raise LabError(f"Prepared model pool selection changed for peer {peer}")
        state = live_observation(meta, peer)
        if (
            state.get("gateway_health") != "healthy"
            or state.get("native_surface_eligibility") != "ready"
            or state.get("can_accept_prompt_now") is not True
            or state.get("host_process_alive") is not True
        ):
            raise LabError(f"Managed agent {peer} is not healthy")
        binding = cccc_json(meta, peer, ["binding"])
        expected = meta["bindings"][peer]
        if (
            binding.get("connection") != "connected"
            or binding.get("binding_id") != expected.get("binding_id")
            or binding.get("agent_id") != agent_id
            or binding.get("group_id") != meta["group_id"]
            or binding.get("actor_id") != meta["actors"][peer]
        ):
            raise LabError(f"CCCC binding {peer} is not connected to expected owner")
        capabilities = cccc_json(meta, peer, ["capabilities"])
        members = cccc_json(meta, peer, ["members", "--group", str(meta["group_id"])])
        member_ids = {
            item.get("id") for item in members.get("members", []) if isinstance(item, dict)
        }
        if member_ids != expected_actors:
            raise LabError(
                f"Peer {peer} sees unexpected Group members: {sorted(str(x) for x in member_ids)}"
            )
        current_body = body_snapshot(run_dir)
        assert_same_body(meta["body_before"][peer], current_body)
        result["agents"][peer] = {
            "agent_id": agent_id,
            **selection,
            "actor_id": meta["actors"][peer],
            "availability": state.get("availability"),
            "active_execution": state.get("active_execution"),
            "binding_id": binding.get("binding_id"),
            "capabilities": capabilities,
            "body": current_body,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def apply_delivery_for_peer(
    meta: dict[str, Any],
    peer: str,
    *,
    policy: str,
    quiet_interval: float,
    max_wait: float,
    timeout: float,
) -> dict[str, Any]:
    """Set receiver delivery policy on one peer and await active convergence."""
    path = "/v1/plugins/cccc/delivery"
    before = gateway_get(meta, peer, path)
    settings: dict[str, Any] = {"transport": "pull"}
    if policy != "pull":
        settings = {"transport": "push", "push_policy": policy}
        if policy == "batch":
            settings.update(quiet_interval=quiet_interval, max_wait=max_wait)
    response = httpx.put(
        str(meta["gateways"][peer]).rstrip("/") + path,
        json={"revision": before["revision"], "settings": settings},
        trust_env=False,
        timeout=20,
    )
    if response.status_code != 200:
        raise LabError(f"Setting delivery on {peer} returned HTTP {response.status_code}")
    revision = response.json()["revision"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        observed = gateway_get(meta, peer, path)
        if observed.get("revision") != revision:
            raise LabError(f"Delivery settings on {peer} changed unexpectedly")
        if observed.get("transition") == "active" and observed.get("effective") == observed.get(
            "desired"
        ):
            return observed
        time.sleep(0.25)
    raise LabError(f"Timed out waiting for delivery policy on {peer}")


def command_delivery(args: argparse.Namespace) -> int:
    """Set effective delivery policy for one peer or all four peers."""
    meta = load_meta(args.run_meta)
    targets = _PEERS if args.peer == "all" else (args.peer,)
    results = {
        peer: apply_delivery_for_peer(
            meta,
            peer,
            policy=args.policy,
            quiet_interval=args.quiet_interval,
            max_wait=args.max_wait,
            timeout=args.timeout,
        )
        for peer in targets
    }
    print(json.dumps({"status": "active", "peers": results}, indent=2, sort_keys=True))
    return 0


def workloads_passed(workloads: object, expected: list[str]) -> bool:
    """Require one accurate, input-preserving result per named workload."""
    if not isinstance(workloads, list) or len(workloads) != len(expected):
        return False
    names: list[str] = []
    for row in workloads:
        if not isinstance(row, dict) or row.get("passed") is not True:
            return False
        if row.get("inputs_immutable") is not True or not isinstance(row.get("name"), str):
            return False
        names.append(row["name"])
    return sorted(names) == sorted(expected)


def verify_candidate(
    meta: dict[str, Any], submitted_src: Path, evidence_dir: Path, verify_root: Path
) -> int:
    """Compile and verify submitted solution.cu against the untouched locked driver."""
    manifest = meta["manifest"]
    problem = manifest["problem"]
    source_dir = Path(str(problem["source_dir"]))
    evidence_dir.mkdir(parents=True, exist_ok=True)
    verify_root.mkdir(parents=True, exist_ok=True)
    verify_dir = Path(tempfile.mkdtemp(prefix="build-", dir=verify_root))

    # Copy untouched locked driver + API header + ONLY submitted solution.cu.
    shutil.copy2(source_dir / "kernel_api.cuh", verify_dir / "kernel_api.cuh")
    shutil.copy2(source_dir / "driver.cu", verify_dir / "driver.cu")
    shutil.copy2(submitted_src, verify_dir / "solution.cu")

    # Save immutable evidence copies of submitted solution and diff vs starter.
    captured = evidence_dir / "submitted-solution.cu"
    shutil.copy2(verify_dir / "solution.cu", captured)
    starter_lines = (
        (source_dir / "solution_starter.cu").read_text(encoding="utf-8").splitlines(keepends=True)
    )
    submitted_lines = captured.read_text(encoding="utf-8").splitlines(keepends=True)
    diff_text = "".join(
        difflib.unified_diff(
            starter_lines,
            submitted_lines,
            fromfile="solution_starter.cu",
            tofile="submitted-solution.cu",
        )
    )
    (evidence_dir / "solution-diff.patch").write_text(diff_text, encoding="utf-8")

    arch = str(manifest["resolved_gpu"]["arch"])
    nvcc = str(manifest["cuda"]["nvcc"])
    binary = verify_dir / "verify_kernel"
    compile_cmd = [
        nvcc,
        "-O3",
        "-std=c++17",
        f"-arch={arch}",
        "--use_fast_math",
        "-DEXTENDED_SHAPES=1",
        str(verify_dir / "driver.cu"),
        str(verify_dir / "solution.cu"),
        "-o",
        str(binary),
    ]
    compile_res = subprocess.run(
        compile_cmd, capture_output=True, text=True, check=False, timeout=180
    )
    report: dict[str, Any] = {
        "problem": manifest["selected_problem"],
        "arch": arch,
        "verify_dir": str(verify_dir),
        "solution_changed_from_starter": bool(diff_text.strip()),
        "compile_returncode": compile_res.returncode,
        "compile_stderr": compile_res.stderr.strip(),
        "min_speedup_target": problem.get("min_speedup"),
        "stretch_speedup_target": problem.get("stretch_speedup"),
    }

    if compile_res.returncode != 0:
        report["status"] = "compile_failed"
        write_json(evidence_dir / "independent-verify.json", report, mode=0o644)
        return 1

    run_res = subprocess.run(
        [str(binary), "--json"], capture_output=True, text=True, check=False, timeout=300
    )
    report["run_returncode"] = run_res.returncode
    report["run_stderr"] = run_res.stderr.strip()
    try:
        driver_json = json.loads(run_res.stdout)
        if not isinstance(driver_json, dict):
            raise ValueError("Expected a driver result object")
    except ValueError:
        report["status"] = "invalid_driver_output"
        report["raw_stdout"] = run_res.stdout[:2000]
        write_json(evidence_dir / "independent-verify.json", report, mode=0o644)
        return 1

    report["driver_result"] = driver_json
    report["workloads_passed"] = workloads_passed(
        driver_json.get("workloads"), problem["expected_workloads"]
    )
    driver_passed = (
        run_res.returncode == 0
        and driver_json.get("problem") == manifest["selected_problem"]
        and driver_json.get("passed") is True
        and driver_json.get("inputs_immutable") is True
        and report["workloads_passed"]
    )
    speedup = driver_json.get("geomean_speedup")
    if (
        not isinstance(speedup, (int, float))
        or isinstance(speedup, bool)
        or not math.isfinite(speedup)
    ):
        speedup = 0.0
    report["meets_gt_1x"] = speedup > 1.0
    report["meets_min_speedup_target"] = speedup >= float(problem.get("min_speedup", 3.0))
    report["meets_stretch_speedup_target"] = speedup >= float(problem.get("stretch_speedup", 10.0))
    report["status"] = "passed" if driver_passed else "failed"
    write_json(evidence_dir / "independent-verify.json", report, mode=0o644)
    return int(report["status"] != "passed")


_KICKOFF = (
    "You are one of four peers working on the same CUDA kernel. This is your private working "
    "directory. Your team has five minutes to implement the target kernel in solution.cu as "
    "efficiently as you can while preserving the correctness requirements in design-brief.md. "
    "Use CCCC for team discussion whenever you choose."
)
_SOURCES = ("solution.cu", "driver.cu", "kernel_api.cuh", "Makefile")


def journal_offsets(run: Path, *, before_kickoff: bool = False) -> dict[str, int]:
    """Record append-only native journal positions for this peer's fixture."""
    client = load_run(run)["configuration"]["client"]
    files = session_files(run, client=client, before_kickoff=before_kickoff)
    return {str(path.relative_to(run)): path.stat().st_size for path in files}


def capture_peer(
    meta: dict[str, Any], peer: str, directory: Path, cutoff_ns: int | None = None
) -> dict[str, Any]:
    """Bound native journals by byte offset and freeze the peer's source at the deadline."""
    before = cutoff_ns is None
    result: dict[str, Any] = {"observed_ns": time.time_ns(), "journals": {}, "sources": {}}
    run = Path(meta["runs"][peer])
    try:
        result["journals"] = journal_offsets(run, before_kickoff=before)
    except (LabError, OSError) as exc:
        result["journal_error"] = str(exc)
    for name in _SOURCES:
        path = Path(meta["workspaces"][peer]) / name
        try:
            if path.is_symlink() or not path.is_file():
                raise LabError("Missing regular source file")
            with path.open("rb") as stream:
                first = os.fstat(stream.fileno())
                data = stream.read()
                last = os.fstat(stream.fileno())
            if (
                first.st_mtime_ns != last.st_mtime_ns
                or len(data) != last.st_size
                or (cutoff_ns is not None and max(last.st_ctime_ns, last.st_mtime_ns) > cutoff_ns)
            ):
                raise LabError("No stable version attributable to the cutoff")
            result["sources"][name] = {"sha256": hashlib.sha256(data).hexdigest()}
            if not before:
                target = directory / "cutoff" / peer / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        except (LabError, OSError) as exc:
            result["sources"][name] = {"error": str(exc)}
    result["finished_ns"] = time.time_ns()
    return result


def watch_peer(
    meta: dict[str, Any], peer: str, directory: Path, stop: Event, queue_enabled: bool
) -> None:
    """Sample public receiver state without consuming messages or holding up the clock."""
    with (directory / f"{peer}-observations.jsonl").open("x", encoding="utf-8") as stream:
        while not stop.is_set():
            sample: dict[str, Any] = {"started_ns": time.time_ns()}
            for key, route in (
                ("state", "/v1/status"),
                ("binding", "/v1/plugins/cccc/binding"),
                ("queue", "/v1/plugins/cccc/chat/queue?wait_seconds=0"),
            ):
                if key == "queue" and not queue_enabled:
                    continue
                try:
                    response = gateway_get(meta, peer, route)
                    if key == "binding":
                        response = {
                            k: response.get(k)
                            for k in ("connection", "binding_id", "actor_id", "group_id")
                        }
                    if key == "queue":
                        response = {
                            k: response.get(k)
                            for k in ("open_batch_count", "additional_queued", "batches")
                        }
                    sample[key] = response
                except (LabError, ValueError) as exc:
                    sample[key] = {"error": str(exc)}
            try:
                sample["journals"] = journal_offsets(Path(meta["runs"][peer]), before_kickoff=True)
            except (LabError, OSError) as exc:
                sample["journal_error"] = str(exc)
            sample["finished_ns"] = time.time_ns()
            stream.write(json.dumps(sample) + "\n")
            stream.flush()
            stop.wait(10)


def peer_control(
    meta: dict[str, Any], peer: str, arguments: list[str], timeout: float
) -> dict[str, Any]:
    """Record the dispatch time and the manager response for one peer independently."""
    run, agent_id = peer_run(meta, peer)
    result: dict[str, Any] = {"started_ns": time.time_ns()}
    try:
        result["response"] = manager_json(
            run_env(run), ["agents", "single", "--agent-id", agent_id, *arguments], timeout=timeout
        )
    except (LabError, OSError, ValueError) as exc:
        result["error"] = str(exc)
    result["finished_ns"] = time.time_ns()
    return result


def command_window(args: argparse.Namespace) -> int:
    """Release the four peers once and seal their evidence at the common deadline."""
    meta = load_meta(args.run_meta)
    directory = Path(meta["evidence_root"]) / "window"
    directory.mkdir(mode=0o700)
    history = {peer: list(iter_history(meta, peer)) for peer in _PEERS}
    write_json(directory / "history-before.json", history)
    if any(history.values()):
        raise LabError("Begin with a fresh group with empty chat history")
    baseline: dict[str, Any] = {}
    queue_enabled: dict[str, bool] = {}
    for peer in _PEERS:
        baseline[peer] = capture_peer(meta, peer, directory)
        state = live_observation(meta, peer)
        baseline[peer]["state"] = state
        caps = gateway_get(meta, peer, "/v1/plugins/cccc/capabilities")
        queue_enabled[peer] = caps.get("chat_queue") is True
        baseline[peer]["queue"] = (
            gateway_get(meta, peer, "/v1/plugins/cccc/chat/queue?wait_seconds=0")
            if queue_enabled[peer]
            else {"available": False}
        )
        write_json(directory / "baseline.json", baseline)
        if (
            caps.get("available") is not True
            or state["can_accept_prompt_now"] is not True
            or baseline[peer].get("journal_error")
            or any("error" in item for item in baseline[peer]["sources"].values())
            or baseline[peer]["queue"].get("batches")
            or baseline[peer]["queue"].get("additional_queued")
            or baseline[peer]["queue"].get("open_batch_count")
        ):
            raise LabError(f"{peer} is not ready for a clean release")
    seconds = meta["manifest"]["duration_seconds"]
    stop = Event()
    with ThreadPoolExecutor(max_workers=len(_PEERS) * 3) as pool:
        watchers = [
            pool.submit(watch_peer, meta, peer, directory, stop, queue_enabled[peer])
            for peer in _PEERS
        ]
        try:
            start = time.monotonic()
            start_ns = time.time_ns()
            cutoff_ns = start_ns + seconds * 1_000_000_000
            deadline = datetime.fromtimestamp(cutoff_ns / 1e9, UTC).isoformat()
            prompt = f"{_KICKOFF} The deadline is {deadline}."
            kickoffs = {
                p: pool.submit(peer_control, meta, p, ["prompt", "--prompt", prompt], seconds + 10)
                for p in _PEERS
            }
            write_json(
                directory / "release.json",
                {
                    "prompt": prompt,
                    "start_ns": start_ns,
                    "cutoff_ns": cutoff_ns,
                    "duration_seconds": seconds,
                },
            )
            time.sleep(max(0, start + seconds - time.monotonic()))
            stop.set()
            elapsed = time.monotonic() - start
            frozen = {peer: capture_peer(meta, peer, directory, cutoff_ns) for peer in _PEERS}
            write_json(directory / "cutoff.json", frozen)
            write_json(directory / "timer.json", {"elapsed_seconds_at_capture": elapsed})
            interrupts = {p: pool.submit(peer_control, meta, p, ["interrupt"], 30) for p in _PEERS}
            write_json(
                directory / "interrupts.json", {p: job.result() for p, job in interrupts.items()}
            )
            write_json(
                directory / "kickoffs.json", {p: job.result() for p, job in kickoffs.items()}
            )
        finally:
            stop.set()
        for job in watchers:
            job.result()
    print(json.dumps({"window": str(directory), "cutoff_ns": cutoff_ns}))
    return 0


def command_collect(args: argparse.Namespace) -> int:
    """Collect scoped CCCC events, handoff attempts and bounded native journal excerpts."""
    meta = load_meta(args.run_meta)
    directory = Path(meta["evidence_root"]) / "window"
    baseline = read_json(directory / "baseline.json", label="baseline")
    cutoff = read_json(directory / "cutoff.json", label="cutoff")
    errors: list[str] = []
    for peer in _PEERS:
        folder = directory / "communication" / peer
        folder.mkdir(parents=True, exist_ok=True)
        try:
            run = Path(meta["runs"][peer])
            for rel, end in cutoff[peer]["journals"].items():
                start = baseline[peer]["journals"].get(rel, 0)
                with (run / rel).open("rb") as stream:
                    stream.seek(start)
                    data = stream.read(max(0, end - start))
                if end < start or len(data) != end - start:
                    raise LabError(f"Truncated journal {rel}")
                dest = folder / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            if cutoff[peer].get("journal_error") or not cutoff[peer]["journals"]:
                raise LabError("Incomplete native journal evidence")
        except (LabError, OSError) as exc:
            errors.append(f"{peer} journal: {exc}")

        try:
            binding = gateway_get(meta, peer, "/v1/plugins/cccc/binding")
            write_json(
                folder / "binding-after.json", {"observed_ns": time.time_ns(), "binding": binding}
            )
        except (LabError, ValueError) as exc:
            errors.append(f"{peer} final binding: {exc}")
        try:
            messages = list(iter_history(meta, peer))
            write_json(
                folder / "history.json", {"observed_ns": time.time_ns(), "messages": messages}
            )
            for msg in messages:
                if msg.get("by") != meta["actors"][peer]:
                    continue
                try:
                    receipts = cccc_json(
                        meta,
                        peer,
                        ["chat", "deliveries", "--event-ref", msg["event_ref"], "--limit", "100"],
                    )
                    if not isinstance(receipts.get("deliveries"), list) or receipts.get("has_more"):
                        errors.append(f"{peer} {msg['event_id']}: incomplete attempt list")
                    write_json(
                        folder / f"deliveries-{msg['event_id']}.json",
                        {"observed_ns": time.time_ns(), "result": receipts},
                    )
                except (KeyError, LabError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
                    errors.append(f"{peer} {msg['event_id']} deliveries: {exc}")
        except (LabError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{peer} history: {exc}")
    write_json(directory / "collection.json", {"errors": errors})
    print(json.dumps({"window": str(directory), "errors": errors}))
    return int(bool(errors))


def command_verify_cuda(args: argparse.Namespace) -> int:
    """Verify each distinct frozen implementation once and record provenance for all peers."""
    meta = load_meta(args.run_meta)
    directory = Path(meta["evidence_root"]) / "window"
    cutoff = read_json(directory / "cutoff.json", label="cutoff")
    source = Path(meta["manifest"]["problem"]["source_dir"])
    arch = meta["manifest"]["resolved_gpu"]["arch"]
    expected = {
        name: hashlib.sha256(source.joinpath(name).read_bytes()).hexdigest()
        for name in ("driver.cu", "kernel_api.cuh")
    }
    expected["Makefile"] = hashlib.sha256(workspace_makefile(source, arch)).hexdigest()
    peers: dict[str, Any] = {}
    candidates: dict[str, Any] = {}
    for peer in _PEERS:
        hashes = cutoff[peer]["sources"]
        digest = hashes["solution.cu"].get("sha256")
        path = directory / "cutoff" / peer / "solution.cu"
        peers[peer] = {
            "solution_sha256": digest,
            "locked_file_mismatches": [
                name for name, value in expected.items() if hashes[name].get("sha256") != value
            ],
        }
        if (
            not digest
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            peers[peer]["error"] = "Frozen source unavailable or digest mismatch"
        elif digest not in candidates:
            try:
                status = verify_candidate(meta, path, directory / "cuda" / digest, args.verify_dir)
                candidates[digest] = {"exit_code": status}
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                candidates[digest] = {"error": str(exc)}
    report = {"peers": peers, "candidates": candidates}
    write_json(directory / "cuda-results.json", report)
    print(json.dumps(report))
    return int(
        any("error" in item or item["locked_file_mismatches"] for item in peers.values())
        or any(item.get("exit_code") != 0 for item in candidates.values())
    )


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
    """Stop all four owned agents, revoke grants, delete Group, and preserve evidence."""
    meta = load_meta(args.run_meta, complete=False)
    result: dict[str, Any] = {"agents": {}, "disconnects": {}, "grants": {}, "credentials": {}}

    for peer in _PEERS:
        if peer not in meta.get("bindings", {}) or peer not in meta.get("gateways", {}):
            continue
        try:
            result["disconnects"][peer] = cccc_json(
                meta,
                peer,
                [
                    "connection",
                    "disconnect",
                    "--binding-id",
                    str(meta["bindings"][peer]["binding_id"]),
                ],
            )
        except (LabError, KeyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
            result["disconnects"][peer] = {"error": str(exc)}

    for peer in _PEERS:
        run_str = (meta.get("runs") or {}).get(peer)
        agent_id = (meta.get("agent_ids") or {}).get(peer)
        if not run_str or not agent_id:
            continue
        run_dir = Path(str(run_str))
        try:
            receipt = manager_json(
                run_env(run_dir),
                ["agents", "single", "--agent-id", str(agent_id), "stop"],
                timeout=90,
            )
            result["agents"][peer] = {"status": "stopped", "receipt": receipt}
        except (LabError, OSError, ValueError) as exc:
            detail = str(exc)
            already_stopped = "relaunch" in detail and "cleanup" in detail
            result["agents"][peer] = {
                "status": "already_stopped" if already_stopped else "error",
                "error": None if already_stopped else detail,
            }
        result["agents"][peer]["tmux"] = kill_private_tmux(
            run_dir, (meta.get("tmux_sockets") or {}).get(peer)
        )

    if meta.get("group_id"):
        try:
            with provider_client(meta) as provider:
                for peer, grant in (meta.get("grants") or {}).items():
                    response = provider.delete(
                        f"/api/v1/external-receiver/v{_RECEIVER_PROTOCOL_VERSION}/grants/"
                        + str(grant["grant_id"])
                    )
                    result["grants"][peer] = {"http_status": response.status_code}
                response = provider.delete(f"/api/v1/groups/{meta['group_id']}")
                result["group_delete_http_status"] = response.status_code
                verification = provider.get(f"/api/v1/groups/{meta['group_id']}")
                result["group_absent"] = verification.status_code == 404
        except (httpx.HTTPError, OSError) as exc:
            result["group_cleanup_error"] = str(exc)

    private_run = Path(str(meta.get("private_run", "")))
    if private_run and private_run.is_absolute() and not private_run.is_relative_to(REPO_ROOT):
        for peer, grant in (meta.get("grants") or {}).items():
            credential = Path(str(grant["credential_file"]))
            if credential.parent != private_run:
                result["credentials"][peer] = {"status": "unverified", "path": str(credential)}
                continue
            credential.unlink(missing_ok=True)
            result["credentials"][peer] = {"absent": not credential.exists()}
        if not private_run.exists():
            result["private_run_absent"] = True
        else:
            try:
                private_run.rmdir()
                result["private_run_absent"] = not private_run.exists()
            except OSError:
                result["private_run_absent"] = False

    failures: list[str] = []
    if any(item.get("status") == "error" for item in result["agents"].values()):
        failures.append("agent stop")
    if any(
        item.get("tmux", {}).get("status") in {"failed", "unverified"}
        for item in result["agents"].values()
    ):
        failures.append("tmux cleanup")
    if any(item.get("http_status") not in (200, 204, 404) for item in result["grants"].values()):
        failures.append("grant revocation")
    if result.get("private_run_absent") is False:
        failures.append("external credential directory")
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
    """Build the four-agent CUDA cooperation lab CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    show = commands.add_parser("show-manifest")
    show.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    show.add_argument("--problem")
    show.set_defaults(handler=command_show_manifest)

    configure = commands.add_parser("configure")
    configure.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    configure.add_argument("--problem")
    configure.add_argument("--endpoint", required=True)
    configure.add_argument("--private-root", type=Path, required=True)
    configure.add_argument("--service-runtime", type=Path)
    configure.add_argument("--provider-binary", type=Path)
    configure.add_argument("--run-meta", type=Path, required=True)
    configure.add_argument("--evidence-root", type=Path, required=True)
    configure.set_defaults(handler=command_configure)

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--run-meta", type=Path, required=True)
    doctor.set_defaults(handler=command_doctor)

    delivery = commands.add_parser("delivery")
    delivery.add_argument("--run-meta", type=Path, required=True)
    delivery.add_argument("--peer", choices=(*_PEERS, "all"), default="all")
    delivery.add_argument("--policy", choices=("pull", "asap", "batch"), required=True)
    delivery.add_argument("--quiet-interval", type=float, default=6.0)
    delivery.add_argument("--max-wait", type=float, default=15.0)
    delivery.add_argument("--timeout", type=float, default=60.0)
    delivery.set_defaults(handler=command_delivery)

    window = commands.add_parser("run-window")
    window.add_argument("--run-meta", type=Path, required=True)
    window.set_defaults(handler=command_window)

    collect = commands.add_parser("collect")
    collect.add_argument("--run-meta", type=Path, required=True)
    collect.set_defaults(handler=command_collect)

    verify = commands.add_parser("verify-cuda")
    verify.add_argument("--run-meta", type=Path, required=True)
    verify.add_argument("--verify-dir", type=Path, required=True)
    verify.set_defaults(handler=command_verify_cuda)

    stop = commands.add_parser("stop")
    stop.add_argument("--run-meta", type=Path, required=True)
    stop.set_defaults(handler=command_stop)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Translate harness failures into a concise nonzero exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (LabError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
