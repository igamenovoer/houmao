"""Bounded all-or-nothing creation operations for Agent Deployments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.project.agent_definitions import (
    DeploymentPlan,
    _project_precondition_digest,
    _register_agent_deployment,
    _sha256_bytes,
    apply_deployment,
    create_deployment_request,
    load_deployment_plan,
    plan_deployment,
    rollback_prepared_deployment,
    validate_revision,
)
from houmao.project.catalog import ProjectCatalog
from houmao.project.overlay import HoumaoProjectOverlay

BATCH_REQUEST_SCHEMA = "houmao-agent-deployment-batch-request.v1"
BATCH_PLAN_SCHEMA = "houmao-agent-deployment-batch-plan.v1"
MAX_BATCH_MEMBERS = 32


def _canonical_json(payload: object) -> bytes:
    """Serialize one object into canonical UTF-8 JSON."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _write_json(path: Path, payload: object) -> None:
    """Write stable JSON after creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class BatchDelegation(BaseModel):
    """Explicit field-limited operator selection authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    names: bool = False
    tools: bool = False
    credentials: bool = False


class BatchMemberOverride(BaseModel):
    """User-fixed or explicitly delegated selections for one member."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ordinal: int = Field(ge=1, le=MAX_BATCH_MEMBERS)
    deployment_name: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]*$")
    specialist_name: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]*$")
    profile_name: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]*$")
    tool: str | None = None
    credential: str | None = None
    values: dict[str, str | int | float | bool] = Field(default_factory=dict)
    rationale: dict[str, str] = Field(default_factory=dict)


class BatchDeploymentRequest(BaseModel):
    """One exact definition, project, quantity, and bounded delegation request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-deployment-batch-request.v1"] = (
        "houmao-agent-deployment-batch-request.v1"
    )
    definition_path: str
    definition_id: str
    revision_id: str
    revision_digest: str
    target_project: str
    count: int = Field(ge=1, le=MAX_BATCH_MEMBERS)
    shared_values: dict[str, str | int | float | bool] = Field(default_factory=dict)
    workdir: str = "."
    tool: str | None = None
    credential: str | None = None
    name_prefix: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]*$")
    delegation: BatchDelegation = Field(default_factory=BatchDelegation)
    member_overrides: tuple[BatchMemberOverride, ...] = ()
    private_workspace_enabled: bool | None = None
    workspace_workdir_mode: str | None = None

    @field_validator("member_overrides")
    @classmethod
    def unique_ordinals(
        cls, value: tuple[BatchMemberOverride, ...]
    ) -> tuple[BatchMemberOverride, ...]:
        """Reject duplicate member ordinals."""

        ordinals = [item.ordinal for item in value]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("Batch member override ordinals must be unique.")
        return value


class BatchPlanMember(BaseModel):
    """One ordered ordinary member plan in a batch envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ordinal: int
    plan_path: str
    plan_digest: str
    selection_rationale: dict[str, str] = Field(default_factory=dict)


class BatchDeploymentPlan(BaseModel):
    """Integrity-protected envelope over ordinary member Deployment Plans."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-deployment-batch-plan.v1"] = (
        "houmao-agent-deployment-batch-plan.v1"
    )
    operation_id: str
    batch_digest: str = ""
    request_digest: str
    target_project: str
    project_precondition_digest: str
    members: tuple[BatchPlanMember, ...]


def create_batch_request(
    *,
    revision_root: Path,
    overlay: HoumaoProjectOverlay,
    count: int,
    shared_values: dict[str, str | int | float | bool],
    delegation: BatchDelegation,
    member_overrides: tuple[BatchMemberOverride, ...] = (),
    workdir: str = ".",
    tool: str | None = None,
    credential: str | None = None,
    name_prefix: str | None = None,
    private_workspace_enabled: bool | None = None,
    workspace_workdir_mode: str | None = None,
) -> BatchDeploymentRequest:
    """Create one exact bounded batch request without resolving delegated choices."""

    revision = validate_revision(revision_root)
    return BatchDeploymentRequest(
        definition_path=str(revision.root),
        definition_id=revision.definition.definition_id,
        revision_id=revision.definition.revision_id,
        revision_digest=revision.revision_digest,
        target_project=str(overlay.project_root),
        count=count,
        shared_values=shared_values,
        workdir=workdir,
        tool=tool,
        credential=credential,
        name_prefix=name_prefix,
        delegation=delegation,
        member_overrides=member_overrides,
        private_workspace_enabled=private_workspace_enabled,
        workspace_workdir_mode=workspace_workdir_mode,
    )


def plan_batch_deployment(
    request: BatchDeploymentRequest,
    *,
    overlay: HoumaoProjectOverlay,
) -> tuple[BatchDeploymentPlan, Path]:
    """Expand, validate, and stage every ordinary member Deployment Plan."""

    if Path(request.target_project).resolve() != overlay.project_root.resolve():
        raise ValueError("Batch Deployment Request targets a different project.")
    revision = validate_revision(Path(request.definition_path))
    if (
        revision.definition.definition_id != request.definition_id
        or revision.definition.revision_id != request.revision_id
        or revision.revision_digest != request.revision_digest
    ):
        raise ValueError("Batch Deployment Request is stale for its definition revision.")
    catalog = ProjectCatalog.from_overlay(overlay)
    auth_profiles = catalog.list_auth_profiles()
    credential_candidates = [(entry.tool, entry.display_name) for entry in auth_profiles]
    overrides = {item.ordinal: item for item in request.member_overrides}
    if any(ordinal > request.count for ordinal in overrides):
        raise ValueError("Batch member override ordinal exceeds requested count.")
    expanded: list[tuple[Any, dict[str, str]]] = []
    seen_names: set[str] = set()
    for ordinal in range(1, request.count + 1):
        override = overrides.get(ordinal, BatchMemberOverride(ordinal=ordinal))
        rationale = dict(override.rationale)
        base_name = override.deployment_name
        if base_name is None:
            if not request.delegation.names:
                raise ValueError(
                    f"Member {ordinal} needs an explicit name or delegated name selection."
                )
            prefix = request.name_prefix or request.definition_id
            base_name = f"{prefix}-{ordinal:02d}"
            rationale.setdefault("name", "Generated from delegated name prefix and member ordinal.")
        specialist_name = override.specialist_name or base_name
        profile_name = override.profile_name or base_name
        if len({base_name, specialist_name, profile_name}.intersection(seen_names)) > 0:
            raise ValueError(f"Batch member {ordinal} collides with another member name.")
        seen_names.update({base_name, specialist_name, profile_name})
        selected_tool = override.tool or request.tool
        selected_credential = override.credential or request.credential
        if override.tool is not None and request.tool is not None and not request.delegation.tools:
            if override.tool != request.tool:
                raise ValueError("A member tool override requires explicit tool delegation.")
        if (
            override.credential is not None
            and request.credential is not None
            and not request.delegation.credentials
            and override.credential != request.credential
        ):
            raise ValueError("A member credential override requires credential delegation.")
        if selected_tool is None:
            if not request.delegation.tools:
                raise ValueError(
                    f"Member {ordinal} needs one fixed tool or delegated tool selection."
                )
            if not credential_candidates:
                raise ValueError("No registered project tool has an existing credential.")
            selected_tool = credential_candidates[(ordinal - 1) % len(credential_candidates)][0]
            rationale.setdefault("tool", "Selected from registered tools with credentials.")
        if selected_credential is None:
            if not request.delegation.credentials:
                raise ValueError(
                    f"Member {ordinal} needs one fixed credential or delegated credential selection."
                )
            candidates = [
                credential
                for tool_name, credential in credential_candidates
                if tool_name == selected_tool
            ]
            if not candidates:
                raise ValueError(
                    f"No existing credential is compatible with delegated tool `{selected_tool}`."
                )
            selected_credential = candidates[(ordinal - 1) % len(candidates)]
            rationale.setdefault(
                "credential", "Selected an existing compatible credential reference."
            )
        if (selected_tool, selected_credential) not in credential_candidates:
            raise ValueError(
                f"Member {ordinal} credential `{selected_tool}/{selected_credential}` "
                "is not an existing compatible reference."
            )
        values = dict(request.shared_values)
        values.update(override.values)
        member_request = create_deployment_request(
            revision_root=revision.root,
            overlay=overlay,
            deployment_name=base_name,
            specialist_name=specialist_name,
            profile_name=profile_name,
            tool=selected_tool,
            credential=selected_credential,
            workdir=request.workdir,
            values=values,
            private_workspace_enabled=request.private_workspace_enabled,
            workspace_workdir_mode=request.workspace_workdir_mode,  # type: ignore[arg-type]
        )
        expanded.append((member_request, rationale))
    request_payload = request.model_dump(mode="json")
    request_digest = _sha256_bytes(_canonical_json(request_payload))
    operation_id = hashlib.sha256(
        _canonical_json(
            {
                "request_digest": request_digest,
                "project_precondition_digest": _project_precondition_digest(overlay),
            }
        )
    ).hexdigest()[:24]
    batch_root = overlay.jobs_root / "agent-definition-batches" / operation_id
    if batch_root.exists():
        return load_batch_plan(batch_root), batch_root
    members: list[BatchPlanMember] = []
    for ordinal, (member_request, rationale) in enumerate(expanded, start=1):
        member_plan, source_plan_root = plan_deployment(member_request, overlay=overlay)
        if member_plan.blockers:
            raise ValueError(
                f"Batch member {ordinal} is blocked: {'; '.join(member_plan.blockers)}"
            )
        member_root = batch_root / "members" / f"{ordinal:03d}"
        shutil.copytree(source_plan_root, member_root)
        copied_plan = load_deployment_plan(member_root)
        members.append(
            BatchPlanMember(
                ordinal=ordinal,
                plan_path=str(member_root),
                plan_digest=copied_plan.plan_digest,
                selection_rationale=rationale,
            )
        )
    plan = BatchDeploymentPlan(
        operation_id=operation_id,
        request_digest=request_digest,
        target_project=request.target_project,
        project_precondition_digest=_project_precondition_digest(overlay),
        members=tuple(members),
    )
    plan = plan.model_copy(update={"batch_digest": _batch_plan_digest(plan)})
    _write_json(batch_root / "request.json", request_payload)
    _write_json(batch_root / "batch-plan.json", plan.model_dump(mode="json"))
    _write_json(batch_root / "journal.json", {"state": "planned", "operation_id": operation_id})
    return plan, batch_root


def load_batch_plan(batch_root: Path) -> BatchDeploymentPlan:
    """Load a batch plan and verify every member plan digest."""

    plan = BatchDeploymentPlan.model_validate(
        json.loads((batch_root / "batch-plan.json").read_text(encoding="utf-8"))
    )
    if _batch_plan_digest(plan) != plan.batch_digest:
        raise ValueError(f"Batch Deployment Plan was edited: {batch_root}")
    for member in plan.members:
        member_plan = load_deployment_plan(Path(member.plan_path))
        if member_plan.plan_digest != member.plan_digest:
            raise ValueError(f"Batch member {member.ordinal} plan digest changed.")
    return plan


def apply_batch_deployment(
    batch_root: Path,
    *,
    overlay: HoumaoProjectOverlay,
) -> dict[str, Any]:
    """Prepare all members and insert all Agent Deployment rows in one transaction."""

    plan = load_batch_plan(batch_root)
    if Path(plan.target_project).resolve() != overlay.project_root.resolve():
        raise ValueError("Batch Deployment Plan targets a different project.")
    if _project_precondition_digest(overlay) != plan.project_precondition_digest:
        raise ValueError("Project catalog changed after batch planning.")
    journal_path = batch_root / "journal.json"
    _write_json(journal_path, {"state": "preparing", "operation_id": plan.operation_id})
    prepared: list[tuple[BatchPlanMember, DeploymentPlan, dict[str, Any]]] = []
    committed = False
    try:
        for member in plan.members:
            member_root = Path(member.plan_path)
            member_plan = load_deployment_plan(member_root)
            result = apply_deployment(
                member_root,
                overlay=overlay,
                defer_registration=True,
                skip_project_precondition=bool(prepared),
                batch_operation_id=plan.operation_id,
                batch_member_ordinal=member.ordinal,
            )
            prepared.append((member, member_plan, result))
        _write_json(journal_path, {"state": "prepared", "operation_id": plan.operation_id})
        _write_json(journal_path, {"state": "committing", "operation_id": plan.operation_id})
        with sqlite3.connect(overlay.catalog_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            for member, member_plan, result in prepared:
                _register_agent_deployment(
                    overlay=overlay,
                    plan=member_plan,
                    plan_root=Path(member.plan_path),
                    deployment_id=str(result["deployment_id"]),
                    batch_operation_id=plan.operation_id,
                    batch_member_ordinal=member.ordinal,
                    connection=connection,
                )
            connection.commit()
        committed = True
        ProjectCatalog.from_overlay(overlay).materialize_projection()
        for member, _, result in prepared:
            _write_json(
                Path(member.plan_path) / "journal.json",
                {
                    "state": "applied",
                    "plan_id": load_deployment_plan(Path(member.plan_path)).plan_id,
                    "deployment_id": result["deployment_id"],
                    "batch_operation_id": plan.operation_id,
                    "batch_member_ordinal": member.ordinal,
                },
            )
        _write_json(journal_path, {"state": "applied", "operation_id": plan.operation_id})
    except Exception as exc:
        if not committed:
            for member, _, _ in reversed(prepared):
                rollback_prepared_deployment(Path(member.plan_path), overlay=overlay)
        _write_json(
            journal_path,
            {
                "state": "failed",
                "operation_id": plan.operation_id,
                "error": str(exc),
                "catalog_committed": committed,
            },
        )
        raise
    handoffs = [
        {
            "ordinal": member.ordinal,
            "deployment_id": result["deployment_id"],
            "deployment_name": member_plan.deployment_name,
            "profile_name": member_plan.profile_name,
            "launch_command": result["launch_command"],
            "launched": False,
        }
        for member, member_plan, result in prepared
    ]
    return {
        "operation_id": plan.operation_id,
        "member_count": len(handoffs),
        "launch_handoffs": handoffs,
        "launched": False,
    }


def inspect_batch_operation(
    batch_root: Path,
    *,
    overlay: HoumaoProjectOverlay,
) -> dict[str, Any]:
    """Inspect historical operation provenance without creating a batch entity."""

    plan = load_batch_plan(batch_root)
    journal = json.loads((batch_root / "journal.json").read_text(encoding="utf-8"))
    with sqlite3.connect(overlay.catalog_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT deployment_id, deployment_name, batch_member_ordinal
            FROM agent_deployments
            WHERE batch_operation_id = ?
            ORDER BY batch_member_ordinal
            """,
            (plan.operation_id,),
        ).fetchall()
    return {
        "operation_id": plan.operation_id,
        "state": journal.get("state"),
        "planned_members": len(plan.members),
        "visible_members": [dict(row) for row in rows],
        "durable_batch_entity": False,
    }


def doctor_batch_operations(overlay: HoumaoProjectOverlay) -> dict[str, Any]:
    """Recover interrupted publication or rollback operation-owned preparation."""

    findings: list[dict[str, str]] = []
    catalog = ProjectCatalog.from_overlay(overlay)
    jobs_root = overlay.jobs_root / "agent-definition-batches"
    if jobs_root.is_dir():
        for operation_root in sorted(path for path in jobs_root.iterdir() if path.is_dir()):
            try:
                plan = load_batch_plan(operation_root)
                journal = json.loads((operation_root / "journal.json").read_text(encoding="utf-8"))
                state = str(journal.get("state"))
                with sqlite3.connect(overlay.catalog_path) as connection:
                    connection.row_factory = sqlite3.Row
                    visible_rows = connection.execute(
                        """
                        SELECT deployment_id, batch_member_ordinal
                        FROM agent_deployments
                        WHERE batch_operation_id = ?
                        ORDER BY batch_member_ordinal
                        """,
                        (plan.operation_id,),
                    ).fetchall()
                committed_failure = state == "failed" and bool(journal.get("catalog_committed"))
                if (state in {"committing"} or committed_failure) and len(visible_rows) == len(
                    plan.members
                ):
                    catalog.materialize_projection()
                    deployment_by_ordinal = {
                        int(row["batch_member_ordinal"]): str(row["deployment_id"])
                        for row in visible_rows
                    }
                    for member in plan.members:
                        member_plan = load_deployment_plan(Path(member.plan_path))
                        _write_json(
                            Path(member.plan_path) / "journal.json",
                            {
                                "state": "applied",
                                "plan_id": member_plan.plan_id,
                                "deployment_id": deployment_by_ordinal[member.ordinal],
                                "batch_operation_id": plan.operation_id,
                                "batch_member_ordinal": member.ordinal,
                                "recovered_by_doctor": True,
                            },
                        )
                    _write_json(
                        operation_root / "journal.json",
                        {
                            "state": "applied",
                            "operation_id": plan.operation_id,
                            "recovered_by_doctor": True,
                        },
                    )
                    findings.append(
                        {
                            "severity": "info",
                            "operation_id": plan.operation_id,
                            "code": "recovered-publication",
                        }
                    )
                elif state in {"preparing", "prepared", "committing"} and not visible_rows:
                    for member in reversed(plan.members):
                        rollback_prepared_deployment(Path(member.plan_path), overlay=overlay)
                    _write_json(
                        operation_root / "journal.json",
                        {
                            "state": "failed",
                            "operation_id": plan.operation_id,
                            "recovered_by_doctor": True,
                            "catalog_committed": False,
                        },
                    )
                    findings.append(
                        {
                            "severity": "info",
                            "operation_id": plan.operation_id,
                            "code": f"rolled-back-{state}",
                        }
                    )
                elif len(visible_rows) not in {0, len(plan.members)}:
                    findings.append(
                        {
                            "severity": "error",
                            "operation_id": plan.operation_id,
                            "code": "partial-catalog-visibility",
                        }
                    )
                elif committed_failure:
                    findings.append(
                        {
                            "severity": "error",
                            "operation_id": plan.operation_id,
                            "code": "committed-publication-incomplete",
                        }
                    )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                findings.append(
                    {
                        "severity": "error",
                        "operation_id": operation_root.name,
                        "code": "invalid-operation",
                        "detail": str(exc),
                    }
                )
    return {
        "healthy": not any(item["severity"] == "error" for item in findings),
        "findings": findings,
    }


def _batch_plan_digest(plan: BatchDeploymentPlan) -> str:
    """Digest a batch envelope with its self-field cleared."""

    payload = plan.model_dump(mode="json")
    payload["batch_digest"] = ""
    return _sha256_bytes(_canonical_json(payload))


__all__ = [
    "BATCH_PLAN_SCHEMA",
    "BATCH_REQUEST_SCHEMA",
    "MAX_BATCH_MEMBERS",
    "BatchDelegation",
    "BatchDeploymentPlan",
    "BatchDeploymentRequest",
    "BatchMemberOverride",
    "apply_batch_deployment",
    "create_batch_request",
    "doctor_batch_operations",
    "inspect_batch_operation",
    "load_batch_plan",
    "plan_batch_deployment",
]
