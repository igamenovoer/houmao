"""Generate and validate the scratch KIMI_CODE_HOME hook configuration (throwaway harness).

Kimi Code reads observer hooks from ``[[hooks]]`` array-of-tables entries in
``$KIMI_CODE_HOME/config.toml``. The schema is strict: every entry may carry
only ``event``, ``matcher``, ``command`` and ``timeout``. One entry with an
extra key voids the *entire* hooks section with a warning diagnostic only, so
this module validates every generated entry by parsing the written file back
with ``tomllib`` before a launch is allowed to proceed.

The observer block writes one entry per Kimi hook event, omits ``matcher``
(match all), uses a 5 second timeout, and invokes ``emit_hook.py`` with the
current Python interpreter. Both command parts are POSIX shell-quoted because
Kimi executes hook commands through the system shell.

``append_raw_toml_block()`` deliberately bypasses validation. It exists for the
campaign's malformed-entry control (S2) and the load-once hot-reload marker
(S1/S7), which must reproduce configurations that the installer-side guard
would refuse.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

EVENT_NAMES: tuple[str, ...] = (
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
ALLOWED_KEYS: frozenset[str] = frozenset({"event", "matcher", "command", "timeout"})
DEFAULT_TIMEOUT_SECONDS = 5
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 600
DEFAULT_EMITTER_NAME = "emit_hook.py"
OBSERVER_BLOCK_BEGIN = "# >>> houmao kimi hook observer >>>"
OBSERVER_BLOCK_END = "# <<< houmao kimi hook observer <<<"


class HookConfigError(ValueError):
    """Raised when a hooks definition would be silently dropped by Kimi."""


@dataclass(frozen=True)
class HookValidationReport:
    """Summary of one strict hooks-section validation."""

    path: Path
    entry_count: int
    events: tuple[str, ...]
    timeouts: tuple[int | None, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable report without configuration contents."""

        return {
            "path": str(self.path),
            "entry_count": self.entry_count,
            "events": list(self.events),
            "timeouts": list(self.timeouts),
        }


def build_command(*, python_executable: str, emitter: Path) -> str:
    """Return the shell command one observer hook executes.

    Parameters
    ----------
    python_executable:
        Interpreter that runs the emitter.
    emitter:
        Absolute path to ``emit_hook.py``.

    Returns
    -------
    str
        A POSIX shell-quoted command string safe for Kimi's system-shell
        execution.
    """

    return f"{shlex.quote(python_executable)} {shlex.quote(str(emitter))}"


def _toml_string(value: str) -> str:
    """Quote one value as a TOML basic string.

    JSON string escaping is a subset of TOML basic-string escaping for the
    characters a shell command can contain (backslash, quote, and control
    characters), so ``json.dumps`` produces a valid TOML literal here.
    """

    return json.dumps(value, ensure_ascii=False)


def render_hook_entry(*, event: str, command: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Render one ``[[hooks]]`` entry with the required fields only.

    ``matcher`` is omitted, which Kimi documents as matching all occurrences.
    """

    return (
        "[[hooks]]\n"
        f"event = {_toml_string(event)}\n"
        f"command = {_toml_string(command)}\n"
        f"timeout = {timeout}\n"
    )


def render_hooks_block(
    *,
    command: str,
    events: Sequence[str] = EVENT_NAMES,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    command_prefix_by_event: Mapping[str, str] | None = None,
) -> str:
    """Render the marker-delimited observer ``[[hooks]]`` block.

    Parameters
    ----------
    command:
        Base shell command (python plus emitter path).
    events:
        Events to subscribe; defaults to all 20 Kimi events.
    timeout:
        Per-entry timeout in seconds.
    command_prefix_by_event:
        Optional shell prefix per event, used by the T1 slow-lifecycle arm
        (for example ``{"SessionStart": "sleep 3; "}``).

    Returns
    -------
    str
        TOML text with one entry per event, wrapped in human-readable markers.
    """

    prefixes = command_prefix_by_event or {}
    lines = [
        OBSERVER_BLOCK_BEGIN,
        "# One entry per Kimi hook event; matcher omitted (match all).",
    ]
    for event_name in events:
        full_command = f"{prefixes.get(event_name, '')}{command}"
        lines.append(render_hook_entry(event=event_name, command=full_command, timeout=timeout))
    lines.append(OBSERVER_BLOCK_END)
    return "\n".join(lines) + "\n"


def validate_hooks_document(
    document: Mapping[str, Any],
    *,
    path: Path = Path("<memory>"),
    require_all_events: bool = False,
    require_timeout: bool = False,
) -> HookValidationReport:
    """Strictly validate the ``hooks`` section of a parsed configuration.

    The checks mirror Kimi's strict schema: only the four documented keys,
    a known event name, a non-empty command, and an integer timeout in
    ``1..600`` when present. Duplicate entries are legal and therefore pass
    validation; Kimi dedupes identical commands at dispatch time.

    Parameters
    ----------
    document:
        Parsed TOML document.
    path:
        Source path recorded in the report.
    require_all_events:
        Require at least one entry for every one of the 20 event names.
    require_timeout:
        Require an explicit timeout on every entry.

    Returns
    -------
    HookValidationReport
        Entry count, event names, and timeouts in declaration order.

    Raises
    ------
    HookConfigError
        On any violation, with the offending entry index and reason.
    """

    raw_hooks = document.get("hooks", [])
    if raw_hooks is None:
        raw_hooks = []
    if not isinstance(raw_hooks, list):
        raise HookConfigError(f"{path}: `hooks` must be an array of tables")

    events: list[str] = []
    timeouts: list[int | None] = []
    for index, entry in enumerate(raw_hooks):
        where = f"{path}: hooks[{index}]"
        if not isinstance(entry, dict):
            raise HookConfigError(f"{where} is not a table")
        extra_keys = sorted(set(entry) - ALLOWED_KEYS)
        if extra_keys:
            raise HookConfigError(
                f"{where} has unsupported key(s) {extra_keys}; Kimi drops the whole "
                "hooks section when any entry carries an unknown key"
            )
        event_name = entry.get("event")
        if not isinstance(event_name, str) or event_name not in EVENT_NAMES:
            raise HookConfigError(f"{where} has unknown event {event_name!r}")
        command = entry.get("command")
        if not isinstance(command, str) or not command.strip():
            raise HookConfigError(f"{where} must carry a non-empty string command")
        matcher = entry.get("matcher")
        if matcher is not None and not isinstance(matcher, str):
            raise HookConfigError(f"{where} matcher must be a string when present")
        timeout = entry.get("timeout")
        if timeout is None:
            if require_timeout:
                raise HookConfigError(f"{where} is missing an explicit timeout")
        else:
            if isinstance(timeout, bool) or not isinstance(timeout, int):
                raise HookConfigError(f"{where} timeout must be an integer")
            if not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
                raise HookConfigError(
                    f"{where} timeout {timeout} is outside "
                    f"{MIN_TIMEOUT_SECONDS}..{MAX_TIMEOUT_SECONDS}"
                )
        events.append(event_name)
        timeouts.append(timeout)

    if require_all_events:
        missing = sorted(set(EVENT_NAMES) - set(events))
        if missing:
            raise HookConfigError(f"{path}: hooks section is missing events {missing}")

    return HookValidationReport(
        path=path,
        entry_count=len(raw_hooks),
        events=tuple(events),
        timeouts=tuple(timeouts),
    )


def validate_hooks_file(
    path: Path,
    *,
    require_all_events: bool = False,
    require_timeout: bool = False,
) -> HookValidationReport:
    """Parse and strictly validate one configuration file's hooks section."""

    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise HookConfigError(f"{path}: cannot parse TOML: {exc}") from exc
    return validate_hooks_document(
        document,
        path=path,
        require_all_events=require_all_events,
        require_timeout=require_timeout,
    )


def merge_observer_hooks(
    config_path: Path,
    *,
    emitter: Path,
    python_executable: str = sys.executable,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    events: Sequence[str] = EVENT_NAMES,
    command_prefix_by_event: Mapping[str, str] | None = None,
) -> HookValidationReport:
    """Append the observer block to a scratch ``config.toml`` and validate it.

    The existing file is parsed before the merge and every other field is
    left byte-identical; only the appended block changes. If read-back
    validation fails, the original bytes are restored and the error is
    re-raised, so a caller can never launch against a silently dead section.

    Parameters
    ----------
    config_path:
        Scratch home's ``config.toml``; must already exist (seeded by copy).
    emitter:
        Absolute path to ``emit_hook.py``.
    python_executable:
        Interpreter used in the hook command.
    timeout:
        Per-entry timeout in seconds.
    events:
        Events to subscribe.
    command_prefix_by_event:
        Optional per-event shell prefix for the T1 slow-lifecycle arm.

    Returns
    -------
    HookValidationReport
        Read-back validation result.
    """

    if not config_path.is_file():
        raise HookConfigError(f"{config_path}: configuration file does not exist")
    if not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
        raise HookConfigError(f"timeout {timeout} is outside 1..600")

    original = config_path.read_bytes()
    try:
        document = tomllib.loads(original.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise HookConfigError(f"{config_path}: cannot parse seeded TOML: {exc}") from exc

    if "hooks" in document:
        raise HookConfigError(
            f"{config_path}: refusing to merge because the seeded config already "
            "declares a hooks key"
        )
    text = original.decode("utf-8")
    if OBSERVER_BLOCK_BEGIN in text:
        raise HookConfigError(f"{config_path}: observer block already appended")
    if text and not text.endswith("\n"):
        text += "\n"
    block = render_hooks_block(
        command=build_command(python_executable=python_executable, emitter=emitter),
        events=events,
        timeout=timeout,
        command_prefix_by_event=command_prefix_by_event,
    )
    merged = text + ("\n" if text else "") + block
    config_path.write_text(merged, encoding="utf-8")
    try:
        return validate_hooks_file(
            config_path,
            require_all_events=set(events) == set(EVENT_NAMES),
            require_timeout=True,
        )
    except HookConfigError:
        config_path.write_bytes(original)
        raise


def append_raw_toml_block(
    config_path: Path,
    block: str,
    *,
    reason: str = "deliberate raw append",
) -> Path:
    """Append a raw TOML block without any schema validation.

    This is the escape hatch for the campaign's deliberate-bypass arms: the
    S2 malformed entry (extra ``cwd`` key) and the S1/S7 hot-reload marker
    hook. The helper only guarantees that the block text is non-empty and
    newline-terminated; it never parses or validates the result.

    Parameters
    ----------
    config_path:
        Scratch home's ``config.toml``.
    block:
        Raw TOML text to append.
    reason:
        One-line human note written as a comment before the block.

    Returns
    -------
    Path
        The configuration path, for call-site convenience.
    """

    if not config_path.is_file():
        raise HookConfigError(f"{config_path}: configuration file does not exist")
    if not block.strip():
        raise HookConfigError("refusing to append an empty TOML block")
    if "\n" in reason:
        reason = reason.replace("\n", " ")
    text = config_path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    text += f"\n# raw append (unvalidated): {reason}\n"
    text += block if block.endswith("\n") else block + "\n"
    config_path.write_text(text, encoding="utf-8")
    return config_path


def sha256_file(path: Path) -> str | None:
    """Return a file's SHA-256 hex digest, or None when it cannot be read."""

    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for manual merge, validation, and raw appends."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="scratch config.toml path")
    parser.add_argument(
        "--emitter",
        type=Path,
        default=Path(__file__).resolve().parent / DEFAULT_EMITTER_NAME,
        help="emit_hook.py path (default: sibling)",
    )
    parser.add_argument("--python", default=sys.executable, help="interpreter for hook commands")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--validate", action="store_true", help="validate an existing file only")
    parser.add_argument(
        "--require-all-events",
        action="store_true",
        help="with --validate: require all 20 events",
    )
    parser.add_argument(
        "--append-raw-block",
        type=Path,
        default=None,
        help="append this file's raw TOML text without validation",
    )
    parser.add_argument("--reason", default="manual raw append")
    args = parser.parse_args(argv)

    try:
        if args.append_raw_block is not None:
            block = args.append_raw_block.read_text(encoding="utf-8")
            append_raw_toml_block(args.config, block, reason=args.reason)
            print(str(args.config))
            return 0
        if args.validate:
            report = validate_hooks_file(args.config, require_all_events=args.require_all_events)
            print(json.dumps(report.to_payload(), indent=2, sort_keys=True))
            return 0
        report = merge_observer_hooks(
            args.config,
            emitter=args.emitter.resolve(),
            python_executable=args.python,
            timeout=args.timeout,
        )
        print(json.dumps(report.to_payload(), indent=2, sort_keys=True))
        return 0
    except HookConfigError as exc:
        print(f"kimi_hooks: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
