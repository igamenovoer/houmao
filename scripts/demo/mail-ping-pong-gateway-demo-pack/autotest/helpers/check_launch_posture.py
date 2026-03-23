#!/usr/bin/env python3
"""Validate unattended launch posture from one demo inspect artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _require_value(payload: dict[str, object], *, key: str, expected: object, role: str) -> None:
    actual = payload.get(key)
    if actual != expected:
        raise SystemExit(
            f"{role} launch posture mismatch for {key}: expected {expected!r}, got {actual!r}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inspect_path")
    args = parser.parse_args(argv)

    inspect_path = Path(args.inspect_path).resolve()
    if not inspect_path.is_file():
        raise SystemExit(f"inspect artifact not found: {inspect_path}")

    payload = json.loads(inspect_path.read_text(encoding="utf-8"))
    participants = payload.get("participants")
    if not isinstance(participants, dict):
        raise SystemExit("inspect artifact missing participants mapping")

    for role in ("initiator", "responder"):
        participant = participants.get(role)
        if not isinstance(participant, dict):
            raise SystemExit(f"inspect artifact missing participant payload for {role}")
        launch_posture = participant.get("launch_posture")
        if not isinstance(launch_posture, dict):
            raise SystemExit(f"inspect artifact missing launch_posture for {role}")
        _require_value(
            launch_posture,
            key="tracked_recipe_operator_prompt_mode",
            expected="unattended",
            role=role,
        )
        _require_value(
            launch_posture,
            key="built_brain_manifest_operator_prompt_mode",
            expected="unattended",
            role=role,
        )
        _require_value(
            launch_posture,
            key="live_launch_request_operator_prompt_mode",
            expected="unattended",
            role=role,
        )
        _require_value(
            launch_posture,
            key="launch_policy_applied",
            expected=True,
            role=role,
        )

    print("launch posture ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
