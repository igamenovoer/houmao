"""AG-UI smoke probe for the single-agent headless gateway demo."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, cast
from urllib import request
from urllib.error import HTTPError, URLError

from .models import DemoPaths, DemoState, utc_now_iso, write_json
from .runtime import DemoRuntimeError

_REQUEST_TIMEOUT_SECONDS = 180.0
_QUEUE_POLL_INTERVAL_SECONDS = 1.0
_NO_PROXY_OPENER = request.build_opener(request.ProxyHandler({}))


@dataclass(frozen=True)
class _GatewayRequestState:
    """Queue state for one AG-UI smoke request."""

    request_id: str
    state: str
    accepted_at_utc: str
    started_at_utc: str | None
    finished_at_utc: str | None
    error_detail: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-safe evidence payload."""

        return {
            "request_id": self.request_id,
            "state": self.state,
            "accepted_at_utc": self.accepted_at_utc,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "error_detail": self.error_detail,
        }


def run_ag_ui_smoke(
    *,
    paths: DemoPaths,
    state: DemoState,
    prompt: str | None = None,
    abort_after_run_start: bool = False,
    timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Post one AG-UI run to the live gateway and write smoke evidence."""

    run_id = f"agui-smoke-{int(time.time())}"
    endpoint = _gateway_url(state=state, path="/v1/ag-ui/runs")
    payload = _run_payload(
        run_id=run_id,
        prompt=prompt
        or f"Reply with exactly this text and no extra words: AG-UI text smoke {run_id}",
    )
    interrupt_count_before = _request_kind_count(state.gateway_root, "interrupt")
    status_code, content_type, event_payloads = _post_ag_ui_run(
        endpoint=endpoint,
        payload=payload,
        abort_after_run_start=abort_after_run_start,
        timeout_seconds=timeout_seconds,
    )
    request_state = _wait_for_gateway_request(
        gateway_root=state.gateway_root,
        run_id=run_id,
        require_terminal=not abort_after_run_start,
        timeout_seconds=timeout_seconds,
    )
    gateway_status_after = _get_json(_gateway_url(state=state, path="/v1/status"))
    interrupt_count_after = _request_kind_count(state.gateway_root, "interrupt")
    event_types = [str(event.get("type")) for event in event_payloads]
    terminal_events = [event for event in event_types if event in {"RUN_FINISHED", "RUN_ERROR"}]
    text_output = "".join(
        str(event.get("delta", ""))
        for event in event_payloads
        if event.get("type") == "TEXT_MESSAGE_CONTENT"
    )
    evidence = {
        "schema_version": 1,
        "created_at_utc": utc_now_iso(),
        "endpoint": endpoint,
        "run_id": run_id,
        "abort_after_run_start": abort_after_run_start,
        "status_code": status_code,
        "content_type": content_type,
        "event_types": event_types,
        "terminal_event_count": len(terminal_events),
        "text_output": text_output,
        "gateway_request": request_state.to_payload(),
        "gateway_status_after": gateway_status_after,
        "interrupt_request_count_before": interrupt_count_before,
        "interrupt_request_count_after": interrupt_count_after,
        "cleanup_evidence": {
            "demo_state_active": state.active,
            "gateway_health_after": gateway_status_after.get("gateway_health"),
            "request_admission_after": gateway_status_after.get("request_admission"),
        },
    }
    evidence_path = paths.evidence_dir / f"ag-ui-smoke-{run_id}.json"
    write_json(evidence_path, evidence)
    _validate_smoke_evidence(
        evidence=evidence,
        abort_after_run_start=abort_after_run_start,
    )
    return {
        "status": "ok",
        "evidence_path": str(evidence_path),
        "run_id": run_id,
        "event_types": event_types,
        "gateway_request": request_state.to_payload(),
    }


def _gateway_url(*, state: DemoState, path: str) -> str:
    """Return one live gateway URL for the persisted demo state."""

    host = "127.0.0.1" if state.gateway_host == "0.0.0.0" else state.gateway_host
    return f"http://{host}:{state.gateway_port}{path}"


def _run_payload(*, run_id: str, prompt: str) -> dict[str, Any]:
    """Return one AG-UI RunAgentInput payload."""

    return {
        "threadId": "single-agent-gateway-wakeup-headless-ag-ui-smoke",
        "runId": run_id,
        "state": {},
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "content": prompt,
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }


def _post_ag_ui_run(
    *,
    endpoint: str,
    payload: dict[str, Any],
    abort_after_run_start: bool,
    timeout_seconds: float,
) -> tuple[int, str, list[dict[str, Any]]]:
    """Post one AG-UI run and collect SSE payloads."""

    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _NO_PROXY_OPENER.open(http_request, timeout=timeout_seconds) as response:
            status_code = int(response.status)
            content_type = response.headers.get("content-type", "")
            if abort_after_run_start:
                return (
                    status_code,
                    content_type,
                    _read_until_run_started(response),
                )
            response_text = response.read().decode("utf-8")
            return status_code, content_type, _payloads_from_sse(response_text)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DemoRuntimeError(f"AG-UI smoke HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise DemoRuntimeError(f"AG-UI smoke could not reach `{endpoint}`: {exc}") from exc


def _read_until_run_started(response: Any) -> list[dict[str, Any]]:
    """Read SSE frames until `RUN_STARTED`, then close the stream."""

    payloads: list[dict[str, Any]] = []
    frame_lines: list[str] = []
    for raw_line in response:
        line = raw_line.decode("utf-8")
        if line in {"\n", "\r\n"}:
            frame = "".join(frame_lines)
            frame_lines = []
            payloads.extend(_payloads_from_sse(frame + "\n\n"))
            if any(payload.get("type") == "RUN_STARTED" for payload in payloads):
                return payloads
            continue
        frame_lines.append(line)
    return payloads


def _payloads_from_sse(response_text: str) -> list[dict[str, Any]]:
    """Parse AG-UI SSE data frames."""

    payloads: list[dict[str, Any]] = []
    for frame in response_text.split("\n\n"):
        if not frame.startswith("data: "):
            continue
        payloads.append(cast(dict[str, Any], json.loads(frame.removeprefix("data: "))))
    return payloads


def _get_json(url: str) -> dict[str, Any]:
    """GET one JSON payload with proxy bypass for loopback gateway calls."""

    try:
        with _NO_PROXY_OPENER.open(url, timeout=30.0) as response:
            return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))
    except URLError as exc:
        raise DemoRuntimeError(f"AG-UI smoke could not read `{url}`: {exc}") from exc


def _wait_for_gateway_request(
    *,
    gateway_root: Path,
    run_id: str,
    require_terminal: bool,
    timeout_seconds: float,
) -> _GatewayRequestState:
    """Wait for the queue row belonging to one AG-UI run id."""

    deadline = time.monotonic() + timeout_seconds
    last_state: _GatewayRequestState | None = None
    while time.monotonic() < deadline:
        last_state = _find_gateway_request(gateway_root=gateway_root, run_id=run_id)
        if last_state is None:
            time.sleep(_QUEUE_POLL_INTERVAL_SECONDS)
            continue
        if not require_terminal or last_state.state in {"completed", "failed", "coalesced"}:
            return last_state
        time.sleep(_QUEUE_POLL_INTERVAL_SECONDS)
    if last_state is not None:
        return last_state
    raise DemoRuntimeError(f"AG-UI smoke did not find gateway request for run_id={run_id!r}.")


def _find_gateway_request(*, gateway_root: Path, run_id: str) -> _GatewayRequestState | None:
    """Return the queued gateway request for one AG-UI run id when present."""

    with sqlite3.connect(gateway_root / "queue.sqlite") as connection:
        rows = connection.execute(
            """
            SELECT request_id, payload_json, state, accepted_at_utc, started_at_utc,
                   finished_at_utc, error_detail
            FROM gateway_requests
            WHERE request_kind = 'submit_prompt'
            ORDER BY accepted_at_utc DESC
            """
        ).fetchall()
    for row in rows:
        payload = json.loads(str(row[1]))
        if payload.get("turn_id") != run_id:
            continue
        return _GatewayRequestState(
            request_id=str(row[0]),
            state=str(row[2]),
            accepted_at_utc=str(row[3]),
            started_at_utc=_optional_text(row[4]),
            finished_at_utc=_optional_text(row[5]),
            error_detail=_optional_text(row[6]),
        )
    return None


def _request_kind_count(gateway_root: Path, request_kind: str) -> int:
    """Return the number of queued gateway requests of one kind."""

    with sqlite3.connect(gateway_root / "queue.sqlite") as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM gateway_requests
            WHERE request_kind = ?
            """,
            (request_kind,),
        ).fetchone()
    return 0 if row is None else int(row[0])


def _optional_text(value: object) -> str | None:
    """Return one text value when present."""

    if value is None:
        return None
    return str(value)


def _validate_smoke_evidence(
    *,
    evidence: dict[str, Any],
    abort_after_run_start: bool,
) -> None:
    """Validate live AG-UI smoke evidence and fail clearly."""

    if evidence["status_code"] != 200:
        raise DemoRuntimeError(f"AG-UI smoke returned HTTP {evidence['status_code']}.")
    if not str(evidence["content_type"]).startswith("text/event-stream"):
        raise DemoRuntimeError(
            f"AG-UI smoke returned non-SSE content type {evidence['content_type']!r}."
        )
    event_types = cast(list[str], evidence["event_types"])
    if "RUN_STARTED" not in event_types:
        raise DemoRuntimeError("AG-UI smoke did not observe RUN_STARTED.")
    if evidence["interrupt_request_count_after"] != evidence["interrupt_request_count_before"]:
        raise DemoRuntimeError("AG-UI smoke stream detach enqueued an interrupt request.")
    if abort_after_run_start:
        return
    if evidence["terminal_event_count"] != 1:
        raise DemoRuntimeError("AG-UI smoke did not observe exactly one terminal event.")
    if "RUN_FINISHED" not in event_types:
        raise DemoRuntimeError("AG-UI smoke did not observe RUN_FINISHED.")
    if not str(evidence["text_output"]).strip():
        raise DemoRuntimeError("AG-UI smoke did not observe mapped text output.")
