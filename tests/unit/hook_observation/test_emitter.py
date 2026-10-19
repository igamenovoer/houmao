"""Tests for the command-hook emitter."""

from __future__ import annotations

import json
import os
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

TOKEN = "emitter-test-token"
GENERATION = 4
LOG_CAP_BYTES = 1 << 20
EMITTER_MODULE = "houmao.hook_observation.emitter"


@contextmanager
def _start_collector(tmp_path: Path) -> Iterator[tuple[int, Path, subprocess.Popen[str]]]:
    """Start a real collector subprocess and yield its port and store."""

    store = tmp_path / "store"
    env = os.environ.copy()
    env["HOUMAO_HOOK_TOKEN"] = TOKEN
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "houmao.hook_observation.collector",
            "--store",
            str(store),
            "--generation",
            str(GENERATION),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert process.stdout is not None
        lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
        line = lines.get(timeout=20.0)
        if not line.startswith("PORT "):
            raise AssertionError(f"collector failed to start: {line!r}")
        yield int(line.split()[1]), store, process
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            process.communicate(timeout=20.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()


@contextmanager
def _dead_port() -> Iterator[int]:
    """Bind an unlistened loopback socket so connections are refused reliably."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        yield int(sock.getsockname()[1])


def _run_emitter(
    *,
    collector_url: str,
    store: Path,
    stdin: bytes,
    generation: int = GENERATION,
    token: str | None = TOKEN,
) -> subprocess.CompletedProcess[bytes]:
    """Run the emitter as a subprocess with the given environment and stdin."""

    env = os.environ.copy()
    env.pop("HOUMAO_HOOK_TOKEN", None)
    if token is not None:
        env["HOUMAO_HOOK_TOKEN"] = token
    return subprocess.run(
        [
            sys.executable,
            "-m",
            EMITTER_MODULE,
            "--collector-url",
            collector_url,
            "--store",
            str(store),
            "--generation",
            str(generation),
        ],
        input=stdin,
        capture_output=True,
        env=env,
        timeout=30.0,
    )


def _emitter_url(port: int) -> str:
    """Return the collector hook endpoint for one port."""

    return f"http://127.0.0.1:{port}/v1/hook"


def _read_rows(store: Path) -> list[dict[str, Any]]:
    """Read every parseable record from ``events.ndjson``."""

    path = store / "events.ndjson"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _event_rows(store: Path) -> list[dict[str, Any]]:
    """Return only provider-event envelopes, excluding boundary records."""

    return [row for row in _read_rows(store) if "provider_event" in row]


def _wait_until(predicate: Callable[[], bool], *, timeout: float = 10.0) -> None:
    """Poll until a predicate holds, or fail the test."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition was not met within the timeout")


def test_emitter_delivers_to_running_collector(tmp_path: Path) -> None:
    payload = {"hook_event_name": "SessionStart", "session_id": "abc", "source": "startup"}
    with _start_collector(tmp_path) as (port, store, _process):
        result = _run_emitter(
            collector_url=_emitter_url(port),
            store=store,
            stdin=json.dumps(payload).encode("utf-8"),
        )
        assert result.returncode == 0
        assert result.stdout == b""
        _wait_until(lambda: len(_event_rows(store)) == 1)
        rows = _event_rows(store)
        assert rows[0]["via"] == "http"
        assert rows[0]["sequence"] == 1
        assert rows[0]["channel_generation"] == GENERATION
        assert rows[0]["provider_event"] == payload
        assert (store / "emitter.log").read_text(encoding="utf-8").count("outcome=delivered") == 1


def test_emitter_falls_back_to_file_when_collector_is_down(tmp_path: Path) -> None:
    payload = {"hook_event_name": "Stop", "session_id": "abc"}
    store = tmp_path / "store"
    with _dead_port() as dead_port:
        result = _run_emitter(
            collector_url=_emitter_url(dead_port),
            store=store,
            stdin=json.dumps(payload).encode("utf-8"),
        )
    assert result.returncode == 0
    assert result.stdout == b""
    rows = _event_rows(store)
    assert len(rows) == 1
    assert rows[0]["via"] == "command_fallback"
    assert rows[0]["sequence"] is None
    assert rows[0]["channel_generation"] == GENERATION
    assert rows[0]["provider_event"] == payload
    log_text = (store / "emitter.log").read_text(encoding="utf-8")
    assert "outcome=fallback_appended" in log_text


def test_emitter_tolerates_malformed_stdin(tmp_path: Path) -> None:
    store = tmp_path / "store"
    with _dead_port() as dead_port:
        result = _run_emitter(
            collector_url=_emitter_url(dead_port),
            store=store,
            stdin=b"{not json",
        )
    assert result.returncode == 0
    assert result.stdout == b""
    rows = _event_rows(store)
    assert len(rows) == 1
    assert rows[0]["via"] == "command_fallback"
    assert rows[0]["provider_event"]["hook_event_name"] == "Unparseable"
    assert "parse_error" in rows[0]["provider_event"]
    assert rows[0]["provider_event"]["raw"] == "{not json"


def test_emitter_without_token_falls_back_without_posting(tmp_path: Path) -> None:
    payload = {"hook_event_name": "SessionStart"}
    with _start_collector(tmp_path) as (port, store, _process):
        result = _run_emitter(
            collector_url=_emitter_url(port),
            store=store,
            stdin=json.dumps(payload).encode("utf-8"),
            token=None,
        )
        assert result.returncode == 0
        assert result.stdout == b""
        rows = _event_rows(store)
        assert len(rows) == 1
        assert rows[0]["via"] == "command_fallback"
        assert (store / "emitter.log").read_text(encoding="utf-8").count("is not set") == 1


def test_emitter_never_exits_two_on_invalid_arguments() -> None:
    result = subprocess.run(
        [sys.executable, "-m", EMITTER_MODULE, "--collector-url"],
        input=b"",
        capture_output=True,
        timeout=30.0,
    )
    assert result.returncode == 0
    assert result.stdout == b""


def test_emitter_falls_back_on_invalid_collector_url(tmp_path: Path) -> None:
    store = tmp_path / "store"
    result = _run_emitter(
        collector_url="not a url",
        store=store,
        stdin=b'{"hook_event_name": "Stop"}',
    )
    assert result.returncode == 0
    assert result.stdout == b""
    rows = _event_rows(store)
    assert len(rows) == 1
    assert rows[0]["via"] == "command_fallback"


def test_emitter_truncates_oversized_log(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir(parents=True)
    log_path = store / "emitter.log"
    log_path.write_bytes(b"x" * (LOG_CAP_BYTES + 100))
    with _dead_port() as dead_port:
        result = _run_emitter(
            collector_url=_emitter_url(dead_port),
            store=store,
            stdin=b'{"hook_event_name": "Stop"}',
        )
    assert result.returncode == 0
    assert result.stdout == b""
    log_text = log_path.read_text(encoding="utf-8")
    assert len(log_text.encode("utf-8")) < LOG_CAP_BYTES
    assert "outcome=fallback_appended" in log_text


def test_emitter_writes_nothing_to_stdout_on_empty_stdin(tmp_path: Path) -> None:
    store = tmp_path / "store"
    with _dead_port() as dead_port:
        result = _run_emitter(
            collector_url=_emitter_url(dead_port),
            store=store,
            stdin=b"",
        )
    assert result.returncode == 0
    assert result.stdout == b""
    rows = _event_rows(store)
    assert len(rows) == 1
    assert rows[0]["provider_event"]["hook_event_name"] == "Unparseable"
