"""Delegate real tmux, with an explicit finite pre-handoff qualification barrier."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time


def main() -> None:
    """Pause only selected bridge launches; preserve normal tmux behavior."""

    real_tmux = os.environ.get("HOUMAO_PLUGIN_FIXTURE_REAL_TMUX")
    if not real_tmux:
        raise SystemExit("A real tmux executable must be explicitly selected")
    control_path = os.environ.get("HOUMAO_PLUGIN_FIXTURE_CONTROL")
    if (
        control_path
        and "respawn-pane" in sys.argv
        and any(
            "houmao.agents.realm_controller.backends.headless_bridge" in arg for arg in sys.argv
        )
    ):
        control = json.loads(Path(control_path).read_text(encoding="utf-8"))
        if control.get("pause_handoff"):
            paused = Path(control["paused_file"])
            paused.with_suffix(".pid").write_text(str(os.getpid()), encoding="utf-8")
            paused.touch(mode=0o600)
            release = Path(control["release_file"])
            deadline = time.monotonic() + 20
            while not release.exists():
                if time.monotonic() >= deadline:
                    raise SystemExit("Qualification handoff barrier timed out")
                time.sleep(0.02)
    os.execv(real_tmux, [real_tmux, *sys.argv[1:]])


if __name__ == "__main__":
    main()
