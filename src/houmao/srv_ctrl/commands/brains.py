"""Local brain-construction commands for `houmao-mgr`."""

from __future__ import annotations

import os
from pathlib import Path

import click

from houmao.agents.brain_builder import (
    BuildRequest,
    build_brain_home,
    load_brain_recipe,
    load_launch_overrides_input,
)
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR

from .common import emit_json

_DEFAULT_AGENT_DEF_DIR = Path(".agentsys") / "agents"


@click.group(name="brains")
def brains_group() -> None:
    """Local brain-construction commands; these do not call `houmao-server`."""


@brains_group.command(name="build")
@click.option("--agent-def-dir", default=None, help="Agent-definition root to build from.")
@click.option("--tool", default=None, help="Tool identifier used by the selected adapter.")
@click.option("--skill", "skills", multiple=True, help="Skill path or name to project.")
@click.option("--config-profile", default=None, help="Config profile to materialize.")
@click.option("--cred-profile", default=None, help="Credential profile to project.")
@click.option("--recipe", default=None, help="Brain recipe path resolved from the agent root.")
@click.option(
    "--runtime-root",
    default=None,
    help="Optional runtime root where the built brain home should be written.",
)
@click.option("--home-id", default=None, help="Optional stable home identifier to reuse.")
@click.option(
    "--reuse-home",
    is_flag=True,
    help="Reuse an existing home when the selected home id already exists.",
)
@click.option(
    "--launch-overrides",
    default=None,
    help="JSON/YAML overrides file applied on top of adapter and recipe defaults.",
)
@click.option(
    "--agent-name",
    default=None,
    help="Optional canonical agent name embedded into the generated manifest.",
)
@click.option(
    "--agent-id",
    default=None,
    help="Optional stable agent id embedded into the generated manifest.",
)
def build_brain_command(
    agent_def_dir: str | None,
    tool: str | None,
    skills: tuple[str, ...],
    config_profile: str | None,
    cred_profile: str | None,
    recipe: str | None,
    runtime_root: str | None,
    home_id: str | None,
    reuse_home: bool,
    launch_overrides: str | None,
    agent_name: str | None,
    agent_id: str | None,
) -> None:
    """Build one local brain home from `BuildRequest`-aligned inputs."""

    cwd = Path.cwd().resolve()
    resolved_agent_def_dir = _resolve_agent_def_dir(agent_def_dir, cwd=cwd)
    recipe_path: Path | None = None
    recipe_payload = None
    if recipe is not None:
        recipe_path = _resolve_path(recipe, base=resolved_agent_def_dir)
        recipe_payload = load_brain_recipe(recipe_path)

    direct_launch_overrides = (
        load_launch_overrides_input(
            launch_overrides,
            base=cwd,
            source="--launch-overrides",
        )
        if launch_overrides is not None
        else None
    )

    resolved_tool = tool or (recipe_payload.tool if recipe_payload is not None else None)
    resolved_skills = (
        list(skills) if skills else (recipe_payload.skills if recipe_payload is not None else [])
    )
    resolved_config_profile = config_profile or (
        recipe_payload.config_profile if recipe_payload is not None else None
    )
    resolved_cred_profile = cred_profile or (
        recipe_payload.credential_profile if recipe_payload is not None else None
    )

    missing: list[str] = []
    if resolved_tool is None:
        missing.append("--tool")
    if not resolved_skills:
        missing.append("--skill")
    if resolved_config_profile is None:
        missing.append("--config-profile")
    if resolved_cred_profile is None:
        missing.append("--cred-profile")
    if missing:
        raise click.ClickException(f"Missing required build inputs: {', '.join(missing)}")

    try:
        result = build_brain_home(
            BuildRequest(
                agent_def_dir=resolved_agent_def_dir,
                tool=resolved_tool,
                skills=[str(item) for item in resolved_skills],
                config_profile=resolved_config_profile,
                credential_profile=resolved_cred_profile,
                recipe_path=recipe_path,
                recipe_launch_overrides=(
                    recipe_payload.launch_overrides if recipe_payload is not None else None
                ),
                runtime_root=_optional_path(runtime_root, base=cwd),
                mailbox=recipe_payload.mailbox if recipe_payload is not None else None,
                agent_name=agent_name
                or (recipe_payload.default_agent_name if recipe_payload is not None else None),
                agent_id=agent_id,
                home_id=home_id,
                reuse_home=reuse_home,
                launch_overrides=direct_launch_overrides,
                operator_prompt_mode=(
                    recipe_payload.operator_prompt_mode if recipe_payload is not None else None
                ),
            )
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    emit_json(
        {
            "home_id": result.home_id,
            "home_path": str(result.home_path),
            "launch_helper_path": str(result.launch_helper_path),
            "manifest_path": str(result.manifest_path),
        }
    )


def _optional_path(value: str | None, *, base: Path) -> Path | None:
    """Resolve one optional CLI path relative to the current working directory."""

    if value is None:
        return None
    return _resolve_path(value, base=base)


def _resolve_agent_def_dir(cli_value: str | None, *, cwd: Path) -> Path:
    """Resolve the agent-definition root used for local brain construction."""

    if cli_value is not None:
        return _resolve_path(cli_value, base=cwd)

    env_value = os.environ.get(AGENT_DEF_DIR_ENV_VAR)
    if env_value:
        return _resolve_path(env_value, base=cwd)

    return (cwd / _DEFAULT_AGENT_DEF_DIR).resolve()


def _resolve_path(value: str, *, base: Path) -> Path:
    """Resolve one CLI path relative to the provided base directory."""

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    return candidate.resolve()
