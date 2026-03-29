"""Repo-local Houmao project overlay helpers."""

from houmao.project.overlay import (
    AgentDefDirResolution,
    HoumaoProjectOverlay,
    ProjectInitResult,
    bootstrap_project_overlay,
    default_project_gitignore,
    discover_project_overlay,
    ensure_project_agent_compatibility_tree,
    load_project_overlay,
    materialize_project_agent_catalog_projection,
    project_config_path,
    project_overlay_root,
    render_default_project_config,
    resolve_materialized_project_aware_agent_def_dir,
    resolve_project_aware_agent_def_dir,
)

__all__ = [
    "AgentDefDirResolution",
    "HoumaoProjectOverlay",
    "ProjectInitResult",
    "bootstrap_project_overlay",
    "default_project_gitignore",
    "discover_project_overlay",
    "ensure_project_agent_compatibility_tree",
    "load_project_overlay",
    "materialize_project_agent_catalog_projection",
    "project_config_path",
    "project_overlay_root",
    "render_default_project_config",
    "resolve_materialized_project_aware_agent_def_dir",
    "resolve_project_aware_agent_def_dir",
]
