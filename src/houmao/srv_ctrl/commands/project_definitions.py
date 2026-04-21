"""Project-scoped role, preset, and recipe commands."""

from __future__ import annotations

# ruff: noqa: F403,F405
from .project_common import *


@click.group(name="roles")
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


@click.group(name="presets")
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
    type=click.IntRange(min=0),
    default=None,
    help="Optional launch-owned tool/model-specific reasoning preset index (>=0).",
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
    type=click.IntRange(min=0),
    default=None,
    help="Optional launch-owned tool/model-specific reasoning preset index override (>=0).",
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
    parsed_preset = _parse_preset_or_click(preset_path)
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
