"""CLI entrypoints for raw launch-helper policy application."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import cast

from houmao.agents.launch_policy.engine import apply_launch_policy
from houmao.agents.launch_policy.models import (
    LaunchPolicyRequest,
    LaunchSurface,
    OperatorPromptMode,
)


def main(argv: list[str] | None = None) -> int:
    """Run the launch-policy helper CLI."""

    parser = argparse.ArgumentParser(description="Apply Houmao launch policy and exec the tool.")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--working-directory", required=True)
    parser.add_argument("--home-path", required=True)
    parser.add_argument("--requested-operator-prompt-mode", default=None)
    parser.add_argument(
        "--launch-arg",
        dest="launch_args",
        action="append",
        default=[],
        help="Base launch arg from the manifest/builder (repeatable).",
    )
    parser.add_argument("passthrough", nargs=argparse.REMAINDER)
    namespace = parser.parse_args(argv)

    passthrough = list(namespace.passthrough)
    if passthrough[:1] == ["--"]:
        passthrough = passthrough[1:]

    backend = _parse_backend(str(namespace.backend))
    requested_operator_prompt_mode = _parse_operator_prompt_mode(
        str(namespace.requested_operator_prompt_mode)
        if namespace.requested_operator_prompt_mode is not None
        else None
    )

    result = apply_launch_policy(
        LaunchPolicyRequest(
            tool=str(namespace.tool),
            backend=backend,
            executable=str(namespace.executable),
            base_args=tuple(str(item) for item in namespace.launch_args),
            requested_operator_prompt_mode=requested_operator_prompt_mode,
            working_directory=Path(str(namespace.working_directory)).resolve(),
            home_path=Path(str(namespace.home_path)).resolve(),
            env=dict(os.environ),
        )
    )
    command = [result.executable, *result.args, *passthrough]
    os.execvpe(result.executable, command, dict(os.environ))
    return 0


def _parse_backend(raw_value: str) -> LaunchSurface:
    """Parse one required launch backend string."""

    value = raw_value.strip()
    if value not in {
        "raw_launch",
        "codex_headless",
        "codex_app_server",
        "claude_headless",
        "gemini_headless",
        "cao_rest",
        "houmao_server_rest",
    }:
        raise SystemExit(f"Unsupported --backend value: {raw_value!r}")
    return cast(LaunchSurface, value)


def _parse_operator_prompt_mode(raw_value: str | None) -> OperatorPromptMode | None:
    """Parse one optional operator prompt mode CLI value."""

    if raw_value is None:
        return None
    value = raw_value.strip()
    if value not in {"as_is", "unattended"}:
        raise SystemExit(
            "--requested-operator-prompt-mode must be `as_is` or `unattended` when set."
        )
    return cast(OperatorPromptMode, value)


if __name__ == "__main__":
    raise SystemExit(main())
