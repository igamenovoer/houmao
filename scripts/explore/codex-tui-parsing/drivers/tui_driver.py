"""Promptfoo Python provider for TUI scenario cases.

Implements promptfoo's documented custom Python provider contract
(``call_api(prompt, options, context)``; see
``extern/orphan/promptfoo/site/docs/providers/python.md``). The provider
ignores prompt text and drives ``context.vars.ops`` against an already
launched, already recording kimi tmux session named by environment
variables:

- ``HOUMAO_TUI_SESSION``: tmux session name
- ``HOUMAO_TUI_PANE``: pane id
- ``HOUMAO_TUI_RECORD_STARTED``: recorder manifest ``started_at_utc``
- ``HOUMAO_TUI_DRIVE_LOG``: drive events NDJSON path

This makes the session YAMLs executable under promptfoo proper; the campaign
runner (``run_session.py``) drives the same ops through the same library
without promptfoo in the loop.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campaign_lib.drive import TmuxDriver  # noqa: E402


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Drive one case's ops against the live session and return run metadata."""

    del prompt  # behavior is fully data-driven via context.vars.ops
    started = time.monotonic()
    session_name = os.environ.get("HOUMAO_TUI_SESSION")
    pane_id = os.environ.get("HOUMAO_TUI_PANE")
    record_started = os.environ.get("HOUMAO_TUI_RECORD_STARTED")
    drive_log = os.environ.get("HOUMAO_TUI_DRIVE_LOG")
    if not (session_name and pane_id and record_started and drive_log):
        return {
            "output": None,
            "error": "HOUMAO_TUI_SESSION/HOUMAO_TUI_PANE/HOUMAO_TUI_RECORD_STARTED/"
            "HOUMAO_TUI_DRIVE_LOG must be set by the session harness",
        }

    vars_block = (context.get("vars") or {}) if isinstance(context, dict) else {}
    case_id = str(vars_block.get("case_id") or "unnamed-case")
    ops = list(vars_block.get("ops") or [])

    driver = TmuxDriver(
        session_name=session_name,
        pane_id=pane_id,
        drive_log_path=Path(drive_log),
        record_started_at_utc=record_started,
    )
    failures: list[str] = []
    for op in ops:
        try:
            driver.run_op(case_id=case_id, op=op)
        except Exception as exc:  # noqa: BLE001 - reported as case output
            failures.append(repr(exc))

    return {
        "output": {
            "case_id": case_id,
            "ops_executed": len(ops) - len(failures),
            "ops_failed": len(failures),
            "failures": failures,
            "session_name": session_name,
            "pane_id": pane_id,
        },
        "latencyMs": int((time.monotonic() - started) * 1000),
        "metadata": {"provider": "houmao-tui-driver", "mode": "tmux-tracker-blind"},
    }
