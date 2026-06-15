"""Internal native-agent file-tree commands for ``houmao-mgr``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any

import click
import yaml

from houmao.agents.definition_parser import parse_agent_preset, parse_tool_adapter
from houmao.terminology import (
    LAUNCH_DOSSIER_TERM,
    NATIVE_AGENT_ROOT_ENV_VAR,
    NATIVE_AGENT_ROOT_TERM,
    NativeAgentRootResolution,
    resolve_native_agent_root,
)

from .brains import native_agent_brain_group
from .credentials import native_agent_credentials_group
from .common import overwrite_confirm_option
from .output import emit

_SUPPORTED_NATIVE_TOOLS: tuple[str, ...] = ("claude", "codex", "gemini", "kimi")


@dataclass(frozen=True)
class NativeAgentContext:
    """Resolved native-agent command context."""

    root: Path
    source: str
    diagnostics: tuple[str, ...] = ()


@click.group(name="native-agent")
def native_agent_group() -> None:
    """Inspect and mutate internal provider-aligned native-agent material."""


@native_agent_group.group(name="roles")
def native_agent_roles_group() -> None:
    """Manage native-agent role prompt roots."""


@native_agent_group.group(name="recipes")
def native_agent_recipes_group() -> None:
    """Manage native-agent recipes stored under `presets/`."""


@native_agent_group.group(name="launch-dossiers")
def native_agent_launch_dossiers_group() -> None:
    """Manage recipe-backed native launch dossiers."""


@native_agent_group.group(name="tools")
def native_agent_tools_group() -> None:
    """Inspect native-agent provider tool/setup trees."""


native_agent_group.add_command(native_agent_credentials_group)
native_agent_group.add_command(native_agent_brain_group)


def native_agent_root_option(function: Any) -> Any:
    """Attach the native-agent root option accepted by direct internals commands."""

    return click.option(
        "--native-agent-root",
        type=click.Path(path_type=Path),
        default=None,
        help=(
            f"{NATIVE_AGENT_ROOT_TERM.capitalize()} to inspect or mutate. "
            f"Defaults to `{NATIVE_AGENT_ROOT_ENV_VAR}`."
        ),
    )(function)


def _native_context(native_agent_root: Path | None) -> NativeAgentContext:
    """Resolve one native-agent command context or raise a Click error."""

    try:
        resolution = resolve_native_agent_root(
            cli_value=native_agent_root,
            base=Path.cwd().resolve(),
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    return _context_from_resolution(resolution)


def _context_from_resolution(resolution: NativeAgentRootResolution) -> NativeAgentContext:
    """Convert root resolution into command context."""

    return NativeAgentContext(
        root=resolution.root,
        source=resolution.source,
        diagnostics=resolution.diagnostics,
    )


def _base_payload(context: NativeAgentContext) -> dict[str, object]:
    """Return shared native-agent context fields."""

    payload: dict[str, object] = {
        "native_agent_root": str(context.root),
        "native_agent_root_source": context.source,
    }
    if context.diagnostics:
        payload["diagnostics"] = list(context.diagnostics)
    return payload


def _require_name(value: str, *, field_name: str) -> str:
    """Return a stripped non-empty CLI name."""

    stripped = value.strip()
    if not stripped:
        raise click.ClickException(f"{field_name} must not be empty.")
    return stripped


def _optional_name(value: str | None, *, field_name: str) -> str | None:
    """Return an optional stripped CLI name."""

    if value is None:
        return None
    return _require_name(value, field_name=field_name)


def _role_root(*, root: Path, name: str) -> Path:
    """Return one native role root."""

    return (root / "roles" / name).resolve()


def _role_prompt_path(*, root: Path, name: str) -> Path:
    """Return one native role prompt path."""

    return (_role_root(root=root, name=name) / "system-prompt.md").resolve()


def _recipe_path(*, root: Path, name: str) -> Path:
    """Return one native recipe path."""

    return (root / "presets" / f"{name}.yaml").resolve()


def _launch_dossier_path(*, root: Path, name: str) -> Path:
    """Return one native launch-dossier path."""

    return (root / "launch-profiles" / f"{name}.yaml").resolve()


def _tool_root(*, root: Path, tool: str) -> Path:
    """Return one native tool root."""

    return (root / "tools" / tool).resolve()


def _tool_setup_path(*, root: Path, tool: str, name: str) -> Path:
    """Return one native tool setup path."""

    return (_tool_root(root=root, tool=tool) / "setups" / name).resolve()


def _relative_file_listing(root: Path) -> list[str]:
    """Return stable relative file paths under one root."""

    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    """Read one YAML mapping from disk."""

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise click.ClickException(f"Could not parse YAML `{path}`: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise click.ClickException(f"{path}: expected a top-level mapping.")
    return dict(loaded)


def _write_yaml_mapping(path: Path, payload: dict[str, object]) -> None:
    """Write one YAML mapping with deterministic ordering."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _default_role_prompt(role_name: str) -> str:
    """Return a minimal default role prompt."""

    return f"You are the `{role_name}` native-agent role."


def _resolve_prompt_text(
    *,
    role_name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    clear: bool = False,
) -> str:
    """Resolve role prompt content from CLI inputs."""

    if clear and (system_prompt is not None or system_prompt_file is not None):
        raise click.ClickException(
            "`--clear-system-prompt` cannot be combined with prompt content."
        )
    if system_prompt is not None and system_prompt_file is not None:
        raise click.ClickException(
            "Provide at most one of `--system-prompt` or `--system-prompt-file`."
        )
    if clear:
        return ""
    if system_prompt is not None:
        text = system_prompt.strip()
        if not text:
            raise click.ClickException("`--system-prompt` must not be empty.")
        return text
    if system_prompt_file is not None:
        return system_prompt_file.read_text(encoding="utf-8").rstrip()
    return _default_role_prompt(role_name)


def _write_role_prompt(*, root: Path, role_name: str, prompt_text: str) -> Path:
    """Write one role prompt."""

    prompt_path = _role_prompt_path(root=root, name=role_name)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    if prompt_path.is_dir():
        raise click.ClickException(f"Prompt path already exists as a directory: {prompt_path}")
    prompt_path.write_text(
        prompt_text.rstrip() + "\n" if prompt_text.strip() else "", encoding="utf-8"
    )
    return prompt_path


def _list_role_names(root: Path) -> list[str]:
    """Return native role names."""

    roles_root = (root / "roles").resolve()
    if not roles_root.is_dir():
        return []
    return sorted(path.name for path in roles_root.iterdir() if path.is_dir())


def _role_summary(*, root: Path, role_name: str, include_prompt: bool = False) -> dict[str, object]:
    """Return one native role summary."""

    prompt_path = _role_prompt_path(root=root, name=role_name)
    payload: dict[str, object] = {
        "name": role_name,
        "role_path": str(prompt_path.parent),
        "system_prompt_path": str(prompt_path),
        "system_prompt_exists": prompt_path.is_file(),
        "recipes": _list_recipe_summaries(root=root, role_name=role_name),
    }
    if include_prompt:
        payload["system_prompt_text"] = (
            prompt_path.read_text(encoding="utf-8").rstrip() if prompt_path.is_file() else ""
        )
    return payload


@native_agent_roles_group.command(name="list")
@native_agent_root_option
def list_native_roles_command(native_agent_root: Path | None) -> None:
    """List native-agent role roots."""

    context = _native_context(native_agent_root)
    emit(
        _base_payload(context)
        | {
            "roles": [
                _role_summary(root=context.root, role_name=name)
                for name in _list_role_names(context.root)
            ]
        }
    )


@native_agent_roles_group.command(name="get")
@click.option("--name", required=True, help="Role name.")
@click.option("--include-prompt", is_flag=True, help="Include role prompt text.")
@native_agent_root_option
def get_native_role_command(
    name: str,
    include_prompt: bool,
    native_agent_root: Path | None,
) -> None:
    """Inspect one native-agent role."""

    context = _native_context(native_agent_root)
    role_name = _require_name(name, field_name="--name")
    role_root = _role_root(root=context.root, name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Native-agent role not found: {role_root}")
    emit(
        _base_payload(context)
        | _role_summary(root=context.root, role_name=role_name, include_prompt=include_prompt)
    )


@native_agent_roles_group.command(name="init")
@click.option("--name", required=True, help="Role name.")
@click.option("--system-prompt", default=None, help="Inline system prompt content.")
@click.option(
    "--system-prompt-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a Markdown system prompt file.",
)
@native_agent_root_option
def init_native_role_command(
    name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    native_agent_root: Path | None,
) -> None:
    """Create one native-agent role root."""

    context = _native_context(native_agent_root)
    role_name = _require_name(name, field_name="--name")
    role_root = _role_root(root=context.root, name=role_name)
    if role_root.exists():
        raise click.ClickException(f"Native-agent role already exists: {role_root}")
    prompt_text = _resolve_prompt_text(
        role_name=role_name,
        system_prompt=system_prompt,
        system_prompt_file=system_prompt_file,
    )
    prompt_path = _write_role_prompt(
        root=context.root, role_name=role_name, prompt_text=prompt_text
    )
    emit(
        _base_payload(context)
        | {
            "role": role_name,
            "role_path": str(role_root),
            "system_prompt_path": str(prompt_path),
            "created_paths": [str(role_root), str(prompt_path)],
        }
    )


@native_agent_roles_group.command(name="set")
@click.option("--name", required=True, help="Role name.")
@click.option("--system-prompt", default=None, help="Inline system prompt content.")
@click.option(
    "--system-prompt-file",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to a Markdown system prompt file.",
)
@click.option("--clear-system-prompt", is_flag=True, help="Clear role prompt text.")
@native_agent_root_option
def set_native_role_command(
    name: str,
    system_prompt: str | None,
    system_prompt_file: Path | None,
    clear_system_prompt: bool,
    native_agent_root: Path | None,
) -> None:
    """Update one native-agent role prompt."""

    context = _native_context(native_agent_root)
    role_name = _require_name(name, field_name="--name")
    role_root = _role_root(root=context.root, name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Native-agent role not found: {role_root}")
    if not clear_system_prompt and system_prompt is None and system_prompt_file is None:
        raise click.ClickException(
            "Provide one of `--system-prompt`, `--system-prompt-file`, or `--clear-system-prompt`."
        )
    prompt_text = _resolve_prompt_text(
        role_name=role_name,
        system_prompt=system_prompt,
        system_prompt_file=system_prompt_file,
        clear=clear_system_prompt,
    )
    prompt_path = _write_role_prompt(
        root=context.root, role_name=role_name, prompt_text=prompt_text
    )
    emit(
        _base_payload(context)
        | _role_summary(root=context.root, role_name=role_name)
        | {"system_prompt_path": str(prompt_path)}
    )


@native_agent_roles_group.command(name="remove")
@click.option("--name", required=True, help="Role name.")
@native_agent_root_option
def remove_native_role_command(name: str, native_agent_root: Path | None) -> None:
    """Remove one native-agent role root."""

    context = _native_context(native_agent_root)
    role_name = _require_name(name, field_name="--name")
    role_root = _role_root(root=context.root, name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Native-agent role not found: {role_root}")
    referencing_recipes = _list_recipe_summaries(root=context.root, role_name=role_name)
    if referencing_recipes:
        recipe_names = ", ".join(str(item["name"]) for item in referencing_recipes)
        raise click.ClickException(
            f"Cannot remove native-agent role `{role_name}` because recipes still reference it: {recipe_names}"
        )
    shutil.rmtree(role_root)
    emit(_base_payload(context) | {"role": role_name, "removed": True, "path": str(role_root)})


def _list_recipe_summaries(
    *,
    root: Path,
    role_name: str | None = None,
    tool: str | None = None,
) -> list[dict[str, object]]:
    """Return native recipe summaries."""

    recipes_root = (root / "presets").resolve()
    if not recipes_root.is_dir():
        return []
    results: list[dict[str, object]] = []
    for recipe_file in sorted(path for path in recipes_root.iterdir() if path.is_file()):
        if recipe_file.suffix not in {".yaml", ".yml"}:
            continue
        parsed = _parse_recipe_or_click(recipe_file)
        if role_name is not None and parsed.role_name != role_name:
            continue
        if tool is not None and parsed.tool != tool:
            continue
        results.append(_recipe_summary(root=root, recipe_name=parsed.name))
    return results


def _parse_recipe_or_click(path: Path) -> Any:
    """Parse one native recipe file or raise a Click error."""

    try:
        return parse_agent_preset(path)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


def _recipe_summary(*, root: Path, recipe_name: str) -> dict[str, object]:
    """Return one native recipe summary."""

    path = _recipe_path(root=root, name=recipe_name)
    if not path.is_file():
        raise click.ClickException(f"Native-agent recipe not found: {path}")
    parsed = _parse_recipe_or_click(path)
    raw_payload = _read_yaml_mapping(path)
    launch_payload = raw_payload.get("launch")
    return {
        "name": parsed.name,
        "role": parsed.role_name,
        "tool": parsed.tool,
        "setup": parsed.setup,
        "path": str(path),
        "skills": list(parsed.skills),
        "auth": parsed.auth,
        "launch": launch_payload if isinstance(launch_payload, dict) else {},
        "mailbox": raw_payload.get("mailbox"),
        "extra": raw_payload.get("extra", {}),
    }


def _ensure_role_exists(*, root: Path, role_name: str) -> None:
    """Require one native role root."""

    role_root = _role_root(root=root, name=role_name)
    if not role_root.is_dir():
        raise click.ClickException(f"Native-agent role not found: {role_root}")


def _ensure_unique_recipe_tuple(
    *,
    root: Path,
    recipe_name: str,
    role_name: str,
    tool: str,
    setup: str,
) -> None:
    """Reject duplicate role/tool/setup recipe tuples."""

    for summary in _list_recipe_summaries(root=root):
        if str(summary["name"]) == recipe_name:
            continue
        if (
            str(summary["role"]) == role_name
            and str(summary["tool"]) == tool
            and str(summary["setup"]) == setup
        ):
            raise click.ClickException(
                f"Native-agent recipe tuple `{role_name}`, `{tool}`, `{setup}` is already owned by `{summary['name']}`."
            )


def _model_payload(*, model: str | None, reasoning_level: int | None) -> dict[str, object] | None:
    """Build the minimal launch model payload."""

    if model is None and reasoning_level is None:
        return None
    payload: dict[str, object] = {}
    if model is not None:
        payload["name"] = _require_name(model, field_name="--model")
    if reasoning_level is not None:
        payload["reasoning"] = {"level": reasoning_level}
    return payload


def _write_recipe(
    *,
    root: Path,
    recipe_name: str,
    role_name: str,
    tool: str,
    setup: str,
    skills: list[str],
    auth: str | None,
    prompt_mode: str | None,
    model: str | None,
    reasoning_level: int | None,
    overwrite: bool = False,
) -> Path:
    """Write one native recipe."""

    _ensure_role_exists(root=root, role_name=role_name)
    path = _recipe_path(root=root, name=recipe_name)
    if path.exists() and not overwrite:
        raise click.ClickException(f"Native-agent recipe already exists: {path}")
    _ensure_unique_recipe_tuple(
        root=root,
        recipe_name=recipe_name,
        role_name=role_name,
        tool=tool,
        setup=setup,
    )
    payload: dict[str, object] = {
        "role": role_name,
        "tool": tool,
        "setup": setup,
        "skills": skills,
    }
    if auth is not None:
        payload["auth"] = auth
    launch_payload: dict[str, object] = {"prompt_mode": prompt_mode or "unattended"}
    model_payload = _model_payload(model=model, reasoning_level=reasoning_level)
    if model_payload is not None:
        launch_payload["model"] = model_payload
    payload["launch"] = launch_payload
    _write_yaml_mapping(path, payload)
    return path


@native_agent_recipes_group.command(name="list")
@click.option("--role", default=None, help="Optional role filter.")
@click.option(
    "--tool",
    "tool_name",
    default=None,
    type=click.Choice(_SUPPORTED_NATIVE_TOOLS),
    help="Optional tool filter.",
)
@native_agent_root_option
def list_native_recipes_command(
    role: str | None,
    tool_name: str | None,
    native_agent_root: Path | None,
) -> None:
    """List native-agent recipes."""

    context = _native_context(native_agent_root)
    emit(
        _base_payload(context)
        | {
            "recipes": _list_recipe_summaries(
                root=context.root,
                role_name=_optional_name(role, field_name="--role"),
                tool=tool_name,
            )
        }
    )


@native_agent_recipes_group.command(name="get")
@click.option("--name", required=True, help="Recipe name.")
@native_agent_root_option
def get_native_recipe_command(name: str, native_agent_root: Path | None) -> None:
    """Inspect one native-agent recipe."""

    context = _native_context(native_agent_root)
    recipe_name = _require_name(name, field_name="--name")
    emit(_base_payload(context) | _recipe_summary(root=context.root, recipe_name=recipe_name))


@native_agent_recipes_group.command(name="add")
@click.option("--name", required=True, help="Recipe name.")
@click.option("--role", required=True, help="Role name.")
@click.option(
    "--tool",
    "tool_name",
    required=True,
    type=click.Choice(_SUPPORTED_NATIVE_TOOLS),
    help="Tool lane.",
)
@click.option("--setup", default="default", show_default=True, help="Recipe setup name.")
@click.option("--skill", "skill_names", multiple=True, help="Repeatable skill name.")
@click.option("--auth", default=None, help="Optional credential/auth bundle name.")
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional launch prompt mode.",
)
@click.option("--model", default=None, help="Optional model name.")
@click.option(
    "--reasoning-level", type=click.IntRange(min=0), default=None, help="Optional reasoning level."
)
@native_agent_root_option
def add_native_recipe_command(
    name: str,
    role: str,
    tool_name: str,
    setup: str,
    skill_names: tuple[str, ...],
    auth: str | None,
    prompt_mode: str | None,
    model: str | None,
    reasoning_level: int | None,
    native_agent_root: Path | None,
) -> None:
    """Create one native-agent recipe."""

    context = _native_context(native_agent_root)
    recipe_name = _require_name(name, field_name="--name")
    path = _write_recipe(
        root=context.root,
        recipe_name=recipe_name,
        role_name=_require_name(role, field_name="--role"),
        tool=tool_name,
        setup=_require_name(setup, field_name="--setup"),
        skills=[_require_name(value, field_name="--skill") for value in skill_names],
        auth=_optional_name(auth, field_name="--auth"),
        prompt_mode=_optional_name(prompt_mode, field_name="--prompt-mode"),
        model=model,
        reasoning_level=reasoning_level,
    )
    emit(_base_payload(context) | {"name": recipe_name, "path": str(path), "created": True})


@native_agent_recipes_group.command(name="set")
@click.option("--name", required=True, help="Recipe name.")
@click.option("--role", default=None, help="Optional role name override.")
@click.option(
    "--tool",
    "tool_name",
    default=None,
    type=click.Choice(_SUPPORTED_NATIVE_TOOLS),
    help="Optional tool lane override.",
)
@click.option("--setup", default=None, help="Optional setup override.")
@click.option("--auth", default=None, help="Optional credential/auth override.")
@click.option("--clear-auth", is_flag=True, help="Clear credential/auth reference.")
@click.option("--add-skill", "add_skill_names", multiple=True, help="Repeatable skill to add.")
@click.option(
    "--remove-skill", "remove_skill_names", multiple=True, help="Repeatable skill to remove."
)
@click.option("--clear-skills", is_flag=True, help="Clear all recipe skill bindings.")
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional prompt mode.",
)
@click.option("--clear-prompt-mode", is_flag=True, help="Clear prompt mode.")
@click.option("--model", default=None, help="Optional model override.")
@click.option("--clear-model", is_flag=True, help="Clear model override.")
@click.option(
    "--reasoning-level", type=click.IntRange(min=0), default=None, help="Optional reasoning level."
)
@click.option("--clear-reasoning-level", is_flag=True, help="Clear reasoning level.")
@native_agent_root_option
def set_native_recipe_command(
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
    native_agent_root: Path | None,
) -> None:
    """Patch one native-agent recipe."""

    context = _native_context(native_agent_root)
    recipe_name = _require_name(name, field_name="--name")
    path = _recipe_path(root=context.root, name=recipe_name)
    if not path.is_file():
        raise click.ClickException(f"Native-agent recipe not found: {path}")
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
    raw = _read_yaml_mapping(path)
    parsed = _parse_recipe_or_click(path)
    role_name = _require_name(role, field_name="--role") if role is not None else parsed.role_name
    resolved_tool = tool_name or parsed.tool
    resolved_setup = (
        _require_name(setup, field_name="--setup") if setup is not None else parsed.setup
    )
    _ensure_role_exists(root=context.root, role_name=role_name)
    skills = [] if clear_skills else list(parsed.skills)
    skills.extend(_require_name(value, field_name="--add-skill") for value in add_skill_names)
    remove_skills = {
        _require_name(value, field_name="--remove-skill") for value in remove_skill_names
    }
    normalized_skills: list[str] = []
    for skill in (item for item in skills if item not in remove_skills):
        if skill not in normalized_skills:
            normalized_skills.append(skill)
    resolved_auth = (
        None
        if clear_auth
        else (_require_name(auth, field_name="--auth") if auth is not None else parsed.auth)
    )
    _ensure_unique_recipe_tuple(
        root=context.root,
        recipe_name=recipe_name,
        role_name=role_name,
        tool=resolved_tool,
        setup=resolved_setup,
    )
    raw["role"] = role_name
    raw["tool"] = resolved_tool
    raw["setup"] = resolved_setup
    raw["skills"] = normalized_skills
    if resolved_auth is None:
        raw.pop("auth", None)
    else:
        raw["auth"] = resolved_auth
    raw_launch = raw.get("launch")
    launch_payload = dict(raw_launch) if isinstance(raw_launch, dict) else {}
    if prompt_mode is not None:
        launch_payload["prompt_mode"] = prompt_mode
    elif clear_prompt_mode:
        launch_payload.pop("prompt_mode", None)
    raw_model = launch_payload.get("model")
    model_payload: dict[str, object] = dict(raw_model) if isinstance(raw_model, dict) else {}
    if clear_model:
        model_payload.pop("name", None)
    if model is not None:
        model_payload["name"] = _require_name(model, field_name="--model")
    if clear_reasoning_level:
        model_payload.pop("reasoning", None)
    if reasoning_level is not None:
        model_payload["reasoning"] = {"level": reasoning_level}
    if model_payload:
        launch_payload["model"] = model_payload
    else:
        launch_payload.pop("model", None)
    if launch_payload:
        raw["launch"] = launch_payload
    else:
        raw.pop("launch", None)
    _write_yaml_mapping(path, raw)
    emit(_base_payload(context) | _recipe_summary(root=context.root, recipe_name=recipe_name))


@native_agent_recipes_group.command(name="remove")
@click.option("--name", required=True, help="Recipe name.")
@native_agent_root_option
def remove_native_recipe_command(name: str, native_agent_root: Path | None) -> None:
    """Remove one native-agent recipe."""

    context = _native_context(native_agent_root)
    recipe_name = _require_name(name, field_name="--name")
    path = _recipe_path(root=context.root, name=recipe_name)
    if not path.is_file():
        raise click.ClickException(f"Native-agent recipe not found: {path}")
    path.unlink()
    emit(_base_payload(context) | {"name": recipe_name, "removed": True, "path": str(path)})


def _launch_dossier_payload(
    *,
    name: str,
    recipe: str,
    defaults: dict[str, object],
) -> dict[str, object]:
    """Build the retained compatibility payload for a native launch dossier."""

    return {
        "profile_lane": "launch_profile",
        "source": {"kind": "recipe", "name": recipe},
        "defaults": defaults,
    }


def _launch_dossier_summary(*, root: Path, name: str) -> dict[str, object]:
    """Return one native launch-dossier summary."""

    path = _launch_dossier_path(root=root, name=name)
    if not path.is_file():
        raise click.ClickException(f"Native launch dossier not found: {path}")
    raw = _read_yaml_mapping(path)
    source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    defaults = raw.get("defaults") if isinstance(raw.get("defaults"), dict) else {}
    return {
        "name": name,
        "resource_kind": LAUNCH_DOSSIER_TERM,
        "source": source,
        "recipe": source.get("name") if isinstance(source, dict) else None,
        "defaults": defaults,
        "path": str(path),
    }


def _list_launch_dossier_summaries(
    *,
    root: Path,
    recipe: str | None = None,
    tool: str | None = None,
) -> list[dict[str, object]]:
    """Return native launch-dossier summaries."""

    dossiers_root = (root / "launch-profiles").resolve()
    if not dossiers_root.is_dir():
        return []
    results: list[dict[str, object]] = []
    for dossier_path in sorted(path for path in dossiers_root.iterdir() if path.is_file()):
        if dossier_path.suffix not in {".yaml", ".yml"}:
            continue
        summary = _launch_dossier_summary(root=root, name=dossier_path.stem)
        if recipe is not None and summary.get("recipe") != recipe:
            continue
        if tool is not None:
            recipe_name = summary.get("recipe")
            if not isinstance(recipe_name, str):
                continue
            try:
                parsed_recipe = _parse_recipe_or_click(_recipe_path(root=root, name=recipe_name))
            except click.ClickException:
                continue
            if parsed_recipe.tool != tool:
                continue
        results.append(summary)
    return results


def _env_records(values: tuple[str, ...]) -> dict[str, str]:
    """Parse simple persistent env records."""

    records: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise click.ClickException("Native launch-dossier `--env-set` requires `NAME=value`.")
        name, record_value = value.split("=", 1)
        key = name.strip()
        if not key:
            raise click.ClickException("Native launch-dossier env names must not be empty.")
        records[key] = record_value
    return records


def _build_dossier_defaults(
    *,
    agent_name: str | None,
    agent_id: str | None,
    workdir: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    prompt_mode: str | None,
    env_set: tuple[str, ...],
    headless: bool,
    no_gateway: bool,
    gateway_port: int | None,
) -> dict[str, object]:
    """Build minimal native launch-dossier defaults."""

    defaults: dict[str, object] = {}
    for key, value in (
        ("agent_name", _optional_name(agent_name, field_name="--agent-name")),
        ("agent_id", _optional_name(agent_id, field_name="--agent-id")),
        ("workdir", _optional_name(workdir, field_name="--workdir")),
        ("auth", _optional_name(auth, field_name="--auth")),
        ("prompt_mode", _optional_name(prompt_mode, field_name="--prompt-mode")),
    ):
        if value is not None:
            defaults[key] = value
    model_payload = _model_payload(model=model, reasoning_level=reasoning_level)
    if model_payload is not None:
        defaults["model"] = model_payload
    if env_set:
        defaults["env_records"] = _env_records(env_set)
    posture: dict[str, object] = {}
    if headless:
        posture["headless"] = True
    if no_gateway:
        posture["gateway_auto_attach"] = False
    elif gateway_port is not None:
        posture["gateway_auto_attach"] = True
        posture["gateway_host"] = "127.0.0.1"
        posture["gateway_port"] = gateway_port
    if posture:
        defaults["posture"] = posture
    return defaults


@native_agent_launch_dossiers_group.command(name="list")
@click.option("--recipe", default=None, help="Optional source recipe filter.")
@click.option(
    "--tool",
    "tool_name",
    default=None,
    type=click.Choice(_SUPPORTED_NATIVE_TOOLS),
    help="Optional tool filter.",
)
@native_agent_root_option
def list_native_launch_dossiers_command(
    recipe: str | None,
    tool_name: str | None,
    native_agent_root: Path | None,
) -> None:
    """List native launch dossiers."""

    context = _native_context(native_agent_root)
    emit(
        _base_payload(context)
        | {
            "launch_dossiers": _list_launch_dossier_summaries(
                root=context.root,
                recipe=_optional_name(recipe, field_name="--recipe"),
                tool=tool_name,
            )
        }
    )


@native_agent_launch_dossiers_group.command(name="get")
@click.option("--name", required=True, help="Launch dossier name.")
@native_agent_root_option
def get_native_launch_dossier_command(name: str, native_agent_root: Path | None) -> None:
    """Inspect one native launch dossier."""

    context = _native_context(native_agent_root)
    dossier_name = _require_name(name, field_name="--name")
    emit(_base_payload(context) | _launch_dossier_summary(root=context.root, name=dossier_name))


@native_agent_launch_dossiers_group.command(name="add")
@click.option("--name", required=True, help="Launch dossier name.")
@click.option("--recipe", required=True, help="Source native recipe name.")
@click.option("--agent-name", default=None, help="Optional default managed-agent name.")
@click.option("--agent-id", default=None, help="Optional default managed-agent id.")
@click.option("--workdir", default=None, help="Optional default workdir.")
@click.option("--auth", default=None, help="Optional default credential/auth override.")
@click.option("--model", default=None, help="Optional model override.")
@click.option(
    "--reasoning-level", type=click.IntRange(min=0), default=None, help="Optional reasoning level."
)
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional prompt mode.",
)
@click.option("--env-set", "env_set", multiple=True, help="Repeatable persistent env record.")
@click.option("--headless", is_flag=True, help="Persist headless launch posture.")
@click.option("--no-gateway", is_flag=True, help="Disable gateway auto-attach.")
@click.option(
    "--gateway-port",
    type=click.IntRange(1, 65535),
    default=None,
    help="Persist fixed gateway port.",
)
@overwrite_confirm_option
@native_agent_root_option
def add_native_launch_dossier_command(
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
    headless: bool,
    no_gateway: bool,
    gateway_port: int | None,
    yes: bool,
    native_agent_root: Path | None,
) -> None:
    """Create one recipe-backed native launch dossier."""

    context = _native_context(native_agent_root)
    dossier_name = _require_name(name, field_name="--name")
    recipe_name = _require_name(recipe, field_name="--recipe")
    recipe_path = _recipe_path(root=context.root, name=recipe_name)
    if not recipe_path.is_file():
        raise click.ClickException(f"Native-agent recipe not found: {recipe_path}")
    path = _launch_dossier_path(root=context.root, name=dossier_name)
    if path.exists() and not yes:
        raise click.ClickException(
            f"Native launch dossier `{dossier_name}` already exists at `{path}`. Rerun with `--yes` to replace it."
        )
    if no_gateway and gateway_port is not None:
        raise click.ClickException("`--no-gateway` and `--gateway-port` cannot be combined.")
    payload = _launch_dossier_payload(
        name=dossier_name,
        recipe=recipe_name,
        defaults=_build_dossier_defaults(
            agent_name=agent_name,
            agent_id=agent_id,
            workdir=workdir,
            auth=auth,
            model=model,
            reasoning_level=reasoning_level,
            prompt_mode=prompt_mode,
            env_set=env_set,
            headless=headless,
            no_gateway=no_gateway,
            gateway_port=gateway_port,
        ),
    )
    _write_yaml_mapping(path, payload)
    emit(
        _base_payload(context)
        | _launch_dossier_summary(root=context.root, name=dossier_name)
        | {"created": True}
    )


@native_agent_launch_dossiers_group.command(name="set")
@click.option("--name", required=True, help="Launch dossier name.")
@click.option("--recipe", default=None, help="Optional source recipe override.")
@click.option("--auth", default=None, help="Optional credential/auth override.")
@click.option("--clear-auth", is_flag=True, help="Clear credential/auth override.")
@click.option("--workdir", default=None, help="Optional workdir override.")
@click.option("--clear-workdir", is_flag=True, help="Clear workdir override.")
@click.option("--model", default=None, help="Optional model override.")
@click.option("--clear-model", is_flag=True, help="Clear model override.")
@click.option(
    "--reasoning-level", type=click.IntRange(min=0), default=None, help="Optional reasoning level."
)
@click.option("--clear-reasoning-level", is_flag=True, help="Clear reasoning level.")
@click.option(
    "--prompt-mode",
    type=click.Choice(("unattended", "as_is")),
    default=None,
    help="Optional prompt mode.",
)
@click.option("--clear-prompt-mode", is_flag=True, help="Clear prompt mode.")
@native_agent_root_option
def set_native_launch_dossier_command(
    name: str,
    recipe: str | None,
    auth: str | None,
    clear_auth: bool,
    workdir: str | None,
    clear_workdir: bool,
    model: str | None,
    clear_model: bool,
    reasoning_level: int | None,
    clear_reasoning_level: bool,
    prompt_mode: str | None,
    clear_prompt_mode: bool,
    native_agent_root: Path | None,
) -> None:
    """Patch one native launch dossier."""

    context = _native_context(native_agent_root)
    dossier_name = _require_name(name, field_name="--name")
    path = _launch_dossier_path(root=context.root, name=dossier_name)
    if not path.is_file():
        raise click.ClickException(f"Native launch dossier not found: {path}")
    raw = _read_yaml_mapping(path)
    raw_source = raw.get("source")
    raw_defaults = raw.get("defaults")
    source = dict(raw_source) if isinstance(raw_source, dict) else {}
    defaults = dict(raw_defaults) if isinstance(raw_defaults, dict) else {}
    if recipe is not None:
        recipe_name = _require_name(recipe, field_name="--recipe")
        recipe_path = _recipe_path(root=context.root, name=recipe_name)
        if not recipe_path.is_file():
            raise click.ClickException(f"Native-agent recipe not found: {recipe_path}")
        source = {"kind": "recipe", "name": recipe_name}
    if clear_auth and auth is not None:
        raise click.ClickException("`--auth` cannot be combined with `--clear-auth`.")
    if clear_auth:
        defaults.pop("auth", None)
    elif auth is not None:
        defaults["auth"] = _require_name(auth, field_name="--auth")
    if clear_workdir and workdir is not None:
        raise click.ClickException("`--workdir` cannot be combined with `--clear-workdir`.")
    if clear_workdir:
        defaults.pop("workdir", None)
    elif workdir is not None:
        defaults["workdir"] = _require_name(workdir, field_name="--workdir")
    if clear_prompt_mode and prompt_mode is not None:
        raise click.ClickException("`--prompt-mode` cannot be combined with `--clear-prompt-mode`.")
    if clear_prompt_mode:
        defaults.pop("prompt_mode", None)
    elif prompt_mode is not None:
        defaults["prompt_mode"] = prompt_mode
    if clear_model and model is not None:
        raise click.ClickException("`--model` cannot be combined with `--clear-model`.")
    if clear_reasoning_level and reasoning_level is not None:
        raise click.ClickException(
            "`--reasoning-level` cannot be combined with `--clear-reasoning-level`."
        )
    raw_model = defaults.get("model")
    model_payload = dict(raw_model) if isinstance(raw_model, dict) else {}
    if clear_model:
        model_payload.pop("name", None)
    elif model is not None:
        model_payload["name"] = _require_name(model, field_name="--model")
    if clear_reasoning_level:
        model_payload.pop("reasoning", None)
    elif reasoning_level is not None:
        model_payload["reasoning"] = {"level": reasoning_level}
    if model_payload:
        defaults["model"] = model_payload
    else:
        defaults.pop("model", None)
    raw["profile_lane"] = "launch_profile"
    raw["source"] = source
    raw["defaults"] = defaults
    _write_yaml_mapping(path, raw)
    emit(_base_payload(context) | _launch_dossier_summary(root=context.root, name=dossier_name))


@native_agent_launch_dossiers_group.command(name="remove")
@click.option("--name", required=True, help="Launch dossier name.")
@native_agent_root_option
def remove_native_launch_dossier_command(name: str, native_agent_root: Path | None) -> None:
    """Remove one native launch dossier."""

    context = _native_context(native_agent_root)
    dossier_name = _require_name(name, field_name="--name")
    path = _launch_dossier_path(root=context.root, name=dossier_name)
    if not path.is_file():
        raise click.ClickException(f"Native launch dossier not found: {path}")
    path.unlink()
    emit(_base_payload(context) | {"name": dossier_name, "removed": True, "path": str(path)})


def _list_tool_setup_names(*, root: Path, tool: str) -> list[str]:
    """Return native tool setup names."""

    setups_root = (_tool_root(root=root, tool=tool) / "setups").resolve()
    if not setups_root.is_dir():
        return []
    return sorted(path.name for path in setups_root.iterdir() if path.is_dir())


def _list_tool_auth_names(*, root: Path, tool: str) -> list[str]:
    """Return native tool auth bundle names."""

    auth_root = (_tool_root(root=root, tool=tool) / "auth").resolve()
    if not auth_root.is_dir():
        return []
    return sorted(path.name for path in auth_root.iterdir() if path.is_dir())


def _emit_tool_get(*, tool: str, native_agent_root: Path | None) -> None:
    """Emit one native tool summary."""

    context = _native_context(native_agent_root)
    tool_root = _tool_root(root=context.root, tool=tool)
    adapter_path = (tool_root / "adapter.yaml").resolve()
    adapter_payload: dict[str, object] | None = None
    if adapter_path.is_file():
        try:
            adapter = parse_tool_adapter(adapter_path)
            adapter_payload = {
                "tool": adapter.tool,
                "launch_executable": adapter.launch_executable,
                "home_selector_env_var": adapter.home_selector_env_var,
            }
        except Exception as exc:
            adapter_payload = {"error": str(exc)}
    emit(
        _base_payload(context)
        | {
            "tool": tool,
            "tool_root": str(tool_root),
            "adapter_path": str(adapter_path),
            "adapter_present": adapter_path.is_file(),
            "adapter": adapter_payload,
            "setups": _list_tool_setup_names(root=context.root, tool=tool),
            "auth_bundles": _list_tool_auth_names(root=context.root, tool=tool),
        }
    )


def _emit_setup_list(*, tool: str, native_agent_root: Path | None) -> None:
    """Emit native setup names."""

    context = _native_context(native_agent_root)
    emit(
        _base_payload(context)
        | {"tool": tool, "setups": _list_tool_setup_names(root=context.root, tool=tool)}
    )


def _emit_setup_get(*, tool: str, name: str, native_agent_root: Path | None) -> None:
    """Emit one native setup summary."""

    context = _native_context(native_agent_root)
    setup_name = _require_name(name, field_name="--name")
    setup_path = _tool_setup_path(root=context.root, tool=tool, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Native-agent setup bundle not found: {setup_path}")
    emit(
        _base_payload(context)
        | {
            "tool": tool,
            "name": setup_name,
            "path": str(setup_path),
            "files": _relative_file_listing(setup_path),
        }
    )


def _emit_setup_add(
    *,
    tool: str,
    name: str,
    source_name: str,
    native_agent_root: Path | None,
) -> None:
    """Clone one native setup bundle."""

    context = _native_context(native_agent_root)
    target_name = _require_name(name, field_name="--name")
    resolved_source = _require_name(source_name, field_name="--from")
    source_path = _tool_setup_path(root=context.root, tool=tool, name=resolved_source)
    target_path = _tool_setup_path(root=context.root, tool=tool, name=target_name)
    if not source_path.is_dir():
        raise click.ClickException(f"Source native setup bundle not found: {source_path}")
    if target_path.exists():
        raise click.ClickException(f"Native setup bundle already exists: {target_path}")
    shutil.copytree(source_path, target_path)
    emit(
        _base_payload(context)
        | {
            "tool": tool,
            "name": target_name,
            "source_name": resolved_source,
            "path": str(target_path),
            "created": True,
        }
    )


def _emit_setup_remove(*, tool: str, name: str, native_agent_root: Path | None) -> None:
    """Remove one native setup bundle."""

    context = _native_context(native_agent_root)
    setup_name = _require_name(name, field_name="--name")
    setup_path = _tool_setup_path(root=context.root, tool=tool, name=setup_name)
    if not setup_path.is_dir():
        raise click.ClickException(f"Native-agent setup bundle not found: {setup_path}")
    shutil.rmtree(setup_path)
    emit(
        _base_payload(context)
        | {"tool": tool, "name": setup_name, "removed": True, "path": str(setup_path)}
    )


def _register_tool_commands(tool: str) -> click.Group:
    """Build one native tool command group."""

    @click.group(name=tool)
    def tool_group() -> None:
        """Manage one native provider tool subtree."""

    @tool_group.command(name="get")
    @native_agent_root_option
    def get_tool_command(native_agent_root: Path | None) -> None:
        """Inspect one native provider tool subtree."""

        _emit_tool_get(tool=tool, native_agent_root=native_agent_root)

    @tool_group.group(name="setups")
    def setups_group() -> None:
        """Manage native provider setup bundles."""

    @setups_group.command(name="list")
    @native_agent_root_option
    def list_setups_command(native_agent_root: Path | None) -> None:
        """List native setup bundles."""

        _emit_setup_list(tool=tool, native_agent_root=native_agent_root)

    @setups_group.command(name="get")
    @click.option("--name", required=True, help="Setup bundle name.")
    @native_agent_root_option
    def get_setup_command(name: str, native_agent_root: Path | None) -> None:
        """Inspect one native setup bundle."""

        _emit_setup_get(tool=tool, name=name, native_agent_root=native_agent_root)

    @setups_group.command(name="add")
    @click.option("--name", required=True, help="New setup bundle name.")
    @click.option(
        "--from", "source_name", default="default", show_default=True, help="Source setup name."
    )
    @native_agent_root_option
    def add_setup_command(
        name: str,
        source_name: str,
        native_agent_root: Path | None,
    ) -> None:
        """Clone one native setup bundle."""

        _emit_setup_add(
            tool=tool,
            name=name,
            source_name=source_name,
            native_agent_root=native_agent_root,
        )

    @setups_group.command(name="remove")
    @click.option("--name", required=True, help="Setup bundle name.")
    @native_agent_root_option
    def remove_setup_command(name: str, native_agent_root: Path | None) -> None:
        """Remove one native setup bundle."""

        _emit_setup_remove(tool=tool, name=name, native_agent_root=native_agent_root)

    return tool_group


for _tool_name in _SUPPORTED_NATIVE_TOOLS:
    native_agent_tools_group.add_command(_register_tool_commands(_tool_name))
