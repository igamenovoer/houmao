#!/usr/bin/env python3
"""Measure bounded readonly observation against one explicitly selected Stalwart account."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import resource
import sys
from time import monotonic, sleep
from typing import Any
from unittest.mock import patch
from urllib import request

from houmao.mailbox.stalwart import StalwartError, StalwartJmapClient
from houmao.mailbox.stalwart_models import JmapMetadataQuery
from houmao.mailbox.sync import SyncBudget, SyncObserver, SyncScope


@dataclass
class _Traffic:
    """Counts only, with no retained HTTP headers, URLs, or message payloads."""

    http_requests: int = 0
    request_body_bytes: int = 0
    response_body_bytes_read: int = 0


class _Response:
    """Count actual response bytes read without retaining or logging the bytes."""

    def __init__(self, response: Any, traffic: _Traffic) -> None:
        self.m_response: Any = response
        self.m_traffic: _Traffic = traffic

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        """Read the same finite provider payload and discard counted byte contents."""
        data: bytes = self.m_response.read(*args, **kwargs)
        self.m_traffic.response_body_bytes_read += len(data)
        return data

    def __enter__(self) -> _Response:
        """Preserve the underlying HTTP resource's context boundary."""
        self.m_response.__enter__()
        return self

    def __exit__(self, *args: Any) -> Any:
        """Close the provider response on success or failure."""
        return self.m_response.__exit__(*args)


def _parser() -> argparse.ArgumentParser:
    """Require explicit private inputs and a finite small-workload selection."""
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("discovery-url", "login", "address", "agent-id", "binding-id", "service-release"):
        parser.add_argument("--" + flag, required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("any_inbox", "unread_only"), default="any_inbox")
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--interval-seconds", type=float, default=0.1)
    parser.add_argument("--declared-retained-messages", type=int)
    parser.add_argument("--declared-active-inbox-messages", type=int)
    return parser


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    """Measure actual readonly cycles while keeping cache/configuration external."""
    if not 1 <= args.cycles <= 100:
        raise ValueError("cycles must be between 1 and 100")
    if not math.isfinite(args.interval_seconds) or not 0 <= args.interval_seconds <= 60:
        raise ValueError("interval must be finite and between 0 and 60 seconds")
    root = Path(__file__).resolve().parents[3]
    for path in (args.work_dir, args.credential_file):
        if path.resolve().is_relative_to(root):
            raise ValueError("private qualification inputs and runs must be outside the checkout")
    args.work_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.work_dir.chmod(0o700)
    traffic = _Traffic()
    original_open = request.OpenerDirector.open

    def counted_open(opener: Any, req: Any, *call_args: Any, **kwargs: Any) -> _Response:
        """Instrument this isolated process, counting bytes without inspecting headers."""
        traffic.http_requests += 1
        data = getattr(req, "data", None)
        traffic.request_body_bytes += len(data) if data is not None else 0
        return _Response(original_open(opener, req, *call_args, **kwargs), traffic)

    def commit(callback: Callable[[], None]) -> bool:
        """Write disposable private qualification state, not a runtime binding."""
        callback()
        return True

    started = monotonic()
    with patch.object(request.OpenerDirector, "open", counted_open):
        client = StalwartJmapClient(
            jmap_url=args.discovery_url,
            login_identity=args.login,
            credential_file=args.credential_file,
            sender_address=args.address,
        )
        binding = client.validate_binding()
        initialization_methods = client.method_call_count
        query = JmapMetadataQuery(
            read_state="unread" if args.mode == "unread_only" else "any", archived=False
        )
        observer = SyncObserver.from_config(
            sqlite_path=args.work_dir / "observation.sqlite",
            client=client,
            scope=SyncScope.for_query(
                agent_id=args.agent_id,
                binding_id=args.binding_id,
                account_id=binding.account_id,
                query=query,
                client=client,
            ),
            commit_guard=commit,
        )
        cycles = []
        first_idle: float | None = None
        for index in range(args.cycles):
            before = monotonic()
            view = observer.observe(query, SyncBudget())
            duration = monotonic() - before
            cycles.append(
                {
                    "cycle": index + 1,
                    "seconds": round(duration, 6),
                    "method_calls": view.method_calls,
                    "phase": view.phase,
                    "cached_count": len(view.messages),
                    "complete": view.complete,
                    "has_more": view.has_more,
                    "budget_limited": view.budget_limited,
                    "error_code": view.error_code,
                }
            )
            if first_idle is None and view.phase == "idle":
                first_idle = monotonic() - started
            if index + 1 < args.cycles and args.interval_seconds:
                sleep(args.interval_seconds)
    durations = sorted(float(cycle["seconds"]) for cycle in cycles)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report: dict[str, Any] = {
        "schema_version": 1,
        "qualified_at_utc": datetime.now(UTC).isoformat(),
        "service_release": args.service_release,
        "accounts_tested": 1,
        "declared_retained_messages": args.declared_retained_messages,
        "declared_active_inbox_messages": args.declared_active_inbox_messages,
        "scope": "representative readonly observation; declared corpus sizes are not counted by a scan",
        "traffic": asdict(traffic),
        "traffic_limits": "payload bytes only; excludes HTTP headers, TLS framing, and unread error bodies",
        "initialization_method_calls": initialization_methods,
        "observation_method_calls": sum(int(cycle["method_calls"]) for cycle in cycles),
        "cycle_latency_p50_seconds": durations[max(0, math.ceil(len(durations) * 0.50) - 1)],
        "cycle_latency_p95_seconds": durations[max(0, math.ceil(len(durations) * 0.95) - 1)],
        "process_peak_rss_bytes": rss if sys.platform == "darwin" else rss * 1024,
        "time_to_first_idle_seconds": round(first_idle, 6) if first_idle is not None else None,
        "reminder_count": None,
        "reminder_measurement": "not measured: this runner has no gateway scheduler or body",
        "cycles": cycles,
        "success": all(cycle["error_code"] is None for cycle in cycles),
    }
    (args.work_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    """Print sanitized counts and never provider error bodies or credential data."""
    args = _parser().parse_args()
    try:
        report = qualify(args)
    except (StalwartError, OSError, ValueError):
        print(json.dumps({"success": False, "error": "selected_account_qualification_failed"}))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
