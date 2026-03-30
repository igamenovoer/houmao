"""Repo-local project-overlay commands for `houmao-mgr`."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import click
import yaml

from houmao.agents.definition_parser import (
    AuthFileMapping,
    ToolAdapter,
    parse_agent_preset,
    parse_tool_adapter,
)
from houmao.agents.launch_env import (
    parse_persistent_env_record_specs,
    resolve_runtime_env_set_specs,
    validate_persistent_env_records,
)
from houmao.agents.realm_controller.manifest import load_session_manifest
from houmao.project.catalog import ProjectCatalog
from houmao.project.easy import (
    SpecialistMetadata,
    TOOL_PROVIDER_MAP,
    list_specialists,
    load_specialist,
    remove_specialist_metadata,
)
from houmao.project.overlay import (
    HoumaoProjectOverlay,
    bootstrap_project_overlay,
    ensure_project_agent_compatibility_tree,
    materialize_project_agent_catalog_projection,
    require_project_overlay,
    resolve_project_aware_agent_def_dir,
)

from .agents.core import emit_local_launch_completion, launch_managed_agent_locally
from .common import (
    build_destructive_confirmation_callback,
    confirm_destructive_action,
    emit_json,
    overwrite_confirm_option,
)
from .mailbox_support import (
    cleanup_mailbox_root,
    get_mailbox_account,
    get_mailbox_message,
    init_mailbox_root,
    list_mailbox_accounts,
    list_mailbox_messages,
    mailbox_root_status_payload,
    register_mailbox_at_root,
    repair_mailbox_root,
    unregister_mailbox_at_root,
)
from .managed_agents import list_managed_agents, resolve_managed_agent_target, stop_managed_agent

_SECRET_ENV_TOKENS: tuple[str, ...] = ("KEY", "TOKEN", "SECRET", "PASSWORD")
_SUPPORTED_PROJECT_TOOLS: tuple[str, ...] = ("claude", "codex", "gemini")


@click.group(name="project")
def project_group() -> None:
    """Local repo-local Houmao project-overlay administration."""


@project_group.command(name="init")
@click.option(
    "--with-compatibility-profiles",
    is_flag=True,
    help="Also create the optional `.houmao/agents/compatibility-profiles/` subtree.",
)
def init_project_command(with_compatibility_profiles: bool) -> None:
    """Create or validate the local `.houmao/` project overlay in the current directory."""

    cwd = Path.cwd().resolve()
    try:
        result = bootstrap_project_overlay(
            cwd,
            include_compatibility_profiles=with_compatibility_profiles,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    emit_json(
        {
            "project_root": str(result.project_overlay.project_root),
            "overlay_root": str(result.project_overlay.overlay_root),
            "config_path": str(result.project_overlay.config_path),
            "catalog_path": str(result.project_overlay.catalog_path),
            "content_root": str(result.project_overlay.content_root),
            "agent_def_dir": str(result.project_overlay.agents_root),
            "mailbox_root": str(result.project_overlay.mailbox_root),
            "easy_root": str(result.project_overlay.easy_root),
            "created_directories": [str(path) for path in result.created_directories],
            "written_files": [str(path) for path in result.written_files],
            "preserved_files": [str(path) for path in result.preserved_files],
        }
    )


@project_group.command(name="status")
def project_status_command() -> None:
    """Report the discovered repo-local Houmao project-overlay state."""

    cwd = Path.cwd().resolve()
    resolution = resolve_project_aware_agent_def_dir(cwd=cwd)
    overlay = resolution.project_overlay
    emit_json(
        {
            "discovered": overlay is not None,
            "project_root": str(overlay.project_root) if overlay is not None else None,
            "overlay_root": str(overlay.overlay_root) if overlay is not None else None,
            "config_path": str(overlay.config_path) if overlay is not None else None,
            "catalog_path": str(overlay.catalog_path) if overlay is not None else None,
            "effective_agent_def_dir": str(resolution.agent_def_dir),
            "effective_agent_def_dir_source": resolution.source,
            "project_mailbox_root": str(overlay.mailbox_root) if overlay is not None else None,
            "project_easy_root": str(overlay.easy_root) if overlay is not None else None,
        }
    )


@project_group.group(name="agents")
def agents_project_group() -> None:
    """Manage canonical project-local agent source content under `.houmao/agents/`."""


@agents_project_group.group(name="tools")
def project_tools_group() -> None:
    """Manage project-local tool content under `.houmao/agents/tools/`."""


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


@claude_tool_group.group(name="auth")
def claude_auth_group() -> None:
    """Manage Claude auth bundles under `.houmao/agents/tools/claude/auth/`."""


@claude_auth_group.command(name="list")
def list_claude_project_auth_command() -> None:
    """List project-local Claude auth bundles."""

    _emit_tool_auth_list(tool="claude")


@claude_auth_group.command(name="get")
@click.option("--name", required=True, help="Auth bundle name.")
def get_claude_project_auth_command(name: str) -> None:
    """Inspect one project-local Claude auth bundle."""

    _emit_tool_auth_get(tool="claude", name=name)


@claude_auth_group.command(name="remove")
@click.option("--name", required=True, help="Auth bundle name to remove.")
def remove_claude_project_auth_command(name: str) -> None:
    """Remove one project-local Claude auth bundle."""

    _emit_tool_auth_remove(tool="claude", name=name)


@claude_auth_group.command(name="add")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `ANTHROPIC_API_KEY`.")
@click.option("--auth-token", default=None, help="Value for `ANTHROPIC_AUTH_TOKEN`.")
@click.option("--base-url", default=None, help="Value for `ANTHROPIC_BASE_URL`.")
@click.option("--model", default=None, help="Value for `ANTHROPIC_MODEL`.")
@click.option("--small-fast-model", default=None, help="Value for `ANTHROPIC_SMALL_FAST_MODEL`.")
@click.option("--subagent-model", default=None, help="Value for `CLAUDE_CODE_SUBAGENT_MODEL`.")
@click.option(
    "--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`."
)
@click.option(
    "--default-sonnet-model",
    default=None,
    help="Value for `ANTHROPIC_DEFAULT_SONNET_MODEL`.",
)
@click.option(
    "--default-haiku-model",
    default=None,
    help="Value for `ANTHROPIC_DEFAULT_HAIKU_MODEL`.",
)
@click.option(
    "--state-template-file",
    "state_template_file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Claude runtime state template JSON to store in the auth bundle.",
)
def add_claude_project_auth_command(
    name: str,
    api_key: str | None,
    auth_token: str | None,
    base_url: str | None,
    model: str | None,
    small_fast_model: str | None,
    subagent_model: str | None,
    default_opus_model: str | None,
    default_sonnet_model: str | None,
    default_haiku_model: str | None,
    state_template_file: Path | None,
) -> None:
    """Create one new Claude auth bundle inside the discovered project overlay."""

    _run_claude_auth_write(
        operation="add",
        name=name,
        api_key=api_key,
        auth_token=auth_token,
        base_url=base_url,
        model=model,
        small_fast_model=small_fast_model,
        subagent_model=subagent_model,
        default_opus_model=default_opus_model,
        default_sonnet_model=default_sonnet_model,
        default_haiku_model=default_haiku_model,
        state_template_file=state_template_file,
        clear_env_names=set(),
        clear_file_sources=set(),
    )


@claude_auth_group.command(name="set")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `ANTHROPIC_API_KEY`.")
@click.option("--auth-token", default=None, help="Value for `ANTHROPIC_AUTH_TOKEN`.")
@click.option("--base-url", default=None, help="Value for `ANTHROPIC_BASE_URL`.")
@click.option("--model", default=None, help="Value for `ANTHROPIC_MODEL`.")
@click.option("--small-fast-model", default=None, help="Value for `ANTHROPIC_SMALL_FAST_MODEL`.")
@click.option("--subagent-model", default=None, help="Value for `CLAUDE_CODE_SUBAGENT_MODEL`.")
@click.option(
    "--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`."
)
@click.option(
    "--default-sonnet-model",
    default=None,
    help="Value for `ANTHROPIC_DEFAULT_SONNET_MODEL`.",
)
@click.option(
    "--default-haiku-model",
    default=None,
    help="Value for `ANTHROPIC_DEFAULT_HAIKU_MODEL`.",
)
@click.option(
    "--state-template-file",
    "state_template_file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Claude runtime state template JSON to store in the auth bundle.",
)
@click.option(
    "--clear-api-key", is_flag=True, help="Remove `ANTHROPIC_API_KEY` from the auth bundle."
)
@click.option(
    "--clear-auth-token", is_flag=True, help="Remove `ANTHROPIC_AUTH_TOKEN` from the auth bundle."
)
@click.option(
    "--clear-base-url", is_flag=True, help="Remove `ANTHROPIC_BASE_URL` from the auth bundle."
)
@click.option("--clear-model", is_flag=True, help="Remove `ANTHROPIC_MODEL` from the auth bundle.")
@click.option(
    "--clear-small-fast-model",
    is_flag=True,
    help="Remove `ANTHROPIC_SMALL_FAST_MODEL` from the auth bundle.",
)
@click.option(
    "--clear-subagent-model",
    is_flag=True,
    help="Remove `CLAUDE_CODE_SUBAGENT_MODEL` from the auth bundle.",
)
@click.option(
    "--clear-default-opus-model",
    is_flag=True,
    help="Remove `ANTHROPIC_DEFAULT_OPUS_MODEL` from the auth bundle.",
)
@click.option(
    "--clear-default-sonnet-model",
    is_flag=True,
    help="Remove `ANTHROPIC_DEFAULT_SONNET_MODEL` from the auth bundle.",
)
@click.option(
    "--clear-default-haiku-model",
    is_flag=True,
    help="Remove `ANTHROPIC_DEFAULT_HAIKU_MODEL` from the auth bundle.",
)
@click.option(
    "--clear-state-template-file",
    is_flag=True,
    help="Remove `files/claude_state.template.json` from the auth bundle.",
)
def set_claude_project_auth_command(
    name: str,
    api_key: str | None,
    auth_token: str | None,
    base_url: str | None,
    model: str | None,
    small_fast_model: str | None,
    subagent_model: str | None,
    default_opus_model: str | None,
    default_sonnet_model: str | None,
    default_haiku_model: str | None,
    state_template_file: Path | None,
    clear_api_key: bool,
    clear_auth_token: bool,
    clear_base_url: bool,
    clear_model: bool,
    clear_small_fast_model: bool,
    clear_subagent_model: bool,
    clear_default_opus_model: bool,
    clear_default_sonnet_model: bool,
    clear_default_haiku_model: bool,
    clear_state_template_file: bool,
) -> None:
    """Update one existing Claude auth bundle inside the discovered project overlay."""

    _run_claude_auth_write(
        operation="set",
        name=name,
        api_key=api_key,
        auth_token=auth_token,
        base_url=base_url,
        model=model,
        small_fast_model=small_fast_model,
        subagent_model=subagent_model,
        default_opus_model=default_opus_model,
        default_sonnet_model=default_sonnet_model,
        default_haiku_model=default_haiku_model,
        state_template_file=state_template_file,
        clear_env_names=_flagged_items(
            {
                "ANTHROPIC_API_KEY": clear_api_key,
                "ANTHROPIC_AUTH_TOKEN": clear_auth_token,
                "ANTHROPIC_BASE_URL": clear_base_url,
                "ANTHROPIC_MODEL": clear_model,
                "ANTHROPIC_SMALL_FAST_MODEL": clear_small_fast_model,
                "CLAUDE_CODE_SUBAGENT_MODEL": clear_subagent_model,
                "ANTHROPIC_DEFAULT_OPUS_MODEL": clear_default_opus_model,
                "ANTHROPIC_DEFAULT_SONNET_MODEL": clear_default_sonnet_model,
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": clear_default_haiku_model,
            }
        ),
        clear_file_sources=_flagged_items(
            {"claude_state.template.json": clear_state_template_file}
        ),
    )


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


@codex_tool_group.group(name="auth")
def codex_auth_group() -> None:
    """Manage Codex auth bundles under `.houmao/agents/tools/codex/auth/`."""


@codex_auth_group.command(name="list")
def list_codex_project_auth_command() -> None:
    """List project-local Codex auth bundles."""

    _emit_tool_auth_list(tool="codex")


@codex_auth_group.command(name="get")
@click.option("--name", required=True, help="Auth bundle name.")
def get_codex_project_auth_command(name: str) -> None:
    """Inspect one project-local Codex auth bundle."""

    _emit_tool_auth_get(tool="codex", name=name)


@codex_auth_group.command(name="remove")
@click.option("--name", required=True, help="Auth bundle name to remove.")
def remove_codex_project_auth_command(name: str) -> None:
    """Remove one project-local Codex auth bundle."""

    _emit_tool_auth_remove(tool="codex", name=name)


@codex_auth_group.command(name="add")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `OPENAI_API_KEY`.")
@click.option("--base-url", default=None, help="Value for `OPENAI_BASE_URL`.")
@click.option("--org-id", default=None, help="Value for `OPENAI_ORG_ID`.")
@click.option(
    "--auth-json",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Codex `auth.json` login-state file to store in the auth bundle.",
)
def add_codex_project_auth_command(
    name: str,
    api_key: str | None,
    base_url: str | None,
    org_id: str | None,
    auth_json: Path | None,
) -> None:
    """Create one new Codex auth bundle inside the discovered project overlay."""

    _run_codex_auth_write(
        operation="add",
        name=name,
        api_key=api_key,
        base_url=base_url,
        org_id=org_id,
        auth_json=auth_json,
        clear_env_names=set(),
        clear_file_sources=set(),
    )


@codex_auth_group.command(name="set")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `OPENAI_API_KEY`.")
@click.option("--base-url", default=None, help="Value for `OPENAI_BASE_URL`.")
@click.option("--org-id", default=None, help="Value for `OPENAI_ORG_ID`.")
@click.option(
    "--auth-json",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Codex `auth.json` login-state file to store in the auth bundle.",
)
@click.option("--clear-api-key", is_flag=True, help="Remove `OPENAI_API_KEY` from the auth bundle.")
@click.option(
    "--clear-base-url", is_flag=True, help="Remove `OPENAI_BASE_URL` from the auth bundle."
)
@click.option("--clear-org-id", is_flag=True, help="Remove `OPENAI_ORG_ID` from the auth bundle.")
@click.option(
    "--clear-auth-json", is_flag=True, help="Remove `files/auth.json` from the auth bundle."
)
def set_codex_project_auth_command(
    name: str,
    api_key: str | None,
    base_url: str | None,
    org_id: str | None,
    auth_json: Path | None,
    clear_api_key: bool,
    clear_base_url: bool,
    clear_org_id: bool,
    clear_auth_json: bool,
) -> None:
    """Update one existing Codex auth bundle inside the discovered project overlay."""

    _run_codex_auth_write(
        operation="set",
        name=name,
        api_key=api_key,
        base_url=base_url,
        org_id=org_id,
        auth_json=auth_json,
        clear_env_names=_flagged_items(
            {
                "OPENAI_API_KEY": clear_api_key,
                "OPENAI_BASE_URL": clear_base_url,
                "OPENAI_ORG_ID": clear_org_id,
            }
        ),
        clear_file_sources=_flagged_items({"auth.json": clear_auth_json}),
    )


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


@gemini_tool_group.group(name="auth")
def gemini_auth_group() -> None:
    """Manage Gemini auth bundles under `.houmao/agents/tools/gemini/auth/`."""


@gemini_auth_group.command(name="list")
def list_gemini_project_auth_command() -> None:
    """List project-local Gemini auth bundles."""

    _emit_tool_auth_list(tool="gemini")


@gemini_auth_group.command(name="get")
@click.option("--name", required=True, help="Auth bundle name.")
def get_gemini_project_auth_command(name: str) -> None:
    """Inspect one project-local Gemini auth bundle."""

    _emit_tool_auth_get(tool="gemini", name=name)


@gemini_auth_group.command(name="remove")
@click.option("--name", required=True, help="Auth bundle name to remove.")
def remove_gemini_project_auth_command(name: str) -> None:
    """Remove one project-local Gemini auth bundle."""

    _emit_tool_auth_remove(tool="gemini", name=name)


@gemini_auth_group.command(name="add")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `GEMINI_API_KEY`.")
@click.option("--google-api-key", default=None, help="Value for `GOOGLE_API_KEY`.")
@click.option(
    "--use-vertex-ai",
    is_flag=True,
    help="Store `GOOGLE_GENAI_USE_VERTEXAI=true` in the auth bundle env file.",
)
@click.option(
    "--oauth-creds",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    required=True,
    help="Path to the Gemini CLI `oauth_creds.json` file required by the current adapter.",
)
def add_gemini_project_auth_command(
    name: str,
    api_key: str | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    oauth_creds: Path,
) -> None:
    """Create one new Gemini auth bundle inside the discovered project overlay."""

    _run_gemini_auth_write(
        operation="add",
        name=name,
        api_key=api_key,
        google_api_key=google_api_key,
        use_vertex_ai=use_vertex_ai,
        oauth_creds=oauth_creds,
        clear_env_names=set(),
    )


@gemini_auth_group.command(name="set")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `GEMINI_API_KEY`.")
@click.option("--google-api-key", default=None, help="Value for `GOOGLE_API_KEY`.")
@click.option(
    "--use-vertex-ai",
    is_flag=True,
    help="Store `GOOGLE_GENAI_USE_VERTEXAI=true` in the auth bundle env file.",
)
@click.option(
    "--oauth-creds",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to the Gemini CLI `oauth_creds.json` file required by the current adapter.",
)
@click.option("--clear-api-key", is_flag=True, help="Remove `GEMINI_API_KEY` from the auth bundle.")
@click.option(
    "--clear-google-api-key", is_flag=True, help="Remove `GOOGLE_API_KEY` from the auth bundle."
)
@click.option(
    "--clear-use-vertex-ai",
    is_flag=True,
    help="Remove `GOOGLE_GENAI_USE_VERTEXAI` from the auth bundle.",
)
def set_gemini_project_auth_command(
    name: str,
    api_key: str | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    oauth_creds: Path | None,
    clear_api_key: bool,
    clear_google_api_key: bool,
    clear_use_vertex_ai: bool,
) -> None:
    """Update one existing Gemini auth bundle inside the discovered project overlay."""

    _run_gemini_auth_write(
        operation="set",
        name=name,
        api_key=api_key,
        google_api_key=google_api_key,
        use_vertex_ai=use_vertex_ai,
        oauth_creds=oauth_creds,
        clear_env_names=_flagged_items(
            {
                "GEMINI_API_KEY": clear_api_key,
                "GOOGLE_API_KEY": clear_google_api_key,
                "GOOGLE_GENAI_USE_VERTEXAI": clear_use_vertex_ai,
            }
        ),
    )


@agents_project_group.group(name="roles")
def project_roles_group() -> None:
    """Manage project-local roles stored under `.houmao/agents/roles/`."""


@project_roles_group.command(name="list")
def list_project_roles_command() -> None:
    """List project-local role roots."""

    overlay = _require_project_overlay()
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "roles": [
                _role_summary(overlay=overlay, role_name=role_name)
                for role_name in _list_role_names(overlay=overlay)
            ],
        }
    )


@project_roles_group.command(name="get")
@click.option("--name", required=True, help="Role name.")
def get_project_role_command(name: str) -> None:
    """Inspect one project-local role."""

    overlay = _require_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")
    emit_json(_role_summary(overlay=overlay, role_name=role_name))


@project_roles_group.command(name="init")
@click.option("--name", required=True, help="Role name.")
@click.option(
    "--tool",
    "tool_name",
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    default=None,
    help="Optional tool lane for an initial preset.",
)
@click.option("--setup", default="default", show_default=True, help="Preset setup name.")
@click.option("--auth", default=None, help="Optional preset auth bundle name.")
@click.option(
    "--skill", "skill_names", multiple=True, help="Repeatable skill name for the initial preset."
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional launch.prompt_mode for the initial preset; defaults to `unattended`.",
)
def init_project_role_command(
    name: str,
    tool_name: str | None,
    setup: str,
    auth: str | None,
    skill_names: tuple[str, ...],
    prompt_mode: str | None,
) -> None:
    """Create one new project-local role root and optional initial preset."""

    overlay = _require_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if role_root.exists():
        raise click.ClickException(f"Role already exists: {role_root}")

    prompt_path = _write_role_prompt(
        role_root=role_root, prompt_text=_default_role_prompt(role_name)
    )
    created_paths: list[str] = [str(role_root), str(prompt_path)]
    preset_path: str | None = None
    if tool_name is not None:
        written_preset_path = _write_role_preset(
            overlay=overlay,
            role_name=role_name,
            tool=tool_name,
            setup=setup,
            skills=[_require_non_empty_name(value, field_name="--skill") for value in skill_names],
            auth=_optional_non_empty_value(auth),
            prompt_mode=_optional_non_empty_value(prompt_mode),
        )
        created_paths.append(str(written_preset_path))
        preset_path = str(written_preset_path)
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "role_path": str(role_root),
            "system_prompt_path": str(prompt_path),
            "preset_path": preset_path,
            "created_paths": created_paths,
        }
    )


@project_roles_group.command(name="scaffold")
@click.option("--name", required=True, help="Role name.")
@click.option(
    "--tool",
    "tool_names",
    multiple=True,
    required=True,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Repeatable tool lane to scaffold.",
)
@click.option(
    "--auth",
    default="default",
    show_default=True,
    help="Auth bundle name to reference in generated presets.",
)
@click.option(
    "--setup",
    default="default",
    show_default=True,
    help="Setup name to reference in generated presets.",
)
@click.option(
    "--skill", "skill_names", multiple=True, help="Repeatable skill name to scaffold or reference."
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional launch.prompt_mode for generated presets; defaults to `unattended`.",
)
def scaffold_project_role_command(
    name: str,
    tool_names: tuple[str, ...],
    auth: str,
    setup: str,
    skill_names: tuple[str, ...],
    prompt_mode: str | None,
) -> None:
    """Create one structurally complete starter slice for a project-local role."""

    overlay = _require_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if role_root.exists():
        raise click.ClickException(f"Role already exists: {role_root}")

    normalized_skills = [
        _require_non_empty_name(value, field_name="--skill") for value in skill_names
    ]
    normalized_setup = _require_non_empty_name(setup, field_name="--setup")
    normalized_auth = _require_non_empty_name(auth, field_name="--auth")

    prompt_path = _write_role_prompt(
        role_root=role_root, prompt_text=_default_role_prompt(role_name)
    )
    created_paths: list[str] = [str(role_root), str(prompt_path)]
    for skill_name in normalized_skills:
        created_skill_path = _ensure_skill_placeholder(overlay=overlay, skill_name=skill_name)
        if created_skill_path is not None:
            created_paths.append(str(created_skill_path))

    for tool_name in tool_names:
        if normalized_setup != "default":
            created_setup_path = _clone_tool_setup_if_missing(
                overlay=overlay,
                tool=tool_name,
                target_name=normalized_setup,
                source_name="default",
            )
            if created_setup_path is not None:
                created_paths.append(str(created_setup_path))
        created_auth_paths = _ensure_placeholder_auth_bundle(
            overlay=overlay,
            tool=tool_name,
            name=normalized_auth,
        )
        created_paths.extend(str(path) for path in created_auth_paths)
        preset_path = _write_role_preset(
            overlay=overlay,
            role_name=role_name,
            tool=tool_name,
            setup=normalized_setup,
            skills=normalized_skills,
            auth=normalized_auth,
            prompt_mode=_optional_non_empty_value(prompt_mode),
        )
        created_paths.append(str(preset_path))

    emit_json(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "role_path": str(role_root),
            "created_paths": created_paths,
        }
    )


@project_roles_group.command(name="remove")
@click.option("--name", required=True, help="Role name to remove.")
def remove_project_role_command(name: str) -> None:
    """Remove one project-local role subtree."""

    overlay = _require_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")
    shutil.rmtree(role_root)
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "removed": True,
            "path": str(role_root),
        }
    )


@project_roles_group.group(name="presets")
def project_role_presets_group() -> None:
    """Manage role presets under `.houmao/agents/roles/<role>/presets/<tool>/<setup>.yaml`."""


@project_role_presets_group.command(name="list")
@click.option("--role", required=True, help="Role name.")
def list_project_role_presets_command(role: str) -> None:
    """List preset files for one project-local role."""

    overlay = _require_project_overlay()
    role_name = _require_non_empty_name(role, field_name="--role")
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "presets": _list_role_presets(overlay=overlay, role_name=role_name),
        }
    )


@project_role_presets_group.command(name="get")
@click.option("--role", required=True, help="Role name.")
@click.option(
    "--tool",
    "tool_name",
    required=True,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Tool lane.",
)
@click.option("--setup", default="default", show_default=True, help="Preset setup name.")
def get_project_role_preset_command(role: str, tool_name: str, setup: str) -> None:
    """Inspect one project-local role preset."""

    overlay = _require_project_overlay()
    emit_json(
        _preset_summary(
            overlay=overlay,
            role_name=_require_non_empty_name(role, field_name="--role"),
            tool=tool_name,
            setup=_require_non_empty_name(setup, field_name="--setup"),
        )
    )


@project_role_presets_group.command(name="add")
@click.option("--role", required=True, help="Role name.")
@click.option(
    "--tool",
    "tool_name",
    required=True,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Tool lane.",
)
@click.option("--setup", default="default", show_default=True, help="Preset setup name.")
@click.option("--skill", "skill_names", multiple=True, help="Repeatable skill name.")
@click.option("--auth", default=None, help="Optional auth bundle name.")
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional launch.prompt_mode value; defaults to `unattended`.",
)
def add_project_role_preset_command(
    role: str,
    tool_name: str,
    setup: str,
    skill_names: tuple[str, ...],
    auth: str | None,
    prompt_mode: str | None,
) -> None:
    """Create one minimal project-local role preset."""

    overlay = _require_project_overlay()
    role_name = _require_non_empty_name(role, field_name="--role")
    preset_path = _write_role_preset(
        overlay=overlay,
        role_name=role_name,
        tool=tool_name,
        setup=_require_non_empty_name(setup, field_name="--setup"),
        skills=[_require_non_empty_name(value, field_name="--skill") for value in skill_names],
        auth=_optional_non_empty_value(auth),
        prompt_mode=_optional_non_empty_value(prompt_mode),
    )
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "tool": tool_name,
            "setup": _require_non_empty_name(setup, field_name="--setup"),
            "path": str(preset_path),
            "created": True,
        }
    )


@project_role_presets_group.command(name="remove")
@click.option("--role", required=True, help="Role name.")
@click.option(
    "--tool",
    "tool_name",
    required=True,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Tool lane.",
)
@click.option("--setup", default="default", show_default=True, help="Preset setup name.")
def remove_project_role_preset_command(role: str, tool_name: str, setup: str) -> None:
    """Remove one project-local role preset."""

    overlay = _require_project_overlay()
    role_name = _require_non_empty_name(role, field_name="--role")
    resolved_setup = _require_non_empty_name(setup, field_name="--setup")
    preset_path = _preset_path(
        overlay=overlay, role_name=role_name, tool=tool_name, setup=resolved_setup
    )
    if not preset_path.is_file():
        raise click.ClickException(f"Preset not found: {preset_path}")
    preset_path.unlink()
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "tool": tool_name,
            "setup": resolved_setup,
            "removed": True,
            "path": str(preset_path),
        }
    )


@project_group.group(name="easy")
def easy_project_group() -> None:
    """Use a higher-level specialist and instance view over the project overlay."""


@easy_project_group.group(name="specialist")
def easy_specialist_group() -> None:
    """Manage high-level specialist definitions compiled into `.houmao/agents/`."""


@easy_specialist_group.command(name="create")
@click.option("--name", required=True, help="Specialist name.")
@click.option("--system-prompt", default=None, help="Inline system prompt content.")
@click.option(
    "--system-prompt-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a Markdown system prompt file.",
)
@click.option(
    "--tool",
    "tool_name",
    required=True,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Tool lane for the specialist.",
)
@click.option("--credential", default=None, help="Credential bundle name.")
@click.option("--api-key", default=None, help="Common API key input for the selected tool.")
@click.option(
    "--base-url", default=None, help="Common base URL input for the selected tool when supported."
)
@click.option("--claude-auth-token", default=None, help="Optional Claude auth token input.")
@click.option("--claude-model", default=None, help="Optional Claude model input.")
@click.option(
    "--claude-state-template-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Claude state template JSON file.",
)
@click.option("--codex-org-id", default=None, help="Optional Codex org id input.")
@click.option(
    "--codex-auth-json",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Codex `auth.json` file.",
)
@click.option("--google-api-key", default=None, help="Optional Gemini Google API key input.")
@click.option("--use-vertex-ai", is_flag=True, help="Enable Gemini Vertex AI mode.")
@click.option(
    "--gemini-oauth-creds",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Gemini `oauth_creds.json` file.",
)
@click.option(
    "--with-skill",
    "skill_dirs",
    multiple=True,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Repeatable skill directory to import into `.houmao/agents/skills/`.",
)
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Repeatable persistent specialist env record (`NAME=value`).",
)
@click.option(
    "--no-unattended",
    is_flag=True,
    help="Persist `launch.prompt_mode: as_is` instead of the easy unattended default.",
)
@overwrite_confirm_option
def create_easy_specialist_command(
    name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    tool_name: str,
    credential: str | None,
    api_key: str | None,
    base_url: str | None,
    claude_auth_token: str | None,
    claude_model: str | None,
    claude_state_template_file: Path | None,
    codex_org_id: str | None,
    codex_auth_json: Path | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    gemini_oauth_creds: Path | None,
    skill_dirs: tuple[Path, ...],
    env_set: tuple[str, ...],
    no_unattended: bool,
    yes: bool,
) -> None:
    """Create one project-local specialist and compile it into the canonical tree."""

    overlay = _require_project_overlay()
    specialist_name = _require_non_empty_name(name, field_name="--name")
    credential_name = (
        _require_non_empty_name(credential, field_name="--credential")
        if credential is not None
        else f"{specialist_name}-creds"
    )
    replace_conflict = _validate_specialist_create_inputs(
        overlay=overlay,
        specialist_name=specialist_name,
        system_prompt=system_prompt,
        system_prompt_file=system_prompt_file,
    )
    if replace_conflict is not None:
        confirm_destructive_action(
            prompt=(
                f"Replace specialist `{specialist_name}` and regenerate its managed prompt/preset?"
            ),
            yes=yes,
            non_interactive_message=(
                f"Specialist `{specialist_name}` already exists ({replace_conflict}). "
                "Rerun with `--yes` to replace it non-interactively."
            ),
            cancelled_message="Specialist replacement cancelled.",
        )
    prompt_text = _resolve_system_prompt_text(
        system_prompt=system_prompt,
        system_prompt_file=system_prompt_file,
    )
    imported_skills = _import_skill_directories(
        overlay=overlay,
        skill_dirs=skill_dirs,
    )
    adapter = _load_overlay_tool_adapter(overlay=overlay, tool=tool_name)
    persistent_env_records = _parse_specialist_env_records_or_click(
        adapter=adapter,
        env_set=env_set,
    )
    auth_result = _ensure_specialist_auth_bundle(
        overlay=overlay,
        tool=tool_name,
        credential_name=credential_name,
        api_key=api_key,
        base_url=base_url,
        claude_auth_token=claude_auth_token,
        claude_model=claude_model,
        claude_state_template_file=claude_state_template_file,
        codex_org_id=codex_org_id,
        codex_auth_json=codex_auth_json,
        google_api_key=google_api_key,
        use_vertex_ai=use_vertex_ai,
        gemini_oauth_creds=gemini_oauth_creds,
    )
    prompt_mode = "as_is" if no_unattended or tool_name not in {"claude", "codex"} else "unattended"
    launch_mapping: dict[str, Any] = {"prompt_mode": prompt_mode}
    if persistent_env_records:
        launch_mapping["env_records"] = dict(persistent_env_records)

    role_root = _role_root(overlay=overlay, role_name=specialist_name)
    if replace_conflict is not None:
        _prepare_specialist_role_projection_for_replace(role_root=role_root)
    system_prompt_path = _write_role_prompt(
        role_root=role_root,
        prompt_text=prompt_text,
        overwrite=replace_conflict is not None,
    )
    preset_path = _write_role_preset(
        overlay=overlay,
        role_name=specialist_name,
        tool=tool_name,
        setup="default",
        skills=[skill_path.name for skill_path in imported_skills],
        auth=credential_name,
        prompt_mode=prompt_mode,
        env_records=persistent_env_records,
        overwrite=replace_conflict is not None,
    )
    metadata = ProjectCatalog.from_overlay(overlay).store_specialist_from_sources(
        name=specialist_name,
        tool=tool_name,
        provider=TOOL_PROVIDER_MAP[tool_name],
        credential_name=credential_name,
        role_name=specialist_name,
        setup_name="default",
        prompt_path=system_prompt_path,
        auth_path=_auth_bundle_root(overlay=overlay, tool=tool_name, name=credential_name),
        skill_paths=tuple(imported_skills),
        launch_mapping=launch_mapping,
        mailbox_mapping=None,
        extra_mapping=None,
    )
    metadata_path = metadata.metadata_path or overlay.catalog_path
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "specialist": specialist_name,
            "tool": tool_name,
            "provider": metadata.provider,
            "credential": credential_name,
            "metadata_path": str(metadata_path),
            "generated": {
                "role_prompt": str(system_prompt_path),
                "preset": str(preset_path),
                "auth": str(
                    _auth_bundle_root(overlay=overlay, tool=tool_name, name=credential_name)
                ),
                "skills": [str(path) for path in imported_skills],
            },
            "auth_result": auth_result,
        }
    )


@easy_specialist_group.command(name="list")
def list_easy_specialists_command() -> None:
    """List persisted project-local specialist definitions."""

    overlay = _require_project_overlay()
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "specialists": [
                _specialist_payload(overlay=overlay, metadata=metadata)
                for metadata in list_specialists(overlay=overlay)
            ],
        }
    )


@easy_specialist_group.command(name="get")
@click.option("--name", required=True, help="Specialist name.")
def get_easy_specialist_command(name: str) -> None:
    """Inspect one persisted specialist definition."""

    overlay = _require_project_overlay()
    specialist = _load_specialist_or_click(overlay=overlay, name=name)
    emit_json(_specialist_payload(overlay=overlay, metadata=specialist))


@easy_specialist_group.command(name="remove")
@click.option("--name", required=True, help="Specialist name.")
def remove_easy_specialist_command(name: str) -> None:
    """Remove one persisted specialist definition and its generated role subtree."""

    overlay = _require_project_overlay()
    specialist = _load_specialist_or_click(overlay=overlay, name=name)
    metadata_path = _remove_specialist_metadata_or_click(overlay=overlay, name=specialist.name)
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "specialist": specialist.name,
            "removed": True,
            "metadata_path": str(metadata_path),
            "role_path": str(_role_root(overlay=overlay, role_name=specialist.role_name)),
            "preserved_auth_path": str(specialist.resolved_auth_path(overlay)),
            "preserved_skill_paths": [
                str(path) for path in specialist.resolved_skill_paths(overlay)
            ],
        }
    )


@easy_project_group.group(name="instance")
def easy_instance_group() -> None:
    """View managed-agent runtime state through project-local specialist names."""


@easy_instance_group.command(name="launch")
@click.option("--specialist", required=True, help="Specialist name.")
@click.option("--name", required=True, help="Managed-agent instance name.")
@click.option("--auth", default=None, help="Optional auth override for the compiled preset.")
@click.option("--session-name", default=None, help="Optional tmux session name.")
@click.option("--headless", is_flag=True, help="Launch in detached mode.")
@click.option("--yolo", is_flag=True, help="Skip workspace trust confirmation.")
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Repeatable one-off launch env (`NAME=value` or `NAME`).",
)
@click.option(
    "--mail-transport",
    type=click.Choice(("filesystem", "email")),
    default=None,
    help="Optional easy-layer mailbox transport.",
)
@click.option(
    "--mail-root",
    type=click.Path(path_type=Path, exists=False, file_okay=False, dir_okay=True),
    default=None,
    help="Shared filesystem mailbox root when `--mail-transport filesystem` is used.",
)
@click.option(
    "--mail-account-dir",
    type=click.Path(path_type=Path, exists=False, file_okay=False, dir_okay=True),
    default=None,
    help="Optional private filesystem mailbox directory to symlink into the shared root.",
)
def launch_easy_instance_command(
    specialist: str,
    name: str,
    auth: str | None,
    session_name: str | None,
    headless: bool,
    yolo: bool,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_root: Path | None,
    mail_account_dir: Path | None,
) -> None:
    """Launch one managed-agent instance from a compiled specialist definition."""

    overlay = _require_project_overlay()
    specialist_metadata = _load_specialist_or_click(overlay=overlay, name=specialist)
    if specialist_metadata.tool == "gemini" and not headless:
        raise click.ClickException(
            "Gemini specialists are currently headless-only. Use `--headless`."
        )
    if mail_transport == "email":
        raise click.ClickException(
            "Mailbox transport `email` is not implemented yet for `project easy instance launch`."
        )
    if mail_transport is None and (mail_root is not None or mail_account_dir is not None):
        raise click.ClickException(
            "`--mail-root` and `--mail-account-dir` require `--mail-transport filesystem`."
        )
    if mail_transport == "filesystem" and mail_root is None:
        raise click.ClickException(
            "`project easy instance launch --mail-transport filesystem` requires `--mail-root`."
        )
    if mail_transport != "filesystem" and mail_account_dir is not None:
        raise click.ClickException(
            "`--mail-account-dir` is only supported with `--mail-transport filesystem`."
        )
    materialize_project_agent_catalog_projection(overlay)
    launch_env_overrides = _resolve_instance_env_set_or_click(env_set)

    controller = launch_managed_agent_locally(
        agents=specialist_metadata.role_name,
        agent_name=_require_non_empty_name(name, field_name="--name"),
        agent_id=None,
        auth=_optional_non_empty_value(auth),
        session_name=_optional_non_empty_value(session_name),
        headless=headless,
        provider=specialist_metadata.provider,
        yolo=yolo,
        working_directory=Path.cwd().resolve(),
        launch_env_overrides=launch_env_overrides,
        mailbox_transport=mail_transport,
        mailbox_root=mail_root.resolve() if mail_root is not None else None,
        mailbox_account_dir=(mail_account_dir.resolve() if mail_account_dir is not None else None),
    )
    emit_local_launch_completion(
        controller=controller,
        agent_name=name,
        session_name=session_name,
        headless=headless,
    )


@easy_instance_group.command(name="list")
def list_easy_instances_command() -> None:
    """List project-local managed agents as specialist instances when resolvable."""

    overlay = _require_project_overlay()
    specialists_by_name = {
        metadata.name: metadata for metadata in list_specialists(overlay=overlay)
    }
    instances = _list_project_instances(overlay=overlay, specialists_by_name=specialists_by_name)
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "instances": instances,
        }
    )


@easy_instance_group.command(name="get")
@click.option("--name", required=True, help="Managed-agent instance name.")
def get_easy_instance_command(name: str) -> None:
    """Inspect one managed-agent instance through the current project overlay."""

    overlay = _require_project_overlay()
    specialists_by_name = {
        metadata.name: metadata for metadata in list_specialists(overlay=overlay)
    }
    target = resolve_managed_agent_target(
        agent_id=None,
        agent_name=_require_non_empty_name(name, field_name="--name"),
        port=None,
    )
    identity = target.identity
    manifest_path = _require_manifest_path_for_identity(
        identity_payload=identity.model_dump(mode="json")
    )
    manifest_payload = _load_manifest_payload(manifest_path)
    if not _manifest_belongs_to_overlay(overlay=overlay, manifest_payload=manifest_payload):
        raise click.ClickException(
            f"Managed agent `{name}` does not belong to the discovered project overlay."
        )
    emit_json(
        _instance_payload(
            overlay=overlay,
            identity_payload=identity.model_dump(mode="json"),
            manifest_payload=manifest_payload,
            specialists_by_name=specialists_by_name,
        )
    )


@easy_instance_group.command(name="stop")
@click.option("--name", required=True, help="Managed-agent instance name.")
def stop_easy_instance_command(name: str) -> None:
    """Stop one managed-agent instance through the current project overlay."""

    overlay = _require_project_overlay()
    target = resolve_managed_agent_target(
        agent_id=None,
        agent_name=_require_non_empty_name(name, field_name="--name"),
        port=None,
    )
    identity = target.identity
    manifest_path = _require_manifest_path_for_identity(
        identity_payload=identity.model_dump(mode="json")
    )
    manifest_payload = _load_manifest_payload(manifest_path)
    if not _manifest_belongs_to_overlay(overlay=overlay, manifest_payload=manifest_payload):
        raise click.ClickException(
            f"Managed agent `{name}` does not belong to the discovered project overlay."
        )
    emit_json(stop_managed_agent(target))


@project_group.group(name="mailbox")
def project_mailbox_group() -> None:
    """Operate on the current project's `.houmao/mailbox` root."""


@project_mailbox_group.command(name="init")
def init_project_mailbox_command() -> None:
    """Bootstrap or validate the current project's mailbox root."""

    emit_json(init_mailbox_root(_project_mailbox_root()))


@project_mailbox_group.command(name="status")
def status_project_mailbox_command() -> None:
    """Inspect the current project's mailbox root."""

    emit_json(mailbox_root_status_payload(_project_mailbox_root()))


@project_mailbox_group.command(name="register")
@click.option("--address", required=True, help="Full mailbox address.")
@click.option("--principal-id", required=True, help="Mailbox owner principal id.")
@click.option(
    "--mode",
    type=click.Choice(("safe", "force", "stash")),
    default="safe",
    show_default=True,
    help="Filesystem mailbox registration mode.",
)
@overwrite_confirm_option
def register_project_mailbox_command(address: str, principal_id: str, mode: str, yes: bool) -> None:
    """Register one mailbox address under the current project's mailbox root."""

    emit_json(
        register_mailbox_at_root(
            mailbox_root=_project_mailbox_root(),
            address=address,
            principal_id=principal_id,
            mode=mode,
            confirm_destructive_replace=build_destructive_confirmation_callback(
                yes=yes,
                non_interactive_message=(
                    "Mailbox registration would replace existing durable mailbox state. "
                    "Rerun with `--yes` to confirm overwrite non-interactively or choose "
                    "a non-destructive registration mode."
                ),
            ),
        )
    )


@project_mailbox_group.command(name="unregister")
@click.option("--address", required=True, help="Full mailbox address.")
@click.option(
    "--mode",
    type=click.Choice(("deactivate", "purge")),
    default="deactivate",
    show_default=True,
    help="Filesystem mailbox deregistration mode.",
)
def unregister_project_mailbox_command(address: str, mode: str) -> None:
    """Deactivate or purge one mailbox address under the current project's mailbox root."""

    emit_json(
        unregister_mailbox_at_root(
            mailbox_root=_project_mailbox_root(),
            address=address,
            mode=mode,
        )
    )


@project_mailbox_group.command(name="repair")
@click.option(
    "--cleanup-staging/--no-cleanup-staging",
    default=True,
    show_default=True,
    help="Clean staging artifacts during repair.",
)
@click.option(
    "--quarantine-staging/--remove-staging",
    default=True,
    show_default=True,
    help="Quarantine staging artifacts instead of deleting them.",
)
def repair_project_mailbox_command(cleanup_staging: bool, quarantine_staging: bool) -> None:
    """Repair the current project's mailbox root."""

    emit_json(
        repair_mailbox_root(
            mailbox_root=_project_mailbox_root(),
            cleanup_staging=cleanup_staging,
            quarantine_staging=quarantine_staging,
        )
    )


@project_mailbox_group.command(name="cleanup")
@click.option(
    "--inactive-older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only clean inactive registrations older than this threshold.",
)
@click.option(
    "--stashed-older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only clean stashed registrations older than this threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview inactive or stashed mailbox cleanup candidates without deleting them.",
)
def cleanup_project_mailbox_command(
    inactive_older_than_seconds: int,
    stashed_older_than_seconds: int,
    dry_run: bool,
) -> None:
    """Clean inactive or stashed registrations under the current project's mailbox root."""

    emit_json(
        cleanup_mailbox_root(
            mailbox_root=_project_mailbox_root(),
            inactive_older_than_seconds=inactive_older_than_seconds,
            stashed_older_than_seconds=stashed_older_than_seconds,
            dry_run=dry_run,
        )
    )


@project_mailbox_group.group(name="accounts")
def project_mailbox_accounts_group() -> None:
    """Inspect mailbox registrations under the current project's mailbox root."""


@project_mailbox_accounts_group.command(name="list")
def list_project_mailbox_accounts_command() -> None:
    """List mailbox accounts under the current project's mailbox root."""

    emit_json(list_mailbox_accounts(mailbox_root=_project_mailbox_root()))


@project_mailbox_accounts_group.command(name="get")
@click.option("--address", required=True, help="Full mailbox address.")
def get_project_mailbox_account_command(address: str) -> None:
    """Inspect one mailbox account under the current project's mailbox root."""

    try:
        payload = get_mailbox_account(mailbox_root=_project_mailbox_root(), address=address)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit_json(payload)


@project_mailbox_group.group(name="messages")
def project_mailbox_messages_group() -> None:
    """Inspect mailbox-visible messages under the current project's mailbox root."""


@project_mailbox_messages_group.command(name="list")
@click.option("--address", required=True, help="Full mailbox address.")
def list_project_mailbox_messages_command(address: str) -> None:
    """List mailbox-visible messages for one project-local mailbox address."""

    try:
        payload = list_mailbox_messages(mailbox_root=_project_mailbox_root(), address=address)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit_json(payload)


@project_mailbox_messages_group.command(name="get")
@click.option("--address", required=True, help="Full mailbox address.")
@click.option("--message-id", required=True, help="Canonical mailbox message id.")
def get_project_mailbox_message_command(address: str, message_id: str) -> None:
    """Get one mailbox-visible message for a project-local mailbox address."""

    try:
        payload = get_mailbox_message(
            mailbox_root=_project_mailbox_root(),
            address=address,
            message_id=message_id,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit_json(payload)


def _require_project_overlay() -> HoumaoProjectOverlay:
    """Return the discovered project overlay or raise one operator-facing error."""

    try:
        return require_project_overlay(Path.cwd().resolve())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _project_mailbox_root() -> Path:
    """Return the current project's mailbox root."""

    return _require_project_overlay().mailbox_root


def _emit_tool_get(*, tool: str) -> None:
    """Emit one project-local tool summary."""

    overlay = _require_project_overlay()
    tool_root = _tool_root(overlay=overlay, tool=tool)
    adapter_path = (tool_root / "adapter.yaml").resolve()
    emit_json(
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

    overlay = _require_project_overlay()
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "setups": _list_tool_setup_names(overlay=overlay, tool=tool),
        }
    )


def _emit_tool_setup_get(*, tool: str, name: str) -> None:
    """Emit one project-local setup summary."""

    overlay = _require_project_overlay()
    setup_name = _require_non_empty_name(name, field_name="--name")
    setup_path = _tool_setup_path(overlay=overlay, tool=tool, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Setup bundle not found: {setup_path}")
    emit_json(
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

    overlay = _require_project_overlay()
    target_name = _require_non_empty_name(name, field_name="--name")
    resolved_source_name = _require_non_empty_name(source_name, field_name="--from")
    source_path = _tool_setup_path(overlay=overlay, tool=tool, name=resolved_source_name)
    target_path = _tool_setup_path(overlay=overlay, tool=tool, name=target_name)
    if not source_path.is_dir():
        raise click.ClickException(f"Source setup bundle not found: {source_path}")
    if target_path.exists():
        raise click.ClickException(f"Setup bundle already exists: {target_path}")
    shutil.copytree(source_path, target_path)
    emit_json(
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

    overlay = _require_project_overlay()
    setup_name = _require_non_empty_name(name, field_name="--name")
    setup_path = _tool_setup_path(overlay=overlay, tool=tool, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Setup bundle not found: {setup_path}")
    shutil.rmtree(setup_path)
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "name": setup_name,
            "removed": True,
            "path": str(setup_path),
        }
    )


def _emit_tool_auth_list(*, tool: str) -> None:
    """Emit the auth-bundle names for one supported tool."""

    overlay = _require_project_overlay()
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "credentials": _list_tool_bundle_names(overlay=overlay, tool=tool),
        }
    )


def _emit_tool_auth_get(*, tool: str, name: str) -> None:
    """Emit one structured auth-bundle description."""

    overlay = _require_project_overlay()
    emit_json(_describe_project_auth_bundle(overlay=overlay, tool=tool, name=name))


def _emit_tool_auth_remove(*, tool: str, name: str) -> None:
    """Remove one named auth bundle and emit the removal payload."""

    overlay = _require_project_overlay()
    resolved_name = _require_non_empty_name(name, field_name="--name")
    target_path = _auth_bundle_root(overlay=overlay, tool=tool, name=resolved_name)
    if not target_path.is_dir():
        raise click.ClickException(f"Auth bundle not found: {target_path}")
    shutil.rmtree(target_path)
    emit_json(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "name": resolved_name,
            "removed": True,
            "path": str(target_path),
        }
    )


def _list_tool_setup_names(*, overlay: HoumaoProjectOverlay, tool: str) -> list[str]:
    """Return the existing setup names for one tool."""

    setups_root = (_tool_root(overlay=overlay, tool=tool) / "setups").resolve()
    if not setups_root.is_dir():
        return []
    return sorted(path.name for path in setups_root.iterdir() if path.is_dir())


def _list_tool_bundle_names(*, overlay: HoumaoProjectOverlay, tool: str) -> list[str]:
    """Return the existing auth bundle names for one tool."""

    auth_root = (_tool_root(overlay=overlay, tool=tool) / "auth").resolve()
    if not auth_root.is_dir():
        return []
    return sorted(path.name for path in auth_root.iterdir() if path.is_dir())


def _tool_root(*, overlay: HoumaoProjectOverlay, tool: str) -> Path:
    """Return one project-local tool root."""

    ensure_project_agent_compatibility_tree(overlay)
    return (overlay.agents_root / "tools" / tool).resolve()


def _tool_setup_path(*, overlay: HoumaoProjectOverlay, tool: str, name: str) -> Path:
    """Return one project-local tool setup root."""

    return (_tool_root(overlay=overlay, tool=tool) / "setups" / name).resolve()


def _role_root(*, overlay: HoumaoProjectOverlay, role_name: str) -> Path:
    """Return one project-local role root."""

    ensure_project_agent_compatibility_tree(overlay)
    return (overlay.agents_root / "roles" / role_name).resolve()


def _preset_path(*, overlay: HoumaoProjectOverlay, role_name: str, tool: str, setup: str) -> Path:
    """Return one canonical project-local preset path."""

    return (
        _role_root(overlay=overlay, role_name=role_name) / "presets" / tool / f"{setup}.yaml"
    ).resolve()


def _list_role_names(*, overlay: HoumaoProjectOverlay) -> list[str]:
    """Return the current project-local role names."""

    ensure_project_agent_compatibility_tree(overlay)
    roles_root = (overlay.agents_root / "roles").resolve()
    if not roles_root.is_dir():
        return []
    return sorted(path.name for path in roles_root.iterdir() if path.is_dir())


def _role_summary(*, overlay: HoumaoProjectOverlay, role_name: str) -> dict[str, object]:
    """Return one structured project-local role summary."""

    role_root = _role_root(overlay=overlay, role_name=role_name)
    prompt_path = (role_root / "system-prompt.md").resolve()
    return {
        "name": role_name,
        "role_path": str(role_root),
        "system_prompt_path": str(prompt_path),
        "system_prompt_exists": prompt_path.is_file(),
        "presets": _list_role_presets(overlay=overlay, role_name=role_name),
    }


def _list_role_presets(*, overlay: HoumaoProjectOverlay, role_name: str) -> list[dict[str, object]]:
    """Return preset summaries for one role without requiring raw YAML inspection."""

    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        return []
    results: list[dict[str, object]] = []
    presets_root = (role_root / "presets").resolve()
    if not presets_root.is_dir():
        return results
    for tool_dir in sorted(path for path in presets_root.iterdir() if path.is_dir()):
        for preset_file in sorted(path for path in tool_dir.iterdir() if path.is_file()):
            if preset_file.suffix not in {".yaml", ".yml"}:
                continue
            results.append(
                _preset_summary(
                    overlay=overlay,
                    role_name=role_name,
                    tool=tool_dir.name,
                    setup=preset_file.stem,
                )
            )
    return results


def _preset_summary(
    *,
    overlay: HoumaoProjectOverlay,
    role_name: str,
    tool: str,
    setup: str,
) -> dict[str, object]:
    """Return one structured project-local preset summary."""

    preset_file = _preset_path(overlay=overlay, role_name=role_name, tool=tool, setup=setup)
    if not preset_file.is_file():
        raise click.ClickException(f"Preset not found: {preset_file}")
    parsed_preset = parse_agent_preset(preset_file)
    raw_payload = _load_yaml_mapping(preset_file)
    launch_payload = raw_payload.get("launch")
    return {
        "role": role_name,
        "tool": tool,
        "setup": setup,
        "path": str(preset_file),
        "skills": list(parsed_preset.skills),
        "auth": parsed_preset.auth,
        "launch": launch_payload if isinstance(launch_payload, dict) else {},
        "mailbox": raw_payload.get("mailbox"),
        "extra": raw_payload.get("extra", {}),
    }


def _write_role_prompt(*, role_root: Path, prompt_text: str, overwrite: bool = False) -> Path:
    """Write one canonical role prompt file."""

    role_root.mkdir(parents=True, exist_ok=overwrite)
    prompt_path = (role_root / "system-prompt.md").resolve()
    if prompt_path.exists() and prompt_path.is_dir():
        raise click.ClickException(f"Prompt path already exists as a directory: {prompt_path}")
    prompt_path.write_text(
        prompt_text.rstrip() + "\n" if prompt_text.strip() else "",
        encoding="utf-8",
    )
    return prompt_path


def _write_role_preset(
    *,
    overlay: HoumaoProjectOverlay,
    role_name: str,
    tool: str,
    setup: str,
    skills: list[str],
    auth: str | None,
    prompt_mode: str | None,
    env_records: dict[str, str] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write one canonical project-local role preset."""

    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")
    preset_file = _preset_path(overlay=overlay, role_name=role_name, tool=tool, setup=setup)
    if preset_file.exists() and not overwrite:
        raise click.ClickException(f"Preset already exists: {preset_file}")
    resolved_prompt_mode = prompt_mode or "unattended"
    payload: dict[str, Any] = {"skills": list(skills)}
    if auth is not None:
        payload["auth"] = auth
    payload["launch"] = {"prompt_mode": resolved_prompt_mode}
    if env_records:
        payload["launch"]["env_records"] = dict(env_records)
    preset_file.parent.mkdir(parents=True, exist_ok=True)
    preset_file.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return preset_file


def _prepare_specialist_role_projection_for_replace(*, role_root: Path) -> None:
    """Clear specialist-owned generated projection paths before one replacement write."""

    if not role_root.exists():
        return
    prompt_path = (role_root / "system-prompt.md").resolve()
    if prompt_path.is_dir():
        raise click.ClickException(f"Prompt path already exists as a directory: {prompt_path}")
    prompt_path.unlink(missing_ok=True)
    presets_root = (role_root / "presets").resolve()
    if presets_root.is_file():
        raise click.ClickException(f"Preset root already exists as a file: {presets_root}")
    if presets_root.is_dir():
        shutil.rmtree(presets_root)


def _ensure_skill_placeholder(*, overlay: HoumaoProjectOverlay, skill_name: str) -> Path | None:
    """Create one placeholder skill directory when it is currently missing."""

    ensure_project_agent_compatibility_tree(overlay)
    skill_root = (overlay.agents_root / "skills" / skill_name).resolve()
    skill_doc = (skill_root / "SKILL.md").resolve()
    if skill_doc.is_file():
        return None
    skill_root.mkdir(parents=True, exist_ok=True)
    skill_doc.write_text(
        f"# {skill_name}\n\nReplace this placeholder skill with real project-local instructions.\n",
        encoding="utf-8",
    )
    return skill_root


def _clone_tool_setup_if_missing(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    target_name: str,
    source_name: str,
) -> Path | None:
    """Clone one tool setup into a missing target path."""

    target_path = _tool_setup_path(overlay=overlay, tool=tool, name=target_name)
    if target_path.exists():
        return None
    source_path = _tool_setup_path(overlay=overlay, tool=tool, name=source_name)
    if not source_path.is_dir():
        raise click.ClickException(f"Source setup bundle not found: {source_path}")
    shutil.copytree(source_path, target_path)
    return target_path


def _ensure_placeholder_auth_bundle(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
) -> list[Path]:
    """Create one placeholder auth bundle when it is missing."""

    auth_root = _auth_bundle_root(overlay=overlay, tool=tool, name=name)
    if auth_root.is_dir():
        return []
    adapter = _load_overlay_tool_adapter(overlay=overlay, tool=tool)
    env_file_path = _auth_bundle_env_file(overlay=overlay, tool=tool, name=name)
    files_root = (auth_root / adapter.auth_files_dir).resolve()
    env_file_path.parent.mkdir(parents=True, exist_ok=True)
    files_root.mkdir(parents=True, exist_ok=True)
    env_file_path.write_text(
        "\n".join(
            ["# Fill in the required auth values for this bundle."]
            + [f"# {env_name}=" for env_name in adapter.auth_env_allowlist]
        )
        + "\n",
        encoding="utf-8",
    )
    created_paths: list[Path] = [auth_root, env_file_path]
    for mapping in adapter.auth_file_mappings:
        if not mapping.required:
            continue
        target_path = (files_root / mapping.source).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text("{}\n", encoding="utf-8")
        created_paths.append(target_path)
    return created_paths


def _run_claude_auth_write(
    *,
    operation: str,
    name: str,
    api_key: str | None,
    auth_token: str | None,
    base_url: str | None,
    model: str | None,
    small_fast_model: str | None,
    subagent_model: str | None,
    default_opus_model: str | None,
    default_sonnet_model: str | None,
    default_haiku_model: str | None,
    state_template_file: Path | None,
    clear_env_names: set[str],
    clear_file_sources: set[str],
) -> None:
    """Create or update one Claude auth bundle and emit its result payload."""

    overlay = _require_project_overlay()
    env_values = _compact_env_values(
        {
            "ANTHROPIC_API_KEY": api_key,
            "ANTHROPIC_AUTH_TOKEN": auth_token,
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_MODEL": model,
            "ANTHROPIC_SMALL_FAST_MODEL": small_fast_model,
            "CLAUDE_CODE_SUBAGENT_MODEL": subagent_model,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": default_opus_model,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": default_sonnet_model,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": default_haiku_model,
        }
    )
    emit_json(
        _write_project_auth_bundle(
            overlay=overlay,
            tool="claude",
            name=name,
            env_values=env_values,
            file_sources={"claude_state.template.json": state_template_file}
            if state_template_file is not None
            else {},
            require_any_input=True,
            operation=operation,
            clear_env_names=clear_env_names,
            clear_file_sources=clear_file_sources,
        )
    )


def _run_codex_auth_write(
    *,
    operation: str,
    name: str,
    api_key: str | None,
    base_url: str | None,
    org_id: str | None,
    auth_json: Path | None,
    clear_env_names: set[str],
    clear_file_sources: set[str],
) -> None:
    """Create or update one Codex auth bundle and emit its result payload."""

    overlay = _require_project_overlay()
    env_values = _compact_env_values(
        {
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "OPENAI_ORG_ID": org_id,
        }
    )
    emit_json(
        _write_project_auth_bundle(
            overlay=overlay,
            tool="codex",
            name=name,
            env_values=env_values,
            file_sources={"auth.json": auth_json} if auth_json is not None else {},
            require_any_input=True,
            operation=operation,
            clear_env_names=clear_env_names,
            clear_file_sources=clear_file_sources,
        )
    )


def _run_gemini_auth_write(
    *,
    operation: str,
    name: str,
    api_key: str | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    oauth_creds: Path | None,
    clear_env_names: set[str],
) -> None:
    """Create or update one Gemini auth bundle and emit its result payload."""

    overlay = _require_project_overlay()
    env_values = _compact_env_values(
        {
            "GEMINI_API_KEY": api_key,
            "GOOGLE_API_KEY": google_api_key,
            "GOOGLE_GENAI_USE_VERTEXAI": "true" if use_vertex_ai else None,
        }
    )
    emit_json(
        _write_project_auth_bundle(
            overlay=overlay,
            tool="gemini",
            name=name,
            env_values=env_values,
            file_sources={"oauth_creds.json": oauth_creds} if oauth_creds is not None else {},
            require_any_input=False,
            operation=operation,
            clear_env_names=clear_env_names,
            clear_file_sources=set(),
        )
    )


def _write_project_auth_bundle(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
    env_values: dict[str, str],
    file_sources: dict[str, Path],
    require_any_input: bool,
    operation: str,
    clear_env_names: set[str],
    clear_file_sources: set[str],
) -> dict[str, object]:
    """Create or update one tool-local auth bundle inside the project overlay."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    adapter = _load_overlay_tool_adapter(overlay=overlay, tool=tool)
    if operation not in {"add", "set"}:
        raise click.ClickException(f"Unsupported auth-bundle operation: {operation}")

    if (
        require_any_input
        and not env_values
        and not file_sources
        and not clear_env_names
        and not clear_file_sources
    ):
        raise click.ClickException(
            f"Provide at least one auth input for `{tool}` (env value or compatible auth file)."
        )
    if (
        operation == "set"
        and not env_values
        and not file_sources
        and not clear_env_names
        and not clear_file_sources
    ):
        raise click.ClickException(
            f"Provide at least one change for `{tool}` (new value, compatible auth file, or clear flag)."
        )

    auth_bundle_root = _auth_bundle_root(overlay=overlay, tool=tool, name=resolved_name)
    bundle_exists = auth_bundle_root.is_dir()
    if operation == "add" and bundle_exists:
        raise click.ClickException(f"Auth bundle already exists: {auth_bundle_root}")
    if operation == "set" and not bundle_exists:
        raise click.ClickException(f"Auth bundle not found: {auth_bundle_root}")

    unsupported_env_keys = sorted(
        (set(env_values) | clear_env_names) - set(adapter.auth_env_allowlist)
    )
    if unsupported_env_keys:
        raise click.ClickException(
            f"Unsupported env var(s) for `{tool}` auth bundles: {', '.join(unsupported_env_keys)}"
        )

    known_file_sources = {mapping.source: mapping for mapping in adapter.auth_file_mappings}
    unsupported_file_sources = sorted(
        (set(file_sources) | clear_file_sources) - set(known_file_sources)
    )
    if unsupported_file_sources:
        raise click.ClickException(
            f"Unsupported auth file(s) for `{tool}` auth bundles: {', '.join(unsupported_file_sources)}"
        )

    existing_env_values = _load_existing_env_values(
        _auth_bundle_env_file(overlay=overlay, tool=tool, name=resolved_name)
    )
    merged_env_values = dict(existing_env_values)
    merged_env_values.update(env_values)
    for env_name in clear_env_names:
        merged_env_values.pop(env_name, None)

    env_file_path = _auth_bundle_env_file(overlay=overlay, tool=tool, name=resolved_name)
    files_root = (auth_bundle_root / adapter.auth_files_dir).resolve()
    env_file_path.parent.mkdir(parents=True, exist_ok=True)
    files_root.mkdir(parents=True, exist_ok=True)

    for source_name in clear_file_sources:
        target_path = (files_root / source_name).resolve()
        if target_path.is_dir():
            shutil.rmtree(target_path)
        elif target_path.exists():
            target_path.unlink()

    for source_name, source_path in file_sources.items():
        destination_path = (files_root / source_name).resolve()
        shutil.copy2(source_path.resolve(), destination_path)

    for mapping in adapter.auth_file_mappings:
        if mapping.required and not (files_root / mapping.source).exists():
            raise click.ClickException(
                f"Missing required auth file `{mapping.source}` for `{tool}` bundle `{resolved_name}`."
            )

    env_file_path.write_text(
        _render_env_file(env_values=merged_env_values, allowlist=adapter.auth_env_allowlist),
        encoding="utf-8",
    )
    return {
        "operation": operation,
        "project_root": str(overlay.project_root),
        "tool": tool,
        "name": resolved_name,
        "path": str(auth_bundle_root),
        "env_file": str(env_file_path),
        "written_env_vars": [
            env_name for env_name in adapter.auth_env_allowlist if env_name in merged_env_values
        ],
        "cleared_env_vars": sorted(clear_env_names),
        "written_files": [
            str((files_root / source_name).resolve()) for source_name in sorted(file_sources)
        ],
        "cleared_files": sorted(clear_file_sources),
    }


def _describe_project_auth_bundle(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
) -> dict[str, object]:
    """Return one structured auth-bundle description with redacted secret values."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    adapter = _load_overlay_tool_adapter(overlay=overlay, tool=tool)
    auth_bundle_root = _auth_bundle_root(overlay=overlay, tool=tool, name=resolved_name)
    if not auth_bundle_root.is_dir():
        raise click.ClickException(f"Auth bundle not found: {auth_bundle_root}")

    env_file_path = _auth_bundle_env_file(overlay=overlay, tool=tool, name=resolved_name)
    env_values = _load_existing_env_values(env_file_path)
    files_root = (auth_bundle_root / adapter.auth_files_dir).resolve()

    return {
        "project_root": str(overlay.project_root),
        "tool": tool,
        "name": resolved_name,
        "path": str(auth_bundle_root),
        "env_file": str(env_file_path),
        "env": {
            env_name: _describe_env_value(env_name=env_name, env_values=env_values)
            for env_name in adapter.auth_env_allowlist
        },
        "files": {
            mapping.source: _describe_file_mapping(files_root=files_root, mapping=mapping)
            for mapping in adapter.auth_file_mappings
        },
    }


def _ensure_specialist_auth_bundle(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    credential_name: str,
    api_key: str | None,
    base_url: str | None,
    claude_auth_token: str | None,
    claude_model: str | None,
    claude_state_template_file: Path | None,
    codex_org_id: str | None,
    codex_auth_json: Path | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    gemini_oauth_creds: Path | None,
) -> dict[str, object]:
    """Create, update, or reuse one auth bundle for specialist compilation."""

    auth_root = _auth_bundle_root(overlay=overlay, tool=tool, name=credential_name)
    if tool == "claude":
        env_values = _compact_env_values(
            {
                "ANTHROPIC_API_KEY": api_key,
                "ANTHROPIC_AUTH_TOKEN": claude_auth_token,
                "ANTHROPIC_BASE_URL": base_url,
                "ANTHROPIC_MODEL": claude_model,
            }
        )
        file_sources = (
            {"claude_state.template.json": claude_state_template_file}
            if claude_state_template_file is not None
            else {}
        )
    elif tool == "codex":
        env_values = _compact_env_values(
            {
                "OPENAI_API_KEY": api_key,
                "OPENAI_BASE_URL": base_url,
                "OPENAI_ORG_ID": codex_org_id,
            }
        )
        file_sources = {"auth.json": codex_auth_json} if codex_auth_json is not None else {}
    elif tool == "gemini":
        if base_url is not None and base_url.strip():
            raise click.ClickException("Gemini auth bundles do not currently support `--base-url`.")
        env_values = _compact_env_values(
            {
                "GEMINI_API_KEY": api_key,
                "GOOGLE_API_KEY": google_api_key,
                "GOOGLE_GENAI_USE_VERTEXAI": "true" if use_vertex_ai else None,
            }
        )
        file_sources = (
            {"oauth_creds.json": gemini_oauth_creds} if gemini_oauth_creds is not None else {}
        )
    else:
        raise click.ClickException(f"Unsupported specialist tool `{tool}`.")

    if auth_root.is_dir():
        if not env_values and not file_sources:
            return {
                "operation": "reuse",
                "tool": tool,
                "name": credential_name,
                "path": str(auth_root),
            }
        return _write_project_auth_bundle(
            overlay=overlay,
            tool=tool,
            name=credential_name,
            env_values=env_values,
            file_sources=file_sources,
            require_any_input=False,
            operation="set",
            clear_env_names=set(),
            clear_file_sources=set(),
        )

    if not env_values and not file_sources:
        raise click.ClickException(
            f"Credential bundle `{credential_name}` does not exist under `{tool}` and no auth inputs were provided."
        )
    return _write_project_auth_bundle(
        overlay=overlay,
        tool=tool,
        name=credential_name,
        env_values=env_values,
        file_sources=file_sources,
        require_any_input=False,
        operation="add",
        clear_env_names=set(),
        clear_file_sources=set(),
    )


def _validate_specialist_create_inputs(
    *,
    overlay: HoumaoProjectOverlay,
    specialist_name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
) -> str | None:
    """Validate project easy specialist creation inputs."""

    if system_prompt is not None and system_prompt_file is not None:
        raise click.ClickException(
            "Provide at most one of `--system-prompt` or `--system-prompt-file`."
        )
    conflict_reasons: list[str] = []
    if ProjectCatalog.from_overlay(overlay).specialist_exists(specialist_name):
        conflict_reasons.append(f"catalog entry in `{overlay.catalog_path}`")
    role_root = _role_root(overlay=overlay, role_name=specialist_name)
    if role_root.exists():
        conflict_reasons.append(f"role projection at `{role_root}`")
    if not conflict_reasons:
        return None
    return ", ".join(conflict_reasons)


def _resolve_system_prompt_text(
    *,
    system_prompt: str | None,
    system_prompt_file: Path | None,
) -> str:
    """Resolve specialist system prompt content from inline or file input."""

    if system_prompt is not None:
        value = system_prompt.strip()
        if not value:
            raise click.ClickException("`--system-prompt` must not be empty.")
        return value
    if system_prompt_file is None:
        return ""
    return system_prompt_file.read_text(encoding="utf-8").rstrip()


def _import_skill_directories(
    *,
    overlay: HoumaoProjectOverlay,
    skill_dirs: tuple[Path, ...],
) -> list[Path]:
    """Copy or reuse skill directories under `.houmao/agents/skills/`."""

    ensure_project_agent_compatibility_tree(overlay)
    imported: list[Path] = []
    for skill_dir in skill_dirs:
        source_dir = skill_dir.resolve()
        skill_doc = (source_dir / "SKILL.md").resolve()
        if not skill_doc.is_file():
            raise click.ClickException(f"Skill directory must contain `SKILL.md`: {source_dir}")
        destination_dir = (overlay.agents_root / "skills" / source_dir.name).resolve()
        if not destination_dir.exists():
            shutil.copytree(source_dir, destination_dir)
        elif not destination_dir.is_dir():
            raise click.ClickException(f"Skill destination is not a directory: {destination_dir}")
        imported.append(destination_dir)
    return imported


def _parse_specialist_env_records_or_click(
    *,
    adapter: ToolAdapter,
    env_set: tuple[str, ...],
) -> dict[str, str]:
    """Parse and validate persistent specialist env records."""

    try:
        parsed = parse_persistent_env_record_specs(env_set)
        return validate_persistent_env_records(
            parsed,
            auth_env_allowlist=adapter.auth_env_allowlist,
            source="project easy specialist create --env-set",
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_instance_env_set_or_click(env_set: tuple[str, ...]) -> dict[str, str]:
    """Resolve one-off instance launch env bindings."""

    try:
        return resolve_runtime_env_set_specs(env_set, process_env=os.environ)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _specialist_payload(
    *,
    overlay: HoumaoProjectOverlay,
    metadata: SpecialistMetadata,
) -> dict[str, object]:
    """Return one structured specialist payload with generated canonical paths."""

    return {
        "name": metadata.name,
        "tool": metadata.tool,
        "provider": metadata.provider,
        "credential": metadata.credential_name,
        "role_name": metadata.role_name,
        "skills": list(metadata.skills),
        "launch": dict(metadata.launch_payload),
        "metadata_path": str(metadata.metadata_path)
        if metadata.metadata_path is not None
        else None,
        "generated": {
            "role_prompt": str(metadata.resolved_system_prompt_path(overlay)),
            "preset": str(metadata.resolved_preset_path(overlay)),
            "auth": str(metadata.resolved_auth_path(overlay)),
            "skills": [str(path) for path in metadata.resolved_skill_paths(overlay)],
        },
    }


def _load_specialist_or_click(*, overlay: HoumaoProjectOverlay, name: str) -> SpecialistMetadata:
    """Load one specialist definition or raise one operator-facing error."""

    specialist_name = _require_non_empty_name(name, field_name="--name")
    try:
        return load_specialist(overlay=overlay, name=specialist_name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def _remove_specialist_metadata_or_click(*, overlay: HoumaoProjectOverlay, name: str) -> Path:
    """Delete one specialist metadata document or raise one operator-facing error."""

    try:
        return remove_specialist_metadata(overlay=overlay, name=name)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _list_project_instances(
    *,
    overlay: HoumaoProjectOverlay,
    specialists_by_name: dict[str, SpecialistMetadata],
) -> list[dict[str, object]]:
    """Return project-local managed agents as specialist-annotated instances."""

    instances: list[dict[str, object]] = []
    for identity in list_managed_agents(port=None).agents:
        identity_payload = identity.model_dump(mode="json")
        manifest_path_value = identity_payload.get("manifest_path")
        if not isinstance(manifest_path_value, str) or not manifest_path_value.strip():
            continue
        manifest_path = Path(manifest_path_value).resolve()
        if not manifest_path.is_file():
            continue
        try:
            manifest_payload = _load_manifest_payload(manifest_path)
        except Exception:
            continue
        if not _manifest_belongs_to_overlay(overlay=overlay, manifest_payload=manifest_payload):
            continue
        instances.append(
            _instance_payload(
                overlay=overlay,
                identity_payload=identity_payload,
                manifest_payload=manifest_payload,
                specialists_by_name=specialists_by_name,
            )
        )
    return instances


def _instance_payload(
    *,
    overlay: HoumaoProjectOverlay,
    identity_payload: dict[str, object],
    manifest_payload: dict[str, object],
    specialists_by_name: dict[str, SpecialistMetadata],
) -> dict[str, object]:
    """Build one project-local instance payload from managed runtime state."""

    role_name = str(manifest_payload.get("role_name", "")).strip() or None
    tool_name = str(manifest_payload.get("tool", "")).strip() or None
    specialist = specialists_by_name.get(role_name) if role_name is not None else None
    mailbox_payload = _instance_mailbox_payload(manifest_payload)
    runtime_payload = manifest_payload.get("runtime")
    return {
        "instance_name": identity_payload.get("agent_name"),
        "agent_id": identity_payload.get("agent_id"),
        "transport": identity_payload.get("transport"),
        "tool": tool_name or identity_payload.get("tool"),
        "role_name": role_name,
        "manifest_path": identity_payload.get("manifest_path"),
        "session_root": identity_payload.get("session_root"),
        "tmux_session_name": identity_payload.get("tmux_session_name"),
        "specialist": specialist.name if specialist is not None else None,
        "project_root": str(overlay.project_root),
        "project_agent_def_dir": runtime_payload.get("agent_def_dir")
        if isinstance(runtime_payload, dict)
        else None,
        "mailbox": mailbox_payload,
    }


def _instance_mailbox_payload(manifest_payload: dict[str, object]) -> dict[str, object] | None:
    """Return one runtime-derived mailbox summary for an instance payload."""

    launch_plan_payload = manifest_payload.get("launch_plan")
    if not isinstance(launch_plan_payload, dict):
        return None
    mailbox_payload = launch_plan_payload.get("mailbox")
    if not isinstance(mailbox_payload, dict):
        return None

    transport = mailbox_payload.get("transport")
    if not isinstance(transport, str) or not transport.strip():
        return None

    if transport == "filesystem":
        address = mailbox_payload.get("address")
        filesystem_root = mailbox_payload.get("filesystem_root")
        if not isinstance(address, str) or not address.strip():
            return None
        if not isinstance(filesystem_root, str) or not filesystem_root.strip():
            return None
        mailbox_root = Path(filesystem_root).resolve()
        mailbox_kind = mailbox_payload.get("mailbox_kind")
        if not isinstance(mailbox_kind, str) or not mailbox_kind.strip():
            mailbox_kind = "in_root"
        mailbox_path_value = mailbox_payload.get("mailbox_path")
        mailbox_dir = (
            Path(mailbox_path_value).resolve()
            if isinstance(mailbox_path_value, str) and mailbox_path_value.strip()
            else mailbox_root / "mailboxes" / address
        )
        return {
            "transport": transport,
            "principal_id": mailbox_payload.get("principal_id"),
            "address": address,
            "mailbox_root": str(mailbox_root),
            "mailbox_kind": mailbox_kind,
            "mailbox_dir": str(mailbox_dir),
            "bindings_version": mailbox_payload.get("bindings_version"),
        }

    return {
        "transport": transport,
        "principal_id": mailbox_payload.get("principal_id"),
        "address": mailbox_payload.get("address"),
        "bindings_version": mailbox_payload.get("bindings_version"),
    }


def _require_manifest_path_for_identity(*, identity_payload: dict[str, object]) -> Path:
    """Return one resolved manifest path from an identity payload."""

    manifest_path_value = identity_payload.get("manifest_path")
    if not isinstance(manifest_path_value, str) or not manifest_path_value.strip():
        raise click.ClickException("Managed agent does not expose a manifest path.")
    manifest_path = Path(manifest_path_value).resolve()
    if not manifest_path.is_file():
        raise click.ClickException(f"Managed agent manifest path is missing: {manifest_path}")
    return manifest_path


def _load_manifest_payload(manifest_path: Path) -> dict[str, object]:
    """Load one manifest payload as a JSON-compatible mapping."""

    payload = load_session_manifest(manifest_path).payload
    if not isinstance(payload, dict):
        raise ValueError(f"{manifest_path}: expected manifest payload to be a mapping.")
    return payload


def _manifest_belongs_to_overlay(
    *,
    overlay: HoumaoProjectOverlay,
    manifest_payload: dict[str, object],
) -> bool:
    """Return whether one manifest payload belongs to the selected project overlay."""

    runtime_payload = manifest_payload.get("runtime")
    if not isinstance(runtime_payload, dict):
        return False
    raw_agent_def_dir = runtime_payload.get("agent_def_dir")
    if not isinstance(raw_agent_def_dir, str) or not raw_agent_def_dir.strip():
        return False
    return Path(raw_agent_def_dir).resolve() == overlay.agents_root


def _load_overlay_tool_adapter(*, overlay: HoumaoProjectOverlay, tool: str) -> ToolAdapter:
    """Load one tool adapter from the project-local agent-definition tree."""

    adapter_path = (_tool_root(overlay=overlay, tool=tool) / "adapter.yaml").resolve()
    if not adapter_path.is_file():
        raise click.ClickException(
            f"Tool `{tool}` is not initialized under the discovered project overlay: {adapter_path}"
        )
    try:
        return parse_tool_adapter(adapter_path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _auth_bundle_root(*, overlay: HoumaoProjectOverlay, tool: str, name: str) -> Path:
    """Return the root directory for one tool-local auth bundle."""

    return (_tool_root(overlay=overlay, tool=tool) / "auth" / name).resolve()


def _auth_bundle_env_file(*, overlay: HoumaoProjectOverlay, tool: str, name: str) -> Path:
    """Return the env-file path for one tool-local auth bundle."""

    return (_auth_bundle_root(overlay=overlay, tool=tool, name=name) / "env" / "vars.env").resolve()


def _describe_env_value(*, env_name: str, env_values: dict[str, str]) -> dict[str, object]:
    """Describe one env-backed auth value without leaking secret-like content."""

    if env_name not in env_values:
        return {"present": False}
    if _is_secret_env_name(env_name):
        return {"present": True, "redacted": True}
    return {"present": True, "value": env_values[env_name]}


def _describe_file_mapping(*, files_root: Path, mapping: AuthFileMapping) -> dict[str, object]:
    """Describe one file-backed auth entry without returning raw content."""

    source_path = (files_root / mapping.source).resolve()
    return {
        "present": source_path.is_file(),
        "path": str(source_path) if source_path.is_file() else None,
        "required": mapping.required,
    }


def _load_existing_env_values(path: Path) -> dict[str, str]:
    """Load existing auth-bundle env values when present."""

    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            continue
        values[normalized_key] = value.strip()
    return values


def _render_env_file(*, env_values: dict[str, str], allowlist: list[str]) -> str:
    """Render one stable `env/vars.env` file for a tool-local auth bundle."""

    lines = [
        f"{env_name}={env_values[env_name]}" for env_name in allowlist if env_name in env_values
    ]
    return "\n".join(lines) + "\n"


def _compact_env_values(raw_values: dict[str, str | None]) -> dict[str, str]:
    """Drop empty env values before auth-bundle materialization."""

    return {
        env_name: value.strip()
        for env_name, value in raw_values.items()
        if value is not None and value.strip()
    }


def _flagged_items(values: dict[str, bool]) -> set[str]:
    """Return the names whose boolean flag is enabled."""

    return {name for name, enabled in values.items() if enabled}


def _is_secret_env_name(env_name: str) -> bool:
    """Return whether one env-var name should be redacted in CLI output."""

    normalized = env_name.upper()
    return any(token in normalized for token in _SECRET_ENV_TOKENS)


def _overlay_relative_path(*, overlay: HoumaoProjectOverlay, path: Path) -> str:
    """Return one path relative to the overlay root using POSIX separators."""

    return path.resolve().relative_to(overlay.overlay_root).as_posix()


def _relative_file_listing(root: Path) -> list[str]:
    """Return stable relative file paths rooted at one directory."""

    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def _default_role_prompt(role_name: str) -> str:
    """Return the default scaffolded role prompt content."""

    return f"# {role_name}\n\nDescribe the specialist system prompt here.\n"


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load one YAML mapping payload from disk."""

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise click.ClickException(f"{path}: expected a top-level YAML mapping.")
    return loaded


def _optional_non_empty_value(value: str | None) -> str | None:
    """Return one optional non-empty CLI value."""

    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _require_non_empty_name(value: str, *, field_name: str) -> str:
    """Validate one tool, role, setup, skill, or auth-bundle name."""

    candidate = value.strip()
    if not candidate:
        raise click.ClickException(f"{field_name} must not be empty.")
    if "/" in candidate or "\\" in candidate:
        raise click.ClickException(f"{field_name} must not contain path separators.")
    return candidate
