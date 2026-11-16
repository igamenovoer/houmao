"""Keep native CCCC attachment independent of persisted Houmao email identity.

These checks use a real gateway runtime and the explicitly selected compatible
CCCC service. The managed session has deterministic body metadata; no model
client, Stalwart service, or body-dispatch stand-in is needed for attachment.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
import uuid

import httpx
import pytest

from houmao.agents.realm_controller.gateway_models import GatewayDesiredConfigV1
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.gateway_storage import write_gateway_desired_config
from houmao.agents.realm_controller.manifest import default_manifest_path, load_session_manifest
from houmao.gateway.plugins import (
    GatewayPluginConfiguration,
    PluginCredentialReference,
    PluginInstanceConfiguration,
)
from houmao.gateway.plugins.discovery import LoadedPluginDefinition
from tests.integration.cccc.test_receiver_provider import _result, _rpc, actors as actors
from tests.unit.agents.realm_controller.test_gateway_dual_mail import _runtime


@pytest.fixture
def cccc_package(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Load optional source for runtime integration, separately from wheel qualification."""

    source = Path(__file__).resolve().parents[3] / "packages/houmao-cccc/src"
    monkeypatch.syspath_prepend(str(source))
    return importlib.import_module("houmao_cccc")


def _registrations(session: Path) -> list[tuple[Any, ...]]:
    """Capture actual offline registration ownership without copying credential content."""

    database = session / "mailbox/index.sqlite"
    if not database.is_file():
        return []
    with sqlite3.connect(database) as connection:
        return connection.execute(
            "SELECT * FROM mailbox_registrations ORDER BY registration_id"
        ).fetchall()


@pytest.mark.parametrize("dual_mail", [True, False])
def test_actual_cccc_attachment_preserves_email_bindings_and_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cccc_package: Any,
    actors: tuple[Any, ...],
    dual_mail: bool,
) -> None:
    """Attach, refresh, reconnect, and remove CCCC without touching either email slot."""

    import houmao.agents.realm_controller.gateway_plugin_host as host_module

    provider, group_id, grants = actors
    endpoint = str(provider.base_url).rstrip("/")
    session = tmp_path / "managed-session"
    session.mkdir()
    runtime = _runtime(session, monkeypatch, dual=dual_mail, enabled=dual_mail)
    manifest = default_manifest_path(session, "cao_rest", "cao-rest-1")
    original_manifest = manifest.read_bytes()
    owner = load_session_manifest(manifest).payload["agent_id"]
    original_mail = runtime.get_mail_status().model_dump(mode="json")
    registrations = _registrations(session)
    if dual_mail:
        assert original_mail["offline"] is not None and original_mail["online"] is not None
        assert original_mail["offline"]["available"]
        assert original_mail["canonical_mail_identity"]["channel"] == "online"
        assert registrations
    else:
        assert original_mail["offline"] is None and original_mail["online"] is None
        assert original_mail["canonical_mail_identity"] is None

    grant = grants[0]
    selected = tmp_path / "selected-actor.json"
    selected.write_text(
        json.dumps(
            {
                "agent_id": owner,
                "endpoint": endpoint,
                "group_id": group_id,
                "actor_id": "sender",
                "actor_generation": grant["actor_generation"],
                "token": grant["token"],
            }
        )
    )
    selected.chmod(0o600)
    configuration = GatewayPluginConfiguration(
        plugins={
            "team": PluginInstanceConfiguration(
                implementation="cccc",
                credential_ref=PluginCredentialReference(file=selected),
                config={
                    "endpoint": endpoint,
                    "group_id": group_id,
                    "actor_id": "sender",
                    "actor_generation": grant["actor_generation"],
                    "reconnect_delay_seconds": 0.05,
                    "poll_timeout_seconds": 0.1,
                },
            )
        }
    )
    write_gateway_desired_config(
        runtime.m_paths.desired_config_path,
        GatewayDesiredConfigV1(desired_plugins=configuration),
    )
    monkeypatch.setattr(
        host_module,
        "load_plugin_definition",
        lambda _name: LoadedPluginDefinition(
            definition=cccc_package.definition,
            distribution="houmao-cccc",
            distribution_version="0.1.0",
        ),
    )

    async def exercise() -> None:
        """Drive actual HTTP routes while the plugin talks to the selected native service."""

        app = create_app(runtime=runtime)
        await runtime.start_plugins()
        assert runtime.m_plugin_host is not None
        host = runtime.m_plugin_host

        async def connected() -> None:
            """Bound each actual service negotiation independently of core health."""

            async with asyncio.timeout(10):
                while True:
                    status = host.status_for("team")
                    assert status is not None
                    assert status.lifecycle != "failed", status.error_code
                    if status.connection == "connected":
                        return
                    await asyncio.sleep(0.02)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:43123"
        ) as http:
            try:
                await connected()
                binding = (await http.get("/v1/plugins/team/binding")).json()["binding_id"]
                members = await http.get("/v1/plugins/team/members")
                assert members.status_code == 200
                assert {member["id"] for member in members.json()["members"]} == {
                    "sender",
                    "receiver",
                }
                sent = await http.post(
                    "/v1/plugins/team/chat/send",
                    json={
                        "expected_binding_id": binding,
                        "operation_id": uuid.uuid4().hex,
                        "to": ["receiver"],
                        "text": "CCCC-only identity coexistence check",
                    },
                )
                assert sent.status_code == 200
                for operation in ("reconnect", "refresh-credentials", "disconnect", "connect"):
                    if operation == "refresh-credentials":
                        rotated = _result(
                            provider.post(
                                "/api/v1/external-receiver/v1/grants",
                                json={"group_id": group_id, "actor_id": "sender"},
                            )
                        )
                        revoked = provider.delete(
                            "/api/v1/external-receiver/v1/grants/" + grant["grant_id"]
                        )
                        assert revoked.status_code == 200
                        private_document = json.loads(selected.read_text())
                        private_document["token"] = rotated["token"]
                        selected.write_text(json.dumps(private_document))
                    response = await http.post(
                        f"/v1/plugins/team/connection/{operation}",
                        json={"expected_binding_id": binding},
                    )
                    assert response.status_code == 200
                    if operation != "disconnect":
                        await connected()
                    else:
                        assert host.status_for("team").connection == "disconnected"
                        if dual_mail:
                            listed = await http.post(
                                "/v1/mail/offline/list",
                                json={
                                    "expected_binding_id": original_mail["offline"]["binding_id"]
                                },
                            )
                            assert listed.status_code == 200
                    assert (await http.get("/health")).status_code == 200
                    assert (await http.get("/v1/mail/status")).json() == original_mail
                    assert manifest.read_bytes() == original_manifest
                    assert _registrations(session) == registrations
            finally:
                await runtime.stop_plugins()
        assert runtime.get_mail_status().model_dump(mode="json") == original_mail
        assert manifest.read_bytes() == original_manifest
        assert _registrations(session) == registrations

    asyncio.run(exercise())
    # Removing the selection affects the next gateway only, never the managed session.
    write_gateway_desired_config(runtime.m_paths.desired_config_path, GatewayDesiredConfigV1())
    replacement = GatewayServiceRuntime.from_gateway_root(
        gateway_root=runtime.m_paths.gateway_root, host="127.0.0.1", port=43123
    )
    create_app(runtime=replacement)
    assert replacement.m_plugin_host is not None
    assert replacement.m_plugin_host.status() == []
    assert manifest.read_bytes() == original_manifest
    assert replacement.get_mail_status().model_dump(mode="json") == original_mail
    assert _registrations(session) == registrations


def test_actual_transport_rejects_untrusted_tls(cccc_package: Any, tmp_path: Path) -> None:
    """Perform a real TLS handshake and refuse a server certificate outside the trust store."""

    executable = shutil.which("openssl")
    assert executable, "Actual TLS qualification requires openssl"
    certificate, key = tmp_path / "server.crt", tmp_path / "server.key"
    generated = subprocess.run(
        [
            executable,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        capture_output=True,
        check=False,
    )
    assert generated.returncode == 0, "Could not prepare an isolated test certificate"
    key.chmod(0o600)
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        """Record whether application bytes pass the rejected TLS boundary."""

        def do_POST(self) -> None:
            """Record unexpected credential-bearing HTTP and close immediately."""

            requests.append(self.path)
            self.send_response(500)
            self.end_headers()

        def log_message(self, _format: str, *args: object) -> None:
            """Keep synthetic TLS fixture diagnostics out of ordinary output."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(certificate, key)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def exercise() -> None:
        """Use the plugin's actual transport defaults without an injected trust override."""

        implementation = importlib.import_module("houmao_cccc.client")
        config = cccc_package.CcccConfiguration(
            endpoint=f"https://127.0.0.1:{server.server_port}",
            group_id="tls-test",
            actor_id="tls-test",
            actor_generation="tls-test",
            request_timeout_seconds=2.0,
        )
        client = implementation.ProviderClient.from_config(config, "synthetic-test-grant")
        try:
            with pytest.raises(implementation.ProviderError) as error:
                await client.request("binding", {})
            assert error.value.code == "provider_unavailable"
            assert error.value.outcome == "not_sent"
            assert requests == []
            assert "certificate" not in str(error.value).lower()
            assert "synthetic-test-grant" not in str(error.value)
        finally:
            await client.aclose()

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_actual_history_gap_is_explicit_and_reconciliation_is_bounded(
    actors: tuple[Any, ...],
) -> None:
    """A missing native history anchor fails explicitly and a fresh bounded page recovers."""

    provider, _group, grants = actors
    sender = grants[0]
    for index in range(3):
        _result(
            _rpc(
                provider,
                sender,
                "chat.send",
                {
                    "operation_id": uuid.uuid4().hex,
                    "to": ["receiver"],
                    "text": f"retained-{index}",
                    "mode": "send",
                },
            )
        )
    gap = _rpc(provider, sender, "chat.history", {"limit": 1, "before_event_id": "missing"})
    assert gap.status_code == 404
    assert gap.json()["error"]["code"] == "event_not_found"
    page = _result(_rpc(provider, sender, "chat.history", {"limit": 1}))
    assert len(page["messages"]) == 1 and page["has_more"]
    older = _result(
        _rpc(
            provider,
            sender,
            "chat.history",
            {"limit": 1, "before_event_id": page["messages"][0]["id"]},
        )
    )
    assert len(older["messages"]) == 1
    assert older["messages"][0]["id"] != page["messages"][0]["id"]
    byte_limit = _rpc(provider, sender, "chat.history", {"limit": 1, "max_bytes": 1})
    assert byte_limit.status_code == 422
    assert byte_limit.json()["error"]["code"] == "content_limit"


def test_actual_lost_send_response_requires_explicit_operation_reconciliation(
    actors: tuple[Any, ...], cccc_package: Any
) -> None:
    """Lose one actual stored-send response and reconcile without another delivery attempt."""

    provider, group_id, grants = actors
    sender = grants[0]
    endpoint = str(provider.base_url).rstrip("/")
    forwarded: list[str] = []
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        """Forward authenticated Actor RPC and drop exactly the first send response."""

        def do_POST(self) -> None:
            """Wait for actual provider storage before terminating the response socket."""

            body = self.rfile.read(int(self.headers["Content-Length"]))
            operation = json.loads(body)["operation"]
            requests.append(operation)
            response = httpx.post(
                endpoint + "/api/v1/external-receiver/v1/rpc",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self.headers["Authorization"],
                },
                timeout=5,
                trust_env=False,
            )
            if operation == "chat.send":
                result = _result(response)
                forwarded.append(result["event"]["id"])
                if len(forwarded) == 1:
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response.content)))
            self.end_headers()
            self.wfile.write(response.content)

        def log_message(self, _format: str, *args: object) -> None:
            """Keep credential-bearing proxy diagnostics private."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def exercise() -> None:
        """Reuse the original caller operation only after the first call reports unknown."""

        implementation = importlib.import_module("houmao_cccc.client")
        config = cccc_package.CcccConfiguration(
            endpoint=f"http://127.0.0.1:{server.server_port}",
            group_id=group_id,
            actor_id="sender",
            actor_generation=sender["actor_generation"],
            request_timeout_seconds=3.0,
        )
        client = implementation.ProviderClient.from_config(config, sender["token"])
        operation_id = uuid.uuid4().hex
        original = {
            "operation_id": operation_id,
            "to": ["receiver"],
            "text": "synthetic lost-response reconciliation",
            "mode": "send",
        }
        try:
            with pytest.raises(implementation.ProviderError) as error:
                await client.request("chat.send", original)
            assert error.value.outcome == "unknown"
            assert error.value.code == "provider_unavailable"
            assert original["operation_id"] == operation_id
            assert requests == ["chat.send"]
            assert len(forwarded) == 1
            recovered = await client.request("chat.send", original)
            assert recovered["duplicate"] is True
            assert recovered["event"]["id"] == forwarded[0]
            assert requests == ["chat.send", "chat.send"]
            assert forwarded == [forwarded[0], forwarded[0]]
            history = await client.request("chat.history", {"limit": 100})
            assert len(history["messages"]) == 1
            assert history["messages"][0]["id"] == forwarded[0]
            receipts = await client.request(
                "chat.deliveries", {"event_id": forwarded[0], "limit": 100}
            )
            assert len(receipts["deliveries"]) == 1
        finally:
            await client.aclose()

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_stock_service_cannot_negotiate_receiver_protocol(cccc_package: Any) -> None:
    """Inspect the actual unextended service without modifying or restarting it."""

    endpoint = os.environ.get("HOUMAO_CCCC_STOCK_TEST_URL")
    assert endpoint, "Stock negative control requires HOUMAO_CCCC_STOCK_TEST_URL"
    assert endpoint.startswith("http://127.0.0.1:"), "Select the local reference service"
    # Stock Web authentication can mask missing routes from ordinary Actor grants.
    # A loopback operator-origin request confirms the interface itself is absent.
    response = httpx.post(
        endpoint + "/api/v1/external-receiver/v1/rpc",
        headers={"Origin": endpoint, "Referer": endpoint + "/"},
        json={"operation": "binding", "arguments": {}},
        trust_env=False,
        timeout=3,
    )
    assert response.status_code == 404

    async def exercise() -> None:
        """A normal plugin request cannot mistake stock authentication for compatibility."""

        implementation = importlib.import_module("houmao_cccc.client")
        config = cccc_package.CcccConfiguration(
            endpoint=endpoint,
            group_id="unprovisioned-negative-control",
            actor_id="unprovisioned-negative-control",
            actor_generation="unprovisioned-negative-control",
            request_timeout_seconds=3.0,
        )
        client = implementation.ProviderClient.from_config(config, "synthetic-stock-negative")
        try:
            with pytest.raises(implementation.ProviderError) as error:
                await client.request("binding", {})
            assert error.value.outcome == "not_sent"
            assert error.value.status_code in {401, 403, 404, 503}
        finally:
            await client.aclose()

    asyncio.run(exercise())
