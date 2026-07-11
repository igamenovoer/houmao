"""Credential management commands for `houmao-mgr`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable, Literal

import click
import yaml

from houmao.agents.definition_parser import (
    AuthFileMapping,
    ToolAdapter,
    parse_agent_preset,
    parse_tool_adapter,
)
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.owned_mutation import (
    remove_tree_or_path,
    replace_file,
    replace_path_with_text,
)
from houmao.terminology import NATIVE_AGENT_ROOT_ENV_VAR, resolve_native_agent_root
from houmao.project.catalog import AuthProfileCatalogEntry, ProjectCatalog
from houmao.project.overlay import (
    HoumaoProjectOverlay,
    ensure_project_aware_local_roots,
    load_project_overlay,
    materialize_project_agent_catalog_projection,
    resolve_project_aware_local_roots,
)

from .output import emit
from .project_context import active_project_dir

CredentialTargetKind = Literal["project", "agent_def_dir"]
CredentialWriteOperation = Literal["add", "set"]
CredentialLoginOperation = Literal["add", "set"]

_SUPPORTED_CREDENTIAL_TOOLS: tuple[str, ...] = ("claude", "codex", "kimi")
_TOOL_DISPLAY_NAMES: dict[str, str] = {
    "claude": "Claude",
    "codex": "Codex",
    "kimi": "Kimi",
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
_KIMI_CONFIG_FILENAME = "config.toml"
_KIMI_CREDENTIAL_JSON_SOURCE = "credentials/kimi-code.json"
_KIMI_CODE_HOME_FILE_SOURCES: frozenset[str] = frozenset(
    {
        _KIMI_CONFIG_FILENAME,
        _KIMI_CREDENTIAL_JSON_SOURCE,
    }
)
_PROVIDER_HOME_ENV_VARS: dict[str, str] = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "kimi": "KIMI_CODE_HOME",
}
_PROVIDER_AUTH_ENV_VARS: dict[str, frozenset[str]] = {
    "claude": frozenset(
        {
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL",
            "CLAUDE_CODE_OAUTH_TOKEN",
            "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
            "CLAUDE_CODE_OAUTH_SCOPES",
        }
    ),
    "codex": frozenset(
        {
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_ORG_ID",
        }
    ),
    "kimi": frozenset(
        {
            "KIMI_MODEL_NAME",
            "KIMI_MODEL_API_KEY",
            "KIMI_MODEL_PROVIDER_TYPE",
            "KIMI_MODEL_BASE_URL",
            "KIMI_CODE_BASE_URL",
            "KIMI_CODE_OAUTH_HOST",
            "KIMI_OAUTH_HOST",
        }
    ),
}


@dataclass(frozen=True)
class CredentialProviderLogin:
    """Provider-specific login command and artifact mapping."""

    command: list[str]
    temp_home_env_var: str
    artifact_sources: dict[str, Path]
    extra_env: dict[str, str]


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


@click.group(name="credentials")
def native_agent_credentials_group() -> None:
    """Manage direct native-agent credentials under the selected native-agent root."""


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
    kimi_model_name: str | None,
    kimi_config_toml: Path | None,
    kimi_credential_json: Path | None,
    kimi_code_home: Path | None,
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
    elif tool == "kimi":
        env_values = _compact_env_values(
            {
                "KIMI_MODEL_NAME": kimi_model_name,
                "KIMI_MODEL_API_KEY": api_key,
                "KIMI_MODEL_BASE_URL": base_url,
            }
        )
        file_sources = _kimi_credential_file_sources(
            config_toml=kimi_config_toml,
            credential_json=kimi_credential_json,
            code_home=kimi_code_home,
        )
        if kimi_code_home is not None:
            clear_file_sources = set(_KIMI_CODE_HOME_FILE_SOURCES)
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
    *,
    native_only: bool = False,
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """Return the shared target-selector decorator for one command family."""

    if project_only:
        return lambda function: function
    if native_only:
        return _native_credential_target_options
    return _credential_target_options


def _native_credential_target_options(function: Callable[..., None]) -> Callable[..., None]:
    """Attach the internal native-agent root selector to one credential command."""

    return click.option(
        "--native-agent-root",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        help=(
            f"Native-agent root to inspect or mutate. Defaults to `{NATIVE_AGENT_ROOT_ENV_VAR}`."
        ),
    )(function)


def _credential_target_options(function: Callable[..., None]) -> Callable[..., None]:
    """Attach the shared credential target selectors to one leaf command."""

    function = click.option(
        "--agent-def-dir",
        type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
        default=None,
        help="Manage only Houmao-owned credential artifacts in the selected plain agent-definition directory.",
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
    native_only: bool = False,
    use_project: bool,
    agent_def_dir: Path | None,
    native_agent_root: Path | None = None,
    allow_project_bootstrap: bool,
) -> CredentialTarget:
    """Resolve the storage target for one credential command."""

    cwd = Path.cwd().resolve()
    if project_only:
        return _resolve_project_target(cwd=cwd, allow_bootstrap=allow_project_bootstrap)
    if native_only:
        try:
            resolution = resolve_native_agent_root(
                cli_value=native_agent_root,
                base=cwd,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        return CredentialTarget.agent_def_dir_target(resolution.root)

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

    try:
        if allow_bootstrap:
            roots = ensure_project_aware_local_roots(cwd=cwd, project_dir=active_project_dir())
        else:
            roots = resolve_project_aware_local_roots(cwd=cwd, project_dir=active_project_dir())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
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


def _credential_command_doc(
    *,
    plain: str,
    project: str,
    native: str,
    project_only: bool,
    native_only: bool,
) -> str:
    """Return the command docstring for one routed credential command."""

    if project_only:
        return project
    if native_only:
        return native
    return plain


def _build_tool_group(*, tool: str, project_only: bool, native_only: bool = False) -> click.Group:
    """Build one tool-specific credential group."""

    display_name = _TOOL_DISPLAY_NAMES[tool]
    if project_only:
        help_text = f"Manage project-scoped {display_name} credentials in the active overlay."
    elif native_only:
        help_text = f"Manage direct native-agent {display_name} credentials."
    else:
        help_text = (
            f"Manage {display_name} credentials through either the active project overlay or "
            "a selected plain agent-definition directory."
        )

    @click.group(name=tool, help=help_text)
    def tool_group() -> None:
        """Tool-specific credential command group."""

    tool_group.add_command(
        _build_list_command(tool=tool, project_only=project_only, native_only=native_only)
    )
    tool_group.add_command(
        _build_get_command(tool=tool, project_only=project_only, native_only=native_only)
    )
    tool_group.add_command(
        _build_remove_command(tool=tool, project_only=project_only, native_only=native_only)
    )
    tool_group.add_command(
        _build_rename_command(tool=tool, project_only=project_only, native_only=native_only)
    )
    if tool == "claude":
        tool_group.add_command(
            _build_claude_add_command(project_only=project_only, native_only=native_only)
        )
        tool_group.add_command(
            _build_claude_set_command(project_only=project_only, native_only=native_only)
        )
        tool_group.add_command(
            _build_claude_login_command(project_only=project_only, native_only=native_only)
        )
    elif tool == "codex":
        tool_group.add_command(
            _build_codex_add_command(project_only=project_only, native_only=native_only)
        )
        tool_group.add_command(
            _build_codex_set_command(project_only=project_only, native_only=native_only)
        )
        tool_group.add_command(
            _build_codex_login_command(project_only=project_only, native_only=native_only)
        )
    elif tool == "kimi":
        tool_group.add_command(
            _build_kimi_add_command(project_only=project_only, native_only=native_only)
        )
        tool_group.add_command(
            _build_kimi_set_command(project_only=project_only, native_only=native_only)
        )
    else:
        raise click.ClickException(f"Unsupported credential tool `{tool}`.")
    return tool_group


def _build_list_command(
    *,
    tool: str,
    project_only: bool,
    native_only: bool = False,
) -> click.Command:
    """Build one `list` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="list")
    @_target_options(project_only, native_only=native_only)
    def list_command(
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """List credential names for one supported tool."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=False,
        )
        emit(_list_credentials_payload(target=target, tool=tool))

    list_command.__doc__ = _credential_command_doc(
        plain=f"List {display_name} credential names.",
        project=f"List project-scoped {display_name} credential names.",
        native=f"List direct native-agent {display_name} credential names.",
        project_only=project_only,
        native_only=native_only,
    )
    return list_command


def _build_get_command(
    *,
    tool: str,
    project_only: bool,
    native_only: bool = False,
) -> click.Command:
    """Build one `get` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="get")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    def get_command(
        name: str,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Inspect one credential safely as structured data."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=False,
        )
        emit(_describe_credential_bundle(target=target, tool=tool, name=name))

    get_command.__doc__ = _credential_command_doc(
        plain=f"Inspect one {display_name} credential safely.",
        project=f"Inspect one project-scoped {display_name} credential safely.",
        native=f"Inspect one direct native-agent {display_name} credential safely.",
        project_only=project_only,
        native_only=native_only,
    )
    return get_command


def _build_remove_command(
    *,
    tool: str,
    project_only: bool,
    native_only: bool = False,
) -> click.Command:
    """Build one `remove` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="remove")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name to remove.")
    def remove_command(
        name: str,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Remove one credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=False,
        )
        emit(_remove_credential_bundle(target=target, tool=tool, name=name))

    remove_command.__doc__ = _credential_command_doc(
        plain=f"Remove one {display_name} credential.",
        project=f"Remove one project-scoped {display_name} credential.",
        native=f"Remove one direct native-agent {display_name} credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return remove_command


def _build_rename_command(
    *,
    tool: str,
    project_only: bool,
    native_only: bool = False,
) -> click.Command:
    """Build one `rename` command for a supported tool."""

    display_name = _TOOL_DISPLAY_NAMES[tool]

    @click.command(name="rename")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Existing credential name.")
    @click.option("--to", "new_name", required=True, help="New credential name.")
    def rename_command(
        name: str,
        new_name: str,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Rename one credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=False,
        )
        emit(_rename_credential_bundle(target=target, tool=tool, name=name, new_name=new_name))

    rename_command.__doc__ = _credential_command_doc(
        plain=f"Rename one {display_name} credential.",
        project=f"Rename one project-scoped {display_name} credential.",
        native=f"Rename one direct native-agent {display_name} credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return rename_command


def _build_claude_add_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Claude `add` command."""

    @click.command(name="add")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `ANTHROPIC_API_KEY`.")
    @click.option("--auth-token", default=None, help="Value for `ANTHROPIC_AUTH_TOKEN`.")
    @click.option("--oauth-token", default=None, help="Value for `CLAUDE_CODE_OAUTH_TOKEN`.")
    @click.option("--base-url", default=None, help="Value for `ANTHROPIC_BASE_URL`.")
    @click.option("--model", default=None, help="Value for `ANTHROPIC_MODEL`.")
    @click.option(
        "--small-fast-model", default=None, help="Value for `ANTHROPIC_SMALL_FAST_MODEL`."
    )
    @click.option("--subagent-model", default=None, help="Value for `CLAUDE_CODE_SUBAGENT_MODEL`.")
    @click.option(
        "--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`."
    )
    @click.option(
        "--default-sonnet-model", default=None, help="Value for `ANTHROPIC_DEFAULT_SONNET_MODEL`."
    )
    @click.option(
        "--default-haiku-model", default=None, help="Value for `ANTHROPIC_DEFAULT_HAIKU_MODEL`."
    )
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
        native_agent_root: Path | None = None,
    ) -> None:
        """Create one Claude credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
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

    add_command.__doc__ = _credential_command_doc(
        plain="Create one Claude credential.",
        project="Create one project-scoped Claude credential.",
        native="Create one direct native-agent Claude credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return add_command


def _build_claude_set_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Claude `set` command."""

    @click.command(name="set")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `ANTHROPIC_API_KEY`.")
    @click.option("--auth-token", default=None, help="Value for `ANTHROPIC_AUTH_TOKEN`.")
    @click.option("--oauth-token", default=None, help="Value for `CLAUDE_CODE_OAUTH_TOKEN`.")
    @click.option("--base-url", default=None, help="Value for `ANTHROPIC_BASE_URL`.")
    @click.option("--model", default=None, help="Value for `ANTHROPIC_MODEL`.")
    @click.option(
        "--small-fast-model", default=None, help="Value for `ANTHROPIC_SMALL_FAST_MODEL`."
    )
    @click.option("--subagent-model", default=None, help="Value for `CLAUDE_CODE_SUBAGENT_MODEL`.")
    @click.option(
        "--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`."
    )
    @click.option(
        "--default-sonnet-model", default=None, help="Value for `ANTHROPIC_DEFAULT_SONNET_MODEL`."
    )
    @click.option(
        "--default-haiku-model", default=None, help="Value for `ANTHROPIC_DEFAULT_HAIKU_MODEL`."
    )
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
    @click.option(
        "--clear-api-key",
        is_flag=True,
        help="Remove `ANTHROPIC_API_KEY` from the credential bundle.",
    )
    @click.option(
        "--clear-auth-token",
        is_flag=True,
        help="Remove `ANTHROPIC_AUTH_TOKEN` from the credential bundle.",
    )
    @click.option(
        "--clear-oauth-token",
        is_flag=True,
        help="Remove `CLAUDE_CODE_OAUTH_TOKEN` from the credential bundle.",
    )
    @click.option(
        "--clear-base-url",
        is_flag=True,
        help="Remove `ANTHROPIC_BASE_URL` from the credential bundle.",
    )
    @click.option(
        "--clear-model", is_flag=True, help="Remove `ANTHROPIC_MODEL` from the credential bundle."
    )
    @click.option(
        "--clear-small-fast-model",
        is_flag=True,
        help="Remove `ANTHROPIC_SMALL_FAST_MODEL` from the credential bundle.",
    )
    @click.option(
        "--clear-subagent-model",
        is_flag=True,
        help="Remove `CLAUDE_CODE_SUBAGENT_MODEL` from the credential bundle.",
    )
    @click.option(
        "--clear-default-opus-model",
        is_flag=True,
        help="Remove `ANTHROPIC_DEFAULT_OPUS_MODEL` from the credential bundle.",
    )
    @click.option(
        "--clear-default-sonnet-model",
        is_flag=True,
        help="Remove `ANTHROPIC_DEFAULT_SONNET_MODEL` from the credential bundle.",
    )
    @click.option(
        "--clear-default-haiku-model",
        is_flag=True,
        help="Remove `ANTHROPIC_DEFAULT_HAIKU_MODEL` from the credential bundle.",
    )
    @click.option(
        "--clear-state-template-file",
        is_flag=True,
        help="Remove optional `files/claude_state.template.json` bootstrap state from the credential bundle.",
    )
    @click.option(
        "--clear-config-dir",
        is_flag=True,
        help="Remove imported Claude vendor login-state files from the credential bundle.",
    )
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
        native_agent_root: Path | None = None,
    ) -> None:
        """Update one Claude credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
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

    set_command.__doc__ = _credential_command_doc(
        plain="Update one Claude credential.",
        project="Update one project-scoped Claude credential.",
        native="Update one direct native-agent Claude credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return set_command


def _build_codex_add_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Codex `add` command."""

    @click.command(name="add")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `OPENAI_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `OPENAI_BASE_URL`.")
    @click.option("--org-id", default=None, help="Value for `OPENAI_ORG_ID`.")
    @click.option(
        "--auth-json",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Codex `auth.json` login-state file to copy into the credential bundle without mutating the source file.",
    )
    def add_command(
        name: str,
        api_key: str | None,
        base_url: str | None,
        org_id: str | None,
        auth_json: Path | None,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Create one Codex credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
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

    add_command.__doc__ = _credential_command_doc(
        plain="Create one Codex credential.",
        project="Create one project-scoped Codex credential.",
        native="Create one direct native-agent Codex credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return add_command


def _build_codex_set_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Codex `set` command."""

    @click.command(name="set")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--api-key", default=None, help="Value for `OPENAI_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `OPENAI_BASE_URL`.")
    @click.option("--org-id", default=None, help="Value for `OPENAI_ORG_ID`.")
    @click.option(
        "--auth-json",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Codex `auth.json` login-state file to copy into the credential bundle without mutating the source file.",
    )
    @click.option(
        "--clear-api-key", is_flag=True, help="Remove `OPENAI_API_KEY` from the credential bundle."
    )
    @click.option(
        "--clear-base-url",
        is_flag=True,
        help="Remove `OPENAI_BASE_URL` from the credential bundle.",
    )
    @click.option(
        "--clear-org-id", is_flag=True, help="Remove `OPENAI_ORG_ID` from the credential bundle."
    )
    @click.option(
        "--clear-auth-json",
        is_flag=True,
        help="Remove `files/auth.json` from the credential bundle.",
    )
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
        native_agent_root: Path | None = None,
    ) -> None:
        """Update one Codex credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
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

    set_command.__doc__ = _credential_command_doc(
        plain="Update one Codex credential.",
        project="Update one project-scoped Codex credential.",
        native="Update one direct native-agent Codex credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return set_command


def _build_kimi_add_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Kimi `add` command."""

    @click.command(name="add")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--model-name", default=None, help="Value for `KIMI_MODEL_NAME`.")
    @click.option("--api-key", default=None, help="Value for `KIMI_MODEL_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `KIMI_MODEL_BASE_URL`.")
    @click.option(
        "--provider-type",
        default=None,
        help="Value for `KIMI_MODEL_PROVIDER_TYPE`.",
    )
    @click.option("--code-base-url", default=None, help="Value for `KIMI_CODE_BASE_URL`.")
    @click.option("--code-oauth-host", default=None, help="Value for `KIMI_CODE_OAUTH_HOST`.")
    @click.option("--oauth-host", default=None, help="Value for `KIMI_OAUTH_HOST`.")
    @click.option(
        "--disable-telemetry",
        is_flag=True,
        help="Store `KIMI_DISABLE_TELEMETRY=true` in the credential bundle env file.",
    )
    @click.option(
        "--config-toml",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Kimi `config.toml` file.",
    )
    @click.option(
        "--credential-json",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Kimi `credentials/kimi-code.json` file.",
    )
    @click.option(
        "--code-home",
        type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
        default=None,
        help="Optional Kimi Code home to import `config.toml` and `credentials/kimi-code.json` from.",
    )
    def add_command(
        name: str,
        model_name: str | None,
        api_key: str | None,
        base_url: str | None,
        provider_type: str | None,
        code_base_url: str | None,
        code_oauth_host: str | None,
        oauth_host: str | None,
        disable_telemetry: bool,
        config_toml: Path | None,
        credential_json: Path | None,
        code_home: Path | None,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Create one Kimi credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=True,
        )
        emit(
            _write_credential_bundle(
                target=target,
                tool="kimi",
                name=name,
                env_values=_compact_env_values(
                    {
                        "KIMI_MODEL_NAME": model_name,
                        "KIMI_MODEL_API_KEY": api_key,
                        "KIMI_MODEL_BASE_URL": base_url,
                        "KIMI_MODEL_PROVIDER_TYPE": provider_type,
                        "KIMI_CODE_BASE_URL": code_base_url,
                        "KIMI_CODE_OAUTH_HOST": code_oauth_host,
                        "KIMI_OAUTH_HOST": oauth_host,
                        "KIMI_DISABLE_TELEMETRY": "true" if disable_telemetry else None,
                    }
                ),
                file_sources=_kimi_credential_file_sources(
                    config_toml=config_toml,
                    credential_json=credential_json,
                    code_home=code_home,
                ),
                require_any_input=True,
                operation="add",
                clear_env_names=set(),
                clear_file_sources=set(),
            )
        )

    add_command.__doc__ = _credential_command_doc(
        plain="Create one Kimi credential.",
        project="Create one project-scoped Kimi credential.",
        native="Create one direct native-agent Kimi credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return add_command


def _build_kimi_set_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Kimi `set` command."""

    @click.command(name="set")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option("--model-name", default=None, help="Value for `KIMI_MODEL_NAME`.")
    @click.option("--api-key", default=None, help="Value for `KIMI_MODEL_API_KEY`.")
    @click.option("--base-url", default=None, help="Value for `KIMI_MODEL_BASE_URL`.")
    @click.option(
        "--provider-type",
        default=None,
        help="Value for `KIMI_MODEL_PROVIDER_TYPE`.",
    )
    @click.option("--code-base-url", default=None, help="Value for `KIMI_CODE_BASE_URL`.")
    @click.option("--code-oauth-host", default=None, help="Value for `KIMI_CODE_OAUTH_HOST`.")
    @click.option("--oauth-host", default=None, help="Value for `KIMI_OAUTH_HOST`.")
    @click.option(
        "--disable-telemetry",
        is_flag=True,
        help="Store `KIMI_DISABLE_TELEMETRY=true` in the credential bundle env file.",
    )
    @click.option(
        "--config-toml",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Kimi `config.toml` file.",
    )
    @click.option(
        "--credential-json",
        type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
        default=None,
        help="Optional Kimi `credentials/kimi-code.json` file.",
    )
    @click.option(
        "--code-home",
        type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
        default=None,
        help="Optional Kimi Code home to import `config.toml` and `credentials/kimi-code.json` from.",
    )
    @click.option(
        "--clear-model-name",
        is_flag=True,
        help="Remove `KIMI_MODEL_NAME` from the credential bundle.",
    )
    @click.option(
        "--clear-api-key",
        is_flag=True,
        help="Remove `KIMI_MODEL_API_KEY` from the credential bundle.",
    )
    @click.option(
        "--clear-base-url",
        is_flag=True,
        help="Remove `KIMI_MODEL_BASE_URL` from the credential bundle.",
    )
    @click.option(
        "--clear-provider-type",
        is_flag=True,
        help="Remove `KIMI_MODEL_PROVIDER_TYPE` from the credential bundle.",
    )
    @click.option(
        "--clear-code-base-url",
        is_flag=True,
        help="Remove `KIMI_CODE_BASE_URL` from the credential bundle.",
    )
    @click.option(
        "--clear-code-oauth-host",
        is_flag=True,
        help="Remove `KIMI_CODE_OAUTH_HOST` from the credential bundle.",
    )
    @click.option(
        "--clear-oauth-host",
        is_flag=True,
        help="Remove `KIMI_OAUTH_HOST` from the credential bundle.",
    )
    @click.option(
        "--clear-disable-telemetry",
        is_flag=True,
        help="Remove `KIMI_DISABLE_TELEMETRY` from the credential bundle.",
    )
    @click.option(
        "--clear-config-toml",
        is_flag=True,
        help="Remove `files/config.toml` from the credential bundle.",
    )
    @click.option(
        "--clear-credential-json",
        is_flag=True,
        help="Remove `files/credentials/kimi-code.json` from the credential bundle.",
    )
    def set_command(
        name: str,
        model_name: str | None,
        api_key: str | None,
        base_url: str | None,
        provider_type: str | None,
        code_base_url: str | None,
        code_oauth_host: str | None,
        oauth_host: str | None,
        disable_telemetry: bool,
        config_toml: Path | None,
        credential_json: Path | None,
        code_home: Path | None,
        clear_model_name: bool,
        clear_api_key: bool,
        clear_base_url: bool,
        clear_provider_type: bool,
        clear_code_base_url: bool,
        clear_code_oauth_host: bool,
        clear_oauth_host: bool,
        clear_disable_telemetry: bool,
        clear_config_toml: bool,
        clear_credential_json: bool,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Update one Kimi credential."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=True,
        )
        emit(
            _write_credential_bundle(
                target=target,
                tool="kimi",
                name=name,
                env_values=_compact_env_values(
                    {
                        "KIMI_MODEL_NAME": model_name,
                        "KIMI_MODEL_API_KEY": api_key,
                        "KIMI_MODEL_BASE_URL": base_url,
                        "KIMI_MODEL_PROVIDER_TYPE": provider_type,
                        "KIMI_CODE_BASE_URL": code_base_url,
                        "KIMI_CODE_OAUTH_HOST": code_oauth_host,
                        "KIMI_OAUTH_HOST": oauth_host,
                        "KIMI_DISABLE_TELEMETRY": "true" if disable_telemetry else None,
                    }
                ),
                file_sources=_kimi_credential_file_sources(
                    config_toml=config_toml,
                    credential_json=credential_json,
                    code_home=code_home,
                ),
                require_any_input=True,
                operation="set",
                clear_env_names=_flagged_items(
                    {
                        "KIMI_MODEL_NAME": clear_model_name,
                        "KIMI_MODEL_API_KEY": clear_api_key,
                        "KIMI_MODEL_BASE_URL": clear_base_url,
                        "KIMI_MODEL_PROVIDER_TYPE": clear_provider_type,
                        "KIMI_CODE_BASE_URL": clear_code_base_url,
                        "KIMI_CODE_OAUTH_HOST": clear_code_oauth_host,
                        "KIMI_OAUTH_HOST": clear_oauth_host,
                        "KIMI_DISABLE_TELEMETRY": clear_disable_telemetry,
                    }
                ),
                clear_file_sources=_flagged_items(
                    {
                        _KIMI_CONFIG_FILENAME: clear_config_toml,
                        _KIMI_CREDENTIAL_JSON_SOURCE: clear_credential_json,
                    }
                ),
            )
        )

    set_command.__doc__ = _credential_command_doc(
        plain="Update one Kimi credential.",
        project="Update one project-scoped Kimi credential.",
        native="Update one direct native-agent Kimi credential.",
        project_only=project_only,
        native_only=native_only,
    )
    return set_command


def _build_codex_login_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Codex `login` command."""

    @click.command(name="login")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option(
        "--update",
        is_flag=True,
        help="Update an existing credential instead of creating a new one.",
    )
    @click.option(
        "--keep-temp-home",
        is_flag=True,
        help="Keep the temporary Codex home after a successful import.",
    )
    @click.option(
        "--inherit-auth-env",
        is_flag=True,
        help="Do not scrub ambient Codex auth-related environment variables for the login process.",
    )
    @click.option(
        "--browser",
        "use_browser_login",
        is_flag=True,
        help="Use ordinary Codex browser login instead of the default device-auth login.",
    )
    def login_command(
        name: str,
        update: bool,
        keep_temp_home: bool,
        inherit_auth_env: bool,
        use_browser_login: bool,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Run Codex login in an isolated temp home and import `auth.json`."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=True,
        )
        emit(
            _login_and_import_credential(
                target=target,
                tool="codex",
                name=name,
                operation="set" if update else "add",
                keep_temp_home=keep_temp_home,
                inherit_auth_env=inherit_auth_env,
                provider_login_factory=lambda temp_home: _codex_provider_login(
                    temp_home=temp_home,
                    use_browser_login=use_browser_login,
                ),
            )
        )

    login_command.__doc__ = _credential_command_doc(
        plain="Log in to Codex in an isolated temp home and import `auth.json`.",
        project=("Log in to Codex in an isolated temp home and import project-scoped `auth.json`."),
        native=(
            "Log in to Codex in an isolated temp home and import direct native-agent `auth.json`."
        ),
        project_only=project_only,
        native_only=native_only,
    )
    return login_command


def _build_claude_login_command(*, project_only: bool, native_only: bool = False) -> click.Command:
    """Build the Claude `login` command."""

    @click.command(name="login")
    @_target_options(project_only, native_only=native_only)
    @click.option("--name", required=True, help="Credential name.")
    @click.option(
        "--update",
        is_flag=True,
        help="Update an existing credential instead of creating a new one.",
    )
    @click.option(
        "--keep-temp-home",
        is_flag=True,
        help="Keep the temporary Claude config home after a successful import.",
    )
    @click.option(
        "--inherit-auth-env",
        is_flag=True,
        help="Do not scrub ambient Claude auth-related environment variables for the login process.",
    )
    @click.option("--claudeai", is_flag=True, help="Pass `--claudeai` to `claude auth login`.")
    @click.option(
        "--console",
        "use_console",
        is_flag=True,
        help="Pass `--console` to `claude auth login`.",
    )
    @click.option("--email", default=None, help="Pass `--email <value>` to `claude auth login`.")
    @click.option("--sso", is_flag=True, help="Pass `--sso` to `claude auth login`.")
    def login_command(
        name: str,
        update: bool,
        keep_temp_home: bool,
        inherit_auth_env: bool,
        claudeai: bool,
        use_console: bool,
        email: str | None,
        sso: bool,
        use_project: bool = False,
        agent_def_dir: Path | None = None,
        native_agent_root: Path | None = None,
    ) -> None:
        """Run Claude login in an isolated config home and import vendor state."""

        target = _resolve_command_target(
            project_only=project_only,
            native_only=native_only,
            use_project=use_project,
            agent_def_dir=agent_def_dir,
            native_agent_root=native_agent_root,
            allow_project_bootstrap=True,
        )
        emit(
            _login_and_import_credential(
                target=target,
                tool="claude",
                name=name,
                operation="set" if update else "add",
                keep_temp_home=keep_temp_home,
                inherit_auth_env=inherit_auth_env,
                provider_login_factory=lambda temp_home: _claude_provider_login(
                    temp_home=temp_home,
                    claudeai=claudeai,
                    use_console=use_console,
                    email=email,
                    sso=sso,
                ),
            )
        )

    login_command.__doc__ = _credential_command_doc(
        plain="Log in to Claude in an isolated config home and import vendor state.",
        project=(
            "Log in to Claude in an isolated config home and import project-scoped vendor state."
        ),
        native=(
            "Log in to Claude in an isolated config home and import direct native-agent "
            "vendor state."
        ),
        project_only=project_only,
        native_only=native_only,
    )
    return login_command


def _login_and_import_credential(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
    operation: CredentialLoginOperation,
    keep_temp_home: bool,
    inherit_auth_env: bool,
    provider_login_factory: Callable[[Path], CredentialProviderLogin],
) -> dict[str, object]:
    """Run one provider login flow in an isolated home and import its artifact."""

    resolved_name = _require_non_empty_name(name, field_name="--name")
    _ensure_login_import_allowed(
        target=target,
        tool=tool,
        name=resolved_name,
        operation=operation,
    )
    temp_home = Path(tempfile.mkdtemp(prefix=f"houmao-{tool}-login-")).resolve()
    temp_home.chmod(0o700)
    login = provider_login_factory(temp_home)
    success = False
    try:
        _run_provider_login(
            tool=tool,
            temp_home=temp_home,
            login=login,
            inherit_auth_env=inherit_auth_env,
        )
        if tool == "claude":
            _add_optional_claude_login_state(
                temp_home=temp_home,
                artifact_sources=login.artifact_sources,
            )
        _validate_provider_artifacts(
            tool=tool,
            temp_home=temp_home,
            artifact_sources=login.artifact_sources,
        )
        payload = _write_credential_bundle(
            target=target,
            tool=tool,
            name=resolved_name,
            env_values={},
            file_sources=login.artifact_sources,
            require_any_input=True,
            operation=operation,
            clear_env_names=set(),
            clear_file_sources=set(_CLAUDE_VENDOR_LOGIN_FILE_SOURCES)
            if tool == "claude"
            else set(),
        )
        success = True
    except click.ClickException as exc:
        raise click.ClickException(
            f"{exc.message} Temporary {tool} login home preserved: {temp_home}"
        ) from exc
    finally:
        if success and not keep_temp_home:
            shutil.rmtree(temp_home)

    payload["login"] = {
        "provider": tool,
        "provider_command": login.command,
        "temp_home": str(temp_home),
        "temp_home_deleted": not keep_temp_home,
        "inherited_auth_env": inherit_auth_env,
    }
    return payload


def _ensure_login_import_allowed(
    *,
    target: CredentialTarget,
    tool: str,
    name: str,
    operation: CredentialLoginOperation,
) -> None:
    """Fail before provider login when the requested add/set import is impossible."""

    if operation == "set":
        _resolve_existing_credential_source_root(
            target=target,
            tool=tool,
            name=name,
            operation="set",
        )
        return

    if operation != "add":
        raise click.ClickException(f"Unsupported credential login operation: {operation}")

    if target.kind == "project":
        assert target.overlay is not None
        if (
            _load_project_auth_profile_optional(overlay=target.overlay, tool=tool, name=name)
            is not None
        ):
            raise click.ClickException(
                f"Credential bundle already exists for `{tool}`: `{name}`. Use `--update` to replace it."
            )
        return

    assert target.agent_def_dir is not None
    bundle_root = _direct_auth_bundle_root(agent_def_dir=target.agent_def_dir, tool=tool, name=name)
    if bundle_root.exists():
        raise click.ClickException(
            f"Credential bundle already exists: {bundle_root}. Use `--update` to replace it."
        )


def _run_provider_login(
    *,
    tool: str,
    temp_home: Path,
    login: CredentialProviderLogin,
    inherit_auth_env: bool,
) -> None:
    """Run one provider login command with inherited stdio."""

    env = _provider_login_env(
        tool=tool,
        temp_home=temp_home,
        login=login,
        inherit_auth_env=inherit_auth_env,
    )
    try:
        completed = subprocess.run(login.command, env=env, check=False)
    except FileNotFoundError as exc:
        raise click.ClickException(
            f"Provider login command not found for `{tool}`: `{login.command[0]}`."
        ) from exc
    if completed.returncode != 0:
        rendered_command = " ".join(login.command)
        raise click.ClickException(
            f"Provider login command failed for `{tool}` with exit code {completed.returncode}: {rendered_command}."
        )


def _provider_login_env(
    *,
    tool: str,
    temp_home: Path,
    login: CredentialProviderLogin,
    inherit_auth_env: bool,
) -> dict[str, str]:
    """Build the provider login environment."""

    env = dict(os.environ)
    if not inherit_auth_env:
        for env_name in _PROVIDER_AUTH_ENV_VARS[tool]:
            env.pop(env_name, None)
    env[login.temp_home_env_var] = str(temp_home)
    env.update(login.extra_env)
    return env


def _validate_provider_artifacts(
    *,
    tool: str,
    temp_home: Path,
    artifact_sources: dict[str, Path],
) -> None:
    """Validate provider login artifacts before importing them."""

    missing_artifacts = [
        source_name
        for source_name, source_path in artifact_sources.items()
        if not source_path.is_file()
    ]
    if missing_artifacts:
        raise click.ClickException(
            "Provider login did not create the expected auth artifact(s) for "
            f"`{tool}` under `{temp_home}`: {', '.join(missing_artifacts)}."
        )


def _add_optional_claude_login_state(
    *,
    temp_home: Path,
    artifact_sources: dict[str, Path],
) -> None:
    """Add optional Claude companion login state after the provider command runs."""

    global_state_path = (temp_home / _CLAUDE_VENDOR_GLOBAL_STATE_FILENAME).resolve()
    if global_state_path.is_file():
        artifact_sources[_CLAUDE_VENDOR_GLOBAL_STATE_FILENAME] = global_state_path


def _codex_provider_login(*, temp_home: Path, use_browser_login: bool) -> CredentialProviderLogin:
    """Return the Codex provider login command and artifact mapping."""

    command = ["codex", "login"] if use_browser_login else ["codex", "login", "--device-auth"]
    return CredentialProviderLogin(
        command=command,
        temp_home_env_var=_PROVIDER_HOME_ENV_VARS["codex"],
        artifact_sources={"auth.json": (temp_home / "auth.json").resolve()},
        extra_env={},
    )


def _claude_provider_login(
    *,
    temp_home: Path,
    claudeai: bool,
    use_console: bool,
    email: str | None,
    sso: bool,
) -> CredentialProviderLogin:
    """Return the Claude provider login command and artifact mapping."""

    command = ["claude", "auth", "login"]
    if claudeai:
        command.append("--claudeai")
    if use_console:
        command.append("--console")
    if email is not None and email.strip():
        command.extend(["--email", email.strip()])
    if sso:
        command.append("--sso")
    return CredentialProviderLogin(
        command=command,
        temp_home_env_var=_PROVIDER_HOME_ENV_VARS["claude"],
        artifact_sources={
            _CLAUDE_VENDOR_CREDENTIALS_FILENAME: (
                temp_home / _CLAUDE_VENDOR_CREDENTIALS_FILENAME
            ).resolve(),
        },
        extra_env={},
    )


def _list_credentials_payload(*, target: CredentialTarget, tool: str) -> dict[str, object]:
    """Return one structured credential listing payload."""

    if target.kind == "project":
        assert target.overlay is not None
        profiles = ProjectCatalog.from_overlay(target.overlay).list_auth_profiles(tool=tool)
        return {
            "target_kind": "project",
            "project_root": str(target.overlay.project_root),
            "tool": tool,
            "credentials": [profile.display_name for profile in profiles],
            "credential_records": [
                {
                    "tool": profile.tool,
                    "name": profile.display_name,
                    "updated_at_utc": profile.updated_at_utc,
                    "updated_at_source": "project_catalog",
                }
                for profile in profiles
            ],
        }

    assert target.agent_def_dir is not None
    auth_root = _agent_def_dir_auth_root(agent_def_dir=target.agent_def_dir, tool=tool)
    credential_paths = (
        sorted(path for path in auth_root.iterdir() if path.is_dir()) if auth_root.is_dir() else []
    )
    return {
        "target_kind": "agent_def_dir",
        "agent_def_dir": str(target.agent_def_dir),
        "tool": tool,
        "credentials": [path.name for path in credential_paths],
        "credential_records": [
            {
                "tool": tool,
                "name": path.name,
                "updated_at_utc": _filesystem_updated_at_utc(path),
                "updated_at_source": "filesystem_metadata",
            }
            for path in credential_paths
        ],
    }


def _filesystem_updated_at_utc(path: Path) -> str:
    """Return one best-effort filesystem update timestamp for a credential bundle."""

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


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
    if not bundle_root.exists() and not bundle_root.is_symlink():
        raise click.ClickException(f"Credential bundle not found: {bundle_root}")
    remove_tree_or_path(
        bundle_root,
        allowed_roots=(_agent_def_dir_auth_root(agent_def_dir=target.agent_def_dir, tool=tool),),
    )
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
        rewrites = _collect_direct_dir_auth_reference_rewrites(
            agent_def_dir=target.overlay.agents_root,
            tool=tool,
            old_name=resolved_name,
            new_name=resolved_new_name,
        )
        rewritten_files: list[str] = []
        for path, payload in rewrites:
            _write_yaml_mapping(path, payload)
            rewritten_files.append(str(path))
        return {
            "target_kind": "project",
            "project_root": str(target.overlay.project_root),
            "tool": tool,
            "name": renamed.display_name,
            "previous_name": resolved_name,
            "bundle_ref": renamed.bundle_ref,
            "path": str(renamed.resolved_projection_path(target.overlay)),
            "rewritten_files": rewritten_files,
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
    direct_rewritten_files: list[str] = []
    for path, payload in rewrites:
        _write_yaml_mapping(path, payload)
        direct_rewritten_files.append(str(path))
    return {
        "target_kind": "agent_def_dir",
        "agent_def_dir": str(target.agent_def_dir),
        "tool": tool,
        "name": resolved_new_name,
        "previous_name": resolved_name,
        "path": str(destination_root),
        "rewritten_files": direct_rewritten_files,
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
                updated_payload = _updated_auth_reference_payload(
                    agent_def_dir=agent_def_dir,
                    payload=payload,
                    tool=tool,
                    old_name=old_name,
                    new_name=new_name,
                )
                if updated_payload is None:
                    continue
                rewrites.append((path.resolve(), updated_payload))
    return rewrites


def _updated_auth_reference_payload(
    *,
    agent_def_dir: Path,
    payload: dict[str, object],
    tool: str,
    old_name: str,
    new_name: str,
) -> dict[str, object] | None:
    """Return one YAML payload with renamed auth reference when it matches the tool."""

    if str(payload.get("tool")) == tool and str(payload.get("auth")) == old_name:
        updated_payload = dict(payload)
        updated_payload["auth"] = new_name
        return updated_payload

    defaults = payload.get("defaults")
    if not isinstance(defaults, dict) or str(defaults.get("auth")) != old_name:
        return None
    if _launch_dossier_tool(agent_def_dir=agent_def_dir, payload=payload) != tool:
        return None
    updated_payload = dict(payload)
    updated_defaults = dict(defaults)
    updated_defaults["auth"] = new_name
    updated_payload["defaults"] = updated_defaults
    return updated_payload


def _launch_dossier_tool(*, agent_def_dir: Path, payload: dict[str, object]) -> str | None:
    """Infer one launch dossier's tool from its source recipe."""

    source = payload.get("source")
    if not isinstance(source, dict):
        return None
    if source.get("kind") != "recipe":
        return None
    recipe_name = str(source.get("name") or "").strip()
    if not recipe_name:
        return None
    recipe_path = (agent_def_dir / "presets" / f"{recipe_name}.yaml").resolve()
    if not recipe_path.is_file():
        return None
    try:
        return str(parse_agent_preset(recipe_path).tool)
    except Exception:
        return None


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

    unsupported_env_keys = sorted(
        (set(env_values) | clear_env_names) - set(adapter.auth_env_allowlist)
    )
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
            target_path = files_root / source_name
            remove_tree_or_path(target_path, allowed_roots=(files_root,))

        for source_name, source_path in file_sources.items():
            destination_path = files_root / source_name
            replace_file(
                source=source_path.resolve(),
                destination=destination_path,
                allowed_roots=(files_root,),
            )

        for mapping in adapter.auth_file_mappings:
            if mapping.required and not (files_root / mapping.source).exists():
                raise click.ClickException(
                    f"Missing required auth file `{mapping.source}` for `{tool}` credential "
                    f"`{resolved_name}`."
                )

        replace_path_with_text(
            destination=env_file_path,
            text=_render_env_file(
                env_values=merged_env_values,
                allowlist=adapter.auth_env_allowlist,
            ),
            allowed_roots=(temp_auth_root,),
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
                str((projection_files_root / source_name).resolve())
                for source_name in sorted(file_sources)
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

    return agent_def_dir.resolve() / "tools" / tool / "auth"


def _direct_auth_bundle_root(*, agent_def_dir: Path, tool: str, name: str) -> Path:
    """Return one plain-directory credential root."""

    return _agent_def_dir_auth_root(agent_def_dir=agent_def_dir, tool=tool) / name


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


def _kimi_credential_file_sources(
    *,
    config_toml: Path | None,
    credential_json: Path | None,
    code_home: Path | None,
) -> dict[str, Path]:
    """Resolve Kimi credential file sources from optional inputs."""

    if code_home is not None and (config_toml is not None or credential_json is not None):
        raise click.ClickException(
            "`--code-home` cannot be combined with `--config-toml` or `--credential-json`."
        )

    if code_home is not None:
        resolved_home = code_home.resolve()
        imported_sources: dict[str, Path] = {}
        config_path = (resolved_home / _KIMI_CONFIG_FILENAME).resolve()
        if config_path.is_file():
            imported_sources[_KIMI_CONFIG_FILENAME] = config_path
        credential_path = (resolved_home / _KIMI_CREDENTIAL_JSON_SOURCE).resolve()
        if not credential_path.is_file():
            raise click.ClickException(
                "Kimi Code home does not contain the required OAuth credential file "
                f"`{credential_path}`."
            )
        imported_sources[_KIMI_CREDENTIAL_JSON_SOURCE] = credential_path
        return imported_sources

    file_sources: dict[str, Path] = {}
    if config_toml is not None:
        file_sources[_KIMI_CONFIG_FILENAME] = config_toml
    if credential_json is not None:
        file_sources[_KIMI_CREDENTIAL_JSON_SOURCE] = credential_json
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

    lines = [
        f"{env_name}={env_values[env_name]}" for env_name in allowlist if env_name in env_values
    ]
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
    native_agent_credentials_group.add_command(
        _build_tool_group(tool=_tool_name, project_only=False, native_only=True)
    )
