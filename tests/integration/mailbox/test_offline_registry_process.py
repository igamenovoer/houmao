"""Isolated processes prove remote offline mail needs no shared runtime paths."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from typing import Iterator
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from houmao.agents.mailbox_runtime_models import RemoteRegistryMailboxResolvedConfig
from houmao.mailbox.filesystem import bootstrap_filesystem_mailbox
from houmao.mailbox.models import (
    GatewayMailArchiveRequestV1,
    GatewayMailAttachmentUploadV1,
    GatewayMailListRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
)
from houmao.mailbox.registry import OfflineRegistryError
from houmao.mailbox.registry_backend import RemoteRegistryMailboxAdapter
from houmao.mailbox.registry_client import OfflineRegistryClient
from houmao.mailbox.scope import MailScope, MailboxScopeError
from houmao.mailbox.services import ScopedMailboxAdapter

_ADMIN = "integration-admin-" + "a" * 48
_ALICE = "integration-alice-" + "b" * 48
_BOB = "integration-bob-" + "c" * 48


def _credential(path: Path, token: str) -> Path:
    """Write explicitly fake credentials into a private temporary host root."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token)
    path.chmod(0o600)
    return path


@contextmanager
def _server(config_path: Path, url: str, cwd: Path) -> Iterator[subprocess.Popen[bytes]]:
    """Start the supported narrow service and bound its startup and shutdown waits."""

    executable = shutil.which("houmao-passive-server")
    assert executable is not None
    port = url.rsplit(":", 1)[1]
    process = subprocess.Popen(
        [executable, "offline-registry", "--config", str(config_path), "--port", port],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 15
    try:
        while True:
            if process.poll() is not None:
                pytest.fail(
                    "registry process exited during startup: "
                    + (process.stderr.read().decode() if process.stderr is not None else "")
                )
            try:
                with urlopen(url + "/health", timeout=0.2) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError, OSError):
                pass
            if time.monotonic() > deadline:
                pytest.fail("registry process did not become healthy")
            time.sleep(0.05)
        yield process
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_remote_members_survive_restart_and_reassignment_with_attachment_isolation(
    tmp_path: Path,
) -> None:
    """Two disjoint agent roots use one durable store while bodies and gateways are absent."""

    server_root = tmp_path / "registry-host"
    alice_root = tmp_path / "agent-host-a"
    bob_root = tmp_path / "agent-host-b"
    server_root.mkdir()
    admin_file = _credential(server_root / "admin-token", _ADMIN)
    alice_file = _credential(alice_root / "member-token", _ALICE)
    bob_file = _credential(bob_root / "member-token", _BOB)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    config = {
        "registry_root": str(server_root / "registry"),
        "mailbox_root": str(server_root / "mail"),
        "admin_credential_file": str(admin_file),
        "public_url": url,
    }
    config_path = server_root / "service.json"
    config_path.write_text(json.dumps(config))
    config_path.chmod(0o600)
    admin = OfflineRegistryClient.from_url(url, admin_file)
    alice = OfflineRegistryClient.from_url(url, alice_file)
    bob = OfflineRegistryClient.from_url(url, bob_file)
    with _server(config_path, url, server_root):
        a = admin.enroll(
            agent_id="agent-a", address="alice@houmao.localhost", member_credential=_ALICE
        )
        b = admin.enroll(agent_id="agent-b", address="bob@houmao.localhost", member_credential=_BOB)
        # Deliberately discard the enrollment response and retry the exact prepared credential.
        assert admin.enroll(agent_id="agent-a", address=a.address, member_credential=_ALICE) == a
        with pytest.raises(OfflineRegistryError) as conflict:
            admin.enroll(agent_id="other", address=a.address, member_credential="other-" + "d" * 48)
        assert conflict.value.code == "address_conflict"
        local_content = b"content exists only on agent host A"
        source = alice_root / "private-artifact.txt"
        source.write_bytes(local_content)
        assert not (server_root / source.name).exists()
        config_a = RemoteRegistryMailboxResolvedConfig(
            transport="registry",
            agent_id=a.agent_id,
            principal_id=a.agent_id,
            binding_id=a.registration_id,
            address=a.address,
            bindings_version="revision-a",
            registry_url=url,
            credential_ref="member-a",
            credential_file=alice_file,
        )
        adapter = ScopedMailboxAdapter.from_backend(
            RemoteRegistryMailboxAdapter.from_config(config_a),
            MailScope(a.agent_id, "offline", a.registration_id),
        )
        sent = adapter.send(
            to_addresses=[b.address],
            cc_addresses=[],
            subject="work",
            body_content="hello",
            attachments=[GatewayMailAttachmentUploadV1(path=str(source))],
        )
        source.unlink()
        inbox = bob.mail("list", GatewayMailListRequestV1(expected_binding_id=b.registration_id))
        assert len(inbox) == 1 and inbox[0].body_text is None
        bob_ref = inbox[0].message_ref
        peek = bob.mail(
            "peek",
            GatewayMailMessageRequestV1(expected_binding_id=b.registration_id, message_ref=bob_ref),
        )[0]
        assert peek.read is False and peek.body_text == "hello"
        assert len(peek.attachments) == 1
        upload_id = peek.attachments[0].attachment_id
        assert bob.download(upload_id) == local_content
        assert str(server_root) not in json.dumps(peek.model_dump(mode="json"))
        assert sent.sender.address == a.address
    with _server(config_path, url, server_root):
        assert alice.self_status() == a and bob.self_status() == b
        bob.mail(
            "read",
            GatewayMailMessageRequestV1(expected_binding_id=b.registration_id, message_ref=bob_ref),
        )
        bob.mail(
            "reply",
            GatewayMailReplyRequestV1(
                expected_binding_id=b.registration_id, message_ref=bob_ref, body_content="done"
            ),
        )
        parent = bob.mail(
            "peek",
            GatewayMailMessageRequestV1(expected_binding_id=b.registration_id, message_ref=bob_ref),
        )[0]
        assert parent.read is True and parent.answered is True and parent.archived is False
        bob.mail(
            "archive",
            GatewayMailArchiveRequestV1(
                expected_binding_id=b.registration_id, message_refs=[bob_ref]
            ),
        )
        assert (
            bob.mail("list", GatewayMailListRequestV1(expected_binding_id=b.registration_id)) == []
        )
        assert admin.release(b.agent_id).status == "released"
        replacement = admin.enroll(agent_id="agent-c", address=b.address, member_credential=_BOB)
        assert replacement.registration_id != b.registration_id
        assert (
            bob.mail(
                "list", GatewayMailListRequestV1(expected_binding_id=replacement.registration_id)
            )
            == []
        )
        with pytest.raises(OfflineRegistryError) as stale:
            bob.mail(
                "peek",
                GatewayMailMessageRequestV1(
                    expected_binding_id=replacement.registration_id, message_ref=bob_ref
                ),
            )
        assert stale.value.code == "binding_conflict"
        with pytest.raises(OfflineRegistryError) as denied:
            bob.download(upload_id)
        assert denied.value.status == 404
        assert (server_root / "mail" / "history" / b.registration_id).is_dir()
        assert not (alice_root / "mail").exists() and not (bob_root / "mail").exists()


def test_concurrent_process_claims_have_one_winner(tmp_path: Path) -> None:
    """Independent processes cannot each reserve the same offline address."""

    store = bootstrap_filesystem_mailbox(tmp_path / "store").root
    script = """
import json, os
from pathlib import Path
from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox, ManagedMailboxOperationError
root = Path(os.environ['CLAIM_TEST_STORE'])
try:
    result = register_mailbox(root, RegisterMailboxRequest(mode='safe', address='shared@houmao.localhost',
        owner_principal_id=os.environ['CLAIM_TEST_OWNER'], mailbox_kind='in_root',
        mailbox_path=root/'mailboxes'/'shared@houmao.localhost'))
    print(json.dumps({'claimed': True, 'registration_id': result['active_registration_id']}))
except ManagedMailboxOperationError:
    print(json.dumps({'claimed': False}))
"""
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "CLAIM_TEST_STORE": str(store), "CLAIM_TEST_OWNER": owner},
        )
        for owner in ("owner-a", "owner-b")
    ]
    results = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr
        results.append(json.loads(stdout))
    assert sum(result["claimed"] for result in results) == 1


def test_killed_preparation_releases_os_locks_and_recovers_same_owner(tmp_path: Path) -> None:
    """An interrupted worker leaves a durable reservation while the OS releases its locks."""

    store = bootstrap_filesystem_mailbox(tmp_path / "store").root
    ready = tmp_path / "prepared-reservation"
    script = """
import os, time
from pathlib import Path
import houmao.mailbox.managed as managed
root = Path(os.environ['CLAIM_TEST_STORE'])
def interrupted(**kwargs):
    Path(os.environ['CLAIM_TEST_READY']).write_text('reserved')
    while True:
        time.sleep(1)
managed._create_requested_artifact = interrupted
managed.register_mailbox(root, managed.RegisterMailboxRequest(mode='safe',
    address='shared@houmao.localhost', owner_principal_id='same-agent', mailbox_kind='in_root',
    mailbox_path=root/'mailboxes'/'shared@houmao.localhost'))
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "CLAIM_TEST_STORE": str(store),
            "CLAIM_TEST_READY": str(ready),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists():
            assert process.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.02)
    finally:
        process.kill()
        process.wait(timeout=5)
    from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox

    recovered = register_mailbox(
        store,
        RegisterMailboxRequest(
            mode="safe",
            address="shared@houmao.localhost",
            owner_principal_id="same-agent",
            mailbox_kind="in_root",
            mailbox_path=store / "mailboxes" / "shared@houmao.localhost",
        ),
    )
    assert recovered["status"] == "active" and recovered["reused_existing"] is True


def test_runtime_remote_join_preserves_body_and_reconciles_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A running body attaches over real registry HTTP after a lost local publication."""

    from houmao.agents.mailbox_runtime_models import (
        MailboxesResolvedConfig,
        MailboxSlotConfig,
        StalwartMailboxResolvedConfig,
    )
    from houmao.agents.realm_controller import runtime as runtime_module
    from houmao.agents.realm_controller.errors import SessionManifestError
    from houmao.agents.realm_controller.manifest import (
        SessionManifestRequest,
        build_session_manifest_payload,
        default_manifest_path,
        load_session_manifest,
        write_session_manifest,
    )
    from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
    from houmao.agents.realm_controller.runtime import RuntimeSessionController
    from houmao.mailbox.models import GatewayMailSendRequestV1

    server_root = tmp_path / "registry-host"
    agent_root = tmp_path / "agent-host"
    server_root.mkdir()
    agent_root.mkdir()
    server_admin = _credential(server_root / "admin-token", _ADMIN)
    operator_admin = _credential(agent_root / "operator-admin-token", _ADMIN)
    member_file = _credential(agent_root / "member-token", _ALICE)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    config_path = server_root / "service.json"
    config_path.write_text(
        json.dumps(
            {
                "registry_root": str(server_root / "registry"),
                "mailbox_root": str(server_root / "mail"),
                "admin_credential_file": str(server_admin),
                "public_url": url,
            }
        )
    )
    config_path.chmod(0o600)
    online = StalwartMailboxResolvedConfig(
        transport="stalwart",
        agent_id="agent-running",
        principal_id="agent-running",
        binding_id="existing-online-account",
        address="alice@example.test",
        bindings_version="online-revision",
        jmap_url="http://127.0.0.1:10080/.well-known/jmap",
        management_url="http://127.0.0.1:10080/api",
        login_identity="online-alice",
        credential_ref="unavailable-online-credential",
    )
    plan = LaunchPlan(
        backend="local_interactive",
        tool="claude",
        executable="claude",
        args=[],
        working_directory=agent_root,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=agent_root / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt", role_name="worker", prompt="Work."
        ),
        mailboxes=MailboxesResolvedConfig(
            online=MailboxSlotConfig(revision=online.bindings_version, binding=online)
        ),
    )
    body = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    class BodyBackend:
        """Keep body ownership and its conversation independent of communication attachment."""

        def __init__(self) -> None:
            self.m_plan: LaunchPlan = plan
            self.m_conversation_id: str = "provider-conversation-a"

        def update_launch_plan(self, updated: LaunchPlan) -> None:
            """Update configuration without replacing the owned body or conversation."""

            self.m_plan = updated

    backend = BodyBackend()
    manifest_path = default_manifest_path(
        agent_root / "runtime", "local_interactive", "running-session"
    )
    initial = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="worker",
            brain_manifest_path=agent_root / "brain.yaml",
            backend_state={
                "pid": body.pid,
                "conversation_id": backend.m_conversation_id,
                "turn_index": 7,
            },
            agent_name="alice",
            agent_id="agent-running",
            tmux_session_name="alice-body",
            session_id="running-session",
            registry_launch_authority="external",
        )
    )
    write_session_manifest(manifest_path, initial)
    controller = RuntimeSessionController(
        launch_plan=plan,
        role_name="worker",
        brain_manifest_path=agent_root / "brain.yaml",
        manifest_path=manifest_path,
        backend_session=backend,  # type: ignore[arg-type]
        agent_identity="alice",
        agent_id="agent-running",
        tmux_session_name="alice-body",
        registry_launch_authority="external",
    )
    original_commit = runtime_module.mutate_session_mailbox_binding

    def lose_publication(*args: object, **kwargs: object) -> object:
        """Fail after remote enrollment while preserving the existing local snapshot."""

        raise OSError("injected local binding publication failure")

    try:
        with _server(config_path, url, server_root):
            monkeypatch.setattr(runtime_module, "mutate_session_mailbox_binding", lose_publication)
            with pytest.raises(
                SessionManifestError,
                match="Registry confirmed registration.*local publication failed",
            ):
                controller.register_remote_offline_mailbox(
                    registry_url=url,
                    credential_file=member_file,
                    admin_credential_file=operator_admin,
                    address="alice@houmao.localhost",
                )
            confirmed = OfflineRegistryClient.from_url(url, member_file).self_status()
            before_retry = member_file.read_bytes()
            assert controller.launch_plan.mailboxes.offline.binding is None
            assert load_session_manifest(manifest_path).payload == initial
            monkeypatch.setattr(runtime_module, "mutate_session_mailbox_binding", original_commit)
            joined = controller.register_remote_offline_mailbox(
                registry_url=url,
                credential_file=member_file,
                admin_credential_file=operator_admin,
                address="alice@houmao.localhost",
            )
            assert joined.mailbox is not None
            assert joined.mailbox.binding_id == confirmed.registration_id
            assert joined.mailbox.agent_id == "agent-running"
            assert member_file.read_bytes() == before_retry
            committed = load_session_manifest(manifest_path).payload
            assert committed["backend_state"] == initial["backend_state"]
            assert (
                committed["launch_plan"]["mailboxes"]["online"]
                == initial["launch_plan"]["mailboxes"]["online"]
            )
            assert committed["agent_id"] == initial["agent_id"]
            assert controller.backend_session is backend
            assert body.poll() is None and body.pid == committed["backend_state"]["pid"]
            assert backend.m_conversation_id == "provider-conversation-a"
            assert backend.m_plan.mailboxes.offline.binding == joined.mailbox
            member = OfflineRegistryClient.from_url(url, member_file)
            member.mail(
                "send",
                GatewayMailSendRequestV1(
                    expected_binding_id=confirmed.registration_id,
                    to=[confirmed.address],
                    subject="late attachment is active",
                    body_content="mail without a body restart",
                ),
            )
            messages = member.mail(
                "list", GatewayMailListRequestV1(expected_binding_id=confirmed.registration_id)
            )
            assert len(messages) == 1 and messages[0].subject == "late attachment is active"
            monkeypatch.setattr(runtime_module, "mutate_session_mailbox_binding", lose_publication)
            with pytest.raises((OSError, SessionManifestError)):
                controller.unregister_filesystem_mailbox()
            assert member.self_status().status == "released"
            administrator = OfflineRegistryClient.from_url(url, operator_admin)
            replacement = administrator.enroll(
                agent_id="next-owner", address=confirmed.address, member_credential=_BOB
            )
            assert replacement.registration_id != confirmed.registration_id
            monkeypatch.setattr(runtime_module, "mutate_session_mailbox_binding", original_commit)
            left = controller.unregister_filesystem_mailbox()
            assert left.mailbox is None
            assert controller.launch_plan.mailboxes.offline.binding is None
            assert (
                controller.launch_plan.mailboxes.online.redacted_payload()
                == initial["launch_plan"]["mailboxes"]["online"]
            )
            replacement_file = _credential(agent_root / "next-owner-token", _BOB)
            assert (
                OfflineRegistryClient.from_url(url, replacement_file).self_status() == replacement
            )
            assert body.poll() is None and controller.backend_session is backend
            assert backend.m_conversation_id == "provider-conversation-a"
    finally:
        body.terminate()
        body.wait(timeout=5)


def test_remote_metadata_continuation_keeps_scope_and_rejects_drift(tmp_path: Path) -> None:
    """Round-trip real continued pages through HTTP, remote backend, and outer scope."""
    server_root = tmp_path / "registry-host-pages"
    server_root.mkdir()
    admin_file = _credential(server_root / "admin-token", _ADMIN)
    alice_file = _credential(tmp_path / "host-alice" / "member-token", _ALICE)
    bob_file = _credential(tmp_path / "host-bob" / "member-token", _BOB)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    config_path = server_root / "service.json"
    config_path.write_text(
        json.dumps(
            {
                "registry_root": str(server_root / "registry"),
                "mailbox_root": str(server_root / "mail"),
                "admin_credential_file": str(admin_file),
                "public_url": url,
            }
        )
    )
    config_path.chmod(0o600)
    admin = OfflineRegistryClient.from_url(url, admin_file)
    alice = OfflineRegistryClient.from_url(url, alice_file)
    bob = OfflineRegistryClient.from_url(url, bob_file)
    with _server(config_path, url, server_root):
        a = admin.enroll(
            agent_id="page-owner-a", address="alice@houmao.localhost", member_credential=_ALICE
        )
        b = admin.enroll(
            agent_id="page-owner-b", address="bob@houmao.localhost", member_credential=_BOB
        )
        for index in range(5):
            alice.mail(
                "send",
                GatewayMailSendRequestV1(
                    expected_binding_id=a.registration_id,
                    to=[b.address],
                    subject=f"page item {index}",
                    body_content="Explicit reads retrieve this content.",
                ),
            )
        scope = MailScope(b.agent_id, "offline", b.registration_id)
        backend = RemoteRegistryMailboxAdapter.from_config(
            RemoteRegistryMailboxResolvedConfig(
                transport="registry",
                agent_id=b.agent_id,
                principal_id=b.agent_id,
                binding_id=b.registration_id,
                address=b.address,
                bindings_version="remote-pages-revision",
                registry_url=url,
                credential_ref="page-member-b",
                credential_file=bob_file,
            )
        )
        adapter = ScopedMailboxAdapter.from_backend(backend, scope)
        first_server = bob.list_page(
            GatewayMailListRequestV1(expected_binding_id=b.registration_id, limit=2)
        )
        assert first_server.message_count == 2
        assert first_server.counts_scope == "page"
        assert first_server.has_more and not first_server.complete
        assert first_server.total_count is None
        pages = []
        cursor = None
        for _ in range(3):
            page = adapter.list_page(
                box="inbox",
                read_state="any",
                answered_state="any",
                archived=None,
                limit=2,
                cursor=cursor,
            )
            pages.append(page)
            cursor = page.next_cursor
        assert [len(page.messages) for page in pages] == [2, 2, 1]
        assert [page.has_more for page in pages] == [True, True, False]
        assert [page.complete for page in pages] == [False, False, True]
        assert cursor is None
        assert pages[0].next_cursor == first_server.next_cursor
        messages = [message for page in pages for message in page.messages]
        assert len({message.message_ref for message in messages}) == 5
        assert all(message.body_text is None for message in messages)
        assert all(
            scope.decode(message.message_ref).startswith("filesystem:") for message in messages
        )
        assert pages[0].next_cursor is not None
        scope.decode(pages[0].next_cursor, kind="cursor")
        foreign_adapter = ScopedMailboxAdapter.from_backend(
            backend, MailScope(a.agent_id, "offline", a.registration_id)
        )
        with pytest.raises(MailboxScopeError):
            foreign_adapter.list_page(
                box="inbox",
                read_state="any",
                answered_state="any",
                archived=None,
                limit=2,
                cursor=pages[0].next_cursor,
            )
        with pytest.raises(OfflineRegistryError) as wrong_filter:
            bob.list_page(
                GatewayMailListRequestV1(
                    expected_binding_id=b.registration_id,
                    read_state="unread",
                    limit=2,
                    cursor=first_server.next_cursor,
                )
            )
        assert wrong_filter.value.status == 409
        assert wrong_filter.value.code == "invalid_mail_cursor"
        with pytest.raises(OfflineRegistryError) as wrong_owner:
            alice.list_page(
                GatewayMailListRequestV1(
                    expected_binding_id=a.registration_id, limit=2, cursor=first_server.next_cursor
                )
            )
        assert wrong_owner.value.status == 409
        adapter.read(message_ref=messages[0].message_ref, box=None)
        with pytest.raises(OfflineRegistryError) as stale:
            bob.list_page(
                GatewayMailListRequestV1(
                    expected_binding_id=b.registration_id, limit=2, cursor=first_server.next_cursor
                )
            )
        assert stale.value.status == 409
        assert stale.value.code == "stale_mail_cursor"
