"""CAO server lifecycle helpers for the interactive demo."""

from __future__ import annotations

import os
import shutil
import signal
import socket
import time
from pathlib import Path

from gig_agents.demo.cao_interactive_demo.models import (
    DEFAULT_CAO_SERVICE_NAME,
    DEFAULT_CAO_STOP_CLEAR_POLL_SECONDS,
    DEFAULT_CAO_STOP_CLEAR_TIMEOUT_SECONDS,
    FIXED_CAO_BASE_URL,
    PORT_LISTEN_STATE,
    TEST_LOOPBACK_PORT_LISTENING_ENV,
    CommandResult,
    CommandRunner,
    DemoEnvironment,
    DemoPaths,
    DemoWorkflowError,
)
from gig_agents.demo.cao_interactive_demo.rendering import _parse_json_output
from gig_agents.demo.cao_interactive_demo.runtime import _launcher_cli_command


def _write_launcher_config(
    path: Path,
    *,
    env: DemoEnvironment,
    runtime_root: Path,
) -> None:
    """Write the fixed loopback CAO launcher config file."""

    env.launcher_home_dir.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            f'base_url = "{FIXED_CAO_BASE_URL}"',
            f'runtime_root = "{runtime_root}"',
            f'home_dir = "{env.launcher_home_dir}"',
            'proxy_policy = "clear"',
            "startup_timeout_seconds = 15",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _ensure_cao_server(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> None:
    """Ensure the fixed loopback CAO server is fresh for this demo run."""

    status_payload = _launcher_status_payload(paths=paths, env=env, run_command=run_command)
    if bool(status_payload.get("healthy")):
        if not _launcher_status_is_verified_cao_server(status_payload):
            service = status_payload.get("service")
            raise DemoWorkflowError(
                "The fixed loopback target is already occupied by a process that did not "
                "verify as `cao-server` "
                f"(service={service!r}). Stop that process and retry."
            )
        _replace_existing_cao_server(paths=paths, env=env, run_command=run_command)
    else:
        if _loopback_port_is_listening(FIXED_CAO_BASE_URL):
            detail = status_payload.get("error")
            raise DemoWorkflowError(
                "The fixed loopback target is occupied by a process that could not be "
                "safely verified as `cao-server`" + (f": {detail}" if detail else ".")
            )
        if shutil.which("cao-server") is None:
            raise DemoWorkflowError(
                "CAO server is unavailable at the fixed loopback target and "
                "`cao-server` is not available on PATH."
            )

    start_payload = _launcher_start_payload(
        paths=paths,
        env=env,
        run_command=run_command,
        log_prefix="cao-start",
    )
    if bool(start_payload.get("reused_existing_process")):
        raise DemoWorkflowError(
            "Interactive demo startup refused to reuse an existing fixed-port `cao-server`; "
            "replace the server and retry."
        )


def _launcher_status_payload(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Run launcher `status` and return its parsed JSON payload."""

    result = run_command(
        _launcher_cli_command(["status", "--config", str(paths.launcher_config_path)]),
        env.repo_root,
        paths.logs_dir / "cao-status.stdout",
        paths.logs_dir / "cao-status.stderr",
        env.timeout_seconds,
    )
    return _parse_command_json_output(
        result,
        context="CAO launcher status output",
        allow_stderr_json=True,
    )


def _launcher_start_payload(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
    log_prefix: str,
) -> dict[str, object]:
    """Run launcher `start` and require a healthy replacement server."""

    result = run_command(
        _launcher_cli_command(["start", "--config", str(paths.launcher_config_path)]),
        env.repo_root,
        paths.logs_dir / f"{log_prefix}.stdout",
        paths.logs_dir / f"{log_prefix}.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        raise DemoWorkflowError(
            "Failed to start the fixed loopback `cao-server` via launcher "
            f"(see `{result.stderr_path}`)."
        )
    return _parse_json_output(result.stdout, context="CAO launcher start output")


def _launcher_status_is_verified_cao_server(status_payload: dict[str, object]) -> bool:
    """Return whether launcher status verified a healthy local `cao-server`."""

    if not bool(status_payload.get("healthy")):
        return False
    service = status_payload.get("service")
    return isinstance(service, str) and service.strip() == DEFAULT_CAO_SERVICE_NAME


def _parse_command_json_output(
    result: CommandResult,
    *,
    context: str,
    allow_stderr_json: bool = False,
) -> dict[str, object]:
    """Parse a command result as JSON from stdout or, optionally, stderr."""

    if result.stdout.strip():
        return _parse_json_output(result.stdout, context=context)
    if allow_stderr_json and result.stderr.strip():
        return _parse_json_output(result.stderr, context=context)
    raise DemoWorkflowError(f"Missing JSON in {context}.")


def _replace_existing_cao_server(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> None:
    """Stop the currently verified loopback `cao-server` before replacement."""

    if _stop_cao_server_with_known_configs(paths=paths, env=env, run_command=run_command):
        return

    candidate_pids = _find_listening_pids_for_port(_fixed_cao_port())
    if len(candidate_pids) != 1:
        raise DemoWorkflowError(
            "Refusing to replace the fixed loopback `cao-server` because the listening "
            "process could not be uniquely identified."
        )

    pid = candidate_pids[0]
    cmdline = _read_process_cmdline(pid)
    if cmdline is None or not _looks_like_cao_server_cmdline(cmdline):
        raise DemoWorkflowError(
            "Refusing to replace the fixed loopback service because the listening "
            f"process did not verify as `cao-server` (pid={pid})."
        )

    _terminate_process(pid)
    if _loopback_port_is_listening(FIXED_CAO_BASE_URL):
        raise DemoWorkflowError(
            "Failed to clear the fixed loopback `cao-server` before replacement."
        )


def _stop_cao_server_with_known_configs(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> bool:
    """Try launcher-managed stop using the current and previously recorded demo configs."""

    config_paths = _known_launcher_config_paths(paths=paths, env=env)
    for index, config_path in enumerate(config_paths, start=1):
        result = run_command(
            _launcher_cli_command(["stop", "--config", str(config_path)]),
            env.repo_root,
            paths.logs_dir / f"cao-stop-{index}.stdout",
            paths.logs_dir / f"cao-stop-{index}.stderr",
            env.timeout_seconds,
        )
        stop_payload = _parse_command_json_output(
            result,
            context="CAO launcher stop output",
            allow_stderr_json=True,
        )
        if bool(stop_payload.get("stopped")) or bool(stop_payload.get("already_stopped")):
            if _wait_for_loopback_port_clear(
                timeout_seconds=DEFAULT_CAO_STOP_CLEAR_TIMEOUT_SECONDS
            ):
                return True
        if not _loopback_port_is_listening(FIXED_CAO_BASE_URL):
            return True
    return False


def _known_launcher_config_paths(*, paths: DemoPaths, env: DemoEnvironment) -> list[Path]:
    """Return launcher config candidates that may own the current fixed-port server."""

    candidates: list[Path] = [paths.launcher_config_path]
    previous_workspace_root: Path | None = None
    if env.current_run_root_path.is_file():
        raw_value = env.current_run_root_path.read_text(encoding="utf-8").strip()
        if raw_value:
            resolved = Path(raw_value).expanduser().resolve()
            if resolved.exists():
                previous_workspace_root = resolved
    if previous_workspace_root is not None:
        candidates.append(
            DemoPaths.from_workspace_root(previous_workspace_root).launcher_config_path
        )

    if env.demo_base_root.exists():
        for candidate_dir in sorted(env.demo_base_root.iterdir(), reverse=True):
            if not candidate_dir.is_dir():
                continue
            config_path = candidate_dir / "cao-server-launcher.toml"
            if config_path.exists():
                candidates.append(config_path)

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        unique_candidates.append(resolved)
    return unique_candidates


def _loopback_port_is_listening(_: str) -> bool:
    """Return whether the fixed loopback TCP port currently has a listener."""

    forced_state = os.environ.get(TEST_LOOPBACK_PORT_LISTENING_ENV)
    if forced_state is not None:
        normalized = forced_state.strip().lower()
        if normalized in {"1", "true", "yes", "y", "occupied", "listening"}:
            return True
        if normalized in {"0", "false", "no", "n", "free", "not_listening"}:
            return False

    parsed = socket.getaddrinfo("127.0.0.1", _fixed_cao_port(), type=socket.SOCK_STREAM)
    for family, socktype, proto, _, sockaddr in parsed:
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(0.5)
                if sock.connect_ex(sockaddr) == 0:
                    return True
        except OSError:
            continue
    return False


def _fixed_cao_port() -> int:
    """Return the TCP port used by the fixed loopback CAO base URL."""

    return int(FIXED_CAO_BASE_URL.rsplit(":", maxsplit=1)[1])


def _find_listening_pids_for_port(port: int) -> list[int]:
    """Return process identifiers listening on the given TCP port."""

    inodes = _list_listening_socket_inodes(port)
    if not inodes:
        return []
    return sorted(_find_pids_for_socket_inodes(inodes))


def _list_listening_socket_inodes(port: int) -> set[str]:
    """Collect listening TCP socket inodes for the provided port from `/proc`."""

    proc_paths = (Path("/proc/net/tcp"), Path("/proc/net/tcp6"))
    target_port = f"{port:04X}"
    inodes: set[str] = set()
    for proc_path in proc_paths:
        if not proc_path.exists():
            continue
        for raw_line in proc_path.read_text(encoding="utf-8").splitlines()[1:]:
            parts = raw_line.split()
            if len(parts) < 10:
                continue
            local_address = parts[1]
            state = parts[3]
            inode = parts[9]
            if ":" not in local_address:
                continue
            _, port_hex = local_address.rsplit(":", maxsplit=1)
            if state == PORT_LISTEN_STATE and port_hex.upper() == target_port:
                inodes.add(inode)
    return inodes


def _find_pids_for_socket_inodes(inodes: set[str]) -> set[int]:
    """Map socket inodes back to owning process identifiers."""

    matched_pids: set[int] = set()
    if not inodes:
        return matched_pids

    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit():
            continue
        fd_dir = proc_dir / "fd"
        if not fd_dir.exists():
            continue
        try:
            fd_paths = tuple(fd_dir.iterdir())
        except OSError:
            continue
        for fd_path in fd_paths:
            try:
                target = os.readlink(fd_path)
            except OSError:
                continue
            if not target.startswith("socket:["):
                continue
            inode = target.removeprefix("socket:[").removesuffix("]")
            if inode in inodes:
                matched_pids.add(int(proc_dir.name))
                break
    return matched_pids


def _wait_for_loopback_port_clear(*, timeout_seconds: float) -> bool:
    """Wait for the fixed loopback CAO port to stop listening."""

    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    while time.monotonic() < deadline:
        if not _loopback_port_is_listening(FIXED_CAO_BASE_URL):
            return True
        time.sleep(DEFAULT_CAO_STOP_CLEAR_POLL_SECONDS)
    return not _loopback_port_is_listening(FIXED_CAO_BASE_URL)


def _read_process_cmdline(pid: int) -> str | None:
    """Read `/proc/<pid>/cmdline` and collapse it into one human-friendly string."""

    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    if not cmdline_path.exists():
        return None
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        return None
    if not raw:
        return ""
    return " ".join(token for token in raw.decode("utf-8", errors="replace").split("\x00") if token)


def _looks_like_cao_server_cmdline(cmdline: str) -> bool:
    """Return whether a process command line looks like `cao-server`."""

    lowered = cmdline.lower()
    return "cao-server" in lowered or "cli_agent_orchestrator" in lowered


def _terminate_process(pid: int) -> None:
    """Terminate a process with SIGTERM and SIGKILL fallback."""

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        raise DemoWorkflowError(f"Failed to terminate pid {pid}: {exc}.") from exc

    if _wait_for_process_exit(pid, timeout_seconds=10.0):
        return

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as exc:
        raise DemoWorkflowError(f"Failed to SIGKILL pid {pid}: {exc}.") from exc

    if not _wait_for_process_exit(pid, timeout_seconds=2.0):
        raise DemoWorkflowError(f"Process {pid} did not exit after replacement shutdown.")


def _wait_for_process_exit(pid: int, *, timeout_seconds: float) -> bool:
    """Wait until a process exits or the timeout budget is exhausted."""

    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        time.sleep(0.1)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False
