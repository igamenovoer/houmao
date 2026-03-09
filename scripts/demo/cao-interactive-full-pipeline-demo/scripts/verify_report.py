#!/usr/bin/env python3
"""Verify or snapshot interactive CAO full-pipeline demo reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from gig_agents.demo.cao_interactive_full_pipeline_demo import FIXED_CAO_BASE_URL

_TERMINAL_LOG_SUFFIX = Path(".aws") / "cli-agent-orchestrator" / "logs" / "terminal"


def _sanitize_turn(turn: dict[str, Any], *, expected_index: int) -> dict[str, Any]:
    turn_index = int(turn.get("turn_index", 0))
    if turn_index != expected_index:
        raise ValueError(
            f"verified turn index mismatch: expected {expected_index}, got {turn_index}"
        )

    agent_identity = str(turn.get("agent_identity", "")).strip()
    if not agent_identity:
        raise ValueError("verified turn.agent_identity must be non-empty")

    if int(turn.get("exit_status", -1)) != 0:
        raise ValueError("verified turn.exit_status must be 0")

    response_text = str(turn.get("response_text", "")).strip()
    if not response_text:
        raise ValueError("verified turn.response_text must be non-empty")

    return {
        "turn_index": expected_index,
        "agent_identity": "<AGENT_IDENTITY>",
        "exit_status": 0,
        "response_text": "<NON_EMPTY_RESPONSE>",
    }


def _sanitize(report: dict[str, Any]) -> dict[str, Any]:
    status = str(report.get("status", "")).strip()
    if status != "ok":
        raise ValueError("report.status must be ok")

    backend = str(report.get("backend", "")).strip()
    if backend != "cao_rest":
        raise ValueError("report.backend must be cao_rest")

    tool = str(report.get("tool", "")).strip()
    if tool != "claude":
        raise ValueError("report.tool must be claude")

    cao_base_url = str(report.get("cao_base_url", "")).strip()
    if cao_base_url != FIXED_CAO_BASE_URL:
        raise ValueError("report.cao_base_url must be the fixed loopback target")

    agent_identity = str(report.get("agent_identity", "")).strip()
    if not agent_identity:
        raise ValueError("report.agent_identity must be non-empty")

    if int(report.get("unique_agent_identity_count", 0)) != 1:
        raise ValueError("report.unique_agent_identity_count must be 1")

    turns = report.get("turns")
    if not isinstance(turns, list):
        raise ValueError("report.turns must be a list")
    if len(turns) < 2:
        raise ValueError("report.turns must contain at least two entries")

    normalized_turns: list[dict[str, Any]] = []
    seen_identities: set[str] = set()
    for raw_turn in turns:
        if not isinstance(raw_turn, dict):
            raise ValueError("report.turns entries must be JSON objects")
        current_identity = str(raw_turn.get("agent_identity", "")).strip()
        if not current_identity:
            raise ValueError("report.turns entry agent_identity must be non-empty")
        seen_identities.add(current_identity)
        if int(raw_turn.get("exit_status", -1)) != 0:
            raise ValueError("report.turns entry exit_status must be 0")
        if not str(raw_turn.get("response_text", "")).strip():
            raise ValueError("report.turns entry response_text must be non-empty")
        normalized_turns.append(raw_turn)

    if seen_identities != {agent_identity}:
        raise ValueError("all recorded turns must reuse the report.agent_identity value")

    normalized_turns.sort(key=lambda item: int(item.get("turn_index", 0)))
    verified_turns = [
        _sanitize_turn(normalized_turns[0], expected_index=1),
        _sanitize_turn(normalized_turns[1], expected_index=2),
    ]

    session_manifest = str(report.get("session_manifest", "")).strip()
    if not session_manifest:
        raise ValueError("report.session_manifest must be non-empty")

    workspace_dir = str(report.get("workspace_dir", "")).strip()
    if not workspace_dir:
        raise ValueError("report.workspace_dir must be non-empty")

    tmux_target = str(report.get("tmux_target", "")).strip()
    if not tmux_target:
        raise ValueError("report.tmux_target must be non-empty")

    terminal_id = str(report.get("terminal_id", "")).strip()
    if not terminal_id:
        raise ValueError("report.terminal_id must be non-empty")

    terminal_log_path_raw = str(report.get("terminal_log_path", "")).strip()
    if not terminal_log_path_raw:
        raise ValueError("report.terminal_log_path must be non-empty")
    if terminal_log_path_raw.startswith("~"):
        raise ValueError("report.terminal_log_path must be a resolved absolute path")
    terminal_log_path = Path(terminal_log_path_raw)
    if not terminal_log_path.is_absolute():
        raise ValueError("report.terminal_log_path must be absolute")
    expected_suffix = _TERMINAL_LOG_SUFFIX / f"{terminal_id}.log"
    if terminal_log_path.parts[-len(expected_suffix.parts) :] != expected_suffix.parts:
        raise ValueError(
            "report.terminal_log_path must point to the resolved CAO terminal log file"
        )

    generated_at_utc = str(report.get("generated_at_utc", "")).strip()
    if not generated_at_utc:
        raise ValueError("report.generated_at_utc must be non-empty")

    return {
        "status": "ok",
        "backend": "cao_rest",
        "tool": "claude",
        "cao_base_url": FIXED_CAO_BASE_URL,
        "agent_identity": "<AGENT_IDENTITY>",
        "unique_agent_identity_count": 1,
        "turns_verified_minimum": 2,
        "verified_turns": verified_turns,
        "session_manifest": "<SESSION_MANIFEST_PATH>",
        "workspace_dir": "<WORKSPACE_PATH>",
        "tmux_target": "<TMUX_TARGET>",
        "terminal_id": "<TERMINAL_ID>",
        "terminal_log_path": (
            "<LAUNCHER_HOME>/.aws/cli-agent-orchestrator/logs/terminal/<TERMINAL_ID>.log"
        ),
        "generated_at_utc": "<TIMESTAMP>",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify or snapshot interactive CAO full-pipeline demo reports"
    )
    parser.add_argument("actual_report", type=Path)
    parser.add_argument("expected_report", type=Path)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()

    actual = json.loads(args.actual_report.read_text(encoding="utf-8"))
    sanitized = _sanitize(actual)

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
            "expected:",
            json.dumps(expected, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        print(
            "actual:",
            json.dumps(sanitized, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 1

    print("verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
