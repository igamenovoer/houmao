"""Install observer hook configuration into launch-owned provider surfaces.

The Claude injection path marker-merges a Houmao-owned hooks block into the
managed home's ``settings.json`` (the ``CLAUDE_CONFIG_DIR`` user-settings
layer). The merge identifies observer entries with
:func:`houmao.hook_observation.settings_generator.is_observer_hook_entry`,
preserves bundle and operator hook entries, and replaces stale observer entries
so every launch generation rewrites the block in place.

The Codex injection path writes the observer ``hooks.json`` into the managed
``CODEX_HOME`` and marker-appends the matching
``[hooks.state."<hooks.json>:<event>:<group>:<handler>"]`` pre-trust tables
into that home's ``config.toml``. The marker block is rewritten once per
generation and removed on cleanup; every other line of ``config.toml``,
including operator-owned ``[hooks.state]`` entries, is preserved byte-for-byte.

When a Claude home file cannot be safely merged, the installer falls back to a
launch-owned ``--settings <observer-settings.json>`` document under the
session's hook artifact directory. If neither path is safe (for example the
resolved arguments already carry a ``--settings`` source), the installer
reports ``unavailable`` and the session proceeds TUI-only. The Codex installer
has no fallback: any unsafe write reports ``unavailable`` with a detail.

The module also owns the small launch-owned artifacts: per-adapter channel
generation counters, the ``0600`` provider launch wrapper that carries the
collector token through the provider environment, and install-time
``channel.json`` status updates through the session store.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Mapping, Sequence

from houmao.hook_observation.codex_hooks_generator import (
    build_emitter_command,
    build_observer_hooks_document,
    default_emitter_path,
    render_hooks_state_toml,
    render_observer_hooks_json,
)
from houmao.hook_observation.settings_generator import (
    TOKEN_ENV_VAR,
    build_observer_hooks_block,
    is_observer_hook_entry,
)
from houmao.hook_observation.store import (
    ADAPTER_DIRNAMES,
    HOOK_OBSERVATION_DIRNAME,
    HookObservationStore,
)

HOOK_OBSERVATION_CLAUDE_ENV_FLAG: Final[str] = "HOUMAO_HOOK_OBSERVATION_CLAUDE"
HOOK_OBSERVATION_CODEX_ENV_FLAG: Final[str] = "HOUMAO_HOOK_OBSERVATION_CODEX"
HOOK_OBSERVATION_ENABLED_VALUE: Final[str] = "1"
HOOK_OBSERVATION_ENV_FLAGS: Final[Mapping[str, str]] = {
    "claude": HOOK_OBSERVATION_CLAUDE_ENV_FLAG,
    "codex": HOOK_OBSERVATION_CODEX_ENV_FLAG,
}
HOOK_OBSERVATION_PAIRS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("claude", "local_interactive"),
        ("codex", "local_interactive"),
    }
)
SETTINGS_FILENAME: Final[str] = "settings.json"
OBSERVER_SETTINGS_FILENAME: Final[str] = "observer-settings.json"
CODEX_HOOKS_FILENAME: Final[str] = "hooks.json"
CODEX_CONFIG_FILENAME: Final[str] = "config.toml"
CODEX_PRETRUST_BEGIN_MARKER: Final[str] = "# >>> houmao hook observation"
CODEX_PRETRUST_END_MARKER: Final[str] = "# <<< houmao hook observation"
GENERATION_FILENAME: Final[str] = "generation.json"
GENERATION_LOCK_FILENAME: Final[str] = "generation.lock"
LAUNCH_WRAPPER_FILENAME: Final[str] = "launch-wrapper.sh"
COLLECTOR_RECORD_FILENAME: Final[str] = "collector.json"
PRIVATE_DIR_MODE: Final[int] = 0o700
PRIVATE_FILE_MODE: Final[int] = 0o600

_CODEX_PRETRUST_BLOCK_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{re.escape(CODEX_PRETRUST_BEGIN_MARKER)}[^\n]*\n"
    rf".*?^{re.escape(CODEX_PRETRUST_END_MARKER)}[^\n]*\n?",
    re.MULTILINE | re.DOTALL,
)

ObserverInstallPath = Literal["managed_home", "settings_file", "unavailable"]
CodexObserverInstallPath = Literal["managed_home", "unavailable"]
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


@dataclass(frozen=True)
class CodexObserverInstallResult:
    """Outcome of one Codex observer configuration installation attempt.

    Parameters
    ----------
    install_path:
        ``managed_home`` when both the ``hooks.json`` and the pre-trust block
        were written, or ``unavailable`` when any write was unsafe.
    generation:
        Channel generation the block was rendered for.
    hooks_path:
        Written ``hooks.json`` path, or ``None`` when installation failed.
    config_path:
        Runtime-home ``config.toml`` carrying the pre-trust block, or ``None``
        when installation failed.
    detail:
        Short, secret-free explanation for logs and ``channel.json``.
    """

    install_path: CodexObserverInstallPath
    generation: int
    hooks_path: Path | None = None
    config_path: Path | None = None
    detail: str | None = None


def hook_observation_enabled(
    env: Mapping[str, str] | None = None,
    *,
    tool: str = "claude",
) -> bool:
    """Return whether one tool's hook observation channel is opted in.

    Parameters
    ----------
    env:
        Environment mapping to inspect; defaults to ``os.environ``.
    tool:
        Provider tool whose flag to inspect. Unknown tools are never enabled.

    Returns
    -------
    bool
        ``True`` only when the tool's ``HOUMAO_HOOK_OBSERVATION_*`` flag is
        exactly ``"1"``. The Claude flag remains
        ``HOUMAO_HOOK_OBSERVATION_CLAUDE``; the Codex flag is
        ``HOUMAO_HOOK_OBSERVATION_CODEX``.
    """

    flag = HOOK_OBSERVATION_ENV_FLAGS.get(tool)
    if flag is None:
        return False
    source = os.environ if env is None else env
    return source.get(flag) == HOOK_OBSERVATION_ENABLED_VALUE


def hook_observation_applies(*, tool: str, backend: str) -> bool:
    """Return whether the observation channel covers one tool/backend pair."""

    return (tool, backend) in HOOK_OBSERVATION_PAIRS


def hook_artifact_dir(session_root: Path | str, *, tool: str = "claude") -> Path:
    """Return one adapter's hook artifact directory under a session root.

    Parameters
    ----------
    session_root:
        Session root that owns the hook subtree.
    tool:
        Provider tool name; ``claude`` and ``codex`` are supported.

    Returns
    -------
    Path
        ``<session_root>/hook-observation/<adapter>/``.

    Raises
    ------
    ValueError
        If ``tool`` has no adapter directory.
    """

    dirname = ADAPTER_DIRNAMES.get(tool)
    if dirname is None:
        raise ValueError(f"unsupported hook observation tool {tool!r}")
    return Path(session_root) / HOOK_OBSERVATION_DIRNAME / dirname


def claude_hook_artifact_dir(session_root: Path | str) -> Path:
    """Return the Claude hook artifact directory under one session root."""

    return hook_artifact_dir(session_root, tool="claude")


def codex_hook_artifact_dir(session_root: Path | str) -> Path:
    """Return the Codex hook artifact directory under one session root."""

    return hook_artifact_dir(session_root, tool="codex")


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


def render_codex_pretrust_block(
    document: Mapping[str, Any],
    hooks_json_path: Path | str,
    *,
    generation: int,
) -> str:
    """Render the marker-delimited Codex ``[hooks.state]`` pre-trust block.

    Parameters
    ----------
    document:
        Observer ``hooks.json`` document produced by
        :func:`houmao.hook_observation.codex_hooks_generator.build_observer_hooks_document`.
    hooks_json_path:
        Absolute path of the ``hooks.json`` file the state keys refer to.
    generation:
        Channel generation stamped into the marker header. Every launch
        generation rewrites the block in place.

    Returns
    -------
    str
        Marker-delimited TOML text, or an empty string when the document has
        no handlers.
    """

    state_toml = render_hooks_state_toml(document, hooks_json_path)
    if not state_toml:
        return ""
    header = f"{CODEX_PRETRUST_BEGIN_MARKER} (managed; do not edit; generation {generation})"
    return f"{header}\n{state_toml}{CODEX_PRETRUST_END_MARKER}\n"


def merge_codex_pretrust_block(
    config_text: str,
    block: str,
    *,
    hooks_json_path: Path | str | None = None,
) -> str:
    """Replace the Houmao-owned pre-trust block inside one ``config.toml``.

    Existing marker blocks from earlier generations are removed first, so the
    merge is idempotent. When ``hooks_json_path`` is given, markerless
    ``[hooks.state."<hooks.json>:..."]`` tables left behind by a TOML
    re-render are removed as well. Every other line is preserved, including
    operator-authored ``[hooks.state]`` entries.

    Parameters
    ----------
    config_text:
        Current ``config.toml`` text; may be empty.
    block:
        Marker-delimited block from :func:`render_codex_pretrust_block`, or an
        empty string to only strip an existing block.
    hooks_json_path:
        Optional absolute observer ``hooks.json`` path. Its state-table prefix
        identifies Houmao-owned entries that lost their marker comments.

    Returns
    -------
    str
        Merged TOML text.

    Raises
    ------
    ObserverSettingsError
        If the marker block is malformed, or the merged document is not valid
        TOML.
    """

    stripped = strip_codex_pretrust_block(
        config_text,
        hooks_json_path=hooks_json_path,
    )
    if not block:
        return stripped
    normalized = block if block.endswith("\n") else f"{block}\n"
    if (
        _count_marker_lines(normalized, CODEX_PRETRUST_BEGIN_MARKER) != 1
        or _count_marker_lines(normalized, CODEX_PRETRUST_END_MARKER) != 1
    ):
        raise ObserverSettingsError("pre-trust block must carry exactly one marker pair")
    prefix = stripped
    if prefix:
        if not prefix.endswith("\n"):
            prefix = f"{prefix}\n"
        if not prefix.endswith("\n\n"):
            prefix = f"{prefix}\n"
    merged = f"{prefix}{normalized}"
    _parse_codex_config_text(merged)
    return merged


def strip_codex_pretrust_block(
    config_text: str,
    *,
    hooks_json_path: Path | str | None = None,
) -> str:
    """Remove every Houmao-owned pre-trust block from one ``config.toml``.

    Parameters
    ----------
    config_text:
        Current ``config.toml`` text.
    hooks_json_path:
        Optional absolute observer ``hooks.json`` path. When given, markerless
        ``[hooks.state."<hooks.json>:..."]`` tables are removed too, which
        keeps cleanup correct after the launch-policy TOML surface re-renders
        the file without comments.

    Returns
    -------
    str
        Text without Houmao-owned pre-trust tables; content outside those
        tables is unchanged.

    Raises
    ------
    ObserverSettingsError
        If marker lines are unbalanced, which means the file was edited or
        truncated unexpectedly.
    """

    begins = _count_marker_lines(config_text, CODEX_PRETRUST_BEGIN_MARKER)
    ends = _count_marker_lines(config_text, CODEX_PRETRUST_END_MARKER)
    if begins != ends:
        raise ObserverSettingsError(
            "config.toml has an unbalanced Houmao hook-observation marker block"
        )
    stripped = _CODEX_PRETRUST_BLOCK_PATTERN.sub("", config_text) if begins else config_text
    if hooks_json_path is None:
        return stripped
    return _remove_codex_state_tables(stripped, hooks_json_path)


def install_codex_observer_configuration(
    *,
    home_path: Path,
    generation: int,
    emitter: Path | str | None = None,
    emitter_command: str | None = None,
    python_executable: str | None = None,
) -> CodexObserverInstallResult:
    """Install the Codex observer hooks and pre-trust block for one generation.

    The observer ``hooks.json`` is written into the managed runtime home and
    the matching marker-delimited ``[hooks.state]`` block is merged into that
    home's ``config.toml``. Both writes are atomic and owner-only. Any unsafe
    or unwritable surface returns ``unavailable`` instead of raising, and no
    partial artifact is left behind.

    Parameters
    ----------
    home_path:
        Managed Codex home (``CODEX_HOME``).
    generation:
        Channel generation stamped into the pre-trust marker header.
    emitter:
        Emitter script invoked by every handler; defaults to the packaged
        :mod:`houmao.hook_observation.emitter` module file.
    emitter_command:
        Fully rendered handler command, for callers that bake collector
        coordinates into argv. Mutually exclusive with ``emitter``.
    python_executable:
        Interpreter used by the handler command; defaults to the current one.

    Returns
    -------
    CodexObserverInstallResult
        Injection outcome with the written paths, or ``unavailable`` with a
        secret-free detail.
    """

    home = Path(home_path)
    hooks_path = home / CODEX_HOOKS_FILENAME
    config_path = home / CODEX_CONFIG_FILENAME
    try:
        if not home.is_dir():
            raise ObserverSettingsError(f"runtime home `{home}` is missing or not a directory")
        if emitter is not None and emitter_command is not None:
            raise ObserverSettingsError("pass either `emitter` or `emitter_command`, not both")
        hooks_abs = Path(os.path.abspath(os.fspath(hooks_path)))
        command = emitter_command
        if command is None:
            command = build_emitter_command(
                emitter=Path(emitter) if emitter is not None else _default_codex_emitter(),
                python_executable=python_executable,
            )
        document = build_observer_hooks_document(emitter_command=command)
        block = render_codex_pretrust_block(
            document,
            hooks_abs,
            generation=generation,
        )
        _require_safe_text_target(hooks_path, label="hooks.json")
        _require_safe_text_target(config_path, label="config.toml")
        existing_config = _read_optional_text(config_path)
        merged_config = merge_codex_pretrust_block(
            existing_config,
            block,
            hooks_json_path=hooks_abs,
        )
        hooks_text = render_observer_hooks_json(document)

        config_mode = _file_mode(config_path, default=PRIVATE_FILE_MODE)
        config_changed = merged_config != existing_config
        if config_changed:
            _write_text_atomic(config_path, merged_config, mode=config_mode)
        try:
            if _read_optional_text(hooks_path) != hooks_text:
                _write_text_atomic(
                    hooks_path,
                    hooks_text,
                    mode=_file_mode(hooks_path, default=PRIVATE_FILE_MODE),
                )
        except BaseException:
            if config_changed:
                try:
                    _write_text_atomic(config_path, existing_config, mode=config_mode)
                except OSError:
                    pass
            raise
    except (ObserverSettingsError, OSError, ValueError) as exc:
        return CodexObserverInstallResult(
            install_path="unavailable",
            generation=generation,
            detail=str(exc),
        )
    return CodexObserverInstallResult(
        install_path="managed_home",
        generation=generation,
        hooks_path=hooks_path,
        config_path=config_path,
    )


def remove_codex_observer_configuration(*, home_path: Path) -> None:
    """Best-effort removal of the Codex observer artifacts from one home.

    The marker-delimited pre-trust block, any markerless state tables owned by
    the home's ``hooks.json`` path, and the launch-owned ``hooks.json`` are
    removed. Every other ``config.toml`` line, including operator
    ``[hooks.state]`` entries, is preserved.
    """

    home = Path(home_path)
    config_path = home / CODEX_CONFIG_FILENAME
    hooks_path = home / CODEX_HOOKS_FILENAME
    try:
        if config_path.is_file() and not config_path.is_symlink():
            config_text = _read_optional_text(config_path)
            stripped = strip_codex_pretrust_block(
                config_text,
                hooks_json_path=Path(os.path.abspath(os.fspath(hooks_path))),
            )
            if stripped != config_text:
                _write_text_atomic(
                    config_path,
                    stripped,
                    mode=_file_mode(config_path, default=PRIVATE_FILE_MODE),
                )
    except (ObserverSettingsError, OSError, ValueError):
        pass
    try:
        if hooks_path.is_file() and not hooks_path.is_symlink():
            hooks_path.unlink()
    except OSError:
        pass


def write_launch_wrapper(
    *,
    session_root: Path,
    script: str,
    tool: str = "claude",
) -> Path:
    """Write the provider launch wrapper with owner-only permissions.

    The wrapper carries the per-session collector token in an ``export`` line,
    so it is written ``0600`` and removed once the provider has started.

    Parameters
    ----------
    session_root:
        Session root that owns the hook artifact directory.
    script:
        Shell script to execute.
    tool:
        Provider tool whose artifact directory owns the wrapper.

    Returns
    -------
    Path
        Written wrapper path.
    """

    artifact_dir = hook_artifact_dir(session_root, tool=tool)
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


def read_channel_generation(
    session_root: Path | str,
    *,
    tool: str = "claude",
) -> int:
    """Return one adapter's persisted channel generation, or ``0`` when unset."""

    path = hook_artifact_dir(session_root, tool=tool) / GENERATION_FILENAME
    try:
        payload = _read_json_object(path)
    except (OSError, ValueError):
        return 0
    value = payload.get("generation")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def allocate_next_generation(
    session_root: Path | str,
    *,
    tool: str = "claude",
) -> int:
    """Persist and return the next channel generation for one session.

    The counter file lives under
    ``<session_root>/hook-observation/<adapter>/`` and is updated under an
    exclusive lock so concurrent control-plane processes cannot allocate the
    same generation. Each adapter keeps an independent counter.

    Parameters
    ----------
    session_root:
        Session root that owns the hook artifact directory.
    tool:
        Provider tool whose counter to advance.

    Returns
    -------
    int
        Newly allocated generation, strictly greater than the persisted value.
    """

    artifact_dir = hook_artifact_dir(session_root, tool=tool)
    _ensure_private_dir(artifact_dir)
    lock_path = artifact_dir / GENERATION_LOCK_FILENAME
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, PRIVATE_FILE_MODE)
    try:
        os.fchmod(descriptor, PRIVATE_FILE_MODE)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            generation = read_channel_generation(session_root, tool=tool) + 1
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
    tool: str = "claude",
) -> None:
    """Publish install-time channel status through the session store.

    Failures are swallowed: observation instrumentation must never fail the
    managed launch. The status document is secret-free by construction.

    Parameters
    ----------
    session_root:
        Session root that owns the hook subtree.
    generation:
        Channel generation the status belongs to.
    install_path:
        Injection path that was used.
    channel_state:
        Channel state to publish.
    detail:
        Optional secret-free explanation.
    settings_path:
        Provider settings file written by the install, when any.
    port:
        Collector port, when known.
    collector_pid:
        Collector process id, when known.
    tool:
        Provider tool whose adapter directory owns the status file.
    """

    try:
        store = HookObservationStore(session_root, generation=generation, adapter=tool)
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


def mark_channel_stopped(
    *,
    session_root: Path,
    generation: int,
    tool: str = "claude",
) -> None:
    """Publish a stopped channel state while preserving install metadata."""

    install: dict[str, Any] | None = None
    try:
        channel_path = hook_artifact_dir(session_root, tool=tool) / "channel.json"
        existing = json.loads(channel_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        existing = None
    if isinstance(existing, dict) and isinstance(existing.get("install"), dict):
        install = dict(existing["install"])
    try:
        store = HookObservationStore(session_root, generation=generation, adapter=tool)
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


def _default_codex_emitter() -> Path:
    """Return the packaged command emitter script path."""

    return default_emitter_path()


def _count_marker_lines(text: str, marker: str) -> int:
    """Count lines that start with one marker prefix."""

    return sum(1 for line in text.splitlines() if line.startswith(marker))


def _toml_escape(value: str) -> str:
    """Escape one value for a TOML basic string without the surrounding quotes."""

    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _remove_codex_state_tables(text: str, hooks_json_path: Path | str) -> str:
    """Remove markerless state tables owned by one ``hooks.json``.

    A TOML re-render (for example the launch policy's ``toml.set`` surface)
    drops marker comments while keeping the tables. This helper drops every
    ``[hooks.state."<hooks.json>:..."]`` header and its body, leaving all
    other tables and scalars untouched.
    """

    absolute_path = os.path.abspath(os.fspath(hooks_json_path))
    escaped_prefix = _toml_escape(f"{absolute_path}:")
    header_prefix = f'[hooks.state."{escaped_prefix}'
    kept: list[str] = []
    skipping = False
    for line in text.splitlines(keepends=True):
        candidate = line.lstrip()
        if candidate.startswith("["):
            skipping = candidate.startswith(header_prefix)
        if not skipping:
            kept.append(line)
    return "".join(kept)


def _parse_codex_config_text(text: str) -> None:
    """Validate one synthesized Codex config document."""

    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ObserverSettingsError(f"synthesized config.toml is not valid TOML: {exc}") from exc


def _require_safe_text_target(path: Path, *, label: str) -> None:
    """Reject symlinked or non-regular observer write targets."""

    if path.is_symlink():
        raise ObserverSettingsError(f"`{path}` ({label}) is a symlink")
    if path.exists() and not path.is_file():
        raise ObserverSettingsError(f"`{path}` ({label}) is not a regular file")


def _read_optional_text(path: Path) -> str:
    """Read one optional UTF-8 text file, returning an empty string when absent."""

    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ObserverSettingsError(f"`{path}` is not valid UTF-8: {exc}") from exc


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
    "CODEX_CONFIG_FILENAME",
    "CODEX_HOOKS_FILENAME",
    "CODEX_PRETRUST_BEGIN_MARKER",
    "CODEX_PRETRUST_END_MARKER",
    "COLLECTOR_RECORD_FILENAME",
    "CodexObserverInstallResult",
    "HOOK_OBSERVATION_CLAUDE_ENV_FLAG",
    "HOOK_OBSERVATION_CODEX_ENV_FLAG",
    "HOOK_OBSERVATION_ENABLED_VALUE",
    "HOOK_OBSERVATION_ENV_FLAGS",
    "HOOK_OBSERVATION_PAIRS",
    "OBSERVER_SETTINGS_FILENAME",
    "ObserverInstallResult",
    "ObserverSettingsError",
    "TOKEN_ENV_VAR",
    "allocate_next_generation",
    "claude_hook_artifact_dir",
    "codex_hook_artifact_dir",
    "hook_artifact_dir",
    "hook_observation_applies",
    "hook_observation_enabled",
    "install_codex_observer_configuration",
    "install_observer_configuration",
    "mark_channel_stopped",
    "merge_codex_pretrust_block",
    "merge_observer_hooks_block",
    "read_channel_generation",
    "remove_codex_observer_configuration",
    "remove_launch_wrapper",
    "remove_observer_configuration",
    "render_codex_pretrust_block",
    "strip_codex_pretrust_block",
    "strip_observer_hooks_block",
    "write_channel_install_status",
    "write_launch_wrapper",
]
