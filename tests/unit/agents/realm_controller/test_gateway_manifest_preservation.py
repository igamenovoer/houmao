"""Preserve gateway-authored conversation state when a held controller is stale."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.agent_identity import AGENT_ID_ENV_VAR
from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_manifest_path
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    load_session_manifest,
    write_session_manifest,
)
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from tests.unit.agents.realm_controller.test_gateway_support import (
    _FakeInteractiveSession,
    _sample_headless_plan,
)


@pytest.mark.parametrize("operation", ["ensure", "attach", "detach", "status"])
@pytest.mark.parametrize("tool", ["claude", "dsh_headless", "dsh_web"])
def test_gateway_controls_preserve_newer_native_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, tool: str
) -> None:
    """An old controller must not overwrite a native turn committed by the gateway."""

    plan = _sample_headless_plan(tmp_path)
    if tool == "dsh_headless":
        plan = replace(plan, backend="dsh_headless", tool="dsh", home_env_var="DSH_HOME")
    elif tool == "dsh_web":
        plan = replace(
            plan, backend="dsh_web", tool="dsh", home_env_var="DSH_HOME", native_surface_kind="web"
        )
    manifest = default_manifest_path(tmp_path, plan.backend, "managed-one")
    controller = RuntimeSessionController(
        launch_plan=plan,
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest,
        agent_def_dir=tmp_path / "agents",
        backend_session=_FakeInteractiveSession(),
        agent_identity="HOUMAO-held-controller",
        agent_id="held-owner",
        tmux_session_name="HOUMAO-held-controller",
    )
    stale_backend = Mock(return_value={"session_id": None, "turn_index": 0})
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._backend_state_for_session", stale_backend
    )
    published = Mock()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared", published
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared", Mock()
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.tmux_session_exists_shared", lambda **_: True
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._read_optional_tmux_session_env_var",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda **_kwargs: 43123,
    )
    store = SimpleNamespace(snapshot=lambda: None)
    access = SimpleNamespace(
        store=store,
        require_self_signing_state=lambda: None,
        target=SimpleNamespace(incarnation="fixture"),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.gateway_access_for_manifest", lambda _path: access
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.load_gateway_deployment", lambda _path: None
    )
    # A separately resumed gateway commits a later native conversation and turn.
    backend_state = {
        "session_id": "gateway-authored-conversation",
        "turn_index": 7,
        "role_bootstrap_applied": True,
        "tmux_session_name": "HOUMAO-held-controller",
    }
    if tool == "dsh_web":
        backend_state.update(
            {
                "origin": "http://127.0.0.1:55123",
                "browser_url": "http://127.0.0.1:55123",
                "web_identity": {
                    "protocol_version": 1,
                    "agent_id": "held-owner",
                    "runtime_session_id": "managed-one",
                    "generation": "new-generation",
                    "host_incarnation": "new-host",
                    "native_session_id": "gateway-authored-conversation",
                    "agent_incarnation": "new-body",
                },
            }
        )
    write_session_manifest(
        manifest,
        build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=plan,
                role_name="role",
                brain_manifest_path=tmp_path / "brain.yaml",
                backend_state=backend_state,
                agent_name="HOUMAO-held-controller",
                agent_id="held-owner",
                tmux_session_name="HOUMAO-held-controller",
                session_id="managed-one",
                registry_generation_id="new-generation" if tool == "dsh_web" else None,
                agent_def_dir=tmp_path / "agents",
            )
        ),
    )
    original = manifest.read_bytes()
    if operation == "ensure":
        controller.ensure_gateway_capability()
    elif operation == "attach":
        assert controller.attach_gateway().status == "ok"
    elif operation == "detach":
        assert controller.detach_gateway().status == "ok"
    else:
        controller.gateway_status()
    assert manifest.read_bytes() == original
    saved = load_session_manifest(manifest).payload
    if tool == "dsh_web":
        assert saved["native_surface"] == {
            "kind": "web",
            "origin": "http://127.0.0.1:55123",
            "native_session_id": "gateway-authored-conversation",
        }
        assert saved["backend_state"]["web_identity"] == backend_state["web_identity"]
    else:
        assert saved["headless"]["session_id"] == "gateway-authored-conversation"
        assert saved["headless"]["turn_index"] == 7
    assert saved["backend_state"]["session_id"] == "gateway-authored-conversation"
    stale_backend.assert_not_called()
    paths = gateway_paths_from_manifest_path(manifest)
    assert paths is not None and paths.attach_path.is_file()
    assert all(
        call.kwargs["env_vars"][AGENT_ID_ENV_VAR] == "held-owner"
        for call in published.call_args_list
    )


def test_dsh_headless_manifest_preserves_newer_turn_across_stale_writes(tmp_path: Path) -> None:
    """Keep the latest same-generation conversation while permitting a new generation."""

    plan = replace(
        _sample_headless_plan(tmp_path), backend="dsh_headless", tool="dsh", home_env_var="DSH_HOME"
    )
    manifest = default_manifest_path(tmp_path, plan.backend, "managed-one")
    request = SessionManifestRequest(
        launch_plan=plan,
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        backend_state={"session_id": None, "turn_index": 0},
        agent_name="HOUMAO-held-controller",
        agent_id="held-owner",
        session_id="managed-one",
        registry_generation_id="generation-one",
    )
    stale = build_session_manifest_payload(request)
    current = build_session_manifest_payload(
        replace(request, backend_state={"session_id": "native-conversation", "turn_index": 2})
    )
    write_session_manifest(manifest, current)
    refreshed = write_session_manifest(manifest, stale).payload
    assert refreshed["headless"]["session_id"] == "native-conversation"
    assert refreshed["backend_state"]["turn_index"] == 2

    restarted = write_session_manifest(
        manifest,
        build_session_manifest_payload(replace(request, registry_generation_id="generation-two")),
        expected_registry_generation_id="generation-one",
    ).payload
    assert restarted["headless"]["session_id"] is None
    assert restarted["backend_state"]["turn_index"] == 0
