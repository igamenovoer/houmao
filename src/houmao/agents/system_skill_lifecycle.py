"""Transactional lifecycle and shared ownership for static Houmao system skills."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from importlib import metadata, resources
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Literal, cast

from houmao.agents.system_skill_manifest import (
    ActivationPosture,
    AutoInstallKind,
    EXPECTED_SHARED_ROUTINE_IDS,
    PackAudience,
    StandaloneSkillRole,
    SystemSkillManifest,
    SystemSkillManifestError,
    load_legacy_system_skill_catalog,
    load_system_skill_manifest,
    resolve_system_skill_pack_members,
    resolve_system_skill_pack_selection,
    stage_system_skill_collection,
    standalone_system_skill_content_digest,
    standalone_system_skill_source_path,
    tree_content_digest,
)


SYSTEM_SKILL_CONFIG_SCHEMA_VERSION = "houmao-skill-config.v1"
SYSTEM_SKILL_CONFIG_FILENAME = "houmao-skill-config.json"
SystemSkillProjectionMode = Literal["copy", "symlink"]
ConfigInspectionStatus = Literal[
    "absent",
    "current",
    "corrupt",
    "unsupported",
]
MemberIntegrityStatus = Literal["absent", "complete", "incomplete", "drifted", "conflicting"]
PackIntegrityStatus = Literal["absent", "complete", "incomplete", "drifted", "conflicting"]
LegacyPathClassification = Literal["package-linked", "digest-matched", "modified", "unknown"]
LegacyOverallStatus = Literal["absent", "complete", "partial", "conflicting"]

_SYSTEM_SKILL_DESTINATION_BY_TOOL: dict[str, str] = {
    "claude": "skills",
    "codex": "skills",
    "copilot": "skills",
    "kimi": "skills",
    "universal": "skills",
}


class SystemSkillInstallError(RuntimeError):
    """Raised when a static skill lifecycle transaction cannot complete safely."""


@dataclass(frozen=True)
class SystemSkillConfigSkillRecord:
    """Minimal ownership evidence for one standalone projection."""

    name: str
    relative_path: str
    content_digest: str
    owning_pack_ids: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe record payload."""

        return {
            "name": self.name,
            "relative_path": self.relative_path,
            "content_digest": self.content_digest,
            "owning_pack_ids": list(self.owning_pack_ids),
        }


@dataclass(frozen=True)
class SystemSkillConfig:
    """Tool-scoped ownership config for one static system-skill collection."""

    schema_version: str
    houmao_version: str
    tool: str
    home_path: Path
    projection_mode: SystemSkillProjectionMode
    skills: tuple[SystemSkillConfigSkillRecord, ...]

    @property
    def path(self) -> Path:
        """Return the canonical config path."""

        return system_skill_config_path(tool=self.tool, home_path=self.home_path)

    @property
    def selected_pack_ids(self) -> tuple[str, ...]:
        """Return installed packs derived from member owner sets."""

        manifest = load_system_skill_manifest()
        owner_ids = {owner_id for record in self.skills for owner_id in record.owning_pack_ids}
        return tuple(pack_id for pack_id in manifest.pack_ids if pack_id in owner_ids)

    def skill_map(self) -> dict[str, SystemSkillConfigSkillRecord]:
        """Return config records keyed by standalone name."""

        return {record.name: record for record in self.skills}

    def to_payload(self) -> dict[str, object]:
        """Return the complete minimal JSON-safe config payload."""

        return {
            "schema_version": self.schema_version,
            "houmao_version": self.houmao_version,
            "projection_mode": self.projection_mode,
            "skills": [record.to_payload() for record in self.skills],
        }


@dataclass(frozen=True)
class SystemSkillConfigInspection:
    """Read-only config parse result suitable for status output."""

    status: ConfigInspectionStatus
    path: Path
    config: SystemSkillConfig | None
    message: str | None = None


@dataclass(frozen=True)
class SystemSkillMemberStatusRecord:
    """Observed integrity and ownership for one standalone skill."""

    name: str
    role: StandaloneSkillRole
    activation: ActivationPosture
    status: MemberIntegrityStatus
    relative_path: str
    owning_pack_ids: tuple[str, ...]
    projection_mode: SystemSkillProjectionMode | None
    expected_content_digest: str | None


@dataclass(frozen=True)
class SystemSkillPackStatusRecord:
    """Observed aggregate integrity state for one actor pack."""

    pack_id: str
    audience: PackAudience
    status: PackIntegrityStatus
    standalone_skill_names: tuple[str, ...]
    standalone_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    drifted_paths: tuple[str, ...]
    conflicting_paths: tuple[str, ...]


@dataclass(frozen=True)
class LegacySystemSkillPathStatus:
    """One observed legacy flat path and its migration classification."""

    name: str
    relative_path: str
    classification: LegacyPathClassification
    content_digest: str | None = None
    link_target: str | None = None


@dataclass(frozen=True)
class LegacySystemSkillInspection:
    """Aggregate conservative legacy-flat inspection result."""

    status: LegacyOverallStatus
    paths: tuple[LegacySystemSkillPathStatus, ...]


@dataclass(frozen=True)
class SystemSkillStatusResult:
    """Config, member, pack, and legacy evidence for one tool home."""

    tool: str
    home_path: Path
    config: SystemSkillConfigInspection
    members: tuple[SystemSkillMemberStatusRecord, ...]
    packs: tuple[SystemSkillPackStatusRecord, ...]
    legacy: LegacySystemSkillInspection


@dataclass(frozen=True)
class SystemSkillInstallResult:
    """Outcome of installing or synchronizing a static collection."""

    tool: str
    home_path: Path
    selected_pack_ids: tuple[str, ...]
    standalone_skill_names: tuple[str, ...]
    projected_relative_dirs: tuple[str, ...]
    config_path: Path
    projection_mode: SystemSkillProjectionMode
    owning_pack_ids_by_skill: dict[str, tuple[str, ...]]
    removed_pack_ids: tuple[str, ...] = ()
    removed_projected_relative_dirs: tuple[str, ...] = ()
    safely_removed_legacy_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class SystemSkillUpgradeResult:
    """Outcome of static refresh and conservative migration."""

    install: SystemSkillInstallResult
    legacy_before: LegacySystemSkillInspection
    preserved_legacy_paths: tuple[str, ...]


@dataclass(frozen=True)
class SystemSkillUninstallResult:
    """Outcome of subtracting selected pack ownership."""

    tool: str
    home_path: Path
    requested_pack_ids: tuple[str, ...]
    removed_pack_ids: tuple[str, ...]
    absent_pack_ids: tuple[str, ...]
    removed_projected_relative_dirs: tuple[str, ...]
    retained_shared_skill_names: tuple[str, ...]
    preserved_conflicting_paths: tuple[str, ...]
    config_path: Path


def system_skills_destination_for_tool(tool: str) -> str:
    """Return the visible skill-root directory for one supported tool."""

    destination = _SYSTEM_SKILL_DESTINATION_BY_TOOL.get(tool)
    if destination is None:
        raise SystemSkillInstallError(f"Unsupported tool `{tool}` for system-skill packs.")
    return destination


def projected_standalone_skill_relative_dir(*, tool: str, skill_name: str) -> str:
    """Return one home-relative standalone projection path."""

    manifest = load_system_skill_manifest()
    if skill_name not in manifest.standalone_skills:
        if skill_name in manifest.shared_routines:
            raise SystemSkillInstallError(
                f"Shared child `{skill_name}` has no independent top-level projection."
            )
        raise SystemSkillInstallError(f"Unknown standalone system skill `{skill_name}`.")
    return str(Path(system_skills_destination_for_tool(tool)) / skill_name)


def system_skill_state_root(*, tool: str, home_path: Path) -> Path:
    """Return the tool-scoped hidden config directory."""

    system_skills_destination_for_tool(tool)
    return home_path.resolve() / ".houmao" / "system-skills" / tool


def system_skill_config_path(*, tool: str, home_path: Path) -> Path:
    """Return the tool-scoped static collection config path."""

    return system_skill_state_root(tool=tool, home_path=home_path) / SYSTEM_SKILL_CONFIG_FILENAME


def inspect_system_skill_config(
    *,
    tool: str,
    home_path: Path,
) -> SystemSkillConfigInspection:
    """Read current config without mutating filesystem state."""

    resolved_home = home_path.resolve()
    path = system_skill_config_path(tool=tool, home_path=resolved_home)
    if not path.exists():
        return SystemSkillConfigInspection(status="absent", path=path, config=None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SystemSkillConfigInspection(
            status="corrupt",
            path=path,
            config=None,
            message=f"Cannot read system-skill config: {exc}",
        )
    if not isinstance(payload, dict):
        return SystemSkillConfigInspection(
            status="corrupt",
            path=path,
            config=None,
            message="System-skill config must be a JSON object.",
        )
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        return SystemSkillConfigInspection(
            status="corrupt",
            path=path,
            config=None,
            message="System-skill config schema_version must be a non-empty string.",
        )
    if schema_version != SYSTEM_SKILL_CONFIG_SCHEMA_VERSION:
        return SystemSkillConfigInspection(
            status="unsupported",
            path=path,
            config=None,
            message=f"Unsupported system-skill config schema `{schema_version}`.",
        )
    try:
        config = _parse_config_payload(
            cast(dict[str, Any], payload),
            expected_tool=tool,
            expected_home=resolved_home,
        )
    except (KeyError, TypeError, ValueError, SystemSkillInstallError) as exc:
        return SystemSkillConfigInspection(
            status="corrupt",
            path=path,
            config=None,
            message=str(exc),
        )
    return SystemSkillConfigInspection(status="current", path=path, config=config)


def inspect_system_skill_packs(
    *,
    tool: str,
    home_path: Path,
) -> SystemSkillStatusResult:
    """Classify static members, actor packs, config posture, and legacy flat paths."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    config_inspection = inspect_system_skill_config(tool=tool, home_path=resolved_home)
    config = config_inspection.config
    config_map = config.skill_map() if config is not None else {}
    member_statuses: list[SystemSkillMemberStatusRecord] = []
    status_by_name: dict[str, MemberIntegrityStatus] = {}
    for record in manifest.standalone_skills.values():
        relative_path = projected_standalone_skill_relative_dir(
            tool=tool,
            skill_name=record.name,
        )
        config_record = config_map.get(record.name)
        status: MemberIntegrityStatus
        owners: tuple[str, ...]
        mode: SystemSkillProjectionMode | None
        digest: str | None
        if config_record is None:
            status = "conflicting" if _path_lexists(resolved_home / relative_path) else "absent"
            owners = ()
            mode = None
            digest = None
        else:
            assert config is not None
            status = _inspect_current_member(
                manifest=manifest,
                home_path=resolved_home,
                record=config_record,
                projection_mode=config.projection_mode,
            )
            owners = config_record.owning_pack_ids
            mode = config.projection_mode
            digest = config_record.content_digest
        status_by_name[record.name] = status
        member_statuses.append(
            SystemSkillMemberStatusRecord(
                name=record.name,
                role=record.role,
                activation=record.activation,
                status=status,
                relative_path=relative_path,
                owning_pack_ids=owners,
                projection_mode=mode,
                expected_content_digest=digest,
            )
        )

    pack_statuses: list[SystemSkillPackStatusRecord] = []
    for pack in manifest.packs.values():
        paths = tuple(
            projected_standalone_skill_relative_dir(tool=tool, skill_name=name)
            for name in pack.standalone_skill_names
        )
        member_states = {name: status_by_name[name] for name in pack.standalone_skill_names}
        if config is not None and pack.pack_id not in config.selected_pack_ids:
            unowned_conflicts = any(
                status_by_name[name] == "conflicting"
                for name in pack.standalone_skill_names
                if not config_map.get(name)
            )
            pack_status: PackIntegrityStatus = "conflicting" if unowned_conflicts else "absent"
        elif all(state == "absent" for state in member_states.values()):
            pack_status = "absent"
        elif any(state == "conflicting" for state in member_states.values()):
            pack_status = "conflicting"
        elif any(state in {"absent", "incomplete"} for state in member_states.values()):
            pack_status = "incomplete"
        elif any(state == "drifted" for state in member_states.values()):
            pack_status = "drifted"
        else:
            pack_status = "complete"
        pack_statuses.append(
            SystemSkillPackStatusRecord(
                pack_id=pack.pack_id,
                audience=pack.audience,
                status=pack_status,
                standalone_skill_names=pack.standalone_skill_names,
                standalone_paths=paths,
                missing_paths=tuple(
                    path
                    for name, path in zip(pack.standalone_skill_names, paths, strict=True)
                    if member_states[name] in {"absent", "incomplete"}
                ),
                drifted_paths=tuple(
                    path
                    for name, path in zip(pack.standalone_skill_names, paths, strict=True)
                    if member_states[name] == "drifted"
                ),
                conflicting_paths=tuple(
                    path
                    for name, path in zip(pack.standalone_skill_names, paths, strict=True)
                    if member_states[name] == "conflicting"
                ),
            )
        )
    return SystemSkillStatusResult(
        tool=tool,
        home_path=resolved_home,
        config=config_inspection,
        members=tuple(member_statuses),
        packs=tuple(pack_statuses),
        legacy=inspect_legacy_system_skill_paths(tool=tool, home_path=resolved_home),
    )


def inspect_legacy_system_skill_paths(
    *,
    tool: str,
    home_path: Path,
) -> LegacySystemSkillInspection:
    """Classify retired flat skill paths without mutating them."""

    manifest = load_system_skill_manifest()
    legacy_catalog = load_legacy_system_skill_catalog()
    resolved_home = home_path.resolve()
    skill_root = resolved_home / system_skills_destination_for_tool(tool)
    package_root = _packaged_asset_filesystem_root()
    paths: list[LegacySystemSkillPathStatus] = []
    standalone_names = set(manifest.standalone_skills)
    known_names = set(manifest.legacy_skills)
    for legacy in manifest.legacy_skills.values():
        if legacy.name in standalone_names:
            continue
        path = skill_root / legacy.name
        if not _path_lexists(path):
            continue
        if path.is_symlink():
            raw_target = path.readlink()
            target = (raw_target if raw_target.is_absolute() else path.parent / raw_target).resolve(
                strict=False
            )
            expected_target = (package_root / legacy.asset_subpath).resolve(strict=False)
            classification: LegacyPathClassification = (
                "package-linked" if target == expected_target else "modified"
            )
            paths.append(
                LegacySystemSkillPathStatus(
                    name=legacy.name,
                    relative_path=str(path.relative_to(resolved_home)),
                    classification=classification,
                    link_target=str(raw_target),
                )
            )
            continue
        digest = tree_content_digest(path) if path.is_dir() else None
        paths.append(
            LegacySystemSkillPathStatus(
                name=legacy.name,
                relative_path=str(path.relative_to(resolved_home)),
                classification=(
                    "digest-matched"
                    if digest is not None and digest == legacy.content_digest
                    else "modified"
                ),
                content_digest=digest,
            )
        )
    if skill_root.is_dir():
        for path in sorted(skill_root.glob("houmao-*")):
            if (
                path.name in known_names
                or path.name in standalone_names
                or path.name == manifest.auto_skill_name
            ):
                continue
            paths.append(
                LegacySystemSkillPathStatus(
                    name=path.name,
                    relative_path=str(path.relative_to(resolved_home)),
                    classification="unknown",
                    link_target=str(path.readlink()) if path.is_symlink() else None,
                )
            )
    conflicting = any(path.classification in {"modified", "unknown"} for path in paths)
    current_v1_names = {
        record.name for record in legacy_catalog.skills if record.name not in standalone_names
    }
    present_v1_names = {record.name for record in paths if record.name in current_v1_names}
    if conflicting:
        overall: LegacyOverallStatus = "conflicting"
    elif not paths:
        overall = "absent"
    elif present_v1_names == current_v1_names:
        overall = "complete"
    else:
        overall = "partial"
    return LegacySystemSkillInspection(status=overall, paths=tuple(paths))


def install_system_skill_packs_for_home(
    *,
    tool: str,
    home_path: Path,
    pack_ids: Sequence[str] = (),
    use_cli_default: bool = False,
    auto_install_kind: AutoInstallKind | None = None,
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillInstallResult:
    """Install selected packs additively as one static collection."""

    manifest = load_system_skill_manifest()
    selected = _resolve_requested_pack_ids(
        manifest,
        pack_ids=pack_ids,
        use_cli_default=use_cli_default,
        auto_install_kind=auto_install_kind,
    )
    return _apply_static_transaction(
        manifest=manifest,
        tool=tool,
        home_path=home_path,
        selected_pack_ids=selected,
        projection_mode=projection_mode,
        exact=False,
        allow_replace_drifted=False,
        legacy_paths_to_remove=(),
    )


def sync_system_skill_packs_for_home(
    *,
    tool: str,
    home_path: Path,
    selected_pack_ids: Sequence[str],
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillInstallResult:
    """Synchronize a managed home to an exact static pack selection."""

    manifest = load_system_skill_manifest()
    selected = resolve_system_skill_pack_selection(manifest, pack_ids=selected_pack_ids)
    return _apply_static_transaction(
        manifest=manifest,
        tool=tool,
        home_path=home_path,
        selected_pack_ids=selected,
        projection_mode=projection_mode,
        exact=True,
        allow_replace_drifted=True,
        legacy_paths_to_remove=(),
    )


def upgrade_system_skill_packs_for_home(
    *,
    tool: str,
    home_path: Path,
    pack_ids: Sequence[str] = (),
    use_cli_default: bool = False,
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillUpgradeResult:
    """Refresh a current config or clean home while removing safe flat legacy paths."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    legacy_before = inspect_legacy_system_skill_paths(tool=tool, home_path=resolved_home)
    safe_legacy_paths = tuple(
        resolved_home / record.relative_path
        for record in legacy_before.paths
        if record.classification in {"package-linked", "digest-matched"}
    )
    preserved = tuple(
        record.relative_path
        for record in legacy_before.paths
        if record.classification in {"modified", "unknown"}
    )
    selected = _resolve_requested_pack_ids(
        manifest,
        pack_ids=pack_ids,
        use_cli_default=use_cli_default,
        auto_install_kind=None,
    )
    result = _apply_static_transaction(
        manifest=manifest,
        tool=tool,
        home_path=resolved_home,
        selected_pack_ids=selected,
        projection_mode=projection_mode,
        exact=False,
        allow_replace_drifted=True,
        legacy_paths_to_remove=safe_legacy_paths,
    )
    return SystemSkillUpgradeResult(
        install=result,
        legacy_before=legacy_before,
        preserved_legacy_paths=preserved,
    )


def uninstall_system_skill_packs_for_home(
    *,
    tool: str,
    home_path: Path,
    pack_ids: Sequence[str] = (),
) -> SystemSkillUninstallResult:
    """Subtract pack owners and remove only final-owner projections."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    inspection = inspect_system_skill_config(tool=tool, home_path=resolved_home)
    if inspection.status in {"corrupt", "unsupported"}:
        raise SystemSkillInstallError(
            inspection.message or "The system-skill config cannot be uninstalled safely."
        )
    config = inspection.config
    if config is None:
        requested = (
            resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids) if pack_ids else ()
        )
        return SystemSkillUninstallResult(
            tool=tool,
            home_path=resolved_home,
            requested_pack_ids=requested,
            removed_pack_ids=(),
            absent_pack_ids=requested,
            removed_projected_relative_dirs=(),
            retained_shared_skill_names=(),
            preserved_conflicting_paths=(),
            config_path=inspection.path,
        )
    requested = (
        resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids)
        if pack_ids
        else config.selected_pack_ids
    )
    present_requested = tuple(
        pack_id for pack_id in requested if pack_id in config.selected_pack_ids
    )
    absent = tuple(pack_id for pack_id in requested if pack_id not in config.selected_pack_ids)
    new_pack_ids = tuple(
        pack_id for pack_id in config.selected_pack_ids if pack_id not in present_requested
    )
    updated_records: list[SystemSkillConfigSkillRecord] = []
    removable_records: list[SystemSkillConfigSkillRecord] = []
    retained_shared: list[str] = []
    conflicts: list[str] = []
    for record in config.skills:
        owners = tuple(owner for owner in record.owning_pack_ids if owner not in present_requested)
        if owners:
            updated_records.append(
                SystemSkillConfigSkillRecord(
                    name=record.name,
                    relative_path=record.relative_path,
                    content_digest=record.content_digest,
                    owning_pack_ids=owners,
                )
            )
            if owners != record.owning_pack_ids:
                retained_shared.append(record.name)
            continue
        integrity = _inspect_current_member(
            manifest=manifest,
            home_path=resolved_home,
            record=record,
            projection_mode=config.projection_mode,
        )
        if integrity not in {"complete", "absent"}:
            conflicts.append(record.relative_path)
        else:
            removable_records.append(record)

    previous_config_bytes = inspection.path.read_bytes()
    removed_paths: list[str] = []
    with _transaction_directory(tool=tool, home_path=resolved_home) as raw_transaction_root:
        transaction_root = Path(raw_transaction_root)
        backups: list[tuple[Path, Path]] = []
        try:
            for record in removable_records:
                target = resolved_home / record.relative_path
                if not _path_lexists(target):
                    continue
                backup = transaction_root / "backups" / str(len(backups))
                _backup_path(target, backup)
                backups.append((target, backup))
                removed_paths.append(record.relative_path)
            if updated_records:
                updated_record_map = {record.name: record for record in updated_records}
                ordered_updated_records = tuple(
                    updated_record_map[record.name]
                    for record in resolve_system_skill_pack_members(
                        manifest,
                        pack_ids=new_pack_ids,
                    )
                )
                updated_config = SystemSkillConfig(
                    schema_version=SYSTEM_SKILL_CONFIG_SCHEMA_VERSION,
                    houmao_version=_package_version(),
                    tool=tool,
                    home_path=resolved_home,
                    projection_mode=config.projection_mode,
                    skills=ordered_updated_records,
                )
                _persist_config_atomic(updated_config)
            elif inspection.path.exists():
                inspection.path.unlink()
        except Exception:
            _restore_backups(backups)
            _restore_config_bytes(inspection.path, previous_config_bytes)
            raise
    return SystemSkillUninstallResult(
        tool=tool,
        home_path=resolved_home,
        requested_pack_ids=requested,
        removed_pack_ids=present_requested,
        absent_pack_ids=absent,
        removed_projected_relative_dirs=tuple(removed_paths),
        retained_shared_skill_names=tuple(retained_shared),
        preserved_conflicting_paths=tuple(conflicts),
        config_path=inspection.path,
    )


def project_system_skill_pack_to_destination(
    destination_root: Path,
    *,
    pack_id: str,
) -> tuple[str, ...]:
    """Copy one pack's complete static members into an explicit destination."""

    manifest = load_system_skill_manifest()
    staged = stage_system_skill_collection(
        manifest,
        pack_ids=(pack_id,),
        destination_root=destination_root,
        projection_mode="copy",
    )
    return tuple(record.name for record in staged.skills)


def _apply_static_transaction(
    *,
    manifest: SystemSkillManifest,
    tool: str,
    home_path: Path,
    selected_pack_ids: tuple[str, ...],
    projection_mode: SystemSkillProjectionMode,
    exact: bool,
    allow_replace_drifted: bool,
    legacy_paths_to_remove: tuple[Path, ...],
) -> SystemSkillInstallResult:
    """Stage, preflight, commit, write config last, and roll back one union."""

    _validate_projection_mode(projection_mode)
    if not selected_pack_ids and not exact:
        raise SystemSkillInstallError("At least one system-skill pack must be selected.")
    resolved_home = home_path.resolve()
    resolved_home.mkdir(parents=True, exist_ok=True)
    system_skills_destination_for_tool(tool)
    state_root = system_skill_state_root(tool=tool, home_path=resolved_home)
    state_root.mkdir(parents=True, exist_ok=True)
    inspection = inspect_system_skill_config(tool=tool, home_path=resolved_home)
    if inspection.status in {"corrupt", "unsupported"}:
        raise SystemSkillInstallError(
            inspection.message or "The system-skill config cannot be used safely."
        )
    previous_config = inspection.config
    previous_pack_ids = previous_config.selected_pack_ids if previous_config is not None else ()
    final_pack_ids = (
        selected_pack_ids
        if exact
        else _manifest_ordered_pack_union(
            manifest,
            (*previous_pack_ids, *selected_pack_ids),
        )
    )
    removed_pack_ids = tuple(
        pack_id for pack_id in previous_pack_ids if pack_id not in final_pack_ids
    )
    previous_map = previous_config.skill_map() if previous_config is not None else {}
    previous_config_bytes = inspection.path.read_bytes() if inspection.path.exists() else None
    with _transaction_directory(tool=tool, home_path=resolved_home) as raw_transaction_root:
        transaction_root = Path(raw_transaction_root)
        staged_root = transaction_root / "staged"
        staged = stage_system_skill_collection(
            manifest,
            pack_ids=final_pack_ids,
            destination_root=staged_root,
            projection_mode=projection_mode,
        )
        final_names = {record.name for record in staged.skills}
        for staged_record in staged.skills:
            relative_path = projected_standalone_skill_relative_dir(
                tool=tool,
                skill_name=staged_record.name,
            )
            target = resolved_home / relative_path
            current_record = previous_map.get(staged_record.name)
            if _path_lexists(target) and current_record is None:
                raise SystemSkillInstallError(
                    f"Untracked system-skill collision at `{target}`. Move or remove it before "
                    "installing the owning pack."
                )
            if current_record is not None:
                assert previous_config is not None
                integrity = _inspect_current_member(
                    manifest=manifest,
                    home_path=resolved_home,
                    record=current_record,
                    projection_mode=previous_config.projection_mode,
                )
                if integrity == "conflicting" or (
                    integrity in {"incomplete", "drifted"} and not allow_replace_drifted
                ):
                    raise SystemSkillInstallError(
                        f"Config-owned system skill `{relative_path}` is {integrity}; use "
                        "sync or upgrade for explicit replacement."
                    )

        obsolete_relative_paths: list[str] = []
        if previous_config is not None:
            obsolete_relative_paths.extend(
                record.relative_path
                for record in previous_config.skills
                if record.name not in final_names
            )

        affected_paths: list[Path] = []
        if previous_config is not None:
            affected_paths.extend(
                resolved_home / record.relative_path for record in previous_config.skills
            )
        affected_paths.extend(
            resolved_home
            / projected_standalone_skill_relative_dir(tool=tool, skill_name=record.name)
            for record in staged.skills
        )
        affected_paths.extend(legacy_paths_to_remove)
        unique_affected = _deduplicate_paths(affected_paths)
        backups: list[tuple[Path, Path]] = []
        committed_paths: list[Path] = []
        safe_legacy_relative_paths: list[str] = []
        try:
            for original in unique_affected:
                if not _path_lexists(original):
                    continue
                try:
                    relative_to_home = original.absolute().relative_to(resolved_home)
                except ValueError as exc:
                    raise SystemSkillInstallError(
                        f"Transaction path `{original}` escapes the target home."
                    ) from exc
                backup = transaction_root / "backups" / str(len(backups))
                _backup_path(original, backup)
                backups.append((original, backup))
                if original in legacy_paths_to_remove:
                    safe_legacy_relative_paths.append(str(relative_to_home))
            for staged_record in staged.skills:
                target = resolved_home / projected_standalone_skill_relative_dir(
                    tool=tool,
                    skill_name=staged_record.name,
                )
                _commit_static_projection(staged_record.path, target)
                committed_paths.append(target)
            if staged.skills:
                config = SystemSkillConfig(
                    schema_version=SYSTEM_SKILL_CONFIG_SCHEMA_VERSION,
                    houmao_version=_package_version(),
                    tool=tool,
                    home_path=resolved_home,
                    projection_mode=projection_mode,
                    skills=tuple(
                        SystemSkillConfigSkillRecord(
                            name=record.name,
                            relative_path=projected_standalone_skill_relative_dir(
                                tool=tool,
                                skill_name=record.name,
                            ),
                            content_digest=record.content_digest,
                            owning_pack_ids=record.owning_pack_ids,
                        )
                        for record in staged.skills
                    ),
                )
                _persist_config_atomic(config)
            elif inspection.path.exists():
                inspection.path.unlink()
        except Exception:
            for path in reversed(committed_paths):
                _remove_path(path)
            _restore_backups(backups)
            _restore_config_bytes(inspection.path, previous_config_bytes)
            raise

    standalone_names = tuple(record.name for record in staged.skills)
    projected_dirs = tuple(
        projected_standalone_skill_relative_dir(tool=tool, skill_name=name)
        for name in standalone_names
    )
    owners_by_skill = {record.name: record.owning_pack_ids for record in staged.skills}
    removed_dirs = tuple(
        dict.fromkeys(
            relative_path
            for relative_path in obsolete_relative_paths
            if relative_path not in projected_dirs
        )
    )
    return SystemSkillInstallResult(
        tool=tool,
        home_path=resolved_home,
        selected_pack_ids=final_pack_ids,
        standalone_skill_names=standalone_names,
        projected_relative_dirs=projected_dirs,
        config_path=system_skill_config_path(tool=tool, home_path=resolved_home),
        projection_mode=projection_mode,
        owning_pack_ids_by_skill=owners_by_skill,
        removed_pack_ids=removed_pack_ids,
        removed_projected_relative_dirs=removed_dirs,
        safely_removed_legacy_paths=tuple(safe_legacy_relative_paths),
    )


def _resolve_requested_pack_ids(
    manifest: SystemSkillManifest,
    *,
    pack_ids: Sequence[str],
    use_cli_default: bool,
    auto_install_kind: AutoInstallKind | None,
) -> tuple[str, ...]:
    """Resolve explicit and lane-default actor pack ids."""

    if use_cli_default and auto_install_kind is not None:
        raise SystemSkillInstallError(
            "CLI default selection and managed automatic selection are mutually exclusive."
        )
    requested: list[str] = []
    if use_cli_default:
        requested.extend(manifest.defaults.cli)
    if auto_install_kind is not None:
        requested.extend(manifest.defaults.pack_ids_for_kind(auto_install_kind))
    requested.extend(pack_ids)
    selected = resolve_system_skill_pack_selection(manifest, pack_ids=requested)
    if not selected:
        raise SystemSkillInstallError("At least one system-skill pack must be selected.")
    return selected


def _manifest_ordered_pack_union(
    manifest: SystemSkillManifest,
    pack_ids: Sequence[str],
) -> tuple[str, ...]:
    """Return a de-duplicated pack union in manifest order."""

    requested = set(resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids))
    return tuple(pack_id for pack_id in manifest.pack_ids if pack_id in requested)


def _parse_config_payload(
    payload: dict[str, Any],
    *,
    expected_tool: str,
    expected_home: Path,
) -> SystemSkillConfig:
    """Parse and strictly validate one current static config."""

    required_keys = {
        "schema_version",
        "houmao_version",
        "projection_mode",
        "skills",
    }
    if set(payload) != required_keys:
        raise SystemSkillInstallError("System-skill config has missing or unknown fields.")
    if _require_string(payload, "schema_version") != SYSTEM_SKILL_CONFIG_SCHEMA_VERSION:
        raise SystemSkillInstallError("System-skill config schema is invalid.")
    mode = payload["projection_mode"]
    if mode not in {"copy", "symlink"}:
        raise SystemSkillInstallError("System-skill config projection mode is invalid.")
    raw_skills = payload["skills"]
    if not isinstance(raw_skills, list) or not raw_skills:
        raise SystemSkillInstallError("System-skill config skills must be a non-empty list.")
    skill_records = tuple(_parse_config_skill(item) for item in raw_skills)
    if len({record.name for record in skill_records}) != len(skill_records):
        raise SystemSkillInstallError("System-skill config has duplicate standalone names.")
    manifest = load_system_skill_manifest()
    selected = tuple(
        pack_id
        for pack_id in manifest.pack_ids
        if any(pack_id in record.owning_pack_ids for record in skill_records)
    )
    if not selected:
        raise SystemSkillInstallError("System-skill config has no installed pack owners.")
    expected_records = resolve_system_skill_pack_members(manifest, pack_ids=selected)
    if tuple(record.name for record in skill_records) != tuple(
        record.name for record in expected_records
    ):
        raise SystemSkillInstallError(
            "System-skill config skills do not match the derived static pack union."
        )
    for record in skill_records:
        expected_relative_path = projected_standalone_skill_relative_dir(
            tool=expected_tool,
            skill_name=record.name,
        )
        if record.relative_path != expected_relative_path:
            raise SystemSkillInstallError(
                f"Config path for `{record.name}` does not match its canonical destination."
            )
        expected_owners = tuple(
            pack_id
            for pack_id in selected
            if record.name in manifest.packs[pack_id].standalone_skill_names
        )
        if record.owning_pack_ids != expected_owners:
            raise SystemSkillInstallError(
                f"Config owner set for `{record.name}` does not match derived packs."
            )
    return SystemSkillConfig(
        schema_version=_require_string(payload, "schema_version"),
        houmao_version=_require_string(payload, "houmao_version"),
        tool=expected_tool,
        home_path=expected_home,
        projection_mode=cast(SystemSkillProjectionMode, mode),
        skills=skill_records,
    )


def _parse_config_skill(payload: object) -> SystemSkillConfigSkillRecord:
    """Parse one strict standalone config record."""

    if not isinstance(payload, dict) or set(payload) != {
        "name",
        "relative_path",
        "content_digest",
        "owning_pack_ids",
    }:
        raise SystemSkillInstallError("System-skill config has an invalid skill record.")
    digest = _require_string(cast(dict[str, Any], payload), "content_digest")
    _validate_digest(digest)
    owners = _require_string_list(cast(dict[str, Any], payload), "owning_pack_ids")
    if not owners:
        raise SystemSkillInstallError("Config standalone owner sets must not be empty.")
    manifest = load_system_skill_manifest()
    if any(owner not in manifest.packs for owner in owners):
        raise SystemSkillInstallError("System-skill config has an unsupported pack owner.")
    manifest_ordered_owners = tuple(pack_id for pack_id in manifest.pack_ids if pack_id in owners)
    if owners != manifest_ordered_owners:
        raise SystemSkillInstallError("System-skill config pack owners are out of order.")
    return SystemSkillConfigSkillRecord(
        name=_require_string(cast(dict[str, Any], payload), "name"),
        relative_path=_require_safe_relative_path(
            cast(dict[str, Any], payload),
            "relative_path",
        ),
        content_digest=digest,
        owning_pack_ids=owners,
    )


def _inspect_current_member(
    *,
    manifest: SystemSkillManifest,
    home_path: Path,
    record: SystemSkillConfigSkillRecord,
    projection_mode: SystemSkillProjectionMode,
) -> MemberIntegrityStatus:
    """Classify one config-owned static member against source and destination."""

    manifest_record = manifest.standalone_skills.get(record.name)
    if manifest_record is None:
        return "drifted"
    if record.content_digest != standalone_system_skill_content_digest(manifest, manifest_record):
        return "drifted"
    expected_relative_path = projected_standalone_skill_relative_dir(
        tool=_tool_from_config_relative_path(record.relative_path),
        skill_name=record.name,
    )
    if expected_relative_path != record.relative_path:
        return "conflicting"
    path = home_path / record.relative_path
    if not _path_lexists(path):
        return "absent"
    if projection_mode == "copy":
        if path.is_symlink() or not path.is_dir():
            return "conflicting"
    else:
        if not path.is_symlink():
            return "conflicting"
        expected_target = standalone_system_skill_source_path(manifest, manifest_record)
        actual_target = _symlink_target(path)
        if actual_target != expected_target.resolve(strict=False):
            return "conflicting"
    if record.name == "houmao-shared-routines" and not _shared_children_complete(path):
        return "incomplete"
    try:
        digest = tree_content_digest(path)
    except SystemSkillManifestError:
        return "drifted"
    return "complete" if digest == record.content_digest else "drifted"


def _tool_from_config_relative_path(relative_path: str) -> str:
    """Return a tool whose destination root matches one config path."""

    destination = Path(relative_path).parts[0] if Path(relative_path).parts else ""
    for tool, root in _SYSTEM_SKILL_DESTINATION_BY_TOOL.items():
        if root == destination:
            return tool
    raise SystemSkillInstallError(f"Config path `{relative_path}` has an unknown skill root.")


def _shared_children_complete(path: Path) -> bool:
    """Return whether shared routines contains all and only sixteen child entrypoints."""

    child_root = path / "subskills"
    if not child_root.is_dir():
        return False
    actual = {
        child.name
        for child in child_root.iterdir()
        if child.is_dir()
        and (child / "SKILL-MAIN.md").is_file()
        and not (child / "SKILL.md").exists()
    }
    return actual == set(EXPECTED_SHARED_ROUTINE_IDS)


def _persist_config_atomic(config: SystemSkillConfig) -> None:
    """Write one config atomically in its tool-scoped state directory."""

    path = config.path
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(config.to_payload(), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _transaction_directory(*, tool: str, home_path: Path) -> tempfile.TemporaryDirectory[str]:
    """Create a bounded same-filesystem transaction directory."""

    state_root = system_skill_state_root(tool=tool, home_path=home_path)
    state_root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=".transaction-", dir=state_root)


def _backup_path(original: Path, backup: Path) -> None:
    """Move one exact affected path into bounded transaction backup storage."""

    backup.parent.mkdir(parents=True, exist_ok=True)
    original.parent.mkdir(parents=True, exist_ok=True)
    os.replace(original, backup)


def _restore_backups(backups: Iterable[tuple[Path, Path]]) -> None:
    """Restore transaction backups in reverse order."""

    for original, backup in reversed(tuple(backups)):
        if not _path_lexists(backup):
            continue
        _remove_path(original)
        original.parent.mkdir(parents=True, exist_ok=True)
        os.replace(backup, original)


def _commit_static_projection(staged_path: Path, target_path: Path) -> None:
    """Commit one complete copied directory or direct source symlink."""

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if _path_lexists(target_path):
        raise SystemSkillInstallError(f"Commit target `{target_path}` was not preflight-cleared.")
    os.replace(staged_path, target_path)


def _restore_config_bytes(path: Path, previous_bytes: bytes | None) -> None:
    """Restore previous config bytes after transaction failure."""

    if previous_bytes is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(previous_bytes)


def _remove_path(path: Path) -> None:
    """Remove one exact file, link, or directory if present."""

    if not _path_lexists(path):
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _path_lexists(path: Path) -> bool:
    """Return whether a path exists, including a dangling symlink."""

    return path.exists() or path.is_symlink()


def _symlink_target(path: Path) -> Path:
    """Resolve one symlink target without requiring that it still exists."""

    raw_target = path.readlink()
    return (raw_target if raw_target.is_absolute() else path.parent / raw_target).resolve(
        strict=False
    )


def _deduplicate_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    """Return first-occurrence unique absolute paths."""

    result: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        absolute = path.absolute()
        if absolute in seen:
            continue
        seen.add(absolute)
        result.append(absolute)
    return tuple(result)


def _validate_projection_mode(mode: str) -> None:
    """Reject unsupported projection modes."""

    if mode not in {"copy", "symlink"}:
        raise SystemSkillInstallError(f"Unsupported system-skill projection mode `{mode}`.")


def _require_string(payload: dict[str, Any], key: str) -> str:
    """Read one required non-empty string field."""

    value = payload[key]
    if not isinstance(value, str) or not value:
        raise SystemSkillInstallError(f"Config field `{key}` must be a non-empty string.")
    return value


def _require_string_list(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    """Read one required unique string-list field."""

    value = payload[key]
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise SystemSkillInstallError(f"Config field `{key}` must be a string list.")
    result = tuple(cast(list[str], value))
    if len(result) != len(set(result)):
        raise SystemSkillInstallError(f"Config field `{key}` must not contain duplicates.")
    return result


def _require_safe_relative_path(payload: dict[str, Any], key: str) -> str:
    """Read and validate one home-relative config path."""

    return _validate_safe_relative_path(_require_string(payload, key))


def _validate_safe_relative_path(value: str) -> str:
    """Reject absolute and escaping config paths."""

    path = Path(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise SystemSkillInstallError(f"Config path `{value}` is unsafe.")
    return value


def _validate_digest(value: str) -> None:
    """Require one lowercase SHA-256 digest."""

    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise SystemSkillInstallError("System-skill config content digest is invalid.")


def _package_version() -> str:
    """Return the installed Houmao package version for config evidence."""

    try:
        return metadata.version("Houmao")
    except metadata.PackageNotFoundError:
        return "0+unknown"


def _packaged_asset_filesystem_root() -> Path:
    """Return the package asset root used for old symlink recognition."""

    root = resources.files("houmao.agents.assets.system_skills")
    if not isinstance(root, Path):
        raise SystemSkillInstallError(
            "Legacy package-link classification requires filesystem-backed assets."
        )
    return root.resolve()
