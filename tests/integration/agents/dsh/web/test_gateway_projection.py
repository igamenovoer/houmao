"""Project actual controlled Web state through the shared gateway observation contract."""

from collections.abc import Callable
import json

from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataWebV1,
    GatewayWebExecutionIdentityV1,
)
from houmao.agents.realm_controller.web_observation import WebObservation
from tests.integration.agents.dsh.web.conftest import NativeWebGates, NativeWebHost
from tests.integration.agents.dsh.web.test_native_control import (
    deadline,
    native_prompt,
    wait_terminal,
)


def _observation(host: NativeWebHost) -> WebObservation:
    """Bind only the actual created native identity and read-only native operations."""

    return WebObservation(
        metadata=GatewayAttachBackendMetadataWebV1(
            origin=host.origin,
            browser_url=host.origin,
            identity=GatewayWebExecutionIdentityV1.model_validate(host.identity),
        ),
        state=lambda: host.client.state(host.identity),
        history=lambda **kwargs: host.client.history(host.identity, **kwargs),
        source="gateway",
    )


def test_actual_native_web_projection_tracks_shared_work_inbox_and_terminal_identity(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
) -> None:
    """Real native events produce Web state without parsing a pane or browser draft."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    observer = _observation(host)
    ready = observer.refresh()
    assert ready.availability == "available" and ready.can_accept_prompt_now
    assert ready.control_available and ready.host_process_alive and ready.native_agent_live
    native_web_gates.hold("step", "projected-program")
    host.client.prompt(
        host.identity, "projected-program", operation_id="projected", deadline_epoch_ms=deadline()
    )
    try:
        native_web_gates.wait("step")
        active = observer.refresh()
        assert active.availability == "available"
        assert active.active_turn is not None and not active.can_accept_prompt_now
        native_prompt(host, "projected-human-next")
        pending = observer.refresh()
        assert len(pending.pending_inbox) == 1
        assert pending.pending_inbox[0].operation_id is None
        assert not pending.can_accept_prompt_now
        host.client.interrupt(
            host.identity,
            turn_start_seq=active.active_turn.start_sequence,
            operation_id="projected",
        )
    finally:
        native_web_gates.release("step")
    receipt = wait_terminal(host, "projected")
    assert receipt["status"] == "terminal"
    settled = observer.refresh()
    assert settled.availability == "available"
    history = observer.history()
    assert history.reconciled
    assert {entry.event for entry in history.entries} >= {
        "created",
        "inbox/inserted",
        "inbox/claimed",
        "turn/start",
        "turn/end",
    }
    assert all(
        entry.identity.native_session_id == host.identity["native_session_id"]
        for entry in history.entries
    )
    public = settled.model_dump_json() + history.model_dump_json()
    assert "projected-program" not in public and "projected-human-next" not in public
    assert "editing_input" not in public and "parsed_surface" not in public
    assert "launch_token" not in public


def test_actual_native_api_revocation_discards_prior_ready_projection(
    native_web_host: NativeWebHost,
) -> None:
    """Revoking only the API Peer closes program readiness without fabricating host death."""

    observer = _observation(native_web_host)
    assert observer.refresh().can_accept_prompt_now
    native_web_host.client.close()
    state = observer.refresh()
    assert state.availability == "unavailable" and not state.can_accept_prompt_now
    assert not state.control_available and state.native_agent_live is None
    assert not state.admission.always
    assert json.loads(state.model_dump_json())["identity"] == native_web_host.identity
