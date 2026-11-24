"""Qualify authenticated HTTPS mail against independently owned services."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import httpx
import pytest

from houmao.agents.mailbox_runtime_models import RemoteRegistryMailboxResolvedConfig
from houmao.agents.realm_controller import gateway_access_runtime
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    mutate_session_mailbox_binding,
)
from houmao.gateway.access import GatewayAdminKey, GatewayClientBinding, public_key_text
from houmao.mailbox.models import (
    GatewayMailArchiveRequestV1,
    GatewayMailAttachmentUploadV1,
    GatewayMailListRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
)
from houmao.mailbox.online_models import OnlineAttachRequest, OnlineControlRequest
from houmao.mailbox.registry_client import OfflineRegistryClient
from houmao.mailbox.stalwart import StalwartJmapClient
from houmao.mailbox.stalwart_models import JmapMetadataQuery
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
from tests.integration.agents.realm_controller.test_gateway_https_access import (
    _AGENT,
    _PREFIX,
    _PrefixProxy,
    _certificate,
    _isolated_tmux,
    _provision_runtime,
    _serve_gateway,
    _write_private_key,
)
from tests.integration.mailbox.test_offline_registry_process import _credential, _server


@dataclass(frozen=True)
class _Gateway:
    """A deployed gateway with separately selected owner and remote callers."""

    manifest: Path
    unsigned: GatewayClient
    self_client: GatewayClient
    admin: GatewayClient


@contextmanager
def _owner_listener(
    manifest: Path,
    monkeypatch: pytest.MonkeyPatch,
    generation: str,
    mode: Literal["foreground", "detached"],
) -> Iterator[str]:
    """Start an in-process fixture or an independent production gateway companion."""

    if mode == "foreground":
        with _serve_gateway(manifest, monkeypatch, generation) as (url, _):
            yield url
        return

    gateway_root = manifest.parent / "gateway"
    with (gateway_root / "fixture-sidecar.log").open("wb") as diagnostic:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "houmao.agents.realm_controller.gateway_service",
                "--gateway-root",
                str(gateway_root),
                "--host",
                "127.0.0.1",
                "--port",
                "0",
            ],
            stdin=subprocess.DEVNULL,
            stdout=diagnostic,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                assert process.poll() is None, "Detached gateway exited during startup"
                try:
                    state = GatewayStatusV1.model_validate_json(
                        (gateway_root / "state.json").read_bytes()
                    )
                except FileNotFoundError:
                    time.sleep(0.05)
                    continue
                if state.gateway_port is not None:
                    assert state.execution_mode == "detached_process"
                    yield f"http://127.0.0.1:{state.gateway_port}"
                    return
                time.sleep(0.05)
            pytest.fail("Detached gateway did not publish a live listener")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@contextmanager
def _deployed_gateway(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: Literal["foreground", "detached"],
) -> Iterator[_Gateway]:
    """Serve the live gateway read and control routes through verified HTTPS."""

    root.mkdir(mode=0o700)
    ca_bundle, tls = _certificate(root)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(root / "config"))
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(root / "registry"))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)

    class MailProxy(_PrefixProxy):
        """Serve each fixture's bindings and requests independently."""

        forwarded_paths: list[str] = []

        def do_PUT(self) -> None:
            """Forward online mailbox attachment requests."""

            self._forward()

    with ThreadingHTTPServer(("127.0.0.1", 0), MailProxy) as proxy, _isolated_tmux(root) as tmux:
        proxy.socket = tls.wrap_socket(proxy.socket, server_side=True)
        remote_url = f"https://127.0.0.1:{proxy.server_port}{_PREFIX}"
        manifest, generation = _provision_runtime(root, tmux_socket=tmux, advertised_url=remote_url)
        with _owner_listener(manifest, monkeypatch, generation, mode) as owner_url:
            MailProxy.backend_port = int(owner_url.rsplit(":", 1)[-1])
            worker = threading.Thread(target=proxy.serve_forever, daemon=True)
            worker.start()
            try:
                unsigned = GatewayClient(base_url=remote_url, ca_bundle_path=ca_bundle)
                target = unsigned.describe_endpoint().target
                key_file = root / "remote-operator.key"
                signer = Ed25519PrivateKey.generate()
                _write_private_key(key_file, signer)
                key = GatewayAdminKey(
                    principal="mail-operator", public_key=public_key_text(signer.public_key())
                )
                enrollment = GatewayClientBinding(
                    base_url=remote_url,
                    owner=target.owner,
                    purpose="register",
                    private_key_path=str(key_file),
                    ca_bundle_path=str(ca_bundle),
                )
                first = GatewayClient(
                    binding=enrollment, registration_key=key, target_incarnation=generation
                )
                assert first.add_admin_key(key) == key.key_id
                admin = GatewayClient(
                    binding=enrollment.model_copy(update={"purpose": "caller"}),
                    target_incarnation=generation,
                )
                self_path = gateway_access_runtime.gateway_access_for_manifest(
                    manifest
                ).self_store.self_signer_path(generation)
                own = GatewayClient(
                    binding=GatewayClientBinding(
                        base_url=owner_url,
                        owner=target.owner,
                        purpose="caller",
                        private_key_path=str(self_path),
                    ),
                    target_incarnation=generation,
                )
                yield _Gateway(manifest, unsigned, own, admin)
                assert f"{_PREFIX}/v1/auth/challenge" in MailProxy.forwarded_paths
                assert f"{_PREFIX}/v1/mail/status" in MailProxy.forwarded_paths
            finally:
                proxy.shutdown()
                worker.join(timeout=5)
                assert not worker.is_alive()


def _loopback_url() -> str:
    """Select a test service address without contacting existing services."""

    with socket.socket() as selected:
        selected.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{selected.getsockname()[1]}"


@contextmanager
def _expect_http(status: int) -> Iterator[None]:
    """Expect the gateway to preserve admission or binding refusal."""

    with pytest.raises(GatewayHttpError) as error:
        yield
    assert error.value.status_code == status, error.value.detail


@pytest.mark.parametrize("mode", ["foreground", "detached"])
def test_authenticated_offline_gateway_reaches_real_remote_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: Literal["foreground", "detached"],
) -> None:
    """Sign remote calls and verify real member, binding, and attachment effects."""

    registry = tmp_path / "registry-host"
    owner = tmp_path / "agent-host"
    peer = tmp_path / "peer-host"
    admin_secret, owner_secret, peer_secret = (secrets.token_hex(32) for _ in range(3))
    admin_file = _credential(registry / "admin", admin_secret)
    owner_file = _credential(owner / "member", owner_secret)
    peer_file = _credential(peer / "member", peer_secret)
    registry_url = _loopback_url()
    config = _credential(
        registry / "service.json",
        json.dumps(
            {
                "registry_root": str(registry / "members"),
                "mailbox_root": str(registry / "messages"),
                "admin_credential_file": str(admin_file),
                "public_url": registry_url,
            }
        ),
    )
    with (
        _server(config, registry_url, registry),
        _deployed_gateway(tmp_path / "g", monkeypatch, mode) as gateway,
    ):
        registrar = OfflineRegistryClient.from_url(registry_url, admin_file)
        member = registrar.enroll(
            agent_id=_AGENT, address="worker@houmao.localhost", member_credential=owner_secret
        )
        correspondent = registrar.enroll(
            agent_id="fixture-peer", address="peer@houmao.localhost", member_credential=peer_secret
        )
        peer_client = OfflineRegistryClient.from_url(registry_url, peer_file)
        manifest = load_session_manifest(gateway.manifest).payload
        offline = manifest["launch_plan"]["mailboxes"]["offline"]
        mutate_session_mailbox_binding(
            gateway.manifest,
            channel="offline",
            expected_revision=offline["revision"],
            binding=RemoteRegistryMailboxResolvedConfig(
                transport="registry",
                agent_id=_AGENT,
                principal_id=_AGENT,
                binding_id=member.registration_id,
                address=member.address,
                bindings_version=offline["revision"],
                registry_url=registry_url,
                credential_ref=str(owner_file),
                credential_file=owner_file,
            ),
            agent_id=_AGENT,
            session_id=manifest["runtime"]["session_id"],
        )
        with _expect_http(401):
            gateway.unsigned.mail_status()
        status = gateway.admin.mail_status()
        assert status.offline is not None and status.offline.binding_id == member.registration_id
        assert gateway.self_client.mail_status().offline == status.offline
        source = owner / "owner-only.txt"
        source.write_text("Attachment from the gateway owner's filesystem.")
        request = GatewayMailSendRequestV1(
            expected_binding_id=member.registration_id,
            to=[correspondent.address],
            subject="TLS offline mail",
            body_content="Authenticated owner delivery.",
            attachments=[GatewayMailAttachmentUploadV1(path=str(source))],
        )
        with _expect_http(403):
            gateway.self_client.send_mail(request, channel="offline")
        query = GatewayMailListRequestV1(expected_binding_id=correspondent.registration_id)
        assert peer_client.mail("list", query) == []
        with _expect_http(409):
            gateway.admin.send_mail(
                request.model_copy(update={"expected_binding_id": "not-current"}), channel="offline"
            )
        sent = gateway.admin.send_mail(request, channel="offline")
        assert sent.message.sender.address == member.address
        incoming = peer_client.mail("list", query)
        assert len(incoming) == 1 and incoming[0].subject == request.subject
        assert peer_client.download(incoming[0].attachments[0].attachment_id) == source.read_bytes()
        peer_client.mail(
            "reply",
            GatewayMailReplyRequestV1(
                expected_binding_id=correspondent.registration_id,
                message_ref=incoming[0].message_ref,
                body_content="Remote reply.",
            ),
        )
        listing = gateway.admin.list_mail(
            GatewayMailListRequestV1(expected_binding_id=member.registration_id), channel="offline"
        )
        assert len(listing.messages) == 1
        read = gateway.admin.read_mail(
            GatewayMailMessageRequestV1(
                expected_binding_id=member.registration_id,
                message_ref=listing.messages[0].message_ref,
            ),
            channel="offline",
        )
        assert read.message.body_text == "Remote reply."


@dataclass(frozen=True)
class _OnlineAccount:
    """One disposable normal account and its explicitly selected source."""

    url: str
    login: str
    address: str
    source: Path

    def connect(self) -> StalwartJmapClient:
        """Use JMAP with the test account's normal provider authority."""

        return StalwartJmapClient(
            jmap_url=self.url,
            login_identity=self.login,
            sender_address=self.address,
            credential_file=self.source,
            timeout_seconds=2.0,
        )


@contextmanager
def _disposable_stalwart(
    root: Path, executable: Path
) -> Iterator[tuple[_OnlineAccount, _OnlineAccount]]:
    """Run a disposable provider and provision two normal accounts on loopback."""

    root.mkdir(mode=0o700)
    url = _loopback_url()
    port = url.rsplit(":", 1)[1]
    administrator = secrets.token_hex(32)
    config = _credential(
        root / "provider.toml",
        f'''\
server.hostname = "mail.example.com"
lookup.default.domain = "example.com"
http.url = "'{url}'"
server.listener.http.bind = ["127.0.0.1:{port}"]
server.listener.http.protocol = "http"
storage.data = "rocksdb"
storage.fts = "rocksdb"
storage.blob = "rocksdb"
storage.lookup = "rocksdb"
storage.directory = "internal"
store.rocksdb.type = "rocksdb"
store.rocksdb.path = "{root / "store"}"
directory.internal.type = "internal"
directory.internal.store = "rocksdb"
authentication.fallback-admin.user = "fixture-admin"
authentication.fallback-admin.secret = "{administrator}"
''',
    )
    process = subprocess.Popen(
        [str(executable), "--config", str(config)],
        cwd=root,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(
            base_url=url, auth=("fixture-admin", administrator), trust_env=False, timeout=2
        ) as manager:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                assert process.poll() is None, "Disposable Stalwart process exited during startup"
                try:
                    if manager.get("/api/principal?types=domain").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                pytest.fail("The disposable Stalwart management API did not become available")
            domain = manager.post("/api/principal", json={"type": "domain", "name": "example.com"})
            assert domain.status_code == 200 and "data" in domain.json()
            accounts = []
            for name in ("gateway-worker", "gateway-peer"):
                address = f"{name}@example.com"
                password = secrets.token_hex(32)
                created = manager.post(
                    "/api/principal",
                    json={
                        "type": "individual",
                        "name": name,
                        "emails": [address],
                        "secrets": [password],
                        "roles": ["user"],
                    },
                )
                assert created.status_code == 200 and "data" in created.json()
                source = _credential(root / f"{name}.json", json.dumps({"password": password}))
                accounts.append(_OnlineAccount(f"{url}/.well-known/jmap", name, address, source))
        yield accounts[0], accounts[1]
    finally:
        process.terminate()
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=4)


@pytest.mark.parametrize("mode", ["foreground", "detached"])
def test_authenticated_online_gateway_reaches_disposable_stalwart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: Literal["foreground", "detached"],
) -> None:
    """Complete signed gateway operations against a running selected Stalwart binary."""

    selected = os.environ.get("HOUMAO_TEST_STALWART_BIN")
    if selected is None:
        pytest.skip("Select an explicit disposable Stalwart binary with HOUMAO_TEST_STALWART_BIN")
    executable = Path(selected).resolve(strict=True)
    assert executable.is_file() and os.access(executable, os.X_OK)
    with (
        _disposable_stalwart(tmp_path / "provider", executable) as (owner, peer),
        _deployed_gateway(tmp_path / "g", monkeypatch, mode) as gateway,
    ):
        owner_jmap = owner.connect()
        binding = owner_jmap.validate_binding()
        if "archive" not in binding.mailbox_roles:
            result = owner_jmap.call(
                [
                    [
                        "Mailbox/set",
                        {
                            "accountId": binding.account_id,
                            "create": {"archive": {"name": "Archive", "role": "archive"}},
                        },
                        "archive",
                    ]
                ]
            )
            assert result["methodResponses"][0][0] == "Mailbox/set"
            assert "archive" in result["methodResponses"][0][1]["created"]
        peer_jmap = peer.connect()
        peer_jmap.validate_binding()
        initial = gateway.admin.online_binding_status()
        attach = OnlineAttachRequest(
            expected_revision=initial.revision,
            address=owner.address,
            login_identity=owner.login,
            credential_source_ref=str(owner.source),
            jmap_url=owner.url,
            timeout_seconds=2.0,
        )
        with _expect_http(401):
            gateway.unsigned.attach_online_binding(attach)
        with _expect_http(403):
            gateway.self_client.attach_online_binding(attach)
        current = gateway.admin.attach_online_binding(attach)
        assert current.available and current.binding_id
        assert current.account_id == binding.account_id
        status = gateway.admin.mail_status()
        assert status.online is not None and status.online.binding_id == current.binding_id
        with _expect_http(401):
            gateway.unsigned.mail_status()
        assert gateway.self_client.mail_status() == status
        outbound = GatewayMailSendRequestV1(
            expected_binding_id=current.binding_id,
            to=[peer.address],
            subject="TLS online mail",
            body_content="Fixture message over real JMAP.",
        )
        with _expect_http(409):
            gateway.admin.send_mail(
                outbound.model_copy(update={"expected_binding_id": "stale-online"}),
                channel="online",
            )
        sent = gateway.admin.send_mail(outbound, channel="online")
        assert sent.message.mutation_receipt is not None
        assert sent.message.mutation_receipt.outcome == "confirmed"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            matches = [
                item
                for item in peer_jmap.query_metadata_page(
                    query=JmapMetadataQuery(), limit=10
                ).messages
                if item.get("subject") == outbound.subject
            ]
            if matches:
                break
            time.sleep(0.1)
        else:
            pytest.fail("The selected Stalwart peer did not receive the confirmed delivery")
        assert len(matches) == 1
        peer_jmap.reply(
            message_ref=matches[0]["id"],
            body_content="Reply from the real provider.",
            sender_address=peer.address,
            attachments=[],
        )
        query = GatewayMailListRequestV1(expected_binding_id=current.binding_id)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            messages = gateway.admin.list_mail(query, channel="online").messages
            if messages:
                break
            time.sleep(0.1)
        else:
            pytest.fail("The gateway did not observe the real provider's reply")
        assert len(messages) == 1
        read = gateway.admin.read_mail(
            GatewayMailMessageRequestV1(
                expected_binding_id=current.binding_id, message_ref=messages[0].message_ref
            ),
            channel="online",
        )
        assert "Reply from the real provider." in read.message.body_text
        archived = gateway.admin.archive_mail(
            GatewayMailArchiveRequestV1(
                expected_binding_id=current.binding_id, message_refs=[messages[0].message_ref]
            ),
            channel="online",
        )
        assert all(message.archived for message in archived.messages)
        refreshed = gateway.admin.refresh_online_binding(
            OnlineControlRequest(expected_revision=current.revision, timeout_seconds=2.0)
        )
        assert refreshed.binding_id == current.binding_id and refreshed.revision != current.revision
        reconnected = gateway.admin.reconnect_online_binding(
            OnlineControlRequest(expected_revision=refreshed.revision, timeout_seconds=2.0)
        )
        assert (
            reconnected.binding_id == current.binding_id
            and reconnected.epoch_id != refreshed.epoch_id
        )
        detached = gateway.admin.detach_online_binding(
            OnlineControlRequest(expected_revision=reconnected.revision, timeout_seconds=2.0)
        )
        assert detached.state == "absent" and gateway.admin.mail_status().online is None
