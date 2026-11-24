"""Offline registry ownership, authorization, isolation, and narrow API tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError
import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller import gateway_access_runtime, manifest, registry_storage
from houmao.execution.context import current_execution_binding, execution_binding_scope
from houmao.execution.models import ExecutionBindingV1
from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway._access_sshsig import public_key_text
from houmao.gateway.access_models import GatewayOwner, GatewayTarget
from houmao.gateway.authorization_models import (
    Credential,
    PolicySnapshot,
    Principal,
    RoleAssignment,
)
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.mailbox import delivery_policy
from houmao.mailbox.filesystem import bootstrap_filesystem_mailbox, load_active_mailbox_registration
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    ManagedMailboxOperationError,
    RegisterMailboxRequest,
    deregister_mailbox,
    register_mailbox,
)
from houmao.mailbox.registry import prepare_member_credential
from houmao.mailbox.registry_app import create_offline_registry_app
from houmao.mailbox.registry_config import (
    OfflineRegistryConfig,
    OfflineRegistryConfigurationError,
    associate_registry_store,
    configured_registry_store,
    validate_registry_url,
    verify_selected_registry_store,
)
from houmao.mailbox.services import FilesystemGatewayMailboxAdapter

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
    *,
    require_recipient_policy: bool = False,
) -> dict[str, str]:
    """Enroll without creating a body or gateway."""

    response = client.post(
        "/houmao/registry/members",
        headers=_headers(_ADMIN),
        json={
            "agent_id": agent,
            "address": address or f"{agent}@houmao.localhost",
            "member_credential": credential,
            "require_recipient_policy": require_recipient_policy,
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


def test_membership_is_durable_and_join_retry_does_not_rotate(
    config: OfflineRegistryConfig,
) -> None:
    """Lost enrollment responses reuse the same identity and credential after service restart."""

    with TestClient(create_offline_registry_app(config=config)) as client:
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


def test_managed_recipient_admission_at_offline_deposit(
    config: OfflineRegistryConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The authenticated member's scoped role overrides the recipient's default."""

    owner = GatewayOwner(agent_id="bob", context_id="bob-owner")
    store = AuthorizationStore(tmp_path / "bob-policy", owner)
    admin = Principal(principal_id="bob-admin", label="Bob admin", kind="operator")
    alice_principal = Principal(
        principal_id="alice-peer", label="Alice", kind="agent", logical_agent_id="alice"
    )
    store.initialize(
        PolicySnapshot(
            owner=owner,
            principals=(admin,),
            credentials=(
                Credential(
                    principal_id=admin.principal_id,
                    public_key=public_key_text(Ed25519PrivateKey.generate().public_key()),
                    admin_revision=0,
                ),
            ),
        )
    )
    access = SimpleNamespace(
        private_root=tmp_path / "bob-policy",
        store=store,
        target=GatewayTarget(owner=owner, incarnation="stopped-bob"),
        require_current=lambda: None,
    )
    carol_owner = GatewayOwner(agent_id="carol", context_id="carol-owner")
    carol_store = AuthorizationStore(tmp_path / "aaa-carol-policy", carol_owner)
    carol_store.initialize()
    carol_access = SimpleNamespace(
        private_root=tmp_path / "aaa-carol-policy",
        store=carol_store,
        target=GatewayTarget(owner=carol_owner, incarnation="stopped-carol"),
        require_current=lambda: None,
    )

    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB, require_recipient_policy=True)
        carol_token = "carol-credential-" + "c" * 48
        carol = _join(client, "carol", carol_token, require_recipient_policy=True)

        def send(*, to: list[str], cc: list[str] | None = None):
            return client.post(
                "/houmao/registry/self/mail/send",
                headers=_headers(_ALICE),
                json={
                    "expected_binding_id": alice["registration_id"],
                    "to": to,
                    "cc": cc or [],
                    "subject": "work",
                    "body_content": "Please review the report.",
                },
            )

        unavailable = send(to=[bob["address"]])
        assert unavailable.status_code == 409
        assert unavailable.json()["code"] == "recipient_policy_unavailable"
        monkeypatch.setattr(
            delivery_policy,
            "_select_recipient",
            lambda receipt, **_: {"bob": access, "carol": carol_access}.get(
                receipt.owner_principal_id
            ),
        )
        assert send(to=[bob["address"]]).status_code == 200

        with store.transaction() as transaction:
            transaction.replace(
                transaction.snapshot.model_copy(
                    update={
                        "principals": (*transaction.snapshot.principals, alice_principal),
                        "role_assignments": (
                            RoleAssignment(
                                principal_id="alice-peer",
                                role_id="builtin:agent-observer",
                                builtin_version=1,
                            ),
                        ),
                    }
                ),
                actor="bob-admin",
                action="role.assign",
            )
        denied = send(to=[carol["address"]], cc=[bob["address"]])
        assert denied.status_code == 409
        assert denied.json()["code"] == "recipient_policy_refused"
        assert (
            _request(client, _BOB, bob, "list")["messages"][0]["sender"]["principal_id"] == "alice"
        )
        assert _request(client, carol_token, carol, "list")["messages"] == []
        assert all(entry.action != "operation.handoff" for entry in carol_store.audit_entries())
        assert len(list((config.mailbox_root / "messages").rglob("*.md"))) == 1

        operator = FilesystemGatewayMailboxAdapter(
            FilesystemMailboxResolvedConfig(
                transport="filesystem",
                principal_id="bob",
                agent_id="bob",
                binding_id=bob["registration_id"],
                address=bob["address"],
                filesystem_root=config.mailbox_root,
                bindings_version=bob["registration_id"],
                registry_root=config.registry_root,
            )
        )
        posted = operator.post(
            subject="operator post",
            body_content="Operator body",
            attachments=(),
            reply_policy="none",
        )
        assert posted.sender.principal_id == "HOUMAO-operator"

        with store.transaction() as transaction:
            transaction.replace(
                transaction.snapshot.model_copy(
                    update={
                        "role_assignments": (),
                        "default_permission_group": "agent-observer",
                    }
                ),
                actor="bob-admin",
                action="admin.default-group.set",
            )
        assert send(to=[bob["address"]]).status_code == 409
        assert _request(client, _BOB, bob, "list")["message_count"] == 2


def test_delivery_selects_owner_independently_of_sender_execution(
    config: OfflineRegistryConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller's execution binding must not become recipient host authority."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        alice = _join(client, "alice", _ALICE)
        bob = _join(client, "bob", _BOB)
    sender = load_active_mailbox_registration(config.mailbox_root, address=alice["address"])
    recipient = load_active_mailbox_registration(config.mailbox_root, address=bob["address"])
    inspected = []

    def select(*_args: object, **_kwargs: object) -> None:
        inspected.append(current_execution_binding())

    monkeypatch.setattr(delivery_policy, "_select_recipient", select)
    binding = ExecutionBindingV1.model_construct(context_id="caller-only")
    with (
        execution_binding_scope(binding),
        sqlite3.connect(config.mailbox_root / "index.sqlite") as connection,
    ):
        with delivery_policy.require_delivery_authority(
            connection,
            mailbox_root=config.mailbox_root,
            registry_root=config.registry_root,
            sender=sender,
            sender_verified=True,
            recipients={recipient.address: recipient},
            message_id="test-cross-execution",
        ):
            assert current_execution_binding() is binding
    assert inspected == [None]


def test_stopped_recipient_uses_manifest_offline_binding_when_projection_is_stale(
    config: OfflineRegistryConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A detached recipient's retained manifest controls exact address ownership."""

    with TestClient(create_offline_registry_app(config=config)) as client:
        bob = _join(client, "bob", _BOB, require_recipient_policy=True)
    registration = load_active_mailbox_registration(config.mailbox_root, address=bob["address"])
    manifest_path = config.registry_root / "bob.json"
    execution = ExecutionBindingV1.model_construct(context_id="recipient")
    owner = GatewayOwner(agent_id="bob", context_id="recipient")
    access = SimpleNamespace(
        manifest_path=manifest_path,
        execution_binding=execution,
        target=GatewayTarget(owner=owner, incarnation="stopped-bob"),
        owner=owner,
    )
    record = SimpleNamespace(
        agent_id="bob",
        generation_id="stopped-bob",
        execution_binding=execution,
        runtime=SimpleNamespace(manifest_path=str(manifest_path)),
        mailboxes=SimpleNamespace(offline=SimpleNamespace(binding=None)),
    )
    binding = SimpleNamespace(
        transport="registry",
        binding_id=bob["registration_id"],
        address=bob["address"],
        agent_id="bob",
    )
    parsed = SimpleNamespace(
        registry_generation_id="stopped-bob",
        runtime=SimpleNamespace(execution_binding=execution),
        launch_plan=SimpleNamespace(
            mailboxes=SimpleNamespace(offline=SimpleNamespace(binding=binding))
        ),
    )
    monkeypatch.setattr(
        registry_storage, "load_managed_agent_record_by_agent_id", lambda *_args, **_kwargs: record
    )
    monkeypatch.setattr(gateway_access_runtime, "gateway_access_for_manifest", lambda _path: access)
    monkeypatch.setattr(
        manifest, "load_session_manifest", lambda _path: SimpleNamespace(payload={})
    )
    monkeypatch.setattr(
        manifest, "parse_session_manifest_payload", lambda _payload, **_kwargs: parsed
    )
    coordinates = {
        "mailbox_root": config.mailbox_root,
        "registry_root": config.registry_root,
        "required": True,
    }
    assert delivery_policy._select_recipient(registration, **coordinates) is access
    binding.binding_id = "replaced-binding"
    with pytest.raises(GatewayAccessError) as denied:
        delivery_policy._select_recipient(registration, **coordinates)
    assert denied.value.code == "recipient_mail_binding_changed"


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
