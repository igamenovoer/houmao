#!/usr/bin/env python3
"""Verify or snapshot tmp-write Claude CAO demo reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _sanitize(report: dict[str, Any]) -> dict[str, Any]:
    response_text = str(report.get("response_text", "")).strip()
    if not response_text:
        raise ValueError("report.response_text must be non-empty")

    output_file = str(report.get("output_file", "")).strip()
    if not output_file.endswith("/hello.py"):
        raise ValueError("report.output_file must end with /hello.py")

    sentinel_expected = str(report.get("sentinel_expected", "")).strip()
    sentinel_actual = str(report.get("sentinel_actual", "")).strip()
    if not sentinel_expected:
        raise ValueError("report.sentinel_expected must be non-empty")
    if sentinel_actual != sentinel_expected:
        raise ValueError("report.sentinel_actual must match report.sentinel_expected")
    if report.get("sentinel_match") is not True:
        raise ValueError("report.sentinel_match must be true")

    git_diff_name_only = report.get("git_diff_name_only")
    if not isinstance(git_diff_name_only, list):
        raise ValueError("report.git_diff_name_only must be a list")
    if any(str(entry).strip() for entry in git_diff_name_only):
        raise ValueError("report.git_diff_name_only must be empty")

    terminal_id = str(report.get("terminal_id", "")).strip()
    if not terminal_id:
        raise ValueError("report.terminal_id must be non-empty")
    session_name = str(report.get("session_name", "")).strip()
    if not session_name:
        raise ValueError("report.session_name must be non-empty")

    terminal_log_path = str(report.get("terminal_log_path", "")).strip()
    expected_log = f"~/.aws/cli-agent-orchestrator/logs/terminal/{terminal_id}.log"
    if terminal_log_path != expected_log:
        raise ValueError("report.terminal_log_path is not the expected CAO terminal log path")

    return {
        "status": "ok",
        "backend": str(report.get("backend", "")),
        "tool": str(report.get("tool", "")),
        "response_text": "<NON_EMPTY_RESPONSE>",
        "session_manifest": "<SESSION_MANIFEST_PATH>",
        "workspace": "<WORKSPACE_PATH>",
        "output_file": "<OUTPUT_FILE_PATH>",
        "sentinel_expected": "<SENTINEL>",
        "sentinel_actual": "<SENTINEL>",
        "sentinel_match": True,
        "git_diff_name_only": [],
        "session_name": "<SESSION_NAME>",
        "terminal_id": "<TERMINAL_ID>",
        "terminal_log_path": "~/.aws/cli-agent-orchestrator/logs/terminal/<TERMINAL_ID>.log",
        "generated_at_utc": "<TIMESTAMP>",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify or snapshot Claude CAO tmp-write demo report"
    )
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
            json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"snapshot updated: {args.expected_report}")
        return 0

    expected = json.loads(args.expected_report.read_text(encoding="utf-8"))
    if sanitized != expected:
        print("sanitized report mismatch", file=sys.stderr)
        print(
            "expected:", json.dumps(expected, indent=2, sort_keys=True), file=sys.stderr
        )
        print(
            "actual:", json.dumps(sanitized, indent=2, sort_keys=True), file=sys.stderr
        )
        return 1

    print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
