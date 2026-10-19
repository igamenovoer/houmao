#!/usr/bin/env python3
"""Command-hook emitter for the Claude hook-observation harness (throwaway).

Implements design section 2.4 of
context/features/2026-10-18-cli-hook-observation-channel/design/claude-hook-adapter.md:
read the hook JSON from stdin, stamp ``received_at_utc``, a local sequence,
and the channel generation, POST the payload to the collector, and append to
``events.ndjson`` when the collector is unreachable. Stdout stays silent,
the exit code is always 0 (never 2), and stderr goes to a bounded local log.

Configuration arrives through environment variables (exported by the
run-scoped launch wrapper): ``HOUMAO_HOOK_COLLECTOR_URL``,
``HOUMAO_HOOK_TOKEN``, ``HOUMAO_HOOK_STORE``, ``HOUMAO_HOOK_GENERATION``.
Each has a matching CLI flag for manual use.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ENV_COLLECTOR_URL = "HOUMAO_HOOK_COLLECTOR_URL"
ENV_TOKEN = "HOUMAO_HOOK_TOKEN"
ENV_STORE = "HOUMAO_HOOK_STORE"
ENV_GENERATION = "HOUMAO_HOOK_GENERATION"
DEFAULT_LOG_NAME = "emitter.log"
LOG_CAP_BYTES = 1 << 20
MAX_STDIN_BYTES = 8 << 20
VIA_FALLBACK = "command_fallback"
EVENTS_FILENAME = "events.ndjson"


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _redirect_stderr(log_path: Path | None) -> None:
    """Point stderr at the bounded log file, truncating it when it exceeds the cap."""

    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if log_path.exists() and log_path.stat().st_size > LOG_CAP_BYTES else "a"
    handle = log_path.open(mode, encoding="utf-8")
    os.dup2(handle.fileno(), sys.stderr.fileno())


def _locked_append(path: Path, line: str) -> None:
    """Append one line under an exclusive flock (shared with collector.py)."""

    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _build_parser() -> argparse.ArgumentParser:
    """Build the emitter CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collector-url", default=os.environ.get(ENV_COLLECTOR_URL, ""))
    parser.add_argument("--token", default=os.environ.get(ENV_TOKEN, ""))
    store_default = Path(os.environ[ENV_STORE]) if ENV_STORE in os.environ else None
    parser.add_argument("--store", type=Path, default=store_default)
    parser.add_argument("--generation", default=os.environ.get(ENV_GENERATION, "0"))
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help=f"stderr log path (default: <store>/{DEFAULT_LOG_NAME})",
    )
    parser.add_argument("--timeout", type=float, default=3.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Emit one hook event: POST to the collector, else file fallback."""

    args = _build_parser().parse_args(argv)
    log_path = args.log or (args.store / DEFAULT_LOG_NAME if args.store else None)
    _redirect_stderr(log_path)

    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)[:MAX_STDIN_BYTES]
    try:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            payload = {
                "hook_event_name": "Unparseable",
                "parse_error": "top-level value is not a JSON object",
            }
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload = {
            "hook_event_name": "Unparseable",
            "parse_error": str(exc),
            "raw": raw[:4096].decode("utf-8", "replace"),
        }

    payload["received_at_utc"] = _utc_now_iso()
    payload["emitter_sequence"] = time.time_ns()
    try:
        payload["channel_generation"] = int(args.generation)
    except ValueError:
        payload["channel_generation"] = args.generation

    event_name = str(payload.get("hook_event_name") or "unknown")
    delivered = False
    if args.collector_url:
        try:
            body = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                args.collector_url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {args.token}",
                },
            )
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                delivered = 200 <= response.status < 300
        except (urllib.error.URLError, OSError) as exc:
            print(f"emitter: collector unreachable ({exc!r}); using file fallback", file=sys.stderr)
    if delivered:
        return

    if args.store is None:
        print("emitter: no store configured; event dropped", file=sys.stderr)
        return
    envelope: dict[str, Any] = {
        "sequence": None,
        "received_at_utc": _utc_now_iso(),
        "channel_generation": payload["channel_generation"],
        "via": VIA_FALLBACK,
        "provider_event": payload,
    }
    _locked_append(args.store / EVENTS_FILENAME, json.dumps(envelope, sort_keys=True) + "\n")
    print(f"emitter: event={event_name} appended via file fallback", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:  # contract: never propagate, always exit 0
        try:
            print(f"emitter: fatal {exc!r}", file=sys.stderr)
        except Exception:
            pass
    sys.exit(0)
