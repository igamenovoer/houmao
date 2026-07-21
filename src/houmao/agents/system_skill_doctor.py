"""Read-only health diagnostics for installed static Houmao system skills."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal

from houmao.agents.system_skill_lifecycle import (
    MemberIntegrityStatus,
    ReceiptInspectionStatus,
    SystemSkillProjectionMode,
    inspect_system_skill_receipt,
    projected_standalone_skill_relative_dir,
)
from houmao.agents.system_skill_manifest import (
    EXPECTED_SHARED_ROUTINE_IDS,
    StandaloneSkillRole,
    SystemSkillManifestError,
    load_system_skill_manifest,
    resolve_system_skill_pack_members,
    resolve_system_skill_pack_selection,
    standalone_system_skill_content_digest,
    tree_content_digest,
)
from houmao.agents.system_skill_version import (
    SystemSkillFrontmatterError,
    parse_top_level_system_skill_frontmatter,
)
from houmao.version import get_version


SystemSkillVersionStatus = Literal["match", "mismatch", "missing", "invalid", "unavailable"]
SystemSkillDoctorTargetKind = Literal["explicit-home", "managed-agent"]


@dataclass(frozen=True)
class SystemSkillDoctorTarget:
    """Resolved provenance for one home inspected by doctor."""

    kind: SystemSkillDoctorTargetKind
    tool: str
    home_path: Path
    agent_id: str | None = None
    agent_name: str | None = None
    lifecycle_state: str | None = None
    session_manifest_path: Path | None = None
    brain_manifest_path: Path | None = None


@dataclass(frozen=True)
class SystemSkillDoctorReceiptEvidence:
    """Tool-home receipt evidence kept separate from direct health checks."""

    status: ReceiptInspectionStatus
    path: Path
    message: str | None
    package_version: str | None
    selected_pack_ids: tuple[str, ...]
    legacy_pack_ids: tuple[str, ...]


@dataclass(frozen=True)
class SystemSkillDoctorMemberReceiptEvidence:
    """Optional current-receipt record for one expected member."""

    present: bool
    projection_mode: SystemSkillProjectionMode | None
    content_digest: str | None
    owning_pack_ids: tuple[str, ...]


@dataclass(frozen=True)
class SystemSkillDoctorMemberResult:
    """Independent integrity, version, and receipt evidence for one expected root."""

    name: str
    role: StandaloneSkillRole
    expected_pack_ids: tuple[str, ...]
    relative_path: str
    path: Path
    integrity_status: MemberIntegrityStatus
    expected_content_digest: str
    observed_content_digest: str | None
    observed_version: str | None
    version_status: SystemSkillVersionStatus
    issues: tuple[str, ...]
    receipt: SystemSkillDoctorMemberReceiptEvidence

    @property
    def healthy(self) -> bool:
        """Return whether this member is complete and release-matched."""

        return self.integrity_status == "complete" and self.version_status == "match"


@dataclass(frozen=True)
class SystemSkillDoctorResult:
    """Aggregate read-only diagnostic for one explicit expected pack set."""

    target: SystemSkillDoctorTarget
    running_houmao_version: str
    selected_pack_ids: tuple[str, ...]
    receipt: SystemSkillDoctorReceiptEvidence
    members: tuple[SystemSkillDoctorMemberResult, ...]
    healthy: bool


def inspect_system_skill_doctor(
    *,
    target: SystemSkillDoctorTarget,
    pack_ids: tuple[str, ...] = (),
    running_houmao_version: str | None = None,
) -> SystemSkillDoctorResult:
    """Inspect an expected pack directly without lifecycle ownership assumptions."""

    manifest = load_system_skill_manifest()
    selected_pack_ids = resolve_system_skill_pack_selection(
        manifest,
        pack_ids=pack_ids or ("agent",),
    )
    records = resolve_system_skill_pack_members(manifest, pack_ids=selected_pack_ids)
    expected_version = running_houmao_version or get_version()
    home_path = target.home_path.expanduser().resolve()
    receipt_inspection = inspect_system_skill_receipt(tool=target.tool, home_path=home_path)
    receipt = receipt_inspection.receipt
    receipt_map = receipt.skill_map() if receipt is not None else {}
    members: list[SystemSkillDoctorMemberResult] = []
    for record in records:
        relative_path = projected_standalone_skill_relative_dir(
            tool=target.tool,
            skill_name=record.name,
        )
        path = home_path / relative_path
        expected_digest = standalone_system_skill_content_digest(manifest, record)
        integrity_status, observed_digest, integrity_issues = _inspect_member_integrity(
            path=path,
            skill_name=record.name,
            expected_digest=expected_digest,
        )
        observed_version, version_status, version_issues = _inspect_member_version(
            path=path,
            skill_name=record.name,
            running_houmao_version=expected_version,
        )
        receipt_record = receipt_map.get(record.name)
        expected_owners = tuple(
            pack_id
            for pack_id in selected_pack_ids
            if record.name in manifest.packs[pack_id].standalone_skill_names
        )
        members.append(
            SystemSkillDoctorMemberResult(
                name=record.name,
                role=record.role,
                expected_pack_ids=expected_owners,
                relative_path=relative_path,
                path=path,
                integrity_status=integrity_status,
                expected_content_digest=expected_digest,
                observed_content_digest=observed_digest,
                observed_version=observed_version,
                version_status=version_status,
                issues=integrity_issues + version_issues,
                receipt=SystemSkillDoctorMemberReceiptEvidence(
                    present=receipt_record is not None,
                    projection_mode=(
                        receipt_record.projection_mode if receipt_record is not None else None
                    ),
                    content_digest=(
                        receipt_record.content_digest if receipt_record is not None else None
                    ),
                    owning_pack_ids=(
                        receipt_record.owning_pack_ids if receipt_record is not None else ()
                    ),
                ),
            )
        )
    receipt_evidence = SystemSkillDoctorReceiptEvidence(
        status=receipt_inspection.status,
        path=receipt_inspection.path,
        message=receipt_inspection.message,
        package_version=receipt.package_version if receipt is not None else None,
        selected_pack_ids=receipt.selected_pack_ids if receipt is not None else (),
        legacy_pack_ids=receipt_inspection.legacy_pack_ids,
    )
    normalized_target = SystemSkillDoctorTarget(
        kind=target.kind,
        tool=target.tool,
        home_path=home_path,
        agent_id=target.agent_id,
        agent_name=target.agent_name,
        lifecycle_state=target.lifecycle_state,
        session_manifest_path=target.session_manifest_path,
        brain_manifest_path=target.brain_manifest_path,
    )
    return SystemSkillDoctorResult(
        target=normalized_target,
        running_houmao_version=expected_version,
        selected_pack_ids=selected_pack_ids,
        receipt=receipt_evidence,
        members=tuple(members),
        healthy=all(member.healthy for member in members),
    )


def _inspect_member_integrity(
    *,
    path: Path,
    skill_name: str,
    expected_digest: str,
) -> tuple[MemberIntegrityStatus, str | None, tuple[str, ...]]:
    """Classify one installed root independently from any receipt."""

    if not os.path.lexists(path):
        return "absent", None, ("expected standalone root is absent",)
    if path.is_symlink() and not path.exists():
        return "conflicting", None, ("destination is a broken symbolic link",)
    if not path.is_dir():
        return "conflicting", None, ("destination is not a directory",)
    entrypoint = path / "SKILL.md"
    if not entrypoint.is_file():
        return "incomplete", None, ("canonical SKILL.md entrypoint is missing",)
    try:
        metadata = parse_top_level_system_skill_frontmatter(
            entrypoint,
            expected_name=skill_name,
        )
    except SystemSkillFrontmatterError as exc:
        if exc.code in {"name-mismatch", "invalid-name", "missing-name"}:
            return "conflicting", None, (str(exc),)
        metadata = None
    if skill_name == "houmao-shared-routines":
        shared_issue = _shared_routine_shape_issue(path)
        if shared_issue is not None:
            return "incomplete", None, (shared_issue,)
    try:
        observed_digest = tree_content_digest(path)
    except (OSError, SystemSkillManifestError) as exc:
        return "drifted", None, (f"cannot digest installed tree: {exc}",)
    if observed_digest != expected_digest:
        issues = ["installed tree differs from the running package"]
        if metadata is None:
            issues.append("top-level frontmatter is invalid")
        return "drifted", observed_digest, tuple(issues)
    return "complete", observed_digest, ()


def _inspect_member_version(
    *,
    path: Path,
    skill_name: str,
    running_houmao_version: str,
) -> tuple[str | None, SystemSkillVersionStatus, tuple[str, ...]]:
    """Read and compare one installed root version without normalization."""

    entrypoint = path / "SKILL.md"
    if not entrypoint.is_file():
        return None, "unavailable", ("installed version is unavailable without SKILL.md",)
    try:
        metadata = parse_top_level_system_skill_frontmatter(
            entrypoint,
            expected_name=skill_name,
        )
    except SystemSkillFrontmatterError as exc:
        if exc.code == "missing-version":
            return None, "missing", (str(exc),)
        return None, "invalid", (str(exc),)
    observed = metadata.houmao_version
    if running_houmao_version == "0+unknown":
        return (
            observed,
            "unavailable",
            ("running Houmao version is unavailable (`0+unknown`)",),
        )
    if observed == running_houmao_version:
        return observed, "match", ()
    return (
        observed,
        "mismatch",
        (f"installed version `{observed}` differs from `{running_houmao_version}`",),
    )


def _shared_routine_shape_issue(path: Path) -> str | None:
    """Return a diagnostic when the shared root lacks its exact child set."""

    child_root = path / "subskills"
    if not child_root.is_dir():
        return "shared routines is missing its subskills directory"
    child_dirs = {child.name for child in child_root.iterdir() if child.is_dir()}
    expected = set(EXPECTED_SHARED_ROUTINE_IDS)
    if child_dirs != expected:
        missing = sorted(expected - child_dirs)
        extra = sorted(child_dirs - expected)
        details: list[str] = []
        if missing:
            details.append(f"missing children: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected children: {', '.join(extra)}")
        return "shared routines child set is incomplete (" + "; ".join(details) + ")"
    for child_name in sorted(expected):
        child = child_root / child_name
        if not (child / "SKILL-MAIN.md").is_file() or (child / "SKILL.md").exists():
            return f"shared child `{child_name}` must expose only canonical SKILL-MAIN.md"
    return None


__all__ = (
    "SystemSkillDoctorMemberReceiptEvidence",
    "SystemSkillDoctorMemberResult",
    "SystemSkillDoctorReceiptEvidence",
    "SystemSkillDoctorResult",
    "SystemSkillDoctorTarget",
    "SystemSkillDoctorTargetKind",
    "SystemSkillVersionStatus",
    "inspect_system_skill_doctor",
)
