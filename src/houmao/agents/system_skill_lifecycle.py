"""Transactional lifecycle and receipt ownership for Houmao system-skill packs."""

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
    AutoInstallKind,
    ComposedSystemSkillPack,
    PackAudience,
    PublicSkillRole,
    SystemSkillManifest,
    SystemSkillManifestError,
    compose_system_skill_pack,
    load_legacy_system_skill_catalog,
    load_system_skill_manifest,
    protected_routine_closure,
    resolve_system_skill_pack_selection,
    tree_content_digest,
)


SYSTEM_SKILL_RECEIPT_SCHEMA_VERSION = "houmao-system-skills-receipt.v1"
SYSTEM_SKILL_RECEIPT_FILENAME = "receipt.json"
SystemSkillProjectionMode = Literal["copy", "symlink"]
ReceiptInspectionStatus = Literal["absent", "current", "corrupt", "unsupported"]
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
    """Raised when a pack lifecycle transaction cannot complete safely."""


@dataclass(frozen=True)
class SystemSkillReceiptPublicRecord:
    """Receipt ownership and integrity evidence for one public projection."""

    name: str
    role: PublicSkillRole
    relative_path: str
    projection_mode: SystemSkillProjectionMode
    content_digest: str
    protected_logical_ids: tuple[str, ...]
    materialization_relative_path: str | None = None

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe record payload."""

        return {
            "name": self.name,
            "role": self.role,
            "relative_path": self.relative_path,
            "projection_mode": self.projection_mode,
            "content_digest": self.content_digest,
            "protected_logical_ids": list(self.protected_logical_ids),
            "materialization_relative_path": self.materialization_relative_path,
        }


@dataclass(frozen=True)
class SystemSkillReceiptPackRecord:
    """Receipt record for one complete audience pack."""

    pack_id: str
    audience: PackAudience
    public_skills: tuple[SystemSkillReceiptPublicRecord, ...]

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-safe record payload."""

        return {
            "pack_id": self.pack_id,
            "audience": self.audience,
            "public_skills": [record.to_payload() for record in self.public_skills],
        }


@dataclass(frozen=True)
class SystemSkillReceipt:
    """Tool-scoped ownership receipt for installed Houmao packs."""

    schema_version: str
    manifest_schema_version: str
    package_version: str
    tool: str
    home_path: Path
    updated_at: str
    packs: tuple[SystemSkillReceiptPackRecord, ...]
    safely_removed_legacy_paths: tuple[str, ...] = ()

    @property
    def selected_pack_ids(self) -> tuple[str, ...]:
        """Return receipt-owned pack ids."""

        return tuple(record.pack_id for record in self.packs)

    @property
    def path(self) -> Path:
        """Return the canonical receipt path."""

        return system_skill_receipt_path(tool=self.tool, home_path=self.home_path)

    def pack_map(self) -> dict[str, SystemSkillReceiptPackRecord]:
        """Return receipt pack records keyed by pack id."""

        return {record.pack_id: record for record in self.packs}

    def public_ownership_map(
        self,
    ) -> dict[str, tuple[SystemSkillReceiptPackRecord, SystemSkillReceiptPublicRecord]]:
        """Return receipt public projections keyed by home-relative path."""

        return {
            public.relative_path: (pack, public)
            for pack in self.packs
            for public in pack.public_skills
        }

    def to_payload(self) -> dict[str, object]:
        """Return the complete JSON-safe receipt payload."""

        return {
            "schema_version": self.schema_version,
            "manifest_schema_version": self.manifest_schema_version,
            "package_version": self.package_version,
            "tool": self.tool,
            "home_path": str(self.home_path),
            "updated_at": self.updated_at,
            "selected_packs": list(self.selected_pack_ids),
            "packs": [record.to_payload() for record in self.packs],
            "safely_removed_legacy_paths": list(self.safely_removed_legacy_paths),
        }


@dataclass(frozen=True)
class SystemSkillReceiptInspection:
    """Read-only receipt parse result suitable for status output."""

    status: ReceiptInspectionStatus
    path: Path
    receipt: SystemSkillReceipt | None
    message: str | None = None


@dataclass(frozen=True)
class SystemSkillPackStatusRecord:
    """Observed integrity state for one manifest pack."""

    pack_id: str
    status: PackIntegrityStatus
    public_paths: tuple[str, ...]
    missing_public_paths: tuple[str, ...]
    drifted_public_paths: tuple[str, ...]
    conflicting_public_paths: tuple[str, ...]
    protected_logical_ids: tuple[str, ...]


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
    """Receipt, pack integrity, and legacy evidence for one tool home."""

    tool: str
    home_path: Path
    receipt: SystemSkillReceiptInspection
    packs: tuple[SystemSkillPackStatusRecord, ...]
    legacy: LegacySystemSkillInspection


@dataclass(frozen=True)
class SystemSkillInstallResult:
    """Outcome of installing or refreshing selected complete packs."""

    tool: str
    home_path: Path
    selected_pack_ids: tuple[str, ...]
    public_skill_names: tuple[str, ...]
    projected_relative_dirs: tuple[str, ...]
    receipt_path: Path
    projection_mode: SystemSkillProjectionMode
    protected_logical_ids_by_public: dict[str, tuple[str, ...]]
    removed_pack_ids: tuple[str, ...] = ()
    removed_projected_relative_dirs: tuple[str, ...] = ()
    safely_removed_legacy_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class SystemSkillUpgradeResult:
    """Outcome of refreshing packs and conservatively migrating legacy paths."""

    install: SystemSkillInstallResult
    legacy_before: LegacySystemSkillInspection
    preserved_legacy_paths: tuple[str, ...]


@dataclass(frozen=True)
class SystemSkillUninstallResult:
    """Outcome of removing selected receipt-owned packs."""

    tool: str
    home_path: Path
    requested_pack_ids: tuple[str, ...]
    removed_pack_ids: tuple[str, ...]
    absent_pack_ids: tuple[str, ...]
    removed_projected_relative_dirs: tuple[str, ...]
    preserved_conflicting_paths: tuple[str, ...]
    receipt_path: Path


def system_skills_destination_for_tool(tool: str) -> str:
    """Return the visible skill-root directory for one supported tool."""

    destination = _SYSTEM_SKILL_DESTINATION_BY_TOOL.get(tool)
    if destination is None:
        raise SystemSkillInstallError(f"Unsupported tool `{tool}` for system-skill packs.")
    return destination


def projected_public_skill_relative_dir(*, tool: str, public_skill_name: str) -> str:
    """Return one home-relative public projection path."""

    manifest = load_system_skill_manifest()
    if public_skill_name not in manifest.public_skills:
        if public_skill_name in manifest.protected_routines:
            raise SystemSkillInstallError(
                f"Protected routine `{public_skill_name}` has no top-level projection."
            )
        raise SystemSkillInstallError(f"Unknown public system skill `{public_skill_name}`.")
    return str(Path(system_skills_destination_for_tool(tool)) / public_skill_name)


def system_skill_state_root(*, tool: str, home_path: Path) -> Path:
    """Return the tool-scoped hidden ownership directory."""

    system_skills_destination_for_tool(tool)
    return home_path.resolve() / ".houmao" / "system-skills" / tool


def system_skill_receipt_path(*, tool: str, home_path: Path) -> Path:
    """Return the tool-scoped pack receipt path."""

    return system_skill_state_root(tool=tool, home_path=home_path) / SYSTEM_SKILL_RECEIPT_FILENAME


def system_skill_materialization_root(*, tool: str, home_path: Path) -> Path:
    """Return the receipt-owned symlink materialization root."""

    return system_skill_state_root(tool=tool, home_path=home_path) / "materialized"


def inspect_system_skill_receipt(
    *,
    tool: str,
    home_path: Path,
) -> SystemSkillReceiptInspection:
    """Read one receipt without mutating or raising for corrupt state."""

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
    if schema_version != SYSTEM_SKILL_RECEIPT_SCHEMA_VERSION:
        return SystemSkillReceiptInspection(
            status="unsupported",
            path=path,
            receipt=None,
            message=f"Unsupported system-skill receipt schema `{schema_version}`.",
        )
    try:
        receipt = _parse_receipt_payload(
            payload,
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
    """Classify every manifest pack and all observed legacy flat paths."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    receipt_inspection = inspect_system_skill_receipt(tool=tool, home_path=resolved_home)
    receipt_map = (
        receipt_inspection.receipt.pack_map() if receipt_inspection.receipt is not None else {}
    )
    pack_statuses: list[SystemSkillPackStatusRecord] = []
    for pack in manifest.packs.values():
        expected_paths = tuple(
            projected_public_skill_relative_dir(tool=tool, public_skill_name=name)
            for name in pack.public_skill_names
        )
        receipt_record = receipt_map.get(pack.pack_id)
        if receipt_record is None:
            conflicts = tuple(
                relative_path
                for relative_path in expected_paths
                if _path_lexists(resolved_home / relative_path)
            )
            pack_statuses.append(
                SystemSkillPackStatusRecord(
                    pack_id=pack.pack_id,
                    status="conflicting" if conflicts else "absent",
                    public_paths=expected_paths,
                    missing_public_paths=(),
                    drifted_public_paths=(),
                    conflicting_public_paths=conflicts,
                    protected_logical_ids=(),
                )
            )
            continue
        missing: list[str] = []
        drifted: list[str] = []
        protected_ids: list[str] = []
        receipt_public_names = {record.name for record in receipt_record.public_skills}
        if receipt_public_names != set(pack.public_skill_names):
            drifted.extend(expected_paths)
        for public in receipt_record.public_skills:
            protected_ids.extend(public.protected_logical_ids)
            integrity = _inspect_public_record(resolved_home, public)
            if integrity == "missing":
                missing.append(public.relative_path)
            elif integrity == "drifted":
                drifted.append(public.relative_path)
        if (
            receipt_inspection.receipt is not None
            and receipt_inspection.receipt.manifest_schema_version != manifest.schema_version
        ):
            drifted.extend(expected_paths)
        expected_protected = tuple(
            routine.logical_id
            for routine in protected_routine_closure(manifest, audience=pack.audience)
        )
        entrypoint_records = [
            record for record in receipt_record.public_skills if record.role == "entrypoint"
        ]
        if len(entrypoint_records) != 1 or (
            entrypoint_records[0].protected_logical_ids != expected_protected
        ):
            drifted.extend(record.relative_path for record in entrypoint_records)
        if missing:
            status: PackIntegrityStatus = "incomplete"
        elif drifted:
            status = "drifted"
        else:
            status = "complete"
        pack_statuses.append(
            SystemSkillPackStatusRecord(
                pack_id=pack.pack_id,
                status=status,
                public_paths=expected_paths,
                missing_public_paths=tuple(dict.fromkeys(missing)),
                drifted_public_paths=tuple(dict.fromkeys(drifted)),
                conflicting_public_paths=(),
                protected_logical_ids=tuple(dict.fromkeys(protected_ids)),
            )
        )
    return SystemSkillStatusResult(
        tool=tool,
        home_path=resolved_home,
        receipt=receipt_inspection,
        packs=tuple(pack_statuses),
        legacy=inspect_legacy_system_skill_paths(tool=tool, home_path=resolved_home),
    )


def inspect_legacy_system_skill_paths(
    *,
    tool: str,
    home_path: Path,
) -> LegacySystemSkillInspection:
    """Classify legacy paths without mutating them."""

    manifest = load_system_skill_manifest()
    legacy_catalog = load_legacy_system_skill_catalog()
    resolved_home = home_path.resolve()
    skill_root = resolved_home / system_skills_destination_for_tool(tool)
    package_root = _packaged_asset_filesystem_root()
    paths: list[LegacySystemSkillPathStatus] = []
    known_names = set(manifest.legacy_skills)
    for legacy in manifest.legacy_skills.values():
        path = skill_root / legacy.name
        if not _path_lexists(path):
            continue
        if path.is_symlink():
            raw_target = path.readlink()
            target = (
                raw_target if raw_target.is_absolute() else (path.parent / raw_target)
            ).resolve(strict=False)
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
        public_names = set(manifest.public_skills)
        for path in sorted(skill_root.glob("houmao-*")):
            if (
                path.name in known_names
                or path.name in public_names
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
    current_v1_names = {record.name for record in legacy_catalog.skills}
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
    """Install or refresh complete selected packs and preserve other owned packs."""

    manifest = load_system_skill_manifest()
    selected = _resolve_requested_pack_ids(
        manifest,
        pack_ids=pack_ids,
        use_cli_default=use_cli_default,
        auto_install_kind=auto_install_kind,
    )
    return _apply_pack_transaction(
        manifest=manifest,
        tool=tool,
        home_path=home_path,
        selected_pack_ids=selected,
        projection_mode=projection_mode,
        exact=False,
        legacy_paths_to_remove=(),
    )


def sync_system_skill_packs_for_home(
    *,
    tool: str,
    home_path: Path,
    selected_pack_ids: Sequence[str],
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillInstallResult:
    """Synchronize a managed home to an exact receipt-owned pack selection."""

    manifest = load_system_skill_manifest()
    selected = resolve_system_skill_pack_selection(manifest, pack_ids=selected_pack_ids)
    return _apply_pack_transaction(
        manifest=manifest,
        tool=tool,
        home_path=home_path,
        selected_pack_ids=selected,
        projection_mode=projection_mode,
        exact=True,
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
    """Refresh selected packs and remove only safely classified legacy paths."""

    manifest = load_system_skill_manifest()
    selected = _resolve_requested_pack_ids(
        manifest,
        pack_ids=pack_ids,
        use_cli_default=use_cli_default,
        auto_install_kind=None,
    )
    resolved_home = home_path.resolve()
    legacy = inspect_legacy_system_skill_paths(tool=tool, home_path=resolved_home)
    safe_records = [
        record
        for record in legacy.paths
        if record.classification in {"package-linked", "digest-matched"}
    ]
    result = _apply_pack_transaction(
        manifest=manifest,
        tool=tool,
        home_path=resolved_home,
        selected_pack_ids=selected,
        projection_mode=projection_mode,
        exact=False,
        legacy_paths_to_remove=tuple(
            resolved_home / record.relative_path for record in safe_records
        ),
    )
    preserved = tuple(
        record.relative_path
        for record in legacy.paths
        if record.classification in {"modified", "unknown"}
    )
    return SystemSkillUpgradeResult(
        install=result,
        legacy_before=legacy,
        preserved_legacy_paths=preserved,
    )


def uninstall_system_skill_packs_for_home(
    *,
    tool: str,
    home_path: Path,
    pack_ids: Sequence[str] = (),
) -> SystemSkillUninstallResult:
    """Remove selected receipt-owned packs and preserve ownership conflicts."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    inspection = inspect_system_skill_receipt(tool=tool, home_path=resolved_home)
    if inspection.status in {"corrupt", "unsupported"}:
        raise SystemSkillInstallError(
            inspection.message or "The system-skill receipt cannot be used safely."
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
            preserved_conflicting_paths=(),
            receipt_path=inspection.path,
        )
    requested = (
        resolve_system_skill_pack_selection(manifest, pack_ids=pack_ids)
        if pack_ids
        else receipt.selected_pack_ids
    )
    receipt_map = receipt.pack_map()
    absent = tuple(pack_id for pack_id in requested if pack_id not in receipt_map)
    removable: list[SystemSkillReceiptPackRecord] = []
    conflicts: list[str] = []
    for pack_id in requested:
        record = receipt_map.get(pack_id)
        if record is None:
            continue
        pack_conflicts = [
            public.relative_path
            for public in record.public_skills
            if _public_path_has_ownership_conflict(resolved_home, public)
        ]
        if pack_conflicts:
            conflicts.extend(pack_conflicts)
        else:
            removable.append(record)
    removed_paths: list[str] = []
    with _transaction_directory(tool=tool, home_path=resolved_home) as raw_transaction_root:
        transaction_root = Path(raw_transaction_root)
        backups_root = transaction_root / "backups"
        backups: list[tuple[Path, Path]] = []
        try:
            for pack in removable:
                for public in pack.public_skills:
                    for relative_path in _receipt_record_owned_paths(public):
                        original = resolved_home / relative_path
                        if not _path_lexists(original):
                            continue
                        backup = backups_root / str(len(backups))
                        _backup_path(original, backup)
                        backups.append((original, backup))
                    removed_paths.append(public.relative_path)
            removable_ids = {record.pack_id for record in removable}
            remaining = tuple(
                record for record in receipt.packs if record.pack_id not in removable_ids
            )
            if remaining:
                updated = SystemSkillReceipt(
                    schema_version=receipt.schema_version,
                    manifest_schema_version=receipt.manifest_schema_version,
                    package_version=_package_version(),
                    tool=tool,
                    home_path=resolved_home,
                    updated_at=_utc_now(),
                    packs=remaining,
                    safely_removed_legacy_paths=receipt.safely_removed_legacy_paths,
                )
                _persist_receipt_atomic(updated)
            elif inspection.path.exists():
                inspection.path.unlink()
        except Exception:
            _restore_backups(backups)
            raise
    return SystemSkillUninstallResult(
        tool=tool,
        home_path=resolved_home,
        requested_pack_ids=requested,
        removed_pack_ids=tuple(record.pack_id for record in removable),
        absent_pack_ids=absent,
        removed_projected_relative_dirs=tuple(removed_paths),
        preserved_conflicting_paths=tuple(conflicts),
        receipt_path=inspection.path,
    )


def project_system_skill_pack_to_destination(
    destination_root: Path,
    *,
    pack_id: str,
) -> tuple[str, ...]:
    """Compose one pack into an explicit non-home destination for fixture use."""

    manifest = load_system_skill_manifest()
    result = compose_system_skill_pack(
        manifest,
        pack_id=pack_id,
        destination_root=destination_root,
    )
    return tuple(record.name for record in result.public_skills)


def _apply_pack_transaction(
    *,
    manifest: SystemSkillManifest,
    tool: str,
    home_path: Path,
    selected_pack_ids: tuple[str, ...],
    projection_mode: SystemSkillProjectionMode,
    exact: bool,
    legacy_paths_to_remove: tuple[Path, ...],
) -> SystemSkillInstallResult:
    """Stage, preflight, commit, receipt, and roll back one pack transaction."""

    _validate_projection_mode(projection_mode)
    if not selected_pack_ids and not exact:
        raise SystemSkillInstallError("At least one system-skill pack must be selected.")
    resolved_home = home_path.resolve()
    resolved_home.mkdir(parents=True, exist_ok=True)
    system_skills_destination_for_tool(tool)
    state_root = system_skill_state_root(tool=tool, home_path=resolved_home)
    state_root.mkdir(parents=True, exist_ok=True)
    inspection = inspect_system_skill_receipt(tool=tool, home_path=resolved_home)
    if inspection.status in {"corrupt", "unsupported"}:
        raise SystemSkillInstallError(
            inspection.message or "The system-skill receipt cannot be used safely."
        )
    previous_receipt = inspection.receipt
    previous_pack_map = previous_receipt.pack_map() if previous_receipt is not None else {}
    ownership_map = previous_receipt.public_ownership_map() if previous_receipt is not None else {}
    removed_pack_ids = (
        tuple(pack_id for pack_id in previous_pack_map if pack_id not in selected_pack_ids)
        if exact
        else ()
    )
    with _transaction_directory(tool=tool, home_path=resolved_home) as raw_transaction_root:
        transaction_root = Path(raw_transaction_root)
        staged_root = transaction_root / "staged"
        composed_by_pack: dict[str, ComposedSystemSkillPack] = {}
        digest_by_public: dict[str, str] = {}
        for pack_id in selected_pack_ids:
            composed = compose_system_skill_pack(
                manifest,
                pack_id=pack_id,
                destination_root=staged_root / pack_id,
            )
            composed_by_pack[pack_id] = composed
            for public in composed.public_skills:
                digest_by_public[public.name] = tree_content_digest(public.path)
                relative_path = projected_public_skill_relative_dir(
                    tool=tool,
                    public_skill_name=public.name,
                )
                target = resolved_home / relative_path
                if _path_lexists(target) and relative_path not in ownership_map:
                    raise SystemSkillInstallError(
                        f"Untracked system-skill collision at `{target}`. "
                        "Move or remove it before installing the owning pack."
                    )
        backups_root = transaction_root / "backups"
        backups: list[tuple[Path, Path]] = []
        committed_paths: list[Path] = []
        previous_receipt_bytes = inspection.path.read_bytes() if inspection.path.exists() else None
        removed_relative_dirs: list[str] = []
        try:
            affected_pack_ids = set(selected_pack_ids) | set(removed_pack_ids)
            for pack_id in affected_pack_ids:
                old_pack = previous_pack_map.get(pack_id)
                if old_pack is None:
                    continue
                for old_public in old_pack.public_skills:
                    for relative_path in _receipt_record_owned_paths(old_public):
                        original = resolved_home / relative_path
                        if not _path_lexists(original):
                            continue
                        backup = backups_root / str(len(backups))
                        _backup_path(original, backup)
                        backups.append((original, backup))
                    if pack_id in removed_pack_ids:
                        removed_relative_dirs.append(old_public.relative_path)
            safe_legacy_relative_paths: list[str] = []
            for legacy_path in legacy_paths_to_remove:
                resolved_legacy = legacy_path.absolute()
                try:
                    legacy_relative_path = resolved_legacy.relative_to(resolved_home)
                except ValueError as exc:
                    raise SystemSkillInstallError(
                        f"Legacy cleanup path `{legacy_path}` escapes the target home."
                    ) from exc
                concrete_path = resolved_home / legacy_relative_path
                if not _path_lexists(concrete_path):
                    continue
                backup = backups_root / str(len(backups))
                _backup_path(concrete_path, backup)
                backups.append((concrete_path, backup))
                safe_legacy_relative_paths.append(str(legacy_relative_path))
            new_pack_records: dict[str, SystemSkillReceiptPackRecord] = {}
            for pack_id in selected_pack_ids:
                composed = composed_by_pack[pack_id]
                public_records: list[SystemSkillReceiptPublicRecord] = []
                for public in composed.public_skills:
                    relative_path = projected_public_skill_relative_dir(
                        tool=tool,
                        public_skill_name=public.name,
                    )
                    target = resolved_home / relative_path
                    materialization_relative_path: str | None = None
                    if projection_mode == "copy":
                        _commit_public_projection(public.path, target)
                        committed_paths.append(target)
                    else:
                        materialization = (
                            system_skill_materialization_root(
                                tool=tool,
                                home_path=resolved_home,
                            )
                            / pack_id
                            / public.name
                        )
                        if _path_lexists(materialization):
                            backup = backups_root / str(len(backups))
                            _backup_path(materialization, backup)
                            backups.append((materialization, backup))
                        _commit_public_projection(public.path, materialization)
                        committed_paths.append(materialization)
                        _commit_public_symlink(target, materialization)
                        committed_paths.append(target)
                        materialization_relative_path = str(
                            materialization.relative_to(resolved_home)
                        )
                    public_records.append(
                        SystemSkillReceiptPublicRecord(
                            name=public.name,
                            role=public.role,
                            relative_path=relative_path,
                            projection_mode=projection_mode,
                            content_digest=digest_by_public[public.name],
                            protected_logical_ids=public.protected_logical_ids,
                            materialization_relative_path=materialization_relative_path,
                        )
                    )
                new_pack_records[pack_id] = SystemSkillReceiptPackRecord(
                    pack_id=pack_id,
                    audience=composed.audience,
                    public_skills=tuple(public_records),
                )
            retained_records = {
                pack_id: record
                for pack_id, record in previous_pack_map.items()
                if pack_id not in set(selected_pack_ids) | set(removed_pack_ids)
            }
            final_records = tuple(
                (new_pack_records | retained_records)[pack_id]
                for pack_id in manifest.pack_ids
                if pack_id in new_pack_records or pack_id in retained_records
            )
            prior_legacy = (
                previous_receipt.safely_removed_legacy_paths if previous_receipt is not None else ()
            )
            receipt = SystemSkillReceipt(
                schema_version=SYSTEM_SKILL_RECEIPT_SCHEMA_VERSION,
                manifest_schema_version=manifest.schema_version,
                package_version=_package_version(),
                tool=tool,
                home_path=resolved_home,
                updated_at=_utc_now(),
                packs=final_records,
                safely_removed_legacy_paths=tuple(
                    dict.fromkeys((*prior_legacy, *safe_legacy_relative_paths))
                ),
            )
            _persist_receipt_atomic(receipt)
        except Exception:
            for path in reversed(committed_paths):
                _remove_path(path)
            _restore_backups(backups)
            _restore_receipt_bytes(inspection.path, previous_receipt_bytes)
            raise
    selected_public = tuple(
        public.name
        for pack_id in selected_pack_ids
        for public in composed_by_pack[pack_id].public_skills
    )
    projected_dirs = tuple(
        projected_public_skill_relative_dir(tool=tool, public_skill_name=name)
        for name in selected_public
    )
    protected_by_public = {
        public.name: public.protected_logical_ids
        for pack_id in selected_pack_ids
        for public in composed_by_pack[pack_id].public_skills
    }
    safely_removed = tuple(
        str(path.absolute().relative_to(resolved_home))
        for path in legacy_paths_to_remove
        if not _path_lexists(path)
    )
    return SystemSkillInstallResult(
        tool=tool,
        home_path=resolved_home,
        selected_pack_ids=selected_pack_ids,
        public_skill_names=selected_public,
        projected_relative_dirs=projected_dirs,
        receipt_path=system_skill_receipt_path(tool=tool, home_path=resolved_home),
        projection_mode=projection_mode,
        protected_logical_ids_by_public=protected_by_public,
        removed_pack_ids=removed_pack_ids,
        removed_projected_relative_dirs=tuple(removed_relative_dirs),
        safely_removed_legacy_paths=safely_removed,
    )


def _resolve_requested_pack_ids(
    manifest: SystemSkillManifest,
    *,
    pack_ids: Sequence[str],
    use_cli_default: bool,
    auto_install_kind: AutoInstallKind | None,
) -> tuple[str, ...]:
    """Resolve explicit and lane-default pack ids."""

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


def _parse_receipt_payload(
    payload: dict[str, Any],
    *,
    expected_tool: str,
    expected_home: Path,
) -> SystemSkillReceipt:
    """Parse and strictly validate a current receipt payload."""

    required_keys = {
        "schema_version",
        "manifest_schema_version",
        "package_version",
        "tool",
        "home_path",
        "updated_at",
        "selected_packs",
        "packs",
        "safely_removed_legacy_paths",
    }
    if set(payload) != required_keys:
        raise SystemSkillInstallError("System-skill receipt has missing or unknown fields.")
    if payload["tool"] != expected_tool:
        raise SystemSkillInstallError("System-skill receipt tool does not match its location.")
    if Path(_require_string(payload, "home_path")).resolve() != expected_home:
        raise SystemSkillInstallError("System-skill receipt home does not match its location.")
    raw_packs = payload["packs"]
    if not isinstance(raw_packs, list):
        raise SystemSkillInstallError("System-skill receipt packs must be a list.")
    packs: list[SystemSkillReceiptPackRecord] = []
    for raw_pack in raw_packs:
        if not isinstance(raw_pack, dict) or set(raw_pack) != {
            "pack_id",
            "audience",
            "public_skills",
        }:
            raise SystemSkillInstallError("System-skill receipt has an invalid pack record.")
        pack_id = _require_string(raw_pack, "pack_id")
        audience = raw_pack["audience"]
        if audience not in {"admin", "agent"}:
            raise SystemSkillInstallError(f"Receipt pack `{pack_id}` has invalid audience.")
        raw_public = raw_pack["public_skills"]
        if not isinstance(raw_public, list):
            raise SystemSkillInstallError(f"Receipt pack `{pack_id}` has invalid public records.")
        public_records = tuple(_parse_receipt_public(item) for item in raw_public)
        if len({record.name for record in public_records}) != len(public_records):
            raise SystemSkillInstallError(f"Receipt pack `{pack_id}` has duplicate public names.")
        packs.append(
            SystemSkillReceiptPackRecord(
                pack_id=pack_id,
                audience=cast(PackAudience, audience),
                public_skills=public_records,
            )
        )
    if len({record.pack_id for record in packs}) != len(packs):
        raise SystemSkillInstallError("System-skill receipt has duplicate pack ids.")
    selected = _require_string_list(payload, "selected_packs")
    if selected != tuple(record.pack_id for record in packs):
        raise SystemSkillInstallError("Receipt selected_packs does not match its pack records.")
    legacy_paths = _require_string_list(payload, "safely_removed_legacy_paths")
    return SystemSkillReceipt(
        schema_version=_require_string(payload, "schema_version"),
        manifest_schema_version=_require_string(payload, "manifest_schema_version"),
        package_version=_require_string(payload, "package_version"),
        tool=expected_tool,
        home_path=expected_home,
        updated_at=_require_string(payload, "updated_at"),
        packs=tuple(packs),
        safely_removed_legacy_paths=legacy_paths,
    )


def _parse_receipt_public(payload: object) -> SystemSkillReceiptPublicRecord:
    """Parse one strict receipt public record."""

    if not isinstance(payload, dict) or set(payload) != {
        "name",
        "role",
        "relative_path",
        "projection_mode",
        "content_digest",
        "protected_logical_ids",
        "materialization_relative_path",
    }:
        raise SystemSkillInstallError("System-skill receipt has an invalid public record.")
    role = payload["role"]
    mode = payload["projection_mode"]
    if role not in {"welcome", "entrypoint"} or mode not in {"copy", "symlink"}:
        raise SystemSkillInstallError("System-skill receipt public role or mode is invalid.")
    digest = _require_string(payload, "content_digest")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise SystemSkillInstallError("System-skill receipt content digest is invalid.")
    materialization = payload["materialization_relative_path"]
    if materialization is not None and not isinstance(materialization, str):
        raise SystemSkillInstallError("Receipt materialization path must be a string or null.")
    protected_ids = _require_string_list(payload, "protected_logical_ids")
    return SystemSkillReceiptPublicRecord(
        name=_require_string(payload, "name"),
        role=cast(PublicSkillRole, role),
        relative_path=_require_safe_relative_path(payload, "relative_path"),
        projection_mode=cast(SystemSkillProjectionMode, mode),
        content_digest=digest,
        protected_logical_ids=protected_ids,
        materialization_relative_path=(
            _validate_safe_relative_path(materialization) if materialization is not None else None
        ),
    )


def _inspect_public_record(
    home_path: Path,
    record: SystemSkillReceiptPublicRecord,
) -> Literal["complete", "missing", "drifted"]:
    """Classify one receipt public record against the filesystem."""

    public_path = home_path / record.relative_path
    if not _path_lexists(public_path):
        return "missing"
    content_root = public_path
    if record.projection_mode == "copy":
        if public_path.is_symlink() or not public_path.is_dir():
            return "drifted"
    else:
        if not public_path.is_symlink() or record.materialization_relative_path is None:
            return "drifted"
        materialization = home_path / record.materialization_relative_path
        if not materialization.is_dir() or materialization.is_symlink():
            return "missing"
        expected_target = materialization.resolve()
        actual_target = (
            public_path.readlink()
            if public_path.readlink().is_absolute()
            else public_path.parent / public_path.readlink()
        ).resolve(strict=False)
        if actual_target != expected_target:
            return "drifted"
        content_root = materialization
    try:
        digest = tree_content_digest(content_root)
    except SystemSkillManifestError:
        return "drifted"
    return "complete" if digest == record.content_digest else "drifted"


def _public_path_has_ownership_conflict(
    home_path: Path,
    record: SystemSkillReceiptPublicRecord,
) -> bool:
    """Return whether a receipt path has changed into an unowned projection shape."""

    path = home_path / record.relative_path
    if not _path_lexists(path):
        return False
    if record.projection_mode == "copy":
        return path.is_symlink() or not path.is_dir()
    if not path.is_symlink() or record.materialization_relative_path is None:
        return True
    materialization = home_path / record.materialization_relative_path
    actual_target = (
        path.readlink() if path.readlink().is_absolute() else path.parent / path.readlink()
    ).resolve(strict=False)
    return actual_target != materialization.resolve(strict=False)


def _receipt_record_owned_paths(record: SystemSkillReceiptPublicRecord) -> tuple[str, ...]:
    """Return all home-relative paths owned by one receipt public record."""

    if record.materialization_relative_path is None:
        return (record.relative_path,)
    return (record.relative_path, record.materialization_relative_path)


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


def _commit_public_projection(staged_path: Path, target_path: Path) -> None:
    """Commit one already validated composed directory."""

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if _path_lexists(target_path):
        raise SystemSkillInstallError(f"Commit target `{target_path}` was not preflight-cleared.")
    os.replace(staged_path, target_path)


def _commit_public_symlink(target_path: Path, materialization_path: Path) -> None:
    """Atomically point a public path at a receipt-owned materialization."""

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if _path_lexists(target_path):
        raise SystemSkillInstallError(f"Symlink target `{target_path}` was not preflight-cleared.")
    temporary_link = target_path.with_name(f".{target_path.name}.houmao-link")
    _remove_path(temporary_link)
    temporary_link.symlink_to(materialization_path)
    os.replace(temporary_link, target_path)


def _restore_receipt_bytes(path: Path, previous_bytes: bytes | None) -> None:
    """Restore the previous receipt after transaction failure."""

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


def _package_version() -> str:
    """Return the installed Houmao package version for receipt evidence."""

    try:
        return metadata.version("Houmao")
    except metadata.PackageNotFoundError:
        return "0+unknown"


def _packaged_asset_filesystem_root() -> Path:
    """Return the concrete package asset root used for old symlink recognition."""

    root = resources.files("houmao.agents.assets.system_skills")
    if not isinstance(root, Path):
        raise SystemSkillInstallError(
            "Legacy package-link classification requires filesystem-backed assets."
        )
    return root.resolve()


def _utc_now() -> str:
    """Return a stable UTC receipt timestamp."""

    return datetime.now(UTC).isoformat()
