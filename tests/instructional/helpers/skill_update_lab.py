#!/usr/bin/env python3
"""Instructional harness for versioned managed-agent skill updates.

The helper wraps the exact `fixture.py` and `houmao-mgr` operations used by the
instructional cases. It keeps disposable state inside one project-local run
directory and never touches the caller's default tmux server.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANAGER = Path("/home/huangzhe/.local/share/uv/tools/houmao/bin/houmao-mgr")
_TMUX_ENV_KEYS = ("TMUX", "TMUX_PANE", "TMUX_TMPDIR")


class LabError(RuntimeError):
    """Report one actionable harness failure."""


def manager_path() -> Path:
    """Resolve the uv-installed manager without ambient project state."""

    configured = os.environ.get("HOUMAO_MGR")
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path
        raise LabError(f"HOUMAO_MGR is not a file: {path}")
    found = shutil.which("houmao-mgr")
    if found:
        return Path(found)
    if DEFAULT_MANAGER.is_file():
        return DEFAULT_MANAGER
    raise LabError("Set HOUMAO_MGR to the uv-installed houmao-mgr binary.")


def run_env(run_dir: Path) -> dict[str, str]:
    """Build the isolated manager environment for one prepared fixture run."""

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


def manager_json(env: dict[str, str], arguments: list[str]) -> dict[str, Any]:
    """Run one maintained manager command and parse its JSON payload."""

    command = [str(manager_path()), "--print-json", *arguments]
    result = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
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
    """Load one launched fixture run and require its managed identity."""

    path = run_dir / "run.json"
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise LabError(f"Cannot read prepared run metadata: {path}") from exc
    identity = payload.get("identity")
    if not isinstance(identity, dict) or not identity.get("agent_id"):
        raise LabError(f"Run is not launched: {run_dir}")
    return payload


def write_json(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    """Write one owner-private JSON document atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.chmod(mode)
    temporary.replace(path)


def load_meta(path: Path) -> dict[str, Any]:
    """Load one run-meta document and reject an incomplete identity set."""

    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise LabError(f"Cannot read run metadata: {path}") from exc
    required = (
        "target_run",
        "source_run",
        "target_agent_id",
        "source_agent_id",
        "target_gateway",
        "source_gateway",
        "mount_id",
    )
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise LabError(f"Run metadata is missing: {', '.join(missing)}")
    return payload


def generate_key(path: Path) -> None:
    """Create one Ed25519 key pair without a passphrase or printed material."""

    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    result = subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise LabError(f"ssh-keygen failed: {result.stderr.strip() or 'unknown error'}")
    path.chmod(0o600)
    path.with_suffix(path.suffix + ".pub").chmod(0o644)


def public_key_path(private_key: Path) -> Path:
    """Return the generated public key path for one private key."""

    return private_key.with_suffix(private_key.suffix + ".pub")


def _skills_mount(env: dict[str, str], agent_id: str) -> dict[str, Any]:
    """Discover the exact `skills` mount or fail before any policy mutation."""

    payload = manager_json(env, ["agents", "single", "--agent-id", agent_id, "files", "mounts"])
    mounts = payload.get("mounts")
    if not isinstance(mounts, list):
        raise LabError("Mount discovery did not return a mounts list")
    for mount in mounts:
        if isinstance(mount, dict) and mount.get("name") == "skills":
            return mount
    raise LabError(
        "No `skills` mount is visible. Enable managed_web_skills before launching "
        "the target DSH Web agent."
    )


def _record_coordinates(target_run: Path, target_agent_id: str) -> dict[str, str]:
    """Read the target's trusted gateway coordinates from its runtime record."""

    record_path = target_run / "registry/live_agents" / target_agent_id / "record.json"
    try:
        record = json.loads(record_path.read_text())
        binding = record["execution_binding"]
        endpoint = record["gateway"]["endpoint_descriptor"]
        return {
            "context_id": str(binding["context_id"]),
            "generation": str(record["generation_id"]),
            "presence": str(endpoint["presence_id"]),
        }
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise LabError(f"Cannot read target gateway coordinates: {record_path}") from exc


def _configure_principal(
    env: dict[str, str],
    *,
    target_agent_id: str,
    principal_id: str,
    label: str,
    logical_agent_id: str,
    public_key: Path,
    mount_id: str,
) -> None:
    """Enroll one agent principal and grant the three versioned-file actions."""

    manager_json(
        env,
        [
            "agents",
            "single",
            "--agent-id",
            target_agent_id,
            "access",
            "principal-add",
            principal_id,
            "--kind",
            "agent",
            "--label",
            label,
            "--logical-agent-id",
            logical_agent_id,
        ],
    )
    manager_json(
        env,
        [
            "agents",
            "single",
            "--agent-id",
            target_agent_id,
            "access",
            "credential-enroll",
            principal_id,
            "--public-key",
            str(public_key),
        ],
    )
    for action in ("files.read", "files.edit", "files.push"):
        manager_json(
            env,
            [
                "agents",
                "single",
                "--agent-id",
                target_agent_id,
                "access",
                "grant",
                principal_id,
                f"files:{mount_id}",
                action,
            ],
        )


def command_enable_mount(args: argparse.Namespace) -> int:
    """Patch a prepared target run so its next launch exposes the skills mount."""

    run_dir = args.run_dir.resolve()
    run_path = run_dir / "run.json"
    try:
        run = json.loads(run_path.read_text())
    except (OSError, ValueError) as exc:
        raise LabError(f"Cannot read prepared run metadata: {run_path}") from exc
    if run.get("status") == "launched":
        raise LabError("Run is already launched; patch a prepared run and relaunch the target.")
    import yaml  # Imported here so the other subcommands stay dependency-light.

    candidates = (
        run_dir / "workdir/.houmao/agents/tools/dsh/setups/fixture/tool-params.yaml",
        run_dir / "assets/tools/dsh/setups/fixture/tool-params.yaml",
        run_dir / "home/houmao-tool-params.yaml",
    )
    patched: list[str] = []
    for path in candidates:
        if not path.is_file():
            continue
        document = yaml.safe_load(path.read_text()) or {}
        if not isinstance(document, dict):
            raise LabError(f"Unexpected tool-params document: {path}")
        document["managed_web_skills"] = True
        path.write_text(yaml.safe_dump(document, sort_keys=True))
        patched.append(str(path))
    if not patched:
        raise LabError("No DSH tool-params file was found under the prepared run")
    print(
        json.dumps(
            {"status": "enabled", "run_dir": str(run_dir), "patched_paths": patched},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_configure(args: argparse.Namespace) -> int:
    """Configure peer signers, target grants, and the source peer brief."""

    target_run = args.target_run.resolve()
    source_run = args.source_run.resolve()
    meta_path = args.run_meta.resolve()
    target = load_run(target_run)
    source = load_run(source_run)
    target_identity = target["identity"]
    source_identity = source["identity"]
    target_agent_id = str(target_identity["agent_id"])
    source_agent_id = str(source_identity["agent_id"])
    for label, identity in (("target", target_identity), ("source", source_identity)):
        if not identity.get("gateway_port"):
            raise LabError(f"{label} has no gateway port; relaunch it with a gateway.")
    target_gateway = f"http://127.0.0.1:{target_identity['gateway_port']}"
    source_gateway = f"http://127.0.0.1:{source_identity['gateway_port']}"
    target_env = run_env(target_run)
    source_env = run_env(source_run)
    key_dir = (args.key_dir or (meta_path.parent / "runtime/keys")).resolve()
    source_key = key_dir / "source-peer"
    target_key = key_dir / "target-peer"
    generate_key(source_key)
    generate_key(target_key)
    manager_json(
        source_env,
        [
            "agents",
            "single",
            "--agent-id",
            source_agent_id,
            "access",
            "peer-signer",
            "--key",
            str(source_key),
        ],
    )
    manager_json(
        target_env,
        [
            "agents",
            "single",
            "--agent-id",
            target_agent_id,
            "access",
            "peer-signer",
            "--key",
            str(target_key),
        ],
    )
    mount = _skills_mount(target_env, target_agent_id)
    mount_id = str(mount["mount_id"])
    coordinates = _record_coordinates(target_run, target_agent_id)
    _configure_principal(
        target_env,
        target_agent_id=target_agent_id,
        principal_id=args.reviewer_id,
        label="Source updater",
        logical_agent_id=source_agent_id,
        public_key=public_key_path(source_key),
        mount_id=mount_id,
    )
    _configure_principal(
        target_env,
        target_agent_id=target_agent_id,
        principal_id=args.self_editor_id,
        label="Self editor",
        logical_agent_id=target_agent_id,
        public_key=public_key_path(target_key),
        mount_id=mount_id,
    )
    peer_brief = {
        "target_agent_id": target_agent_id,
        "target_gateway_url": target_gateway,
        "target_context_id": coordinates["context_id"],
        "target_generation": coordinates["generation"],
        "target_presence": coordinates["presence"],
    }
    peer_brief_path = Path(str(source["workdir"])) / "peer-brief.json"
    write_json(peer_brief_path, peer_brief, mode=0o644)
    meta = {
        "schema_version": 1,
        "target_run": str(target_run),
        "source_run": str(source_run),
        "target_agent_id": target_agent_id,
        "source_agent_id": source_agent_id,
        "target_agent_name": target_identity.get("agent_name"),
        "source_agent_name": source_identity.get("agent_name"),
        "target_gateway": target_gateway,
        "source_gateway": source_gateway,
        "target_workdir": str(target["workdir"]),
        "source_workdir": str(source["workdir"]),
        "target_socket": target.get("tmux_socket_path"),
        "source_socket": source.get("tmux_socket_path"),
        "mount_id": mount_id,
        "mount_resource": mount.get("resource"),
        "published_commit": mount.get("published_commit"),
        "target_context_id": coordinates["context_id"],
        "target_generation": coordinates["generation"],
        "target_presence": coordinates["presence"],
        "peer_brief_path": str(peer_brief_path),
        "source_key_path": str(source_key),
        "target_key_path": str(target_key),
        "reviewer_principal": args.reviewer_id,
        "self_editor_principal": args.self_editor_id,
        "evidence_root": str((args.evidence_root or (meta_path.parent / "evidence")).resolve()),
    }
    write_json(meta_path, meta)
    print(
        json.dumps(
            {
                "status": "configured",
                "run_meta": str(meta_path),
                "target_agent_id": target_agent_id,
                "source_agent_id": source_agent_id,
                "mount_id": mount_id,
                "published_commit": mount.get("published_commit"),
                "peer_brief_path": str(peer_brief_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    """Check both agents, the visible mount, and the retained grants."""

    meta_path = args.run_meta.resolve()
    meta = load_meta(meta_path)
    target_run = Path(str(meta["target_run"]))
    source_run = Path(str(meta["source_run"]))
    target_env = run_env(target_run)
    source_env = run_env(source_run)
    target_agent_id = str(meta["target_agent_id"])
    source_agent_id = str(meta["source_agent_id"])
    mount_id = str(meta["mount_id"])
    checks: dict[str, Any] = {}
    healthy = True

    def record(name: str, payload: dict[str, Any], *, ok: bool) -> None:
        """Keep one bounded check result."""

        nonlocal healthy
        checks[name] = {"ok": ok, "payload": payload}
        healthy = healthy and ok

    target_state = manager_json(
        target_env, ["agents", "single", "--agent-id", target_agent_id, "state"]
    )
    record(
        "target_state",
        target_state,
        ok=target_state.get("availability") == "available"
        and (target_state.get("gateway") or {}).get("gateway_health") == "healthy",
    )
    source_state = manager_json(
        source_env, ["agents", "single", "--agent-id", source_agent_id, "state"]
    )
    record(
        "source_state",
        source_state,
        ok=source_state.get("availability") == "available"
        and (source_state.get("gateway") or {}).get("gateway_health") == "healthy",
    )
    try:
        mount = _skills_mount(target_env, target_agent_id)
        record("skills_mount", mount, ok=True)
    except LabError as exc:
        record("skills_mount", {"error": str(exc)}, ok=False)
    grant_checks: dict[str, Any] = {}
    principal_ids = (
        meta.get("reviewer_principal", "reviewer"),
        meta.get("self_editor_principal", "self-editor"),
    )
    for principal_id in principal_ids:
        try:
            explanation = manager_json(
                target_env,
                [
                    "agents",
                    "single",
                    "--agent-id",
                    target_agent_id,
                    "access",
                    "explain",
                    str(principal_id),
                    f"files:{mount_id}",
                    "files.push",
                ],
            )
            direct = explanation.get("direct_grant") or {}
            grant_checks[str(principal_id)] = {
                "ok": bool(direct.get("active")),
                "payload": explanation,
            }
        except LabError as exc:
            grant_checks[str(principal_id)] = {"ok": False, "error": str(exc)}
    for principal_id, check in grant_checks.items():
        checks[f"grant_{principal_id}"] = check
        healthy = healthy and bool(check.get("ok"))
    checks["grants"] = grant_checks
    print(json.dumps({"healthy": healthy, "run_meta": str(meta_path), "checks": checks}, indent=2))
    return 0 if healthy else 1


def command_prompt(args: argparse.Namespace) -> int:
    """Submit one operator prompt to the selected agent and print its receipt."""

    meta = load_meta(args.run_meta.resolve())
    if args.role == "source":
        run_dir = Path(str(meta["source_run"]))
        agent_id = str(meta["source_agent_id"])
    else:
        run_dir = Path(str(meta["target_run"]))
        agent_id = str(meta["target_agent_id"])
    payload = manager_json(
        run_env(run_dir),
        [
            "agents",
            "single",
            "--agent-id",
            agent_id,
            "prompt",
            "--prompt",
            args.prompt,
        ],
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_state(args: argparse.Namespace) -> int:
    """Print one agent's operational state through its isolated run roots."""

    meta = load_meta(args.run_meta.resolve())
    if args.role == "source":
        run_dir = Path(str(meta["source_run"]))
        agent_id = str(meta["source_agent_id"])
    else:
        run_dir = Path(str(meta["target_run"]))
        agent_id = str(meta["target_agent_id"])
    payload = manager_json(run_env(run_dir), ["agents", "single", "--agent-id", agent_id, "state"])
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_mounts(args: argparse.Namespace) -> int:
    """List target mounts with current read permission."""

    meta = load_meta(args.run_meta.resolve())
    payload = manager_json(
        run_env(Path(str(meta["target_run"]))),
        ["agents", "single", "--agent-id", str(meta["target_agent_id"]), "files", "mounts"],
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_read(args: argparse.Namespace) -> int:
    """Read one logical file from the target mount."""

    meta = load_meta(args.run_meta.resolve())
    arguments = [
        "agents",
        "single",
        "--agent-id",
        str(meta["target_agent_id"]),
        "files",
        "--mount",
        str(meta["mount_id"]),
        "read",
        args.path,
    ]
    if args.revision:
        arguments.extend(["--revision", args.revision])
    payload = manager_json(run_env(Path(str(meta["target_run"]))), arguments)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_push_owner(args: argparse.Namespace) -> int:
    """Publish one saved candidate through the target's open owner roster."""

    meta = load_meta(args.run_meta.resolve())
    arguments = [
        "agents",
        "single",
        "--agent-id",
        str(meta["target_agent_id"]),
        "files",
        "--mount",
        str(meta["mount_id"]),
        "push",
        args.candidate,
        "--expected-base",
        args.expected_base,
    ]
    if args.operation_id:
        arguments.extend(["--operation-id", args.operation_id])
    payload = manager_json(run_env(Path(str(meta["target_run"]))), arguments)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _kill_private_tmux(socket_path: str | None) -> dict[str, str]:
    """Stop one recorded private tmux server and remove its stale socket."""

    if not socket_path:
        return {"status": "not_recorded"}
    socket = Path(socket_path)
    environment = {key: value for key, value in os.environ.items() if key not in _TMUX_ENV_KEYS}
    if not socket.exists():
        return {"socket": str(socket), "status": "already_absent"}
    subprocess.run(
        ["tmux", "-S", str(socket), "kill-server"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if socket.is_socket():
        socket.unlink(missing_ok=True)
    return {"socket": str(socket), "status": "killed" if not socket.exists() else "retained"}


def command_stop(args: argparse.Namespace) -> int:
    """Stop only the pair owned by one run-meta document and preserve evidence."""

    meta = load_meta(args.run_meta.resolve())
    stopped: dict[str, Any] = {}
    for role, run_key, agent_key in (
        ("target", "target_run", "target_agent_id"),
        ("source", "source_run", "source_agent_id"),
    ):
        run_dir = Path(str(meta[run_key]))
        agent_id = str(meta[agent_key])
        try:
            receipt = manager_json(
                run_env(run_dir), ["agents", "single", "--agent-id", agent_id, "stop"]
            )
            stopped[role] = {"agent_id": agent_id, "receipt": receipt}
        except LabError as exc:
            detail = str(exc)
            already_stopped = "relaunch" in detail and "cleanup" in detail
            stopped[role] = {
                "agent_id": agent_id,
                "already_stopped": already_stopped,
                "error": None if already_stopped else detail,
            }
    recorded_sockets = meta.get("tmux_sockets") or {}
    target_socket = meta.get("target_socket") or recorded_sockets.get("target")
    source_socket = meta.get("source_socket") or recorded_sockets.get("source")
    sockets = {
        "target": _kill_private_tmux(target_socket),
        "source": _kill_private_tmux(source_socket),
    }
    meta_parent = args.run_meta.resolve().parent
    fallback_evidence = meta_parent if meta_parent.name == "evidence" else meta_parent / "evidence"
    print(
        json.dumps(
            {
                "status": "stopped",
                "run_meta": str(args.run_meta.resolve()),
                "agents": stopped,
                "private_tmux_servers_cleaned": sockets,
                "evidence_root": meta.get("evidence_root", str(fallback_evidence)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line surface used by the instructional cases."""

    parser = argparse.ArgumentParser(
        description="Prepare, configure, drive, and stop the skill-update test pair."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    enable = subparsers.add_parser(
        "enable-mount",
        help="Patch a prepared target run with managed_web_skills before launch.",
    )
    enable.add_argument("--run-dir", type=Path, required=True)
    enable.set_defaults(handler=command_enable_mount)

    configure = subparsers.add_parser(
        "configure",
        help="Configure peer signers, target grants, and the source peer brief.",
    )
    configure.add_argument("--target-run", type=Path, required=True)
    configure.add_argument("--source-run", type=Path, required=True)
    configure.add_argument("--run-meta", type=Path, required=True)
    configure.add_argument("--key-dir", type=Path)
    configure.add_argument("--evidence-root", type=Path)
    configure.add_argument("--reviewer-id", default="reviewer")
    configure.add_argument("--self-editor-id", default="self-editor")
    configure.set_defaults(handler=command_configure)

    doctor = subparsers.add_parser(
        "doctor", help="Check both agents, the visible mount, and retained grants."
    )
    doctor.add_argument("--run-meta", type=Path, required=True)
    doctor.set_defaults(handler=command_doctor)

    prompt = subparsers.add_parser(
        "prompt", help="Submit one operator prompt to the source or target agent."
    )
    prompt.add_argument("--run-meta", type=Path, required=True)
    prompt.add_argument("--role", choices=("source", "target"), required=True)
    prompt.add_argument("--prompt", required=True)
    prompt.set_defaults(handler=command_prompt)

    state = subparsers.add_parser(
        "state", help="Print the source or target agent's operational state."
    )
    state.add_argument("--run-meta", type=Path, required=True)
    state.add_argument("--role", choices=("source", "target"), required=True)
    state.set_defaults(handler=command_state)

    mounts = subparsers.add_parser("mounts", help="List target mounts.")
    mounts.add_argument("--run-meta", type=Path, required=True)
    mounts.set_defaults(handler=command_mounts)

    read = subparsers.add_parser("read", help="Read one logical file from the target mount.")
    read.add_argument("--run-meta", type=Path, required=True)
    read.add_argument("--path", required=True)
    read.add_argument("--revision")
    read.set_defaults(handler=command_read)

    push_owner = subparsers.add_parser(
        "push-owner", help="Publish a saved candidate through the target's open roster."
    )
    push_owner.add_argument("--run-meta", type=Path, required=True)
    push_owner.add_argument("--candidate", required=True)
    push_owner.add_argument("--expected-base", required=True)
    push_owner.add_argument("--operation-id")
    push_owner.set_defaults(handler=command_push_owner)

    stop = subparsers.add_parser("stop", help="Stop only the pair owned by the run-meta document.")
    stop.add_argument("--run-meta", type=Path, required=True)
    stop.set_defaults(handler=command_stop)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch one helper command and render actionable errors."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except LabError as exc:
        print(f"skill_update_lab: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
