#!/usr/bin/env python3
"""Verify/snapshot claude CAO demo reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _sanitize(report: dict[str, Any]) -> dict[str, Any]:
    response = str(report.get("response_text", "")).strip()
    if not response:
        raise ValueError("report.response_text must be non-empty")

    return {
        "status": "ok",
        "backend": str(report.get("backend", "")),
        "tool": str(report.get("tool", "")),
        "response_text": "<NON_EMPTY_RESPONSE>",
        "session_manifest": "<SESSION_MANIFEST_PATH>",
        "workspace": "<WORKSPACE_PATH>",
        "generated_at_utc": "<TIMESTAMP>",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or snapshot claude CAO demo report")
    parser.add_argument("actual_report", type=Path)
    parser.add_argument("expected_report", type=Path)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()

    actual = json.loads(args.actual_report.read_text(encoding="utf-8"))
    sanitized = _sanitize(actual)

    if sanitized.get("backend") != "cao_rest":
        raise ValueError("backend must be cao_rest")
    if sanitized.get("tool") != "claude":
        raise ValueError("tool must be claude")

    if args.snapshot:
        args.expected_report.parent.mkdir(parents=True, exist_ok=True)
        args.expected_report.write_text(
            json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"snapshot updated: {args.expected_report}")
        return 0

    expected = json.loads(args.expected_report.read_text(encoding="utf-8"))
    if sanitized != expected:
        print("sanitized report mismatch", file=sys.stderr)
        print("expected:", json.dumps(expected, indent=2, sort_keys=True), file=sys.stderr)
        print("actual:", json.dumps(sanitized, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
