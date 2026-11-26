"""Verify read-only native-home authority without native workers or real tmux."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller import native_refresh
from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError
from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.errors import GatewayError, RetiredJoinedSessionError
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.managed_terminal import PrimaryTmuxObservation
from houmao.agents.realm_controller.models import BackendKind
from houmao.agents.realm_controller.run_modes import mode_for_backend
from houmao.execution.tmux import current_tmux_socket_path, tmux_server_scope


def _payload(tmp_path: Path, *, backend: BackendKind = "dsh_headless") -> SimpleNamespace:
    """Build only the parsed authority fields consumed by the home reader."""

    native = tmp_path / "selected-native-home"
    native.mkdir()
    return SimpleNamespace(
        backend=backend,
        mode=mode_for_backend(backend),
        tool="dsh",
        agent_id="selected",
        tmux_session_name="HOUMAO-selected",
        registry_generation_id="generation",
        registry_launch_authority="runtime",
        runtime=SimpleNamespace(session_id="logical-runtime", execution_binding=None),
        tmux=SessionManifestTmuxSectionV1(
            socket_path=str(tmp_path / "owner.sock"),
            session_name="HOUMAO-selected",
            primary_window_id="@7",
            primary_pane_id="%8",
        ),
        agent_launch_authority=SimpleNamespace(
            primary_window_id="@7",
            primary_pane_id="%8",
            session_origin=None,
            posture_kind="runtime_launch_plan",
        ),
        launch_plan=SimpleNamespace(
            home_selector=SimpleNamespace(env_var="DSH_HOME", home_path=str(native))
        ),
        backend_state={
            "web_identity": {
                "protocol_version": 1,
                "agent_id": "selected",
                "runtime_session_id": "logical-runtime",
                "generation": "generation",
                "host_incarnation": "host",
                "native_session_id": "native",
                "agent_incarnation": "agent",
            }
        }
        if backend == "dsh_web"
        else {},
    )


def _install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: SimpleNamespace
) -> tuple[Path, dict[str, str | None], Mock]:
    """Replace physical reads while preserving exact persisted tmux bindings."""

    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    environment: dict[str, str | None] = {
        AGENT_MANIFEST_PATH_ENV_VAR: str(manifest),
        AGENT_ID_ENV_VAR: "selected",
        payload.launch_plan.home_selector.env_var: None,
    }
    monkeypatch.setattr(
        native_refresh, "load_session_manifest", lambda _: SimpleNamespace(payload={})
    )
    monkeypatch.setattr(
        native_refresh, "parse_session_manifest_payload", lambda *_args, **_kwargs: payload
    )
    surface = Mock(return_value=PrimaryTmuxObservation("valid", session_exists=True))
    monkeypatch.setattr(native_refresh, "observe_primary_tmux", surface)

    def read(*, session_name: str, variable_name: str) -> str | None:
        """Permit single explicit authority selectors, never an environment dump."""

        assert session_name == payload.tmux_session_name
        assert variable_name in environment
        return environment[variable_name]

    monkeypatch.setattr(native_refresh, "read_tmux_session_environment_value", read)
    return manifest, environment, surface


def _controller(manifest: Path, payload: SimpleNamespace) -> SimpleNamespace:
    """Describe an existing runtime without exposing any worker-start operation."""

    identity = payload.backend_state.get("web_identity")
    backend = SimpleNamespace(
        state=SimpleNamespace(web_identity=identity),
        native_invocation_active=False,
        observe_web_state=Mock(return_value={"available": True, "identity": identity}),
        send_prompt=Mock(side_effect=AssertionError("No worker startup")),
    )
    return SimpleNamespace(
        manifest_path=manifest,
        backend_session=backend,
        agent_id=payload.agent_id,
        registry_generation_id=payload.registry_generation_id,
        tmux_session_name=payload.tmux_session_name,
        launch_plan=SimpleNamespace(
            backend=payload.backend, home_path=Path(payload.launch_plan.home_selector.home_path)
        ),
    )


def test_native_home_differs_from_caller_and_uses_exact_primary_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ambient HOME cannot replace the selected native home or captured pane."""

    payload = _payload(tmp_path)
    manifest, _environment, surface = _install(tmp_path, monkeypatch, payload)
    monkeypatch.setenv("HOME", str(tmp_path / "caller-home"))
    home = native_refresh.inspect_native_home_from_manifest(manifest)
    assert home.home_dir == payload.launch_plan.home_selector.home_path
    assert home.home_env_var == "DSH_HOME"
    surface.assert_called_once_with(payload.tmux)


def test_between_worker_dsh_home_stays_inspectable_without_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live headless shell envelope requires no currently running native worker."""

    payload = _payload(tmp_path)
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    controller = _controller(manifest, payload)
    project = Mock(side_effect=AssertionError("No home materialization"))
    monkeypatch.setattr("houmao.agents.dsh_configuration.prepare_dsh_home", project)
    home = native_refresh.inspect_native_home(controller)
    assert home.backend == "dsh_headless"
    assert controller.backend_session.native_invocation_active is False
    controller.backend_session.send_prompt.assert_not_called()
    controller.backend_session.observe_web_state.assert_not_called()
    project.assert_not_called()


def test_dsh_service_refresh_requires_explicit_relaunch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project startup and session-binding evidence without changing the native incarnation."""

    payload = _payload(tmp_path, backend="dsh_acp")
    payload.backend_state = {
        "service_incarnation": "native-body",
        "native_session_id": "native-conversation",
        "generation_id": "generation",
        "runtime_session_id": "logical-runtime",
        "socket_path": "/private/socket",
    }
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    controller = _controller(manifest, payload)
    controller.launch_plan.metadata = {"dsh": {"detected_tool_version": "0.2.2-rc.3"}}
    controller.observe_managed_service = Mock(
        return_value=ManagedControlObservationV1(
            source="service_native",
            freshness="current",
            owner_available=True,
            connection_ready=True,
            can_accept_prompt_now=True,
            native_session_id="native-conversation",
            service_incarnation="native-body",
        )
    )
    observation = native_refresh.observe_common_plugins(controller)
    assert observation.home.identity["service_incarnation"] == "native-body"
    assert "/private/socket" not in observation.model_dump_json()
    assert [(item.kind, item.component, item.boundary) for item in observation.resources] == [
        ("skills", "provider_start", "next_load"),
        ("mcp", "session_binding", "next_load"),
    ]
    planned = native_refresh.plan_native_refresh(observation)
    assert planned is not None and planned.outcome == "restart_required"
    controller.backend_session.send_prompt.assert_not_called()


def test_native_home_leaves_private_material_unread_and_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home inspection reads authority metadata without opening home contents."""

    payload = _payload(tmp_path)
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    home_path = Path(payload.launch_plan.home_selector.home_path)
    secret = home_path / "private-config"
    secret.write_bytes(b"synthetic-private-marker")
    original = Path.open

    def guarded(path: Path, *args: Any, **kwargs: Any):
        """Fail if inspection attempts either a home read or home write."""

        assert not path.is_relative_to(home_path), "Home contents must remain unread"
        return original(path, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", guarded)
        descriptor = native_refresh.inspect_native_home_from_manifest(manifest)
    assert secret.read_bytes() == b"synthetic-private-marker"
    assert "synthetic-private-marker" not in descriptor.model_dump_json()
    assert manifest.read_text() == "{}"


def test_retired_adoption_refuses_native_home_before_terminal_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saved adoption cannot select a native home or start an observation."""

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"schema_version":6,"agent_launch_authority":{"session_origin":"joined_tmux"}}',
        encoding="utf-8",
    )
    observe = Mock(side_effect=AssertionError("Retired home inspection must not observe tmux"))
    monkeypatch.setattr(native_refresh, "observe_primary_tmux", observe)

    with pytest.raises(RetiredJoinedSessionError):
        native_refresh.inspect_native_home_from_manifest(manifest)
    observe.assert_not_called()


@pytest.mark.parametrize("field", ["registry_generation_id", "runtime.session_id"])
def test_missing_active_identity_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Session existence alone cannot invent generation or logical runtime identity."""

    payload = _payload(tmp_path)
    if field == "runtime.session_id":
        payload.runtime.session_id = None
    else:
        payload.registry_generation_id = None
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home_from_manifest(manifest)


@pytest.mark.parametrize("condition", ["missing", "stale_handles", "dead_primary", "unavailable"])
def test_missing_stale_or_stopped_primary_cannot_authorize_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, condition: str
) -> None:
    """A surviving unrelated pane or reused session name is insufficient authority."""

    payload = _payload(tmp_path)
    manifest, _environment, surface = _install(tmp_path, monkeypatch, payload)
    if condition == "missing":
        surface.return_value = PrimaryTmuxObservation("missing_session", session_exists=False)
    elif condition == "stale_handles":
        surface.return_value = PrimaryTmuxObservation("stale_handles", session_exists=True)
    elif condition == "dead_primary":
        surface.return_value = PrimaryTmuxObservation("dead_pane", session_exists=True)
    else:
        surface.side_effect = TmuxCommandError("Selected socket is unavailable")
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home_from_manifest(manifest)


@pytest.mark.parametrize("value", [None, "relative-manifest", "/another/manifest.json"])
def test_reused_session_with_other_manifest_binding_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    """The same tmux name cannot transfer authority to another persisted runtime."""

    payload = _payload(tmp_path)
    manifest, environment, _surface = _install(tmp_path, monkeypatch, payload)
    environment[AGENT_MANIFEST_PATH_ENV_VAR] = value
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home_from_manifest(manifest)


@pytest.mark.parametrize("value", [None, "other-agent"])
def test_reused_session_with_other_agent_binding_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    """A manifest path cannot override a mismatched live agent binding."""

    payload = _payload(tmp_path)
    manifest, environment, _surface = _install(tmp_path, monkeypatch, payload)
    environment[AGENT_ID_ENV_VAR] = value
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home_from_manifest(manifest)


@pytest.mark.parametrize("home", ["relative", "~/.dsh", ""])
def test_nonabsolute_native_home_is_not_resolved_from_ambient_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, home: str
) -> None:
    """An unknown selector remains unavailable rather than expanding caller state."""

    payload = _payload(tmp_path)
    payload.launch_plan.home_selector.home_path = home
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home_from_manifest(manifest)


def test_external_launch_authority_cannot_inspect_local_native_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Communication-only external authority cannot become local lifecycle authority."""

    payload = _payload(tmp_path)
    payload.registry_launch_authority = "external"
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home_from_manifest(manifest)


@pytest.mark.parametrize("field", ["host_incarnation", "native_session_id", "agent_incarnation"])
def test_incomplete_web_identity_cannot_be_published_as_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Web home authority retains every captured live execution dimension."""

    payload = _payload(tmp_path, backend="dsh_web")
    del payload.backend_state["web_identity"][field]
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home_from_manifest(manifest)


def test_home_identity_excludes_protocol_and_arbitrary_backend_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only execution identity strings may leave private backend state."""

    payload = _payload(tmp_path, backend="dsh_web")
    payload.backend_state["web_identity"]["credential"] = "synthetic-private-marker"
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    home = native_refresh.inspect_native_home_from_manifest(manifest)
    assert "credential" not in home.identity and "protocol_version" not in home.identity
    assert "synthetic-private-marker" not in home.model_dump_json()


def test_stale_controller_tmux_name_cannot_claim_current_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The controller and manifest must address the same captured envelope."""

    payload = _payload(tmp_path)
    manifest, _environment, _surface = _install(tmp_path, monkeypatch, payload)
    controller = _controller(manifest, payload)
    controller.tmux_session_name = "HOUMAO-replacement"
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home(controller)


def test_read_only_home_inspection_restores_saved_socket_before_probing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inspection cannot borrow an unrelated current server's same-named session."""

    payload = _payload(tmp_path)
    payload.tmux = payload.tmux.model_copy(update={"socket_path": "/owner/recorded.sock"})
    manifest, _environment, surface = _install(tmp_path, monkeypatch, payload)
    probes: list[str | None] = []

    def observe(*_args: object, **_kwargs: object) -> PrimaryTmuxObservation:
        """Capture authority before the first native liveness probe."""

        probes.append(current_tmux_socket_path())
        return PrimaryTmuxObservation("valid", session_exists=True)

    surface.side_effect = observe
    with tmux_server_scope("/operator/enclosing.sock"):
        result = native_refresh.inspect_native_home_from_manifest(manifest)
        assert current_tmux_socket_path() == "/operator/enclosing.sock"
    assert result.agent_id == "selected"
    assert probes == ["/owner/recorded.sock"]


def test_read_only_home_rejects_missing_saved_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing socket never borrows tmux authority from an enclosing server."""

    payload = _payload(tmp_path)
    payload.tmux = payload.tmux.model_copy(update={"socket_path": None})
    manifest, _environment, surface = _install(tmp_path, monkeypatch, payload)

    with tmux_server_scope("/operator/enclosing.sock"):
        with pytest.raises(GatewayError, match="Primary native runtime authority is unavailable"):
            native_refresh.inspect_native_home_from_manifest(manifest)

    surface.assert_not_called()
