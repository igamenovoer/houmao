"""Generate and validate the Kimi hook observer configuration.

Kimi Code reads observer hooks from ``[[hooks]]`` array-of-tables entries in
``$KIMI_CODE_HOME/config.toml``. The provider schema is strict: every entry may
carry only ``event``, ``matcher``, ``command`` and ``timeout``. One entry with
an extra key voids the entire hooks section with a warning diagnostic only, so
this module validates generated configuration by parsing it back with
``tomllib`` and refuses to return a document the provider would silently drop.

The observer block subscribes all 20 Kimi events with one entry each, omits
``matcher`` (match all), uses a 5 second timeout, and invokes the packaged
emitter script with the current interpreter. Both command parts are POSIX
shell-quoted because Kimi executes hook commands through the system shell. The
block is marker-delimited so it can be rewritten idempotently per launch
generation and removed on teardown while every byte outside the block stays
untouched.

Kimi has no hook trust mechanism, so there is no pre-trust artifact analogous
to ``codex_hooks_generator``; the read-back guard below is the injection-time
tripwire instead.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from houmao.hook_observation.settings_generator import collector_url

KIMI_EVENTS: Final[tuple[str, ...]] = (
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionRequest",
    "PermissionResult",
    "UserPromptSubmit",
    "UserPromptQueued",
    "TurnStarted",
    "Stop",
    "StopFailure",
    "Interrupt",
    "SessionStart",
    "SessionEnd",
    "SessionHeartbeat",
    "SubagentStart",
    "SubagentStop",
    "TaskStarted",
    "PreCompact",
    "PostCompact",
    "Notification",
)
ALLOWED_HOOK_KEYS: Final[frozenset[str]] = frozenset({"event", "matcher", "command", "timeout"})
DEFAULT_TIMEOUT_SECONDS: Final[int] = 5
MIN_TIMEOUT_SECONDS: Final[int] = 1
MAX_TIMEOUT_SECONDS: Final[int] = 600
OBSERVER_BLOCK_BEGIN_MARKER: Final[str] = "# >>> houmao kimi hook observation"
OBSERVER_BLOCK_END_MARKER: Final[str] = "# <<< houmao kimi hook observation"

_OBSERVER_BLOCK_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"\n?^{re.escape(OBSERVER_BLOCK_BEGIN_MARKER)}[^\n]*\n"
    rf".*?^{re.escape(OBSERVER_BLOCK_END_MARKER)}[^\n]*\n?",
    re.MULTILINE | re.DOTALL,
)


class KimiHookConfigError(RuntimeError):
    """Raised when a Kimi hooks surface would be silently voided by the provider."""


@dataclass(frozen=True)
class KimiHookValidationReport:
    """Summary of one strict read-back validation.

    Parameters
    ----------
    path:
        Source path recorded for diagnostics; ``<memory>`` for text input.
    entry_count:
        Number of ``[[hooks]]`` entries in the validated document.
    events:
        Event names in declaration order.
    timeouts:
        Timeouts in declaration order; ``None`` when an entry omits one and
        timeout enforcement was disabled.
    """

    path: Path
    entry_count: int
    events: tuple[str, ...]
    timeouts: tuple[int | None, ...]


def default_emitter_path() -> Path:
    """Return the packaged command-emitter script path."""

    return Path(__file__).with_name("emitter.py")


def build_emitter_command(*, emitter: Path | str, python_executable: str | None = None) -> str:
    """Return the shell command a Kimi hook handler executes.

    Kimi runs the string through the system shell; both parts are POSIX
    shell-quoted so paths containing spaces or metacharacters stay intact.

    Parameters
    ----------
    emitter:
        Path of the emitter script to invoke.
    python_executable:
        Interpreter used to run the emitter; defaults to the current one.

    Returns
    -------
    str
        Shell-quoted command line.
    """

    return shlex.join([python_executable or sys.executable, str(emitter)])


def build_collector_emitter_command(
    *,
    port: int,
    store: Path | str,
    generation: int,
    emitter: Path | str | None = None,
    python_executable: str | None = None,
) -> str:
    """Return the fully rendered handler command for collector delivery.

    The collector URL, artifact directory, and channel generation are baked
    into the hook command because the provider performs no environment
    interpolation for command arguments. The bearer token stays in the
    provider environment (``HOUMAO_HOOK_TOKEN``), never in the command.

    Parameters
    ----------
    port:
        Loopback collector port baked into the command.
    store:
        Hook artifact directory used for the file fallback.
    generation:
        Channel generation stamped onto accepted and fallback events.
    emitter:
        Emitter script invoked by the command; defaults to the packaged
        :mod:`houmao.hook_observation.emitter` file.
    python_executable:
        Interpreter used to run the emitter; defaults to the current one.

    Returns
    -------
    str
        Shell-quoted command line.
    """

    return shlex.join(
        [
            python_executable or sys.executable,
            str(emitter if emitter is not None else default_emitter_path()),
            "--collector-url",
            collector_url(port),
            "--store",
            str(store),
            "--generation",
            str(generation),
        ]
    )


def render_hook_entry(*, event: str, command: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Render one ``[[hooks]]`` entry with the provider's fields only.

    ``matcher`` is omitted deliberately: an absent matcher matches all
    occurrences, which is the observer's intent for every event.

    Parameters
    ----------
    event:
        One of :data:`KIMI_EVENTS`.
    command:
        Shell command executed by the provider.
    timeout:
        Per-hook timeout in seconds, within ``1..600``.

    Returns
    -------
    str
        TOML text for one array-of-tables entry, ending with a newline.

    Raises
    ------
    KimiHookConfigError
        If the event is unknown, the command is blank, or the timeout is
        outside the provider's accepted range.
    """

    if event not in KIMI_EVENTS:
        raise KimiHookConfigError(f"unknown Kimi hook event {event!r}")
    if not command.strip():
        raise KimiHookConfigError(f"hook command for {event!r} must not be empty")
    _require_timeout(timeout, where=f"hook event {event!r}")
    return (
        "[[hooks]]\n"
        f"event = {_toml_string(event)}\n"
        f"command = {_toml_string(command)}\n"
        f"timeout = {timeout}\n"
    )


def render_observer_block(
    *,
    emitter_command: str,
    generation: int,
    events: Sequence[str] = KIMI_EVENTS,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Render the marker-delimited observer ``[[hooks]]`` block.

    The block carries one entry per subscribed event and a generation-stamped
    header so a later launch can identify and replace it in place.

    Parameters
    ----------
    emitter_command:
        Shell command every entry executes.
    generation:
        Channel generation stamped into the marker header; must be positive.
    events:
        Events to subscribe; defaults to all 20 Kimi events.
    timeout:
        Per-entry timeout in seconds.

    Returns
    -------
    str
        Marker-delimited TOML text, beginning with the begin marker and ending
        with the end marker plus a newline.

    Raises
    ------
    KimiHookConfigError
        If the command is blank, the generation is not positive, the event list
        is empty or contains duplicates or unknown names, or the timeout is
        outside the provider's accepted range.
    """

    if not emitter_command.strip():
        raise KimiHookConfigError("emitter command must not be empty")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise KimiHookConfigError("channel generation must be a positive integer")
    _require_timeout(timeout, where="observer block")
    selected = tuple(events)
    if not selected:
        raise KimiHookConfigError("observer block must subscribe at least one event")
    if len(set(selected)) != len(selected):
        raise KimiHookConfigError("observer block must not repeat an event")
    unknown = sorted(set(selected) - set(KIMI_EVENTS))
    if unknown:
        raise KimiHookConfigError(f"unknown Kimi hook event(s) {unknown}")

    entries = "\n".join(
        render_hook_entry(event=event, command=emitter_command, timeout=timeout)
        for event in selected
    )
    header = f"{OBSERVER_BLOCK_BEGIN_MARKER} (managed; do not edit; generation {generation})"
    return (
        f"{header}\n"
        "# One entry per Kimi hook event; matcher omitted (match all).\n"
        f"{entries}{OBSERVER_BLOCK_END_MARKER}\n"
    )


def merge_observer_block(
    config_text: str,
    block: str,
    *,
    path: Path = Path("<memory>"),
    require_all_events: bool = True,
) -> str:
    """Replace the Houmao-owned observer block inside one ``config.toml``.

    An existing marker block from an earlier generation is removed first, so
    the merge is idempotent. The new block is appended after every other byte
    of the document, which is valid TOML because ``[[hooks]]`` headers always
    open a root-level array-of-tables entry. The merged document is parsed
    back with ``tomllib`` and validated strictly before it is returned.

    The block owns exactly one separator newline before its begin marker;
    :func:`strip_observer_block` removes that newline together with the block,
    so a merge-then-strip round trip restores the original bytes.

    Parameters
    ----------
    config_text:
        Current ``config.toml`` text; may be empty.
    block:
        Marker-delimited block from :func:`render_observer_block`.
    path:
        Source path recorded in validation errors; defaults to ``<memory>``.
    require_all_events:
        Require at least one entry for every one of the 20 event names.

    Returns
    -------
    str
        Merged and validated TOML text.

    Raises
    ------
    KimiHookConfigError
        If the block is not exactly one marker pair, the existing document is
        not valid TOML, or the merged document violates the provider schema.
    """

    normalized = block if block.endswith("\n") else f"{block}\n"
    if not normalized.strip():
        raise KimiHookConfigError("observer block must not be empty")
    if (
        _count_marker_lines(normalized, OBSERVER_BLOCK_BEGIN_MARKER) != 1
        or _count_marker_lines(normalized, OBSERVER_BLOCK_END_MARKER) != 1
    ):
        raise KimiHookConfigError("observer block must carry exactly one marker pair")

    stripped = strip_observer_block(config_text)
    merged = f"{stripped}\n{normalized}" if stripped else normalized
    validate_hooks_text(
        merged,
        path=path,
        require_all_events=require_all_events,
        require_timeout=True,
    )
    return merged


def strip_observer_block(config_text: str) -> str:
    """Remove every Houmao observer block from one ``config.toml`` text.

    The block owns the separator newline immediately before its begin marker;
    removing both restores the pre-merge bytes exactly. Content outside the
    block, including operator-authored ``[[hooks]]`` entries, is untouched.

    Parameters
    ----------
    config_text:
        Current ``config.toml`` text.

    Returns
    -------
    str
        Text without the Houmao-owned observer block.

    Raises
    ------
    KimiHookConfigError
        If the begin and end markers are unbalanced, which means the file was
        edited or truncated unexpectedly.
    """

    begins = _count_marker_lines(config_text, OBSERVER_BLOCK_BEGIN_MARKER)
    ends = _count_marker_lines(config_text, OBSERVER_BLOCK_END_MARKER)
    if begins != ends:
        raise KimiHookConfigError(
            "config.toml has an unbalanced Houmao Kimi hook-observation marker block"
        )
    if not begins:
        return config_text
    return _OBSERVER_BLOCK_PATTERN.sub("", config_text)


def validate_hooks_document(
    document: Mapping[str, Any],
    *,
    path: Path = Path("<memory>"),
    require_all_events: bool = True,
    require_timeout: bool = True,
) -> KimiHookValidationReport:
    """Strictly validate the ``hooks`` section of a parsed configuration.

    The checks mirror the provider's schema: only the four documented keys, a
    known event name, a non-empty command string, and an integer timeout in
    ``1..600``. Duplicate entries are legal because operator hooks outside the
    observer block may subscribe an event the observer also subscribes.

    Parameters
    ----------
    document:
        Parsed TOML document.
    path:
        Source path recorded in the report and error messages.
    require_all_events:
        Require at least one entry for every one of the 20 event names.
    require_timeout:
        Require an explicit timeout on every entry.

    Returns
    -------
    KimiHookValidationReport
        Entry count, event names, and timeouts in declaration order.

    Raises
    ------
    KimiHookConfigError
        On any violation, naming the offending entry index and reason.
    """

    raw_hooks = document.get("hooks", [])
    if raw_hooks is None:
        raw_hooks = []
    if not isinstance(raw_hooks, list):
        raise KimiHookConfigError(f"{path}: `hooks` must be an array of tables")

    events: list[str] = []
    timeouts: list[int | None] = []
    for index, entry in enumerate(raw_hooks):
        where = f"{path}: hooks[{index}]"
        if not isinstance(entry, dict):
            raise KimiHookConfigError(f"{where} is not a table")
        extra_keys = sorted(set(entry) - ALLOWED_HOOK_KEYS)
        if extra_keys:
            raise KimiHookConfigError(
                f"{where} has unsupported key(s) {extra_keys}; Kimi drops the whole "
                "hooks section when any entry carries an unknown key"
            )
        event_name = entry.get("event")
        if not isinstance(event_name, str) or event_name not in KIMI_EVENTS:
            raise KimiHookConfigError(f"{where} has unknown event {event_name!r}")
        command = entry.get("command")
        if not isinstance(command, str) or not command.strip():
            raise KimiHookConfigError(f"{where} must carry a non-empty string command")
        matcher = entry.get("matcher")
        if matcher is not None and not isinstance(matcher, str):
            raise KimiHookConfigError(f"{where} matcher must be a string when present")
        timeout = entry.get("timeout")
        if timeout is None:
            if require_timeout:
                raise KimiHookConfigError(f"{where} is missing an explicit timeout")
        else:
            _require_timeout(timeout, where=where)
        events.append(event_name)
        timeouts.append(None if timeout is None else timeout)

    if require_all_events:
        missing = sorted(set(KIMI_EVENTS) - set(events))
        if missing:
            raise KimiHookConfigError(f"{path}: hooks section is missing events {missing}")

    return KimiHookValidationReport(
        path=path,
        entry_count=len(raw_hooks),
        events=tuple(events),
        timeouts=tuple(timeouts),
    )


def validate_hooks_text(
    text: str,
    *,
    path: Path = Path("<memory>"),
    require_all_events: bool = True,
    require_timeout: bool = True,
) -> KimiHookValidationReport:
    """Parse and strictly validate one configuration text's hooks section.

    Parameters
    ----------
    text:
        TOML configuration text.
    path:
        Source path recorded in the report and error messages.
    require_all_events:
        Require at least one entry for every one of the 20 event names.
    require_timeout:
        Require an explicit timeout on every entry.

    Returns
    -------
    KimiHookValidationReport
        Validation summary.

    Raises
    ------
    KimiHookConfigError
        If the text is not valid TOML or the hooks section violates the
        provider schema.
    """

    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise KimiHookConfigError(f"{path}: cannot parse TOML: {exc}") from exc
    return validate_hooks_document(
        document,
        path=path,
        require_all_events=require_all_events,
        require_timeout=require_timeout,
    )


def validate_hooks_file(
    path: Path,
    *,
    require_all_events: bool = True,
    require_timeout: bool = True,
) -> KimiHookValidationReport:
    """Parse and strictly validate one configuration file's hooks section.

    Parameters
    ----------
    path:
        ``config.toml`` path to read back.
    require_all_events:
        Require at least one entry for every one of the 20 event names.
    require_timeout:
        Require an explicit timeout on every entry.

    Returns
    -------
    KimiHookValidationReport
        Validation summary.

    Raises
    ------
    KimiHookConfigError
        If the file cannot be read, is not valid TOML, or the hooks section
        violates the provider schema.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise KimiHookConfigError(f"{path}: cannot read configuration: {exc}") from exc
    return validate_hooks_text(
        text,
        path=path,
        require_all_events=require_all_events,
        require_timeout=require_timeout,
    )


def _toml_string(value: str) -> str:
    """Quote one value as a TOML basic string.

    JSON string escaping is a subset of TOML basic-string escaping for the
    characters a shell command can contain (backslash, quote, and control
    characters), so ``json.dumps`` produces a valid TOML literal here.
    """

    return json.dumps(value, ensure_ascii=False)


def _require_timeout(timeout: object, *, where: str) -> None:
    """Validate one timeout against the provider's integer ``1..600`` range."""

    if isinstance(timeout, bool) or not isinstance(timeout, int):
        raise KimiHookConfigError(f"{where} timeout must be an integer")
    if not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
        raise KimiHookConfigError(
            f"{where} timeout {timeout} is outside {MIN_TIMEOUT_SECONDS}..{MAX_TIMEOUT_SECONDS}"
        )


def _count_marker_lines(text: str, marker: str) -> int:
    """Count lines that start with one marker prefix."""

    return sum(1 for line in text.splitlines() if line.startswith(marker))
