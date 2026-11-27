"""Dispatch admitted finite operations to maintained owner-local application services."""

from __future__ import annotations

import json
from pathlib import Path
from time import monotonic
from typing import cast

from pydantic import BaseModel, JsonValue

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import load_registry_mode_authority
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.execution.arguments import (
    CleanupArguments,
    GatewayAttachArguments,
    LaunchArguments,
    NoArguments,
    OwnerOperation,
    PromptArguments,
    RefreshArguments,
    RelaunchArguments,
)
from houmao.execution.context import (
    current_execution_deadline,
    execution_deadline_scope,
    execution_read_only_scope,
)
from houmao.execution.models import ExecutionBindingV1, ExecutionRequestV1, JsonObject
from houmao.execution.owner import OwnerAdmissionError, OwnerPolicyV1, prepare_owner_operation


def dispatch_operation(
    request: ExecutionRequestV1 | OwnerOperation,
    binding: ExecutionBindingV1,
    policy: OwnerPolicyV1,
) -> JsonObject:
    """Run the validated operation under the owner-local application scope."""

    from houmao.srv_ctrl.commands import managed_agents as managed

    operation = (
        prepare_owner_operation(request, policy)
        if isinstance(request, ExecutionRequestV1)
        else request
    )
    with managed.owner_local_target_scope(), execution_read_only_scope(operation.read_only):
        if isinstance(operation.arguments, LaunchArguments):
            return _launch(operation.arguments)
        return _control(operation.request, operation.arguments, binding)


def _json_result(value: object) -> JsonObject:
    """Normalize a maintained service result to a bounded protocol object."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    document: object = json.loads(json.dumps(value))
    if not isinstance(document, dict):
        return {"result": cast(JsonValue, document)}
    return cast(JsonObject, document)


def _launch(arguments: LaunchArguments) -> JsonObject:
    """Return the shared launch completion directly as the protocol result."""

    from houmao.srv_ctrl.commands.agents.core import ManagedTmuxPreflightError
    from houmao.srv_ctrl.commands.project_easy import (
        ProjectRunModePreflightError,
        launch_project_agent,
    )

    assert arguments.project_dir is not None
    try:
        completion = launch_project_agent(arguments, project_dir=Path(arguments.project_dir))
    except ProjectRunModePreflightError as exc:
        raise OwnerAdmissionError("invalid_run_mode", str(exc)) from None
    except ManagedTmuxPreflightError as exc:
        raise OwnerAdmissionError("invalid_tmux_server", str(exc)) from None
    return _json_result(completion.payload)


def _control(
    request: ExecutionRequestV1, arguments: NoArguments, binding: ExecutionBindingV1
) -> JsonObject:
    """Verify owner identity and generation before resolving maintained runtime control."""

    from houmao.agents.realm_controller.registry_storage import (
        load_managed_agent_record_by_agent_id,
    )
    from houmao.srv_ctrl.commands import managed_agents as managed

    started = monotonic()
    if request.agent_id is None:
        if request.operation == "describe":
            return {"initialized": True, "uid": binding.uid, "gid": binding.gid}
        raise OwnerAdmissionError("agent_required", "An exact managed-agent ID is required.")
    try:
        record = load_managed_agent_record_by_agent_id(request.agent_id)
    except (SessionManifestError, OSError):
        raise OwnerAdmissionError(
            "unusable_mode_authority",
            "The owner could not read a current managed-agent registry record. "
            "Stop agents from an earlier Houmao release with that release, "
            "then start a fresh runtime session.",
        ) from None
    if record is None:
        raise OwnerAdmissionError("agent_not_found", "Owner has no matching managed agent.")
    if record.agent_id != request.agent_id:
        raise OwnerAdmissionError(
            "identity_mismatch", "Owner record differs from the requested agent identity."
        )
    if record.execution_binding != binding:
        raise OwnerAdmissionError(
            "context_mismatch", "Agent belongs to a different execution binding."
        )
    if request.generation_id is not None and request.generation_id != record.generation_id:
        raise OwnerAdmissionError(
            "generation_conflict", "Agent generation changed before admission."
        )
    operation = request.operation
    if operation == "describe":
        try:
            manifest = load_registry_mode_authority(record)
        except (SessionManifestError, OSError):
            raise OwnerAdmissionError(
                "unusable_mode_authority",
                "The owner registry record lacks matching current session mode and native "
                "surface authority. Stop agents from an earlier Houmao release with that "
                "release, then start a fresh runtime session.",
            ) from None
        return {
            "initialized": True,
            "identity": _json_result(managed._identity_from_record(record, manifest=manifest)),
            "lifecycle": _json_result(record.lifecycle),
            "generation_id": record.generation_id,
        }
    if isinstance(arguments, CleanupArguments):
        return _cleanup(record, arguments)
    # Reconstruction is validation, even for a mutating operation. Only the
    # explicit operation below may repair or change runtime-owned material.
    with execution_read_only_scope():
        target = (
            managed.resolve_relaunch_managed_agent_target(
                agent_id=request.agent_id, agent_name=None, port=None
            )
            if operation == "relaunch"
            else managed.resolve_managed_agent_target(
                agent_id=request.agent_id,
                agent_name=None,
                port=None,
                include_inactive=operation in {"state", "inspect", "capture"},
            )
        )
    # Recheck after reconstruction, which can race another lifecycle controller.
    current = load_managed_agent_record_by_agent_id(request.agent_id)
    if current is None:
        raise OwnerAdmissionError("agent_not_found", "Agent disappeared during target resolution.")
    if current.agent_id != request.agent_id:
        raise OwnerAdmissionError(
            "identity_mismatch", "Agent identity changed during target resolution."
        )
    if current.execution_binding != binding:
        raise OwnerAdmissionError(
            "context_mismatch", "Agent execution binding changed during target resolution."
        )
    if current.generation_id != record.generation_id:
        raise OwnerAdmissionError("generation_conflict", "Agent changed during target resolution.")
    deadline = started + request.deadline_seconds
    admitted_deadline = current_execution_deadline()
    if admitted_deadline is not None:
        deadline = min(deadline, admitted_deadline)
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise OwnerAdmissionError(
            "deadline_exhausted", "Execution deadline expired before operation admission."
        )
    if operation == "state":
        return _json_result(managed.managed_agent_state_payload(target))
    if operation in {"inspect", "capture"}:
        return _json_result(managed.managed_agent_detail_payload(target))
    if operation == "resume":
        return _json_result(managed.managed_agent_identity_payload(target))
    if operation == "home":
        return _json_result(managed.managed_agent_native_home(target))
    if operation in {"status", "refresh_check"}:
        return _json_result(managed.managed_agent_common_plugin_state(target))
    if isinstance(arguments, RefreshArguments):
        return _json_result(
            managed.refresh_managed_agent(
                target, timeout_seconds=min(arguments.timeout_seconds, remaining)
            )
        )
    if isinstance(arguments, PromptArguments):
        # Leave time to serialize and transmit the result when native work is still active.
        with execution_deadline_scope(deadline - min(0.25, remaining / 2)):
            try:
                return _json_result(
                    managed.prompt_managed_agent(
                        target,
                        prompt=arguments.prompt,
                        model=arguments.model,
                        reasoning_level=arguments.reasoning_level,
                    )
                )
            except managed.HermesManagerPromptRefused as exc:
                raise OwnerAdmissionError(exc.code, exc.message) from None
    if operation == "interrupt":
        return _json_result(managed.interrupt_managed_agent(target))
    if operation == "stop":
        return _json_result(managed.stop_managed_agent(target))
    if isinstance(arguments, RelaunchArguments):
        return _json_result(
            managed.relaunch_managed_agent(target, relaunch_chat_session=arguments.chat_session)
        )
    if operation == "gateway_status":
        return _json_result(managed.gateway_status(target))
    if operation == "gateway_detach":
        return _json_result(managed.detach_gateway(target))
    if isinstance(arguments, GatewayAttachArguments):
        return _json_result(
            managed.attach_gateway(
                target,
                background=arguments.background,
                tui_tracking_timing_overrides=arguments.tui_tracking_timing_overrides,
                access_config_path=(
                    Path(arguments.access_config_path)
                    if arguments.access_config_path is not None
                    else None
                ),
            )
        )
    raise OwnerAdmissionError("unsupported_operation", "Unsupported finite owner operation.")


def _cleanup(record: ManagedAgentRegistryRecordV3, arguments: CleanupArguments) -> JsonObject:
    """Clean only the admitted owner's selected session through maintained safety checks."""

    from houmao.srv_ctrl.commands.runtime_cleanup import (
        cleanup_managed_session,
        cleanup_managed_session_logs,
        cleanup_managed_session_mailbox,
    )

    kind = arguments.kind
    if kind == "session":
        return _json_result(
            cleanup_managed_session(
                agent_id=record.agent_id,
                agent_name=None,
                manifest_path=None,
                session_root=None,
                dry_run=arguments.dry_run,
                purge_registry=arguments.purge_registry,
                expected_record=record,
            )
        )
    function = cleanup_managed_session_logs if kind == "logs" else cleanup_managed_session_mailbox
    return _json_result(
        function(
            agent_id=record.agent_id,
            agent_name=None,
            manifest_path=None,
            session_root=None,
            dry_run=arguments.dry_run,
            expected_record=record,
        )
    )
