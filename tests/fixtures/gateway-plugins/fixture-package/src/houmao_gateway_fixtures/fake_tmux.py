"""Delegate real tmux, with an explicit finite pre-handoff qualification barrier."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import sys
import time


from houmao_gateway_fixtures.fake_codex import fixture_control_path

_BRIDGE = "houmao.agents.realm_controller.backends.headless_bridge"


def _bridge_control_path(arguments: list[str]) -> Path | None:
    """Resolve a bridge's explicitly selected synthetic Codex home."""

    if "respawn-pane" not in arguments or _BRIDGE not in arguments[-1]:
        return None
    try:
        shell = shlex.split(arguments[-1])
        if len(shell) != 3 or shell[:2] != ["bash", "-lc"]:
            return None
        tokens = shlex.split(shell[2])
        invocation = tokens[tokens.index(_BRIDGE) :]
        env_file = Path(invocation[invocation.index("--env-file") + 1])
        home = json.loads(env_file.read_bytes()).get("CODEX_HOME")
    except (AttributeError, IndexError, OSError, ValueError):
        return None
    if not isinstance(home, str):
        return None
    return fixture_control_path(home)


def main() -> None:
    """Pause only selected bridge launches; preserve normal tmux behavior."""

    real_tmux = os.environ.get("HOUMAO_PLUGIN_FIXTURE_REAL_TMUX")
    if real_tmux is None:
        try:
            real_tmux = Path(sys.argv[0]).with_suffix(".real").read_text(encoding="utf-8").strip()
        except OSError:
            raise SystemExit("A real tmux executable must be explicitly selected") from None
    if not Path(real_tmux).is_absolute():
        raise SystemExit("The selected tmux executable must be an absolute path")
    control_path = _bridge_control_path(sys.argv[1:])
    if control_path is not None:
        control = json.loads(control_path.read_bytes())
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
