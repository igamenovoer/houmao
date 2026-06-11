"""Catalog loading and installation helpers for Houmao-owned system skills."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module, resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path
import shutil
import tomllib
from typing import Any, Literal, cast


SYSTEM_SKILLS_PACKAGE = "houmao.agents.assets.system_skills"
SYSTEM_SKILL_CATALOG_FILENAME = "catalog.toml"
SYSTEM_SKILL_SCHEMA_FILENAME = "catalog.schema.json"

SYSTEM_SKILL_SET_CORE = "core"
SYSTEM_SKILL_SET_ALL = "all"
SYSTEM_SKILL_TOURING = "houmao-touring"
SYSTEM_SKILL_SPECIALIST_MGR = "houmao-specialist-mgr"
SYSTEM_SKILL_CREDENTIAL_MGR = "houmao-credential-mgr"
SYSTEM_SKILL_AGENT_DEFINITION = "houmao-agent-definition"
SYSTEM_SKILL_AGENT_INSTANCE = "houmao-agent-instance"
SYSTEM_SKILL_AGENT_INSPECT = "houmao-agent-inspect"
SYSTEM_SKILL_OPERATOR_MESSAGING = "houmao-operator-messaging"
SYSTEM_SKILL_AGENT_MESSAGING = "houmao-agent-messaging"
SYSTEM_SKILL_AGENT_GATEWAY = "houmao-agent-gateway"
SYSTEM_SKILL_INTEROP_AG_UI = "houmao-interop-ag-ui"
SYSTEM_SKILL_MEMORY_MGR = "houmao-memory-mgr"
SYSTEM_SKILL_AGENT_LOOP_PRO = "houmao-agent-loop-pro"
SYSTEM_SKILL_UTILS_WORKSPACE_MGR = "houmao-utils-workspace-mgr"

_SYSTEM_SKILL_DESTINATION_BY_TOOL: dict[str, str] = {
    "claude": "skills",
    "codex": "skills",
    "copilot": "skills",
    "gemini": ".gemini/skills",
    "kimi": "skills",
}
AutoInstallKind = Literal["managed_launch", "managed_join", "cli_default"]
SystemSkillProjectionMode = Literal["copy", "symlink"]
SystemSkillPolicyMode = Literal["default", "inherit", "extend", "replace", "none"]
SourceSystemSkillPolicyMode = Literal["default", "extend", "replace", "none"]
ProfileSystemSkillPolicyMode = Literal["inherit", "extend", "replace", "none"]
SOURCE_SYSTEM_SKILL_POLICY_MODES: tuple[SystemSkillPolicyMode, ...] = (
    "default",
    "extend",
    "replace",
    "none",
)
PROFILE_SYSTEM_SKILL_POLICY_MODES: tuple[SystemSkillPolicyMode, ...] = (
    "inherit",
    "extend",
    "replace",
    "none",
)


class SystemSkillError(RuntimeError):
    """Base error for Houmao-owned system-skill loading and installation."""


class SystemSkillCatalogError(SystemSkillError):
    """Raised when the packaged system-skill catalog is invalid."""


class SystemSkillInstallError(SystemSkillError):
    """Raised when system-skill installation cannot complete safely."""


class SystemSkillPolicyError(SystemSkillError):
    """Raised when a managed-launch system-skill policy is invalid."""


@dataclass(frozen=True)
class SystemSkillRecord:
    """One installable Houmao-owned system skill."""

    name: str
    asset_subpath: str
    description: str | None = None


@dataclass(frozen=True)
class SystemSkillSetRecord:
    """One named set of current Houmao-owned system skills."""

    name: str
    skill_names: tuple[str, ...]
    description: str | None = None


@dataclass(frozen=True)
class AutoInstallSelection:
    """Fixed internal and CLI-default set lists from the packaged catalog."""

    managed_launch_sets: tuple[str, ...]
    managed_join_sets: tuple[str, ...]
    cli_default_sets: tuple[str, ...]

    def set_names_for_kind(self, kind: AutoInstallKind) -> tuple[str, ...]:
        """Return the configured set list for one auto-install selection kind."""

        if kind == "managed_launch":
            return self.managed_launch_sets
        if kind == "managed_join":
            return self.managed_join_sets
        return self.cli_default_sets


@dataclass(frozen=True)
class SystemSkillCatalog:
    """Normalized packaged catalog for the current Houmao-owned system skills."""

    schema_version: int
    skills: dict[str, SystemSkillRecord]
    sets: dict[str, SystemSkillSetRecord]
    auto_install: AutoInstallSelection
    retired_skill_names: tuple[str, ...]

    @property
    def skill_names(self) -> tuple[str, ...]:
        """Return the catalog skill names in packaged order."""

        return tuple(self.skills.keys())


@dataclass(frozen=True)
class SystemSkillSelectionPolicy:
    """Stored managed-launch policy for Houmao-owned system skills."""

    mode: SystemSkillPolicyMode
    set_names: tuple[str, ...] = ()
    skill_names: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        """Return a JSON/YAML-safe representation of this policy."""

        payload: dict[str, object] = {"mode": self.mode}
        if self.set_names:
            payload["sets"] = list(self.set_names)
        if self.skill_names:
            payload["skills"] = list(self.skill_names)
        return payload


@dataclass(frozen=True)
class ResolvedManagedSystemSkillSelection:
    """Effective managed-launch system-skill selection after policy resolution."""

    selected_set_names: tuple[str, ...]
    explicit_skill_names: tuple[str, ...]
    resolved_skill_names: tuple[str, ...]
    source_policy: SystemSkillSelectionPolicy | None = None
    profile_policy: SystemSkillSelectionPolicy | None = None


@dataclass(frozen=True)
class SystemSkillInstallResult:
    """Outcome of one system-skill installation request."""

    tool: str
    home_path: Path
    selected_set_names: tuple[str, ...]
    explicit_skill_names: tuple[str, ...]
    resolved_skill_names: tuple[str, ...]
    projected_relative_dirs: tuple[str, ...]
    projection_mode: SystemSkillProjectionMode
    removed_retired_skill_names: tuple[str, ...] = ()
    removed_retired_projected_relative_dirs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SystemSkillSyncResult:
    """Outcome of syncing one managed home to an exact resolved selection."""

    tool: str
    home_path: Path
    selected_set_names: tuple[str, ...]
    explicit_skill_names: tuple[str, ...]
    resolved_skill_names: tuple[str, ...]
    projected_relative_dirs: tuple[str, ...]
    projection_mode: SystemSkillProjectionMode
    removed_skill_names: tuple[str, ...] = ()
    removed_projected_relative_dirs: tuple[str, ...] = ()
    removed_retired_skill_names: tuple[str, ...] = ()
    removed_retired_projected_relative_dirs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SystemSkillUninstallResult:
    """Outcome of one system-skill removal request."""

    tool: str
    home_path: Path
    removed_skill_names: tuple[str, ...]
    removed_projected_relative_dirs: tuple[str, ...]
    absent_skill_names: tuple[str, ...]
    absent_projected_relative_dirs: tuple[str, ...]
    removed_retired_skill_names: tuple[str, ...] = ()
    removed_retired_projected_relative_dirs: tuple[str, ...] = ()
    absent_retired_skill_names: tuple[str, ...] = ()
    absent_retired_projected_relative_dirs: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstalledSystemSkillStatusRecord:
    """One current packaged skill discovered in a live tool home."""

    name: str
    projected_relative_dir: str
    projection_mode: SystemSkillProjectionMode


@dataclass(frozen=True)
class RetiredSystemSkillStatusRecord:
    """One known retired Houmao-owned skill projection discovered in a tool home."""

    name: str
    projected_relative_dir: str
    projection_mode: SystemSkillProjectionMode


def system_skills_destination_for_tool(tool: str) -> str:
    """Return the visible skill destination root for one supported tool."""

    destination = _SYSTEM_SKILL_DESTINATION_BY_TOOL.get(tool)
    if destination is None:
        raise SystemSkillInstallError(f"Unsupported tool `{tool}` for system-skill projection.")
    return destination


def system_skill_reference_for_name(skill_name: str, *, tool: str | None = None) -> str:
    """Return the visible projected skill reference for one supported tool."""

    _system_skill_record_for_name(skill_name)
    if tool is not None:
        system_skills_destination_for_tool(tool)
    return skill_name


def projected_system_skill_relative_dir(*, tool: str, skill_name: str) -> str:
    """Return the home-relative directory path for one projected skill."""

    relative_path = Path(
        system_skills_destination_for_tool(tool)
    ) / system_skill_reference_for_name(skill_name, tool=tool)
    return str(relative_path)


def projected_retired_system_skill_relative_dir(*, tool: str, skill_name: str) -> str:
    """Return the home-relative directory path for one known retired skill projection."""

    _validate_retired_system_skill_name(skill_name)
    relative_path = Path(system_skills_destination_for_tool(tool)) / skill_name
    return str(relative_path)


def projected_system_skill_directory(
    *,
    tool: str,
    home_path: Path,
    skill_name: str,
) -> Path:
    """Return the installed directory path for one skill inside a tool home."""

    return home_path.resolve() / projected_system_skill_relative_dir(
        tool=tool, skill_name=skill_name
    )


@lru_cache(maxsize=1)
def load_system_skill_catalog() -> SystemSkillCatalog:
    """Load the packaged current-system-skill catalog."""

    package_root = resources.files(SYSTEM_SKILLS_PACKAGE)
    catalog_text = (package_root / SYSTEM_SKILL_CATALOG_FILENAME).read_text(encoding="utf-8")
    schema_text = (package_root / SYSTEM_SKILL_SCHEMA_FILENAME).read_text(encoding="utf-8")
    return _parse_system_skill_catalog(
        raw_catalog_text=catalog_text,
        raw_schema_text=schema_text,
        source=f"{SYSTEM_SKILLS_PACKAGE}:{SYSTEM_SKILL_CATALOG_FILENAME}",
    )


def load_system_skill_catalog_from_paths(
    *, catalog_path: Path, schema_path: Path
) -> SystemSkillCatalog:
    """Load one system-skill catalog from explicit filesystem paths."""

    return _parse_system_skill_catalog(
        raw_catalog_text=catalog_path.read_text(encoding="utf-8"),
        raw_schema_text=schema_path.read_text(encoding="utf-8"),
        source=str(catalog_path),
    )


def resolve_system_skill_selection(
    catalog: SystemSkillCatalog,
    *,
    set_names: tuple[str, ...] = (),
    skill_names: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Resolve explicit named sets and skill names into one ordered skill list."""

    resolved: list[str] = []
    seen: set[str] = set()
    for set_name in set_names:
        record = catalog.sets.get(set_name)
        if record is None:
            raise SystemSkillCatalogError(f"Unknown system-skill set `{set_name}`.")
        for skill_name in record.skill_names:
            if skill_name in seen:
                continue
            seen.add(skill_name)
            resolved.append(skill_name)

    for skill_name in skill_names:
        if skill_name not in catalog.skills:
            raise SystemSkillCatalogError(f"Unknown system skill `{skill_name}`.")
        if skill_name in seen:
            continue
        seen.add(skill_name)
        resolved.append(skill_name)

    return tuple(resolved)


def parse_system_skill_selection_policy(
    payload: object,
    *,
    allowed_modes: tuple[SystemSkillPolicyMode, ...],
    default_mode: SystemSkillPolicyMode,
    source: str,
    catalog: SystemSkillCatalog | None = None,
) -> SystemSkillSelectionPolicy | None:
    """Parse one stored managed-launch system-skill policy payload.

    Empty or omitted payloads return ``None`` so callers can apply source/profile
    omission semantics explicitly.
    """

    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise SystemSkillPolicyError(f"{source}: system_skills must be a mapping")
    if not payload:
        return None

    unknown_keys = sorted(set(payload) - {"mode", "sets", "skills"})
    if unknown_keys:
        raise SystemSkillPolicyError(
            f"{source}: system_skills has unknown field(s): {', '.join(unknown_keys)}"
        )

    raw_mode = payload.get("mode", default_mode)
    if not isinstance(raw_mode, str):
        raise SystemSkillPolicyError(f"{source}: system_skills.mode must be a string")
    if raw_mode not in {"default", "inherit", "extend", "replace", "none"}:
        raise SystemSkillPolicyError(f"{source}: unknown system-skills mode `{raw_mode}`")
    mode = cast(SystemSkillPolicyMode, raw_mode)

    policy = SystemSkillSelectionPolicy(
        mode=mode,
        set_names=_parse_system_skill_policy_string_sequence(
            payload.get("sets"), source=source, key="sets"
        ),
        skill_names=_parse_system_skill_policy_string_sequence(
            payload.get("skills"), source=source, key="skills"
        ),
    )
    validate_system_skill_selection_policy(
        policy,
        allowed_modes=allowed_modes,
        catalog=catalog,
        source=source,
    )
    return policy


def system_skill_selection_policy_to_payload(
    policy: SystemSkillSelectionPolicy | None,
) -> dict[str, object]:
    """Return a JSON/YAML-safe system-skill policy payload."""

    if policy is None:
        return {}
    return policy.to_payload()


def validate_system_skill_selection_policy(
    policy: SystemSkillSelectionPolicy,
    *,
    allowed_modes: tuple[SystemSkillPolicyMode, ...],
    catalog: SystemSkillCatalog | None = None,
    source: str,
) -> None:
    """Validate policy mode and selectors against the packaged catalog."""

    if policy.mode not in allowed_modes:
        allowed = "|".join(allowed_modes)
        raise SystemSkillPolicyError(
            f"{source}: system-skills mode `{policy.mode}` is not allowed here; "
            f"expected one of {allowed}"
        )
    if policy.mode in {"default", "inherit", "none"} and (policy.set_names or policy.skill_names):
        raise SystemSkillPolicyError(
            f"{source}: system-skills mode `{policy.mode}` cannot be combined with "
            "explicit set or skill selectors"
        )
    if policy.mode == "replace" and not policy.set_names and not policy.skill_names:
        raise SystemSkillPolicyError(
            f"{source}: system-skills mode `replace` requires at least one set or skill "
            "selector; use `none` to disable system skills"
        )

    effective_catalog = catalog or load_system_skill_catalog()
    resolve_system_skill_selection(
        effective_catalog,
        set_names=policy.set_names,
        skill_names=policy.skill_names,
    )


def resolve_managed_system_skill_selection(
    *,
    source_policy: SystemSkillSelectionPolicy | None = None,
    profile_policy: SystemSkillSelectionPolicy | None = None,
    catalog: SystemSkillCatalog | None = None,
) -> ResolvedManagedSystemSkillSelection:
    """Resolve source and profile policy into one exact managed-launch selection."""

    effective_catalog = catalog or load_system_skill_catalog()
    if source_policy is not None:
        validate_system_skill_selection_policy(
            source_policy,
            allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
            catalog=effective_catalog,
            source="source system_skills",
        )
    if profile_policy is not None:
        validate_system_skill_selection_policy(
            profile_policy,
            allowed_modes=PROFILE_SYSTEM_SKILL_POLICY_MODES,
            catalog=effective_catalog,
            source="profile system_skills",
        )

    source_selection = _resolve_source_system_skill_selection(
        catalog=effective_catalog,
        source_policy=source_policy,
    )
    if profile_policy is None or profile_policy.mode == "inherit":
        return ResolvedManagedSystemSkillSelection(
            selected_set_names=source_selection.selected_set_names,
            explicit_skill_names=source_selection.explicit_skill_names,
            resolved_skill_names=source_selection.resolved_skill_names,
            source_policy=source_policy,
            profile_policy=profile_policy,
        )
    if profile_policy.mode == "none":
        return ResolvedManagedSystemSkillSelection(
            selected_set_names=(),
            explicit_skill_names=(),
            resolved_skill_names=(),
            source_policy=source_policy,
            profile_policy=profile_policy,
        )
    if profile_policy.mode == "replace":
        return _build_resolved_managed_system_skill_selection(
            catalog=effective_catalog,
            set_names=profile_policy.set_names,
            skill_names=profile_policy.skill_names,
            source_policy=source_policy,
            profile_policy=profile_policy,
        )

    selected_set_names = _dedupe_strings(
        (*source_selection.selected_set_names, *profile_policy.set_names)
    )
    explicit_skill_names = _dedupe_strings(
        (*source_selection.explicit_skill_names, *profile_policy.skill_names)
    )
    return _build_resolved_managed_system_skill_selection(
        catalog=effective_catalog,
        set_names=selected_set_names,
        skill_names=explicit_skill_names,
        source_policy=source_policy,
        profile_policy=profile_policy,
    )


def resolve_auto_install_skill_selection(
    catalog: SystemSkillCatalog,
    *,
    kind: AutoInstallKind,
) -> tuple[str, ...]:
    """Resolve one fixed auto-install selection from the packaged catalog."""

    return resolve_system_skill_selection(
        catalog,
        set_names=catalog.auto_install.set_names_for_kind(kind),
    )


def project_system_skills_to_destination(
    destination_root: Path,
    *,
    tool: str | None = None,
    skill_names: tuple[str, ...],
    projection_mode: SystemSkillProjectionMode = "copy",
) -> tuple[str, ...]:
    """Project packaged system-skill trees into one visible skill destination."""

    catalog = load_system_skill_catalog()
    resolved_skill_names = resolve_system_skill_selection(catalog, skill_names=skill_names)
    if not resolved_skill_names:
        raise SystemSkillInstallError("At least one system skill must be selected for projection.")

    resolved_destination_root = destination_root.resolve()
    resolved_destination_root.mkdir(parents=True, exist_ok=True)
    for retired_skill_name in catalog.retired_skill_names:
        _remove_existing_path_if_present(resolved_destination_root / retired_skill_name)
    for skill_name in resolved_skill_names:
        skill_record = catalog.skills[skill_name]
        target_dir = resolved_destination_root / skill_name
        _remove_existing_path_if_present(target_dir)
        _project_packaged_skill(
            asset_subpath=skill_record.asset_subpath,
            destination_root=target_dir,
            projection_mode=projection_mode,
        )

    return tuple(
        system_skill_reference_for_name(skill_name, tool=tool)
        for skill_name in resolved_skill_names
    )


def discover_installed_system_skills(
    *,
    tool: str,
    home_path: Path,
) -> tuple[InstalledSystemSkillStatusRecord, ...]:
    """Return current packaged skills discovered in one concrete tool home."""

    catalog = load_system_skill_catalog()
    resolved_home_path = home_path.resolve()
    discovered: list[InstalledSystemSkillStatusRecord] = []
    for skill_name in catalog.skill_names:
        projected_relative_dir = projected_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        target_dir = resolved_home_path / projected_relative_dir
        if target_dir.is_symlink():
            discovered.append(
                InstalledSystemSkillStatusRecord(
                    name=skill_name,
                    projected_relative_dir=projected_relative_dir,
                    projection_mode="symlink",
                )
            )
            continue
        if not target_dir.is_dir():
            continue
        discovered.append(
            InstalledSystemSkillStatusRecord(
                name=skill_name,
                projected_relative_dir=projected_relative_dir,
                projection_mode="copy",
            )
        )
    return tuple(discovered)


def discover_retired_system_skill_projections(
    *,
    tool: str,
    home_path: Path,
) -> tuple[RetiredSystemSkillStatusRecord, ...]:
    """Return known retired Houmao-owned projections discovered in one tool home."""

    catalog = load_system_skill_catalog()
    resolved_home_path = home_path.resolve()
    discovered: list[RetiredSystemSkillStatusRecord] = []
    for skill_name in catalog.retired_skill_names:
        projected_relative_dir = projected_retired_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        target_dir = resolved_home_path / projected_relative_dir
        if target_dir.is_symlink():
            discovered.append(
                RetiredSystemSkillStatusRecord(
                    name=skill_name,
                    projected_relative_dir=projected_relative_dir,
                    projection_mode="symlink",
                )
            )
            continue
        if not target_dir.is_dir():
            continue
        discovered.append(
            RetiredSystemSkillStatusRecord(
                name=skill_name,
                projected_relative_dir=projected_relative_dir,
                projection_mode="copy",
            )
        )
    return tuple(discovered)


def install_system_skills_for_home(
    *,
    tool: str,
    home_path: Path,
    set_names: tuple[str, ...] = (),
    skill_names: tuple[str, ...] = (),
    use_cli_default: bool = False,
    auto_install_kind: AutoInstallKind | None = None,
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillInstallResult:
    """Install selected Houmao-owned system skills into one target tool home."""

    if auto_install_kind is not None and use_cli_default:
        raise SystemSkillInstallError(
            "CLI default selection and auto-install selection are mutually exclusive."
        )
    _validate_projection_mode(projection_mode)

    catalog = load_system_skill_catalog()
    selected_set_names = _resolve_requested_set_names(
        catalog,
        explicit_set_names=set_names,
        use_cli_default=use_cli_default,
        auto_install_kind=auto_install_kind,
    )
    resolved_skill_names = resolve_system_skill_selection(
        catalog,
        set_names=selected_set_names,
        skill_names=skill_names,
    )
    if not resolved_skill_names:
        raise SystemSkillInstallError(
            "At least one system skill must be selected for installation."
        )

    resolved_home_path = home_path.resolve()
    resolved_home_path.mkdir(parents=True, exist_ok=True)
    removed_retired_skill_names, removed_retired_projected_relative_dirs = (
        _remove_retired_system_skill_projections_for_home(
            catalog=catalog,
            tool=tool,
            home_path=resolved_home_path,
        )
    )
    projected_relative_dirs: list[str] = []
    for skill_name in resolved_skill_names:
        skill_record = catalog.skills[skill_name]
        projected_relative_dir = projected_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        projected_relative_dirs.append(projected_relative_dir)
        target_path = resolved_home_path / projected_relative_dir
        _remove_existing_path_if_present(target_path)
        _project_packaged_skill(
            asset_subpath=skill_record.asset_subpath,
            destination_root=target_path,
            projection_mode=projection_mode,
        )

    return SystemSkillInstallResult(
        tool=tool,
        home_path=resolved_home_path,
        selected_set_names=selected_set_names,
        explicit_skill_names=skill_names,
        resolved_skill_names=resolved_skill_names,
        projected_relative_dirs=tuple(projected_relative_dirs),
        projection_mode=projection_mode,
        removed_retired_skill_names=removed_retired_skill_names,
        removed_retired_projected_relative_dirs=removed_retired_projected_relative_dirs,
    )


def sync_system_skills_for_home(
    *,
    tool: str,
    home_path: Path,
    selection: ResolvedManagedSystemSkillSelection,
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillSyncResult:
    """Sync one managed home to an exact resolved system-skill selection."""

    _validate_projection_mode(projection_mode)
    catalog = load_system_skill_catalog()
    resolved_skill_names = resolve_system_skill_selection(
        catalog,
        set_names=selection.selected_set_names,
        skill_names=selection.explicit_skill_names,
    )
    if resolved_skill_names != selection.resolved_skill_names:
        raise SystemSkillPolicyError(
            "Resolved managed system-skill selection does not match its selectors."
        )

    resolved_home_path = home_path.resolve()
    resolved_home_path.mkdir(parents=True, exist_ok=True)
    resolved_skill_name_set = set(selection.resolved_skill_names)
    removed_skill_names: list[str] = []
    removed_projected_relative_dirs: list[str] = []
    for skill_name in catalog.skill_names:
        if skill_name in resolved_skill_name_set:
            continue
        projected_relative_dir = projected_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        target_path = resolved_home_path / projected_relative_dir
        if not target_path.exists() and not target_path.is_symlink():
            continue
        _remove_existing_path_if_present(target_path)
        removed_skill_names.append(skill_name)
        removed_projected_relative_dirs.append(projected_relative_dir)

    removed_retired_skill_names, removed_retired_projected_relative_dirs = (
        _remove_retired_system_skill_projections_for_home(
            catalog=catalog,
            tool=tool,
            home_path=resolved_home_path,
        )
    )

    projected_relative_dirs: list[str] = []
    for skill_name in selection.resolved_skill_names:
        skill_record = catalog.skills[skill_name]
        projected_relative_dir = projected_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        projected_relative_dirs.append(projected_relative_dir)
        target_path = resolved_home_path / projected_relative_dir
        _remove_existing_path_if_present(target_path)
        _project_packaged_skill(
            asset_subpath=skill_record.asset_subpath,
            destination_root=target_path,
            projection_mode=projection_mode,
        )

    return SystemSkillSyncResult(
        tool=tool,
        home_path=resolved_home_path,
        selected_set_names=selection.selected_set_names,
        explicit_skill_names=selection.explicit_skill_names,
        resolved_skill_names=selection.resolved_skill_names,
        projected_relative_dirs=tuple(projected_relative_dirs),
        projection_mode=projection_mode,
        removed_skill_names=tuple(removed_skill_names),
        removed_projected_relative_dirs=tuple(removed_projected_relative_dirs),
        removed_retired_skill_names=removed_retired_skill_names,
        removed_retired_projected_relative_dirs=removed_retired_projected_relative_dirs,
    )


def uninstall_system_skills_for_home(
    *,
    tool: str,
    home_path: Path,
) -> SystemSkillUninstallResult:
    """Remove all current Houmao-owned system skills from one target tool home."""

    catalog = load_system_skill_catalog()
    resolved_home_path = home_path.resolve()
    removed_skill_names: list[str] = []
    removed_projected_relative_dirs: list[str] = []
    absent_skill_names: list[str] = []
    absent_projected_relative_dirs: list[str] = []
    removed_retired_skill_names: list[str] = []
    removed_retired_projected_relative_dirs: list[str] = []
    absent_retired_skill_names: list[str] = []
    absent_retired_projected_relative_dirs: list[str] = []

    for skill_name in catalog.skill_names:
        projected_relative_dir = projected_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        target_path = resolved_home_path / projected_relative_dir
        if not target_path.exists() and not target_path.is_symlink():
            absent_skill_names.append(skill_name)
            absent_projected_relative_dirs.append(projected_relative_dir)
            continue

        _remove_existing_path_if_present(target_path)
        removed_skill_names.append(skill_name)
        removed_projected_relative_dirs.append(projected_relative_dir)

    for skill_name in catalog.retired_skill_names:
        projected_relative_dir = projected_retired_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        target_path = resolved_home_path / projected_relative_dir
        if not target_path.exists() and not target_path.is_symlink():
            absent_retired_skill_names.append(skill_name)
            absent_retired_projected_relative_dirs.append(projected_relative_dir)
            continue

        _remove_existing_path_if_present(target_path)
        removed_retired_skill_names.append(skill_name)
        removed_retired_projected_relative_dirs.append(projected_relative_dir)

    return SystemSkillUninstallResult(
        tool=tool,
        home_path=resolved_home_path,
        removed_skill_names=tuple(removed_skill_names),
        removed_projected_relative_dirs=tuple(removed_projected_relative_dirs),
        absent_skill_names=tuple(absent_skill_names),
        absent_projected_relative_dirs=tuple(absent_projected_relative_dirs),
        removed_retired_skill_names=tuple(removed_retired_skill_names),
        removed_retired_projected_relative_dirs=tuple(removed_retired_projected_relative_dirs),
        absent_retired_skill_names=tuple(absent_retired_skill_names),
        absent_retired_projected_relative_dirs=tuple(absent_retired_projected_relative_dirs),
    )


def _resolve_source_system_skill_selection(
    *,
    catalog: SystemSkillCatalog,
    source_policy: SystemSkillSelectionPolicy | None,
) -> ResolvedManagedSystemSkillSelection:
    """Resolve the recipe/specialist side of a managed-launch policy."""

    if source_policy is None or source_policy.mode == "default":
        return _build_resolved_managed_system_skill_selection(
            catalog=catalog,
            set_names=catalog.auto_install.managed_launch_sets,
            skill_names=(),
            source_policy=source_policy,
            profile_policy=None,
        )
    if source_policy.mode == "none":
        return ResolvedManagedSystemSkillSelection(
            selected_set_names=(),
            explicit_skill_names=(),
            resolved_skill_names=(),
            source_policy=source_policy,
            profile_policy=None,
        )
    if source_policy.mode == "replace":
        return _build_resolved_managed_system_skill_selection(
            catalog=catalog,
            set_names=source_policy.set_names,
            skill_names=source_policy.skill_names,
            source_policy=source_policy,
            profile_policy=None,
        )

    selected_set_names = _dedupe_strings(
        (*catalog.auto_install.managed_launch_sets, *source_policy.set_names)
    )
    return _build_resolved_managed_system_skill_selection(
        catalog=catalog,
        set_names=selected_set_names,
        skill_names=source_policy.skill_names,
        source_policy=source_policy,
        profile_policy=None,
    )


def _build_resolved_managed_system_skill_selection(
    *,
    catalog: SystemSkillCatalog,
    set_names: tuple[str, ...],
    skill_names: tuple[str, ...],
    source_policy: SystemSkillSelectionPolicy | None,
    profile_policy: SystemSkillSelectionPolicy | None,
) -> ResolvedManagedSystemSkillSelection:
    """Build one resolved managed selection from already chosen selectors."""

    selected_set_names = _dedupe_strings(set_names)
    explicit_skill_names = _dedupe_strings(skill_names)
    return ResolvedManagedSystemSkillSelection(
        selected_set_names=selected_set_names,
        explicit_skill_names=explicit_skill_names,
        resolved_skill_names=resolve_system_skill_selection(
            catalog,
            set_names=selected_set_names,
            skill_names=explicit_skill_names,
        ),
        source_policy=source_policy,
        profile_policy=profile_policy,
    )


def _parse_system_skill_policy_string_sequence(
    value: object,
    *,
    source: str,
    key: str,
) -> tuple[str, ...]:
    """Parse a policy string-list field and preserve first-seen order."""

    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SystemSkillPolicyError(f"{source}: system_skills.{key} must be a list of strings")

    values: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise SystemSkillPolicyError(
                f"{source}: system_skills.{key}[{index}] must be a non-empty string"
            )
        values.append(item)
    return _dedupe_strings(tuple(values))


def _dedupe_strings(values: tuple[str, ...]) -> tuple[str, ...]:
    """Return values in first-seen order with duplicates removed."""

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)


def _parse_system_skill_catalog(
    *,
    raw_catalog_text: str,
    raw_schema_text: str,
    source: str,
) -> SystemSkillCatalog:
    """Parse, normalize, schema-validate, and materialize one catalog payload."""

    try:
        raw_catalog_payload = tomllib.loads(raw_catalog_text)
    except tomllib.TOMLDecodeError as exc:
        raise SystemSkillCatalogError(
            f"Invalid system-skill catalog TOML at {source}: {exc}"
        ) from exc
    if not isinstance(raw_catalog_payload, dict):
        raise SystemSkillCatalogError(
            f"Invalid system-skill catalog at {source}: expected top-level mapping"
        )

    try:
        raw_schema_payload = json.loads(raw_schema_text)
    except json.JSONDecodeError as exc:
        raise SystemSkillCatalogError(
            f"Invalid system-skill schema JSON for {source}: {exc}"
        ) from exc
    if not isinstance(raw_schema_payload, dict):
        raise SystemSkillCatalogError(f"Invalid system-skill schema for {source}: expected object")

    normalized_payload = _normalize_catalog_payload(raw_catalog_payload, source=source)
    _validate_schema_payload(normalized_payload, raw_schema_payload, path="$")
    _validate_catalog_cross_references(normalized_payload, source=source)
    return _build_catalog_from_normalized_payload(normalized_payload)


def _normalize_catalog_payload(
    raw_payload: dict[str, object],
    *,
    source: str,
) -> dict[str, Any]:
    """Normalize one raw TOML mapping into the schema-validated payload shape."""

    skills_mapping = _require_mapping(raw_payload, "skills", source=source)
    normalized_skills: list[dict[str, Any]] = []
    for name, raw_skill in skills_mapping.items():
        if not isinstance(name, str):
            raise SystemSkillCatalogError(f"{source}: skill names must be strings")
        if not isinstance(raw_skill, dict):
            raise SystemSkillCatalogError(f"{source}: skills.{name} must be a mapping")
        normalized_skill: dict[str, Any] = {
            "name": name,
            "asset_subpath": raw_skill.get("asset_subpath"),
        }
        if raw_skill.get("description") is not None:
            normalized_skill["description"] = raw_skill.get("description")
        normalized_skills.append(normalized_skill)

    sets_mapping = _require_mapping(raw_payload, "sets", source=source)
    normalized_sets: list[dict[str, Any]] = []
    for name, raw_set in sets_mapping.items():
        if not isinstance(name, str):
            raise SystemSkillCatalogError(f"{source}: set names must be strings")
        if not isinstance(raw_set, dict):
            raise SystemSkillCatalogError(f"{source}: sets.{name} must be a mapping")
        normalized_set: dict[str, Any] = {
            "name": name,
            "skills": raw_set.get("skills"),
        }
        if raw_set.get("description") is not None:
            normalized_set["description"] = raw_set.get("description")
        normalized_sets.append(normalized_set)

    auto_install_mapping = _require_mapping(raw_payload, "auto_install", source=source)
    return {
        "schema_version": raw_payload.get("schema_version"),
        "skills": normalized_skills,
        "retired_skill_names": raw_payload.get("retired_skill_names", []),
        "sets": normalized_sets,
        "auto_install": {
            "managed_launch_sets": auto_install_mapping.get("managed_launch_sets"),
            "managed_join_sets": auto_install_mapping.get("managed_join_sets"),
            "cli_default_sets": auto_install_mapping.get("cli_default_sets"),
        },
    }


def _build_catalog_from_normalized_payload(payload: dict[str, Any]) -> SystemSkillCatalog:
    """Materialize one validated normalized payload into dataclasses."""

    skills: dict[str, SystemSkillRecord] = {}
    for raw_skill in payload["skills"]:
        skill = SystemSkillRecord(
            name=raw_skill["name"],
            asset_subpath=raw_skill["asset_subpath"],
            description=raw_skill.get("description"),
        )
        skills[skill.name] = skill

    sets: dict[str, SystemSkillSetRecord] = {}
    for raw_set in payload["sets"]:
        record = SystemSkillSetRecord(
            name=raw_set["name"],
            skill_names=tuple(raw_set["skills"]),
            description=raw_set.get("description"),
        )
        sets[record.name] = record

    raw_auto_install = payload["auto_install"]
    return SystemSkillCatalog(
        schema_version=payload["schema_version"],
        skills=skills,
        sets=sets,
        auto_install=AutoInstallSelection(
            managed_launch_sets=tuple(raw_auto_install["managed_launch_sets"]),
            managed_join_sets=tuple(raw_auto_install["managed_join_sets"]),
            cli_default_sets=tuple(raw_auto_install["cli_default_sets"]),
        ),
        retired_skill_names=tuple(payload["retired_skill_names"]),
    )


def _validate_catalog_cross_references(payload: dict[str, Any], *, source: str) -> None:
    """Reject unknown set and auto-install references after schema validation."""

    known_skill_names = {record["name"] for record in payload["skills"]}
    retired_skill_names = payload["retired_skill_names"]
    duplicate_retired_names = sorted(
        name for name in set(retired_skill_names) if retired_skill_names.count(name) > 1
    )
    if duplicate_retired_names:
        raise SystemSkillCatalogError(
            f"{source}: retired_skill_names contains duplicate skill name(s): "
            f"{', '.join(duplicate_retired_names)}"
        )
    current_retired_overlap = known_skill_names.intersection(retired_skill_names)
    if current_retired_overlap:
        names = ", ".join(sorted(current_retired_overlap))
        raise SystemSkillCatalogError(
            f"{source}: skill name(s) cannot be both current and retired: {names}"
        )
    for raw_set in payload["sets"]:
        for skill_name in raw_set["skills"]:
            if skill_name not in known_skill_names:
                raise SystemSkillCatalogError(
                    f"{source}: set `{raw_set['name']}` references unknown system skill `{skill_name}`"
                )

    known_set_names = {record["name"] for record in payload["sets"]}
    raw_auto_install = payload["auto_install"]
    for key in ("managed_launch_sets", "managed_join_sets", "cli_default_sets"):
        for set_name in raw_auto_install[key]:
            if set_name not in known_set_names:
                raise SystemSkillCatalogError(
                    f"{source}: auto_install.{key} references unknown set `{set_name}`"
                )


def _validate_schema_payload(value: Any, schema: dict[str, Any], *, path: str) -> None:
    """Validate one payload node against one JSON Schema node."""

    if "const" in schema and value != schema["const"]:
        raise SystemSkillCatalogError(f"{path}: expected const value {schema['const']!r}")

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        raise SystemSkillCatalogError(f"{path}: expected one of {enum!r}, got {value!r}")

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_schema_type(value, expected_type):
        raise SystemSkillCatalogError(
            f"{path}: expected type {expected_type!r}, got {type(value).__name__}"
        )

    if isinstance(value, dict):
        _validate_schema_object(value, schema, path=path)
    elif isinstance(value, list):
        _validate_schema_array(value, schema, path=path)
    elif isinstance(value, str):
        _validate_schema_string(value, schema, path=path)


def _validate_schema_object(value: dict[str, Any], schema: dict[str, Any], *, path: str) -> None:
    """Validate one object node against one JSON Schema object schema."""

    required = schema.get("required", [])
    if isinstance(required, list):
        for key in required:
            if key not in value:
                raise SystemSkillCatalogError(f"{path}: missing required field `{key}`")

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return

    additional_properties = schema.get("additionalProperties", True)
    if additional_properties is False:
        unknown = sorted(set(value.keys()) - set(properties.keys()))
        if unknown:
            raise SystemSkillCatalogError(f"{path}: unknown field(s): {', '.join(unknown)}")

    for key, property_schema in properties.items():
        if key not in value:
            continue
        if not isinstance(property_schema, dict):
            raise SystemSkillCatalogError(f"{path}.{key}: schema property must be an object")
        _validate_schema_payload(value[key], property_schema, path=f"{path}.{key}")


def _validate_schema_array(value: list[Any], schema: dict[str, Any], *, path: str) -> None:
    """Validate one array node against one JSON Schema array schema."""

    min_items = schema.get("minItems")
    if isinstance(min_items, int) and len(value) < min_items:
        raise SystemSkillCatalogError(
            f"{path}: expected at least {min_items} item(s), got {len(value)}"
        )

    items = schema.get("items")
    if not isinstance(items, dict):
        return
    for index, item in enumerate(value):
        _validate_schema_payload(item, items, path=f"{path}[{index}]")


def _validate_schema_string(value: str, schema: dict[str, Any], *, path: str) -> None:
    """Validate one string node against one JSON Schema string schema."""

    pattern = schema.get("pattern")
    if isinstance(pattern, str):
        import re

        if re.search(pattern, value) is None:
            raise SystemSkillCatalogError(f"{path}: value does not match pattern {pattern!r}")


def _matches_schema_type(value: Any, expected_type: str | list[str]) -> bool:
    """Return whether one payload value matches the requested JSON Schema type."""

    if isinstance(expected_type, list):
        return any(_matches_schema_type(value, item) for item in expected_type)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    if expected_type == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
    return False


def _system_skill_record_for_name(skill_name: str) -> SystemSkillRecord:
    """Return one packaged system-skill record by name."""

    catalog = load_system_skill_catalog()
    record = catalog.skills.get(skill_name)
    if record is None:
        raise SystemSkillCatalogError(f"Unknown system skill `{skill_name}`.")
    return record


def _validate_retired_system_skill_name(skill_name: str) -> None:
    """Reject names that are not known retired Houmao-owned skill projections."""

    catalog = load_system_skill_catalog()
    if skill_name not in catalog.retired_skill_names:
        raise SystemSkillCatalogError(f"Unknown retired system skill `{skill_name}`.")


def _remove_retired_system_skill_projections_for_home(
    *,
    catalog: SystemSkillCatalog,
    tool: str,
    home_path: Path,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Remove known retired Houmao-owned projections from one concrete tool home."""

    removed_skill_names: list[str] = []
    removed_projected_relative_dirs: list[str] = []
    for skill_name in catalog.retired_skill_names:
        projected_relative_dir = projected_retired_system_skill_relative_dir(
            tool=tool,
            skill_name=skill_name,
        )
        target_path = home_path / projected_relative_dir
        if not target_path.exists() and not target_path.is_symlink():
            continue
        _remove_existing_path_if_present(target_path)
        removed_skill_names.append(skill_name)
        removed_projected_relative_dirs.append(projected_relative_dir)
    return tuple(removed_skill_names), tuple(removed_projected_relative_dirs)


def _resolve_requested_set_names(
    catalog: SystemSkillCatalog,
    *,
    explicit_set_names: tuple[str, ...],
    use_cli_default: bool,
    auto_install_kind: AutoInstallKind | None,
) -> tuple[str, ...]:
    """Resolve the effective ordered set names for one install request."""

    resolved: list[str] = []
    if use_cli_default:
        resolved.extend(catalog.auto_install.cli_default_sets)
    if auto_install_kind is not None:
        resolved.extend(catalog.auto_install.set_names_for_kind(auto_install_kind))
    resolved.extend(explicit_set_names)
    return tuple(resolved)


def replaceable_system_skill_relative_dirs(
    *,
    tool: str,
    skill_name: str,
) -> tuple[str, ...]:
    """Return the exact current relative dir replaceable for one skill."""

    _system_skill_record_for_name(skill_name)
    return (projected_system_skill_relative_dir(tool=tool, skill_name=skill_name),)


def _packaged_skill_root(asset_subpath: str) -> Traversable:
    """Return one packaged resource root for the requested asset subpath."""

    current: Traversable = resources.files(SYSTEM_SKILLS_PACKAGE)
    for part in Path(asset_subpath).parts:
        current = current / part
    if not current.is_dir():
        raise SystemSkillInstallError(
            f"Packaged system-skill asset path `{asset_subpath}` is missing or not a directory."
        )
    return current


@lru_cache(maxsize=1)
def _system_skills_package_directory() -> Path:
    """Return the filesystem directory for the packaged system-skill asset root."""

    package_module = import_module(SYSTEM_SKILLS_PACKAGE)
    module_file = getattr(package_module, "__file__", None)
    if not isinstance(module_file, str) or not module_file.strip():
        raise SystemSkillInstallError(
            f"Packaged system-skill assets for `{SYSTEM_SKILLS_PACKAGE}` are not filesystem-backed."
        )
    package_dir = Path(module_file).resolve().parent
    if not package_dir.is_dir():
        raise SystemSkillInstallError(
            f"Packaged system-skill asset root `{package_dir}` is not a directory."
        )
    return package_dir


@lru_cache(maxsize=None)
def _packaged_skill_filesystem_root(asset_subpath: str) -> Path:
    """Return one filesystem-backed packaged skill root for symlink projection."""

    skill_root = _system_skills_package_directory().joinpath(*Path(asset_subpath).parts)
    if not skill_root.is_dir():
        raise SystemSkillInstallError(
            f"Packaged system-skill asset path `{asset_subpath}` is missing or not a directory."
        )
    return skill_root


def _copy_resource_tree(source_root: Traversable, destination_root: Path) -> None:
    """Copy one packaged resource tree into a filesystem destination."""

    for child in source_root.iterdir():
        destination_path = destination_root / child.name
        if child.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            _copy_resource_tree(child, destination_path)
            continue

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with child.open("rb") as source_handle:
            destination_path.write_bytes(source_handle.read())


def _project_packaged_skill(
    *,
    asset_subpath: str,
    destination_root: Path,
    projection_mode: SystemSkillProjectionMode,
) -> None:
    """Project one packaged skill using the requested filesystem mode."""

    _validate_projection_mode(projection_mode)
    destination_root.parent.mkdir(parents=True, exist_ok=True)
    if projection_mode == "copy":
        _copy_resource_tree(_packaged_skill_root(asset_subpath), destination_root)
        return
    destination_root.symlink_to(_packaged_skill_filesystem_root(asset_subpath))


def _validate_projection_mode(projection_mode: str) -> None:
    """Reject unsupported system-skill projection modes."""

    if projection_mode not in {"copy", "symlink"}:
        raise SystemSkillInstallError(
            f"Unsupported system-skill projection mode `{projection_mode}`."
        )


def _remove_existing_path_if_present(path: Path) -> None:
    """Remove one existing filesystem path when it already exists."""

    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()


def _require_mapping(payload: dict[str, object], key: str, *, source: str) -> dict[str, object]:
    """Return one required mapping value from a raw payload."""

    value = payload.get(key)
    if not isinstance(value, dict):
        raise SystemSkillCatalogError(f"{source}: `{key}` must be a mapping")
    return value
