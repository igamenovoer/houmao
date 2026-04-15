"""Project easy specialist, profile, and instance commands."""

from __future__ import annotations

# ruff: noqa: F403,F405
from .project_common import *


@click.group(name="easy")
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
    type=click.IntRange(min=0),
    default=None,
    help="Optional launch-owned tool/model-specific reasoning preset index override (>=0).",
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
    "--managed-header-section",
    "managed_header_section",
    multiple=True,
    metavar="SECTION=STATE",
    help="Persist one managed-header section policy (`enabled` or `disabled`).",
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
@overwrite_confirm_option
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
    managed_header_section: tuple[str, ...],
    gateway_port: int | None,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
    yes: bool,
) -> None:
    """Create one specialist-backed easy profile."""

    overlay = _ensure_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    payload = _store_launch_profile_from_cli(
        overlay=overlay,
        profile_name=profile_name,
        profile_lane="easy_profile",
        source_kind="specialist",
        source_name=_require_non_empty_name(specialist, field_name="--specialist"),
        operation=_resolve_launch_profile_create_operation_or_click(
            overlay=overlay,
            profile_name=profile_name,
            profile_lane="easy_profile",
            yes=yes,
        ),
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
        managed_header_section=managed_header_section,
        clear_managed_header_section=(),
        clear_managed_header_sections=False,
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
    )
    emit(payload)


@easy_profile_group.command(name="set")
@click.option("--name", required=True, help="Easy profile name.")
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
    type=click.IntRange(min=0),
    default=None,
    help="Optional launch-owned tool/model-specific reasoning preset index override (>=0).",
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
    "--managed-header-section",
    "managed_header_section",
    multiple=True,
    metavar="SECTION=STATE",
    help="Persist or replace one managed-header section policy (`enabled` or `disabled`).",
)
@click.option(
    "--clear-managed-header-section",
    "clear_managed_header_section",
    multiple=True,
    metavar="SECTION",
    help="Clear one stored managed-header section policy entry.",
)
@click.option(
    "--clear-managed-header-sections",
    is_flag=True,
    help="Clear all stored managed-header section policy entries.",
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
def set_easy_profile_command(
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
    managed_header_section: tuple[str, ...],
    clear_managed_header_section: tuple[str, ...],
    clear_managed_header_sections: bool,
    gateway_port: int | None,
    prompt_overlay_mode: str | None,
    prompt_overlay_text: str | None,
    prompt_overlay_file: Path | None,
    clear_prompt_overlay: bool,
) -> None:
    """Update one specialist-backed easy profile."""

    overlay = _ensure_project_overlay()
    profile_name = _require_non_empty_name(name, field_name="--name")
    payload = _store_launch_profile_from_cli(
        overlay=overlay,
        profile_name=profile_name,
        profile_lane="easy_profile",
        source_kind="specialist",
        source_name=_load_launch_profile_or_click(
            overlay=overlay,
            name=profile_name,
            expected_lane="easy_profile",
        ).entry.source_name,
        operation="patch",
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
        managed_header_section=managed_header_section,
        clear_managed_header_section=clear_managed_header_section,
        clear_managed_header_sections=clear_managed_header_sections,
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
    type=click.IntRange(min=0),
    default=None,
    help="Optional launch-owned tool/model-specific reasoning preset index (>=0).",
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
    auth_result = ensure_specialist_credential_bundle(
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
    auth_profile = _load_auth_profile_or_click(
        overlay=overlay,
        tool=tool_name,
        name=credential_name,
    )

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
        auth_profile=auth_profile,
        role_name=specialist_name,
        setup_name=setup_name,
        prompt_path=system_prompt_path,
        skill_paths=tuple(imported_skills),
        setup_path=setup_path,
        launch_mapping=launch_mapping,
        mailbox_mapping=None,
        extra_mapping=None,
    )
    materialize_project_agent_catalog_projection(overlay)
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
                "auth": str(auth_profile.resolved_projection_path(overlay)),
                "skills": [str(path) for path in imported_skills],
            },
            "auth_result": auth_result,
        }
    )


def _has_specialist_set_updates(
    *,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    clear_system_prompt: bool,
    setup: str | None,
    credential: str | None,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
    env_set: tuple[str, ...],
    clear_env: bool,
    skill_dirs: tuple[Path, ...],
    add_skill_names: tuple[str, ...],
    remove_skill_names: tuple[str, ...],
    clear_skills: bool,
) -> bool:
    """Return whether a specialist patch command requested any mutation."""

    return any(
        (
            system_prompt is not None,
            system_prompt_file is not None,
            clear_system_prompt,
            setup is not None,
            credential is not None,
            prompt_mode is not None,
            clear_prompt_mode,
            model is not None,
            clear_model,
            reasoning_level is not None,
            clear_reasoning_level,
            bool(env_set),
            clear_env,
            bool(skill_dirs),
            bool(add_skill_names),
            bool(remove_skill_names),
            clear_skills,
        )
    )


def _resolve_specialist_set_prompt_path(
    *,
    overlay: HoumaoProjectOverlay,
    specialist: SpecialistMetadata,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    clear_system_prompt: bool,
) -> Path:
    """Resolve the prompt file source for one specialist patch."""

    if clear_system_prompt and (system_prompt is not None or system_prompt_file is not None):
        raise click.ClickException(
            "`--clear-system-prompt` cannot be combined with `--system-prompt` or "
            "`--system-prompt-file`."
        )
    if clear_system_prompt:
        return _write_role_prompt(
            role_root=_role_root(overlay=overlay, role_name=specialist.role_name),
            prompt_text="",
            overwrite=True,
        )
    if system_prompt is not None or system_prompt_file is not None:
        return _write_role_prompt(
            role_root=_role_root(overlay=overlay, role_name=specialist.role_name),
            prompt_text=_resolve_system_prompt_text(
                system_prompt=system_prompt,
                system_prompt_file=system_prompt_file,
            ),
            overwrite=True,
        )
    prompt_path = specialist.resolved_system_prompt_path(overlay)
    if not prompt_path.is_file():
        raise click.ClickException(f"Specialist prompt projection was not found: {prompt_path}")
    return prompt_path


def _deduplicate_names(names: list[str]) -> list[str]:
    """Return unique non-empty names while preserving operator order."""

    result: list[str] = []
    seen: set[str] = set()
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def _resolve_specialist_set_skill_paths(
    *,
    overlay: HoumaoProjectOverlay,
    specialist: SpecialistMetadata,
    skill_dirs: tuple[Path, ...],
    add_skill_names: tuple[str, ...],
    remove_skill_names: tuple[str, ...],
    clear_skills: bool,
) -> tuple[Path, ...]:
    """Resolve projected skill directories for one specialist patch."""

    skill_names = [] if clear_skills else list(specialist.skills)
    for raw_name in remove_skill_names:
        remove_name = _require_non_empty_name(raw_name, field_name="--remove-skill")
        skill_names = [name for name in skill_names if name != remove_name]
    for raw_name in add_skill_names:
        skill_names.append(_require_non_empty_name(raw_name, field_name="--add-skill"))
    imported_skill_paths = _import_skill_directories(overlay=overlay, skill_dirs=skill_dirs)
    skill_names.extend(path.name for path in imported_skill_paths)
    resolved_skill_names = _deduplicate_names(skill_names)

    skill_paths: list[Path] = []
    for skill_name in resolved_skill_names:
        skill_path = (overlay.agents_root / "skills" / skill_name).resolve()
        if not (skill_path / "SKILL.md").is_file():
            raise click.ClickException(
                f"Skill `{skill_name}` was not found in the project projection: {skill_path}"
            )
        skill_paths.append(skill_path)
    return tuple(skill_paths)


def _load_specialist_auth_profile_by_id_or_click(
    *,
    catalog: ProjectCatalog,
    specialist: SpecialistMetadata,
) -> AuthProfileCatalogEntry:
    """Load the specialist's current auth profile."""

    try:
        return catalog.load_auth_profile_by_id(specialist.auth_profile_id)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _specialist_model_fields(launch_mapping: dict[str, Any]) -> tuple[str | None, int | None]:
    """Return stored model name and reasoning level from a launch mapping."""

    raw_model = launch_mapping.get("model")
    if not isinstance(raw_model, dict):
        return None, None
    raw_name = raw_model.get("name")
    model_name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
    raw_reasoning = raw_model.get("reasoning")
    raw_level = raw_reasoning.get("level") if isinstance(raw_reasoning, dict) else None
    if raw_level is None:
        return model_name, None
    try:
        return model_name, int(raw_level)
    except (TypeError, ValueError) as exc:
        raise click.ClickException(
            f"Specialist stores invalid launch.model.reasoning.level {raw_level!r}."
        ) from exc


def _resolve_specialist_set_launch_mapping(
    *,
    overlay: HoumaoProjectOverlay,
    specialist: SpecialistMetadata,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
    env_set: tuple[str, ...],
    clear_env: bool,
) -> dict[str, Any]:
    """Resolve launch payload updates for one specialist patch."""

    if prompt_mode is not None and clear_prompt_mode:
        raise click.ClickException("`--prompt-mode` cannot be combined with `--clear-prompt-mode`.")
    if model is not None and clear_model:
        raise click.ClickException("`--model` cannot be combined with `--clear-model`.")
    if reasoning_level is not None and clear_reasoning_level:
        raise click.ClickException(
            "`--reasoning-level` cannot be combined with `--clear-reasoning-level`."
        )
    if env_set and clear_env:
        raise click.ClickException("`--env-set` cannot be combined with `--clear-env`.")

    launch_mapping = dict(specialist.launch_payload)
    if clear_prompt_mode:
        launch_mapping.pop("prompt_mode", None)
    elif prompt_mode is not None:
        launch_mapping["prompt_mode"] = prompt_mode

    if any((model is not None, clear_model, reasoning_level is not None, clear_reasoning_level)):
        current_model_name, current_reasoning_level = _specialist_model_fields(launch_mapping)
        model_config = _merge_model_config_for_storage(
            current_name=current_model_name,
            current_reasoning_level=current_reasoning_level,
            model_name=_resolve_model_name_or_click(model),
            reasoning_level=reasoning_level,
            clear_model=clear_model,
            clear_reasoning_level=clear_reasoning_level,
        )
        model_payload = _model_mapping_payload(model_config)
        if model_payload is None:
            launch_mapping.pop("model", None)
        else:
            launch_mapping["model"] = model_payload

    if clear_env:
        launch_mapping.pop("env_records", None)
    elif env_set:
        adapter = _load_overlay_tool_adapter(overlay=overlay, tool=specialist.tool)
        launch_mapping["env_records"] = _parse_launch_profile_env_records_or_click(
            adapter=adapter,
            env_set=env_set,
            source_label="project easy specialist set --env-set",
        )
    return launch_mapping


def _store_specialist_patch_from_cli(
    *,
    overlay: HoumaoProjectOverlay,
    specialist: SpecialistMetadata,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    clear_system_prompt: bool,
    setup: str | None,
    credential: str | None,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
    env_set: tuple[str, ...],
    clear_env: bool,
    skill_dirs: tuple[Path, ...],
    add_skill_names: tuple[str, ...],
    remove_skill_names: tuple[str, ...],
    clear_skills: bool,
) -> tuple[SpecialistMetadata, Path | None]:
    """Apply one specialist patch to the catalog and return the updated metadata."""

    materialize_project_agent_catalog_projection(overlay)
    catalog = ProjectCatalog.from_overlay(overlay)
    old_preset_path = specialist.resolved_preset_path(overlay)
    prompt_path = _resolve_specialist_set_prompt_path(
        overlay=overlay,
        specialist=specialist,
        system_prompt=system_prompt,
        system_prompt_file=system_prompt_file,
        clear_system_prompt=clear_system_prompt,
    )
    skill_paths = _resolve_specialist_set_skill_paths(
        overlay=overlay,
        specialist=specialist,
        skill_dirs=skill_dirs,
        add_skill_names=add_skill_names,
        remove_skill_names=remove_skill_names,
        clear_skills=clear_skills,
    )
    setup_name = (
        _require_non_empty_name(setup, field_name="--setup")
        if setup is not None
        else specialist.setup_name
    )
    setup_path = _tool_setup_path(overlay=overlay, tool=specialist.tool, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Setup bundle not found: {setup_path}")
    credential_name = (
        _require_non_empty_name(credential, field_name="--credential")
        if credential is not None
        else specialist.credential_name
    )
    auth_profile = (
        _load_auth_profile_or_click(overlay=overlay, tool=specialist.tool, name=credential_name)
        if credential is not None
        else _load_specialist_auth_profile_by_id_or_click(
            catalog=catalog,
            specialist=specialist,
        )
    )
    launch_mapping = _resolve_specialist_set_launch_mapping(
        overlay=overlay,
        specialist=specialist,
        prompt_mode=prompt_mode,
        clear_prompt_mode=clear_prompt_mode,
        model=model,
        clear_model=clear_model,
        reasoning_level=reasoning_level,
        clear_reasoning_level=clear_reasoning_level,
        env_set=env_set,
        clear_env=clear_env,
    )
    metadata = catalog.store_specialist_from_sources(
        name=specialist.name,
        preset_name=_canonical_preset_name(
            role_name=specialist.role_name,
            tool=specialist.tool,
            setup=setup_name,
        ),
        tool=specialist.tool,
        provider=specialist.provider,
        auth_profile=auth_profile,
        role_name=specialist.role_name,
        setup_name=setup_name,
        prompt_path=prompt_path,
        skill_paths=skill_paths,
        setup_path=setup_path,
        launch_mapping=launch_mapping,
        mailbox_mapping=specialist.mailbox_payload,
        extra_mapping=specialist.extra_payload,
    )
    removed_old_preset_path = (
        old_preset_path if metadata.preset_name != specialist.preset_name else None
    )
    materialize_project_agent_catalog_projection(overlay)
    if removed_old_preset_path is not None:
        removed_old_preset_path.unlink(missing_ok=True)
    return metadata, removed_old_preset_path


@easy_specialist_group.command(name="set")
@click.option("--name", required=True, help="Specialist name.")
@click.option("--system-prompt", default=None, help="Replace system prompt with inline content.")
@click.option(
    "--system-prompt-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Replace system prompt from a Markdown file.",
)
@click.option("--clear-system-prompt", is_flag=True, help="Clear the stored system prompt.")
@click.option("--setup", default=None, help="Replace the specialist setup bundle name.")
@click.option("--credential", default=None, help="Replace the credential bundle name.")
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Replace the persisted operator prompt mode.",
)
@click.option("--clear-prompt-mode", is_flag=True, help="Clear the persisted prompt mode.")
@click.option("--model", default=None, help="Replace the launch-owned default model name.")
@click.option("--clear-model", is_flag=True, help="Clear the persisted default model name.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Replace the launch-owned tool/model-specific reasoning preset index (>=0).",
)
@click.option(
    "--clear-reasoning-level",
    is_flag=True,
    help="Clear the persisted reasoning preset index.",
)
@click.option(
    "--env-set",
    "env_set",
    multiple=True,
    help="Replace persistent specialist env records with repeatable `NAME=value` entries.",
)
@click.option("--clear-env", is_flag=True, help="Clear persistent specialist env records.")
@click.option(
    "--with-skill",
    "skill_dirs",
    multiple=True,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Repeatable skill directory to import and add to the specialist.",
)
@click.option("--add-skill", "add_skill_names", multiple=True, help="Add a project skill by name.")
@click.option(
    "--remove-skill",
    "remove_skill_names",
    multiple=True,
    help="Remove a skill by name from this specialist.",
)
@click.option("--clear-skills", is_flag=True, help="Remove all skills from this specialist.")
def set_easy_specialist_command(
    name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    clear_system_prompt: bool,
    setup: str | None,
    credential: str | None,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
    env_set: tuple[str, ...],
    clear_env: bool,
    skill_dirs: tuple[Path, ...],
    add_skill_names: tuple[str, ...],
    remove_skill_names: tuple[str, ...],
    clear_skills: bool,
) -> None:
    """Patch one existing project-local specialist without recreating it."""

    if not _has_specialist_set_updates(
        system_prompt=system_prompt,
        system_prompt_file=system_prompt_file,
        clear_system_prompt=clear_system_prompt,
        setup=setup,
        credential=credential,
        prompt_mode=prompt_mode,
        clear_prompt_mode=clear_prompt_mode,
        model=model,
        clear_model=clear_model,
        reasoning_level=reasoning_level,
        clear_reasoning_level=clear_reasoning_level,
        env_set=env_set,
        clear_env=clear_env,
        skill_dirs=skill_dirs,
        add_skill_names=add_skill_names,
        remove_skill_names=remove_skill_names,
        clear_skills=clear_skills,
    ):
        raise click.ClickException("No specialist updates requested.")

    overlay = _resolve_existing_project_overlay()
    specialist = _load_specialist_or_click(
        overlay=overlay,
        name=_require_non_empty_name(name, field_name="--name"),
    )
    metadata, removed_old_preset_path = _store_specialist_patch_from_cli(
        overlay=overlay,
        specialist=specialist,
        system_prompt=system_prompt,
        system_prompt_file=system_prompt_file,
        clear_system_prompt=clear_system_prompt,
        setup=setup,
        credential=credential,
        prompt_mode=prompt_mode,
        clear_prompt_mode=clear_prompt_mode,
        model=model,
        clear_model=clear_model,
        reasoning_level=reasoning_level,
        clear_reasoning_level=clear_reasoning_level,
        env_set=env_set,
        clear_env=clear_env,
        skill_dirs=skill_dirs,
        add_skill_names=add_skill_names,
        remove_skill_names=remove_skill_names,
        clear_skills=clear_skills,
    )
    payload = _specialist_payload(overlay=overlay, metadata=metadata)
    payload["updated"] = True
    if removed_old_preset_path is not None:
        payload["removed_old_preset_path"] = str(removed_old_preset_path)
    emit(payload)


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
    type=click.IntRange(min=0),
    default=None,
    help="Optional one-off tool/model-specific reasoning preset index override (>=0).",
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
    "--gateway-tui-watch-poll-interval-seconds",
    type=click.FloatRange(min=0.0, min_open=True),
    default=None,
    help="Override gateway-owned TUI watch poll interval seconds for this launch.",
)
@click.option(
    "--gateway-tui-stability-threshold-seconds",
    type=click.FloatRange(min=0.0, min_open=True),
    default=None,
    help="Override gateway-owned TUI stability threshold seconds for this launch.",
)
@click.option(
    "--gateway-tui-completion-stability-seconds",
    type=click.FloatRange(min=0.0, min_open=True),
    default=None,
    help="Override gateway-owned TUI completion stability seconds for this launch.",
)
@click.option(
    "--gateway-tui-unknown-to-stalled-timeout-seconds",
    type=click.FloatRange(min=0.0, min_open=True),
    default=None,
    help="Override gateway-owned TUI unknown-to-stalled timeout seconds for this launch.",
)
@click.option(
    "--gateway-tui-stale-active-recovery-seconds",
    type=click.FloatRange(min=0.0, min_open=True),
    default=None,
    help="Override gateway-owned TUI stale-active recovery seconds for this launch.",
)
@click.option(
    "--gateway-tui-final-stable-active-recovery-seconds",
    type=click.FloatRange(min=0.0, min_open=True),
    default=None,
    help="Override gateway-owned TUI final stable-active recovery seconds for this launch.",
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
    "--managed-header-section",
    "managed_header_section",
    multiple=True,
    metavar="SECTION=STATE",
    help="One-shot managed-header section override (`enabled` or `disabled`).",
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
    gateway_tui_watch_poll_interval_seconds: float | None,
    gateway_tui_stability_threshold_seconds: float | None,
    gateway_tui_completion_stability_seconds: float | None,
    gateway_tui_unknown_to_stalled_timeout_seconds: float | None,
    gateway_tui_stale_active_recovery_seconds: float | None,
    gateway_tui_final_stable_active_recovery_seconds: float | None,
    workdir: Path | None,
    env_set: tuple[str, ...],
    mail_transport: str | None,
    mail_root: Path | None,
    mail_account_dir: Path | None,
    managed_header: bool | None,
    managed_header_section: tuple[str, ...],
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
    launch_profile_managed_header_policy: ManagedHeaderPolicy | None = None
    launch_profile_managed_header_section_policy: (
        dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy] | None
    ) = None
    launch_profile_provenance = None
    direct_model_config = _build_model_config_or_click(
        model_name=_resolve_model_name_or_click(model),
        reasoning_level=reasoning_level,
    )
    managed_header_section_overrides = _managed_header_section_policy_from_options(
        managed_header_section
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
        launch_profile_managed_header_section_policy = dict(
            getattr(resolved_profile.entry, "managed_header_section_policy", {})
        )
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
    gateway_tui_tracking_timing_overrides = GatewayTuiTrackingTimingOverridesV1(
        watch_poll_interval_seconds=gateway_tui_watch_poll_interval_seconds,
        stability_threshold_seconds=gateway_tui_stability_threshold_seconds,
        completion_stability_seconds=gateway_tui_completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=gateway_tui_unknown_to_stalled_timeout_seconds,
        stale_active_recovery_seconds=gateway_tui_stale_active_recovery_seconds,
        final_stable_active_recovery_seconds=(gateway_tui_final_stable_active_recovery_seconds),
    )
    if no_gateway and gateway_tui_tracking_timing_overrides.has_values():
        raise click.ClickException(
            "`--no-gateway` cannot be combined with gateway TUI timing overrides."
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
    elif gateway_tui_tracking_timing_overrides.has_values():
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
        gateway_tui_tracking_timing_overrides=(
            gateway_tui_tracking_timing_overrides
            if gateway_tui_tracking_timing_overrides.has_values()
            else None
        ),
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
        managed_header_override=managed_header,
        launch_profile_managed_header_policy=launch_profile_managed_header_policy,
        managed_header_section_overrides=managed_header_section_overrides,
        launch_profile_managed_header_section_policy=(launch_profile_managed_header_section_policy),
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
