"""Owner-private file mounts with fenced drafts and immutable Git history."""

from __future__ import annotations

import base64
from collections.abc import Callable, Iterator, Mapping
from contextlib import closing, contextmanager
from dataclasses import dataclass
from functools import partial
import hashlib
from hmac import compare_digest
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time
from typing import Literal
from uuid import uuid4

from dulwich.errors import (
    FileFormatException,
    NotGitRepository,
    RefFormatError,
    WrongObjectException,
)
from dulwich.object_store import MaxTreeDepthExceeded
from dulwich.repo import Repo

from houmao.gateway._access_storage import (
    GatewayAccessError,
    _file_lock,
    _private_directory,
    _read_file,
    _require_private_file,
    _write_file,
)
from houmao.gateway.access_models import GatewayOwner
from houmao.gateway.authorization_models import AuthorizationDecision, Permission
from houmao.gateway.file_edits import git_objects
from houmao.gateway.file_edits.contracts import (
    EDIT,
    FILE_ACTIONS,
    MAX_FILE_BYTES,
    READ,
    FileActor,
    FileCommitReceipt,
    FileDiffRequest,
    FileDiffResponse,
    FileDraftCommitRequest,
    FileDraftDiffRequest,
    FileDraftListRequest,
    FileDraftOpenRequest,
    FileDraftPathRequest,
    FileDraftReceipt,
    FileDraftRenameRequest,
    FileDraftRequest,
    FileDraftWriteRequest,
    FileHistoryEntry,
    FileHistoryRequest,
    FileHistoryResponse,
    FileListRequest,
    FileListResponse,
    FileMountDescriptor,
    FileMountRequest,
    FileMutationReceipt,
    FileReadRequest,
    FileReadResponse,
)
from houmao.gateway.file_edits.inspection import diff_page, list_page
from houmao.gateway.file_edits.paths import check_tree, insert_parents, logical_path

_STATE = "mount.sqlite3"
_REPOSITORY = "git"
_LEASE_SECONDS = 300
_MAX_CANDIDATES = 1024
_APPLICATION_ID = 0x484D4645
_VERSION = 2
_STATE_ERRORS = (
    FileFormatException,
    KeyError,
    MaxTreeDepthExceeded,
    NotGitRepository,
    OSError,
    RefFormatError,
    sqlite3.Error,
    ValueError,
    WrongObjectException,
)
_SCHEMA = """
CREATE TABLE mount (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    identity TEXT NOT NULL,
    mount_id TEXT NOT NULL,
    published_commit TEXT NOT NULL,
    lease_epoch INTEGER NOT NULL
) STRICT;
CREATE TABLE revision (
    sequence INTEGER PRIMARY KEY,
    commit_id TEXT NOT NULL UNIQUE,
    parent TEXT REFERENCES revision(commit_id),
    author TEXT NOT NULL,
    actor TEXT NOT NULL,
    message TEXT NOT NULL,
    published_order INTEGER UNIQUE
) STRICT;
CREATE TABLE lease (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    draft_id TEXT NOT NULL,
    target_generation TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    actor_kind TEXT NOT NULL,
    principal_id TEXT,
    author TEXT NOT NULL,
    base_commit TEXT NOT NULL REFERENCES revision(commit_id),
    open_epoch INTEGER,
    default_permission_revision INTEGER,
    capability_sha256 TEXT,
    expires_at REAL NOT NULL,
    epoch INTEGER NOT NULL,
    content_version INTEGER NOT NULL
) STRICT;
CREATE TABLE entry (
    path TEXT PRIMARY KEY,
    data BLOB
) STRICT;
"""

EffectFence = Callable[[AuthorizationDecision], object]
DraftEntries = dict[str, bytes | None]


@dataclass(frozen=True)
class CandidateRevision:
    """A preserved candidate and the exact published base it was prepared from."""

    commit_id: str
    base_commit: str
    files: dict[str, bytes]


class MountStorage:
    """Store one retained mount and generation-bound drafts below a private root."""

    def __init__(
        self,
        root: Path,
        owner: GatewayOwner,
        *,
        lineage: str,
        name: str = "skills",
        kind: Literal["skills", "mcp"] = "skills",
    ) -> None:
        """Scope the mount to an explicit owner, storage lineage, and mount name."""

        if not lineage or not name or len(lineage) > 4096 or len(name) > 128:
            raise GatewayAccessError(422, "invalid_mount_identity")
        identity = json.dumps(
            [owner.model_dump(mode="json"), lineage, name], sort_keys=True, separators=(",", ":")
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        self.m_root: Path = root / "file-edits" / digest
        self.m_owner: GatewayOwner = owner
        self.m_name: str = name
        self.m_kind: Literal["skills", "mcp"] = kind
        self.m_identity: str = identity

    @property
    def root(self) -> Path:
        """Return the owner-controlled mount directory for local services."""

        return self.m_root

    @property
    def kind(self) -> Literal["skills", "mcp"]:
        """Return the owner-selected common-plugin mount kind."""

        return self.m_kind

    @property
    def mount_id(self) -> str:
        """Return the retained mount ID without creating or repairing state."""

        with self._session() as (conn, _):
            return str(self._mount(conn)["mount_id"])

    def initialize(self) -> FileMountDescriptor:
        """Explicitly provision a private mount, or confirm its retained identity."""

        parent = self.m_root.parent
        try:
            with _private_directory(parent, create=True) as directory:
                lock = f".{self.m_root.name}.lock"
                initialized = f".{self.m_root.name}.initialized"
                with _file_lock(directory, lock, create=True):
                    try:
                        os.stat(self.m_root.name, dir_fd=directory, follow_symlinks=False)
                    except FileNotFoundError:
                        try:
                            os.stat(initialized, dir_fd=directory, follow_symlinks=False)
                        except FileNotFoundError:
                            pass
                        else:
                            raise GatewayAccessError(503, "mount_unavailable") from None
                        with tempfile.TemporaryDirectory(prefix=".mount-", dir=parent) as staging:
                            source = Path(staging) / "mount"
                            self._provision(source)
                            os.rename(source, self.m_root)
                            os.fsync(directory)
                    self._upgrade_state()
                    descriptor = self.describe()
                    encoded_id = descriptor.mount_id.encode("ascii")
                    try:
                        recorded_id = _read_file(directory, initialized, 32)
                    except FileNotFoundError:
                        _write_file(directory, initialized, encoded_id)
                    else:
                        if recorded_id != encoded_id:
                            raise GatewayAccessError(503, "mount_unavailable")
                    return descriptor
        except _STATE_ERRORS:
            raise GatewayAccessError(503, "mount_unavailable") from None

    def describe(self) -> FileMountDescriptor:
        """Read the mount's resource, operations, and current published commit."""

        with self._session() as (conn, _):
            row = self._mount(conn)
            mount_id = str(row["mount_id"])
            return FileMountDescriptor(
                mount_id=mount_id,
                name=self.m_name,
                kind=self.kind,
                resource=f"files:{mount_id}",
                actions=sorted(FILE_ACTIONS),
                published_commit=str(row["published_commit"]),
            )

    def published_commit(self) -> str:
        """Read the revision selected by the durable published index."""

        with self._session() as (conn, _):
            return str(self._mount(conn)["published_commit"])

    def published_files(self, revision: str | None = None) -> dict[str, bytes]:
        """Read the current or a retained published tree for local projection."""

        with self._session() as (conn, repo):
            pinned = self._published_revision(conn, revision)
            return git_objects.read_files(repo, pinned)

    def candidate(self, commit_id: str) -> CandidateRevision:
        """Load a retained candidate before preparing its immutable projection."""

        with self._session() as (conn, repo):
            row = self._saved_candidate(conn, commit_id)
            return CandidateRevision(
                commit_id, str(row["parent"]), git_objects.read_files(repo, commit_id)
            )

    def advance_published(self, expected_base: str, candidate: str) -> str:
        """Reflect a proven projection switch in the compare-and-advance index."""

        with self._session(write=True) as (conn, repo):
            row = self._saved_candidate(conn, candidate)
            if row["parent"] != expected_base:
                raise GatewayAccessError(409, "revision_conflict")
            current = str(self._mount(conn)["published_commit"])
            if current == candidate:
                repo.refs[git_objects.PUBLISHED_REF] = git_objects.object_id(candidate)
                return current
            if current != expected_base:
                raise GatewayAccessError(409, "revision_conflict")
            if row["published_order"] is not None:
                raise GatewayAccessError(409, "revision_conflict")
            conn.execute(
                "UPDATE revision SET published_order = "
                "(SELECT max(published_order) + 1 FROM revision) WHERE commit_id = ?",
                (candidate,),
            )
            conn.execute("UPDATE mount SET published_commit = ?", (candidate,))
            repo.refs[git_objects.PUBLISHED_REF] = git_objects.object_id(candidate)
            return candidate

    def lease_open(
        self,
        request: FileDraftOpenRequest,
        *,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
        current_default_revision: int | None = None,
    ) -> FileDraftReceipt:
        """Open an exclusive draft based on the caller's observed revision."""

        self._check_actor(decision, actor)
        with self._session() as (conn, repo):
            mount = self._bound(conn, request, decision, EDIT)
            base = str(mount["published_commit"])
            if base != request.expected_base:
                raise GatewayAccessError(409, "revision_conflict")
            entries = _directory_entries(git_objects.read_files(repo, base))
        lease_secret = secrets.token_urlsafe(32) if actor.kind == "anonymous" else None
        lease_id = uuid4().hex
        with self._session(write=True) as (conn, _):
            mount = self._bound(conn, request, decision, EDIT)
            if mount["published_commit"] != base:
                raise GatewayAccessError(409, "revision_conflict")
            old = conn.execute("SELECT * FROM lease").fetchone()
            if old is not None and self._lease_current(
                old, decision, default_revision=current_default_revision
            ):
                raise GatewayAccessError(409, "draft_busy")
            epoch = int(mount["lease_epoch"]) + 1
            expires = time.time() + _LEASE_SECONDS
            fence(decision)
            conn.execute("DELETE FROM lease")
            conn.execute("DELETE FROM entry")
            conn.execute("UPDATE mount SET lease_epoch = ?", (epoch,))
            conn.execute(
                "INSERT INTO lease (singleton, draft_id, target_generation, policy_id, "
                "actor_kind, principal_id, author, base_commit, open_epoch, "
                "default_permission_revision, capability_sha256, expires_at, epoch, "
                "content_version) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    lease_id,
                    decision.target.incarnation,
                    decision.policy_id,
                    decision.actor.kind,
                    decision.actor.principal_id,
                    actor.model_dump_json(),
                    base,
                    decision.open_epoch if lease_secret is not None else None,
                    decision.default_permission_revision if lease_secret is not None else None,
                    _capability_digest(lease_secret) if lease_secret is not None else None,
                    expires,
                    epoch,
                ),
            )
            conn.executemany("INSERT INTO entry VALUES (?, ?)", entries.items())
        return FileDraftReceipt(
            draft_id=lease_id,
            base_commit=base,
            expires_at=expires,
            actor=actor,
            lease_capability=lease_secret,
        )

    def lease_renew(
        self,
        request: FileDraftRequest,
        *,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
    ) -> FileDraftReceipt:
        """Renew the current caller's draft lease without exposing its secret."""

        self._check_actor(decision, actor)
        with self._session(write=True) as (conn, _):
            lease = self._draft(conn, request, decision)
            expires = time.time() + _LEASE_SECONDS
            fence(decision)
            self._check_lease_expiry(lease)
            conn.execute("UPDATE lease SET expires_at = ?", (expires,))
            return FileDraftReceipt(
                draft_id=request.draft_id,
                base_commit=lease["base_commit"],
                expires_at=expires,
                actor=actor,
            )

    def draft_abort(
        self,
        request: FileDraftRequest,
        *,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
    ) -> FileMutationReceipt:
        """Release a lease and remove its staged entries."""

        self._check_actor(decision, actor)
        with self._session(write=True) as (conn, _):
            lease = self._draft(conn, request, decision)
            fence(decision)
            self._check_lease_expiry(lease)
            conn.execute("DELETE FROM lease")
            conn.execute("DELETE FROM entry")
        return FileMutationReceipt(draft_id=request.draft_id, actor=actor)

    def draft_write(
        self,
        request: FileDraftWriteRequest,
        *,
        content: bytes,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
    ) -> FileMutationReceipt:
        """Install staged regular-file bytes in a still-current draft."""

        if len(content) > MAX_FILE_BYTES:
            raise GatewayAccessError(413, "file_too_large")
        path = logical_path(request.path)
        return self._edit(request, decision, actor, fence, partial(_set_entry, path, content))

    def draft_mkdir(
        self,
        request: FileDraftPathRequest,
        *,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
    ) -> FileMutationReceipt:
        """Create a logical directory in the caller's draft."""

        return self._edit(
            request, decision, actor, fence, partial(_set_entry, logical_path(request.path), None)
        )

    def draft_delete(
        self,
        request: FileDraftPathRequest,
        *,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
    ) -> FileMutationReceipt:
        """Remove a logical entry and its descendants from the caller's draft."""

        return self._edit(
            request, decision, actor, fence, partial(_delete, logical_path(request.path))
        )

    def draft_rename(
        self,
        request: FileDraftRenameRequest,
        *,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
    ) -> FileMutationReceipt:
        """Rename a regular file or directory within one current draft."""

        source = logical_path(request.path)
        destination = logical_path(request.destination)
        return self._edit(request, decision, actor, fence, partial(_rename, source, destination))

    def draft_commit(
        self,
        request: FileDraftCommitRequest,
        *,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
        validate: Callable[[dict[str, bytes]], None],
    ) -> FileCommitReceipt:
        """Validate a frozen draft, then save it under its original author."""

        self._check_actor(decision, actor)
        message = _message(request.message)
        with self._session() as (conn, _):
            lease = self._draft(conn, request, decision)
            draft_id = str(lease["draft_id"])
            base = str(lease["base_commit"])
            version = (lease["epoch"], lease["content_version"])
            author = FileActor.model_validate_json(lease["author"])
            files = _files(self._entries(conn))
        validate(files.copy())
        with self._repo() as repo:
            revision = git_objects.write_commit(
                repo,
                files,
                parent=base,
                author=author,
                committer=self.m_owner.agent_id,
                message=message,
                draft_id=draft_id,
            )
        with self._session(write=True) as (conn, repo):
            lease = self._draft(conn, request, decision)
            if (lease["epoch"], lease["content_version"]) != version:
                raise GatewayAccessError(409, "draft_changed")
            if (
                conn.execute(
                    "SELECT count(*) FROM revision WHERE published_order IS NULL"
                ).fetchone()[0]
                >= _MAX_CANDIDATES
            ):
                raise GatewayAccessError(413, "candidate_capacity")
            fence(decision)
            self._check_lease_expiry(lease)
            git_objects.retain(repo, revision)
            conn.execute(
                "INSERT INTO revision (commit_id, parent, author, actor, message) "
                "VALUES (?, ?, ?, ?, ?)",
                (revision, base, author.model_dump_json(), actor.model_dump_json(), message),
            )
            conn.execute("DELETE FROM lease")
            conn.execute("DELETE FROM entry")
        return FileCommitReceipt(
            commit_id=revision,
            base_commit=base,
            author=author,
            committer=self.m_owner.agent_id,
            actor=actor,
        )

    def list(
        self, request: FileListRequest, *, decision: AuthorizationDecision, fence: EffectFence
    ) -> FileListResponse:
        """List part of a logical directory in one pinned published revision."""

        with self._session() as (conn, repo):
            self._bound(conn, request, decision, READ)
            revision = self._published_revision(conn, request.revision)
            entries = _directory_entries(git_objects.read_files(repo, revision))
            response = list_page(entries, revision, request.directory, request.after, request.limit)
            fence(decision)
            return response

    def read(
        self, request: FileReadRequest, *, decision: AuthorizationDecision, fence: EffectFence
    ) -> FileReadResponse:
        """Serve one regular file from a pinned published revision."""

        path = logical_path(request.path)
        with self._session() as (conn, repo):
            self._bound(conn, request, decision, READ)
            revision = self._published_revision(conn, request.revision)
            files = git_objects.read_files(repo, revision)
            response = _read_file_response(files, revision, path)
            fence(decision)
            return response

    def draft_list(
        self, request: FileDraftListRequest, *, decision: AuthorizationDecision, fence: EffectFence
    ) -> FileListResponse:
        """List a bounded directory page inside a current caller-owned draft."""

        with self._session() as (conn, _):
            lease = self._draft(conn, request, decision)
            response = list_page(
                self._entries(conn),
                str(lease["base_commit"]),
                request.directory,
                request.after,
                request.limit,
            )
            self._check_lease_expiry(lease)
            fence(decision)
            return response

    def draft_read(
        self, request: FileDraftPathRequest, *, decision: AuthorizationDecision, fence: EffectFence
    ) -> FileReadResponse:
        """Read one regular file from a current caller-owned draft."""

        path = logical_path(request.path)
        with self._session() as (conn, _):
            lease = self._draft(conn, request, decision)
            response = _read_file_response(self._entries(conn), str(lease["base_commit"]), path)
            self._check_lease_expiry(lease)
            fence(decision)
            return response

    def diff(
        self, request: FileDiffRequest, *, decision: AuthorizationDecision, fence: EffectFence
    ) -> FileDiffResponse:
        """Inspect a stored commit against its immutable parent."""

        with self._session() as (conn, repo):
            self._bound(conn, request, decision, READ)
            row = self._revision(conn, request.commit_id)
            parent = row["parent"]
            base = git_objects.read_files(repo, parent) if parent is not None else {}
            files = git_objects.read_files(repo, request.commit_id)
            response = diff_page(base, files, parent, request.after, request.limit)
            fence(decision)
            return response

    def draft_diff(
        self, request: FileDraftDiffRequest, *, decision: AuthorizationDecision, fence: EffectFence
    ) -> FileDiffResponse:
        """Inspect the changes in one current caller-owned draft."""

        with self._session() as (conn, repo):
            lease = self._draft(conn, request, decision)
            base_commit = str(lease["base_commit"])
            before = git_objects.read_files(repo, base_commit)
            after = _files(self._entries(conn))
            response = diff_page(before, after, base_commit, request.after, request.limit)
            self._check_lease_expiry(lease)
            fence(decision)
            return response

    def history(
        self, request: FileHistoryRequest, *, decision: AuthorizationDecision, fence: EffectFence
    ) -> FileHistoryResponse:
        """Read bounded ancestry or saved candidates without side effects."""

        with self._session() as (conn, _):
            self._bound(conn, request, decision, READ)
            if request.history == "published":
                order, condition = "published_order", "published_order IS NOT NULL"
            else:
                order, condition = "sequence", "published_order IS NULL"
            args: tuple[int, ...]
            if request.after is not None:
                cursor = self._revision(conn, request.after)
                visible = (cursor["published_order"] is not None) == (
                    request.history == "published"
                )
                if not visible:
                    raise GatewayAccessError(404, "unknown_revision")
                condition += f" AND {order} < ?"
                args = (int(cursor[order]), request.limit + 1)
            else:
                args = (request.limit + 1,)
            rows = conn.execute(
                f"SELECT * FROM revision WHERE {condition} ORDER BY {order} DESC LIMIT ?",
                args,
            ).fetchall()
            commits = [
                FileHistoryEntry(
                    commit_id=row["commit_id"],
                    parent=row["parent"],
                    message=row["message"],
                    author=FileActor.model_validate_json(row["author"]),
                    committer=self.m_owner.agent_id,
                )
                for row in rows[: request.limit]
            ]
            next_after = commits[-1].commit_id if len(rows) > request.limit else None
            response = FileHistoryResponse(commits=commits, next_after=next_after)
            fence(decision)
            return response

    @contextmanager
    def _session(self, *, write: bool = False) -> Iterator[tuple[sqlite3.Connection, Repo]]:
        """Open and verify the owner-private repository and one SQLite snapshot."""

        try:
            with _private_directory(self.m_root) as directory:
                _check_sqlite_files(directory)
                with closing(sqlite3.connect(self.m_root / _STATE, timeout=2.0)) as conn:
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA trusted_schema = OFF")
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.execute("PRAGMA synchronous = FULL")
                    if (
                        conn.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID
                        or conn.execute("PRAGMA user_version").fetchone()[0] != _VERSION
                    ):
                        raise ValueError("unexpected mount state schema")
                    with conn, self._repo() as repo:
                        conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                        self._mount(conn)
                        yield conn, repo
        except _STATE_ERRORS:
            raise GatewayAccessError(503, "mount_unavailable") from None

    @contextmanager
    def _repo(self) -> Iterator[Repo]:
        """Open the private Git repository without holding a mount-state transaction."""

        root = self.m_root / _REPOSITORY
        try:
            with _private_directory(root), Repo(root) as repo:
                if not repo.bare:
                    raise ValueError("mount repository is not bare")
                yield repo
        except _STATE_ERRORS:
            raise GatewayAccessError(503, "mount_unavailable") from None

    def _provision(self, root: Path) -> None:
        """Build a complete new mount outside its final path before installation."""

        root.mkdir(mode=0o700)
        repo_root = root / _REPOSITORY
        repo_root.mkdir(mode=0o700)
        mount_id = uuid4().hex
        actor = FileActor(kind="anonymous")
        with Repo.init_bare(
            repo_root, default_branch=b"published", shared_repository=False, object_format="sha1"
        ) as repo:
            initial = git_objects.write_commit(
                repo,
                {},
                parent=None,
                author=actor,
                committer=self.m_owner.agent_id,
                message=f"Initialize managed mount {mount_id}",
            )
            git_objects.retain(repo, initial)
            repo.refs[git_objects.PUBLISHED_REF] = git_objects.object_id(initial)
        state = root / _STATE
        os.close(os.open(state, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600))
        with closing(sqlite3.connect(state)) as conn, conn:
            conn.execute("PRAGMA synchronous = FULL")
            conn.executescript(_SCHEMA)
            conn.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
            conn.execute(f"PRAGMA user_version = {_VERSION}")
            encoded_actor = actor.model_dump_json()
            conn.execute(
                "INSERT INTO revision (commit_id, author, actor, message, published_order) "
                "VALUES (?, ?, ?, ?, 1)",
                (initial, encoded_actor, encoded_actor, f"Initialize managed mount {mount_id}"),
            )
            conn.execute(
                "INSERT INTO mount VALUES (1, ?, ?, ?, 0)",
                (self.m_identity, mount_id, initial),
            )

    def _upgrade_state(self) -> None:
        """Keep saved history and existing leases when adding the default admission fence."""

        with _private_directory(self.m_root) as directory:
            _check_sqlite_files(directory)
            with closing(sqlite3.connect(self.m_root / _STATE, timeout=2.0)) as conn, conn:
                conn.execute("PRAGMA trusted_schema = OFF")
                conn.execute("PRAGMA synchronous = FULL")
                conn.execute("BEGIN IMMEDIATE")
                if conn.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID:
                    raise ValueError("unexpected mount state schema")
                if conn.execute("PRAGMA user_version").fetchone()[0] == 1:
                    conn.execute("ALTER TABLE lease ADD COLUMN default_permission_revision INTEGER")
                    conn.execute(f"PRAGMA user_version = {_VERSION}")

    def _mount(self, conn: sqlite3.Connection) -> sqlite3.Row:
        """Verify the scope stored in the retained mount record."""

        row = conn.execute("SELECT * FROM mount WHERE singleton = 1").fetchone()
        if not isinstance(row, sqlite3.Row) or row["identity"] != self.m_identity:
            raise GatewayAccessError(503, "mount_unavailable")
        return row

    def _bound(
        self,
        conn: sqlite3.Connection,
        request: FileMountRequest,
        decision: AuthorizationDecision,
        action: str,
    ) -> sqlite3.Row:
        """Bind the already-verified grant to this exact owner-side mount and action."""

        mount = self._mount(conn)
        if request.mount_id != mount["mount_id"]:
            raise GatewayAccessError(404, "unknown_mount")
        if (
            request.target.owner != self.m_owner
            or request.target != decision.target
            or request.presence_id != decision.listener_id
        ):
            raise GatewayAccessError(409, "authorization_target_conflict")
        permission = Permission(resource=f"files:{request.mount_id}", action=action)
        if permission not in decision.permissions or decision.basis == "public":
            raise GatewayAccessError(403, "insufficient_authority")
        return mount

    @staticmethod
    def _check_actor(decision: AuthorizationDecision, actor: FileActor) -> None:
        """Match trusted attribution to the exact admitted actor evidence."""

        verified = decision.actor
        expected_kind = (
            "credential" if actor.kind in {"operator", "service", "agent"} else actor.kind
        )
        if expected_kind != verified.kind or actor.principal_id != verified.principal_id:
            raise GatewayAccessError(403, "invalid_file_actor")
        if actor.kind == "anonymous" and (
            decision.basis not in {"open", "default"}
            or actor.logical_agent_id is not None
            or actor.label is not None
        ):
            raise GatewayAccessError(403, "invalid_file_actor")

    @staticmethod
    def _lease_current(
        lease: sqlite3.Row,
        decision: AuthorizationDecision,
        *,
        default_revision: int | None = None,
    ) -> bool:
        """Determine whether the row holds an exclusive lease for this target."""

        if (
            lease["expires_at"] <= time.time()
            or lease["target_generation"] != decision.target.incarnation
            or lease["policy_id"] != decision.policy_id
        ):
            return False
        if lease["actor_kind"] != "anonymous":
            return True
        if lease["open_epoch"] is not None:
            return bool(lease["open_epoch"] == decision.open_epoch)
        current_revision = (
            decision.default_permission_revision if default_revision is None else default_revision
        )
        return (
            decision.basis != "open"
            and current_revision is not None
            and lease["default_permission_revision"] == current_revision
        )

    @staticmethod
    def _check_lease_expiry(lease: sqlite3.Row) -> None:
        """Refuse a long operation that finishes after its own lease has elapsed."""

        if lease["expires_at"] <= time.time():
            raise GatewayAccessError(409, "draft_expired")

    def _draft(
        self, conn: sqlite3.Connection, request: FileDraftRequest, decision: AuthorizationDecision
    ) -> sqlite3.Row:
        """Require a current lease with matching owner evidence."""

        self._bound(conn, request, decision, EDIT)
        lease = conn.execute("SELECT * FROM lease").fetchone()
        if (
            not isinstance(lease, sqlite3.Row)
            or request.draft_id != lease["draft_id"]
            or not self._lease_current(lease, decision)
        ):
            raise GatewayAccessError(404, "unknown_draft")
        if (
            decision.actor.kind != lease["actor_kind"]
            or decision.actor.principal_id != lease["principal_id"]
        ):
            raise GatewayAccessError(403, "lease_owner_required")
        if decision.actor.kind == "anonymous":
            if request.lease_capability is None or not compare_digest(
                _capability_digest(request.lease_capability), lease["capability_sha256"]
            ):
                raise GatewayAccessError(403, "lease_owner_required")
        return lease

    @staticmethod
    def _entries(conn: sqlite3.Connection) -> DraftEntries:
        """Read the bounded set of entries retained in the current draft."""

        entries: DraftEntries = dict(conn.execute("SELECT path, data FROM entry").fetchall())
        check_tree(entries)
        return entries

    def _edit(
        self,
        request: FileDraftRequest,
        decision: AuthorizationDecision,
        actor: FileActor,
        fence: EffectFence,
        change: Callable[[DraftEntries], None],
    ) -> FileMutationReceipt:
        """Apply a prepared logical change only under its current lease and shared policy."""

        self._check_actor(decision, actor)
        with self._session(write=True) as (conn, _):
            lease = self._draft(conn, request, decision)
            before = self._entries(conn)
            after = before.copy()
            change(after)
            check_tree(after)
            self._check_lease_expiry(lease)
            fence(decision)
            self._check_lease_expiry(lease)
            conn.executemany(
                "DELETE FROM entry WHERE path = ?", ((p,) for p in before.keys() - after.keys())
            )
            conn.executemany(
                "INSERT OR REPLACE INTO entry VALUES (?, ?)",
                (
                    (path, data)
                    for path, data in after.items()
                    if path not in before or before[path] != data
                ),
            )
            conn.execute("UPDATE lease SET content_version = content_version + 1")
        return FileMutationReceipt(draft_id=request.draft_id, actor=actor)

    @staticmethod
    def _revision(conn: sqlite3.Connection, revision: str) -> sqlite3.Row:
        """Resolve an object ID against the mount's retained revision index."""

        git_objects.object_id(revision)
        row = conn.execute("SELECT * FROM revision WHERE commit_id = ?", (revision,)).fetchone()
        if not isinstance(row, sqlite3.Row):
            raise GatewayAccessError(404, "unknown_revision")
        return row

    def _saved_candidate(self, conn: sqlite3.Connection, revision: str) -> sqlite3.Row:
        """Select a saved commit that was created from a published base."""

        row = self._revision(conn, revision)
        if row["parent"] is None:
            raise GatewayAccessError(404, "unknown_candidate")
        return row

    def _published_revision(self, conn: sqlite3.Connection, selected: str | None) -> str:
        """Resolve a retained published revision without exposing staged candidates."""

        if selected is None:
            selected = str(self._mount(conn)["published_commit"])
        if self._revision(conn, selected)["published_order"] is None:
            raise GatewayAccessError(404, "unknown_revision")
        return selected


def _check_sqlite_files(directory: int) -> None:
    """Refuse symlinks, shared files, and missing owner-private mount state."""

    for suffix in ("", "-journal", "-wal", "-shm"):
        try:
            fd = os.open(
                _STATE + suffix, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
        except FileNotFoundError:
            if not suffix:
                raise
        else:
            try:
                _require_private_file(fd)
            finally:
                os.close(fd)


def _directory_entries(files: dict[str, bytes]) -> DraftEntries:
    """Expand immutable file paths into a logical hierarchy for listing and drafts."""

    entries: DraftEntries = {}
    for path, data in files.items():
        insert_parents(entries, path)
        entries[path] = data
    return entries


def _files(entries: DraftEntries) -> dict[str, bytes]:
    """Select regular files, omitting empty draft directories from Git."""

    return {path: data for path, data in entries.items() if data is not None}


def _capability_digest(value: str) -> str:
    """Store a derived digest instead of the anonymous lease capability."""

    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _message(value: str) -> str:
    """Keep exact caller-supplied Git messages within the wire size limit."""

    if not value.strip() or "\x00" in value or len(value.encode("utf-8")) > 4096:
        raise GatewayAccessError(422, "invalid_commit_message")
    return value


def _read_file_response(
    entries: Mapping[str, bytes | None], revision: str, path: str
) -> FileReadResponse:
    """Encode one present regular file for the typed gateway."""

    data = entries.get(path)
    if data is None:
        raise GatewayAccessError(404, "unknown_path")
    return FileReadResponse(
        revision=revision, path=path, content_base64=base64.b64encode(data).decode("ascii")
    )


def _set_entry(path: str, data: bytes | None, entries: DraftEntries) -> None:
    """Create directories or write regular files without changing an entry's type."""

    if path in entries and (entries[path] is None) != (data is None):
        raise GatewayAccessError(409, "path_conflict")
    insert_parents(entries, path)
    entries[path] = data


def _delete(path: str, entries: DraftEntries) -> None:
    """Remove the addressed logical subtree from the staged entries."""

    if path not in entries:
        raise GatewayAccessError(404, "unknown_path")
    for item in tuple(entries):
        if item == path or item.startswith(path + "/"):
            del entries[item]


def _rename(source: str, destination: str, entries: DraftEntries) -> None:
    """Move an existing logical subtree to an unused and canonical destination."""

    if source not in entries:
        raise GatewayAccessError(404, "unknown_path")
    if destination in entries or destination.startswith(source + "/"):
        raise GatewayAccessError(409, "path_conflict")
    insert_parents(entries, destination)
    for path in tuple(entries):
        if path == source or path.startswith(source + "/"):
            new_path = logical_path(destination + path[len(source) :])
            entries[new_path] = entries.pop(path)
