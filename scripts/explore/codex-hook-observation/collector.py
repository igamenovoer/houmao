"""Loopback HTTP collector for Codex hook events (throwaway harness).

Ported from ``scripts/explore/claude-hook-observation/collector.py`` with
three deliberate changes: millisecond-granularity UTC timestamps,
per-event monotonic receive times for pane-frame alignment, and a
periodically refreshed ``collector.json`` heartbeat used for
collector-death detection (the production design's health file).

Delivery is **ack-before-disk** (the choice made by the Claude lane): the
HTTP handler validates the request and enqueues it, then returns 204; one
writer thread stamps the monotonic sequence and appends to the run's
``events.ndjson``. A collector crash can therefore lose an already-acked
event; the harness accepts that trade for low hook latency.

Stdlib only. Routes: ``POST /v1/hook?event=<name>&seq=<n>`` (bearer-gated)
and ``GET /health`` (unauthenticated, secret-free).
"""

from __future__ import annotations

import argparse
import fcntl
import hmac
import json
import os
import queue
import signal
import sys
import threading
import time
from collections import Counter
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

MAX_PAYLOAD_BYTES = 1 << 20
HOOK_ROUTE = "/v1/hook"
HEALTH_ROUTE = "/health"
EVENTS_FILENAME = "events.ndjson"
COLLECTOR_FILENAME = "collector.json"
WRITER_DRAIN_TIMEOUT_SECONDS = 10.0
DEFAULT_HEARTBEAT_SECONDS = 2.0


def utc_now_ms() -> str:
    """Return the current UTC time as an ISO-8601 string with milliseconds."""

    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _locked_append(path: Path, line: str) -> None:
    """Append one line under an exclusive flock (shared with emit_hook.py)."""

    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class CollectorState:
    """Mutable collector state shared between the HTTP handler and writer."""

    def __init__(
        self,
        *,
        store: Path,
        token: str,
        generation: int,
        port: int,
        heartbeat_seconds: float = DEFAULT_HEARTBEAT_SECONDS,
    ) -> None:
        """Initialize state; ``last_sequence`` resumes from the events file."""

        self.m_store = store
        self.m_token = token
        self.m_generation = generation
        self.m_port = port
        self.m_heartbeat_seconds = max(heartbeat_seconds, 0.05)
        self.m_started_at_utc = utc_now_ms()
        self.m_started_monotonic = time.monotonic()
        self.m_last_heartbeat_at_utc = self.m_started_at_utc
        self.m_last_heartbeat_monotonic = self.m_started_monotonic
        self.m_events_path = store / EVENTS_FILENAME
        self.m_collector_path = store / COLLECTOR_FILENAME
        self.m_queue: queue.Queue[tuple[dict[str, Any], int, dict[str, Any], str, float] | None] = (
            queue.Queue()
        )
        self.m_lock = threading.Lock()
        self.m_stop_event = threading.Event()
        self.m_accepted = 0
        self.m_oversized = 0
        self.m_malformed = 0
        self.m_unauthorized = 0
        self.m_not_found = 0
        self.m_last_sequence = self._resume_sequence()
        self.m_events_by_name: Counter[str] = Counter()
        self.m_stopped = False
        self.m_stopped_at_utc: str | None = None

    def _resume_sequence(self) -> int:
        """Recover the highest sequence already present in events.ndjson."""

        if not self.m_events_path.is_file():
            return 0
        highest = 0
        with self.m_events_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                value = row.get("sequence")
                if isinstance(value, int) and value > highest:
                    highest = value
        return highest

    def _status_payload_locked(self) -> dict[str, Any]:
        """Build the secret-free status document while holding ``m_lock``."""

        return {
            "schema_version": 1,
            "status": "stopped" if self.m_stopped else "running",
            "port": self.m_port,
            "generation": self.m_generation,
            "pid": os.getpid(),
            "started_at_utc": self.m_started_at_utc,
            "started_monotonic": round(self.m_started_monotonic, 6),
            "last_heartbeat_at_utc": self.m_last_heartbeat_at_utc,
            "last_heartbeat_monotonic": round(self.m_last_heartbeat_monotonic, 6),
            "heartbeat_interval_seconds": self.m_heartbeat_seconds,
            "stopped_at_utc": self.m_stopped_at_utc,
            "events_path": str(self.m_events_path),
            "counts": {
                "accepted": self.m_accepted,
                "oversized": self.m_oversized,
                "malformed": self.m_malformed,
                "unauthorized": self.m_unauthorized,
                "not_found": self.m_not_found,
            },
            "events_by_name": dict(sorted(self.m_events_by_name.items())),
            "last_sequence": self.m_last_sequence,
        }

    def status_payload(self) -> dict[str, Any]:
        """Return a consistent snapshot of the status document."""

        with self.m_lock:
            snapshot = self._status_payload_locked()
        snapshot["last_heartbeat_at_utc"] = utc_now_ms()
        snapshot["last_heartbeat_monotonic"] = round(time.monotonic(), 6)
        return snapshot

    def write_collector_status_locked(self) -> None:
        """Persist the status payload to collector.json atomically.

        The caller must hold ``m_lock`` so the fixed temporary path cannot be
        raced by the heartbeat and writer threads.
        """

        self.m_last_heartbeat_at_utc = utc_now_ms()
        self.m_last_heartbeat_monotonic = time.monotonic()
        tmp_path = self.m_collector_path.with_name(f".{COLLECTOR_FILENAME}.tmp")
        tmp_path.write_text(
            json.dumps(self._status_payload_locked(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, self.m_collector_path)


def _writer_loop(state: CollectorState) -> None:
    """Single writer thread: dequeue, stamp, append, and refresh collector.json."""

    while True:
        item = state.m_queue.get()
        if item is None:
            break
        payload, size, delivery, received_at_utc, received_monotonic = item
        with state.m_lock:
            state.m_last_sequence += 1
            envelope = {
                "sequence": state.m_last_sequence,
                "received_at_utc": received_at_utc,
                "received_at_monotonic": round(received_monotonic, 6),
                "channel_generation": state.m_generation,
                "via": "http",
                "provider_event": payload,
            }
            if delivery:
                envelope["delivery"] = delivery
            _locked_append(state.m_events_path, json.dumps(envelope, sort_keys=True) + "\n")
            state.m_accepted += 1
            name = "unknown"
            if isinstance(payload, dict):
                name = str(payload.get("hook_event_name") or "unknown")
            state.m_events_by_name[name] += 1
            state.write_collector_status_locked()
            sequence = state.m_last_sequence
        print(
            f"event={name} seq={sequence} bytes={size} outcome=accepted",
            file=sys.stderr,
            flush=True,
        )


def _heartbeat_loop(state: CollectorState) -> None:
    """Refresh collector.json on a fixed interval until shutdown."""

    while not state.m_stop_event.wait(state.m_heartbeat_seconds):
        with state.m_lock:
            state.write_collector_status_locked()


class HookHandler(BaseHTTPRequestHandler):
    """HTTP handler: POST /v1/hook (bearer-gated) and GET /health."""

    server_version = "houmao-codex-hook-collector/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        """Silence default request logging; the writer logs structured lines."""

        return

    @property
    def m_state(self) -> CollectorState:
        """Return the collector state attached to the server."""

        return self.server.state  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        """Serve GET /health; everything else 404s."""

        if urlsplit(self.path).path == HEALTH_ROUTE:
            self._send_json(200, self.m_state.status_payload())
            return
        with self.m_state.m_lock:
            self.m_state.m_not_found += 1
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        """Validate and enqueue one hook payload; ack before disk work."""

        state = self.m_state
        parts = urlsplit(self.path)
        if parts.path != HOOK_ROUTE:
            with state.m_lock:
                state.m_not_found += 1
            self._send_json(404, {"error": "not found"})
            return
        authorization = self.headers.get("Authorization", "")
        if not hmac.compare_digest(authorization, f"Bearer {state.m_token}"):
            with state.m_lock:
                state.m_unauthorized += 1
            self._send_json(403, {"error": "unauthorized"})
            return
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else 0
        except ValueError:
            length = 0
        if length > MAX_PAYLOAD_BYTES:
            with state.m_lock:
                state.m_oversized += 1
            self._discard_body(length)
            self._send_json(413, {"error": "payload too large"})
            return
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            with state.m_lock:
                state.m_malformed += 1
            self._send_json(400, {"error": "malformed json"})
            return
        if not isinstance(payload, dict):
            with state.m_lock:
                state.m_malformed += 1
            self._send_json(400, {"error": "payload must be a json object"})
            return

        params = parse_qs(parts.query)
        delivery: dict[str, Any] = {}
        event_query = params.get("event", [""])[0]
        seq_query = params.get("seq", [""])[0]
        event_header = self.headers.get("X-Hook-Event", "")
        seq_header = self.headers.get("X-Hook-Seq", "")
        event_name = event_query or event_header
        if event_name:
            delivery["event"] = event_name
        client_seq = seq_query or seq_header
        if client_seq:
            delivery["client_seq"] = client_seq
        received_at_utc = utc_now_ms()
        received_monotonic = time.monotonic()
        state.m_queue.put((payload, len(body), delivery, received_at_utc, received_monotonic))
        self._send_json(204, None)

    def _discard_body(self, length: int) -> None:
        """Drain an oversized body so the connection closes cleanly."""

        remaining = min(length, MAX_PAYLOAD_BYTES + 1)
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            remaining -= len(chunk)

    def _send_json(self, status: int, payload: dict[str, Any] | None) -> None:
        """Write one JSON response; 204 carries an empty body."""

        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: bind, report the port, serve until SIGTERM/SIGINT."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True, help="artifact directory")
    parser.add_argument("--token", required=True, help="per-session bearer token")
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--port", type=int, default=0, help="0 picks an ephemeral port")
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=DEFAULT_HEARTBEAT_SECONDS,
        help="collector.json refresh interval",
    )
    args = parser.parse_args(argv)

    args.store.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), HookHandler)
    server.daemon_threads = True
    state = CollectorState(
        store=args.store,
        token=args.token,
        generation=args.generation,
        port=int(server.server_address[1]),
        heartbeat_seconds=args.heartbeat_seconds,
    )
    server.state = state  # type: ignore[attr-defined]

    def _handle_signal(signum: int, frame: Any) -> None:
        """Shut the server down from a helper thread (shutdown is not reentrant)."""

        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    with state.m_lock:
        state.write_collector_status_locked()
    print(f"PORT {state.m_port}", flush=True)

    heartbeat = threading.Thread(target=_heartbeat_loop, args=(state,), daemon=True)
    heartbeat.start()
    writer = threading.Thread(target=_writer_loop, args=(state,), daemon=True)
    writer.start()
    server.serve_forever(poll_interval=0.2)
    state.m_stop_event.set()
    state.m_queue.put(None)
    writer.join(timeout=WRITER_DRAIN_TIMEOUT_SECONDS)
    with state.m_lock:
        state.m_stopped = True
        state.m_stopped_at_utc = utc_now_ms()
        state.write_collector_status_locked()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
