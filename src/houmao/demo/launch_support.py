"""Preset-backed launch helpers shared by demo and tutorial packs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from houmao.agents.definition_parser import (
    AgentPreset,
    ToolAdapter,
    parse_agent_preset,
    parse_tool_adapter,
)


@dataclass(frozen=True)
class ResolvedDemoPresetLaunch:
    """Resolved preset-backed launch inputs for one demo-owned startup flow."""

    preset_path: Path
    preset: AgentPreset
    adapter_path: Path
    adapter: ToolAdapter
    role_prompt_path: Path
    setup_path: Path
    auth_path: Path | None
    auth_env_path: Path | None
    required_auth_paths: tuple[Path, ...]
    optional_auth_paths: tuple[Path, ...]

    @property
    def role_name(self) -> str:
        """Return the preset-owned role name."""

        return self.preset.role_name

    @property
    def tool(self) -> str:
        """Return the preset-owned tool lane."""

        return self.preset.tool

    @property
    def config_profile(self) -> str:
        """Compatibility alias for the selected setup."""

        return self.preset.config_profile

    @property
    def credential_profile(self) -> str | None:
        """Compatibility alias for the selected auth bundle."""

        return self.preset.credential_profile


def normalize_demo_launch_backend(backend: str) -> str:
    """Normalize one demo-local backend onto a currently supported launch surface."""

    stripped = backend.strip()
    if not stripped:
        raise ValueError("Demo backend must not be empty.")
    if stripped == "cao_rest":
        return "local_interactive"
    return stripped


def resolve_demo_preset_launch(
    *,
    agent_def_dir: Path,
    preset_path: Path | str,
) -> ResolvedDemoPresetLaunch:
    """Resolve one preset path into the launch-owned setup and auth inputs."""

    resolved_agent_def_dir = agent_def_dir.resolve()
    resolved_preset_path = _resolve_existing_preset_path(
        agent_def_dir=resolved_agent_def_dir,
        raw_path=preset_path,
    )
    preset = parse_agent_preset(resolved_preset_path)
    adapter_path = (resolved_agent_def_dir / "tools" / preset.tool / "adapter.yaml").resolve()
    adapter = parse_tool_adapter(adapter_path)
    role_prompt_path = (
        resolved_agent_def_dir / "roles" / preset.role_name / "system-prompt.md"
    ).resolve()
    setup_path = (
        resolved_agent_def_dir / "tools" / preset.tool / "setups" / preset.setup
    ).resolve()
    auth_path = (
        (resolved_agent_def_dir / "tools" / preset.tool / "auth" / preset.auth).resolve()
        if preset.auth is not None
        else None
    )
    auth_env_path = (
        (auth_path / adapter.auth_env_source).resolve() if auth_path is not None else None
    )
    required_auth_paths = (
        tuple(
            (auth_path / adapter.auth_files_dir / mapping.source).resolve()
            for mapping in adapter.auth_file_mappings
            if mapping.required
        )
        if auth_path is not None
        else ()
    )
    optional_auth_paths = (
        tuple(
            (auth_path / adapter.auth_files_dir / mapping.source).resolve()
            for mapping in adapter.auth_file_mappings
            if not mapping.required
        )
        if auth_path is not None
        else ()
    )
    return ResolvedDemoPresetLaunch(
        preset_path=resolved_preset_path,
        preset=preset,
        adapter_path=adapter_path,
        adapter=adapter,
        role_prompt_path=role_prompt_path,
        setup_path=setup_path,
        auth_path=auth_path,
        auth_env_path=auth_env_path,
        required_auth_paths=required_auth_paths,
        optional_auth_paths=optional_auth_paths,
    )


def _resolve_existing_preset_path(*, agent_def_dir: Path, raw_path: Path | str) -> Path:
    """Resolve one preset path against the current working tree or agent-def root."""

    requested = Path(raw_path).expanduser()
    candidates: list[Path] = []
    if requested.is_absolute():
        candidates.append(requested.resolve())
    else:
        candidates.append(requested.resolve())
        candidates.append((agent_def_dir / requested).resolve())

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[-1]
