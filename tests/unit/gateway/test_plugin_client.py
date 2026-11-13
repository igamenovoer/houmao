"""Typed gateway plugin client reads over actual loopback HTTP."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.gateway.plugins import GatewayPluginStatusResponse, PluginStatus


class _PluginStatusHandler(BaseHTTPRequestHandler):
    """Serve maintained host snapshots without any plugin implementation code."""

    def do_GET(self) -> None:
        """Return a known failed instance, its inventory, or an unknown-instance error."""

        status = PluginStatus(
            instance_id="events",
            implementation="external-example",
            lifecycle="failed",
            error_code="implementation_missing",
        )
        if self.path == "/v1/plugins":
            payload = GatewayPluginStatusResponse(
                configuration_digest="opaque-active-selection", plugins=[status]
            ).model_dump(mode="json")
        elif self.path == "/v1/plugins/events/_status":
            payload = status.model_dump(mode="json")
        else:
            self.send_error(404, "Unknown plugin instance")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        """Suppress test-server request logging."""


def test_plugin_client_reads_inventory_known_failure_and_unknown_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public client returns typed safe snapshots and preserves HTTP404."""

    monkeypatch.delenv("HOUMAO_GATEWAY_RESPECT_PROXY_ENV", raising=False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PluginStatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = GatewayClient(
            endpoint=GatewayEndpoint(host="127.0.0.1", port=server.server_port),
            timeout_seconds=1.0,
        )
        inventory = client.get_plugins()
        status = client.get_plugin_status("events")
        with pytest.raises(GatewayHttpError) as error:
            client.get_plugin_status("unknown")
        assert error.value.status_code == 404
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()
    assert inventory.configuration_digest == "opaque-active-selection"
    assert inventory.plugins == [status]
    assert status.lifecycle == "failed"
    assert status.error_code == "implementation_missing"
