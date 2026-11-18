"""Dispatch admitted finite operations to maintained owner-local application services."""

from __future__ import annotations

from houmao.gateway.deployment import validate_gateway_access_config_path

import json
from pathlib import Path
from time import monotonic
from typing import Any, cast

import click
from click._utils import UNSET
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.models import RelaunchChatSessionSelection
from houmao.execution.context import execution_read_only_scope

from houmao.execution.models import ExecutionBindingV1, ExecutionRequestV1, JsonObject
from houmao.execution.owner import OwnerAdmissionError, OwnerPolicyV1

_READ_ONLY_DISPATCH = frozenset(
    {
        "describe",
        "state",
        "inspect",
        "capture",
        "resume",
        "home",
        "status",
        "refresh_check",
        "gateway_status",
    }
)


class _PromptArguments(BaseModel):
    """Validate prompt inputs before touching runtime state."""

    model_config = ConfigDict(extra="forbid", strict=True)
    prompt: str = Field(min_length=1)
    model: str | None = None
    reasoning_level: int | None = Field(default=None, ge=0)


def dispatch_operation(
    request: ExecutionRequestV1, binding: ExecutionBindingV1, policy: OwnerPolicyV1
) -> JsonObject:
    """Use existing owner-local launch and lifecycle behavior after fixed-policy admission."""

    from houmao.srv_ctrl.commands import managed_agents as managed

    read_only = request.operation in _READ_ONLY_DISPATCH or (
        request.operation == "cleanup" and request.arguments.get("dry_run") is True
    )
    with managed.owner_local_target_scope(), execution_read_only_scope(read_only):
        if request.operation == "launch":
            return _launch(request, policy)
        return _control(request, binding)


def _json_result(value: object) -> JsonObject:
    """Normalize a maintained service result to a bounded protocol object."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    document: object = json.loads(json.dumps(value))
    if not isinstance(document, dict):
        return {"result": cast(JsonValue, document)}
    return cast(JsonObject, document)


def _launch(request: ExecutionRequestV1, policy: OwnerPolicyV1) -> JsonObject:
    """Validate target-side launch parameters and call the shared project launch service."""

    from houmao.srv_ctrl.commands.output import collect_output_payloads
    from houmao.srv_ctrl.commands.project_context import store_project_command_context
    from houmao.srv_ctrl.commands.project_easy import (
        launch_easy_instance_command,
        launch_project_agent,
    )

    started = monotonic()
    supplied = dict(request.arguments)
    project_dir = supplied.pop("project_dir", policy.profile.project_root)
    if not isinstance(project_dir, str):
        raise OwnerAdmissionError("invalid_arguments", "Project directory must be a target path.")
    path = Path(project_dir)
    if not path.is_absolute():
        path = Path(policy.profile.project_root) / path
    allowed = {parameter.name for parameter in launch_easy_instance_command.params} - {"executor"}
    if set(supplied) - allowed:
        raise OwnerAdmissionError("invalid_arguments", "Unsupported project launch parameter.")
    parameters: dict[str, Any] = {}
    with click.Context(launch_easy_instance_command, obj={}) as context:
        store_project_command_context(context, project_dir=path)
        try:
            for parameter in launch_easy_instance_command.params:
                name = parameter.name
                if name is None or name == "executor":
                    continue
                value = supplied.get(name, parameter.get_default(context))
                # Click's repeatable inputs arrive as JSON arrays over stdio.
                if parameter.multiple and isinstance(value, list):
                    value = tuple(value)
                processed = parameter.process_value(context, value)
                parameters[name] = None if processed is UNSET else processed
        except (click.BadParameter, click.MissingParameter):
            raise OwnerAdmissionError(
                "invalid_arguments", "Invalid project launch parameter."
            ) from None
        # Workdir validation belongs here, after entering the owner environment.
        workdir = parameters.get("workdir")
        if workdir is not None:
            workdir = Path(workdir)
            if not workdir.is_absolute():
                workdir = path / workdir
            if not workdir.is_dir():
                raise OwnerAdmissionError("invalid_target_path", "Target workdir is unavailable.")
            parameters["workdir"] = workdir
        else:
            parameters["workdir"] = path
        tool_params = parameters.get("tool_params")
        if isinstance(tool_params, str) and tool_params.startswith("@") and len(tool_params) > 1:
            params_path = Path(tool_params[1:]).expanduser()
            parameters["tool_params"] = f"@{path / params_path}"
        if monotonic() - started >= request.deadline_seconds:
            raise OwnerAdmissionError(
                "deadline_exhausted", "Execution deadline expired before launch preparation."
            )
        with collect_output_payloads() as results:
            launch_project_agent(**parameters)
    for result in results:
        if isinstance(result, dict) and result.get("agent_id"):
            return _json_result(result)
    raise RuntimeError("Owner launch did not return its admitted identity")


def _control(request: ExecutionRequestV1, binding: ExecutionBindingV1) -> JsonObject:
    """Verify owner identity and generation before resolving maintained runtime control."""

    from houmao.agents.realm_controller.registry_storage import (
        load_managed_agent_record_by_agent_id,
    )
    from houmao.srv_ctrl.commands import managed_agents as managed

    started = monotonic()
    if request.agent_id is None:
        if request.operation == "describe" and not request.arguments:
            return {"initialized": True, "uid": binding.uid, "gid": binding.gid}
        raise OwnerAdmissionError("agent_required", "An exact managed-agent ID is required.")
    record = load_managed_agent_record_by_agent_id(request.agent_id)
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
    arguments = dict(request.arguments)
    allowed: dict[str, set[str]] = {
        "describe": set(),
        "state": set(),
        "inspect": set(),
        "capture": set(),
        "resume": set(),
        "home": set(),
        "status": set(),
        "refresh_check": set(),
        "interrupt": set(),
        "stop": set(),
        "gateway_status": set(),
        "gateway_detach": set(),
        "prompt": {"prompt", "model", "reasoning_level"},
        "refresh": {"timeout_seconds"},
        "relaunch": {"chat_session"},
        "gateway_attach": {"background", "tui_tracking_timing_overrides", "access_config_path"},
        "cleanup": {"kind", "dry_run", "purge_registry"},
    }
    if operation not in allowed or set(arguments) - allowed[operation]:
        raise OwnerAdmissionError(
            "unsupported_operation", "Unsupported finite operation or arguments."
        )
    if operation == "describe":
        return {
            "initialized": True,
            "identity": _json_result(managed._identity_from_record(record)),
            "lifecycle": _json_result(record.lifecycle),
            "generation_id": record.generation_id,
        }
    if operation == "cleanup":
        return _cleanup(request.agent_id, arguments)
    if operation == "prompt":
        try:
            _PromptArguments.model_validate(arguments)
        except ValueError:
            raise OwnerAdmissionError("invalid_arguments", "Invalid prompt arguments.") from None
    if operation == "refresh":
        timeout = arguments.get("timeout_seconds", request.deadline_seconds)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0 < timeout <= 120
        ):
            raise OwnerAdmissionError("invalid_arguments", "Invalid refresh deadline.")
    selected: RelaunchChatSessionSelection | None = None
    if operation == "relaunch":
        selection = arguments.get("chat_session")
        try:
            selected = (
                TypeAdapter(RelaunchChatSessionSelection).validate_json(json.dumps(selection))
                if selection is not None
                else None
            )
        except ValueError:
            raise OwnerAdmissionError(
                "invalid_arguments", "Invalid relaunch chat-session selection."
            ) from None
    timings: GatewayTuiTrackingTimingOverridesV1 | None = None
    if operation == "gateway_attach":
        if not isinstance(arguments.get("background", False), bool):
            raise OwnerAdmissionError("invalid_arguments", "Invalid gateway posture.")
        access_path = arguments.get("access_config_path")
        if "access_config_path" in arguments:
            try:
                access_path = validate_gateway_access_config_path(access_path)
            except ValueError:
                raise OwnerAdmissionError(
                    "invalid_arguments", "Invalid gateway access configuration path."
                ) from None
        timing = arguments.get("tui_tracking_timing_overrides")
        try:
            timings = (
                GatewayTuiTrackingTimingOverridesV1.model_validate(timing)
                if timing is not None
                else None
            )
        except ValueError:
            raise OwnerAdmissionError(
                "invalid_arguments", "Invalid gateway tracking parameters."
            ) from None
    # Reconstruction is validation, even for a mutating operation. Only the
    # explicit operation below may repair or change runtime-owned material.
    with execution_read_only_scope():
        target = (
            managed.resolve_relaunch_managed_agent_target(
                agent_id=request.agent_id, agent_name=None, port=None
            )
            if operation == "relaunch"
            else managed.resolve_managed_agent_target(
                agent_id=request.agent_id, agent_name=None, port=None
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
    remaining = request.deadline_seconds - (monotonic() - started)
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
    if operation == "refresh":
        return _json_result(
            managed.refresh_managed_agent(
                target, timeout_seconds=min(float(cast(float, timeout)), remaining)
            )
        )
    if operation == "prompt":
        prompt = _PromptArguments.model_validate(arguments)
        return _json_result(managed.prompt_managed_agent(target, **prompt.model_dump()))
    if operation == "interrupt":
        return _json_result(managed.interrupt_managed_agent(target))
    if operation == "stop":
        return _json_result(managed.stop_managed_agent(target))
    if operation == "relaunch":
        return _json_result(managed.relaunch_managed_agent(target, relaunch_chat_session=selected))
    if operation == "gateway_status":
        return _json_result(managed.gateway_status(target))
    if operation == "gateway_detach":
        return _json_result(managed.detach_gateway(target))
    if operation == "gateway_attach":
        return _json_result(
            managed.attach_gateway(
                target,
                background=cast(bool, arguments.get("background", False)),
                tui_tracking_timing_overrides=timings,
                access_config_path=Path(access_path) if isinstance(access_path, str) else None,
            )
        )
    raise OwnerAdmissionError("unsupported_operation", "Unsupported finite owner operation.")


def _cleanup(agent_id: str, arguments: JsonObject) -> JsonObject:
    """Clean only the admitted owner's selected session through maintained safety checks."""

    from houmao.srv_ctrl.commands.runtime_cleanup import (
        cleanup_managed_session,
        cleanup_managed_session_logs,
        cleanup_managed_session_mailbox,
    )

    kind = arguments.get("kind")
    dry_run = arguments.get("dry_run", False)
    purge = arguments.get("purge_registry", False)
    if (
        kind not in {"session", "logs", "mailbox"}
        or not isinstance(dry_run, bool)
        or not isinstance(purge, bool)
    ):
        raise OwnerAdmissionError(
            "invalid_arguments", "Invalid selected-session cleanup arguments."
        )
    if kind == "session":
        return _json_result(
            cleanup_managed_session(
                agent_id=agent_id,
                agent_name=None,
                manifest_path=None,
                session_root=None,
                dry_run=dry_run,
                purge_registry=purge,
            )
        )
    function = cleanup_managed_session_logs if kind == "logs" else cleanup_managed_session_mailbox
    return _json_result(
        function(
            agent_id=agent_id,
            agent_name=None,
            manifest_path=None,
            session_root=None,
            dry_run=dry_run,
        )
    )
