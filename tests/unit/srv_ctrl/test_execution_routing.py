"""Executor-managed targets retain owner routing without caller-local fallbacks."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import click
from pydantic import ValidationError
import pytest

from houmao.execution.locators import ExecutorAgentLocatorV1
from houmao.execution.models import ControllerScopeV1, ExecutionBindingV1, ExecutionResponseV1
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.srv_ctrl.commands import managed_agents as helpers


def _locator() -> ExecutorAgentLocatorV1:
    """Use target-only paths and a saved owner binding for one logical agent."""

    return ExecutorAgentLocatorV1(
        agent_id="agent-1",
        agent_name="reviewer",
        tool="codex",
        mode="headless",
        backend="codex_headless",
        profile_name="worker",
        binding=ExecutionBindingV1(
            context_id="owner-context",
            host_id="foreign-host",
            account="alice",
            uid=1001,
            gid=1001,
            registry_root="/owner-only/registry",
            runtime_root="/owner-only/runtime",
            project_root="/owner-only/project",
            profile_name="worker",
            transport="sudo",
            controller=ControllerScopeV1(
                controller_id="operator",
                authority="sudo_policy",
                operations=(
                    "describe",
                    "state",
                    "home",
                    "refresh_check",
                    "refresh",
                    "prompt",
                    "interrupt",
                    "stop",
                    "relaunch",
                ),
            ),
            route_fingerprint="f" * 64,
            tmux_socket="/owner-only/tmux.sock",
        ),
    )


def _identity() -> HoumaoManagedAgentIdentity:
    """Return owner-local identity data without pretending paths are caller-local."""

    return HoumaoManagedAgentIdentity(
        tracked_agent_id="agent-1",
        agent_id="agent-1",
        agent_name="reviewer",
        transport="headless",
        mode="headless",
        backend="codex_headless",
        tool="codex",
        lifecycle_state="active",
        management_kind="local_lifecycle",
        lifecycle_owner="local",
        manifest_path="/owner-only/runtime/session/manifest.json",
        session_root="/owner-only/runtime/session",
    )


def _target() -> helpers.ManagedAgentTarget:
    """Construct a selected executor target without creating local runtime state."""

    return helpers.ManagedAgentTarget(
        mode="executor", agent_ref="agent-1", identity=_identity(), executor_locator=_locator()
    )


def _completed(result: dict[str, object]) -> ExecutionResponseV1:
    """Return a confirmed owner result with a matching execution binding."""

    return ExecutionResponseV1.model_validate(
        {
            "request_id": "request-1",
            "outcome": "completed",
            "admitted": True,
            "binding": _locator().binding,
            "result": result,
        }
    )


def _forbid_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail immediately if delegated routing touches a caller-local control path."""

    def forbidden(*args: object, **kwargs: object) -> None:
        """Mark caller-local reconstruction/probing/fallback as a test failure."""

        raise AssertionError("delegated target must not use caller-local authority")

    for name in (
        "_probe_local_tmux_authority_for_record",
        "_resume_controller_from_record",
        "_resolve_local_managed_agent_record_with_miss_context",
        "require_supported_houmao_pair",
        "_resolve_local_relaunch_record_with_miss_context",
    ):
        monkeypatch.setattr(helpers, name, forbidden)


@pytest.mark.parametrize(
    "resolver",
    [helpers.resolve_managed_agent_target, helpers.resolve_relaunch_managed_agent_target],
)
def test_exact_executor_target_resolves_before_local_control(
    monkeypatch: pytest.MonkeyPatch, resolver: object
) -> None:
    """Both active controls and stopped relaunch retain the configured owner route."""

    _forbid_local(monkeypatch)
    monkeypatch.setattr(helpers, "resolve_executor_locator", lambda **kwargs: _locator())
    monkeypatch.setattr(helpers, "load_managed_agent_record_by_agent_id", lambda agent_id: None)
    transport = Mock(return_value=_completed({"identity": _identity().model_dump(mode="json")}))
    monkeypatch.setattr(helpers, "_execute_executor_operation", transport)
    target = resolver(agent_id="agent-1", agent_name=None, port=None)
    assert target.mode == "executor"
    assert target.controller is None and target.client is None
    assert target.identity.execution_context == _locator().binding
    assert target.identity.lifecycle_owner == "executor"
    assert transport.call_args.args[1] == "describe"


def test_explicit_port_skips_execution_locator_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit pair authority retains its existing registry bypass semantics."""

    monkeypatch.setattr(
        helpers,
        "resolve_executor_locator",
        Mock(side_effect=AssertionError("registry bypass required")),
    )
    client = Mock()
    monkeypatch.setattr(helpers, "require_supported_houmao_pair", lambda **kwargs: client)
    monkeypatch.setattr(
        helpers, "resolve_managed_agent_identity", lambda *args, **kwargs: _identity()
    )
    target = helpers.resolve_managed_agent_target(agent_id="agent-1", agent_name=None, port=9999)
    assert target.mode == "server" and target.client is client


def test_friendly_name_conflict_is_reported_before_owner_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A local namesake cannot shadow or silently redirect a delegated target."""

    monkeypatch.setattr(helpers, "resolve_executor_locator", lambda **kwargs: _locator())
    monkeypatch.setattr(
        helpers,
        "resolve_managed_agent_records_by_name",
        lambda name: (SimpleNamespace(agent_id="other-agent", execution_binding=None),),
    )
    transport = Mock(side_effect=AssertionError("ambiguity must precede dispatch"))
    monkeypatch.setattr(helpers, "_execute_executor_operation", transport)
    with pytest.raises(click.ClickException, match="ambiguous or has conflicting"):
        helpers.resolve_managed_agent_target(agent_id=None, agent_name="reviewer", port=None)
    transport.assert_not_called()


def test_unreachable_saved_owner_does_not_fall_through_to_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One unreachable describe leaves the saved owner unresolved for every action."""

    _forbid_local(monkeypatch)
    monkeypatch.setattr(helpers, "resolve_executor_locator", lambda **kwargs: _locator())
    monkeypatch.setattr(helpers, "resolve_managed_agent_records_by_name", lambda name: ())
    transport = Mock(
        return_value=ExecutionResponseV1(
            request_id="request-unavailable",
            outcome="indeterminate",
            admitted=None,
            error_code="transport_timeout",
        )
    )
    monkeypatch.setattr(helpers, "_execute_executor_operation", transport)

    with pytest.raises(click.ClickException, match="transport_timeout.*request-unavailable"):
        helpers.resolve_managed_agent_target(agent_id=None, agent_name="reviewer", port=None)

    transport.assert_called_once()
    assert transport.call_args.args[:2] == (_locator(), "describe")


def test_equivalent_owner_record_deduplicates_without_local_manifest_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sharing one account/registry does not accidentally choose local reconstruction."""

    _forbid_local(monkeypatch)
    monkeypatch.setattr(helpers, "resolve_executor_locator", lambda **kwargs: _locator())
    monkeypatch.setattr(
        helpers,
        "load_managed_agent_record_by_agent_id",
        lambda agent_id: SimpleNamespace(agent_id="agent-1", execution_binding=_locator().binding),
    )
    monkeypatch.setattr(
        helpers,
        "_execute_executor_operation",
        lambda *args: _completed({"identity": _identity().model_dump(mode="json")}),
    )
    assert (
        helpers.resolve_managed_agent_target(agent_id="agent-1", agent_name=None, port=None).mode
        == "executor"
    )


def test_owner_dispatch_scope_prevents_same_user_recursive_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An admitted owner can resolve its local record even when an operator locator exists."""

    def lookup_forbidden(**kwargs: object) -> None:
        """Require owner-local dispatch to bypass operator locator lookup entirely."""

        raise AssertionError("owner must not delegate recursively")

    monkeypatch.setattr(helpers, "resolve_executor_locator", lookup_forbidden)
    record = SimpleNamespace(identity=SimpleNamespace(backend="codex_headless"))
    monkeypatch.setattr(
        helpers,
        "_resolve_local_managed_agent_record_with_miss_context",
        lambda **kwargs: (record, None),
    )
    monkeypatch.setattr(helpers, "_is_local_tmux_backed_active_record", lambda record: False)
    monkeypatch.setattr(helpers, "_resume_controller_from_record", lambda record: SimpleNamespace())
    monkeypatch.setattr(helpers, "_identity_from_controller", lambda controller: _identity())
    with helpers.owner_local_target_scope():
        assert (
            helpers.resolve_managed_agent_target(
                agent_id="agent-1", agent_name=None, port=None
            ).mode
            == "local"
        )
    with pytest.raises(AssertionError, match="recursively"):
        helpers.resolve_managed_agent_target(agent_id="agent-1", agent_name=None, port=None)


@pytest.mark.parametrize(
    "outcome,admitted,code",
    [
        ("rejected", False, "transport_authorization_failed"),
        ("rejected", False, "generation_conflict"),
        ("indeterminate", None, "transport_timeout"),
    ],
)
def test_failed_owner_control_never_replays_or_falls_back(
    monkeypatch: pytest.MonkeyPatch, outcome: str, admitted: bool | None, code: str
) -> None:
    """Retain authorization/conflict/uncertainty rather than targeting another context."""

    _forbid_local(monkeypatch)
    response = ExecutionResponseV1.model_validate(
        {"request_id": "request-1", "outcome": outcome, "admitted": admitted, "error_code": code}
    )
    transport = Mock(return_value=response)
    monkeypatch.setattr(helpers, "_execute_executor_operation", transport)
    with pytest.raises(click.ClickException, match=code):
        helpers.stop_managed_agent(_target())
    assert transport.call_count == 1


def test_home_and_refresh_are_owner_qualified_without_local_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context qualification preserves native freshness semantics and no-restart behavior."""

    monkeypatch.setattr(
        helpers,
        "inspect_native_home",
        Mock(side_effect=AssertionError("caller home must not be inspected")),
    )
    home = {
        "agent_id": "agent-1",
        "backend": "codex_headless",
        "tool": "codex",
        "home_dir": "/owner-only/native",
    }
    observation = {"home": home, "resources": [], "freshness": "unknown"}
    seen = []

    def execute(locator: object, operation: str, arguments: object) -> ExecutionResponseV1:
        """Supply owner-native results without mutating any local files."""

        seen.append(operation)
        if operation == "home":
            return _completed(home)
        if operation == "refresh_check":
            return _completed(observation)
        return _completed({"method": "none", "outcome": "unsupported", "observation": observation})

    monkeypatch.setattr(helpers, "_execute_executor_operation", execute)
    assert (
        helpers.managed_agent_native_home(_target()).identity["execution_context_id"]
        == "owner-context"
    )
    assert (
        helpers.managed_agent_common_plugin_state(_target()).home.identity["execution_owner"]
        == "alice"
    )
    result = helpers.refresh_managed_agent(_target())
    assert result.outcome == "unsupported" and result.method == "none"
    assert result.observation.home.identity["execution_context_id"] == "owner-context"
    assert seen == ["home", "refresh_check", "refresh"]


def test_stop_and_relaunch_return_owner_qualified_cleanup_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserved manifest paths remain associated with the owning context."""

    monkeypatch.setattr(
        helpers,
        "_execute_executor_operation",
        lambda *args: _completed(
            {
                "success": True,
                "tracked_agent_id": "agent-1",
                "detail": "owner operation complete",
                "manifest_path": "/owner-only/manifest.json",
                "session_root": "/owner-only/session",
            }
        ),
    )
    for operation in (helpers.stop_managed_agent, helpers.relaunch_managed_agent):
        result = operation(_target())
        assert result.execution_context == _locator().binding
        assert result.manifest_path == "/owner-only/manifest.json"
        assert result.model_dump(mode="json")["execution_context"]["context_id"] == "owner-context"


def test_lifecycle_inclusive_listing_retains_unavailable_owner_as_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No local session or failed owner connection can prove an agent has stopped."""

    monkeypatch.setattr(helpers, "_list_registry_identities", lambda **kwargs: ())
    monkeypatch.setattr(helpers, "list_executor_locators", lambda: (_locator(),))
    monkeypatch.setattr(helpers, "load_managed_agent_record_by_agent_id", lambda agent_id: None)
    monkeypatch.setattr(helpers, "list_external_managed_agent_records", lambda: ())
    monkeypatch.setattr(helpers, "_optional_pair_client", lambda **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "_execute_executor_operation",
        lambda *args: ExecutionResponseV1(
            request_id="request-1",
            outcome="indeterminate",
            admitted=None,
            error_code="transport_timeout",
        ),
    )
    assert helpers.list_managed_agents(port=None).agents == []
    rows = helpers.list_managed_agents(port=None, lifecycle_state="all").agents
    assert len(rows) == 1
    assert rows[0].agent_id == "agent-1" and rows[0].lifecycle_state is None
    assert rows[0].transport == "unknown" and rows[0].execution_status == "unavailable"


def test_unsupported_finite_operation_has_no_local_controller_fallback() -> None:
    """Unimplemented terminal/gateway operations fail before local authority is requested."""

    with pytest.raises(
        click.ClickException, match="unsupported through the finite execution transport"
    ):
        helpers._require_live_local_controller(
            _target(), operation="attach an interactive terminal"
        )


def test_owner_gateway_loopback_endpoint_is_context_qualified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A returned owner-local listener must not masquerade as the caller's loopback port."""

    status = {
        "attach_identity": "agent-1",
        "backend": "codex_headless",
        "tmux_session_name": "owner-session",
        "gateway_health": "healthy",
        "managed_agent_connectivity": "connected",
        "managed_agent_recovery": "idle",
        "request_admission": "open",
        "terminal_surface_eligibility": "ready",
        "active_execution": "idle",
        "queue_depth": 0,
        "gateway_host": "127.0.0.1",
        "gateway_port": 4567,
        "managed_agent_instance_epoch": 1,
    }
    monkeypatch.setattr(helpers, "_execute_executor_operation", lambda *args: _completed(status))
    result = helpers.gateway_status(_target()).model_dump(mode="json")
    assert result["gateway_host"] == "127.0.0.1"
    assert result["execution_context"]["host_id"] == "foreign-host"


def test_native_home_of_another_agent_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid native-home payload still needs the requested logical agent identity."""

    monkeypatch.setattr(
        helpers,
        "_execute_executor_operation",
        lambda *args: _completed(
            {
                "agent_id": "other-agent",
                "backend": "codex_headless",
                "tool": "codex",
                "home_dir": "/other/native",
            }
        ),
    )
    with pytest.raises(click.ClickException, match="different agent's native home"):
        helpers.managed_agent_native_home(_target())


def test_unknown_transport_cannot_claim_a_live_or_local_agent() -> None:
    """Only explicitly unverified executor rows can have unknown native transport."""

    with pytest.raises(ValidationError, match="unknown transport"):
        HoumaoManagedAgentIdentity(
            tracked_agent_id="agent-1", agent_id="agent-1", transport="unknown", tool="unknown"
        )


def test_verified_executor_appears_in_active_listing_without_local_presence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner-observed active state is sufficient when this host has no tmux record."""

    monkeypatch.setattr(helpers, "_list_registry_identities", lambda **kwargs: ())
    monkeypatch.setattr(helpers, "list_executor_locators", lambda: (_locator(),))
    monkeypatch.setattr(helpers, "load_managed_agent_record_by_agent_id", lambda agent_id: None)
    monkeypatch.setattr(helpers, "list_external_managed_agent_records", lambda: ())
    monkeypatch.setattr(helpers, "_optional_pair_client", lambda **kwargs: None)
    monkeypatch.setattr(
        helpers,
        "_execute_executor_operation",
        lambda *args: _completed({"identity": _identity().model_dump(mode="json")}),
    )
    rows = helpers.list_managed_agents(port=None).agents
    assert len(rows) == 1 and rows[0].agent_id == "agent-1"
    assert rows[0].execution_status == "available"
    assert rows[0].management_kind == "executor_managed"
