"""Typed manifest and composition support for Houmao system-skill packs."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError  # type: ignore[import-untyped]


SYSTEM_SKILLS_PACKAGE = "houmao.agents.assets.system_skills"
SYSTEM_SKILL_MANIFEST_FILENAME = "manifest.toml"
SYSTEM_SKILL_MANIFEST_SCHEMA_FILENAME = "manifest.schema.json"
LEGACY_SYSTEM_SKILL_CATALOG_FILENAME = "legacy/catalog.v1.toml"
SYSTEM_SKILL_MANIFEST_SCHEMA_VERSION = "houmao-system-skills.v3"
SYSTEM_SKILL_AUTO_PROMPT_NAME = "houmao-auto-system-prompt"
SYSTEM_SKILL_ACTOR_FRAME_HEADING = "## Actor Frame Gate"
SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME = "SKILL.md"
SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME = "SKILL-MAIN.md"
SYSTEM_SKILL_INVOCATION_NOTATION_FRONTMATTER = """skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints."""

_SYSTEM_SKILL_OBJECT_DESIGNATOR_RE = re.compile(
    r"(?:<public-entrypoint>|houmao-(?:admin|agent)-entrypoint)->houmao-shared-routines"
)

PackAudience = Literal["admin", "agent"]
PublicSkillRole = Literal["welcome", "entrypoint"]
DefaultLane = Literal["cli", "managed_launch", "managed_join"]
AutoInstallKind = Literal["managed_launch", "managed_join", "cli_default"]


class SystemSkillManifestError(RuntimeError):
    """Raised when packaged pack metadata or composed content is invalid."""


@dataclass(frozen=True)
class ProtectedRoutineDependency:
    """One logical dependency resolved inside an audience composition."""

    logical_id: str


@dataclass(frozen=True)
class SystemSkillPackRecord:
    """One atomically managed audience pack."""

    pack_id: str
    audience: PackAudience
    description: str
    public_skill_names: tuple[str, ...]
    protected_mount_ids: tuple[str, ...]
    default_lanes: tuple[DefaultLane, ...]


@dataclass(frozen=True)
class PublicSystemSkillRecord:
    """One visible welcome or executable entrypoint in a pack."""

    name: str
    pack_id: str
    role: PublicSkillRole
    source_path: str
    public_commands: tuple[str, ...]
    handoff_to: str | None = None
    welcome_delegate: str | None = None


@dataclass(frozen=True)
class ProtectedMountRecord:
    """One canonical protected bundle mounted below executable entrypoints."""

    mount_id: str
    source_path: str
    member_name: str
    admin_route_path: str
    agent_route_path: str
    shared_paths: tuple[str, ...]

    def route_path_for_audience(self, audience: PackAudience) -> str:
        """Return the checked-in route file for one audience."""

        if audience == "admin":
            return self.admin_route_path
        return self.agent_route_path


@dataclass(frozen=True)
class ProtectedRoutineRecord:
    """One stable protected routine selectively copied into a mount."""

    logical_id: str
    source_path: str
    member_name: str
    route_name: str
    audiences: tuple[PackAudience, ...]
    dependencies: tuple[ProtectedRoutineDependency, ...]
    commands: tuple[str, ...]


@dataclass(frozen=True)
class LegacySystemSkillRecord:
    """Known v1 content used only for conservative migration classification."""

    name: str
    asset_subpath: str
    content_digest: str


@dataclass(frozen=True)
class LegacySystemSkillCatalogRecord:
    """One skill record from the read-only v1 catalog."""

    name: str
    asset_subpath: str


@dataclass(frozen=True)
class LegacySystemSkillCatalog:
    """Read-only representation of the retired flat catalog."""

    schema_version: int
    skills: tuple[LegacySystemSkillCatalogRecord, ...]
    retired_skill_names: tuple[str, ...]


@dataclass(frozen=True)
class SystemSkillDefaults:
    """Default pack selectors for external and managed lanes."""

    cli: tuple[str, ...]
    managed_launch: tuple[str, ...]
    managed_join: tuple[str, ...]

    def pack_ids_for_kind(self, kind: AutoInstallKind) -> tuple[str, ...]:
        """Return pack ids for one automatic-selection lane."""

        if kind == "managed_launch":
            return self.managed_launch
        if kind == "managed_join":
            return self.managed_join
        return self.cli


@dataclass(frozen=True)
class ActorInvocationDesignator:
    """One actor-qualified protected routine invocation designator."""

    audience: PackAudience
    entrypoint_name: str
    mount_id: str
    logical_id: str
    route_name: str

    @property
    def value(self) -> str:
        """Return the route designator without a command suffix."""

        return f"{self.entrypoint_name}->{self.mount_id}->{self.route_name}"

    def command(self, command_name: str) -> str:
        """Return the designator for one command trace."""

        if not command_name.strip():
            raise SystemSkillManifestError("Invocation command names must not be empty.")
        return f"{self.value}->{command_name}()"


@dataclass(frozen=True)
class SystemSkillManifest:
    """Validated pack, public-skill, mount, and protected-routine manifest."""

    schema_version: str
    auto_skill_name: str
    defaults: SystemSkillDefaults
    packs: dict[str, SystemSkillPackRecord]
    public_skills: dict[str, PublicSystemSkillRecord]
    protected_mounts: dict[str, ProtectedMountRecord]
    protected_routines: dict[str, ProtectedRoutineRecord]
    legacy_skills: dict[str, LegacySystemSkillRecord]
    source_root: Traversable

    @property
    def pack_ids(self) -> tuple[str, ...]:
        """Return pack ids in manifest order."""

        return tuple(self.packs)

    @property
    def public_skill_names(self) -> tuple[str, ...]:
        """Return public skill names in manifest order."""

        return tuple(self.public_skills)

    @property
    def skill_names(self) -> tuple[str, ...]:
        """Return visible public names for callers that need a skill inventory."""

        return self.public_skill_names

    @property
    def retired_skill_names(self) -> tuple[str, ...]:
        """Return names recognized only as legacy migration evidence."""

        return tuple(self.legacy_skills)

    @property
    def protected_logical_ids(self) -> tuple[str, ...]:
        """Return protected logical ids in manifest order."""

        return tuple(self.protected_routines)

    def entrypoint_for_audience(self, audience: PackAudience) -> PublicSystemSkillRecord:
        """Return the single executable entrypoint for one audience."""

        records = [
            record
            for record in self.public_skills.values()
            if self.packs[record.pack_id].audience == audience and record.role == "entrypoint"
        ]
        if len(records) != 1:
            raise SystemSkillManifestError(
                f"Audience `{audience}` must resolve exactly one public entrypoint."
            )
        return records[0]


@dataclass(frozen=True)
class ComposedPublicSkillRecord:
    """One staged public tree and its nested protected evidence."""

    name: str
    role: PublicSkillRole
    path: Path
    protected_logical_ids: tuple[str, ...]


@dataclass(frozen=True)
class ComposedSystemSkillPack:
    """Complete staged output for one selected audience pack."""

    pack_id: str
    audience: PackAudience
    public_skills: tuple[ComposedPublicSkillRecord, ...]


@lru_cache(maxsize=1)
def load_system_skill_manifest() -> SystemSkillManifest:
    """Load and validate the packaged Houmao system-skill manifest."""

    source_root = resources.files(SYSTEM_SKILLS_PACKAGE)
    return _parse_system_skill_manifest(
        manifest_text=(source_root / SYSTEM_SKILL_MANIFEST_FILENAME).read_text(encoding="utf-8"),
        schema_text=(source_root / SYSTEM_SKILL_MANIFEST_SCHEMA_FILENAME).read_text(
            encoding="utf-8"
        ),
        source=f"{SYSTEM_SKILLS_PACKAGE}:{SYSTEM_SKILL_MANIFEST_FILENAME}",
        source_root=source_root,
    )


def load_system_skill_manifest_from_paths(
    *,
    manifest_path: Path,
    schema_path: Path,
    assets_root: Path | None = None,
) -> SystemSkillManifest:
    """Load a manifest from explicit paths for validation and tests."""

    resolved_manifest_path = manifest_path.resolve()
    source_root = (assets_root or resolved_manifest_path.parent).resolve()
    return _parse_system_skill_manifest(
        manifest_text=resolved_manifest_path.read_text(encoding="utf-8"),
        schema_text=schema_path.resolve().read_text(encoding="utf-8"),
        source=str(resolved_manifest_path),
        source_root=source_root,
    )


@lru_cache(maxsize=1)
def load_legacy_system_skill_catalog() -> LegacySystemSkillCatalog:
    """Load the retired v1 catalog without exposing it as install state."""

    root = resources.files(SYSTEM_SKILLS_PACKAGE)
    payload = _load_toml_mapping(
        (root / LEGACY_SYSTEM_SKILL_CATALOG_FILENAME).read_text(encoding="utf-8"),
        source=f"{SYSTEM_SKILLS_PACKAGE}:{LEGACY_SYSTEM_SKILL_CATALOG_FILENAME}",
    )
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise SystemSkillManifestError("The read-only legacy catalog must use schema version 1.")
    raw_skills = payload.get("skills")
    if not isinstance(raw_skills, dict):
        raise SystemSkillManifestError("The read-only legacy catalog has no skills mapping.")
    skills: list[LegacySystemSkillCatalogRecord] = []
    for name, raw_record in raw_skills.items():
        if not isinstance(name, str) or not isinstance(raw_record, dict):
            raise SystemSkillManifestError("The read-only legacy catalog has an invalid skill.")
        asset_subpath = raw_record.get("asset_subpath")
        if not isinstance(asset_subpath, str):
            raise SystemSkillManifestError(f"Legacy skill `{name}` has no asset_subpath.")
        skills.append(LegacySystemSkillCatalogRecord(name=name, asset_subpath=asset_subpath))
    retired = payload.get("retired_skill_names", [])
    if not isinstance(retired, list) or not all(isinstance(item, str) for item in retired):
        raise SystemSkillManifestError("The read-only legacy catalog has invalid retired names.")
    return LegacySystemSkillCatalog(
        schema_version=1,
        skills=tuple(skills),
        retired_skill_names=tuple(cast(list[str], retired)),
    )


def resolve_system_skill_pack_selection(
    manifest: SystemSkillManifest,
    *,
    pack_ids: Sequence[str],
) -> tuple[str, ...]:
    """Validate and de-duplicate installable pack ids in first-seen order."""

    resolved: list[str] = []
    seen: set[str] = set()
    for pack_id in pack_ids:
        if pack_id in manifest.protected_routines or pack_id in manifest.protected_mounts:
            raise SystemSkillManifestError(
                f"Protected system-skill id `{pack_id}` is not an install selector; "
                "select `admin` or `agent`."
            )
        if pack_id not in manifest.packs:
            raise SystemSkillManifestError(f"Unknown system-skill pack `{pack_id}`.")
        if pack_id not in seen:
            seen.add(pack_id)
            resolved.append(pack_id)
    return tuple(resolved)


def protected_routine_closure(
    manifest: SystemSkillManifest,
    *,
    audience: PackAudience,
) -> tuple[ProtectedRoutineRecord, ...]:
    """Return the manifest-ordered audience closure and validate dependencies."""

    eligible_ids = {
        routine.logical_id
        for routine in manifest.protected_routines.values()
        if audience in routine.audiences
    }
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(logical_id: str) -> None:
        if logical_id in visited:
            return
        if logical_id in visiting:
            raise SystemSkillManifestError(
                f"Protected routine dependency cycle includes `{logical_id}`."
            )
        routine = manifest.protected_routines.get(logical_id)
        if routine is None:
            raise SystemSkillManifestError(
                f"Protected routine dependency `{logical_id}` is missing."
            )
        if audience not in routine.audiences:
            raise SystemSkillManifestError(
                f"Protected routine `{logical_id}` is ineligible for `{audience}` composition."
            )
        visiting.add(logical_id)
        for dependency in routine.dependencies:
            if dependency.logical_id not in eligible_ids:
                raise SystemSkillManifestError(
                    f"Protected routine `{logical_id}` has ineligible `{audience}` dependency "
                    f"`{dependency.logical_id}`."
                )
            visit(dependency.logical_id)
        visiting.remove(logical_id)
        visited.add(logical_id)

    for logical_id in eligible_ids:
        visit(logical_id)
    return tuple(
        routine for routine in manifest.protected_routines.values() if routine.logical_id in visited
    )


def protected_invocation_designator(
    logical_id: str,
    *,
    audience: PackAudience,
    manifest: SystemSkillManifest | None = None,
) -> ActorInvocationDesignator:
    """Map one logical routine id to an actor-qualified invocation designator."""

    effective_manifest = manifest or load_system_skill_manifest()
    routine = effective_manifest.protected_routines.get(logical_id)
    if routine is None:
        raise SystemSkillManifestError(f"Unknown protected routine `{logical_id}`.")
    if audience not in routine.audiences:
        raise SystemSkillManifestError(
            f"Protected routine `{logical_id}` is not eligible for `{audience}`."
        )
    entrypoint = effective_manifest.entrypoint_for_audience(audience)
    pack = effective_manifest.packs[entrypoint.pack_id]
    if len(pack.protected_mount_ids) != 1:
        raise SystemSkillManifestError(
            f"Pack `{pack.pack_id}` must use exactly one protected mount."
        )
    return ActorInvocationDesignator(
        audience=audience,
        entrypoint_name=entrypoint.name,
        mount_id=pack.protected_mount_ids[0],
        logical_id=logical_id,
        route_name=routine.route_name,
    )


def compose_system_skill_pack(
    manifest: SystemSkillManifest,
    *,
    pack_id: str,
    destination_root: Path,
) -> ComposedSystemSkillPack:
    """Compose one complete audience pack into an empty staging root."""

    selected_ids = resolve_system_skill_pack_selection(manifest, pack_ids=(pack_id,))
    pack = manifest.packs[selected_ids[0]]
    if destination_root.exists() and any(destination_root.iterdir()):
        raise SystemSkillManifestError(
            f"Composition destination `{destination_root}` must be empty."
        )
    destination_root.mkdir(parents=True, exist_ok=True)
    closure = protected_routine_closure(manifest, audience=pack.audience)
    closure_ids = tuple(routine.logical_id for routine in closure)
    composed: list[ComposedPublicSkillRecord] = []

    for public_name in pack.public_skill_names:
        public = manifest.public_skills[public_name]
        public_root = destination_root / public.name
        _copy_resource_tree(_resource_at(manifest.source_root, public.source_path), public_root)
        mounted_ids: tuple[str, ...] = ()
        if public.role == "entrypoint":
            for mount_id in pack.protected_mount_ids:
                _compose_protected_mount(
                    manifest,
                    mount=manifest.protected_mounts[mount_id],
                    audience=pack.audience,
                    closure=closure,
                    public_root=public_root,
                )
            _render_actor_entrypoint_placeholders(
                public_root,
                entrypoint_name=public.name,
            )
            mounted_ids = closure_ids
        composed.append(
            ComposedPublicSkillRecord(
                name=public.name,
                role=public.role,
                path=public_root,
                protected_logical_ids=mounted_ids,
            )
        )

    result = ComposedSystemSkillPack(
        pack_id=pack.pack_id,
        audience=pack.audience,
        public_skills=tuple(composed),
    )
    validate_composed_system_skill_pack(manifest, result=result)
    return result


def validate_composed_system_skill_pack(
    manifest: SystemSkillManifest,
    *,
    result: ComposedSystemSkillPack,
) -> None:
    """Recursively validate one staged pack before target mutation."""

    pack = manifest.packs[result.pack_id]
    expected_public_names = set(pack.public_skill_names)
    actual_public_names = {record.path.name for record in result.public_skills}
    if actual_public_names != expected_public_names:
        raise SystemSkillManifestError(f"Pack `{pack.pack_id}` staged an invalid public path set.")
    for record in result.public_skills:
        public = manifest.public_skills[record.name]
        _validate_skill_frontmatter(
            record.path,
            expected_name=public.name,
            entrypoint_filename=SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME,
        )
        _validate_no_unresolved_actor_placeholders(record.path)
        _validate_path_invocation_notation(record.path)
        _reject_obsolete_layout_directories(record.path)
        _validate_true_subskills(record.path)
        _validate_public_scanner_safety(record.path)
        for command_name in public.public_commands:
            command_path = record.path / "commands" / f"{command_name}.md"
            if not command_path.is_file():
                raise SystemSkillManifestError(
                    f"Public skill `{public.name}` is missing command page `{command_name}`."
                )
        mount_root = record.path / "subskills"
        if public.role == "welcome":
            if mount_root.exists():
                raise SystemSkillManifestError(
                    f"Welcome `{public.name}` must not contain protected content."
                )
            if record.protected_logical_ids:
                raise SystemSkillManifestError(
                    f"Welcome `{public.name}` reports protected members."
                )
            continue
        for mount_id in pack.protected_mount_ids:
            protected_root = mount_root / manifest.protected_mounts[mount_id].member_name
            _validate_skill_frontmatter(
                protected_root,
                expected_name=mount_id,
                entrypoint_filename=SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME,
            )
            route_text = (
                protected_root / SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME
            ).read_text(encoding="utf-8")
            if SYSTEM_SKILL_ACTOR_FRAME_HEADING not in route_text:
                raise SystemSkillManifestError(
                    f"Protected route `{mount_id}` has no actor-frame gate."
                )
            for routine in protected_routine_closure(manifest, audience=pack.audience):
                routine_root = protected_root / "subskills" / routine.member_name
                _validate_skill_frontmatter(
                    routine_root,
                    expected_name=routine.logical_id,
                    entrypoint_filename=SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME,
                )
                routine_text = (
                    routine_root / SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME
                ).read_text(encoding="utf-8")
                if SYSTEM_SKILL_ACTOR_FRAME_HEADING not in routine_text:
                    raise SystemSkillManifestError(
                        f"Protected routine `{routine.logical_id}` has no actor-frame gate."
                    )
                summary = _protected_route_summary_marker(routine)
                if summary not in route_text:
                    raise SystemSkillManifestError(
                        f"Protected route `{mount_id}` has no direct summary for "
                        f"`{routine.route_name}`."
                    )


def tree_content_digest(root: Path) -> str:
    """Return a stable SHA-256 digest for one file tree."""

    from hashlib import sha256

    if not root.is_dir():
        raise SystemSkillManifestError(f"Cannot digest missing directory `{root}`.")
    digest = sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_symlink():
            digest.update(relative)
            digest.update(b"\0L\0")
            digest.update(path.readlink().as_posix().encode("utf-8"))
            digest.update(b"\0")
        elif path.is_file():
            digest.update(relative)
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _render_actor_entrypoint_placeholders(
    public_root: Path,
    *,
    entrypoint_name: str,
) -> None:
    """Resolve protected-source entrypoint placeholders in one staged composition."""

    for path in sorted(public_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml"}:
            continue
        content = path.read_text(encoding="utf-8")
        if "<public-entrypoint>" in content:
            path.write_text(
                content.replace("<public-entrypoint>", entrypoint_name),
                encoding="utf-8",
            )


def _validate_no_unresolved_actor_placeholders(public_root: Path) -> None:
    """Reject unresolved actor-entrypoint placeholders in staged public skills."""

    for path in sorted(public_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml"}:
            continue
        if "<public-entrypoint>" in path.read_text(encoding="utf-8"):
            raise SystemSkillManifestError(
                f"Composed public skill `{public_root.name}` contains an unresolved "
                f"actor entrypoint placeholder in `{path.relative_to(public_root)}`."
            )


def _parse_system_skill_manifest(
    *,
    manifest_text: str,
    schema_text: str,
    source: str,
    source_root: Traversable,
) -> SystemSkillManifest:
    """Parse, schema-check, materialize, and cross-validate a manifest."""

    payload = _load_toml_mapping(manifest_text, source=source)
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as exc:
        raise SystemSkillManifestError(f"Invalid system-skill schema JSON: {exc}") from exc
    if not isinstance(schema, dict):
        raise SystemSkillManifestError("System-skill manifest schema must be an object.")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise SystemSkillManifestError(f"Invalid system-skill JSON Schema: {exc.message}") from exc
    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path)
    )
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        raise SystemSkillManifestError(f"{source}:{path}: {error.message}")

    defaults_payload = cast(dict[str, Any], payload["defaults"])
    defaults = SystemSkillDefaults(
        cli=tuple(defaults_payload["cli"]),
        managed_launch=tuple(defaults_payload["managed_launch"]),
        managed_join=tuple(defaults_payload["managed_join"]),
    )
    packs: dict[str, SystemSkillPackRecord] = {}
    for item in cast(list[dict[str, Any]], payload["packs"]):
        pack_record = SystemSkillPackRecord(
            pack_id=item["pack_id"],
            audience=cast(PackAudience, item["audience"]),
            description=item["description"],
            public_skill_names=tuple(item["public_skills"]),
            protected_mount_ids=tuple(item["protected_mounts"]),
            default_lanes=tuple(cast(list[DefaultLane], item["default_lanes"])),
        )
        _insert_unique(packs, pack_record.pack_id, pack_record, kind="pack")
    public_skills: dict[str, PublicSystemSkillRecord] = {}
    for item in cast(list[dict[str, Any]], payload["public_skills"]):
        public_record = PublicSystemSkillRecord(
            name=item["name"],
            pack_id=item["pack_id"],
            role=cast(PublicSkillRole, item["role"]),
            source_path=item["source_path"],
            public_commands=tuple(item["public_commands"]),
            handoff_to=item.get("handoff_to"),
            welcome_delegate=item.get("welcome_delegate"),
        )
        _insert_unique(public_skills, public_record.name, public_record, kind="public skill")
    protected_mounts: dict[str, ProtectedMountRecord] = {}
    for item in cast(list[dict[str, Any]], payload["protected_mounts"]):
        mount_record = ProtectedMountRecord(
            mount_id=item["mount_id"],
            source_path=item["source_path"],
            member_name=item["member_name"],
            admin_route_path=item["admin_route_path"],
            agent_route_path=item["agent_route_path"],
            shared_paths=tuple(item["shared_paths"]),
        )
        _insert_unique(
            protected_mounts,
            mount_record.mount_id,
            mount_record,
            kind="protected mount",
        )
    protected_routines: dict[str, ProtectedRoutineRecord] = {}
    for item in cast(list[dict[str, Any]], payload["protected_routines"]):
        routine_record = ProtectedRoutineRecord(
            logical_id=item["logical_id"],
            source_path=item["source_path"],
            member_name=item["member_name"],
            route_name=item["route_name"],
            audiences=tuple(cast(list[PackAudience], item["audiences"])),
            dependencies=tuple(
                ProtectedRoutineDependency(logical_id=dependency)
                for dependency in cast(list[str], item["dependencies"])
            ),
            commands=tuple(item["commands"]),
        )
        _insert_unique(
            protected_routines,
            routine_record.logical_id,
            routine_record,
            kind="protected routine",
        )
    legacy_skills: dict[str, LegacySystemSkillRecord] = {}
    for item in cast(list[dict[str, Any]], payload["legacy_skills"]):
        legacy_record = LegacySystemSkillRecord(
            name=item["name"],
            asset_subpath=item["asset_subpath"],
            content_digest=item["content_digest"],
        )
        _insert_unique(legacy_skills, legacy_record.name, legacy_record, kind="legacy skill")

    manifest = SystemSkillManifest(
        schema_version=payload["schema_version"],
        auto_skill_name=payload["auto_skill_name"],
        defaults=defaults,
        packs=packs,
        public_skills=public_skills,
        protected_mounts=protected_mounts,
        protected_routines=protected_routines,
        legacy_skills=legacy_skills,
        source_root=source_root,
    )
    _validate_manifest_cross_references(manifest, source=source)
    return manifest


def _validate_manifest_cross_references(
    manifest: SystemSkillManifest,
    *,
    source: str,
) -> None:
    """Validate semantic references, cardinality, routes, and source ownership."""

    if manifest.schema_version != SYSTEM_SKILL_MANIFEST_SCHEMA_VERSION:
        raise SystemSkillManifestError(f"{source}: unsupported manifest schema version.")
    if manifest.auto_skill_name != SYSTEM_SKILL_AUTO_PROMPT_NAME:
        raise SystemSkillManifestError(f"{source}: auto-skill ownership changed unexpectedly.")
    reserved = {manifest.auto_skill_name}
    if reserved & (set(manifest.public_skills) | set(manifest.protected_routines)):
        raise SystemSkillManifestError(
            f"{source}: `{manifest.auto_skill_name}` must stay outside system-skill packs."
        )
    all_public_members: list[str] = []
    lane_owners: dict[DefaultLane, list[str]] = {
        "cli": [],
        "managed_launch": [],
        "managed_join": [],
    }
    for pack in manifest.packs.values():
        all_public_members.extend(pack.public_skill_names)
        for lane in pack.default_lanes:
            lane_owners[lane].append(pack.pack_id)
        public_records = []
        for public_name in pack.public_skill_names:
            public = manifest.public_skills.get(public_name)
            if public is None or public.pack_id != pack.pack_id:
                raise SystemSkillManifestError(
                    f"{source}: pack `{pack.pack_id}` has invalid public member `{public_name}`."
                )
            public_records.append(public)
        roles = [record.role for record in public_records]
        expected_roles = ["welcome", "entrypoint"] if pack.audience == "admin" else ["entrypoint"]
        if sorted(roles) != sorted(expected_roles):
            raise SystemSkillManifestError(
                f"{source}: `{pack.audience}` pack `{pack.pack_id}` must contain roles "
                f"{expected_roles}."
            )
        for mount_id in pack.protected_mount_ids:
            if mount_id not in manifest.protected_mounts:
                raise SystemSkillManifestError(
                    f"{source}: pack `{pack.pack_id}` references missing mount `{mount_id}`."
                )
    if len(all_public_members) != len(set(all_public_members)):
        raise SystemSkillManifestError(f"{source}: a public skill belongs to multiple packs.")
    if set(all_public_members) != set(manifest.public_skills):
        raise SystemSkillManifestError(f"{source}: every public skill must belong to one pack.")
    expected_defaults: dict[DefaultLane, tuple[str, ...]] = {
        "cli": manifest.defaults.cli,
        "managed_launch": manifest.defaults.managed_launch,
        "managed_join": manifest.defaults.managed_join,
    }
    for lane, pack_ids in expected_defaults.items():
        if tuple(lane_owners[lane]) != pack_ids:
            raise SystemSkillManifestError(
                f"{source}: defaults.{lane} does not match pack default_lanes."
            )
        resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids)
    for public in manifest.public_skills.values():
        _validate_owned_source(
            manifest.source_root,
            public.source_path,
            required_prefix="public",
            require_directory=True,
        )
        _require_resource_file(
            manifest.source_root,
            f"{public.source_path}/{SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME}",
        )
        _reject_resource_file(
            manifest.source_root,
            f"{public.source_path}/{SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME}",
        )
        for command in public.public_commands:
            _require_resource_file(
                manifest.source_root,
                f"{public.source_path}/commands/{command}.md",
            )
        if public.handoff_to is not None and public.handoff_to not in manifest.public_skills:
            raise SystemSkillManifestError(
                f"{source}: public handoff `{public.handoff_to}` is missing."
            )
        if (
            public.welcome_delegate is not None
            and public.welcome_delegate not in manifest.public_skills
        ):
            raise SystemSkillManifestError(
                f"{source}: welcome delegate `{public.welcome_delegate}` is missing."
            )
    for mount in manifest.protected_mounts.values():
        _validate_owned_source(
            manifest.source_root,
            mount.source_path,
            required_prefix="protected",
            require_directory=True,
        )
        for route_path in (mount.admin_route_path, mount.agent_route_path):
            if PurePosixPath(route_path).name != SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME:
                raise SystemSkillManifestError(
                    f"{source}: protected route `{route_path}` must use "
                    f"`{SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME}`."
                )
            _require_resource_file(manifest.source_root, route_path)
            _reject_resource_file(
                manifest.source_root,
                str(PurePosixPath(route_path).with_name(SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME)),
            )
        for shared_path in mount.shared_paths:
            _validate_owned_source(
                manifest.source_root,
                f"{mount.source_path}/{shared_path}",
                required_prefix="protected",
                require_directory=True,
            )
    route_names: dict[PackAudience, set[str]] = {"admin": set(), "agent": set()}
    for routine in manifest.protected_routines.values():
        _validate_owned_source(
            manifest.source_root,
            routine.source_path,
            required_prefix="protected",
            require_directory=True,
        )
        skill_path = f"{routine.source_path}/{SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME}"
        _require_resource_file(manifest.source_root, skill_path)
        _reject_resource_file(
            manifest.source_root,
            f"{routine.source_path}/{SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME}",
        )
        skill_text = _resource_at(manifest.source_root, skill_path).read_text(encoding="utf-8")
        if SYSTEM_SKILL_ACTOR_FRAME_HEADING not in skill_text:
            raise SystemSkillManifestError(
                f"{source}: protected routine `{routine.logical_id}` lacks an actor-frame gate."
            )
        commands_root = _resource_at(
            manifest.source_root,
            f"{routine.source_path}/commands",
        )
        command_page_names = {
            path.name.removesuffix(".md")
            for path in _iter_resource_files(commands_root)
            if path.name.endswith(".md")
        }
        for command in routine.commands:
            if command not in skill_text and command not in command_page_names:
                raise SystemSkillManifestError(
                    f"{source}: protected routine `{routine.logical_id}` command map omits "
                    f"`{command}`."
                )
        for audience in routine.audiences:
            if routine.route_name in route_names[audience]:
                raise SystemSkillManifestError(
                    f"{source}: duplicate `{audience}` route name `{routine.route_name}`."
                )
            route_names[audience].add(routine.route_name)
        for dependency in routine.dependencies:
            if dependency.logical_id not in manifest.protected_routines:
                raise SystemSkillManifestError(
                    f"{source}: routine `{routine.logical_id}` references missing dependency "
                    f"`{dependency.logical_id}`."
                )
    for audience in ("admin", "agent"):
        protected_routine_closure(manifest, audience=audience)
        for mount in manifest.protected_mounts.values():
            route_text = _resource_at(
                manifest.source_root,
                mount.route_path_for_audience(audience),
            ).read_text(encoding="utf-8")
            for routine in manifest.protected_routines.values():
                marker = _protected_route_summary_marker(routine)
                if audience in routine.audiences and marker not in route_text:
                    raise SystemSkillManifestError(
                        f"{source}: `{audience}` route omits `{routine.route_name}` summary."
                    )
                if audience not in routine.audiences and marker in route_text:
                    raise SystemSkillManifestError(
                        f"{source}: `{audience}` route exposes ineligible `{routine.route_name}`."
                    )
    for mount in manifest.protected_mounts.values():
        _validate_resource_invocation_notation(
            _resource_at(manifest.source_root, mount.source_path),
            source=mount.source_path,
        )


def _compose_protected_mount(
    manifest: SystemSkillManifest,
    *,
    mount: ProtectedMountRecord,
    audience: PackAudience,
    closure: tuple[ProtectedRoutineRecord, ...],
    public_root: Path,
) -> None:
    """Compose one protected mount below one staged executable entrypoint."""

    mount_root = public_root / "subskills" / mount.member_name
    mount_root.mkdir(parents=True, exist_ok=False)
    route_source = _resource_at(manifest.source_root, mount.route_path_for_audience(audience))
    (mount_root / SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME).write_text(
        route_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for shared_path in mount.shared_paths:
        _copy_resource_tree(
            _resource_at(manifest.source_root, f"{mount.source_path}/{shared_path}"),
            mount_root / shared_path,
        )
    subskills_root = mount_root / "subskills"
    subskills_root.mkdir(parents=True, exist_ok=True)
    for routine in closure:
        _copy_resource_tree(
            _resource_at(manifest.source_root, routine.source_path),
            subskills_root / routine.member_name,
        )


def _copy_resource_tree(source_root: Traversable, destination_root: Path) -> None:
    """Copy a packaged resource tree into a concrete staging directory."""

    if not source_root.is_dir():
        raise SystemSkillManifestError(f"Packaged source `{source_root}` is not a directory.")
    destination_root.mkdir(parents=True, exist_ok=True)
    for child in source_root.iterdir():
        destination_path = destination_root / child.name
        if child.is_dir():
            _copy_resource_tree(child, destination_path)
        elif child.is_file():
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            with child.open("rb") as source_handle:
                destination_path.write_bytes(source_handle.read())


def _validate_skill_frontmatter(
    root: Path,
    *,
    expected_name: str,
    entrypoint_filename: str,
) -> None:
    """Require a skill router and matching YAML-style name frontmatter."""

    skill_path = root / entrypoint_filename
    if not skill_path.is_file():
        raise SystemSkillManifestError(f"Skill tree `{root}` has no `{entrypoint_filename}`.")
    alternate_filename = (
        SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME
        if entrypoint_filename == SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME
        else SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME
    )
    if (root / alternate_filename).exists():
        raise SystemSkillManifestError(
            f"Skill tree `{root}` has ambiguous entrypoints `{entrypoint_filename}` and "
            f"`{alternate_filename}`."
        )
    text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(?P<header>.*?)\n---\s*\n", text, flags=re.DOTALL)
    if match is None:
        raise SystemSkillManifestError(f"Skill `{root}` has invalid frontmatter.")
    name_match = re.search(r"(?m)^name:\s*([^\s]+)\s*$", match.group("header"))
    if name_match is None or name_match.group(1) != expected_name:
        raise SystemSkillManifestError(
            f"Skill `{root}` frontmatter name must be `{expected_name}`."
        )


def _validate_true_subskills(root: Path) -> None:
    """Require every direct subskill directory to own only SKILL-MAIN.md."""

    for subskills_root in (path for path in root.rglob("subskills") if path.is_dir()):
        for child in subskills_root.iterdir():
            if child.is_file():
                raise SystemSkillManifestError(
                    f"Procedure page `{child}` must be a command or reference, not a subskill."
                )
            if not child.is_dir():
                continue
            parent_entrypoint = child / SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME
            public_entrypoint = child / SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME
            if public_entrypoint.exists() and parent_entrypoint.exists():
                raise SystemSkillManifestError(
                    f"Nested capability `{child}` has ambiguous entrypoint files."
                )
            if public_entrypoint.exists():
                raise SystemSkillManifestError(
                    f"Nested capability `{child}` must not own "
                    f"`{SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME}`."
                )
            if not parent_entrypoint.is_file():
                raise SystemSkillManifestError(
                    f"Nested capability `{child}` must own "
                    f"`{SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME}`."
                )


def _validate_public_scanner_safety(root: Path) -> None:
    """Require exact-SKILL.md discovery to find only the public root."""

    discovered = sorted(root.rglob(SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME))
    expected = [root / SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME]
    if discovered != expected:
        rendered = ", ".join(str(path.relative_to(root)) for path in discovered)
        raise SystemSkillManifestError(
            f"Public skill `{root}` exposes nested exact-SKILL.md entrypoints: {rendered}."
        )


def _validate_path_invocation_notation(root: Path) -> None:
    """Validate notation metadata for designator-bearing staged Markdown pages."""

    for path in sorted(root.rglob("*.md")):
        _validate_invocation_notation_text(
            path.read_text(encoding="utf-8"),
            source=str(path),
        )


def _validate_resource_invocation_notation(root: Traversable, *, source: str) -> None:
    """Validate notation metadata for packaged Markdown resources."""

    for path in _iter_resource_files(root):
        if not path.name.endswith(".md"):
            continue
        _validate_invocation_notation_text(
            path.read_text(encoding="utf-8"),
            source=f"{source}/.../{path.name}",
        )


def _validate_invocation_notation_text(text: str, *, source: str) -> None:
    """Require the standard notation declaration when object designators appear."""

    if _SYSTEM_SKILL_OBJECT_DESIGNATOR_RE.search(text) is None:
        return
    match = re.match(r"\A---\s*\n(?P<header>.*?)\n---\s*\n", text, flags=re.DOTALL)
    if match is None or SYSTEM_SKILL_INVOCATION_NOTATION_FRONTMATTER not in match.group("header"):
        raise SystemSkillManifestError(
            f"Instruction page `{source}` uses object-style invocation designators without "
            "the standard `skill_invocation_notation` declaration."
        )


def _protected_route_summary_marker(routine: ProtectedRoutineRecord) -> str:
    """Return the canonical audience-router row prefix for one protected routine."""

    return (
        f"| `{routine.route_name}` | "
        f"`subskills/{routine.member_name}/{SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME}` | "
        "When to Route Here:"
    )


def _reject_obsolete_layout_directories(root: Path) -> None:
    """Reject action directories left behind by the v1 resource layout."""

    obsolete = [path for path in root.rglob("actions") if path.is_dir()]
    if obsolete:
        raise SystemSkillManifestError(
            f"Staged skill contains obsolete action directory `{obsolete[0]}`."
        )


def _validate_owned_source(
    source_root: Traversable,
    relative_path: str,
    *,
    required_prefix: str,
    require_directory: bool,
) -> None:
    """Reject absolute, escaping, cross-area, or missing manifest sources."""

    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or ".." in pure_path.parts or not pure_path.parts:
        raise SystemSkillManifestError(f"Source path `{relative_path}` escapes the asset root.")
    if pure_path.parts[0] != required_prefix:
        raise SystemSkillManifestError(
            f"Source path `{relative_path}` must be below `{required_prefix}/`."
        )
    resource = _resource_at(source_root, relative_path)
    if require_directory and not resource.is_dir():
        raise SystemSkillManifestError(f"Source directory `{relative_path}` is missing.")
    if isinstance(source_root, Path):
        resolved_root = source_root.resolve()
        resolved_source = source_root.joinpath(*pure_path.parts).resolve()
        try:
            resolved_source.relative_to(resolved_root)
        except ValueError as exc:
            raise SystemSkillManifestError(
                f"Source path `{relative_path}` resolves outside the asset root."
            ) from exc


def _require_resource_file(source_root: Traversable, relative_path: str) -> None:
    """Require one contained packaged file."""

    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise SystemSkillManifestError(f"Source file `{relative_path}` escapes the asset root.")
    if not _resource_at(source_root, relative_path).is_file():
        raise SystemSkillManifestError(f"Required source file `{relative_path}` is missing.")


def _reject_resource_file(source_root: Traversable, relative_path: str) -> None:
    """Reject one packaged file that conflicts with its entrypoint role."""

    if _resource_at(source_root, relative_path).is_file():
        raise SystemSkillManifestError(
            f"Conflicting source entrypoint `{relative_path}` must not exist."
        )


def _resource_at(source_root: Traversable, relative_path: str) -> Traversable:
    """Resolve a POSIX manifest path below a resource root."""

    resource = source_root
    for part in PurePosixPath(relative_path).parts:
        resource = resource / part
    return resource


def _iter_resource_files(root: Traversable) -> Iterable[Traversable]:
    """Yield every file below one resource directory."""

    if not root.is_dir():
        return
    for child in root.iterdir():
        if child.is_dir():
            yield from _iter_resource_files(child)
        elif child.is_file():
            yield child


def _load_toml_mapping(text: str, *, source: str) -> dict[str, Any]:
    """Parse TOML and require an object payload."""

    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise SystemSkillManifestError(f"Invalid TOML at {source}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemSkillManifestError(f"TOML at {source} must contain an object.")
    return payload


def _insert_unique(
    target: dict[str, Any],
    key: str,
    value: Any,
    *,
    kind: str,
) -> None:
    """Insert a manifest record while rejecting duplicate identifiers."""

    if key in target:
        raise SystemSkillManifestError(f"Duplicate {kind} id `{key}`.")
    target[key] = value
