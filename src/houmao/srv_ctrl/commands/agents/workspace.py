"""Managed-agent memory commands for `houmao-mgr agents`."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

import click

from houmao.agents.agent_workspace import (
    AgentMemoryPaths,
    delete_memory_page,
    list_memory_pages,
    read_memo,
    read_memory_page,
    resolve_memory_page_path,
    write_memo,
    write_memory_page,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayMemoryActionResponseV1,
    GatewayMemoryMemoResponseV1,
    GatewayMemoryMemoWriteRequestV1,
    GatewayMemoryPageEntryV1,
    GatewayMemoryPagePathRequestV1,
    GatewayMemoryPagePathResolutionV1,
    GatewayMemoryPageResponseV1,
    GatewayMemoryPageTreeRequestV1,
    GatewayMemoryPageTreeResponseV1,
    GatewayMemoryPageWriteRequestV1,
    GatewayMemorySummaryV1,
)

from ..common import managed_agent_selector_options, pair_port_option, pair_request
from ..managed_agents import ManagedAgentTarget, resolve_managed_agent_target
from ..output import emit


@click.group(name="memory")
def memory_group() -> None:
    """Inspect and mutate managed-agent memo pages."""


@memory_group.command(name="path")
@pair_port_option()
@managed_agent_selector_options
def memory_path_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show resolved memory paths for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(memory_summary(target))


@memory_group.command(name="status")
@pair_port_option()
@managed_agent_selector_options
def memory_status_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Show resolved memory paths for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(memory_summary(target))


@memory_group.command(name="memo")
@click.argument("operation", type=click.Choice(["show", "set", "append"], case_sensitive=False))
@click.option("--content", default=None, help="Inline memo content for `set` or `append`.")
@click.option("--content-file", default=None, help="Memo content file for `set` or `append`.")
@pair_port_option()
@managed_agent_selector_options
def memory_memo_command(
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
        emit(memory_memo(target))
        return

    emit(
        memory_memo_write(
            target,
            content=_resolve_memory_content(content=content, content_file=content_file),
            append=normalized_operation == "append",
        )
    )


@memory_group.command(name="tree")
@click.option("--path", "relative_path", default=".", show_default=True, help="Pages path.")
@pair_port_option()
@managed_agent_selector_options
def memory_tree_command(
    relative_path: str,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """List the pages directory tree."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(memory_pages_tree(target, relative_path=relative_path))


@memory_group.command(name="resolve")
@click.option("--path", "relative_path", required=True, help="Pages path.")
@pair_port_option()
@managed_agent_selector_options
def memory_resolve_command(
    relative_path: str,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Resolve one contained memory page path."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(memory_page_resolve(target, relative_path=relative_path))


@memory_group.command(name="read")
@click.option("--path", "relative_path", required=True, help="Pages file path.")
@pair_port_option()
@managed_agent_selector_options
def memory_read_command(
    relative_path: str,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Read one contained memory page."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(memory_page_read(target, relative_path=relative_path))


@memory_group.command(name="write")
@click.option("--path", "relative_path", required=True, help="Pages file path.")
@click.option("--content", default=None, help="Inline file content.")
@click.option("--content-file", default=None, help="File containing content to write.")
@pair_port_option()
@managed_agent_selector_options
def memory_write_command(
    relative_path: str,
    content: str | None,
    content_file: str | None,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Write one contained memory page."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        memory_page_write(
            target,
            relative_path=relative_path,
            content=_resolve_memory_content(content=content, content_file=content_file),
        )
    )


@memory_group.command(name="append")
@click.option("--path", "relative_path", required=True, help="Pages file path.")
@click.option("--content", default=None, help="Inline file content.")
@click.option("--content-file", default=None, help="File containing content to append.")
@pair_port_option()
@managed_agent_selector_options
def memory_append_command(
    relative_path: str,
    content: str | None,
    content_file: str | None,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Append to one contained memory page."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        memory_page_write(
            target,
            relative_path=relative_path,
            content=_resolve_memory_content(content=content, content_file=content_file),
            append=True,
        )
    )


@memory_group.command(name="delete")
@click.option("--path", "relative_path", required=True, help="Pages file or directory path.")
@pair_port_option()
@managed_agent_selector_options
def memory_delete_command(
    relative_path: str,
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Delete one contained memory page path."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(memory_page_delete(target, relative_path=relative_path))


def _resolve_memory_content(*, content: str | None, content_file: str | None) -> str:
    """Resolve memory mutation content from an option, file, or stdin."""

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
        raise click.ClickException("Memory content must not contain NUL bytes.")
    return value


def memory_summary(target: ManagedAgentTarget) -> GatewayMemorySummaryV1:
    """Return a managed-agent memory summary."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_memory, target.agent_ref)

    paths = _local_memory_paths(target)
    return GatewayMemorySummaryV1(
        memory_root=str(paths.memory_root),
        memo_file=str(paths.memo_file),
        pages_dir=str(paths.pages_dir),
    )


def memory_memo(target: ManagedAgentTarget) -> GatewayMemoryMemoResponseV1:
    """Return the fixed memory memo for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_memory_memo, target.agent_ref)

    paths = _local_memory_paths(target)
    try:
        content = read_memo(paths)
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMemoryMemoResponseV1(memo_file=str(paths.memo_file), content=content)


def memory_memo_write(
    target: ManagedAgentTarget,
    *,
    content: str,
    append: bool = False,
) -> GatewayMemoryMemoResponseV1:
    """Write or append the fixed memory memo for one managed agent."""

    request_model = GatewayMemoryMemoWriteRequestV1(content=content)
    if target.mode == "server":
        assert target.client is not None
        if append:
            return pair_request(
                target.client.append_managed_agent_gateway_memory_memo,
                target.agent_ref,
                request_model,
            )
        return pair_request(
            target.client.put_managed_agent_gateway_memory_memo,
            target.agent_ref,
            request_model,
        )

    paths = _local_memory_paths(target)
    try:
        write_memo(paths, content, append=append)
        new_content = read_memo(paths)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMemoryMemoResponseV1(memo_file=str(paths.memo_file), content=new_content)


def memory_pages_tree(
    target: ManagedAgentTarget,
    *,
    relative_path: str = ".",
) -> GatewayMemoryPageTreeResponseV1:
    """List the pages directory tree."""

    request_model = GatewayMemoryPageTreeRequestV1(path=relative_path)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.list_managed_agent_gateway_memory_pages,
            target.agent_ref,
            request_model,
        )

    paths = _local_memory_paths(target)
    try:
        entries = list_memory_pages(paths, relative_path=relative_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMemoryPageTreeResponseV1(
        root=str(paths.pages_dir),
        path=relative_path,
        entries=[
            GatewayMemoryPageEntryV1(
                path=entry.path,
                relative_link=entry.relative_link,
                absolute_path=str(entry.absolute_path),
                kind=entry.kind,
                size_bytes=entry.size_bytes,
            )
            for entry in entries
        ],
    )


def memory_page_resolve(
    target: ManagedAgentTarget,
    *,
    relative_path: str,
) -> GatewayMemoryPagePathResolutionV1:
    """Resolve one memory page path."""

    request_model = GatewayMemoryPagePathRequestV1(path=relative_path)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.resolve_managed_agent_gateway_memory_page,
            target.agent_ref,
            request_model,
        )

    paths = _local_memory_paths(target)
    try:
        resolved = resolve_memory_page_path(paths, relative_path=relative_path)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMemoryPagePathResolutionV1(
        path=resolved.path,
        relative_link=resolved.relative_link,
        absolute_path=str(resolved.absolute_path),
        exists=resolved.exists,
        kind=resolved.kind,
        size_bytes=resolved.size_bytes,
    )


def memory_page_read(
    target: ManagedAgentTarget,
    *,
    relative_path: str,
) -> GatewayMemoryPageResponseV1:
    """Read one memory page."""

    request_model = GatewayMemoryPagePathRequestV1(path=relative_path)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.read_managed_agent_gateway_memory_page,
            target.agent_ref,
            request_model,
        )

    paths = _local_memory_paths(target)
    try:
        resolved = resolve_memory_page_path(paths, relative_path=relative_path)
        content = read_memory_page(paths, relative_path=relative_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMemoryPageResponseV1(
        path=resolved.path,
        relative_link=resolved.relative_link,
        absolute_path=str(resolved.absolute_path),
        content=content,
    )


def memory_page_write(
    target: ManagedAgentTarget,
    *,
    relative_path: str,
    content: str,
    append: bool = False,
) -> GatewayMemoryActionResponseV1:
    """Write or append one memory page."""

    request_model = GatewayMemoryPageWriteRequestV1(path=relative_path, content=content)
    if target.mode == "server":
        assert target.client is not None
        if append:
            return pair_request(
                target.client.append_managed_agent_gateway_memory_page,
                target.agent_ref,
                request_model,
            )
        return pair_request(
            target.client.write_managed_agent_gateway_memory_page,
            target.agent_ref,
            request_model,
        )

    paths = _local_memory_paths(target)
    try:
        write_memory_page(
            paths,
            relative_path=relative_path,
            content=content,
            append=append,
        )
        resolved = resolve_memory_page_path(paths, relative_path=relative_path)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMemoryActionResponseV1(
        action="append_page" if append else "write_page",
        path=resolved.path,
        relative_link=resolved.relative_link,
        absolute_path=str(resolved.absolute_path),
        detail=f"Memory page {'appended' if append else 'written'}: {relative_path}",
    )


def memory_page_delete(
    target: ManagedAgentTarget,
    *,
    relative_path: str,
) -> GatewayMemoryActionResponseV1:
    """Delete one memory page path."""

    request_model = GatewayMemoryPagePathRequestV1(path=relative_path)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.delete_managed_agent_gateway_memory_page,
            target.agent_ref,
            request_model,
        )

    paths = _local_memory_paths(target)
    try:
        delete_memory_page(paths, relative_path=relative_path)
        resolved = resolve_memory_page_path(paths, relative_path=relative_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMemoryActionResponseV1(
        action="delete_page",
        path=resolved.path,
        relative_link=resolved.relative_link,
        absolute_path=str(resolved.absolute_path),
        detail=f"Memory page deleted: {relative_path}",
    )


def _local_memory_paths(target: ManagedAgentTarget) -> AgentMemoryPaths:
    """Return manifest-backed local memory paths for one resolved target."""

    if target.mode != "local" or target.controller is None:
        raise click.ClickException("Memory direct file access requires a local managed agent.")
    controller = target.controller
    if (
        controller.memory_root is None
        or controller.memo_file is None
        or controller.pages_dir is None
    ):
        raise click.ClickException(
            "This managed agent does not expose memory metadata. Relaunch it with the current "
            "memory-aware runtime."
        )
    return AgentMemoryPaths(
        memory_root=controller.memory_root,
        memo_file=controller.memo_file,
        pages_dir=controller.pages_dir,
    )
