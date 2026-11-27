"""Offline registry ownership, authorization, isolation, and narrow API tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import hashlib
import os
from pathlib import Path
import sqlite3
from threading import Event
from unittest.mock import patch

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError
import pytest

from houmao.agents.realm_controller import gateway_access_runtime
from houmao.gateway._access_sshsig import public_key_text
from houmao.mailbox import managed
from houmao.mailbox.filesystem import bootstrap_filesystem_mailbox
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    ManagedMailboxOperationError,
    RegisterMailboxRequest,
    RepairRequest,
    deregister_mailbox,
    register_mailbox,
    repair_mailbox_index,
)
from houmao.mailbox.policy import (
    MailPolicyReceipt,
    MailPolicyUpdate,
    SignedMailPolicyUpdate,
    sign_mail_policy_update,
)
from houmao.mailbox.registry import OfflineRegistryService, prepare_member_credential
from houmao.mailbox.registry_app import create_offline_registry_app
from houmao.mailbox.registry_config import (
    OfflineRegistryConfig,
    OfflineRegistryConfigurationError,
    associate_registry_store,
    configured_registry_store,
    validate_registry_url,
    verify_selected_registry_store,
)

_ADMIN = "admin-test-credential-" + "a" * 48
_ALICE = "alice-test-credential-" + "b" * 48
_BOB = "bob-test-credential-" + "c" * 48


@pytest.fixture
def config(tmp_path: Path) -> OfflineRegistryConfig:
    """Keep all service state and deliberately fake credentials inside an isolated temp root."""

    credential = tmp_path / "admin-token"
    credential.write_text(_ADMIN)
    credential.chmod(0o600)
    return OfflineRegistryConfig(
        registry_root=tmp_path / "registry",
        mailbox_root=tmp_path / "store",
        admin_credential_file=credential,
        max_attachment_bytes=32,
    )


def _headers(token: str) -> dict[str, str]:
    """Select a fake test credential explicitly."""

    return {"Authorization": "Bearer " + token}


def _join(
    client: TestClient,
    agent: str,
    credential: str,
    address: str | None = None,
) -> dict[str, str]:
    """Enroll without creating a body or gateway."""

    response = client.post(
        "/houmao/registry/members",
        headers=_headers(_ADMIN),
        json={
            "agent_id": agent,
            "address": address or f"{agent}@houmao.localhost",
            "member_credential": credential,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _request(
    client: TestClient, token: str, member: dict[str, str], operation: str, **fields: object
) -> dict[str, object]:
    """Use a binding selected before each explicit lifecycle request."""

    response = client.post(
        "/houmao/registry/self/mail/" + operation,
        headers=_headers(token),
        json={"expected_binding_id": member["registration_id"], **fields},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def protected_config(config: OfflineRegistryConfig) -> OfflineRegistryConfig:
    """Declare a separate runtime UID and start the store with registry-only access."""

    return config.model_copy(
        update={"protected_filtering": True, "protected_runtime_uids": (os.geteuid() + 1,)}
    )


def _enroll_policy_owner(
    client: TestClient,
    member: dict[str, str],
    owner: Ed25519PrivateKey,
    *,
    expected_revision: int = 0,
) -> None:
    """Set the protected policy verification key with the separate registry credential."""

    response = client.put(
        f"/houmao/registry/members/{member['agent_id']}/mail/policy/owner",
        headers=_headers(_ADMIN),
        json={
            "expected_registration_id": member["registration_id"],
            "public_key": public_key_text(owner.public_key()),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["placement_writable"] is False
    assert response.json()["policy_revision"] == expected_revision


def _signed_rules(
    member: dict[str, str],
    owner: Ed25519PrivateKey,
    *,
    operation_id: str,
    revision: int = 0,
    blocked_senders: tuple[str, ...] = (),
) -> SignedMailPolicyUpdate:
    """Sign a prospective blocklist for the exact durable registry and recipient."""

    return sign_mail_policy_update(
        MailPolicyUpdate(
            backend_id=member["policy_backend_id"] or "unqualified",
            binding_id=member["registration_id"],
            expected_revision=revision,
            operation_id=operation_id,
            blocked_senders=blocked_senders,
        ),
        owner,
    )


def _owner_mail(
    client: TestClient,
    member: dict[str, str],
    operation: str,
    **fields: object,
) -> dict[str, object]:
    """Access the selected mailbox as the trusted registry administrator."""

    response = client.post(
        f"/houmao/registry/members/{member['agent_id']}/mail/{operation}",
        headers=_headers(_ADMIN),
        json={"expected_binding_id": member["registration_id"], **fields},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_membership_is_durable_and_join_retry_does_not_rotate(
    config: OfflineRegistryConfig,
) -> None:
    """Lost enrollment responses reuse the same identity and credential after service restart."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        shared_admin = client.post(
            "/houmao/registry/members",
            headers=_headers(_ADMIN),
            json={
                "agent_id": "alice",
                "address": "alice@houmao.localhost",
                "member_credential": _ADMIN,
            },
        )
        assert shared_admin.status_code == 409
        first = _join(client, "alice", _ALICE)
        assert _join(client, "alice", _ALICE) == first
        conflict = client.post(
            "/houmao/registry/members",
            headers=_headers(_ADMIN),
            json={
                "agent_id": "alice",
                "address": first["address"],
                "member_credential": _BOB,
            },
        )
        assert conflict.status_code == 409
    with TestClient(create_offline_registry_app(config=config)) as client:
        assert client.get("/houmao/registry/self", headers=_headers(_ALICE)).json() == first
        assert client.get("/houmao/registry/self", headers=_headers("alice")).status_code == 401
        assert _ADMIN not in str(first) and _ALICE not in str(first)
    with sqlite3.connect(config.mailbox_root / "index.sqlite") as connection:
        assert (
            connection.execute("SELECT credential_digest FROM offline_members").fetchone()[0]
            != _ALICE
        )


def test_conflicting_owner_cannot_claim_address(config: OfflineRegistryConfig) -> None:
    """An occupied address never becomes another agent's inbox through rejoin."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        response = client.post(
            "/houmao/registry/members",
            headers=_headers(_ADMIN),
            json={
                "agent_id": "bob",
                "address": alice["address"],
                "member_credential": _BOB,
            },
        )
        assert response.status_code == 409
        assert client.get("/houmao/registry/self", headers=_headers(_ALICE)).json() == alice
        assert not (config.mailbox_root / "mailboxes" / "bob@houmao.localhost").exists()


def test_delivery_to_stopped_recipients_uses_transport_registrations(
    config: OfflineRegistryConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Commit one logical delivery without consulting a recipient's gateway manifest."""

    monkeypatch.setattr(
        gateway_access_runtime,
        "gateway_access_for_manifest",
        lambda *_args: pytest.fail("offline publication consulted recipient gateway authority"),
    )
    carol_token = "carol-credential-" + "d" * 48
    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
        carol = _join(client, "carol", carol_token)
        sent = _request(
            client,
            _ALICE,
            alice,
            "send",
            to=[bob["address"]],
            cc=[carol["address"]],
            subject="hello",
            body_content="stopped recipients",
        )["messages"][0]
        assert sent["box"] == "sent"
        assert _request(client, _BOB, bob, "list")["message_count"] == 1
        assert _request(client, carol_token, carol, "list")["message_count"] == 1
        assert len(list((config.mailbox_root / "messages").rglob("*.md"))) == 1


def test_protected_registry_places_each_recipient_and_preserves_rules_and_history(
    protected_config: OfflineRegistryConfig,
) -> None:
    """Apply a prospective block privately, survive restart and repair, then unblock."""

    root = protected_config.mailbox_root
    owner = Ed25519PrivateKey.generate()
    carol_token = "carol-credential-" + "d" * 48
    with TestClient(create_offline_registry_app(config=protected_config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
        carol = _join(client, "carol", carol_token)
        _enroll_policy_owner(client, bob, owner)
        _enroll_policy_owner(client, bob, owner)

        def deliver(subject: str) -> dict[str, object]:
            """Send the same canonical mail to both recipients."""

            return _request(
                client,
                _ALICE,
                alice,
                "send",
                to=[bob["address"]],
                cc=[carol["address"]],
                subject=subject,
                body_content="hello",
            )["messages"][0]

        before = deliver("before")
        signed = _signed_rules(
            bob, owner, operation_id="block-alice", blocked_senders=(alice["address"],)
        )
        payload = signed.model_dump(mode="json")
        relay = "/houmao/registry/self/mail/policy/apply"
        assert (
            client.post(relay, json=payload, headers=_headers(_ALICE)).json()["status"] == "refused"
        )
        forged = _signed_rules(bob, Ed25519PrivateKey.generate(), operation_id="forged").model_dump(
            mode="json"
        )
        assert client.post(relay, json=forged, headers=_headers(_BOB)).json()["status"] == "refused"
        result = client.post(relay, json=payload, headers=_headers(_BOB)).json()
        assert result["status"] == "applied" and result["revision"] == 1
        assert client.post(relay, json=payload, headers=_headers(_BOB)).json() == result

        during = deliver("during")
        assert (before["box"], before["archived"]) == (during["box"], during["archived"])
        assert _request(client, carol_token, carol, "list")["message_count"] == 2
        assert _request(client, _BOB, bob, "list")["message_count"] == 1
        archived = _owner_mail(client, bob, "list", box="archive")["messages"][0]
        assert archived["subject"] == "during" and archived["archived"] is True
        bob_path = root / "mailboxes" / bob["address"]
        assert len(list((bob_path / "inbox").glob("*.md"))) == 1
        archive_projection = next((bob_path / "archive").glob("*.md"))
        assert (
            archive_projection.resolve()
            == (root / "mailboxes" / alice["address"] / "sent" / archive_projection.name).resolve()
        )
        assert (
            archive_projection.resolve()
            == (root / "mailboxes" / carol["address"] / "inbox" / archive_projection.name).resolve()
        )
        assert len(list((root / "messages").rglob("*.md"))) == 2

        for operation, fields, status in (
            ("list", {"box": "archive"}, 422),
            ("peek", {"message_ref": archived["message_ref"]}, 404),
            ("move", {"message_refs": [archived["message_ref"]], "destination_box": "inbox"}, 422),
            ("mark", {"message_refs": [archived["message_ref"]], "archived": False}, 422),
            ("archive", {"message_refs": [archived["message_ref"]]}, 422),
        ):
            assert (
                client.post(
                    "/houmao/registry/self/mail/" + operation,
                    headers=_headers(_BOB),
                    json={"expected_binding_id": bob["registration_id"], **fields},
                ).status_code
                == status
            )
        assert (
            client.delete(
                "/houmao/registry/self",
                headers=_headers(_BOB),
                params={"expected_registration_id": bob["registration_id"]},
            ).status_code
            == 422
        )
        receipt = f"/houmao/registry/members/bob/mail/policy/receipts/{signed.update.operation_id}"
        receipt_params = {"expected_registration_id": bob["registration_id"]}
        assert client.get(receipt, headers=_headers(_BOB), params=receipt_params).status_code == 401
        assert root.stat().st_mode & 0o077 == 0

    archive_projection.unlink()
    (bob_path / "mailbox.sqlite").unlink()
    repair_mailbox_index(root, RepairRequest())
    assert archive_projection.is_symlink()
    assert not (bob_path / "inbox" / archive_projection.name).exists()
    with sqlite3.connect(root / "index.sqlite") as connection:
        connection.execute("DELETE FROM mailbox_projections")
    repair_mailbox_index(root, RepairRequest())
    assert archive_projection.is_symlink()
    assert not (bob_path / "inbox" / archive_projection.name).exists()

    with TestClient(create_offline_registry_app(config=protected_config)) as client:
        member = client.get("/houmao/registry/self", headers=_headers(_BOB)).json()
        assert member["policy_backend_id"] == bob["policy_backend_id"]
        assert member["placement_writable"] is False
        assert "policy_revision" not in member
        assert client.get(receipt, headers=_headers(_ADMIN), params=receipt_params).json() == result
        unblock = _signed_rules(bob, owner, operation_id="unblock-alice", revision=1)
        assert (
            client.post(
                "/houmao/registry/mail/policy/apply", json=unblock.model_dump(mode="json")
            ).json()["revision"]
            == 2
        )
        assert deliver("after")["box"] == "sent"
        inbox = _request(client, _BOB, bob, "list")
        assert {message["subject"] for message in inbox["messages"]} == {"before", "after"}
        assert _owner_mail(client, bob, "list", box="archive")["messages"][0]["subject"] == "during"
        completed = inbox["messages"][0]["message_ref"]
        assert _owner_mail(client, bob, "archive", message_refs=[completed])["messages"][0][
            "archived"
        ]
        revoked = client.put(
            "/houmao/registry/members/bob/mail/policy/owner",
            headers=_headers(_ADMIN),
            json={"expected_registration_id": bob["registration_id"], "public_key": None},
        )
        assert revoked.json()["policy_revision"] == 3
        _enroll_policy_owner(client, bob, owner, expected_revision=4)
        stale = _signed_rules(bob, owner, operation_id="before-revocation", revision=2)
        assert (
            client.post(
                "/houmao/registry/mail/policy/apply", json=stale.model_dump(mode="json")
            ).json()["detail"]
            == "revision_conflict"
        )


@pytest.mark.parametrize("isolation_failure", ["shared", "same-uid", "external-projection"])
def test_unqualified_registry_leaves_ordinary_delivery_available(
    protected_config: OfflineRegistryConfig, tmp_path: Path, isolation_failure: str
) -> None:
    """An operator opt-in cannot qualify a shared authoritative filesystem."""

    root = protected_config.mailbox_root
    root.mkdir(mode=0o700)
    if isolation_failure == "shared":
        # Directory creation masks group and other access under umask 077.
        root.chmod(0o755)
    elif isolation_failure == "same-uid":
        protected_config = protected_config.model_copy(
            update={"protected_runtime_uids": (os.geteuid(),)}
        )
    elif isolation_failure == "external-projection":
        (root / "external").symlink_to(tmp_path)
    with TestClient(create_offline_registry_app(config=protected_config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
        owner = Ed25519PrivateKey.generate()
        signed = _signed_rules(bob, owner, operation_id="unsupported")
        assert (
            client.post(
                "/houmao/registry/mail/policy/apply", json=signed.model_dump(mode="json")
            ).json()["status"]
            == "unsupported"
        )
        assert (
            _request(
                client,
                _ALICE,
                alice,
                "send",
                to=[bob["address"]],
                subject="hello",
                body_content="hello",
            )["messages"][0]["box"]
            == "sent"
        )
        assert _request(client, _BOB, bob, "list")["message_count"] == 1


def test_policy_update_waits_for_in_progress_publication(
    protected_config: OfflineRegistryConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One committed rule revision determines each delivery even during a policy race."""

    owner = Ed25519PrivateKey.generate()
    publish_started = Event()
    release_publish = Event()
    update_started = Event()
    create_projection = managed._create_projection_symlink
    apply_policy = OfflineRegistryService.apply_policy

    def paused_projection(path: Path, canonical_path: Path) -> None:
        """Pause the publication after choosing placement under the writer lock."""

        if not publish_started.is_set():
            publish_started.set()
            assert release_publish.wait(5)
        create_projection(path, canonical_path)

    def tracked_apply(
        registry: OfflineRegistryService,
        request: SignedMailPolicyUpdate,
        *,
        credential: str | None = None,
    ) -> MailPolicyReceipt:
        """Observe that the competing rule update entered the registry."""

        update_started.set()
        return apply_policy(registry, request, credential=credential)

    with TestClient(create_offline_registry_app(config=protected_config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
        _enroll_policy_owner(client, bob, owner)
        raw = _signed_rules(
            bob, owner, operation_id="racing-block", blocked_senders=(alice["address"],)
        ).model_dump(mode="json")
        monkeypatch.setattr(managed, "_create_projection_symlink", paused_projection)
        monkeypatch.setattr(OfflineRegistryService, "apply_policy", tracked_apply)
        with ThreadPoolExecutor(max_workers=2) as executor:
            publication = executor.submit(
                _request,
                client,
                _ALICE,
                alice,
                "send",
                to=[bob["address"]],
                subject="publisher first",
                body_content="hello",
            )
            try:
                assert publish_started.wait(5)
                update = executor.submit(
                    client.post, "/houmao/registry/mail/policy/apply", json=raw
                )
                assert update_started.wait(5)
                with pytest.raises(TimeoutError):
                    update.result(timeout=0.1)
            finally:
                release_publish.set()
            assert publication.result(timeout=5)["messages"][0]["box"] == "sent"
            assert update.result(timeout=5).json()["status"] == "applied"
        _request(
            client,
            _ALICE,
            alice,
            "send",
            to=[bob["address"]],
            subject="policy first",
            body_content="hello",
        )
        assert _request(client, _BOB, bob, "list")["messages"][0]["subject"] == "publisher first"
        assert (
            _owner_mail(client, bob, "list", box="archive")["messages"][0]["subject"]
            == "policy first"
        )


def test_offline_lifecycle_and_reassignment_isolate_history(config: OfflineRegistryConfig) -> None:
    """Stopped members exchange, read, answer, and archive without cross-owner history reuse."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
        _request(
            client, _ALICE, alice, "send", to=[bob["address"]], subject="work", body_content="hello"
        )
        messages = _request(client, _BOB, bob, "list")["messages"]
        assert isinstance(messages, list) and len(messages) == 1
        original_ref = messages[0]["message_ref"]
        peek = _request(client, _BOB, bob, "peek", message_ref=original_ref)["messages"][0]
        assert peek["read"] is False
        read = _request(client, _BOB, bob, "read", message_ref=original_ref)["messages"][0]
        assert read["read"] is True and read["archived"] is False
        _request(client, _BOB, bob, "reply", message_ref=original_ref, body_content="done")
        parent = _request(client, _BOB, bob, "peek", message_ref=original_ref)["messages"][0]
        assert parent["answered"] is True and parent["archived"] is False
        _request(client, _BOB, bob, "archive", message_refs=[original_ref])
        assert _request(client, _BOB, bob, "list")["messages"] == []
        assert (
            client.delete("/houmao/registry/members/bob", headers=_headers(_ADMIN)).status_code
            == 200
        )
        replacement = _join(client, "carol", _BOB, address=bob["address"])
        assert replacement["registration_id"] != bob["registration_id"]
        assert _request(client, _BOB, replacement, "list")["messages"] == []
        stale = client.post(
            "/houmao/registry/self/mail/peek",
            headers=_headers(_BOB),
            json={
                "expected_binding_id": replacement["registration_id"],
                "message_ref": original_ref,
            },
        )
        assert stale.status_code == 409
        assert (config.mailbox_root / "history" / bob["registration_id"]).is_dir()
        assert list((config.mailbox_root / "messages").rglob("*.md"))


def test_sender_fields_and_stale_fresh_send_fail_before_delivery(
    config: OfflineRegistryConfig,
) -> None:
    """The caller cannot choose another sender or silently follow a replacement binding."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
        for extra, expected in (
            ({"sender": bob["address"]}, 422),
            ({"expected_binding_id": "old"}, 409),
        ):
            payload = {
                "expected_binding_id": alice["registration_id"],
                "to": [bob["address"]],
                "subject": "no",
                "body_content": "no",
                **extra,
            }
            response = client.post(
                "/houmao/registry/self/mail/send", headers=_headers(_ALICE), json=payload
            )
            assert response.status_code == expected
        assert _request(client, _BOB, bob, "list")["messages"] == []


def test_narrow_route_inventory_and_redacted_validation(config: OfflineRegistryConfig) -> None:
    """Mail membership never exposes a lifecycle or shutdown endpoint."""

    app = create_offline_registry_app(config=config)
    routes = {route.path for route in app.routes}
    assert routes
    assert all(path == "/health" or path.startswith("/houmao/registry/") for path in routes)
    with TestClient(app) as client:
        assert client.post("/shutdown", headers=_headers(_ADMIN)).status_code == 404
        response = client.post(
            "/houmao/registry/members",
            headers=_headers(_ADMIN),
            json={
                "agent_id": "alice",
                "address": "alice@houmao.localhost",
                "member_credential": "short-secret",
            },
        )
        assert response.status_code == 422
        assert "short-secret" not in response.text
        assert client.post("/houmao/registry/members", json={}).status_code == 401


def test_managed_attachments_require_upload_and_message_ownership(
    config: OfflineRegistryConfig,
) -> None:
    """Content transfers have bounded bytes/digests and remain scoped after address reassignment."""

    content = b"host-local-content"
    digest = hashlib.sha256(content).hexdigest()
    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
        response = client.post(
            "/houmao/registry/self/attachments",
            headers={**_headers(_ALICE), "X-Content-SHA256": digest},
            content=content,
        )
        assert response.status_code == 200, response.text
        upload = response.json()
        assert str(config.mailbox_root) not in str(upload)
        path = "/houmao/registry/self/attachments/" + upload["attachment_id"]
        assert client.get(path, headers=_headers(_BOB)).status_code == 404
        _request(
            client,
            _ALICE,
            alice,
            "send",
            to=[bob["address"]],
            subject="file",
            body_content="file",
            attachments=[{"path": upload["locator"]}],
        )
        downloaded = client.get(path, headers=_headers(_BOB))
        assert downloaded.content == content and downloaded.headers["x-content-sha256"] == digest
        response = client.post(
            "/houmao/registry/self/mail/send",
            headers=_headers(_ALICE),
            json={
                "expected_binding_id": alice["registration_id"],
                "to": [bob["address"]],
                "subject": "bad",
                "body_content": "bad",
                "attachments": [{"path": "/etc/passwd"}],
            },
        )
        assert response.status_code == 422
        assert (
            client.post(
                "/houmao/registry/self/attachments",
                headers={**_headers(_ALICE), "X-Content-SHA256": "0" * 64},
                content=content,
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/houmao/registry/self/attachments",
                headers={**_headers(_ALICE), "X-Content-SHA256": digest},
                content=b"x" * 33,
            ).status_code
            == 413
        )
        assert (
            client.delete("/houmao/registry/members/bob", headers=_headers(_ADMIN)).status_code
            == 200
        )
        _join(client, "carol", _BOB, address=bob["address"])
        assert client.get(path, headers=_headers(_BOB)).status_code == 404


def test_explicit_credential_replacement(config: OfflineRegistryConfig) -> None:
    """Token replacement is administrative and is never a side effect of retry."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        _join(client, "alice", _ALICE)
        path = "/houmao/registry/members/alice/credential"
        assert (
            client.put(path, headers=_headers(_ALICE), json={"member_credential": _BOB}).status_code
            == 401
        )
        assert (
            client.put(path, headers=_headers(_ADMIN), json={"member_credential": _BOB}).status_code
            == 200
        )
        assert client.get("/houmao/registry/self", headers=_headers(_ALICE)).status_code == 401
        assert client.get("/houmao/registry/self", headers=_headers(_BOB)).status_code == 200


def test_preparing_claim_is_recoverable_and_excludes_other_owners(tmp_path: Path) -> None:
    """An interrupted filesystem preparation reserves ownership without publishing an active route."""

    paths = bootstrap_filesystem_mailbox(tmp_path / "store")
    request = RegisterMailboxRequest(
        mode="safe",
        address="alice@houmao.localhost",
        owner_principal_id="alice",
        mailbox_kind="in_root",
        mailbox_path=paths.mailbox_entry_path("alice@houmao.localhost"),
    )
    with patch(
        "houmao.mailbox.managed._create_requested_artifact", side_effect=OSError("interrupted")
    ):
        with pytest.raises(OSError, match="interrupted"):
            register_mailbox(paths.root, request)
    with sqlite3.connect(paths.sqlite_path) as connection:
        reservation = connection.execute(
            "SELECT registration_id,status FROM mailbox_registrations WHERE address=?",
            (request.address,),
        ).fetchone()
        assert reservation[1] == "preparing"
    with pytest.raises(ManagedMailboxOperationError, match="address conflict"):
        register_mailbox(paths.root, request.model_copy(update={"owner_principal_id": "other"}))
    completed = register_mailbox(paths.root, request)
    assert completed["active_registration_id"] == reservation[0]
    assert register_mailbox(paths.root, request)["active_registration_id"] == reservation[0]


def test_removed_takeover_modes_and_external_target_preservation(tmp_path: Path) -> None:
    """Neither a removed mode nor a symlink release can expose another owner's private history."""

    paths = bootstrap_filesystem_mailbox(tmp_path / "store")
    private = tmp_path / "private"
    request = RegisterMailboxRequest(
        mode="safe",
        address="alice@houmao.localhost",
        owner_principal_id="alice",
        mailbox_kind="symlink",
        mailbox_path=private,
    )
    register_mailbox(paths.root, request)
    marker = private / "keep.txt"
    marker.write_text("keep")
    for mode in ("force", "stash"):
        with pytest.raises(ValidationError):
            RegisterMailboxRequest.model_validate({**request.model_dump(), "mode": mode})
    deregister_mailbox(
        paths.root, DeregisterMailboxRequest(mode="deactivate", address=request.address)
    )
    assert marker.read_text() == "keep"
    assert not paths.mailbox_entry_path(request.address).is_symlink()
    with pytest.raises(ManagedMailboxOperationError, match="retained history"):
        register_mailbox(paths.root, request.model_copy(update={"owner_principal_id": "other"}))


def test_registry_association_is_explicit_and_never_rewritten(tmp_path: Path) -> None:
    """Maintenance root selection cannot silently create another mail group."""

    registry = tmp_path / "registry"
    store = tmp_path / "store"
    with pytest.raises(OfflineRegistryConfigurationError, match="no offline store"):
        configured_registry_store(registry)
    assert associate_registry_store(registry, store) == store
    assert associate_registry_store(registry, store) == store
    for operation in (
        associate_registry_store,
        lambda root, selected: verify_selected_registry_store(selected, root),
    ):
        with pytest.raises(OfflineRegistryConfigurationError, match="differs"):
            operation(registry, tmp_path / "other")
    assert configured_registry_store(registry) == store


@pytest.mark.parametrize(
    "url",
    [
        "http://192.0.2.1:9892",
        "http://registry.example.test",
        "https://user:secret@example.test",
        "ftp://localhost",
    ],
)
def test_plaintext_remote_credentials_are_rejected(url: str) -> None:
    """Only protected remote endpoints or local test/tunnel endpoints are accepted."""

    with pytest.raises(OfflineRegistryConfigurationError):
        validate_registry_url(url)


def test_member_credential_is_created_once_and_private(tmp_path: Path) -> None:
    """A retry reuses private local credential material instead of losing the first identity."""

    target = tmp_path / "credentials" / "member"
    assert prepare_member_credential(target) == target
    original = target.read_bytes()
    assert prepare_member_credential(target) == target
    assert target.read_bytes() == original and target.stat().st_mode & 0o777 == 0o600


def test_repair_preserves_member_verifiers_and_rejects_missing_authority(
    config: OfflineRegistryConfig,
) -> None:
    """Derived index repair cannot replace ownership with guesses from message headers."""

    from houmao.mailbox.managed import RepairRequest, repair_mailbox_index

    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        _request(
            client,
            _ALICE,
            alice,
            "send",
            to=[alice["address"]],
            subject="self",
            body_content="work",
        )
        result = repair_mailbox_index(config.mailbox_root, RepairRequest())
        assert result["ok"] is True
        assert client.get("/houmao/registry/self", headers=_headers(_ALICE)).json() == alice
    index = config.mailbox_root / "index.sqlite"
    index.rename(index.with_suffix(".operator-backup"))
    with pytest.raises(ManagedMailboxOperationError, match="ownership index is missing"):
        repair_mailbox_index(config.mailbox_root, RepairRequest())
    assert not index.exists()


def test_non_loopback_listener_requires_explicit_https_termination(
    config: OfflineRegistryConfig,
) -> None:
    """An advertised loopback URL cannot accidentally enable a public plaintext listener."""

    from houmao.mailbox.registry_config import validate_registry_listener

    validate_registry_listener("127.0.0.1", config.public_url)
    with pytest.raises(OfflineRegistryConfigurationError, match="non-loopback registry listener"):
        validate_registry_listener("0.0.0.0", config.public_url)
    validate_registry_listener("0.0.0.0", "https://registry.example.test")


def test_released_member_can_reconcile_lost_leave_response(config: OfflineRegistryConfig) -> None:
    """An owner can confirm explicit release without gaining mail or another owner's authority."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        member = _join(client, "alice", _ALICE)
        first = client.delete(
            "/houmao/registry/self",
            headers=_headers(_ALICE),
            params={"expected_registration_id": member["registration_id"]},
        )
        assert first.status_code == 200 and first.json()["status"] == "released"
        assert (
            client.delete(
                "/houmao/registry/self",
                headers=_headers(_ALICE),
                params={"expected_registration_id": member["registration_id"]},
            ).json()
            == first.json()
        )
        assert (
            client.get(
                "/houmao/registry/self",
                headers=_headers(_ALICE),
                params={"expected_registration_id": member["registration_id"]},
            ).json()["status"]
            == "released"
        )
        assert (
            client.post(
                "/houmao/registry/self/mail/list",
                headers=_headers(_ALICE),
                json={
                    "expected_binding_id": member["registration_id"],
                },
            ).status_code
            == 401
        )


def test_lifecycle_cleanup_preserves_durable_remote_membership(
    config: OfflineRegistryConfig,
) -> None:
    """Local presence cleanup cannot release communication registration or its address."""

    from houmao.agents.realm_controller.registry_storage import remove_managed_agent_record

    with TestClient(create_offline_registry_app(config=config)) as client:
        member = _join(client, "alice", _ALICE)
        live = config.registry_root / "live_agents" / "alice"
        live.mkdir(parents=True)
        (live / "record.json").write_text("invalid stale local presence")
        assert remove_managed_agent_record(
            "alice", env={"HOUMAO_GLOBAL_REGISTRY_DIR": str(config.registry_root)}
        )
        assert not live.exists()
        assert client.get("/houmao/registry/self", headers=_headers(_ALICE)).json() == member
        _request(
            client,
            _ALICE,
            member,
            "send",
            to=[member["address"]],
            subject="stopped",
            body_content="work",
        )


def test_operator_can_explicitly_release_interrupted_preparation(tmp_path: Path) -> None:
    """An admitted preparing reservation requires explicit release before a different owner joins."""

    paths = bootstrap_filesystem_mailbox(tmp_path / "store")
    request = RegisterMailboxRequest(
        mode="safe",
        address="pending@houmao.localhost",
        owner_principal_id="owner-a",
        mailbox_kind="in_root",
        mailbox_path=paths.mailbox_entry_path("pending@houmao.localhost"),
    )
    with patch(
        "houmao.mailbox.managed._create_requested_artifact", side_effect=OSError("interrupted")
    ):
        with pytest.raises(OSError):
            register_mailbox(paths.root, request)
    released = deregister_mailbox(
        paths.root, DeregisterMailboxRequest(mode="deactivate", address=request.address)
    )
    assert released["resulting_status"] == "inactive"
    fresh = register_mailbox(
        paths.root, request.model_copy(update={"owner_principal_id": "owner-b"})
    )
    assert fresh["owner_principal_id"] == "owner-b"


def test_remote_backend_contains_connection_failure_and_preserves_scope_conflict(
    config: OfflineRegistryConfig, tmp_path: Path
) -> None:
    """Remote transport exceptions obey the shared per-channel error contract."""

    from houmao.agents.mailbox_runtime_models import RemoteRegistryMailboxResolvedConfig
    from houmao.mailbox.registry import OfflineRegistryError
    from houmao.mailbox.registry_backend import RemoteRegistryMailboxAdapter
    from houmao.mailbox.scope import MailboxScopeError
    from houmao.mailbox.services import GatewayMailboxError

    token = prepare_member_credential(tmp_path / "private" / "member-token")
    adapter = RemoteRegistryMailboxAdapter.from_config(
        RemoteRegistryMailboxResolvedConfig(
            transport="registry",
            agent_id="a",
            binding_id="binding-a",
            principal_id="a",
            address="a@houmao.localhost",
            bindings_version="revision-a",
            registry_url="http://127.0.0.1:1",
            credential_ref="member-a",
            credential_file=token,
        )
    )
    with patch.object(
        adapter.m_client,
        "self_status",
        side_effect=OfflineRegistryError(
            "registry_unavailable",
            "unavailable",
            503,
        ),
    ):
        with pytest.raises(GatewayMailboxError, match="registry_unavailable"):
            adapter.status()
    with patch.object(
        adapter.m_client,
        "self_status",
        side_effect=OfflineRegistryError(
            "binding_conflict",
            "binding changed",
            409,
        ),
    ):
        with pytest.raises(MailboxScopeError):
            adapter.status()


def test_private_configuration_error_does_not_echo_embedded_url_credentials(tmp_path: Path) -> None:
    """Invalid private configuration does not print supplied secret values in validation traces."""

    target = tmp_path / "private.json"
    target.write_text(
        '{"registry_root":"/tmp/r", "mailbox_root":"/tmp/m",'
        '"admin_credential_file":"/tmp/a", "public_url":"https://user:secret-token@example.test"}'
    )
    target.chmod(0o600)
    with pytest.raises(OfflineRegistryConfigurationError) as caught:
        OfflineRegistryConfig.from_file(target)
    assert "secret-token" not in str(caught.value)


def test_stale_member_release_cannot_release_new_registration(
    config: OfflineRegistryConfig,
) -> None:
    """A reused private token cannot let a stale controller release its replacement binding."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        first = _join(client, "alice", _ALICE)
        assert client.delete("/houmao/registry/self", headers=_headers(_ALICE)).status_code == 422
        released = client.delete(
            "/houmao/registry/self",
            headers=_headers(_ALICE),
            params={"expected_registration_id": first["registration_id"]},
        )
        assert released.status_code == 200
        current = _join(client, "alice", _ALICE)
        assert current["registration_id"] != first["registration_id"]
        stale = client.delete(
            "/houmao/registry/self",
            headers=_headers(_ALICE),
            params={"expected_registration_id": first["registration_id"]},
        )
        assert stale.status_code == 409
        assert client.get("/houmao/registry/self", headers=_headers(_ALICE)).json() == current


def test_separate_registries_reuse_an_address_without_cross_delivery(
    tmp_path: Path, config: OfflineRegistryConfig
) -> None:
    """Registry selection, rather than a cluster identifier, scopes identical offline addresses."""

    from pydantic import SecretStr
    from houmao.mailbox.models import GatewayMailListRequestV1, GatewayMailSendRequestV1
    from houmao.mailbox.registry import OfflineRegistryService, RegistryEnrollment

    first = OfflineRegistryService.from_config(config)
    second = OfflineRegistryService.from_config(
        config.model_copy(
            update={
                "registry_root": tmp_path / "other-registry",
                "mailbox_root": tmp_path / "other-store",
            }
        )
    )
    a = first.enroll(
        RegistryEnrollment(
            agent_id="agent-a", address="same@houmao.localhost", member_credential=SecretStr(_ALICE)
        )
    )
    b = second.enroll(
        RegistryEnrollment(
            agent_id="agent-b", address="same@houmao.localhost", member_credential=SecretStr(_BOB)
        )
    )
    first.mail(
        _ALICE,
        "send",
        GatewayMailSendRequestV1(
            expected_binding_id=a.registration_id,
            to=[a.address],
            subject="local",
            body_content="local",
        ),
    )
    assert (
        len(
            first.list_page(
                _ALICE, GatewayMailListRequestV1(expected_binding_id=a.registration_id)
            ).messages
        )
        == 1
    )
    assert (
        second.list_page(
            _BOB, GatewayMailListRequestV1(expected_binding_id=b.registration_id)
        ).messages
        == []
    )
    assert a.registration_id != b.registration_id
