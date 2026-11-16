"""Preserve gateway-authored conversation state when a held controller is stale."""

from __future__ import annotations

from pathlib import Path
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
def test_gateway_controls_preserve_newer_native_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """An old controller must not overwrite a native turn committed by the gateway."""

    plan = _sample_headless_plan(tmp_path)
    manifest = default_manifest_path(tmp_path, "claude_headless", "managed-one")
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
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda **_kwargs: 43123,
    )
    # A separately resumed gateway commits a later native conversation and turn.
    write_session_manifest(
        manifest,
        build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=plan,
                role_name="role",
                brain_manifest_path=tmp_path / "brain.yaml",
                backend_state={
                    "session_id": "gateway-authored-conversation",
                    "turn_index": 7,
                    "role_bootstrap_applied": True,
                    "tmux_session_name": "HOUMAO-held-controller",
                },
                agent_name="HOUMAO-held-controller",
                agent_id="held-owner",
                tmux_session_name="HOUMAO-held-controller",
                session_id="managed-one",
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
