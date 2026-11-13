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


def main() -> None:
    """Run a controlled synthetic headless turn or print the fixture version."""

    if "--version" in sys.argv[1:]:
        print("codex-cli 0.167.2")
        return
    control_path = os.environ.get("HOUMAO_PLUGIN_FIXTURE_CONTROL")
    if not control_path:
        raise SystemExit("Qualification control was not explicitly selected")
    control = json.loads(Path(control_path).read_text(encoding="utf-8"))
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
