"""Detached startup helpers for `houmao-mgr server start`."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import click
from pydantic import BaseModel, ConfigDict

from houmao.server.client import HoumaoServerClient
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import HoumaoCurrentInstance

_DEFAULT_STARTUP_TIMEOUT_SECONDS = 10.0
_DEFAULT_POLL_INTERVAL_SECONDS = 0.1
_DEFAULT_HEALTH_TIMEOUT_SECONDS = 0.5
_STDOUT_LOG_NAME = "houmao-server.stdout.log"
_STDERR_LOG_NAME = "houmao-server.stderr.log"
_MIXED_PAIR_ERROR = (
    "The supported replacement is `houmao-server + houmao-mgr`; "
    "mixed usage with raw `cao-server` is unsupported."
)


class HoumaoServerStartLogPaths(BaseModel):
    """Stable detached-start log paths owned by one server root."""

    model_config = ConfigDict(extra="forbid", strict=True)

    stdout: str
    stderr: str


class HoumaoDetachedServerStartResult(BaseModel):
    """Detached startup result emitted by `houmao-mgr server start`."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool
    running: bool
    mode: str = "background"
    api_base_url: str
    detail: str
    reused_existing: bool = False
    pid: int | None = None
    exit_code: int | None = None
    server_root: str | None = None
    started_at_utc: str | None = None
    current_instance: HoumaoCurrentInstance | None = None
    log_paths: HoumaoServerStartLogPaths | None = None


def start_detached_server(
    config: HoumaoServerConfig,
    *,
    startup_timeout_seconds: float = _DEFAULT_STARTUP_TIMEOUT_SECONDS,
    poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS,
    health_timeout_seconds: float = _DEFAULT_HEALTH_TIMEOUT_SECONDS,
) -> HoumaoDetachedServerStartResult:
    """Start or reuse one detached `houmao-server` instance."""

    log_paths = _resolve_log_paths(config)
    existing_instance = _probe_ready_server(
        api_base_url=config.api_base_url,
        timeout_seconds=health_timeout_seconds,
        strict_pair_identity=True,
    )
    if existing_instance is not None:
        return _successful_start_result(
            config=config,
            current_instance=existing_instance,
            reused_existing=True,
            detail=(
                f"Reusing healthy houmao-server at {config.api_base_url} "
                f"(pid={existing_instance.pid})."
            ),
            log_paths=log_paths,
        )

    try:
        config.logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _failure_start_result(
            config=config,
            detail=f"Failed to prepare detached server log directory: {exc}",
            log_paths=log_paths,
        )

    try:
        process = _launch_detached_server(config=config, log_paths=log_paths)
    except OSError as exc:
        return _failure_start_result(
            config=config,
            detail=f"Failed to launch detached houmao-server: {exc}",
            log_paths=log_paths,
        )

    return _wait_for_detached_server(
        config=config,
        process=process,
        log_paths=log_paths,
        startup_timeout_seconds=startup_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        health_timeout_seconds=health_timeout_seconds,
    )


def _resolve_log_paths(config: HoumaoServerConfig) -> HoumaoServerStartLogPaths:
    """Return stable detached-start log paths for one resolved server config."""

    return HoumaoServerStartLogPaths(
        stdout=str((config.logs_dir / _STDOUT_LOG_NAME).resolve()),
        stderr=str((config.logs_dir / _STDERR_LOG_NAME).resolve()),
    )


def _probe_ready_server(
    *,
    api_base_url: str,
    timeout_seconds: float,
    strict_pair_identity: bool,
) -> HoumaoCurrentInstance | None:
    """Return a ready server instance when the target base URL is healthy."""

    client = HoumaoServerClient(
        api_base_url,
        timeout_seconds=timeout_seconds,
        create_timeout_seconds=timeout_seconds,
    )
    try:
        health = client.health_extended()
    except Exception:
        return None
    if health.status != "ok":
        return None
    try:
        return client.current_instance()
    except Exception as exc:
        if strict_pair_identity:
            raise click.ClickException(_MIXED_PAIR_ERROR) from exc
        return None


def _launch_detached_server(
    *,
    config: HoumaoServerConfig,
    log_paths: HoumaoServerStartLogPaths,
) -> subprocess.Popen[bytes]:
    """Spawn one detached child that re-enters `houmao-mgr server start`."""

    command = _background_server_command(config)
    stdout_path = Path(log_paths.stdout)
    stderr_path = Path(log_paths.stderr)
    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        return subprocess.Popen(
            command,
            cwd=Path.cwd(),
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )


def _background_server_command(config: HoumaoServerConfig) -> list[str]:
    """Build the detached child command line from one resolved config."""

    args = [
        sys.executable,
        "-m",
        "houmao.srv_ctrl",
        "server",
        "start",
        "--foreground",
        "--api-base-url",
        config.api_base_url,
        "--runtime-root",
        str(config.runtime_root),
        "--watch-poll-interval-seconds",
        str(config.watch_poll_interval_seconds),
        "--recent-transition-limit",
        str(config.recent_transition_limit),
        "--stability-threshold-seconds",
        str(config.stability_threshold_seconds),
        "--completion-stability-seconds",
        str(config.completion_stability_seconds),
        "--unknown-to-stalled-timeout-seconds",
        str(config.unknown_to_stalled_timeout_seconds),
        "--compat-shell-ready-timeout-seconds",
        str(config.compat_shell_ready_timeout_seconds),
        "--compat-shell-ready-poll-interval-seconds",
        str(config.compat_shell_ready_poll_interval_seconds),
        "--compat-provider-ready-timeout-seconds",
        str(config.compat_provider_ready_timeout_seconds),
        "--compat-provider-ready-poll-interval-seconds",
        str(config.compat_provider_ready_poll_interval_seconds),
        "--compat-codex-warmup-seconds",
        str(config.compat_codex_warmup_seconds),
    ]
    for tool, names in sorted(config.supported_tui_processes.items()):
        args.extend(["--supported-tui-process", f"{tool}={','.join(names)}"])
    args.append("--startup-child" if config.startup_child else "--no-startup-child")
    return args


def _wait_for_detached_server(
    *,
    config: HoumaoServerConfig,
    process: subprocess.Popen[bytes],
    log_paths: HoumaoServerStartLogPaths,
    startup_timeout_seconds: float,
    poll_interval_seconds: float,
    health_timeout_seconds: float,
) -> HoumaoDetachedServerStartResult:
    """Wait for the detached child to become healthy or fail clearly."""

    deadline = time.monotonic() + startup_timeout_seconds
    while time.monotonic() < deadline:
        current_instance = _probe_ready_server(
            api_base_url=config.api_base_url,
            timeout_seconds=health_timeout_seconds,
            strict_pair_identity=False,
        )
        if current_instance is not None:
            return _successful_start_result(
                config=config,
                current_instance=current_instance,
                reused_existing=False,
                detail=(
                    f"Started houmao-server at {config.api_base_url} "
                    f"(pid={current_instance.pid})."
                ),
                log_paths=log_paths,
            )

        returncode = process.poll()
        if returncode is not None:
            raced_instance = _probe_ready_server(
                api_base_url=config.api_base_url,
                timeout_seconds=health_timeout_seconds,
                strict_pair_identity=False,
            )
            if raced_instance is not None:
                return _successful_start_result(
                    config=config,
                    current_instance=raced_instance,
                    reused_existing=True,
                    detail=(
                        "Detected a healthy houmao-server after a detached launch race; "
                        f"spawned process exited with code {returncode}."
                    ),
                    log_paths=log_paths,
                )
            return _failure_start_result(
                config=config,
                detail=(
                    "Detached houmao-server exited before becoming healthy "
                    f"(exit code {returncode})."
                ),
                log_paths=log_paths,
                pid=process.pid,
                exit_code=returncode,
            )
        time.sleep(max(0.01, poll_interval_seconds))

    _terminate_detached_process(process)
    return _failure_start_result(
        config=config,
        detail=(
            f"`{config.api_base_url}` did not become healthy within "
            f"{startup_timeout_seconds:.1f} seconds."
        ),
        log_paths=log_paths,
        pid=process.pid,
    )


def _terminate_detached_process(process: subprocess.Popen[bytes]) -> None:
    """Best-effort terminate one detached child process group."""

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        return

    try:
        process.wait(timeout=2.0)
        return
    except subprocess.TimeoutExpired:
        pass

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        return

    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        return


def _successful_start_result(
    *,
    config: HoumaoServerConfig,
    current_instance: HoumaoCurrentInstance,
    reused_existing: bool,
    detail: str,
    log_paths: HoumaoServerStartLogPaths,
) -> HoumaoDetachedServerStartResult:
    """Build one successful detached-start result payload."""

    return HoumaoDetachedServerStartResult(
        success=True,
        running=True,
        api_base_url=config.api_base_url,
        detail=detail,
        reused_existing=reused_existing,
        pid=current_instance.pid,
        server_root=current_instance.server_root,
        started_at_utc=current_instance.started_at_utc,
        current_instance=current_instance,
        log_paths=log_paths,
    )


def _failure_start_result(
    *,
    config: HoumaoServerConfig,
    detail: str,
    log_paths: HoumaoServerStartLogPaths | None,
    pid: int | None = None,
    exit_code: int | None = None,
) -> HoumaoDetachedServerStartResult:
    """Build one unsuccessful detached-start result payload."""

    return HoumaoDetachedServerStartResult(
        success=False,
        running=False,
        api_base_url=config.api_base_url,
        detail=detail,
        pid=pid,
        exit_code=exit_code,
        server_root=str(config.server_root),
        log_paths=log_paths,
    )
