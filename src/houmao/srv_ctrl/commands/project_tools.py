"""Project-scoped tool setup commands for `houmao-mgr project agents tools`."""

from __future__ import annotations

# ruff: noqa: F403,F405
from .project_common import *


@click.group(name="tools")
def project_tools_group() -> None:
    """Manage project-local tool content under `.houmao/agents/tools/`."""


def _emit_tool_get(*, tool: str) -> None:
    """Emit one project-local tool summary."""

    overlay = _resolve_existing_project_overlay()
    tool_root = _tool_root(overlay=overlay, tool=tool)
    adapter_path = (tool_root / "adapter.yaml").resolve()
    emit(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "tool_root": str(tool_root),
            "adapter_path": str(adapter_path),
            "adapter_present": adapter_path.is_file(),
            "setups": _list_tool_setup_names(overlay=overlay, tool=tool),
            "auth_bundles": _list_tool_bundle_names(overlay=overlay, tool=tool),
        }
    )


def _emit_tool_setup_list(*, tool: str) -> None:
    """Emit the setup names for one supported tool."""

    overlay = _resolve_existing_project_overlay()
    emit(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "setups": _list_tool_setup_names(overlay=overlay, tool=tool),
        }
    )


def _emit_tool_setup_get(*, tool: str, name: str) -> None:
    """Emit one project-local setup summary."""

    overlay = _resolve_existing_project_overlay()
    setup_name = _require_non_empty_name(name, field_name="--name")
    setup_path = _tool_setup_path(overlay=overlay, tool=tool, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Setup bundle not found: {setup_path}")
    emit(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "name": setup_name,
            "path": str(setup_path),
            "files": _relative_file_listing(setup_path),
        }
    )


def _emit_tool_setup_add(*, tool: str, name: str, source_name: str) -> None:
    """Clone one project-local tool setup bundle."""

    overlay = _ensure_project_overlay()
    target_name = _require_non_empty_name(name, field_name="--name")
    resolved_source_name = _require_non_empty_name(source_name, field_name="--from")
    source_path = _tool_setup_path(overlay=overlay, tool=tool, name=resolved_source_name)
    target_path = _tool_setup_path(overlay=overlay, tool=tool, name=target_name)
    if not source_path.is_dir():
        raise click.ClickException(f"Source setup bundle not found: {source_path}")
    if target_path.exists():
        raise click.ClickException(f"Setup bundle already exists: {target_path}")
    shutil.copytree(source_path, target_path)
    emit(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "name": target_name,
            "source_name": resolved_source_name,
            "path": str(target_path),
            "created": True,
        }
    )


def _emit_tool_setup_remove(*, tool: str, name: str) -> None:
    """Remove one project-local tool setup bundle."""

    overlay = _resolve_existing_project_overlay()
    setup_name = _require_non_empty_name(name, field_name="--name")
    setup_path = _tool_setup_path(overlay=overlay, tool=tool, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Setup bundle not found: {setup_path}")
    shutil.rmtree(setup_path)
    emit(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "name": setup_name,
            "removed": True,
            "path": str(setup_path),
        }
    )


def _register_tool_commands(tool: str) -> click.Group:
    """Build one project-local tool group."""

    @click.group(
        name=tool, help=f"Manage project-local content under `.houmao/agents/tools/{tool}/`."
    )
    def tool_group() -> None:
        """Manage one project-local tool subtree."""

    @tool_group.command(name="get")
    def get_tool_command() -> None:
        """Inspect one project-local tool subtree."""

        _emit_tool_get(tool=tool)

    @tool_group.group(name="setups")
    def setups_group() -> None:
        """Manage project-local setup bundles for this tool."""

    @setups_group.command(name="list")
    def list_setups_command() -> None:
        """List project-local setup bundles."""

        _emit_tool_setup_list(tool=tool)

    @setups_group.command(name="get")
    @click.option("--name", required=True, help="Setup bundle name.")
    def get_setup_command(name: str) -> None:
        """Inspect one project-local setup bundle."""

        _emit_tool_setup_get(tool=tool, name=name)

    @setups_group.command(name="add")
    @click.option("--name", required=True, help="New setup bundle name.")
    @click.option(
        "--from", "source_name", default="default", show_default=True, help="Source setup name."
    )
    def add_setup_command(name: str, source_name: str) -> None:
        """Clone one project-local setup bundle."""

        _emit_tool_setup_add(tool=tool, name=name, source_name=source_name)

    @setups_group.command(name="remove")
    @click.option("--name", required=True, help="Setup bundle name to remove.")
    def remove_setup_command(name: str) -> None:
        """Remove one project-local setup bundle."""

        _emit_tool_setup_remove(tool=tool, name=name)

    return tool_group


for _tool in _SUPPORTED_PROJECT_TOOLS:
    project_tools_group.add_command(_register_tool_commands(_tool))
