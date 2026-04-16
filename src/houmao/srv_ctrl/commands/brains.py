"""Local brain-construction commands for `houmao-mgr`."""

from __future__ import annotations

from pathlib import Path

import click

from houmao.agents.brain_builder import (
    BuildRequest,
    build_brain_home,
    load_brain_recipe,
    load_launch_overrides_input,
)
from houmao.agents.definition_parser import resolve_explicit_or_named_preset_path
from houmao.project.overlay import (
    ensure_project_aware_local_roots,
    resolve_materialized_project_aware_agent_def_dir,
    resolve_project_aware_runtime_root,
)

from .output import emit
from .project_aware_wording import (
    describe_overlay_bootstrap,
    describe_overlay_root_selection_source,
    describe_runtime_root_selection,
)


@click.group(name="brains")
def brains_group() -> None:
    """Local brain-construction commands; these do not call `houmao-server`."""


@brains_group.command(name="build")
@click.option("--agent-def-dir", default=None, help="Agent-definition root to build from.")
@click.option("--tool", default=None, help="Tool identifier used by the selected adapter.")
@click.option("--skill", "skills", multiple=True, help="Skill path or name to project.")
@click.option("--setup", default=None, help="Setup bundle to materialize.")
@click.option("--auth", default=None, help="Auth bundle to project.")
@click.option(
    "--preset",
    default=None,
    help="Preset path or bare preset name resolved from the agent root.",
)
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
    setup: str | None,
    auth: str | None,
    preset: str | None,
    runtime_root: str | None,
    home_id: str | None,
    reuse_home: bool,
    launch_overrides: str | None,
    agent_name: str | None,
    agent_id: str | None,
) -> None:
    """Build one local brain home from `BuildRequest`-aligned inputs."""

    cwd = Path.cwd().resolve()
    project_roots = ensure_project_aware_local_roots(cwd=cwd, cli_agent_def_dir=agent_def_dir)
    resolved_agent_def_dir = _resolve_agent_def_dir(agent_def_dir, cwd=cwd)
    resolved_runtime_root = resolve_project_aware_runtime_root(
        cwd=cwd,
        explicit_root=runtime_root,
        base=cwd,
    )
    preset_path: Path | None = None
    preset_payload = None
    if preset is not None:
        preset_path = resolve_explicit_or_named_preset_path(
            agent_def_dir=resolved_agent_def_dir,
            selector=preset,
        )
        preset_payload = load_brain_recipe(preset_path)

    direct_launch_overrides = (
        load_launch_overrides_input(
            launch_overrides,
            base=cwd,
            source="--launch-overrides",
        )
        if launch_overrides is not None
        else None
    )

    resolved_tool = tool or (preset_payload.tool if preset_payload is not None else None)
    resolved_skills = (
        list(skills) if skills else (preset_payload.skills if preset_payload is not None else [])
    )
    resolved_setup = setup or (preset_payload.setup if preset_payload is not None else None)
    resolved_auth = auth or (preset_payload.auth if preset_payload is not None else None)

    missing: list[str] = []
    if resolved_tool is None:
        missing.append("--tool")
    if not resolved_skills:
        missing.append("--skill")
    if resolved_setup is None:
        missing.append("--setup")
    if resolved_auth is None:
        missing.append("--auth")
    if missing:
        raise click.ClickException(f"Missing required build inputs: {', '.join(missing)}")
    assert resolved_tool is not None
    assert resolved_setup is not None
    assert resolved_auth is not None

    try:
        result = build_brain_home(
            BuildRequest(
                agent_def_dir=resolved_agent_def_dir,
                tool=resolved_tool,
                skills=[str(item) for item in resolved_skills],
                setup=resolved_setup,
                auth=resolved_auth,
                preset_path=preset_path,
                preset_launch_overrides=(
                    preset_payload.launch_overrides if preset_payload is not None else None
                ),
                runtime_root=resolved_runtime_root,
                mailbox=preset_payload.mailbox if preset_payload is not None else None,
                extra=preset_payload.extra if preset_payload is not None else None,
                agent_name=agent_name,
                agent_id=agent_id,
                home_id=home_id,
                reuse_home=reuse_home,
                launch_overrides=direct_launch_overrides,
                operator_prompt_mode=(
                    preset_payload.operator_prompt_mode if preset_payload is not None else None
                ),
                persistent_env_records=(
                    preset_payload.launch_env_records if preset_payload is not None else None
                ),
            )
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    emit(
        {
            "home_id": result.home_id,
            "home_path": str(result.home_path),
            "launch_helper_path": str(result.launch_helper_path),
            "manifest_path": str(result.manifest_path),
            "runtime_root": str(resolved_runtime_root),
            "runtime_root_detail": describe_runtime_root_selection(explicit_root=runtime_root),
            "project_overlay_bootstrapped": project_roots.created_overlay,
            "overlay_root": str(project_roots.overlay_root),
            "overlay_root_detail": describe_overlay_root_selection_source(
                overlay_root_source=project_roots.overlay_root_source,
                overlay_discovery_mode=project_roots.overlay_discovery_mode,
            ),
            "overlay_bootstrap_detail": describe_overlay_bootstrap(
                created_overlay=project_roots.created_overlay
            ),
        }
    )


def _optional_path(value: str | None, *, base: Path) -> Path | None:
    """Resolve one optional CLI path relative to the current working directory."""

    if value is None:
        return None
    return _resolve_path(value, base=base)


def _resolve_agent_def_dir(cli_value: str | None, *, cwd: Path) -> Path:
    """Resolve the agent-definition root used for local brain construction."""

    try:
        return resolve_materialized_project_aware_agent_def_dir(cwd=cwd, cli_value=cli_value)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_path(value: str, *, base: Path) -> Path:
    """Resolve one CLI path relative to the provided base directory."""

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    return candidate.resolve()
