#!/usr/bin/env python3
"""Verify or snapshot CAO launcher demo reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from sanitize_report import sanitize_report


def _load_json(path: Path, *, label: str) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    """Run verification or snapshot refresh for launcher reports."""

    parser = argparse.ArgumentParser(description="Verify or snapshot CAO launcher demo reports")
    parser.add_argument("actual_report", type=Path)
    parser.add_argument("expected_report", type=Path)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument(
        "--sanitized-output",
        type=Path,
        default=None,
        help="Optional path to write sanitized actual report",
    )
    args = parser.parse_args()

    try:
        actual = _load_json(args.actual_report, label="actual_report")
        sanitized = sanitize_report(actual)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"verification setup failed: {exc}", file=sys.stderr)
        return 1

    if args.sanitized_output is not None:
        _write_json(args.sanitized_output, sanitized)
        print(f"sanitized report written: {args.sanitized_output}")

    if args.snapshot:
        _write_json(args.expected_report, sanitized)
        print(f"snapshot updated: {args.expected_report}")
        return 0

    try:
        expected = _load_json(args.expected_report, label="expected_report")
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"failed to load expected report: {exc}", file=sys.stderr)
        return 1

    if dict(sanitized) != dict(expected):
        print("sanitized report mismatch", file=sys.stderr)
        print(
            "expected:",
            json.dumps(dict(expected), indent=2, sort_keys=True),
            file=sys.stderr,
        )
        print(
            "actual:",
            json.dumps(dict(sanitized), indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 1

    print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
