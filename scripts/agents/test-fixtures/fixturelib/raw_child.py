"""Read private raw-TUI inputs inside tmux, then replace this process with the client."""

from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fixturelib.launch import raw_command, run_environment  # noqa: E402
from fixturelib.prepare import load_run  # noqa: E402


def main() -> None:
    """Keep credentials out of OS argv and scrub inherited provider bindings."""

    run = load_run(Path(sys.argv[1]))
    os.umask(0o077)
    command = raw_command(run)
    env = run_environment(run)
    os.chdir(run["workdir"])
    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    main()
