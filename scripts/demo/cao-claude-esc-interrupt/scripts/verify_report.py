#!/usr/bin/env python3
"""Verify or snapshot Esc-interrupt Claude CAO demo reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _sanitize(report: dict[str, Any]) -> dict[str, Any]:
    second_response_text = str(report.get("second_response_text", "")).strip()
    if not second_response_text:
        raise ValueError("report.second_response_text must be non-empty")
    second_response_source = str(report.get("second_response_source", "")).strip()
    if not second_response_source:
        raise ValueError("report.second_response_source must be non-empty")

    second_response_chars = int(report.get("second_response_chars", 0))
    if second_response_chars <= 0:
        raise ValueError("report.second_response_chars must be positive")

    processing_observed = report.get("processing_observed")
    idle_after_escape = report.get("idle_after_escape")
    if processing_observed is not True:
        raise ValueError("report.processing_observed must be true")
    if idle_after_escape is not True:
        raise ValueError("report.idle_after_escape must be true")

    terminal_id = str(report.get("terminal_id", "")).strip()
    session_name = str(report.get("session_name", "")).strip()
    window_name = str(report.get("window_name", "")).strip()
    tmux_target = str(report.get("tmux_target", "")).strip()
    if not terminal_id:
        raise ValueError("report.terminal_id must be non-empty")
    if not session_name:
        raise ValueError("report.session_name must be non-empty")
    if not window_name:
        raise ValueError("report.window_name must be non-empty")
    if ":" not in tmux_target:
        raise ValueError("report.tmux_target must include session:window")

    expected_log_path = f"~/.aws/cli-agent-orchestrator/logs/terminal/{terminal_id}.log"
    terminal_log_path = str(report.get("terminal_log_path", "")).strip()
    if terminal_log_path != expected_log_path:
        raise ValueError("report.terminal_log_path is not the expected CAO terminal log path")

    return {
        "status": "ok",
        "backend": str(report.get("backend", "")),
        "tool": str(report.get("tool", "")),
        "session_manifest": "<SESSION_MANIFEST_PATH>",
        "workspace": "<WORKSPACE_PATH>",
        "terminal_id": "<TERMINAL_ID>",
        "session_name": "<SESSION_NAME>",
        "window_name": "<WINDOW_NAME>",
        "tmux_target": "<SESSION_NAME:WINDOW_NAME>",
        "terminal_log_path": "~/.aws/cli-agent-orchestrator/logs/terminal/<TERMINAL_ID>.log",
        "processing_observed": True,
        "idle_after_escape": True,
        "second_response_text": "<NON_EMPTY_RESPONSE>",
        "second_response_source": second_response_source,
        "second_response_chars": "<POSITIVE_INT>",
        "processing_shadow_status": "processing",
        "idle_shadow_status": "idle",
        "second_shadow_status": "completed",
        "shadow_preset_version": "<PRESET_VERSION>",
        "generated_at_utc": "<TIMESTAMP>",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify or snapshot Claude CAO Esc-interrupt demo report"
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
        print("expected:", json.dumps(expected, indent=2, sort_keys=True), file=sys.stderr)
        print("actual:", json.dumps(sanitized, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
