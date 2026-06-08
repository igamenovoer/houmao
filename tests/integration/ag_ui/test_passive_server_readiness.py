"""Readiness contract for future passive-server AG-UI stream proxying."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _UpstreamResponse:
    """Minimal upstream response shape for passive-server readiness checks."""

    status_code: int
    content_type: str
    body: bytes


def _readiness_proxy_response(upstream: _UpstreamResponse) -> _UpstreamResponse:
    """Return the stream-preserving response a future proxy must emulate."""

    return _UpstreamResponse(
        status_code=upstream.status_code,
        content_type=upstream.content_type,
        body=upstream.body,
    )


def test_readiness_proxy_contract_preserves_sse_content_type_and_bytes() -> None:
    """Assert the future passive-server proxy target preserves AG-UI SSE bytes."""

    upstream = _UpstreamResponse(
        status_code=200,
        content_type="text/event-stream; charset=utf-8",
        body=(
            b'data: {"type":"RUN_STARTED","threadId":"thread-1","runId":"run-1"}\n\n'
            b'data: {"type":"RUN_FINISHED","threadId":"thread-1","runId":"run-1"}\n\n'
        ),
    )

    proxied = _readiness_proxy_response(upstream)

    assert proxied.status_code == 200
    assert proxied.content_type.startswith("text/event-stream")
    assert proxied.body == upstream.body


def test_readiness_proxy_contract_preserves_upstream_http_errors() -> None:
    """Assert future proxying does not turn pre-admission HTTP errors into SSE."""

    upstream = _UpstreamResponse(
        status_code=503,
        content_type="application/json",
        body=b'{"detail":"AG-UI run admission is blocked."}',
    )

    proxied = _readiness_proxy_response(upstream)

    assert proxied.status_code == 503
    assert proxied.content_type == "application/json"
    assert proxied.body == upstream.body
