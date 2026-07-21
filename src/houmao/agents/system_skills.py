"""Public pack-oriented facade for Houmao's static system-skill collection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from houmao.agents.system_skill_doctor import (
    SystemSkillDoctorMemberReceiptEvidence,
    SystemSkillDoctorMemberResult,
    SystemSkillDoctorReceiptEvidence,
    SystemSkillDoctorResult,
    SystemSkillDoctorTarget,
    SystemSkillDoctorTargetKind,
    SystemSkillVersionStatus,
    inspect_system_skill_doctor,
)
from houmao.agents.system_skill_lifecycle import (
    LegacySystemSkillInspection,
    LegacySystemSkillPathStatus,
    PackIntegrityStatus,
    SystemSkillInstallError,
    SystemSkillInstallResult,
    SystemSkillMemberStatusRecord,
    SystemSkillPackStatusRecord,
    SystemSkillProjectionMode,
    SystemSkillReceipt,
    SystemSkillReceiptInspection,
    SystemSkillStatusResult,
    SystemSkillUninstallResult,
    SystemSkillUpgradeResult,
    inspect_legacy_system_skill_paths,
    inspect_system_skill_packs,
    inspect_system_skill_receipt,
    install_system_skill_packs_for_home,
    project_system_skill_pack_to_destination,
    projected_standalone_skill_relative_dir,
    system_skill_receipt_path,
    system_skills_destination_for_tool,
    sync_system_skill_packs_for_home,
    uninstall_system_skill_packs_for_home,
    upgrade_system_skill_packs_for_home,
)
from houmao.agents.system_skill_manifest import (
    ActivationPosture,
    AutoInstallKind,
    DefaultLane,
    EXPECTED_SHARED_ROUTINE_IDS,
    EXPECTED_STANDALONE_SKILL_NAMES,
    LegacySystemSkillCatalog,
    LegacySystemSkillRecord,
    PackAudience,
    SharedRoutineDependency,
    SharedRoutineRecord,
    StagedStandaloneSystemSkill,
    StagedSystemSkillCollection,
    StandaloneSkillRole,
    StandaloneSystemSkillRecord,
    SystemSkillDefaults,
    SystemSkillManifest,
    SystemSkillManifestError,
    SystemSkillPackRecord,
    load_legacy_system_skill_catalog,
    load_system_skill_manifest,
    load_system_skill_manifest_from_paths,
    resolve_system_skill_pack_members,
    resolve_system_skill_pack_selection,
    stage_system_skill_collection,
    standalone_system_skill_source_path,
    tree_content_digest,
    validate_static_system_skill_source,
)
from houmao.agents.system_skill_version import (
    SystemSkillFrontmatterError,
    SystemSkillVersionSourceCheck,
    SystemSkillVersionSourceIssue,
    TopLevelSystemSkillFrontmatter,
    check_system_skill_source_versions,
    parse_top_level_system_skill_frontmatter,
)


__all__ = (
    "ActivationPosture",
    "AutoInstallKind",
    "DefaultLane",
    "EXPECTED_SHARED_ROUTINE_IDS",
    "EXPECTED_STANDALONE_SKILL_NAMES",
    "LegacySystemSkillCatalog",
    "LegacySystemSkillInspection",
    "LegacySystemSkillPathStatus",
    "LegacySystemSkillRecord",
    "PackAudience",
    "PackIntegrityStatus",
    "SharedRoutineDependency",
    "SharedRoutineRecord",
    "StagedStandaloneSystemSkill",
    "StagedSystemSkillCollection",
    "StandaloneSkillRole",
    "StandaloneSystemSkillRecord",
    "SystemSkillDefaults",
    "SystemSkillDoctorMemberReceiptEvidence",
    "SystemSkillDoctorMemberResult",
    "SystemSkillDoctorReceiptEvidence",
    "SystemSkillDoctorResult",
    "SystemSkillDoctorTarget",
    "SystemSkillDoctorTargetKind",
    "SystemSkillFrontmatterError",
    "SystemSkillInstallError",
    "SystemSkillInstallResult",
    "SystemSkillMemberStatusRecord",
    "SystemSkillManifest",
    "SystemSkillManifestError",
    "SystemSkillPackRecord",
    "SystemSkillPackStatusRecord",
    "SystemSkillProjectionMode",
    "SystemSkillReceipt",
    "SystemSkillReceiptInspection",
    "SystemSkillStatusResult",
    "SystemSkillUninstallResult",
    "SystemSkillUpgradeResult",
    "SystemSkillVersionSourceCheck",
    "SystemSkillVersionSourceIssue",
    "SystemSkillVersionStatus",
    "TopLevelSystemSkillFrontmatter",
    "check_system_skill_source_versions",
    "inspect_legacy_system_skill_paths",
    "inspect_system_skill_packs",
    "inspect_system_skill_receipt",
    "inspect_system_skill_doctor",
    "install_system_skill_packs_for_home",
    "load_legacy_system_skill_catalog",
    "load_system_skill_manifest",
    "load_system_skill_manifest_from_paths",
    "project_system_skill_pack_to_destination",
    "parse_top_level_system_skill_frontmatter",
    "projected_standalone_skill_relative_dir",
    "resolve_system_skill_pack_members",
    "resolve_system_skill_pack_selection",
    "stage_system_skill_collection",
    "standalone_system_skill_source_path",
    "system_skill_receipt_path",
    "system_skills_destination_for_tool",
    "sync_system_skill_packs_for_home",
    "tree_content_digest",
    "uninstall_system_skill_packs_for_home",
    "upgrade_system_skill_packs_for_home",
    "validate_static_system_skill_source",
)


SYSTEM_SKILL_PACK_ADMIN = "admin"
SYSTEM_SKILL_PACK_AGENT = "agent"
SYSTEM_SKILL_ADMIN_WELCOME = "houmao-admin-welcome"
SYSTEM_SKILL_ADMIN_ENTRYPOINT = "houmao-admin-entrypoint"
SYSTEM_SKILL_AGENT_ENTRYPOINT = "houmao-agent-entrypoint"
SYSTEM_SKILL_SHARED_ROUTINES = "houmao-shared-routines"

SYSTEM_SKILL_PROCESS_EMAILS = "houmao-process-emails-via-gateway"
SYSTEM_SKILL_AGENT_EMAIL_COMMS = "houmao-agent-email-comms"
SYSTEM_SKILL_ADV_USAGE_PATTERN = "houmao-adv-usage-pattern"
SYSTEM_SKILL_UTILS_WORKSPACE_MGR = "houmao-utils-workspace-mgr"
SYSTEM_SKILL_EXT_GRAPHING = "houmao-ext-graphing"
SYSTEM_SKILL_MAILBOX_MGR = "houmao-mailbox-mgr"
SYSTEM_SKILL_MEMORY_MGR = "houmao-memory-mgr"
SYSTEM_SKILL_PROJECT_MGR = "houmao-project-mgr"
SYSTEM_SKILL_CREDENTIAL_MGR = "houmao-credential-mgr"
SYSTEM_SKILL_AGENT_DEFINITION = "houmao-agent-definition"
SYSTEM_SKILL_AGENT_LOOP_PRO = "houmao-agent-loop-pro"
SYSTEM_SKILL_AGENT_LOOP_LITE = "houmao-agent-loop-lite"
SYSTEM_SKILL_AGENT_INSTANCE = "houmao-agent-instance"
SYSTEM_SKILL_AGENT_INSPECT = "houmao-agent-inspect"
SYSTEM_SKILL_OPERATOR_MESSAGING = "houmao-operator-messaging"
SYSTEM_SKILL_AGENT_MESSAGING = "houmao-agent-messaging"
SYSTEM_SKILL_AGENT_GATEWAY = "houmao-agent-gateway"
SYSTEM_SKILL_INTEROP_AG_UI = "houmao-interop-ag-ui"

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
    """Base error for pack policy and facade validation."""


class SystemSkillPolicyError(SystemSkillError):
    """Raised when stored pack selection policy is invalid."""


SystemSkillCatalogError = SystemSkillManifestError
SystemSkillCatalog = SystemSkillManifest


@dataclass(frozen=True)
class SystemSkillSelectionPolicy:
    """Stored managed-launch policy selecting complete audience packs."""

    mode: SystemSkillPolicyMode
    pack_ids: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        """Return a JSON and YAML-safe policy payload."""

        payload: dict[str, object] = {"mode": self.mode}
        if self.pack_ids:
            payload["packs"] = list(self.pack_ids)
        return payload


@dataclass(frozen=True)
class ResolvedManagedSystemSkillSelection:
    """Effective complete-pack selection for one managed tool home."""

    selected_pack_ids: tuple[str, ...]
    resolved_standalone_skill_names: tuple[str, ...]
    source_policy: SystemSkillSelectionPolicy | None = None
    profile_policy: SystemSkillSelectionPolicy | None = None


@dataclass(frozen=True)
class InstalledSystemSkillStatusRecord:
    """One visible public skill projection discovered in a tool home."""

    name: str
    projected_relative_dir: str
    projection_mode: SystemSkillProjectionMode


def load_system_skill_catalog() -> SystemSkillManifest:
    """Return the v4 manifest under the historical loader spelling."""

    return load_system_skill_manifest()


def load_system_skill_catalog_from_paths(
    *,
    catalog_path: Path,
    schema_path: Path,
) -> SystemSkillManifest:
    """Load v4 manifest fixtures under the historical loader spelling."""

    return load_system_skill_manifest_from_paths(
        manifest_path=catalog_path,
        schema_path=schema_path,
    )


def system_skill_reference_for_name(skill_name: str, *, tool: str | None = None) -> str:
    """Return the canonical standalone or shared-child invocation reference."""

    manifest = load_system_skill_manifest()
    if tool is not None:
        system_skills_destination_for_tool(tool)
    if skill_name in manifest.standalone_skills:
        return skill_name
    if skill_name == "houmao-specialist-mgr":
        return "houmao-shared-routines->houmao-agent-definition"
    if skill_name in manifest.shared_routines:
        return f"houmao-shared-routines->{skill_name}"
    raise SystemSkillManifestError(f"Unknown system skill or shared routine `{skill_name}`.")


def projected_system_skill_relative_dir(*, tool: str, skill_name: str) -> str:
    """Return the home-relative path for one standalone skill."""

    return projected_standalone_skill_relative_dir(tool=tool, skill_name=skill_name)


def parse_system_skill_selection_policy(
    payload: object,
    *,
    allowed_modes: tuple[SystemSkillPolicyMode, ...],
    default_mode: SystemSkillPolicyMode,
    source: str,
    catalog: SystemSkillManifest | None = None,
) -> SystemSkillSelectionPolicy | None:
    """Parse one source or profile policy that selects complete packs."""

    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise SystemSkillPolicyError(f"{source}: system_skills must be a mapping")
    if not payload:
        return None
    obsolete_fields = sorted(set(payload) & {"sets", "skills"})
    if obsolete_fields:
        raise SystemSkillPolicyError(
            f"{source}: obsolete system-skills selector field(s): "
            f"{', '.join(obsolete_fields)}; use `packs: [admin|agent]`"
        )
    unknown_fields = sorted(set(payload) - {"mode", "packs"})
    if unknown_fields:
        raise SystemSkillPolicyError(
            f"{source}: system_skills has unknown field(s): {', '.join(unknown_fields)}"
        )
    raw_mode = payload.get("mode", default_mode)
    if not isinstance(raw_mode, str) or raw_mode not in {
        "default",
        "inherit",
        "extend",
        "replace",
        "none",
    }:
        raise SystemSkillPolicyError(f"{source}: unknown system-skills mode `{raw_mode}`")
    policy = SystemSkillSelectionPolicy(
        mode=cast(SystemSkillPolicyMode, raw_mode),
        pack_ids=_parse_policy_string_sequence(payload.get("packs"), source=source),
    )
    validate_system_skill_selection_policy(
        policy,
        allowed_modes=allowed_modes,
        catalog=catalog,
        source=source,
    )
    return policy


def validate_system_skill_selection_policy(
    policy: SystemSkillSelectionPolicy,
    *,
    allowed_modes: tuple[SystemSkillPolicyMode, ...],
    catalog: SystemSkillManifest | None = None,
    source: str,
) -> None:
    """Validate policy mode and complete-pack selectors."""

    if policy.mode not in allowed_modes:
        raise SystemSkillPolicyError(
            f"{source}: system-skills mode `{policy.mode}` is not allowed here; "
            f"expected one of {'|'.join(allowed_modes)}"
        )
    if policy.mode in {"default", "inherit", "none"} and policy.pack_ids:
        raise SystemSkillPolicyError(
            f"{source}: system-skills mode `{policy.mode}` cannot select packs"
        )
    if policy.mode == "replace" and not policy.pack_ids:
        raise SystemSkillPolicyError(
            f"{source}: system-skills mode `replace` requires at least one pack; "
            "use `none` to disable system skills"
        )
    try:
        resolve_system_skill_pack_selection(
            catalog or load_system_skill_manifest(),
            pack_ids=policy.pack_ids,
        )
    except SystemSkillManifestError as exc:
        raise SystemSkillPolicyError(f"{source}: {exc}") from exc


def system_skill_selection_policy_to_payload(
    policy: SystemSkillSelectionPolicy | None,
) -> dict[str, object]:
    """Return one JSON and YAML-safe pack policy payload."""

    return {} if policy is None else policy.to_payload()


def resolve_managed_system_skill_selection(
    *,
    source_policy: SystemSkillSelectionPolicy | None = None,
    profile_policy: SystemSkillSelectionPolicy | None = None,
    catalog: SystemSkillManifest | None = None,
) -> ResolvedManagedSystemSkillSelection:
    """Resolve source and profile policy with the agent pack as managed default."""

    manifest = catalog or load_system_skill_manifest()
    if source_policy is not None:
        validate_system_skill_selection_policy(
            source_policy,
            allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
            catalog=manifest,
            source="source system_skills",
        )
    if profile_policy is not None:
        validate_system_skill_selection_policy(
            profile_policy,
            allowed_modes=PROFILE_SYSTEM_SKILL_POLICY_MODES,
            catalog=manifest,
            source="profile system_skills",
        )
    source_pack_ids = _resolve_source_policy_pack_ids(manifest, source_policy)
    if profile_policy is None or profile_policy.mode == "inherit":
        selected = source_pack_ids
    elif profile_policy.mode == "none":
        selected = ()
    elif profile_policy.mode == "replace":
        selected = resolve_system_skill_pack_selection(
            manifest,
            pack_ids=profile_policy.pack_ids,
        )
    else:
        selected = resolve_system_skill_pack_selection(
            manifest,
            pack_ids=(*source_pack_ids, *profile_policy.pack_ids),
        )
    standalone_names = tuple(
        record.name for record in resolve_system_skill_pack_members(manifest, pack_ids=selected)
    )
    return ResolvedManagedSystemSkillSelection(
        selected_pack_ids=selected,
        resolved_standalone_skill_names=standalone_names,
        source_policy=source_policy,
        profile_policy=profile_policy,
    )


def resolve_auto_install_pack_selection(
    manifest: SystemSkillManifest,
    *,
    kind: AutoInstallKind,
) -> tuple[str, ...]:
    """Return the fixed pack selection for one automatic lane."""

    return resolve_system_skill_pack_selection(
        manifest,
        pack_ids=manifest.defaults.pack_ids_for_kind(kind),
    )


def install_system_skills_for_home(
    *,
    tool: str,
    home_path: Path,
    pack_ids: Sequence[str] = (),
    use_cli_default: bool = False,
    auto_install_kind: AutoInstallKind | None = None,
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillInstallResult:
    """Install complete packs under the established shared-helper spelling."""

    return install_system_skill_packs_for_home(
        tool=tool,
        home_path=home_path,
        pack_ids=pack_ids,
        use_cli_default=use_cli_default,
        auto_install_kind=auto_install_kind,
        projection_mode=projection_mode,
    )


def sync_system_skills_for_home(
    *,
    tool: str,
    home_path: Path,
    selection: ResolvedManagedSystemSkillSelection,
    projection_mode: SystemSkillProjectionMode = "copy",
) -> SystemSkillInstallResult:
    """Synchronize a managed home to the exact resolved pack selection."""

    return sync_system_skill_packs_for_home(
        tool=tool,
        home_path=home_path,
        selected_pack_ids=selection.selected_pack_ids,
        projection_mode=projection_mode,
    )


def uninstall_system_skills_for_home(
    *,
    tool: str,
    home_path: Path,
    pack_ids: Sequence[str] = (),
) -> SystemSkillUninstallResult:
    """Remove selected receipt-owned packs."""

    return uninstall_system_skill_packs_for_home(
        tool=tool,
        home_path=home_path,
        pack_ids=pack_ids,
    )


def discover_installed_system_skills(
    *,
    tool: str,
    home_path: Path,
) -> tuple[InstalledSystemSkillStatusRecord, ...]:
    """Return visible standalone paths that currently exist."""

    manifest = load_system_skill_manifest()
    resolved_home = home_path.resolve()
    records: list[InstalledSystemSkillStatusRecord] = []
    for name in manifest.standalone_skill_names:
        relative_path = projected_standalone_skill_relative_dir(
            tool=tool,
            skill_name=name,
        )
        path = resolved_home / relative_path
        if not path.exists() and not path.is_symlink():
            continue
        records.append(
            InstalledSystemSkillStatusRecord(
                name=name,
                projected_relative_dir=relative_path,
                projection_mode="symlink" if path.is_symlink() else "copy",
            )
        )
    return tuple(records)


def project_system_skills_to_destination(
    destination_root: Path,
    *,
    pack_id: str,
) -> tuple[str, ...]:
    """Copy one complete static pack into an explicit destination."""

    return project_system_skill_pack_to_destination(destination_root, pack_id=pack_id)


def resolve_system_skill_selection(
    catalog: SystemSkillManifest,
    *,
    set_names: tuple[str, ...] = (),
    skill_names: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Reject the removed v1 set and individual-skill selector surface."""

    del catalog, set_names, skill_names
    raise SystemSkillPolicyError(
        "System-skill `sets` and individual `skills` selectors were removed; "
        "select complete `admin` or `agent` packs."
    )


def _resolve_source_policy_pack_ids(
    manifest: SystemSkillManifest,
    policy: SystemSkillSelectionPolicy | None,
) -> tuple[str, ...]:
    """Resolve source policy with managed-agent defaults."""

    if policy is None or policy.mode == "default":
        return manifest.defaults.managed_launch
    if policy.mode == "none":
        return ()
    if policy.mode == "replace":
        return resolve_system_skill_pack_selection(manifest, pack_ids=policy.pack_ids)
    return resolve_system_skill_pack_selection(
        manifest,
        pack_ids=(*manifest.defaults.managed_launch, *policy.pack_ids),
    )


def _parse_policy_string_sequence(value: object, *, source: str) -> tuple[str, ...]:
    """Parse and de-duplicate one policy pack list."""

    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SystemSkillPolicyError(f"{source}: system_skills.packs must be a list of strings")
    values: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise SystemSkillPolicyError(
                f"{source}: system_skills.packs[{index}] must be a non-empty string"
            )
        if item not in values:
            values.append(item)
    return tuple(values)
