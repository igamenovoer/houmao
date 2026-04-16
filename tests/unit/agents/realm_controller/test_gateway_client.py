"""Tests for live gateway HTTP client behavior."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

from houmao.agents.realm_controller.gateway_client import (
    GATEWAY_RESPECT_PROXY_ENV_VAR,
    GatewayClient,
    GatewayEndpoint,
    gateway_client_respects_proxy_env,
)

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)


class _HealthHandler(BaseHTTPRequestHandler):
    """Serve a minimal gateway health endpoint."""

    def do_GET(self) -> None:
        """Return the gateway health payload."""

        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {"protocol_version": "v1", "status": "ok"}
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        """Suppress noisy test-server logs."""


class _ProxyHealthHandler(BaseHTTPRequestHandler):
    """Serve gateway health from an HTTP proxy test double."""

    paths: list[str] = []

    def do_GET(self) -> None:
        """Return a valid gateway health payload and capture the proxy request path."""

        self.__class__.paths.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {"protocol_version": "v1", "status": "ok"}
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        """Suppress noisy test-server logs."""


def test_gateway_client_respects_proxy_env_only_for_one() -> None:
    """Gateway proxy handling is enabled only by the exact opt-in value."""

    assert gateway_client_respects_proxy_env({}) is False
    assert gateway_client_respects_proxy_env({GATEWAY_RESPECT_PROXY_ENV_VAR: ""}) is False
    assert gateway_client_respects_proxy_env({GATEWAY_RESPECT_PROXY_ENV_VAR: "true"}) is False
    assert gateway_client_respects_proxy_env({GATEWAY_RESPECT_PROXY_ENV_VAR: "1"}) is True


def test_gateway_client_bypasses_environment_proxy_for_loopback(
    monkeypatch,
) -> None:
    """Gateway health checks must connect directly to the loopback listener."""

    for key in _PROXY_ENV_KEYS:
        monkeypatch.setenv(key, "http://127.0.0.1:9")
    monkeypatch.delenv(GATEWAY_RESPECT_PROXY_ENV_VAR, raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = GatewayClient(
            endpoint=GatewayEndpoint(host="127.0.0.1", port=server.server_port),
            timeout_seconds=0.5,
        )

        health = client.health()
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()

    assert health.status == "ok"
    assert health.protocol_version == "v1"
    assert os.environ.get("NO_PROXY") is None
    assert os.environ.get("no_proxy") is None


def test_gateway_client_proxy_opt_in_uses_environment_proxy(
    monkeypatch,
) -> None:
    """Gateway proxy opt-in uses normal proxy handling from the caller environment."""

    _ProxyHealthHandler.paths = []
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), _ProxyHealthHandler)
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    proxy_url = f"http://127.0.0.1:{proxy.server_port}"
    for key in _PROXY_ENV_KEYS:
        monkeypatch.setenv(key, proxy_url)
    monkeypatch.setenv(GATEWAY_RESPECT_PROXY_ENV_VAR, "1")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)

    try:
        client = GatewayClient(
            endpoint=GatewayEndpoint(host="127.0.0.1", port=9),
            timeout_seconds=0.5,
        )

        health = client.health()
    finally:
        proxy.shutdown()
        proxy_thread.join(timeout=2.0)
        proxy.server_close()

    assert health.status == "ok"
    assert health.protocol_version == "v1"
    assert _ProxyHealthHandler.paths == ["http://127.0.0.1:9/health"]
