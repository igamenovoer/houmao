"""Execution application boundaries retain identity and avoid replay after uncertain mutation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import pwd
from types import SimpleNamespace
from unittest.mock import Mock

import click
from pydantic import ValidationError
import pytest

from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxSlotV1,
    RegistryMailboxesV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.execution import application, router
from houmao.execution.context import execution_is_read_only
from houmao.execution.locators import ExecutorAgentLocatorV1
from houmao.execution.locators import load_executor_locator, publish_executor_locator
from houmao.execution.models import (
    ControllerScopeV1,
    ExecutionBindingV1,
    ExecutionProfileV1,
    ExecutionRequestV1,
    ExecutionResponseV1,
    route_fingerprint,
)
from houmao.execution.owner import OwnerAdmissionError, OwnerPolicyV1
from houmao.execution.profiles import ExecutionProfileError
from houmao.passive_server.models import PassiveHeadlessLaunchRequest
from houmao.srv_ctrl.commands import managed_agents as managed
from houmao.srv_ctrl.commands import project_easy
from houmao.srv_ctrl.commands.output import collect_output_payloads, emit


@pytest.fixture
def boundary(tmp_path: Path) -> SimpleNamespace:
    """Provide strict owner, controller, and lifecycle contracts without a harness process."""

    project = tmp_path / "target-project"
    project.mkdir()
    profile = ExecutionProfileV1(
        name="worker",
        transport="local",
        account=pwd.getpwuid(os.geteuid()).pw_name,
        entrypoint="/usr/local/bin/houmao-mgr",
        policy_path=str(tmp_path / "policy.yaml"),
        project_root=str(project),
    )
    scope = ControllerScopeV1(
        controller_id="operator",
        authority="local_uid",
        operations=("describe", "state", "launch", "relaunch", "gateway_attach", "refresh", "stop"),
        project_roots=(str(project),),
    )
    policy = OwnerPolicyV1(
        profile=profile,
        controller=scope,
        uid=os.geteuid(),
        gid=os.getegid(),
        registry_root=str(tmp_path / "registry"),
        runtime_root=str(tmp_path / "runtime"),
    )
    binding = ExecutionBindingV1(
        context_id="owner-context",
        host_id="owner-host",
        account=profile.account,
        uid=policy.uid,
        gid=policy.gid,
        groups=tuple(os.getgroups()),
        registry_root=policy.registry_root,
        runtime_root=policy.runtime_root,
        project_root=profile.project_root,
        profile_name=profile.name,
        transport=profile.transport,
        controller=scope,
        route_fingerprint=route_fingerprint(profile),
        tmux_socket=str(tmp_path / "server.sock"),
    )
    now = datetime.now(UTC)
    record = ManagedAgentRegistryRecordV3(
        agent_id="agent-1",
        agent_name="reviewer",
        generation_id="generation-1",
        lifecycle=RegistryLifecycleV1(
            state="active", relaunchable=True, state_updated_at=now.isoformat()
        ),
        identity=RegistryIdentityV1(backend="codex_headless", tool="codex"),
        runtime=RegistryRuntimeV1(
            manifest_path=str(tmp_path / "runtime/session/manifest.json"),
            session_root=str(tmp_path / "runtime/session"),
            agent_def_dir=str(project / ".houmao/agents"),
        ),
        terminal=RegistryTerminalV2(
            current_session_name="owner-session",
            last_session_name="owner-session",
            socket_path=binding.tmux_socket,
        ),
        liveness=RegistryLivenessV1(
            published_at=now.isoformat(), lease_expires_at=(now + timedelta(days=1)).isoformat()
        ),
        mailboxes=RegistryMailboxesV1(
            offline=RegistryMailboxSlotV1(revision="offline-empty", binding=None),
            online=RegistryMailboxSlotV1(revision="online-empty", binding=None),
        ),
        canonical_mail_identity=None,
        execution_binding=binding,
    )
    locator = ExecutorAgentLocatorV1(
        agent_id=record.agent_id,
        agent_name=record.agent_name,
        profile_name=profile.name,
        binding=binding,
    )
    return SimpleNamespace(
        profile=profile, policy=policy, binding=binding, record=record, locator=locator
    )


def _response(
    request: ExecutionRequestV1, boundary: SimpleNamespace, **result: object
) -> ExecutionResponseV1:
    """Return the exact correlated owner result expected from a qualified transport."""

    return ExecutionResponseV1.model_validate(
        {
            "request_id": request.request_id,
            "outcome": "completed",
            "admitted": True,
            "binding": boundary.binding,
            "result": result,
        }
    )


def _registry(monkeypatch: pytest.MonkeyPatch, value: object) -> Mock:
    """Replace only owner registry I/O while retaining public dispatcher behavior."""

    loader = Mock(return_value=value)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.registry_storage.load_managed_agent_record_by_agent_id",
        loader,
    )
    return loader


@pytest.mark.parametrize(
    "change,code",
    [
        ({"generation_id": "replacement"}, "generation_conflict"),
        ({"execution_binding": None}, "context_mismatch"),
        ({"agent_id": "another-agent"}, "identity_mismatch"),
    ],
)
def test_owner_control_checks_exact_authority_before_reconstruction(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, change: dict[str, object], code: str
) -> None:
    """A matching owner alone cannot authorize a different logical ID or generation."""

    _registry(monkeypatch, boundary.record.model_copy(update=change))
    resolve = Mock(side_effect=AssertionError("invalid target must not be reconstructed"))
    monkeypatch.setattr(managed, "resolve_managed_agent_target", resolve)
    request = ExecutionRequestV1(
        operation="state", agent_id="agent-1", generation_id="generation-1"
    )
    with pytest.raises(OwnerAdmissionError) as error:
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert error.value.code == code
    resolve.assert_not_called()


@pytest.mark.parametrize(
    "change,code",
    [
        ({"generation_id": "replacement"}, "generation_conflict"),
        ({"execution_binding": None}, "context_mismatch"),
        ({"agent_id": "another-agent"}, "identity_mismatch"),
    ],
)
def test_owner_control_rechecks_authority_after_resolution(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, change: dict[str, object], code: str
) -> None:
    """Concurrent owner-record replacement cannot reach a native control operation."""

    loader = _registry(monkeypatch, boundary.record)
    loader.side_effect = [boundary.record, boundary.record.model_copy(update=change)]
    monkeypatch.setattr(managed, "resolve_managed_agent_target", lambda **kwargs: object())
    state = Mock(side_effect=AssertionError("replacement must not be inspected"))
    monkeypatch.setattr(managed, "managed_agent_state_payload", state)
    request = ExecutionRequestV1(
        operation="state", agent_id="agent-1", generation_id="generation-1"
    )
    with pytest.raises(OwnerAdmissionError) as error:
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert error.value.code == code
    state.assert_not_called()


@pytest.mark.parametrize(
    "operation,arguments",
    [
        ("state", {"unexpected": "value"}),
        ("prompt", {"prompt": 42}),
        ("refresh", {"timeout_seconds": True}),
        ("relaunch", {"chat_session": {"mode": "exact"}}),
        ("gateway_attach", {"background": "yes"}),
        ("gateway_attach", {"tui_tracking_timing_overrides": {"watch_poll_interval_seconds": -1}}),
    ],
)
def test_invalid_operation_parameters_fail_before_runtime_resolution(
    boundary: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    arguments: dict[str, object],
) -> None:
    """Closed argument validation happens before preparation can mutate runtime material."""

    _registry(monkeypatch, boundary.record)
    resolve = Mock(side_effect=AssertionError("invalid input must not reconstruct runtime"))
    monkeypatch.setattr(managed, "resolve_managed_agent_target", resolve)
    monkeypatch.setattr(managed, "resolve_relaunch_managed_agent_target", resolve)
    request = ExecutionRequestV1.model_validate(
        {
            "operation": operation,
            "arguments": arguments,
            "agent_id": "agent-1",
            "generation_id": "generation-1",
        }
    )
    with pytest.raises(OwnerAdmissionError):
        application.dispatch_operation(request, boundary.binding, boundary.policy)
    resolve.assert_not_called()


def test_owner_launch_reuses_shared_service_and_output_collector(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The delegated path preserves maintained launch preparation and captures its result."""

    seen = []

    def launch(**parameters: object) -> None:
        """Act as the maintained application boundary without starting a harness."""

        assert managed._OWNER_LOCAL_TARGET_SCOPE.get()
        seen.append(parameters)
        emit(
            {
                "agent_id": "agent-1",
                "agent_name": "reviewer",
                "manifest_path": "/owner/manifest.json",
            }
        )

    monkeypatch.setattr(project_easy, "launch_project_agent", launch)
    result = application.dispatch_operation(
        ExecutionRequestV1(operation="launch", arguments={"profile": "reviewer"}),
        boundary.binding,
        boundary.policy,
    )
    assert result["agent_id"] == "agent-1"
    assert len(seen) == 1 and seen[0]["profile"] == "reviewer"
    assert seen[0]["workdir"] == Path(boundary.profile.project_root)
    assert "executor" not in seen[0]


def test_bound_route_rejects_a_different_described_identity(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh generation value is insufficient when the owner describes another agent."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    calls = []

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Capture any accidental second mutation after a mismatched describe response."""

        calls.append(request.operation)
        return _response(
            request, boundary, identity={"agent_id": "another-agent"}, generation_id="generation-1"
        )

    monkeypatch.setattr(router, "execute_request", execute)
    with pytest.raises(click.ClickException, match="identity"):
        router.execute_bound_operation(boundary.locator, "stop")
    assert calls == ["describe"]


def test_bound_describe_verifies_execution_binding(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read-only callers receive the same owner verification as mutation callers."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    monkeypatch.setattr(
        router,
        "execute_request",
        lambda profile, request: _response(
            request, boundary, identity={"agent_id": "agent-1"}, generation_id="generation-1"
        ).model_copy(
            update={
                "binding": boundary.binding.model_copy(update={"context_id": "another-context"})
            }
        ),
    )
    with pytest.raises(click.ClickException, match="binding"):
        router.execute_bound_operation(boundary.locator, "describe")


def test_lost_launch_response_never_publishes_or_replays(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An indeterminate birth is not an invitation to create another logical agent."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    transport = Mock(
        return_value=ExecutionResponseV1(
            request_id="request-1",
            outcome="indeterminate",
            admitted=None,
            error_code="transport_timeout",
        )
    )
    publish = Mock(
        side_effect=AssertionError("uncertain launch cannot publish a confirmed locator")
    )
    monkeypatch.setattr(router, "execute_request", transport)
    monkeypatch.setattr(router, "publish_executor_locator", publish)
    with pytest.raises(click.ClickException, match="request=request-1"):
        router.launch_with_executor("worker", {"profile": "reviewer"})
    assert transport.call_count == 1
    publish.assert_not_called()


def test_failed_operator_publication_reports_admitted_identity_without_second_birth(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed operator write leaves the already-launched owner as the recovery target."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    transport = Mock(
        side_effect=lambda profile, request: _response(
            request, boundary, agent_id="agent-1", agent_name="reviewer"
        )
    )
    monkeypatch.setattr(router, "execute_request", transport)
    monkeypatch.setattr(
        router,
        "publish_executor_locator",
        Mock(side_effect=OSError("operator registry unavailable")),
    )
    with collect_output_payloads() as output:
        with pytest.raises(click.ClickException, match="Do not launch again"):
            router.launch_with_executor("worker", {"profile": "reviewer"})
    assert transport.call_count == 1
    assert output[0]["outcome"] == "partial_success"
    assert output[0]["agent_id"] == "agent-1"
    assert "reconcile" in output[0]["recovery"]


def test_describe_consumes_mutation_transport_budget(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner discovery cannot grant a second full transport deadline to the mutation."""

    clock = [0.0]
    requests = []
    monkeypatch.setattr(router, "monotonic", lambda: clock[0], raising=False)
    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Spend twelve seconds in describe without a wall-clock wait."""

        requests.append(request)
        if request.operation == "describe":
            clock[0] = 12.0
        return _response(
            request, boundary, identity={"agent_id": "agent-1"}, generation_id="generation-1"
        )

    monkeypatch.setattr(router, "execute_request", execute)
    router.execute_bound_operation(boundary.locator, "stop")
    assert [request.operation for request in requests] == ["describe", "stop"]
    assert requests[1].deadline_seconds == pytest.approx(18.0)


def test_expired_describe_budget_prevents_mutation_dispatch(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed read does not permit a mutation after the caller's deadline expires."""

    clock = [0.0]
    operations = []
    monkeypatch.setattr(router, "monotonic", lambda: clock[0], raising=False)
    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Finish describe after the original finite budget has expired."""

        operations.append(request.operation)
        clock[0] = 31.0
        return _response(
            request, boundary, identity={"agent_id": "agent-1"}, generation_id="generation-1"
        )

    monkeypatch.setattr(router, "execute_request", execute)
    try:
        result = router.execute_bound_operation(boundary.locator, "stop")
    except click.ClickException:
        pass
    else:
        assert result.outcome == "rejected" and result.admitted is False
    assert operations == ["describe"]


def test_native_refresh_timeout_cannot_exceed_request_budget(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner-side refresh honors the remaining operation deadline over a longer explicit value."""

    _registry(monkeypatch, boundary.record)
    monkeypatch.setattr(managed, "resolve_managed_agent_target", lambda **kwargs: object())
    observed = []

    def refresh(target: object, *, timeout_seconds: float) -> dict[str, object]:
        """Capture the budget handed to the native refresh boundary."""

        observed.append(timeout_seconds)
        return {"method": "none", "outcome": "unsupported"}

    monkeypatch.setattr(managed, "refresh_managed_agent", refresh)
    request = ExecutionRequestV1(
        operation="refresh",
        agent_id="agent-1",
        generation_id="generation-1",
        deadline_seconds=3.0,
        arguments={"timeout_seconds": 10.0},
    )
    application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert len(observed) == 1 and 0 < observed[0] <= 3.0


@pytest.mark.parametrize("operation,read_only", [("state", True), ("stop", False)])
def test_reconstruction_is_read_only_and_explicit_operation_retains_its_scope(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, operation: str, read_only: bool
) -> None:
    """Admission validation cannot repair files, while explicit mutation retains its authority."""

    _registry(monkeypatch, boundary.record)

    def resolve(**kwargs: object) -> object:
        """Observe the reconstruction-only scope at the actual resolver boundary."""

        assert execution_is_read_only()
        return object()

    def act(target: object) -> dict[str, object]:
        """Observe the declared read/mutation scope after reconstruction completes."""

        assert execution_is_read_only() is read_only
        return {"success": True}

    monkeypatch.setattr(managed, "resolve_managed_agent_target", resolve)
    monkeypatch.setattr(
        managed,
        "managed_agent_state_payload" if operation == "state" else "stop_managed_agent",
        act,
    )
    request = ExecutionRequestV1.model_validate(
        {"operation": operation, "agent_id": "agent-1", "generation_id": "generation-1"}
    )
    application.dispatch_operation(request, boundary.binding, boundary.policy)
    assert not execution_is_read_only()


def test_reconciliation_publishes_only_existing_owner_locator(
    boundary: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Recovery performs one owner describe and a lexical operator write without a new birth."""

    monkeypatch.setattr(router, "load_execution_profile", lambda name: boundary.profile)
    operations = []

    def execute(profile: ExecutionProfileV1, request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Allow only read-only recovery of an already admitted identity."""

        operations.append(request.operation)
        return _response(
            request, boundary, identity={"agent_id": "agent-1", "agent_name": "reviewer"}
        )

    monkeypatch.setattr(router, "execute_request", execute)
    root = tmp_path / "operator-registry"
    monkeypatch.setattr(
        router,
        "publish_executor_locator",
        lambda record: publish_executor_locator(record, root=root),
    )
    record = router.reconcile_executor_agent("worker", "agent-1")
    assert operations == ["describe"]
    assert load_executor_locator("agent-1", root=root) == record
    assert not (root / "live_agents").exists()


def test_unconfigured_execution_target_cannot_spawn_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing operator route fails before any privileged helper or runtime setup."""

    monkeypatch.setattr(
        router,
        "load_execution_profile",
        Mock(side_effect=ExecutionProfileError("missing configured profile")),
    )
    transport = Mock(side_effect=AssertionError("unconfigured target must not spawn"))
    monkeypatch.setattr(router, "execute_request", transport)
    with pytest.raises(ExecutionProfileError):
        router.launch_with_executor("unconfigured", {"profile": "reviewer"})
    transport.assert_not_called()


def test_public_http_launch_contract_cannot_supply_execution_authority() -> None:
    """The maintained HTTP body accepts no execution profile or controller grant."""

    payload = {
        "tool": "codex",
        "working_directory": "/owner/project",
        "agent_def_dir": "/owner/project/.houmao/agents",
        "brain_manifest_path": "/owner/runtime/brain.json",
    }
    assert PassiveHeadlessLaunchRequest.model_validate(payload).tool == "codex"
    for field in ("executor", "controller"):
        with pytest.raises(ValidationError) as error:
            PassiveHeadlessLaunchRequest.model_validate({**payload, field: "claimed-authority"})
        assert any(
            item["loc"] == (field,) and item["type"] == "extra_forbidden"
            for item in error.value.errors()
        )
