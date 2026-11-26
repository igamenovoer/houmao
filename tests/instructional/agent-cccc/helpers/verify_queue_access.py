"""Verify the real-agent CCCC queue case from native and provider evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex
import sys
from typing import Any

from cccc_lab import (
    LabError,
    cccc_json,
    load_meta,
    native_tool_calls,
    native_user_messages,
    read_json,
)


def _require(condition: bool, message: str) -> None:
    """Report a failed observation without copying live payloads to errors."""

    if not condition:
        raise LabError(message)


def _one(items: list[dict[str, Any]], label: str) -> dict[str, Any]:
    """Require a unique event or attempt for the asserted scope."""

    _require(len(items) == 1, f"Expected one {label}")
    return items[0]


def _messages(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Read ordered message fields across batches while checking compact projection."""

    batches = document.get("batches")
    _require(isinstance(batches, list), "Queue evidence lacks ordered batches")
    messages = []
    for batch in batches:
        _require(isinstance(batch, list) and bool(batch), "Queue result contains an empty batch")
        for message in batch:
            _require(
                isinstance(message, dict)
                and set(message) == {"sender", "timestamp", "mode", "text", "handle"}
                and all(isinstance(field, str) and bool(field) for field in message.values())
                and message["handle"].startswith("msg_"),
                "Queue evidence lacks compact attributed message fields",
            )
            messages.append(message)
    _require(
        len({message["handle"] for message in messages}) == len(messages),
        "Queue result reused a reply handle",
    )
    return messages


def _attribution(message: dict[str, Any]) -> tuple[str, str, str, str]:
    """Select native fields that survive a freshly minted reply handle."""

    return message["sender"], message["timestamp"], message["mode"], message["text"]


def _recipient_trace(evidence: Path) -> tuple[int | str, list[str]]:
    """Find successful queue and reply steps within one recipient turn."""

    requests: list[str] = []
    commands_by_turn: dict[tuple[Path, int | str], list[str]] = {}
    for path in sorted(evidence.glob("b-transcript-*.jsonl")):
        requests.extend(
            text for _, text in native_user_messages(path) if "<<< BEGIN CCCC REQUEST >>>" in text
        )
        scripts: dict[tuple[int | str, str], str] = {}
        for turn, name, arguments, succeeded in native_tool_calls(path):
            if not succeeded or turn is None:
                continue
            if name == "write":
                script_path = arguments.get("file_path") or arguments.get("path")
                content = arguments.get("content")
                if isinstance(script_path, str) and isinstance(content, str):
                    scripts[(turn, Path(script_path).name)] = content
                continue
            command = arguments.get("command")
            if name != "bash" or not isinstance(command, str):
                continue
            commands = commands_by_turn.setdefault((path, turn), [])
            commands.append(command)
            for line in command.splitlines():
                if line.lstrip().startswith(("bash ", "sh ")):
                    try:
                        parts = shlex.split(line)
                    except ValueError:
                        continue
                    if len(parts) > 1 and (turn, Path(parts[1]).name) in scripts:
                        commands.append(scripts[(turn, Path(parts[1]).name)])
    operations = ("peek", "pop", "ack", "pop-result", "reply")
    turns = [
        turn
        for (_, turn), commands in commands_by_turn.items()
        if all(
            any(re.search(rf"\bchat\s+{operation}(?:\s|$)", command) for command in commands)
            for operation in operations
        )
    ]
    _require(len(turns) == 1, "Successful queue operations and reply must share one native turn")
    return turns[0], requests


def _verify(args: argparse.Namespace) -> dict[str, Any]:
    """Correlate the observed queue results and replies with exact CCCC attempts."""

    evidence = args.evidence
    meta = load_meta(args.run_meta)
    documents = {
        name: read_json(evidence / f"{name}.json", label=name)
        for name in (
            "empty",
            "peek",
            "pop",
            "ack",
            "result",
            "b-yield-ready",
            "yield-round-trip",
            "yield-native-request",
            "b-before-release",
            "next-staged",
            "next-native-absent",
            "next-round-trip",
            "next-native-request",
            "b-final-ready",
            "channel-audit",
        )
    }
    empty, peek, pop, ack, result = (
        documents[name] for name in ("empty", "peek", "pop", "ack", "result")
    )
    _require(empty.get("snapshot") is None and not _messages(empty), "Initial peek was not empty")
    _require(bool(peek.get("snapshot")), "Peek did not return a snapshot")
    selected = _messages(pop)
    _require(
        list(map(_attribution, selected)) == list(map(_attribution, _messages(peek)))
        and list(map(len, pop["batches"])) == list(map(len, peek["batches"])) == [1, 1],
        "Peek and pop differ in their ASAP selection",
    )
    _require(
        bool(pop.get("operation_id"))
        and bool(pop.get("receipt"))
        and ack.get("receipt") == result.get("receipt") == pop["receipt"]
        and ack.get("acknowledged") is True
        and result.get("operation_id") == pop["operation_id"]
        and result.get("status") == "acknowledged"
        and list(map(len, result["batches"])) == [1, 1]
        and list(map(_attribution, _messages(result))) == list(map(_attribution, selected)),
        "Receipt acknowledgment or exact result recovery differs from the pop",
    )

    turn, native_requests = _recipient_trace(evidence)
    history = cccc_json(meta, "a", ["chat", "history", "--limit", "100"])
    read_attempts = []
    for marker in (args.first, args.second):
        events = [event for event in history["messages"] if marker in event["data"].get("text", "")]
        request = _one(
            [
                event
                for event in events
                if event["by"] == meta["actors"]["b"]
                and event["data"].get("message_mode") == "request_reply"
                and not event["data"].get("reply_to")
            ],
            "native request for an in-turn reply",
        )
        reply = _one(
            [
                event
                for event in events
                if event["by"] == meta["actors"]["a"]
                and event["data"].get("reply_to") == request["id"]
            ],
            "peer reply with the exact request parent",
        )
        confirmation = _one(
            [
                event
                for event in events
                if event["by"] == meta["actors"]["b"]
                and event["data"].get("reply_to") == reply["id"]
            ],
            "in-turn confirmation with the exact popped parent",
        )
        attempt = _one(
            cccc_json(meta, "a", ["chat", "deliveries", "--event-ref", reply["event_ref"]])[
                "deliveries"
            ],
            "delivery attempt for the popped reply",
        )
        _require(
            attempt["state"] == "gateway_tool_read"
            and attempt["actor_id"] == meta["actors"]["b"]
            and attempt["event_id"] == reply["id"]
            and bool(attempt["attempt_id"]),
            "The popped reply did not record an exact acknowledged gateway read",
        )
        _require(
            all(marker not in prompt for prompt in native_requests),
            "A popped reply also entered an ordinary request fence",
        )
        read_attempts.append(
            {
                "event_id": reply["id"],
                "attempt_id": attempt["attempt_id"],
                "sequence": attempt["sequence"],
                "state": attempt["state"],
                "confirmation_id": confirmation["id"],
                "attribution": (
                    reply["by"],
                    reply["ts"],
                    reply["data"]["message_mode"],
                    reply["data"]["text"],
                ),
            }
        )
    read_attempts.sort(key=lambda attempt: attempt["sequence"])
    _require(
        len({attempt["attempt_id"] for attempt in read_attempts}) == 2
        and [attempt["attribution"] for attempt in read_attempts]
        == list(map(_attribution, selected)),
        "The selected messages differ from the two acknowledged attempts in provider order",
    )
    for attempt in read_attempts:
        del attempt["attribution"]

    ordinary = {}
    for prefix in ("yield", "next"):
        verified = documents[f"{prefix}-round-trip"]
        fence = documents[f"{prefix}-native-request"]
        attempt = _one(verified["delivery_attempts"], "ordinary handoff attempt")
        _require(
            attempt["state"] == "accepted"
            and verified["native_reply_ancestry"]
            == attempt["event_id"]
            == verified["request"]["id"]
            and fence["fence_count"] == 1
            and fence["message_count"] == 1
            and fence["entries"][0]["event_id"] == attempt["event_id"]
            and sum(verified["token"] in prompt for prompt in native_requests) == 1,
            "Ordinary notification did not arrive once with the exact reply parent",
        )
        ordinary[prefix] = {"event_id": attempt["event_id"], "attempt_id": attempt["attempt_id"]}

    staged = _one(documents["next-staged"]["delivery_attempts"], "staged follow-up attempt")
    _require(
        staged["state"] == "offered"
        and staged["attempt_id"] == ordinary["next"]["attempt_id"]
        and staged["sequence"] > read_attempts[-1]["sequence"]
        and documents["b-before-release"]["state"] == "busy"
        and documents["next-native-absent"]["occurrences"] == 0
        and documents["channel-audit"]["status"] == "passed",
        "The follow-up did not keep its exact attempt across readiness and admission",
    )
    for name in ("b-yield-ready", "b-final-ready"):
        _require(
            documents[name]["request_admission"] == "open"
            and documents[name]["active_execution"] == "idle"
            and documents[name]["state"] == "ready",
            "The recipient did not reach idle open admission",
        )
    return {
        "status": "passed",
        "active_turn": turn,
        "tool_reads": read_attempts,
        "ordinary": ordinary,
    }


def main() -> int:
    """Read captured files and print the safe qualification projection."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-meta", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--first", required=True)
    parser.add_argument("--second", required=True)
    args = parser.parse_args()
    try:
        proof = _verify(args)
    except (LabError, KeyError, TypeError, ValueError, IndexError) as exc:
        message = str(exc) if isinstance(exc, LabError) else "Unexpected queue evidence shape"
        print(f"Queue proof failed: {message}", file=sys.stderr)
        return 1
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
