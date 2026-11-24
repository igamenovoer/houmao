"""Write and inspect retained owner-side Git objects through Dulwich."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import re
import time
import unicodedata

from dulwich.object_store import iter_tree_contents
from dulwich.objects import Blob, Commit, ObjectID, Tree
from dulwich.refs import Ref
from dulwich.repo import Repo

from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.file_edits.contracts import MAX_FILE_BYTES, FileActor
from houmao.gateway.file_edits.paths import MAX_ENTRIES, MAX_TREE_BYTES, logical_path, parents

PUBLISHED_REF = Ref(b"refs/heads/published")
_BLOB_MODE = 0o100644
_TREE_MODE = 0o040000
_OBJECT_ID = re.compile(r"[0-9a-f]{40}\Z")
_DRAFT_ID = re.compile(r"[0-9a-f]{32}\Z")


def object_id(value: str) -> ObjectID:
    """Accept only an exact SHA-1 object ID in the mount repository."""

    if _OBJECT_ID.fullmatch(value) is None:
        raise GatewayAccessError(422, "invalid_git_revision")
    return ObjectID(value.encode("ascii"))


def retain(repo: Repo, revision: str) -> None:
    """Make a saved object reachable from an ordinary Git reference."""

    repo.refs[Ref(b"refs/houmao/commits/" + object_id(revision))] = object_id(revision)


def read_files(repo: Repo, revision: str) -> dict[str, bytes]:
    """Read one bounded Git tree, accepting only canonical regular files."""

    commit = repo[object_id(revision)]
    if not isinstance(commit, Commit):
        raise GatewayAccessError(503, "mount_unavailable")
    result: dict[str, bytes] = {}
    size = 0
    names = set()
    for entry in iter_tree_contents(repo.object_store, commit.tree, max_depth=32):
        path = logical_path(entry.path.decode("utf-8"))
        if entry.mode != _BLOB_MODE or path in result:
            raise GatewayAccessError(503, "mount_unavailable")
        names.add(path)
        names.update(parents(path))
        if len(names) > MAX_ENTRIES:
            raise GatewayAccessError(503, "mount_unavailable")
        blob = repo[entry.sha]
        if not isinstance(blob, Blob) or len(blob.data) > MAX_FILE_BYTES:
            raise GatewayAccessError(503, "mount_unavailable")
        size += len(blob.data)
        if size > MAX_TREE_BYTES:
            raise GatewayAccessError(503, "mount_unavailable")
        result[path] = blob.data
    return result


def write_commit(
    repo: Repo,
    files: Mapping[str, bytes],
    *,
    parent: str | None,
    author: FileActor,
    committer: str,
    message: str,
    draft_id: str | None = None,
) -> str:
    """Write a Git commit whose attribution is derived from trusted actor evidence."""

    if draft_id is not None and _DRAFT_ID.fullmatch(draft_id) is None:
        raise ValueError("Invalid retained draft ID")
    entries: dict[str, list[tuple[str, int, ObjectID]]] = {"": []}
    for path, data in files.items():
        for directory in parents(path):
            entries.setdefault(directory, [])
        directory, _, name = path.rpartition("/")
        blob = Blob.from_string(data)
        repo.object_store.add_object(blob)
        entries[directory].append((name, _BLOB_MODE, blob.id))

    root = Tree()
    for path in sorted(entries, key=lambda value: (bool(value), value.count("/")), reverse=True):
        tree = Tree()
        for name, mode, sha in entries[path]:
            tree.add(name.encode("utf-8"), mode, sha)
        repo.object_store.add_object(tree)
        if path:
            directory, _, name = path.rpartition("/")
            entries[directory].append((name, _TREE_MODE, tree.id))
        else:
            root = tree

    commit = Commit()
    commit.tree = root.id
    commit.parents = [object_id(parent)] if parent is not None else []
    commit.author = _identity(
        author.label or author.logical_agent_id or author.principal_id or "anonymous",
        author.kind,
        author.logical_agent_id or author.principal_id or "anonymous",
    )
    commit.committer = _identity(f"Houmao gateway {committer}", "gateway", committer)
    commit.author_time = commit.commit_time = int(time.time())
    commit.author_timezone = commit.commit_timezone = 0
    commit.encoding = b"UTF-8"
    commit.message = message.encode("utf-8")
    if draft_id is not None:
        headers, _, body = commit.as_raw_string().partition(b"\n\n")
        commit = Commit.from_string(
            headers + b"\nhoumao-draft " + draft_id.encode("ascii") + b"\n\n" + body
        )
    repo.object_store.add_object(commit)
    return commit.id.decode("ascii")


def _identity(label: str, kind: str, identity: str) -> bytes:
    """Encode a safe display label and stable synthetic address."""

    label = "".join(
        char if char not in "<>" and not unicodedata.category(char).startswith("C") else " "
        for char in label
    )
    name = " ".join(label.split())[:128] or kind
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return f"{name} <{kind}-{digest}@houmao.invalid>".encode("utf-8")
