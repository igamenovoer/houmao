"""Manager Web inspection and timing validation preserve the native surface boundary."""

from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import click
import pytest

from houmao.agents.realm_controller.backends.dsh_web import DshWebSession
from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.manifest import write_session_manifest
from houmao.execution.tmux import TmuxServer
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.srv_ctrl.commands import managed_agent_observation, managed_agents
from tests.unit.agents.realm_controller.test_dsh_web_models import _manifest
from tests.unit.agents.realm_controller.test_dsh_web_observation import _page, _state
from tests.unit.agents.realm_controller.test_gateway_support import _sample_headless_plan
from tests.unit.srv_ctrl.test_managed_agents import _observation_target


@pytest.mark.parametrize("available", [True, False])
def test_manager_native_web_detail_uses_fresh_structured_state_without_terminal_or_headless_fabrication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    available: bool,
) -> None:
    """Native inspection reads the recorded Web owner without probing its supervisor."""

    manifest = tmp_path / "manifest.json"
    write_session_manifest(manifest, _manifest(tmp_path))
    plan = replace(
        _sample_headless_plan(tmp_path), backend="dsh_web", tool="dsh", native_surface_kind="web"
    )
    target = _observation_target(manifest)
    identity = target.identity
    assert identity.transport == "web" and identity.native_surface.kind == "web"
    backend = object.__new__(DshWebSession)
    payload = _state()
    payload["interaction_waits"] = ["question"]
    payload["admission"] = {
        "ready_only": False,
        "if_no_pending": False,
        "always": True,
        "reason": "question",
    }
    monkeypatch.setattr(
        backend,
        "observe_web_state_read_only",
        Mock(return_value=payload)
        if available
        else Mock(side_effect=RuntimeError("private credential error")),
    )
    monkeypatch.setattr(backend, "observe_web_history_read_only", lambda **_: _page(1))
    open_native_adapter = Mock(
        return_value=SimpleNamespace(
            agent_id="owner",
            registry_generation_id="generation",
            execution_binding=None,
            launch_plan=plan,
            execution_scope=nullcontext,
            backend_session=backend,
        )
    )
    monkeypatch.setattr(managed_agent_observation, "resume_runtime_session", open_native_adapter)
    monkeypatch.setattr(
        TmuxServer, "observe_session", Mock(side_effect=AssertionError("Supervisor inaccessible"))
    )
    detail = managed_agents.managed_agent_detail_payload(target)
    assert detail.detail.transport == "web"
    assert detail.summary_state.availability == ("available" if available else "unavailable")
    assert detail.summary_state.turn.phase == ("blocked" if available else "unknown")
    assert detail.detail.state is not None
    assert not detail.detail.state.can_accept_prompt_now
    assert "parsed_surface" not in detail.detail.model_dump()
    assert "canonical_terminal_state_route" not in detail.detail.model_dump()
    assert "private credential" not in detail.model_dump_json()
    assert detail.summary_state.control.source == "web_native"
    if available:
        assert detail.summary_state.control.freshness == "current"
        assert detail.summary_state.control.observed_at_utc is not None
    else:
        assert detail.summary_state.control.freshness == "unknown"
        assert detail.summary_state.control.observed_at_utc is None
    open_native_adapter.assert_called_once_with(session_manifest_path=manifest, read_only=True)


def test_manager_web_gateway_attach_rejects_terminal_timing_before_any_controller_effect() -> None:
    """Terminal-only timing flags cannot reach a Web provider or its supervisor."""

    controller = Mock()
    target = managed_agents.ManagedAgentTarget(
        mode="local",
        agent_ref="owner",
        controller=controller,
        identity=HoumaoManagedAgentIdentity(tracked_agent_id="owner", transport="web", tool="dsh"),
    )
    with pytest.raises(click.ClickException, match="timing.*unsupported.*Web"):
        managed_agents.attach_gateway(
            target,
            tui_tracking_timing_overrides=GatewayTuiTrackingTimingOverridesV1(
                watch_poll_interval_seconds=0.1
            ),
        )
    assert controller.mock_calls == []
