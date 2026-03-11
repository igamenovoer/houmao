"""Recipe resolution helpers for the interactive CAO demo.

This module centralizes the recipe-first startup contract used by the
interactive CAO full-pipeline demo. It resolves operator-provided recipe
selectors under the fixed `brains/brain-recipes/` root, normalizes canonical
selectors, detects basename ambiguity, and loads the shared recipe payload used
to drive startup metadata.

Classes
-------
ResolvedDemoBrainRecipe
    Resolved recipe metadata consumed by interactive-demo startup.

Functions
---------
resolve_demo_brain_recipe
    Resolve one operator-facing recipe selector into canonical startup data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from gig_agents.agents.brain_builder import BrainRecipe
from gig_agents.agents.brain_launch_runtime.loaders import load_brain_recipe_from_path
from gig_agents.demo.cao_interactive_demo.models import (
    BRAIN_RECIPES_RELATIVE_DIR,
    DEFAULT_BRAIN_RECIPE_SELECTOR,
    DemoWorkflowError,
)


@dataclass(frozen=True)
class ResolvedDemoBrainRecipe:
    """Resolved interactive-demo recipe selection.

    Attributes
    ----------
    canonical_selector:
        Canonical recipe selector relative to `brains/brain-recipes/`, without
        the `.yaml` suffix.
    variant_id:
        Stable machine-friendly identifier derived from `canonical_selector`.
    recipe_path:
        Absolute path to the resolved recipe file.
    recipe:
        Shared recipe payload loaded through the runtime recipe loader.
    default_agent_name:
        Default agent name declared by the selected recipe.
    """

    canonical_selector: str
    variant_id: str
    recipe_path: Path
    recipe: BrainRecipe
    default_agent_name: str

    @property
    def tool(self) -> str:
        """Return the recipe-selected tool.

        Returns
        -------
        str
            Tool identifier declared by the resolved recipe.
        """

        return self.recipe.tool


def resolve_demo_brain_recipe(
    *,
    agent_def_dir: Path,
    selector: str | None,
) -> ResolvedDemoBrainRecipe:
    """Resolve a demo recipe selector under the fixed recipe root.

    Parameters
    ----------
    agent_def_dir:
        Agent definition root that contains `brains/brain-recipes/`.
    selector:
        Optional selector relative to the fixed recipe root. When omitted, the
        default Claude recipe is used.

    Returns
    -------
    ResolvedDemoBrainRecipe
        Canonical selector, resolved file path, shared recipe payload, and the
        validated default agent name required by the interactive demo.

    Examples
    --------
    Resolve the default demo recipe:

    >>> resolve_demo_brain_recipe(agent_def_dir=Path("tests/fixtures/agents"), selector=None)

    Resolve an explicit Codex recipe:

    >>> resolve_demo_brain_recipe(
    ...     agent_def_dir=Path("tests/fixtures/agents"),
    ...     selector="codex/gpu-kernel-coder-default",
    ... )
    """

    recipe_root = (agent_def_dir / BRAIN_RECIPES_RELATIVE_DIR).expanduser().resolve()
    if not recipe_root.is_dir():
        raise DemoWorkflowError(f"Interactive demo recipe root not found: `{recipe_root}`.")

    normalized_selector = _normalize_selector(selector or DEFAULT_BRAIN_RECIPE_SELECTOR)
    if "/" in normalized_selector:
        recipe_path = _resolve_subpath_selector(
            recipe_root=recipe_root, selector=normalized_selector
        )
    else:
        recipe_path = _resolve_basename_selector(
            recipe_root=recipe_root,
            selector=normalized_selector,
        )

    recipe = load_brain_recipe_from_path(recipe_path)
    default_agent_name = (recipe.default_agent_name or "").strip()
    if not default_agent_name:
        canonical_selector = _canonical_selector(recipe_root=recipe_root, recipe_path=recipe_path)
        raise DemoWorkflowError(
            f"Interactive demo recipe `{canonical_selector}` must declare `default_agent_name`."
        )

    canonical_selector = _canonical_selector(recipe_root=recipe_root, recipe_path=recipe_path)
    return ResolvedDemoBrainRecipe(
        canonical_selector=canonical_selector,
        variant_id=canonical_selector.replace("/", "-"),
        recipe_path=recipe_path,
        recipe=recipe,
        default_agent_name=default_agent_name,
    )


def _normalize_selector(selector: str) -> str:
    """Return a normalized selector without a `.yaml` suffix."""

    raw_selector = selector.strip().replace("\\", "/")
    if not raw_selector:
        raise DemoWorkflowError("Brain recipe selector must not be empty.")

    posix_selector = PurePosixPath(raw_selector)
    if posix_selector.is_absolute():
        raise DemoWorkflowError("Brain recipe selector must be relative to the fixed recipe root.")
    if any(part in {"", ".", ".."} for part in posix_selector.parts):
        raise DemoWorkflowError(
            "Brain recipe selector must stay within the fixed recipe root and must not "
            "contain `.` or `..` path segments."
        )

    normalized = posix_selector.as_posix()
    if normalized.endswith(".yaml"):
        normalized = normalized[: -len(".yaml")]
    if not normalized:
        raise DemoWorkflowError("Brain recipe selector must not be empty.")
    return normalized


def _resolve_subpath_selector(*, recipe_root: Path, selector: str) -> Path:
    """Resolve a selector that already includes subdirectory context."""

    candidate = (recipe_root / selector).with_suffix(".yaml").resolve()
    try:
        candidate.relative_to(recipe_root)
    except ValueError as exc:
        raise DemoWorkflowError(
            "Brain recipe selector must stay within the fixed recipe root."
        ) from exc
    if not candidate.is_file():
        raise DemoWorkflowError(f"No brain recipe matched `{selector}` under `{recipe_root}`.")
    return candidate


def _resolve_basename_selector(*, recipe_root: Path, selector: str) -> Path:
    """Resolve a basename selector and detect ambiguity explicitly."""

    matches = sorted(recipe_root.rglob(f"{selector}.yaml"))
    if not matches:
        raise DemoWorkflowError(f"No brain recipe matched `{selector}` under `{recipe_root}`.")
    if len(matches) > 1:
        canonical_matches = ", ".join(
            _canonical_selector(recipe_root=recipe_root, recipe_path=path) for path in matches
        )
        example_selector = _canonical_selector(recipe_root=recipe_root, recipe_path=matches[0])
        raise DemoWorkflowError(
            f"Multiple brain recipes matched `{selector}`: {canonical_matches}. "
            "Retry with subdirectory context, for example "
            f"`--brain-recipe {example_selector}`."
        )
    return matches[0].resolve()


def _canonical_selector(*, recipe_root: Path, recipe_path: Path) -> str:
    """Return the canonical selector for a resolved recipe file."""

    relative_path = recipe_path.resolve().relative_to(recipe_root)
    return relative_path.with_suffix("").as_posix()
