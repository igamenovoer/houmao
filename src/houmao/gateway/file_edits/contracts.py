"""Typed direct gateway file-edit requests and receipts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from houmao.gateway.access_models import GatewayTarget

FILE_EDIT_PATH = "/v1/control/file-edits"
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_FILE_REQUEST_BYTES = 4 * 1024 * 1024
MAX_LIST_ENTRIES = 256

READ = "files.read"
EDIT = "files.edit"
PUSH = "files.push"
FILE_ACTIONS = frozenset({READ, EDIT, PUSH})

MountId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
ObjectId = Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
ReferenceId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$")]
LogicalPath = Annotated[str, Field(min_length=1, max_length=1024)]
SecretLease = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{43}$")]


class FileEditModel(BaseModel):
    """Reject extra fields, untyped values and disclosure through validation errors."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class FileTargetRequest(FileEditModel):
    """Select one live endpoint, including for unsigned open operations."""

    target: GatewayTarget
    presence_id: ReferenceId


class FileMountRequest(FileTargetRequest):
    """Select an exact owner-defined mount."""

    mount_id: MountId


class FileRevisionRequest(FileMountRequest):
    """Select the current or an explicitly pinned published revision."""

    revision: ObjectId | None = None


class FileListRequest(FileRevisionRequest):
    """Read a bounded slice of one logical directory."""

    directory: LogicalPath | None = None
    after: LogicalPath | None = None
    limit: int = Field(default=100, ge=1, le=MAX_LIST_ENTRIES)


class FileReadRequest(FileRevisionRequest):
    """Read one regular file from the selected published revision."""

    path: LogicalPath


class FileDraftOpenRequest(FileMountRequest):
    """Reserve a draft based on the exact caller-observed publication."""

    expected_base: ObjectId


class FileDraftRequest(FileMountRequest):
    """Select a current lease and its optional anonymous capability."""

    draft_id: ReferenceId
    lease_capability: SecretLease | None = Field(default=None, repr=False)


class FileDraftListRequest(FileDraftRequest):
    """Read a bounded slice of a private draft."""

    directory: LogicalPath | None = None
    after: LogicalPath | None = None
    limit: int = Field(default=100, ge=1, le=MAX_LIST_ENTRIES)


class FileDraftPathRequest(FileDraftRequest):
    """Address one logical path within a private draft."""

    path: LogicalPath


class FileDraftWriteRequest(FileDraftPathRequest):
    """Stage arbitrary regular-file bytes using a bounded base64 envelope."""

    content_base64: str = Field(max_length=4 * ((MAX_FILE_BYTES + 2) // 3), repr=False)


class FileDraftRenameRequest(FileDraftPathRequest):
    """Name both endpoints of a within-draft rename."""

    destination: LogicalPath


class FileDraftCommitRequest(FileDraftRequest):
    """Freeze the draft using a caller-supplied commit message."""

    message: str = Field(min_length=1, max_length=4096, repr=False)


class FileCandidateRequest(FileMountRequest):
    """Address one immutable candidate in this mount's history."""

    commit_id: ObjectId


class FilePushRequest(FileCandidateRequest):
    """Publish one immutable candidate under revision and repeat preconditions."""

    expected_base: ObjectId
    operation_id: ReferenceId


class FileStatusRequest(FileMountRequest):
    """Read the durable receipt for one operation without dispatching it."""

    operation_id: ReferenceId


class FileHistoryRequest(FileMountRequest):
    """Read a bounded page of published ancestry or retained candidates."""

    history: Literal["published", "candidates"] = "published"
    after: ObjectId | None = None
    limit: int = Field(default=20, ge=1, le=MAX_LIST_ENTRIES)


class FileDiffRequest(FileCandidateRequest):
    """Read a bounded page of paths changed by a retained candidate."""

    after: LogicalPath | None = None
    limit: int = Field(default=100, ge=1, le=MAX_LIST_ENTRIES)


class FileDraftDiffRequest(FileDraftRequest):
    """Read a bounded page of paths changed in the caller's draft."""

    after: LogicalPath | None = None
    limit: int = Field(default=100, ge=1, le=MAX_LIST_ENTRIES)


class FileActor(FileEditModel):
    """Safe actor attribution projected from the target's admitted policy."""

    kind: Literal["anonymous", "operator", "service", "agent", "self"]
    principal_id: ReferenceId | None = None
    logical_agent_id: ReferenceId | None = None
    label: str | None = None


class FileMountDescriptor(FileEditModel):
    """Advertise an exact mount resource and its qualified live operations."""

    mount_id: MountId
    name: str
    resource: str
    actions: list[str]
    published_commit: ObjectId


class FileMountsResponse(FileEditModel):
    """List only mounts for which the caller has current read permissions."""

    mounts: list[FileMountDescriptor]


class FileEntry(FileEditModel):
    """Describe a logical file or directory without a physical pathname."""

    path: LogicalPath
    kind: Literal["file", "directory"]
    size: int | None = None


class FileListResponse(FileEditModel):
    """Serve a bounded page of logical paths and its pinned revision."""

    revision: ObjectId
    entries: list[FileEntry]
    next_after: LogicalPath | None = None


class FileReadResponse(FileEditModel):
    """Serve regular-file bytes pinned to a logical revision."""

    revision: ObjectId
    path: LogicalPath
    content_base64: str


class FileDraftReceipt(FileEditModel):
    """Return the draft lease and capability only to its initiating caller."""

    draft_id: ReferenceId
    base_commit: ObjectId
    expires_at: float
    actor: FileActor
    lease_capability: SecretLease | None = Field(default=None, repr=False)


class FileMutationReceipt(FileEditModel):
    """Confirm one private draft mutation."""

    draft_id: ReferenceId
    actor: FileActor


class FileCommitReceipt(FileEditModel):
    """Return the saved candidate without implying publication."""

    commit_id: ObjectId
    base_commit: ObjectId
    author: FileActor
    committer: ReferenceId
    actor: FileActor


class FileDiffEntry(FileEditModel):
    """Represent one changed path in a draft or immutable commit."""

    path: LogicalPath
    change: Literal["added", "modified", "deleted"]
    before_sha256: str | None = None
    after_sha256: str | None = None
    patch: str | None = None
    patch_truncated: bool = False


class FileDiffResponse(FileEditModel):
    """Return changed logical paths scoped to one immutable base."""

    base_commit: ObjectId | None
    changes: list[FileDiffEntry]
    next_after: LogicalPath | None = None


class FileHistoryEntry(FileEditModel):
    """Report the retained identity and attribution of one Git commit."""

    commit_id: ObjectId
    parent: ObjectId | None = None
    message: str
    author: FileActor
    committer: ReferenceId


class FileHistoryResponse(FileEditModel):
    """Serve a bounded page of retained Git history."""

    commits: list[FileHistoryEntry]
    next_after: ObjectId | None = None


class FilePushReceipt(FileEditModel):
    """Keep publication, native effectiveness, and readiness distinct."""

    operation_id: ReferenceId
    candidate: ObjectId
    expected_base: ObjectId
    publisher: FileActor
    outcome: Literal[
        "pending", "busy", "conflict", "refused", "published", "unavailable", "unknown"
    ]
    published_commit: ObjectId | None = None
    effective_commit: ObjectId | None = None
    activation: Literal["not_started", "effective", "partial", "unknown"] = "not_started"
    native_settled: bool | None = None
    native_ready: bool | None = None
    reason: str | None = None


FILE_REQUESTS: dict[str, tuple[type[FileTargetRequest], str | None]] = {
    "mounts": (FileTargetRequest, None),
    "list": (FileListRequest, READ),
    "read": (FileReadRequest, READ),
    "diff": (FileDiffRequest, READ),
    "history": (FileHistoryRequest, READ),
    "status": (FileStatusRequest, READ),
    "lease/open": (FileDraftOpenRequest, EDIT),
    "lease/renew": (FileDraftRequest, EDIT),
    "draft/list": (FileDraftListRequest, EDIT),
    "draft/read": (FileDraftPathRequest, EDIT),
    "draft/diff": (FileDraftDiffRequest, EDIT),
    "draft/write": (FileDraftWriteRequest, EDIT),
    "draft/delete": (FileDraftPathRequest, EDIT),
    "draft/mkdir": (FileDraftPathRequest, EDIT),
    "draft/rename": (FileDraftRenameRequest, EDIT),
    "draft/commit": (FileDraftCommitRequest, EDIT),
    "draft/abort": (FileDraftRequest, EDIT),
    "push": (FilePushRequest, PUSH),
}
