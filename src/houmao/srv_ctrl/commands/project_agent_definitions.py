"""Maintained project commands for Agent Definition authoring and deployment."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any

import click

from houmao.project.agent_definitions import (
    AgentDefinitionWorkspace,
    MaterializationSpec,
    apply_deployment,
    approve_derivation,
    create_deployment_request,
    deployment_instance_references,
    derive_intent,
    doctor_agent_deployments,
    init_intent,
    inspect_agent_deployment,
    list_agent_deployments,
    materialize_revision,
    plan_deployment,
    remove_agent_deployment,
    validate_revision,
)
from houmao.project.agent_definition_batches import (
    BatchDelegation,
    BatchMemberOverride,
    apply_batch_deployment,
    create_batch_request,
    doctor_batch_operations,
    inspect_batch_operation,
    plan_batch_deployment,
)

from .output import emit
from .project_common import _ensure_project_overlay, _resolve_existing_project_overlay


@click.group(name="agent-definitions")
def project_agent_definitions_group() -> None:
    """Author portable Agent Definitions and manage project deployments."""


@project_agent_definitions_group.command(name="init-intent")
@click.argument("workspace", type=click.Path(path_type=Path))
@click.option("--overview-file", type=click.Path(path_type=Path, dir_okay=False))
def init_intent_command(workspace: Path, overview_file: Path | None) -> None:
    """Create only `intent/src/agent-def-overview.md` in WORKSPACE."""

    text = overview_file.read_text(encoding="utf-8") if overview_file is not None else ""
    try:
        result = init_intent(workspace, overview_text=text)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit({"workspace": str(result.root), "overview_path": str(result.overview_path)})


@project_agent_definitions_group.command(name="derive")
@click.argument("workspace", type=click.Path(path_type=Path, exists=True, file_okay=False))
@click.option(
    "--interpretation-file",
    required=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--materialization-file",
    required=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--skill",
    "skills",
    multiple=True,
    type=click.Path(path_type=Path, exists=True, file_okay=False),
)
def derive_command(
    workspace: Path,
    interpretation_file: Path,
    materialization_file: Path,
    skills: tuple[Path, ...],
) -> None:
    """Record reviewed operator interpretation and normalized materialization input."""

    try:
        materialization = MaterializationSpec.model_validate(
            tomllib.loads(materialization_file.read_text(encoding="utf-8"))
        )
        validation = derive_intent(
            AgentDefinitionWorkspace(workspace),
            interpretation_text=interpretation_file.read_text(encoding="utf-8"),
            materialization=materialization,
            source_skill_roots=skills,
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(validation)


@project_agent_definitions_group.command(name="approve")
@click.argument("workspace", type=click.Path(path_type=Path, exists=True, file_okay=False))
@click.option("--approved-by", required=True)
def approve_command(workspace: Path, approved_by: str) -> None:
    """Approve the exact current source and derived digests."""

    try:
        approval = approve_derivation(AgentDefinitionWorkspace(workspace), approved_by=approved_by)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(approval)


@project_agent_definitions_group.command(name="materialize")
@click.argument("workspace", type=click.Path(path_type=Path, exists=True, file_okay=False))
@click.option("--output", type=click.Path(path_type=Path), default=None)
@click.option(
    "--preview", is_flag=True, help="Validate materialization without writing a revision."
)
def materialize_command(workspace: Path, output: Path | None, preview: bool) -> None:
    """Preview or write one immutable Agent Definition Revision."""

    try:
        revision = materialize_revision(
            AgentDefinitionWorkspace(workspace),
            output_root=output,
            write=not preview,
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "definition_id": revision.definition.definition_id,
            "revision_id": revision.definition.revision_id,
            "revision_digest": revision.revision_digest,
            "output": None if preview else str(revision.root),
            "preview": preview,
        }
    )


@project_agent_definitions_group.command(name="validate")
@click.argument("definition", type=click.Path(path_type=Path, file_okay=False))
def validate_command(definition: Path) -> None:
    """Validate one portable Agent Definition Revision."""

    try:
        revision = validate_revision(definition)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "valid": True,
            "definition_id": revision.definition.definition_id,
            "revision_id": revision.definition.revision_id,
            "revision_digest": revision.revision_digest,
            "instance_contract_digest": revision.instance_contract_digest,
        }
    )


def _parse_set_values(assignments: tuple[str, ...]) -> dict[str, str | int | float | bool]:
    """Parse repeated KEY=JSON scalar assignments."""

    values: dict[str, str | int | float | bool] = {}
    for assignment in assignments:
        key, separator, raw_value = assignment.partition("=")
        if not separator or not key:
            raise click.ClickException(f"Expected KEY=VALUE for `--set`: {assignment}")
        try:
            value: Any = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        if not isinstance(value, (str, int, float, bool)):
            raise click.ClickException(f"`--set {key}` must use a scalar value.")
        values[key] = value
    return values


def _build_plan(
    *,
    definition: Path,
    deployment_name: str,
    specialist_name: str,
    profile_name: str,
    tool: str,
    credential: str,
    workdir: str,
    values: tuple[str, ...],
    private_workspace: bool | None,
    workspace_workdir_mode: str | None,
    update_existing: bool = False,
) -> dict[str, Any]:
    """Create and persist one request and deterministic plan."""

    overlay = _ensure_project_overlay()
    request = create_deployment_request(
        revision_root=definition,
        overlay=overlay,
        deployment_name=deployment_name,
        specialist_name=specialist_name,
        profile_name=profile_name,
        tool=tool,
        credential=credential,
        workdir=workdir,
        values=_parse_set_values(values),
        private_workspace_enabled=private_workspace,
        workspace_workdir_mode=workspace_workdir_mode,  # type: ignore[arg-type]
        update_existing=update_existing,
    )
    plan, plan_root = plan_deployment(request, overlay=overlay)
    return {
        "plan_id": plan.plan_id,
        "plan_path": str(plan_root),
        "plan_digest": plan.plan_digest,
        "blockers": list(plan.blockers),
        "warnings": list(plan.warnings),
        "apply_command": (
            "houmao-mgr project agent-definitions apply " + json.dumps(str(plan_root))
        ),
    }


def _plan_options(function: Any) -> Any:
    """Add the common single-deployment planning options."""

    function = click.option("--set", "values", multiple=True, metavar="KEY=VALUE")(function)
    function = click.option(
        "--workspace-workdir-mode",
        type=click.Choice(("project-root", "private-root")),
        default=None,
    )(function)
    function = click.option(
        "--private-workspace/--no-private-workspace",
        default=None,
        help="Select optional private per-instance storage.",
    )(function)
    function = click.option("--workdir", default=".")(function)
    function = click.option("--credential", required=True)(function)
    function = click.option("--tool", required=True)(function)
    function = click.option("--profile-name", required=True)(function)
    function = click.option("--specialist-name", required=True)(function)
    function = click.option("--deployment-name", required=True)(function)
    return function


@project_agent_definitions_group.command(name="plan")
@click.argument("definition", type=click.Path(path_type=Path, file_okay=False))
@_plan_options
def plan_command(
    definition: Path,
    deployment_name: str,
    specialist_name: str,
    profile_name: str,
    tool: str,
    credential: str,
    workdir: str,
    values: tuple[str, ...],
    private_workspace: bool | None,
    workspace_workdir_mode: str | None,
) -> None:
    """Create one non-secret request and deterministic Deployment Plan."""

    try:
        payload = _build_plan(
            definition=definition,
            deployment_name=deployment_name,
            specialist_name=specialist_name,
            profile_name=profile_name,
            tool=tool,
            credential=credential,
            workdir=workdir,
            values=values,
            private_workspace=private_workspace,
            workspace_workdir_mode=workspace_workdir_mode,
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="apply")
@click.argument("plan", type=click.Path(path_type=Path, exists=True, file_okay=False))
def apply_command(plan: Path) -> None:
    """Apply one intact Deployment Plan without launching the agent."""

    try:
        payload = apply_deployment(plan, overlay=_resolve_existing_project_overlay())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="inspect")
@click.argument("deployment_name", required=False)
def inspect_command(deployment_name: str | None) -> None:
    """List deployments or inspect one deployment by name."""

    try:
        overlay = _resolve_existing_project_overlay()
        payload: object = (
            inspect_agent_deployment(overlay, deployment_name)
            if deployment_name is not None
            else {"deployments": list_agent_deployments(overlay)}
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="doctor")
def doctor_command() -> None:
    """Diagnose plan journals and deployment-owned content drift."""

    try:
        payload = doctor_agent_deployments(_resolve_existing_project_overlay())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="update")
@click.argument("definition", type=click.Path(path_type=Path, file_okay=False))
@_plan_options
def update_command(
    definition: Path,
    deployment_name: str,
    specialist_name: str,
    profile_name: str,
    tool: str,
    credential: str,
    workdir: str,
    values: tuple[str, ...],
    private_workspace: bool | None,
    workspace_workdir_mode: str | None,
) -> None:
    """Create a fresh request and plan for an explicit deployment update."""

    try:
        current = inspect_agent_deployment(_resolve_existing_project_overlay(), deployment_name)
        revision = validate_revision(definition)
        if current["definition_id"] != revision.definition.definition_id:
            raise ValueError("A deployment update cannot change definition identity.")
        if specialist_name == current["specialist_name"] or profile_name == current["profile_name"]:
            raise ValueError(
                "Update requires fresh specialist and profile names for recoverable publication."
            )
        if current[
            "instance_contract_digest"
        ] != revision.instance_contract_digest and deployment_instance_references(
            _resolve_existing_project_overlay(),
            str(current["deployment_id"]),
        ):
            raise ValueError(
                "Instance-contract changes are blocked by live or preserved instance state."
            )
        payload = _build_plan(
            definition=definition,
            deployment_name=deployment_name,
            specialist_name=specialist_name,
            profile_name=profile_name,
            tool=tool,
            credential=credential,
            workdir=workdir,
            values=values,
            private_workspace=private_workspace,
            workspace_workdir_mode=workspace_workdir_mode,
            update_existing=True,
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="remove")
@click.argument("deployment_name")
def remove_command(deployment_name: str) -> None:
    """Remove one unreferenced Agent Deployment and owned relationships."""

    try:
        payload = remove_agent_deployment(_resolve_existing_project_overlay(), deployment_name)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="batch-plan")
@click.argument("definition", type=click.Path(path_type=Path, file_okay=False))
@click.option("--count", type=click.IntRange(min=1, max=32), required=True)
@click.option("--set", "values", multiple=True, metavar="KEY=VALUE")
@click.option("--workdir", default=".")
@click.option("--tool")
@click.option("--credential")
@click.option("--name-prefix")
@click.option("--delegate-names", is_flag=True)
@click.option("--delegate-tools", is_flag=True)
@click.option("--delegate-credentials", is_flag=True)
@click.option(
    "--member-override",
    "member_overrides",
    multiple=True,
    metavar="JSON",
    help="One JSON BatchMemberOverride object.",
)
@click.option("--private-workspace/--no-private-workspace", default=None)
@click.option(
    "--workspace-workdir-mode",
    type=click.Choice(("project-root", "private-root")),
    default=None,
)
def batch_plan_command(
    definition: Path,
    count: int,
    values: tuple[str, ...],
    workdir: str,
    tool: str | None,
    credential: str | None,
    name_prefix: str | None,
    delegate_names: bool,
    delegate_tools: bool,
    delegate_credentials: bool,
    member_overrides: tuple[str, ...],
    private_workspace: bool | None,
    workspace_workdir_mode: str | None,
) -> None:
    """Plan N ordinary deployments from one exact definition revision."""

    try:
        parsed_overrides = tuple(
            BatchMemberOverride.model_validate(json.loads(raw)) for raw in member_overrides
        )
        overlay = _ensure_project_overlay()
        request = create_batch_request(
            revision_root=definition,
            overlay=overlay,
            count=count,
            shared_values=_parse_set_values(values),
            workdir=workdir,
            tool=tool,
            credential=credential,
            name_prefix=name_prefix,
            delegation=BatchDelegation(
                names=delegate_names,
                tools=delegate_tools,
                credentials=delegate_credentials,
            ),
            member_overrides=parsed_overrides,
            private_workspace_enabled=private_workspace,
            workspace_workdir_mode=workspace_workdir_mode,
        )
        plan, plan_root = plan_batch_deployment(request, overlay=overlay)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "operation_id": plan.operation_id,
            "batch_plan_path": str(plan_root),
            "batch_digest": plan.batch_digest,
            "members": [member.model_dump(mode="json") for member in plan.members],
            "apply_command": (
                "houmao-mgr project agent-definitions batch-apply " + json.dumps(str(plan_root))
            ),
        }
    )


@project_agent_definitions_group.command(name="batch-apply")
@click.argument("batch_plan", type=click.Path(path_type=Path, exists=True, file_okay=False))
def batch_apply_command(batch_plan: Path) -> None:
    """Apply one complete batch plan without launching any member."""

    try:
        payload = apply_batch_deployment(batch_plan, overlay=_resolve_existing_project_overlay())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="batch-inspect-operation")
@click.argument("batch_plan", type=click.Path(path_type=Path, exists=True, file_okay=False))
def batch_inspect_command(batch_plan: Path) -> None:
    """Inspect operation provenance without a durable batch business object."""

    try:
        payload = inspect_batch_operation(batch_plan, overlay=_resolve_existing_project_overlay())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


@project_agent_definitions_group.command(name="batch-doctor")
def batch_doctor_command() -> None:
    """Diagnose interrupted or edited batch operations."""

    try:
        payload = doctor_batch_operations(_resolve_existing_project_overlay())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    emit(payload)


__all__ = ["project_agent_definitions_group"]
