"""Emit deterministic Codex JSON events without authentication or provider I/O."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import uuid


def _emit(payload: dict[str, object]) -> None:
    """Flush one supported provider event."""

    print(json.dumps(payload), flush=True)


def fixture_control_path(home: str | None) -> Path | None:
    """Read the external qualifier's selected control path from a synthetic home."""

    if home is None:
        return None
    try:
        selected = Path((Path(home) / ".fixture-control-path").read_text(encoding="utf-8").strip())
    except OSError:
        return None
    return selected if selected.is_absolute() else None


def main() -> None:
    """Run a controlled synthetic headless turn or print the fixture version."""

    if "--version" in sys.argv[1:]:
        print("codex-cli 0.167.2")
        return
    configured = os.environ.get("HOUMAO_PLUGIN_FIXTURE_CONTROL")
    control_path = (
        Path(configured)
        if configured is not None
        else fixture_control_path(os.environ.get("CODEX_HOME"))
    )
    if control_path is None or not control_path.is_absolute():
        raise SystemExit("Qualification control was not explicitly selected")
    control = json.loads(control_path.read_text(encoding="utf-8"))
    count_path = Path(control["count_file"])
    count = int(count_path.read_text(encoding="utf-8")) if count_path.exists() else 0
    count_path.write_text(str(count + 1), encoding="utf-8")
    _emit({"type": "thread.started", "thread_id": "fixture-thread-" + uuid.uuid4().hex})
    _emit({"type": "turn.started"})
    time.sleep(float(control.get("turn_seconds", 0.25)))
    _emit(
        {
            "type": "item.completed",
            "item": {"id": "fixture-item", "type": "agent_message", "text": "Fixture complete"},
        }
    )
    _emit(
        {
            "type": "turn.completed",
            "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1},
        }
    )


if __name__ == "__main__":
    main()
