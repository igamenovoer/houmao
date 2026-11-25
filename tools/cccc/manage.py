"""Build and manage an isolated native CCCC development service on Linux.

Pixi supplies the toolchain. The upstream checkout remains reference code, and
build caches, daemon state, logs, and process metadata live outside the checkout.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def _paths() -> tuple[Path, Path, Path]:
    """Resolve explicit source and persistent development roots."""

    project = Path(__file__).resolve().parents[2]
    source = Path(os.environ.get("HOUMAO_CCCC_SOURCE", project / "extern/orphan/cccc"))
    root = Path(os.environ.get("HOUMAO_CCCC_ROOT", Path.home() / ".local/share/houmao-cccc"))
    source, root = source.expanduser().resolve(), root.expanduser().resolve()
    if root.is_relative_to(project):
        raise RuntimeError("HOUMAO_CCCC_ROOT must be outside the project checkout")
    binary = root / "target" / "debug" / "cccc"
    return source, root, binary


def _environment(root: Path) -> dict[str, str]:
    """Select isolated CCCC state without changing the developer's HOME."""

    environment = os.environ.copy()
    environment.update(
        PATH=str(root / "target" / "debug") + os.pathsep + environment.get("PATH", ""),
        CCCC_HOME=str(root / "data"),
        CCCC_WEB_HOST="127.0.0.1",
        CARGO_HOME=str(root / "cache" / "cargo"),
        CARGO_TARGET_DIR=str(root / "target"),
        CARGO_BUILD_JOBS=environment.get("HOUMAO_CCCC_BUILD_JOBS", "4"),
        npm_config_cache=str(root / "cache" / "npm"),
    )
    # Direct native launches use owner-private Unix-domain daemon IPC by default.
    for key in ("CCCC_DAEMON_TRANSPORT", "CCCC_DAEMON_HOST", "CCCC_DAEMON_PORT"):
        environment.pop(key, None)
    return environment


def _prepare(root: Path) -> None:
    """Create owner-private runtime directories, keeping logs and tokens local."""

    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    for name in ("data", "cache"):
        (root / name).mkdir(exist_ok=True, mode=0o700)


def _metadata(root: Path) -> dict[str, Any]:
    """Read only this helper's process descriptor, never provider secrets."""

    path = root / "runtime.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RuntimeError("Invalid CCCC runtime descriptor")
    return value


@contextmanager
def _lifecycle_lock(root: Path) -> Iterator[None]:
    """Serialize startup/shutdown so concurrent helpers cannot replace ownership."""

    _prepare(root)
    descriptor = os.open(root / "lifecycle.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _write_metadata(root: Path, metadata: dict[str, Any]) -> None:
    """Publish one complete owner-private descriptor for concurrent status reads."""

    descriptor, name = tempfile.mkstemp(prefix="runtime-", dir=root)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(json.dumps(metadata, indent=2) + "\n")
        os.replace(temporary, root / "runtime.json")
    finally:
        temporary.unlink(missing_ok=True)


def _start_ticks(pid: int) -> str | None:
    """Check Linux process birth identity and exclude exited/zombie processes."""

    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[19] if fields[0] not in {"Z", "X"} else None
    except (OSError, IndexError):
        return None


def _owned_process(metadata: dict[str, Any], root: Path, binary: Path) -> bool:
    """Require PID birth, command, and selected home before managing a process."""

    pid = metadata.get("pid")
    if not isinstance(pid, int) or pid <= 1:
        return False
    if _start_ticks(pid) != metadata.get("start_ticks"):
        return False
    try:
        arguments = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        environment = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except OSError:
        return False
    return bool(
        arguments
        and arguments[0] == os.fsencode(binary)
        and os.fsencode("CCCC_HOME=" + str(root / "data")) in environment
    )


def _health(url: str) -> bool:
    """Require a successful response from CCCC's daemon-backed health route."""

    try:
        with urlopen(url + "/api/v1/health", timeout=2) as response:
            value = json.loads(response.read(65536))
        return response.status == 200 and isinstance(value, dict) and value.get("ok") is True
    except (OSError, URLError, ValueError):
        return False


def _require_binary(binary: Path) -> None:
    """Explain the build prerequisite before attempting lifecycle work."""

    if not binary.is_file():
        raise RuntimeError("CCCC is not built; run the Pixi build task first")


def _build(source: Path, root: Path) -> None:
    """Build the pinned upstream workspace and embedded Web UI with managed tools."""

    if not (source / "Cargo.lock").is_file():
        raise RuntimeError("Clone ChesterRa/cccc into extern/orphan/cccc first")
    _prepare(root)
    subprocess.run(
        ["cargo", "build", "--locked", "-p", "cccc", "--bin", "cccc"],
        cwd=source,
        env=_environment(root),
        check=True,
    )
    identity = _source_identity(source)
    identity["binary_sha256"] = hashlib.sha256(
        (root / "target/debug/cccc").read_bytes()
    ).hexdigest()
    identity["binary_verified"] = True
    (root / "build.json").write_text(json.dumps(identity, indent=2) + "\n")


def _source_identity(source: Path) -> dict[str, Any]:
    """Describe the exact selected source, including maintained receiver patches."""

    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    difference = subprocess.check_output(["git", "-C", str(source), "diff", "--binary", "HEAD"])
    identity: dict[str, Any] = {
        "source_revision": revision,
        "source_diff_sha256": hashlib.sha256(difference).hexdigest(),
        "receiver_protocol_version": None,
        "binary_verified": False,
    }
    manifest_path = (
        Path(__file__).resolve().parents[2] / "extern/tracked/cccc-receiver/upstream.json"
    )
    manifest = json.loads(manifest_path.read_text())
    patches = [manifest_path.parent / patch for patch in manifest["patches"]]
    digest = hashlib.sha256(revision.encode())
    for patch in patches:
        digest.update(patch.read_bytes())
    receipt_path = source.parent / (source.name + ".receipt.json")
    receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
    prepared_matches = (
        receipt.get("selection") == digest.hexdigest()
        and receipt.get("diff_sha256") == identity["source_diff_sha256"]
        and receipt.get("protocol_version") == manifest["protocol_version"]
    )
    single_matches = (
        len(patches) == 1
        and hashlib.sha256(patches[0].read_bytes()).hexdigest() == identity["source_diff_sha256"]
    )
    if revision == manifest["revision"] and (prepared_matches or single_matches):
        identity["receiver_protocol_version"] = manifest["protocol_version"]
        identity["receiver_selection_sha256"] = digest.hexdigest()
        identity["receiver_patches"] = [
            {
                "path": str(patch.relative_to(manifest_path.parent)),
                "sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
            }
            for patch in patches
        ]
    return identity


def _status(root: Path, binary: Path) -> dict[str, Any]:
    """Report process ownership and HTTP readiness independently."""

    metadata = _metadata(root)
    owned = _owned_process(metadata, root, binary)
    url = metadata.get("url", f"http://127.0.0.1:{os.environ.get('HOUMAO_CCCC_PORT', '8848')}")
    return {
        "running": owned,
        "healthy": owned and _health(str(url)),
        "pid": metadata.get("pid") if owned else None,
        "url": url,
        "cccc_home": str(root / "data"),
        "log": str(root / "server.log"),
        "source_revision": metadata.get("source_revision"),
        "build_identity": metadata.get("build_identity"),
    }


def _start(source: Path, root: Path, binary: Path, port: int) -> None:
    """Start a detached service and confirm HTTP plus daemon readiness."""

    _require_binary(binary)
    _prepare(root)
    if not 1 <= port <= 65535:
        raise RuntimeError("HOUMAO_CCCC_PORT must be between 1 and 65535")
    if _owned_process(_metadata(root), root, binary):
        current = _status(root, binary)
        if not current["healthy"]:
            raise RuntimeError(f"Owned CCCC process is not healthy; inspect {root / 'server.log'}")
        print(json.dumps(current, indent=2))
        return
    source_identity = _source_identity(source)
    build_identity = source_identity
    build_path = root / "build.json"
    if build_path.is_file():
        built = json.loads(build_path.read_text())
        if (
            built.get("binary_sha256") != hashlib.sha256(binary.read_bytes()).hexdigest()
            or built.get("source_revision") != source_identity["source_revision"]
            or built.get("source_diff_sha256") != source_identity["source_diff_sha256"]
        ):
            raise RuntimeError(
                "Selected source or executable differs from the build; rebuild first"
            )
        build_identity = built
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))
    environment = _environment(root)
    existing = subprocess.run(
        [str(binary), "daemon", "status"],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )
    if existing.returncode == 0:
        raise RuntimeError("A daemon already uses this CCCC_HOME; choose another HOUMAO_CCCC_ROOT")
    descriptor = os.open(root / "server.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, "a") as log:
        process = subprocess.Popen(
            [str(binary), "--headless", "--host", "127.0.0.1", "--port", str(port)],
            cwd=source,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    metadata = {
        "pid": process.pid,
        "start_ticks": _start_ticks(process.pid),
        "url": f"http://127.0.0.1:{port}",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "source_revision": source_identity["source_revision"],
        "build_identity": build_identity,
    }
    _write_metadata(root, metadata)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"CCCC exited during startup; inspect {root / 'server.log'}")
        if _health(str(metadata["url"])):
            print(json.dumps(_status(root, binary), indent=2))
            return
        time.sleep(0.2)
    _stop(root, binary)
    raise RuntimeError(f"CCCC readiness deadline exceeded; inspect {root / 'server.log'}")


def _stop(root: Path, binary: Path) -> None:
    """Stop only this descriptor's verified process and its selected daemon."""

    metadata = _metadata(root)
    if not _owned_process(metadata, root, binary):
        print("No owned CCCC service is running")
        return
    subprocess.run(
        [str(binary), "daemon", "stop"],
        env=_environment(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    )
    pid = int(metadata["pid"])
    if _owned_process(metadata, root, binary):
        os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while _owned_process(metadata, root, binary) and time.monotonic() < deadline:
        time.sleep(0.1)
    if _owned_process(metadata, root, binary):
        raise RuntimeError("Owned CCCC process has not stopped; no unrelated process was signalled")
    (root / "runtime.json").unlink(missing_ok=True)
    print("Stopped the owned CCCC service")


def main() -> int:
    """Expose managed build/start/status/stop and explicit CLI passthrough tasks."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "start", "run", "status", "stop", "cli"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    if args.action != "cli" and arguments:
        parser.error("Lifecycle/build tasks take no extra arguments; use HOUMAO_CCCC_* settings")
    try:
        source, root, binary = _paths()
        if args.action == "build":
            _build(source, root)
        elif args.action == "start":
            with _lifecycle_lock(root):
                _start(source, root, binary, int(os.environ.get("HOUMAO_CCCC_PORT", "8848")))
        elif args.action == "status":
            print(json.dumps(_status(root, binary), indent=2))
        elif args.action == "stop":
            with _lifecycle_lock(root):
                _stop(root, binary)
        else:
            _require_binary(binary)
            _prepare(root)
            if args.action == "run":
                arguments = [
                    "--headless",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    os.environ.get("HOUMAO_CCCC_PORT", "8848"),
                ]
            working_directory = (
                Path(os.environ.get("INIT_CWD", Path.cwd())) if args.action == "cli" else source
            )
            return subprocess.call(
                [str(binary), *arguments], cwd=working_directory, env=_environment(root)
            )
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        print(f"CCCC development service: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
