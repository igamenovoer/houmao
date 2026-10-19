"""Generate the Claude Code observer hook configuration for hook observation.

The generator produces two shapes from the same inputs:

- a complete standalone settings document (``{"hooks": {...}}``) for the
  launch-owned ``--settings`` fallback path;
- the hooks block alone (``{event: [entry, ...]}``) for marker-merging into a
  managed home's ``settings.json``, which is the primary injection path.

``SessionStart`` uses a command handler because HTTP hooks cannot deliver it;
the other eight v1 events use HTTP handlers posting to the loopback collector.
The bearer token is always referenced through ``$HOUMAO_HOOK_TOKEN`` (and the
provider's ``allowedEnvVars`` mechanism) and never embedded in the output.

The command handler bakes the collector URL, store directory, and channel
generation into its argv because command hooks receive no environment
interpolation for arguments. It invokes the emitter with the current Python
interpreter, so the generated configuration is valid for the interpreter that
generated it.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit

HTTP_EVENTS: Final[tuple[str, ...]] = (
    "UserPromptSubmit",
    "Stop",
    "StopFailure",
    "PermissionRequest",
    "PreCompact",
    "PostCompact",
    "PostToolUse",
    "PostToolUseFailure",
)
COMMAND_EVENTS: Final[tuple[str, ...]] = ("SessionStart",)
OBSERVER_EVENTS: Final[tuple[str, ...]] = COMMAND_EVENTS + HTTP_EVENTS
HOOK_ROUTE: Final = "/v1/hook"
TOKEN_ENV_VAR: Final = "HOUMAO_HOOK_TOKEN"
DEFAULT_TIMEOUT_SECONDS: Final = 2
EMITTER_MODULE: Final = "houmao.hook_observation.emitter"


def collector_url(port: int) -> str:
    """Return the loopback collector hook endpoint for one port."""

    return f"http://127.0.0.1:{port}{HOOK_ROUTE}"


def emitter_command(
    *,
    port: int,
    store: Path,
    generation: int,
    python_executable: str | None = None,
) -> str:
    """Return the shell command that runs the emitter for ``SessionStart``."""

    argv = [
        python_executable or sys.executable,
        "-m",
        EMITTER_MODULE,
        "--collector-url",
        collector_url(port),
        "--store",
        str(store),
        "--generation",
        str(generation),
    ]
    return shlex.join(argv)


def build_observer_hooks_block(
    *,
    port: int,
    store: Path,
    generation: int,
    token_env: str = TOKEN_ENV_VAR,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    python_executable: str | None = None,
) -> dict[str, Any]:
    """Build the hooks block for one collector port and channel generation.

    Parameters
    ----------
    port:
        Loopback port the collector is listening on.
    store:
        Hook artifact directory; baked into the command handler argv.
    generation:
        Channel generation; baked into the command handler argv.
    token_env:
        Environment variable the provider exports the bearer token under.
        Referenced, never embedded.
    timeout_seconds:
        Per-hook timeout in seconds.
    python_executable:
        Interpreter used for the command handler; defaults to the current one.

    Returns
    -------
    dict
        ``{event_name: [matcher_group, ...]}`` suitable for merging into a
        ``settings.json`` ``hooks`` key.
    """

    url = collector_url(port)
    command = emitter_command(
        port=port,
        store=store,
        generation=generation,
        python_executable=python_executable,
    )
    hooks: dict[str, Any] = {}
    for name in COMMAND_EVENTS:
        hooks[name] = [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": timeout_seconds,
                    }
                ]
            }
        ]
    for name in HTTP_EVENTS:
        hooks[name] = [
            {
                "hooks": [
                    {
                        "type": "http",
                        "url": url,
                        "timeout": timeout_seconds,
                        "headers": {"Authorization": f"Bearer ${token_env}"},
                        "allowedEnvVars": [token_env],
                    }
                ]
            }
        ]
    return hooks


def build_observer_settings(
    *,
    port: int,
    store: Path,
    generation: int,
    token_env: str = TOKEN_ENV_VAR,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    python_executable: str | None = None,
) -> dict[str, Any]:
    """Build a complete standalone observer settings document.

    The document is secret-free and suitable for ``claude --settings``.
    """

    return {
        "hooks": build_observer_hooks_block(
            port=port,
            store=store,
            generation=generation,
            token_env=token_env,
            timeout_seconds=timeout_seconds,
            python_executable=python_executable,
        )
    }


def _entry_handlers(entry: object) -> list[object]:
    """Return the hook handlers of a matcher group or a bare handler."""

    if not isinstance(entry, dict):
        return []
    handlers = entry.get("hooks")
    if isinstance(handlers, list):
        return list(handlers)
    if "type" in entry:
        return [entry]
    return []


def is_observer_hook_entry(entry: object) -> bool:
    """Return whether a hooks-list entry belongs to the Houmao observer.

    This is the marker contract for phase-2 settings merging: an entry is
    Houmao-owned when any handler posts to the observer route path
    ``/v1/hook`` or invokes the ``houmao.hook_observation.emitter`` module.
    Merge code uses this predicate to remove or replace stale observer entries
    while preserving operator, bundle, and plugin hook entries.

    Parameters
    ----------
    entry:
        One entry from a settings ``hooks.<event>`` list, or a bare hook
        handler. Malformed values are treated as non-observer entries.

    Returns
    -------
    bool
        ``True`` when the entry carries an observer marker.
    """

    for handler in _entry_handlers(entry):
        if not isinstance(handler, dict):
            continue
        url = handler.get("url")
        if isinstance(url, str) and urlsplit(url).path == HOOK_ROUTE:
            return True
        command = handler.get("command")
        if isinstance(command, str) and EMITTER_MODULE in command:
            return True
    return False
