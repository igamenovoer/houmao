"""Transactional lifecycle and shared ownership for static Houmao system skills."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
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


SYSTEM_SKILL_RECEIPT_SCHEMA_VERSION = "houmao-system-skills-receipt.v2"
LEGACY_V3_RECEIPT_SCHEMA_VERSION = "houmao-system-skills-receipt.v1"
SYSTEM_SKILL_RECEIPT_FILENAME = "receipt.json"
SystemSkillProjectionMode = Literal["copy", "symlink"]
ReceiptInspectionStatus = Literal[
    "absent",
    "current",
    "legacy-v3",
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
class SystemSkillReceiptSkillRecord:
    """Receipt evidence and owner set for one standalone projection."""

    name: str
    role: StandaloneSkillRole
    relative_path: str
    projection_mode: SystemSkillProjectionMode
    content_digest: str
    owning_pack_ids: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe record payload."""

        return {
            "name": self.name,
            "role": self.role,
            "relative_path": self.relative_path,
            "projection_mode": self.projection_mode,
            "content_digest": self.content_digest,
            "owning_pack_ids": list(self.owning_pack_ids),
        }


@dataclass(frozen=True)
class SystemSkillReceipt:
    """Tool-scoped receipt for one static system-skill collection."""

    schema_version: str
    manifest_schema_version: str
    package_version: str
    tool: str
    home_path: Path
    updated_at: str
    projection_mode: SystemSkillProjectionMode
    selected_pack_ids: tuple[str, ...]
    skills: tuple[SystemSkillReceiptSkillRecord, ...]
    safely_removed_legacy_paths: tuple[str, ...] = ()

    @property
    def path(self) -> Path:
        """Return the canonical receipt path."""

        return system_skill_receipt_path(tool=self.tool, home_path=self.home_path)

    def skill_map(self) -> dict[str, SystemSkillReceiptSkillRecord]:
        """Return receipt records keyed by standalone name."""

        return {record.name: record for record in self.skills}

    def to_payload(self) -> dict[str, object]:
        """Return the complete JSON-safe receipt payload."""

        return {
            "schema_version": self.schema_version,
            "manifest_schema_version": self.manifest_schema_version,
            "package_version": self.package_version,
            "tool": self.tool,
            "home_path": str(self.home_path),
            "updated_at": self.updated_at,
            "projection_mode": self.projection_mode,
            "selected_packs": list(self.selected_pack_ids),
            "skills": [record.to_payload() for record in self.skills],
            "safely_removed_legacy_paths": list(self.safely_removed_legacy_paths),
        }


@dataclass(frozen=True)
class SystemSkillReceiptInspection:
    """Read-only receipt parse result suitable for status output."""

    status: ReceiptInspectionStatus
    path: Path
    receipt: SystemSkillReceipt | None
    message: str | None = None
    legacy_pack_ids: tuple[str, ...] = ()
    legacy_owned_paths: tuple[str, ...] = ()


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
    """Receipt, member, pack, and legacy evidence for one tool home."""

    tool: str
    home_path: Path
    receipt: SystemSkillReceiptInspection
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
    receipt_path: Path
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
    migrated_v3: bool = False
    removed_obsolete_paths: tuple[str, ...] = ()


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
    receipt_path: Path


@dataclass(frozen=True)
class _LegacyV3SkillRecord:
    """Owned projection evidence parsed from a v3 composer receipt."""

    name: str
    relative_path: str
    projection_mode: SystemSkillProjectionMode
    content_digest: str
    materialization_relative_path: str | None

    @property
    def owned_relative_paths(self) -> tuple[str, ...]:
        """Return all paths owned by the legacy record."""

        if self.materialization_relative_path is None:
            return (self.relative_path,)
        return (self.relative_path, self.materialization_relative_path)


@dataclass(frozen=True)
class _LegacyV3Receipt:
    """Minimal safe parse of a receipt-owned composed installation."""

    selected_pack_ids: tuple[str, ...]
    skills: tuple[_LegacyV3SkillRecord, ...]


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
    """Return the tool-scoped hidden receipt directory."""

    system_skills_destination_for_tool(tool)
    return home_path.resolve() / ".houmao" / "system-skills" / tool


def system_skill_receipt_path(*, tool: str, home_path: Path) -> Path:
    """Return the tool-scoped static collection receipt path."""

    return system_skill_state_root(tool=tool, home_path=home_path) / SYSTEM_SKILL_RECEIPT_FILENAME


def inspect_system_skill_receipt(
    *,
    tool: str,
    home_path: Path,
) -> SystemSkillReceiptInspection:
    """Read a v4 or recognized v3 receipt without mutating filesystem state."""

    resolved_home = home_path.resolve()
    path = system_skill_receipt_path(tool=tool, home_path=resolved_home)
    if not path.exists():
        return SystemSkillReceiptInspection(status="absent", path=path, receipt=None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SystemSkillReceiptInspection(
            status="corrupt",
            path=path,
            receipt=None,
            message=f"Cannot read system-skill receipt: {exc}",
        )
    if not isinstance(payload, dict):
        return SystemSkillReceiptInspection(
            status="corrupt",
            path=path,
            receipt=None,
            message="System-skill receipt must be a JSON object.",
        )
    schema_version = payload.get("schema_version")
    if schema_version == LEGACY_V3_RECEIPT_SCHEMA_VERSION:
        try:
            legacy = _parse_legacy_v3_receipt(
                cast(dict[str, Any], payload),
                expected_tool=tool,
                expected_home=resolved_home,
            )
        except (KeyError, TypeError, ValueError, SystemSkillInstallError) as exc:
            return SystemSkillReceiptInspection(
                status="corrupt",
                path=path,
                receipt=None,
                message=str(exc),
            )
        return SystemSkillReceiptInspection(
            status="legacy-v3",
            path=path,
            receipt=None,
            message="Receipt owns a v3 composed installation; run system-skills upgrade.",
            legacy_pack_ids=legacy.selected_pack_ids,
            legacy_owned_paths=tuple(
                relative_path
                for record in legacy.skills
                for relative_path in record.owned_relative_paths
            ),
        )
    if schema_version != SYSTEM_SKILL_RECEIPT_SCHEMA_VERSION:
        return SystemSkillReceiptInspection(
            status="unsupported",
            path=path,
            receipt=None,
            message=f"Unsupported system-skill receipt schema `{schema_version}`.",
        )
    try:
        receipt = _parse_receipt_payload(
            cast(dict[str, Any], payload),
            expected_tool=tool,
            expected_home=resolved_home,
        )
    except (KeyError, TypeError, ValueError, SystemSkillInstallError) as exc:
        return SystemSkillReceiptInspection(
            status="corrupt",
            path=path,
            receipt=None,
            message=str(exc),
        )
    return SystemSkillReceiptInspection(status="current", path=path, receipt=receipt)


def inspect_system_skill_packs(
    *,
    tool: str,
    home_path: Path,
) -> SystemSkillStatusResult:
    """Classify static members, actor packs, receipt posture, and legacy flat paths."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    receipt_inspection = inspect_system_skill_receipt(tool=tool, home_path=resolved_home)
    receipt = receipt_inspection.receipt
    receipt_map = receipt.skill_map() if receipt is not None else {}
    member_statuses: list[SystemSkillMemberStatusRecord] = []
    status_by_name: dict[str, MemberIntegrityStatus] = {}
    for record in manifest.standalone_skills.values():
        relative_path = projected_standalone_skill_relative_dir(
            tool=tool,
            skill_name=record.name,
        )
        receipt_record = receipt_map.get(record.name)
        if receipt_inspection.status == "legacy-v3":
            status: MemberIntegrityStatus = (
                "drifted"
                if record.name
                in {
                    "houmao-admin-welcome",
                    "houmao-admin-entrypoint",
                    "houmao-agent-entrypoint",
                }
                and relative_path in receipt_inspection.legacy_owned_paths
                else "conflicting"
                if _path_lexists(resolved_home / relative_path)
                else "absent"
            )
            owners = tuple(
                pack_id
                for pack_id in receipt_inspection.legacy_pack_ids
                if record.name in manifest.packs[pack_id].standalone_skill_names
            )
            mode: SystemSkillProjectionMode | None = None
            digest: str | None = None
        elif receipt_record is None:
            status = "conflicting" if _path_lexists(resolved_home / relative_path) else "absent"
            owners = ()
            mode = None
            digest = None
        else:
            status = _inspect_current_member(
                manifest=manifest,
                home_path=resolved_home,
                record=receipt_record,
            )
            owners = receipt_record.owning_pack_ids
            mode = receipt_record.projection_mode
            digest = receipt_record.content_digest
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
        if receipt_inspection.status == "legacy-v3" and pack.pack_id in (
            receipt_inspection.legacy_pack_ids
        ):
            pack_status: PackIntegrityStatus = "drifted"
        elif receipt is not None and pack.pack_id not in receipt.selected_pack_ids:
            unowned_conflicts = any(
                status_by_name[name] == "conflicting"
                for name in pack.standalone_skill_names
                if not receipt_map.get(name)
            )
            pack_status = "conflicting" if unowned_conflicts else "absent"
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
        receipt=receipt_inspection,
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
    """Upgrade v3 composition or refresh v4 while removing safe flat legacy paths."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    inspection = inspect_system_skill_receipt(tool=tool, home_path=resolved_home)
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
    if inspection.status == "legacy-v3":
        payload = _read_receipt_payload(inspection.path)
        legacy_v3 = _parse_legacy_v3_receipt(
            payload,
            expected_tool=tool,
            expected_home=resolved_home,
        )
        conflicts = tuple(
            record.relative_path
            for record in legacy_v3.skills
            if _inspect_legacy_v3_record(resolved_home, record) != "complete"
        )
        if conflicts:
            rendered = ", ".join(conflicts)
            raise SystemSkillInstallError(
                f"V3 receipt-owned content is incomplete or modified: {rendered}."
            )
        selected = (
            resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids)
            if pack_ids
            else resolve_system_skill_pack_selection(
                manifest,
                pack_ids=legacy_v3.selected_pack_ids,
            )
        )
        result = _apply_static_transaction(
            manifest=manifest,
            tool=tool,
            home_path=resolved_home,
            selected_pack_ids=selected,
            projection_mode=projection_mode,
            exact=True,
            allow_replace_drifted=True,
            legacy_paths_to_remove=safe_legacy_paths,
            legacy_v3=legacy_v3,
        )
        _remove_empty_v3_materialization_dirs(tool=tool, home_path=resolved_home)
        obsolete = tuple(
            relative_path
            for record in legacy_v3.skills
            for relative_path in record.owned_relative_paths
            if relative_path not in result.projected_relative_dirs
        )
        return SystemSkillUpgradeResult(
            install=result,
            legacy_before=legacy_before,
            preserved_legacy_paths=preserved,
            migrated_v3=True,
            removed_obsolete_paths=obsolete,
        )
    if inspection.status in {"corrupt", "unsupported"}:
        raise SystemSkillInstallError(
            inspection.message or "The system-skill receipt cannot be upgraded safely."
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
    inspection = inspect_system_skill_receipt(tool=tool, home_path=resolved_home)
    if inspection.status in {"corrupt", "unsupported", "legacy-v3"}:
        raise SystemSkillInstallError(
            inspection.message or "The system-skill receipt cannot be uninstalled safely."
        )
    receipt = inspection.receipt
    if receipt is None:
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
            receipt_path=inspection.path,
        )
    requested = (
        resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids)
        if pack_ids
        else receipt.selected_pack_ids
    )
    present_requested = tuple(
        pack_id for pack_id in requested if pack_id in receipt.selected_pack_ids
    )
    absent = tuple(pack_id for pack_id in requested if pack_id not in receipt.selected_pack_ids)
    new_pack_ids = tuple(
        pack_id for pack_id in receipt.selected_pack_ids if pack_id not in present_requested
    )
    updated_records: list[SystemSkillReceiptSkillRecord] = []
    removable_records: list[SystemSkillReceiptSkillRecord] = []
    retained_shared: list[str] = []
    conflicts: list[str] = []
    for record in receipt.skills:
        owners = tuple(owner for owner in record.owning_pack_ids if owner not in present_requested)
        if owners:
            updated_records.append(
                SystemSkillReceiptSkillRecord(
                    name=record.name,
                    role=record.role,
                    relative_path=record.relative_path,
                    projection_mode=record.projection_mode,
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
        )
        if integrity not in {"complete", "absent"}:
            conflicts.append(record.relative_path)
        else:
            removable_records.append(record)

    previous_receipt_bytes = inspection.path.read_bytes()
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
                updated_receipt = SystemSkillReceipt(
                    schema_version=SYSTEM_SKILL_RECEIPT_SCHEMA_VERSION,
                    manifest_schema_version=manifest.schema_version,
                    package_version=_package_version(),
                    tool=tool,
                    home_path=resolved_home,
                    updated_at=_utc_now(),
                    projection_mode=receipt.projection_mode,
                    selected_pack_ids=new_pack_ids,
                    skills=ordered_updated_records,
                    safely_removed_legacy_paths=receipt.safely_removed_legacy_paths,
                )
                _persist_receipt_atomic(updated_receipt)
            elif inspection.path.exists():
                inspection.path.unlink()
        except Exception:
            _restore_backups(backups)
            _restore_receipt_bytes(inspection.path, previous_receipt_bytes)
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
        receipt_path=inspection.path,
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
    legacy_v3: _LegacyV3Receipt | None = None,
) -> SystemSkillInstallResult:
    """Stage, preflight, commit, write receipt last, and roll back one union."""

    _validate_projection_mode(projection_mode)
    if not selected_pack_ids and not exact:
        raise SystemSkillInstallError("At least one system-skill pack must be selected.")
    resolved_home = home_path.resolve()
    resolved_home.mkdir(parents=True, exist_ok=True)
    system_skills_destination_for_tool(tool)
    state_root = system_skill_state_root(tool=tool, home_path=resolved_home)
    state_root.mkdir(parents=True, exist_ok=True)
    inspection = inspect_system_skill_receipt(tool=tool, home_path=resolved_home)
    if legacy_v3 is None and inspection.status in {"corrupt", "unsupported", "legacy-v3"}:
        raise SystemSkillInstallError(
            inspection.message or "The system-skill receipt cannot be used safely."
        )
    previous_receipt = inspection.receipt if legacy_v3 is None else None
    previous_pack_ids = previous_receipt.selected_pack_ids if previous_receipt is not None else ()
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
    previous_map = previous_receipt.skill_map() if previous_receipt is not None else {}
    legacy_owned_by_relative = (
        {record.relative_path: record for record in legacy_v3.skills}
        if legacy_v3 is not None
        else {}
    )
    previous_receipt_bytes = inspection.path.read_bytes() if inspection.path.exists() else None
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
            legacy_record = legacy_owned_by_relative.get(relative_path)
            if _path_lexists(target) and current_record is None and legacy_record is None:
                raise SystemSkillInstallError(
                    f"Untracked system-skill collision at `{target}`. Move or remove it before "
                    "installing the owning pack."
                )
            if current_record is not None:
                integrity = _inspect_current_member(
                    manifest=manifest,
                    home_path=resolved_home,
                    record=current_record,
                )
                if integrity == "conflicting" or (
                    integrity in {"incomplete", "drifted"} and not allow_replace_drifted
                ):
                    raise SystemSkillInstallError(
                        f"Receipt-owned system skill `{relative_path}` is {integrity}; use "
                        "sync or upgrade for explicit replacement."
                    )

        obsolete_relative_paths: list[str] = []
        if previous_receipt is not None:
            obsolete_relative_paths.extend(
                record.relative_path
                for record in previous_receipt.skills
                if record.name not in final_names
            )
        if legacy_v3 is not None:
            obsolete_relative_paths.extend(
                relative_path
                for record in legacy_v3.skills
                for relative_path in record.owned_relative_paths
                if relative_path
                not in {
                    projected_standalone_skill_relative_dir(tool=tool, skill_name=name)
                    for name in final_names
                }
            )

        affected_paths: list[Path] = []
        if previous_receipt is not None:
            affected_paths.extend(
                resolved_home / record.relative_path for record in previous_receipt.skills
            )
        if legacy_v3 is not None:
            affected_paths.extend(
                resolved_home / relative_path
                for record in legacy_v3.skills
                for relative_path in record.owned_relative_paths
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
                prior_legacy = (
                    previous_receipt.safely_removed_legacy_paths
                    if previous_receipt is not None
                    else ()
                )
                receipt = SystemSkillReceipt(
                    schema_version=SYSTEM_SKILL_RECEIPT_SCHEMA_VERSION,
                    manifest_schema_version=manifest.schema_version,
                    package_version=_package_version(),
                    tool=tool,
                    home_path=resolved_home,
                    updated_at=_utc_now(),
                    projection_mode=projection_mode,
                    selected_pack_ids=final_pack_ids,
                    skills=tuple(
                        SystemSkillReceiptSkillRecord(
                            name=record.name,
                            role=record.role,
                            relative_path=projected_standalone_skill_relative_dir(
                                tool=tool,
                                skill_name=record.name,
                            ),
                            projection_mode=projection_mode,
                            content_digest=record.content_digest,
                            owning_pack_ids=record.owning_pack_ids,
                        )
                        for record in staged.skills
                    ),
                    safely_removed_legacy_paths=tuple(
                        dict.fromkeys((*prior_legacy, *safe_legacy_relative_paths))
                    ),
                )
                _persist_receipt_atomic(receipt)
            elif inspection.path.exists():
                inspection.path.unlink()
        except Exception:
            for path in reversed(committed_paths):
                _remove_path(path)
            _restore_backups(backups)
            _restore_receipt_bytes(inspection.path, previous_receipt_bytes)
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
        receipt_path=system_skill_receipt_path(tool=tool, home_path=resolved_home),
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


def _parse_receipt_payload(
    payload: dict[str, Any],
    *,
    expected_tool: str,
    expected_home: Path,
) -> SystemSkillReceipt:
    """Parse and strictly validate one current static receipt."""

    required_keys = {
        "schema_version",
        "manifest_schema_version",
        "package_version",
        "tool",
        "home_path",
        "updated_at",
        "projection_mode",
        "selected_packs",
        "skills",
        "safely_removed_legacy_paths",
    }
    if set(payload) != required_keys:
        raise SystemSkillInstallError("System-skill receipt has missing or unknown fields.")
    if payload["tool"] != expected_tool:
        raise SystemSkillInstallError("System-skill receipt tool does not match its location.")
    if Path(_require_string(payload, "home_path")).resolve() != expected_home:
        raise SystemSkillInstallError("System-skill receipt home does not match its location.")
    mode = payload["projection_mode"]
    if mode not in {"copy", "symlink"}:
        raise SystemSkillInstallError("System-skill receipt projection mode is invalid.")
    selected = _require_string_list(payload, "selected_packs")
    raw_skills = payload["skills"]
    if not isinstance(raw_skills, list):
        raise SystemSkillInstallError("System-skill receipt skills must be a list.")
    skill_records = tuple(
        _parse_receipt_skill(item, collection_mode=cast(SystemSkillProjectionMode, mode))
        for item in raw_skills
    )
    if len({record.name for record in skill_records}) != len(skill_records):
        raise SystemSkillInstallError("System-skill receipt has duplicate standalone names.")
    manifest = load_system_skill_manifest()
    resolve_system_skill_pack_selection(manifest, pack_ids=selected)
    if _require_string(payload, "manifest_schema_version") != manifest.schema_version:
        raise SystemSkillInstallError(
            "System-skill receipt manifest schema does not match the current static manifest."
        )
    expected_records = resolve_system_skill_pack_members(manifest, pack_ids=selected)
    if tuple(record.name for record in skill_records) != tuple(
        record.name for record in expected_records
    ):
        raise SystemSkillInstallError(
            "System-skill receipt skills do not match the selected static pack union."
        )
    expected_by_name = {record.name: record for record in expected_records}
    for record in skill_records:
        expected_record = expected_by_name[record.name]
        if record.role != expected_record.role:
            raise SystemSkillInstallError(
                f"Receipt role for `{record.name}` does not match the static manifest."
            )
        expected_relative_path = projected_standalone_skill_relative_dir(
            tool=expected_tool,
            skill_name=record.name,
        )
        if record.relative_path != expected_relative_path:
            raise SystemSkillInstallError(
                f"Receipt path for `{record.name}` does not match its canonical destination."
            )
        expected_owners = tuple(
            pack_id
            for pack_id in selected
            if record.name in manifest.packs[pack_id].standalone_skill_names
        )
        if record.owning_pack_ids != expected_owners:
            raise SystemSkillInstallError(
                f"Receipt owner set for `{record.name}` does not match selected packs."
            )
    return SystemSkillReceipt(
        schema_version=_require_string(payload, "schema_version"),
        manifest_schema_version=_require_string(payload, "manifest_schema_version"),
        package_version=_require_string(payload, "package_version"),
        tool=expected_tool,
        home_path=expected_home,
        updated_at=_require_string(payload, "updated_at"),
        projection_mode=cast(SystemSkillProjectionMode, mode),
        selected_pack_ids=selected,
        skills=skill_records,
        safely_removed_legacy_paths=_require_string_list(
            payload,
            "safely_removed_legacy_paths",
        ),
    )


def _parse_receipt_skill(
    payload: object,
    *,
    collection_mode: SystemSkillProjectionMode,
) -> SystemSkillReceiptSkillRecord:
    """Parse one strict standalone receipt record."""

    if not isinstance(payload, dict) or set(payload) != {
        "name",
        "role",
        "relative_path",
        "projection_mode",
        "content_digest",
        "owning_pack_ids",
    }:
        raise SystemSkillInstallError("System-skill receipt has an invalid skill record.")
    role = payload["role"]
    if role not in {"welcome", "entrypoint", "shared-routines", "loop"}:
        raise SystemSkillInstallError("System-skill receipt skill role is invalid.")
    if payload["projection_mode"] != collection_mode:
        raise SystemSkillInstallError(
            "System-skill receipt mixes projection modes in one static collection."
        )
    digest = _require_string(cast(dict[str, Any], payload), "content_digest")
    _validate_digest(digest)
    owners = _require_string_list(cast(dict[str, Any], payload), "owning_pack_ids")
    if not owners:
        raise SystemSkillInstallError("Receipt standalone owner sets must not be empty.")
    return SystemSkillReceiptSkillRecord(
        name=_require_string(cast(dict[str, Any], payload), "name"),
        role=cast(StandaloneSkillRole, role),
        relative_path=_require_safe_relative_path(
            cast(dict[str, Any], payload),
            "relative_path",
        ),
        projection_mode=collection_mode,
        content_digest=digest,
        owning_pack_ids=owners,
    )


def _parse_legacy_v3_receipt(
    payload: dict[str, Any],
    *,
    expected_tool: str,
    expected_home: Path,
) -> _LegacyV3Receipt:
    """Parse enough v3 receipt evidence for safe migration."""

    if payload.get("schema_version") != LEGACY_V3_RECEIPT_SCHEMA_VERSION:
        raise SystemSkillInstallError("Receipt is not a recognized v3 composition receipt.")
    if payload.get("tool") != expected_tool:
        raise SystemSkillInstallError("V3 receipt tool does not match its location.")
    raw_home = payload.get("home_path")
    if not isinstance(raw_home, str) or Path(raw_home).resolve() != expected_home:
        raise SystemSkillInstallError("V3 receipt home does not match its location.")
    selected = payload.get("selected_packs")
    if not isinstance(selected, list) or not all(
        isinstance(item, str) and item in {"admin", "agent"} for item in selected
    ):
        raise SystemSkillInstallError("V3 receipt has invalid selected packs.")
    selected_pack_ids = tuple(cast(list[str], selected))
    if len(selected_pack_ids) != len(set(selected_pack_ids)):
        raise SystemSkillInstallError("V3 receipt has duplicate selected packs.")
    raw_packs = payload.get("packs")
    if not isinstance(raw_packs, list):
        raise SystemSkillInstallError("V3 receipt has invalid pack records.")
    records: list[_LegacyV3SkillRecord] = []
    for raw_pack in raw_packs:
        if not isinstance(raw_pack, dict):
            raise SystemSkillInstallError("V3 receipt has an invalid pack record.")
        raw_public = raw_pack.get("public_skills")
        if not isinstance(raw_public, list):
            raise SystemSkillInstallError("V3 receipt pack has invalid public records.")
        for raw_record in raw_public:
            if not isinstance(raw_record, dict):
                raise SystemSkillInstallError("V3 receipt has an invalid public record.")
            mode = raw_record.get("projection_mode")
            if mode not in {"copy", "symlink"}:
                raise SystemSkillInstallError("V3 receipt public projection mode is invalid.")
            digest = raw_record.get("content_digest")
            if not isinstance(digest, str):
                raise SystemSkillInstallError("V3 receipt content digest is invalid.")
            _validate_digest(digest)
            materialization = raw_record.get("materialization_relative_path")
            if materialization is not None and not isinstance(materialization, str):
                raise SystemSkillInstallError("V3 receipt materialization path is invalid.")
            name = raw_record.get("name")
            relative_path = raw_record.get("relative_path")
            if not isinstance(name, str) or not isinstance(relative_path, str):
                raise SystemSkillInstallError("V3 receipt public identity is invalid.")
            records.append(
                _LegacyV3SkillRecord(
                    name=name,
                    relative_path=_validate_safe_relative_path(relative_path),
                    projection_mode=cast(SystemSkillProjectionMode, mode),
                    content_digest=digest,
                    materialization_relative_path=(
                        _validate_safe_relative_path(materialization)
                        if materialization is not None
                        else None
                    ),
                )
            )
    if len({record.relative_path for record in records}) != len(records):
        raise SystemSkillInstallError("V3 receipt has duplicate public paths.")
    return _LegacyV3Receipt(selected_pack_ids=selected_pack_ids, skills=tuple(records))


def _inspect_current_member(
    *,
    manifest: SystemSkillManifest,
    home_path: Path,
    record: SystemSkillReceiptSkillRecord,
) -> MemberIntegrityStatus:
    """Classify one receipt-owned static member against source and destination."""

    manifest_record = manifest.standalone_skills.get(record.name)
    if manifest_record is None:
        return "drifted"
    if record.content_digest != standalone_system_skill_content_digest(manifest, manifest_record):
        return "drifted"
    expected_relative_path = projected_standalone_skill_relative_dir(
        tool=_tool_from_receipt_relative_path(record.relative_path),
        skill_name=record.name,
    )
    if expected_relative_path != record.relative_path:
        return "conflicting"
    path = home_path / record.relative_path
    if not _path_lexists(path):
        return "absent"
    if record.projection_mode == "copy":
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


def _tool_from_receipt_relative_path(relative_path: str) -> str:
    """Return a tool whose destination root matches one receipt path."""

    destination = Path(relative_path).parts[0] if Path(relative_path).parts else ""
    for tool, root in _SYSTEM_SKILL_DESTINATION_BY_TOOL.items():
        if root == destination:
            return tool
    raise SystemSkillInstallError(f"Receipt path `{relative_path}` has an unknown skill root.")


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


def _inspect_legacy_v3_record(
    home_path: Path,
    record: _LegacyV3SkillRecord,
) -> Literal["complete", "missing", "drifted"]:
    """Validate one receipt-owned composed projection before upgrade."""

    path = home_path / record.relative_path
    if not _path_lexists(path):
        return "missing"
    content_root = path
    if record.projection_mode == "copy":
        if path.is_symlink() or not path.is_dir():
            return "drifted"
    else:
        if not path.is_symlink() or record.materialization_relative_path is None:
            return "drifted"
        materialization = home_path / record.materialization_relative_path
        if not materialization.is_dir() or materialization.is_symlink():
            return "missing"
        if _symlink_target(path) != materialization.resolve(strict=False):
            return "drifted"
        content_root = materialization
    try:
        digest = tree_content_digest(content_root)
    except SystemSkillManifestError:
        return "drifted"
    return "complete" if digest == record.content_digest else "drifted"


def _persist_receipt_atomic(receipt: SystemSkillReceipt) -> None:
    """Write one receipt atomically in its tool-scoped state directory."""

    path = receipt.path
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(receipt.to_payload(), handle, indent=2, sort_keys=True)
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


def _restore_receipt_bytes(path: Path, previous_bytes: bytes | None) -> None:
    """Restore previous receipt bytes after transaction failure."""

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


def _remove_empty_v3_materialization_dirs(*, tool: str, home_path: Path) -> None:
    """Remove only empty directory shells left by a migrated v3 symlink receipt."""

    root = system_skill_state_root(tool=tool, home_path=home_path) / "materialized"
    if not root.is_dir() or root.is_symlink():
        return
    directories = sorted(
        (path for path in root.rglob("*") if path.is_dir() and not path.is_symlink()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for path in (*directories, root):
        try:
            path.rmdir()
        except OSError:
            continue


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
        raise SystemSkillInstallError(f"Receipt field `{key}` must be a non-empty string.")
    return value


def _require_string_list(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    """Read one required unique string-list field."""

    value = payload[key]
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise SystemSkillInstallError(f"Receipt field `{key}` must be a string list.")
    result = tuple(cast(list[str], value))
    if len(result) != len(set(result)):
        raise SystemSkillInstallError(f"Receipt field `{key}` must not contain duplicates.")
    return result


def _require_safe_relative_path(payload: dict[str, Any], key: str) -> str:
    """Read and validate one home-relative receipt path."""

    return _validate_safe_relative_path(_require_string(payload, key))


def _validate_safe_relative_path(value: str) -> str:
    """Reject absolute and escaping receipt paths."""

    path = Path(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise SystemSkillInstallError(f"Receipt path `{value}` is unsafe.")
    return value


def _validate_digest(value: str) -> None:
    """Require one lowercase SHA-256 digest."""

    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise SystemSkillInstallError("System-skill receipt content digest is invalid.")


def _read_receipt_payload(path: Path) -> dict[str, Any]:
    """Read one already-inspected JSON receipt object."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemSkillInstallError("System-skill receipt must be a JSON object.")
    return cast(dict[str, Any], payload)


def _package_version() -> str:
    """Return the installed Houmao package version for receipt evidence."""

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


def _utc_now() -> str:
    """Return a stable UTC receipt timestamp."""

    return datetime.now(UTC).isoformat()
