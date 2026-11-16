"""Private managed-envelope entrypoint for one DSH ACP invocation."""

from __future__ import annotations

import argparse
from dataclasses import replace
from importlib.resources import files
import json
import os
from pathlib import Path
import signal
import sys
import threading
from typing import Any

from houmao.agents.dsh_configuration import DshConfigurationError, DshSetup, prepare_dsh_home
from houmao.agents.realm_controller.backends.dsh_acp_connection import (
    DshAcpProtocolError,
    DshAcpRequestError,
)
from houmao.agents.realm_controller.backends.dsh_acp_driver import (
    DshAcpInvocation,
    _write_private_json,
    run_dsh_acp_turn,
)


def main() -> int:
    """Execute a private invocation and emit semantic driver records only."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    private = json.loads(args.input.read_text(encoding="utf-8"))
    args.input.unlink()
    turn_dir = Path(private["turn_dir"])
    home = Path(private["home_path"])
    interrupted = threading.Event()

    def interrupt(signum: int, frame: object) -> None:
        """Request native cancellation without exiting before its result drains."""

        interrupted.set()

    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)

    def emit(event: dict[str, Any]) -> None:
        """Persist selected native identity before the first user input is sent."""

        if event["type"] == "session_init":
            binding = json.loads((turn_dir / "dsh-native-binding.json").read_text())
            target = home / "houmao-native-session.json"
            temporary = target.with_name(f".native-session-{private['attempt_id']}.tmp")
            _write_private_json(temporary, binding)
            temporary.replace(target)
        print(json.dumps(event, ensure_ascii=False), flush=True)

    def prepare(invocation: DshAcpInvocation) -> DshAcpInvocation:
        """Resolve the exact model and compose per-attempt assets under the lock."""

        setup = DshSetup.from_file(Path(private["setup_path"]))
        prepared = prepare_dsh_home(
            home,
            setup,
            os.environ,
            private["role_prompt"],
            selected_model=private.get("model"),
            reasoning_level=private.get("reasoning_level"),
            skill_roots=(home / "skills",),
            operator_prompt_mode=private.get("operator_prompt_mode", "unattended"),
        )
        abandoned: list[str] = []
        for path in sorted(turn_dir.parent.glob("*/dsh-native-evidence.jsonl")):
            if path.parent == turn_dir:
                continue
            for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
                if not line.endswith("\n"):
                    continue
                row = json.loads(line)
                if (
                    row.get("version") == 1
                    and row.get("runtime_session_id") == invocation.runtime_session_id
                    and row.get("native_session_id") == invocation.session_id
                    and row.get("event") in {"admitted", "claimed"}
                    and isinstance(row.get("message_id"), str)
                ):
                    abandoned.append(row["message_id"])
        control_path = turn_dir / "dsh-control.json"
        _write_private_json(
            control_path,
            {
                "version": 1,
                "attempt_id": invocation.attempt_id,
                "runtime_session_id": invocation.runtime_session_id,
                "generation": invocation.generation,
                "expected_native_session_id": invocation.session_id,
                "evidence_path": str(invocation.evidence_path),
                "abandoned_message_ids": sorted(set(abandoned)),
            },
        )
        companion = files("houmao.agents").joinpath("assets/dsh/managed-companion.mjs")
        patch = turn_dir / "dsh-companion.patch.json"
        descriptor = os.open(patch, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as patch_stream:
            patch_stream.write(
                json.dumps(
                    [
                        {
                            "insert": [
                                {
                                    "id": "houmao-managed",
                                    "name": str(companion),
                                    "config": {
                                        "controlFile": str(control_path),
                                        "roleFile": str(prepared.role_path),
                                    },
                                }
                            ]
                        }
                    ]
                )
            )
        guard = os.environ.get("HOUMAO_DSH_DISPATCH_GUARD")
        return replace(
            invocation,
            command=(
                private["executable"],
                "--profile",
                "acp",
                "--patch",
                str(prepared.patch_path),
                "--patch",
                str(patch),
            ),
            environment=prepared.environment,
            persistence_root=prepared.persistence_root,
            mcp_servers=tuple(prepared.mcp_servers),
            model=(prepared.provider, prepared.model),
            reasoning_effort=prepared.metadata.get("reasoning_effort"),
            dispatch_guard=Path(guard) if guard else None,
        )

    def confirmed() -> None:
        """Publish the driver's verified receipt, never a helper-launch receipt."""

        binding = json.loads((turn_dir / "dsh-native-binding.json").read_text())
        _write_private_json(turn_dir / "dsh-native-handoff.json", binding)

    invocation = DshAcpInvocation(
        command=(),
        working_directory=Path(private["working_directory"]),
        environment={},
        prompt=private["prompt"],
        session_id=private.get("session_id"),
        attempt_id=private["attempt_id"],
        runtime_session_id=private["runtime_session_id"],
        generation=private["generation"],
        turn_dir=turn_dir,
        lock_path=home / "houmao-invocation.lock",
        evidence_path=turn_dir / "dsh-native-evidence.jsonl",
    )
    try:
        outcome = run_dsh_acp_turn(
            invocation, emit=emit, interrupted=interrupted, confirmed=confirmed, prepare=prepare
        )
        return (
            0
            if outcome.stop_reason == "end_turn"
            else 130
            if outcome.stop_reason == "cancelled"
            else 1
        )
    except Exception as exc:
        reason = (
            str(exc)
            if isinstance(exc, (DshConfigurationError, DshAcpProtocolError, DshAcpRequestError))
            else type(exc).__name__
        )
        emit(
            {
                "type": "driver_error",
                "message": f"DSH invocation failed: {reason}",
                "error_kind": type(exc).__name__,
            }
        )
        print(f"DSH invocation failed: {reason}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
