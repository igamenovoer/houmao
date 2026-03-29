"""SQLite-backed project-local configuration catalog and managed content store."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from importlib import resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path
import shutil
import sqlite3
import tomllib
from typing import TYPE_CHECKING, Any, Iterator, cast

from houmao.agents.definition_parser import parse_agent_preset

if TYPE_CHECKING:
    from houmao.project.overlay import HoumaoProjectOverlay

CATALOG_SCHEMA_VERSION = 1
PROJECT_CATALOG_FILENAME = "catalog.sqlite"
PROJECT_CONTENT_DIRNAME = "content"
_STARTER_ASSET_PACKAGE = "houmao.project.assets"
_STARTER_ASSET_ROOT = "starter_agents"

_CONTENT_KIND_PROMPT = "prompt_blob"
_CONTENT_KIND_AUTH = "auth_tree"
_CONTENT_KIND_SKILL = "skill_tree"
_CONTENT_KIND_SETUP = "setup_tree"
_CONTENT_KIND_VALUES = (
    _CONTENT_KIND_PROMPT,
    _CONTENT_KIND_AUTH,
    _CONTENT_KIND_SKILL,
    _CONTENT_KIND_SETUP,
)
_STORAGE_KIND_FILE = "file"
_STORAGE_KIND_TREE = "tree"
_STORAGE_KIND_VALUES = (_STORAGE_KIND_FILE, _STORAGE_KIND_TREE)


@dataclass(frozen=True)
class ManagedContentRef:
    """Reference one managed file-backed content payload."""

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
    tool: str
    provider: str
    credential_name: str
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

        return (
            overlay.agents_root
            / "roles"
            / self.role_name
            / "presets"
            / self.tool
            / f"{self.setup_name}.yaml"
        ).resolve()

    def resolved_auth_path(self, overlay: HoumaoProjectOverlay) -> Path:
        """Return the compatibility projection auth bundle path."""

        return (
            overlay.agents_root / "tools" / self.tool / "auth" / self.credential_name
        ).resolve()

    def resolved_skill_paths(self, overlay: HoumaoProjectOverlay) -> tuple[Path, ...]:
        """Return the compatibility projection skill paths."""

        return tuple(
            (overlay.agents_root / "skills" / skill_name).resolve() for skill_name in self.skills
        )


@dataclass(frozen=True)
class CatalogIntegrityReport:
    """Validation report for one project-local catalog."""

    missing_content: tuple[str, ...]
    orphaned_content: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether the catalog passed integrity validation."""

        return not self.missing_content


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
            connection.executescript(_schema_sql())
            self._ensure_catalog_metadata(connection)
            self._seed_setup_profiles(connection)

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
                raise ValueError(f"{metadata_path}: referenced preset does not exist: {preset_path}")
            if not auth_path.is_dir():
                raise ValueError(
                    f"{metadata_path}: referenced auth bundle does not exist: {auth_path}"
                )
            for skill_name, skill_path in zip(payload["skills"], skill_paths, strict=True):
                if not skill_path.is_dir():
                    raise ValueError(
                        f"{metadata_path}: referenced skill `{skill_name}` does not exist: {skill_path}"
                    )

            preset = parse_agent_preset(preset_path)
            self.store_specialist_from_sources(
                name=payload["name"],
                tool=payload["tool"],
                provider=payload["provider"],
                credential_name=payload["credential_name"],
                role_name=payload["role_name"],
                setup_name=preset.setup,
                prompt_path=prompt_path,
                auth_path=auth_path,
                skill_paths=skill_paths,
                setup_path=(self.m_projection_root / "tools" / preset.tool / "setups" / preset.setup),
                launch_mapping=_load_preset_top_level_mapping(preset_path, "launch"),
                mailbox_mapping=_load_preset_top_level_mapping(preset_path, "mailbox"),
                extra_mapping=_load_preset_top_level_mapping(preset_path, "extra"),
            )

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
                    specialists.tool,
                    specialists.provider,
                    specialists.credential_name,
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
                    specialists.tool,
                    specialists.provider,
                    specialists.credential_name,
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
        tool: str,
        provider: str,
        credential_name: str,
        role_name: str,
        setup_name: str,
        prompt_path: Path,
        auth_path: Path,
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
        auth_ref = self._snapshot_tree(
            source_path=auth_path,
            content_kind=_CONTENT_KIND_AUTH,
            relative_path=f"auth/{tool}/{credential_name}",
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
            prompt_ref_id = self._upsert_content_ref(connection, prompt_ref)
            auth_ref_id = self._upsert_content_ref(connection, auth_ref)
            role_id = self._upsert_role(
                connection=connection,
                role_name=role_name,
                prompt_ref_id=prompt_ref_id,
            )
            auth_profile_id = self._upsert_auth_profile(
                connection=connection,
                tool=tool,
                auth_name=credential_name,
                content_ref_id=auth_ref_id,
            )
            preset_id = self._upsert_preset(
                connection=connection,
                role_id=role_id,
                tool=tool,
                setup_profile_id=setup_profile_id,
                auth_profile_id=auth_profile_id,
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
                    credential_name,
                    role_id,
                    preset_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    tool = excluded.tool,
                    provider = excluded.provider,
                    credential_name = excluded.credential_name,
                    role_id = excluded.role_id,
                    preset_id = excluded.preset_id,
                    updated_at = excluded.updated_at
                """,
                (
                    name,
                    tool,
                    provider,
                    credential_name,
                    role_id,
                    preset_id,
                    timestamp,
                    timestamp,
                ),
            )
        return self.load_specialist(name)

    def remove_specialist(self, name: str) -> Path:
        """Delete one specialist definition from the catalog."""

        specialist = self.load_specialist(name)
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
            if remaining_preset_refs is not None and int(remaining_preset_refs[0]) == 0:
                connection.execute("DELETE FROM preset_skill_packages WHERE preset_id = ?", (preset_id,))
                connection.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
            remaining_role_refs = connection.execute(
                "SELECT COUNT(*) FROM specialists WHERE role_id = ?",
                (role_id,),
            ).fetchone()
            if remaining_role_refs is not None and int(remaining_role_refs[0]) == 0:
                connection.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        role_root = self.m_projection_root / "roles" / specialist.role_name
        if role_root.is_dir():
            shutil.rmtree(role_root)
        metadata_path = (self.m_legacy_specialists_root / f"{name}.toml").resolve()
        if metadata_path.exists():
            metadata_path.unlink()
        return self.m_catalog_path

    def materialize_projection(self) -> Path:
        """Materialize the non-authoritative agent tree projection from the catalog."""

        self.ensure_legacy_import()
        self._ensure_projection_starter_tree()
        entries = self.list_specialists()
        for entry in entries:
            prompt_source = entry.prompt_ref.resolve_under_content_root(self.m_content_root)
            prompt_target = (
                self.m_projection_root / "roles" / entry.role_name / "system-prompt.md"
            ).resolve()
            prompt_target.parent.mkdir(parents=True, exist_ok=True)
            prompt_target.write_text(prompt_source.read_text(encoding="utf-8"), encoding="utf-8")

            preset_target = (
                self.m_projection_root
                / "roles"
                / entry.role_name
                / "presets"
                / entry.tool
                / f"{entry.setup_name}.yaml"
            ).resolve()
            preset_target.parent.mkdir(parents=True, exist_ok=True)
            preset_target.write_text(
                _render_preset_yaml(entry=entry),
                encoding="utf-8",
            )

            auth_source = entry.auth_ref.resolve_under_content_root(self.m_content_root)
            auth_target = (
                self.m_projection_root / "tools" / entry.tool / "auth" / entry.credential_name
            ).resolve()
            _replace_tree(source=auth_source, destination=auth_target)

            for skill_name, skill_ref in zip(entry.skills, entry.skill_refs, strict=True):
                skill_source = skill_ref.resolve_under_content_root(self.m_content_root)
                skill_target = (self.m_projection_root / "skills" / skill_name).resolve()
                _replace_tree(source=skill_source, destination=skill_target)
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
                    """
                ).fetchall()
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
        for tool_dir in sorted((item for item in tools_root.iterdir() if item.is_dir()), key=lambda item: item.name):
            setups_root = tool_dir / "setups"
            if not setups_root.is_dir():
                continue
            for setup_dir in sorted((item for item in setups_root.iterdir() if item.is_dir()), key=lambda item: item.name):
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

    def _upsert_auth_profile(
        self,
        *,
        connection: sqlite3.Connection,
        tool: str,
        auth_name: str,
        content_ref_id: int,
    ) -> int:
        """Insert or update one auth profile row and return its id."""

        connection.execute(
            """
            INSERT INTO auth_profiles(tool, name, content_ref_id)
            VALUES (?, ?, ?)
            ON CONFLICT(tool, name) DO UPDATE SET content_ref_id = excluded.content_ref_id
            """,
            (tool, auth_name, content_ref_id),
        )
        row = connection.execute(
            "SELECT id FROM auth_profiles WHERE tool = ? AND name = ? LIMIT 1",
            (tool, auth_name),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def _upsert_preset(
        self,
        *,
        connection: sqlite3.Connection,
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
                role_id,
                tool,
                setup_profile_id,
                auth_profile_id,
                launch_payload,
                mailbox_payload,
                extra_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(role_id, tool, setup_profile_id) DO UPDATE SET
                auth_profile_id = excluded.auth_profile_id,
                launch_payload = excluded.launch_payload,
                mailbox_payload = excluded.mailbox_payload,
                extra_payload = excluded.extra_payload
            """,
            (
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
            tool=str(row["tool"]),
            provider=str(row["provider"]),
            credential_name=str(row["credential_name"]),
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


def _schema_sql() -> str:
    """Return the initial SQLite schema."""

    content_kind_check = ", ".join(f"'{value}'" for value in _CONTENT_KIND_VALUES)
    storage_kind_check = ", ".join(f"'{value}'" for value in _STORAGE_KIND_VALUES)
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
        name TEXT NOT NULL,
        content_ref_id INTEGER NOT NULL REFERENCES content_refs(id) ON DELETE RESTRICT,
        UNIQUE(tool, name)
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
        credential_name TEXT NOT NULL,
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
        preset_id INTEGER NOT NULL REFERENCES presets(id) ON DELETE RESTRICT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE VIEW IF NOT EXISTS v_content_refs AS
    SELECT
        id,
        content_kind,
        storage_kind,
        relative_path,
        sha256,
        created_at
    FROM content_refs;

    CREATE VIEW IF NOT EXISTS v_roles AS
    SELECT
        roles.name AS role_name,
        content_refs.relative_path AS prompt_relative_path
    FROM roles
    INNER JOIN content_refs ON content_refs.id = roles.prompt_content_ref_id;

    CREATE VIEW IF NOT EXISTS v_presets AS
    SELECT
        roles.name AS role_name,
        presets.tool AS tool,
        setup_profiles.name AS setup_name,
        auth_profiles.name AS auth_name,
        presets.launch_payload AS launch_payload,
        presets.mailbox_payload AS mailbox_payload,
        presets.extra_payload AS extra_payload
    FROM presets
    INNER JOIN roles ON roles.id = presets.role_id
    INNER JOIN setup_profiles ON setup_profiles.id = presets.setup_profile_id
    INNER JOIN auth_profiles ON auth_profiles.id = presets.auth_profile_id;

    CREATE VIEW IF NOT EXISTS v_specialists AS
    SELECT
        specialists.name AS specialist_name,
        specialists.tool AS tool,
        specialists.provider AS provider,
        specialists.credential_name AS credential_name,
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
    """


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


def _render_preset_yaml(entry: SpecialistCatalogEntry) -> str:
    """Render one compatibility projection preset file."""

    payload: dict[str, Any] = {"skills": list(entry.skills)}
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
