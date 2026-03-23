#!/usr/bin/env python3
"""Write one machine-readable case result payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _optional_existing_path(path_value: str | None) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value).resolve()
    return str(path) if path.exists() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--status", required=True, choices=("passed", "failed"))
    parser.add_argument("--failure-reason", default="")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument("--snapshot-path", action="append", default=[])
    args = parser.parse_args(argv)

    output_root = Path(args.output_root).resolve()
    result_path = Path(args.result_path).resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "case_id": args.case_id,
        "status": args.status,
        "failure_reason": args.failure_reason or None,
        "output_root": str(output_root),
        "artifact_refs": {
            "demo_state_path": _optional_existing_path(
                str(output_root / "control" / "demo_state.json")
            ),
            "inspect_path": _optional_existing_path(str(output_root / "control" / "inspect.json")),
            "report_path": _optional_existing_path(str(output_root / "control" / "report.json")),
            "sanitized_report_path": _optional_existing_path(
                str(output_root / "control" / "report.sanitized.json")
            ),
            "tmux_snapshot_paths": [
                str(Path(path).resolve()) for path in args.snapshot_path if Path(path).exists()
            ],
        },
    }
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
