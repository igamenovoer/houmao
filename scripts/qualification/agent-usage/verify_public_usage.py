"""Verify public accounting pages against isolated native provider evidence.

Run this utility through ``pixi run python`` after launching a local managed
qualification session. It writes only public accounting data and numeric
comparisons; prompts, responses, credentials, and native paths stay out of the
report. The native readers deliberately use the captured provider fields
directly, independently of Houmao's accounting adapters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import urlopen


def _get(base_url: str, agent: str, *, after: str | None = None) -> dict[str, Any]:
    """Read one maintained usage page with an optional opaque end cursor."""

    query: dict[str, str | int] = {"limit": 500}
    if after is not None:
        query["after"] = after
    url = f"{base_url.rstrip('/')}/houmao/agents/{quote(agent, safe='')}/usage?{urlencode(query)}"
    with urlopen(url, timeout=10) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError("Expected an accounting page object")
    return result


def _native_counts(
    paths: list[Path], *, provider: str, session_id: str
) -> dict[str, tuple[int, int]]:
    """Read request increments using qualified native fields and explicit IDs."""

    requests: dict[tuple[str, str], tuple[int, int]] = {}
    for path in paths:
        turn: str | None = None
        sequence = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            usage = None
            request_id: str | None = None
            if provider == "claude":
                if item.get("sessionId") != session_id or item.get("isSidechain"):
                    continue
                if item.get("type") == "user":
                    turn = item.get("uuid")
                elif item.get("type") == "assistant":
                    message = item.get("message", {})
                    usage = message.get("usage")
                    request_id = message.get("id")
            elif provider == "codex" and item.get("type") == "token_usage_record":
                payload = item.get("payload", {})
                turn = payload.get("turn_id")
                usage = payload.get("usage")
                request_id = payload.get("response_id")
            elif provider == "kimi":
                if item.get("type") == "turn.prompt":
                    turn = str(item["turnId"])
                elif item.get("type") == "usage.record":
                    usage = item.get("usage")
                    sequence += 1
                    request_id = str(sequence)
            if not isinstance(usage, dict) or not turn or not request_id:
                continue
            inputs = usage.get("inputOther" if provider == "kimi" else "input_tokens")
            outputs = usage.get("output" if provider == "kimi" else "output_tokens")
            if isinstance(inputs, int) and isinstance(outputs, int):
                requests[(turn, request_id)] = inputs, outputs
    result: dict[str, tuple[int, int]] = {}
    for (turn, _), (inputs, outputs) in requests.items():
        prior = result.get(turn, (0, 0))
        result[turn] = prior[0] + inputs, prior[1] + outputs
    return result


def main() -> None:
    """Poll final rows, compare native counters, and save an accounting-only report."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:19987")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--expected-records", required=True, type=int)
    parser.add_argument("--timeout-seconds", default=45.0, type=float)
    parser.add_argument("--native-file", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout_seconds
    page = _get(args.base_url, args.agent)
    while len(page["records"]) < args.expected_records and time.monotonic() < deadline:
        time.sleep(0.25)
        page = _get(args.base_url, args.agent)
    records = page["records"]
    assert len(records) == args.expected_records, "Unexpected finalized record count"
    assert len({item["record_id"] for item in records}) == len(records)
    cursor = page["next_cursor"]
    assert cursor is not None, "Finalized accounting must expose a polling position"
    empty = _get(args.base_url, args.agent, after=cursor)
    assert empty["records"] == [] and empty["next_cursor"] == cursor
    checks = []
    if args.native_file:
        assert len({item["provider_session_id"] for item in records}) == 1
        native = _native_counts(
            args.native_file,
            provider=records[0]["provider"],
            session_id=records[0]["provider_session_id"],
        )
        for record in records:
            counts = native[record["provider_turn_id"]]
            actual = (
                record["token_usage"]["input_tokens"]["value"],
                record["token_usage"]["output_tokens"]["value"],
            )
            assert actual == counts, "Public counters differ from native request increments"
            checks.append(
                {"record_id": record["record_id"], "input": counts[0], "output": counts[1]}
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"page": page, "native_checks": checks, "end_cursor_retained": True}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"records": len(records), "native_checks": len(checks), "end_cursor_retained": True}
        )
    )


if __name__ == "__main__":
    main()
