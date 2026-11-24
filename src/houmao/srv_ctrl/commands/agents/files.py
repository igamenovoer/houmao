"""Scoped manager commands for direct versioned gateway file operations."""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, TypeVar, cast
from uuid import uuid4

import click
from pydantic import BaseModel

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_access_runtime import owner_gateway_client_binding
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.gateway.access import read_private_access_file
from houmao.gateway.file_edits import contracts as file
from houmao.srv_ctrl.commands.agents.access import (
    _VerifiedEndpoint,
    _access_errors,
    _endpoint_options,
    _local_verified_endpoint,
    _peer_signer_path,
    _source_access,
    _verified_endpoint,
)
from houmao.srv_ctrl.commands.output import emit

_Response = TypeVar("_Response", bound=BaseModel)
_KEY_FILE = click.Path(exists=True, dir_okay=False, path_type=Path)
_LIMIT = click.IntRange(min=1, max=file.MAX_LIST_ENTRIES)


@dataclass(frozen=True)
class _FileClient:
    """Select one verified target, signer, and optional draft for a command."""

    endpoint: _VerifiedEndpoint
    client: GatewayClient
    mount: str | None
    draft: str | None
    capability: str | None

    def call(self, name: str, response: type[_Response], **fields: object) -> _Response:
        """Validate the exact local request before using the shared HTTP transport."""

        model, _ = file.FILE_REQUESTS[name]
        common: dict[str, object] = {
            "target": self.endpoint.descriptor.target,
            "presence_id": self.endpoint.descriptor.presence_id,
        }
        if issubclass(model, file.FileMountRequest):
            if self.mount is None:
                raise click.UsageError("Select a mount with --mount.")
            common["mount_id"] = self.mount
        if issubclass(model, file.FileDraftRequest):
            if self.draft is None:
                raise click.UsageError("Select a draft with --draft.")
            common.update(draft_id=self.draft, lease_capability=self.capability)
        payload = model.model_validate({**common, **fields})
        return self.client.request_file_edit(name, payload, response)

    def emit(self, name: str, response: type[BaseModel], **fields: object) -> None:
        """Use the manager's existing text and JSON output modes."""

        with _access_errors():
            emit(self.call(name, response, **fields))


def _file_client() -> _FileClient:
    """Resolve the direct connection after Click has parsed the command."""

    connect = cast(Callable[[], _FileClient], click.get_current_context().meta["file_edit_client"])
    with _access_errors():
        return connect()


@click.group(name="files")
@click.pass_context
@_endpoint_options
@click.option("--signer", type=_KEY_FILE, help="Explicit owner-private enrolled signing key.")
@click.option("--source-agent-id", help="Use this local source agent's configured peer signer.")
@click.option("--self-signer", is_flag=True, help="Use the current managed self's peer signer.")
@click.option("--unsigned", is_flag=True, help="Use the target's unsigned admission policy.")
@click.option("--mount", help="Exact mount ID from authorized discovery.")
@click.option("--draft", help="Current draft ID for private draft operations.")
@click.option(
    "--lease-capability-file",
    type=_KEY_FILE,
    help="Owner-private file containing the anonymous draft capability.",
)
def single_files_group(
    ctx: click.Context,
    url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
    signer: Path | None,
    source_agent_id: str | None,
    self_signer: bool,
    unsigned: bool,
    mount: str | None,
    draft: str | None,
    lease_capability_file: Path | None,
) -> None:
    """Edit versioned files on the selected agent's verified attached gateway."""

    if sum((signer is not None, source_agent_id is not None, self_signer, unsigned)) > 1:
        raise click.UsageError("Select one explicit or configured peer signer or --unsigned.")
    if draft is None and lease_capability_file is not None:
        raise click.UsageError("A lease capability requires a selected draft.")

    def connect() -> _FileClient:
        """Verify the listener before resolving any configured signer."""

        endpoint = _verified_endpoint(url, context_id, generation, presence, ca_bundle)
        selected_signer = signer
        if source_agent_id is not None or self_signer:
            selected_signer = _peer_signer_path(_source_access(source_agent_id))
        if selected_signer is not None:
            client = endpoint.signed_client(selected_signer)
        elif unsigned or endpoint.descriptor.admin_mode == "open":
            client = GatewayClient(
                base_url=endpoint.base_url,
                ca_bundle_path=endpoint.ca_bundle,
                respect_proxy_env=False,
            )
        else:
            raise click.ClickException("Select an enrolled signer for the verified gateway.")
        capability = (
            read_private_access_file(lease_capability_file, limit=64).decode("ascii").strip()
            if lease_capability_file is not None
            else None
        )
        return _FileClient(endpoint, client, mount, draft, capability)

    ctx.meta["file_edit_client"] = connect


@click.group(name="files")
@click.pass_context
@click.option("--mount", help="Exact mount ID from authorized discovery.")
@click.option("--draft", help="Current draft ID for private draft operations.")
@click.option("--unsigned", is_flag=True, help="Use the target's unsigned admission policy.")
@click.option(
    "--lease-capability-file",
    type=_KEY_FILE,
    help="Owner-private file containing the anonymous draft capability.",
)
def self_files_group(
    ctx: click.Context,
    mount: str | None,
    draft: str | None,
    unsigned: bool,
    lease_capability_file: Path | None,
) -> None:
    """Edit versioned files on this managed runtime's verified attached gateway."""

    if lease_capability_file is not None and (draft is None or not unsigned):
        raise click.UsageError("A lease capability requires --draft and --unsigned.")

    def connect() -> _FileClient:
        """Use only this verified runtime and its current managed-self registration."""

        access = _source_access(None)
        endpoint, port = _local_verified_endpoint(access)
        if unsigned:
            client = GatewayClient(base_url=endpoint.base_url, respect_proxy_env=False)
        else:
            binding, generation = owner_gateway_client_binding(
                access.manifest_path, port=port, private=True, prefer_self=True
            )
            if (
                binding is None
                or binding.owner != endpoint.descriptor.target.owner
                or binding.base_url != endpoint.base_url
                or generation != endpoint.descriptor.target.incarnation
            ):
                raise click.ClickException("Current managed-self signing authority is unavailable.")
            client = GatewayClient(
                binding=binding,
                target_incarnation=generation,
                target_presence_id=endpoint.descriptor.presence_id,
                respect_proxy_env=False,
            )
        capability = (
            read_private_access_file(lease_capability_file, limit=64).decode("ascii").strip()
            if lease_capability_file is not None
            else None
        )
        return _FileClient(endpoint, client, mount, draft, capability)

    ctx.meta["file_edit_client"] = connect


@single_files_group.command(name="mounts")
@click.option("--kind", type=click.Choice(["skills", "mcp"]), help="Select a provider kind.")
def mounts(kind: str | None) -> None:
    """List mounts with current read permission."""

    _file_client().emit("mounts", file.FileMountsResponse, kind=kind)


@single_files_group.command(name="list")
@click.argument("directory", required=False)
@click.option("--revision")
@click.option("--after")
@click.option("--limit", type=_LIMIT, default=100)
def list_files(directory: str | None, revision: str | None, after: str | None, limit: int) -> None:
    """List a bounded page of a published revision or the selected draft."""

    client = _file_client()
    fields = {"directory": directory, "after": after, "limit": limit}
    if client.draft is not None:
        if revision is not None:
            raise click.UsageError("A draft already selects its own base revision.")
        client.emit("draft/list", file.FileListResponse, **fields)
    else:
        client.emit("list", file.FileListResponse, revision=revision, **fields)


@single_files_group.command(name="read")
@click.argument("path")
@click.option("--revision")
def read_file(path: str, revision: str | None) -> None:
    """Read a logical file with a bounded base64 content field."""

    client = _file_client()
    if client.draft is not None:
        if revision is not None:
            raise click.UsageError("A draft already selects its own base revision.")
        client.emit("draft/read", file.FileReadResponse, path=path)
    else:
        client.emit("read", file.FileReadResponse, path=path, revision=revision)


@single_files_group.command(name="diff")
@click.argument("commit_id", required=False)
@click.option("--after")
@click.option("--limit", type=_LIMIT, default=100)
def diff(commit_id: str | None, after: str | None, limit: int) -> None:
    """Inspect changes in a retained commit or the selected draft."""

    client = _file_client()
    if client.draft is not None and commit_id is None:
        client.emit("draft/diff", file.FileDiffResponse, after=after, limit=limit)
    elif commit_id is not None and client.draft is None:
        client.emit("diff", file.FileDiffResponse, commit_id=commit_id, after=after, limit=limit)
    else:
        raise click.UsageError("Select one draft or commit ID.")


@single_files_group.command(name="status")
@click.argument("operation_id")
def status(operation_id: str) -> None:
    """Read the strongest known evidence for a retained push."""

    _file_client().emit("status", file.FilePushReceipt, operation_id=operation_id)


@single_files_group.command(name="history")
@click.option("--candidates", is_flag=True)
@click.option("--after")
@click.option("--limit", type=_LIMIT, default=20)
def history(candidates: bool, after: str | None, limit: int) -> None:
    """Read published ancestry or retained candidates."""

    _file_client().emit(
        "history",
        file.FileHistoryResponse,
        history="candidates" if candidates else "published",
        after=after,
        limit=limit,
    )


@single_files_group.group(name="lease")
def lease() -> None:
    """Open or renew a private draft lease."""


@lease.command(name="open")
@click.option("--expected-base", required=True)
def open_lease(expected_base: str) -> None:
    """Reserve a draft based on the selected publication."""

    _file_client().emit("lease/open", file.FileDraftReceipt, expected_base=expected_base)


@lease.command(name="renew")
def renew_lease() -> None:
    """Extend the selected draft's current lease."""

    _file_client().emit("lease/renew", file.FileDraftReceipt)


@single_files_group.command(name="write")
@click.argument("path")
@click.option("--from-file", "source", type=click.File("rb"), required=True)
def write_file(path: str, source: BinaryIO) -> None:
    """Stage bytes read from a local file or standard input."""

    content = source.read(file.MAX_FILE_BYTES + 1)
    if len(content) > file.MAX_FILE_BYTES:
        raise click.UsageError("File exceeds the supported upload size.")
    _file_client().emit(
        "draft/write",
        file.FileMutationReceipt,
        path=path,
        content_base64=base64.b64encode(content).decode("ascii"),
    )


@single_files_group.command(name="delete")
@click.argument("path")
def delete(path: str) -> None:
    """Delete a logical path in the current draft."""

    _file_client().emit("draft/delete", file.FileMutationReceipt, path=path)


@single_files_group.command(name="mkdir")
@click.argument("path")
def mkdir(path: str) -> None:
    """Create a logical directory in the current draft."""

    _file_client().emit("draft/mkdir", file.FileMutationReceipt, path=path)


@single_files_group.command(name="rename")
@click.argument("path")
@click.argument("destination")
def rename(path: str, destination: str) -> None:
    """Move a logical file or directory within the current draft."""

    _file_client().emit(
        "draft/rename", file.FileMutationReceipt, path=path, destination=destination
    )


@single_files_group.command(name="commit")
@click.option("--message", required=True)
def commit(message: str) -> None:
    """Save the selected draft as a candidate Git commit."""

    _file_client().emit("draft/commit", file.FileCommitReceipt, message=message)


@single_files_group.command(name="abort")
def abort() -> None:
    """Discard the selected draft and release its lease."""

    _file_client().emit("draft/abort", file.FileMutationReceipt)


@single_files_group.command(name="push")
@click.argument("commit_id")
@click.option("--expected-base", required=True)
@click.option("--operation-id", help="Exact attempt identity. Defaults to a fresh ID.")
def push(commit_id: str, expected_base: str, operation_id: str | None) -> None:
    """Request publication of an immutable candidate under owner maintenance."""

    _push(commit_id, expected_base, operation_id, when_idle=False)


@self_files_group.command(name="push")
@click.argument("commit_id")
@click.option("--expected-base", required=True)
@click.option("--operation-id", help="Exact attempt identity. Defaults to a fresh ID.")
@click.option("--when-idle", is_flag=True, help="Publish after this runtime becomes idle.")
def self_push(
    commit_id: str, expected_base: str, operation_id: str | None, when_idle: bool
) -> None:
    """Publish now or retain a signed intent until this runtime is idle."""

    _push(commit_id, expected_base, operation_id, when_idle=when_idle)


def _push(commit_id: str, expected_base: str, operation_id: str | None, *, when_idle: bool) -> None:
    """Report the exact publication attempt and retain its identifier after transport loss."""

    identifier = operation_id or uuid4().hex
    client = _file_client()
    with _access_errors():
        try:
            receipt = client.call(
                "push",
                file.FilePushReceipt,
                commit_id=commit_id,
                expected_base=expected_base,
                operation_id=identifier,
                when_idle=when_idle,
            )
        except GatewayHttpError as error:
            if error.status_code is not None and error.status_code < 500:
                raise
            emit({"operation_id": identifier, "candidate": commit_id, "outcome": "unconfirmed"})
            raise click.exceptions.Exit(1) from None
        emit(receipt)
        if receipt.outcome != "published" and not (
            when_idle and receipt.outcome in {"queued", "pending"}
        ):
            raise click.exceptions.Exit(1)


for _name, _command in single_files_group.commands.items():
    if _name != "push":
        self_files_group.add_command(_command, _name)
