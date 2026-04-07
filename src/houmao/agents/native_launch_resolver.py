"""Shared native launch-target resolution for pair launch flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from houmao.agents.definition_parser import AgentPreset, load_agent_catalog, resolve_agent_preset
from houmao.project.overlay import PROJECT_DIRNAME, resolve_materialized_project_aware_agent_def_dir

_TOOL_BY_PROVIDER: dict[str, str] = {
    "claude_code": "claude",
    "codex": "codex",
    "gemini_cli": "gemini",
}


@dataclass(frozen=True)
class ResolvedNativeLaunchTarget:
    """Resolved launch target from pair convenience launch inputs."""

    selector: str
    provider: str
    tool: str
    working_directory: Path
    agent_def_dir: Path
    preset_path: Path
    preset: AgentPreset
    role_name: str
    role_prompt: str
    role_prompt_path: Path

    @property
    def recipe_path(self) -> Path:
        """Compatibility alias for the resolved preset path."""

        return self.preset_path

    @property
    def recipe(self) -> AgentPreset:
        """Compatibility alias for the resolved preset payload."""

        return self.preset


def tool_for_provider(provider: str) -> str:
    """Return the native tool lane for one provider identifier."""

    stripped = provider.strip()
    if not stripped:
        raise ValueError("Provider must not be empty.")
    return _TOOL_BY_PROVIDER.get(stripped, stripped)


def resolve_effective_agent_def_dir(
    *,
    working_directory: Path,
    agent_def_dir: Path | None = None,
) -> Path:
    """Resolve the effective agent-definition root for pair launch."""

    if agent_def_dir is not None:
        return agent_def_dir.resolve()
    return resolve_materialized_project_aware_agent_def_dir(cwd=working_directory.resolve())


def resolve_preset_owner_agent_def_dir(*, preset_path: Path) -> Path:
    """Return the owner agent-definition tree for one resolved preset path."""

    resolved_preset_path = preset_path.resolve()
    if resolved_preset_path.parent.name != "presets":
        raise ValueError(
            f"{preset_path}: preset paths must live under a `presets/` directory."
        )
    return resolved_preset_path.parent.parent.resolve()


def infer_launch_source_directory_from_agent_def_dir(*, agent_def_dir: Path) -> Path:
    """Infer the source directory that should anchor project-aware launch resolution."""

    resolved_agent_def_dir = agent_def_dir.resolve()
    if resolved_agent_def_dir.name == "agents":
        if resolved_agent_def_dir.parent.name == PROJECT_DIRNAME:
            return resolved_agent_def_dir.parent.parent.resolve()
        return resolved_agent_def_dir.parent.resolve()
    return resolved_agent_def_dir


def resolve_native_launch_target(
    *,
    selector: str,
    provider: str,
    working_directory: Path,
    agent_def_dir: Path | None = None,
) -> ResolvedNativeLaunchTarget:
    """Resolve one shared native launch target from pair launch inputs."""

    resolved_working_directory = working_directory.resolve()
    resolved_selector = selector.strip()
    if not resolved_selector:
        raise ValueError("Launch selector must not be empty.")

    resolved_provider = provider.strip()
    if not resolved_provider:
        raise ValueError("Provider must not be empty.")
    resolved_tool = tool_for_provider(resolved_provider)
    resolved_agent_def_dir = resolve_effective_agent_def_dir(
        working_directory=resolved_working_directory,
        agent_def_dir=agent_def_dir,
    )
    catalog = load_agent_catalog(resolved_agent_def_dir)
    preset = resolve_agent_preset(
        catalog=catalog,
        selector=resolved_selector,
        tool=resolved_tool,
    )
    if preset.tool != resolved_tool:
        raise ValueError(
            f"Resolved preset `{preset.path}` targets tool `{preset.tool}`, not `{resolved_tool}`."
        )

    role_prompt, role_prompt_path = _resolve_role_prompt(
        role_name=preset.role_name,
        agent_def_dir=resolved_agent_def_dir,
    )
    return ResolvedNativeLaunchTarget(
        selector=resolved_selector,
        provider=resolved_provider,
        tool=resolved_tool,
        working_directory=resolved_working_directory,
        agent_def_dir=resolved_agent_def_dir,
        preset_path=preset.path,
        preset=preset,
        role_name=preset.role_name,
        role_prompt=role_prompt,
        role_prompt_path=role_prompt_path,
    )


def _resolve_role_prompt(*, role_name: str, agent_def_dir: Path) -> tuple[str, Path]:
    """Resolve the role prompt required by one preset-backed launch."""

    role_prompt_path = (agent_def_dir / "roles" / role_name / "system-prompt.md").resolve()
    if not role_prompt_path.is_file():
        raise FileNotFoundError(
            f"Missing role prompt for preset role `{role_name}`: {role_prompt_path}"
        )
    return role_prompt_path.read_text(encoding="utf-8").strip(), role_prompt_path
