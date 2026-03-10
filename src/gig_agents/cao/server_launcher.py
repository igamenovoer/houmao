"""Utilities for launching and managing a local `cao-server` process."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
import tomllib
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from urllib import error, parse, request

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from .no_proxy import (
    SUPPORTED_LOOPBACK_CAO_BASE_URLS,
    inject_loopback_no_proxy_env,
    is_supported_loopback_cao_base_url,
    normalize_cao_base_url,
    scoped_loopback_no_proxy_for_cao_base_url,
)

SUPPORTED_CAO_BASE_URLS: tuple[str, ...] = SUPPORTED_LOOPBACK_CAO_BASE_URLS
_CONTROLLED_PROXY_ENV_VARS: tuple[str, ...] = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


class CaoServerLauncherError(RuntimeError):
    """Raised when launcher configuration or process management fails."""


class ProxyPolicy(str, Enum):
    """Proxy handling policy for the launched `cao-server` process."""

    CLEAR = "clear"
    INHERIT = "inherit"


class _LauncherConfigModel(BaseModel):
    """Strict shape for launcher TOML config parsing."""

    model_config = ConfigDict(extra="forbid")

    base_url: str
    runtime_root: str
    home_dir: str | None = None
    proxy_policy: ProxyPolicy = ProxyPolicy.CLEAR
    startup_timeout_seconds: float = 15.0

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        normalized = _normalize_base_url(value)
        if normalized not in SUPPORTED_CAO_BASE_URLS:
            supported = ", ".join(SUPPORTED_CAO_BASE_URLS)
            raise ValueError(f"must be one of: {supported}")
        return normalized

    @field_validator("runtime_root")
    @classmethod
    def _validate_runtime_root(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("home_dir")
    @classmethod
    def _validate_home_dir(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty when provided")
        return value.strip()

    @field_validator("startup_timeout_seconds")
    @classmethod
    def _validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


@dataclass(frozen=True)
class CaoServerLauncherConfig:
    """Resolved launcher configuration.

    Parameters
    ----------
    base_url:
        CAO base URL to health-check (`GET /health`).
    runtime_root:
        Root directory used for launcher artifacts.
    home_dir:
        Optional CAO `HOME` override for launched server process.
    proxy_policy:
        Proxy policy for launched process environment.
    startup_timeout_seconds:
        Time budget for health polling after launch.
    config_path:
        Source config path used for loading/validation.
    """

    base_url: str
    runtime_root: Path
    home_dir: Path | None
    proxy_policy: ProxyPolicy
    startup_timeout_seconds: float
    config_path: Path


@dataclass(frozen=True)
class CaoServerLauncherConfigOverrides:
    """Optional CLI/API overrides layered on top of config file values."""

    base_url: str | None = None
    runtime_root: Path | None = None
    home_dir: Path | None = None
    proxy_policy: ProxyPolicy | None = None
    startup_timeout_seconds: float | None = None


@dataclass(frozen=True)
class CaoServerRuntimeArtifacts:
    """Filesystem layout for CAO server runtime artifacts."""

    artifact_dir: Path
    pid_file: Path
    log_file: Path
    launcher_result_file: Path


@dataclass(frozen=True)
class CaoServerStatusResult:
    """Outcome of a CAO health check."""

    operation: str
    base_url: str
    healthy: bool
    health_status: str | None
    service: str | None
    error: str | None


@dataclass(frozen=True)
class CaoServerStartResult:
    """Outcome of CAO start/reuse operation."""

    operation: str
    base_url: str
    healthy: bool
    started_new_process: bool
    reused_existing_process: bool
    pid: int | None
    artifact_dir: Path
    pid_file: Path
    log_file: Path
    launcher_result_file: Path
    message: str


@dataclass(frozen=True)
class CaoServerStopResult:
    """Outcome of CAO stop operation."""

    operation: str
    base_url: str
    stopped: bool
    already_stopped: bool
    verification_passed: bool | None
    pid: int | None
    signal_sent: str | None
    artifact_dir: Path
    pid_file: Path
    message: str


def load_cao_server_launcher_config(
    config_path: Path,
    *,
    overrides: CaoServerLauncherConfigOverrides | None = None,
) -> CaoServerLauncherConfig:
    """Load and validate CAO launcher config.

    Parameters
    ----------
    config_path:
        Path to TOML launcher config.
    overrides:
        Optional in-memory overrides for ad-hoc CLI usage.

    Returns
    -------
    CaoServerLauncherConfig
        Parsed, validated, and path-resolved launcher config.

    Raises
    ------
    CaoServerLauncherError
        If file read/parsing/validation fails.
    """

    resolved_config_path = config_path.expanduser().resolve()
    if not resolved_config_path.exists():
        raise CaoServerLauncherError(
            f"Launcher config not found: `{resolved_config_path}`."
        )
    if not resolved_config_path.is_file():
        raise CaoServerLauncherError(
            f"Launcher config must be a file: `{resolved_config_path}`."
        )

    try:
        with resolved_config_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise CaoServerLauncherError(
            f"Malformed launcher TOML `{resolved_config_path}`: {exc}."
        ) from exc
    except OSError as exc:
        raise CaoServerLauncherError(
            f"Failed to read launcher config `{resolved_config_path}`: {exc}."
        ) from exc

    if not isinstance(raw, dict):
        raise CaoServerLauncherError(
            f"Launcher config `{resolved_config_path}` must contain a top-level table."
        )

    merged_raw = _apply_overrides(raw=raw, overrides=overrides)

    try:
        parsed = _LauncherConfigModel.model_validate(merged_raw)
    except ValidationError as exc:
        raise CaoServerLauncherError(
            _format_pydantic_error(
                f"Invalid launcher config `{resolved_config_path}`",
                exc,
            )
        ) from exc

    runtime_root = _resolve_runtime_root(
        parsed.runtime_root,
        base=resolved_config_path.parent,
    )
    home_dir = _resolve_home_dir(
        parsed.home_dir,
        config_path=resolved_config_path,
    )

    return CaoServerLauncherConfig(
        base_url=parsed.base_url,
        runtime_root=runtime_root,
        home_dir=home_dir,
        proxy_policy=parsed.proxy_policy,
        startup_timeout_seconds=float(parsed.startup_timeout_seconds),
        config_path=resolved_config_path,
    )


def resolve_cao_server_runtime_artifacts(
    config: CaoServerLauncherConfig,
) -> CaoServerRuntimeArtifacts:
    """Return deterministic artifact paths for a launcher config.

    Parameters
    ----------
    config:
        Launcher config.

    Returns
    -------
    CaoServerRuntimeArtifacts
        Paths under `runtime_root/cao-server/<host>-<port>/`.
    """

    parsed = parse.urlsplit(config.base_url)
    host = parsed.hostname
    port = parsed.port
    if host is None or port is None:
        raise CaoServerLauncherError(
            f"Invalid base_url `{config.base_url}`: missing host or port."
        )

    artifact_dir = config.runtime_root / "cao-server" / f"{host}-{port}"
    return CaoServerRuntimeArtifacts(
        artifact_dir=artifact_dir,
        pid_file=artifact_dir / "cao-server.pid",
        log_file=artifact_dir / "cao-server.log",
        launcher_result_file=artifact_dir / "launcher_result.json",
    )


def write_cao_server_pid(pid_file: Path, pid: int) -> None:
    """Write a CAO pidfile atomically.

    Parameters
    ----------
    pid_file:
        Destination pidfile path.
    pid:
        Process identifier to persist.
    """

    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(f"{pid}\n", encoding="utf-8")


def read_cao_server_pid(pid_file: Path) -> int:
    """Read a CAO pidfile.

    Parameters
    ----------
    pid_file:
        Source pidfile path.

    Returns
    -------
    int
        Parsed process id.

    Raises
    ------
    CaoServerLauncherError
        If file missing or malformed.
    """

    if not pid_file.exists():
        raise CaoServerLauncherError(f"Pidfile not found: `{pid_file}`.")
    raw = pid_file.read_text(encoding="utf-8").strip()
    if not raw:
        raise CaoServerLauncherError(f"Pidfile is empty: `{pid_file}`.")
    try:
        pid = int(raw)
    except ValueError as exc:
        raise CaoServerLauncherError(
            f"Pidfile `{pid_file}` does not contain an integer pid: `{raw}`."
        ) from exc
    if pid <= 0:
        raise CaoServerLauncherError(
            f"Pidfile `{pid_file}` contains non-positive pid: `{pid}`."
        )
    return pid


def build_cao_server_environment(
    *,
    base_env: Mapping[str, str] | None = None,
    proxy_policy: ProxyPolicy = ProxyPolicy.CLEAR,
    home_dir: Path | None = None,
) -> dict[str, str]:
    """Build subprocess env for launching `cao-server`.

    Parameters
    ----------
    base_env:
        Base environment to copy. Defaults to `os.environ`.
    proxy_policy:
        Proxy policy for controlled proxy variables.
    home_dir:
        Optional `HOME` override for launched process.

    Returns
    -------
    dict[str, str]
        Subprocess environment map.
    """

    env = dict(base_env if base_env is not None else os.environ)
    if proxy_policy == ProxyPolicy.CLEAR:
        for key in _CONTROLLED_PROXY_ENV_VARS:
            env.pop(key, None)
    elif proxy_policy != ProxyPolicy.INHERIT:
        raise CaoServerLauncherError(f"Unsupported proxy policy: `{proxy_policy}`.")

    inject_loopback_no_proxy_env(env)

    if home_dir is not None:
        env["HOME"] = str(home_dir)

    return env


def status_cao_server(
    config: CaoServerLauncherConfig,
    *,
    timeout_seconds: float = 3.0,
) -> CaoServerStatusResult:
    """Check CAO health by calling `GET /health`.

    Parameters
    ----------
    config:
        Launcher configuration.
    timeout_seconds:
        HTTP timeout for health request.

    Returns
    -------
    CaoServerStatusResult
        Health-check result.
    """

    url = f"{config.base_url}/health"
    req = request.Request(url, method="GET", headers={"Accept": "application/json"})

    try:
        with scoped_loopback_no_proxy_for_cao_base_url(config.base_url):
            with request.urlopen(req, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        detail = body[:200] if body else str(exc)
        return CaoServerStatusResult(
            operation="status",
            base_url=config.base_url,
            healthy=False,
            health_status=None,
            service=None,
            error=f"HTTP {int(exc.code)}: {detail}",
        )
    except (error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        detail = str(reason if reason is not None else exc)
        return CaoServerStatusResult(
            operation="status",
            base_url=config.base_url,
            healthy=False,
            health_status=None,
            service=None,
            error=detail,
        )
    except json.JSONDecodeError as exc:
        return CaoServerStatusResult(
            operation="status",
            base_url=config.base_url,
            healthy=False,
            health_status=None,
            service=None,
            error=f"/health returned invalid JSON: {exc}",
        )

    if not isinstance(payload, dict):
        return CaoServerStatusResult(
            operation="status",
            base_url=config.base_url,
            healthy=False,
            health_status=None,
            service=None,
            error=f"/health returned unexpected payload type: {type(payload).__name__}",
        )

    status_value = payload.get("status")
    service_value = payload.get("service")
    health_status = str(status_value) if status_value is not None else None
    service = str(service_value) if service_value is not None else None
    healthy = health_status == "ok"
    return CaoServerStatusResult(
        operation="status",
        base_url=config.base_url,
        healthy=healthy,
        health_status=health_status,
        service=service,
        error=None if healthy else "CAO health response is not ok",
    )


def start_cao_server(
    config: CaoServerLauncherConfig,
    *,
    status_timeout_seconds: float = 3.0,
    poll_interval_seconds: float = 0.2,
) -> CaoServerStartResult:
    """Start or reuse local `cao-server`.

    Parameters
    ----------
    config:
        Launcher configuration.
    status_timeout_seconds:
        Timeout used for each health probe.
    poll_interval_seconds:
        Poll interval while waiting for startup.

    Returns
    -------
    CaoServerStartResult
        Start operation outcome.

    Raises
    ------
    CaoServerLauncherError
        If start fails.
    """

    _ensure_supported_base_url(config.base_url)
    _validate_home_dir_or_raise(config.home_dir, config_path=config.config_path)

    artifacts = resolve_cao_server_runtime_artifacts(config)
    artifacts.artifact_dir.mkdir(parents=True, exist_ok=True)

    initial_status = status_cao_server(config, timeout_seconds=status_timeout_seconds)
    if initial_status.healthy:
        existing_pid = _read_pid_if_exists(artifacts.pid_file)
        result = CaoServerStartResult(
            operation="start",
            base_url=config.base_url,
            healthy=True,
            started_new_process=False,
            reused_existing_process=True,
            pid=existing_pid,
            artifact_dir=artifacts.artifact_dir,
            pid_file=artifacts.pid_file,
            log_file=artifacts.log_file,
            launcher_result_file=artifacts.launcher_result_file,
            message=f"CAO server already healthy at {config.base_url}.",
        )
        _write_launcher_result(artifacts.launcher_result_file, result)
        return result

    executable = _require_executable_on_path(
        "cao-server",
        install_hint=(
            "Install CAO with uv (`uv tool install cli-agent-orchestrator`) and "
            "verify with `command -v cao-server`."
        ),
    )

    launch_env = build_cao_server_environment(
        proxy_policy=config.proxy_policy,
        home_dir=config.home_dir,
    )

    with artifacts.log_file.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            [executable],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=launch_env,
            start_new_session=True,
        )

    write_cao_server_pid(artifacts.pid_file, process.pid)

    deadline = time.monotonic() + config.startup_timeout_seconds
    while time.monotonic() < deadline:
        probe = status_cao_server(config, timeout_seconds=status_timeout_seconds)
        if probe.healthy:
            result = CaoServerStartResult(
                operation="start",
                base_url=config.base_url,
                healthy=True,
                started_new_process=True,
                reused_existing_process=False,
                pid=process.pid,
                artifact_dir=artifacts.artifact_dir,
                pid_file=artifacts.pid_file,
                log_file=artifacts.log_file,
                launcher_result_file=artifacts.launcher_result_file,
                message=f"Started `cao-server` (pid={process.pid}).",
            )
            _write_launcher_result(artifacts.launcher_result_file, result)
            return result

        returncode = process.poll()
        if returncode is not None:
            race_probe = status_cao_server(
                config, timeout_seconds=status_timeout_seconds
            )
            if race_probe.healthy:
                artifacts.pid_file.unlink(missing_ok=True)
                result = CaoServerStartResult(
                    operation="start",
                    base_url=config.base_url,
                    healthy=True,
                    started_new_process=False,
                    reused_existing_process=True,
                    pid=_read_pid_if_exists(artifacts.pid_file),
                    artifact_dir=artifacts.artifact_dir,
                    pid_file=artifacts.pid_file,
                    log_file=artifacts.log_file,
                    launcher_result_file=artifacts.launcher_result_file,
                    message=(
                        "Detected a healthy CAO server after launch race; "
                        f"spawned process exited with code {returncode}."
                    ),
                )
                _write_launcher_result(artifacts.launcher_result_file, result)
                return result

            artifacts.pid_file.unlink(missing_ok=True)
            raise CaoServerLauncherError(
                "Failed to start `cao-server`: process exited early with "
                f"code {returncode}. See `{artifacts.log_file}`."
            )

        time.sleep(max(0.01, poll_interval_seconds))

    _terminate_process_tree(process.pid)
    artifacts.pid_file.unlink(missing_ok=True)
    raise CaoServerLauncherError(
        "Failed to start `cao-server`: health check did not become healthy "
        f"within {config.startup_timeout_seconds:.1f}s. See `{artifacts.log_file}`."
    )


def stop_cao_server(
    config: CaoServerLauncherConfig,
    *,
    grace_period_seconds: float = 10.0,
    poll_interval_seconds: float = 0.2,
) -> CaoServerStopResult:
    """Stop a pidfile-tracked CAO server.

    Parameters
    ----------
    config:
        Launcher configuration.
    grace_period_seconds:
        Wait time after SIGTERM before SIGKILL fallback.
    poll_interval_seconds:
        Poll interval while waiting for process exit.

    Returns
    -------
    CaoServerStopResult
        Stop operation outcome.
    """

    artifacts = resolve_cao_server_runtime_artifacts(config)
    if not artifacts.pid_file.exists():
        return CaoServerStopResult(
            operation="stop",
            base_url=config.base_url,
            stopped=False,
            already_stopped=True,
            verification_passed=None,
            pid=None,
            signal_sent=None,
            artifact_dir=artifacts.artifact_dir,
            pid_file=artifacts.pid_file,
            message=f"No pidfile found at `{artifacts.pid_file}`.",
        )

    pid = read_cao_server_pid(artifacts.pid_file)
    if not _is_process_running(pid):
        artifacts.pid_file.unlink(missing_ok=True)
        return CaoServerStopResult(
            operation="stop",
            base_url=config.base_url,
            stopped=False,
            already_stopped=True,
            verification_passed=None,
            pid=pid,
            signal_sent=None,
            artifact_dir=artifacts.artifact_dir,
            pid_file=artifacts.pid_file,
            message=f"Process {pid} is not running; removed stale pidfile.",
        )

    cmdline = _read_process_cmdline(pid)
    if cmdline is None:
        return CaoServerStopResult(
            operation="stop",
            base_url=config.base_url,
            stopped=False,
            already_stopped=False,
            verification_passed=False,
            pid=pid,
            signal_sent=None,
            artifact_dir=artifacts.artifact_dir,
            pid_file=artifacts.pid_file,
            message=(
                "Refusing to stop process because identity could not be verified: "
                f"cannot read cmdline for pid {pid}."
            ),
        )

    if not _looks_like_cao_server_cmdline(cmdline):
        return CaoServerStopResult(
            operation="stop",
            base_url=config.base_url,
            stopped=False,
            already_stopped=False,
            verification_passed=False,
            pid=pid,
            signal_sent=None,
            artifact_dir=artifacts.artifact_dir,
            pid_file=artifacts.pid_file,
            message=(
                "Refusing to stop process because cmdline does not look like "
                f"`cao-server` (pid={pid}, cmdline={cmdline})."
            ),
        )

    os.kill(pid, signal.SIGTERM)
    if _wait_for_exit(
        pid,
        timeout_seconds=grace_period_seconds,
        poll_interval_seconds=poll_interval_seconds,
    ):
        artifacts.pid_file.unlink(missing_ok=True)
        return CaoServerStopResult(
            operation="stop",
            base_url=config.base_url,
            stopped=True,
            already_stopped=False,
            verification_passed=True,
            pid=pid,
            signal_sent="SIGTERM",
            artifact_dir=artifacts.artifact_dir,
            pid_file=artifacts.pid_file,
            message=f"Stopped `cao-server` with SIGTERM (pid={pid}).",
        )

    os.kill(pid, signal.SIGKILL)
    if _wait_for_exit(
        pid,
        timeout_seconds=2.0,
        poll_interval_seconds=poll_interval_seconds,
    ):
        artifacts.pid_file.unlink(missing_ok=True)
        return CaoServerStopResult(
            operation="stop",
            base_url=config.base_url,
            stopped=True,
            already_stopped=False,
            verification_passed=True,
            pid=pid,
            signal_sent="SIGKILL",
            artifact_dir=artifacts.artifact_dir,
            pid_file=artifacts.pid_file,
            message=f"Stopped `cao-server` with SIGKILL (pid={pid}).",
        )

    raise CaoServerLauncherError(
        f"Failed to stop process {pid}: still running after SIGTERM/SIGKILL."
    )


def to_jsonable_payload(value: object) -> object:
    """Convert launcher dataclass payloads into JSON-serializable values.

    Parameters
    ----------
    value:
        Dataclass payload or nested structure.

    Returns
    -------
    object
        JSON-serializable equivalent.
    """

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): to_jsonable_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable_payload(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable_payload(item) for item in value]
    return value


def dataclass_to_json_payload(value: object) -> dict[str, object]:
    """Convert a launcher dataclass into a JSON-serializable mapping."""

    if not is_dataclass(value):
        raise CaoServerLauncherError("Expected dataclass payload for JSON conversion.")
    return to_jsonable_payload(asdict(value))  # type: ignore[arg-type, return-value]


def _apply_overrides(
    *,
    raw: dict[str, Any],
    overrides: CaoServerLauncherConfigOverrides | None,
) -> dict[str, Any]:
    merged = dict(raw)
    if overrides is None:
        return merged

    if overrides.base_url is not None:
        merged["base_url"] = overrides.base_url
    if overrides.runtime_root is not None:
        merged["runtime_root"] = str(overrides.runtime_root)
    if overrides.home_dir is not None:
        merged["home_dir"] = str(overrides.home_dir)
    if overrides.proxy_policy is not None:
        merged["proxy_policy"] = overrides.proxy_policy.value
    if overrides.startup_timeout_seconds is not None:
        merged["startup_timeout_seconds"] = overrides.startup_timeout_seconds
    return merged


def _normalize_base_url(value: str) -> str:
    return normalize_cao_base_url(value)


def _resolve_runtime_root(value: str, *, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _resolve_home_dir(value: str | None, *, config_path: Path) -> Path | None:
    if value is None:
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        raise CaoServerLauncherError(
            f"Invalid launcher config `{config_path}`: $.home_dir must be an absolute path."
        )
    resolved = path.resolve()
    _validate_home_dir_or_raise(resolved, config_path=config_path)
    return resolved


def _validate_home_dir_or_raise(home_dir: Path | None, *, config_path: Path) -> None:
    if home_dir is None:
        return
    if not home_dir.exists():
        raise CaoServerLauncherError(
            f"Invalid launcher config `{config_path}`: home_dir does not exist: `{home_dir}`."
        )
    if not home_dir.is_dir():
        raise CaoServerLauncherError(
            f"Invalid launcher config `{config_path}`: home_dir must be a directory: `{home_dir}`."
        )
    if not os.access(home_dir, os.W_OK):
        raise CaoServerLauncherError(
            "Invalid launcher config "
            f"`{config_path}`: home_dir must be writable because CAO writes state under "
            f"`HOME/.aws/cli-agent-orchestrator/` (home_dir=`{home_dir}`)."
        )


def _format_pydantic_error(prefix: str, exc: ValidationError) -> str:
    details: list[str] = []
    for issue in exc.errors(include_url=False):
        location = _format_error_location(issue.get("loc", ()))
        message = str(issue.get("msg", "validation failed"))
        details.append(f"{location}: {message}")
        if len(details) >= 5:
            break
    joined = "; ".join(details) if details else "validation failed"
    return f"{prefix}: {joined}"


def _require_executable_on_path(executable: str, *, install_hint: str) -> str:
    resolved = shutil.which(executable)
    if resolved is None:
        raise CaoServerLauncherError(
            f"`{executable}` not found on PATH. {install_hint}"
        )
    return resolved


def _format_error_location(location: object) -> str:
    if not isinstance(location, tuple) or not location:
        return "$"

    path = "$"
    for item in location:
        if isinstance(item, int):
            path += f"[{item}]"
            continue
        path += f".{item}"
    return path


def _ensure_supported_base_url(base_url: str) -> None:
    if not is_supported_loopback_cao_base_url(base_url):
        supported = ", ".join(SUPPORTED_CAO_BASE_URLS)
        raise CaoServerLauncherError(
            f"Unsupported base_url `{base_url}`. Supported values: {supported}."
        )


def _read_pid_if_exists(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return read_cao_server_pid(path)
    except CaoServerLauncherError:
        return None


def _write_launcher_result(path: Path, result: object) -> None:
    payload: dict[str, object]
    if hasattr(result, "__dataclass_fields__"):
        payload = dataclass_to_json_payload(result)
    else:
        payload = {"result": to_jsonable_payload(result)}
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_process_cmdline(pid: int) -> str | None:
    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    if not cmdline_path.exists():
        return None
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        return None

    if not raw:
        return ""
    tokens = [
        token for token in raw.decode("utf-8", errors="replace").split("\x00") if token
    ]
    return " ".join(tokens)


def _looks_like_cao_server_cmdline(cmdline: str) -> bool:
    lower = cmdline.lower()
    return "cao-server" in lower or "cli_agent_orchestrator" in lower


def _wait_for_exit(
    pid: int,
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> bool:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while time.monotonic() < deadline:
        if not _is_process_running(pid):
            return True
        time.sleep(max(0.01, poll_interval_seconds))
    return not _is_process_running(pid)


def _terminate_process_tree(pid: int) -> None:
    if not _is_process_running(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    if _wait_for_exit(pid, timeout_seconds=3.0, poll_interval_seconds=0.1):
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return
