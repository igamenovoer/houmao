#!/usr/bin/env python3
"""Command-hook emitter for Kimi hook events (throwaway harness).

Ported from ``scripts/explore/codex-hook-observation/emit_hook.py``. Kimi runs
command hooks through the system shell with a single JSON object on stdin (no
trailing newline), inherits the environment from the Kimi process, and treats
``UserPromptSubmit`` stdout as model context. This emitter therefore reads
stdin to EOF, POSTs the untouched payload to the loopback collector with event
name and client-sequence metadata, appends to the run's ``events.ndjson`` when
the collector is unreachable, and always exits 0 with empty stdout.

Kimi payloads do contain ``hook_event_name``, but the event name still travels
as the ``event`` query parameter and the ``X-Hook-Event`` header for parity
with the Claude and Codex lanes; the collector records both under ``delivery``.

Configuration arrives through environment variables exported by the run-scoped
launch wrapper: ``HOUMAO_HOOK_COLLECTOR_URL``, ``HOUMAO_HOOK_TOKEN``,
``HOUMAO_HOOK_STORE``, ``HOUMAO_HOOK_GENERATION``. Each has a matching CLI
flag for manual use.

The provider payload is deliberately not mutated: receive stamps and sequence
numbers live on the collector's envelope so the raw Kimi payload stays faithful
for the campaign's payload catalog.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
import urllib.error
import urllib.parse
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
CLIENT_SEQ_FILENAME = ".emitter-seq"


def utc_now_ms() -> str:
    """Return the current UTC time as an ISO-8601 string with milliseconds."""

    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _redirect_stderr(log_path: Path | None) -> None:
    """Point stderr at the bounded log file, truncating it when it exceeds the cap."""

    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if log_path.exists() and log_path.stat().st_size > LOG_CAP_BYTES else "a"
    try:
        handle = log_path.open(mode, encoding="utf-8")
        os.dup2(handle.fileno(), sys.stderr.fileno())
    except OSError:
        return


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


def _next_client_seq(store: Path | None) -> int:
    """Return a run-local, cross-process monotonically increasing delivery sequence.

    The counter lives in ``<store>/.emitter-seq`` under an exclusive flock so
    concurrent hook processes cannot reuse a number. Without a store (manual
    invocation), a nanosecond wall-clock value is the best available stamp.
    """

    if store is None:
        return time.time_ns()
    store.mkdir(parents=True, exist_ok=True)
    path = store / CLIENT_SEQ_FILENAME
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            raw = handle.read().strip()
            try:
                value = int(raw) if raw else 0
            except ValueError:
                value = 0
            value += 1
            handle.seek(0)
            handle.truncate()
            handle.write(str(value))
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return value


def _with_query(url: str, *, event_name: str, client_seq: int) -> str:
    """Return ``url`` with ``event`` and ``seq`` query parameters merged in."""

    split = urllib.parse.urlsplit(url)
    extra = urllib.parse.urlencode({"event": event_name, "seq": str(client_seq)})
    query = f"{split.query}&{extra}" if split.query else extra
    return urllib.parse.urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))


def _extract_event_name(payload: dict[str, Any]) -> str:
    """Return the hook event name from a Kimi payload, or ``unknown``."""

    for key in ("hook_event_name", "event_name", "event"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


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
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.5,
        help="collector HTTP timeout; must stay below the shortest hook timeout",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Emit one hook event: POST to the collector, else append to the fallback file."""

    args = _build_parser().parse_args(argv)
    log_path = args.log or (args.store / DEFAULT_LOG_NAME if args.store else None)
    _redirect_stderr(log_path)

    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)[:MAX_STDIN_BYTES]
    try:
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            payload: dict[str, Any] = {
                "hook_event_name": "Unparseable",
                "parse_error": "top-level value is not a JSON object",
                "raw": raw[:4096].decode("utf-8", "replace"),
            }
        else:
            payload = parsed
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload = {
            "hook_event_name": "Unparseable",
            "parse_error": str(exc),
            "raw": raw[:4096].decode("utf-8", "replace"),
        }

    event_name = _extract_event_name(payload)
    client_seq = _next_client_seq(args.store)
    try:
        generation: int | str = int(args.generation)
    except ValueError:
        generation = args.generation

    delivered = False
    if args.collector_url:
        url = _with_query(args.collector_url, event_name=event_name, client_seq=client_seq)
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {args.token}",
                    "X-Hook-Event": event_name,
                    "X-Hook-Seq": str(client_seq),
                },
            )
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                delivered = 200 <= response.status < 300
            if not delivered:
                print(
                    f"emitter: collector returned {response.status}; using file fallback",
                    file=sys.stderr,
                )
        except (urllib.error.URLError, OSError) as exc:
            print(
                f"emitter: collector unreachable ({exc!r}); using file fallback",
                file=sys.stderr,
            )
    if delivered:
        return

    if args.store is None:
        print("emitter: no store configured; event dropped", file=sys.stderr)
        return
    envelope: dict[str, Any] = {
        "sequence": None,
        "received_at_utc": utc_now_ms(),
        "received_at_monotonic": round(time.monotonic(), 6),
        "channel_generation": generation,
        "via": VIA_FALLBACK,
        "emitter_seq": client_seq,
        "provider_event": payload,
    }
    _locked_append(args.store / EVENTS_FILENAME, json.dumps(envelope, sort_keys=True) + "\n")
    print(
        f"emitter: event={event_name} seq={client_seq} appended via file fallback", file=sys.stderr
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:  # contract: never propagate, always exit 0
        try:
            print(f"emitter: fatal {exc!r}", file=sys.stderr)
        except Exception:
            pass
    sys.exit(0)
