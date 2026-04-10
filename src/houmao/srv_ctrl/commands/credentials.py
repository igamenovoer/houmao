"""Credential management commands for `houmao-mgr`."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Literal

import click
import yaml

from houmao.agents.definition_parser import AuthFileMapping, ToolAdapter, parse_tool_adapter
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.project.catalog import AuthProfileCatalogEntry, ProjectCatalog
from houmao.project.overlay import (
    HoumaoProjectOverlay,
    ensure_project_aware_local_roots,
    load_project_overlay,
    materialize_project_agent_catalog_projection,
    resolve_project_aware_local_roots,
)

from .output import emit

CredentialTargetKind = Literal["project", "agent_def_dir"]
CredentialWriteOperation = Literal["add", "set"]

_SUPPORTED_CREDENTIAL_TOOLS: tuple[str, ...] = ("claude", "codex", "gemini")
_TOOL_DISPLAY_NAMES: dict[str, str] = {
    "claude": "Claude",
    "codex": "Codex",
    "gemini": "Gemini",
}
_SECRET_ENV_TOKENS: tuple[str, ...] = ("KEY", "TOKEN", "SECRET", "PASSWORD")
_CLAUDE_RUNTIME_STATE_TEMPLATE_FILENAME = "claude_state.template.json"
_CLAUDE_VENDOR_CREDENTIALS_FILENAME = ".credentials.json"
_CLAUDE_VENDOR_GLOBAL_STATE_FILENAME = ".claude.json"
_CLAUDE_VENDOR_LOGIN_FILE_SOURCES: frozenset[str] = frozenset(
    {
        _CLAUDE_VENDOR_CREDENTIALS_FILENAME,
        _CLAUDE_VENDOR_GLOBAL_STATE_FILENAME,
    }
)


@dataclass(frozen=True)
class CredentialTarget:
    """Resolved storage backend for one credential command."""

    kind: CredentialTargetKind
    overlay: HoumaoProjectOverlay | None = None
    agent_def_dir: Path | None = None

    @classmethod
    def project(cls, overlay: HoumaoProjectOverlay) -> "CredentialTarget":
        """Build one project-backed credential target."""

        return cls(kind="project", overlay=overlay)

    @classmethod
    def agent_def_dir_target(cls, agent_def_dir: Path) -> "CredentialTarget":
        """Build one plain agent-definition-directory credential target."""

        return cls(kind="agent_def_dir", agent_def_dir=agent_def_dir.resolve())


@click.group(name="credentials")
def credentials_group() -> None:
    """Manage credentials through the supported concern-oriented CLI surface."""


@click.group(name="credentials")
def project_credentials_group() -> None:
    """Manage project-scoped credentials in the active project overlay."""


def ensure_specialist_credential_bundle(
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
    """Create, update, or reuse one project-backed credential for specialist creation."""

    target = CredentialTarget.project(overlay)
    existing_profile = _load_project_auth_profile_optional(
        overlay=overlay,
        tool=tool,
        name=credential_name,
    )
    clear_file_sources: set[str] = set()
    if tool == "claude":
        env_values = _compact_env_values(
            {
                "ANTHROPIC_API_KEY": api_key,
                "ANTHROPIC_AUTH_TOKEN": claude_auth_token,
                "CLAUDE_CODE_OAUTH_TOKEN": claude_oauth_token,
                "ANTHROPIC_BASE_URL": base_url,
            }
        )
        file_sources = _claude_credential_file_sources(
            state_template_file=claude_state_template_file,
            config_dir=claude_config_dir,
        )
        if claude_config_dir is not None:
            clear_file_sources = set(_CLAUDE_VENDOR_LOGIN_FILE_SOURCES)
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
    else:
        raise click.ClickException(f"Unsupported specialist tool `{tool}`.")

    if existing_profile is not None:
        if not env_values and not file_sources:
            return {
                "operation": "reuse",
                "project_root": str(overlay.project_root),
                "tool": tool,
                "name": credential_name,
                "bundle_ref": existing_profile.bundle_ref,
                "path": str(existing_profile.resolved_projection_path(overlay)),
            }
        return _write_credential_bundle(
            target=target,
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
            f"Credential bundle `{credential_name}` does not exist under `{tool}` and no credential inputs were provided."
        )
    return _write_credential_bundle(
        target=target,
        tool=tool,
        name=credential_name,
        env_values=env_values,
        file_sources=file_sources,
        require_any_input=False,
        operation="add",
        clear_env_names=set(),
        clear_file_sources=clear_file_sources,
    )


def _target_options(
    project_only: bool,
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """Return the shared target-selector decorator for one command family."""

    if project_only:
        return lambda function: function
    return _credential_target_options


def _credential_target_options(function: Callable[..., None]) -> Callable[..., None]:
    """Attach the shared credential target selectors to one leaf command."""

    function = click.option(
        "--agent-def-dir",
        type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
        default=None,
        help="Manage credentials in the selected plain agent-definition directory.",
    )(function)
    function = click.option(
        "--project",
        "use_project",
        is_flag=True,
        help="Resolve credentials through the active project overlay.",
    )(function)
    return function


def _resolve_command_target(
    *,
    project_only: bool,
    use_project: bool,
    agent_def_dir: Path | None,
    allow_project_bootstrap: bool,
) -> CredentialTarget:
    """Resolve the storage target for one credential command."""

    cwd = Path.cwd().resolve()
    if project_only:
        return _resolve_project_target(cwd=cwd, allow_bootstrap=allow_project_bootstrap)

    if use_project and agent_def_dir is not None:
        raise click.ClickException("Provide at most one of `--project` or `--agent-def-dir`.")

    if agent_def_dir is not None:
        return _resolve_agent_def_dir_target(agent_def_dir.resolve())

    if use_project:
        return _resolve_project_target(cwd=cwd, allow_bootstrap=allow_project_bootstrap)

    env_value = os.environ.get(AGENT_DEF_DIR_ENV_VAR)
    if env_value is not None and env_value.strip():
        return _resolve_agent_def_dir_target(_resolve_input_path(env_value.strip(), base=cwd))

    roots = resolve_project_aware_local_roots(cwd=cwd)
    if roots.project_overlay is not None:
        return CredentialTarget.project(roots.project_overlay)

    raise click.ClickException(_missing_credential_target_message())


def _resolve_project_target(*, cwd: Path, allow_bootstrap: bool) -> CredentialTarget:
    """Resolve one project-backed target."""

    if allow_bootstrap:
        roots = ensure_project_aware_local_roots(cwd=cwd)
    else:
        roots = resolve_project_aware_local_roots(cwd=cwd)
    if roots.project_overlay is None:
        raise click.ClickException(_missing_credential_target_message())
    return CredentialTarget.project(roots.project_overlay)


def _resolve_agent_def_dir_target(agent_def_dir: Path) -> CredentialTarget:
    """Resolve one target from an explicit or ambient agent-definition directory."""

    owner_overlay = _load_owner_overlay_for_agent_def_dir(agent_def_dir)
    if owner_overlay is not None:
        return CredentialTarget.project(owner_overlay)
    return CredentialTarget.agent_def_dir_target(agent_def_dir)


def _load_owner_overlay_for_agent_def_dir(agent_def_dir: Path) -> HoumaoProjectOverlay | None:
    """Return the owning project overlay when one agent-definition path is overlay-managed."""

    resolved_agent_def_dir = agent_def_dir.resolve()
    for candidate_root in (resolved_agent_def_dir, *resolved_agent_def_dir.parents):
        config_path = (candidate_root / "houmao-config.toml").resolve()
        if not config_path.is_file():
            continue
        try:
            overlay = load_project_overlay(config_path)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        if overlay.agents_root == resolved_agent_def_dir:
            return overlay
    return None


def _resolve_input_path(value: str, *, base: Path) -> Path:
    """Resolve one CLI or env path relative to the current working directory."""

    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base / candidate).resolve()


def _missing_credential_target_message() -> str:
    """Return the maintained credential-target resolution failure message."""

    return (
        "No credential target could be resolved. Use `--project` to target the active project "
        "overlay or `--agent-def-dir <path>` to target a plain agent-definition directory."
    )


def _build_tool_group(*, tool: str, project_only: bool) -> click.Group:
    """Build one tool-specific credential group."""

    display_name = _TOOL_DISPLAY_NAMES[tool]
    help_text = (
        f"Manage project-scoped {display_name} credentials in the active overlay."
        if project_only
        else (
            f"Manage {display_name} credentials through either the active project overlay or "
            "a selected plain agent-definition directory."
        )
    )

    @click.group(name=tool, help=help_text)
    def tool_group() -> None:
        """Tool-specific credential command group."""

    tool_group.add_command(_build_list_command(tool=tool, project_only=project_only))
    tool_group.add_command(_build_get_command(tool=tool, project_only=project_only))
    tool_group.add_command(_build_remove_command(tool=tool, project_only=project_only))
    tool_group.add_command(_build_rename_command(tool=tool, project_only=project_only))
    if tool == "claude":
        tool_group.add_command(_build_claude_add_command(project_only=project_only))
        tool_group.add_command(_build_claude_set_command(project_only=project_only))
    elif tool == "codex":
        tool_group.add_command(_build_codex_add_command(project_only=project_only))
        tool_group.add_command(_build_codex_set_command(project_only=project_only))
    elif tool == "gemini":
        tool_group.add_command(_build_gemini_add_command(project_only=project_only))
        tool_group.add_command(_build_gemini_set_command(project_only=project_only))
    else:
        raise click.ClickException(f"Unsupported credential tool `{tool}`.")
    return tool_group


def _build_list_command(*, tool: str, project_only: bool) -> click.Command:
    """Build one `list` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="list")
    @_target_options(project_only)
    def list_command(
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """List credential names for one supported tool."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=False,
        )
        emit(_list_credentials_payload(target=target, tool=tool))

    list_command.__doc__ = (
        f"List {display_name} credential names."
        if not project_only
        else f"List project-scoped {display_name} credential names."
    )
    return list_command


def _build_get_command(*, tool: str, project_only: bool) -> click.Command:
    """Build one `get` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="get")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name.")
    def get_command(
        name: str,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Inspect one credential safely as structured data."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=False,
        )
        emit(_describe_credential_bundle(target=target, tool=tool, name=name))

    get_command.__doc__ = (
        f"Inspect one {display_name} credential safely."
        if not project_only
        else f"Inspect one project-scoped {display_name} credential safely."
    )
    return get_command


def _build_remove_command(*, tool: str, project_only: bool) -> click.Command:
    """Build one `remove` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="remove")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name to remove.")
    def remove_command(
        name: str,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Remove one credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=False,
        )
        emit(_remove_credential_bundle(target=target, tool=tool, name=name))

    remove_command.__doc__ = (
        f"Remove one {display_name} credential."
        if not project_only
        else f"Remove one project-scoped {display_name} credential."
    )
    return remove_command


def _build_rename_command(*, tool: str, project_only: bool) -> click.Command:
    """Build one `rename` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="rename")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Existing credential name.")
    @click.option("--to", "new_name", required=True, help="New credential name.")
    def rename_command(
        name: str,
        new_name: str,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Rename one credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=False,
        )
        emit(_rename_credential_bundle(target=target, tool=tool, name=name, new_name=new_name))

    rename_command.__doc__ = (
        f"Rename one {display_name} credential."
        if not project_only
        else f"Rename one project-scoped {display_name} credential."
    )
    return rename_command


def _build_claude_add_command(*, project_only: bool) -> click.Command:
    """Build the Claude `add` command."""

    @click.command(name="add")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `ANTHROPIC_API_KEY`.")
    @click.option("--auth-token", default=None, help="Value for `ANTHROPIC_AUTH_TOKEN`.")
    @click.option("--oauth-token", default=None, help="Value for `CLAUDE_CODE_OAUTH_TOKEN`.")
    @click.option("--base-url", default=None, help="Value for `ANTHROPIC_BASE_URL`.")
    @click.option("--model", default=None, help="Value for `ANTHROPIC_MODEL`.")
    @click.option("--small-fast-model", default=None, help="Value for `ANTHROPIC_SMALL_FAST_MODEL`.")
    @click.option("--subagent-model", default=None, help="Value for `CLAUDE_CODE_SUBAGENT_MODEL`.")
    @click.option("--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`.")
    @click.option("--default-sonnet-model", default=None, help="Value for `ANTHROPIC_DEFAULT_SONNET_MODEL`.")
    @click.option("--default-haiku-model", default=None, help="Value for `ANTHROPIC_DEFAULT_HAIKU_MODEL`.")
    @click.option(
        "--state-template-file",
        "state_template_file",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Claude bootstrap state template JSON to store in the credential bundle (not a credential).",
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
    def add_command(
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
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Create one Claude credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=True,
        )
        emit(
            _write_credential_bundle(
                target=target,
                tool="claude",
                name=name,
                env_values=_compact_env_values(
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
                ),
                file_sources=_claude_credential_file_sources(
                    state_template_file=state_template_file,
                    config_dir=config_dir,
                ),
                require_any_input=True,
                operation="add",
                clear_env_names=set(),
                clear_file_sources=set(),
            )
        )

    add_command.__doc__ = (
        "Create one Claude credential."
        if not project_only
        else "Create one project-scoped Claude credential."
    )
    return add_command


def _build_claude_set_command(*, project_only: bool) -> click.Command:
    """Build the Claude `set` command."""

    @click.command(name="set")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `ANTHROPIC_API_KEY`.")
    @click.option("--auth-token", default=None, help="Value for `ANTHROPIC_AUTH_TOKEN`.")
    @click.option("--oauth-token", default=None, help="Value for `CLAUDE_CODE_OAUTH_TOKEN`.")
    @click.option("--base-url", default=None, help="Value for `ANTHROPIC_BASE_URL`.")
    @click.option("--model", default=None, help="Value for `ANTHROPIC_MODEL`.")
    @click.option("--small-fast-model", default=None, help="Value for `ANTHROPIC_SMALL_FAST_MODEL`.")
    @click.option("--subagent-model", default=None, help="Value for `CLAUDE_CODE_SUBAGENT_MODEL`.")
    @click.option("--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`.")
    @click.option("--default-sonnet-model", default=None, help="Value for `ANTHROPIC_DEFAULT_SONNET_MODEL`.")
    @click.option("--default-haiku-model", default=None, help="Value for `ANTHROPIC_DEFAULT_HAIKU_MODEL`.")
    @click.option(
        "--state-template-file",
        "state_template_file",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Claude bootstrap state template JSON to store in the credential bundle (not a credential).",
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
    @click.option("--clear-api-key", is_flag=True, help="Remove `ANTHROPIC_API_KEY` from the credential bundle.")
    @click.option("--clear-auth-token", is_flag=True, help="Remove `ANTHROPIC_AUTH_TOKEN` from the credential bundle.")
    @click.option("--clear-oauth-token", is_flag=True, help="Remove `CLAUDE_CODE_OAUTH_TOKEN` from the credential bundle.")
    @click.option("--clear-base-url", is_flag=True, help="Remove `ANTHROPIC_BASE_URL` from the credential bundle.")
    @click.option("--clear-model", is_flag=True, help="Remove `ANTHROPIC_MODEL` from the credential bundle.")
    @click.option("--clear-small-fast-model", is_flag=True, help="Remove `ANTHROPIC_SMALL_FAST_MODEL` from the credential bundle.")
    @click.option("--clear-subagent-model", is_flag=True, help="Remove `CLAUDE_CODE_SUBAGENT_MODEL` from the credential bundle.")
    @click.option("--clear-default-opus-model", is_flag=True, help="Remove `ANTHROPIC_DEFAULT_OPUS_MODEL` from the credential bundle.")
    @click.option("--clear-default-sonnet-model", is_flag=True, help="Remove `ANTHROPIC_DEFAULT_SONNET_MODEL` from the credential bundle.")
    @click.option("--clear-default-haiku-model", is_flag=True, help="Remove `ANTHROPIC_DEFAULT_HAIKU_MODEL` from the credential bundle.")
    @click.option("--clear-state-template-file", is_flag=True, help="Remove optional `files/claude_state.template.json` bootstrap state from the credential bundle.")
    @click.option("--clear-config-dir", is_flag=True, help="Remove imported Claude vendor login-state files from the credential bundle.")
    def set_command(
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
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Update one Claude credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=True,
        )
        clear_file_sources = _flagged_items(
            {
                _CLAUDE_RUNTIME_STATE_TEMPLATE_FILENAME: clear_state_template_file,
                _CLAUDE_VENDOR_CREDENTIALS_FILENAME: clear_config_dir,
                _CLAUDE_VENDOR_GLOBAL_STATE_FILENAME: clear_config_dir,
            }
        )
        if config_dir is not None:
            clear_file_sources.update(_CLAUDE_VENDOR_LOGIN_FILE_SOURCES)
        emit(
            _write_credential_bundle(
                target=target,
                tool="claude",
                name=name,
                env_values=_compact_env_values(
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
                ),
                file_sources=_claude_credential_file_sources(
                    state_template_file=state_template_file,
                    config_dir=config_dir,
                ),
                require_any_input=True,
                operation="set",
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
                clear_file_sources=clear_file_sources,
            )
        )

    set_command.__doc__ = (
        "Update one Claude credential."
        if not project_only
        else "Update one project-scoped Claude credential."
    )
    return set_command


def _build_codex_add_command(*, project_only: bool) -> click.Command:
    """Build the Codex `add` command."""

    @click.command(name="add")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `OPENAI_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `OPENAI_BASE_URL`.")
    @click.option("--org-id", default=None, help="Value for `OPENAI_ORG_ID`.")
    @click.option(
        "--auth-json",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Codex `auth.json` login-state file to store in the credential bundle.",
    )
    def add_command(
        name: str,
        api_key: str | None,
        base_url: str | None,
        org_id: str | None,
        auth_json: Path | None,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Create one Codex credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=True,
        )
        emit(
            _write_credential_bundle(
                target=target,
                tool="codex",
                name=name,
                env_values=_compact_env_values(
                    {
                        "OPENAI_API_KEY": api_key,
                        "OPENAI_BASE_URL": base_url,
                        "OPENAI_ORG_ID": org_id,
                    }
                ),
                file_sources={"auth.json": auth_json} if auth_json is not None else {},
                require_any_input=True,
                operation="add",
                clear_env_names=set(),
                clear_file_sources=set(),
            )
        )

    add_command.__doc__ = (
        "Create one Codex credential."
        if not project_only
        else "Create one project-scoped Codex credential."
    )
    return add_command


def _build_codex_set_command(*, project_only: bool) -> click.Command:
    """Build the Codex `set` command."""

    @click.command(name="set")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `OPENAI_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `OPENAI_BASE_URL`.")
    @click.option("--org-id", default=None, help="Value for `OPENAI_ORG_ID`.")
    @click.option(
        "--auth-json",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Codex `auth.json` login-state file to store in the credential bundle.",
    )
    @click.option("--clear-api-key", is_flag=True, help="Remove `OPENAI_API_KEY` from the credential bundle.")
    @click.option("--clear-base-url", is_flag=True, help="Remove `OPENAI_BASE_URL` from the credential bundle.")
    @click.option("--clear-org-id", is_flag=True, help="Remove `OPENAI_ORG_ID` from the credential bundle.")
    @click.option("--clear-auth-json", is_flag=True, help="Remove `files/auth.json` from the credential bundle.")
    def set_command(
        name: str,
        api_key: str | None,
        base_url: str | None,
        org_id: str | None,
        auth_json: Path | None,
        clear_api_key: bool,
        clear_base_url: bool,
        clear_org_id: bool,
        clear_auth_json: bool,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Update one Codex credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=True,
        )
        emit(
            _write_credential_bundle(
                target=target,
                tool="codex",
                name=name,
                env_values=_compact_env_values(
                    {
                        "OPENAI_API_KEY": api_key,
                        "OPENAI_BASE_URL": base_url,
                        "OPENAI_ORG_ID": org_id,
                    }
                ),
                file_sources={"auth.json": auth_json} if auth_json is not None else {},
                require_any_input=True,
                operation="set",
                clear_env_names=_flagged_items(
                    {
                        "OPENAI_API_KEY": clear_api_key,
                        "OPENAI_BASE_URL": clear_base_url,
                        "OPENAI_ORG_ID": clear_org_id,
                    }
                ),
                clear_file_sources=_flagged_items({"auth.json": clear_auth_json}),
            )
        )

    set_command.__doc__ = (
        "Update one Codex credential."
        if not project_only
        else "Update one project-scoped Codex credential."
    )
    return set_command


def _build_gemini_add_command(*, project_only: bool) -> click.Command:
    """Build the Gemini `add` command."""

    @click.command(name="add")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `GEMINI_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `GOOGLE_GEMINI_BASE_URL`.")
    @click.option("--google-api-key", default=None, help="Value for `GOOGLE_API_KEY`.")
    @click.option(
        "--use-vertex-ai",
        is_flag=True,
        help="Store `GOOGLE_GENAI_USE_VERTEXAI=true` in the credential bundle env file.",
    )
    @click.option(
        "--oauth-creds",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional path to the Gemini CLI `oauth_creds.json` file.",
    )
    def add_command(
        name: str,
        api_key: str | None,
        base_url: str | None,
        google_api_key: str | None,
        use_vertex_ai: bool,
        oauth_creds: Path | None,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Create one Gemini credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=True,
        )
        emit(
            _write_credential_bundle(
                target=target,
                tool="gemini",
                name=name,
                env_values=_compact_env_values(
                    {
                        "GEMINI_API_KEY": api_key,
                        "GOOGLE_GEMINI_BASE_URL": base_url,
                        "GOOGLE_API_KEY": google_api_key,
                        "GOOGLE_GENAI_USE_VERTEXAI": "true" if use_vertex_ai else None,
                    }
                ),
                file_sources={"oauth_creds.json": oauth_creds} if oauth_creds is not None else {},
                require_any_input=True,
                operation="add",
                clear_env_names=set(),
                clear_file_sources=set(),
            )
        )

    add_command.__doc__ = (
        "Create one Gemini credential."
        if not project_only
        else "Create one project-scoped Gemini credential."
    )
    return add_command


def _build_gemini_set_command(*, project_only: bool) -> click.Command:
    """Build the Gemini `set` command."""

    @click.command(name="set")
    @_target_options(project_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `GEMINI_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `GOOGLE_GEMINI_BASE_URL`.")
    @click.option("--google-api-key", default=None, help="Value for `GOOGLE_API_KEY`.")
    @click.option(
        "--use-vertex-ai",
        is_flag=True,
        help="Store `GOOGLE_GENAI_USE_VERTEXAI=true` in the credential bundle env file.",
    )
    @click.option(
        "--oauth-creds",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Path to the Gemini CLI `oauth_creds.json` file required by the current adapter.",
    )
    @click.option("--clear-api-key", is_flag=True, help="Remove `GEMINI_API_KEY` from the credential bundle.")
    @click.option("--clear-base-url", is_flag=True, help="Remove `GOOGLE_GEMINI_BASE_URL` from the credential bundle.")
    @click.option("--clear-google-api-key", is_flag=True, help="Remove `GOOGLE_API_KEY` from the credential bundle.")
    @click.option("--clear-use-vertex-ai", is_flag=True, help="Remove `GOOGLE_GENAI_USE_VERTEXAI` from the credential bundle.")
    def set_command(
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
        use_project: bool = False,
        agent_def_dir: Path | None = None,
    ) -> None:
        """Update one Gemini credential."""

        target = _resolve_command_target(
            project_only=project_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            allow_project_bootstrap=True,
        )
        emit(
            _write_credential_bundle(
                target=target,
                tool="gemini",
                name=name,
                env_values=_compact_env_values(
                    {
                        "GEMINI_API_KEY": api_key,
                        "GOOGLE_GEMINI_BASE_URL": base_url,
                        "GOOGLE_API_KEY": google_api_key,
                        "GOOGLE_GENAI_USE_VERTEXAI": "true" if use_vertex_ai else None,
                    }
                ),
                file_sources={"oauth_creds.json": oauth_creds} if oauth_creds is not None else {},
                require_any_input=True,
                operation="set",
                clear_env_names=_flagged_items(
                    {
                        "GEMINI_API_KEY": clear_api_key,
                        "GOOGLE_GEMINI_BASE_URL": clear_base_url,
                        "GOOGLE_API_KEY": clear_google_api_key,
                        "GOOGLE_GENAI_USE_VERTEXAI": clear_use_vertex_ai,
                    }
                ),
                clear_file_sources=set(),
            )
        )

    set_command.__doc__ = (
        "Update one Gemini credential."
        if not project_only
        else "Update one project-scoped Gemini credential."
    )
    return set_command


def _list_credentials_payload(*, target: CredentialTarget, tool: str) -> dict[str, object]:
    """Return one structured credential listing payload."""

    if target.kind == "project":
        assert target.overlay is not None
        return {
            "target_kind": "project",
            "project_root": str(target.overlay.project_root),
            "tool": tool,
            "credentials": [
                profile.display_name
                for profile in ProjectCatalog.from_overlay(target.overlay).list_auth_profiles(tool=tool)
            ],
        }

    assert target.agent_def_dir is not None
    auth_root = _agent_def_dir_auth_root(agent_def_dir=target.agent_def_dir, tool=tool)
    return {
        "target_kind": "agent_def_dir",
        "agent_def_dir": str(target.agent_def_dir),
        "tool": tool,
        "credentials": (
            sorted(path.name for path in auth_root.iterdir() if path.is_dir()) if auth_root.is_dir() else []
        ),
    }


def _describe_credential_bundle(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
) -> dict[str, object]:
    """Return one structured credential description with redaction."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    adapter = _load_target_tool_adapter(target=target, tool=tool)
    if target.kind == "project":
        assert target.overlay is not None
        profile = _load_project_auth_profile_or_click(
            overlay=target.overlay,
            tool=tool,
            name=resolved_name,
        )
        source_root = _project_auth_source_root(overlay=target.overlay, profile=profile)
        files_root = (source_root / adapter.auth_files_dir).resolve()
        projection_root = profile.resolved_projection_path(target.overlay)
        env_values = _load_existing_env_values((source_root / adapter.auth_env_source).resolve())
        return {
            "target_kind": "project",
            "project_root": str(target.overlay.project_root),
            "tool": tool,
            "name": profile.display_name,
            "bundle_ref": profile.bundle_ref,
            "path": str(projection_root),
            "env_file": str((projection_root / adapter.auth_env_source).resolve()),
            "env": {
                env_name: _describe_env_value(env_name=env_name, env_values=env_values)
                for env_name in adapter.auth_env_allowlist
            },
            "files": {
                mapping.source: _describe_file_mapping(files_root=files_root, mapping=mapping)
                for mapping in adapter.auth_file_mappings
            },
        }

    assert target.agent_def_dir is not None
    bundle_root = _direct_auth_bundle_root(
        agent_def_dir=target.agent_def_dir,
        tool=tool,
        name=resolved_name,
    )
    if not bundle_root.is_dir():
        raise click.ClickException(f"Credential bundle not found: {bundle_root}")
    files_root = (bundle_root / adapter.auth_files_dir).resolve()
    env_file = (bundle_root / adapter.auth_env_source).resolve()
    env_values = _load_existing_env_values(env_file)
    return {
        "target_kind": "agent_def_dir",
        "agent_def_dir": str(target.agent_def_dir),
        "tool": tool,
        "name": resolved_name,
        "path": str(bundle_root),
        "env_file": str(env_file),
        "env": {
            env_name: _describe_env_value(env_name=env_name, env_values=env_values)
            for env_name in adapter.auth_env_allowlist
        },
        "files": {
            mapping.source: _describe_file_mapping(files_root=files_root, mapping=mapping)
            for mapping in adapter.auth_file_mappings
        },
    }


def _remove_credential_bundle(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
) -> dict[str, object]:
    """Remove one credential and return the removal payload."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    if target.kind == "project":
        assert target.overlay is not None
        catalog = ProjectCatalog.from_overlay(target.overlay)
        try:
            removed = catalog.remove_auth_profile(tool=tool, name=resolved_name)
        except (FileNotFoundError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        materialize_project_agent_catalog_projection(target.overlay)
        return {
            "target_kind": "project",
            "project_root": str(target.overlay.project_root),
            "tool": tool,
            "name": removed.display_name,
            "bundle_ref": removed.bundle_ref,
            "removed": True,
            "path": str(removed.resolved_projection_path(target.overlay)),
        }

    assert target.agent_def_dir is not None
    bundle_root = _direct_auth_bundle_root(
        agent_def_dir=target.agent_def_dir,
        tool=tool,
        name=resolved_name,
    )
    if not bundle_root.is_dir():
        raise click.ClickException(f"Credential bundle not found: {bundle_root}")
    shutil.rmtree(bundle_root)
    return {
        "target_kind": "agent_def_dir",
        "agent_def_dir": str(target.agent_def_dir),
        "tool": tool,
        "name": resolved_name,
        "removed": True,
        "path": str(bundle_root),
    }


def _rename_credential_bundle(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
    new_name: str,
) -> dict[str, object]:
    """Rename one credential and return the rename payload."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    resolved_new_name = _require_non_empty_name(new_name, field_name="--to")
    if target.kind == "project":
        assert target.overlay is not None
        catalog = ProjectCatalog.from_overlay(target.overlay)
        try:
            renamed = catalog.rename_auth_profile(
                tool=tool,
                name=resolved_name,
                new_name=resolved_new_name,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        materialize_project_agent_catalog_projection(target.overlay)
        return {
            "target_kind": "project",
            "project_root": str(target.overlay.project_root),
            "tool": tool,
            "name": renamed.display_name,
            "previous_name": resolved_name,
            "bundle_ref": renamed.bundle_ref,
            "path": str(renamed.resolved_projection_path(target.overlay)),
        }

    assert target.agent_def_dir is not None
    source_root = _direct_auth_bundle_root(
        agent_def_dir=target.agent_def_dir,
        tool=tool,
        name=resolved_name,
    )
    if not source_root.is_dir():
        raise click.ClickException(f"Credential bundle not found: {source_root}")
    destination_root = _direct_auth_bundle_root(
        agent_def_dir=target.agent_def_dir,
        tool=tool,
        name=resolved_new_name,
    )
    if destination_root.exists():
        raise click.ClickException(f"Credential bundle already exists: {destination_root}")
    rewrites = _collect_direct_dir_auth_reference_rewrites(
        agent_def_dir=target.agent_def_dir,
        tool=tool,
        old_name=resolved_name,
        new_name=resolved_new_name,
    )
    source_root.rename(destination_root)
    rewritten_files: list[str] = []
    for path, payload in rewrites:
        _write_yaml_mapping(path, payload)
        rewritten_files.append(str(path))
    return {
        "target_kind": "agent_def_dir",
        "agent_def_dir": str(target.agent_def_dir),
        "tool": tool,
        "name": resolved_new_name,
        "previous_name": resolved_name,
        "path": str(destination_root),
        "rewritten_files": rewritten_files,
    }


def _collect_direct_dir_auth_reference_rewrites(
    *,
    agent_def_dir: Path,
    tool: str,
    old_name: str,
    new_name: str,
) -> list[tuple[Path, dict[str, object]]]:
    """Collect maintained YAML rewrites for one direct-dir credential rename."""

    rewrites: list[tuple[Path, dict[str, object]]] = []
    for relative_root in ("presets", "launch-profiles"):
        candidate_root = (agent_def_dir / relative_root).resolve()
        if not candidate_root.is_dir():
            continue
        for pattern in ("*.yaml", "*.yml"):
            for path in sorted(candidate_root.glob(pattern)):
                payload = _load_yaml_mapping(path)
                if str(payload.get("tool")) != tool:
                    continue
                if str(payload.get("auth")) != old_name:
                    continue
                updated_payload = dict(payload)
                updated_payload["auth"] = new_name
                rewrites.append((path.resolve(), updated_payload))
    return rewrites


def _write_credential_bundle(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
    env_values: dict[str, str],
    file_sources: dict[str, Path],
    require_any_input: bool,
    operation: CredentialWriteOperation,
    clear_env_names: set[str],
    clear_file_sources: set[str],
) -> dict[str, object]:
    """Create or update one credential using the shared adapter-driven engine."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    adapter = _load_target_tool_adapter(target=target, tool=tool)
    if operation not in {"add", "set"}:
        raise click.ClickException(f"Unsupported credential operation: {operation}")

    if (
        require_any_input
        and not env_values
        and not file_sources
        and not clear_env_names
        and not clear_file_sources
    ):
        raise click.ClickException(
            f"Provide at least one credential input for `{tool}` (env value or compatible auth file)."
        )
    if (
        operation == "set"
        and not env_values
        and not file_sources
        and not clear_env_names
        and not clear_file_sources
    ):
        raise click.ClickException(
            f"Provide at least one change to update credential `{resolved_name}` for `{tool}`."
        )

    unsupported_env_keys = sorted((set(env_values) | clear_env_names) - set(adapter.auth_env_allowlist))
    if unsupported_env_keys:
        raise click.ClickException(
            f"Unsupported env var(s) for `{tool}` credentials: {', '.join(unsupported_env_keys)}"
        )
    known_file_sources = {mapping.source: mapping for mapping in adapter.auth_file_mappings}
    unsupported_file_sources = sorted(
        (set(file_sources) | clear_file_sources) - set(known_file_sources)
    )
    if unsupported_file_sources:
        raise click.ClickException(
            f"Unsupported auth file(s) for `{tool}` credentials: {', '.join(unsupported_file_sources)}"
        )

    existing_source_root = _resolve_existing_credential_source_root(
        target=target,
        tool=tool,
        name=resolved_name,
        operation=operation,
    )

    with tempfile.TemporaryDirectory(prefix=f"houmao-credential-{tool}-") as temp_dir:
        temp_auth_root = (Path(temp_dir).resolve() / "auth").resolve()
        if existing_source_root is not None:
            shutil.copytree(existing_source_root, temp_auth_root)
        else:
            temp_auth_root.mkdir(parents=True, exist_ok=True)

        env_file_path = (temp_auth_root / adapter.auth_env_source).resolve()
        files_root = (temp_auth_root / adapter.auth_files_dir).resolve()
        existing_env_values = _load_existing_env_values(env_file_path)
        merged_env_values = dict(existing_env_values)
        merged_env_values.update(env_values)
        for env_name in clear_env_names:
            merged_env_values.pop(env_name, None)

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
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path.resolve(), destination_path)

        for mapping in adapter.auth_file_mappings:
            if mapping.required and not (files_root / mapping.source).exists():
                raise click.ClickException(
                    f"Missing required auth file `{mapping.source}` for `{tool}` credential "
                    f"`{resolved_name}`."
                )

        env_file_path.write_text(
            _render_env_file(env_values=merged_env_values, allowlist=adapter.auth_env_allowlist),
            encoding="utf-8",
        )

        return _persist_credential_bundle(
            target=target,
            tool=tool,
            name=resolved_name,
            adapter=adapter,
            temp_auth_root=temp_auth_root,
            merged_env_values=merged_env_values,
            file_sources=file_sources,
            clear_env_names=clear_env_names,
            clear_file_sources=clear_file_sources,
            operation=operation,
        )


def _resolve_existing_credential_source_root(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
    operation: CredentialWriteOperation,
) -> Path | None:
    """Resolve one existing source root for a credential mutation."""

    if target.kind == "project":
        assert target.overlay is not None
        profile = _load_project_auth_profile_optional(overlay=target.overlay, tool=tool, name=name)
        if operation == "set" and profile is None:
            raise click.ClickException(f"Credential bundle not found for `{tool}`: `{name}`.")
        return (
            _project_auth_source_root(overlay=target.overlay, profile=profile)
            if profile is not None
            else None
        )

    assert target.agent_def_dir is not None
    bundle_root = _direct_auth_bundle_root(
        agent_def_dir=target.agent_def_dir,
        tool=tool,
        name=name,
    )
    if operation == "set" and not bundle_root.is_dir():
        raise click.ClickException(f"Credential bundle not found: {bundle_root}")
    if operation == "add" and bundle_root.exists():
        raise click.ClickException(f"Credential bundle already exists: {bundle_root}")
    return bundle_root if bundle_root.is_dir() else None


def _persist_credential_bundle(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
    adapter: ToolAdapter,
    temp_auth_root: Path,
    merged_env_values: dict[str, str],
    file_sources: dict[str, Path],
    clear_env_names: set[str],
    clear_file_sources: set[str],
    operation: CredentialWriteOperation,
) -> dict[str, object]:
    """Persist one fully prepared credential bundle into the selected backend."""

    if target.kind == "project":
        assert target.overlay is not None
        catalog = ProjectCatalog.from_overlay(target.overlay)
        try:
            stored_profile = (
                catalog.create_auth_profile_from_source(
                    tool=tool,
                    display_name=name,
                    source_path=temp_auth_root,
                )
                if operation == "add"
                else catalog.update_auth_profile_from_source(
                    tool=tool,
                    display_name=name,
                    source_path=temp_auth_root,
                )
            )
        except (FileNotFoundError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        materialize_project_agent_catalog_projection(target.overlay)
        projection_root = stored_profile.resolved_projection_path(target.overlay)
        projection_env_file = (projection_root / adapter.auth_env_source).resolve()
        projection_files_root = (projection_root / adapter.auth_files_dir).resolve()
        return {
            "target_kind": "project",
            "operation": operation,
            "project_root": str(target.overlay.project_root),
            "tool": tool,
            "name": name,
            "bundle_ref": stored_profile.bundle_ref,
            "path": str(projection_root),
            "env_file": str(projection_env_file),
            "written_env_vars": [
                env_name for env_name in adapter.auth_env_allowlist if env_name in merged_env_values
            ],
            "cleared_env_vars": sorted(clear_env_names),
            "written_files": [
                str((projection_files_root / source_name).resolve()) for source_name in sorted(file_sources)
            ],
            "cleared_files": sorted(clear_file_sources),
        }

    assert target.agent_def_dir is not None
    bundle_root = _direct_auth_bundle_root(agent_def_dir=target.agent_def_dir, tool=tool, name=name)
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(temp_auth_root, bundle_root)
    files_root = (bundle_root / adapter.auth_files_dir).resolve()
    return {
        "target_kind": "agent_def_dir",
        "operation": operation,
        "agent_def_dir": str(target.agent_def_dir),
        "tool": tool,
        "name": name,
        "path": str(bundle_root),
        "env_file": str((bundle_root / adapter.auth_env_source).resolve()),
        "written_env_vars": [
            env_name for env_name in adapter.auth_env_allowlist if env_name in merged_env_values
        ],
        "cleared_env_vars": sorted(clear_env_names),
        "written_files": [
            str((files_root / source_name).resolve()) for source_name in sorted(file_sources)
        ],
        "cleared_files": sorted(clear_file_sources),
    }


def _load_target_tool_adapter(*, target: CredentialTarget, tool: str) -> ToolAdapter:
    """Load one adapter for the selected credential target."""

    if target.kind == "project":
        assert target.overlay is not None
        agent_def_dir = materialize_project_agent_catalog_projection(target.overlay)
    else:
        assert target.agent_def_dir is not None
        agent_def_dir = target.agent_def_dir
    adapter_path = (agent_def_dir / "tools" / tool / "adapter.yaml").resolve()
    if not adapter_path.is_file():
        if target.kind == "project":
            assert target.overlay is not None
            raise click.ClickException(
                f"Tool `{tool}` is not initialized under the selected project overlay: {adapter_path}"
            )
        raise click.ClickException(
            f"Tool `{tool}` is not initialized under the selected agent-definition directory: {adapter_path}"
        )
    try:
        return parse_tool_adapter(adapter_path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _load_project_auth_profile_or_click(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
) -> AuthProfileCatalogEntry:
    """Load one project-backed auth profile or raise one operator-facing error."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    try:
        return ProjectCatalog.from_overlay(overlay).load_auth_profile(tool=tool, name=resolved_name)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _load_project_auth_profile_optional(
    *,
    overlay: HoumaoProjectOverlay,
    tool: str,
    name: str,
) -> AuthProfileCatalogEntry | None:
    """Load one project-backed auth profile when present."""

    try:
        return ProjectCatalog.from_overlay(overlay).load_auth_profile(tool=tool, name=name)
    except FileNotFoundError:
        return None


def _project_auth_source_root(
    *,
    overlay: HoumaoProjectOverlay,
    profile: AuthProfileCatalogEntry,
) -> Path:
    """Return the authoritative managed-content root for one project-backed credential."""

    return profile.content_ref.resolve(overlay)


def _agent_def_dir_auth_root(*, agent_def_dir: Path, tool: str) -> Path:
    """Return the auth root for one tool inside one plain agent-definition directory."""

    return (agent_def_dir.resolve() / "tools" / tool / "auth").resolve()


def _direct_auth_bundle_root(*, agent_def_dir: Path, tool: str, name: str) -> Path:
    """Return one plain-directory credential root."""

    return (_agent_def_dir_auth_root(agent_def_dir=agent_def_dir, tool=tool) / name).resolve()


def _claude_credential_file_sources(
    *,
    state_template_file: Path | None,
    config_dir: Path | None,
) -> dict[str, Path]:
    """Resolve Claude credential file sources from optional inputs."""

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


def _describe_env_value(*, env_name: str, env_values: dict[str, str]) -> dict[str, object]:
    """Describe one env-backed credential value without leaking secret-like content."""

    if env_name not in env_values:
        return {"present": False}
    if _is_secret_env_name(env_name):
        return {"present": True, "redacted": True}
    return {"present": True, "value": env_values[env_name]}


def _describe_file_mapping(*, files_root: Path, mapping: AuthFileMapping) -> dict[str, object]:
    """Describe one file-backed credential entry without returning raw content."""

    source_path = (files_root / mapping.source).resolve()
    return {
        "present": source_path.is_file(),
        "path": str(source_path) if source_path.is_file() else None,
        "required": mapping.required,
    }


def _load_existing_env_values(path: Path) -> dict[str, str]:
    """Load existing credential env values when present."""

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
    """Render one stable `env/vars.env` file for a credential bundle."""

    lines = [f"{env_name}={env_values[env_name]}" for env_name in allowlist if env_name in env_values]
    return "\n".join(lines) + "\n"


def _compact_env_values(raw_values: dict[str, str | None]) -> dict[str, str]:
    """Drop empty env values before credential materialization."""

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


def _require_non_empty_name(value: str, *, field_name: str) -> str:
    """Validate one credential name."""

    candidate = value.strip()
    if not candidate:
        raise click.ClickException(f"{field_name} must not be empty.")
    if "/" in candidate or "\\" in candidate:
        raise click.ClickException(f"{field_name} must not contain path separators.")
    return candidate


for _tool_name in _SUPPORTED_CREDENTIAL_TOOLS:
    credentials_group.add_command(_build_tool_group(tool=_tool_name, project_only=False))
    project_credentials_group.add_command(_build_tool_group(tool=_tool_name, project_only=True))
