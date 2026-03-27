"""Shared native launch-target resolution for pair launch flows."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from houmao.agents.brain_builder import BrainRecipe, load_brain_recipe
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR

_RECIPE_FILE_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
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
    recipe_path: Path
    recipe: BrainRecipe
    role_name: str | None
    role_prompt: str
    role_prompt_path: Path | None


def tool_for_provider(provider: str) -> str:
    """Return the native tool lane for one provider identifier."""

    stripped = provider.strip()
    if not stripped:
        raise ValueError("Provider must not be empty.")
    return _TOOL_BY_PROVIDER.get(stripped, stripped)


def resolve_effective_agent_def_dir(*, working_directory: Path) -> Path:
    """Resolve the effective agent-definition root for pair launch."""

    env_value = os.environ.get(AGENT_DEF_DIR_ENV_VAR)
    if env_value is not None and env_value.strip():
        return Path(env_value).expanduser().resolve()
    return (working_directory.resolve() / ".agentsys" / "agents").resolve()


def resolve_native_launch_target(
    *,
    selector: str,
    provider: str,
    working_directory: Path,
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
    agent_def_dir = resolve_effective_agent_def_dir(working_directory=resolved_working_directory)
    recipe_path = _resolve_recipe_path(
        selector=resolved_selector,
        tool=resolved_tool,
        agent_def_dir=agent_def_dir,
    )
    recipe = load_brain_recipe(recipe_path)
    if recipe.tool != resolved_tool:
        raise ValueError(
            f"Resolved recipe `{recipe_path}` targets tool `{recipe.tool}`, not `{resolved_tool}`."
        )

    role_name, role_prompt, role_prompt_path = _resolve_optional_role(
        selector=resolved_selector,
        agent_def_dir=agent_def_dir,
    )
    return ResolvedNativeLaunchTarget(
        selector=resolved_selector,
        provider=resolved_provider,
        tool=resolved_tool,
        working_directory=resolved_working_directory,
        agent_def_dir=agent_def_dir,
        recipe_path=recipe_path,
        recipe=recipe,
        role_name=role_name,
        role_prompt=role_prompt,
        role_prompt_path=role_prompt_path,
    )


def _resolve_recipe_path(
    *,
    selector: str,
    tool: str,
    agent_def_dir: Path,
) -> Path:
    """Resolve one recipe path from selector and tool lane."""

    if _is_path_like_selector(selector):
        return _resolve_path_like_recipe_path(selector=selector, agent_def_dir=agent_def_dir)

    recipe_root = (agent_def_dir / "brains" / "brain-recipes" / tool).resolve()
    candidates = (
        recipe_root / f"{selector}.yaml",
        recipe_root / f"{selector}.yml",
        recipe_root / f"{selector}-default.yaml",
        recipe_root / f"{selector}-default.yml",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        f"Could not resolve a native brain recipe for `{selector}` under `{recipe_root}`."
    )


def _is_path_like_selector(selector: str) -> bool:
    """Return whether the selector should be interpreted as a path-like value."""

    return (
        "/" in selector
        or "\\" in selector
        or selector.startswith(".")
        or selector.startswith("~")
        or selector.endswith(_RECIPE_FILE_SUFFIXES)
    )


def _resolve_path_like_recipe_path(*, selector: str, agent_def_dir: Path) -> Path:
    """Resolve one path-like selector against the effective agent-def root."""

    base_path = Path(selector).expanduser()
    if not base_path.is_absolute():
        base_path = (agent_def_dir / base_path).resolve()
    else:
        base_path = base_path.resolve()

    candidates: tuple[Path, ...]
    if base_path.suffix in _RECIPE_FILE_SUFFIXES:
        candidates = (base_path,)
    else:
        candidates = tuple(base_path.with_suffix(suffix) for suffix in _RECIPE_FILE_SUFFIXES)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not resolve native recipe path from selector `{selector}`.")


def _resolve_optional_role(
    *, selector: str, agent_def_dir: Path
) -> tuple[str | None, str, Path | None]:
    """Resolve one optional role binding for a native launch selector."""

    role_candidate = _safe_role_name(selector)
    role_prompt_path = (agent_def_dir / "roles" / role_candidate / "system-prompt.md").resolve()
    if not role_prompt_path.is_file():
        return None, "", None
    return role_candidate, role_prompt_path.read_text(encoding="utf-8").strip(), role_prompt_path


def _safe_role_name(value: str) -> str:
    stripped = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-" for character in value
    )
    stripped = stripped.strip("-_")
    return stripped or "brain-only"
