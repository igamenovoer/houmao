"""Runtime lifecycle for the CLI hook observation channel.

This module owns the provider-launch side of the observation channel for the
Claude, Codex, and Kimi adapters:

- starting the per-session loopback collector before the provider process
  exists, capturing its ephemeral port, and waiting until it answers health
  checks;
- generating the per-session bearer token and carrying it through the launch
  plan metadata only (the provider receives it through the ``local_interactive``
  launch wrapper, never through ``plan.env``);
- rewriting the adapter's observer configuration with the real collector port
  and installing it before the provider starts: Claude's ``settings.json``
  block, Codex's runtime-home ``hooks.json`` plus ``[hooks.state]`` pre-trust
  block, or Kimi's marker-delimited ``[[hooks]]`` block in the runtime-home
  ``config.toml``;
- allocating a new channel generation on every provider start or relaunch,
  and when a resume has to restart a dead collector, while adopting a live
  collector on control-plane resume;
- stopping the collector when the session stops.

Artifacts are adapter-scoped under
``<session_root>/hook-observation/<adapter>/``. Every observation failure
degrades to ``unavailable`` and returns the original launch plan shape;
instrumentation never fails a managed session.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import selectors
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final, Mapping

from houmao.hook_observation.codex_hooks_generator import build_collector_emitter_command
from houmao.hook_observation.install import (
    COLLECTOR_RECORD_FILENAME,
    ObserverInstallPath,
    allocate_next_generation,
    codex_hook_artifact_dir,
    hook_artifact_dir,
    hook_observation_enabled,
    install_codex_observer_configuration,
    install_kimi_observer_configuration,
    install_observer_configuration,
    kimi_hook_artifact_dir,
    mark_channel_stopped,
    read_channel_generation,
    remove_codex_observer_configuration,
    remove_kimi_observer_configuration,
    remove_observer_configuration,
    write_channel_install_status,
)
from houmao.hook_observation.kimi_hooks_generator import (
    build_collector_emitter_command as build_kimi_collector_emitter_command,
)
from houmao.hook_observation.settings_generator import TOKEN_ENV_VAR

from .models import LaunchPlan

COLLECTOR_MODULE: Final[str] = "houmao.hook_observation.collector"
COLLECTOR_LOG_FILENAME: Final[str] = "collector.log"
TOKEN_BYTES: Final[int] = 32
PORT_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^PORT (\d+)$")
HEALTH_PATH: Final[str] = "/health"
COLLECTOR_START_TIMEOUT_SECONDS: Final[float] = 10.0
COLLECTOR_HEALTH_TIMEOUT_SECONDS: Final[float] = 5.0
COLLECTOR_STOP_TIMEOUT_SECONDS: Final[float] = 5.0
_POLL_INTERVAL_SECONDS: Final[float] = 0.05


@dataclass(frozen=True)
class CollectorHandle:
    """One live collector process discovered from ``collector.json``."""

    pid: int
    port: int
    generation: int


@dataclass(frozen=True)
class _AdapterInstall:
    """Provider-neutral view of one adapter's observer install outcome."""

    install_path: ObserverInstallPath
    settings_path: Path | None
    appended_args: tuple[str, ...]
    detail: str | None


def activate_hook_observation_for_provider_start(
    plan: LaunchPlan,
    *,
    session_root: Path,
) -> LaunchPlan:
    """Start the collector and install observer configuration before a provider start.

    The returned plan carries the fresh token in its ``hook_observation``
    metadata for the ``local_interactive`` launch wrapper. The plan environment
    is never modified.

    Parameters
    ----------
    plan:
        Provider-start launch plan, with provisional observer metadata written
        by :func:`build_launch_plan`.
    session_root:
        Session root that owns the hook artifact directory.

    Returns
    -------
    LaunchPlan
        Updated plan, or the original plan when the channel is unavailable.
    """

    metadata = _hook_metadata(plan)
    if metadata is None or not metadata.get("enabled"):
        return plan
    if metadata.get("install_path") == "unavailable":
        return plan
    tool = plan.tool
    generation_value = metadata.get("generation")
    if (
        isinstance(generation_value, int)
        and not isinstance(generation_value, bool)
        and generation_value > 0
    ):
        generation = generation_value
    else:
        allocated = _allocate_generation(session_root, tool=tool)
        if allocated is None:
            return plan
        generation = allocated
    generation = max(generation, read_channel_generation(session_root, tool=tool))
    return _activate(
        plan,
        session_root=session_root,
        generation=generation,
        token=secrets.token_hex(TOKEN_BYTES),
    )


def ensure_hook_observation_on_resume(
    plan: LaunchPlan,
    *,
    session_root: Path,
    env: Mapping[str, str] | None = None,
) -> LaunchPlan:
    """Reuse or restart the collector when a runtime controller resumes.

    A live collector is reused without bumping the generation, because the
    running provider still points at its port and token. When no live
    collector exists, a new generation is allocated and installed, matching the
    channel-generation isolation requirement for subsequent provider starts.

    Parameters
    ----------
    plan:
        Resume-control launch plan.
    session_root:
        Session root that owns the hook artifact directory.
    env:
        Environment mapping used to re-evaluate the opt-in flag.

    Returns
    -------
    LaunchPlan
        Updated plan, or the original plan when the channel is inactive.
    """

    metadata = _hook_metadata(plan)
    if metadata is None or not metadata.get("enabled"):
        return plan
    tool = plan.tool
    if not hook_observation_enabled(env, tool=tool):
        return plan
    if metadata.get("install_path") == "unavailable":
        return plan

    existing = live_collector(session_root, tool=tool)
    if existing is not None:
        updated_metadata = {
            **metadata,
            "generation": existing.generation,
            "port": existing.port,
            "collector_pid": existing.pid,
            "detail": "collector reused on resume",
        }
        write_channel_install_status(
            session_root=session_root,
            generation=existing.generation,
            install_path=_install_path(metadata),
            channel_state="active",
            detail="collector reused on resume",
            settings_path=_optional_path(metadata.get("settings_path")),
            port=existing.port,
            collector_pid=existing.pid,
            tool=tool,
        )
        return _with_hook_metadata(plan, updated_metadata)

    generation = _allocate_generation(session_root, tool=tool)
    if generation is None:
        return plan
    return _activate(
        plan,
        session_root=session_root,
        generation=generation,
        token=secrets.token_hex(TOKEN_BYTES),
    )


def _allocate_generation(session_root: Path, *, tool: str = "claude") -> int | None:
    """Allocate a generation, or return ``None`` when artifacts are unwritable."""

    try:
        return allocate_next_generation(session_root, tool=tool)
    except OSError:
        return None


def stop_hook_observation(session_root: Path | None, *, tool: str = "claude") -> None:
    """Stop the session's collector, tolerating an already-dead process."""

    if session_root is None:
        return
    stop_collector(session_root, tool=tool)


def start_collector(
    *,
    session_root: Path,
    generation: int,
    token: str,
    timeout_seconds: float = COLLECTOR_START_TIMEOUT_SECONDS,
    tool: str = "claude",
) -> CollectorHandle:
    """Start a detached collector subprocess and wait until it accepts traffic.

    Parameters
    ----------
    session_root:
        Session root that owns the hook artifact directory.
    generation:
        Channel generation stamped onto accepted events.
    token:
        Bearer token passed only through the collector's environment.
    timeout_seconds:
        Maximum time to wait for the ``PORT`` line and a ready health endpoint.
    tool:
        Provider tool whose adapter directory owns the collector artifacts.

    Returns
    -------
    CollectorHandle
        Live collector pid, port, and generation.

    Raises
    ------
    RuntimeError
        If the collector exits early, never reports a port, or never becomes
        healthy.
    """

    artifact_dir = hook_artifact_dir(session_root, tool=tool)
    artifact_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(artifact_dir, 0o700)
    log_path = artifact_dir / COLLECTOR_LOG_FILENAME
    environment = os.environ.copy()
    environment[TOKEN_ENV_VAR] = token
    stderr_descriptor = os.open(
        log_path,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    try:
        os.fchmod(stderr_descriptor, 0o600)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                COLLECTOR_MODULE,
                "--store",
                str(artifact_dir),
                "--generation",
                str(generation),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr_descriptor,
            env=environment,
            start_new_session=True,
        )
    finally:
        os.close(stderr_descriptor)

    try:
        port = _read_port_line(process, timeout_seconds=timeout_seconds)
        _wait_for_collector_health(
            process,
            port=port,
            timeout_seconds=COLLECTOR_HEALTH_TIMEOUT_SECONDS,
        )
    except BaseException:
        _terminate_process(process)
        raise
    _COLLECTOR_PROCESSES[(session_root.resolve(), tool)] = process
    return CollectorHandle(pid=process.pid, port=port, generation=generation)


def stop_collector(
    session_root: Path,
    *,
    timeout_seconds: float = COLLECTOR_STOP_TIMEOUT_SECONDS,
    tool: str = "claude",
) -> bool:
    """Stop the collector recorded in ``collector.json``.

    Parameters
    ----------
    session_root:
        Session root that owns the hook artifact directory.
    timeout_seconds:
        Grace period after ``SIGTERM`` before ``SIGKILL``.
    tool:
        Provider tool whose adapter directory owns the collector artifacts.

    Returns
    -------
    bool
        ``True`` when a live collector was stopped, ``False`` when no live
        collector existed or the record was unreadable.
    """

    record = _read_collector_record(session_root, tool=tool)
    if record is None:
        return False
    pid = _int_value(record.get("pid"))
    if pid is None or pid <= 0 or not _pid_running(pid):
        _reap_registered_process(session_root, tool=tool)
        _mark_channel_stopped_from_record(session_root, record, tool=tool)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        _reap_registered_process(session_root, tool=tool)
        _mark_channel_stopped_from_record(session_root, record, tool=tool)
        return False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_running(pid):
            _reap_registered_process(session_root, tool=tool)
            _mark_channel_stopped_from_record(session_root, record, tool=tool)
            return True
        if _collector_record_status(session_root, tool=tool) == "stopped":
            _reap_registered_process(session_root, tool=tool)
            _mark_channel_stopped_from_record(session_root, record, tool=tool)
            return True
        time.sleep(_POLL_INTERVAL_SECONDS)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        _reap_registered_process(session_root, tool=tool)
        _mark_channel_stopped_from_record(session_root, record, tool=tool)
        return True
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if not _pid_running(pid):
            _reap_registered_process(session_root, tool=tool)
            _mark_channel_stopped_from_record(session_root, record, tool=tool)
            return True
        time.sleep(_POLL_INTERVAL_SECONDS)
    return False


def live_collector(
    session_root: Path,
    *,
    generation: int | None = None,
    tool: str = "claude",
) -> CollectorHandle | None:
    """Return the running collector for one session, or ``None``.

    Parameters
    ----------
    session_root:
        Session root that owns the hook artifact directory.
    generation:
        Optional required generation.
    tool:
        Provider tool whose adapter directory owns the collector artifacts.

    Returns
    -------
    CollectorHandle | None
        The live collector when its pid is alive and its health endpoint
        answers.
    """

    record = _read_collector_record(session_root, tool=tool)
    if record is None or record.get("status") != "running":
        return None
    pid = _int_value(record.get("pid"))
    port = _int_value(record.get("port"))
    record_generation = _int_value(record.get("generation"))
    if pid is None or pid <= 0 or port is None or record_generation is None:
        return None
    if generation is not None and record_generation != generation:
        return None
    if not _pid_running(pid):
        return None
    if not _collector_health(port):
        return None
    return CollectorHandle(pid=pid, port=port, generation=record_generation)


def _install_observer_for_tool(
    *,
    plan: LaunchPlan,
    tool: str,
    session_root: Path,
    generation: int,
    port: int,
    resolved_args: list[str],
) -> _AdapterInstall:
    """Install one adapter's observer configuration for a live collector port."""

    if tool == "codex":
        codex_result = install_codex_observer_configuration(
            home_path=plan.home_path,
            generation=generation,
            emitter_command=build_collector_emitter_command(
                port=port,
                store=codex_hook_artifact_dir(session_root),
                generation=generation,
            ),
        )
        return _AdapterInstall(
            install_path=codex_result.install_path,
            settings_path=codex_result.config_path,
            appended_args=(),
            detail=codex_result.detail,
        )
    if tool == "kimi":
        kimi_result = install_kimi_observer_configuration(
            home_path=plan.home_path,
            generation=generation,
            emitter_command=build_kimi_collector_emitter_command(
                port=port,
                store=kimi_hook_artifact_dir(session_root),
                generation=generation,
            ),
        )
        return _AdapterInstall(
            install_path=kimi_result.install_path,
            settings_path=kimi_result.config_path,
            appended_args=(),
            detail=kimi_result.detail,
        )
    if tool != "claude":
        return _AdapterInstall(
            install_path="unavailable",
            settings_path=None,
            appended_args=(),
            detail=f"unsupported hook observation adapter {tool!r}",
        )
    result = install_observer_configuration(
        home_path=plan.home_path,
        session_root=session_root,
        generation=generation,
        port=port,
        resolved_args=resolved_args,
    )
    return _AdapterInstall(
        install_path=result.install_path,
        settings_path=result.settings_path,
        appended_args=tuple(result.appended_args),
        detail=result.detail,
    )


def _activate(
    plan: LaunchPlan,
    *,
    session_root: Path,
    generation: int,
    token: str,
) -> LaunchPlan:
    """Start the collector, install observer configuration, and return the plan."""

    tool = plan.tool
    metadata = _hook_metadata(plan) or {}
    args = _strip_observer_settings_args(plan.args, metadata)
    existing = live_collector(session_root, tool=tool)
    if existing is not None:
        stop_collector(session_root, tool=tool)
    try:
        collector = start_collector(
            session_root=session_root,
            generation=generation,
            token=token,
            tool=tool,
        )
    except Exception as exc:
        return _degrade(
            plan,
            session_root=session_root,
            generation=generation,
            detail=f"collector start failed: {exc}",
        )

    try:
        result = _install_observer_for_tool(
            plan=plan,
            tool=tool,
            session_root=session_root,
            generation=generation,
            port=collector.port,
            resolved_args=args,
        )
    except Exception as exc:
        stop_collector(session_root, tool=tool)
        return _degrade(
            plan,
            session_root=session_root,
            generation=generation,
            detail=f"observer configuration install failed: {exc}",
        )

    if result.install_path == "unavailable":
        stop_collector(session_root, tool=tool)
        return _degrade(
            plan,
            session_root=session_root,
            generation=generation,
            detail=result.detail or "observer configuration unavailable",
        )

    updated_metadata = _installed_metadata(
        plan=plan,
        result=result,
        generation=generation,
        port=collector.port,
        collector_pid=collector.pid,
        token=token,
        session_root=session_root,
    )
    write_channel_install_status(
        session_root=session_root,
        generation=generation,
        install_path=result.install_path,
        channel_state="active",
        detail=result.detail,
        settings_path=result.settings_path,
        port=collector.port,
        collector_pid=collector.pid,
        tool=tool,
    )
    return replace(
        plan,
        args=[*args, *result.appended_args],
        metadata={**plan.metadata, "hook_observation": updated_metadata},
    )


def _degrade(
    plan: LaunchPlan,
    *,
    session_root: Path,
    generation: int,
    detail: str,
) -> LaunchPlan:
    """Return a TUI-only plan after an observation failure."""

    tool = plan.tool
    metadata = _hook_metadata(plan) or {}
    args = _strip_observer_settings_args(plan.args, metadata)
    if tool == "codex":
        remove_codex_observer_configuration(home_path=plan.home_path)
    elif tool == "kimi":
        remove_kimi_observer_configuration(home_path=plan.home_path)
    else:
        remove_observer_configuration(home_path=plan.home_path, session_root=session_root)
    write_channel_install_status(
        session_root=session_root,
        generation=generation,
        install_path="unavailable",
        channel_state="unavailable",
        detail=detail,
        tool=tool,
    )
    updated_metadata = {
        **metadata,
        "enabled": True,
        "install_path": "unavailable",
        "generation": generation,
        "port": None,
        "collector_pid": None,
        "settings_path": None,
        "settings_args": [],
        "detail": detail,
        "session_root": str(session_root.resolve()),
        "token_env": TOKEN_ENV_VAR,
    }
    updated_metadata.pop("token", None)
    return replace(
        plan,
        args=args,
        metadata={**plan.metadata, "hook_observation": updated_metadata},
    )


def _installed_metadata(
    *,
    plan: LaunchPlan,
    result: _AdapterInstall,
    generation: int,
    port: int,
    collector_pid: int,
    token: str,
    session_root: Path,
) -> dict[str, Any]:
    """Build the in-memory hook observation metadata for one provider start."""

    metadata = _hook_metadata(plan) or {}
    return {
        **metadata,
        "enabled": True,
        "install_path": result.install_path,
        "generation": generation,
        "port": port,
        "collector_pid": collector_pid,
        "settings_path": str(result.settings_path) if result.settings_path is not None else None,
        "settings_args": list(result.appended_args),
        "detail": result.detail,
        "session_root": str(session_root.resolve()),
        "token": token,
        "token_env": TOKEN_ENV_VAR,
    }


def _strip_observer_settings_args(
    args: list[str],
    metadata: Mapping[str, Any],
) -> list[str]:
    """Remove observer-owned ``--settings`` pairs from launch arguments."""

    raw_marker = metadata.get("settings_args")
    if not isinstance(raw_marker, list) or not raw_marker:
        return list(args)
    if not all(isinstance(item, str) for item in raw_marker):
        return list(args)
    marker = tuple(raw_marker)
    stripped: list[str] = []
    index = 0
    while index < len(args):
        if tuple(args[index : index + len(marker)]) == marker:
            index += len(marker)
            continue
        stripped.append(args[index])
        index += 1
    return stripped


def _hook_metadata(plan: LaunchPlan) -> dict[str, Any] | None:
    """Return the plan's hook observation metadata when present."""

    value = plan.metadata.get("hook_observation")
    return dict(value) if isinstance(value, dict) else None


def _with_hook_metadata(plan: LaunchPlan, metadata: Mapping[str, Any]) -> LaunchPlan:
    """Return a plan with replaced hook observation metadata."""

    return replace(
        plan,
        metadata={**plan.metadata, "hook_observation": dict(metadata)},
    )


def _optional_path(value: object) -> Path | None:
    """Return one optional path from plan metadata."""

    return Path(value) if isinstance(value, str) and value else None


def _install_path(metadata: Mapping[str, Any]) -> ObserverInstallPath:
    """Return a safe install-path label from plan metadata."""

    value = metadata.get("install_path")
    if value == "settings_file":
        return "settings_file"
    if value == "unavailable":
        return "unavailable"
    return "managed_home"


def _read_port_line(process: subprocess.Popen[bytes], *, timeout_seconds: float) -> int:
    """Read the collector's ``PORT <n>`` line with a bounded timeout."""

    if process.stdout is None:
        raise RuntimeError("collector stdout is unavailable")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout_seconds
    buffer = b""
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"collector exited with code {process.returncode} before reporting a port"
                )
            wait_seconds = min(0.2, max(deadline - time.monotonic(), 0.01))
            if not selector.select(timeout=wait_seconds):
                continue
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                raise RuntimeError("collector stdout closed before reporting a port")
            buffer += chunk
            while b"\n" in buffer:
                raw_line, buffer = buffer.split(b"\n", 1)
                match = PORT_LINE_PATTERN.match(raw_line.decode("ascii", "replace").strip())
                if match is not None:
                    return int(match.group(1))
    finally:
        selector.close()
    raise RuntimeError(f"collector did not report a port within {timeout_seconds:.1f}s")


def _wait_for_collector_health(
    process: subprocess.Popen[bytes],
    *,
    port: int,
    timeout_seconds: float,
) -> None:
    """Wait until the collector answers a health request."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"collector exited with code {process.returncode} before becoming healthy"
            )
        if _collector_health(port):
            return
        time.sleep(_POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"collector health endpoint did not answer within {timeout_seconds:.1f}s")


def _collector_health(port: int) -> bool:
    """Return whether one collector health endpoint reports running."""

    url = f"http://127.0.0.1:{port}{HEALTH_PATH}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=0.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return False
    return isinstance(payload, dict) and payload.get("state") == "running"


def _read_collector_record(
    session_root: Path,
    *,
    tool: str = "claude",
) -> dict[str, Any] | None:
    """Read the secret-free collector liveness record."""

    path = hook_artifact_dir(session_root, tool=tool) / COLLECTOR_RECORD_FILENAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _mark_channel_stopped_from_record(
    session_root: Path,
    record: Mapping[str, Any],
    *,
    tool: str = "claude",
) -> None:
    """Publish a stopped channel state using one collector record."""

    generation = _int_value(record.get("generation"))
    if generation is None:
        return
    mark_channel_stopped(session_root=session_root, generation=generation, tool=tool)


def _collector_record_status(session_root: Path, *, tool: str = "claude") -> str | None:
    """Return the collector record status label, if readable."""

    record = _read_collector_record(session_root, tool=tool)
    status = record.get("status") if record is not None else None
    return status if isinstance(status, str) else None


def _int_value(value: object) -> int | None:
    """Return one optional integer metadata value."""

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _pid_running(pid: int) -> bool:
    """Return whether one pid is alive, reaping it when it is our child."""

    if pid <= 0:
        return False
    try:
        reaped, _ = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        reaped = 0
    except OSError:
        reaped = 0
    if reaped == pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _reap_registered_process(session_root: Path, *, tool: str = "claude") -> None:
    """Reap a collector child this process started, when present."""

    process = _COLLECTOR_PROCESSES.pop((session_root.resolve(), tool), None)
    if process is None:
        return
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1.0)


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    """Terminate one failed collector subprocess."""

    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=2.0)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
            process.wait(timeout=2.0)
        except (OSError, subprocess.TimeoutExpired):
            return


_COLLECTOR_PROCESSES: dict[tuple[Path, str], subprocess.Popen[bytes]] = {}
