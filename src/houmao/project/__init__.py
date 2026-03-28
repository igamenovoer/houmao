"""Repo-local Houmao project overlay helpers."""

from houmao.project.overlay import (
    AgentDefDirResolution,
    HoumaoProjectOverlay,
    ProjectInitResult,
    bootstrap_project_overlay,
    default_project_gitignore,
    discover_project_overlay,
    load_project_overlay,
    project_config_path,
    project_overlay_root,
    render_default_project_config,
    resolve_project_aware_agent_def_dir,
)

__all__ = [
    "AgentDefDirResolution",
    "HoumaoProjectOverlay",
    "ProjectInitResult",
    "bootstrap_project_overlay",
    "default_project_gitignore",
    "discover_project_overlay",
    "load_project_overlay",
    "project_config_path",
    "project_overlay_root",
    "render_default_project_config",
    "resolve_project_aware_agent_def_dir",
]
