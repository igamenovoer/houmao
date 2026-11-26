"""Verify finite Hermes JSONL settlement against the requested logical session."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from typing import Any, Literal

from houmao.agents.realm_controller.backends.dsh_diagnostics import sanitize_dsh_diagnostic
from houmao.agents.realm_controller.backends.headless_output import CanonicalHeadlessEvent


HERMES_HEADLESS_REQUEST = "hermes-request.json"
HERMES_HEADLESS_INPUT = ".hermes-input"
HERMES_HEADLESS_CLIENT_REFUSAL = "hermes-not-started.json"

_MAX_LINE = 2 * 1024 * 1024
_MAX_STREAM = 16 * 1024 * 1024


@dataclass(frozen=True)
class HermesHeadlessSettlement:
    """Report terminal evidence or distinguish client exit from native settlement."""

    status: Literal["completed", "interrupted", "failed", "uncertain"]
    returncode: int | None = None
    completion_source: str | None = None
    session_id: str | None = None
    events: list[CanonicalHeadlessEvent] = field(default_factory=list)
    turn_index: int | None = None


def reconcile_hermes_headless_turn(
    turn_dir: Path, *, generation_id: str | None = None
) -> HermesHeadlessSettlement:
    """Re-read durable evidence without contacting the current daemon."""

    try:
        returncode = int((turn_dir / "exitcode").read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return HermesHeadlessSettlement("uncertain")
    return replace(
        inspect_hermes_headless_result(
            turn_dir=turn_dir, returncode=returncode, generation_id=generation_id
        ),
        events=[],
    )


def inspect_hermes_headless_result(
    *,
    turn_dir: Path,
    returncode: int,
    secrets: tuple[str, ...] = (),
    generation_id: str | None = None,
) -> HermesHeadlessSettlement:
    """Evidence comes from a matching terminal frame or a definite prelaunch refusal."""

    try:
        request = json.loads((turn_dir / HERMES_HEADLESS_REQUEST).read_text(encoding="utf-8"))
        if not isinstance(request, dict) or request.get("turn_id") != turn_dir.name:
            raise ValueError("turn mismatch")
        if generation_id is not None and request.get("generation_id") != generation_id:
            raise ValueError("generation mismatch")
        expected = request.get("session_id")
        index = request.get("turn_index")
        if not isinstance(expected, str) or not expected or type(index) is not int or index < 1:
            raise ValueError("missing session identity")
        if returncode in {125, 127}:
            refusal = json.loads(
                (turn_dir / HERMES_HEADLESS_CLIENT_REFUSAL).read_text(encoding="utf-8")
            )
            if isinstance(refusal, dict) and refusal.get("returncode") == returncode:
                return HermesHeadlessSettlement("failed", returncode, "before_native_start")
        if returncode != 0:
            # Native transport failure, detaching on input/approval, and true
            # cancellation overlap on the CLI exit and JSONL error surfaces.
            return HermesHeadlessSettlement("uncertain", returncode)
        frames = _read_frames(turn_dir / "stdout.jsonl")
        events = _completed_events(frames, session_id=expected, index=index, secrets=secrets)
        return HermesHeadlessSettlement(
            "completed", returncode, "native_jsonl", expected, events, turn_index=index
        )
    except (OSError, UnicodeError, ValueError, RecursionError):
        return HermesHeadlessSettlement("uncertain", returncode)


def _read_frames(path: Path) -> list[dict[str, Any]]:
    """Read bounded, complete JSON lines from the privately captured stream."""

    frames = []
    total = 0
    with path.open("rb") as stream:
        while line := stream.readline(_MAX_LINE + 1):
            total += len(line)
            if len(line) > _MAX_LINE or total > _MAX_STREAM or not line.endswith(b"\n"):
                raise ValueError("Incomplete Hermes JSONL")
            if not line.strip():
                continue
            frame = json.loads(line)
            if not isinstance(frame, dict):
                raise ValueError("Invalid Hermes JSONL frame")
            frames.append(frame)
    return frames


def _completed_events(
    frames: list[dict[str, Any]], *, session_id: str, index: int, secrets: tuple[str, ...]
) -> list[CanonicalHeadlessEvent]:
    """Publish only output belonging to the verified finite invocation."""

    if len(frames) < 2 or frames[0].get("type") != "system" or frames[0].get("subtype") != "init":
        raise ValueError("Missing Hermes stream initialization")
    if frames[0].get("session_id") not in (None, "", session_id):
        raise ValueError("Hermes initialized a different conversation")
    result = frames[-1]
    final_text = result.get("text")
    if (
        result.get("type") != "result"
        or type(result.get("exit_code")) is not int
        or result["exit_code"] != 0
        or result.get("session_id") != session_id
        or not isinstance(final_text, str)
        or result.get("error")
        or type(result.get("replay_gap", False)) is not bool
    ):
        raise ValueError("Hermes result conflicts with the requested turn")
    events = [
        CanonicalHeadlessEvent(
            "session",
            "Hermes conversation verified",
            index,
            "hermes",
            "system",
            session_id=session_id,
        )
    ]
    for frame in frames[1:-1]:
        kind = frame.get("type")
        if frame.get("session_id", session_id) != session_id:
            raise ValueError("Cross-session Hermes frame")
        if kind == "text":
            if not isinstance(frame.get("text"), str):
                raise ValueError("Malformed Hermes text frame")
            # CLI deltas can contain interim segments. The final result is
            # authoritative, including following a native replay gap.
            continue
        if kind not in {"tool_use", "tool_result"}:
            raise ValueError("Unrecognized Hermes stream frame")
        name = frame.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Malformed Hermes tool frame")
        safe_name = _redact_text(name, secrets=secrets)
        data: dict[str, Any] = {"tool_name": safe_name}
        call_id = frame.get("tool_call_id")
        if isinstance(call_id, str) and call_id:
            data["tool_call_id"] = _redact_text(call_id, secrets=secrets)
        if type(frame.get("is_error")) is bool:
            data["is_error"] = frame["is_error"]
        events.append(
            CanonicalHeadlessEvent(
                "tool_call" if kind == "tool_use" else "tool_result",
                safe_name,
                index,
                "hermes",
                kind,
                session_id=session_id,
                data=data,
            )
        )
    if final_text:
        text = _redact_text(final_text, secrets=secrets)
        events.append(
            CanonicalHeadlessEvent(
                "assistant",
                text,
                index,
                "hermes",
                "result",
                session_id=session_id,
                data={"text": text, "replay_gap": result.get("replay_gap", False)},
            )
        )
    return events


def _redact_text(value: str, *, secrets: tuple[str, ...]) -> str:
    """Scrub private values while preserving normal assistant output formatting."""

    return "\n".join(
        sanitize_dsh_diagnostic(line, secret_values=secrets, max_length=_MAX_LINE)
        if secrets or "://" in line
        else line
        for line in value.split("\n")
    )
