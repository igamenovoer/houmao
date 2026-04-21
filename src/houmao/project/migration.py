"""Explicit project-structure migration helpers for repo-local Houmao overlays."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import tomllib
from typing import Any, Literal, cast

from houmao.agents.definition_parser import parse_agent_preset
from houmao.agents.model_selection import model_config_to_payload
from houmao.project.catalog import (
    CATALOG_SCHEMA_VERSION,
    ProjectCatalog,
    _catalog_schema_version,
)
from houmao.project.overlay import HoumaoProjectOverlay


@dataclass(frozen=True)
class ProjectMigrationStep:
    """One named migration step planned for one project overlay."""

    code: str
    description: str
    paths: tuple[Path, ...]
    automatic: bool = True

    def to_payload(self) -> dict[str, object]:
        """Return one operator-facing payload."""

        return {
            "code": self.code,
            "description": self.description,
            "paths": [str(path) for path in self.paths],
            "automatic": self.automatic,
        }


@dataclass(frozen=True)
class ProjectMigrationPlan:
    """Detected project migration plan for one overlay."""

    overlay_root: Path
    catalog_path: Path
    catalog_version: int
    required: bool
    can_apply: bool
    steps: tuple[ProjectMigrationStep, ...]
    unsupported_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return one operator-facing payload."""

        return {
            "overlay_root": str(self.overlay_root),
            "catalog_path": str(self.catalog_path),
            "catalog_version": self.catalog_version,
            "migration_required": self.required,
            "can_apply": self.can_apply,
            "steps": [step.to_payload() for step in self.steps],
            "unsupported_reasons": list(self.unsupported_reasons),
        }


@dataclass(frozen=True)
class ProjectMigrationApplyResult:
    """Result of applying one project migration plan."""

    plan: ProjectMigrationPlan
    applied_steps: tuple[ProjectMigrationStep, ...]

    def to_payload(self) -> dict[str, object]:
        """Return one operator-facing payload."""

        payload = self.plan.to_payload()
        payload["applied"] = True
        payload["applied_steps"] = [step.to_payload() for step in self.applied_steps]
        return payload


@dataclass(frozen=True)
class LegacySpecialistMetadata:
    """Parsed legacy easy-specialist metadata file."""

    path: Path
    name: str
    tool: str
    provider: str
    credential_name: str
    role_name: str
    system_prompt_path: Path
    preset_path: Path
    auth_path: Path
    skills: tuple[str, ...]


def detect_project_migration_plan(overlay: HoumaoProjectOverlay) -> ProjectMigrationPlan:
    """Detect supported migration steps for one project overlay."""

    catalog = ProjectCatalog.from_overlay(overlay)
    state = catalog.detect_pending_migration()
    catalog_exists = overlay.catalog_path.exists()
    unsupported_reasons: list[str] = []
    steps: list[ProjectMigrationStep] = []

    if catalog_exists and state.catalog_version not in {14, CATALOG_SCHEMA_VERSION}:
        unsupported_reasons.append(
            f"catalog schema version `{state.catalog_version}` is not supported for automatic migration"
        )

    if not catalog_exists:
        steps.append(
            ProjectMigrationStep(
                code="initialize-current-catalog",
                description="Create the current catalog-backed project storage.",
                paths=(overlay.catalog_path,),
            )
        )
    elif state.catalog_version == 14:
        steps.append(
            ProjectMigrationStep(
                code="upgrade-catalog-schema",
                description="Upgrade the project catalog schema for project skill registry metadata.",
                paths=(overlay.catalog_path,),
            )
        )

    if state.unmanaged_skill_paths:
        steps.append(
            ProjectMigrationStep(
                code="canonicalize-project-skills",
                description=(
                    "Import compatibility-tree-first project skills into canonical "
                    "`.houmao/content/skills/` entries and rebuild `.houmao/agents/skills/` as "
                    "derived projection."
                ),
                paths=state.unmanaged_skill_paths,
            )
        )

    legacy_specialist_paths = state.legacy_specialist_paths
    if legacy_specialist_paths:
        parse_errors = _validate_legacy_specialists(overlay, legacy_specialist_paths)
        unsupported_reasons.extend(parse_errors)
        steps.append(
            ProjectMigrationStep(
                code="import-legacy-easy-specialists",
                description="Import legacy `.houmao/easy/specialists/*.toml` metadata into the catalog.",
                paths=legacy_specialist_paths,
            )
        )

    return ProjectMigrationPlan(
        overlay_root=overlay.overlay_root,
        catalog_path=overlay.catalog_path,
        catalog_version=state.catalog_version,
        required=bool(steps or unsupported_reasons),
        can_apply=not unsupported_reasons,
        steps=tuple(steps),
        unsupported_reasons=tuple(unsupported_reasons),
    )


def apply_project_migration(overlay: HoumaoProjectOverlay) -> ProjectMigrationApplyResult:
    """Apply the supported migration steps for one project overlay."""

    plan = detect_project_migration_plan(overlay)
    if not plan.required:
        return ProjectMigrationApplyResult(plan=plan, applied_steps=())
    if not plan.can_apply:
        joined = "; ".join(plan.unsupported_reasons)
        raise ValueError(f"Automatic project migration is not supported for this overlay: {joined}")

    applied_steps: list[ProjectMigrationStep] = []
    if any(step.code == "initialize-current-catalog" for step in plan.steps):
        ProjectCatalog.from_overlay(overlay).initialize(allow_pending_migration=True)
        applied_steps.extend(
            step for step in plan.steps if step.code == "initialize-current-catalog"
        )
    elif any(step.code == "upgrade-catalog-schema" for step in plan.steps):
        _upgrade_catalog_schema_in_place(overlay.catalog_path)
        ProjectCatalog.from_overlay(overlay).initialize(allow_pending_migration=True)
        applied_steps.extend(step for step in plan.steps if step.code == "upgrade-catalog-schema")

    catalog = ProjectCatalog.from_overlay(overlay)
    if any(step.code == "canonicalize-project-skills" for step in plan.steps):
        for legacy_skill_path in _legacy_projection_skills_to_import(
            overlay=overlay, catalog=catalog
        ):
            mode = "symlink" if legacy_skill_path.is_symlink() else "copy"
            source_path = (
                legacy_skill_path.resolve() if legacy_skill_path.is_symlink() else legacy_skill_path
            )
            catalog.ensure_project_skill_from_source(
                name=legacy_skill_path.name,
                source_path=source_path,
                mode=cast(Literal["copy", "symlink"], mode),
                allow_pending_migration=True,
            )
        applied_steps.extend(
            step for step in plan.steps if step.code == "canonicalize-project-skills"
        )

    if any(step.code == "import-legacy-easy-specialists" for step in plan.steps):
        for metadata in _load_legacy_specialists(overlay):
            preset = parse_agent_preset(metadata.preset_path)
            auth_profile = catalog.ensure_auth_profile_from_source(
                tool=metadata.tool,
                display_name=metadata.credential_name,
                source_path=metadata.auth_path,
                allow_pending_migration=True,
            )
            missing_skills = [
                skill_name
                for skill_name in preset.skills
                if not catalog.project_skill_exists(
                    skill_name,
                    allow_pending_migration=True,
                )
            ]
            if missing_skills:
                joined = ", ".join(missing_skills)
                raise ValueError(
                    f"Legacy specialist `{metadata.name}` references missing project skill(s): {joined}"
                )
            catalog.store_specialist(
                name=metadata.name,
                preset_name=preset.name,
                tool=metadata.tool,
                provider=metadata.provider,
                auth_profile=auth_profile,
                role_name=metadata.role_name,
                setup_name=preset.setup,
                prompt_path=metadata.system_prompt_path,
                skill_names=tuple(preset.skills),
                setup_path=None,
                launch_mapping=_legacy_launch_mapping(preset),
                mailbox_mapping=_normalize_payload_model(preset.mailbox),
                extra_mapping=dict(preset.extra),
                allow_pending_migration=True,
            )
            metadata.path.unlink(missing_ok=True)
        legacy_specialists_root = overlay.specialists_root
        if legacy_specialists_root.is_dir() and not any(legacy_specialists_root.iterdir()):
            legacy_specialists_root.rmdir()
        if overlay.easy_root.is_dir() and not any(overlay.easy_root.iterdir()):
            overlay.easy_root.rmdir()
        applied_steps.extend(
            step for step in plan.steps if step.code == "import-legacy-easy-specialists"
        )

    catalog.materialize_projection()
    return ProjectMigrationApplyResult(
        plan=detect_project_migration_plan(overlay), applied_steps=tuple(applied_steps)
    )


def _validate_legacy_specialists(
    overlay: HoumaoProjectOverlay,
    paths: tuple[Path, ...],
) -> list[str]:
    """Validate whether one set of legacy specialist files is migratable."""

    errors: list[str] = []
    for path in paths:
        try:
            metadata = _load_legacy_specialist_file(overlay=overlay, path=path)
            parse_agent_preset(metadata.preset_path)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"{path}: {exc}")
    return errors


def _load_legacy_specialists(overlay: HoumaoProjectOverlay) -> list[LegacySpecialistMetadata]:
    """Load every legacy specialist metadata file in one overlay."""

    if not overlay.specialists_root.is_dir():
        return []
    return [
        _load_legacy_specialist_file(overlay=overlay, path=path)
        for path in sorted(overlay.specialists_root.glob("*.toml"))
    ]


def _load_legacy_specialist_file(
    *,
    overlay: HoumaoProjectOverlay,
    path: Path,
) -> LegacySpecialistMetadata:
    """Parse one legacy easy-specialist metadata file."""

    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    name = _require_str(payload, "name", source=str(path))
    tool = _require_str(payload, "tool", source=str(path))
    provider = _require_str(payload, "provider", source=str(path))
    credential_name = _require_str(payload, "credential_name", source=str(path))
    role_name = _require_str(payload, "role_name", source=str(path))
    system_prompt_path = _resolve_overlay_relative_path(
        overlay=overlay,
        raw_value=_require_str(payload, "system_prompt_path", source=str(path)),
    )
    preset_path = _resolve_overlay_relative_path(
        overlay=overlay,
        raw_value=_require_str(payload, "preset_path", source=str(path)),
    )
    auth_path = _resolve_overlay_relative_path(
        overlay=overlay,
        raw_value=_require_str(payload, "auth_path", source=str(path)),
    )
    raw_skills = payload.get("skills", [])
    if not isinstance(raw_skills, list) or any(not isinstance(item, str) for item in raw_skills):
        raise ValueError(f"{path}: `skills` must be a string list")
    for candidate in (system_prompt_path, preset_path, auth_path):
        if not candidate.exists() and not candidate.is_symlink():
            raise ValueError(f"{path}: referenced path does not exist: {candidate}")
    for skill_name in raw_skills:
        skill_path = (overlay.agents_root / "skills" / skill_name).resolve()
        if not (skill_path / "SKILL.md").is_file():
            raise ValueError(f"{path}: referenced skill was not found: {skill_path}")
    return LegacySpecialistMetadata(
        path=path,
        name=name,
        tool=tool,
        provider=provider,
        credential_name=credential_name,
        role_name=role_name,
        system_prompt_path=system_prompt_path,
        preset_path=preset_path,
        auth_path=auth_path,
        skills=tuple(raw_skills),
    )


def _legacy_projection_skills_to_import(
    *,
    overlay: HoumaoProjectOverlay,
    catalog: ProjectCatalog,
) -> list[Path]:
    """Return legacy compatibility-tree skills that still need import."""

    if not overlay.agents_root.joinpath("skills").is_dir():
        return []
    return [
        path
        for path in sorted((overlay.agents_root / "skills").iterdir())
        if not catalog.project_skill_exists(path.name, allow_pending_migration=True)
    ]


def _upgrade_catalog_schema_in_place(catalog_path: Path) -> None:
    """Upgrade one version-14 catalog in place to the current schema."""

    connection = sqlite3.connect(catalog_path)
    try:
        connection.row_factory = sqlite3.Row
        version = _catalog_schema_version(connection)
        if version == CATALOG_SCHEMA_VERSION:
            return
        if version != 14:
            raise ValueError(
                f"Catalog `{catalog_path}` is not at a supported migratable schema version: {version}"
            )
        column_names = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(skill_packages)").fetchall()
        }
        if "mode" not in column_names:
            connection.execute("ALTER TABLE skill_packages ADD COLUMN mode TEXT DEFAULT 'copy'")
        if "source_path" not in column_names:
            connection.execute("ALTER TABLE skill_packages ADD COLUMN source_path TEXT")
        connection.execute(
            "UPDATE skill_packages SET mode = 'copy' WHERE mode IS NULL OR TRIM(mode) = ''"
        )
        connection.execute(
            "UPDATE catalog_meta SET value = ? WHERE key = 'schema_version'",
            (str(CATALOG_SCHEMA_VERSION),),
        )
        connection.commit()
    finally:
        connection.close()


def _legacy_launch_mapping(preset: Any) -> dict[str, Any]:
    """Convert one parsed preset launch block into stored specialist launch payload."""

    payload: dict[str, Any] = {}
    if preset.launch.prompt_mode is not None:
        payload["prompt_mode"] = preset.launch.prompt_mode
    model_payload = model_config_to_payload(preset.launch.model_config)
    if model_payload is not None:
        payload["model"] = model_payload
    if preset.launch.env_records:
        payload["env_records"] = dict(preset.launch.env_records)
    return payload


def _normalize_payload_model(value: object) -> dict[str, Any] | None:
    """Normalize one payload-ish model into a plain mapping when present."""

    if value is None:
        return None
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        payload = model_dump(mode="json")
        return payload if isinstance(payload, dict) else None
    if isinstance(value, dict):
        return dict(value)
    return None


def _resolve_overlay_relative_path(*, overlay: HoumaoProjectOverlay, raw_value: str) -> Path:
    """Resolve one path stored relative to the project overlay root."""

    candidate = Path(raw_value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (overlay.overlay_root / candidate).resolve()


def _require_str(payload: dict[str, object], key: str, *, source: str) -> str:
    """Require one non-empty string key from a TOML payload."""

    raw_value = payload.get(key)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{source}: `{key}` must be a non-empty string")
    return raw_value.strip()


__all__ = [
    "ProjectMigrationApplyResult",
    "ProjectMigrationPlan",
    "ProjectMigrationStep",
    "apply_project_migration",
    "detect_project_migration_plan",
]
