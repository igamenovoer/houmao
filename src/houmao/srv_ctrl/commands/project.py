"""Repo-local project-overlay commands for `houmao-mgr`."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from houmao.agents.definition_parser import AuthFileMapping, ToolAdapter, parse_tool_adapter
from houmao.project.overlay import (
    HoumaoProjectOverlay,
    bootstrap_project_overlay,
    discover_project_overlay,
    resolve_project_aware_agent_def_dir,
)

from .common import emit_json

_SECRET_ENV_TOKENS: tuple[str, ...] = ("KEY", "TOKEN", "SECRET", "PASSWORD")


@click.group(name="project")
def project_group() -> None:
    """Local repo-local Houmao project-overlay administration."""


@project_group.command(name="init")
def init_project_command() -> None:
    """Create or validate the local `.houmao/` project overlay in the current directory."""

    cwd = Path.cwd().resolve()
    try:
        result = bootstrap_project_overlay(cwd)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    emit_json(
        {
            "project_root": str(result.project_overlay.project_root),
            "overlay_root": str(result.project_overlay.overlay_root),
            "config_path": str(result.project_overlay.config_path),
            "agent_def_dir": str(result.project_overlay.agent_def_dir),
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
            "effective_agent_def_dir": str(resolution.agent_def_dir),
            "effective_agent_def_dir_source": resolution.source,
        }
    )


@project_group.group(name="agent-tools")
def agent_tools_group() -> None:
    """Manage project-local tool content under `.houmao/agents/tools/`."""


@agent_tools_group.group(name="claude")
def claude_tool_group() -> None:
    """Manage the project-local Claude tool subtree."""


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
@click.option("--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`.")
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
@click.option("--default-opus-model", default=None, help="Value for `ANTHROPIC_DEFAULT_OPUS_MODEL`.")
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
@click.option("--clear-api-key", is_flag=True, help="Remove `ANTHROPIC_API_KEY` from the auth bundle.")
@click.option(
    "--clear-auth-token",
    is_flag=True,
    help="Remove `ANTHROPIC_AUTH_TOKEN` from the auth bundle.",
)
@click.option("--clear-base-url", is_flag=True, help="Remove `ANTHROPIC_BASE_URL` from the auth bundle.")
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


@agent_tools_group.group(name="codex")
def codex_tool_group() -> None:
    """Manage the project-local Codex tool subtree."""


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
@click.option("--clear-base-url", is_flag=True, help="Remove `OPENAI_BASE_URL` from the auth bundle.")
@click.option("--clear-org-id", is_flag=True, help="Remove `OPENAI_ORG_ID` from the auth bundle.")
@click.option(
    "--clear-auth-json",
    is_flag=True,
    help="Remove `files/auth.json` from the auth bundle.",
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


@agent_tools_group.group(name="gemini")
def gemini_tool_group() -> None:
    """Manage the project-local Gemini tool subtree."""


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
    "--clear-google-api-key",
    is_flag=True,
    help="Remove `GOOGLE_API_KEY` from the auth bundle.",
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


def _require_project_overlay() -> HoumaoProjectOverlay:
    """Return the discovered project overlay or raise one operator-facing error."""

    cwd = Path.cwd().resolve()
    try:
        project_overlay = discover_project_overlay(cwd)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if project_overlay is None:
        raise click.ClickException(
            "No local Houmao project overlay was discovered from the current directory. "
            "Run `houmao-mgr project init` first."
        )
    return project_overlay


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


def _list_tool_bundle_names(*, overlay: HoumaoProjectOverlay, tool: str) -> list[str]:
    """Return the existing auth bundle names for one tool."""

    auth_root = (overlay.agent_def_dir / "tools" / tool / "auth").resolve()
    if not auth_root.is_dir():
        return []
    return sorted(path.name for path in auth_root.iterdir() if path.is_dir())


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

    if require_any_input and not env_values and not file_sources and not clear_env_names and not clear_file_sources:
        raise click.ClickException(
            f"Provide at least one auth input for `{tool}` (env value or compatible auth file)."
        )
    if operation == "set" and not env_values and not file_sources and not clear_env_names and not clear_file_sources:
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
            f"Unsupported auth file(s) for `{tool}` auth bundles: "
            f"{', '.join(unsupported_file_sources)}"
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
        "written_env_vars": [name for name in adapter.auth_env_allowlist if name in merged_env_values],
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


def _load_overlay_tool_adapter(*, overlay: HoumaoProjectOverlay, tool: str) -> ToolAdapter:
    """Load one tool adapter from the project-local agent-definition tree."""

    adapter_path = (overlay.agent_def_dir / "tools" / tool / "adapter.yaml").resolve()
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

    return (overlay.agent_def_dir / "tools" / tool / "auth" / name).resolve()


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

    lines = [f"{name}={env_values[name]}" for name in allowlist if name in env_values]
    return "\n".join(lines) + "\n"


def _compact_env_values(raw_values: dict[str, str | None]) -> dict[str, str]:
    """Drop empty env values before auth-bundle materialization."""

    return {
        name: value.strip()
        for name, value in raw_values.items()
        if value is not None and value.strip()
    }


def _flagged_items(values: dict[str, bool]) -> set[str]:
    """Return the names whose boolean flag is enabled."""

    return {name for name, enabled in values.items() if enabled}


def _is_secret_env_name(env_name: str) -> bool:
    """Return whether one env-var name should be redacted in CLI output."""

    normalized = env_name.upper()
    return any(token in normalized for token in _SECRET_ENV_TOKENS)


def _require_non_empty_name(value: str, *, field_name: str) -> str:
    """Validate one tool or auth-bundle name."""

    candidate = value.strip()
    if not candidate:
        raise click.ClickException(f"{field_name} must not be empty.")
    if "/" in candidate or "\\" in candidate:
        raise click.ClickException(f"{field_name} must not contain path separators.")
    return candidate
