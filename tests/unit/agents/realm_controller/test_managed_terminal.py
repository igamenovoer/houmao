"""Qualify managed primary selection, restore, and compare-and-repair."""

from dataclasses import replace
import json
from pathlib import Path
from typing import Any, cast

import pytest

from houmao.agents.realm_controller import gateway_service, managed_terminal, runtime
from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.errors import GatewayError, SessionManifestError
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataHeadlessV1,
    GatewayAttachContractV1,
)
from houmao.agents.realm_controller.managed_terminal import (
    PrimaryTmuxObservation,
    observe_primary_tmux,
    select_primary_tmux_surface,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    load_session_manifest,
    repair_session_tmux_binding,
    update_session_manifest,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    BackendKind,
    InteractiveSession,
    LaunchPlan,
    RoleInjectionPlan,
)
from houmao.execution.context import observed_local_binding, persisted_execution_scope
from houmao.execution.tmux import TmuxPaneRecord, current_tmux_socket_path, tmux_server_scope


def _saved_binding(tmp_path: Path) -> SessionManifestTmuxSectionV1:
    """Return an owner-local binding for a saved primary pane."""

    return SessionManifestTmuxSectionV1(
        socket_path=str(tmp_path / "owner.sock"),
        session_name="HOUMAO-agent",
        primary_window_name="adopted",
        primary_window_id="@1",
        primary_pane_id="%7",
    )


def _pane(**updates: Any) -> TmuxPaneRecord:
    """Model a checked tmux record in the bound session."""

    return replace(
        TmuxPaneRecord("%7", "HOUMAO-agent", "@1", "0", "adopted", "1", False), **updates
    )


def _manifest(
    tmp_path: Path,
    binding: SessionManifestTmuxSectionV1,
    *,
    bind_execution: bool = True,
    backend: BackendKind = "local_interactive",
) -> tuple[Path, dict[str, Any]]:
    """Write a minimal current managed manifest on the supplied owner binding."""

    execution_binding = (
        observed_local_binding(
            working_directory=tmp_path,
            runtime_root=tmp_path / "runtime",
            registry_root=tmp_path / "registry",
            tmux_socket=binding.socket_path,
        )
        if bind_execution
        else None
    )
    plan = LaunchPlan(
        backend=backend,
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "native-home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions", role_name="reviewer", prompt=""
        ),
        metadata={"tmux_socket_path": str(tmp_path / "wrong.sock")},
        execution_binding=execution_binding,
    )
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="reviewer",
            brain_manifest_path=tmp_path / "brain.yaml",
            backend_state={
                "tmux_session_name": "different",
                "tmux_window_name": "other",
                "tmux_window_id": "@99",
                "tmux_pane_id": "%99",
                "turn_index": 3,
            },
            agent_name="HOUMAO-agent",
            agent_id="agent-a",
            tmux_binding=binding,
            session_id="session-a",
            registry_generation_id="generation-a",
        )
    )
    path = tmp_path / "manifest.json"
    write_session_manifest(path, payload)
    return path, payload


def test_primary_selector_preserves_owned_and_joined_contracts(tmp_path: Path) -> None:
    """A saved owned pane can have a nonzero index and a joined pane uses index zero."""

    binding = _saved_binding(tmp_path)
    owned = _pane()
    auxiliary = _pane(pane_id="%9", window_id="@2", window_index="1", pane_active=True)
    assert select_primary_tmux_surface(binding, (owned, auxiliary)).pane == owned

    joined = _pane(pane_index="0")
    assert select_primary_tmux_surface(binding, (joined, auxiliary), joined=True).pane == joined
    assert (
        select_primary_tmux_surface(binding, (owned, auxiliary), joined=True).state
        == "missing_pane"
    )
    renamed = replace(joined, window_name="other")
    assert (
        select_primary_tmux_surface(binding, (renamed, auxiliary), joined=True).state
        == "missing_pane"
    )


def test_primary_selector_distinguishes_inconclusive_surfaces(tmp_path: Path) -> None:
    """Only a unique live primary candidate supplies a replacement."""

    binding = _saved_binding(tmp_path)
    candidate = _pane(pane_id="%9")
    observed = select_primary_tmux_surface(binding, (candidate,))
    assert observed.state == "stale_handles"
    assert observed.pane is None
    assert observed.replacement == candidate
    assert binding.primary_pane_id == "%7"
    assert select_primary_tmux_surface(binding, None).state == "missing_session"
    assert select_primary_tmux_surface(binding, ()).state == "missing_window"
    ambiguous = select_primary_tmux_surface(binding, (candidate, _pane(pane_id="%10")))
    assert ambiguous.state == "ambiguous_pane"
    assert ambiguous.replacement is None
    dead = _pane(pane_dead=True)
    dead_observation = select_primary_tmux_surface(binding, (dead, candidate))
    assert dead_observation.state == "dead_pane"
    assert dead_observation.pane == dead
    assert dead_observation.replacement is None


def test_manifest_resume_uses_canonical_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A conflicting projection and enclosing socket cannot redirect restore."""

    binding = _saved_binding(tmp_path)
    path, payload = _manifest(tmp_path, binding)
    payload["backend_state"].update(tmux_window_id="@99", tmux_pane_id="%99")
    payload["agent_launch_authority"].update(primary_window_id="@98", primary_pane_id="%98")
    path.write_text(json.dumps(payload), encoding="utf-8")
    captured: list[tuple[str | None, str | None, str | None]] = []

    def capture_state(**options: Any) -> InteractiveSession:
        """Capture backend reconstruction without touching either socket."""

        state = runtime._resume_local_interactive_state(
            options["resume_state"], launch_plan=options["launch_plan"]
        )
        assert state is not None
        captured.append((current_tmux_socket_path(), state.tmux_window_id, state.tmux_pane_id))
        return cast(InteractiveSession, object())

    monkeypatch.setattr(runtime, "_create_backend_session", capture_state)
    with tmux_server_scope(tmp_path / "enclosing.sock"):
        controller = runtime.resume_runtime_session(session_manifest_path=path, read_only=True)
        assert current_tmux_socket_path() == str(tmp_path / "enclosing.sock")

    assert captured == [(binding.socket_path, "@1", "%7")]
    assert controller.tmux_socket_path == binding.socket_path
    assert controller.build_shared_registry_record() is not None
    record = controller.build_shared_registry_record()
    assert record is not None
    assert record.terminal.socket_path == binding.socket_path
    assert record.terminal.current_session_name == binding.session_name
    assert record.native_surface is not None
    assert record.native_surface.model_dump()["pane_id"] == "%7"
    assert json.loads(path.read_bytes()) == payload


def test_missing_saved_socket_cannot_inherit_enclosing_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing socket prevents a live constructor or direct primary observation."""

    binding = _saved_binding(tmp_path).model_copy(update={"socket_path": None})
    path, _ = _manifest(tmp_path, binding, bind_execution=False)
    monkeypatch.setattr(
        runtime, "_create_backend_session", lambda **_: pytest.fail("live constructor")
    )
    monkeypatch.setattr(managed_terminal, "TmuxServer", lambda _: pytest.fail("tmux observation"))
    with tmux_server_scope(tmp_path / "enclosing.sock"):
        with pytest.raises(SessionManifestError, match="requires a saved tmux socket"):
            runtime.resume_runtime_session(session_manifest_path=path)
        with pytest.raises(SessionManifestError, match="requires a saved tmux socket"):
            observe_primary_tmux(binding)
        with pytest.raises(ValueError, match="requires a saved tmux socket"):
            with persisted_execution_scope(path):
                pytest.fail("persisted gateway scope inherited the enclosing tmux socket")


def test_owner_repair_rechecks_live_membership_and_publishes_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read-only inspection is pure and repair acts only on the re-observed candidate."""

    binding = _saved_binding(tmp_path)
    path, payload = _manifest(tmp_path, binding)
    before = path.read_bytes()
    candidate = _pane(pane_id="%9", session_id="$4")
    panes = (candidate,)

    class _ObservedServer:
        """Expose one checked session observation on the saved socket."""

        def __init__(self, socket_path: str) -> None:
            assert socket_path == binding.socket_path

        def observe_session(self, session_name: str) -> tuple[TmuxPaneRecord, ...]:
            """Return the available primary evidence for this read."""

            assert session_name == binding.session_name
            return panes

    def publish() -> None:
        """Record the binding visible to a registry refresh after commit."""

        published.append(load_session_manifest(path).payload["tmux"]["primary_pane_id"])

    published: list[str] = []
    monkeypatch.setattr(managed_terminal, "TmuxServer", _ObservedServer)
    monkeypatch.setattr(runtime, "_create_backend_session", lambda **_: object())
    monkeypatch.setattr(
        runtime.RuntimeSessionController, "ensure_gateway_capability", lambda _: None
    )
    controller = runtime.resume_runtime_session(session_manifest_path=path)
    authority = runtime.parse_session_manifest_payload(payload, source=str(path))
    monkeypatch.setattr(controller, "require_managed_control_owner", lambda: authority)
    monkeypatch.setattr(controller, "refresh_shared_registry_record", publish)

    assert observe_primary_tmux(binding).replacement == candidate
    assert path.read_bytes() == before
    assert not published

    panes = (replace(candidate, session_id="$5"),)
    with pytest.raises(SessionManifestError, match="replacement changed before repair"):
        controller._repair_primary_tmux_binding(binding, candidate)
    assert path.read_bytes() == before
    assert not published

    panes = (candidate,)
    repaired = controller._repair_primary_tmux_binding(binding, candidate)
    assert repaired.primary_pane_id == "%9"
    assert controller.m_tmux_binding == repaired
    assert published == ["%9"]


def test_gateway_identity_requires_valid_canonical_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A connected backing API alone cannot qualify a stale or foreign primary pane."""

    binding = _saved_binding(tmp_path)
    path, _ = _manifest(tmp_path, binding, backend="codex_headless")
    adapter = gateway_service._ServerManagedHeadlessGatewayAdapter(
        attach_contract=GatewayAttachContractV1(
            attach_identity="fixture",
            backend="codex_headless",
            tmux_session_name=binding.session_name,
            working_directory=str(tmp_path),
            manifest_path=str(path),
            backend_metadata=GatewayAttachBackendMetadataHeadlessV1(
                tool="codex",
                managed_api_base_url="http://localhost:3000",
                managed_agent_ref="agent-a",
            ),
        ),
    )
    target = gateway_service._GatewayTargetState(
        instance_id="agent-a",
        connectivity="connected",
        terminal_surface_eligibility="ready",
        prompt_admission_open=True,
    )
    monkeypatch.setattr(adapter, "inspect_target", lambda: target)
    pane = _pane()

    def observe(selected: SessionManifestTmuxSectionV1, *, joined: bool) -> PrimaryTmuxObservation:
        """Verify the gateway uses the saved owner scope and one primary observation."""

        assert current_tmux_socket_path() == binding.socket_path
        return select_primary_tmux_surface(selected, (pane,), joined=joined)

    monkeypatch.setattr(gateway_service, "observe_primary_tmux", observe)
    with tmux_server_scope(tmp_path / "unrelated.sock"):
        assert adapter.capture_plugin_execution_identity() == ("generation-a", "@1", "%7")
        pane = replace(pane, pane_id="%9")
        with pytest.raises(GatewayError, match="Managed execution identity is unavailable"):
            adapter.capture_plugin_execution_identity()


@pytest.mark.parametrize("conflict", [None, "binding", "generation"])
def test_repair_preserves_current_state_and_rejects_stale_writes(
    tmp_path: Path, conflict: str | None
) -> None:
    """The repair updates both projections only for the same complete saved binding."""

    binding = _saved_binding(tmp_path)
    path, payload = _manifest(tmp_path, binding)
    authority = runtime.parse_session_manifest_payload(
        payload, source=str(path)
    ).runtime.execution_binding
    assert authority is not None
    if conflict == "binding":
        update_session_manifest(path, {"tmux": {**payload["tmux"], "primary_pane_id": "%12"}})
    elif conflict == "generation":
        update_session_manifest(
            path,
            {
                "registry_generation_id": "generation-b",
                "runtime": {**payload["runtime"], "registry_generation_id": "generation-b"},
            },
        )
    update_session_manifest(
        path,
        {
            "backend_state": {
                **load_session_manifest(path).payload["backend_state"],
                "turn_index": 25,
            }
        },
    )
    before = path.read_bytes()

    def repair() -> dict[str, Any]:
        """Try to commit the observed replacement against the captured binding."""

        return repair_session_tmux_binding(
            path,
            expected_agent_id="agent-a",
            expected_session_id="session-a",
            expected_generation_id="generation-a",
            expected_binding=binding,
            expected_execution_binding=authority,
            window_name="replacement",
            window_id="@4",
            pane_id="%4",
        ).payload

    if conflict is not None:
        with pytest.raises(
            SessionManifestError, match="generation, or primary tmux binding changed"
        ):
            repair()
        assert path.read_bytes() == before
        return

    repaired = repair()
    assert repaired["tmux"]["primary_window_name"] == "replacement"
    assert (
        repaired["tmux"]["primary_window_id"] == repaired["backend_state"]["tmux_window_id"] == "@4"
    )
    assert repaired["tmux"]["primary_pane_id"] == repaired["backend_state"]["tmux_pane_id"] == "%4"
    assert repaired["agent_launch_authority"]["primary_pane_id"] == "%4"
    assert repaired["native_surface"]["pane_id"] == "%4"
    assert repaired["backend_state"]["turn_index"] == 25
