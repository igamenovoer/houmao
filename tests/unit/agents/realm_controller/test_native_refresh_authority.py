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
from houmao.agents.realm_controller.errors import GatewayError


def _payload(tmp_path: Path, *, backend: str = "dsh_acp") -> SimpleNamespace:
    """Build only the parsed authority fields consumed by the home reader."""

    native = tmp_path / "selected-native-home"
    native.mkdir()
    return SimpleNamespace(
        backend=backend,
        tool="dsh",
        agent_id="selected",
        tmux_session_name="HOUMAO-selected",
        registry_generation_id="generation",
        registry_launch_authority="runtime",
        runtime=SimpleNamespace(session_id="logical-runtime"),
        tmux=SimpleNamespace(primary_window_id="@7", primary_pane_id="%8"),
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
    monkeypatch.setattr(native_refresh, "tmux_session_exists", lambda **_: True)
    surface = Mock(return_value=SimpleNamespace(pane_dead=False))
    monkeypatch.setattr(native_refresh, "resolve_primary_tmux_surface", surface)

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
    surface.assert_called_once_with(
        session_name="HOUMAO-selected", window_id="@7", pane_id="%8", require_pane_index_zero=True
    )


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
    assert home.backend == "dsh_acp"
    assert controller.backend_session.native_invocation_active is False
    controller.backend_session.send_prompt.assert_not_called()
    controller.backend_session.observe_web_state.assert_not_called()
    project.assert_not_called()


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


@pytest.mark.parametrize("selected", [None, "/unrelated/home", "relative-home"])
def test_unknown_thin_joined_home_is_not_a_fallback_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: str | None
) -> None:
    """A joined envelope's disposable tool-home does not prove native selection."""

    payload = _payload(tmp_path, backend="local_interactive")
    payload.tool = "claude"
    payload.launch_plan.home_selector.env_var = "CLAUDE_CONFIG_DIR"
    payload.agent_launch_authority.session_origin = "joined_tmux"
    payload.agent_launch_authority.posture_kind = "unavailable"
    manifest, environment, _surface = _install(tmp_path, monkeypatch, payload)
    environment["CLAUDE_CONFIG_DIR"] = selected
    with pytest.raises(GatewayError, match="Joined native home"):
        native_refresh.inspect_native_home_from_manifest(manifest)


def test_known_thin_joined_native_home_uses_matching_selector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching native selector makes an otherwise thin join inspectable."""

    payload = _payload(tmp_path, backend="local_interactive")
    payload.tool = "claude"
    payload.launch_plan.home_selector.env_var = "CLAUDE_CONFIG_DIR"
    payload.agent_launch_authority.session_origin = "joined_tmux"
    payload.agent_launch_authority.posture_kind = "unavailable"
    manifest, environment, _surface = _install(tmp_path, monkeypatch, payload)
    environment["CLAUDE_CONFIG_DIR"] = payload.launch_plan.home_selector.home_path
    assert (
        native_refresh.inspect_native_home_from_manifest(manifest).home_env_var
        == "CLAUDE_CONFIG_DIR"
    )


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


@pytest.mark.parametrize("condition", ["missing", "stale_handles", "dead_primary"])
def test_missing_stale_or_stopped_primary_cannot_authorize_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, condition: str
) -> None:
    """A surviving unrelated pane or reused session name is insufficient authority."""

    payload = _payload(tmp_path)
    manifest, _environment, surface = _install(tmp_path, monkeypatch, payload)
    if condition == "missing":
        monkeypatch.setattr(native_refresh, "tmux_session_exists", lambda **_: False)
    elif condition == "stale_handles":
        surface.side_effect = TmuxCommandError("Captured primary no longer exists")
    else:
        surface.return_value = SimpleNamespace(pane_dead=True)
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
