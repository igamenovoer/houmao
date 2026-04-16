"""SQLite-backed project-local configuration catalog and managed content store."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from importlib import resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path
import shutil
import sqlite3
import tomllib
from typing import TYPE_CHECKING, Any, Iterator, Literal, cast
from uuid import uuid4

from houmao.agents.model_selection import parse_reasoning_level
from houmao.agents.managed_prompt_header import (
    ManagedHeaderPolicy,
    ManagedHeaderSectionName,
    ManagedHeaderSectionPolicy,
    normalize_managed_header_policy,
    normalize_managed_header_section_policy_mapping,
)

if TYPE_CHECKING:
    from houmao.project.overlay import HoumaoProjectOverlay

CATALOG_SCHEMA_VERSION = 11
PROJECT_CATALOG_FILENAME = "catalog.sqlite"
PROJECT_CONTENT_DIRNAME = "content"
_STARTER_ASSET_PACKAGE = "houmao.project.assets"
_STARTER_ASSET_ROOT = "starter_agents"

_CONTENT_KIND_PROMPT = "prompt_blob"
_CONTENT_KIND_AUTH = "auth_tree"
_CONTENT_KIND_SKILL = "skill_tree"
_CONTENT_KIND_SETUP = "setup_tree"
_CONTENT_KIND_MEMO_SEED = "memo_seed"
_CONTENT_KIND_VALUES = (
    _CONTENT_KIND_PROMPT,
    _CONTENT_KIND_AUTH,
    _CONTENT_KIND_SKILL,
    _CONTENT_KIND_SETUP,
    _CONTENT_KIND_MEMO_SEED,
)
_STORAGE_KIND_FILE = "file"
_STORAGE_KIND_TREE = "tree"
_STORAGE_KIND_VALUES = (_STORAGE_KIND_FILE, _STORAGE_KIND_TREE)
_PROFILE_LANE_EASY = "easy_profile"
_PROFILE_LANE_EXPLICIT = "launch_profile"
_PROFILE_LANE_VALUES = (_PROFILE_LANE_EASY, _PROFILE_LANE_EXPLICIT)
_SOURCE_KIND_SPECIALIST = "specialist"
_SOURCE_KIND_RECIPE = "recipe"
_SOURCE_KIND_VALUES = (_SOURCE_KIND_SPECIALIST, _SOURCE_KIND_RECIPE)
_MEMO_SEED_SOURCE_KIND_MEMO = "memo"
_MEMO_SEED_SOURCE_KIND_TREE = "tree"
_MEMO_SEED_SOURCE_KIND_VALUES = (_MEMO_SEED_SOURCE_KIND_MEMO, _MEMO_SEED_SOURCE_KIND_TREE)
_MEMO_SEED_TOP_LEVEL_MEMO_FILE = "houmao-memo.md"
_MEMO_SEED_TOP_LEVEL_PAGES_DIR = "pages"


@dataclass(frozen=True)
class ManagedContentRef:
    """Reference one managed content payload."""

    content_kind: str
    storage_kind: str
    relative_path: str

    def resolve(self, overlay: HoumaoProjectOverlay) -> Path:
        """Resolve this content ref against one overlay content root."""

        return (overlay.content_root / self.relative_path).resolve()

    def resolve_under_content_root(self, content_root: Path) -> Path:
        """Resolve this content ref against one explicit content root."""

        return (content_root.resolve() / self.relative_path).resolve()


@dataclass(frozen=True)
class SpecialistCatalogEntry:
    """Resolved project-local specialist semantics loaded from the catalog."""

    name: str
    preset_name: str
    tool: str
    provider: str
    auth_profile_id: int
    credential_name: str
    auth_bundle_ref: str
    role_name: str
    setup_name: str
    skills: tuple[str, ...]
    prompt_ref: ManagedContentRef
    auth_ref: ManagedContentRef
    skill_refs: tuple[ManagedContentRef, ...]
    launch_payload: dict[str, Any]
    mailbox_payload: dict[str, Any] | None
    extra_payload: dict[str, Any]
    metadata_path: Path | None = None

    def resolved_system_prompt_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the compatibility projection prompt path."""

        return (overlay.agents_root / "roles" / self.role_name / "system-prompt.md").resolve()

    def resolved_preset_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the compatibility projection preset path."""

        return (overlay.agents_root / "presets" / f"{self.preset_name}.yaml").resolve()

    def resolved_auth_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the compatibility projection auth bundle path."""

        return (overlay.agents_root / "tools" / self.tool / "auth" / self.auth_bundle_ref).resolve()

    def resolved_skill_paths(self, overlay: HoumaoProjectOverlay) -> tuple[Path, ...]:
        """Return the compatibility projection skill paths."""

        return tuple(
            (overlay.agents_root / "skills" / skill_name).resolve() for skill_name in self.skills
        )


@dataclass(frozen=True)
class LaunchProfileMemoSeed:
    """Managed memo-seed metadata stored on one launch profile."""

    source_kind: Literal["memo", "tree"]
    content_ref: ManagedContentRef


@dataclass(frozen=True)
class LaunchProfileCatalogEntry:
    """Resolved project-local launch-profile semantics loaded from the catalog."""

    name: str
    profile_lane: str
    source_kind: str
    source_name: str
    managed_agent_name: str | None
    managed_agent_id: str | None
    workdir: str | None
    auth_profile_id: int | None
    auth_name: str | None
    auth_bundle_ref: str | None
    model_name: str | None
    reasoning_level: int | None
    operator_prompt_mode: str | None
    env_payload: dict[str, str]
    mailbox_payload: dict[str, Any] | None
    posture_payload: dict[str, Any]
    managed_header_policy: ManagedHeaderPolicy | None
    prompt_overlay_mode: str | None
    prompt_overlay_ref: ManagedContentRef | None
    memo_seed: LaunchProfileMemoSeed | None = None
    managed_header_section_policy: dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy] = (
        field(default_factory=dict)
    )
    metadata_path: Path | None = None

    def resolved_projection_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the compatibility projection launch-profile path."""

        return (overlay.agents_root / "launch-profiles" / f"{self.name}.yaml").resolve()


@dataclass(frozen=True)
class CatalogIntegrityReport:
    """Validation report for one project-local catalog."""

    missing_content: tuple[str, ...]
    orphaned_content: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether the catalog passed integrity validation."""

        return not self.missing_content


@dataclass(frozen=True)
class AuthProfileCatalogEntry:
    """Resolved project-local auth profile semantics loaded from the catalog."""

    id: int
    tool: str
    display_name: str
    bundle_ref: str
    content_ref: ManagedContentRef
    metadata_path: Path | None = None

    def resolved_projection_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the compatibility projection auth path."""

        return (overlay.agents_root / "tools" / self.tool / "auth" / self.bundle_ref).resolve()


class ProjectCatalog:
    """Repository and projection seam for one project-local catalog."""

    def __init__(
        self,
        *,
        overlay_root: Path,
        catalog_path: Path,
        content_root: Path,
        projection_root: Path,
        legacy_specialists_root: Path,
        legacy_easy_root: Path,
    ) -> None:
        """Initialize one repository bound to a project overlay."""

        self.m_overlay_root = overlay_root.resolve()
        self.m_catalog_path = catalog_path.resolve()
        self.m_content_root = content_root.resolve()
        self.m_projection_root = projection_root.resolve()
        self.m_legacy_specialists_root = legacy_specialists_root.resolve()
        self.m_legacy_easy_root = legacy_easy_root.resolve()

    @classmethod
    def from_overlay(cls, overlay: HoumaoProjectOverlay) -> ProjectCatalog:
        """Build one project catalog repository from a resolved overlay."""

        return cls(
            overlay_root=overlay.overlay_root,
            catalog_path=overlay.catalog_path,
            content_root=overlay.content_root,
            projection_root=overlay.agents_root,
            legacy_specialists_root=overlay.specialists_root,
            legacy_easy_root=overlay.easy_root,
        )

    def initialize(self) -> None:
        """Create the catalog schema and managed content roots when missing."""

        self._ensure_content_roots()
        with self._connect() as connection:
            connection.executescript(_table_schema_sql())
            self._migrate_schema(connection)
            self._ensure_catalog_metadata(connection)
            self._seed_setup_profiles(connection)
            connection.executescript(_view_sql())

    def ensure_legacy_import(self) -> None:
        """Import legacy easy specialists into the catalog when needed."""

        self.initialize()
        if self._specialist_count() > 0:
            return
        if not self.m_legacy_specialists_root.is_dir():
            return

        candidates = sorted(self.m_legacy_specialists_root.glob("*.toml"))
        if not candidates:
            return

        for metadata_path in candidates:
            payload = _load_legacy_specialist_payload(metadata_path)
            prompt_path = (self.m_overlay_root / payload["system_prompt_path"]).resolve()
            preset_path = (self.m_overlay_root / payload["preset_path"]).resolve()
            auth_path = (self.m_overlay_root / payload["auth_path"]).resolve()
            skill_paths = tuple(
                (self.m_projection_root / "skills" / skill_name).resolve()
                for skill_name in payload["skills"]
            )

            if not prompt_path.is_file():
                raise ValueError(
                    f"{metadata_path}: referenced system prompt does not exist: {prompt_path}"
                )
            if not preset_path.is_file():
                raise ValueError(
                    f"{metadata_path}: referenced preset does not exist: {preset_path}"
                )
            if not auth_path.is_dir():
                raise ValueError(
                    f"{metadata_path}: referenced auth bundle does not exist: {auth_path}"
                )
            for skill_name, skill_path in zip(payload["skills"], skill_paths, strict=True):
                if not skill_path.is_dir():
                    raise ValueError(
                        f"{metadata_path}: referenced skill `{skill_name}` does not exist: {skill_path}"
                    )

            auth_profile = self.ensure_auth_profile_from_source(
                tool=payload["tool"],
                display_name=payload["credential_name"],
                source_path=auth_path,
            )
            self.store_specialist_from_sources(
                name=payload["name"],
                preset_name=preset_path.stem,
                tool=payload["tool"],
                provider=payload["provider"],
                auth_profile=auth_profile,
                role_name=payload["role_name"],
                setup_name=_load_legacy_preset_setup_name(preset_path),
                prompt_path=prompt_path,
                skill_paths=skill_paths,
                setup_path=(
                    self.m_projection_root
                    / "tools"
                    / payload["tool"]
                    / "setups"
                    / _load_legacy_preset_setup_name(preset_path)
                ),
                launch_mapping=_load_preset_top_level_mapping(preset_path, "launch"),
                mailbox_mapping=_load_preset_top_level_mapping(preset_path, "mailbox"),
                extra_mapping=_load_preset_top_level_mapping(preset_path, "extra"),
            )

    def list_auth_profiles(self, *, tool: str | None = None) -> list[AuthProfileCatalogEntry]:
        """Return persisted auth profiles, optionally filtered by tool."""

        self.initialize()
        with self._connect() as connection:
            if tool is None:
                rows = connection.execute(
                    """
                    SELECT
                        auth_profiles.id,
                        auth_profiles.tool,
                        auth_profiles.display_name,
                        auth_profiles.bundle_ref,
                        content_refs.content_kind,
                        content_refs.storage_kind,
                        content_refs.relative_path
                    FROM auth_profiles
                    INNER JOIN content_refs ON content_refs.id = auth_profiles.content_ref_id
                    ORDER BY auth_profiles.tool, auth_profiles.display_name
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        auth_profiles.id,
                        auth_profiles.tool,
                        auth_profiles.display_name,
                        auth_profiles.bundle_ref,
                        content_refs.content_kind,
                        content_refs.storage_kind,
                        content_refs.relative_path
                    FROM auth_profiles
                    INNER JOIN content_refs ON content_refs.id = auth_profiles.content_ref_id
                    WHERE auth_profiles.tool = ?
                    ORDER BY auth_profiles.display_name
                    """,
                    (tool,),
                ).fetchall()
        return [self._auth_profile_from_row(row) for row in rows]

    def load_auth_profile(self, *, tool: str, name: str) -> AuthProfileCatalogEntry:
        """Load one auth profile by tool and display name."""

        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    auth_profiles.id,
                    auth_profiles.tool,
                    auth_profiles.display_name,
                    auth_profiles.bundle_ref,
                    content_refs.content_kind,
                    content_refs.storage_kind,
                    content_refs.relative_path
                FROM auth_profiles
                INNER JOIN content_refs ON content_refs.id = auth_profiles.content_ref_id
                WHERE auth_profiles.tool = ? AND auth_profiles.display_name = ?
                LIMIT 1
                """,
                (tool, name),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(
                f"Auth profile `{tool}/{name}` was not found: {self.m_catalog_path}"
            )
        return self._auth_profile_from_row(row)

    def load_auth_profile_by_id(self, auth_profile_id: int) -> AuthProfileCatalogEntry:
        """Load one auth profile by its catalog id."""

        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    auth_profiles.id,
                    auth_profiles.tool,
                    auth_profiles.display_name,
                    auth_profiles.bundle_ref,
                    content_refs.content_kind,
                    content_refs.storage_kind,
                    content_refs.relative_path
                FROM auth_profiles
                INNER JOIN content_refs ON content_refs.id = auth_profiles.content_ref_id
                WHERE auth_profiles.id = ?
                LIMIT 1
                """,
                (auth_profile_id,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(
                f"Auth profile id `{auth_profile_id}` was not found: {self.m_catalog_path}"
            )
        return self._auth_profile_from_row(row)

    def create_auth_profile_from_source(
        self,
        *,
        tool: str,
        display_name: str,
        source_path: Path,
    ) -> AuthProfileCatalogEntry:
        """Create one new auth profile from a file-backed auth tree source."""

        return self._store_auth_profile_from_source(
            tool=tool,
            display_name=display_name,
            source_path=source_path,
            operation="add",
        )

    def update_auth_profile_from_source(
        self,
        *,
        tool: str,
        display_name: str,
        source_path: Path,
    ) -> AuthProfileCatalogEntry:
        """Update one existing auth profile from a file-backed auth tree source."""

        return self._store_auth_profile_from_source(
            tool=tool,
            display_name=display_name,
            source_path=source_path,
            operation="set",
        )

    def ensure_auth_profile_from_source(
        self,
        *,
        tool: str,
        display_name: str,
        source_path: Path,
    ) -> AuthProfileCatalogEntry:
        """Create or update one auth profile from a file-backed auth tree source."""

        return self._store_auth_profile_from_source(
            tool=tool,
            display_name=display_name,
            source_path=source_path,
            operation="upsert",
        )

    def rename_auth_profile(
        self,
        *,
        tool: str,
        name: str,
        new_name: str,
    ) -> AuthProfileCatalogEntry:
        """Rename one auth profile display name without changing stable identity."""

        resolved_name = _require_catalog_name(name, field_name="name")
        resolved_new_name = _require_catalog_name(new_name, field_name="new_name")
        if resolved_name == resolved_new_name:
            return self.load_auth_profile(tool=tool, name=resolved_name)

        self.ensure_legacy_import()
        with self._connect() as connection:
            row = self._find_auth_profile_row(
                connection=connection,
                tool=tool,
                display_name=resolved_name,
            )
            if row is None:
                raise FileNotFoundError(
                    f"Auth profile `{tool}/{resolved_name}` was not found: {self.m_catalog_path}"
                )
            try:
                connection.execute(
                    """
                    UPDATE auth_profiles
                    SET display_name = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (resolved_new_name, _utcnow_iso(), int(row["id"])),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Auth profile `{tool}/{resolved_new_name}` already exists in "
                    f"{self.m_catalog_path}"
                ) from exc
        return self.load_auth_profile(tool=tool, name=resolved_new_name)

    def remove_auth_profile(self, *, tool: str, name: str) -> AuthProfileCatalogEntry:
        """Remove one existing auth profile and its managed auth content."""

        profile = self.load_auth_profile(tool=tool, name=name)
        content_path = profile.content_ref.resolve_under_content_root(self.m_content_root)
        projection_path = (
            self.m_projection_root / "tools" / profile.tool / "auth" / profile.bundle_ref
        ).resolve()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, content_ref_id
                FROM auth_profiles
                WHERE tool = ? AND display_name = ?
                LIMIT 1
                """,
                (tool, profile.display_name),
            ).fetchone()
            if row is None:
                raise FileNotFoundError(
                    f"Auth profile `{tool}/{profile.display_name}` was not found: "
                    f"{self.m_catalog_path}"
                )
            try:
                connection.execute(
                    "DELETE FROM auth_profiles WHERE id = ?",
                    (int(row["id"]),),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Auth profile `{tool}/{profile.display_name}` is still referenced and "
                    "cannot be removed."
                ) from exc
            connection.execute(
                "DELETE FROM content_refs WHERE id = ?",
                (int(row["content_ref_id"]),),
            )
        if content_path.is_dir():
            shutil.rmtree(content_path)
        if projection_path.is_dir():
            shutil.rmtree(projection_path)
        return profile

    def specialist_exists(self, name: str) -> bool:
        """Return whether one specialist already exists in the catalog."""

        self.ensure_legacy_import()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM specialists WHERE name = ? LIMIT 1",
                (name,),
            ).fetchone()
        return row is not None

    def list_specialists(self) -> list[SpecialistCatalogEntry]:
        """Return every persisted specialist definition."""

        self.ensure_legacy_import()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    specialists.name,
                    presets.name AS preset_name,
                    specialists.tool,
                    specialists.provider,
                    auth_profiles.id AS auth_profile_id,
                    auth_profiles.display_name AS credential_name,
                    auth_profiles.bundle_ref AS auth_bundle_ref,
                    roles.name AS role_name,
                    setup_profiles.name AS setup_name,
                    prompt_refs.content_kind AS prompt_kind,
                    prompt_refs.storage_kind AS prompt_storage_kind,
                    prompt_refs.relative_path AS prompt_relative_path,
                    auth_refs.content_kind AS auth_kind,
                    auth_refs.storage_kind AS auth_storage_kind,
                    auth_refs.relative_path AS auth_relative_path,
                    presets.launch_payload,
                    presets.mailbox_payload,
                    presets.extra_payload
                FROM specialists
                INNER JOIN roles ON roles.id = specialists.role_id
                INNER JOIN presets ON presets.id = specialists.preset_id
                INNER JOIN setup_profiles ON setup_profiles.id = presets.setup_profile_id
                INNER JOIN content_refs AS prompt_refs
                    ON prompt_refs.id = roles.prompt_content_ref_id
                INNER JOIN auth_profiles ON auth_profiles.id = presets.auth_profile_id
                INNER JOIN content_refs AS auth_refs
                    ON auth_refs.id = auth_profiles.content_ref_id
                ORDER BY specialists.name
                """
            ).fetchall()
            return [self._entry_from_row(connection, row) for row in rows]

    def load_specialist(self, name: str) -> SpecialistCatalogEntry:
        """Load one specialist from the catalog."""

        self.ensure_legacy_import()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    specialists.name,
                    presets.name AS preset_name,
                    specialists.tool,
                    specialists.provider,
                    auth_profiles.id AS auth_profile_id,
                    auth_profiles.display_name AS credential_name,
                    auth_profiles.bundle_ref AS auth_bundle_ref,
                    roles.name AS role_name,
                    setup_profiles.name AS setup_name,
                    prompt_refs.content_kind AS prompt_kind,
                    prompt_refs.storage_kind AS prompt_storage_kind,
                    prompt_refs.relative_path AS prompt_relative_path,
                    auth_refs.content_kind AS auth_kind,
                    auth_refs.storage_kind AS auth_storage_kind,
                    auth_refs.relative_path AS auth_relative_path,
                    presets.launch_payload,
                    presets.mailbox_payload,
                    presets.extra_payload
                FROM specialists
                INNER JOIN roles ON roles.id = specialists.role_id
                INNER JOIN presets ON presets.id = specialists.preset_id
                INNER JOIN setup_profiles ON setup_profiles.id = presets.setup_profile_id
                INNER JOIN content_refs AS prompt_refs
                    ON prompt_refs.id = roles.prompt_content_ref_id
                INNER JOIN auth_profiles ON auth_profiles.id = presets.auth_profile_id
                INNER JOIN content_refs AS auth_refs
                    ON auth_refs.id = auth_profiles.content_ref_id
                WHERE specialists.name = ?
                LIMIT 1
                """,
                (name,),
            ).fetchone()
            if row is None:
                raise FileNotFoundError(f"Specialist `{name}` was not found: {self.m_catalog_path}")
            return self._entry_from_row(connection, row)

    def store_specialist_from_sources(
        self,
        *,
        name: str,
        preset_name: str,
        tool: str,
        provider: str,
        auth_profile: AuthProfileCatalogEntry,
        role_name: str,
        setup_name: str,
        prompt_path: Path,
        skill_paths: tuple[Path, ...],
        setup_path: Path | None = None,
        launch_mapping: dict[str, Any] | None,
        mailbox_mapping: dict[str, Any] | None,
        extra_mapping: dict[str, Any] | None,
    ) -> SpecialistCatalogEntry:
        """Snapshot one specialist from generated or imported file-backed sources."""

        self.initialize()
        prompt_ref = self._snapshot_file(
            source_path=prompt_path,
            content_kind=_CONTENT_KIND_PROMPT,
            relative_path=f"prompts/{role_name}.md",
        )
        skill_refs = tuple(
            self._snapshot_tree(
                source_path=skill_path,
                content_kind=_CONTENT_KIND_SKILL,
                relative_path=f"skills/{skill_path.name}",
            )
            for skill_path in skill_paths
        )
        setup_profile_id = self._ensure_setup_profile(
            tool=tool,
            name=setup_name,
            setup_path=setup_path,
        )

        with self._connect() as connection:
            existing_specialist_row = connection.execute(
                "SELECT role_id, preset_id FROM specialists WHERE name = ? LIMIT 1",
                (name,),
            ).fetchone()
            prompt_ref_id = self._upsert_content_ref(connection, prompt_ref)
            self._upsert_content_ref(connection, auth_profile.content_ref)
            role_id = self._upsert_role(
                connection=connection,
                role_name=role_name,
                prompt_ref_id=prompt_ref_id,
            )
            preset_id = self._upsert_preset(
                connection=connection,
                preset_name=preset_name,
                role_id=role_id,
                tool=tool,
                setup_profile_id=setup_profile_id,
                auth_profile_id=auth_profile.id,
                launch_mapping=launch_mapping,
                mailbox_mapping=mailbox_mapping,
                extra_mapping=extra_mapping,
            )
            self._replace_preset_skills(
                connection=connection,
                preset_id=preset_id,
                skill_refs=skill_refs,
            )
            timestamp = _utcnow_iso()
            connection.execute(
                """
                INSERT INTO specialists (
                    name,
                    tool,
                    provider,
                    role_id,
                    preset_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    tool = excluded.tool,
                    provider = excluded.provider,
                    role_id = excluded.role_id,
                    preset_id = excluded.preset_id,
                    updated_at = excluded.updated_at
                """,
                (
                    name,
                    tool,
                    provider,
                    role_id,
                    preset_id,
                    timestamp,
                    timestamp,
                ),
            )
            if existing_specialist_row is not None:
                previous_preset_id = int(existing_specialist_row["preset_id"])
                previous_role_id = int(existing_specialist_row["role_id"])
                if previous_preset_id != preset_id:
                    remaining_preset_refs = connection.execute(
                        "SELECT COUNT(*) FROM specialists WHERE preset_id = ?",
                        (previous_preset_id,),
                    ).fetchone()
                    if remaining_preset_refs is not None and int(remaining_preset_refs[0]) == 0:
                        connection.execute(
                            "DELETE FROM preset_skill_packages WHERE preset_id = ?",
                            (previous_preset_id,),
                        )
                        connection.execute(
                            "DELETE FROM presets WHERE id = ?",
                            (previous_preset_id,),
                        )
                if previous_role_id != role_id:
                    remaining_role_refs = connection.execute(
                        "SELECT COUNT(*) FROM specialists WHERE role_id = ?",
                        (previous_role_id,),
                    ).fetchone()
                    if remaining_role_refs is not None and int(remaining_role_refs[0]) == 0:
                        connection.execute("DELETE FROM roles WHERE id = ?", (previous_role_id,))
        return self.load_specialist(name)

    def remove_specialist(self, name: str) -> Path:
        """Delete one specialist definition from the catalog."""

        specialist = self.load_specialist(name)
        delete_preset_projection = False
        delete_role_projection = False
        with self._connect() as connection:
            specialist_row = connection.execute(
                "SELECT role_id, preset_id FROM specialists WHERE name = ?",
                (name,),
            ).fetchone()
            if specialist_row is None:
                raise FileNotFoundError(f"Specialist `{name}` was not found: {self.m_catalog_path}")
            role_id = int(specialist_row["role_id"])
            preset_id = int(specialist_row["preset_id"])
            connection.execute("DELETE FROM specialists WHERE name = ?", (name,))
            remaining_preset_refs = connection.execute(
                "SELECT COUNT(*) FROM specialists WHERE preset_id = ?",
                (preset_id,),
            ).fetchone()
            delete_preset_projection = (
                remaining_preset_refs is not None and int(remaining_preset_refs[0]) == 0
            )
            if delete_preset_projection:
                connection.execute(
                    "DELETE FROM preset_skill_packages WHERE preset_id = ?", (preset_id,)
                )
                connection.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
            remaining_role_refs = connection.execute(
                "SELECT COUNT(*) FROM specialists WHERE role_id = ?",
                (role_id,),
            ).fetchone()
            delete_role_projection = (
                remaining_role_refs is not None and int(remaining_role_refs[0]) == 0
            )
            if delete_role_projection:
                connection.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        if delete_preset_projection:
            (self.m_projection_root / "presets" / f"{specialist.preset_name}.yaml").unlink(
                missing_ok=True
            )
        role_root = self.m_projection_root / "roles" / specialist.role_name
        if delete_role_projection and role_root.is_dir():
            shutil.rmtree(role_root)
        metadata_path = (self.m_legacy_specialists_root / f"{name}.toml").resolve()
        if metadata_path.exists():
            metadata_path.unlink()
        return self.m_catalog_path

    def list_launch_profiles(self) -> list[LaunchProfileCatalogEntry]:
        """Return every persisted launch-profile definition."""

        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    launch_profiles.name,
                    launch_profiles.profile_lane,
                    launch_profiles.source_kind,
                    launch_profiles.source_name,
                    launch_profiles.managed_agent_name,
                    launch_profiles.managed_agent_id,
                    launch_profiles.workdir,
                    launch_profiles.auth_profile_id,
                    auth_profiles.display_name AS auth_name,
                    auth_profiles.bundle_ref AS auth_bundle_ref,
                    launch_profiles.model_name,
                    launch_profiles.reasoning_level,
                    launch_profiles.operator_prompt_mode,
                    launch_profiles.env_payload,
                    launch_profiles.mailbox_payload,
                    launch_profiles.posture_payload,
                    launch_profiles.managed_header_policy,
                    launch_profiles.managed_header_section_policy,
                    launch_profiles.prompt_overlay_mode,
                    launch_profiles.memo_seed_source_kind,
                    prompt_refs.content_kind AS prompt_kind,
                    prompt_refs.storage_kind AS prompt_storage_kind,
                    prompt_refs.relative_path AS prompt_relative_path,
                    memo_refs.content_kind AS memo_kind,
                    memo_refs.storage_kind AS memo_storage_kind,
                    memo_refs.relative_path AS memo_relative_path
                FROM launch_profiles
                LEFT JOIN auth_profiles ON auth_profiles.id = launch_profiles.auth_profile_id
                LEFT JOIN content_refs AS prompt_refs
                    ON prompt_refs.id = launch_profiles.prompt_overlay_content_ref_id
                LEFT JOIN content_refs AS memo_refs
                    ON memo_refs.id = launch_profiles.memo_seed_content_ref_id
                ORDER BY launch_profiles.name
                """
            ).fetchall()
        return [self._launch_profile_from_row(row) for row in rows]

    def load_launch_profile(self, name: str) -> LaunchProfileCatalogEntry:
        """Load one persisted launch profile from the catalog."""

        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    launch_profiles.name,
                    launch_profiles.profile_lane,
                    launch_profiles.source_kind,
                    launch_profiles.source_name,
                    launch_profiles.managed_agent_name,
                    launch_profiles.managed_agent_id,
                    launch_profiles.workdir,
                    launch_profiles.auth_profile_id,
                    auth_profiles.display_name AS auth_name,
                    auth_profiles.bundle_ref AS auth_bundle_ref,
                    launch_profiles.model_name,
                    launch_profiles.reasoning_level,
                    launch_profiles.operator_prompt_mode,
                    launch_profiles.env_payload,
                    launch_profiles.mailbox_payload,
                    launch_profiles.posture_payload,
                    launch_profiles.managed_header_policy,
                    launch_profiles.managed_header_section_policy,
                    launch_profiles.prompt_overlay_mode,
                    launch_profiles.memo_seed_source_kind,
                    prompt_refs.content_kind AS prompt_kind,
                    prompt_refs.storage_kind AS prompt_storage_kind,
                    prompt_refs.relative_path AS prompt_relative_path,
                    memo_refs.content_kind AS memo_kind,
                    memo_refs.storage_kind AS memo_storage_kind,
                    memo_refs.relative_path AS memo_relative_path
                FROM launch_profiles
                LEFT JOIN auth_profiles ON auth_profiles.id = launch_profiles.auth_profile_id
                LEFT JOIN content_refs AS prompt_refs
                    ON prompt_refs.id = launch_profiles.prompt_overlay_content_ref_id
                LEFT JOIN content_refs AS memo_refs
                    ON memo_refs.id = launch_profiles.memo_seed_content_ref_id
                WHERE launch_profiles.name = ?
                LIMIT 1
                """,
                (name,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"Launch profile `{name}` was not found: {self.m_catalog_path}")
        return self._launch_profile_from_row(row)

    def store_launch_profile(
        self,
        *,
        name: str,
        profile_lane: str,
        source_kind: str,
        source_name: str,
        managed_agent_name: str | None,
        managed_agent_id: str | None,
        workdir: str | None,
        auth_tool: str | None,
        auth_name: str | None,
        operator_prompt_mode: str | None,
        env_mapping: dict[str, str] | None,
        mailbox_mapping: dict[str, Any] | None,
        posture_mapping: dict[str, Any] | None,
        managed_header_policy: ManagedHeaderPolicy | None = None,
        managed_header_section_policy: dict[Any, Any] | None = None,
        prompt_overlay_mode: str | None,
        prompt_overlay_text: str | None,
        memo_seed_source_kind: str | None = None,
        memo_seed_text: str | None = None,
        memo_seed_source_path: Path | None = None,
        model_name: str | None = None,
        reasoning_level: int | None = None,
    ) -> LaunchProfileCatalogEntry:
        """Insert or update one shared launch-profile record."""

        self.initialize()
        if profile_lane not in _PROFILE_LANE_VALUES:
            raise ValueError(
                f"Unsupported launch-profile lane {profile_lane!r}; expected one of "
                f"{sorted(_PROFILE_LANE_VALUES)}."
            )
        if source_kind not in _SOURCE_KIND_VALUES:
            raise ValueError(
                f"Unsupported launch-profile source kind {source_kind!r}; expected one of "
                f"{sorted(_SOURCE_KIND_VALUES)}."
            )
        if prompt_overlay_mode is None and prompt_overlay_text is not None:
            raise ValueError("Prompt-overlay text requires a prompt-overlay mode.")
        if prompt_overlay_mode is not None and prompt_overlay_mode not in {"append", "replace"}:
            raise ValueError("Prompt-overlay mode must be `append` or `replace` when provided.")
        if prompt_overlay_mode is not None and prompt_overlay_text is None:
            raise ValueError("Prompt-overlay mode requires prompt-overlay text.")
        if (
            memo_seed_source_kind is not None
            and memo_seed_source_kind not in _MEMO_SEED_SOURCE_KIND_VALUES
        ):
            raise ValueError(
                f"Memo-seed source kind must be one of {sorted(_MEMO_SEED_SOURCE_KIND_VALUES)}."
            )
        if memo_seed_source_kind is None:
            if memo_seed_text is not None or memo_seed_source_path is not None:
                raise ValueError("Memo-seed content requires a memo-seed source kind.")
        else:
            if (memo_seed_text is None) == (memo_seed_source_path is None):
                raise ValueError(
                    "Provide exactly one memo-seed text payload or memo-seed source path."
                )
        resolved_model_name = (
            model_name.strip() if model_name is not None and model_name.strip() else None
        )
        resolved_reasoning_level = (
            parse_reasoning_level(reasoning_level, source="launch_profiles.reasoning_level")
            if reasoning_level is not None
            else None
        )
        resolved_managed_header_policy = normalize_managed_header_policy(
            managed_header_policy,
            source="launch_profiles.managed_header_policy",
        )
        resolved_managed_header_section_policy = normalize_managed_header_section_policy_mapping(
            managed_header_section_policy,
            source="launch_profiles.managed_header_section_policy",
        )

        prompt_overlay_ref: ManagedContentRef | None = None
        if prompt_overlay_text is not None:
            prompt_overlay_ref = self._snapshot_text(
                text=prompt_overlay_text,
                content_kind=_CONTENT_KIND_PROMPT,
                relative_path=f"prompts/launch-profiles/{name}.md",
            )
        memo_seed_ref: ManagedContentRef | None = None
        if memo_seed_source_kind is not None:
            memo_seed_ref = self._snapshot_launch_profile_memo_seed(
                name=name,
                source_kind=memo_seed_source_kind,
                memo_seed_text=memo_seed_text,
                memo_seed_source_path=memo_seed_source_path,
            )

        with self._connect() as connection:
            auth_profile_id = (
                self._auth_profile_id_for_name(
                    connection=connection,
                    tool=auth_tool,
                    display_name=auth_name,
                )
                if auth_name is not None
                else None
            )
            prompt_overlay_ref_id = (
                self._upsert_content_ref(connection, prompt_overlay_ref)
                if prompt_overlay_ref is not None
                else None
            )
            memo_seed_ref_id = (
                self._upsert_content_ref(connection, memo_seed_ref)
                if memo_seed_ref is not None
                else None
            )
            timestamp = _utcnow_iso()
            connection.execute(
                """
                INSERT INTO launch_profiles (
                    name,
                    profile_lane,
                    source_kind,
                    source_name,
                    managed_agent_name,
                    managed_agent_id,
                    workdir,
                    auth_profile_id,
                    persist_dir,
                    persist_disabled,
                    model_name,
                    reasoning_level,
                    operator_prompt_mode,
                    env_payload,
                    mailbox_payload,
                    posture_payload,
                    managed_header_policy,
                    managed_header_section_policy,
                    prompt_overlay_mode,
                    prompt_overlay_content_ref_id,
                    memo_seed_source_kind,
                    memo_seed_content_ref_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    profile_lane = excluded.profile_lane,
                    source_kind = excluded.source_kind,
                    source_name = excluded.source_name,
                    managed_agent_name = excluded.managed_agent_name,
                    managed_agent_id = excluded.managed_agent_id,
                    workdir = excluded.workdir,
                    auth_profile_id = excluded.auth_profile_id,
                    persist_dir = NULL,
                    persist_disabled = 0,
                    model_name = excluded.model_name,
                    reasoning_level = excluded.reasoning_level,
                    operator_prompt_mode = excluded.operator_prompt_mode,
                    env_payload = excluded.env_payload,
                    mailbox_payload = excluded.mailbox_payload,
                    posture_payload = excluded.posture_payload,
                    managed_header_policy = excluded.managed_header_policy,
                    managed_header_section_policy = excluded.managed_header_section_policy,
                    prompt_overlay_mode = excluded.prompt_overlay_mode,
                    prompt_overlay_content_ref_id = excluded.prompt_overlay_content_ref_id,
                    memo_seed_source_kind = excluded.memo_seed_source_kind,
                    memo_seed_content_ref_id = excluded.memo_seed_content_ref_id,
                    updated_at = excluded.updated_at
                """,
                (
                    name,
                    profile_lane,
                    source_kind,
                    source_name,
                    managed_agent_name,
                    managed_agent_id,
                    workdir,
                    auth_profile_id,
                    None,
                    0,
                    resolved_model_name,
                    resolved_reasoning_level,
                    operator_prompt_mode,
                    json.dumps(env_mapping or {}, sort_keys=True),
                    json.dumps(mailbox_mapping or {}, sort_keys=True),
                    json.dumps(posture_mapping or {}, sort_keys=True),
                    resolved_managed_header_policy,
                    json.dumps(resolved_managed_header_section_policy, sort_keys=True),
                    prompt_overlay_mode,
                    prompt_overlay_ref_id,
                    memo_seed_source_kind,
                    memo_seed_ref_id,
                    timestamp,
                    timestamp,
                ),
            )
        return self.load_launch_profile(name)

    def remove_launch_profile(self, name: str) -> Path:
        """Delete one launch-profile definition from the catalog."""

        profile = self.load_launch_profile(name)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM launch_profiles WHERE name = ? LIMIT 1",
                (name,),
            ).fetchone()
            if row is None:
                raise FileNotFoundError(
                    f"Launch profile `{name}` was not found: {self.m_catalog_path}"
                )
            connection.execute("DELETE FROM launch_profiles WHERE name = ?", (name,))
        (self.m_projection_root / "launch-profiles" / f"{profile.name}.yaml").unlink(
            missing_ok=True
        )
        return self.m_catalog_path

    def materialize_projection(self) -> Path:
        """Materialize the non-authoritative agent tree projection from the catalog."""

        self.ensure_legacy_import()
        self._ensure_projection_starter_tree()
        entries = self.list_specialists()
        launch_profiles = self.list_launch_profiles()
        auth_profiles = self.list_auth_profiles()
        for entry in entries:
            prompt_source = entry.prompt_ref.resolve_under_content_root(self.m_content_root)
            prompt_target = (
                self.m_projection_root / "roles" / entry.role_name / "system-prompt.md"
            ).resolve()
            prompt_target.parent.mkdir(parents=True, exist_ok=True)
            prompt_target.write_text(prompt_source.read_text(encoding="utf-8"), encoding="utf-8")

            preset_target = (
                self.m_projection_root / "presets" / f"{entry.preset_name}.yaml"
            ).resolve()
            preset_target.parent.mkdir(parents=True, exist_ok=True)
            preset_target.write_text(
                _render_preset_yaml(entry=entry),
                encoding="utf-8",
            )

            for skill_name, skill_ref in zip(entry.skills, entry.skill_refs, strict=True):
                skill_source = skill_ref.resolve_under_content_root(self.m_content_root)
                skill_target = (self.m_projection_root / "skills" / skill_name).resolve()
                _replace_tree(source=skill_source, destination=skill_target)
        desired_auth_dirs: dict[str, set[str]] = {}
        for auth_profile in auth_profiles:
            auth_source = auth_profile.content_ref.resolve_under_content_root(self.m_content_root)
            auth_target = (
                self.m_projection_root
                / "tools"
                / auth_profile.tool
                / "auth"
                / auth_profile.bundle_ref
            ).resolve()
            _replace_tree(source=auth_source, destination=auth_target)
            desired_auth_dirs.setdefault(auth_profile.tool, set()).add(auth_profile.bundle_ref)
        tools_root = (self.m_projection_root / "tools").resolve()
        if tools_root.is_dir():
            for tool_dir in sorted(path for path in tools_root.iterdir() if path.is_dir()):
                auth_root = (tool_dir / "auth").resolve()
                auth_root.mkdir(parents=True, exist_ok=True)
                desired = desired_auth_dirs.get(tool_dir.name, set())
                for child in sorted(auth_root.iterdir(), key=lambda path: path.name):
                    if child.name in desired:
                        continue
                    if child.is_dir() and not child.is_symlink():
                        shutil.rmtree(child)
                    else:
                        child.unlink(missing_ok=True)
        launch_profiles_root = (self.m_projection_root / "launch-profiles").resolve()
        launch_profiles_root.mkdir(parents=True, exist_ok=True)
        for launch_profile in launch_profiles:
            profile_target = (launch_profiles_root / f"{launch_profile.name}.yaml").resolve()
            profile_target.write_text(
                _render_launch_profile_yaml(
                    entry=launch_profile,
                    content_root=self.m_content_root,
                ),
                encoding="utf-8",
            )
        return self.m_projection_root

    def validate_integrity(self) -> CatalogIntegrityReport:
        """Validate managed content references and detect orphaned content rows."""

        self.ensure_legacy_import()
        missing_content: list[str] = []
        orphaned_content: list[str] = []
        with self._connect() as connection:
            content_rows = connection.execute(
                "SELECT id, relative_path, storage_kind FROM content_refs ORDER BY relative_path"
            ).fetchall()
            referenced_rows = {
                int(row[0])
                for row in connection.execute(
                    """
                    SELECT prompt_content_ref_id FROM roles
                    UNION
                    SELECT content_ref_id FROM auth_profiles
                    UNION
                    SELECT content_ref_id FROM skill_packages
                    UNION
                    SELECT content_ref_id FROM setup_profiles
                    UNION
                    SELECT prompt_overlay_content_ref_id FROM launch_profiles
                    UNION
                    SELECT memo_seed_content_ref_id FROM launch_profiles
                    """
                ).fetchall()
                if row[0] is not None
            }
        for row in content_rows:
            relative_path = str(row["relative_path"])
            candidate = (self.m_content_root / relative_path).resolve()
            storage_kind = str(row["storage_kind"])
            if storage_kind == _STORAGE_KIND_FILE and not candidate.is_file():
                missing_content.append(relative_path)
            if storage_kind == _STORAGE_KIND_TREE and not candidate.is_dir():
                missing_content.append(relative_path)
            if int(row["id"]) not in referenced_rows:
                orphaned_content.append(relative_path)
        return CatalogIntegrityReport(
            missing_content=tuple(missing_content),
            orphaned_content=tuple(orphaned_content),
        )

    def _ensure_content_roots(self) -> None:
        """Create the managed content roots."""

        for directory in (
            self.m_content_root,
            self.m_content_root / "prompts",
            self.m_content_root / "auth",
            self.m_content_root / "skills",
            self.m_content_root / "setups",
            self.m_content_root / "memo-seeds",
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open one SQLite connection with foreign keys enabled."""

        connection = sqlite3.connect(self.m_catalog_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _specialist_count(self) -> int:
        """Return the number of persisted specialists."""

        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM specialists").fetchone()
            assert row is not None
            return int(row[0])

    def _ensure_catalog_metadata(self, connection: sqlite3.Connection) -> None:
        """Seed the schema metadata rows."""

        connection.execute(
            """
            INSERT INTO catalog_meta(key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(CATALOG_SCHEMA_VERSION),),
        )
        connection.execute(
            """
            INSERT INTO catalog_meta(key, value)
            VALUES ('storage_model', 'hybrid_sqlite_catalog')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        )

    def _seed_setup_profiles(self, connection: sqlite3.Connection) -> None:
        """Seed starter setup profiles into managed content and catalog rows."""

        starter_root = resources.files(_STARTER_ASSET_PACKAGE) / _STARTER_ASSET_ROOT
        tools_root = starter_root / "tools"
        if not tools_root.is_dir():
            raise ValueError("Packaged Houmao project starter assets are missing.")
        for tool_dir in sorted(
            (item for item in tools_root.iterdir() if item.is_dir()), key=lambda item: item.name
        ):
            setups_root = tool_dir / "setups"
            if not setups_root.is_dir():
                continue
            for setup_dir in sorted(
                (item for item in setups_root.iterdir() if item.is_dir()),
                key=lambda item: item.name,
            ):
                relative_path = f"setups/{tool_dir.name}/{setup_dir.name}"
                destination = (self.m_content_root / relative_path).resolve()
                _copy_traversable_tree(source=setup_dir, destination=destination)
                content_ref = ManagedContentRef(
                    content_kind=_CONTENT_KIND_SETUP,
                    storage_kind=_STORAGE_KIND_TREE,
                    relative_path=relative_path,
                )
                content_ref_id = self._upsert_content_ref(connection, content_ref)
                connection.execute(
                    """
                    INSERT INTO setup_profiles(tool, name, content_ref_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(tool, name) DO UPDATE SET content_ref_id = excluded.content_ref_id
                    """,
                    (tool_dir.name, setup_dir.name, content_ref_id),
                )

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        """Apply in-place catalog migrations required by the current schema."""

        current_version = _catalog_schema_version(connection)
        if current_version == CATALOG_SCHEMA_VERSION:
            return
        required_columns = (
            ("auth_profiles", "display_name"),
            ("auth_profiles", "bundle_ref"),
            ("launch_profiles", "auth_profile_id"),
        )
        if current_version in {0, 7, 8} and all(
            _table_has_column(connection, table_name=table_name, column_name=column_name)
            for table_name, column_name in required_columns
        ):
            if not _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="managed_header_section_policy",
            ):
                connection.execute(
                    """
                    ALTER TABLE launch_profiles
                    ADD COLUMN managed_header_section_policy TEXT NOT NULL DEFAULT '{}'
                    """
                )
            if _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="memory_dir",
            ) and not _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="persist_dir",
            ):
                connection.execute(
                    "ALTER TABLE launch_profiles RENAME COLUMN memory_dir TO persist_dir"
                )
            if _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="memory_disabled",
            ) and not _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="persist_disabled",
            ):
                connection.execute(
                    "ALTER TABLE launch_profiles RENAME COLUMN memory_disabled TO persist_disabled"
                )
            current_version = 9
        if current_version == 9:
            if not _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="memo_seed_source_kind",
            ):
                memo_seed_source_kind_check = ", ".join(
                    f"'{value}'" for value in _MEMO_SEED_SOURCE_KIND_VALUES
                )
                connection.execute(
                    f"""
                    ALTER TABLE launch_profiles
                    ADD COLUMN memo_seed_source_kind TEXT
                    CHECK(memo_seed_source_kind IN ({memo_seed_source_kind_check}))
                    """
                )
            if not _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="memo_seed_content_ref_id",
            ):
                connection.execute(
                    """
                    ALTER TABLE launch_profiles
                    ADD COLUMN memo_seed_content_ref_id INTEGER
                    REFERENCES content_refs(id) ON DELETE SET NULL
                    """
                )
            current_version = 10
        if current_version == 10:
            if _table_has_column(
                connection,
                table_name="launch_profiles",
                column_name="memo_seed_policy",
            ):
                _drop_launch_profile_memo_seed_policy(connection)
            return
        raise ValueError(
            "Unsupported project catalog schema. Reinitialize the project overlay to adopt the "
            "current catalog format."
        )

    def _ensure_setup_profile(self, *, tool: str, name: str, setup_path: Path | None = None) -> int:
        """Return the existing setup profile id for one tool/setup pair."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM setup_profiles WHERE tool = ? AND name = ? LIMIT 1",
                (tool, name),
            ).fetchone()
            if row is not None:
                return int(row["id"])
            if setup_path is None:
                raise ValueError(f"Unknown setup profile `{tool}/{name}` in {self.m_catalog_path}")
            content_ref = self._snapshot_tree(
                source_path=setup_path,
                content_kind=_CONTENT_KIND_SETUP,
                relative_path=f"setups/{tool}/{name}",
            )
            content_ref_id = self._upsert_content_ref(connection, content_ref)
            connection.execute(
                """
                INSERT INTO setup_profiles(tool, name, content_ref_id)
                VALUES (?, ?, ?)
                ON CONFLICT(tool, name) DO UPDATE SET content_ref_id = excluded.content_ref_id
                """,
                (tool, name, content_ref_id),
            )
            inserted = connection.execute(
                "SELECT id FROM setup_profiles WHERE tool = ? AND name = ? LIMIT 1",
                (tool, name),
            ).fetchone()
            assert inserted is not None
            return int(inserted["id"])

    def _snapshot_file(
        self,
        *,
        source_path: Path,
        content_kind: str,
        relative_path: str,
    ) -> ManagedContentRef:
        """Copy one file payload into managed content storage."""

        resolved_source = source_path.resolve()
        if not resolved_source.is_file():
            raise ValueError(f"Managed content file does not exist: {resolved_source}")
        destination = (self.m_content_root / relative_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved_source, destination)
        return ManagedContentRef(
            content_kind=content_kind,
            storage_kind=_STORAGE_KIND_FILE,
            relative_path=relative_path,
        )

    def _snapshot_text(
        self,
        *,
        text: str,
        content_kind: str,
        relative_path: str,
    ) -> ManagedContentRef:
        """Write one managed text payload into content storage."""

        destination = (self.m_content_root / relative_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text.rstrip() + "\n" if text.strip() else "", encoding="utf-8")
        return ManagedContentRef(
            content_kind=content_kind,
            storage_kind=_STORAGE_KIND_FILE,
            relative_path=relative_path,
        )

    def _snapshot_tree(
        self,
        *,
        source_path: Path,
        content_kind: str,
        relative_path: str,
    ) -> ManagedContentRef:
        """Copy one tree payload into managed content storage."""

        resolved_source = source_path.resolve()
        if not resolved_source.is_dir():
            raise ValueError(f"Managed content tree does not exist: {resolved_source}")
        destination = (self.m_content_root / relative_path).resolve()
        _replace_tree(source=resolved_source, destination=destination)
        return ManagedContentRef(
            content_kind=content_kind,
            storage_kind=_STORAGE_KIND_TREE,
            relative_path=relative_path,
        )

    def _snapshot_launch_profile_memo_seed(
        self,
        *,
        name: str,
        source_kind: str,
        memo_seed_text: str | None,
        memo_seed_source_path: Path | None,
    ) -> ManagedContentRef:
        """Snapshot one launch-profile memo seed into managed content storage."""

        relative_path = f"memo-seeds/launch-profiles/{name}/seed"
        if source_kind == _MEMO_SEED_SOURCE_KIND_MEMO:
            if memo_seed_text is not None:
                return self._snapshot_memo_seed_text(
                    text=memo_seed_text,
                    relative_path=relative_path,
                )
            assert memo_seed_source_path is not None
            return self._snapshot_memo_seed_file(
                source_path=memo_seed_source_path,
                relative_path=relative_path,
            )
        if source_kind == _MEMO_SEED_SOURCE_KIND_TREE:
            if memo_seed_text is not None:
                raise ValueError("Directory memo seeds do not accept inline memo text.")
            if memo_seed_source_path is None:
                raise ValueError("Directory memo seeds require a source path.")
            return self._snapshot_memo_seed_tree(
                source_path=memo_seed_source_path,
                relative_path=relative_path,
            )
        raise ValueError(
            f"Unsupported memo-seed source kind {source_kind!r}; expected one of "
            f"{sorted(_MEMO_SEED_SOURCE_KIND_VALUES)}."
        )

    def _snapshot_memo_seed_text(self, *, text: str, relative_path: str) -> ManagedContentRef:
        """Write one inline memo-seed text payload into managed content storage."""

        _validate_memo_seed_text_content(text, source="inline memo seed")
        destination = (self.m_content_root / relative_path).resolve()
        _replace_path_with_text(destination=destination, text=text)
        return ManagedContentRef(
            content_kind=_CONTENT_KIND_MEMO_SEED,
            storage_kind=_STORAGE_KIND_FILE,
            relative_path=relative_path,
        )

    def _snapshot_memo_seed_file(
        self, *, source_path: Path, relative_path: str
    ) -> ManagedContentRef:
        """Copy one memo-seed Markdown file into managed content storage."""

        text = _read_memo_seed_text_file(source_path, source=str(source_path))
        destination = (self.m_content_root / relative_path).resolve()
        _replace_path_with_text(destination=destination, text=text)
        return ManagedContentRef(
            content_kind=_CONTENT_KIND_MEMO_SEED,
            storage_kind=_STORAGE_KIND_FILE,
            relative_path=relative_path,
        )

    def _snapshot_memo_seed_tree(
        self, *, source_path: Path, relative_path: str
    ) -> ManagedContentRef:
        """Copy one validated memo-seed directory into managed content storage."""

        _validate_memo_seed_tree(source_path)
        destination = (self.m_content_root / relative_path).resolve()
        _replace_tree(source=source_path.resolve(), destination=destination)
        return ManagedContentRef(
            content_kind=_CONTENT_KIND_MEMO_SEED,
            storage_kind=_STORAGE_KIND_TREE,
            relative_path=relative_path,
        )

    def _store_auth_profile_from_source(
        self,
        *,
        tool: str,
        display_name: str,
        source_path: Path,
        operation: str,
    ) -> AuthProfileCatalogEntry:
        """Create or update one auth profile from a file-backed source tree."""

        resolved_display_name = _require_catalog_name(display_name, field_name="display_name")
        if operation not in {"add", "set", "upsert"}:
            raise ValueError(f"Unsupported auth-profile store operation: {operation!r}")

        self.initialize()
        with self._connect() as connection:
            existing_row = self._find_auth_profile_row(
                connection=connection,
                tool=tool,
                display_name=resolved_display_name,
            )
            if operation == "add" and existing_row is not None:
                raise ValueError(
                    f"Auth profile `{tool}/{resolved_display_name}` already exists in "
                    f"{self.m_catalog_path}"
                )
            if operation == "set" and existing_row is None:
                raise FileNotFoundError(
                    f"Auth profile `{tool}/{resolved_display_name}` was not found: "
                    f"{self.m_catalog_path}"
                )
            bundle_ref = (
                str(existing_row["bundle_ref"]) if existing_row is not None else uuid4().hex
            )
            content_ref = self._snapshot_tree(
                source_path=source_path,
                content_kind=_CONTENT_KIND_AUTH,
                relative_path=f"auth/{tool}/{bundle_ref}",
            )
            content_ref_id = self._upsert_content_ref(connection, content_ref)
            if existing_row is None:
                self._insert_auth_profile(
                    connection=connection,
                    tool=tool,
                    display_name=resolved_display_name,
                    bundle_ref=bundle_ref,
                    content_ref_id=content_ref_id,
                )
            else:
                self._update_auth_profile_content(
                    connection=connection,
                    auth_profile_id=int(existing_row["id"]),
                    display_name=resolved_display_name,
                    bundle_ref=bundle_ref,
                    content_ref_id=content_ref_id,
                )
        return self.load_auth_profile(tool=tool, name=resolved_display_name)

    def _find_auth_profile_row(
        self,
        *,
        connection: sqlite3.Connection,
        tool: str,
        display_name: str,
    ) -> sqlite3.Row | None:
        """Return one auth-profile row for a `(tool, display_name)` lookup when present."""

        row = connection.execute(
            """
            SELECT id, bundle_ref, content_ref_id
            FROM auth_profiles
            WHERE tool = ? AND display_name = ?
            LIMIT 1
            """,
            (tool, display_name),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    def _upsert_content_ref(
        self,
        connection: sqlite3.Connection,
        content_ref: ManagedContentRef,
    ) -> int:
        """Insert or update one content ref row and return its id."""

        relative_path = content_ref.relative_path
        resolved_path = (self.m_content_root / relative_path).resolve()
        digest = _compute_path_digest(resolved_path, storage_kind=content_ref.storage_kind)
        connection.execute(
            """
            INSERT INTO content_refs(content_kind, storage_kind, relative_path, sha256, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(relative_path) DO UPDATE SET
                content_kind = excluded.content_kind,
                storage_kind = excluded.storage_kind,
                sha256 = excluded.sha256
            """,
            (
                content_ref.content_kind,
                content_ref.storage_kind,
                relative_path,
                digest,
                _utcnow_iso(),
            ),
        )
        row = connection.execute(
            "SELECT id FROM content_refs WHERE relative_path = ? LIMIT 1",
            (relative_path,),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def _upsert_role(
        self,
        *,
        connection: sqlite3.Connection,
        role_name: str,
        prompt_ref_id: int,
    ) -> int:
        """Insert or update one role row and return its id."""

        connection.execute(
            """
            INSERT INTO roles(name, prompt_content_ref_id)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET prompt_content_ref_id = excluded.prompt_content_ref_id
            """,
            (role_name, prompt_ref_id),
        )
        row = connection.execute(
            "SELECT id FROM roles WHERE name = ? LIMIT 1",
            (role_name,),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def _insert_auth_profile(
        self,
        *,
        connection: sqlite3.Connection,
        tool: str,
        display_name: str,
        bundle_ref: str,
        content_ref_id: int,
    ) -> int:
        """Insert one new auth-profile row and return its id."""

        timestamp = _utcnow_iso()
        connection.execute(
            """
            INSERT INTO auth_profiles(
                tool,
                display_name,
                bundle_ref,
                content_ref_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tool, display_name, bundle_ref, content_ref_id, timestamp, timestamp),
        )
        row = self._find_auth_profile_row(
            connection=connection,
            tool=tool,
            display_name=display_name,
        )
        assert row is not None
        return int(row["id"])

    def _update_auth_profile_content(
        self,
        *,
        connection: sqlite3.Connection,
        auth_profile_id: int,
        display_name: str,
        bundle_ref: str,
        content_ref_id: int,
    ) -> None:
        """Update one existing auth-profile row without changing its stable identity."""

        try:
            connection.execute(
                """
                UPDATE auth_profiles
                SET display_name = ?,
                    bundle_ref = ?,
                    content_ref_id = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (display_name, bundle_ref, content_ref_id, _utcnow_iso(), auth_profile_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Auth profile display name `{display_name}` is already in use."
            ) from exc

    def _auth_profile_id_for_name(
        self,
        *,
        connection: sqlite3.Connection,
        tool: str | None,
        display_name: str | None,
    ) -> int:
        """Return one auth-profile id for a `(tool, display_name)` lookup."""

        if display_name is None:
            raise ValueError("Auth profile display name is required.")
        if tool is None:
            raise ValueError("Auth profile tool is required when resolving auth by display name.")
        row = self._find_auth_profile_row(
            connection=connection,
            tool=tool,
            display_name=_require_catalog_name(display_name, field_name="display_name"),
        )
        if row is None:
            raise FileNotFoundError(f"Auth profile `{tool}/{display_name}` was not found.")
        return int(row["id"])

    def _upsert_preset(
        self,
        *,
        connection: sqlite3.Connection,
        preset_name: str,
        role_id: int,
        tool: str,
        setup_profile_id: int,
        auth_profile_id: int,
        launch_mapping: dict[str, Any] | None,
        mailbox_mapping: dict[str, Any] | None,
        extra_mapping: dict[str, Any] | None,
    ) -> int:
        """Insert or update one preset row and return its id."""

        connection.execute(
            """
            INSERT INTO presets(
                name,
                role_id,
                tool,
                setup_profile_id,
                auth_profile_id,
                launch_payload,
                mailbox_payload,
                extra_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(role_id, tool, setup_profile_id) DO UPDATE SET
                name = excluded.name,
                auth_profile_id = excluded.auth_profile_id,
                launch_payload = excluded.launch_payload,
                mailbox_payload = excluded.mailbox_payload,
                extra_payload = excluded.extra_payload
            """,
            (
                preset_name,
                role_id,
                tool,
                setup_profile_id,
                auth_profile_id,
                json.dumps(launch_mapping or {}, sort_keys=True),
                json.dumps(mailbox_mapping or {}, sort_keys=True),
                json.dumps(extra_mapping or {}, sort_keys=True),
            ),
        )
        row = connection.execute(
            """
            SELECT id FROM presets
            WHERE role_id = ? AND tool = ? AND setup_profile_id = ?
            LIMIT 1
            """,
            (role_id, tool, setup_profile_id),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def _replace_preset_skills(
        self,
        *,
        connection: sqlite3.Connection,
        preset_id: int,
        skill_refs: tuple[ManagedContentRef, ...],
    ) -> None:
        """Replace the ordered skill package bindings for one preset."""

        connection.execute("DELETE FROM preset_skill_packages WHERE preset_id = ?", (preset_id,))
        for ordinal, skill_ref in enumerate(skill_refs):
            skill_ref_id = self._upsert_content_ref(connection, skill_ref)
            skill_name = Path(skill_ref.relative_path).name
            connection.execute(
                """
                INSERT INTO skill_packages(name, content_ref_id)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET content_ref_id = excluded.content_ref_id
                """,
                (skill_name, skill_ref_id),
            )
            skill_row = connection.execute(
                "SELECT id FROM skill_packages WHERE name = ? LIMIT 1",
                (skill_name,),
            ).fetchone()
            assert skill_row is not None
            connection.execute(
                """
                INSERT INTO preset_skill_packages(preset_id, skill_package_id, ordinal)
                VALUES (?, ?, ?)
                """,
                (preset_id, int(skill_row["id"]), ordinal),
            )

    def _auth_profile_from_row(self, row: sqlite3.Row) -> AuthProfileCatalogEntry:
        """Build one structured auth-profile entry from a joined row."""

        return AuthProfileCatalogEntry(
            id=int(row["id"]),
            tool=str(row["tool"]),
            display_name=str(row["display_name"]),
            bundle_ref=str(row["bundle_ref"]),
            content_ref=ManagedContentRef(
                content_kind=str(row["content_kind"]),
                storage_kind=str(row["storage_kind"]),
                relative_path=str(row["relative_path"]),
            ),
            metadata_path=self.m_catalog_path,
        )

    def _entry_from_row(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> SpecialistCatalogEntry:
        """Build one structured specialist entry from a joined row."""

        specialist_name = str(row["name"])
        skill_rows = connection.execute(
            """
            SELECT
                skill_packages.name AS skill_name,
                content_refs.content_kind,
                content_refs.storage_kind,
                content_refs.relative_path
            FROM specialists
            INNER JOIN presets ON presets.id = specialists.preset_id
            INNER JOIN preset_skill_packages
                ON preset_skill_packages.preset_id = presets.id
            INNER JOIN skill_packages
                ON skill_packages.id = preset_skill_packages.skill_package_id
            INNER JOIN content_refs
                ON content_refs.id = skill_packages.content_ref_id
            WHERE specialists.name = ?
            ORDER BY preset_skill_packages.ordinal
            """,
            (specialist_name,),
        ).fetchall()
        skill_names = tuple(str(skill_row["skill_name"]) for skill_row in skill_rows)
        skill_refs = tuple(
            ManagedContentRef(
                content_kind=str(skill_row["content_kind"]),
                storage_kind=str(skill_row["storage_kind"]),
                relative_path=str(skill_row["relative_path"]),
            )
            for skill_row in skill_rows
        )
        launch_payload = _load_json_mapping(str(row["launch_payload"]))
        mailbox_payload = _load_json_mapping(str(row["mailbox_payload"]))
        extra_payload = _load_json_mapping(str(row["extra_payload"]))
        return SpecialistCatalogEntry(
            name=specialist_name,
            preset_name=str(row["preset_name"]),
            tool=str(row["tool"]),
            provider=str(row["provider"]),
            auth_profile_id=int(row["auth_profile_id"]),
            credential_name=str(row["credential_name"]),
            auth_bundle_ref=str(row["auth_bundle_ref"]),
            role_name=str(row["role_name"]),
            setup_name=str(row["setup_name"]),
            skills=skill_names,
            prompt_ref=ManagedContentRef(
                content_kind=str(row["prompt_kind"]),
                storage_kind=str(row["prompt_storage_kind"]),
                relative_path=str(row["prompt_relative_path"]),
            ),
            auth_ref=ManagedContentRef(
                content_kind=str(row["auth_kind"]),
                storage_kind=str(row["auth_storage_kind"]),
                relative_path=str(row["auth_relative_path"]),
            ),
            skill_refs=skill_refs,
            launch_payload=launch_payload,
            mailbox_payload=mailbox_payload if mailbox_payload else None,
            extra_payload=extra_payload,
            metadata_path=self.m_catalog_path,
        )

    def _launch_profile_from_row(self, row: sqlite3.Row) -> LaunchProfileCatalogEntry:
        """Build one structured launch-profile entry from a joined row."""

        prompt_overlay_ref: ManagedContentRef | None = None
        prompt_relative_path = row["prompt_relative_path"]
        if prompt_relative_path is not None:
            prompt_overlay_ref = ManagedContentRef(
                content_kind=str(row["prompt_kind"]),
                storage_kind=str(row["prompt_storage_kind"]),
                relative_path=str(prompt_relative_path),
            )
        memo_seed: LaunchProfileMemoSeed | None = None
        memo_relative_path = row["memo_relative_path"]
        if memo_relative_path is not None:
            memo_source_kind = row["memo_seed_source_kind"]
            if memo_source_kind is None:
                raise ValueError(
                    f"Launch profile `{row['name']}` stores incomplete memo-seed metadata."
                )
            memo_seed = LaunchProfileMemoSeed(
                source_kind=cast(Literal["memo", "tree"], str(memo_source_kind)),
                content_ref=ManagedContentRef(
                    content_kind=str(row["memo_kind"]),
                    storage_kind=str(row["memo_storage_kind"]),
                    relative_path=str(memo_relative_path),
                ),
            )
        env_payload = _load_json_mapping(str(row["env_payload"]))
        mailbox_payload = _load_json_mapping(str(row["mailbox_payload"]))
        posture_payload = _load_json_mapping(str(row["posture_payload"]))
        managed_header_section_policy = normalize_managed_header_section_policy_mapping(
            _load_json_mapping(str(row["managed_header_section_policy"]))
            if row["managed_header_section_policy"] is not None
            else {},
            source=f"launch profile `{row['name']}` managed_header_section_policy",
        )
        return LaunchProfileCatalogEntry(
            name=str(row["name"]),
            profile_lane=str(row["profile_lane"]),
            source_kind=str(row["source_kind"]),
            source_name=str(row["source_name"]),
            managed_agent_name=(
                str(row["managed_agent_name"]) if row["managed_agent_name"] is not None else None
            ),
            managed_agent_id=str(row["managed_agent_id"])
            if row["managed_agent_id"] is not None
            else None,
            workdir=str(row["workdir"]) if row["workdir"] is not None else None,
            auth_name=str(row["auth_name"]) if row["auth_name"] is not None else None,
            model_name=str(row["model_name"]) if row["model_name"] is not None else None,
            reasoning_level=(
                parse_reasoning_level(
                    int(row["reasoning_level"]),
                    source=f"launch profile `{row['name']}` reasoning_level",
                )
                if row["reasoning_level"] is not None
                else None
            ),
            auth_profile_id=(
                int(row["auth_profile_id"]) if row["auth_profile_id"] is not None else None
            ),
            auth_bundle_ref=(
                str(row["auth_bundle_ref"]) if row["auth_bundle_ref"] is not None else None
            ),
            operator_prompt_mode=(
                str(row["operator_prompt_mode"])
                if row["operator_prompt_mode"] is not None
                else None
            ),
            env_payload={str(key): str(value) for key, value in env_payload.items()},
            mailbox_payload=mailbox_payload if mailbox_payload else None,
            posture_payload=posture_payload,
            managed_header_policy=normalize_managed_header_policy(
                str(row["managed_header_policy"])
                if row["managed_header_policy"] is not None
                else None,
                source=f"launch profile `{row['name']}` managed_header_policy",
            ),
            prompt_overlay_mode=(
                str(row["prompt_overlay_mode"]) if row["prompt_overlay_mode"] is not None else None
            ),
            prompt_overlay_ref=prompt_overlay_ref,
            memo_seed=memo_seed,
            managed_header_section_policy=managed_header_section_policy,
            metadata_path=self.m_catalog_path,
        )

    def _ensure_projection_starter_tree(self) -> None:
        """Bootstrap the compatibility projection tree from packaged starter assets."""

        starter_root = resources.files(_STARTER_ASSET_PACKAGE) / _STARTER_ASSET_ROOT
        if not starter_root.is_dir():
            raise ValueError("Packaged Houmao project starter assets are missing.")
        _copy_traversable_tree(source=starter_root, destination=self.m_projection_root)
        for tool_dir in sorted(
            path for path in (self.m_projection_root / "tools").iterdir() if path.is_dir()
        ):
            (tool_dir / "auth").mkdir(parents=True, exist_ok=True)


def _table_schema_sql() -> str:
    """Return the SQLite table schema."""

    content_kind_check = ", ".join(f"'{value}'" for value in _CONTENT_KIND_VALUES)
    storage_kind_check = ", ".join(f"'{value}'" for value in _STORAGE_KIND_VALUES)
    memo_seed_source_kind_check = ", ".join(f"'{value}'" for value in _MEMO_SEED_SOURCE_KIND_VALUES)
    return f"""
    CREATE TABLE IF NOT EXISTS catalog_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS content_refs (
        id INTEGER PRIMARY KEY,
        content_kind TEXT NOT NULL CHECK(content_kind IN ({content_kind_check})),
        storage_kind TEXT NOT NULL CHECK(storage_kind IN ({storage_kind_check})),
        relative_path TEXT NOT NULL UNIQUE,
        sha256 TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        prompt_content_ref_id INTEGER NOT NULL REFERENCES content_refs(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS setup_profiles (
        id INTEGER PRIMARY KEY,
        tool TEXT NOT NULL,
        name TEXT NOT NULL,
        content_ref_id INTEGER NOT NULL REFERENCES content_refs(id) ON DELETE RESTRICT,
        UNIQUE(tool, name)
    );

    CREATE TABLE IF NOT EXISTS auth_profiles (
        id INTEGER PRIMARY KEY,
        tool TEXT NOT NULL,
        display_name TEXT NOT NULL,
        bundle_ref TEXT NOT NULL UNIQUE,
        content_ref_id INTEGER NOT NULL REFERENCES content_refs(id) ON DELETE RESTRICT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(tool, display_name)
    );

    CREATE TABLE IF NOT EXISTS skill_packages (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        content_ref_id INTEGER NOT NULL REFERENCES content_refs(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS mailbox_policies (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        transport TEXT NOT NULL DEFAULT 'none',
        policy_payload TEXT NOT NULL DEFAULT '{{}}'
    );

    CREATE TABLE IF NOT EXISTS presets (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
        tool TEXT NOT NULL,
        setup_profile_id INTEGER NOT NULL REFERENCES setup_profiles(id) ON DELETE RESTRICT,
        auth_profile_id INTEGER NOT NULL REFERENCES auth_profiles(id) ON DELETE RESTRICT,
        mailbox_policy_id INTEGER REFERENCES mailbox_policies(id) ON DELETE SET NULL,
        launch_payload TEXT NOT NULL DEFAULT '{{}}',
        mailbox_payload TEXT NOT NULL DEFAULT '{{}}',
        extra_payload TEXT NOT NULL DEFAULT '{{}}',
        UNIQUE(role_id, tool, setup_profile_id)
    );

    CREATE TABLE IF NOT EXISTS preset_skill_packages (
        preset_id INTEGER NOT NULL REFERENCES presets(id) ON DELETE CASCADE,
        skill_package_id INTEGER NOT NULL REFERENCES skill_packages(id) ON DELETE RESTRICT,
        ordinal INTEGER NOT NULL,
        PRIMARY KEY(preset_id, skill_package_id)
    );

    CREATE TABLE IF NOT EXISTS specialists (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        tool TEXT NOT NULL,
        provider TEXT NOT NULL,
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
        preset_id INTEGER NOT NULL REFERENCES presets(id) ON DELETE RESTRICT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS launch_profiles (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        profile_lane TEXT NOT NULL CHECK(profile_lane IN ('easy_profile', 'launch_profile')),
        source_kind TEXT NOT NULL CHECK(source_kind IN ('specialist', 'recipe')),
        source_name TEXT NOT NULL,
        managed_agent_name TEXT,
        managed_agent_id TEXT,
        workdir TEXT,
        auth_profile_id INTEGER REFERENCES auth_profiles(id) ON DELETE RESTRICT,
        persist_dir TEXT,
        persist_disabled INTEGER NOT NULL DEFAULT 0,
        model_name TEXT,
        reasoning_level INTEGER,
        operator_prompt_mode TEXT,
        env_payload TEXT NOT NULL DEFAULT '{{}}',
        mailbox_payload TEXT NOT NULL DEFAULT '{{}}',
        posture_payload TEXT NOT NULL DEFAULT '{{}}',
        managed_header_policy TEXT,
        managed_header_section_policy TEXT NOT NULL DEFAULT '{{}}',
        prompt_overlay_mode TEXT,
        prompt_overlay_content_ref_id INTEGER REFERENCES content_refs(id) ON DELETE SET NULL,
        memo_seed_source_kind TEXT CHECK(
            memo_seed_source_kind IN ({memo_seed_source_kind_check})
        ),
        memo_seed_content_ref_id INTEGER REFERENCES content_refs(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """


def _view_sql() -> str:
    """Return the SQLite view schema."""

    return """
    DROP VIEW IF EXISTS v_content_refs;
    DROP VIEW IF EXISTS v_roles;
    DROP VIEW IF EXISTS v_presets;
    DROP VIEW IF EXISTS v_specialists;
    DROP VIEW IF EXISTS v_launch_profiles;

    CREATE VIEW v_content_refs AS
    SELECT
        id,
        content_kind,
        storage_kind,
        relative_path,
        sha256,
        created_at
    FROM content_refs;

    CREATE VIEW v_roles AS
    SELECT
        roles.name AS role_name,
        content_refs.relative_path AS prompt_relative_path
    FROM roles
    INNER JOIN content_refs ON content_refs.id = roles.prompt_content_ref_id;

    CREATE VIEW v_presets AS
    SELECT
        presets.name AS preset_name,
        roles.name AS role_name,
        presets.tool AS tool,
        setup_profiles.name AS setup_name,
        auth_profiles.display_name AS auth_name,
        presets.launch_payload AS launch_payload,
        presets.mailbox_payload AS mailbox_payload,
        presets.extra_payload AS extra_payload
    FROM presets
    INNER JOIN roles ON roles.id = presets.role_id
    INNER JOIN setup_profiles ON setup_profiles.id = presets.setup_profile_id
    INNER JOIN auth_profiles ON auth_profiles.id = presets.auth_profile_id;

    CREATE VIEW v_specialists AS
    SELECT
        specialists.name AS specialist_name,
        presets.name AS preset_name,
        specialists.tool AS tool,
        specialists.provider AS provider,
        auth_profiles.display_name AS credential_name,
        roles.name AS role_name,
        setup_profiles.name AS setup_name,
        prompt_refs.relative_path AS prompt_relative_path,
        auth_refs.relative_path AS auth_relative_path
    FROM specialists
    INNER JOIN roles ON roles.id = specialists.role_id
    INNER JOIN presets ON presets.id = specialists.preset_id
    INNER JOIN setup_profiles ON setup_profiles.id = presets.setup_profile_id
    INNER JOIN content_refs AS prompt_refs ON prompt_refs.id = roles.prompt_content_ref_id
    INNER JOIN auth_profiles ON auth_profiles.id = presets.auth_profile_id
    INNER JOIN content_refs AS auth_refs ON auth_refs.id = auth_profiles.content_ref_id;

    CREATE VIEW v_launch_profiles AS
    SELECT
        launch_profiles.name AS launch_profile_name,
        launch_profiles.profile_lane AS profile_lane,
        launch_profiles.source_kind AS source_kind,
        launch_profiles.source_name AS source_name,
        launch_profiles.managed_agent_name AS managed_agent_name,
        launch_profiles.managed_agent_id AS managed_agent_id,
        launch_profiles.workdir AS workdir,
        auth_profiles.display_name AS auth_name,
        launch_profiles.model_name AS model_name,
        launch_profiles.reasoning_level AS reasoning_level,
        launch_profiles.operator_prompt_mode AS operator_prompt_mode,
        launch_profiles.env_payload AS env_payload,
        launch_profiles.mailbox_payload AS mailbox_payload,
        launch_profiles.posture_payload AS posture_payload,
        launch_profiles.managed_header_policy AS managed_header_policy,
        launch_profiles.managed_header_section_policy AS managed_header_section_policy,
        launch_profiles.prompt_overlay_mode AS prompt_overlay_mode,
        prompt_refs.relative_path AS prompt_overlay_relative_path,
        launch_profiles.memo_seed_source_kind AS memo_seed_source_kind,
        memo_refs.relative_path AS memo_seed_relative_path
    FROM launch_profiles
    LEFT JOIN auth_profiles ON auth_profiles.id = launch_profiles.auth_profile_id
    LEFT JOIN content_refs AS prompt_refs
        ON prompt_refs.id = launch_profiles.prompt_overlay_content_ref_id
    LEFT JOIN content_refs AS memo_refs
        ON memo_refs.id = launch_profiles.memo_seed_content_ref_id;
    """


def _catalog_schema_version(connection: sqlite3.Connection) -> int:
    """Return the stored catalog schema version when present."""

    row = connection.execute(
        """
        SELECT value
        FROM catalog_meta
        WHERE key = 'schema_version'
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 0


def _table_has_column(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    column_name: str,
) -> bool:
    """Return whether one SQLite table currently exposes the requested column."""

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row[1]) == column_name for row in rows)


def _drop_launch_profile_memo_seed_policy(connection: sqlite3.Connection) -> None:
    """Rebuild launch_profiles without the removed memo-seed policy column."""

    columns = (
        "id",
        "name",
        "profile_lane",
        "source_kind",
        "source_name",
        "managed_agent_name",
        "managed_agent_id",
        "workdir",
        "auth_profile_id",
        "persist_dir",
        "persist_disabled",
        "model_name",
        "reasoning_level",
        "operator_prompt_mode",
        "env_payload",
        "mailbox_payload",
        "posture_payload",
        "managed_header_policy",
        "managed_header_section_policy",
        "prompt_overlay_mode",
        "prompt_overlay_content_ref_id",
        "memo_seed_source_kind",
        "memo_seed_content_ref_id",
        "created_at",
        "updated_at",
    )
    column_list = ", ".join(columns)
    connection.execute("DROP VIEW IF EXISTS v_launch_profiles")
    connection.execute("ALTER TABLE launch_profiles RENAME TO launch_profiles_with_policy")
    connection.executescript(_table_schema_sql())
    connection.execute(
        f"""
        INSERT INTO launch_profiles ({column_list})
        SELECT {column_list}
        FROM launch_profiles_with_policy
        """
    )
    connection.execute("DROP TABLE launch_profiles_with_policy")


def _load_legacy_specialist_payload(path: Path) -> dict[str, Any]:
    """Load one legacy easy specialist TOML payload."""

    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a top-level TOML table.")
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise ValueError(f"{path}: only schema_version=1 is supported.")
    required_keys = (
        "name",
        "tool",
        "provider",
        "credential_name",
        "role_name",
        "system_prompt_path",
        "preset_path",
        "auth_path",
    )
    result: dict[str, Any] = {}
    for key in required_keys:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{path}: missing string `{key}`.")
        result[key] = value.strip()
    raw_skills = payload.get("skills")
    if raw_skills is None:
        result["skills"] = []
    elif isinstance(raw_skills, list) and all(
        isinstance(item, str) and item.strip() for item in raw_skills
    ):
        result["skills"] = [item.strip() for item in raw_skills]
    else:
        raise ValueError(f"{path}: expected `skills` to be a list of non-empty strings.")
    return result


def _load_legacy_preset_setup_name(path: Path) -> str:
    """Return the `setup` field from one legacy YAML-like preset file."""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("setup:"):
            continue
        value = line.partition(":")[2].strip().strip('"').strip("'")
        if value:
            return value
    raise ValueError(f"{path}: missing `setup` field.")


def _render_preset_yaml(entry: SpecialistCatalogEntry) -> str:
    """Render one compatibility projection preset file."""

    payload: dict[str, Any] = {
        "role": entry.role_name,
        "tool": entry.tool,
        "setup": entry.setup_name,
        "skills": list(entry.skills),
    }
    payload["auth"] = entry.credential_name
    if entry.launch_payload:
        payload["launch"] = entry.launch_payload
    if entry.mailbox_payload:
        payload["mailbox"] = entry.mailbox_payload
    if entry.extra_payload:
        payload["extra"] = entry.extra_payload
    try:
        import yaml

        rendered = yaml.safe_dump(payload, sort_keys=False)
    except Exception:
        rendered = json.dumps(payload, indent=2, sort_keys=False)
    return rendered


def _render_launch_profile_yaml(
    *,
    entry: LaunchProfileCatalogEntry,
    content_root: Path,
) -> str:
    """Render one compatibility projection launch-profile file."""

    payload: dict[str, Any] = {
        "profile_lane": entry.profile_lane,
        "source": {
            "kind": entry.source_kind,
            "name": entry.source_name,
        },
        "defaults": {},
    }
    defaults = cast(dict[str, Any], payload["defaults"])
    if entry.managed_agent_name is not None:
        defaults["agent_name"] = entry.managed_agent_name
    if entry.managed_agent_id is not None:
        defaults["agent_id"] = entry.managed_agent_id
    if entry.workdir is not None:
        defaults["workdir"] = entry.workdir
    if entry.auth_name is not None:
        defaults["auth"] = entry.auth_name
    if entry.model_name is not None or entry.reasoning_level is not None:
        defaults["model"] = {}
        if entry.model_name is not None:
            defaults["model"]["name"] = entry.model_name
        if entry.reasoning_level is not None:
            defaults["model"]["reasoning"] = {"level": entry.reasoning_level}
    if entry.operator_prompt_mode is not None:
        defaults["prompt_mode"] = entry.operator_prompt_mode
    if entry.env_payload:
        defaults["env"] = dict(entry.env_payload)
    if entry.mailbox_payload:
        defaults["mailbox"] = entry.mailbox_payload
    if entry.posture_payload:
        defaults["posture"] = entry.posture_payload
    if entry.managed_header_policy is not None:
        defaults["managed_header"] = entry.managed_header_policy
    if entry.managed_header_section_policy:
        defaults["managed_header_sections"] = dict(
            sorted(entry.managed_header_section_policy.items())
        )
    if entry.prompt_overlay_mode is not None and entry.prompt_overlay_ref is not None:
        overlay_path = entry.prompt_overlay_ref.resolve_under_content_root(content_root)
        defaults["prompt_overlay"] = {
            "mode": entry.prompt_overlay_mode,
            "text": overlay_path.read_text(encoding="utf-8").rstrip(),
        }
    if entry.memo_seed is not None:
        memo_seed_path = entry.memo_seed.content_ref.resolve_under_content_root(content_root)
        defaults["memo_seed"] = {
            "source_kind": entry.memo_seed.source_kind,
            "content_ref": {
                "content_kind": entry.memo_seed.content_ref.content_kind,
                "storage_kind": entry.memo_seed.content_ref.storage_kind,
                "relative_path": entry.memo_seed.content_ref.relative_path,
                "path": str(memo_seed_path),
            },
        }
    try:
        import yaml

        rendered = yaml.safe_dump(payload, sort_keys=False)
    except Exception:
        rendered = json.dumps(payload, indent=2, sort_keys=False)
    return rendered


def _copy_traversable_tree(*, source: Traversable, destination: Path) -> None:
    """Copy one package-resource tree without overwriting existing files."""

    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for child in sorted(source.iterdir(), key=lambda item: item.name):
            _copy_traversable_tree(source=child, destination=destination / child.name)
        return
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def _replace_tree(*, source: Path, destination: Path) -> None:
    """Replace one directory tree atomically enough for local overlay use."""

    if destination.exists():
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)


def _replace_path_with_text(*, destination: Path, text: str) -> None:
    """Replace one file-or-tree destination with UTF-8 text content."""

    if destination.exists():
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def _utcnow_iso() -> str:
    """Return one stable UTC timestamp for catalog writes."""

    return datetime.now(tz=UTC).isoformat()


def _compute_path_digest(path: Path, *, storage_kind: str) -> str:
    """Compute a stable digest for one file or tree content payload."""

    digest = hashlib.sha256()
    if storage_kind == _STORAGE_KIND_FILE:
        digest.update(path.read_bytes())
        return digest.hexdigest()
    for child in sorted(item for item in path.rglob("*")):
        relative = child.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative)
        if child.is_file():
            digest.update(child.read_bytes())
    return digest.hexdigest()


def _load_json_mapping(raw_value: str) -> dict[str, Any]:
    """Load one JSON mapping payload from the database."""

    try:
        loaded = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed catalog JSON payload: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError("Catalog JSON payload must be a mapping.")
    return cast(dict[str, Any], loaded)


def _read_memo_seed_text_file(path: Path, *, source: str) -> str:
    """Read one memo-seed text file after UTF-8 and NUL validation."""

    resolved_path = path.resolve()
    if not resolved_path.is_file():
        raise ValueError(f"{source}: memo-seed file does not exist: {resolved_path}")
    raw_bytes = resolved_path.read_bytes()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source}: memo-seed content must be valid UTF-8 text.") from exc
    _validate_memo_seed_text_content(text, source=source)
    return text


def _validate_memo_seed_text_content(text: str, *, source: str) -> None:
    """Reject unsupported memo-seed text content."""

    if "\x00" in text:
        raise ValueError(f"{source}: memo-seed content must not contain NUL bytes.")


def _validate_memo_seed_tree(source_path: Path) -> None:
    """Validate one memo-shaped launch-profile memo-seed tree."""

    resolved_source = source_path.resolve()
    if not resolved_source.is_dir():
        raise ValueError(f"Memo-seed directory does not exist: {resolved_source}")
    entries = sorted(resolved_source.iterdir(), key=lambda item: item.name)
    if not entries:
        raise ValueError("Memo-seed directories must contain `houmao-memo.md`, `pages/`, or both.")
    supported_entries = {_MEMO_SEED_TOP_LEVEL_MEMO_FILE, _MEMO_SEED_TOP_LEVEL_PAGES_DIR}
    has_supported_entry = False
    for entry in entries:
        if entry.is_symlink():
            raise ValueError(f"Memo-seed directories must not contain symlinks: {entry}")
        if entry.name not in supported_entries:
            raise ValueError(
                "Memo-seed directories may contain only `houmao-memo.md` and `pages/` at the "
                f"top level: {entry}"
            )
        if entry.name == _MEMO_SEED_TOP_LEVEL_MEMO_FILE:
            _read_memo_seed_text_file(entry, source=str(entry))
            has_supported_entry = True
            continue
        if not entry.is_dir():
            raise ValueError(f"Memo-seed `pages/` must be a directory: {entry}")
        _validate_memo_seed_pages_tree(entry)
        has_supported_entry = True
    if not has_supported_entry:
        raise ValueError("Memo-seed directories must contain `houmao-memo.md`, `pages/`, or both.")


def _validate_memo_seed_pages_tree(pages_root: Path) -> None:
    """Validate one contained `pages/` subtree inside a memo seed."""

    resolved_pages_root = pages_root.resolve()
    for candidate in sorted(resolved_pages_root.rglob("*"), key=lambda item: item.as_posix()):
        if candidate.is_symlink():
            raise ValueError(
                "Memo-seed pages must be regular contained files or directories: "
                f"{candidate.relative_to(resolved_pages_root).as_posix()}"
            )
        if candidate.is_dir():
            continue
        if not candidate.is_file():
            raise ValueError(
                "Memo-seed pages must be regular contained files or directories: "
                f"{candidate.relative_to(resolved_pages_root).as_posix()}"
            )
        _read_memo_seed_text_file(
            candidate,
            source=f"memo-seed page `{candidate.relative_to(resolved_pages_root).as_posix()}`",
        )


def _load_preset_top_level_mapping(path: Path, key: str) -> dict[str, Any] | None:
    """Load one top-level preset mapping field when present."""

    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        payload = yaml.safe_load(text)
    except Exception:
        payload = json.loads(text)
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a top-level mapping.")
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected `{key}` to be a mapping when present.")
    return cast(dict[str, Any], value)


def _require_catalog_name(value: str, *, field_name: str) -> str:
    """Return one non-empty catalog-facing display name."""

    resolved = value.strip()
    if not resolved:
        raise ValueError(f"`{field_name}` must not be empty.")
    return resolved
