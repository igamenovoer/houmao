"""Manager Web inspection and timing validation preserve the native surface boundary."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import click
import pytest

from houmao.agents.realm_controller.backends.dsh_web import DshWebSession
from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.manifest import write_session_manifest
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.srv_ctrl.commands import managed_agents
from tests.unit.agents.realm_controller.test_dsh_web_models import _manifest
from tests.unit.agents.realm_controller.test_dsh_web_observation import _page, _state
from tests.unit.agents.realm_controller.test_gateway_support import _sample_headless_plan


@pytest.mark.parametrize("available", [True, False])
def test_manager_native_web_detail_uses_fresh_structured_state_without_terminal_or_headless_fabrication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    available: bool,
) -> None:
    """Direct inspection reconnects read-only authority and closes only its API connection."""

    manifest = tmp_path / "manifest.json"
    write_session_manifest(manifest, _manifest(tmp_path))
    plan = replace(
        _sample_headless_plan(tmp_path), backend="dsh_web", tool="dsh", native_surface_kind="web"
    )
    controller = SimpleNamespace(
        launch_plan=plan,
        manifest_path=manifest,
        agent_def_dir=tmp_path / "definitions",
        agent_id="owner",
        agent_identity="web-agent",
        tmux_session_name="supervisor",
        memory_root=None,
        memo_file=None,
        pages_dir=None,
    )
    identity = managed_agents._identity_from_controller(controller)
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
        "observe_web_state",
        Mock(return_value=payload)
        if available
        else Mock(side_effect=RuntimeError("private credential error")),
    )
    monkeypatch.setattr(backend, "observe_web_history", lambda **_: _page(1))
    close = Mock()
    monkeypatch.setattr(backend, "close_control_connection", close)
    monkeypatch.setattr(
        managed_agents,
        "resume_runtime_session",
        Mock(return_value=SimpleNamespace(backend_session=backend)),
    )
    monkeypatch.setattr(managed_agents, "_live_gateway_client_for_controller", lambda _: None)
    monkeypatch.setattr(managed_agents, "_local_gateway_summary", lambda _: None)
    monkeypatch.setattr(
        managed_agents,
        "_refresh_local_tui_state",
        Mock(side_effect=AssertionError("Web is not a terminal")),
    )
    monkeypatch.setattr(
        managed_agents,
        "_local_headless_state_response",
        Mock(side_effect=AssertionError("Web is not headless")),
    )
    target = managed_agents.ManagedAgentTarget(
        mode="local", agent_ref="owner", identity=identity, controller=controller
    )
    detail = managed_agents.managed_agent_detail_payload(target)
    assert detail.detail.transport == "web"
    assert detail.summary_state.availability == ("available" if available else "unavailable")
    assert detail.summary_state.turn.phase == ("blocked" if available else "unknown")
    assert not detail.detail.state.can_accept_prompt_now
    assert "parsed_surface" not in detail.detail.model_dump()
    assert "canonical_terminal_state_route" not in detail.detail.model_dump()
    assert "private credential" not in detail.model_dump_json()
    close.assert_called_once()


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
