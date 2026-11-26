#!/usr/bin/env python3
"""Provision, inspect, verify, and clean up a four-agent CCCC CUDA cooperation run."""

from __future__ import annotations

import argparse
import difflib
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
import tomllib
from pathlib import Path
from typing import Any

import httpx

BUNDLE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MANIFEST = BUNDLE_ROOT / "manifest.toml"
DEFAULT_MANAGER = REPO_ROOT / ".pixi/envs/default/bin/houmao-mgr"
DEFAULT_CCCC = REPO_ROOT / ".pixi/envs/default/bin/houmao-cccc"
_TMUX_ENV_KEYS = ("TMUX", "TMUX_PANE", "TMUX_TMPDIR")
_ROLES = ("lead", "algo", "kernel", "profiler")
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
    roles = tuple(team.get("roles") or _ROLES)
    if roles != _ROLES:
        raise LabError(f"Manifest team.roles must be {list(_ROLES)}, got {list(roles)}")
    slots = team.get("slots")
    if not isinstance(slots, dict) or set(slots) != set(_ROLES):
        raise LabError(f"Manifest team.slots must declare all four roles: {', '.join(_ROLES)}")
    for role in _ROLES:
        if slots[role] != {"mode": "web"}:
            raise LabError(f"Manifest team.slots.{role} must declare mode = 'web'")
    actors_cfg = team.get("actors") or {role: role for role in _ROLES}
    actors = {role: str(actors_cfg.get(role, role)) for role in _ROLES}
    cuda_cfg = raw.get("cuda") or {}
    delivery_cfg = raw.get("delivery") or {}
    return {
        "manifest_path": str(resolved_manifest),
        "default_problem": str(raw.get("default_problem")),
        "selected_problem": selected_id,
        "available_problems": sorted(problems.keys()),
        "problem": {**problem, "source_dir": str(source_dir)},
        "cuda": {
            "arch_config": str(cuda_cfg.get("arch", "auto")),
            "nvcc": str(cuda_cfg.get("nvcc", "nvcc")),
            "ncu": str(cuda_cfg.get("ncu", "ncu")),
            "nsys": str(cuda_cfg.get("nsys", "nsys")),
        },
        "delivery": {
            "default_policy": str(delivery_cfg.get("default_policy", "batch")),
            "quiet_interval_seconds": float(delivery_cfg.get("quiet_interval_seconds", 6.0)),
            "max_wait_seconds": float(delivery_cfg.get("max_wait_seconds", 15.0)),
        },
        "roles": list(_ROLES),
        "actors": actors,
        "slots": slots,
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


def pool_selection(run: dict[str, Any], *, role: str, mode: str) -> dict[str, str]:
    """Read the pool selection from a managed fixture prepared for this role."""
    config = run.get("configuration")
    if not isinstance(config, dict) or (config.get("mode"), config.get("surface")) != (
        mode,
        "manager",
    ):
        raise LabError(f"Role {role} requires a manager fixture in {mode} mode")
    key = run.get("pool_key")
    if not isinstance(key, str) or not key or run.get("pool_slot") != role:
        raise LabError(f"Prepare role {role} with fixture.py prepare --pool-slot {role}")
    return {"pool_key": key, "pool_slot": role}


def load_meta(path: Path, *, complete: bool = True) -> dict[str, Any]:
    """Load run metadata and require configured identities when complete."""
    payload = read_json(path, label="run metadata")
    required = ["runs", "agent_ids", "endpoint", "tag", "manifest", "workspace_dir"]
    if complete:
        required.extend(["group_id", "actors", "bindings", "gateways", "plugin_configs"])
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise LabError(f"Run metadata is missing: {', '.join(missing)}")
    return payload


def role_run(meta: dict[str, Any], role: str) -> tuple[Path, str]:
    """Resolve one role's fixture directory and managed agent ID."""
    return Path(str(meta["runs"][role])), str(meta["agent_ids"][role])


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
    """Run one local houmao-cccc CLI command against a role's gateway."""
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


def session_files(run_dir: Path, *, client: str) -> list[Path]:
    """Return native Web journals from this fixture's managed homes."""
    journal = {"dsh": "session.v4.jsonl", "kimi": "wire.jsonl"}.get(client)
    if journal is None:
        raise LabError(f"Native transcript capture is unavailable for Web client {client}")
    homes = (run_dir / "runtime" / "homes").resolve()
    files = sorted(
        (path for path in homes.rglob(journal) if path.is_file() and path.resolve() == path),
        key=lambda path: path.stat().st_mtime,
    )
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


def seed_cuda_workspace(source_dir: Path, workspace_dir: Path, arch: str) -> dict[str, Any]:
    """Copy neutral problem files into the shared run workspace."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    copies = {
        "kernel_api.cuh": "kernel_api.cuh",
        "driver.cu": "driver.cu",
        "solution_starter.cu": "solution.cu",
        "design-brief.md": "design-brief.md",
    }
    for src_name, dst_name in copies.items():
        shutil.copy2(source_dir / src_name, workspace_dir / dst_name)
    makefile_text = (source_dir / "Makefile").read_text(encoding="utf-8")
    makefile_text = re.sub(r"^ARCH\s*\?=.*$", f"ARCH ?= {arch}", makefile_text, flags=re.MULTILINE)
    (workspace_dir / "Makefile").write_text(makefile_text, encoding="utf-8")
    return {
        "workspace_dir": str(workspace_dir),
        "arch": arch,
        "files": sorted([*copies.values(), "Makefile"]),
    }


def check_cuda_toolchain(cuda_cfg: dict[str, Any]) -> dict[str, Any]:
    """Verify nvcc, ncu, nsys, and local GPU visibility without writing to repo."""
    gpu = detect_gpu_arch(str(cuda_cfg.get("arch_config", "auto")))
    versions: dict[str, str] = {}
    for key in ("nvcc", "ncu", "nsys"):
        exe = str(cuda_cfg.get(key, key))
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        if result.returncode != 0:
            raise LabError(f"CUDA tool '{exe}' is unavailable or failed --version")
        lines = [
            line.strip() for line in (result.stdout or result.stderr).splitlines() if line.strip()
        ]
        versions[key] = lines[-1] if lines else "available"
    return {"gpu": gpu, "tools": versions}


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
        "lead": args.run_lead.resolve(),
        "algo": args.run_algo.resolve(),
        "kernel": args.run_kernel.resolve(),
        "profiler": args.run_profiler.resolve(),
    }
    runs = {role: load_run(path) for role, path in run_dirs.items()}
    model_pool = {
        role: pool_selection(runs[role], role=role, mode=manifest["slots"][role]["mode"])
        for role in _ROLES
    }
    agent_ids = {role: str(runs[role]["identity"]["agent_id"]) for role in _ROLES}
    if len(set(agent_ids.values())) != len(_ROLES):
        raise LabError("All four managed CCCC owners must have distinct agent IDs")

    private_parent = args.private_root.expanduser().resolve()
    if private_parent.is_relative_to(REPO_ROOT):
        raise LabError("CCCC_PRIVATE_ROOT must be outside the checkout")
    tag = "cuda-coop-" + secrets.token_hex(6)
    private_run = private_parent / tag
    if private_run.exists():
        raise LabError(f"Private run directory already exists: {private_run}")
    private_run.mkdir(parents=True, mode=0o700)
    private_run.chmod(0o700)

    workspace_dir = args.workspace_dir.expanduser().resolve()
    seeded = seed_cuda_workspace(
        Path(manifest["problem"]["source_dir"]), workspace_dir, gpu_info["arch"]
    )

    meta: dict[str, Any] = {
        "schema_version": 1,
        "execution_identity": execution_identity(),
        "status": "provisioning",
        "tag": tag,
        "endpoint": args.endpoint.rstrip("/"),
        "manifest": manifest,
        "workspace_dir": str(workspace_dir),
        "workspace_seed": seeded,
        "runs": {role: str(path) for role, path in run_dirs.items()},
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
        "tmux_sockets": {role: runs[role].get("tmux_socket_path") for role in _ROLES},
        "body_before": {role: body_snapshot(run_dirs[role]) for role in _ROLES},
    }
    write_json(args.run_meta, meta)

    try:
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

        members = cccc_json(meta, "lead", ["members", "--group", str(meta["group_id"])])
        expected_actors = set(meta["actors"].values())
        member_ids = {
            item.get("id") for item in members.get("members", []) if isinstance(item, dict)
        }
        if member_ids != expected_actors:
            raise LabError(
                f"CCCC Group membership mismatch: expected {sorted(expected_actors)}, "
                f"got {sorted(str(x) for x in member_ids)}"
            )

        for role in _ROLES:
            run_dir, _ = role_run(meta, role)
            peers = {r: meta["actors"][r] for r in _ROLES if r != role}
            write_json(
                run_dir / "workdir" / "cccc-brief.json",
                {
                    "cccc_cli": str(cccc_path()),
                    "gateway_url": meta["gateways"][role],
                    "plugin_instance": "cccc",
                    "binding_id": meta["bindings"][role]["binding_id"],
                    "group_id": meta["group_id"],
                    "actor_id": meta["actors"][role],
                    "role": role,
                    "peers": peers,
                    "workspace_dir": str(workspace_dir),
                    "cuda_arch": gpu_info["arch"],
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
                "selected_problem": manifest["selected_problem"],
                "workspace_dir": str(workspace_dir),
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
    """Verify CUDA toolchain, provider, 4 gateways, native bodies, bindings, and recovery mail."""
    meta = load_meta(args.run_meta)
    if meta.get("status") != "configured":
        raise LabError(f"Run is not configured: {meta.get('status')}")
    model_pool = meta.get("model_pool")
    if not isinstance(model_pool, dict) or set(model_pool) != set(_ROLES):
        raise LabError("Run metadata is missing model pool selections for the four roles")
    cuda_health = check_cuda_toolchain(meta["manifest"]["cuda"])

    workspace = Path(str(meta["workspace_dir"]))
    for filename in ("kernel_api.cuh", "driver.cu", "solution.cu", "Makefile", "design-brief.md"):
        if not (workspace / filename).is_file():
            raise LabError(f"Seeded workspace is missing {filename}: {workspace}")

    service = meta.get("service_identity")
    if service:
        os.kill(int(service["pid"]), 0)
        if Path(f"/proc/{service['pid']}/exe").resolve() != Path(service["binary_path"]):
            raise LabError("CCCC service executable changed")

    with provider_client(meta) as provider:
        health = provider_result(provider.get("/api/v1/health"))

    result: dict[str, Any] = {
        "status": "healthy",
        "selected_problem": meta["manifest"]["selected_problem"],
        "cuda": cuda_health,
        "provider_health": health,
        "agents": {},
    }
    expected_actors = set(meta["actors"].values())
    for role in _ROLES:
        run_dir, agent_id = role_run(meta, role)
        selection = pool_selection(
            load_run(run_dir), role=role, mode=meta["manifest"]["slots"][role]["mode"]
        )
        if selection != model_pool[role]:
            raise LabError(f"Prepared model pool selection changed for role {role}")
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
            raise LabError(f"CCCC binding {role} is not connected to expected owner")
        capabilities = cccc_json(meta, role, ["capabilities"])
        members = cccc_json(meta, role, ["members", "--group", str(meta["group_id"])])
        member_ids = {
            item.get("id") for item in members.get("members", []) if isinstance(item, dict)
        }
        if member_ids != expected_actors:
            raise LabError(
                f"Role {role} sees unexpected Group members: {sorted(str(x) for x in member_ids)}"
            )
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
            **selection,
            "actor_id": meta["actors"][role],
            "availability": state.get("availability"),
            "active_execution": state.get("active_execution"),
            "binding_id": binding.get("binding_id"),
            "capabilities": capabilities,
            "body": current_body,
            "offline_recovery_registered": True,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def apply_delivery_for_role(
    meta: dict[str, Any],
    role: str,
    *,
    policy: str,
    quiet_interval: float,
    max_wait: float,
    timeout: float,
) -> dict[str, Any]:
    """Set receiver delivery policy on one role and await active convergence."""
    path = "/v1/plugins/cccc/delivery"
    before = gateway_get(meta, role, path)
    settings: dict[str, Any] = {"transport": "pull"}
    if policy != "pull":
        settings = {"transport": "push", "push_policy": policy}
        if policy == "batch":
            settings.update(quiet_interval=quiet_interval, max_wait=max_wait)
    response = httpx.put(
        str(meta["gateways"][role]).rstrip("/") + path,
        json={"revision": before["revision"], "settings": settings},
        trust_env=False,
        timeout=20,
    )
    if response.status_code != 200:
        raise LabError(f"Setting delivery on {role} returned HTTP {response.status_code}")
    revision = response.json()["revision"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        observed = gateway_get(meta, role, path)
        if observed.get("revision") != revision:
            raise LabError(f"Delivery settings on {role} changed unexpectedly")
        if observed.get("transition") == "active" and observed.get("effective") == observed.get(
            "desired"
        ):
            return observed
        time.sleep(0.25)
    raise LabError(f"Timed out waiting for delivery policy on {role}")


def command_delivery(args: argparse.Namespace) -> int:
    """Set effective delivery policy for one role or all four roles."""
    meta = load_meta(args.run_meta)
    targets = _ROLES if args.role == "all" else (args.role,)
    results = {
        role: apply_delivery_for_role(
            meta,
            role,
            policy=args.policy,
            quiet_interval=args.quiet_interval,
            max_wait=args.max_wait,
            timeout=args.timeout,
        )
        for role in targets
    }
    print(json.dumps({"status": "active", "roles": results}, indent=2, sort_keys=True))
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
    """Inspect live readiness for one role or all four roles."""
    meta = load_meta(args.run_meta)
    targets = _ROLES if args.role == "all" else (args.role,)
    payload = {role: live_observation(meta, role) for role in targets}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_wait_idle(args: argparse.Namespace) -> int:
    """Wait until all four agents stay idle for a quiet window and no messages arrive."""
    meta = load_meta(args.run_meta)
    start = time.monotonic()
    deadline = start + args.timeout
    quiet_since: float | None = None
    last_msg_count: int | None = None

    while time.monotonic() < deadline:
        states = {role: live_observation(meta, role) for role in _ROLES}
        history = cccc_json(meta, "lead", ["chat", "history", "--limit", "200"])
        msg_count = len(history.get("messages") or [])
        all_idle = all(
            st.get("active_execution") == "idle" and st.get("can_accept_prompt_now") is True
            for st in states.values()
        )
        if all_idle and (last_msg_count is None or msg_count == last_msg_count):
            if quiet_since is None:
                quiet_since = time.monotonic()
            elif time.monotonic() - quiet_since >= args.quiesce_seconds:
                print(
                    json.dumps(
                        {
                            "status": "quiescent",
                            "elapsed_seconds": round(time.monotonic() - start, 2),
                            "message_count": msg_count,
                            "states": states,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0
        else:
            quiet_since = None
        last_msg_count = msg_count
        time.sleep(args.interval)

    raise LabError(f"Timed out after {args.timeout}s waiting for all four agents to settle")


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


def command_verify_cuda(args: argparse.Namespace) -> int:
    """Compile and verify submitted solution.cu against the untouched locked driver."""
    meta = load_meta(args.run_meta)
    manifest = meta["manifest"]
    problem = manifest["problem"]
    source_dir = Path(str(problem["source_dir"]))
    workspace_dir = Path(str(meta["workspace_dir"]))
    submitted_src = workspace_dir / "solution.cu"
    if not submitted_src.is_file():
        raise LabError(f"Submitted solution.cu not found: {submitted_src}")

    evidence_dir = args.evidence_dir.expanduser().resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    verify_dir = args.verify_dir.expanduser().resolve()
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)

    # Copy untouched locked driver + API header + ONLY submitted solution.cu.
    shutil.copy2(source_dir / "kernel_api.cuh", verify_dir / "kernel_api.cuh")
    shutil.copy2(source_dir / "driver.cu", verify_dir / "driver.cu")
    shutil.copy2(submitted_src, verify_dir / "solution.cu")

    # Save immutable evidence copies of submitted solution and diff vs starter.
    shutil.copy2(submitted_src, evidence_dir / "submitted-solution.cu")
    starter_lines = (
        (source_dir / "solution_starter.cu").read_text(encoding="utf-8").splitlines(keepends=True)
    )
    submitted_lines = submitted_src.read_text(encoding="utf-8").splitlines(keepends=True)
    diff_text = "".join(
        difflib.unified_diff(
            starter_lines,
            submitted_lines,
            fromfile="solution_starter.cu",
            tofile="submitted-solution.cu",
        )
    )
    (evidence_dir / "solution-diff.patch").write_text(diff_text, encoding="utf-8")

    # Detect whether agents tampered with locked workspace files.
    tampered_files: list[str] = []
    for locked_name in ("kernel_api.cuh", "driver.cu"):
        src_bytes = (source_dir / locked_name).read_bytes()
        ws_file = workspace_dir / locked_name
        if not ws_file.is_file() or ws_file.read_bytes() != src_bytes:
            tampered_files.append(locked_name)

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
        "solution_changed_from_starter": bool(diff_text.strip()),
        "workspace_locked_files_untouched": not tampered_files,
        "tampered_workspace_files": tampered_files,
        "compile_returncode": compile_res.returncode,
        "compile_stderr": compile_res.stderr.strip(),
        "min_speedup_target": problem.get("min_speedup"),
        "stretch_speedup_target": problem.get("stretch_speedup"),
    }

    if compile_res.returncode != 0:
        report["status"] = "compile_failed"
        write_json(evidence_dir / "independent-verify.json", report, mode=0o644)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    run_res = subprocess.run(
        [str(binary), "--json"], capture_output=True, text=True, check=False, timeout=300
    )
    report["run_returncode"] = run_res.returncode
    report["run_stderr"] = run_res.stderr.strip()
    try:
        driver_json = json.loads(run_res.stdout)
    except json.JSONDecodeError:
        report["status"] = "invalid_driver_output"
        report["raw_stdout"] = run_res.stdout[:2000]
        write_json(evidence_dir / "independent-verify.json", report, mode=0o644)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    report["driver_result"] = driver_json
    passed = bool(driver_json.get("passed")) and bool(driver_json.get("inputs_immutable"))
    speedup = float(driver_json.get("geomean_speedup", 0.0))
    report["meets_gt_1x"] = speedup > 1.0
    report["meets_min_speedup_target"] = speedup >= float(problem.get("min_speedup", 3.0))
    report["meets_stretch_speedup_target"] = speedup >= float(problem.get("stretch_speedup", 10.0))
    report["status"] = "passed" if (passed and not tampered_files and speedup > 1.0) else "failed"

    if args.run_ncu and passed:
        ncu = str(manifest["cuda"]["ncu"])
        ncu_cmd = [
            ncu,
            "--metrics",
            (
                "sm__throughput.avg.pct_of_peak_sustained_elapsed,"
                "dram__throughput.avg.pct_of_peak_sustained_elapsed,"
                "sm__warps_active.avg.pct_of_peak_sustained_active,"
                "launch__registers_per_thread"
            ),
            str(binary),
            "--profile-only",
        ]
        ncu_res = subprocess.run(ncu_cmd, capture_output=True, text=True, check=False, timeout=180)
        (evidence_dir / "ncu-summary.txt").write_text(
            (ncu_res.stdout or "") + "\n" + (ncu_res.stderr or ""), encoding="utf-8"
        )
        report["ncu_returncode"] = ncu_res.returncode

    write_json(evidence_dir / "independent-verify.json", report, mode=0o644)
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(report["status"] != "passed")


def bash_call(record: dict[str, Any]) -> dict[str, Any] | None:
    """Read one shell invocation from a native DSH or Kimi journal row."""
    if record.get("type") == "tool/call":
        event = record.get("data")
        if not isinstance(event, dict) or event.get("name") != "bash":
            return None
        try:
            arguments = json.loads(event.get("arguments") or "{}")
        except (TypeError, json.JSONDecodeError):
            return None
        turn = event.get("turn")
    elif record.get("type") == "context.append_loop_event":
        event = record.get("event")
        if not isinstance(event, dict) or (event.get("type"), event.get("name")) != (
            "tool.call",
            "Bash",
        ):
            return None
        arguments = event.get("args")
        turn = event.get("turnId")
    else:
        return None
    command = arguments.get("command") if isinstance(arguments, dict) else None
    return {"turn": turn, "command": command} if isinstance(command, str) else None


def audit_role_transcripts(files: list[Path]) -> dict[str, Any]:
    """Inspect native bash tool calls for forbidden mail/admin channels and CUDA/CCCC tool usage."""
    commands: list[dict[str, Any]] = []
    for path in files:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict) and (call := bash_call(record)) is not None:
                    commands.append(call)

    forbidden: list[dict[str, Any]] = []
    cccc_calls = 0
    cuda_calls = 0
    for item in commands:
        command = item["command"]
        lower = command.lower()
        if "houmao-cccc" in lower or "/v1/plugins/cccc" in lower:
            cccc_calls += 1
        if any(tool in lower for tool in ("nvcc", "ncu", "nsys", "make ", "./run_kernel")):
            cuda_calls += 1
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
        "bash_tool_call_count": len(commands),
        "cccc_command_count": cccc_calls,
        "cuda_command_count": cuda_calls,
        "forbidden_calls": forbidden,
        "status": "passed" if not forbidden else "failed",
    }


def command_audit(args: argparse.Namespace) -> int:
    """Capture transcripts, CCCC history, 4-agent participation metrics, and channel audit."""
    meta = load_meta(args.run_meta)
    evidence_dir = args.evidence_dir.expanduser().resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)

    copied_transcripts: dict[str, list[str]] = {}
    role_audits: dict[str, Any] = {}
    for role in _ROLES:
        run_dir, _ = role_run(meta, role)
        client = load_run(run_dir)["configuration"]["client"]
        files = session_files(run_dir, client=client)
        if not files:
            raise LabError(f"No native {client} transcript found for role {role}")
        copied: list[str] = []
        for idx, source in enumerate(files[-args.max_files :]):
            target = evidence_dir / f"transcript-{role}-{idx}{source.suffix}"
            shutil.copy2(source, target)
            copied.append(str(target))
        copied_transcripts[role] = copied
        role_audits[role] = audit_role_transcripts(files)

    history = cccc_json(meta, "lead", ["chat", "history", "--limit", "200"])
    write_json(evidence_dir / "cccc-history.json", history, mode=0o644)

    messages = [msg for msg in (history.get("messages") or []) if isinstance(msg, dict)]
    expected_actors = {str(meta["actors"][r]) for r in _ROLES}
    messages_by_actor: dict[str, int] = {actor: 0 for actor in sorted(expected_actors)}
    multi_recipient_count = 0
    threaded_reply_count = 0
    request_reply_count = 0

    for msg in messages:
        sender = str(msg.get("by") or "")
        if sender in messages_by_actor:
            messages_by_actor[sender] += 1
        data = msg.get("data") or {}
        to_list = data.get("to") if isinstance(data.get("to"), list) else []
        if len(to_list) > 1:
            multi_recipient_count += 1
        if data.get("reply_to"):
            threaded_reply_count += 1
        if data.get("message_mode") == "request_reply":
            request_reply_count += 1

    active_actors = sorted([actor for actor, count in messages_by_actor.items() if count > 0])
    missing_actors = sorted(expected_actors - set(active_actors))

    channel_audit = {
        "status": "passed"
        if all(role_audits[role]["status"] == "passed" for role in _ROLES)
        else "failed",
        "roles": role_audits,
        "transcripts": copied_transcripts,
    }
    participation = {
        "status": "passed" if not missing_actors else "failed",
        "total_messages": len(messages),
        "messages_by_actor": messages_by_actor,
        "active_actors": active_actors,
        "missing_actors": missing_actors,
        "multi_recipient_messages": multi_recipient_count,
        "request_reply_messages": request_reply_count,
        "threaded_replies": threaded_reply_count,
    }
    write_json(evidence_dir / "channel-audit.json", channel_audit, mode=0o644)
    write_json(evidence_dir / "participation-summary.json", participation, mode=0o644)

    combined = {
        "status": "passed"
        if (channel_audit["status"] == "passed" and participation["status"] == "passed")
        else "failed",
        "channel_audit": channel_audit,
        "participation": participation,
    }
    print(json.dumps(combined, indent=2, sort_keys=True))
    return int(combined["status"] != "passed")


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
    """Stop all four owned agents, revoke grants, delete Group, and preserve evidence."""
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
        run_str = (meta.get("runs") or {}).get(role)
        agent_id = (meta.get("agent_ids") or {}).get(role)
        if not run_str or not agent_id:
            continue
        run_dir = Path(str(run_str))
        try:
            receipt = manager_json(
                run_env(run_dir),
                ["agents", "single", "--agent-id", str(agent_id), "stop"],
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
                for role, grant in (meta.get("grants") or {}).items():
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
        for role, grant in (meta.get("grants") or {}).items():
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

    failures: list[str] = []
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
    configure.add_argument("--run-lead", type=Path, required=True)
    configure.add_argument("--run-algo", type=Path, required=True)
    configure.add_argument("--run-kernel", type=Path, required=True)
    configure.add_argument("--run-profiler", type=Path, required=True)
    configure.add_argument("--endpoint", required=True)
    configure.add_argument("--private-root", type=Path, required=True)
    configure.add_argument("--workspace-dir", type=Path, required=True)
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
    delivery.add_argument("--role", choices=(*_ROLES, "all"), default="all")
    delivery.add_argument("--policy", choices=("pull", "asap", "batch"), required=True)
    delivery.add_argument("--quiet-interval", type=float, default=6.0)
    delivery.add_argument("--max-wait", type=float, default=15.0)
    delivery.add_argument("--timeout", type=float, default=60.0)
    delivery.set_defaults(handler=command_delivery)

    prompt = commands.add_parser("prompt")
    prompt.add_argument("--run-meta", type=Path, required=True)
    prompt.add_argument("--role", choices=_ROLES, required=True)
    prompt.add_argument("--prompt", required=True)
    prompt.add_argument("--timeout", type=float, default=600.0)
    prompt.set_defaults(handler=command_prompt)

    state = commands.add_parser("state")
    state.add_argument("--run-meta", type=Path, required=True)
    state.add_argument("--role", choices=(*_ROLES, "all"), default="all")
    state.set_defaults(handler=command_state)

    wait_idle = commands.add_parser("wait-idle")
    wait_idle.add_argument("--run-meta", type=Path, required=True)
    wait_idle.add_argument("--timeout", type=float, default=900.0)
    wait_idle.add_argument("--quiesce-seconds", type=float, default=12.0)
    wait_idle.add_argument("--interval", type=float, default=2.0)
    wait_idle.set_defaults(handler=command_wait_idle)

    inspect = commands.add_parser("cccc")
    inspect.add_argument("--run-meta", type=Path, required=True)
    inspect.add_argument("--role", choices=_ROLES, required=True)
    inspect.add_argument("arguments", nargs=argparse.REMAINDER)
    inspect.set_defaults(handler=command_cccc)

    verify_cuda = commands.add_parser("verify-cuda")
    verify_cuda.add_argument("--run-meta", type=Path, required=True)
    verify_cuda.add_argument("--verify-dir", type=Path, required=True)
    verify_cuda.add_argument("--evidence-dir", type=Path, required=True)
    verify_cuda.add_argument("--run-ncu", action="store_true")
    verify_cuda.set_defaults(handler=command_verify_cuda)

    audit = commands.add_parser("audit")
    audit.add_argument("--run-meta", type=Path, required=True)
    audit.add_argument("--evidence-dir", type=Path, required=True)
    audit.add_argument("--max-files", type=int, default=3)
    audit.set_defaults(handler=command_audit)

    recovery = commands.add_parser("recovery-post")
    recovery.add_argument("--run-meta", type=Path, required=True)
    recovery.add_argument("--role", choices=_ROLES, required=True)
    recovery.add_argument("--subject", required=True)
    recovery.add_argument("--body", required=True)
    recovery.add_argument("--confirm-operator-recovery", action="store_true")
    recovery.set_defaults(handler=command_recovery_post)

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
    except (LabError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
