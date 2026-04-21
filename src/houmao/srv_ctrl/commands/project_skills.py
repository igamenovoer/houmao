"""Project-scoped canonical skill registry commands."""

from __future__ import annotations

from typing import Literal, cast

from houmao.project.catalog import ProjectCatalog

# ruff: noqa: F403,F405
from .project_common import *


@click.group(name="skills")
def project_skills_group() -> None:
    """Manage canonical project-local skills under `.houmao/content/skills/`."""


@project_skills_group.command(name="list")
def list_project_skills_command() -> None:
    """List registered project-local skills."""

    overlay = _resolve_existing_project_overlay()
    catalog = ProjectCatalog.from_overlay(overlay)
    emit(
        {
            "project_root": str(overlay.project_root),
            "skills": [
                _project_skill_payload(overlay=overlay, metadata=metadata)
                for metadata in catalog.list_project_skills()
            ],
        }
    )


@project_skills_group.command(name="get")
@click.option("--name", required=True, help="Registered project skill name.")
def get_project_skill_command(name: str) -> None:
    """Inspect one registered project-local skill."""

    overlay = _resolve_existing_project_overlay()
    skill_name = _require_non_empty_name(name, field_name="--name")
    try:
        metadata = ProjectCatalog.from_overlay(overlay).load_project_skill(skill_name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_skill_payload(overlay=overlay, metadata=metadata))


@project_skills_group.command(name="add")
@click.option("--name", required=True, help="New project skill name.")
@click.option(
    "--source",
    required=True,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Source skill directory containing `SKILL.md`.",
)
@click.option(
    "--mode",
    type=click.Choice(("copy", "symlink")),
    default="copy",
    show_default=True,
    help="Canonical project skill storage mode.",
)
def add_project_skill_command(name: str, source: Path, mode: str) -> None:
    """Register one new project-local skill."""

    overlay = _ensure_project_overlay()
    skill_name = _require_non_empty_name(name, field_name="--name")
    catalog = ProjectCatalog.from_overlay(overlay)
    try:
        metadata = catalog.create_project_skill_from_source(
            name=skill_name,
            source_path=source,
            mode=cast(Literal["copy", "symlink"], mode),
        )
        materialize_project_agent_catalog_projection(overlay)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_skill_payload(overlay=overlay, metadata=metadata))


@project_skills_group.command(name="set")
@click.option("--name", required=True, help="Registered project skill name.")
@click.option(
    "--source",
    required=True,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Replacement source skill directory containing `SKILL.md`.",
)
@click.option(
    "--mode",
    type=click.Choice(("copy", "symlink")),
    default="copy",
    show_default=True,
    help="Canonical project skill storage mode.",
)
def set_project_skill_command(name: str, source: Path, mode: str) -> None:
    """Update one registered project-local skill."""

    overlay = _resolve_existing_project_overlay()
    skill_name = _require_non_empty_name(name, field_name="--name")
    catalog = ProjectCatalog.from_overlay(overlay)
    try:
        metadata = catalog.update_project_skill_from_source(
            name=skill_name,
            source_path=source,
            mode=cast(Literal["copy", "symlink"], mode),
        )
        materialize_project_agent_catalog_projection(overlay)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(_project_skill_payload(overlay=overlay, metadata=metadata))


@project_skills_group.command(name="remove")
@click.option("--name", required=True, help="Registered project skill name.")
def remove_project_skill_command(name: str) -> None:
    """Remove one unreferenced project-local skill registration."""

    overlay = _resolve_existing_project_overlay()
    skill_name = _require_non_empty_name(name, field_name="--name")
    catalog = ProjectCatalog.from_overlay(overlay)
    try:
        metadata = catalog.remove_project_skill(skill_name)
        materialize_project_agent_catalog_projection(overlay)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            **_project_skill_payload(overlay=overlay, metadata=metadata),
            "removed": True,
        }
    )
