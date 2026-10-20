"""Generate the Codex observer hook configuration for hook observation.

The generator produces the two launch-owned artifacts from the same inputs:

- a complete ``hooks.json`` declaration that subscribes all 14 Codex hook
  events with one synchronous command handler each;
- the ``[hooks.state."<key>"]`` TOML block that pre-trusts every generated
  handler in the runtime home's ``config.toml``.

Timeouts are 5 s for every event except ``SessionEnd``, which uses 2 s inside
Codex's 1-3 s clamp (``codex-rs/hooks/src/events/session_end.rs``). Matchers
are deliberately omitted: an absent matcher matches all occurrences, and Codex
drops matcher values on events that do not support them when computing the
trust hash (``codex-rs/hooks/src/events/common.rs``).

The state block is rendered textually because ``hooks.json`` has no TOML
serializer on this path. Keys are emitted as quoted TOML basic strings with
backslash, quote, and control characters escaped.
"""

from __future__ import annotations

import json
import shlex
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from houmao.hook_observation.settings_generator import collector_url
from houmao.hook_observation.trust_hash import (
    hook_hash,
    hook_state_key,
    iter_handlers,
)

CODEX_EVENTS: Final[tuple[str, ...]] = (
    "PreModelRequest",
    "PostModelRequest",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "Interrupt",
)
DEFAULT_TIMEOUT_SECONDS: Final[int] = 5
SESSION_END_TIMEOUT_SECONDS: Final[int] = 2
SESSION_END_EVENT: Final[str] = "SessionEnd"


def build_emitter_command(*, emitter: Path | str, python_executable: str | None = None) -> str:
    """Return the shell command a Codex hook handler executes.

    Codex runs the string through ``<shell> -c``; both parts are POSIX
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


def default_emitter_path() -> Path:
    """Return the packaged command-emitter script path."""

    return Path(__file__).with_name("emitter.py")


def build_collector_emitter_command(
    *,
    port: int,
    store: Path | str,
    generation: int,
    emitter: Path | str | None = None,
    python_executable: str | None = None,
) -> str:
    """Return the fully rendered handler command for collector delivery.

    Every handler in the generated ``hooks.json`` runs this exact string, and
    Codex trust-hashes it verbatim. The collector coordinates therefore travel
    inside the trusted handler command, while the bearer token stays in the
    provider environment.

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


def build_observer_hooks_document(
    *,
    emitter_command: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    session_end_timeout_seconds: int = SESSION_END_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Build the ``hooks.json`` document subscribing all 14 Codex events.

    Parameters
    ----------
    emitter_command:
        Shell command executed for every handler.
    timeout_seconds:
        Timeout for the 13 events outside Codex's SessionEnd clamp.
    session_end_timeout_seconds:
        Timeout for ``SessionEnd``; Codex clamps it to 1-3 s.

    Returns
    -------
    dict
        ``{"hooks": {<Event>: [{"hooks": [<handler>]}]}}`` with no matchers.

    Raises
    ------
    ValueError
        If the command is empty or a timeout is outside its valid range.
    """

    if not emitter_command.strip():
        raise ValueError("emitter command must not be empty")
    if not 1 <= session_end_timeout_seconds <= 3:
        raise ValueError("SessionEnd timeout must stay within Codex's 1-3 s clamp")
    if timeout_seconds < 1:
        raise ValueError("hook timeout must be at least 1 second")

    hooks: dict[str, Any] = {}
    for event_name in CODEX_EVENTS:
        timeout = (
            session_end_timeout_seconds if event_name == SESSION_END_EVENT else timeout_seconds
        )
        hooks[event_name] = [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": emitter_command,
                        "timeout": timeout,
                        "async": False,
                    }
                ]
            }
        ]
    return {"hooks": hooks}


def render_observer_hooks_json(document: Mapping[str, Any]) -> str:
    """Render a ``hooks.json`` document as indented JSON with a trailing newline.

    Parameters
    ----------
    document:
        Document produced by :func:`build_observer_hooks_document`.

    Returns
    -------
    str
        JSON text suitable for writing to the runtime home's ``hooks.json``.
    """

    return json.dumps(document, indent=2) + "\n"


def render_hooks_state_toml(document: Mapping[str, Any], hooks_json_path: Path | str) -> str:
    """Render the pre-trust TOML block for every handler in a hooks document.

    Each handler becomes one ``[hooks.state."<key>"]`` table carrying its
    ``trusted_hash``. The key is the absolute ``hooks.json`` path joined with
    the snake_case event label and the matcher-group and handler indices.

    Parameters
    ----------
    document:
        Document produced by :func:`build_observer_hooks_document` or any
        compatible hooks document.
    hooks_json_path:
        Path of the ``hooks.json`` file the state keys refer to.

    Returns
    -------
    str
        TOML text with one table per handler, separated by blank lines and
        ending with a newline. Empty when the document has no handlers.
    """

    blocks: list[str] = []
    for event_name, group_index, handler_index, matcher, handler in iter_handlers(document):
        key = hook_state_key(hooks_json_path, event_name, group_index, handler_index)
        digest = hook_hash(event_name, matcher, handler)
        blocks.append(f'[hooks.state.{_toml_basic_string(key)}]\ntrusted_hash = "{digest}"')
    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n"


def _toml_basic_string(value: str) -> str:
    """Quote one value as a TOML basic string, including the surrounding quotes."""

    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'
