#!/usr/bin/env python3
"""Render a concise summary of the ping-pong demo state file."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _print_role(role: str, payload: dict[str, object]) -> None:
    print(f"{role}:")
    print(f"  tool: {payload['tool']}")
    print(f"  role_name: {payload['role_name']}")
    print(f"  tracked_agent_id: {payload['tracked_agent_id']}")
    print(f"  tmux_session_name: {payload['tmux_session_name']}")
    print(f"  brain_recipe_path: {payload['brain_recipe_path']}")
    print(f"  working_directory: {payload['working_directory']}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_demo_state_summary.py <demo_state.json>", file=sys.stderr)
        return 2

    state_path = Path(argv[1]).resolve()
    if not state_path.is_file():
        print(f"demo state file not found: {state_path}", file=sys.stderr)
        return 1

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    print(f"demo_state: {state_path}")
    print(f"active: {payload.get('active')}")
    print(f"output_root: {payload.get('output_root')}")
    print(f"api_base_url: {payload.get('api_base_url')}")
    print(f"thread_key: {payload.get('thread_key')}")
    print(f"round_limit: {payload.get('round_limit')}")
    print()
    _print_role("initiator", payload["initiator"])
    print()
    _print_role("responder", payload["responder"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
