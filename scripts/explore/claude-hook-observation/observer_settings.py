"""Generate the session-scoped Claude Code observer settings JSON.

Throwaway campaign harness for the 2026-10-19 hook-observation iteration
(see context/campaigns/debug/2026-10-19-claude-hook-observation/). Implements
the observer configuration contract of
context/features/2026-10-18-cli-hook-observation-channel/design/claude-hook-adapter.md
sections 2.3 (handler layout) and 2.5 (HTTP-hook contract).

The v1 event set has 9 events. ``SessionStart`` uses a ``type: command``
handler (HTTP hooks are not supported on ``SessionStart``); the other eight
events use ``type: http`` handlers posting to the loopback collector. The
generated file is secret-free: the bearer token is referenced through the
allowed environment variable ``$HOUMAO_HOOK_TOKEN``, never embedded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HTTP_EVENTS: tuple[str, ...] = (
    "UserPromptSubmit",
    "Stop",
    "StopFailure",
    "PermissionRequest",
    "PreCompact",
    "PostCompact",
    "PostToolUse",
    "PostToolUseFailure",
)
COMMAND_EVENTS: tuple[str, ...] = ("SessionStart",)
HOOK_ROUTE = "/v1/hook"
DEFAULT_TOKEN_ENV = "HOUMAO_HOOK_TOKEN"
DEFAULT_TIMEOUT_SECONDS = 2


def build_observer_settings(
    *,
    port: int,
    emitter: Path,
    token_env: str = DEFAULT_TOKEN_ENV,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Build the observer settings document for one collector port.

    Parameters
    ----------
    port:
        Loopback port the collector is listening on.
    emitter:
        Absolute path to ``emit_hook.py`` (must be executable; the command
        hook runs it through a shell).
    token_env:
        Name of the environment variable the provider process exports the
        bearer token under. Referenced, never embedded.
    timeout_seconds:
        Per-hook timeout in seconds (design 2.4 boundary-event budget).

    Returns
    -------
    dict
        Secret-free settings document suitable for ``claude --settings``.
    """

    url = f"http://127.0.0.1:{port}{HOOK_ROUTE}"
    hooks: dict[str, Any] = {}
    for name in COMMAND_EVENTS:
        hooks[name] = [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": str(emitter),
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
    return {"hooks": hooks}


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: write one observer settings JSON file."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True, help="collector loopback port")
    parser.add_argument(
        "--emitter",
        type=Path,
        required=True,
        help="absolute path to emit_hook.py (invoked for SessionStart)",
    )
    parser.add_argument("--out", type=Path, required=True, help="output settings path")
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV)
    args = parser.parse_args(argv)

    settings = build_observer_settings(
        port=args.port, emitter=args.emitter, token_env=args.token_env
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
