"""Tests for the loopback hook collector."""

from __future__ import annotations

import fcntl
import io
import json
import os
import queue
import signal
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from houmao.hook_observation.collector import MAX_PAYLOAD_BYTES

TOKEN = "collector-test-token"
GENERATION = 7
SECRET_SENTINEL = "prompt-secret-sentinel-42"


@dataclass
class CollectorProcess:
    """A running collector subprocess and its endpoints."""

    process: subprocess.Popen[str]
    port: int
    store: Path
    token: str


def _read_line(stream: io.TextIOBase, *, timeout: float) -> str:
    """Read one line from a stream with a timeout."""

    lines: queue.Queue[str] = queue.Queue()

    def _read() -> None:
        lines.put(stream.readline())

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()
    try:
        return lines.get(timeout=timeout)
    except queue.Empty:
        raise AssertionError("timed out waiting for collector output") from None


@contextmanager
def _start_collector(
    tmp_path: Path,
    *,
    generation: int = GENERATION,
    env_token: str | None = TOKEN,
    cli_token: str | None = None,
) -> Iterator[CollectorProcess]:
    """Start a real collector subprocess on an ephemeral loopback port."""

    store = tmp_path / "store"
    env = os.environ.copy()
    env.pop("HOUMAO_HOOK_TOKEN", None)
    if env_token is not None:
        env["HOUMAO_HOOK_TOKEN"] = env_token
    argv = [
        sys.executable,
        "-m",
        "houmao.hook_observation.collector",
        "--store",
        str(store),
        "--generation",
        str(generation),
    ]
    if cli_token is not None:
        argv.extend(["--token", cli_token])
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert process.stdout is not None
        line = _read_line(process.stdout, timeout=20.0)
        if not line.startswith("PORT "):
            process.wait(timeout=5.0)
            stderr = process.stderr.read() if process.stderr is not None else ""
            raise AssertionError(f"collector failed to start: {line!r} {stderr}")
        yield CollectorProcess(
            process=process,
            port=int(line.split()[1]),
            store=store,
            token=env_token or cli_token or "",
        )
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            process.communicate(timeout=20.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()


def _post(
    port: int,
    payload: dict[str, Any] | bytes,
    *,
    token: str | None = TOKEN,
    timeout: float = 5.0,
) -> tuple[int, bytes]:
    """Post one payload and return the status and body, including error statuses."""

    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/hook",
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _get(port: int, path: str) -> tuple[int, str]:
    """Fetch one collector endpoint and return the status and text."""

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5.0) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _health(port: int) -> dict[str, Any]:
    """Return the parsed health document."""

    status, text = _get(port, "/health")
    assert status == 200
    return json.loads(text)


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


def test_collector_rejects_unauthorized_delivery(tmp_path: Path) -> None:
    with _start_collector(tmp_path) as collector:
        assert _post(collector.port, {"hook_event_name": "Stop"}, token=None)[0] == 403
        assert _post(collector.port, {"hook_event_name": "Stop"}, token="wrong-token")[0] == 403

        health = _health(collector.port)
        assert health["counts"]["unauthorized"] == 2
        assert health["counts"]["accepted"] == 0
        assert _event_rows(collector.store) == []


def test_collector_stamps_receive_order_across_posts(tmp_path: Path) -> None:
    names = ["SessionStart", "UserPromptSubmit", "Stop"]
    with _start_collector(tmp_path) as collector:
        for name in names:
            status, body = _post(collector.port, {"hook_event_name": name, "session_id": "s1"})
            assert status == 204
            assert body == b""

        _wait_until(lambda: len(_event_rows(collector.store)) == len(names))
        rows = _event_rows(collector.store)
        assert [row["sequence"] for row in rows] == [1, 2, 3]
        assert [row["provider_event"]["hook_event_name"] for row in rows] == names
        assert {row["via"] for row in rows} == {"http"}
        assert {row["channel_generation"] for row in rows} == {GENERATION}
        for row in rows:
            assert row["provider_event"]["session_id"] == "s1"
            datetime.fromisoformat(row["received_at_utc"])

        boundaries = [
            row for row in _read_rows(collector.store) if row.get("record") == "generation_boundary"
        ]
        assert len(boundaries) == 1
        assert set(boundaries[0]) == {"record", "channel_generation", "recorded_at_utc"}
        assert boundaries[0]["channel_generation"] == GENERATION
        datetime.fromisoformat(boundaries[0]["recorded_at_utc"])


def test_collector_stamps_concurrent_posts_with_unique_sequences(tmp_path: Path) -> None:
    total = 12
    with _start_collector(tmp_path) as collector:
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(
                pool.map(
                    lambda index: _post(
                        collector.port, {"hook_event_name": "PostToolUse", "index": index}
                    )[0],
                    range(total),
                )
            )
        assert statuses == [204] * total
        _wait_until(lambda: len(_event_rows(collector.store)) == total)
        sequences = sorted(row["sequence"] for row in _event_rows(collector.store))
        assert sequences == list(range(1, total + 1))


def test_collector_resumes_sequence_from_existing_store(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir(parents=True)
    existing = {
        "sequence": 41,
        "received_at_utc": "2026-10-19T00:00:00+00:00",
        "channel_generation": 1,
        "via": "http",
        "provider_event": {"hook_event_name": "Stop"},
    }
    (store / "events.ndjson").write_text(json.dumps(existing) + "\n", encoding="utf-8")

    with _start_collector(tmp_path, generation=2) as collector:
        assert _post(collector.port, {"hook_event_name": "Stop"})[0] == 204
        _wait_until(lambda: len(_event_rows(collector.store)) == 2)
        rows = _event_rows(collector.store)
        assert rows[0]["sequence"] == 41
        assert rows[1]["sequence"] == 42
        assert rows[1]["channel_generation"] == 2


def test_collector_rejects_oversized_payload(tmp_path: Path) -> None:
    prefix = b'{"hook_event_name": "PostToolUse", "padding": "'
    suffix = b'"}'
    body = prefix + b"x" * (MAX_PAYLOAD_BYTES + 1 - len(prefix) - len(suffix)) + suffix
    assert len(body) == MAX_PAYLOAD_BYTES + 1

    with _start_collector(tmp_path) as collector:
        status, _ = _post(collector.port, body)
        assert status == 413
        health = _health(collector.port)
        assert health["counts"]["oversized"] == 1
        assert health["counts"]["accepted"] == 0
        assert _event_rows(collector.store) == []


def test_collector_acknowledges_before_slow_disk_work(tmp_path: Path) -> None:
    with _start_collector(tmp_path) as collector:
        events_path = collector.store / "events.ndjson"
        lock_fd = os.open(events_path, os.O_RDWR)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            started = time.monotonic()
            status, _ = _post(collector.port, {"hook_event_name": "Stop"})
            elapsed = time.monotonic() - started
            assert status == 204
            assert elapsed < 2.0
            assert _health(collector.port)["counts"]["accepted"] == 0
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

        _wait_until(lambda: len(_event_rows(collector.store)) == 1)
        assert _event_rows(collector.store)[0]["sequence"] == 1


def test_health_and_collector_record_are_secret_free(tmp_path: Path) -> None:
    payload = {"hook_event_name": "UserPromptSubmit", "prompt": SECRET_SENTINEL}
    with _start_collector(tmp_path) as collector:
        assert _post(collector.port, payload)[0] == 204
        _wait_until(lambda: _health(collector.port)["counts"]["accepted"] == 1)

        status, raw_health = _get(collector.port, "/health")
        assert status == 200
        health = json.loads(raw_health)
        assert health["state"] == "running"
        assert health["generation"] == GENERATION
        assert health["port"] == collector.port
        assert health["last_event"]["name"] == "UserPromptSubmit"
        assert health["last_event"]["sequence"] == 1
        assert "received_at_utc" in health["last_event"]
        assert TOKEN not in raw_health
        assert SECRET_SENTINEL not in raw_health

        record_text = (collector.store / "collector.json").read_text(encoding="utf-8")
        record = json.loads(record_text)
        assert record["status"] == "running"
        assert record["pid"] == collector.process.pid
        assert record["port"] == collector.port
        assert record["generation"] == GENERATION
        assert "started_at_utc" in record
        assert TOKEN not in record_text
        assert SECRET_SENTINEL not in record_text

        assert stat.S_IMODE(collector.store.stat().st_mode) == 0o700
        assert stat.S_IMODE((collector.store / "events.ndjson").stat().st_mode) == 0o600
        assert stat.S_IMODE((collector.store / "collector.json").stat().st_mode) == 0o600


def test_sigterm_drains_queued_events_and_finalizes_record(tmp_path: Path) -> None:
    total = 25
    with _start_collector(tmp_path) as collector:
        for index in range(total):
            assert (
                _post(collector.port, {"hook_event_name": "PostToolUse", "index": index})[0] == 204
            )
        collector.process.send_signal(signal.SIGTERM)
        assert collector.process.wait(timeout=20.0) == 0

        rows = _event_rows(collector.store)
        assert len(rows) == total
        assert [row["sequence"] for row in rows] == list(range(1, total + 1))
        record = json.loads((collector.store / "collector.json").read_text(encoding="utf-8"))
        assert record["status"] == "stopped"
        assert record["port"] == collector.port
        assert record["generation"] == GENERATION
        assert record["stopped_at_utc"] is not None


def test_token_flag_overrides_environment(tmp_path: Path) -> None:
    with _start_collector(tmp_path, env_token=None, cli_token="flag-token") as collector:
        assert _post(collector.port, {"hook_event_name": "Stop"}, token="flag-token")[0] == 204
        _wait_until(lambda: len(_event_rows(collector.store)) == 1)


def test_collector_refuses_to_start_without_token(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("HOUMAO_HOOK_TOKEN", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "houmao.hook_observation.collector",
            "--store",
            str(tmp_path / "store"),
            "--generation",
            "1",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=20.0,
    )
    assert result.returncode != 0
    assert "PORT " not in result.stdout
