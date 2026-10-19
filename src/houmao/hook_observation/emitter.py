"""Command-hook emitter for the CLI hook observation channel.

The emitter is the ``SessionStart`` command-hook handler: it reads one hook
payload from stdin, posts it to the loopback collector with the per-session
bearer token, and appends a fallback envelope directly to ``events.ndjson`` when
delivery fails. The hook contract is strict: stdout stays empty, no decision
fields are produced, and the process always exits 0 (never 2). Diagnostic output
goes to a bounded ``emitter.log`` under the store directory.

The collector URL, store directory, and channel generation are baked into the
generated hook command line; the bearer token is read from the
``HOUMAO_HOOK_TOKEN`` environment variable so it never appears in settings or
process arguments. Standard library only.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ENV_TOKEN: Final = "HOUMAO_HOOK_TOKEN"
DEFAULT_LOG_NAME: Final = "emitter.log"
LOG_CAP_BYTES: Final = 1 << 20
MAX_STDIN_BYTES: Final = 8 << 20
MAX_RAW_ECHO_BYTES: Final = 4096
EVENTS_FILENAME: Final = "events.ndjson"
VIA_COMMAND_FALLBACK: Final = "command_fallback"
DEFAULT_TIMEOUT_SECONDS: Final = 1.5


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _ensure_store(store: Path) -> None:
    """Create the artifact directory owner-only."""

    store.mkdir(parents=True, exist_ok=True)
    os.chmod(store, 0o700)


def _redirect_stderr(store: Path | None) -> None:
    """Point stderr at a bounded log, truncating it when it exceeds the cap."""

    if store is None:
        return
    try:
        _ensure_store(store)
        log_path = store / DEFAULT_LOG_NAME
        mode = "w" if log_path.exists() and log_path.stat().st_size > LOG_CAP_BYTES else "a"
        handle = log_path.open(mode, encoding="utf-8")
        os.fchmod(handle.fileno(), 0o600)
        os.dup2(handle.fileno(), sys.stderr.fileno())
    except (OSError, ValueError):
        return


def _silence_stdout() -> None:
    """Detach stdout so an unexpected write cannot reach the provider."""

    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, sys.stdout.fileno())
        os.close(devnull_fd)
    except (OSError, ValueError):
        return


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


def _read_provider_event() -> dict[str, Any]:
    """Read one hook payload from stdin, synthesizing a marker when malformed."""

    try:
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)[:MAX_STDIN_BYTES]
    except OSError as exc:
        return {"hook_event_name": "Unparseable", "parse_error": f"stdin read failed: {exc}"}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "hook_event_name": "Unparseable",
            "parse_error": str(exc),
            "raw": raw[:MAX_RAW_ECHO_BYTES].decode("utf-8", "replace"),
        }
    if not isinstance(payload, dict):
        return {
            "hook_event_name": "Unparseable",
            "parse_error": "top-level value is not a JSON object",
        }
    return payload


def _event_name(payload: dict[str, Any]) -> str:
    """Return the provider event name, or ``unknown`` when absent."""

    name = payload.get("hook_event_name")
    return name if isinstance(name, str) and name else "unknown"


def _post(collector_url: str, token: str, payload: dict[str, Any], timeout: float) -> bool:
    """Post one provider payload to the collector; return whether it was accepted."""

    try:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            collector_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            return bool(200 <= response.status < 300)
    except Exception as exc:
        print(
            f"emitter: event={_event_name(payload)} outcome=unreachable error={exc!r}",
            file=sys.stderr,
            flush=True,
        )
        return False


def _append_fallback(store: Path, payload: dict[str, Any], generation: int) -> bool:
    """Append one fallback envelope to ``events.ndjson``; return success."""

    envelope: dict[str, Any] = {
        "sequence": None,
        "received_at_utc": _utc_now_iso(),
        "channel_generation": generation,
        "via": VIA_COMMAND_FALLBACK,
        "provider_event": payload,
    }
    try:
        _ensure_store(store)
        _locked_append(store / EVENTS_FILENAME, json.dumps(envelope, sort_keys=True) + "\n")
    except OSError as exc:
        print(
            f"emitter: event={_event_name(payload)} outcome=fallback_failed error={exc!r}",
            file=sys.stderr,
            flush=True,
        )
        return False
    print(
        f"emitter: event={_event_name(payload)} outcome=fallback_appended",
        file=sys.stderr,
        flush=True,
    )
    return True


def _build_parser() -> argparse.ArgumentParser:
    """Build the emitter CLI parser with non-failing optional arguments."""

    parser = argparse.ArgumentParser(
        description="Post one CLI hook payload to the observation collector.",
    )
    parser.add_argument("--collector-url", default="", help="collector hook endpoint")
    parser.add_argument("--store", type=Path, default=None, help="hook artifact directory")
    parser.add_argument("--generation", type=int, default=0, help="channel generation")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="collector request timeout in seconds",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Emit one hook event; return 0 on every outcome."""

    try:
        args = _build_parser().parse_args(argv)
    except SystemExit:
        return 0
    _redirect_stderr(args.store)
    _silence_stdout()

    payload = _read_provider_event()
    token = os.environ.get(ENV_TOKEN, "")
    delivered = False
    if args.collector_url and token:
        delivered = _post(args.collector_url, token, payload, float(args.timeout))
    elif not args.collector_url:
        print(
            "emitter: collector url is not configured; using file fallback",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            f"emitter: ${ENV_TOKEN} is not set; using file fallback",
            file=sys.stderr,
            flush=True,
        )
    if delivered:
        print(
            f"emitter: event={_event_name(payload)} outcome=delivered",
            file=sys.stderr,
            flush=True,
        )
        return 0
    if args.store is None:
        print(
            f"emitter: event={_event_name(payload)} outcome=dropped",
            file=sys.stderr,
            flush=True,
        )
        return 0
    _append_fallback(args.store, payload, int(args.generation))
    return 0


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        try:
            print(f"emitter: fatal error={exc!r}", file=sys.stderr, flush=True)
        except Exception:
            pass
    raise SystemExit(0)
