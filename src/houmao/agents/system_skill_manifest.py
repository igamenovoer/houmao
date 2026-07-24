"""Typed v4 manifest and static staging for Houmao system skills."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import tomllib
from typing import Any, Literal, cast
from urllib.parse import unquote

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError  # type: ignore[import-untyped]


SYSTEM_SKILLS_PACKAGE = "houmao.agents.assets.system_skills"
SYSTEM_SKILL_MANIFEST_FILENAME = "manifest.toml"
SYSTEM_SKILL_MANIFEST_SCHEMA_FILENAME = "manifest.schema.json"
LEGACY_SYSTEM_SKILL_CATALOG_FILENAME = "legacy/catalog.v1.toml"
SYSTEM_SKILL_MANIFEST_SCHEMA_VERSION = "houmao-system-skills.v4"
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

EXPECTED_STANDALONE_SKILL_NAMES = (
    "houmao-admin-welcome",
    "houmao-admin-entrypoint",
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
)
EXPECTED_NARROW_IMPLICIT_SKILL_NAMES = (
    "houmao-admin-entrypoint",
    "houmao-agent-entrypoint",
)
EXPECTED_EXPLICIT_STANDALONE_SKILL_NAMES = (
    "houmao-admin-welcome",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
)
EXPECTED_SHARED_ROUTINE_IDS = (
    "houmao-adv-usage-pattern",
    "houmao-agent-definition",
    "houmao-agent-email-comms",
    "houmao-agent-gateway",
    "houmao-agent-inspect",
    "houmao-agent-instance",
    "houmao-agent-messaging",
    "houmao-credential-mgr",
    "houmao-ext-graphing",
    "houmao-interop-ag-ui",
    "houmao-mailbox-mgr",
    "houmao-memory-mgr",
    "houmao-operator-messaging",
    "houmao-process-emails-via-gateway",
    "houmao-project-mgr",
    "houmao-utils-workspace-mgr",
)
EXPECTED_PACK_MEMBERS: dict[str, tuple[str, ...]] = {
    "admin": (
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    ),
    "agent": (
        "houmao-agent-entrypoint",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    ),
}

_MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\((?P<target>[^)]+)\)")
_OBJECT_DESIGNATOR_RE = re.compile(r"\b(?:X|houmao-[a-z0-9-]+)->[A-Za-z0-9<>()_-]+")
_ACTUAL_INVALID_SKILL_CALL_RE = re.compile(r"\bhoumao-[a-z0-9-]+\(\)(?:->|\b)")
_INLINE_OBJECT_DESIGNATOR_RE = re.compile(
    r"`(?P<value>houmao-[a-z0-9-]+(?:->[a-z0-9-]+(?:\(\))?)+)`"
)

PackAudience = Literal["admin", "agent"]
StandaloneSkillRole = Literal["welcome", "entrypoint", "shared-routines", "loop"]
ActivationPosture = Literal["narrow-implicit", "explicit"]
StaticProjectionMode = Literal["copy", "symlink"]
DefaultLane = Literal["cli", "managed_launch", "managed_join"]
AutoInstallKind = Literal["managed_launch", "managed_join", "cli_default"]


class SystemSkillManifestError(RuntimeError):
    """Raised when static system-skill metadata or content is invalid."""


@dataclass(frozen=True)
class SharedRoutineDependency:
    """One logical dependency between shared child routines."""

    logical_id: str


@dataclass(frozen=True)
class SystemSkillPackRecord:
    """One atomically selected actor pack of standalone skills."""

    pack_id: str
    audience: PackAudience
    description: str
    standalone_skill_names: tuple[str, ...]
    default_lanes: tuple[DefaultLane, ...]


@dataclass(frozen=True)
class StandaloneSystemSkillRecord:
    """One host-discoverable, independently copyable skill root."""

    name: str
    role: StandaloneSkillRole
    source_path: str
    activation: ActivationPosture
    pack_ids: tuple[str, ...]
    commands: tuple[str, ...]
    aliases: tuple[str, ...]
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class SharedRoutineRecord:
    """One parent-scoped child owned by ``houmao-shared-routines``."""

    logical_id: str
    source_path: str
    member_name: str
    route_name: str
    audiences: tuple[PackAudience, ...]
    dependencies: tuple[SharedRoutineDependency, ...]
    commands: tuple[str, ...]
    aliases: tuple[str, ...]


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
    """Default actor pack selectors for external and managed lanes."""

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
class SystemSkillManifest:
    """Validated v4 static collection manifest."""

    schema_version: str
    auto_skill_name: str
    defaults: SystemSkillDefaults
    packs: dict[str, SystemSkillPackRecord]
    standalone_skills: dict[str, StandaloneSystemSkillRecord]
    shared_routines: dict[str, SharedRoutineRecord]
    legacy_skills: dict[str, LegacySystemSkillRecord]
    source_root: Traversable

    @property
    def pack_ids(self) -> tuple[str, ...]:
        """Return pack ids in manifest order."""

        return tuple(self.packs)

    @property
    def standalone_skill_names(self) -> tuple[str, ...]:
        """Return standalone skill names in manifest order."""

        return tuple(self.standalone_skills)

    @property
    def skill_names(self) -> tuple[str, ...]:
        """Return installable standalone skill names."""

        return self.standalone_skill_names

    @property
    def shared_logical_ids(self) -> tuple[str, ...]:
        """Return parent-scoped child ids in manifest order."""

        return tuple(self.shared_routines)

    @property
    def retired_skill_names(self) -> tuple[str, ...]:
        """Return names recognized only as legacy migration evidence."""

        return tuple(self.legacy_skills)

    def entrypoint_for_audience(self, audience: PackAudience) -> StandaloneSystemSkillRecord:
        """Return the single actor entrypoint for one audience."""

        records = [
            record
            for record in self.standalone_skills.values()
            if record.role == "entrypoint"
            and any(self.packs[pack_id].audience == audience for pack_id in record.pack_ids)
        ]
        if len(records) != 1:
            raise SystemSkillManifestError(
                f"Audience `{audience}` must resolve exactly one standalone entrypoint."
            )
        return records[0]


@dataclass(frozen=True)
class StagedStandaloneSystemSkill:
    """One complete static skill directory staged for projection."""

    name: str
    role: StandaloneSkillRole
    source_path: str
    path: Path
    owning_pack_ids: tuple[str, ...]
    content_digest: str


@dataclass(frozen=True)
class StagedSystemSkillCollection:
    """Deduplicated staged union for one or more actor packs."""

    selected_pack_ids: tuple[str, ...]
    projection_mode: StaticProjectionMode
    skills: tuple[StagedStandaloneSystemSkill, ...]


@lru_cache(maxsize=1)
def load_system_skill_manifest() -> SystemSkillManifest:
    """Load and validate the packaged v4 system-skill manifest."""

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
    """Load a v4 manifest from explicit paths for validation and tests."""

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
    """Validate and de-duplicate actor pack ids in first-seen order."""

    resolved: list[str] = []
    for pack_id in pack_ids:
        if pack_id in manifest.standalone_skills:
            raise SystemSkillManifestError(
                f"Standalone skill `{pack_id}` is not a pack selector; select `admin` or `agent`."
            )
        if pack_id in manifest.shared_routines:
            raise SystemSkillManifestError(
                f"Shared routine `{pack_id}` is not an install selector; select `admin` or `agent`."
            )
        if pack_id not in manifest.packs:
            raise SystemSkillManifestError(f"Unknown system-skill pack `{pack_id}`.")
        if pack_id not in resolved:
            resolved.append(pack_id)
    return tuple(resolved)


def resolve_system_skill_pack_members(
    manifest: SystemSkillManifest,
    *,
    pack_ids: Sequence[str],
) -> tuple[StandaloneSystemSkillRecord, ...]:
    """Resolve selected packs to a first-occurrence, deduplicated static union."""

    selected = resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids)
    names: list[str] = []
    for pack_id in selected:
        for name in manifest.packs[pack_id].standalone_skill_names:
            if name not in names:
                names.append(name)
    return tuple(manifest.standalone_skills[name] for name in names)


def stage_system_skill_collection(
    manifest: SystemSkillManifest,
    *,
    pack_ids: Sequence[str],
    destination_root: Path,
    projection_mode: StaticProjectionMode = "copy",
) -> StagedSystemSkillCollection:
    """Stage complete source directories without rendering or composition."""

    if projection_mode not in {"copy", "symlink"}:
        raise SystemSkillManifestError(f"Unsupported static projection mode `{projection_mode}`.")
    selected = resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids)
    if destination_root.exists() and any(destination_root.iterdir()):
        raise SystemSkillManifestError(
            f"Static staging destination `{destination_root}` must be empty."
        )
    destination_root.mkdir(parents=True, exist_ok=True)
    staged: list[StagedStandaloneSystemSkill] = []
    for record in resolve_system_skill_pack_members(manifest, pack_ids=selected):
        destination = destination_root / record.name
        source_resource = _resource_at(manifest.source_root, record.source_path)
        if projection_mode == "copy":
            _copy_resource_tree(source_resource, destination)
        else:
            source_path = _resource_filesystem_path(
                manifest.source_root,
                record.source_path,
            )
            destination.symlink_to(source_path, target_is_directory=True)
        source_digest = resource_tree_content_digest(source_resource)
        if tree_content_digest(destination) != source_digest:
            raise SystemSkillManifestError(f"Static staging changed content for `{record.name}`.")
        owners = tuple(
            pack_id
            for pack_id in selected
            if record.name in manifest.packs[pack_id].standalone_skill_names
        )
        staged.append(
            StagedStandaloneSystemSkill(
                name=record.name,
                role=record.role,
                source_path=record.source_path,
                path=destination,
                owning_pack_ids=owners,
                content_digest=source_digest,
            )
        )
    return StagedSystemSkillCollection(
        selected_pack_ids=selected,
        projection_mode=projection_mode,
        skills=tuple(staged),
    )


def standalone_system_skill_source_path(
    manifest: SystemSkillManifest,
    record: StandaloneSystemSkillRecord,
) -> Path:
    """Return the direct filesystem source path for one standalone record."""

    return _resource_filesystem_path(manifest.source_root, record.source_path)


def standalone_system_skill_content_digest(
    manifest: SystemSkillManifest,
    record: StandaloneSystemSkillRecord,
) -> str:
    """Return the packaged content digest for one standalone record."""

    return resource_tree_content_digest(_resource_at(manifest.source_root, record.source_path))


def validate_static_system_skill_source(manifest: SystemSkillManifest) -> None:
    """Validate exact static ownership, entrypoint roles, metadata, links, and routes."""

    public_root = _resource_at(manifest.source_root, "public")
    if not public_root.is_dir():
        raise SystemSkillManifestError("The static system-skill public root is missing.")
    discovered_skill_paths = tuple(
        relative
        for relative, resource in _walk_resources(public_root)
        if resource.is_file()
        and PurePosixPath(relative).name == SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME
    )
    expected_skill_paths = tuple(
        f"{name}/{SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME}"
        for name in EXPECTED_STANDALONE_SKILL_NAMES
    )
    if set(discovered_skill_paths) != set(expected_skill_paths):
        raise SystemSkillManifestError(
            "Static public discovery must expose exactly six canonical SKILL.md roots."
        )
    active_protected = _resource_at(manifest.source_root, "protected")
    if active_protected.is_dir():
        raise SystemSkillManifestError("The v4 source must not contain an active protected tree.")

    for record in manifest.standalone_skills.values():
        root = _resource_at(manifest.source_root, record.source_path)
        _validate_owned_source(
            manifest.source_root,
            record.source_path,
            required_prefix="public",
            require_directory=True,
        )
        _validate_skill_frontmatter(
            root,
            expected_name=record.name,
            entrypoint_filename=SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME,
        )
        _reject_resource_file(
            manifest.source_root,
            f"{record.source_path}/{SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME}",
        )
        _validate_metadata_posture(root, activation=record.activation, source=record.source_path)
        _validate_local_markdown_links(root, source=record.source_path)
        _validate_resource_invocation_notation(root, source=record.source_path)
        _validate_no_forbidden_placeholders(root, source=record.source_path)

    shared_root = _resource_at(
        manifest.source_root,
        manifest.standalone_skills["houmao-shared-routines"].source_path,
    )
    child_root = shared_root / "subskills"
    actual_child_names = {child.name for child in child_root.iterdir() if child.is_dir()}
    if actual_child_names != set(EXPECTED_SHARED_ROUTINE_IDS):
        raise SystemSkillManifestError(
            "houmao-shared-routines must own exactly the sixteen canonical children."
        )
    shared_entrypoint = (shared_root / SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME).read_text(
        encoding="utf-8"
    )
    for routine in manifest.shared_routines.values():
        root = _resource_at(manifest.source_root, routine.source_path)
        _validate_skill_frontmatter(
            root,
            expected_name=routine.logical_id,
            entrypoint_filename=SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME,
        )
        _reject_resource_file(
            manifest.source_root,
            f"{routine.source_path}/{SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME}",
        )
        if routine.member_name != PurePosixPath(routine.source_path).name:
            raise SystemSkillManifestError(
                f"Shared routine `{routine.logical_id}` has a mismatched member name."
            )
        entrypoint_text = (root / SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME).read_text(
            encoding="utf-8"
        )
        if SYSTEM_SKILL_ACTOR_FRAME_HEADING not in entrypoint_text:
            raise SystemSkillManifestError(
                f"Shared routine `{routine.logical_id}` lacks an actor-frame gate."
            )
        if f"| `{routine.route_name}` |" not in shared_entrypoint:
            raise SystemSkillManifestError(
                f"Shared router omits a route row for `{routine.route_name}`."
            )
        if "When to Route Here" not in shared_entrypoint:
            raise SystemSkillManifestError("Shared router lacks When to Route Here guidance.")
        _validate_metadata_posture(root, activation="explicit", source=routine.source_path)

    for loop_name in ("houmao-agent-loop-pro", "houmao-agent-loop-lite"):
        if (child_root / loop_name).is_dir():
            raise SystemSkillManifestError(f"Top-level loop `{loop_name}` must not be a child.")
    _validate_manifest_object_designators(manifest, public_root=public_root)


def tree_content_digest(root: Path) -> str:
    """Return a stable SHA-256 digest for one concrete file tree."""

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
            digest.update(b"\0F\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def resource_tree_content_digest(root: Traversable) -> str:
    """Return the same stable digest for a packaged resource tree."""

    from hashlib import sha256

    if isinstance(root, Path):
        return tree_content_digest(root)
    if not root.is_dir():
        raise SystemSkillManifestError(f"Cannot digest missing packaged directory `{root}`.")
    digest = sha256()
    for relative, resource in sorted(_walk_resources(root), key=lambda item: item[0]):
        if not resource.is_file():
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0F\0")
        with resource.open("rb") as handle:
            digest.update(handle.read())
        digest.update(b"\0")
    return digest.hexdigest()


def _parse_system_skill_manifest(
    *,
    manifest_text: str,
    schema_text: str,
    source: str,
    source_root: Traversable,
) -> SystemSkillManifest:
    """Parse, schema-check, materialize, and cross-validate a v4 manifest."""

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
            standalone_skill_names=tuple(item["standalone_skills"]),
            default_lanes=tuple(cast(list[DefaultLane], item["default_lanes"])),
        )
        _insert_unique(packs, pack_record.pack_id, pack_record, kind="pack")
    standalone_skills: dict[str, StandaloneSystemSkillRecord] = {}
    for item in cast(list[dict[str, Any]], payload["standalone_skills"]):
        standalone_record = StandaloneSystemSkillRecord(
            name=item["name"],
            role=cast(StandaloneSkillRole, item["role"]),
            source_path=item["source_path"],
            activation=cast(ActivationPosture, item["activation"]),
            pack_ids=tuple(item["pack_ids"]),
            commands=tuple(item["commands"]),
            aliases=tuple(item["aliases"]),
            dependencies=tuple(item["dependencies"]),
        )
        _insert_unique(
            standalone_skills,
            standalone_record.name,
            standalone_record,
            kind="standalone skill",
        )
    shared_routines: dict[str, SharedRoutineRecord] = {}
    for item in cast(list[dict[str, Any]], payload["shared_routines"]):
        routine_record = SharedRoutineRecord(
            logical_id=item["logical_id"],
            source_path=item["source_path"],
            member_name=item["member_name"],
            route_name=item["route_name"],
            audiences=tuple(cast(list[PackAudience], item["audiences"])),
            dependencies=tuple(
                SharedRoutineDependency(logical_id=dependency)
                for dependency in cast(list[str], item["dependencies"])
            ),
            commands=tuple(item["commands"]),
            aliases=tuple(item["aliases"]),
        )
        _insert_unique(
            shared_routines,
            routine_record.logical_id,
            routine_record,
            kind="shared routine",
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
        standalone_skills=standalone_skills,
        shared_routines=shared_routines,
        legacy_skills=legacy_skills,
        source_root=source_root,
    )
    _validate_manifest_cross_references(manifest, source=source)
    validate_static_system_skill_source(manifest)
    return manifest


def _validate_manifest_cross_references(
    manifest: SystemSkillManifest,
    *,
    source: str,
) -> None:
    """Validate exact records, pack closure, dependencies, routes, and operations."""

    if manifest.schema_version != SYSTEM_SKILL_MANIFEST_SCHEMA_VERSION:
        raise SystemSkillManifestError(f"{source}: unsupported manifest schema version.")
    if manifest.auto_skill_name != SYSTEM_SKILL_AUTO_PROMPT_NAME:
        raise SystemSkillManifestError(f"{source}: auto-skill ownership changed unexpectedly.")
    if tuple(manifest.standalone_skills) != EXPECTED_STANDALONE_SKILL_NAMES:
        raise SystemSkillManifestError(f"{source}: standalone skill inventory is not canonical.")
    if set(manifest.shared_routines) != set(EXPECTED_SHARED_ROUTINE_IDS):
        raise SystemSkillManifestError(f"{source}: shared routine inventory is not canonical.")
    if tuple(manifest.packs) != ("admin", "agent"):
        raise SystemSkillManifestError(f"{source}: pack inventory must be admin then agent.")
    narrow_implicit_names = tuple(
        record.name
        for record in manifest.standalone_skills.values()
        if record.activation == "narrow-implicit"
    )
    if narrow_implicit_names != EXPECTED_NARROW_IMPLICIT_SKILL_NAMES:
        raise SystemSkillManifestError(
            f"{source}: only actor entrypoints may use narrow implicit activation."
        )
    explicit_names = tuple(
        record.name
        for record in manifest.standalone_skills.values()
        if record.activation == "explicit"
    )
    if explicit_names != EXPECTED_EXPLICIT_STANDALONE_SKILL_NAMES:
        raise SystemSkillManifestError(
            f"{source}: welcome, shared routines, and loop roots must remain explicit."
        )
    for pack_id, expected_members in EXPECTED_PACK_MEMBERS.items():
        pack = manifest.packs[pack_id]
        if pack.standalone_skill_names != expected_members:
            raise SystemSkillManifestError(
                f"{source}: pack `{pack_id}` does not contain its canonical static members."
            )
        for name in pack.standalone_skill_names:
            record = manifest.standalone_skills.get(name)
            if record is None or pack_id not in record.pack_ids:
                raise SystemSkillManifestError(
                    f"{source}: pack `{pack_id}` has invalid standalone member `{name}`."
                )
    for record in manifest.standalone_skills.values():
        expected_owners = tuple(
            pack_id
            for pack_id, pack in manifest.packs.items()
            if record.name in pack.standalone_skill_names
        )
        if record.pack_ids != expected_owners:
            raise SystemSkillManifestError(
                f"{source}: standalone skill `{record.name}` has inconsistent pack ownership."
            )
        for standalone_dependency in record.dependencies:
            if standalone_dependency not in manifest.standalone_skills:
                raise SystemSkillManifestError(
                    f"{source}: standalone skill `{record.name}` references missing sibling "
                    f"`{standalone_dependency}`."
                )
            for pack_id in record.pack_ids:
                if standalone_dependency not in manifest.packs[pack_id].standalone_skill_names:
                    raise SystemSkillManifestError(
                        f"{source}: pack `{pack_id}` omits dependency "
                        f"`{standalone_dependency}` required by `{record.name}`."
                    )
        _validate_manifest_operations(
            _resource_at(manifest.source_root, record.source_path),
            entrypoint_filename=SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME,
            commands=record.commands,
            aliases=record.aliases,
            logical_id=record.name,
        )
    route_names: dict[PackAudience, set[str]] = {"admin": set(), "agent": set()}
    for routine in manifest.shared_routines.values():
        expected_path = "public/houmao-shared-routines/subskills/" + routine.member_name
        if routine.source_path != expected_path:
            raise SystemSkillManifestError(
                f"{source}: shared routine `{routine.logical_id}` has invalid ownership path."
            )
        for audience in routine.audiences:
            if routine.route_name in route_names[audience]:
                raise SystemSkillManifestError(
                    f"{source}: duplicate `{audience}` route `{routine.route_name}`."
                )
            route_names[audience].add(routine.route_name)
        for routine_dependency in routine.dependencies:
            target = manifest.shared_routines.get(routine_dependency.logical_id)
            if target is None:
                raise SystemSkillManifestError(
                    f"{source}: routine `{routine.logical_id}` references missing dependency "
                    f"`{routine_dependency.logical_id}`."
                )
            for audience in routine.audiences:
                if audience not in target.audiences:
                    raise SystemSkillManifestError(
                        f"{source}: routine `{routine.logical_id}` has ineligible `{audience}` "
                        f"dependency `{routine_dependency.logical_id}`."
                    )
        _validate_manifest_operations(
            _resource_at(manifest.source_root, routine.source_path),
            entrypoint_filename=SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME,
            commands=routine.commands,
            aliases=routine.aliases,
            logical_id=routine.logical_id,
        )
    default_lanes: tuple[DefaultLane, ...] = ("cli", "managed_launch", "managed_join")
    lane_owners: dict[DefaultLane, tuple[str, ...]] = {
        lane: tuple(pack.pack_id for pack in manifest.packs.values() if lane in pack.default_lanes)
        for lane in default_lanes
    }
    if lane_owners["cli"] != manifest.defaults.cli:
        raise SystemSkillManifestError(f"{source}: defaults.cli does not match pack lanes.")
    if lane_owners["managed_launch"] != manifest.defaults.managed_launch:
        raise SystemSkillManifestError(
            f"{source}: defaults.managed_launch does not match pack lanes."
        )
    if lane_owners["managed_join"] != manifest.defaults.managed_join:
        raise SystemSkillManifestError(
            f"{source}: defaults.managed_join does not match pack lanes."
        )


def _validate_manifest_operations(
    root: Traversable,
    *,
    entrypoint_filename: str,
    commands: tuple[str, ...],
    aliases: tuple[str, ...],
    logical_id: str,
) -> None:
    """Require every declared operation and alias to remain represented in source."""

    entrypoint = root / entrypoint_filename
    if not entrypoint.is_file():
        raise SystemSkillManifestError(
            f"System skill `{logical_id}` is missing `{entrypoint_filename}`."
        )
    source_text = entrypoint.read_text(encoding="utf-8")
    command_page_names = {
        PurePosixPath(relative).stem
        for relative, resource in _walk_resources(root)
        if resource.is_file() and "/commands/" in f"/{relative}" and relative.endswith(".md")
    }
    for command in commands:
        if command not in source_text and command not in command_page_names:
            raise SystemSkillManifestError(
                f"System skill `{logical_id}` omits declared operation `{command}`."
            )
    for alias in aliases:
        alias_parts = alias.split("=", maxsplit=1)
        alias_name = alias_parts[0]
        canonical_name = alias_parts[-1]
        if (
            alias_name not in source_text
            and alias_name not in command_page_names
            and canonical_name not in source_text
            and canonical_name not in command_page_names
        ):
            raise SystemSkillManifestError(
                f"System skill `{logical_id}` omits declared alias `{alias_name}`."
            )


def _validate_skill_frontmatter(
    root: Traversable,
    *,
    expected_name: str,
    entrypoint_filename: str,
) -> None:
    """Require one role-canonical entrypoint and matching name frontmatter."""

    skill_path = root / entrypoint_filename
    if not skill_path.is_file():
        raise SystemSkillManifestError(f"Skill tree `{root}` has no `{entrypoint_filename}`.")
    alternate = (
        SYSTEM_SKILL_PARENT_SCOPED_ENTRYPOINT_FILENAME
        if entrypoint_filename == SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME
        else SYSTEM_SKILL_PUBLIC_ENTRYPOINT_FILENAME
    )
    if (root / alternate).is_file():
        raise SystemSkillManifestError(
            f"Skill tree `{root}` has ambiguous entrypoints `{entrypoint_filename}` and "
            f"`{alternate}`."
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


def _validate_metadata_posture(
    root: Traversable,
    *,
    activation: ActivationPosture,
    source: str,
) -> None:
    """Require OpenAI metadata to match the manifest activation posture."""

    metadata_path = root / "agents" / "openai.yaml"
    if not metadata_path.is_file():
        raise SystemSkillManifestError(f"Skill `{source}` has no agents/openai.yaml metadata.")
    text = metadata_path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*allow_implicit_invocation:\s*(true|false)\s*$", text)
    expected = activation == "narrow-implicit"
    if match is None or (match.group(1) == "true") != expected:
        raise SystemSkillManifestError(
            f"Skill `{source}` has metadata inconsistent with activation `{activation}`."
        )


def _validate_local_markdown_links(root: Traversable, *, source: str) -> None:
    """Require every relative Markdown link to resolve within its owning skill."""

    for relative, resource in _walk_resources(root):
        if not resource.is_file() or not relative.endswith(".md"):
            continue
        text = _strip_markdown_code(resource.read_text(encoding="utf-8"))
        for match in _MARKDOWN_LINK_RE.finditer(text):
            raw_target = match.group("target").strip()
            if raw_target.startswith("<") and raw_target.endswith(">"):
                raw_target = raw_target[1:-1]
            else:
                raw_target = raw_target.split(maxsplit=1)[0]
            target = unquote(raw_target).split("#", maxsplit=1)[0]
            if (
                not target
                or raw_target.startswith("#")
                or raw_target.startswith("//")
                or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw_target)
                or any(character in target for character in "{}")
            ):
                continue
            page_parent = PurePosixPath(relative).parent.as_posix()
            normalized = posixpath.normpath(posixpath.join(page_parent, target))
            target_path = PurePosixPath(normalized)
            if target_path.is_absolute() or ".." in target_path.parts:
                raise SystemSkillManifestError(
                    f"Markdown link `{raw_target}` in `{source}/{relative}` escapes its owner."
                )
            linked = _resource_at(root, normalized)
            if not linked.is_file() and not linked.is_dir():
                raise SystemSkillManifestError(
                    f"Broken local Markdown link `{raw_target}` in `{source}/{relative}`."
                )


def _strip_markdown_code(text: str) -> str:
    """Remove fenced and inline code before interpreting Markdown links."""

    without_fences = re.sub(r"(?ms)^(```|~~~).*?^\1\s*$", "", text)
    return re.sub(r"`[^`\n]*`", "", without_fences)


def _validate_resource_invocation_notation(root: Traversable, *, source: str) -> None:
    """Validate notation metadata and basic object-designator syntax."""

    for relative, resource in _walk_resources(root):
        if not resource.is_file() or not relative.endswith(".md"):
            continue
        text = resource.read_text(encoding="utf-8")
        if _ACTUAL_INVALID_SKILL_CALL_RE.search(text):
            raise SystemSkillManifestError(
                f"Instruction page `{source}/{relative}` calls a skill component with `()`."
            )
        for match in _INLINE_OBJECT_DESIGNATOR_RE.finditer(text):
            _validate_object_designator_syntax(
                match.group("value"),
                source=f"{source}/{relative}",
            )
        if _OBJECT_DESIGNATOR_RE.search(text) is None:
            continue
        frontmatter = re.match(r"\A---\s*\n(?P<header>.*?)\n---\s*\n", text, re.DOTALL)
        if (
            frontmatter is None
            or SYSTEM_SKILL_INVOCATION_NOTATION_FRONTMATTER not in frontmatter.group("header")
        ):
            raise SystemSkillManifestError(
                f"Instruction page `{source}/{relative}` uses object designators without the "
                "standard skill_invocation_notation declaration."
            )


def _validate_object_designator_syntax(designator: str, *, source: str) -> None:
    """Require bare object components before a fully parenthesized command chain."""

    components = designator.split("->")
    if re.fullmatch(r"houmao-[a-z0-9-]+", components[0]) is None:
        raise SystemSkillManifestError(
            f"Instruction page `{source}` has invalid skill designator `{designator}`."
        )
    command_started = False
    for component in components[1:]:
        is_bare = re.fullmatch(r"[a-z0-9-]+", component) is not None
        is_command = re.fullmatch(r"[a-z0-9-]+\(\)", component) is not None
        if not is_bare and not is_command:
            raise SystemSkillManifestError(
                f"Instruction page `{source}` has invalid component in `{designator}`."
            )
        if command_started and not is_command:
            raise SystemSkillManifestError(
                f"Instruction page `{source}` returns to a bare component in `{designator}`."
            )
        command_started = command_started or is_command


def _validate_manifest_object_designators(
    manifest: SystemSkillManifest,
    *,
    public_root: Traversable,
) -> None:
    """Resolve concrete designators to declared standalone, child, and command records."""

    for relative, resource in _walk_resources(public_root):
        if not resource.is_file() or not relative.endswith(".md"):
            continue
        text = resource.read_text(encoding="utf-8")
        for match in _INLINE_OBJECT_DESIGNATOR_RE.finditer(text):
            designator = match.group("value")
            components = designator.split("->")
            root_record = manifest.standalone_skills.get(components[0])
            if root_record is None:
                raise SystemSkillManifestError(
                    f"Instruction page `public/{relative}` references unknown skill "
                    f"`{components[0]}`."
                )
            cursor = 1
            command_names = root_record.commands
            if cursor < len(components) and not components[cursor].endswith("()"):
                child_name = components[cursor]
                child = manifest.shared_routines.get(child_name)
                if root_record.name != "houmao-shared-routines" or child is None:
                    raise SystemSkillManifestError(
                        f"Instruction page `public/{relative}` references unknown subskill "
                        f"in `{designator}`."
                    )
                command_names = child.commands
                cursor += 1
            if cursor < len(components):
                command_name = components[cursor].removesuffix("()")
                if command_name not in command_names:
                    raise SystemSkillManifestError(
                        f"Instruction page `public/{relative}` references undeclared command "
                        f"`{command_name}` in `{designator}`."
                    )


def _validate_no_forbidden_placeholders(root: Traversable, *, source: str) -> None:
    """Reject composition placeholders in static source content."""

    for relative, resource in _walk_resources(root):
        if not resource.is_file() or PurePosixPath(relative).suffix not in {".md", ".yaml", ".yml"}:
            continue
        text = resource.read_text(encoding="utf-8")
        if "<public-entrypoint>" in text:
            raise SystemSkillManifestError(
                f"Static source `{source}/{relative}` contains a composition placeholder."
            )


def _copy_resource_tree(source_root: Traversable, destination_root: Path) -> None:
    """Copy one complete packaged resource directory without content rewriting."""

    if not source_root.is_dir():
        raise SystemSkillManifestError(f"Packaged source `{source_root}` is not a directory.")
    if isinstance(source_root, Path):
        shutil.copytree(source_root, destination_root, symlinks=True, copy_function=shutil.copy2)
        return
    destination_root.mkdir(parents=True, exist_ok=False)
    for child in source_root.iterdir():
        destination_path = destination_root / child.name
        if child.is_dir():
            _copy_resource_tree(child, destination_path)
        elif child.is_file():
            with child.open("rb") as source_handle:
                destination_path.write_bytes(source_handle.read())


def _resource_filesystem_path(source_root: Traversable, relative_path: str) -> Path:
    """Resolve a packaged source as a direct filesystem directory for symlinking."""

    if not isinstance(source_root, Path):
        raise SystemSkillManifestError(
            "Direct symlink staging requires filesystem-backed packaged skill assets."
        )
    path = source_root.joinpath(*PurePosixPath(relative_path).parts).resolve()
    if not path.is_dir():
        raise SystemSkillManifestError(f"Static source directory `{relative_path}` is missing.")
    return path


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
        try:
            source_root.joinpath(*pure_path.parts).resolve().relative_to(source_root.resolve())
        except ValueError as exc:
            raise SystemSkillManifestError(
                f"Source path `{relative_path}` resolves outside the asset root."
            ) from exc


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
        if part in {"", "."}:
            continue
        resource = resource / part
    return resource


def _walk_resources(root: Traversable, prefix: str = "") -> Iterable[tuple[str, Traversable]]:
    """Yield resource paths and objects recursively in deterministic order."""

    if not root.is_dir():
        return
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        relative = f"{prefix}/{child.name}" if prefix else child.name
        yield relative, child
        if child.is_dir():
            yield from _walk_resources(child, relative)


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
    """Insert one manifest record while rejecting duplicate identifiers."""

    if key in target:
        raise SystemSkillManifestError(f"Duplicate {kind} id `{key}`.")
    target[key] = value
