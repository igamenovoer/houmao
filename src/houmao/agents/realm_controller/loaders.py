"""Loaders for repository inputs and runtime manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from houmao.agents.brain_builder import BrainRecipe, load_brain_recipe
from houmao.agents.realm_controller.gateway_models import BlueprintGatewayDefaults

from .errors import LaunchPlanError, SessionManifestError


@dataclass(frozen=True)
class BlueprintBinding:
    """Blueprint mapping between a brain recipe and role.

    Parameters
    ----------
    name:
        Blueprint name.
    brain_recipe_path:
        Path to the linked brain recipe file.
    role:
        Role package name.
    """

    name: str
    brain_recipe_path: Path
    role: str
    gateway: BlueprintGatewayDefaults | None = None


@dataclass(frozen=True)
class RolePackage:
    """Loaded role package prompt."""

    role_name: str
    system_prompt: str
    path: Path


class _StrictBlueprintModel(BaseModel):
    """Strict base model for blueprint parsing."""

    model_config = ConfigDict(extra="forbid", strict=True)


class _BlueprintPayloadV1(_StrictBlueprintModel):
    """Strict schema for blueprint bindings."""

    schema_version: int
    name: str
    role: str
    brain_recipe: str
    gateway: BlueprintGatewayDefaults | None = None

    @field_validator("name", "role", "brain_recipe")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


def _load_mapping_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SessionManifestError(f"Missing file: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        loaded = yaml.safe_load(text)
    except Exception:
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SessionManifestError(f"Could not parse {path} as YAML/JSON: {exc}") from exc

    if not isinstance(loaded, dict):
        raise SessionManifestError(f"Expected top-level mapping in {path}")
    return loaded


def load_brain_manifest(path: Path) -> dict[str, Any]:
    """Load a builder-generated brain manifest.

    Parameters
    ----------
    path:
        Brain manifest file path.

    Returns
    -------
    dict[str, Any]
        Parsed manifest payload.
    """

    payload = _load_mapping_file(path)
    schema_version = payload.get("schema_version")
    if schema_version != 3:
        if schema_version == 1:
            raise LaunchPlanError(
                f"{path}: brain manifest uses legacy schema_version=1. Rebuild the brain "
                "home with the current builder to get schema_version=3 preset support."
            )
        if schema_version == 2:
            raise LaunchPlanError(
                f"{path}: brain manifest uses schema_version=2. Rebuild the brain home with the "
                "current builder to get schema_version=3 preset support."
            )
        raise LaunchPlanError(f"{path}: brain manifest must use schema_version=3")
    if not isinstance(payload.get("runtime"), dict):
        raise LaunchPlanError(f"Manifest missing `runtime` mapping: {path}")
    if not isinstance(payload.get("credentials"), dict):
        raise LaunchPlanError(f"Manifest missing `credentials` mapping: {path}")
    return payload


def load_blueprint(path: Path) -> BlueprintBinding:
    """Load a blueprint binding.

    Parameters
    ----------
    path:
        Blueprint YAML/JSON file path.

    Returns
    -------
    BlueprintBinding
        Parsed blueprint payload.
    """

    payload = _load_mapping_file(path)
    try:
        parsed = _BlueprintPayloadV1.model_validate(payload)
    except ValidationError as exc:
        details: list[str] = []
        for issue in exc.errors(include_url=False):
            location = ".".join(str(part) for part in issue.get("loc", ())) or "$"
            details.append(f"{location}: {issue.get('msg', 'validation failed')}")
            if len(details) >= 3:
                break
        joined = "; ".join(details) if details else "validation failed"
        raise LaunchPlanError(f"{path}: blueprint validation failed: {joined}") from exc

    if parsed.schema_version != 1:
        raise LaunchPlanError(f"{path}: only schema_version=1 is supported")

    recipe_path = (path.parent / parsed.brain_recipe).resolve()
    return BlueprintBinding(
        name=parsed.name,
        brain_recipe_path=recipe_path,
        role=parsed.role,
        gateway=parsed.gateway,
    )


def load_brain_recipe_from_path(path: Path) -> BrainRecipe:
    """Load a brain recipe from YAML/JSON.

    Parameters
    ----------
    path:
        Recipe file path.

    Returns
    -------
    BrainRecipe
        Parsed recipe.
    """

    return load_brain_recipe(path)


def load_role_package(agent_def_dir: Path, role_name: str) -> RolePackage:
    """Load a role package system prompt.

    Parameters
    ----------
    agent_def_dir:
        Agent definition directory path.
    role_name:
        Role package directory name under `roles/`.

    Returns
    -------
    RolePackage
        Loaded role prompt and source path.
    """

    role_path = agent_def_dir / "roles" / role_name / "system-prompt.md"
    if not role_path.is_file():
        raise LaunchPlanError(f"Role prompt not found: {role_path}")
    prompt = role_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise LaunchPlanError(f"Role prompt is empty: {role_path}")
    return RolePackage(role_name=role_name, system_prompt=prompt, path=role_path)


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse an env file as key/value pairs.

    Parameters
    ----------
    path:
        Env file path.

    Returns
    -------
    dict[str, str]
        Parsed key/value values.
    """

    if not path.is_file():
        raise LaunchPlanError(f"Missing env file: {path}")

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def parse_allowlisted_env(path: Path, allowlist: list[str]) -> tuple[dict[str, str], list[str]]:
    """Parse an env file and select allowlisted keys.

    Parameters
    ----------
    path:
        Source env file path.
    allowlist:
        Env var names accepted by the tool adapter.

    Returns
    -------
    tuple[dict[str, str], list[str]]
        Selected env values and selected key names.
    """

    parsed = parse_env_file(path)
    selected = {name: parsed[name] for name in allowlist if name in parsed}
    return selected, sorted(selected.keys())
