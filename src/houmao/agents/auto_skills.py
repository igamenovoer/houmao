"""Catalog loading and projection helpers for Houmao-managed auto skills."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
import hashlib
import shutil
from typing import Any, Literal

from houmao.agents.launch_policy.provider_hooks import load_toml_state, set_toml_key
from houmao.agents.system_skills import system_skills_destination_for_tool

AUTO_SKILLS_PACKAGE = "houmao.agents.assets.auto_skills"
AUTO_SKILL_SYSTEM_PROMPT = "houmao-auto-system-prompt"
AUTO_SKILL_SYSTEM_PROMPT_REASON = "auto_skill_system_prompt_role_injection"

AutoSkillProjectionMode = Literal["copy"]


class AutoSkillError(RuntimeError):
    """Base error for Houmao-managed auto-skill loading and projection."""


class AutoSkillCatalogError(AutoSkillError):
    """Raised when packaged auto-skill assets are invalid."""


class AutoSkillProjectionError(AutoSkillError):
    """Raised when auto-skill projection cannot complete safely."""


@dataclass(frozen=True)
class AutoSkillRecord:
    """One packaged Houmao-managed auto skill."""

    name: str
    asset_subpath: str


@dataclass(frozen=True)
class AutoSkillCatalog:
    """Packaged auto-skill catalog derived from asset directories."""

    skills: dict[str, AutoSkillRecord]

    @property
    def skill_names(self) -> tuple[str, ...]:
        """Return packaged auto-skill names in deterministic order."""

        return tuple(self.skills.keys())


@dataclass(frozen=True)
class AutoSkillProjectionResult:
    """Outcome of one auto-skill projection pass."""

    tool: str
    home_path: Path
    selected_skill_names: tuple[str, ...]
    reason: str
    projected_relative_dirs: tuple[str, ...]
    destination_root: str
    projection_mode: AutoSkillProjectionMode = "copy"
    prompt_reference: str | None = None
    prompt_sha256: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON/YAML-safe provenance payload."""

        payload: dict[str, Any] = {
            "state": "projected",
            "applied": False,
            "tool": self.tool,
            "home_path": str(self.home_path),
            "selected_skill_names": list(self.selected_skill_names),
            "reason": self.reason,
            "projected_relative_dirs": list(self.projected_relative_dirs),
            "destination_root": self.destination_root,
            "projection_mode": self.projection_mode,
        }
        if self.prompt_reference is not None:
            payload["prompt_reference"] = self.prompt_reference
        if self.prompt_sha256 is not None:
            payload["prompt_sha256"] = self.prompt_sha256
        return payload


def auto_skills_destination_for_tool(tool: str) -> str:
    """Return the provider-visible skill destination root for one tool."""

    return system_skills_destination_for_tool(tool)


def projected_auto_skill_relative_dir(*, tool: str, skill_name: str) -> str:
    """Return the home-relative directory for one projected auto skill."""

    _auto_skill_record_for_name(skill_name)
    return str(Path(auto_skills_destination_for_tool(tool)) / skill_name)


def prompt_sha256(prompt: str) -> str:
    """Return the SHA-256 digest for one effective prompt string."""

    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_auto_skill_catalog() -> AutoSkillCatalog:
    """Load the packaged auto-skill catalog from asset directories."""

    package_root = resources.files(AUTO_SKILLS_PACKAGE)
    records: dict[str, AutoSkillRecord] = {}
    for child in sorted(package_root.iterdir(), key=lambda item: item.name):
        if not child.is_dir() or child.name.startswith("_") or child.name == "__pycache__":
            continue
        if not (child / "SKILL.md").is_file():
            continue
        _validate_auto_skill_name(child.name)
        records[child.name] = AutoSkillRecord(
            name=child.name,
            asset_subpath=child.name,
        )

    if AUTO_SKILL_SYSTEM_PROMPT not in records:
        raise AutoSkillCatalogError(
            f"Packaged auto-skill catalog is missing `{AUTO_SKILL_SYSTEM_PROMPT}`."
        )
    return AutoSkillCatalog(skills=records)


def project_auto_skills_for_home(
    *,
    tool: str,
    home_path: Path,
    skill_names: tuple[str, ...],
    reason: str,
    prompt_reference: str | None = None,
    prompt_sha256: str | None = None,
    projection_mode: AutoSkillProjectionMode = "copy",
) -> AutoSkillProjectionResult:
    """Project selected packaged auto skills into one managed provider home."""

    if projection_mode != "copy":
        raise AutoSkillProjectionError(f"Unsupported auto-skill projection mode: {projection_mode}")
    if not skill_names:
        raise AutoSkillProjectionError("At least one auto skill must be selected for projection.")

    catalog = load_auto_skill_catalog()
    resolved_names = _dedupe_skill_names(skill_names)
    unknown_names = sorted(name for name in resolved_names if name not in catalog.skills)
    if unknown_names:
        raise AutoSkillCatalogError(f"Unknown auto skill(s): {', '.join(unknown_names)}")

    resolved_home_path = home_path.resolve()
    destination_root = auto_skills_destination_for_tool(tool)
    projected_relative_dirs: list[str] = []
    for skill_name in resolved_names:
        record = catalog.skills[skill_name]
        projected_relative_dir = projected_auto_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        target_dir = resolved_home_path / projected_relative_dir
        _remove_existing_path_if_present(target_dir)
        _project_traversable_tree(
            resources.files(AUTO_SKILLS_PACKAGE) / record.asset_subpath,
            target_dir,
        )
        projected_relative_dirs.append(projected_relative_dir)

    return AutoSkillProjectionResult(
        tool=tool,
        home_path=resolved_home_path,
        selected_skill_names=resolved_names,
        reason=reason,
        projected_relative_dirs=tuple(projected_relative_dirs),
        destination_root=destination_root,
        projection_mode=projection_mode,
        prompt_reference=prompt_reference,
        prompt_sha256=prompt_sha256,
    )


def ensure_auto_skill_provider_discovery(
    *,
    tool: str,
    home_path: Path,
    destination_root: str,
    has_projected_auto_skills: bool,
) -> dict[str, Any] | None:
    """Ensure provider config can discover projected auto-skill roots when needed."""

    if tool != "kimi" or not has_projected_auto_skills:
        return None

    resolved_home_path = home_path.resolve()
    projected_skill_root = str((resolved_home_path / destination_root).resolve())
    config_path = resolved_home_path / "config.toml"
    payload = load_toml_state(config_path, repair_invalid=True)
    raw_extra_skill_dirs = payload.get("extra_skill_dirs")
    existing_dirs = (
        [entry for entry in raw_extra_skill_dirs if isinstance(entry, str) and entry.strip()]
        if isinstance(raw_extra_skill_dirs, list)
        else []
    )
    next_dirs = list(existing_dirs)
    added = projected_skill_root not in next_dirs
    if added:
        next_dirs.append(projected_skill_root)
        set_toml_key(
            path=config_path,
            key_path=("extra_skill_dirs",),
            value=next_dirs,
            repair_invalid=True,
        )

    return {
        "path": str(config_path),
        "key_path": ["extra_skill_dirs"],
        "projected_skill_root": projected_skill_root,
        "added": added,
        "value": next_dirs,
    }


def _auto_skill_record_for_name(skill_name: str) -> AutoSkillRecord:
    """Return one auto-skill record or raise a catalog error."""

    record = load_auto_skill_catalog().skills.get(skill_name)
    if record is None:
        raise AutoSkillCatalogError(f"Unknown auto skill `{skill_name}`.")
    return record


def _validate_auto_skill_name(name: str) -> None:
    """Reject auto-skill names that cannot be projected as one directory."""

    if not name.strip() or "/" in name or "\\" in name:
        raise AutoSkillCatalogError(f"Invalid auto-skill directory name `{name}`.")


def _dedupe_skill_names(values: tuple[str, ...]) -> tuple[str, ...]:
    """Return skill names in first-seen order with duplicates removed."""

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)


def _remove_existing_path_if_present(path: Path) -> None:
    """Remove an existing file, symlink, or directory before projection."""

    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def _project_traversable_tree(source: Traversable, destination: Path) -> None:
    """Copy one package resource tree into a filesystem destination."""

    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for child in sorted(source.iterdir(), key=lambda item: item.name):
            _project_traversable_tree(child, destination / child.name)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
