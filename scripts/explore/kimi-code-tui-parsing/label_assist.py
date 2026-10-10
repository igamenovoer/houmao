#!/usr/bin/env python3
"""Blind-labeling assistant: inspect raw frozen snapshots without replay data.

Views over ``pane_snapshots.ndjson`` only (plus ``drive_events.ndjson`` and
``runtime_observations.ndjson`` for timing context). Never touches
``state_observed*`` / ``parser_observed*`` outputs.

Usage:
    pixi run python scripts/explore/kimi-code-tui-parsing/label_assist.py timeline --run-root R [--tail-lines 4] [--stride 1] [--from-elapsed S] [--to-elapsed E]
    pixi run python scripts/explore/kimi-code-tui-parsing/label_assist.py show --run-root R --at-elapsed 42.0
    pixi run python scripts/explore/kimi-code-tui-parsing/label_assist.py ops --run-root R
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


def main() -> int:
    """Run one label-assist view."""

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("timeline", "show", "ops"):
        sub.add_parser(name)
    args, remaining = parser.parse_known_args()

    opts = argparse.Namespace()
    for index in range(0, len(remaining), 2):
        key = remaining[index].lstrip("-").replace("-", "_")
        value = remaining[index + 1] if index + 1 < len(remaining) else "true"
        setattr(opts, key, value)

    run_root = Path(getattr(opts, "run_root")).resolve()
    snapshots = _load_snapshots(run_root)

    if args.command == "ops":
        return _ops(run_root)
    if args.command == "show":
        return _show(snapshots, float(getattr(opts, "at_elapsed", "0")))
    return _timeline(
        snapshots,
        tail_lines=int(getattr(opts, "tail_lines", "4")),
        stride=int(getattr(opts, "stride", "1")),
        from_elapsed=float(getattr(opts, "from_elapsed", "0")),
        to_elapsed=float(getattr(opts, "to_elapsed", "1e18")),
    )


def _load_snapshots(run_root: Path) -> list[dict]:
    """Load frozen pane snapshots."""

    path = run_root / "capture" / "recording" / "pane_snapshots.ndjson"
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _plain(text: str) -> str:
    """Strip ANSI escapes from one raw capture."""

    return _ANSI_RE.sub("", text)


def _ops(run_root: Path) -> int:
    """Print drive operations with elapsed-time bounds."""

    path = run_root / "capture" / "drive_events.ndjson"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["phase"] == "started":
            print(f"{row['elapsed_seconds']:>8.2f}  {row['case_id']:<32} {row['op_name']}")
    return 0


def _show(snapshots: list[dict], at_elapsed: float) -> int:
    """Print the full plain pane for the sample nearest one elapsed time."""

    row = min(snapshots, key=lambda item: abs(item["elapsed_seconds"] - at_elapsed))
    print(f"=== {row['sample_id']} @ {row['elapsed_seconds']:.2f}s ===")
    print(_plain(row["output_text"]))
    return 0


def _timeline(
    snapshots: list[dict], *, tail_lines: int, stride: int, from_elapsed: float, to_elapsed: float
) -> int:
    """Print a compact per-sample live-edge timeline for boundary hunting."""

    for row in snapshots:
        if not (from_elapsed <= row["elapsed_seconds"] <= to_elapsed):
            continue
        index = int(row["sample_id"][1:])
        if index % stride:
            continue
        plain_lines = [ln.strip() for ln in _plain(row["output_text"]).splitlines() if ln.strip()]
        tail = plain_lines[-tail_lines:]
        joined = " ⏎ ".join(ln[:100] for ln in tail)
        print(f"{row['sample_id']} {row['elapsed_seconds']:>8.2f}  {joined[:220]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
