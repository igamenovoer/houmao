"""Repo-local project-overlay commands for `houmao-mgr`."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, cast

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
from houmao.agents.launch_policy.models import OperatorPromptMode
from houmao.agents.managed_prompt_header import ManagedHeaderPolicy
from houmao.agents.mailbox_runtime_support import (
    parse_declarative_mailbox_config,
    serialize_declarative_mailbox_config,
)
from houmao.agents.model_selection import (
    ModelConfig,
    model_config_to_payload,
    normalize_model_config,
)
from houmao.agents.realm_controller.gateway_models import GatewayCurrentExecutionMode
from houmao.agents.realm_controller.manifest import load_session_manifest
from houmao.project.catalog import ProjectCatalog
from houmao.project.easy import (
    SpecialistMetadata,
    TOOL_PROVIDER_MAP,
    list_specialists,
    load_specialist,
    remove_profile_metadata,
    remove_specialist_metadata,
)
from houmao.project.launch_profiles import (
    launch_profile_defaults_payload,
    launch_profile_source_payload,
    list_resolved_launch_profiles,
    resolve_launch_profile,
)
from houmao.project.overlay import (
    HoumaoProjectOverlay,
    ProjectAwareLocalRoots,
    bootstrap_project_overlay_at_root,
    ensure_project_aware_local_roots,
    ensure_project_agent_compatibility_tree,
    materialize_project_agent_catalog_projection,
    resolve_project_init_overlay_root,
    resolve_project_aware_local_roots,
)

from .agents.core import emit_local_launch_completion, launch_managed_agent_locally
from .cleanup_support import emit_cleanup_payload
from .common import (
    build_destructive_confirmation_callback,
    confirm_destructive_action,
    managed_launch_force_option,
    overwrite_confirm_option,
)
from .output import emit
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
from .project_aware_wording import (
    describe_overlay_bootstrap,
    describe_overlay_discovery_mode,
    describe_overlay_root_selection_source,
)

_SECRET_ENV_TOKENS: tuple[str, ...] = ("KEY", "TOKEN", "SECRET", "PASSWORD")
_SUPPORTED_PROJECT_TOOLS: tuple[str, ...] = ("claude", "codex", "gemini")
_CLAUDE_RUNTIME_STATE_TEMPLATE_FILENAME = "claude_state.template.json"
_CLAUDE_VENDOR_CREDENTIALS_FILENAME = ".credentials.json"
_CLAUDE_VENDOR_GLOBAL_STATE_FILENAME = ".claude.json"
_CLAUDE_VENDOR_LOGIN_FILE_SOURCES: frozenset[str] = frozenset(
    {
        _CLAUDE_VENDOR_CREDENTIALS_FILENAME,
        _CLAUDE_VENDOR_GLOBAL_STATE_FILENAME,
    }
)


@click.group(name="project")
def project_group() -> None:
    """Manage the selected Houmao project overlay for this invocation."""


@project_group.command(name="init")
@click.option(
    "--with-compatibility-profiles",
    is_flag=True,
    help="Also create the optional `.houmao/agents/compatibility-profiles/` subtree.",
)
def init_project_command(with_compatibility_profiles: bool) -> None:
    """Create or validate the active project overlay, defaulting to `<cwd>/.houmao`."""

    cwd = Path.cwd().resolve()
    try:
        overlay_root = resolve_project_init_overlay_root(cwd=cwd)
        result = bootstrap_project_overlay_at_root(
            overlay_root,
            include_compatibility_profiles=with_compatibility_profiles,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    emit(
        {
            "project_root": str(result.project_overlay.project_root),
            "overlay_root": str(result.project_overlay.overlay_root),
            "config_path": str(result.project_overlay.config_path),
            "catalog_path": str(result.project_overlay.catalog_path),
            "content_root": str(result.project_overlay.content_root),
            "agent_def_dir": str(result.project_overlay.agents_root),
            "runtime_root": str(result.project_overlay.runtime_root),
            "jobs_root": str(result.project_overlay.jobs_root),
            "mailbox_root": str(result.project_overlay.mailbox_root),
            "easy_root": str(result.project_overlay.easy_root),
            "created_directories": [str(path) for path in result.created_directories],
            "written_files": [str(path) for path in result.written_files],
            "preserved_files": [str(path) for path in result.preserved_files],
        }
    )


@project_group.command(name="status")
def project_status_command() -> None:
    """Report the selected Houmao project-overlay state for this invocation."""

    cwd = Path.cwd().resolve()
    try:
        roots = resolve_project_aware_local_roots(cwd=cwd)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    overlay = roots.project_overlay
    emit(
        {
            "discovered": overlay is not None,
            "project_root": str(overlay.project_root) if overlay is not None else None,
            "overlay_root": str(roots.overlay_root),
            "overlay_root_source": roots.overlay_root_source,
            "overlay_discovery_mode": roots.overlay_discovery_mode,
            "overlay_discovery_detail": describe_overlay_discovery_mode(
                overlay_discovery_mode=roots.overlay_discovery_mode
            ),
            "selected_overlay_detail": _selected_overlay_detail(roots),
            "config_path": str(overlay.config_path) if overlay is not None else None,
            "catalog_path": str(overlay.catalog_path) if overlay is not None else None,
            "effective_agent_def_dir": str(roots.agent_def_dir),
            "effective_agent_def_dir_source": roots.agent_def_dir_source,
            "project_runtime_root": str(roots.runtime_root),
            "project_jobs_root": str(roots.jobs_root),
            "project_mailbox_root": str(roots.mailbox_root),
            "project_easy_root": str(roots.easy_root),
            "would_bootstrap_overlay": overlay is None,
            "overlay_bootstrap_detail": _status_overlay_bootstrap_detail(roots),
        }
    )


def _ensure_project_roots() -> ProjectAwareLocalRoots:
    """Return ensured project-aware roots or raise one operator-facing error."""

    try:
        roots = ensure_project_aware_local_roots(cwd=Path.cwd().resolve())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if roots.project_overlay is None:
        raise click.ClickException("Failed to ensure the active project overlay.")
    return roots


def _ensure_project_overlay() -> HoumaoProjectOverlay:
    """Return the ensured selected project overlay."""

    overlay = _ensure_project_roots().project_overlay
    assert overlay is not None
    return overlay


def _resolve_existing_project_roots(
    *,
    fallback_label: str | None = None,
) -> ProjectAwareLocalRoots:
    """Return the selected roots for one non-creating project flow."""

    try:
        roots = resolve_project_aware_local_roots(cwd=Path.cwd().resolve())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if roots.project_overlay is None:
        raise click.ClickException(
            _missing_selected_overlay_message(roots=roots, fallback_label=fallback_label)
        )
    return roots


def _resolve_existing_project_overlay(
    *,
    fallback_label: str | None = None,
) -> HoumaoProjectOverlay:
    """Return the active selected overlay for non-creating project flows."""

    overlay = _resolve_existing_project_roots(fallback_label=fallback_label).project_overlay
    assert overlay is not None
    return overlay


def _selected_overlay_detail(roots: ProjectAwareLocalRoots) -> str:
    """Describe the selected overlay root for one invocation."""

    detail = describe_overlay_root_selection_source(
        overlay_root_source=roots.overlay_root_source,
        overlay_discovery_mode=roots.overlay_discovery_mode,
    )
    if roots.project_overlay is None:
        return (
            f"{detail} No project overlay exists yet at `{roots.overlay_root}` for this invocation."
        )
    return detail


def _status_overlay_bootstrap_detail(roots: ProjectAwareLocalRoots) -> str:
    """Describe the bootstrap outcome for `project status`."""

    if roots.project_overlay is None:
        return (
            "Project status used non-creating resolution and would bootstrap the selected overlay "
            "during a stateful project command."
        )
    return describe_overlay_bootstrap(created_overlay=False, overlay_exists=True)


def _missing_selected_overlay_message(
    *,
    roots: ProjectAwareLocalRoots,
    fallback_label: str | None = None,
) -> str:
    """Build one non-creating selected-overlay failure message."""

    message = (
        "No Houmao project overlay is available at the selected overlay root "
        f"`{roots.overlay_root}`. This command uses non-creating resolution and did not "
        "bootstrap it."
    )
    if fallback_label is not None:
        return f"{message} It did not fall back to the {fallback_label}."
    return message


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
@click.option("--oauth-token", default=None, help="Value for `CLAUDE_CODE_OAUTH_TOKEN`.")
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
    help="Optional Claude bootstrap state template JSON to store in the auth bundle (not a credential).",
)
@click.option(
    "--config-dir",
    "config_dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    default=None,
    help=(
        "Optional Claude config dir to import vendor login state from "
        "(`.credentials.json` plus companion `.claude.json` when present)."
    ),
)
def add_claude_project_auth_command(
    name: str,
    api_key: str | None,
    auth_token: str | None,
    oauth_token: str | None,
    base_url: str | None,
    model: str | None,
    small_fast_model: str | None,
    subagent_model: str | None,
    default_opus_model: str | None,
    default_sonnet_model: str | None,
    default_haiku_model: str | None,
    state_template_file: Path | None,
    config_dir: Path | None,
) -> None:
    """Create one new Claude auth bundle inside the active project overlay."""

    _run_claude_auth_write(
        operation="add",
        name=name,
        api_key=api_key,
        auth_token=auth_token,
        oauth_token=oauth_token,
        base_url=base_url,
        model=model,
        small_fast_model=small_fast_model,
        subagent_model=subagent_model,
        default_opus_model=default_opus_model,
        default_sonnet_model=default_sonnet_model,
        default_haiku_model=default_haiku_model,
        state_template_file=state_template_file,
        config_dir=config_dir,
        clear_env_names=set(),
        clear_file_sources=set(),
    )


@claude_auth_group.command(name="set")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `ANTHROPIC_API_KEY`.")
@click.option("--auth-token", default=None, help="Value for `ANTHROPIC_AUTH_TOKEN`.")
@click.option("--oauth-token", default=None, help="Value for `CLAUDE_CODE_OAUTH_TOKEN`.")
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
    help="Optional Claude bootstrap state template JSON to store in the auth bundle (not a credential).",
)
@click.option(
    "--config-dir",
    "config_dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    default=None,
    help=(
        "Optional Claude config dir to import vendor login state from "
        "(`.credentials.json` plus companion `.claude.json` when present)."
    ),
)
@click.option(
    "--clear-api-key", is_flag=True, help="Remove `ANTHROPIC_API_KEY` from the auth bundle."
)
@click.option(
    "--clear-auth-token", is_flag=True, help="Remove `ANTHROPIC_AUTH_TOKEN` from the auth bundle."
)
@click.option(
    "--clear-oauth-token",
    is_flag=True,
    help="Remove `CLAUDE_CODE_OAUTH_TOKEN` from the auth bundle.",
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
    help="Remove optional `files/claude_state.template.json` bootstrap state from the auth bundle.",
)
@click.option(
    "--clear-config-dir",
    is_flag=True,
    help="Remove imported Claude vendor login-state files from the auth bundle.",
)
def set_claude_project_auth_command(
    name: str,
    api_key: str | None,
    auth_token: str | None,
    oauth_token: str | None,
    base_url: str | None,
    model: str | None,
    small_fast_model: str | None,
    subagent_model: str | None,
    default_opus_model: str | None,
    default_sonnet_model: str | None,
    default_haiku_model: str | None,
    state_template_file: Path | None,
    config_dir: Path | None,
    clear_api_key: bool,
    clear_auth_token: bool,
    clear_oauth_token: bool,
    clear_base_url: bool,
    clear_model: bool,
    clear_small_fast_model: bool,
    clear_subagent_model: bool,
    clear_default_opus_model: bool,
    clear_default_sonnet_model: bool,
    clear_default_haiku_model: bool,
    clear_state_template_file: bool,
    clear_config_dir: bool,
) -> None:
    """Update one existing Claude auth bundle inside the active project overlay."""

    _run_claude_auth_write(
        operation="set",
        name=name,
        api_key=api_key,
        auth_token=auth_token,
        oauth_token=oauth_token,
        base_url=base_url,
        model=model,
        small_fast_model=small_fast_model,
        subagent_model=subagent_model,
        default_opus_model=default_opus_model,
        default_sonnet_model=default_sonnet_model,
        default_haiku_model=default_haiku_model,
        state_template_file=state_template_file,
        config_dir=config_dir,
        clear_env_names=_flagged_items(
            {
                "ANTHROPIC_API_KEY": clear_api_key,
                "ANTHROPIC_AUTH_TOKEN": clear_auth_token,
                "CLAUDE_CODE_OAUTH_TOKEN": clear_oauth_token,
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
            {
                _CLAUDE_RUNTIME_STATE_TEMPLATE_FILENAME: clear_state_template_file,
                _CLAUDE_VENDOR_CREDENTIALS_FILENAME: clear_config_dir,
                _CLAUDE_VENDOR_GLOBAL_STATE_FILENAME: clear_config_dir,
            }
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
    """Create one new Codex auth bundle inside the active project overlay."""

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
    """Update one existing Codex auth bundle inside the active project overlay."""

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
@click.option("--base-url", default=None, help="Value for `GOOGLE_GEMINI_BASE_URL`.")
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
    help="Optional path to the Gemini CLI `oauth_creds.json` file.",
)
def add_gemini_project_auth_command(
    name: str,
    api_key: str | None,
    base_url: str | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    oauth_creds: Path | None,
) -> None:
    """Create one new Gemini auth bundle inside the active project overlay."""

    _run_gemini_auth_write(
        operation="add",
        name=name,
        api_key=api_key,
        base_url=base_url,
        google_api_key=google_api_key,
        use_vertex_ai=use_vertex_ai,
        oauth_creds=oauth_creds,
        clear_env_names=set(),
    )


@gemini_auth_group.command(name="set")
@click.option("--name", required=True, help="Auth bundle name.")
@click.option("--api-key", default=None, help="Value for `GEMINI_API_KEY`.")
@click.option("--base-url", default=None, help="Value for `GOOGLE_GEMINI_BASE_URL`.")
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
    "--clear-base-url", is_flag=True, help="Remove `GOOGLE_GEMINI_BASE_URL` from the auth bundle."
)
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
    base_url: str | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    oauth_creds: Path | None,
    clear_api_key: bool,
    clear_base_url: bool,
    clear_google_api_key: bool,
    clear_use_vertex_ai: bool,
) -> None:
    """Update one existing Gemini auth bundle inside the active project overlay."""

    _run_gemini_auth_write(
        operation="set",
        name=name,
        api_key=api_key,
        base_url=base_url,
        google_api_key=google_api_key,
        use_vertex_ai=use_vertex_ai,
        oauth_creds=oauth_creds,
        clear_env_names=_flagged_items(
            {
                "GEMINI_API_KEY": clear_api_key,
                "GOOGLE_GEMINI_BASE_URL": clear_base_url,
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

    overlay = _resolve_existing_project_overlay()
    emit(
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
@click.option(
    "--include-prompt",
    is_flag=True,
    help="Include the current role prompt text in the structured output.",
)
def get_project_role_command(name: str, include_prompt: bool) -> None:
    """Inspect one project-local role."""

    overlay = _resolve_existing_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")
    emit(_role_summary(overlay=overlay, role_name=role_name, include_prompt=include_prompt))


@project_roles_group.command(name="init")
@click.option("--name", required=True, help="Role name.")
@click.option(
    "--system-prompt",
    default=None,
    help="Inline system prompt content.",
)
@click.option(
    "--system-prompt-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a Markdown system prompt file.",
)
def init_project_role_command(
    name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
) -> None:
    """Create one new project-local role root."""

    overlay = _ensure_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if role_root.exists():
        raise click.ClickException(f"Role already exists: {role_root}")
    if system_prompt is not None and system_prompt_file is not None:
        raise click.ClickException(
            "Provide at most one of `--system-prompt` or `--system-prompt-file`."
        )

    prompt_text = _default_role_prompt(role_name)
    if system_prompt is not None:
        prompt_text = _resolve_required_prompt_text(
            system_prompt=system_prompt,
            system_prompt_file=None,
        )
    elif system_prompt_file is not None:
        prompt_text = _resolve_required_prompt_text(
            system_prompt=None,
            system_prompt_file=system_prompt_file,
        )

    prompt_path = _write_role_prompt(role_root=role_root, prompt_text=prompt_text)
    created_paths: list[str] = [str(role_root), str(prompt_path)]
    emit(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "role_path": str(role_root),
            "system_prompt_path": str(prompt_path),
            "created_paths": created_paths,
        }
    )


@project_roles_group.command(name="set")
@click.option("--name", required=True, help="Role name.")
@click.option(
    "--system-prompt",
    default=None,
    help="Inline system prompt content.",
)
@click.option(
    "--system-prompt-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a Markdown system prompt file.",
)
@click.option("--clear-system-prompt", is_flag=True, help="Clear the role system prompt.")
def set_project_role_command(
    name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    clear_system_prompt: bool,
) -> None:
    """Update one existing project-local role prompt."""

    overlay = _ensure_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")
    if clear_system_prompt and (system_prompt is not None or system_prompt_file is not None):
        raise click.ClickException(
            "`--clear-system-prompt` cannot be combined with `--system-prompt` or "
            "`--system-prompt-file`."
        )
    if not clear_system_prompt and system_prompt is None and system_prompt_file is None:
        raise click.ClickException(
            "Provide one of `--system-prompt`, `--system-prompt-file`, or `--clear-system-prompt`."
        )
    prompt_text = (
        ""
        if clear_system_prompt
        else _resolve_required_prompt_text(
            system_prompt=system_prompt,
            system_prompt_file=system_prompt_file,
        )
    )
    prompt_path = _write_role_prompt(role_root=role_root, prompt_text=prompt_text, overwrite=True)
    emit(
        _role_summary(overlay=overlay, role_name=role_name)
        | {"system_prompt_path": str(prompt_path)}
    )


@project_roles_group.command(name="remove")
@click.option("--name", required=True, help="Role name to remove.")
def remove_project_role_command(name: str) -> None:
    """Remove one project-local role subtree."""

    overlay = _resolve_existing_project_overlay()
    role_name = _require_non_empty_name(name, field_name="--name")
    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")
    referencing_presets = _list_named_preset_summaries(overlay=overlay, role_name=role_name)
    if referencing_presets:
        preset_names = ", ".join(str(item["name"]) for item in referencing_presets)
        raise click.ClickException(
            f"Cannot remove role `{role_name}` because named recipes still reference it: "
            f"{preset_names}"
        )
    shutil.rmtree(role_root)
    emit(
        {
            "project_root": str(overlay.project_root),
            "role": role_name,
            "removed": True,
            "path": str(role_root),
        }
    )


@agents_project_group.group(name="presets")
def project_presets_group() -> None:
    """Compatibility alias for `project agents recipes` stored under `.houmao/agents/presets/`."""


project_recipes_group = click.Group(
    name="recipes",
    help="Manage project-local named recipes stored under `.houmao/agents/presets/`.",
)


@project_presets_group.command(name="list")
@click.option("--role", default=None, help="Optional role filter.")
@click.option(
    "--tool",
    "tool_name",
    default=None,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Optional tool filter.",
)
def list_project_presets_command(role: str | None, tool_name: str | None) -> None:
    """List project-local named recipes."""

    overlay = _resolve_existing_project_overlay()
    emit(
        {
            "project_root": str(overlay.project_root),
            "recipes": _list_named_preset_summaries(
                overlay=overlay,
                role_name=_optional_non_empty_value(role),
                tool=tool_name,
            ),
        }
    )


@project_presets_group.command(name="get")
@click.option("--name", required=True, help="Recipe name.")
def get_project_preset_command(name: str) -> None:
    """Inspect one project-local named recipe."""

    overlay = _resolve_existing_project_overlay()
    emit(
        _preset_summary(
            overlay=overlay, preset_name=_require_non_empty_name(name, field_name="--name")
        )
    )


@project_presets_group.command(name="add")
@click.option("--name", required=True, help="Recipe name.")
@click.option("--role", required=True, help="Role name.")
@click.option(
    "--tool",
    "tool_name",
    required=True,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Tool lane.",
)
@click.option("--setup", default="default", show_default=True, help="Recipe setup name.")
@click.option("--skill", "skill_names", multiple=True, help="Repeatable skill name.")
@click.option("--auth", default=None, help="Optional auth bundle name.")
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional launch.prompt_mode value; defaults to `unattended`.",
)
@click.option("--model", default=None, help="Optional launch-owned model name.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(1, 10),
    default=None,
    help="Optional Houmao-defined launch-owned reasoning level (1..10).",
)
def add_project_preset_command(
    name: str,
    role: str,
    tool_name: str,
    setup: str,
    skill_names: tuple[str, ...],
    auth: str | None,
    prompt_mode: str | None,
    model: str | None,
    reasoning_level: int | None,
) -> None:
    """Create one minimal project-local named recipe."""

    overlay = _ensure_project_overlay()
    preset_name = _require_non_empty_name(name, field_name="--name")
    role_name = _require_non_empty_name(role, field_name="--role")
    resolved_setup = _require_non_empty_name(setup, field_name="--setup")
    _ensure_role_exists(overlay=overlay, role_name=role_name)
    _ensure_unique_preset_tuple(
        overlay=overlay,
        preset_name=preset_name,
        role_name=role_name,
        tool=tool_name,
        setup=resolved_setup,
    )
    preset_path = _write_named_preset(
        overlay=overlay,
        preset_name=preset_name,
        role_name=role_name,
        tool=tool_name,
        setup=resolved_setup,
        skills=[_require_non_empty_name(value, field_name="--skill") for value in skill_names],
        auth=_optional_non_empty_value(auth),
        prompt_mode=_optional_non_empty_value(prompt_mode),
        model_config=_build_model_config_or_click(
            model_name=_resolve_model_name_or_click(model),
            reasoning_level=reasoning_level,
        ),
    )
    emit(
        {
            "project_root": str(overlay.project_root),
            "name": preset_name,
            "path": str(preset_path),
            "created": True,
        }
    )


@project_presets_group.command(name="set")
@click.option("--name", required=True, help="Recipe name.")
@click.option("--role", default=None, help="Optional role name override.")
@click.option(
    "--tool",
    "tool_name",
    default=None,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Optional tool lane override.",
)
@click.option("--setup", default=None, help="Optional setup override.")
@click.option("--auth", default=None, help="Optional auth override.")
@click.option("--clear-auth", is_flag=True, help="Clear the recipe auth bundle reference.")
@click.option("--add-skill", "add_skill_names", multiple=True, help="Repeatable skill to add.")
@click.option(
    "--remove-skill",
    "remove_skill_names",
    multiple=True,
    help="Repeatable skill to remove.",
)
@click.option("--clear-skills", is_flag=True, help="Clear all recipe skill bindings.")
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional launch.prompt_mode override.",
)
@click.option("--clear-prompt-mode", is_flag=True, help="Clear launch.prompt_mode.")
@click.option("--model", default=None, help="Optional launch-owned model name override.")
@click.option("--clear-model", is_flag=True, help="Clear launch.model.name.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(1, 10),
    default=None,
    help="Optional Houmao-defined launch-owned reasoning level override (1..10).",
)
@click.option(
    "--clear-reasoning-level",
    is_flag=True,
    help="Clear launch.model.reasoning.level.",
)
def set_project_preset_command(
    name: str,
    role: str | None,
    tool_name: str | None,
    setup: str | None,
    auth: str | None,
    clear_auth: bool,
    add_skill_names: tuple[str, ...],
    remove_skill_names: tuple[str, ...],
    clear_skills: bool,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
) -> None:
    """Update one existing project-local named recipe."""

    overlay = _ensure_project_overlay()
    preset_name = _require_non_empty_name(name, field_name="--name")
    preset_path = _preset_path(overlay=overlay, preset_name=preset_name)
    if not preset_path.is_file():
        raise click.ClickException(f"Recipe not found: {preset_path}")
    if clear_auth and auth is not None:
        raise click.ClickException("`--auth` cannot be combined with `--clear-auth`.")
    if clear_prompt_mode and prompt_mode is not None:
        raise click.ClickException("`--prompt-mode` cannot be combined with `--clear-prompt-mode`.")
    if clear_model and model is not None:
        raise click.ClickException("`--model` cannot be combined with `--clear-model`.")
    if clear_reasoning_level and reasoning_level is not None:
        raise click.ClickException(
            "`--reasoning-level` cannot be combined with `--clear-reasoning-level`."
        )
    if (
        role is None
        and tool_name is None
        and setup is None
        and auth is None
        and not clear_auth
        and not add_skill_names
        and not remove_skill_names
        and not clear_skills
        and prompt_mode is None
        and not clear_prompt_mode
        and model is None
        and not clear_model
        and reasoning_level is None
        and not clear_reasoning_level
    ):
        raise click.ClickException("No recipe updates were requested.")

    raw_payload = _load_yaml_mapping(preset_path)
    parsed_preset = parse_agent_preset(preset_path)
    role_name = (
        _require_non_empty_name(role, field_name="--role")
        if role is not None
        else parsed_preset.role_name
    )
    resolved_tool = tool_name or parsed_preset.tool
    resolved_setup = (
        _require_non_empty_name(setup, field_name="--setup")
        if setup is not None
        else parsed_preset.setup
    )
    _ensure_role_exists(overlay=overlay, role_name=role_name)
    skills = [] if clear_skills else list(parsed_preset.skills)
    skills.extend(
        _require_non_empty_name(value, field_name="--add-skill") for value in add_skill_names
    )
    remove_skill_set = {
        _require_non_empty_name(value, field_name="--remove-skill") for value in remove_skill_names
    }
    skills = [skill for skill in skills if skill not in remove_skill_set]
    normalized_skills: list[str] = []
    for skill in skills:
        if skill not in normalized_skills:
            normalized_skills.append(skill)
    resolved_auth = (
        None
        if clear_auth
        else (
            _require_non_empty_name(auth, field_name="--auth")
            if auth is not None
            else parsed_preset.auth
        )
    )
    _ensure_unique_preset_tuple(
        overlay=overlay,
        preset_name=preset_name,
        role_name=role_name,
        tool=resolved_tool,
        setup=resolved_setup,
    )

    raw_payload["role"] = role_name
    raw_payload["tool"] = resolved_tool
    raw_payload["setup"] = resolved_setup
    raw_payload["skills"] = normalized_skills
    if resolved_auth is None:
        raw_payload.pop("auth", None)
    else:
        raw_payload["auth"] = resolved_auth
    launch_payload = raw_payload.get("launch")
    if launch_payload is None:
        launch_mapping: dict[str, object] = {}
    elif isinstance(launch_payload, dict):
        launch_mapping = dict(launch_payload)
    else:
        raise click.ClickException(
            f"{preset_path}: expected `launch` to be a mapping when present."
        )
    if prompt_mode is not None:
        launch_mapping["prompt_mode"] = prompt_mode
    elif clear_prompt_mode:
        launch_mapping.pop("prompt_mode", None)
    current_model_payload = _build_model_config_or_click(
        model_name=parsed_preset.launch.model_config.name
        if parsed_preset.launch.model_config is not None
        else None,
        reasoning_level=parsed_preset.launch.model_config.reasoning.level
        if parsed_preset.launch.model_config is not None
        and parsed_preset.launch.model_config.reasoning is not None
        else None,
    )
    updated_model_config = _merge_model_config_for_storage(
        current_name=current_model_payload.name if current_model_payload is not None else None,
        current_reasoning_level=(
            current_model_payload.reasoning.level
            if current_model_payload is not None and current_model_payload.reasoning is not None
            else None
        ),
        model_name=_resolve_model_name_or_click(model) if model is not None else None,
        reasoning_level=reasoning_level,
        clear_model=clear_model,
        clear_reasoning_level=clear_reasoning_level,
    )
    model_payload = _model_mapping_payload(updated_model_config)
    if model_payload is None:
        launch_mapping.pop("model", None)
    else:
        launch_mapping["model"] = model_payload
    if launch_mapping:
        raw_payload["launch"] = launch_mapping
    else:
        raw_payload.pop("launch", None)

    _write_yaml_mapping(preset_path, raw_payload)
    emit(_preset_summary(overlay=overlay, preset_name=preset_name))


@project_presets_group.command(name="remove")
@click.option("--name", required=True, help="Recipe name.")
def remove_project_preset_command(name: str) -> None:
    """Remove one project-local named recipe."""

    overlay = _resolve_existing_project_overlay()
    preset_name = _require_non_empty_name(name, field_name="--name")
    preset_path = _preset_path(overlay=overlay, preset_name=preset_name)
    if not preset_path.is_file():
        raise click.ClickException(f"Recipe not found: {preset_path}")
    preset_path.unlink()
    emit(
        {
            "project_root": str(overlay.project_root),
            "name": preset_name,
            "removed": True,
            "path": str(preset_path),
        }
    )


project_recipes_group.add_command(list_project_presets_command, name="list")
project_recipes_group.add_command(get_project_preset_command, name="get")
project_recipes_group.add_command(add_project_preset_command, name="add")
project_recipes_group.add_command(set_project_preset_command, name="set")
project_recipes_group.add_command(remove_project_preset_command, name="remove")
agents_project_group.add_command(project_recipes_group)


@agents_project_group.group(name="launch-profiles")
def project_launch_profiles_group() -> None:
    """Manage recipe-backed reusable launch profiles stored under `.houmao/agents/launch-profiles/`."""


@project_launch_profiles_group.command(name="list")
@click.option("--recipe", default=None, help="Optional source recipe filter.")
@click.option(
    "--tool",
    "tool_name",
    default=None,
    type=click.Choice(_SUPPORTED_PROJECT_TOOLS),
    help="Optional tool filter.",
)
def list_project_launch_profiles_command(recipe: str | None, tool_name: str | None) -> None:
    """List project-local named launch profiles."""

    overlay = _resolve_existing_project_overlay()
    emit(
        {
            "project_root": str(overlay.project_root),
            "launch_profiles": _list_launch_profile_payloads(
                overlay=overlay,
                source_recipe=_optional_non_empty_value(recipe),
                tool=tool_name,
            ),
        }
    )


@project_launch_profiles_group.command(name="get")
@click.option("--name", required=True, help="Launch profile name.")
def get_project_launch_profile_command(name: str) -> None:
    """Inspect one project-local named launch profile."""

    overlay = _resolve_existing_project_overlay()
    emit(
        _launch_profile_payload(
            overlay=overlay,
            profile_name=_require_non_empty_name(name, field_name="--name"),
        )
    )


@project_launch_profiles_group.command(name="add")
@click.option("--name", required=True, help="Launch profile name.")
@click.option("--recipe", required=True, help="Source recipe name.")
@click.option("--agent-name", default=None, help="Optional default managed-agent name.")
@click.option("--agent-id", default=None, help="Optional default managed-agent id.")
@click.option("--workdir", default=None, help="Optional default working directory.")
@click.option("--auth", default=None, help="Optional default auth bundle override.")
@click.option("--model", default=None, help="Optional launch-owned model override.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(1, 10),
    default=None,
    help="Optional Houmao-defined launch-owned reasoning override (1..10).",
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional default operator prompt mode.",
)
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Repeatable persistent launch env record (`NAME=value`).",
)
@click.option(
    "--mail-transport",
    type=click.Choice(("filesystem", "stalwart")),
    default=None,
    help="Optional declarative mailbox transport.",
)
@click.option(
    "--mail-principal-id", default=None, help="Optional declarative mailbox principal id."
)
@click.option("--mail-address", default=None, help="Optional declarative mailbox address.")
@click.option("--mail-root", default=None, help="Optional declarative filesystem mailbox root.")
@click.option("--mail-base-url", default=None, help="Optional declarative Stalwart base URL.")
@click.option("--mail-jmap-url", default=None, help="Optional declarative Stalwart JMAP URL.")
@click.option(
    "--mail-management-url",
    default=None,
    help="Optional declarative Stalwart management URL.",
)
@click.option("--headless", is_flag=True, help="Persist headless launch as the default posture.")
@click.option("--no-gateway", is_flag=True, help="Persist gateway auto-attach disabled.")
@click.option(
    "--managed-header/--no-managed-header",
    "managed_header",
    default=None,
    help="Persist managed prompt header policy for launches from this profile.",
)
@click.option(
    "--gateway-port",
    type=click.IntRange(1, 65535),
    default=None,
    help="Persist one fixed loopback gateway port for launches from this profile.",
)
@click.option(
    "--prompt-overlay-mode",
    type=click.Choice(("append", "replace")),
    default=None,
    help="Optional prompt-overlay mode.",
)
@click.option("--prompt-overlay-text", default=None, help="Inline prompt-overlay text.")
@click.option(
    "--prompt-overlay-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a prompt-overlay text file.",
)
def add_project_launch_profile_command(
    name: str,
    recipe: str,
    agent_name: str | None,
    agent_id: str | None,
    workdir: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    prompt_mode: str | None,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    headless: bool,
    no_gateway: bool,
    managed_header: bool | None,
    gateway_port: int | None,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
) -> None:
    """Create one recipe-backed explicit launch profile."""

    overlay = _ensure_project_overlay()
    payload = _store_launch_profile_from_cli(
        overlay=overlay,
        profile_name=_require_non_empty_name(name, field_name="--name"),
        profile_lane="launch_profile",
        source_kind="recipe",
        source_name=_require_non_empty_name(recipe, field_name="--recipe"),
        agent_name=agent_name,
        agent_id=agent_id,
        workdir=workdir,
        auth=auth,
        model=model,
        reasoning_level=reasoning_level,
        prompt_mode=prompt_mode,
        env_set=env_set,
        mail_transport=mail_transport,
        mail_principal_id=mail_principal_id,
        mail_address=mail_address,
        mail_root=mail_root,
        mail_base_url=mail_base_url,
        mail_jmap_url=mail_jmap_url,
        mail_management_url=mail_management_url,
        headless=headless,
        clear_headless=False,
        no_gateway=no_gateway,
        managed_header=managed_header,
        clear_managed_header=False,
        gateway_port=gateway_port,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        prompt_overlay_file=prompt_overlay_file,
        clear_prompt_overlay=False,
        clear_mailbox=False,
        clear_env=False,
        clear_agent_name=False,
        clear_agent_id=False,
        clear_workdir=False,
        clear_auth=False,
        clear_model=False,
        clear_reasoning_level=False,
        clear_prompt_mode=False,
        existing_name=None,
    )
    emit(payload)


@project_launch_profiles_group.command(name="set")
@click.option("--name", required=True, help="Launch profile name.")
@click.option("--agent-name", default=None, help="Optional default managed-agent name override.")
@click.option(
    "--clear-agent-name", is_flag=True, help="Clear the stored default managed-agent name."
)
@click.option("--agent-id", default=None, help="Optional default managed-agent id override.")
@click.option("--clear-agent-id", is_flag=True, help="Clear the stored default managed-agent id.")
@click.option("--workdir", default=None, help="Optional default working directory override.")
@click.option("--clear-workdir", is_flag=True, help="Clear the stored default working directory.")
@click.option("--auth", default=None, help="Optional default auth bundle override.")
@click.option("--clear-auth", is_flag=True, help="Clear the stored auth override.")
@click.option("--model", default=None, help="Optional launch-owned model override.")
@click.option("--clear-model", is_flag=True, help="Clear the stored launch-owned model.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(1, 10),
    default=None,
    help="Optional Houmao-defined launch-owned reasoning override (1..10).",
)
@click.option(
    "--clear-reasoning-level",
    is_flag=True,
    help="Clear the stored launch-owned reasoning level.",
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional default operator prompt mode override.",
)
@click.option("--clear-prompt-mode", is_flag=True, help="Clear the stored operator prompt mode.")
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Repeatable persistent launch env record replacement (`NAME=value`).",
)
@click.option("--clear-env", is_flag=True, help="Clear stored persistent launch env records.")
@click.option(
    "--mail-transport",
    type=click.Choice(("filesystem", "stalwart")),
    default=None,
    help="Optional declarative mailbox transport override.",
)
@click.option(
    "--mail-principal-id", default=None, help="Optional declarative mailbox principal id."
)
@click.option("--mail-address", default=None, help="Optional declarative mailbox address.")
@click.option("--mail-root", default=None, help="Optional declarative filesystem mailbox root.")
@click.option("--mail-base-url", default=None, help="Optional declarative Stalwart base URL.")
@click.option("--mail-jmap-url", default=None, help="Optional declarative Stalwart JMAP URL.")
@click.option(
    "--mail-management-url",
    default=None,
    help="Optional declarative Stalwart management URL.",
)
@click.option(
    "--clear-mailbox", is_flag=True, help="Clear the stored declarative mailbox defaults."
)
@click.option("--headless", is_flag=True, help="Persist headless launch as the default posture.")
@click.option("--clear-headless", is_flag=True, help="Clear the stored headless launch posture.")
@click.option("--no-gateway", is_flag=True, help="Persist gateway auto-attach disabled.")
@click.option(
    "--managed-header/--no-managed-header",
    "managed_header",
    default=None,
    help="Persist managed prompt header policy for launches from this profile.",
)
@click.option(
    "--clear-managed-header",
    is_flag=True,
    help="Clear the stored managed prompt header policy back to inherit.",
)
@click.option(
    "--gateway-port",
    type=click.IntRange(1, 65535),
    default=None,
    help="Persist one fixed loopback gateway port for launches from this profile.",
)
@click.option(
    "--prompt-overlay-mode",
    type=click.Choice(("append", "replace")),
    default=None,
    help="Optional prompt-overlay mode override.",
)
@click.option("--prompt-overlay-text", default=None, help="Inline prompt-overlay text override.")
@click.option(
    "--prompt-overlay-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a prompt-overlay text file.",
)
@click.option("--clear-prompt-overlay", is_flag=True, help="Clear the stored prompt overlay.")
def set_project_launch_profile_command(
    name: str,
    agent_name: str | None,
    clear_agent_name: bool,
    agent_id: str | None,
    clear_agent_id: bool,
    workdir: str | None,
    clear_workdir: bool,
    auth: str | None,
    clear_auth: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    env_set: tuple[str, ...],
    clear_env: bool,
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    clear_mailbox: bool,
    headless: bool,
    clear_headless: bool,
    no_gateway: bool,
    managed_header: bool | None,
    clear_managed_header: bool,
    gateway_port: int | None,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
    clear_prompt_overlay: bool,
) -> None:
    """Update one recipe-backed explicit launch profile."""

    overlay = _ensure_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    payload = _store_launch_profile_from_cli(
        overlay=overlay,
        profile_name=profile_name,
        profile_lane="launch_profile",
        source_kind="recipe",
        source_name=_load_launch_profile_or_click(
            overlay=overlay,
            name=profile_name,
            expected_lane="launch_profile",
        ).entry.source_name,
        agent_name=agent_name,
        agent_id=agent_id,
        workdir=workdir,
        auth=auth,
        model=model,
        reasoning_level=reasoning_level,
        prompt_mode=prompt_mode,
        env_set=env_set,
        mail_transport=mail_transport,
        mail_principal_id=mail_principal_id,
        mail_address=mail_address,
        mail_root=mail_root,
        mail_base_url=mail_base_url,
        mail_jmap_url=mail_jmap_url,
        mail_management_url=mail_management_url,
        headless=headless,
        clear_headless=clear_headless,
        no_gateway=no_gateway,
        managed_header=managed_header,
        clear_managed_header=clear_managed_header,
        gateway_port=gateway_port,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        prompt_overlay_file=prompt_overlay_file,
        clear_prompt_overlay=clear_prompt_overlay,
        clear_mailbox=clear_mailbox,
        clear_env=clear_env,
        clear_agent_name=clear_agent_name,
        clear_agent_id=clear_agent_id,
        clear_workdir=clear_workdir,
        clear_auth=clear_auth,
        clear_model=clear_model,
        clear_reasoning_level=clear_reasoning_level,
        clear_prompt_mode=clear_prompt_mode,
        existing_name=profile_name,
    )
    emit(payload)


@project_launch_profiles_group.command(name="remove")
@click.option("--name", required=True, help="Launch profile name.")
def remove_project_launch_profile_command(name: str) -> None:
    """Remove one project-local named launch profile."""

    overlay = _resolve_existing_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    try:
        metadata_path = ProjectCatalog.from_overlay(overlay).remove_launch_profile(profile_name)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "project_root": str(overlay.project_root),
            "name": profile_name,
            "removed": True,
            "metadata_path": str(metadata_path),
            "path": str(
                (overlay.agents_root / "launch-profiles" / f"{profile_name}.yaml").resolve()
            ),
        }
    )


@project_group.group(name="easy")
def easy_project_group() -> None:
    """Use a higher-level specialist and instance view over the project overlay."""


@easy_project_group.group(name="profile")
def easy_profile_group() -> None:
    """Manage high-level specialist-backed reusable launch profiles."""


@easy_profile_group.command(name="create")
@click.option("--name", required=True, help="Easy profile name.")
@click.option("--specialist", required=True, help="Source specialist name.")
@click.option("--agent-name", default=None, help="Optional default managed-agent name.")
@click.option("--agent-id", default=None, help="Optional default managed-agent id.")
@click.option("--workdir", default=None, help="Optional default working directory.")
@click.option("--auth", default=None, help="Optional default auth bundle override.")
@click.option("--model", default=None, help="Optional launch-owned model override.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(1, 10),
    default=None,
    help="Optional Houmao-defined launch-owned reasoning override (1..10).",
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional default operator prompt mode override.",
)
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Repeatable persistent launch env record (`NAME=value`).",
)
@click.option(
    "--mail-transport",
    type=click.Choice(("filesystem", "stalwart")),
    default=None,
    help="Optional declarative mailbox transport.",
)
@click.option(
    "--mail-principal-id", default=None, help="Optional declarative mailbox principal id."
)
@click.option("--mail-address", default=None, help="Optional declarative mailbox address.")
@click.option("--mail-root", default=None, help="Optional declarative filesystem mailbox root.")
@click.option("--mail-base-url", default=None, help="Optional declarative Stalwart base URL.")
@click.option("--mail-jmap-url", default=None, help="Optional declarative Stalwart JMAP URL.")
@click.option(
    "--mail-management-url",
    default=None,
    help="Optional declarative Stalwart management URL.",
)
@click.option("--headless", is_flag=True, help="Persist headless launch as the default posture.")
@click.option("--no-gateway", is_flag=True, help="Persist gateway auto-attach disabled.")
@click.option(
    "--managed-header/--no-managed-header",
    "managed_header",
    default=None,
    help="Persist managed prompt header policy for launches from this easy profile.",
)
@click.option(
    "--gateway-port",
    type=click.IntRange(1, 65535),
    default=None,
    help="Persist one fixed loopback gateway port for launches from this profile.",
)
@click.option(
    "--prompt-overlay-mode",
    type=click.Choice(("append", "replace")),
    default=None,
    help="Optional prompt-overlay mode.",
)
@click.option("--prompt-overlay-text", default=None, help="Inline prompt-overlay text.")
@click.option(
    "--prompt-overlay-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a prompt-overlay text file.",
)
def create_easy_profile_command(
    name: str,
    specialist: str,
    agent_name: str | None,
    agent_id: str | None,
    workdir: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    prompt_mode: str | None,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    headless: bool,
    no_gateway: bool,
    managed_header: bool | None,
    gateway_port: int | None,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
) -> None:
    """Create one specialist-backed easy profile."""

    overlay = _ensure_project_overlay()
    payload = _store_launch_profile_from_cli(
        overlay=overlay,
        profile_name=_require_non_empty_name(name, field_name="--name"),
        profile_lane="easy_profile",
        source_kind="specialist",
        source_name=_require_non_empty_name(specialist, field_name="--specialist"),
        agent_name=agent_name,
        agent_id=agent_id,
        workdir=workdir,
        auth=auth,
        model=model,
        reasoning_level=reasoning_level,
        prompt_mode=prompt_mode,
        env_set=env_set,
        mail_transport=mail_transport,
        mail_principal_id=mail_principal_id,
        mail_address=mail_address,
        mail_root=mail_root,
        mail_base_url=mail_base_url,
        mail_jmap_url=mail_jmap_url,
        mail_management_url=mail_management_url,
        headless=headless,
        clear_headless=False,
        no_gateway=no_gateway,
        managed_header=managed_header,
        clear_managed_header=False,
        gateway_port=gateway_port,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        prompt_overlay_file=prompt_overlay_file,
        clear_prompt_overlay=False,
        clear_mailbox=False,
        clear_env=False,
        clear_agent_name=False,
        clear_agent_id=False,
        clear_workdir=False,
        clear_auth=False,
        clear_model=False,
        clear_reasoning_level=False,
        clear_prompt_mode=False,
        existing_name=None,
    )
    emit(payload)


@easy_profile_group.command(name="list")
def list_easy_profiles_command() -> None:
    """List persisted project-local easy profiles."""

    overlay = _resolve_existing_project_overlay()
    profiles = [
        _launch_profile_payload_from_resolved(overlay=overlay, resolved=profile)
        for profile in list_resolved_launch_profiles(overlay=overlay)
        if profile.entry.profile_lane == "easy_profile"
    ]
    emit({"project_root": str(overlay.project_root), "profiles": profiles})


@easy_profile_group.command(name="get")
@click.option("--name", required=True, help="Easy profile name.")
def get_easy_profile_command(name: str) -> None:
    """Inspect one persisted easy profile definition."""

    overlay = _resolve_existing_project_overlay()
    emit(
        _launch_profile_payload(
            overlay=overlay,
            profile_name=_require_non_empty_name(name, field_name="--name"),
            expected_lane="easy_profile",
        )
    )


@easy_profile_group.command(name="remove")
@click.option("--name", required=True, help="Easy profile name.")
def remove_easy_profile_command(name: str) -> None:
    """Remove one persisted easy profile definition."""

    overlay = _resolve_existing_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    try:
        metadata_path = remove_profile_metadata(overlay=overlay, name=profile_name)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "project_root": str(overlay.project_root),
            "name": profile_name,
            "removed": True,
            "metadata_path": str(metadata_path),
            "path": str(
                (overlay.agents_root / "launch-profiles" / f"{profile_name}.yaml").resolve()
            ),
        }
    )


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
@click.option("--setup", default="default", show_default=True, help="Preset setup name.")
@click.option("--credential", default=None, help="Credential bundle name.")
@click.option("--api-key", default=None, help="Common API key input for the selected tool.")
@click.option(
    "--base-url", default=None, help="Common base URL input for the selected tool when supported."
)
@click.option("--claude-auth-token", default=None, help="Optional Claude auth token input.")
@click.option("--claude-oauth-token", default=None, help="Optional Claude OAuth token input.")
@click.option("--model", default=None, help="Optional launch-owned default model name.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(1, 10),
    default=None,
    help="Optional Houmao-defined launch-owned reasoning level (1..10).",
)
@click.option(
    "--claude-model",
    default=None,
    help="Compatibility alias for `--model` on Claude specialists.",
)
@click.option(
    "--claude-state-template-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Optional Claude bootstrap state template JSON file (not a credential).",
)
@click.option(
    "--claude-config-dir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    default=None,
    help=(
        "Optional Claude config dir to import vendor login state from "
        "(`.credentials.json` plus companion `.claude.json` when present)."
    ),
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
    setup: str,
    credential: str | None,
    api_key: str | None,
    base_url: str | None,
    claude_auth_token: str | None,
    claude_oauth_token: str | None,
    model: str | None,
    reasoning_level: int | None,
    claude_model: str | None,
    claude_state_template_file: Path | None,
    claude_config_dir: Path | None,
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

    overlay = _ensure_project_overlay()
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
    existing_specialist = (
        load_specialist(overlay=overlay, name=specialist_name)
        if ProjectCatalog.from_overlay(overlay).specialist_exists(specialist_name)
        else None
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
    setup_name = _require_non_empty_name(setup, field_name="--setup")
    setup_path = _tool_setup_path(overlay=overlay, tool=tool_name, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Setup bundle not found: {setup_path}")
    adapter = _load_overlay_tool_adapter(overlay=overlay, tool=tool_name)
    persistent_env_records = _parse_specialist_env_records_or_click(
        adapter=adapter,
        env_set=env_set,
    )
    if model is not None and claude_model is not None:
        raise click.ClickException("`--model` cannot be combined with `--claude-model`.")
    if claude_model is not None and tool_name != "claude":
        raise click.ClickException("`--claude-model` is only supported with `--tool claude`.")
    resolved_model_name = _resolve_model_name_or_click(model or claude_model)
    resolved_model_config = _build_model_config_or_click(
        model_name=resolved_model_name,
        reasoning_level=reasoning_level,
    )
    auth_result = _ensure_specialist_auth_bundle(
        overlay=overlay,
        tool=tool_name,
        credential_name=credential_name,
        api_key=api_key,
        base_url=base_url,
        claude_auth_token=claude_auth_token,
        claude_oauth_token=claude_oauth_token,
        claude_state_template_file=claude_state_template_file,
        claude_config_dir=claude_config_dir,
        codex_org_id=codex_org_id,
        codex_auth_json=codex_auth_json,
        google_api_key=google_api_key,
        use_vertex_ai=use_vertex_ai,
        gemini_oauth_creds=gemini_oauth_creds,
    )
    prompt_mode = (
        "as_is" if no_unattended or tool_name not in {"claude", "codex", "gemini"} else "unattended"
    )
    launch_mapping: dict[str, Any] = {"prompt_mode": prompt_mode}
    model_payload = _model_mapping_payload(resolved_model_config)
    if model_payload is not None:
        launch_mapping["model"] = model_payload
    if persistent_env_records:
        launch_mapping["env_records"] = dict(persistent_env_records)

    role_root = _role_root(overlay=overlay, role_name=specialist_name)
    preset_name = _canonical_preset_name(
        role_name=specialist_name,
        tool=tool_name,
        setup=setup_name,
    )
    if replace_conflict is not None:
        _prepare_specialist_projection_for_replace(
            role_root=role_root,
            preset_path=(
                existing_specialist.resolved_preset_path(overlay)
                if existing_specialist is not None
                else _preset_path(overlay=overlay, preset_name=preset_name)
            ),
        )
    system_prompt_path = _write_role_prompt(
        role_root=role_root,
        prompt_text=prompt_text,
        overwrite=replace_conflict is not None,
    )
    preset_path = _write_named_preset(
        overlay=overlay,
        preset_name=preset_name,
        role_name=specialist_name,
        tool=tool_name,
        setup=setup_name,
        skills=[skill_path.name for skill_path in imported_skills],
        auth=credential_name,
        prompt_mode=prompt_mode,
        model_config=resolved_model_config,
        env_records=persistent_env_records,
        overwrite=replace_conflict is not None,
    )
    metadata = ProjectCatalog.from_overlay(overlay).store_specialist_from_sources(
        name=specialist_name,
        preset_name=preset_name,
        tool=tool_name,
        provider=TOOL_PROVIDER_MAP[tool_name],
        credential_name=credential_name,
        role_name=specialist_name,
        setup_name=setup_name,
        prompt_path=system_prompt_path,
        auth_path=_auth_bundle_root(overlay=overlay, tool=tool_name, name=credential_name),
        skill_paths=tuple(imported_skills),
        setup_path=setup_path,
        launch_mapping=launch_mapping,
        mailbox_mapping=None,
        extra_mapping=None,
    )
    metadata_path = metadata.metadata_path or overlay.catalog_path
    emit(
        {
            "project_root": str(overlay.project_root),
            "specialist": specialist_name,
            "tool": tool_name,
            "setup": setup_name,
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

    overlay = _resolve_existing_project_overlay()
    emit(
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

    overlay = _resolve_existing_project_overlay()
    specialist = _load_specialist_or_click(overlay=overlay, name=name)
    emit(_specialist_payload(overlay=overlay, metadata=specialist))


@easy_specialist_group.command(name="remove")
@click.option("--name", required=True, help="Specialist name.")
def remove_easy_specialist_command(name: str) -> None:
    """Remove one persisted specialist definition and its generated role subtree."""

    overlay = _resolve_existing_project_overlay()
    specialist = _load_specialist_or_click(overlay=overlay, name=name)
    metadata_path = _remove_specialist_metadata_or_click(overlay=overlay, name=specialist.name)
    emit(
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
@click.option("--specialist", default=None, help="Specialist name.")
@click.option("--profile", default=None, help="Easy profile name.")
@click.option("--name", default=None, help="Managed-agent instance name.")
@click.option("--auth", default=None, help="Optional auth override for the compiled preset.")
@click.option("--model", default=None, help="Optional one-off launch-owned model override.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(1, 10),
    default=None,
    help="Optional one-off Houmao-defined reasoning override (1..10).",
)
@click.option("--session-name", default=None, help="Optional tmux session name.")
@click.option(
    "--headless/--no-headless",
    default=None,
    help="Override detached launch posture.",
)
@click.option(
    "--no-gateway",
    is_flag=True,
    help="Skip the default launch-time gateway attach for this instance.",
)
@click.option(
    "--gateway-port",
    type=click.IntRange(1, 65535),
    default=None,
    help="Request one fixed loopback gateway listener port for this launch.",
)
@click.option(
    "--gateway-background",
    is_flag=True,
    help="Run the auto-attached gateway as a detached background process for this launch.",
)
@click.option(
    "--workdir",
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    default=None,
    help="Optional runtime working directory override; defaults to the invocation cwd.",
)
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
@click.option(
    "--managed-header/--no-managed-header",
    "managed_header",
    default=None,
    help="Force-enable or disable the Houmao-managed prompt header for this launch.",
)
@click.option(
    "--append-system-prompt-text",
    default=None,
    help="Inline launch-owned system-prompt appendix for this launch only.",
)
@click.option(
    "--append-system-prompt-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a launch-owned system-prompt appendix file for this launch only.",
)
@managed_launch_force_option
def launch_easy_instance_command(
    specialist: str | None,
    profile: str | None,
    name: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    session_name: str | None,
    headless: bool | None,
    no_gateway: bool,
    gateway_port: int | None,
    gateway_background: bool,
    workdir: Path | None,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_root: Path | None,
    mail_account_dir: Path | None,
    managed_header: bool | None,
    append_system_prompt_text: str | None,
    append_system_prompt_file: Path | None,
    force_mode: str | None,
) -> None:
    """Launch one managed-agent instance from a compiled specialist definition."""

    overlay = _ensure_project_overlay()
    if specialist is not None and profile is not None:
        raise click.ClickException("`--specialist` and `--profile` cannot be combined.")
    if specialist is None and profile is None:
        raise click.ClickException("Provide exactly one of `--specialist` or `--profile`.")

    resolved_profile = None
    declared_mailbox = None
    operator_prompt_mode: OperatorPromptMode | None = None
    persistent_env_records: dict[str, str] | None = None
    launch_profile_model_config: ModelConfig | None = None
    prompt_overlay_mode = None
    prompt_overlay_text = None
    launch_appendix_text = _resolve_launch_appendix_text_or_click(
        appendix_text=append_system_prompt_text,
        appendix_file=append_system_prompt_file,
    )
    launch_profile_managed_header_policy: ManagedHeaderPolicy | None = None
    launch_profile_provenance = None
    direct_model_config = _build_model_config_or_click(
        model_name=_resolve_model_name_or_click(model),
        reasoning_level=reasoning_level,
    )
    default_gateway_auto_attach = True
    default_gateway_host: str | None = "127.0.0.1"
    default_gateway_port: int | None = 0
    if profile is not None:
        resolved_profile = _load_launch_profile_or_click(
            overlay=overlay,
            name=_require_non_empty_name(profile, field_name="--profile"),
            expected_lane="easy_profile",
        )
        if resolved_profile.specialist is None or not resolved_profile.source_exists:
            raise click.ClickException(
                f"Easy profile `{resolved_profile.entry.name}` references unavailable specialist "
                f"`{resolved_profile.entry.source_name}`."
            )
        specialist_metadata = resolved_profile.specialist
        declared_mailbox = _stored_mailbox_or_click(
            resolved_profile.entry.mailbox_payload,
            source=f"easy profile `{resolved_profile.entry.name}`",
        )
        operator_prompt_mode = _resolve_operator_prompt_mode_or_click(
            resolved_profile.entry.operator_prompt_mode,
            source=f"easy profile `{resolved_profile.entry.name}`",
        )
        persistent_env_records = dict(resolved_profile.entry.env_payload)
        launch_profile_model_config = _build_model_config_or_click(
            model_name=resolved_profile.entry.model_name,
            reasoning_level=resolved_profile.entry.reasoning_level,
        )
        launch_profile_managed_header_policy = resolved_profile.entry.managed_header_policy
        prompt_overlay_mode = resolved_profile.entry.prompt_overlay_mode
        prompt_overlay_text = resolved_profile.prompt_overlay_text
        launch_profile_provenance = _launch_profile_provenance_payload(resolved_profile)
        posture_payload = dict(resolved_profile.entry.posture_payload)
        if posture_payload.get("gateway_auto_attach") is False:
            default_gateway_auto_attach = False
            default_gateway_port = None
            default_gateway_host = None
        if posture_payload.get("gateway_port") is not None:
            default_gateway_auto_attach = True
            default_gateway_port = int(posture_payload["gateway_port"])
            default_gateway_host = str(posture_payload.get("gateway_host") or "127.0.0.1")
        resolved_headless = (
            headless if headless is not None else bool(posture_payload.get("headless", False))
        )
        resolved_name = _optional_non_empty_value(name) or resolved_profile.entry.managed_agent_name
        if resolved_name is None:
            raise click.ClickException(
                "`project easy instance launch --profile` requires `--name` unless the selected "
                "profile stores a default managed-agent name."
            )
        resolved_auth = _optional_non_empty_value(auth) or resolved_profile.entry.auth_name
        working_directory = (
            Path(resolved_profile.entry.workdir).expanduser().resolve()
            if workdir is None and resolved_profile.entry.workdir is not None
            else (workdir or Path.cwd()).resolve()
        )
    else:
        assert specialist is not None
        specialist_metadata = _load_specialist_or_click(
            overlay=overlay,
            name=_require_non_empty_name(specialist, field_name="--specialist"),
        )
        resolved_headless = bool(headless)
        resolved_name = _optional_non_empty_value(name)
        if resolved_name is None:
            raise click.ClickException(
                "`project easy instance launch --specialist` requires `--name`."
            )
        resolved_auth = _optional_non_empty_value(auth)
        working_directory = (workdir or Path.cwd()).resolve()

    if specialist_metadata.tool == "gemini" and not resolved_headless:
        raise click.ClickException(
            "Gemini specialists are currently headless-only. Use `--headless`."
        )
    if no_gateway and gateway_port is not None:
        raise click.ClickException("`--no-gateway` and `--gateway-port` cannot be combined.")
    if no_gateway and gateway_background:
        raise click.ClickException("`--no-gateway` and `--gateway-background` cannot be combined.")
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
    source_agent_def_dir = materialize_project_agent_catalog_projection(overlay)
    launch_env_overrides = _resolve_instance_env_set_or_click(env_set)
    gateway_auto_attach = default_gateway_auto_attach
    requested_gateway_port = default_gateway_port if gateway_auto_attach else None
    gateway_host = default_gateway_host if gateway_auto_attach else None
    if no_gateway:
        gateway_auto_attach = False
        requested_gateway_port = None
        gateway_host = None
    elif gateway_port is not None:
        gateway_auto_attach = True
        requested_gateway_port = gateway_port
        gateway_host = default_gateway_host or "127.0.0.1"
    elif gateway_background:
        gateway_auto_attach = True
        if requested_gateway_port is None:
            requested_gateway_port = 0
        if gateway_host is None:
            gateway_host = "127.0.0.1"
    requested_gateway_port = (
        requested_gateway_port
        if requested_gateway_port is not None
        else 0
        if gateway_auto_attach
        else None
    )
    gateway_execution_mode: GatewayCurrentExecutionMode | None = (
        "detached_process"
        if gateway_auto_attach and gateway_background
        else "tmux_auxiliary_window"
        if gateway_auto_attach
        else None
    )

    launch_result = launch_managed_agent_locally(
        agents=str(specialist_metadata.resolved_preset_path(overlay)),
        agent_name=resolved_name,
        agent_id=None,
        auth=resolved_auth,
        session_name=_optional_non_empty_value(session_name),
        headless=resolved_headless,
        provider=specialist_metadata.provider,
        working_directory=working_directory,
        source_working_directory=overlay.project_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        launch_env_overrides=launch_env_overrides,
        gateway_auto_attach=gateway_auto_attach,
        gateway_host=gateway_host,
        gateway_port=requested_gateway_port,
        gateway_execution_mode=gateway_execution_mode,
        mailbox_transport=mail_transport,
        mailbox_root=mail_root.resolve() if mail_root is not None else None,
        mailbox_account_dir=(mail_account_dir.resolve() if mail_account_dir is not None else None),
        declared_mailbox=declared_mailbox,
        operator_prompt_mode=operator_prompt_mode,
        persistent_env_records=persistent_env_records,
        launch_profile_model_config=launch_profile_model_config,
        direct_model_config=direct_model_config,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        launch_appendix_text=launch_appendix_text,
        managed_header_override=managed_header,
        launch_profile_managed_header_policy=launch_profile_managed_header_policy,
        launch_profile_provenance=launch_profile_provenance,
        force_mode=force_mode,
    )
    emit_local_launch_completion(
        launch_result=launch_result,
        agent_name=resolved_name,
        session_name=session_name,
        headless=resolved_headless,
    )


@easy_instance_group.command(name="list")
def list_easy_instances_command() -> None:
    """List project-local managed agents as specialist instances when resolvable."""

    roots = _resolve_existing_project_roots()
    overlay = roots.project_overlay
    assert overlay is not None
    specialists_by_name = {
        metadata.name: metadata for metadata in list_specialists(overlay=overlay)
    }
    instances = _list_project_instances(overlay=overlay, specialists_by_name=specialists_by_name)
    emit(
        {
            "project_root": str(overlay.project_root),
            "selected_overlay_root": str(roots.overlay_root),
            "selected_overlay_detail": _selected_overlay_detail(roots),
            "instances": instances,
        }
    )


@easy_instance_group.command(name="get")
@click.option("--name", required=True, help="Managed-agent instance name.")
def get_easy_instance_command(name: str) -> None:
    """Inspect one managed-agent instance through the selected project overlay."""

    roots = _resolve_existing_project_roots()
    overlay = roots.project_overlay
    assert overlay is not None
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
            f"Managed agent `{name}` does not belong to the selected project overlay."
        )
    emit(
        {
            **_instance_payload(
                overlay=overlay,
                identity_payload=identity.model_dump(mode="json"),
                manifest_payload=manifest_payload,
                specialists_by_name=specialists_by_name,
            ),
            "selected_overlay_root": str(roots.overlay_root),
            "selected_overlay_detail": _selected_overlay_detail(roots),
        }
    )


@easy_instance_group.command(name="stop")
@click.option("--name", required=True, help="Managed-agent instance name.")
def stop_easy_instance_command(name: str) -> None:
    """Stop one managed-agent instance through the selected project overlay."""

    roots = _resolve_existing_project_roots()
    overlay = roots.project_overlay
    assert overlay is not None
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
            f"Managed agent `{name}` does not belong to the selected project overlay."
        )
    action_payload = stop_managed_agent(target).model_dump(mode="json")
    emit(
        {
            **action_payload,
            "selected_overlay_root": str(roots.overlay_root),
            "selected_overlay_detail": _selected_overlay_detail(roots),
        }
    )


@project_group.group(name="mailbox")
def project_mailbox_group() -> None:
    """Operate on `mailbox/` under the selected project overlay."""


@project_mailbox_group.command(name="init")
def init_project_mailbox_command() -> None:
    """Bootstrap or validate `mailbox/` under the selected project overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(_project_mailbox_payload(roots=roots, payload=init_mailbox_root(roots.mailbox_root)))


@project_mailbox_group.command(name="status")
def status_project_mailbox_command() -> None:
    """Inspect `mailbox/` under the selected project overlay."""

    roots = _resolve_existing_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots, payload=mailbox_root_status_payload(roots.mailbox_root)
        )
    )


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
    """Register one mailbox address under `mailbox/` in the selected project overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots,
            payload=register_mailbox_at_root(
                mailbox_root=roots.mailbox_root,
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
    """Deactivate or purge one mailbox address under `mailbox/` in the selected overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots,
            payload=unregister_mailbox_at_root(
                mailbox_root=roots.mailbox_root,
                address=address,
                mode=mode,
            ),
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
    """Repair `mailbox/` under the selected project overlay."""

    roots = _ensure_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots,
            payload=repair_mailbox_root(
                mailbox_root=roots.mailbox_root,
                cleanup_staging=cleanup_staging,
                quarantine_staging=quarantine_staging,
            ),
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
    """Clean inactive or stashed registrations under `mailbox/` in the selected overlay."""

    roots = _ensure_project_mailbox_roots()
    emit_cleanup_payload(
        _project_mailbox_payload(
            roots=roots,
            payload=cleanup_mailbox_root(
                mailbox_root=roots.mailbox_root,
                inactive_older_than_seconds=inactive_older_than_seconds,
                stashed_older_than_seconds=stashed_older_than_seconds,
                dry_run=dry_run,
            ),
        )
    )


@project_mailbox_group.group(name="accounts")
def project_mailbox_accounts_group() -> None:
    """Inspect mailbox registrations under `mailbox/` in the selected overlay."""


@project_mailbox_accounts_group.command(name="list")
def list_project_mailbox_accounts_command() -> None:
    """List mailbox accounts under `mailbox/` in the selected overlay."""

    roots = _resolve_existing_project_mailbox_roots()
    emit(
        _project_mailbox_payload(
            roots=roots, payload=list_mailbox_accounts(mailbox_root=roots.mailbox_root)
        )
    )


@project_mailbox_accounts_group.command(name="get")
@click.option("--address", required=True, help="Full mailbox address.")
def get_project_mailbox_account_command(address: str) -> None:
    """Inspect one mailbox account under `mailbox/` in the selected overlay."""

    roots = _resolve_existing_project_mailbox_roots()
    try:
        payload = get_mailbox_account(mailbox_root=roots.mailbox_root, address=address)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_mailbox_payload(roots=roots, payload=payload))


@project_mailbox_group.group(name="messages")
def project_mailbox_messages_group() -> None:
    """Inspect structural message projections under `mailbox/` in the selected overlay."""


@project_mailbox_messages_group.command(name="list")
@click.option("--address", required=True, help="Full mailbox address.")
def list_project_mailbox_messages_command(address: str) -> None:
    """List structurally projected messages for one project-local mailbox address."""

    roots = _resolve_existing_project_mailbox_roots()
    try:
        payload = list_mailbox_messages(mailbox_root=roots.mailbox_root, address=address)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_mailbox_payload(roots=roots, payload=payload))


@project_mailbox_messages_group.command(name="get")
@click.option("--address", required=True, help="Full mailbox address.")
@click.option("--message-id", required=True, help="Canonical mailbox message id.")
def get_project_mailbox_message_command(address: str, message_id: str) -> None:
    """Get one structurally projected message for a project-local mailbox address."""

    roots = _resolve_existing_project_mailbox_roots()
    try:
        payload = get_mailbox_message(
            mailbox_root=roots.mailbox_root,
            address=address,
            message_id=message_id,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_mailbox_payload(roots=roots, payload=payload))


def _ensure_project_mailbox_roots() -> ProjectAwareLocalRoots:
    """Return ensured project roots for stateful project-mailbox commands."""

    return _ensure_project_roots()


def _resolve_existing_project_mailbox_roots() -> ProjectAwareLocalRoots:
    """Return existing project roots for non-creating project-mailbox commands."""

    return _resolve_existing_project_roots(fallback_label="shared mailbox root")


def _project_mailbox_payload(
    *,
    roots: ProjectAwareLocalRoots,
    payload: dict[str, object],
) -> dict[str, object]:
    """Extend one project-mailbox payload with selected-overlay wording fields."""

    return {
        **payload,
        "selected_overlay_root": str(roots.overlay_root),
        "selected_overlay_detail": _selected_overlay_detail(roots),
        "mailbox_root_detail": "Selected `mailbox/` under the selected project overlay.",
        "project_overlay_bootstrapped": roots.created_overlay,
        "overlay_bootstrap_detail": describe_overlay_bootstrap(
            created_overlay=roots.created_overlay,
            overlay_exists=roots.project_overlay is not None,
        ),
    }


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


def _emit_tool_auth_list(*, tool: str) -> None:
    """Emit the auth-bundle names for one supported tool."""

    overlay = _resolve_existing_project_overlay()
    emit(
        {
            "project_root": str(overlay.project_root),
            "tool": tool,
            "credentials": _list_tool_bundle_names(overlay=overlay, tool=tool),
        }
    )


def _emit_tool_auth_get(*, tool: str, name: str) -> None:
    """Emit one structured auth-bundle description."""

    overlay = _resolve_existing_project_overlay()
    emit(_describe_project_auth_bundle(overlay=overlay, tool=tool, name=name))


def _emit_tool_auth_remove(*, tool: str, name: str) -> None:
    """Remove one named auth bundle and emit the removal payload."""

    overlay = _resolve_existing_project_overlay()
    resolved_name = _require_non_empty_name(name, field_name="--name")
    target_path = _auth_bundle_root(overlay=overlay, tool=tool, name=resolved_name)
    if not target_path.is_dir():
        raise click.ClickException(f"Auth bundle not found: {target_path}")
    shutil.rmtree(target_path)
    emit(
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


def _presets_root(*, overlay: HoumaoProjectOverlay) -> Path:
    """Return the project-local named preset root."""

    ensure_project_agent_compatibility_tree(overlay)
    return (overlay.agents_root / "presets").resolve()


def _preset_path(*, overlay: HoumaoProjectOverlay, preset_name: str) -> Path:
    """Return one canonical project-local named preset path."""

    return (_presets_root(overlay=overlay) / f"{preset_name}.yaml").resolve()


def _list_role_names(*, overlay: HoumaoProjectOverlay) -> list[str]:
    """Return the current project-local role names."""

    ensure_project_agent_compatibility_tree(overlay)
    roles_root = (overlay.agents_root / "roles").resolve()
    if not roles_root.is_dir():
        return []
    return sorted(path.name for path in roles_root.iterdir() if path.is_dir())


def _role_summary(
    *,
    overlay: HoumaoProjectOverlay,
    role_name: str,
    include_prompt: bool = False,
) -> dict[str, object]:
    """Return one structured project-local role summary."""

    role_root = _role_root(overlay=overlay, role_name=role_name)
    prompt_path = (role_root / "system-prompt.md").resolve()
    payload: dict[str, object] = {
        "name": role_name,
        "role_path": str(role_root),
        "system_prompt_path": str(prompt_path),
        "system_prompt_exists": prompt_path.is_file(),
        "recipes": _list_named_preset_summaries(overlay=overlay, role_name=role_name),
    }
    if include_prompt:
        payload["system_prompt_text"] = (
            prompt_path.read_text(encoding="utf-8").rstrip() if prompt_path.is_file() else ""
        )
    return payload


def _list_named_preset_summaries(
    *,
    overlay: HoumaoProjectOverlay,
    role_name: str | None = None,
    tool: str | None = None,
) -> list[dict[str, object]]:
    """Return named preset summaries, optionally filtered by role and tool."""

    presets_root = _presets_root(overlay=overlay)
    if not presets_root.is_dir():
        return []
    results: list[dict[str, object]] = []
    for preset_file in sorted(path for path in presets_root.iterdir() if path.is_file()):
        if preset_file.suffix not in {".yaml", ".yml"}:
            continue
        parsed_preset = parse_agent_preset(preset_file)
        if role_name is not None and parsed_preset.role_name != role_name:
            continue
        if tool is not None and parsed_preset.tool != tool:
            continue
        results.append(_preset_summary(overlay=overlay, preset_name=parsed_preset.name))
    return results


def _preset_summary(
    *,
    overlay: HoumaoProjectOverlay,
    preset_name: str,
) -> dict[str, object]:
    """Return one structured project-local preset summary."""

    preset_file = _preset_path(overlay=overlay, preset_name=preset_name)
    if not preset_file.is_file():
        raise click.ClickException(f"Preset not found: {preset_file}")
    parsed_preset = parse_agent_preset(preset_file)
    raw_payload = _load_yaml_mapping(preset_file)
    launch_payload = raw_payload.get("launch")
    return {
        "name": parsed_preset.name,
        "role": parsed_preset.role_name,
        "tool": parsed_preset.tool,
        "setup": parsed_preset.setup,
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


def _canonical_preset_name(*, role_name: str, tool: str, setup: str) -> str:
    """Return the default deterministic preset name for one role/tool/setup tuple."""

    return f"{role_name}-{tool}-{setup}"


def _ensure_role_exists(*, overlay: HoumaoProjectOverlay, role_name: str) -> None:
    """Fail clearly when one project-local role root is missing."""

    role_root = _role_root(overlay=overlay, role_name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Role not found: {role_root}")


def _ensure_unique_preset_tuple(
    *,
    overlay: HoumaoProjectOverlay,
    preset_name: str,
    role_name: str,
    tool: str,
    setup: str,
) -> None:
    """Reject duplicate `(role, tool, setup)` tuples across named presets."""

    for summary in _list_named_preset_summaries(overlay=overlay):
        if str(summary["name"]) == preset_name:
            continue
        if (
            str(summary["role"]) == role_name
            and str(summary["tool"]) == tool
            and str(summary["setup"]) == setup
        ):
            raise click.ClickException(
                "Recipe `(role, tool, setup)` tuples must remain unique across "
                f"`.houmao/agents/presets/`: `{role_name}`, `{tool}`, `{setup}` is already "
                f"owned by `{summary['name']}`."
            )


def _write_named_preset(
    *,
    overlay: HoumaoProjectOverlay,
    preset_name: str,
    role_name: str,
    tool: str,
    setup: str,
    skills: list[str],
    auth: str | None,
    prompt_mode: str | None,
    model_config: ModelConfig | None = None,
    env_records: dict[str, str] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write one canonical project-local named preset."""

    _ensure_role_exists(overlay=overlay, role_name=role_name)
    preset_file = _preset_path(overlay=overlay, preset_name=preset_name)
    if preset_file.exists() and not overwrite:
        raise click.ClickException(f"Preset already exists: {preset_file}")
    _ensure_unique_preset_tuple(
        overlay=overlay,
        preset_name=preset_name,
        role_name=role_name,
        tool=tool,
        setup=setup,
    )
    resolved_prompt_mode = prompt_mode or "unattended"
    payload: dict[str, Any] = {
        "role": role_name,
        "tool": tool,
        "setup": setup,
        "skills": list(skills),
    }
    if auth is not None:
        payload["auth"] = auth
    payload["launch"] = {"prompt_mode": resolved_prompt_mode}
    model_payload = _model_mapping_payload(model_config)
    if model_payload is not None:
        payload["launch"]["model"] = model_payload
    if env_records:
        payload["launch"]["env_records"] = dict(env_records)
    _write_yaml_mapping(preset_file, payload)
    return preset_file


def _prepare_specialist_projection_for_replace(*, role_root: Path, preset_path: Path) -> None:
    """Clear specialist-owned generated projection paths before one replacement write."""

    if not role_root.exists():
        preset_path.unlink(missing_ok=True)
        return
    prompt_path = (role_root / "system-prompt.md").resolve()
    if prompt_path.is_dir():
        raise click.ClickException(f"Prompt path already exists as a directory: {prompt_path}")
    prompt_path.unlink(missing_ok=True)
    preset_path.unlink(missing_ok=True)


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
    oauth_token: str | None,
    base_url: str | None,
    model: str | None,
    small_fast_model: str | None,
    subagent_model: str | None,
    default_opus_model: str | None,
    default_sonnet_model: str | None,
    default_haiku_model: str | None,
    state_template_file: Path | None,
    config_dir: Path | None,
    clear_env_names: set[str],
    clear_file_sources: set[str],
) -> None:
    """Create or update one Claude auth bundle under the active project overlay."""

    overlay = _ensure_project_overlay()
    env_values = _compact_env_values(
        {
            "ANTHROPIC_API_KEY": api_key,
            "ANTHROPIC_AUTH_TOKEN": auth_token,
            "CLAUDE_CODE_OAUTH_TOKEN": oauth_token,
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_MODEL": model,
            "ANTHROPIC_SMALL_FAST_MODEL": small_fast_model,
            "CLAUDE_CODE_SUBAGENT_MODEL": subagent_model,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": default_opus_model,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": default_sonnet_model,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": default_haiku_model,
        }
    )
    file_sources = _claude_auth_file_sources(
        state_template_file=state_template_file,
        config_dir=config_dir,
    )
    effective_clear_file_sources = set(clear_file_sources)
    if config_dir is not None:
        effective_clear_file_sources.update(_CLAUDE_VENDOR_LOGIN_FILE_SOURCES)
    emit(
        _write_project_auth_bundle(
            overlay=overlay,
            tool="claude",
            name=name,
            env_values=env_values,
            file_sources=file_sources,
            require_any_input=True,
            operation=operation,
            clear_env_names=clear_env_names,
            clear_file_sources=effective_clear_file_sources,
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
    """Create or update one Codex auth bundle under the active project overlay."""

    overlay = _ensure_project_overlay()
    env_values = _compact_env_values(
        {
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "OPENAI_ORG_ID": org_id,
        }
    )
    emit(
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
    base_url: str | None,
    google_api_key: str | None,
    use_vertex_ai: bool,
    oauth_creds: Path | None,
    clear_env_names: set[str],
) -> None:
    """Create or update one Gemini auth bundle under the active project overlay."""

    overlay = _ensure_project_overlay()
    env_values = _compact_env_values(
        {
            "GEMINI_API_KEY": api_key,
            "GOOGLE_GEMINI_BASE_URL": base_url,
            "GOOGLE_API_KEY": google_api_key,
            "GOOGLE_GENAI_USE_VERTEXAI": "true" if use_vertex_ai else None,
        }
    )
    emit(
        _write_project_auth_bundle(
            overlay=overlay,
            tool="gemini",
            name=name,
            env_values=env_values,
            file_sources={"oauth_creds.json": oauth_creds} if oauth_creds is not None else {},
            require_any_input=True,
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
    claude_oauth_token: str | None,
    claude_state_template_file: Path | None,
    claude_config_dir: Path | None,
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
                "CLAUDE_CODE_OAUTH_TOKEN": claude_oauth_token,
                "ANTHROPIC_BASE_URL": base_url,
            }
        )
        file_sources = _claude_auth_file_sources(
            state_template_file=claude_state_template_file,
            config_dir=claude_config_dir,
        )
        clear_file_sources = (
            set(_CLAUDE_VENDOR_LOGIN_FILE_SOURCES) if claude_config_dir is not None else set()
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
        env_values = _compact_env_values(
            {
                "GEMINI_API_KEY": api_key,
                "GOOGLE_GEMINI_BASE_URL": base_url,
                "GOOGLE_API_KEY": google_api_key,
                "GOOGLE_GENAI_USE_VERTEXAI": "true" if use_vertex_ai else None,
            }
        )
        file_sources = (
            {"oauth_creds.json": gemini_oauth_creds} if gemini_oauth_creds is not None else {}
        )
        clear_file_sources = set()
    else:
        raise click.ClickException(f"Unsupported specialist tool `{tool}`.")
    if tool != "claude":
        clear_file_sources = set()

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
            clear_file_sources=clear_file_sources,
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
        clear_file_sources=clear_file_sources,
    )


def _claude_auth_file_sources(
    *,
    state_template_file: Path | None,
    config_dir: Path | None,
) -> dict[str, Path]:
    """Resolve Claude auth-bundle file sources from optional inputs."""

    file_sources: dict[str, Path] = {}
    if state_template_file is not None:
        file_sources[_CLAUDE_RUNTIME_STATE_TEMPLATE_FILENAME] = state_template_file
    file_sources.update(_resolve_claude_vendor_login_state_files(config_dir=config_dir))
    return file_sources


def _resolve_claude_vendor_login_state_files(*, config_dir: Path | None) -> dict[str, Path]:
    """Resolve Claude vendor login-state files from one config-root input."""

    if config_dir is None:
        return {}

    resolved_dir = config_dir.resolve()
    credentials_path = (resolved_dir / _CLAUDE_VENDOR_CREDENTIALS_FILENAME).resolve()
    if not credentials_path.is_file():
        raise click.ClickException(
            "Claude config dir does not contain the required vendor credential file "
            f"`{credentials_path}`."
        )

    file_sources: dict[str, Path] = {
        _CLAUDE_VENDOR_CREDENTIALS_FILENAME: credentials_path,
    }
    global_state_path = _find_claude_vendor_global_state_path(config_dir=resolved_dir)
    if global_state_path is not None:
        file_sources[_CLAUDE_VENDOR_GLOBAL_STATE_FILENAME] = global_state_path
    return file_sources


def _find_claude_vendor_global_state_path(*, config_dir: Path) -> Path | None:
    """Return the maintained Claude global-state file for one config-root when present."""

    candidates: list[Path] = [(config_dir / _CLAUDE_VENDOR_GLOBAL_STATE_FILENAME).resolve()]
    if config_dir.name == ".claude":
        candidates.append((config_dir.parent / _CLAUDE_VENDOR_GLOBAL_STATE_FILENAME).resolve())

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


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


def _load_recipe_or_click(*, overlay: HoumaoProjectOverlay, name: str) -> Any:
    """Load one project-local recipe or raise one operator-facing error."""

    recipe_name = _require_non_empty_name(name, field_name="--recipe")
    recipe_path = _preset_path(overlay=overlay, preset_name=recipe_name)
    if not recipe_path.is_file():
        raise click.ClickException(f"Recipe not found: {recipe_path}")
    try:
        return parse_agent_preset(recipe_path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _profile_lane_label(profile_lane: str) -> str:
    """Return one operator-facing launch-profile lane label."""

    if profile_lane == "easy_profile":
        return "easy-profile"
    if profile_lane == "launch_profile":
        return "launch-profile"
    return profile_lane


def _load_launch_profile_or_click(
    *,
    overlay: HoumaoProjectOverlay,
    name: str,
    expected_lane: str | None = None,
) -> Any:
    """Load one resolved launch profile or raise one operator-facing error."""

    try:
        resolved = resolve_launch_profile(overlay=overlay, name=name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if expected_lane is not None and resolved.entry.profile_lane != expected_lane:
        lane_label = _profile_lane_label(expected_lane)
        raise click.ClickException(
            f"Launch profile `{name}` is not an available `{lane_label}` definition."
        )
    return resolved


def _launch_profile_payload(
    *,
    overlay: HoumaoProjectOverlay,
    profile_name: str,
    expected_lane: str | None = None,
) -> dict[str, object]:
    """Return one operator-facing launch-profile payload."""

    resolved = _load_launch_profile_or_click(
        overlay=overlay,
        name=profile_name,
        expected_lane=expected_lane,
    )
    return _launch_profile_payload_from_resolved(overlay=overlay, resolved=resolved)


def _launch_profile_payload_from_resolved(
    *,
    overlay: HoumaoProjectOverlay,
    resolved: Any,
) -> dict[str, object]:
    """Return one operator-facing payload from a resolved launch profile."""

    payload: dict[str, object] = {
        "name": resolved.entry.name,
        "profile_lane": _profile_lane_label(resolved.entry.profile_lane),
        "source": launch_profile_source_payload(resolved),
        "defaults": launch_profile_defaults_payload(resolved),
        "path": str(resolved.entry.resolved_projection_path(overlay)),
        "metadata_path": str(resolved.entry.metadata_path)
        if resolved.entry.metadata_path is not None
        else None,
    }
    if resolved.entry.source_kind == "specialist":
        payload["specialist"] = resolved.entry.source_name
    if resolved.entry.source_kind == "recipe":
        payload["recipe"] = resolved.entry.source_name
    if resolved.tool is not None:
        payload["tool"] = resolved.tool
    return payload


def _list_launch_profile_payloads(
    *,
    overlay: HoumaoProjectOverlay,
    source_recipe: str | None = None,
    tool: str | None = None,
) -> list[dict[str, object]]:
    """Return explicit launch-profile payloads filtered by recipe or tool when requested."""

    results: list[dict[str, object]] = []
    for resolved in list_resolved_launch_profiles(overlay=overlay):
        if resolved.entry.profile_lane != "launch_profile":
            continue
        if source_recipe is not None and resolved.recipe_name != source_recipe:
            continue
        if tool is not None and resolved.tool != tool:
            continue
        results.append(_launch_profile_payload_from_resolved(overlay=overlay, resolved=resolved))
    return results


def _parse_launch_profile_env_records_or_click(
    *,
    adapter: ToolAdapter,
    env_set: tuple[str, ...],
    source_label: str,
) -> dict[str, str]:
    """Parse and validate persistent launch-profile env records."""

    try:
        parsed = parse_persistent_env_record_specs(env_set)
        return validate_persistent_env_records(
            parsed,
            auth_env_allowlist=adapter.auth_env_allowlist,
            source=source_label,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_prompt_overlay_text_or_click(
    *,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
) -> tuple[str | None, str | None]:
    """Resolve one optional prompt overlay from inline or file input."""

    if prompt_overlay_text is not None and prompt_overlay_file is not None:
        raise click.ClickException(
            "Provide at most one of `--prompt-overlay-text` or `--prompt-overlay-file`."
        )
    resolved_text = (
        prompt_overlay_text.strip()
        if prompt_overlay_text is not None
        else (
            prompt_overlay_file.read_text(encoding="utf-8").rstrip()
            if prompt_overlay_file is not None
            else None
        )
    )
    if resolved_text is not None and not resolved_text:
        raise click.ClickException("Prompt-overlay text must not be empty.")
    if prompt_overlay_mode is None and resolved_text is not None:
        raise click.ClickException(
            "Prompt-overlay text requires `--prompt-overlay-mode append|replace`."
        )
    if prompt_overlay_mode is not None and resolved_text is None:
        raise click.ClickException(
            "Prompt-overlay mode requires `--prompt-overlay-text` or `--prompt-overlay-file`."
        )
    return prompt_overlay_mode, resolved_text


def _resolve_launch_appendix_text_or_click(
    *,
    appendix_text: str | None,
    appendix_file: Path | None,
) -> str | None:
    """Resolve one launch-owned appendix from inline or file input."""

    if appendix_text is not None and appendix_file is not None:
        raise click.ClickException(
            "Provide at most one of `--append-system-prompt-text` or `--append-system-prompt-file`."
        )
    if appendix_text is not None:
        resolved_text = appendix_text.rstrip()
        return resolved_text if resolved_text.strip() else None
    if appendix_file is not None:
        resolved_text = appendix_file.read_text(encoding="utf-8").rstrip()
        return resolved_text if resolved_text.strip() else None
    return None


def _managed_header_policy_from_override(value: bool | None) -> ManagedHeaderPolicy | None:
    """Return one stored managed-header policy from a tri-state CLI override."""

    if value is None:
        return None
    return "enabled" if value else "disabled"


def _build_profile_mailbox_mapping_or_click(
    *,
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    source_label: str,
) -> dict[str, Any] | None:
    """Resolve one optional declarative mailbox mapping for launch-profile storage."""

    if mail_transport is None:
        provided = (
            mail_principal_id is not None
            or mail_address is not None
            or mail_root is not None
            or mail_base_url is not None
            or mail_jmap_url is not None
            or mail_management_url is not None
        )
        if provided:
            raise click.ClickException(
                "Mailbox fields require `--mail-transport filesystem|stalwart`."
            )
        return None

    payload: dict[str, Any] = {"transport": mail_transport}
    if mail_principal_id is not None:
        payload["principal_id"] = _require_non_empty_name(
            mail_principal_id, field_name="--mail-principal-id"
        )
    if mail_address is not None:
        payload["address"] = _require_non_empty_name(mail_address, field_name="--mail-address")
    if mail_transport == "filesystem":
        if (
            mail_base_url is not None
            or mail_jmap_url is not None
            or mail_management_url is not None
        ):
            raise click.ClickException(
                "Filesystem mailbox defaults do not accept Stalwart URL flags."
            )
        if mail_root is not None:
            payload["filesystem_root"] = mail_root.strip()
    else:
        if mail_root is not None:
            raise click.ClickException("Stalwart mailbox defaults do not accept `--mail-root`.")
        if mail_base_url is not None:
            payload["base_url"] = mail_base_url.strip()
        if mail_jmap_url is not None:
            payload["jmap_url"] = mail_jmap_url.strip()
        if mail_management_url is not None:
            payload["management_url"] = mail_management_url.strip()
    try:
        parsed = parse_declarative_mailbox_config(payload, source=source_label)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if parsed is None:
        return None
    return serialize_declarative_mailbox_config(parsed)


def _stored_mailbox_or_click(
    payload: dict[str, Any] | None,
    *,
    source: str,
) -> Any:
    """Parse one stored mailbox payload or raise one operator-facing error."""

    if payload is None:
        return None
    try:
        return parse_declarative_mailbox_config(payload, source=source)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_profile_posture_mapping(
    *,
    current: dict[str, Any] | None,
    headless: bool,
    clear_headless: bool,
    no_gateway: bool,
    gateway_port: int | None,
) -> dict[str, Any]:
    """Resolve one persisted launch-posture mapping."""

    if clear_headless and headless:
        raise click.ClickException("`--headless` cannot be combined with `--clear-headless`.")
    if no_gateway and gateway_port is not None:
        raise click.ClickException("`--no-gateway` and `--gateway-port` cannot be combined.")

    payload = dict(current or {})
    if clear_headless:
        payload.pop("headless", None)
    elif headless:
        payload["headless"] = True

    if no_gateway:
        payload["gateway_auto_attach"] = False
        payload.pop("gateway_host", None)
        payload.pop("gateway_port", None)
    elif gateway_port is not None:
        payload["gateway_auto_attach"] = True
        payload["gateway_host"] = "127.0.0.1"
        payload["gateway_port"] = gateway_port

    return payload


def _store_launch_profile_from_cli(
    *,
    overlay: HoumaoProjectOverlay,
    profile_name: str,
    profile_lane: str,
    source_kind: str,
    source_name: str,
    agent_name: str | None,
    agent_id: str | None,
    workdir: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    prompt_mode: str | None,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_principal_id: str | None,
    mail_address: str | None,
    mail_root: str | None,
    mail_base_url: str | None,
    mail_jmap_url: str | None,
    mail_management_url: str | None,
    headless: bool,
    clear_headless: bool,
    no_gateway: bool,
    managed_header: bool | None,
    clear_managed_header: bool,
    gateway_port: int | None,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
    clear_prompt_overlay: bool,
    clear_mailbox: bool,
    clear_env: bool,
    clear_agent_name: bool,
    clear_agent_id: bool,
    clear_workdir: bool,
    clear_auth: bool,
    clear_model: bool,
    clear_reasoning_level: bool,
    clear_prompt_mode: bool,
    existing_name: str | None,
) -> dict[str, object]:
    """Create or update one catalog-backed launch profile from CLI inputs."""

    catalog = ProjectCatalog.from_overlay(overlay)
    current = (
        _load_launch_profile_or_click(
            overlay=overlay,
            name=existing_name,
            expected_lane=profile_lane,
        )
        if existing_name is not None
        else None
    )
    if existing_name is None:
        try:
            catalog.load_launch_profile(profile_name)
        except FileNotFoundError:
            pass
        else:
            raise click.ClickException(
                f"Launch profile `{profile_name}` already exists in `{overlay.catalog_path}`."
            )

    if source_kind == "specialist":
        source = _load_specialist_or_click(overlay=overlay, name=source_name)
        adapter = _load_overlay_tool_adapter(overlay=overlay, tool=source.tool)
    else:
        source = _load_recipe_or_click(overlay=overlay, name=source_name)
        adapter = _load_overlay_tool_adapter(overlay=overlay, tool=source.tool)

    mailbox_mapping = (
        None
        if clear_mailbox
        else _build_profile_mailbox_mapping_or_click(
            mail_transport=mail_transport,
            mail_principal_id=mail_principal_id,
            mail_address=mail_address,
            mail_root=mail_root,
            mail_base_url=mail_base_url,
            mail_jmap_url=mail_jmap_url,
            mail_management_url=mail_management_url,
            source_label=f"{profile_name}:mailbox",
        )
    )
    prompt_overlay = (
        (None, None)
        if clear_prompt_overlay
        else _resolve_prompt_overlay_text_or_click(
            prompt_overlay_mode=prompt_overlay_mode,
            prompt_overlay_text=prompt_overlay_text,
            prompt_overlay_file=prompt_overlay_file,
        )
    )
    env_mapping = (
        {}
        if clear_env
        else (
            _parse_launch_profile_env_records_or_click(
                adapter=adapter,
                env_set=env_set,
                source_label=f"{profile_name}:env",
            )
            if env_set
            else None
        )
    )
    resolved_model_input = _resolve_model_name_or_click(model) if model is not None else None
    resolved_managed_header_policy: ManagedHeaderPolicy | None

    if current is None:
        resolved_agent_name = _optional_non_empty_value(agent_name)
        resolved_agent_id = _optional_non_empty_value(agent_id)
        resolved_workdir = _optional_non_empty_value(workdir)
        resolved_auth = _optional_non_empty_value(auth)
        resolved_model_config = _build_model_config_or_click(
            model_name=resolved_model_input,
            reasoning_level=reasoning_level,
        )
        resolved_prompt_mode = _optional_non_empty_value(prompt_mode)
        resolved_mailbox = mailbox_mapping
        resolved_env = env_mapping if env_mapping is not None else {}
        resolved_posture = _resolve_profile_posture_mapping(
            current=None,
            headless=headless,
            clear_headless=clear_headless,
            no_gateway=no_gateway,
            gateway_port=gateway_port,
        )
        resolved_managed_header_policy = (
            _managed_header_policy_from_override(managed_header) or "inherit"
        )
        resolved_prompt_overlay_mode, resolved_prompt_overlay_text = prompt_overlay
    else:
        resolved_agent_name = (
            None
            if clear_agent_name
            else (
                _optional_non_empty_value(agent_name)
                if agent_name is not None
                else current.entry.managed_agent_name
            )
        )
        resolved_agent_id = (
            None
            if clear_agent_id
            else (
                _optional_non_empty_value(agent_id)
                if agent_id is not None
                else current.entry.managed_agent_id
            )
        )
        resolved_workdir = (
            None
            if clear_workdir
            else (
                _optional_non_empty_value(workdir) if workdir is not None else current.entry.workdir
            )
        )
        if clear_auth and auth is not None:
            raise click.ClickException("`--auth` cannot be combined with `--clear-auth`.")
        resolved_auth = (
            None
            if clear_auth
            else (_optional_non_empty_value(auth) if auth is not None else current.entry.auth_name)
        )
        if clear_model and model is not None:
            raise click.ClickException("`--model` cannot be combined with `--clear-model`.")
        if clear_reasoning_level and reasoning_level is not None:
            raise click.ClickException(
                "`--reasoning-level` cannot be combined with `--clear-reasoning-level`."
            )
        resolved_model_config = _merge_model_config_for_storage(
            current_name=current.entry.model_name,
            current_reasoning_level=current.entry.reasoning_level,
            model_name=resolved_model_input,
            reasoning_level=reasoning_level,
            clear_model=clear_model,
            clear_reasoning_level=clear_reasoning_level,
        )
        if clear_prompt_mode and prompt_mode is not None:
            raise click.ClickException(
                "`--prompt-mode` cannot be combined with `--clear-prompt-mode`."
            )
        resolved_prompt_mode = (
            None
            if clear_prompt_mode
            else (
                _optional_non_empty_value(prompt_mode)
                if prompt_mode is not None
                else current.entry.operator_prompt_mode
            )
        )
        resolved_mailbox = (
            mailbox_mapping if mail_transport is not None else current.entry.mailbox_payload
        )
        if clear_mailbox:
            resolved_mailbox = None
        resolved_env = (
            {}
            if clear_env
            else (env_mapping if env_mapping is not None else dict(current.entry.env_payload))
        )
        resolved_posture = _resolve_profile_posture_mapping(
            current=current.entry.posture_payload,
            headless=headless,
            clear_headless=clear_headless,
            no_gateway=no_gateway,
            gateway_port=gateway_port,
        )
        if clear_managed_header and managed_header is not None:
            raise click.ClickException(
                "`--managed-header` or `--no-managed-header` cannot be combined with "
                "`--clear-managed-header`."
            )
        if clear_managed_header:
            resolved_managed_header_policy = "inherit"
        elif managed_header is not None:
            resolved_managed_header_policy = _managed_header_policy_from_override(managed_header)
        else:
            resolved_managed_header_policy = current.entry.managed_header_policy
        if clear_prompt_overlay:
            resolved_prompt_overlay_mode = None
            resolved_prompt_overlay_text = None
        elif prompt_overlay[0] is not None:
            resolved_prompt_overlay_mode, resolved_prompt_overlay_text = prompt_overlay
        else:
            resolved_prompt_overlay_mode = current.entry.prompt_overlay_mode
            resolved_prompt_overlay_text = current.prompt_overlay_text

    mutation_requested = any(
        (
            current is None,
            agent_name is not None,
            clear_agent_name,
            agent_id is not None,
            clear_agent_id,
            workdir is not None,
            clear_workdir,
            auth is not None,
            clear_auth,
            model is not None,
            clear_model,
            reasoning_level is not None,
            clear_reasoning_level,
            prompt_mode is not None,
            clear_prompt_mode,
            bool(env_set),
            clear_env,
            mail_transport is not None,
            clear_mailbox,
            headless,
            clear_headless,
            no_gateway,
            managed_header is not None,
            clear_managed_header,
            gateway_port is not None,
            prompt_overlay_mode is not None,
            prompt_overlay_text is not None,
            prompt_overlay_file is not None,
            clear_prompt_overlay,
        )
    )
    if not mutation_requested:
        raise click.ClickException("No launch-profile updates were requested.")

    catalog.store_launch_profile(
        name=profile_name,
        profile_lane=profile_lane,
        source_kind=source_kind,
        source_name=source_name,
        managed_agent_name=resolved_agent_name,
        managed_agent_id=resolved_agent_id,
        workdir=resolved_workdir,
        auth_name=resolved_auth,
        model_name=resolved_model_config.name if resolved_model_config is not None else None,
        reasoning_level=(
            resolved_model_config.reasoning.level
            if resolved_model_config is not None and resolved_model_config.reasoning is not None
            else None
        ),
        operator_prompt_mode=resolved_prompt_mode,
        env_mapping=resolved_env,
        mailbox_mapping=resolved_mailbox,
        posture_mapping=resolved_posture,
        managed_header_policy=resolved_managed_header_policy,
        prompt_overlay_mode=resolved_prompt_overlay_mode,
        prompt_overlay_text=resolved_prompt_overlay_text,
    )
    materialize_project_agent_catalog_projection(overlay)
    return _launch_profile_payload(
        overlay=overlay,
        profile_name=profile_name,
        expected_lane=profile_lane,
    )


def _launch_profile_provenance_payload(resolved: Any) -> dict[str, Any]:
    """Return secret-free launch-profile provenance for build and runtime metadata."""

    return {
        "name": resolved.entry.name,
        "lane": resolved.entry.profile_lane,
        "source_kind": resolved.entry.source_kind,
        "source_name": resolved.entry.source_name,
        "recipe_name": resolved.recipe_name,
        "prompt_overlay": {
            "mode": resolved.entry.prompt_overlay_mode,
            "present": resolved.prompt_overlay_text is not None,
        },
    }


def _specialist_payload(
    *,
    overlay: HoumaoProjectOverlay,
    metadata: SpecialistMetadata,
) -> dict[str, object]:
    """Return one structured specialist payload with generated canonical paths."""

    return {
        "name": metadata.name,
        "preset_name": metadata.preset_name,
        "tool": metadata.tool,
        "provider": metadata.provider,
        "credential": metadata.credential_name,
        "setup": metadata.setup_name,
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
    easy_profile_name = _instance_easy_profile_name(manifest_payload)
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
        "easy_profile": easy_profile_name,
        "project_root": str(overlay.project_root),
        "project_agent_def_dir": runtime_payload.get("agent_def_dir")
        if isinstance(runtime_payload, dict)
        else None,
        "mailbox": mailbox_payload,
    }


def _instance_easy_profile_name(manifest_payload: dict[str, object]) -> str | None:
    """Return the originating easy-profile name from one runtime manifest when available."""

    launch_profile = _instance_launch_profile_provenance(manifest_payload)
    if not isinstance(launch_profile, dict):
        return None
    lane = launch_profile.get("lane")
    name = launch_profile.get("name")
    if lane != "easy_profile" or not isinstance(name, str) or not name.strip():
        return None
    return name


def _instance_launch_profile_provenance(
    manifest_payload: dict[str, object],
) -> dict[str, Any] | None:
    """Return secret-free launch-profile provenance from one runtime manifest."""

    launch_plan_payload = manifest_payload.get("launch_plan")
    if not isinstance(launch_plan_payload, dict):
        return None
    metadata_payload = launch_plan_payload.get("metadata")
    if not isinstance(metadata_payload, dict):
        return None
    launch_overrides_payload = metadata_payload.get("launch_overrides")
    if not isinstance(launch_overrides_payload, dict):
        return None
    construction_provenance_payload = launch_overrides_payload.get("construction_provenance")
    if not isinstance(construction_provenance_payload, dict):
        return None
    launch_profile_payload = construction_provenance_payload.get("launch_profile")
    if not isinstance(launch_profile_payload, dict):
        return None
    return dict(launch_profile_payload)


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
            f"Tool `{tool}` is not initialized under the selected project overlay: {adapter_path}"
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
    """Return the default project-local role prompt content."""

    return f"# {role_name}\n\nDescribe the specialist system prompt here.\n"


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    """Load one YAML mapping payload from disk."""

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise click.ClickException(f"{path}: expected a top-level YAML mapping.")
    return loaded


def _write_yaml_mapping(path: Path, payload: dict[str, object]) -> None:
    """Write one YAML mapping payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _resolve_model_name_or_click(
    value: str | None,
    *,
    field_name: str = "--model",
) -> str | None:
    """Return one optional non-empty model name."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise click.ClickException(f"{field_name} must not be empty.")
    return stripped


def _build_model_config_or_click(
    *,
    model_name: str | None,
    reasoning_level: int | None,
) -> ModelConfig | None:
    """Build one normalized model config from CLI inputs."""

    try:
        return normalize_model_config(name=model_name, reasoning_level=reasoning_level)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_operator_prompt_mode_or_click(
    value: str | None,
    *,
    source: str,
) -> OperatorPromptMode | None:
    """Return one validated operator prompt mode from stored project state."""

    if value is None:
        return None
    if value not in {"as_is", "unattended"}:
        raise click.ClickException(
            f"{source} stores invalid launch.prompt_mode {value!r}; expected `as_is` or "
            "`unattended`."
        )
    return cast(OperatorPromptMode, value)


def _model_mapping_payload(model_config: ModelConfig | None) -> dict[str, object] | None:
    """Return one YAML/JSON-ready payload for optional model config."""

    payload = model_config_to_payload(model_config)
    if payload is None:
        return None
    return payload


def _merge_model_config_for_storage(
    *,
    current_name: str | None,
    current_reasoning_level: int | None,
    model_name: str | None,
    reasoning_level: int | None,
    clear_model: bool,
    clear_reasoning_level: bool,
) -> ModelConfig | None:
    """Resolve one stored model-config mutation on a per-subfield basis."""

    resolved_name = (
        None if clear_model else (model_name if model_name is not None else current_name)
    )
    resolved_reasoning_level = (
        None
        if clear_reasoning_level
        else (reasoning_level if reasoning_level is not None else current_reasoning_level)
    )
    return _build_model_config_or_click(
        model_name=resolved_name,
        reasoning_level=resolved_reasoning_level,
    )


def _resolve_required_prompt_text(
    *,
    system_prompt: str | None,
    system_prompt_file: Path | None,
) -> str:
    """Resolve one required prompt payload from inline or file input."""

    if system_prompt is not None and system_prompt_file is not None:
        raise click.ClickException(
            "Provide at most one of `--system-prompt` or `--system-prompt-file`."
        )
    if system_prompt is not None:
        value = system_prompt.strip()
        if not value:
            raise click.ClickException("`--system-prompt` must not be empty.")
        return value
    if system_prompt_file is not None:
        return system_prompt_file.read_text(encoding="utf-8").rstrip()
    raise click.ClickException("Provide one of `--system-prompt` or `--system-prompt-file`.")


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
