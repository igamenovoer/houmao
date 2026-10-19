"""Loopback HTTP collector for CLI hook observation events.

The collector is a per-session ingress adapter: it authenticates deliveries with
a bearer token, stamps each accepted provider payload with receive order and the
channel generation, appends one envelope per event to ``events.ndjson``, and
publishes secret-free health and liveness documents. It does not resolve tracked
state and never logs or publishes raw payloads.

The HTTP handler acknowledges a request as soon as the payload is parsed and
queued; a single writer thread performs the disk work. The collector binds
``127.0.0.1`` on an ephemeral port and prints the chosen port as ``PORT <n>`` on
stdout so a launcher can discover it. Standard library only.
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
from collections import Counter
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import FrameType
from typing import Any, Final, cast

MAX_PAYLOAD_BYTES: Final = 1 << 20
HOOK_ROUTE: Final = "/v1/hook"
HEALTH_ROUTE: Final = "/health"
EVENTS_FILENAME: Final = "events.ndjson"
COLLECTOR_FILENAME: Final = "collector.json"
TOKEN_ENV: Final = "HOUMAO_HOOK_TOKEN"
WRITER_DRAIN_TIMEOUT_SECONDS: Final = 10.0
GENERATION_BOUNDARY_RECORD: Final = "generation_boundary"
COUNT_KEYS: Final[tuple[str, ...]] = (
    "accepted",
    "unauthorized",
    "oversized",
    "malformed",
    "not_found",
    "write_failed",
)


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _log(
    outcome: str, *, name: str | None = None, size: int | None = None, sequence: int | None = None
) -> None:
    """Write one structured stderr line about an event outcome."""

    fields: list[str] = []
    if name is not None:
        fields.append(f"event={name}")
    if size is not None:
        fields.append(f"bytes={size}")
    if sequence is not None:
        fields.append(f"seq={sequence}")
    fields.append(f"outcome={outcome}")
    print(" ".join(fields), file=sys.stderr, flush=True)


def _ensure_store(store: Path) -> None:
    """Create the artifact directory owner-only."""

    store.mkdir(parents=True, exist_ok=True)
    os.chmod(store, 0o700)


def _locked_append(path: Path, line: str) -> None:
    """Append one line to a shared NDJSON file under an exclusive ``flock``."""

    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            data = line.encode("utf-8")
            while data:
                written = os.write(fd, data)
                data = data[written:]
            os.fsync(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


class CollectorState:
    """Mutable collector state shared between HTTP handlers and the writer."""

    def __init__(self, *, store: Path, token: str, generation: int, port: int) -> None:
        """Initialize state; the sequence counter resumes from ``events.ndjson``."""

        self.m_store: Path = store
        self.m_token: str = token
        self.m_generation: int = generation
        self.m_port: int = port
        self.m_started_at_utc: str = _utc_now_iso()
        self.m_stopped_at_utc: str | None = None
        self.m_events_path: Path = store / EVENTS_FILENAME
        self.m_collector_path: Path = store / COLLECTOR_FILENAME
        self.m_queue: queue.Queue[tuple[dict[str, Any], int] | None] = queue.Queue()
        self.m_state_lock: threading.Lock = threading.Lock()
        self.m_counts: Counter[str] = Counter()
        self.m_last_sequence: int = self._resume_sequence()
        self.m_last_event: dict[str, Any] | None = None
        self.m_events_by_name: Counter[str] = Counter()
        self.m_stopped: bool = False

    def _resume_sequence(self) -> int:
        """Return the highest sequence already present in ``events.ndjson``."""

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
                if not isinstance(row, dict):
                    continue
                value = row.get("sequence")
                if isinstance(value, int) and value > highest:
                    highest = value
        return highest

    def note(self, outcome: str) -> None:
        """Count one request outcome under the state lock."""

        with self.m_state_lock:
            self.m_counts[outcome] += 1

    def health_payload(self) -> dict[str, Any]:
        """Return the secret-free health document served on ``GET /health``."""

        with self.m_state_lock:
            counts = {key: self.m_counts[key] for key in COUNT_KEYS}
            events_by_name = dict(sorted(self.m_events_by_name.items()))
            last_event = dict(self.m_last_event) if self.m_last_event is not None else None
            last_sequence = self.m_last_sequence
            stopped_at = self.m_stopped_at_utc
        return {
            "state": "stopped" if self.m_stopped else "running",
            "pid": os.getpid(),
            "port": self.m_port,
            "generation": self.m_generation,
            "started_at_utc": self.m_started_at_utc,
            "stopped_at_utc": stopped_at,
            "counts": counts,
            "events_by_name": events_by_name,
            "last_sequence": last_sequence,
            "last_event": last_event,
        }

    def write_collector_record(self) -> None:
        """Persist the secret-free liveness record atomically."""

        payload = {
            "schema_version": 1,
            "status": "stopped" if self.m_stopped else "running",
            "pid": os.getpid(),
            "port": self.m_port,
            "generation": self.m_generation,
            "started_at_utc": self.m_started_at_utc,
            "stopped_at_utc": self.m_stopped_at_utc,
        }
        tmp_path = self.m_collector_path.with_name(self.m_collector_path.name + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, self.m_collector_path)

    def write_generation_boundary(self) -> None:
        """Append the generation boundary record before the provider starts."""

        record = {
            "record": GENERATION_BOUNDARY_RECORD,
            "channel_generation": self.m_generation,
            "recorded_at_utc": _utc_now_iso(),
        }
        _locked_append(self.m_events_path, json.dumps(record) + "\n")

    def stop(self) -> None:
        """Mark the collector stopped and stamp the stop time."""

        self.m_stopped = True
        self.m_stopped_at_utc = _utc_now_iso()

    def writer_loop(self) -> None:
        """Dequeue, stamp, append, and log accepted events until the sentinel."""

        while True:
            item = self.m_queue.get()
            if item is None:
                return
            payload, size = item
            name = "unknown"
            if isinstance(payload.get("hook_event_name"), str):
                name = str(payload["hook_event_name"])
            sequence = self.m_last_sequence + 1
            received_at = _utc_now_iso()
            envelope = {
                "sequence": sequence,
                "received_at_utc": received_at,
                "channel_generation": self.m_generation,
                "via": "http",
                "provider_event": payload,
            }
            try:
                _locked_append(self.m_events_path, json.dumps(envelope, sort_keys=True) + "\n")
            except OSError as exc:
                _log("write_failed", name=name, size=size, sequence=sequence)
                print(f"collector: write error {exc!r}", file=sys.stderr, flush=True)
                self.note("write_failed")
                continue
            with self.m_state_lock:
                self.m_last_sequence = sequence
                self.m_counts["accepted"] += 1
                self.m_events_by_name[name] += 1
                self.m_last_event = {
                    "name": name,
                    "sequence": sequence,
                    "received_at_utc": received_at,
                }
            _log("accepted", name=name, size=size, sequence=sequence)


class HookHTTPServer(ThreadingHTTPServer):
    """Threaded loopback HTTP server carrying the collector state."""

    def __init__(self, server_address: tuple[str, int]) -> None:
        """Bind the server and leave the state unset until the collector exists."""

        self.m_state: CollectorState | None = None
        super().__init__(server_address, HookHandler)

    def set_state(self, state: CollectorState) -> None:
        """Attach the collector state to this server."""

        self.m_state = state


class HookHandler(BaseHTTPRequestHandler):
    """HTTP handler: authenticated ``POST /v1/hook`` and ``GET /health``."""

    server_version = "houmao-hook-collector/1.0"

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default request log; the writer emits structured lines."""

        return

    @property
    def m_state(self) -> CollectorState:
        """Return the collector state attached to the server."""

        state = cast(HookHTTPServer, self.server).m_state
        if state is None:
            raise RuntimeError("collector state is not initialized")
        return state

    def do_GET(self) -> None:
        """Serve ``GET /health``; everything else is a counted 404."""

        path = self.path.split("?", 1)[0]
        if path == HEALTH_ROUTE:
            self._send_json(200, self.m_state.health_payload())
            return
        self.m_state.note("not_found")
        self.close_connection = True
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        """Authenticate, cap, parse, enqueue, and acknowledge one hook payload."""

        state = self.m_state
        if self.path.split("?", 1)[0] != HOOK_ROUTE:
            state.note("not_found")
            self.close_connection = True
            self._send_json(404, {"error": "not found"})
            return
        if not self._authorized(state):
            state.note("unauthorized")
            self.close_connection = True
            self._send_json(403, {"error": "unauthorized"})
            _log("unauthorized")
            return
        length = self._content_length()
        if length is None or length < 0:
            state.note("malformed")
            self.close_connection = True
            self._send_json(400, {"error": "invalid content length"})
            _log("malformed")
            return
        if length > MAX_PAYLOAD_BYTES:
            state.note("oversized")
            self._discard_body(length)
            self.close_connection = True
            self._send_json(413, {"error": "payload too large"})
            _log("oversized", size=length)
            return
        body = self.rfile.read(length) if length > 0 else b""
        payload = self._parse_payload(body)
        if payload is None:
            state.note("malformed")
            self.close_connection = True
            self._send_json(400, {"error": "malformed json"})
            _log("malformed", size=len(body))
            return
        state.m_queue.put((payload, len(body)))
        self._send_json(204, None)

    def _authorized(self, state: CollectorState) -> bool:
        """Compare the bearer token without early exit."""

        header = self.headers.get("Authorization", "")
        return hmac.compare_digest(
            header.encode("utf-8", "replace"),
            f"Bearer {state.m_token}".encode("utf-8"),
        )

    def _content_length(self) -> int | None:
        """Return the declared body length, or ``None`` when unusable."""

        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return 0
        try:
            return int(raw_length)
        except ValueError:
            return None

    def _parse_payload(self, body: bytes) -> dict[str, Any] | None:
        """Decode one JSON object payload, or return ``None`` when malformed."""

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _discard_body(self, length: int) -> None:
        """Drain a bounded amount of an oversized body before responding."""

        remaining = min(length, MAX_PAYLOAD_BYTES + 1)
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                return
            remaining -= len(chunk)

    def _send_json(self, status: int, payload: dict[str, Any] | None) -> None:
        """Write one JSON response; ``204`` carries an empty body."""

        body = b"" if payload is None else json.dumps(payload, sort_keys=True).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)
                self.wfile.flush()
        except OSError:
            self.close_connection = True


def _install_signal_handlers(server: HookHTTPServer) -> None:
    """Stop the serve loop from a helper thread, since ``shutdown`` blocks."""

    def _handle_signal(signum: int, frame: FrameType | None) -> None:
        """Request a graceful shutdown without re-entering the serve loop."""

        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)


def _build_parser() -> argparse.ArgumentParser:
    """Build the collector CLI parser."""

    parser = argparse.ArgumentParser(
        description="Loopback collector for CLI hook observation events."
    )
    parser.add_argument("--store", type=Path, required=True, help="hook artifact directory")
    parser.add_argument(
        "--token",
        default=os.environ.get(TOKEN_ENV, ""),
        help=f"bearer token (default: ${TOKEN_ENV})",
    )
    parser.add_argument("--generation", type=int, required=True, help="channel generation")
    parser.add_argument("--port", type=int, default=0, help="0 selects an ephemeral loopback port")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the collector until SIGTERM or SIGINT, then drain and finalize."""

    args = _build_parser().parse_args(argv)
    if not args.token:
        print(f"collector: no bearer token; set ${TOKEN_ENV} or pass --token", file=sys.stderr)
        return 2
    _ensure_store(args.store)
    server = HookHTTPServer(("127.0.0.1", int(args.port)))
    port = int(server.server_address[1])
    state = CollectorState(
        store=args.store,
        token=args.token,
        generation=int(args.generation),
        port=port,
    )
    server.set_state(state)
    state.write_generation_boundary()
    state.write_collector_record()
    _install_signal_handlers(server)
    writer = threading.Thread(target=state.writer_loop, name="hook-collector-writer", daemon=True)
    writer.start()
    print(f"PORT {port}", flush=True)
    print(
        f"collector listening on 127.0.0.1:{port} generation={state.m_generation}",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        state.m_queue.put(None)
        writer.join(timeout=WRITER_DRAIN_TIMEOUT_SECONDS)
        if writer.is_alive():
            _log("writer_drain_timeout")
        state.stop()
        state.write_collector_record()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
