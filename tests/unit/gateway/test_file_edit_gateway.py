"""Exercise direct proof, draft isolation, and journaled push through the gateway."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
import time
from unittest.mock import Mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.owner_admission import OwnerAdmissionError
from houmao.gateway._access_storage import GatewayAccessError, _private_directory, _write_file
from houmao.gateway.authorization_models import Credential, Permission, PolicySnapshot
from houmao.gateway.file_edits import publication
from houmao.gateway.file_edits.contracts import EDIT, FILE_EDIT_PATH, PUSH, READ
from houmao.gateway.file_edits.journal import PushJournal
from houmao.gateway.file_edits.projection import FileProjection
from houmao.gateway.file_edits.storage import MountStorage
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER
from houmao.gateway.roster import add_admin_key, remove_admin_key
from tests.fixtures.gateway_access import (
    FixtureProofAuth,
    configure_fixture_gateway_access,
    enroll_fixture_admin,
    enroll_fixture_caller,
    fixture_admin_key,
    self_fixture_auth,
)
from tests.unit.agents.realm_controller.test_gateway_access_http import _runtime


class _NativeTransaction:
    """Expose controlled native publication and lost acknowledgement to the fake adapter."""

    def __init__(self, mount: _Mount, operation: str, candidate: str) -> None:
        """Select the exact candidate prepared by the real gateway service."""

        self.mount = mount
        self.operation = operation
        self.candidate = candidate
        self.settlement: dict[str, object] | None = None

    def publish(self) -> dict[str, object]:
        """Atomically switch the same durable marker used by the live adapter."""

        self.mount.publishes += 1
        if self.mount.before_publish is not None:
            self.mount.before_publish()
        with _private_directory(self.mount.projection.root) as directory:
            _write_file(directory, "published", f"{self.candidate}\n{self.operation}\n".encode())
        if self.mount.lose_acknowledgement:
            raise TimeoutError
        evidence = {
            "published_commit": self.candidate,
            "effective_commit": self.candidate,
            "native_settled": True,
            "native_ready": True,
        }
        self.settlement = evidence
        self.mount.evidence[self.operation] = evidence
        return evidence


class _Mount:
    """Use real Git and SQLite state with an immediate, controllable native boundary."""

    def __init__(self, storage: MountStorage, projection: FileProjection) -> None:
        """Select one owner fixture mount."""

        self.storage = storage
        self.projection = projection
        self.before_handoff: Callable[[], None] | None = None
        self.before_publish: Callable[[], None] | None = None
        self.lose_acknowledgement = False
        self.publishes = 0
        self.evidence: dict[str, dict[str, object]] = {}

    def validate(self, _files: dict[str, bytes]) -> None:
        """Accept the storage layer's verified logical paths for this fixture."""

    @contextmanager
    def native_transaction(
        self, operation_id: str, candidate: str, expected: str, *, deadline_monotonic: float
    ) -> Iterator[_NativeTransaction]:
        """Simulate the native maintenance check before the shared policy handoff."""

        assert self.projection.published_marker() == expected
        if self.before_handoff is not None:
            self.before_handoff()
        transaction = _NativeTransaction(self, operation_id, candidate)
        try:
            yield transaction
        finally:
            if transaction.settlement is None and not self.lose_acknowledgement:
                transaction.settlement = {"native_settled": True, "native_ready": True}

    def native_status(self, operation_id: str) -> dict[str, object]:
        """Read a previously recorded result without dispatching native work."""

        return self.evidence.get(operation_id, {})


class _Fixture:
    """Create a test gateway with real admission and a controllable publication adapter."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Supply valid registry identity while isolating every test filesystem."""

        access = configure_fixture_gateway_access(tmp_path, monkeypatch)
        storage = MountStorage(tmp_path / "versioned-mount", access.owner, lineage="test-home")
        self.descriptor = storage.initialize()
        projection = FileProjection(storage.root / "projection")
        projection.initialize(self.descriptor.mount_id, self.descriptor.published_commit, {})
        self.mount = _Mount(storage, projection)
        self.runtime = _runtime(tmp_path)
        monkeypatch.setattr(self.runtime, "_resolve_qualified_file_mounts", lambda: (self.mount,))
        monkeypatch.setattr(self.runtime, "_file_listener_is_current", lambda: True)
        self.client = self._client(self.runtime)
        self.store = access.store
        self.target = access.target.model_dump(mode="json")
        self.fields = {
            "target": self.target,
            "presence_id": self.runtime.m_presence_id,
            "mount_id": self.descriptor.mount_id,
        }
        self.claim = Mock()
        self.claim.active.return_value = True
        self.reserve = Mock(return_value=self.claim)
        monkeypatch.setattr(publication, "reserve_owner_maintenance", self.reserve)
        monkeypatch.setattr(publication, "load_owner_maintenance", lambda *_args: self.claim)

    @staticmethod
    def _client(runtime: GatewayServiceRuntime) -> TestClient:
        """Keep challenge origin consistent with the selected fixture listener."""

        return TestClient(create_app(runtime=runtime), base_url=runtime.owner_connect_url)

    def post(self, name: str, *, fields: dict[str, object] | None = None, **kwargs: object):
        """Send a typed file operation through actual middleware and shared proof."""

        body = {**self.fields, **(fields or {})}
        if name == "mounts":
            body.pop("mount_id", None)
        return self.client.post(f"{FILE_EDIT_PATH}/{name}", json=body, **kwargs)

    @property
    def policy(self):
        """Read the actual current gateway policy for audit evidence assertions."""

        return self.runtime._require_access_policy()

    def candidate(self, *, auth: FixtureProofAuth | None = None) -> str:
        """Commit a candidate without changing the visible revision."""

        opened = self.post(
            "lease/open", fields={"expected_base": self.descriptor.published_commit}, auth=auth
        )
        assert opened.is_success, opened.text
        lease = opened.json()
        draft = {key: lease[key] for key in ("draft_id", "lease_capability")}
        write = self.post(
            "draft/write",
            fields={**draft, "path": "draft/SKILL.md", "content_base64": "aGVsbG8="},
            auth=auth,
        )
        assert write.is_success, write.text
        committed = self.post(
            "draft/commit", fields={**draft, "message": "Save a skill"}, auth=auth
        )
        assert committed.is_success, committed.text
        assert committed.json()["author"]["kind"] == ("anonymous" if auth is None else "operator")
        return committed.json()["commit_id"]

    def push_fields(self, revision: str, operation: str) -> dict[str, object]:
        """Pin the current target and exact expected base for a new attempt."""

        return {
            "commit_id": revision,
            "operation_id": operation,
            "expected_base": self.descriptor.published_commit,
        }


def test_open_file_workflow_recovers_publication_and_never_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Distinguish the draft, durable marker, and subsequently observed activation."""

    fixture = _Fixture(tmp_path, monkeypatch)
    discovered = fixture.post("mounts")
    assert discovered.json()["mounts"][0]["resource"] == fixture.descriptor.resource
    candidate = fixture.candidate()
    assert fixture.post("list").json()["entries"] == []
    assert fixture.post("diff", fields={"commit_id": candidate}).json()["changes"][0]["path"] == (
        "draft/SKILL.md"
    )

    fixture.reserve.side_effect = OwnerAdmissionError("not_ready", "Native work is active.")
    busy = fixture.post("push", fields=fixture.push_fields(candidate, "busy"))
    assert busy.json()["outcome"] == "busy"
    assert fixture.mount.publishes == 0
    fixture.reserve.side_effect = None

    fixture.mount.lose_acknowledgement = True
    fields = fixture.push_fields(candidate, "successful")
    lost = fixture.post("push", fields=fields)
    assert lost.is_success, lost.text
    assert lost.json()["published_commit"] == candidate
    assert lost.json()["activation"] == "unknown"
    assert fixture.mount.publishes == 1

    record = PushJournal(fixture.mount.storage.root).read("successful")
    fixture.mount.evidence[record.handoff_id] = {
        "published_commit": candidate,
        "effective_commit": candidate,
        "native_settled": True,
        "native_ready": True,
    }
    status = fixture.post("status", fields={"operation_id": "successful"})
    assert status.json()["effective_commit"] == candidate
    assert status.json()["native_ready"] is True
    fixture.claim.finish.assert_called()
    repeat = fixture.post("push", fields=fields)
    assert repeat.json() == status.json()
    assert fixture.mount.publishes == 1
    assert fixture.post("read", fields={"path": "draft/SKILL.md"}).json()["revision"] == candidate
    stale = fixture.post("push", fields=fixture.push_fields(candidate, "stale"))
    assert stale.json()["outcome"] == "conflict"


def test_scheduled_push_waits_for_native_idle_and_keeps_one_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retry only the native pre-handoff busy race and keep status observational."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()
    auth = self_fixture_auth(fixture.runtime)
    fields = {**fixture.push_fields(candidate, "when-idle"), "when_idle": True}
    assert fixture.post("push", fields=fields).status_code == 403
    accepted = fixture.post("push", fields=fields, auth=auth)
    assert accepted.json()["outcome"] == "queued"
    assert fixture.post("status", fields={"operation_id": "when-idle"}, auth=auth).json() == (
        accepted.json()
    )
    fixture.reserve.assert_not_called()

    def busy() -> None:
        """Simulate a native turn starting first after owner reservation."""

        raise GatewayAccessError(409, "file_native_busy")

    fixture.mount.before_handoff = busy
    service = fixture.runtime.m_file_edits
    assert service is not None
    service.dispatch_scheduled()
    fixture.claim.release_before_handoff.assert_called_once()
    journal = PushJournal(fixture.mount.storage.root)
    first_attempt = journal.read("when-idle")
    assert first_attempt.receipt.outcome == "queued"
    assert fixture.policy.handoff_evidence(first_attempt.handoff_id) is None

    fixture.mount.before_handoff = None
    service.dispatch_scheduled()
    settled = journal.read("when-idle")
    assert settled.receipt.outcome == "published"
    assert settled.receipt.effective_commit == candidate
    assert settled.handoff_id != first_attempt.handoff_id
    assert fixture.policy.handoff_evidence(settled.handoff_id) is not None
    assert fixture.post("push", fields=fields, auth=auth).json()["outcome"] == "published"
    assert fixture.post("push", fields={**fields, "when_idle": False}, auth=auth).status_code == 409
    assert fixture.mount.publishes == 1


def test_multiple_exact_mounts_have_independent_drafts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discover two owner-exposed resources and acquire a lease in each independent store."""

    fixture = _Fixture(tmp_path, monkeypatch)
    storage = MountStorage(
        tmp_path / "versioned-mount",
        fixture.store.snapshot().owner,
        lineage="test-home",
        name="mcp",
        kind="mcp",
    )
    second = storage.initialize()
    projection = FileProjection(storage.root / "projection")
    projection.initialize(second.mount_id, second.published_commit, {})
    service = fixture.runtime.m_file_edits
    assert service is not None
    monkeypatch.setattr(
        service, "m_resolve_mounts", lambda: (fixture.mount, _Mount(storage, projection))
    )
    discovered = fixture.post("mounts").json()["mounts"]
    assert {item["kind"]: item["mount_id"] for item in discovered} == {
        "skills": fixture.descriptor.mount_id,
        "mcp": second.mount_id,
    }
    for descriptor in (fixture.descriptor, second):
        opened = fixture.post(
            "lease/open",
            fields={"mount_id": descriptor.mount_id, "expected_base": descriptor.published_commit},
        )
        assert opened.is_success, opened.text


def test_queued_push_retires_on_managed_self_rotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fence the original proof even when the same generation can submit a fresh intent."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()
    fields = {**fixture.push_fields(candidate, "retired-key"), "when_idle": True}
    old_auth = self_fixture_auth(fixture.runtime)
    assert fixture.post("push", fields=fields, auth=old_auth).json()["outcome"] == "queued"
    generation = str(fixture.target["incarnation"])
    with fixture.store.transaction() as transaction:
        transaction.replace_self(
            generation,
            expected_revision=transaction.self_revision(generation),
            signer=Ed25519PrivateKey.generate(),
            actor="fixture-owner",
        )
    service = fixture.runtime.m_file_edits
    assert service is not None
    service.dispatch_scheduled()
    fixture.reserve.assert_not_called()
    new_auth = self_fixture_auth(fixture.runtime)
    status = fixture.post("status", fields={"operation_id": "retired-key"}, auth=new_auth)
    assert status.json()["outcome"] == "refused"
    assert (
        fixture.post(
            "push", fields={**fields, "operation_id": "current-key"}, auth=new_auth
        ).json()["outcome"]
        == "queued"
    )
    service.dispatch_scheduled()
    assert fixture.mount.publishes == 1


def test_direct_gateway_authentication_and_scoped_mount_visibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep file permissions exact and refuse delegated or stale caller proof."""

    fixture = _Fixture(tmp_path, monkeypatch)
    for header in (RELAY_HEADER, BACKING_HEADER, "Houmao-Signature"):
        assert fixture.post("mounts", headers={header: "invalid"}).status_code == 401
    assert fixture.post("mounts", fields={"presence_id": "retired"}).status_code == 409
    candidate = fixture.candidate()
    admin, admin_path = fixture_admin_key(tmp_path, "file-admin")
    enroll_fixture_admin(fixture.client, admin, admin_path)
    reviewer, reviewer_path = fixture_admin_key(tmp_path, "reviewer")
    enroll_fixture_caller(
        fixture.runtime,
        reviewer,
        permissions=(Permission(resource=fixture.descriptor.resource, action=PUSH),),
    )
    auth = FixtureProofAuth(reviewer_path)
    assert fixture.post("mounts", auth=auth).json() == {"mounts": []}
    assert fixture.post("list", auth=auth).status_code == 403
    assert fixture.post("status", fields={"operation_id": "missing"}, auth=auth).status_code == 403
    assert fixture.post("mounts").status_code == 401
    result = fixture.post("push", fields=fixture.push_fields(candidate, "publish"), auth=auth)
    assert result.json()["publisher"]["principal_id"] == reviewer.principal
    assert result.json()["outcome"] == "published"
    assert fixture.post("status", fields={"operation_id": "publish"}, auth=auth).status_code == 403
    selected_admin = FixtureProofAuth(admin_path)
    assert fixture.post("mounts", auth=selected_admin).json()["mounts"]


@pytest.mark.parametrize("keyed", [False, True])
def test_direct_push_revocation_uses_current_roster_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keyed: bool
) -> None:
    """Apply direct grant revocation independently of open and keyed admission."""

    fixture = _Fixture(tmp_path, monkeypatch)
    if keyed:
        admin, admin_path = fixture_admin_key(tmp_path, "owner")
        enroll_fixture_admin(fixture.client, admin, admin_path)
    reviewer, reviewer_path = fixture_admin_key(tmp_path, "reviewer")
    push_permission = Permission(resource=fixture.descriptor.resource, action=PUSH)
    enroll_fixture_caller(
        fixture.runtime,
        reviewer,
        permissions=(
            Permission(resource=fixture.descriptor.resource, action=READ),
            Permission(resource=fixture.descriptor.resource, action=EDIT),
            push_permission,
        ),
    )
    auth = FixtureProofAuth(reviewer_path)
    candidate = fixture.candidate(auth=auth)
    revoked = fixture.store.update(
        lambda state: state.model_copy(
            update={
                "grants": tuple(row for row in state.grants if row.permission != push_permission)
            }
        ),
        actor="owner",
        action="grant.revoke",
    )
    assert {row.permission.action for row in revoked.grants} == {READ, EDIT}

    result = fixture.post("push", fields=fixture.push_fields(candidate, "after-revoke"), auth=auth)
    if keyed:
        assert result.status_code == 403, result.text
        assert result.json() == {"detail": {"error_code": "insufficient_authority"}}
        assert fixture.mount.publishes == 0
        assert fixture.mount.projection.published_marker() == fixture.descriptor.published_commit
        diff = fixture.post("diff", fields={"commit_id": candidate}, auth=auth)
        assert diff.is_success, diff.text
        assert diff.json()["changes"][0]["path"] == "draft/SKILL.md"
    else:
        assert result.is_success, result.text
        assert result.json()["published_commit"] == candidate
        assert result.json()["publisher"]["principal_id"] == reviewer.principal
        assert fixture.mount.publishes == 1


@pytest.mark.parametrize("signed", [False, True])
def test_open_epoch_change_refuses_pending_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signed: bool
) -> None:
    """Fence both signed and unsigned admissions through an open roster cycle."""

    fixture = _Fixture(tmp_path, monkeypatch)
    key, path = fixture_admin_key(tmp_path, "peer")
    enroll_fixture_caller(
        fixture.runtime,
        key,
        permissions=(Permission(resource=fixture.descriptor.resource, action=EDIT),),
    )
    auth = FixtureProofAuth(path) if signed else None
    candidate = fixture.candidate(auth=auth)
    admin, _ = fixture_admin_key(tmp_path, "transient-admin")

    def reopen() -> None:
        """Cycle the retained mode after initial proof and before native handoff."""

        fixture.store.update(
            lambda state: add_admin_key(state, admin), actor="owner", action="admin.key.add"
        )
        fixture.store.update(
            lambda state: remove_admin_key(state, admin.key_id),
            actor="owner",
            action="admin.key.remove",
        )

    fixture.mount.before_handoff = reopen
    response = fixture.post("push", fields=fixture.push_fields(candidate, "old-epoch"), auth=auth)
    assert response.status_code in {403, 409}, response.text
    assert fixture.mount.publishes == 0
    assert fixture.mount.projection.published_marker() == fixture.descriptor.published_commit


def test_named_admin_demotion_before_handoff_refuses_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin the original per-key admin qualification even when open mode resumes."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()
    admin, path = fixture_admin_key(tmp_path, "publisher")
    enroll_fixture_admin(fixture.client, admin, path)

    def revoke() -> None:
        """Demote the specific key after the owner takes native maintenance."""

        fixture.store.update(
            lambda state: remove_admin_key(state, admin.key_id),
            actor="owner",
            action="admin.key.remove",
        )

    fixture.mount.before_handoff = revoke
    response = fixture.post(
        "push", fields=fixture.push_fields(candidate, "removed-admin"), auth=FixtureProofAuth(path)
    )
    assert response.status_code in {403, 409}, response.text
    assert fixture.mount.publishes == 0
    fixture.claim.release_before_handoff.assert_called()


def test_replacement_mount_requires_new_exact_grants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retire grants and requests even when a replacement has the same display name."""

    fixture = _Fixture(tmp_path, monkeypatch)
    admin, path = fixture_admin_key(tmp_path, "owner")
    enroll_fixture_admin(fixture.client, admin, path)
    peer, peer_path = fixture_admin_key(tmp_path, "old-reader")
    enroll_fixture_caller(
        fixture.runtime,
        peer,
        permissions=(Permission(resource=fixture.descriptor.resource, action=READ),),
    )
    auth = FixtureProofAuth(peer_path)
    assert fixture.post("mounts", auth=auth).json()["mounts"]
    storage = MountStorage(
        tmp_path / "another-mount", fixture.store.snapshot().owner, lineage="another-home"
    )
    replacement = storage.initialize()
    projection = FileProjection(storage.root / "projection")
    projection.initialize(replacement.mount_id, replacement.published_commit, {})
    assert replacement.name == fixture.descriptor.name
    fixture.mount = _Mount(storage, projection)
    fixture.runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=fixture.runtime.m_paths.gateway_root, host="127.0.0.1", port=43123
    )
    monkeypatch.setattr(fixture.runtime, "_resolve_qualified_file_mounts", lambda: (fixture.mount,))
    fixture.fields["presence_id"] = fixture.runtime.m_presence_id
    fixture.client = fixture._client(fixture.runtime)
    assert fixture.post("mounts", auth=auth).json() == {"mounts": []}
    assert fixture.post("list", auth=auth).status_code == 404
    assert (
        fixture.post("list", auth=auth, fields={"mount_id": replacement.mount_id}).status_code
        == 403
    )


def test_signed_draft_follows_principal_and_current_unexpired_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject former keys and expired grants, and resume with a replacement key."""

    fixture = _Fixture(tmp_path, monkeypatch)
    admin, path = fixture_admin_key(tmp_path, "owner")
    enroll_fixture_admin(fixture.client, admin, path)
    peer, old_path = fixture_admin_key(tmp_path, "drafter")
    replacement, new_path = fixture_admin_key(tmp_path, "rotated")
    permission = Permission(resource=fixture.descriptor.resource, action=EDIT)
    enroll_fixture_caller(fixture.runtime, peer, permissions=(permission,))
    old_auth = FixtureProofAuth(old_path)
    new_auth = FixtureProofAuth(new_path)
    other, other_path = fixture_admin_key(tmp_path, "other-editor")
    enroll_fixture_caller(fixture.runtime, other, permissions=(permission,))
    lease = fixture.post(
        "lease/open", fields={"expected_base": fixture.descriptor.published_commit}, auth=old_auth
    ).json()
    assert lease["lease_capability"] is None
    fields = {"draft_id": lease["draft_id"], "path": "alpha/SKILL.md", "content_base64": "YQ=="}
    assert (
        fixture.post("draft/write", fields=fields, auth=FixtureProofAuth(other_path)).status_code
        == 403
    )

    def rotate(state: PolicySnapshot) -> PolicySnapshot:
        """Replace only the peer's enrollment while keeping the principal."""

        updated = Credential(principal_id=peer.principal, public_key=replacement.public_key)
        remaining = tuple(key for key in state.credentials if key.key_id != peer.key_id)
        return state.model_copy(update={"credentials": (*remaining, updated)})

    fixture.store.update(rotate, actor="owner", action="policy.credential.rotate")
    assert fixture.post("draft/write", fields=fields, auth=old_auth).status_code == 401
    assert fixture.post("draft/write", fields=fields, auth=new_auth).is_success

    def expire(state: PolicySnapshot) -> PolicySnapshot:
        """Set the same grant's expiry to a known past clock value."""

        expired = int(time.time()) - 1
        return state.model_copy(
            update={
                "grants": tuple(
                    row.model_copy(update={"expires_at": expired})
                    if row.permission == permission
                    else row
                    for row in state.grants
                )
            }
        )

    fixture.store.update(expire, actor="owner", action="policy.grant.put")
    assert fixture.post("draft/write", fields=fields, auth=new_auth).status_code == 403


@pytest.mark.parametrize("winner", ["policy", "handoff"])
def test_scoped_revocation_orders_against_shared_publication_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winner: str
) -> None:
    """Keep publication and disclosure ordering independent after admitted work wins."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()
    admin, admin_path = fixture_admin_key(tmp_path, "owner")
    enroll_fixture_admin(fixture.client, admin, admin_path)
    peer, peer_path = fixture_admin_key(tmp_path, "reviewer")
    permission = Permission(resource=fixture.descriptor.resource, action=PUSH)
    enroll_fixture_caller(fixture.runtime, peer, permissions=(permission,))

    def revoke() -> None:
        """Revoke only the exact grant under the same owner policy writer."""

        fixture.store.update(
            lambda state: state.model_copy(update={"grants": ()}),
            actor="owner",
            action="policy.grant.revoke",
        )

    if winner == "policy":
        fixture.mount.before_handoff = revoke
    else:
        fixture.mount.before_publish = revoke
    result = fixture.post(
        "push", fields=fixture.push_fields(candidate, "race"), auth=FixtureProofAuth(peer_path)
    )
    assert result.status_code == 403, result.text
    record = PushJournal(fixture.mount.storage.root).read("race")
    receipt = fixture.post(
        "status", fields={"operation_id": "race"}, auth=FixtureProofAuth(admin_path)
    ).json()
    assert receipt["publisher"]["principal_id"] == peer.principal
    assert receipt["outcome"] == ("refused" if winner == "policy" else "published")
    assert (fixture.policy.handoff_evidence(record.handoff_id) is None) == (winner == "policy")


def test_interrupted_shared_handoff_releases_only_after_settled_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recover a durable handoff before a marker switch without replaying it."""

    class Interrupted(Exception):
        """Simulate stopping the dispatcher without normal settlement handling."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()

    def crash() -> None:
        """Interrupt after shared handoff and before native publication settles."""

        raise Interrupted

    fixture.mount.before_publish = crash
    fields = fixture.push_fields(candidate, "interrupted")
    with pytest.raises(Interrupted):
        fixture.post("push", fields=fields)
    record = PushJournal(fixture.mount.storage.root).read("interrupted")
    assert fixture.policy.handoff_evidence(record.handoff_id) is not None
    assert fixture.mount.projection.published_marker() == fixture.descriptor.published_commit
    outcome = fixture.post("status", fields={"operation_id": "interrupted"}).json()
    assert outcome["outcome"] == "unknown" and outcome["activation"] == "unknown"
    fixture.claim.finish.assert_called_with(
        evidence="file_publication_settlement", settled=False, ready=False
    )
    fixture.mount.evidence[record.handoff_id] = {"native_settled": True, "native_ready": True}
    resumed = fixture.post("push", fields=fields).json()
    assert resumed["outcome"] == "refused" and resumed["activation"] == "unknown"
    fixture.claim.finish.assert_called_with(
        evidence="file_publication_settlement", settled=True, ready=True
    )
    conflict = fixture.post("push", fields={**fields, "expected_base": candidate})
    assert conflict.status_code == 409
    assert fixture.mount.publishes == 1


def test_foreign_projected_drift_refuses_before_native_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Block a valid candidate once the original published projection has changed."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()
    path = fixture.mount.projection.root / "revisions" / fixture.descriptor.published_commit
    (path / "foreign.txt").write_text("unmanaged change")
    result = fixture.post("push", fields=fixture.push_fields(candidate, "drift"))
    assert result.json()["outcome"] == "conflict"
    fixture.reserve.assert_not_called()
    assert fixture.mount.publishes == 0


def test_new_listener_resolves_only_the_operation_in_the_durable_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recover a complete tree after a lost journal settlement under a new listener."""

    class Interrupted(Exception):
        """Simulate a dispatcher exiting between two durable steps."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()
    fixture.reserve.side_effect = Interrupted
    older = fixture.push_fields(candidate, "unadmitted")
    with pytest.raises(Interrupted):
        fixture.post("push", fields=older)
    fixture.reserve.side_effect = None

    with monkeypatch.context() as interrupted:
        interrupted.setattr(publication.FilePublication, "_settle", Mock(side_effect=Interrupted))
        current = fixture.push_fields(candidate, "selected")
        with pytest.raises(Interrupted):
            fixture.post("push", fields=current)

    journal = PushJournal(fixture.mount.storage.root)
    selected = journal.read("selected")
    assert selected.receipt.outcome == "pending"
    assert fixture.mount.projection.publication_identity() == (candidate, selected.handoff_id)
    assert fixture.mount.storage.published_commit() == fixture.descriptor.published_commit
    fixture.runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=fixture.runtime.m_paths.gateway_root, host="127.0.0.1", port=43123
    )
    monkeypatch.setattr(fixture.runtime, "_resolve_qualified_file_mounts", lambda: (fixture.mount,))
    fixture.fields["presence_id"] = fixture.runtime.m_presence_id
    fixture.client = fixture._client(fixture.runtime)
    listed = fixture.post("list")
    assert listed.json()["revision"] == candidate
    assert journal.read("selected").receipt.activation == "unknown"
    assert journal.read("unadmitted").receipt.outcome == "pending"
    repeated = fixture.post("push", fields=current)
    assert repeated.json()["effective_commit"] == candidate
    assert fixture.mount.publishes == 1


def test_candidate_bytes_are_rechecked_under_native_maintenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Detect changed prepared bytes before the caller's handoff or marker switch."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()

    def change_projection() -> None:
        """Alter a prepared file after validation and before the exact handoff."""

        root = fixture.mount.projection.root / "revisions" / candidate
        (root / "draft" / "SKILL.md").write_bytes(b"foreign bytes")

    fixture.mount.before_handoff = change_projection
    result = fixture.post("push", fields=fixture.push_fields(candidate, "prepared-drift")).json()
    assert result["outcome"] == "conflict"
    record = PushJournal(fixture.mount.storage.root).read("prepared-drift")
    assert fixture.policy.handoff_evidence(record.handoff_id) is None
    assert fixture.mount.publishes == 0


def test_missing_native_open_response_keeps_admission_until_reconciled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retain the exact native reservation even before publication authority exists."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()

    def lose_response() -> None:
        """Simulate a native hold whose acknowledgement never reached the gateway."""

        raise GatewayAccessError(503, "file_native_admission_unconfirmed")

    fixture.mount.before_handoff = lose_response
    response = fixture.post("push", fields=fixture.push_fields(candidate, "lost-open"))
    assert response.json()["outcome"] == "unknown"
    fixture.claim.release_before_handoff.assert_not_called()
    fixture.claim.retain_before_handoff.assert_called_once()
    record = PushJournal(fixture.mount.storage.root).read("lost-open")
    assert fixture.policy.handoff_evidence(record.handoff_id) is None
    assert (
        fixture.post("status", fields={"operation_id": "lost-open"}).json()["outcome"] == "unknown"
    )
    fixture.mount.evidence[record.handoff_id] = {"native_settled": True, "native_ready": True}
    settled = fixture.post("status", fields={"operation_id": "lost-open"}).json()
    assert settled["outcome"] == "unavailable"
    assert fixture.mount.publishes == 0


def test_verified_receipt_survives_interrupted_git_index_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep observed publication attributable while repairing its logical index."""

    fixture = _Fixture(tmp_path, monkeypatch)
    candidate = fixture.candidate()

    def fail_index_update(*_args: object) -> None:
        """Confirm publication was retained before trying to advance the index."""

        record = PushJournal(fixture.mount.storage.root).read("index-repair")
        assert record.receipt.effective_commit == candidate
        raise OSError("synthetic index interruption")

    with monkeypatch.context() as interrupted:
        interrupted.setattr(fixture.mount.storage, "advance_published", fail_index_update)
        response = fixture.post("push", fields=fixture.push_fields(candidate, "index-repair"))
        assert response.json()["published_commit"] == candidate
    assert fixture.mount.storage.published_commit() == fixture.descriptor.published_commit
    assert fixture.post("list").json()["revision"] == candidate
    receipt = fixture.post("status", fields={"operation_id": "index-repair"}).json()
    assert receipt["effective_commit"] == candidate
    assert fixture.mount.publishes == 1
