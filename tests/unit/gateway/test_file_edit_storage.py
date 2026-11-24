"""Exercise owner-private drafts and Git history with the Git binary unavailable."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import shutil
from threading import Barrier
import time
from types import SimpleNamespace

from dulwich.objects import Commit
from dulwich.repo import Repo
from pydantic import ValidationError
import pytest

from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.access_models import GatewayOwner, GatewayTarget
from houmao.gateway.authorization_models import (
    AuthorizationActor,
    AuthorizationDecision,
    Permission,
)
from houmao.gateway.file_edits import git_objects, storage
from houmao.gateway.file_edits.contracts import (
    EDIT,
    READ,
    FileActor,
    FileDiffRequest,
    FileDraftCommitRequest,
    FileDraftListRequest,
    FileDraftOpenRequest,
    FileDraftPathRequest,
    FileDraftReceipt,
    FileDraftRenameRequest,
    FileDraftRequest,
    FileDraftWriteRequest,
    FileHistoryRequest,
    FileListRequest,
    FileReadRequest,
)
from houmao.gateway.file_edits.git_objects import object_id
from houmao.gateway.file_edits.storage import MountStorage


def _fence(_decision: AuthorizationDecision) -> None:
    """Accept the test's already-verified gateway identity."""


@dataclass(frozen=True)
class Mount:
    """Provide one owner, mounted storage, and synthetic admitted peer."""

    store: MountStorage
    target: GatewayTarget
    mount_id: str
    initial: str

    @property
    def coordinates(self) -> dict[str, object]:
        """Select the live test mount."""

        return {"target": self.target, "presence_id": "listener", "mount_id": self.mount_id}

    @staticmethod
    def editor() -> FileActor:
        """Return verified logical peer attribution."""

        return FileActor(
            kind="agent", principal_id="peer", logical_agent_id="reviewer", label="Reviewer"
        )

    def decision(
        self, action: str, *, actor: AuthorizationActor | None = None, epoch: int | None = None
    ) -> AuthorizationDecision:
        """Create admitted authority for the requested effect."""

        return AuthorizationDecision(
            actor=actor
            or AuthorizationActor(
                kind="credential",
                principal_id="peer",
                key_id="SHA256:" + "A" * 43,
                enrollment_id="first-key",
            ),
            target=self.target,
            listener_id="listener",
            permissions=(Permission(resource=f"files:{self.mount_id}", action=action),),
            basis="open" if epoch is not None else "scoped",
            policy_id="policy",
            policy_revision=0,
            open_epoch=epoch,
        )

    def open(self, base: str | None = None) -> FileDraftReceipt:
        """Open a draft for the test peer's attributed edits."""

        return self.store.lease_open(
            FileDraftOpenRequest(expected_base=base or self.initial, **self.coordinates),
            decision=self.decision(EDIT),
            actor=self.editor(),
            fence=_fence,
        )

    def draft(self, opened: FileDraftReceipt) -> dict[str, object]:
        """Select the current lease for request construction."""

        return {
            **self.coordinates,
            "draft_id": opened.draft_id,
            "lease_capability": opened.lease_capability,
        }

    def write(self, lease: FileDraftReceipt, path: str, data: bytes) -> None:
        """Apply one private regular file under the chosen lease."""

        self.store.draft_write(
            FileDraftWriteRequest(
                path=path, content_base64=base64.b64encode(data).decode(), **self.draft(lease)
            ),
            content=data,
            decision=self.decision(EDIT),
            actor=self.editor(),
            fence=_fence,
        )


@pytest.fixture
def mount(tmp_path: Path) -> Mount:
    """Provision one explicitly owned test home."""

    owner = GatewayOwner(agent_id="writer", context_id="test-owner")
    target = GatewayTarget(owner=owner, incarnation="generation")
    store = MountStorage(tmp_path, owner, lineage="first-home")
    result = store.initialize()
    return Mount(store, target, result.mount_id, result.published_commit)


def test_git_history_works_without_git_executable(
    mount: Mount, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Save an attributed commit independently of its publication and undo with ancestry."""

    monkeypatch.setenv("PATH", "")
    assert shutil.which("git") is None
    lease = mount.open()
    mount.write(lease, "skill/docs/SKILL.md", b"---\nname: my-skill\n---\nRevision 1\n")
    draft = mount.draft(lease)
    mount.store.draft_mkdir(
        FileDraftPathRequest(path="empty", **draft),
        decision=mount.decision(EDIT),
        actor=mount.editor(),
        fence=_fence,
    )
    saved = mount.store.draft_commit(
        FileDraftCommitRequest(message="Save first skill", **draft),
        decision=mount.decision(EDIT),
        actor=mount.editor(),
        fence=_fence,
        validate=lambda _: None,
    )
    assert saved.base_commit == mount.initial
    assert saved.author == mount.editor()
    assert saved.actor == mount.editor()
    assert saved.committer == mount.target.owner.agent_id
    assert mount.store.published_commit() == mount.initial
    assert not mount.store.published_files()
    with Repo(mount.store.root / "git") as repo:
        commit = repo[object_id(saved.commit_id)]
        assert isinstance(commit, Commit)
        assert commit.author.startswith(b"Reviewer <agent-")
        assert commit.committer.startswith(b"Houmao gateway writer <gateway-")
        assert commit.parents == [object_id(mount.initial)]
    candidate = mount.store.candidate(saved.commit_id)
    assert candidate.base_commit == mount.initial
    assert sorted(candidate.files) == ["skill/docs/SKILL.md"]
    diff = mount.store.diff(
        FileDiffRequest(commit_id=saved.commit_id, **mount.coordinates),
        decision=mount.decision(READ),
        fence=_fence,
    )
    assert diff.changes[0].change == "added"
    assert "Revision 1" in (diff.changes[0].patch or "")
    assert diff.changes[0].after_sha256
    assert mount.store.advance_published(mount.initial, saved.commit_id) == saved.commit_id
    assert mount.store.advance_published(mount.initial, saved.commit_id) == saved.commit_id
    old = mount.store.list(
        FileListRequest(revision=mount.initial, **mount.coordinates),
        decision=mount.decision(READ),
        fence=_fence,
    )
    assert old.revision == mount.initial and not old.entries
    current = mount.store.read(
        FileReadRequest(path="skill/docs/SKILL.md", **mount.coordinates),
        decision=mount.decision(READ),
        fence=_fence,
    )
    assert current.revision == saved.commit_id
    assert b"Revision 1" in base64.b64decode(current.content_base64)

    rollback = mount.open(saved.commit_id)
    mount.store.draft_delete(
        FileDraftPathRequest(path="skill", **mount.draft(rollback)),
        decision=mount.decision(EDIT),
        actor=mount.editor(),
        fence=_fence,
    )
    restored = mount.store.draft_commit(
        FileDraftCommitRequest(message="Restore initial contents", **mount.draft(rollback)),
        decision=mount.decision(EDIT),
        actor=mount.editor(),
        fence=_fence,
        validate=lambda _: None,
    )
    assert restored.commit_id != mount.initial
    assert not mount.store.candidate(restored.commit_id).files
    mount.store.advance_published(saved.commit_id, restored.commit_id)
    history = mount.store.history(
        FileHistoryRequest(limit=2, **mount.coordinates),
        decision=mount.decision(READ),
        fence=_fence,
    )
    assert [entry.commit_id for entry in history.commits] == [restored.commit_id, saved.commit_id]
    assert history.next_after == saved.commit_id
    assert mount.store.published_files(saved.commit_id) == candidate.files


def test_same_git_author_and_contents_preserve_separate_principal_attribution(
    mount: Mount, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retain distinct drafts by principals that share a Git author and timestamp."""

    monkeypatch.setattr(git_objects, "time", SimpleNamespace(time=lambda: 1_735_689_600.0))
    message = "Save shared skill\n\nPreserve the exact message."
    path = "review/SKILL.md"
    content = b"Identical contents"
    peers = (
        mount.editor(),
        mount.editor().model_copy(update={"principal_id": "another-peer"}),
    )
    commit_ids = []
    draft_ids = []
    for peer in peers:
        proof = AuthorizationActor(
            kind="credential",
            principal_id=peer.principal_id,
            key_id="SHA256:" + ("A" if peer == peers[0] else "B") * 43,
            enrollment_id=f"{peer.principal_id}-enrollment",
        )
        decision = mount.decision(EDIT, actor=proof)
        opened = mount.store.lease_open(
            FileDraftOpenRequest(expected_base=mount.initial, **mount.coordinates),
            decision=decision,
            actor=peer,
            fence=_fence,
        )
        draft = mount.draft(opened)
        mount.store.draft_write(
            FileDraftWriteRequest(
                path=path, content_base64=base64.b64encode(content).decode(), **draft
            ),
            content=content,
            decision=decision,
            actor=peer,
            fence=_fence,
        )
        saved = mount.store.draft_commit(
            FileDraftCommitRequest(message=message, **draft),
            decision=decision,
            actor=peer,
            fence=_fence,
            validate=lambda _: None,
        )
        assert saved.author == saved.actor == peer
        commit_ids.append(saved.commit_id)
        draft_ids.append(opened.draft_id)

    assert len(set(commit_ids)) == 2
    history = mount.store.history(
        FileHistoryRequest(history="candidates", **mount.coordinates),
        decision=mount.decision(READ),
        fence=_fence,
    )
    assert {commit.commit_id: commit.author for commit in history.commits} == dict(
        zip(commit_ids, peers, strict=True)
    )
    with Repo(mount.store.root / "git") as repo:
        first, second = [repo[object_id(commit_id)] for commit_id in commit_ids]
        assert isinstance(first, Commit) and isinstance(second, Commit)
        assert first.author == second.author
        assert first.author_time == second.author_time
        assert first.tree == second.tree
        assert first.message == second.message == message.encode()
        for commit, draft_id in zip((first, second), draft_ids, strict=True):
            commit.check()
            header = commit.as_raw_string().partition(b"\n\n")[0]
            assert f"houmao-draft {draft_id}".encode() in header.splitlines()


def test_mount_identity_is_retained_and_fresh_homes_have_private_history(
    mount: Mount, tmp_path: Path
) -> None:
    """Prevent a replaced home with the same name from inheriting object access."""

    reopened = MountStorage(tmp_path, mount.target.owner, lineage="first-home")
    new_home = MountStorage(tmp_path, mount.target.owner, lineage="new-home")
    assert reopened.initialize() == mount.store.describe()
    details = new_home.initialize()
    assert details.name == reopened.describe().name
    assert details.mount_id != mount.mount_id
    assert details.published_commit != mount.initial
    with pytest.raises(GatewayAccessError, match="not found") as missing:
        new_home.published_files(mount.initial)
    assert missing.value.code == "unknown_revision"
    assert reopened.root.stat().st_mode & 0o777 == 0o700


def test_only_one_lease_can_open_and_stale_upload_cannot_modify_replacement(
    mount: Mount, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fence callers concurrently selecting the same mount and later expire the winner."""

    now = time.time()
    monkeypatch.setattr(storage, "time", SimpleNamespace(time=lambda: now))
    start = Barrier(2)

    def attempt() -> FileDraftReceipt | str:
        """Compete with another request for the exact same retained lease."""

        start.wait(timeout=5)
        try:
            return mount.open()
        except GatewayAccessError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt)
        second = pool.submit(attempt)
        leases = [first.result(timeout=10), second.result(timeout=10)]
    old = next(value for value in leases if isinstance(value, FileDraftReceipt))
    assert "draft_busy" in leases
    now = old.expires_at + 1
    replacement = mount.open()
    with pytest.raises(GatewayAccessError) as expired:
        mount.write(old, "stale.md", b"old edit")
    assert expired.value.code == "unknown_draft"
    directory = mount.store.draft_list(
        FileDraftListRequest(**mount.draft(replacement)),
        decision=mount.decision(EDIT),
        fence=_fence,
    )
    assert not directory.entries
    mount.store.draft_abort(
        FileDraftRequest(**mount.draft(replacement)),
        decision=mount.decision(EDIT),
        actor=mount.editor(),
        fence=_fence,
    )
    assert mount.open().draft_id != replacement.draft_id


def test_paths_and_both_rename_endpoints_are_fenced(mount: Mount) -> None:
    """Keep all mutations in the draft and reject noncanonical destination paths."""

    lease = mount.open()
    mount.write(lease, "one/value.md", b"original")
    for source, dest in [
        ("../one", "two"),
        ("one", "two/../three"),
        ("one", "one/child"),
        ("one", "/two"),
        ("one", "bad//dest"),
        ("one", "two/.git/conf"),
        ("one", "two\\inside"),
    ]:
        with pytest.raises(GatewayAccessError):
            mount.store.draft_rename(
                FileDraftRenameRequest(path=source, destination=dest, **mount.draft(lease)),
                decision=mount.decision(EDIT),
                actor=mount.editor(),
                fence=_fence,
            )
    mount.store.draft_rename(
        FileDraftRenameRequest(path="one", destination="two", **mount.draft(lease)),
        decision=mount.decision(EDIT),
        actor=mount.editor(),
        fence=_fence,
    )
    read = mount.store.draft_read(
        FileDraftPathRequest(path="two/value.md", **mount.draft(lease)),
        decision=mount.decision(EDIT),
        fence=_fence,
    )
    assert base64.b64decode(read.content_base64) == b"original"
    assert not mount.store.published_files()


def test_rotated_key_resumes_same_principal_and_commit_records_actor(mount: Mount) -> None:
    """Restrict draft ownership by stable principal and check original admissions at effects."""

    lease = mount.open()
    initial = mount.decision(EDIT)
    old = initial.actor
    new = old.model_copy(update={"key_id": "SHA256:" + "B" * 43, "enrollment_id": "rotated"})
    fresh = mount.decision(EDIT, actor=new)
    writer = mount.editor().model_copy(update={"label": "Revised peer label"})

    def require_current(admitted: AuthorizationDecision) -> None:
        """Use current enrollment evidence at the side-effect boundary."""

        if admitted.actor != new:
            raise GatewayAccessError(401, "credential_revoked")

    request = FileDraftWriteRequest(
        path="skill.md",
        content_base64="dXBkYXRlZA==",
        **mount.draft(lease),
    )
    with pytest.raises(GatewayAccessError) as denied:
        mount.store.draft_write(
            request,
            content=b"old bytes",
            decision=initial,
            actor=mount.editor(),
            fence=require_current,
        )
    assert denied.value.code == "credential_revoked"
    directory = mount.store.draft_list(
        FileDraftListRequest(**mount.draft(lease)),
        decision=fresh,
        fence=require_current,
    )
    assert not directory.entries
    mount.store.draft_write(
        request,
        content=b"updated",
        decision=fresh,
        actor=writer,
        fence=require_current,
    )
    receipt = mount.store.draft_commit(
        FileDraftCommitRequest(message="Record actual actor", **mount.draft(lease)),
        decision=fresh,
        actor=writer,
        fence=require_current,
        validate=lambda _: None,
    )
    assert receipt.author == mount.editor()
    assert receipt.actor == writer
    assert mount.store.candidate(receipt.commit_id).files == {"skill.md": b"updated"}


def test_anonymous_lease_capability_is_private_and_expires_with_epoch(mount: Mount) -> None:
    """Bind anonymous drafts to a secret and their original open authorization epoch."""

    identity = AuthorizationActor(kind="anonymous")
    actor = FileActor(kind="anonymous")
    opened = mount.store.lease_open(
        FileDraftOpenRequest(expected_base=mount.initial, **mount.coordinates),
        decision=mount.decision(EDIT, actor=identity, epoch=1),
        actor=actor,
        fence=_fence,
    )
    secret = opened.lease_capability
    assert secret is not None
    assert secret not in repr(opened)
    assert secret.encode() not in (mount.store.root / "mount.sqlite3").read_bytes()
    wrong = FileDraftListRequest(draft_id=opened.draft_id, **mount.coordinates)
    with pytest.raises(GatewayAccessError) as denied:
        mount.store.draft_list(
            wrong, decision=mount.decision(EDIT, actor=identity, epoch=1), fence=_fence
        )
    assert denied.value.code == "lease_owner_required"
    signed = FileDraftListRequest(
        draft_id=opened.draft_id, lease_capability=secret, **mount.coordinates
    )
    with pytest.raises(GatewayAccessError) as denied:
        mount.store.draft_list(
            signed, decision=mount.decision(EDIT, actor=identity, epoch=2), fence=_fence
        )
    assert denied.value.code == "unknown_draft"
    receipt = mount.store.draft_commit(
        FileDraftCommitRequest(message="Anonymous empty draft", **mount.draft(opened)),
        decision=mount.decision(EDIT, actor=identity, epoch=1),
        actor=actor,
        fence=_fence,
        validate=lambda _: None,
    )
    assert receipt.author == actor
    assert receipt.actor == actor


def test_commit_refuses_override_and_preserves_a_concurrent_draft_edit(mount: Mount) -> None:
    """Validate a frozen draft off lock and refuse to commit a superseded snapshot."""

    opened = mount.open()
    mount.write(opened, "skill.md", b"First body")
    with pytest.raises(ValidationError):
        FileDraftCommitRequest(
            message="Try to claim another identity", author="owner", **mount.draft(opened)
        )
    request = FileDraftCommitRequest(message="Keep current edits", **mount.draft(opened))

    def validate(files: dict[str, bytes]) -> None:
        """Simulate a concurrent writer changing the draft during semantic validation."""

        assert files == {"skill.md": b"First body"}
        mount.write(opened, "skill.md", b"Concurrent edit")

    with pytest.raises(GatewayAccessError) as rejected:
        mount.store.draft_commit(
            request,
            decision=mount.decision(EDIT),
            actor=mount.editor(),
            fence=_fence,
            validate=validate,
        )
    assert rejected.value.code == "draft_changed"
    saved = mount.store.draft_commit(
        request,
        decision=mount.decision(EDIT),
        actor=mount.editor(),
        fence=_fence,
        validate=lambda _: None,
    )
    assert mount.store.candidate(saved.commit_id).files == {"skill.md": b"Concurrent edit"}
