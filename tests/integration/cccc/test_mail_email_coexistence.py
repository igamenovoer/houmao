"""Exercise actual Stalwart and CCCC Mail through independent gateway routes.

Only the selected normal test accounts receive owned disposable messages. A
private loopback proxy models an outage without stopping the shared service.
Email turn completion is deterministic; this is separate from real-agent smoke.
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from datetime import datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit
import uuid

import httpx
import pytest

from houmao.agents.realm_controller.gateway_models import GatewayDesiredConfigV1
from houmao.agents.realm_controller.gateway_service import create_app
from houmao.agents.realm_controller.gateway_storage import (
    read_gateway_mail_notifier_record,
    read_gateway_notifier_audit_records,
    write_gateway_desired_config,
    write_gateway_mail_notifier_record,
)
from houmao.agents.realm_controller.manifest import default_manifest_path, load_session_manifest
from houmao.gateway.plugins import GatewayPluginConfiguration
from houmao.gateway.plugins.discovery import LoadedPluginDefinition
from houmao.mailbox.stalwart import StalwartJmapClient
from tests.integration.cccc.test_receiver_provider import actors as actors
from tests.unit.agents.realm_controller.test_gateway_dual_mail import _runtime
from tests.unit.agents.realm_controller import test_gateway_support as support


class _FaultProxy:
    """Forward only the explicitly selected Stalwart service and count requests."""

    def __init__(self) -> None:
        """Declare owned listener state without opening resources."""

        self.m_server: ThreadingHTTPServer | None = None
        self.m_thread: threading.Thread | None = None
        self.m_outage: threading.Event = threading.Event()
        self.m_lock: threading.Lock = threading.Lock()
        self.m_requests: int = 0
        self.m_upstream: str = ""
        self.m_drop_submission: threading.Event = threading.Event()
        self.m_submission_committed: threading.Event = threading.Event()
        self.m_dropped_submissions: int = 0

    @classmethod
    def start(cls, discovery_url: str) -> _FaultProxy:
        """Start a private proxy with discovery URLs pinned to its fault boundary."""

        proxy = cls()
        parsed = urlsplit(discovery_url)
        assert parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
        assert not parsed.username and not parsed.password
        proxy.m_upstream = f"{parsed.scheme}://{parsed.netloc}"

        class Handler(BaseHTTPRequestHandler):
            """Forward normal-account traffic without logging headers or contents."""

            def log_message(self, _format: str, *args: Any) -> None:
                """Keep authentication and native message output out of diagnostics."""

            def do_GET(self) -> None:
                """Forward non-consuming discovery and metadata operations."""

                self._forward()

            def do_POST(self) -> None:
                """Forward explicit JMAP operations while the selected service is healthy."""

                self._forward()

            def _forward(self) -> None:
                """Apply a selected outage before any request reaches Stalwart."""

                with proxy.m_lock:
                    proxy.m_requests += 1
                if proxy.m_outage.is_set():
                    self.send_response(503)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                size = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(size)
                headers = {
                    name: value
                    for name, value in self.headers.items()
                    if name.lower() in {"authorization", "content-type", "accept"}
                }
                with httpx.Client(trust_env=False, follow_redirects=False, timeout=10) as client:
                    response = client.request(
                        self.command, proxy.m_upstream + self.path, content=body, headers=headers
                    )
                    for _hop in range(5):
                        if self.command != "GET" or not response.is_redirect:
                            break
                        destination = response.url.join(response.headers["Location"])
                        assert str(destination).startswith(proxy.m_upstream + "/")
                        response = client.get(destination, headers=headers)
                content = response.content
                if self.command == "POST" and proxy.m_drop_submission.is_set():
                    request = json.loads(body)
                    if any(
                        call[0] == "EmailSubmission/set" for call in request.get("methodCalls", [])
                    ):
                        result = response.json()
                        assert any(
                            call[0] == "EmailSubmission/set" and call[1].get("created")
                            for call in result.get("methodResponses", [])
                        )
                        proxy.m_drop_submission.clear()
                        proxy.m_submission_committed.set()
                        with proxy.m_lock:
                            proxy.m_dropped_submissions += 1
                        self.close_connection = True
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                        return
                if self.path.startswith("/.well-known/jmap") and response.status_code == 200:
                    document = response.json()
                    for field in ("apiUrl", "uploadUrl", "downloadUrl"):
                        if isinstance(document.get(field), str):
                            document[field] = proxy.base_url + urlsplit(document[field]).path
                    content = json.dumps(document).encode()
                self.send_response(response.status_code)
                self.send_header(
                    "Content-Type", response.headers.get("Content-Type", "application/json")
                )
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        proxy.m_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        proxy.m_server.daemon_threads = True
        proxy.m_thread = threading.Thread(target=proxy.m_server.serve_forever, daemon=True)
        proxy.m_thread.start()
        return proxy

    @property
    def base_url(self) -> str:
        """Return this test's explicit loopback origin."""

        assert self.m_server is not None
        return f"http://127.0.0.1:{self.m_server.server_port}"

    @property
    def requests(self) -> int:
        """Read a content-free counter under the proxy lock."""

        with self.m_lock:
            return self.m_requests

    def set_outage(self, value: bool) -> None:
        """Change only this owned fault endpoint's availability."""

        self.m_outage.set() if value else self.m_outage.clear()

    def close(self) -> None:
        """Drain only this proxy's threads and socket."""

        if self.m_server is not None:
            self.m_server.shutdown()
            self.m_server.server_close()
        if self.m_thread is not None:
            self.m_thread.join(timeout=3)
            assert not self.m_thread.is_alive()


def _account(peer: bool) -> tuple[str, str, Path]:
    """Require explicit protected normal-account input, never an administrator source."""

    prefix = "HOUMAO_CCCC_STALWART_PEER_" if peer else "HOUMAO_CCCC_STALWART_"
    login, address, credential = (
        os.environ.get(prefix + key) for key in ("LOGIN", "ADDRESS", "CREDENTIAL_FILE")
    )
    assert login and address and credential, "Select both explicit normal Stalwart test accounts"
    path = Path(credential).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[3]
    assert path.is_file() and not path.is_relative_to(checkout)
    assert path.stat().st_mode & 0o077 == 0
    return login, address, path


def test_actual_deferred_mail_survives_selected_stalwart_outage_and_preserves_reminders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, actors: tuple[Any, ...]
) -> None:
    """Exchange Mail during an isolated real-email fault without bridging either slot."""

    discovery = os.environ.get("HOUMAO_CCCC_STALWART_URL")
    assert discovery, "Select the actual Stalwart discovery URL"
    assert not tmp_path.resolve().is_relative_to(Path(__file__).resolve().parents[3])
    source = Path(__file__).resolve().parents[3] / "packages/houmao-cccc/src"
    monkeypatch.syspath_prepend(str(source))
    package = importlib.import_module("houmao_cccc")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_plugin_host.load_plugin_definition",
        lambda _name: LoadedPluginDefinition(
            definition=package.definition, distribution="houmao-cccc", distribution_version="0.2.0"
        ),
    )
    provider, group_id, grants = actors
    endpoint = str(provider.base_url).rstrip("/")
    proxy = _FaultProxy.start(discovery)
    normal_clients: list[StalwartJmapClient] = []
    owned_messages: list[str] = []
    clock = [datetime.now(timezone.utc).replace(microsecond=0)]
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.now_utc_iso", lambda: clock[0].isoformat()
    )

    async def exercise() -> None:
        """Drive two normal Actor gateways and explicit email reminder admission cycles."""

        runtimes, clients, bindings, mail_state, compacted = [], [], [], [], []
        async with AsyncExitStack() as stack:
            try:
                for index, actor_id in enumerate(("sender", "receiver")):
                    root = tmp_path / actor_id
                    root.mkdir()
                    login, address, credential = _account(bool(index))
                    normal = StalwartJmapClient(
                        jmap_url=discovery,
                        login_identity=login,
                        credential_file=credential,
                        sender_address=address,
                    )
                    normal.validate_binding()
                    fixture = normal.send(
                        sender_address=address,
                        to_addresses=[address],
                        cc_addresses=[],
                        subject="CCCC coexistence " + uuid.uuid4().hex,
                        body_content="Owned disposable email reminder work.",
                        attachments=[],
                    )
                    message_id = str(fixture["id"])
                    normal.move(message_ref=message_id, destination_box="inbox")
                    normal_clients.append(normal)
                    owned_messages.append(message_id)
                    owner = str(uuid.uuid4())
                    original_derive = support.derive_agent_id_from_name
                    monkeypatch.setattr(support, "derive_agent_id_from_name", lambda _name: owner)
                    try:
                        runtime = _runtime(root, monkeypatch, dual=False, enabled=True)
                        offline_id = support._deliver_unread_mailbox_message(
                            root, recipient_principal_id=owner
                        )
                    finally:
                        monkeypatch.setattr(support, "derive_agent_id_from_name", original_derive)
                    runtimes.append(runtime)
                    monkeypatch.setattr(
                        runtime, "_notifier_block_detail_locked", lambda **_kwargs: None
                    )
                    manifest = default_manifest_path(root, "cao_rest", "cao-rest-1")
                    assert load_session_manifest(manifest).payload["agent_id"] == owner
                    selected = tmp_path / (actor_id + "-actor.json")
                    selected.write_text(
                        json.dumps(
                            {
                                "agent_id": owner,
                                "endpoint": endpoint,
                                "group_id": group_id,
                                "actor_id": actor_id,
                                "actor_generation": grants[index]["actor_generation"],
                                "token": grants[index]["token"],
                            }
                        )
                    )
                    selected.chmod(0o600)
                    selection = GatewayPluginConfiguration.model_validate(
                        {
                            "plugins": {
                                "cccc": {
                                    "implementation": "cccc",
                                    "credential_ref": {"file": str(selected)},
                                    "config": {
                                        "endpoint": endpoint,
                                        "group_id": group_id,
                                        "actor_id": actor_id,
                                        "actor_generation": grants[index]["actor_generation"],
                                    },
                                }
                            }
                        }
                    )
                    write_gateway_desired_config(
                        runtime.m_paths.desired_config_path,
                        GatewayDesiredConfigV1(desired_plugins=selection),
                    )
                    app = create_app(runtime=runtime)
                    await runtime.start_plugins()
                    client = await stack.enter_async_context(
                        httpx.AsyncClient(
                            transport=httpx.ASGITransport(app=app),
                            base_url=f"http://127.0.0.1:{43123 + index}",
                        )
                    )
                    clients.append(client)
                    async with asyncio.timeout(30):
                        while True:
                            binding = (await client.get("/v1/plugins/cccc/binding")).json()
                            if binding.get("connection") == "connected":
                                break
                            await asyncio.sleep(0.02)
                    bindings.append(binding["binding_id"])
                    current = (await client.get("/v1/mail/online/binding")).json()
                    attached = await client.put(
                        "/v1/mail/online/binding",
                        json={
                            "expected_revision": current["revision"],
                            "jmap_url": proxy.base_url + "/.well-known/jmap",
                            "address": address,
                            "login_identity": login,
                            "credential_source_ref": str(credential),
                        },
                    )
                    assert attached.status_code == 200, "Normal Stalwart attachment failed"
                    state = (await client.get("/v1/mail/status")).json()
                    assert state["canonical_mail_identity"]["channel"] == "online"
                    assert state["offline"] and state["online"]
                    mail_state.append(state)
                    refs = []
                    for channel, native_ref in (
                        ("offline", "filesystem:" + offline_id),
                        ("online", "stalwart:" + message_id),
                    ):
                        adapter = runtime._mailbox_adapter_locked(channel=channel)
                        ref = adapter.scope.encode(native_ref)
                        enabled = await client.put(
                            f"/v1/mail-notifier/{channel}", json={"interval_seconds": 60}
                        )
                        assert enabled.status_code == 200
                        key = runtime._mail_notifier_scope_key(channel)
                        write_gateway_mail_notifier_record(
                            runtime.m_paths.queue_path,
                            scope_key=key,
                            compacted_eligible_message_refs=(ref,),
                        )
                        runtime._run_notifier_cycle(channel=channel)
                        refs.append((key, ref))
                        with sqlite3.connect(runtime.m_paths.queue_path) as connection:
                            connection.execute("UPDATE gateway_requests SET state='completed'")
                    compacted.append(refs)

                # Model genuine uncertainty after an owned email submission commits.
                # This is separate from the selected pre-request outage below.
                proxy.m_drop_submission.set()
                uncertain = await clients[0].post(
                    "/v1/mail/online/send",
                    json={
                        "expected_binding_id": mail_state[0]["online"]["binding_id"],
                        "to": [_account(False)[1]],
                        "subject": "Owned uncertain email " + uuid.uuid4().hex,
                        "body_content": "Reconcile this email; never mirror it into CCCC.",
                    },
                )
                detail = uncertain.json().get("detail", {})
                if isinstance(detail, dict) and detail.get("email_id"):
                    normal_clients.append(normal_clients[0])
                    owned_messages.append(detail["email_id"])
                assert uncertain.status_code == 502 and detail.get("outcome") == "uncertain"
                assert proxy.m_submission_committed.is_set() and proxy.m_dropped_submissions == 1
                for client in clients:
                    untouched = await client.get(
                        "/v1/plugins/cccc/chat/history", params={"limit": 1}
                    )
                    assert untouched.status_code == 200 and untouched.json()["messages"] == []

                proxy.set_outage(True)
                for client, state in zip(clients, mail_state, strict=True):
                    outage = await client.post(
                        "/v1/mail/online/list",
                        json={
                            "expected_binding_id": state["online"]["binding_id"],
                            "limit": 1,
                        },
                    )
                    assert outage.status_code == 502
                before_requests = proxy.requests
                prefix = "/v1/plugins/cccc"
                before = (await clients[1].get(prefix + "/mail/cursor")).json()
                sent = await clients[0].post(
                    prefix + "/mail/send",
                    json={
                        "expected_binding_id": bindings[0],
                        "operation_id": uuid.uuid4().hex,
                        "to": ["receiver"],
                        "text": "Deferred correspondence during selected email outage.",
                    },
                )
                assert sent.status_code == 200
                event = sent.json()["event"]
                assert event["data"]["message_mode"] == "mail"
                peek = (await clients[1].get(prefix + "/mail/peek", params={"limit": 1})).json()
                assert peek["messages"][0]["id"] == event["id"] and not peek["consumed"]
                read = await clients[1].post(
                    prefix + "/mail/read",
                    json={
                        "expected_binding_id": bindings[1],
                        "operation_id": uuid.uuid4().hex,
                        "expected_cursor": before["cursor_ref"],
                        "limit": 1,
                        "max_bytes": 262144,
                    },
                )
                assert read.status_code == 200
                batch = read.json()
                assert batch["outcome"] == "consumed" and batch["receipt"]["event_ids"] == [
                    event["id"]
                ]
                reply = await clients[1].post(
                    prefix + "/mail/reply",
                    json={
                        "expected_binding_id": bindings[1],
                        "operation_id": uuid.uuid4().hex,
                        "event_ref": batch["messages"][0]["event_ref"],
                        "text": "Deferred reply.",
                    },
                )
                assert (
                    reply.status_code == 200
                    and reply.json()["event"]["data"]["reply_to"] == event["id"]
                )
                assert proxy.requests == before_requests, "CCCC Mail contacted the email provider"
                clock[0] += timedelta(seconds=61)
                for runtime in runtimes:
                    runtime._run_notifier_cycle(channel="offline")
                    runtime._run_notifier_cycle(channel="online")
                    with sqlite3.connect(runtime.m_paths.queue_path) as connection:
                        connection.execute("UPDATE gateway_requests SET state='completed'")
                proxy.set_outage(False)
                for runtime, client, state, references in zip(
                    runtimes, clients, mail_state, compacted, strict=True
                ):
                    online_key = runtime._mail_notifier_scope_key("online")
                    async with asyncio.timeout(15):
                        while True:
                            runtime._run_notifier_cycle(channel="online")
                            observed = read_gateway_notifier_audit_records(
                                runtime.m_paths.queue_path
                            )
                            if (
                                sum(
                                    row.scope_key == online_key and row.outcome == "enqueued"
                                    for row in observed
                                )
                                == 2
                            ):
                                break
                            await asyncio.sleep(0.25)
                    now = (await client.get("/v1/mail/status")).json()
                    assert now["canonical_mail_identity"] == state["canonical_mail_identity"]
                    assert now["offline"]["binding_id"] == state["offline"]["binding_id"]
                    assert now["online"]["binding_id"] == state["online"]["binding_id"]
                    audit = read_gateway_notifier_audit_records(runtime.m_paths.queue_path)
                    for key, ref in references:
                        record = read_gateway_mail_notifier_record(
                            runtime.m_paths.queue_path, scope_key=key
                        )
                        assert record.compacted_eligible_message_refs == (ref,)
                        assert (
                            sum(row.scope_key == key and row.outcome == "enqueued" for row in audit)
                            == 2
                        )
            finally:
                for runtime in reversed(runtimes):
                    await runtime.stop_plugins()

    try:
        asyncio.run(exercise())
    finally:
        proxy.close()
        for client, message_id in zip(normal_clients, owned_messages, strict=True):
            client.archive(message_ref=message_id)
