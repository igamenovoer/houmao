"""Qualify authenticated HTTPS mail against independently owned services."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
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
from typing import Callable, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import httpx
import pytest

from houmao.agents.mailbox_runtime_models import RemoteRegistryMailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import mailboxes_resolved_config_from_payload
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_access_runtime import gateway_access_for_manifest
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import (
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitWorkRequestV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    mutate_session_mailbox_binding,
)
from houmao.gateway.access import GatewayAdminKey, GatewayClientBinding, public_key_text
from houmao.gateway.authorization_models import (
    Credential,
    DefaultFallbackRequest,
    Principal,
    ScopedGrant,
)
from houmao.gateway.operations import STATUS
from houmao.mailbox.models import (
    GatewayMailArchiveRequestV1,
    GatewayMailAttachmentUploadV1,
    GatewayMailListRequestV1,
    GatewayMailListResponseV1,
    GatewayMailMessageRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
)
from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineAuthorityContext,
    OnlineControlRequest,
)
from houmao.mailbox.policy import (
    GatewayMailPolicyRequest,
    MailPolicyReceipt,
    MailPolicyUpdate,
    sign_mail_policy_update,
)
from houmao.mailbox.registry_client import OfflineRegistryClient
from houmao.mailbox.services import build_scoped_mailbox_adapter
from houmao.mailbox.stalwart import (
    JMAP_SIEVE_CAPABILITY,
    StalwartJmapClient,
    StalwartReadinessError,
    _require_method_response,
    ensure_stalwart_mailbox,
)
from houmao.mailbox.stalwart_models import JmapMetadataQuery
from houmao.mailbox.stalwart_policy_authority import _archive_script
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
    enroll_admin: Callable[[], GatewayClient]
    public_url: str
    ca_bundle: Path


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
    *,
    keyed: bool = True,
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
                own = GatewayClient(
                    binding=GatewayClientBinding(
                        base_url=owner_url,
                        owner=target.owner,
                        purpose="caller",
                        managed_self_manifest_path=str(manifest),
                    ),
                    target_incarnation=generation,
                )

                def enroll_admin() -> GatewayClient:
                    """Enroll the first roster key through the live HTTPS gateway."""

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
                    return GatewayClient(
                        binding=enrollment.model_copy(update={"purpose": "caller"}),
                        target_incarnation=generation,
                    )

                admin = enroll_admin() if keyed else own
                yield _Gateway(manifest, unsigned, own, admin, enroll_admin, remote_url, ca_bundle)
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
    api_origin: str

    def connect(self) -> StalwartJmapClient:
        """Use JMAP with the test account's normal provider authority."""

        return StalwartJmapClient(
            jmap_url=self.url,
            login_identity=self.login,
            sender_address=self.address,
            credential_file=self.source,
            timeout_seconds=2.0,
            allowed_api_origins=(self.api_origin,),
        )


@contextmanager
def _disposable_stalwart(
    root: Path, executable: Path
) -> Iterator[tuple[_OnlineAccount, _OnlineAccount]]:
    """Run a disposable provider and provision two normal accounts on loopback."""

    root.mkdir(mode=0o700)
    url = _loopback_url()
    port = url.rsplit(":", 1)[1]
    api_origin = f"http://localhost:{port}"
    administrator = secrets.token_hex(32)
    config = _credential(
        root / "provider.toml",
        f'''\
server.hostname = "mail.example.com"
lookup.default.domain = "example.com"
http.url = "'{api_origin}'"
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
        accounts = []
        token = base64.b64encode(f"fixture-admin:{administrator}".encode()).decode("ascii")
        for name in ("gateway-worker", "gateway-peer"):
            address = f"{name}@example.com"
            discovery = f"{url}/.well-known/jmap"
            provisioned = ensure_stalwart_mailbox(
                runtime_root=root / "runtime",
                session_root=root / name,
                principal_id=name,
                address=address,
                jmap_url=discovery,
                management_url=f"{url}/api",
                management_auth_headers={"Authorization": f"Basic {token}"},
                trusted_jmap_origins=(api_origin,),
            )
            assert provisioned.api_origin == api_origin
            assert {"inbox", "sent", "archive"} <= provisioned.mailbox_roles.keys()
            accounts.append(
                _OnlineAccount(
                    discovery,
                    provisioned.login_identity,
                    address,
                    provisioned.credential_file,
                    api_origin,
                )
            )
        yield accounts[0], accounts[1]
    finally:
        process.terminate()
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=4)


def _selected_stalwart_executable() -> Path:
    """Resolve only the explicitly selected disposable provider executable."""

    selected = os.environ.get("HOUMAO_TEST_STALWART_BIN")
    if selected is None:
        pytest.skip("Select an explicit disposable Stalwart binary with HOUMAO_TEST_STALWART_BIN")
    executable = Path(selected).resolve(strict=True)
    assert executable.is_file() and os.access(executable, os.X_OK)
    return executable


@pytest.mark.parametrize("mode", ["foreground", "detached"])
@pytest.mark.parametrize("keyed_first", [True, False], ids=["key-then-mail", "mail-then-key"])
def test_authenticated_online_gateway_reaches_disposable_stalwart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: Literal["foreground", "detached"],
    keyed_first: bool,
) -> None:
    """Complete owner gateway operations against a provisioned Stalwart account."""

    executable = _selected_stalwart_executable()
    with (
        _disposable_stalwart(tmp_path / "provider", executable) as (owner, peer),
        _deployed_gateway(tmp_path / "g", monkeypatch, mode, keyed=keyed_first) as gateway,
    ):
        owner_jmap = owner.connect()
        binding = owner_jmap.validate_binding()
        assert "archive" in binding.mailbox_roles
        with pytest.raises(StalwartReadinessError, match="required isolation"):
            owner_jmap.require_protected_runtime(binding.account_id)
        peer_jmap = peer.connect()
        peer_jmap.validate_binding()
        initial = gateway.admin.online_binding_status()
        attach = OnlineAttachRequest(
            expected_revision=initial.revision,
            address=owner.address,
            login_identity=owner.login,
            credential_source_ref=str(owner.source),
            jmap_url=owner.url,
            trusted_jmap_origins=[owner.api_origin],
            timeout_seconds=2.0,
        )
        with _expect_http(400):
            gateway.admin.attach_online_binding(
                attach.model_copy(update={"trusted_jmap_origins": []})
            )
        current = gateway.admin.attach_online_binding(attach)
        assert current.available and current.binding_id
        assert current.account_id == binding.account_id
        assert current.api_origin == owner.api_origin
        if not keyed_first:
            gateway = replace(gateway, admin=gateway.enroll_admin())
        assert gateway.admin.online_binding_status() == current.model_copy(
            update={"committed": False}
        )
        status = gateway.admin.mail_status()
        assert status.online is not None and status.online.binding_id == current.binding_id
        assert gateway.self_client.mail_status() == status
        with _expect_http(401):
            gateway.unsigned.mail_status()
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
        handle = load_session_manifest(gateway.manifest)
        configured = mailboxes_resolved_config_from_payload(
            handle.payload["launch_plan"]["mailboxes"], manifest_path=gateway.manifest
        ).online.binding
        assert configured is not None
        direct = build_scoped_mailbox_adapter(
            configured,
            authority=OnlineAuthorityContext(
                gateway.manifest,
                handle.payload["agent_id"],
                handle.payload["runtime"]["session_id"],
            ),
        )
        direct_page = direct.list_page(
            box="inbox", read_state="any", answered_state="any", archived=False
        )
        assert [item.message_ref for item in direct_page.messages] == [messages[0].message_ref]
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
        assert refreshed.trusted_jmap_origins == [owner.api_origin]
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


def test_status_only_peer_delivers_through_both_mail_backends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise a keyed gateway and independent registry and Stalwart processes."""

    executable = _selected_stalwart_executable()
    registry = tmp_path / "registry-host"
    registry.mkdir(mode=0o700)
    registry_url = _loopback_url()
    admin_secret, owner_secret, peer_secret = (secrets.token_hex(32) for _ in range(3))
    admin_file = _credential(registry / "admin", admin_secret)
    owner_file = _credential(tmp_path / "owner" / "member", owner_secret)
    peer_file = _credential(tmp_path / "peer" / "member", peer_secret)
    config = _credential(
        registry / "service.json",
        json.dumps(
            {
                "registry_root": str(registry / "members"),
                "mailbox_root": str(registry / "messages"),
                "admin_credential_file": str(admin_file),
                "public_url": registry_url,
                "protected_filtering": True,
                # Loopback processes share a test UID and exercise the registry's API boundary.
                "protected_runtime_uids": [],
            }
        ),
    )
    with (
        _server(config, registry_url, registry),
        _disposable_stalwart(tmp_path / "provider", executable) as (online_owner, online_peer),
    ):
        registrar = OfflineRegistryClient.from_url(registry_url, admin_file)
        recipient = registrar.enroll(
            agent_id=_AGENT, address="worker@houmao.localhost", member_credential=owner_secret
        )
        correspondent = registrar.enroll(
            agent_id="fixture-peer", address="peer@houmao.localhost", member_credential=peer_secret
        )
        peer_registry = OfflineRegistryClient.from_url(registry_url, peer_file)
        assert recipient.policy_backend_id is not None

        def submit_offline(subject: str) -> None:
            """Prove transport acceptance from the sender's own binding."""

            [sent] = peer_registry.mail(
                "send",
                GatewayMailSendRequestV1(
                    expected_binding_id=correspondent.registration_id,
                    to=[recipient.address],
                    subject=subject,
                    body_content="Offline message from the status-only gateway peer.",
                ),
            )
            assert sent.subject == subject and sent.sender.address == correspondent.address
            assert sent.box == "sent" and sent.archived is False

        with _deployed_gateway(tmp_path / "g", monkeypatch, "detached") as gateway:
            manifest = load_session_manifest(gateway.manifest).payload
            offline_revision = manifest["launch_plan"]["mailboxes"]["offline"]["revision"]
            mutate_session_mailbox_binding(
                gateway.manifest,
                channel="offline",
                expected_revision=offline_revision,
                binding=RemoteRegistryMailboxResolvedConfig(
                    transport="registry",
                    principal_id=_AGENT,
                    agent_id=_AGENT,
                    binding_id=recipient.registration_id,
                    address=recipient.address,
                    bindings_version=offline_revision,
                    registry_url=registry_url,
                    credential_ref=str(owner_file),
                    credential_file=owner_file,
                ),
                agent_id=_AGENT,
                session_id=manifest["runtime"]["session_id"],
            )
            online = gateway.admin.attach_online_binding(
                OnlineAttachRequest(
                    expected_revision=gateway.admin.online_binding_status().revision,
                    address=online_owner.address,
                    login_identity=online_owner.login,
                    credential_source_ref=str(online_owner.source),
                    jmap_url=online_owner.url,
                    trusted_jmap_origins=[online_owner.api_origin],
                    timeout_seconds=2.0,
                )
            )
            assert online.available and online.binding_id and online.account_id

            peer_signer = Ed25519PrivateKey.generate()
            peer_key_path = tmp_path / "peer" / "gateway.key"
            _write_private_key(peer_key_path, peer_signer)
            peer = Principal(
                principal_id="fixture-peer",
                kind="agent",
                label="Mail peer",
                logical_agent_id=correspondent.agent_id,
            )
            credential = Credential(
                principal_id=peer.principal_id, public_key=public_key_text(peer_signer.public_key())
            )
            access = gateway_access_for_manifest(gateway.manifest)
            access.store.update(
                lambda state: state.model_copy(
                    update={
                        "principals": (*state.principals, peer),
                        "credentials": (*state.credentials, credential),
                        "grants": (
                            *state.grants,
                            ScopedGrant(principal_id=peer.principal_id, permission=STATUS),
                        ),
                    }
                ),
                actor="fixture-operator",
                action="fixture.peer.status",
            )
            assert not gateway.admin.set_default_fallback(
                peer.principal_id, DefaultFallbackRequest(enabled=False)
            ).enabled
            peer_gateway = GatewayClient(
                binding=GatewayClientBinding(
                    base_url=gateway.public_url,
                    owner=access.target.owner,
                    purpose="caller",
                    private_key_path=str(peer_key_path),
                    ca_bundle_path=str(gateway.ca_bundle),
                ),
                target_incarnation=access.target.incarnation,
            )
            assert peer_gateway.status().attach_identity
            with _expect_http(403):
                peer_gateway.create_request(
                    GatewayRequestCreateV1(
                        kind="submit_work_request",
                        payload=GatewayRequestPayloadSubmitWorkRequestV1(text="Gateway request"),
                    )
                )

            owner_signer = Ed25519PrivateKey.generate()
            enrolled = registrar.set_policy_owner(
                _AGENT,
                expected_registration_id=recipient.registration_id,
                public_key=public_key_text(owner_signer.public_key()),
            )
            assert enrolled.policy_revision == 0
            status = gateway.admin.mail_status()
            assert (
                status.offline is not None
                and status.offline.binding_id == recipient.registration_id
            )
            assert status.online is not None and status.online.binding_id == online.binding_id
            submit_offline("before offline rule")
            offline_query = GatewayMailListRequestV1(expected_binding_id=recipient.registration_id)
            [incoming] = gateway.admin.list_mail(offline_query, channel="offline").messages
            assert incoming.subject == "before offline rule"
            with pytest.raises(
                GatewayHttpError, match="offline registry operation is unsupported"
            ) as denied_archive:
                gateway.admin.archive_mail(
                    GatewayMailArchiveRequestV1(
                        expected_binding_id=recipient.registration_id,
                        message_refs=[incoming.message_ref],
                    ),
                    channel="offline",
                )
            assert denied_archive.value.status_code == 422

            def relay(
                channel: Literal["offline", "online"],
                update: MailPolicyUpdate,
                signer: Ed25519PrivateKey,
            ) -> MailPolicyReceipt:
                """Send one independently signed update through gateway HTTPS."""

                request = GatewayMailPolicyRequest(
                    expected_binding_id=update.binding_id,
                    signed_update=sign_mail_policy_update(update, signer),
                )
                return MailPolicyReceipt.model_validate(
                    gateway.admin.request_json(
                        "POST",
                        f"/v1/mail/{channel}/policy/apply",
                        body=request.model_dump(mode="json"),
                    )
                )

            block = MailPolicyUpdate(
                backend_id=recipient.policy_backend_id,
                binding_id=recipient.registration_id,
                expected_revision=0,
                operation_id="block-offline-peer",
                blocked_senders=(correspondent.address,),
            )
            assert relay("offline", block, peer_signer).status == "refused"
            applied = relay("offline", block, owner_signer)
            assert applied.status == "applied" and applied.revision == 1
            assert (
                registrar.policy_receipt(
                    _AGENT,
                    expected_registration_id=recipient.registration_id,
                    operation_id=block.operation_id,
                )
                == applied
            )

            native_block = MailPolicyUpdate(
                backend_id=online.account_id,
                binding_id=online.binding_id,
                expected_revision=0,
                operation_id="unqualified-native-rule",
                blocked_senders=(online_peer.address,),
            )
            assert relay("online", native_block, owner_signer).status == "unsupported"
            sent = online_peer.connect().send(
                sender_address=online_peer.address,
                to_addresses=[online_owner.address],
                cc_addresses=[],
                subject="ordinary online mail",
                body_content="Online message from the same status-only gateway peer.",
                attachments=[],
            )
            assert sent["mutation_receipt"]["outcome"] == "confirmed"
            online_query = GatewayMailListRequestV1(expected_binding_id=online.binding_id)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                online_inbox = gateway.admin.list_mail(online_query, channel="online").messages
                if online_inbox:
                    break
                time.sleep(0.1)
            else:
                pytest.fail("The ordinary online delivery did not reach the recipient Inbox")
            assert [message.subject for message in online_inbox] == ["ordinary online mail"]
            assert [
                message.subject
                for message in gateway.admin.list_mail(offline_query, channel="offline").messages
            ] == ["before offline rule"]

        submit_offline("after gateway stopped")
        owner_registry = OfflineRegistryClient.from_url(registry_url, owner_file)
        assert [
            message.subject for message in owner_registry.list_page(offline_query).messages
        ] == ["before offline rule"]
        archive = httpx.post(
            f"{registry_url}/houmao/registry/members/{_AGENT}/mail/list",
            headers={"Authorization": "Bearer " + admin_secret},
            json={"expected_binding_id": recipient.registration_id, "box": "archive"},
            timeout=2,
            trust_env=False,
        )
        archive.raise_for_status()
        [filed] = GatewayMailListResponseV1.model_validate_json(archive.content).messages
        assert filed.subject == "after gateway stopped" and filed.archived is True


def test_stalwart_native_sieve_archives_new_matches_without_gateway(tmp_path: Path) -> None:
    """Qualify native filing separately from a deployment's runtime isolation."""

    executable = _selected_stalwart_executable()
    with _disposable_stalwart(tmp_path / "provider", executable) as (owner, peer):
        client = owner.connect()
        account_id = client.validate_binding().account_id
        sender = peer.connect()

        def sieve(method: str, **arguments: object) -> dict[str, object]:
            """Exercise the selected account's real Sieve API."""

            return _require_method_response(
                client.call(
                    [[method, {"accountId": account_id, **arguments}, "native"]],
                    additional_capabilities=(JMAP_SIEVE_CAPABILITY,),
                ),
                method_name=method,
                call_id="native",
            )

        def submit(subject: str) -> None:
            """Submit exactly one disposable test message through the peer account."""

            sender.send(
                sender_address=peer.address,
                to_addresses=[owner.address],
                cc_addresses=[],
                subject=subject,
                body_content="Native delivery-time policy fixture.",
                attachments=[],
            )

        def observed_mailbox_ids(subject: str, box: str) -> set[str]:
            """Read the provider's actual mailbox membership within a finite wait."""

            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                page = client.query_metadata_page(query=JmapMetadataQuery(box=box), limit=10)
                for message in page.messages:
                    if message["subject"] == subject:
                        return set(message["mailboxIds"])
                time.sleep(0.1)
            pytest.fail(f"The disposable provider did not file {subject} in {box}.")

        empty_rule = b"# empty native policy\n"
        wrapper = client.upload_sieve_script(
            account_id=account_id,
            script=b'require "include";\ninclude :personal "houmao-protected-archive";\n',
        )
        initial = client.upload_sieve_script(account_id=account_id, script=empty_rule)
        created = sieve(
            "SieveScript/set",
            create={
                "managed": {"name": "houmao-protected-archive", "blobId": initial},
                "wrapper": {"name": "fixture-rules", "blobId": wrapper},
            },
            onSuccessActivateScript="#wrapper",
        )["created"]
        assert isinstance(created, dict)
        managed_id = created["managed"]["id"]

        def update_native_include(script: bytes) -> None:
            """Update only the existing include using a provider state fence and readback."""

            state = sieve("SieveScript/get", ids=[managed_id])["state"]
            uploaded = client.upload_sieve_script(account_id=account_id, script=script)
            updated = sieve(
                "SieveScript/set", ifInState=state, update={managed_id: {"blobId": uploaded}}
            )["updated"]
            assert isinstance(updated, dict) and managed_id in updated
            current = sieve("SieveScript/get", ids=[managed_id])["list"]
            assert isinstance(current, list) and len(current) == 1
            assert (
                client.download_sieve_script(account_id=account_id, blob_id=current[0]["blobId"])
                == script
            )

        submit("Before rule")
        inbox = {client.mailbox_id_for_role("inbox")}
        archive = {client.mailbox_id_for_role("archive")}
        assert observed_mailbox_ids("Before rule", "inbox") == inbox

        update = MailPolicyUpdate(
            backend_id="native-fixture",
            binding_id="native-fixture",
            expected_revision=0,
            operation_id="native-rule",
            blocked_senders=(peer.address,),
        )
        update_native_include(
            _archive_script(sign_mail_policy_update(update, Ed25519PrivateKey.generate()))
        )
        submit("Blocked by native rule")
        assert observed_mailbox_ids("Blocked by native rule", "archive") == archive
        assert observed_mailbox_ids("Before rule", "inbox") == inbox

        update_native_include(empty_rule)
        submit("After rule removal")
        assert observed_mailbox_ids("After rule removal", "inbox") == inbox
        assert observed_mailbox_ids("Blocked by native rule", "archive") == archive
