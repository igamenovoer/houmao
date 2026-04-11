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


@project_tools_group.group(name="claude")
def claude_tool_group() -> None:
    """Manage the project-local Claude tool subtree."""


@claude_tool_group.command(name="get")
def get_claude_project_tool_command() -> None:
    """Inspect the project-local Claude tool subtree."""

    _emit_tool_get(tool="claude")


@claude_tool_group.group(name="setups")
def claude_tool_setups_group() -> None:
    """Manage Claude setup bundles under `.houmao/agents/tools/claude/setups/`."""


@claude_tool_setups_group.command(name="list")
def list_claude_project_setups_command() -> None:
    """List project-local Claude setup bundles."""

    _emit_tool_setup_list(tool="claude")


@claude_tool_setups_group.command(name="get")
@click.option("--name", required=True, help="Setup bundle name.")
def get_claude_project_setup_command(name: str) -> None:
    """Inspect one project-local Claude setup bundle."""

    _emit_tool_setup_get(tool="claude", name=name)


@claude_tool_setups_group.command(name="add")
@click.option("--name", required=True, help="New setup bundle name.")
@click.option(
    "--from", "source_name", default="default", show_default=True, help="Source setup name."
)
def add_claude_project_setup_command(name: str, source_name: str) -> None:
    """Clone one project-local Claude setup bundle."""

    _emit_tool_setup_add(tool="claude", name=name, source_name=source_name)


@claude_tool_setups_group.command(name="remove")
@click.option("--name", required=True, help="Setup bundle name to remove.")
def remove_claude_project_setup_command(name: str) -> None:
    """Remove one project-local Claude setup bundle."""

    _emit_tool_setup_remove(tool="claude", name=name)


@project_tools_group.group(name="codex")
def codex_tool_group() -> None:
    """Manage the project-local Codex tool subtree."""


@codex_tool_group.command(name="get")
def get_codex_project_tool_command() -> None:
    """Inspect the project-local Codex tool subtree."""

    _emit_tool_get(tool="codex")


@codex_tool_group.group(name="setups")
def codex_tool_setups_group() -> None:
    """Manage Codex setup bundles under `.houmao/agents/tools/codex/setups/`."""


@codex_tool_setups_group.command(name="list")
def list_codex_project_setups_command() -> None:
    """List project-local Codex setup bundles."""

    _emit_tool_setup_list(tool="codex")


@codex_tool_setups_group.command(name="get")
@click.option("--name", required=True, help="Setup bundle name.")
def get_codex_project_setup_command(name: str) -> None:
    """Inspect one project-local Codex setup bundle."""

    _emit_tool_setup_get(tool="codex", name=name)


@codex_tool_setups_group.command(name="add")
@click.option("--name", required=True, help="New setup bundle name.")
@click.option(
    "--from", "source_name", default="default", show_default=True, help="Source setup name."
)
def add_codex_project_setup_command(name: str, source_name: str) -> None:
    """Clone one project-local Codex setup bundle."""

    _emit_tool_setup_add(tool="codex", name=name, source_name=source_name)


@codex_tool_setups_group.command(name="remove")
@click.option("--name", required=True, help="Setup bundle name to remove.")
def remove_codex_project_setup_command(name: str) -> None:
    """Remove one project-local Codex setup bundle."""

    _emit_tool_setup_remove(tool="codex", name=name)


@project_tools_group.group(name="gemini")
def gemini_tool_group() -> None:
    """Manage the project-local Gemini tool subtree."""


@gemini_tool_group.command(name="get")
def get_gemini_project_tool_command() -> None:
    """Inspect the project-local Gemini tool subtree."""

    _emit_tool_get(tool="gemini")


@gemini_tool_group.group(name="setups")
def gemini_tool_setups_group() -> None:
    """Manage Gemini setup bundles under `.houmao/agents/tools/gemini/setups/`."""


@gemini_tool_setups_group.command(name="list")
def list_gemini_project_setups_command() -> None:
    """List project-local Gemini setup bundles."""

    _emit_tool_setup_list(tool="gemini")


@gemini_tool_setups_group.command(name="get")
@click.option("--name", required=True, help="Setup bundle name.")
def get_gemini_project_setup_command(name: str) -> None:
    """Inspect one project-local Gemini setup bundle."""

    _emit_tool_setup_get(tool="gemini", name=name)


@gemini_tool_setups_group.command(name="add")
@click.option("--name", required=True, help="New setup bundle name.")
@click.option(
    "--from", "source_name", default="default", show_default=True, help="Source setup name."
)
def add_gemini_project_setup_command(name: str, source_name: str) -> None:
    """Clone one project-local Gemini setup bundle."""

    _emit_tool_setup_add(tool="gemini", name=name, source_name=source_name)


@gemini_tool_setups_group.command(name="remove")
@click.option("--name", required=True, help="Setup bundle name to remove.")
def remove_gemini_project_setup_command(name: str) -> None:
    """Remove one project-local Gemini setup bundle."""

    _emit_tool_setup_remove(tool="gemini", name=name)
