"""Exercise the embedded authorization rules and retained owner-side fence."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError
import pytest

from houmao.gateway._access_sshsig import public_key_text
from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.access_models import GatewayAdminKey, GatewayLaunchSeed, GatewayOwner
from houmao.gateway.access_models import GatewayTarget
from houmao.gateway.access import GatewayAccessPolicy
from houmao.gateway.authorization import GatewayAuthorizer
from houmao.gateway.authorization_catalog import (
    DEFAULT_FALLBACK_SET,
    DEFAULT_GROUP_SET,
    RETIRED_MAIL_DELIVER,
)
from houmao.gateway.authorization_models import (
    AuthorizationActor,
    Credential,
    Permission,
    PolicySnapshot,
    Principal,
    RoleAssignment,
    RoleDefinition,
    ScopedGrant,
    seed_snapshot,
)
from houmao.gateway.authorization_store import AuthorizationStore

_OWNER = GatewayOwner(agent_id="writer", context_id="owner-bob")
_TARGET = GatewayTarget(owner=_OWNER, incarnation="writer-generation")
_LISTENER = "gateway-instance"
_PEER = Principal(
    principal_id="reviewer-principal", kind="agent", label="Reviewer", logical_agent_id="reviewer"
)
_ADMIN = Principal(principal_id="operator", kind="operator", label="Operator")
_READ = Permission(resource="mount:skills", action="files.read")
_PUSH = Permission(resource="mount:skills", action="files.push")
_ATTACHMENT = Permission(resource="mail:offline", action="mail.read_attachment")
_STATUS = Permission(resource="gateway", action="status.read")
_HEALTH = Permission(resource="gateway", action="health.read")
_ANONYMOUS = AuthorizationActor(kind="anonymous")

_PEER_EFFECTS = tuple(
    Permission(resource="agent", action=action)
    for action in (
        "agent.status.read",
        "agent.request.submit",
        "agent.prompt.direct",
        "agent.command.invoke",
        "agent.interrupt",
        "agent.input.raw",
    )
)
_COMMON_WRITE = Permission(resource="files:common", action="files.edit")
_OTHER_WRITE = Permission(resource="files:other", action="files.edit")


@pytest.mark.parametrize(
    ("group", "allowed"),
    [
        ("agent-requester", _PEER_EFFECTS[:2]),
        ("agent-maintainer", (*_PEER_EFFECTS[:2], _COMMON_WRITE)),
        ("agent-operator", (*_PEER_EFFECTS[:5], _COMMON_WRITE)),
        ("managed-self", (*_PEER_EFFECTS, _COMMON_WRITE, _OTHER_WRITE)),
        (
            "agent-admin",
            (
                *_PEER_EFFECTS,
                _COMMON_WRITE,
                _OTHER_WRITE,
                DEFAULT_GROUP_SET,
                DEFAULT_FALLBACK_SET,
            ),
        ),
    ],
)
def test_default_group_effects(tmp_path: Path, group: str, allowed: tuple[Permission, ...]) -> None:
    """Each default gives its versioned exact effects to an otherwise unassigned caller."""

    catalog = (
        *_PEER_EFFECTS,
        _COMMON_WRITE,
        _OTHER_WRITE,
        DEFAULT_GROUP_SET,
        DEFAULT_FALLBACK_SET,
        _HEALTH,
    )
    store = _store(
        tmp_path,
        PolicySnapshot.model_validate(
            {
                "owner": _OWNER,
                "principals": (_ADMIN,),
                "credentials": (_key(_ADMIN, admin=True),),
                "default_permission_group": group,
            }
        ),
    )
    authorizer = GatewayAuthorizer(
        store,
        catalog=catalog,
        self_permissions=catalog,
        public_permissions=(_HEALTH,),
        supports_common=lambda effect: effect == _COMMON_WRITE,
    )
    for effect in catalog:
        if effect == _HEALTH:
            assert _allow(authorizer, _ANONYMOUS, effect) == "public"
        elif effect in allowed:
            assert _allow(authorizer, _ANONYMOUS, effect) == "default"
        else:
            _reject(authorizer, _ANONYMOUS, effect, status=401)
    _reject(authorizer, _ANONYMOUS, RETIRED_MAIL_DELIVER, status=403)


def test_default_fencing_and_expired_builtin_assignment(tmp_path: Path) -> None:
    """A legacy role and direct grant keep their exact scope while fallback changes."""

    key = _key(_PEER)
    actor = AuthorizationActor.from_credential(key)
    old_role = "builtin:agent-requester"
    status, request, direct = _PEER_EFFECTS[:3]
    retired = Permission(resource="agent", action="agent.prompt")
    initial = PolicySnapshot(
        owner=_OWNER,
        principals=(_ADMIN, _PEER),
        credentials=(_key(_ADMIN, admin=True), key),
        roles=(RoleDefinition(role_id=old_role, permissions=(direct, retired)),),
        role_assignments=(RoleAssignment(principal_id=_PEER.principal_id, role_id=old_role),),
    )
    store = _store(tmp_path, initial)
    authorizer = GatewayAuthorizer(store, catalog=(status, request, direct))
    admitted = authorizer.authorize(actor, (request, direct), target=_TARGET, listener_id=_LISTENER)
    assert admitted.default_permissions == (request,)
    _reject(authorizer, actor, retired, status=403)

    with store.transaction() as transaction:
        state = transaction.snapshot
        transaction.replace(
            state.model_copy(
                update={
                    "role_assignments": (
                        *state.role_assignments,
                        RoleAssignment(
                            principal_id=_PEER.principal_id,
                            role_id=old_role,
                            builtin_version=1,
                            expires_at=1,
                        ),
                    )
                }
            ),
            actor="owner",
            action="role.assign",
        )

    assert _allow(authorizer, actor, direct) == "scoped"
    _reject(authorizer, actor, request, status=403)
    _reject(authorizer, actor, status, status=403)
    assert not authorizer.revalidate(admitted, target=_TARGET, listener_id=_LISTENER)
    assert _allow(authorizer, _ANONYMOUS, request) == "default"

    with store.transaction() as transaction:
        transaction.replace(
            transaction.snapshot.model_copy(
                update={
                    "role_assignments": initial.role_assignments,
                    "default_permission_group": "agent-operator",
                }
            ),
            actor="owner",
            action="test.setting",
        )
        transaction.replace(
            transaction.snapshot.model_copy(update={"default_permission_group": "agent-requester"}),
            actor="owner",
            action="test.setting",
        )
    assert _allow(authorizer, actor, request) == "default"
    assert not authorizer.revalidate(admitted, target=_TARGET, listener_id=_LISTENER)
    with pytest.raises(GatewayAccessError, match="lacks authority"):
        authorizer.handoff(admitted, operation_id="pending", target=_TARGET, listener_id=_LISTENER)


def test_verified_fallback_revisions_fence_handoff_without_affecting_unsigned(
    tmp_path: Path,
) -> None:
    """Each verified principal has an independent revision across setting changes."""

    admin_key, peer_key = _key(_ADMIN, admin=True), _key(_PEER)
    admin, peer = map(AuthorizationActor.from_credential, (admin_key, peer_key))
    status, request = _PEER_EFFECTS[:2]
    store = _store(
        tmp_path,
        PolicySnapshot(
            owner=_OWNER,
            principals=(_ADMIN, _PEER),
            credentials=(admin_key, peer_key),
            grants=(ScopedGrant(principal_id=_PEER.principal_id, permission=status),),
        ),
    )
    gateway = GatewayAccessPolicy(
        store=store, target=lambda: _TARGET, current_self=lambda: None, listener_id=_LISTENER
    )
    setter = gateway.authorize(admin, (DEFAULT_FALLBACK_SET,))
    signed = gateway.authorize(peer, (request,))
    unsigned = gateway.authorize(_ANONYMOUS, (request,))
    disabled = gateway.set_default_fallback(setter, _PEER.principal_id, False)
    assert disabled.default_fallback_revision == disabled.policy_revision
    assert gateway.authorize(peer, (status,)).basis == "scoped"
    with pytest.raises(GatewayAccessError, match="lacks authority"):
        gateway.authorize(peer, (request,))
    assert not gateway.revalidate(signed)
    assert gateway.revalidate(unsigned)
    enabled = gateway.set_default_fallback(setter, _PEER.principal_id, True)
    assert enabled.default_fallback_revision > disabled.default_fallback_revision
    assert not gateway.revalidate(signed)
    assert gateway.revalidate(unsigned)
    assert gateway.authorize(peer, (request,)).default_fallback_revision == enabled.policy_revision

    store.update(
        lambda state: state.model_copy(
            update={"credentials": tuple(row for row in state.credentials if row != admin_key)}
        ),
        actor="owner",
        action="credential.revoke",
    )
    with pytest.raises(GatewayAccessError, match="proof"):
        gateway.set_default_fallback(setter, _PEER.principal_id, False)
    assert store.snapshot().find_default_fallback(_PEER.principal_id).enabled


def test_migrate_observer_policy_preserves_exact_effects_and_independent_expiries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upgrade a v2 database with an old default, overlapping grants, and both expiries."""

    status, request = _PEER_EFFECTS[:2]
    expired = Principal(principal_id="expired", kind="operator", label="Expired observer")
    admin_key, peer_key, expired_key = _key(_ADMIN, admin=True), _key(_PEER), _key(expired)
    seed = PolicySnapshot(
        owner=_OWNER,
        principals=(_ADMIN, _PEER, expired),
        credentials=(admin_key, peer_key, expired_key),
        grants=(
            ScopedGrant(principal_id=_PEER.principal_id, permission=status, expires_at=30),
            ScopedGrant(principal_id=expired.principal_id, permission=_READ),
        ),
    )
    store = _store(tmp_path, seed)
    legacy = seed.model_dump(mode="json")
    legacy.update(schema_version=1, default_permission_group="agent-observer")
    del legacy["default_permission_effects"]
    del legacy["principal_default_fallback"]
    for grant in legacy["grants"]:
        del grant["source"]
    legacy["role_assignments"] = [
        RoleAssignment(
            principal_id=row.principal_id,
            role_id="builtin:agent-observer",
            expires_at=expiry,
            builtin_version=1,
        ).model_dump(mode="json")
        for row, expiry in ((_PEER, 10), (expired, 1))
    ]
    with closing(sqlite3.connect(tmp_path / "policy" / "authorization.sqlite3")) as db, db:
        db.execute("UPDATE policy SET payload = ?", (json.dumps(legacy).encode(),))
        db.execute("PRAGMA user_version = 2")
    monkeypatch.setattr("houmao.gateway.authorization.time.time", lambda: 5)
    migrated = store.snapshot()
    assert migrated.owner == seed.owner
    assert migrated.policy_id == seed.policy_id
    assert migrated.credentials == seed.credentials
    assert migrated.default_permission_group is None
    assert migrated.default_permission_effects == (status,)
    assert migrated.role_assignments == ()
    assert [
        (row.source, row.expires_at) for row in migrated.grants if row.permission == status
    ] == [
        ("direct", 30),
        ("retired-observer", 10),
        ("retired-observer", 1),
    ]
    assert all(not setting.enabled for setting in migrated.principal_default_fallback)
    assert AuthorizationStore(tmp_path / "policy", _OWNER).snapshot() == migrated
    assert store.audit_entries(limit=1)[0].action == "policy.migrate-observer"
    authorizer = GatewayAuthorizer(store, catalog=(status, request, _READ))
    active_actor = AuthorizationActor.from_credential(peer_key)
    expired_actor = AuthorizationActor.from_credential(expired_key)
    assert _allow(authorizer, active_actor, status) == "scoped"
    assert _allow(authorizer, expired_actor, _READ) == "scoped"
    assert _allow(authorizer, _ANONYMOUS, status) == "default"
    _reject(authorizer, _ANONYMOUS, request, status=401)
    _reject(authorizer, active_actor, request, status=403)
    _reject(authorizer, expired_actor, status, status=403)
    monkeypatch.setattr("houmao.gateway.authorization.time.time", lambda: 15)
    assert _allow(authorizer, active_actor, status) == "scoped"
    monkeypatch.setattr("houmao.gateway.authorization.time.time", lambda: 31)
    _reject(authorizer, active_actor, status, status=403)
    gateway = GatewayAccessPolicy(
        store=store, target=lambda: _TARGET, current_self=lambda: None, listener_id=_LISTENER
    )
    admin_actor = AuthorizationActor.from_credential(admin_key)
    receipt = gateway.set_default_permission_group(
        gateway.authorize(admin_actor, (DEFAULT_GROUP_SET,)), "agent-requester"
    )
    assert receipt.default_permission_revision > migrated.default_permission_revision
    assert store.snapshot().default_permission_effects == ()
    assert _allow(authorizer, _ANONYMOUS, request) == "default"
    _reject(authorizer, active_actor, request, status=403)


def _key(principal: Principal, *, admin: bool = False) -> Credential:
    """Create one synthetic public credential without writing private key material."""

    return Credential(
        principal_id=principal.principal_id,
        public_key=public_key_text(Ed25519PrivateKey.generate().public_key()),
        admin_revision=0 if admin else None,
    )


def _store(tmp_path: Path, seed: PolicySnapshot) -> AuthorizationStore:
    """Initialize an isolated owner directory for a policy test."""

    store = AuthorizationStore(tmp_path / "policy", _OWNER)
    store.initialize(seed)
    return store


def _allow(
    authorizer: GatewayAuthorizer, actor: AuthorizationActor, *permissions: Permission
) -> str:
    """Return the admission basis for the fixed live target used by the tests."""

    return authorizer.authorize(actor, permissions, target=_TARGET, listener_id=_LISTENER).basis


def _reject(
    authorizer: GatewayAuthorizer,
    actor: AuthorizationActor,
    *permissions: Permission,
    status: int,
) -> None:
    """Assert the public distinction between invalid proof and missing permission."""

    with pytest.raises(GatewayAccessError) as refusal:
        _allow(authorizer, actor, *permissions)
    assert refusal.value.status_code == status


def test_exact_compound_scope_and_domain(tmp_path: Path) -> None:
    """One peer uses a role and a direct grant without broad resource or action matching."""

    credential = _key(_PEER)
    other_mount = Permission(resource="mount:mcp", action="files.read")
    extra = Permission(resource="thread:current", action="ag-ui.observe")
    initial = PolicySnapshot(
        owner=_OWNER,
        principals=(_ADMIN, _PEER),
        credentials=(_key(_ADMIN, admin=True), credential),
        roles=(RoleDefinition(role_id="observer", permissions=(_STATUS,)),),
        role_assignments=(RoleAssignment(principal_id=_PEER.principal_id, role_id="observer"),),
        grants=(
            ScopedGrant(principal_id=_PEER.principal_id, permission=_READ),
            ScopedGrant(principal_id=_PEER.principal_id, permission=extra),
        ),
    )
    store = _store(tmp_path, initial)
    authorizer = GatewayAuthorizer(
        store,
        catalog=(_STATUS, _HEALTH, _READ, _PUSH, other_mount),
        public_permissions=(_HEALTH,),
        supports=lambda permission: permission == extra,
    )
    actor = AuthorizationActor.from_credential(credential)

    assert _allow(authorizer, actor, _HEALTH, _STATUS, _READ, extra) == "scoped"
    assert _allow(authorizer, _ANONYMOUS, _HEALTH) == "public"
    _reject(authorizer, actor, other_mount, status=403)
    _reject(authorizer, actor, _READ, _PUSH, status=403)
    _reject(authorizer, actor, status=403)
    _reject(authorizer, _ANONYMOUS, _STATUS, status=401)
    with pytest.raises(GatewayAccessError) as refusal:
        authorizer.authorize(
            actor,
            (_READ,),
            target=GatewayTarget(
                owner=GatewayOwner(agent_id=_OWNER.agent_id, context_id="other-owner"),
                incarnation=_TARGET.incarnation,
            ),
            listener_id=_LISTENER,
        )
    assert refusal.value.status_code == 403


def test_rejects_unknown_and_invalid_permission(tmp_path: Path) -> None:
    """Open authority remains subject to the runtime catalog and strict permission shape."""

    store = _store(tmp_path, PolicySnapshot(owner=_OWNER))
    authorizer = GatewayAuthorizer(store, catalog=(_READ,))
    _reject(authorizer, _ANONYMOUS, _PUSH, status=403)
    with pytest.raises(ValidationError):
        Permission(resource="mount:*", action="files.read")
    with pytest.raises(ValidationError):
        RoleDefinition(role_id="gateway-admin", permissions=(_PUSH,))
    with pytest.raises(ValidationError):
        PolicySnapshot(
            owner=_OWNER,
            credentials=(_key(_PEER),),
        )
    assert _allow(authorizer, _ANONYMOUS, _READ) == "open"


def test_admin_qualification_is_per_key_and_open_role_has_parity(tmp_path: Path) -> None:
    """Every catalog action is available to admin, with none inherited by a sibling key."""

    admin = _key(_ADMIN, admin=True)
    ordinary = _key(_ADMIN)
    store = _store(
        tmp_path,
        PolicySnapshot(
            owner=_OWNER,
            principals=(_ADMIN,),
            credentials=(admin, ordinary),
            grants=(ScopedGrant(principal_id=_ADMIN.principal_id, permission=_READ),),
        ),
    )
    catalog = [_READ, _PUSH]
    authorizer = GatewayAuthorizer(store, catalog=lambda: catalog)
    operator = AuthorizationActor.from_credential(admin)
    sibling = AuthorizationActor.from_credential(ordinary)
    assert _allow(authorizer, operator, _READ, _PUSH) == "admin"
    assert _allow(authorizer, sibling, _READ) == "scoped"
    _reject(authorizer, sibling, _PUSH, status=403)

    catalog.append(_ATTACHMENT)
    assert _allow(authorizer, operator, _ATTACHMENT) == "admin"
    signed = authorizer.authorize(operator, (_PUSH,), target=_TARGET, listener_id=_LISTENER)
    state = store.update(
        lambda old: old.model_copy(
            update={"credentials": (admin.model_copy(update={"admin_revision": None}), ordinary)}
        ),
        actor=_ADMIN.principal_id,
        action="admin.remove",
    )
    assert (state.admin_mode, state.roster_revision, state.open_epoch) == ("open", 1, 1)
    assert state.find_credential(admin.key_id) == admin.model_copy(update={"admin_revision": None})
    assert _allow(authorizer, operator, _READ, _PUSH, _ATTACHMENT) == "open"
    assert _allow(authorizer, _ANONYMOUS, _READ, _PUSH, _ATTACHMENT) == "open"
    assert not authorizer.revalidate(signed, target=_TARGET, listener_id=_LISTENER)


def test_demoted_admin_proof_retains_scope_and_new_qualification_has_new_epoch(
    tmp_path: Path,
) -> None:
    """Qualification changes leave ordinary proof intact and fence earlier admin admission."""

    key = _key(_ADMIN, admin=True)
    other = _key(_ADMIN, admin=True)
    store = _store(
        tmp_path,
        PolicySnapshot(
            owner=_OWNER,
            principals=(_ADMIN,),
            credentials=(key, other),
            grants=(ScopedGrant(principal_id=_ADMIN.principal_id, permission=_READ),),
        ),
    )
    authorizer = GatewayAuthorizer(store, catalog=(_READ, _PUSH))
    actor = AuthorizationActor.from_credential(key)
    initial = authorizer.authorize(actor, (_PUSH,), target=_TARGET, listener_id=_LISTENER)
    demoted = key.model_copy(update={"admin_revision": None})
    after = store.update(
        lambda old: old.model_copy(update={"credentials": (demoted, other)}),
        actor=_ADMIN.principal_id,
        action="admin.remove",
    )
    assert (after.admin_mode, after.roster_revision, after.open_epoch) == ("keyed", 1, 0)
    assert _allow(authorizer, actor, _READ) == "scoped"
    _reject(authorizer, actor, _PUSH, status=403)

    restored = store.update(
        lambda old: old.model_copy(update={"credentials": (key, other)}),
        actor=_ADMIN.principal_id,
        action="admin.qualify",
    )
    requalified = restored.find_credential(key.key_id)
    assert requalified is not None
    assert requalified.admin_revision == restored.revision > initial.policy_revision
    assert _allow(authorizer, actor, _PUSH) == "admin"
    assert not authorizer.revalidate(initial, target=_TARGET, listener_id=_LISTENER)


def test_rotation_preserves_grants_and_fences_revoked_enrollment(tmp_path: Path) -> None:
    """Re-enrolling even the original public key cannot revive its old signed actor."""

    admin = _key(_ADMIN, admin=True)
    source = _key(_PEER)
    store = _store(
        tmp_path,
        PolicySnapshot(
            owner=_OWNER,
            principals=(_ADMIN, _PEER),
            credentials=(admin, source),
            grants=(ScopedGrant(principal_id=_PEER.principal_id, permission=_READ),),
        ),
    )
    current = AuthorizationActor.from_credential(source)
    authorizer = GatewayAuthorizer(store, catalog=(_READ,))
    assert _allow(authorizer, current, _READ) == "scoped"
    store.update(
        lambda old: old.model_copy(update={"credentials": (admin,)}),
        actor=_ADMIN.principal_id,
        action="credential.revoke",
    )
    _reject(authorizer, current, _READ, status=401)
    state = store.update(
        lambda old: old.model_copy(update={"credentials": (admin, source)}),
        actor=_ADMIN.principal_id,
        action="credential.enroll",
    )
    replacement = state.find_credential(source.key_id)
    assert replacement is not None and replacement.enrollment_id != source.enrollment_id
    assert _allow(authorizer, AuthorizationActor.from_credential(replacement), _READ) == "scoped"
    _reject(authorizer, current, _READ, status=401)


def test_open_epoch_fences_signed_and_unsigned_work(tmp_path: Path) -> None:
    """A stale open role cannot reappear after first enrollment and final removal."""

    ordinary = _key(_PEER)
    store = _store(
        tmp_path, PolicySnapshot(owner=_OWNER, principals=(_PEER,), credentials=(ordinary,))
    )
    authorizer = GatewayAuthorizer(store, catalog=(_PUSH,))
    signed_actor = AuthorizationActor.from_credential(ordinary)
    decisions = [
        authorizer.authorize(actor, (_PUSH,), target=_TARGET, listener_id=_LISTENER)
        for actor in (_ANONYMOUS, signed_actor)
    ]
    qualified = ordinary.model_copy(update={"admin_revision": 0})
    first = store.update(
        lambda state: state.model_copy(update={"credentials": (qualified,)}),
        actor=_PEER.principal_id,
        action="admin.bootstrap",
        expected_revision=0,
    )
    assert (first.revision, first.open_epoch, first.admin_mode) == (1, 1, "keyed")
    with pytest.raises(GatewayAccessError) as conflict:
        store.update(
            lambda old: old,
            actor=_PEER.principal_id,
            action="admin.bootstrap",
            expected_revision=0,
        )
    assert conflict.value.status_code == 409
    reopened = store.update(
        lambda state: state.model_copy(update={"credentials": (ordinary,)}),
        actor=_PEER.principal_id,
        action="admin.remove",
    )
    assert (reopened.revision, reopened.open_epoch, reopened.admin_mode) == (2, 2, "open")
    for decision in decisions:
        assert not authorizer.revalidate(decision, target=_TARGET, listener_id=_LISTENER)
    assert _allow(authorizer, signed_actor, _PUSH) == "open"


def test_expiry_changes_decisions_without_policy_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Expiry fences direct grants and role assignment without a store edit."""

    source = _key(_PEER)
    store = _store(
        tmp_path,
        PolicySnapshot(
            owner=_OWNER,
            principals=(_ADMIN, _PEER),
            credentials=(_key(_ADMIN, admin=True), source),
            roles=(RoleDefinition(role_id="observer", permissions=(_STATUS,)),),
            role_assignments=(
                RoleAssignment(principal_id=_PEER.principal_id, role_id="observer", expires_at=20),
            ),
            grants=(ScopedGrant(principal_id=_PEER.principal_id, permission=_READ, expires_at=10),),
        ),
    )
    authorizer = GatewayAuthorizer(store, catalog=(_READ, _STATUS))
    actor = AuthorizationActor.from_credential(source)
    monkeypatch.setattr("houmao.gateway.authorization.time.time", lambda: 5)
    decision = authorizer.authorize(actor, (_READ, _STATUS), target=_TARGET, listener_id=_LISTENER)
    monkeypatch.setattr("houmao.gateway.authorization.time.time", lambda: 10)
    assert not authorizer.revalidate(decision, target=_TARGET, listener_id=_LISTENER)
    assert _allow(authorizer, actor, _STATUS) == "scoped"
    _reject(authorizer, actor, _READ, status=403)
    monkeypatch.setattr("houmao.gateway.authorization.time.time", lambda: 20)
    _reject(authorizer, actor, _STATUS, status=403)
    assert store.snapshot().revision == 0


def test_same_target_self_and_listener_are_current(tmp_path: Path) -> None:
    """A scoped self permission requires the verified current target-generation key."""

    store = _store(
        tmp_path,
        PolicySnapshot(owner=_OWNER, principals=(_ADMIN,), credentials=(_key(_ADMIN, admin=True),)),
    )
    key = store.provision_self(_TARGET.incarnation)
    actor = AuthorizationActor.from_self(key)
    authorizer = GatewayAuthorizer(
        store,
        catalog=(_STATUS,),
        supports=lambda permission: permission == _READ,
        supports_self=lambda permission: permission == _READ,
    )
    decision = authorizer.authorize(
        actor, (_READ,), target=_TARGET, listener_id=_LISTENER, current_self=key
    )
    assert decision.basis == "self"
    assert not authorizer.revalidate(
        decision, target=_TARGET, listener_id="replacement-gateway", current_self=key
    )
    assert not authorizer.revalidate(
        decision,
        target=_TARGET,
        listener_id=_LISTENER,
        current_self=key.model_copy(update={"generation_id": "replacement-generation"}),
    )
    _reject(authorizer, actor, _READ, status=401)


def test_handoff_once_and_policy_writes_share_durable_fence(tmp_path: Path) -> None:
    """A completed handoff persists while admin demotion prevents later handoff."""

    admin = _key(_ADMIN, admin=True)
    store = _store(
        tmp_path, PolicySnapshot(owner=_OWNER, principals=(_ADMIN,), credentials=(admin,))
    )
    operator = AuthorizationActor.from_credential(admin)
    authorizer = GatewayAuthorizer(store, catalog=(_PUSH,))
    decision = authorizer.authorize(operator, (_PUSH,), target=_TARGET, listener_id=_LISTENER)
    admitted = authorizer.handoff(
        decision, operation_id="publish-1", target=_TARGET, listener_id=_LISTENER
    )
    assert admitted == decision
    with pytest.raises(GatewayAccessError) as duplicate:
        authorizer.handoff(
            decision, operation_id="publish-1", target=_TARGET, listener_id=_LISTENER
        )
    assert duplicate.value.status_code == 409
    store.update(
        lambda state: state.model_copy(update={"credentials": ()}),
        actor=_ADMIN.principal_id,
        action="credential.revoke",
    )
    with pytest.raises(GatewayAccessError) as refusal:
        authorizer.handoff(
            decision, operation_id="publish-2", target=_TARGET, listener_id=_LISTENER
        )
    assert refusal.value.status_code == 401
    evidence = AuthorizationStore(tmp_path / "policy", _OWNER).audit_entries()
    assert [(entry.action, entry.operation_id, entry.policy_revision) for entry in evidence] == [
        ("credential.revoke", None, 1),
        ("operation.handoff", "publish-1", 0),
        ("policy.initialize", None, 0),
    ]


def test_snapshot_updates_are_visible_across_processes(tmp_path: Path) -> None:
    """A second process commits policy used by the first process's next decision."""

    ordinary = _key(_PEER)
    store = _store(
        tmp_path,
        PolicySnapshot(
            owner=_OWNER,
            principals=(_ADMIN, _PEER),
            credentials=(_key(_ADMIN, admin=True), ordinary),
            grants=(ScopedGrant(principal_id=_PEER.principal_id, permission=_READ),),
        ),
    )
    authorizer = GatewayAuthorizer(store, catalog=(_READ,))
    actor = AuthorizationActor.from_credential(ordinary)
    decision = authorizer.authorize(actor, (_READ,), target=_TARGET, listener_id=_LISTENER)
    subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                (
                    "import sys",
                    "from pathlib import Path",
                    "from houmao.gateway.access_models import GatewayOwner",
                    "from houmao.gateway.authorization_store import AuthorizationStore",
                    "root, agent, context = sys.argv[1:]",
                    "store = AuthorizationStore(Path(root), GatewayOwner(agent_id=agent, "
                    "context_id=context))",
                    "assert store.snapshot().revision == 0",
                    "store.update(lambda state: state.model_copy(update={'grants': ()}), "
                    "actor='owner', action='grant.revoke')",
                )
            ),
            str(tmp_path / "policy"),
            _OWNER.agent_id,
            _OWNER.context_id,
        ],
        check=True,
        timeout=10,
    )
    assert store.snapshot().revision == 1
    assert not authorizer.revalidate(decision, target=_TARGET, listener_id=_LISTENER)
    _reject(authorizer, actor, _READ, status=403)


def test_initialized_policy_survives_reattach_without_reseed(tmp_path: Path) -> None:
    """An owner's first seed remains distinct from the retained live state."""

    key = _key(_ADMIN)
    seed = seed_snapshot(
        _OWNER,
        GatewayLaunchSeed(
            admin_keys=(GatewayAdminKey(principal=_ADMIN.principal_id, public_key=key.public_key),)
        ),
    )
    store = _store(tmp_path, seed)
    updated = store.update(
        lambda old: old.model_copy(update={"credentials": ()}),
        actor=_ADMIN.principal_id,
        action="credential.revoke",
    )
    reopened_store = AuthorizationStore(tmp_path / "policy", _OWNER)
    assert reopened_store.initialize(seed) == updated
    assert updated.credentials == ()
    assert updated.admin_mode == "open"


@pytest.mark.parametrize("fault", ["missing", "old_schema", "symlink", "shared", "foreign"])
def test_invalid_policy_never_becomes_open(tmp_path: Path, fault: str) -> None:
    """Unsafe state fails closed on reads and explicit repeated initialization."""

    store = _store(tmp_path, PolicySnapshot(owner=_OWNER))
    path = tmp_path / "policy" / "authorization.sqlite3"
    if fault == "missing":
        path.unlink()
    elif fault == "old_schema":
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version = 999")
        connection.close()
    elif fault == "symlink":
        actual = path.with_suffix(".real")
        path.rename(actual)
        path.symlink_to(actual)
    elif fault == "shared":
        path.chmod(0o644)
    else:
        store = AuthorizationStore(
            tmp_path / "policy", GatewayOwner(agent_id="other", context_id=_OWNER.context_id)
        )
    for operation in (
        store.snapshot,
        store.initialize,
        lambda: store.initialize(allow_retired=True),
    ):
        with pytest.raises(GatewayAccessError) as unavailable:
            operation()
        assert unavailable.value.status_code == 503
