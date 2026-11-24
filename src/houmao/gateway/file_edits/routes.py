"""Expose typed file operations after direct gateway caller authentication."""

from __future__ import annotations

import base64
from binascii import Error as Base64Error
from collections.abc import Callable
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from houmao.gateway.access import GatewayAccessError, GatewayAccessPolicy
from houmao.gateway.access_models import GatewayTarget, parse_access_document
from houmao.gateway.authorization_models import (
    AuthorizationActor,
    AuthorizationDecision,
    Permission,
)
from houmao.gateway.file_edits.contracts import (
    EDIT,
    FILE_ACTIONS,
    FILE_EDIT_PATH,
    FILE_REQUESTS,
    MAX_FILE_BYTES,
    MAX_FILE_REQUEST_BYTES,
    READ,
    FileActor,
    FileDiffRequest,
    FileDraftCommitRequest,
    FileDraftDiffRequest,
    FileDraftListRequest,
    FileDraftOpenRequest,
    FileDraftPathRequest,
    FileDraftRenameRequest,
    FileDraftRequest,
    FileDraftWriteRequest,
    FileEditModel,
    FileHistoryRequest,
    FileListRequest,
    FileMountRequest,
    FileMountsResponse,
    FilePushRequest,
    FileReadRequest,
    FileStatusRequest,
    FileTargetRequest,
)
from houmao.gateway.file_edits.publication import FilePublication, NativeFileMount


class GatewayFileEdits:
    """Select a qualified mount and apply retained policy at its effect boundaries."""

    def __init__(
        self,
        *,
        policy: Callable[[], GatewayAccessPolicy],
        target: Callable[[], GatewayTarget],
        presence_id: str,
        manifest_path: Path,
        resolve_mount: Callable[[], NativeFileMount | None],
    ) -> None:
        """Bind file operations to this gateway and the verified owner target."""

        self.m_policy: Callable[[], GatewayAccessPolicy] = policy
        self.m_target: Callable[[], GatewayTarget] = target
        self.m_presence_id: str = presence_id
        self.m_manifest_path: Path = manifest_path
        self.m_resolve_mount: Callable[[], NativeFileMount | None] = resolve_mount
        self.m_selected: tuple[GatewayTarget, str, NativeFileMount] | None = None
        self.m_lock: Lock = Lock()

    def supports(self, permission: Permission) -> bool:
        """Recognize only the selected generation's qualified mount actions."""

        selected = self.m_selected
        return (
            selected is not None
            and permission.resource == f"files:{selected[1]}"
            and permission.action in FILE_ACTIONS
        )

    def dispatch(
        self, name: str, payload: FileTargetRequest, actor: AuthorizationActor
    ) -> FileEditModel:
        """Authorize the requested mount and perform the selected typed operation."""

        target = self.m_target()
        if payload.target != target or payload.presence_id != self.m_presence_id:
            raise GatewayAccessError(409, "file_target_changed")
        policy = self.m_policy()
        selected = self._select_mount(target)
        if name == "mounts":
            return self._mounts(actor, target, selected, policy)
        assert isinstance(payload, FileMountRequest)
        if selected is None or payload.mount_id != selected[1]:
            raise GatewayAccessError(404, "unknown_file_mount")
        mount = selected[2]
        action = FILE_REQUESTS[name][1]
        assert action is not None
        permission = Permission(resource=f"files:{payload.mount_id}", action=action)
        decision = policy.authorize(actor, (permission,))
        if decision.target != target or decision.listener_id != payload.presence_id:
            raise GatewayAccessError(409, "file_target_changed")

        def disclose(admitted: AuthorizationDecision) -> None:
            """Before returning any protected files or metadata, recheck the exact decision."""

            if not policy.revalidate(admitted):
                raise GatewayAccessError(403, "insufficient_authority")

        if action == EDIT:
            result = self._edit(name, payload, mount, decision, policy, disclose)
            disclose(decision)
            return result
        publication = FilePublication(mount, policy, self.m_manifest_path, target)
        if isinstance(payload, FilePushRequest):
            return publication.push(payload, decision, _attributed_actor(actor, policy))
        if isinstance(payload, FileStatusRequest):
            return publication.status(payload.operation_id, decision)
        publication.reconcile_visible_revision()
        storage = mount.storage
        if isinstance(payload, FileListRequest):
            return storage.list(payload, decision=decision, fence=disclose)
        if isinstance(payload, FileReadRequest):
            return storage.read(payload, decision=decision, fence=disclose)
        if isinstance(payload, FileDiffRequest):
            return storage.diff(payload, decision=decision, fence=disclose)
        if isinstance(payload, FileHistoryRequest):
            return storage.history(payload, decision=decision, fence=disclose)
        raise GatewayAccessError(422, "invalid_file_operation")

    def _select_mount(
        self, target: GatewayTarget
    ) -> tuple[GatewayTarget, str, NativeFileMount] | None:
        """Load the owner-selected adapter before resolving its policy resource."""

        with self.m_lock:
            selected = self.m_selected
            if selected is not None and selected[0] == target:
                return selected
            self.m_selected = None
            mount = self.m_resolve_mount()
            if mount is not None:
                self.m_selected = target, mount.storage.mount_id, mount
            return self.m_selected

    def _mounts(
        self,
        actor: AuthorizationActor,
        target: GatewayTarget,
        selected: tuple[GatewayTarget, str, NativeFileMount] | None,
        policy: GatewayAccessPolicy,
    ) -> FileMountsResponse:
        """Filter mount discovery by the caller's exact current read permission."""

        if selected is None:
            return FileMountsResponse(mounts=[])
        _, mount_id, mount = selected
        try:
            decision = policy.authorize(
                actor, (Permission(resource=f"files:{mount_id}", action=READ),)
            )
        except GatewayAccessError as error:
            if error.status_code == 403:
                return FileMountsResponse(mounts=[])
            raise
        if decision.target != target:
            raise GatewayAccessError(409, "file_target_changed")
        FilePublication(mount, policy, self.m_manifest_path, target).reconcile_visible_revision()
        descriptor = mount.storage.describe()
        if not policy.revalidate(decision):
            raise GatewayAccessError(403, "insufficient_authority")
        return FileMountsResponse(mounts=[descriptor])

    @staticmethod
    def _edit(
        name: str,
        payload: FileMountRequest,
        mount: NativeFileMount,
        decision: AuthorizationDecision,
        policy: GatewayAccessPolicy,
        disclose: Callable[[AuthorizationDecision], None],
    ) -> FileEditModel:
        """Wait to commit a draft handoff until the store checks its current lease."""

        storage = mount.storage
        match payload:
            case FileDraftListRequest():
                return storage.draft_list(payload, decision=decision, fence=disclose)
            case FileDraftDiffRequest():
                return storage.draft_diff(payload, decision=decision, fence=disclose)
            case FileDraftPathRequest() if name == "draft/read":
                return storage.draft_read(payload, decision=decision, fence=disclose)
        actor = _attributed_actor(decision.actor, policy)
        fence = policy.handoff
        match payload:
            case FileDraftOpenRequest():
                return storage.lease_open(payload, decision=decision, actor=actor, fence=fence)
            case FileDraftWriteRequest():
                content = _decode_file(payload.content_base64)
                return storage.draft_write(
                    payload, content=content, decision=decision, actor=actor, fence=fence
                )
            case FileDraftRenameRequest():
                return storage.draft_rename(payload, decision=decision, actor=actor, fence=fence)
            case FileDraftPathRequest() if name == "draft/mkdir":
                return storage.draft_mkdir(payload, decision=decision, actor=actor, fence=fence)
            case FileDraftPathRequest() if name == "draft/delete":
                return storage.draft_delete(payload, decision=decision, actor=actor, fence=fence)
            case FileDraftCommitRequest():
                return storage.draft_commit(
                    payload, validate=mount.validate, decision=decision, actor=actor, fence=fence
                )
            case FileDraftRequest() if name == "lease/renew":
                return storage.lease_renew(payload, decision=decision, actor=actor, fence=fence)
            case FileDraftRequest() if name == "draft/abort":
                return storage.draft_abort(payload, decision=decision, actor=actor, fence=fence)
        raise GatewayAccessError(422, "invalid_file_operation")


def register_file_edit_routes(app: FastAPI, service: GatewayFileEdits) -> None:
    """Publish the same finite direct operations declared at gateway ingress."""

    for name, (model, _) in FILE_REQUESTS.items():
        app.add_api_route(
            f"{FILE_EDIT_PATH}/{name}",
            _file_handler(name, model, service),
            methods=["POST"],
            name=f"file_edits_{name.replace('/', '_')}",
        )


def _file_handler(
    name: str, model: type[FileTargetRequest], service: GatewayFileEdits
) -> Callable[..., object]:
    """Bind one request model before creating its authenticated route handler."""

    async def handle(request: Request) -> JSONResponse:
        """Use the exact caller established by the shared ingress."""

        actor = getattr(request.state, "gateway_actor", None)
        if not isinstance(actor, AuthorizationActor):
            raise GatewayAccessError(401, "proof_required")
        if request.scope["query_string"]:
            raise GatewayAccessError(422, "invalid_file_operation")
        try:
            payload = parse_access_document(
                model, await request.body(), max_bytes=MAX_FILE_REQUEST_BYTES
            )
        except ValueError:
            raise GatewayAccessError(422, "invalid_file_operation") from None
        result = await run_in_threadpool(service.dispatch, name, payload, actor)
        return JSONResponse(result.model_dump(mode="json"), headers={"Cache-Control": "no-store"})

    return handle


def _attributed_actor(actor: AuthorizationActor, policy: GatewayAccessPolicy) -> FileActor:
    """Project attribution only from verified current owner policy."""

    if actor.kind == "anonymous":
        return FileActor(kind="anonymous")
    if actor.kind == "self":
        return FileActor(kind="self", principal_id=actor.principal_id, label="Managed self")
    principal = next(
        (
            principal
            for principal in policy.store.snapshot().principals
            if principal.principal_id == actor.principal_id
        ),
        None,
    )
    if principal is None:
        raise GatewayAccessError(403, "insufficient_authority")
    return FileActor(
        kind=principal.kind,
        principal_id=principal.principal_id,
        logical_agent_id=principal.logical_agent_id,
        label=principal.label,
    )


def _decode_file(content: str) -> bytes:
    """Decode an exact base64 file after validating the bounded JSON envelope."""

    try:
        result = base64.b64decode(content, validate=True)
    except (Base64Error, ValueError):
        raise GatewayAccessError(422, "invalid_file_content") from None
    if len(result) > MAX_FILE_BYTES:
        raise GatewayAccessError(413, "file_too_large")
    return result
