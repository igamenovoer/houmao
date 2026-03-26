#!/usr/bin/env python3
"""Verify or snapshot one sanitized passive-server parallel validation report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from houmao.demo.passive_server_parallel_validation_demo_pack.reporting import (
    verify_sanitized_report,
)


def main() -> int:
    """Run the verification CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sanitized_report", type=Path)
    parser.add_argument("expected_report", type=Path)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()

    actual = json.loads(args.sanitized_report.read_text(encoding="utf-8"))
    if args.snapshot:
        args.expected_report.parent.mkdir(parents=True, exist_ok=True)
        args.expected_report.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"snapshot updated: {args.expected_report}")
        return 0

    expected = json.loads(args.expected_report.read_text(encoding="utf-8"))
    try:
        verify_sanitized_report(actual, expected)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

