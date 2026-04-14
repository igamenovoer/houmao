"""Managed-agent workspace commands for `houmao-mgr agents`."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal, TypeVar, cast

import click

from houmao.agents.agent_workspace import (
    AgentWorkspacePaths,
    clear_workspace_lane,
    delete_workspace_path,
    lane_root,
    list_workspace_tree,
    read_memo,
    read_workspace_file,
    write_memo,
    write_workspace_file,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayWorkspaceActionResponseV1,
    GatewayWorkspaceFileResponseV1,
    GatewayWorkspaceFileWriteRequestV1,
    GatewayWorkspaceLane,
    GatewayWorkspaceLanePathRequestV1,
    GatewayWorkspaceLaneRequestV1,
    GatewayWorkspaceMemoResponseV1,
    GatewayWorkspaceMemoWriteRequestV1,
    GatewayWorkspaceSummaryV1,
    GatewayWorkspaceTreeEntryV1,
    GatewayWorkspaceTreeRequestV1,
    GatewayWorkspaceTreeResponseV1,
)

from ..common import managed_agent_selector_options, pair_port_option, pair_request
from ..managed_agents import ManagedAgentTarget, resolve_managed_agent_target
from ..output import emit

_FunctionT = TypeVar("_FunctionT", bound=Callable[..., object])


def _lane_option(function: _FunctionT) -> _FunctionT:
    """Attach the shared workspace lane option."""

    return click.option(
        "--lane",
        type=click.Choice(["scratch", "persist"], case_sensitive=False),
        required=True,
        help="Workspace lane to address.",
    )(function)


@click.group(name="workspace")
def workspace_group() -> None:
    """Inspect and mutate managed-agent workspace files."""


@workspace_group.command(name="path")
@pair_port_option()
@managed_agent_selector_options
def workspace_path_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show resolved workspace paths for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(workspace_summary(target))


@workspace_group.command(name="status")
@pair_port_option()
@managed_agent_selector_options
def workspace_status_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show resolved workspace paths for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(workspace_summary(target))


@workspace_group.command(name="memo")
@click.argument("operation", type=click.Choice(["show", "set", "append"], case_sensitive=False))
@click.option("--content", default=None, help="Inline memo content for `set` or `append`.")
@click.option("--content-file", default=None, help="Memo content file for `set` or `append`.")
@pair_port_option()
@managed_agent_selector_options
def workspace_memo_command(
    operation: str,
    content: str | None,
    content_file: str | None,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show, replace, or append the fixed managed-agent memo."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    normalized_operation = cast(Literal["show", "set", "append"], operation.lower())
    if normalized_operation == "show":
        if content is not None or content_file is not None:
            raise click.ClickException(
                "Memo `show` does not accept `--content` or `--content-file`."
            )
        emit(workspace_memo(target))
        return

    resolved_content = _resolve_workspace_content(content=content, content_file=content_file)
    emit(
        workspace_memo_write(
            target,
            content=resolved_content,
            append=normalized_operation == "append",
        )
    )


@workspace_group.command(name="tree")
@_lane_option
@click.option("--path", "relative_path", default=".", show_default=True, help="Lane-relative path.")
@pair_port_option()
@managed_agent_selector_options
def workspace_tree_command(
    lane: str,
    relative_path: str,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """List one workspace lane tree."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(workspace_tree(target, lane=_lane_value(lane), relative_path=relative_path))


@workspace_group.command(name="read")
@_lane_option
@click.option("--path", "relative_path", required=True, help="Lane-relative file path.")
@pair_port_option()
@managed_agent_selector_options
def workspace_read_command(
    lane: str,
    relative_path: str,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Read one contained workspace lane file."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(workspace_file_read(target, lane=_lane_value(lane), relative_path=relative_path))


@workspace_group.command(name="write")
@_lane_option
@click.option("--path", "relative_path", required=True, help="Lane-relative file path.")
@click.option("--content", default=None, help="Inline file content.")
@click.option("--content-file", default=None, help="File containing content to write.")
@pair_port_option()
@managed_agent_selector_options
def workspace_write_command(
    lane: str,
    relative_path: str,
    content: str | None,
    content_file: str | None,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Write one contained workspace lane file."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        workspace_file_write(
            target,
            lane=_lane_value(lane),
            relative_path=relative_path,
            content=_resolve_workspace_content(content=content, content_file=content_file),
        )
    )


@workspace_group.command(name="append")
@_lane_option
@click.option("--path", "relative_path", required=True, help="Lane-relative file path.")
@click.option("--content", default=None, help="Inline file content.")
@click.option("--content-file", default=None, help="File containing content to append.")
@pair_port_option()
@managed_agent_selector_options
def workspace_append_command(
    lane: str,
    relative_path: str,
    content: str | None,
    content_file: str | None,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Append to one contained workspace lane file."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        workspace_file_write(
            target,
            lane=_lane_value(lane),
            relative_path=relative_path,
            content=_resolve_workspace_content(content=content, content_file=content_file),
            append=True,
        )
    )


@workspace_group.command(name="delete")
@_lane_option
@click.option(
    "--path", "relative_path", required=True, help="Lane-relative file or directory path."
)
@pair_port_option()
@managed_agent_selector_options
def workspace_delete_command(
    lane: str,
    relative_path: str,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Delete one contained workspace lane path."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(workspace_path_delete(target, lane=_lane_value(lane), relative_path=relative_path))


@workspace_group.command(name="clear")
@_lane_option
@click.option("--dry-run", is_flag=True, help="Show the lane that would be cleared.")
@pair_port_option()
@managed_agent_selector_options
def workspace_clear_command(
    lane: str,
    dry_run: bool,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Clear one workspace lane while preserving the lane directory."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(workspace_lane_clear(target, lane=_lane_value(lane), dry_run=dry_run))


def _lane_value(value: str) -> GatewayWorkspaceLane:
    """Normalize a CLI lane value."""

    return cast(GatewayWorkspaceLane, value.lower())


def _resolve_workspace_content(*, content: str | None, content_file: str | None) -> str:
    """Resolve workspace mutation content from an option, file, or stdin."""

    if content is not None and content_file is not None:
        raise click.ClickException("Use either `--content` or `--content-file`, not both.")
    if content is not None:
        if "\x00" in content:
            raise click.ClickException("`--content` must not contain NUL bytes.")
        return content
    if content_file is not None:
        try:
            value = Path(content_file).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise click.ClickException(f"Failed to read `--content-file`: {exc}") from exc
        if "\x00" in value:
            raise click.ClickException("`--content-file` must not contain NUL bytes.")
        return value

    stdin = click.get_text_stream("stdin")
    if stdin.isatty():
        raise click.ClickException(
            "Provide `--content`, `--content-file`, or pipe content on stdin."
        )
    value = stdin.read()
    if "\x00" in value:
        raise click.ClickException("Workspace content must not contain NUL bytes.")
    return value


def workspace_summary(target: ManagedAgentTarget) -> GatewayWorkspaceSummaryV1:
    """Return a managed-agent workspace summary."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_workspace, target.agent_ref)

    paths = _local_workspace_paths(target)
    return GatewayWorkspaceSummaryV1(
        workspace_root=str(paths.workspace_root),
        memo_file=str(paths.memo_file),
        scratch_dir=str(paths.scratch_dir),
        persist_binding=paths.persist_binding,
        persist_dir=str(paths.persist_dir) if paths.persist_dir is not None else None,
    )


def workspace_memo(target: ManagedAgentTarget) -> GatewayWorkspaceMemoResponseV1:
    """Return the fixed workspace memo for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.get_managed_agent_gateway_workspace_memo, target.agent_ref
        )

    paths = _local_workspace_paths(target)
    try:
        content = read_memo(paths)
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayWorkspaceMemoResponseV1(memo_file=str(paths.memo_file), content=content)


def workspace_memo_write(
    target: ManagedAgentTarget,
    *,
    content: str,
    append: bool = False,
) -> GatewayWorkspaceMemoResponseV1:
    """Write or append the fixed workspace memo for one managed agent."""

    request_model = GatewayWorkspaceMemoWriteRequestV1(content=content)
    if target.mode == "server":
        assert target.client is not None
        if append:
            return pair_request(
                target.client.append_managed_agent_gateway_workspace_memo,
                target.agent_ref,
                request_model,
            )
        return pair_request(
            target.client.put_managed_agent_gateway_workspace_memo,
            target.agent_ref,
            request_model,
        )

    paths = _local_workspace_paths(target)
    try:
        write_memo(paths, content, append=append)
        new_content = read_memo(paths)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayWorkspaceMemoResponseV1(memo_file=str(paths.memo_file), content=new_content)


def workspace_tree(
    target: ManagedAgentTarget,
    *,
    lane: GatewayWorkspaceLane,
    relative_path: str = ".",
) -> GatewayWorkspaceTreeResponseV1:
    """List one workspace lane tree."""

    request_model = GatewayWorkspaceTreeRequestV1(lane=lane, path=relative_path)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.list_managed_agent_gateway_workspace_tree,
            target.agent_ref,
            request_model,
        )

    paths = _local_workspace_paths(target)
    try:
        entries = list_workspace_tree(paths, lane=lane, relative_path=relative_path)
        root = lane_root(paths, lane)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayWorkspaceTreeResponseV1(
        lane=lane,
        root=str(root),
        path=relative_path,
        entries=[
            GatewayWorkspaceTreeEntryV1(
                path=entry.path,
                kind=entry.kind,
                size_bytes=entry.size_bytes,
            )
            for entry in entries
        ],
    )


def workspace_file_read(
    target: ManagedAgentTarget,
    *,
    lane: GatewayWorkspaceLane,
    relative_path: str,
) -> GatewayWorkspaceFileResponseV1:
    """Read one workspace lane file."""

    request_model = GatewayWorkspaceLanePathRequestV1(lane=lane, path=relative_path)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.read_managed_agent_gateway_workspace_file,
            target.agent_ref,
            request_model,
        )

    paths = _local_workspace_paths(target)
    try:
        content = read_workspace_file(paths, lane=lane, relative_path=relative_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayWorkspaceFileResponseV1(lane=lane, path=relative_path, content=content)


def workspace_file_write(
    target: ManagedAgentTarget,
    *,
    lane: GatewayWorkspaceLane,
    relative_path: str,
    content: str,
    append: bool = False,
) -> GatewayWorkspaceActionResponseV1:
    """Write or append one workspace lane file."""

    request_model = GatewayWorkspaceFileWriteRequestV1(
        lane=lane,
        path=relative_path,
        content=content,
    )
    if target.mode == "server":
        assert target.client is not None
        if append:
            return pair_request(
                target.client.append_managed_agent_gateway_workspace_file,
                target.agent_ref,
                request_model,
            )
        return pair_request(
            target.client.write_managed_agent_gateway_workspace_file,
            target.agent_ref,
            request_model,
        )

    paths = _local_workspace_paths(target)
    try:
        write_workspace_file(
            paths,
            lane=lane,
            relative_path=relative_path,
            content=content,
            append=append,
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayWorkspaceActionResponseV1(
        action="append_file" if append else "write_file",
        lane=lane,
        path=relative_path,
        detail=f"Workspace file {'appended' if append else 'written'}: {lane}:{relative_path}",
    )


def workspace_path_delete(
    target: ManagedAgentTarget,
    *,
    lane: GatewayWorkspaceLane,
    relative_path: str,
) -> GatewayWorkspaceActionResponseV1:
    """Delete one workspace lane path."""

    request_model = GatewayWorkspaceLanePathRequestV1(lane=lane, path=relative_path)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.delete_managed_agent_gateway_workspace_path,
            target.agent_ref,
            request_model,
        )

    paths = _local_workspace_paths(target)
    try:
        delete_workspace_path(paths, lane=lane, relative_path=relative_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayWorkspaceActionResponseV1(
        action="delete_path",
        lane=lane,
        path=relative_path,
        detail=f"Workspace path deleted: {lane}:{relative_path}",
    )


def workspace_lane_clear(
    target: ManagedAgentTarget,
    *,
    lane: GatewayWorkspaceLane,
    dry_run: bool = False,
) -> GatewayWorkspaceActionResponseV1:
    """Clear one workspace lane for a managed agent."""

    request_model = GatewayWorkspaceLaneRequestV1(lane=lane)
    if dry_run:
        root = _workspace_lane_root_for_dry_run(target, lane=lane)
        return GatewayWorkspaceActionResponseV1(
            action="clear_lane",
            lane=lane,
            detail=f"Dry run: would clear workspace lane `{lane}` at `{root}`.",
        )

    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.clear_managed_agent_gateway_workspace_lane,
            target.agent_ref,
            request_model,
        )

    paths = _local_workspace_paths(target)
    try:
        clear_workspace_lane(paths, lane=lane)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayWorkspaceActionResponseV1(
        action="clear_lane",
        lane=lane,
        detail=f"Workspace lane cleared: {lane}",
    )


def _workspace_lane_root_for_dry_run(
    target: ManagedAgentTarget, *, lane: GatewayWorkspaceLane
) -> str:
    """Return the lane root string for a dry-run clear payload."""

    if target.mode == "server":
        summary = workspace_summary(target)
        if lane == "scratch":
            return summary.scratch_dir
        if summary.persist_dir is None:
            raise click.ClickException("The persist lane is disabled for this managed agent.")
        return summary.persist_dir

    paths = _local_workspace_paths(target)
    try:
        return str(lane_root(paths, lane))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _local_workspace_paths(target: ManagedAgentTarget) -> AgentWorkspacePaths:
    """Return manifest-backed local workspace paths for one resolved target."""

    if target.mode != "local" or target.controller is None:
        raise click.ClickException("Workspace direct file access requires a local managed agent.")
    controller = target.controller
    if (
        controller.workspace_root is None
        or controller.memo_file is None
        or controller.scratch_dir is None
        or controller.persist_binding is None
    ):
        raise click.ClickException(
            "This managed agent does not expose workspace metadata. Relaunch it with the "
            "current workspace-aware runtime."
        )
    return AgentWorkspacePaths(
        workspace_root=controller.workspace_root,
        memo_file=controller.memo_file,
        scratch_dir=controller.scratch_dir,
        persist_binding=controller.persist_binding,
        persist_dir=controller.persist_dir,
    )
