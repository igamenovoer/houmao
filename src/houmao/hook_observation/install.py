"""Install Claude observer hook configuration into launch-owned surfaces.

The primary injection path marker-merges a Houmao-owned hooks block into the
managed home's ``settings.json`` (the ``CLAUDE_CONFIG_DIR`` user-settings
layer). The merge identifies observer entries with
:func:`houmao.hook_observation.settings_generator.is_observer_hook_entry`,
preserves bundle and operator hook entries, and replaces stale observer entries
so every launch generation rewrites the block in place.

When the home file cannot be safely merged, the installer falls back to a
launch-owned ``--settings <observer-settings.json>`` document under the
session's hook artifact directory. If neither path is safe (for example the
resolved arguments already carry a ``--settings`` source), the installer
reports ``unavailable`` and the session proceeds TUI-only.

The module also owns the small launch-owned artifacts: the per-session
channel generation counter, the ``0600`` provider launch wrapper that carries
the collector token through the provider environment, and install-time
``channel.json`` status updates through the session store.
"""

from __future__ import annotations

import fcntl
import json
import os
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Mapping, Sequence

from houmao.hook_observation.settings_generator import (
    TOKEN_ENV_VAR,
    build_observer_hooks_block,
    is_observer_hook_entry,
)
from houmao.hook_observation.store import (
    CLAUDE_ADAPTER_DIRNAME,
    HOOK_OBSERVATION_DIRNAME,
    HookObservationStore,
)

HOOK_OBSERVATION_CLAUDE_ENV_FLAG: Final[str] = "HOUMAO_HOOK_OBSERVATION_CLAUDE"
HOOK_OBSERVATION_ENABLED_VALUE: Final[str] = "1"
SETTINGS_FILENAME: Final[str] = "settings.json"
OBSERVER_SETTINGS_FILENAME: Final[str] = "observer-settings.json"
GENERATION_FILENAME: Final[str] = "generation.json"
GENERATION_LOCK_FILENAME: Final[str] = "generation.lock"
LAUNCH_WRAPPER_FILENAME: Final[str] = "launch-wrapper.sh"
COLLECTOR_RECORD_FILENAME: Final[str] = "collector.json"
PRIVATE_DIR_MODE: Final[int] = 0o700
PRIVATE_FILE_MODE: Final[int] = 0o600

ObserverInstallPath = Literal["managed_home", "settings_file", "unavailable"]
ChannelInstallState = Literal["installing", "active", "unavailable", "stopped"]


class ObserverSettingsError(RuntimeError):
    """Raised when an observer settings surface cannot be safely written."""


@dataclass(frozen=True)
class ObserverInstallResult:
    """Outcome of one observer configuration installation attempt.

    Parameters
    ----------
    install_path:
        Injection path that was used, or ``unavailable`` when neither path was
        safe.
    generation:
        Channel generation the observer block was written for.
    settings_path:
        Managed home settings file or launch-owned fallback settings file.
    appended_args:
        Launch arguments the caller must append (the fallback ``--settings``
        pair), empty for the managed-home path.
    detail:
        Short, secret-free explanation for logs and ``channel.json``.
    """

    install_path: ObserverInstallPath
    generation: int
    settings_path: Path | None = None
    appended_args: tuple[str, ...] = ()
    detail: str | None = None


def hook_observation_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the Claude hook observation channel is opted in.

    Parameters
    ----------
    env:
        Environment mapping to inspect; defaults to ``os.environ``.

    Returns
    -------
    bool
        ``True`` only when ``HOUMAO_HOOK_OBSERVATION_CLAUDE`` is exactly
        ``"1"``.
    """

    source = os.environ if env is None else env
    return source.get(HOOK_OBSERVATION_CLAUDE_ENV_FLAG) == HOOK_OBSERVATION_ENABLED_VALUE


def hook_observation_applies(*, tool: str, backend: str) -> bool:
    """Return whether the v1 adapter covers one tool/backend pair."""

    return tool == "claude" and backend == "local_interactive"


def claude_hook_artifact_dir(session_root: Path | str) -> Path:
    """Return the Claude hook artifact directory under one session root."""

    return Path(session_root) / HOOK_OBSERVATION_DIRNAME / CLAUDE_ADAPTER_DIRNAME


def merge_observer_hooks_block(
    settings: Mapping[str, Any],
    observer_hooks: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge the observer hooks block into a settings document.

    Existing observer entries for every event in ``observer_hooks`` are
    replaced in place, so a stale block from an earlier generation is repaired
    rather than duplicated. All other entries and top-level keys are preserved.

    Parameters
    ----------
    settings:
        Parsed ``settings.json`` object.
    observer_hooks:
        ``{event_name: [matcher_group, ...]}`` produced by
        :func:`build_observer_hooks_block`.

    Returns
    -------
    dict
        A new settings document carrying the merged hooks block.

    Raises
    ------
    ObserverSettingsError
        If the existing ``hooks`` shape is not a mapping of event names to
        entry lists.
    """

    merged = _deep_copy_mapping(settings)
    hooks_value = merged.get("hooks")
    if hooks_value is None:
        hooks: dict[str, Any] = {}
    elif isinstance(hooks_value, dict):
        hooks = hooks_value
    else:
        raise ObserverSettingsError("managed home `hooks` value is not a JSON object")

    for event_name, observer_entries in observer_hooks.items():
        existing = hooks.get(event_name)
        if existing is None:
            existing_entries: list[Any] = []
        elif isinstance(existing, list):
            existing_entries = existing
        else:
            raise ObserverSettingsError(
                f"managed home `hooks.{event_name}` value is not a JSON list"
            )
        preserved = [entry for entry in existing_entries if not is_observer_hook_entry(entry)]
        hooks[event_name] = [*preserved, *_deep_copy_sequence(observer_entries)]
    merged["hooks"] = hooks
    return merged


def strip_observer_hooks_block(settings: Mapping[str, Any]) -> dict[str, Any]:
    """Remove every observer entry from a settings document.

    Operator and bundle entries are preserved. Event lists left empty are
    dropped, as is an empty ``hooks`` mapping.

    Parameters
    ----------
    settings:
        Parsed ``settings.json`` object.

    Returns
    -------
    dict
        A new settings document without observer entries.

    Raises
    ------
    ObserverSettingsError
        If the existing ``hooks`` shape is not safely inspectable.
    """

    stripped = _deep_copy_mapping(settings)
    hooks_value = stripped.get("hooks")
    if hooks_value is None:
        return stripped
    if not isinstance(hooks_value, dict):
        raise ObserverSettingsError("managed home `hooks` value is not a JSON object")

    hooks: dict[str, Any] = {}
    for event_name, entries in hooks_value.items():
        if not isinstance(entries, list):
            raise ObserverSettingsError(
                f"managed home `hooks.{event_name}` value is not a JSON list"
            )
        preserved = [entry for entry in entries if not is_observer_hook_entry(entry)]
        if preserved:
            hooks[event_name] = preserved
    if hooks:
        stripped["hooks"] = hooks
    else:
        stripped.pop("hooks", None)
    return stripped


def install_observer_configuration(
    *,
    home_path: Path,
    session_root: Path,
    generation: int,
    port: int,
    resolved_args: Sequence[str] = (),
    python_executable: str | None = None,
) -> ObserverInstallResult:
    """Install the observer configuration for one launch generation.

    Parameters
    ----------
    home_path:
        Managed Claude home (``CLAUDE_CONFIG_DIR``).
    session_root:
        Session root that owns the hook artifact directory.
    generation:
        Channel generation to bake into the observer block.
    port:
        Collector port. The launch planner uses ``0`` provisionally; runtime
        activation rewrites the block once the real ephemeral port exists.
    resolved_args:
        Effective launch arguments, used to detect a fallback ``--settings``
        conflict.
    python_executable:
        Interpreter used by the ``SessionStart`` command handler; defaults to
        the current interpreter.

    Returns
    -------
    ObserverInstallResult
        Injection path, settings source, and any arguments the caller must
        append.
    """

    artifact_dir = claude_hook_artifact_dir(session_root)
    observer_hooks = build_observer_hooks_block(
        port=port,
        store=artifact_dir,
        generation=generation,
        python_executable=python_executable,
    )
    try:
        managed_settings_path = _install_managed_home_block(
            home_path=home_path,
            observer_hooks=observer_hooks,
        )
    except (ObserverSettingsError, OSError) as exc:
        detail = f"managed home settings not mergeable: {exc}"
        if _args_contain_settings_source(resolved_args):
            return ObserverInstallResult(
                install_path="unavailable",
                generation=generation,
                detail=f"{detail}; resolved launch args already provide --settings",
            )
        try:
            fallback_path = _write_observer_settings_file(
                artifact_dir=artifact_dir,
                observer_hooks=observer_hooks,
            )
        except (ObserverSettingsError, OSError) as fallback_exc:
            return ObserverInstallResult(
                install_path="unavailable",
                generation=generation,
                detail=f"{detail}; fallback settings write failed: {fallback_exc}",
            )
        return ObserverInstallResult(
            install_path="settings_file",
            generation=generation,
            settings_path=fallback_path,
            appended_args=("--settings", str(fallback_path)),
            detail=detail,
        )

    return ObserverInstallResult(
        install_path="managed_home",
        generation=generation,
        settings_path=managed_settings_path,
        detail=None,
    )


def remove_observer_configuration(*, home_path: Path, session_root: Path) -> None:
    """Best-effort removal of observer entries and the fallback settings file."""

    settings_path = home_path / SETTINGS_FILENAME
    try:
        if settings_path.is_file() and not settings_path.is_symlink():
            payload = _read_json_object(settings_path)
            stripped = strip_observer_hooks_block(payload)
            if stripped != payload:
                _write_json_atomic(
                    settings_path,
                    stripped,
                    mode=_file_mode(settings_path, default=PRIVATE_FILE_MODE),
                )
    except (ObserverSettingsError, OSError, ValueError):
        pass
    try:
        (claude_hook_artifact_dir(session_root) / OBSERVER_SETTINGS_FILENAME).unlink()
    except OSError:
        pass


def write_launch_wrapper(*, session_root: Path, script: str) -> Path:
    """Write the provider launch wrapper with owner-only permissions.

    The wrapper carries the per-session collector token in an ``export`` line,
    so it is written ``0600`` and removed once the provider has started.

    Parameters
    ----------
    session_root:
        Session root that owns the hook artifact directory.
    script:
        Shell script to execute.

    Returns
    -------
    Path
        Written wrapper path.
    """

    artifact_dir = claude_hook_artifact_dir(session_root)
    _ensure_private_dir(artifact_dir)
    wrapper_path = artifact_dir / LAUNCH_WRAPPER_FILENAME
    _write_text_atomic(wrapper_path, script, mode=PRIVATE_FILE_MODE)
    return wrapper_path


def remove_launch_wrapper(path: Path | None) -> None:
    """Remove a provider launch wrapper, tolerating an already-missing file."""

    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return


def read_channel_generation(session_root: Path | str) -> int:
    """Return the persisted channel generation, or ``0`` when unset."""

    path = claude_hook_artifact_dir(session_root) / GENERATION_FILENAME
    try:
        payload = _read_json_object(path)
    except (OSError, ValueError):
        return 0
    value = payload.get("generation")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def allocate_next_generation(session_root: Path | str) -> int:
    """Persist and return the next channel generation for one session.

    The counter file lives under ``<session_root>/hook-observation/claude/``
    and is updated under an exclusive lock so concurrent control-plane
    processes cannot allocate the same generation.

    Parameters
    ----------
    session_root:
        Session root that owns the hook artifact directory.

    Returns
    -------
    int
        Newly allocated generation, strictly greater than the persisted value.
    """

    artifact_dir = claude_hook_artifact_dir(session_root)
    _ensure_private_dir(artifact_dir)
    lock_path = artifact_dir / GENERATION_LOCK_FILENAME
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, PRIVATE_FILE_MODE)
    try:
        os.fchmod(descriptor, PRIVATE_FILE_MODE)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            generation = read_channel_generation(session_root) + 1
            counter_path = artifact_dir / GENERATION_FILENAME
            payload = {
                "schema_version": 1,
                "generation": generation,
                "updated_at_utc": _utc_now_iso(),
            }
            _write_json_atomic(counter_path, payload, mode=PRIVATE_FILE_MODE)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)
    return generation


def write_channel_install_status(
    *,
    session_root: Path,
    generation: int,
    install_path: ObserverInstallPath,
    channel_state: ChannelInstallState,
    detail: str | None,
    settings_path: Path | None = None,
    port: int | None = None,
    collector_pid: int | None = None,
) -> None:
    """Publish install-time channel status through the session store.

    Failures are swallowed: observation instrumentation must never fail the
    managed launch. The status document is secret-free by construction.
    """

    try:
        store = HookObservationStore(session_root, generation=generation)
        if channel_state != "active":
            store.mark_stopped()
        store.write_channel_status(
            extra={
                "channel_state": channel_state,
                "install": {
                    "path": install_path,
                    "generation": generation,
                    "detail": detail,
                    "settings_path": (str(settings_path) if settings_path is not None else None),
                    "port": port,
                    "collector_pid": collector_pid,
                },
            }
        )
    except (OSError, ValueError):
        return


def mark_channel_stopped(*, session_root: Path, generation: int) -> None:
    """Publish a stopped channel state while preserving install metadata."""

    install: dict[str, Any] | None = None
    channel_path = claude_hook_artifact_dir(session_root) / "channel.json"
    try:
        existing = json.loads(channel_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        existing = None
    if isinstance(existing, dict) and isinstance(existing.get("install"), dict):
        install = dict(existing["install"])
    try:
        store = HookObservationStore(session_root, generation=generation)
        store.mark_stopped()
        extra: dict[str, Any] = {"channel_state": "stopped"}
        if install is not None:
            extra["install"] = install
        store.write_channel_status(extra=extra)
    except (OSError, ValueError):
        return


def _install_managed_home_block(
    *,
    home_path: Path,
    observer_hooks: Mapping[str, Any],
) -> Path:
    """Marker-merge the observer block into the managed home settings."""

    settings_path = home_path / SETTINGS_FILENAME
    if settings_path.is_symlink():
        raise ObserverSettingsError(f"`{settings_path}` is a symlink")
    if not settings_path.is_file():
        raise ObserverSettingsError(f"`{settings_path}` is missing")
    if not os.access(settings_path, os.R_OK | os.W_OK):
        raise ObserverSettingsError(f"`{settings_path}` is not readable and writable")
    if not os.access(settings_path.parent, os.W_OK | os.X_OK):
        raise ObserverSettingsError(f"`{settings_path.parent}` is not writable")
    payload = _read_json_object(settings_path)
    merged = merge_observer_hooks_block(payload, observer_hooks)
    if merged != payload:
        _write_json_atomic(
            settings_path,
            merged,
            mode=_file_mode(settings_path, default=PRIVATE_FILE_MODE),
        )
    return settings_path


def _write_observer_settings_file(
    *,
    artifact_dir: Path,
    observer_hooks: Mapping[str, Any],
) -> Path:
    """Write the launch-owned fallback settings document."""

    _ensure_private_dir(artifact_dir)
    settings_path = artifact_dir / OBSERVER_SETTINGS_FILENAME
    _write_json_atomic(settings_path, {"hooks": _deep_copy_mapping(observer_hooks)}, mode=0o600)
    return settings_path


def _args_contain_settings_source(args: Sequence[str]) -> bool:
    """Return whether launch args already carry a settings source."""

    return any(arg == "--settings" or arg.startswith("--settings=") for arg in args)


def _read_json_object(path: Path) -> dict[str, Any]:
    """Read one JSON object or raise an observer settings error."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ObserverSettingsError(f"`{path}` is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ObserverSettingsError(f"`{path}` must contain a top-level JSON object")
    return payload


def _write_json_atomic(path: Path, payload: Mapping[str, Any], *, mode: int) -> None:
    """Write one JSON document with a tmp-then-rename replacement."""

    text = json.dumps(payload, indent=2) + "\n"
    _write_text_atomic(path, text, mode=mode)


def _write_text_atomic(path: Path, text: str, *, mode: int) -> None:
    """Write one text file with a tmp-then-rename replacement."""

    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _ensure_private_dir(path: Path) -> None:
    """Create an owner-only directory when needed."""

    path.mkdir(parents=True, exist_ok=True, mode=PRIVATE_DIR_MODE)
    os.chmod(path, PRIVATE_DIR_MODE)


def _file_mode(path: Path, *, default: int) -> int:
    """Return the permission bits of one existing file."""

    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return default


def _deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-copy a JSON-like mapping."""

    result: dict[str, Any] = {}
    for key, item in value.items():
        result[key] = _deep_copy_value(item)
    return result


def _deep_copy_sequence(value: Sequence[Any]) -> list[Any]:
    """Deep-copy a JSON-like sequence."""

    return [_deep_copy_value(item) for item in value]


def _deep_copy_value(value: Any) -> Any:
    """Deep-copy one JSON-like value."""

    if isinstance(value, dict):
        return _deep_copy_mapping(value)
    if isinstance(value, list):
        return _deep_copy_sequence(value)
    if isinstance(value, tuple):
        return _deep_copy_sequence(value)
    return value


def _utc_now_iso() -> str:
    """Return the current UTC time in ISO-8601 form."""

    return datetime.now(UTC).isoformat(timespec="seconds")


__all__ = [
    "COLLECTOR_RECORD_FILENAME",
    "HOOK_OBSERVATION_CLAUDE_ENV_FLAG",
    "HOOK_OBSERVATION_ENABLED_VALUE",
    "OBSERVER_SETTINGS_FILENAME",
    "ObserverInstallResult",
    "ObserverSettingsError",
    "TOKEN_ENV_VAR",
    "allocate_next_generation",
    "claude_hook_artifact_dir",
    "hook_observation_applies",
    "hook_observation_enabled",
    "install_observer_configuration",
    "mark_channel_stopped",
    "merge_observer_hooks_block",
    "read_channel_generation",
    "remove_launch_wrapper",
    "remove_observer_configuration",
    "strip_observer_hooks_block",
    "write_channel_install_status",
    "write_launch_wrapper",
]
