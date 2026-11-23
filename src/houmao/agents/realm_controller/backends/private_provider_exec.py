"""Start a pane process with an explicit owner-private environment."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.runtime_launch_environment import (
    read_runtime_launch_environment,
    write_runtime_launch_environment,
)


def prepare_private_provider_command(
    *,
    session_root: Path,
    environment: dict[str, str],
    command: list[str],
    cao_terminal_only: bool = False,
) -> tuple[list[str], Path]:
    """Prepare a pane invocation with only the private file locator on argv."""

    name = write_runtime_launch_environment(
        session_root, environment=environment, transient_names=frozenset(), mcp_environment={}
    )
    path = session_root / name
    return [
        sys.executable,
        "-I",
        "-m",
        __name__,
        *(["--cao-terminal-only"] if cao_terminal_only else []),
        str(path),
        "--",
        *command,
    ], path


def main() -> int:
    """Read the private input and replace this bootstrap with the provider or CAO shell."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cao-terminal-only", action="store_true")
    parser.add_argument("environment_file", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not command:
        parser.error("a provider command is required")
    try:
        if args.cao_terminal_only and not os.environ.get("CAO_TERMINAL_ID"):
            # Other user-created panes keep their ordinary shell during CAO startup.
            os.execv(command[0], command)
        environment = read_runtime_launch_environment(args.environment_file).environment
        for name in ("TMUX", "TMUX_PANE", "CAO_TERMINAL_ID"):
            if name in os.environ:
                environment[name] = os.environ[name]
        os.execvpe(command[0], command, environment)
    except (OSError, ValueError, SessionManifestError):
        print("Could not start the provider with its private launch environment.", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
