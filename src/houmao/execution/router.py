"""Operator-side routing that preserves admitted owner identity without local fallback."""

from __future__ import annotations

import json
from pathlib import Path
from time import monotonic
from typing import Any, cast

import click

from houmao.execution.locators import ExecutorAgentLocatorV1, publish_executor_locator
from houmao.execution.models import (
    ExecutionOperation,
    ExecutionRequestV1,
    ExecutionResponseV1,
    JsonObject,
    route_fingerprint,
)
from houmao.execution.profiles import load_execution_profile
from houmao.execution.transports import execute_request


def execute_bound_operation(
    locator: ExecutorAgentLocatorV1,
    operation: ExecutionOperation,
    arguments: JsonObject | None = None,
) -> ExecutionResponseV1:
    """Describe and operate on the pinned owner; never retry a mutation or local substitute."""

    started = monotonic()
    profile = load_execution_profile(locator.profile_name)
    if route_fingerprint(profile) != locator.binding.route_fingerprint:
        raise click.ClickException(
            "Execution profile changed authority; refusing to retarget agent."
        )
    arguments = dict(arguments or {})
    budget = profile.timeout_seconds
    if operation == "refresh":
        supplied_timeout = arguments.get("timeout_seconds", budget)
        if (
            isinstance(supplied_timeout, bool)
            or not isinstance(supplied_timeout, (int, float))
            or not 0 < supplied_timeout <= 120
        ):
            raise click.ClickException("Invalid finite refresh deadline.")
        budget = min(budget, float(supplied_timeout))
    remaining = budget - (monotonic() - started)
    if remaining <= 0:
        raise click.ClickException("Execution deadline expired before owner discovery.")
    described = execute_request(
        profile,
        ExecutionRequestV1(
            operation="describe",
            expected_binding=locator.binding,
            agent_id=locator.agent_id,
            deadline_seconds=remaining,
        ),
    )
    if described.outcome != "completed":
        return described
    if described.binding != locator.binding:
        raise click.ClickException("Owner reported a different execution binding.")
    identity = described.result.get("identity")
    if not isinstance(identity, dict) or identity.get("agent_id") != locator.agent_id:
        raise click.ClickException("Owner reported a different managed-agent identity.")
    if operation == "describe":
        return described
    generation = described.result.get("generation_id")
    if not isinstance(generation, str):
        raise click.ClickException("Owner did not report an authoritative generation.")
    remaining = budget - (monotonic() - started)
    if remaining <= 0:
        raise click.ClickException("Execution deadline expired before mutation admission.")
    if operation == "refresh":
        arguments["timeout_seconds"] = remaining
    return execute_request(
        profile,
        ExecutionRequestV1(
            operation=operation,
            arguments=arguments,
            expected_binding=locator.binding,
            agent_id=locator.agent_id,
            generation_id=generation,
            deadline_seconds=remaining,
        ),
    )


def require_execution_result(response: ExecutionResponseV1) -> JsonObject:
    """Return confirmed results or surface safe owner failure/uncertainty information."""

    if response.outcome != "completed":
        raise click.ClickException(
            f"Execution {response.outcome}: {response.error_code}; request={response.request_id}. "
            "Inspect the owning agent before deliberately retrying."
        )
    return response.result


def launch_with_executor(executor: str, parameters: dict[str, Any]) -> None:
    """Enter a trusted target before any caller-side project or runtime preparation."""

    from houmao.srv_ctrl.commands.output import emit
    from houmao.srv_ctrl.commands.project_context import active_project_dir

    profile = load_execution_profile(executor)
    values = dict(parameters)
    project_dir = active_project_dir()
    values["project_dir"] = str(project_dir) if project_dir is not None else profile.project_root
    arguments = cast(JsonObject, json.loads(json.dumps(values, default=_json_path)))
    response = execute_request(
        profile,
        ExecutionRequestV1(
            operation="launch",
            arguments=arguments,
            deadline_seconds=profile.timeout_seconds,
        ),
    )
    result = require_execution_result(response)
    identity = result.get("agent_id")
    name = result.get("agent_name")
    if not isinstance(identity, str) or not isinstance(name, str) or response.binding is None:
        raise click.ClickException(
            "Owner launch returned no admitted identity; inspect before retrying."
        )
    locator = ExecutorAgentLocatorV1(
        agent_id=identity,
        agent_name=name,
        profile_name=profile.name,
        binding=response.binding,
    )
    try:
        publish_executor_locator(locator)
    except (OSError, ValueError):
        emit(
            {
                "outcome": "partial_success",
                "agent_id": identity,
                "execution_context": response.binding.model_dump(mode="json"),
                "locator_published": False,
                "recovery": f"houmao-mgr admin executors reconcile --executor {executor} --agent-id {identity}",
            }
        )
        raise click.ClickException(
            "Owner launch succeeded; operator locator publication failed. Do not launch again."
        ) from None
    emit({**result, "execution_context": response.binding.model_dump(mode="json")})


def reconcile_executor_agent(executor: str, agent_id: str) -> ExecutorAgentLocatorV1:
    """Recover an admitted owner identity without another launch or context migration."""

    profile = load_execution_profile(executor)
    response = execute_request(
        profile,
        ExecutionRequestV1(
            operation="describe",
            agent_id=agent_id,
            deadline_seconds=profile.timeout_seconds,
        ),
    )
    result = require_execution_result(response)
    identity = result.get("identity")
    if not isinstance(identity, dict) or response.binding is None:
        raise click.ClickException("Owner did not return an admitted managed identity.")
    name = identity.get("agent_name")
    observed_id = identity.get("agent_id") or identity.get("tracked_agent_id")
    if observed_id != agent_id or not isinstance(name, str):
        raise click.ClickException("Owner identity does not match reconciliation target.")
    return publish_executor_locator(
        ExecutorAgentLocatorV1(
            agent_id=agent_id,
            agent_name=name,
            profile_name=executor,
            binding=response.binding,
        )
    )


def _json_path(value: object) -> str:
    """Serialize explicit target path inputs without resolving them locally."""

    if isinstance(value, Path):
        return str(value)
    raise TypeError("Unsupported launch input")
