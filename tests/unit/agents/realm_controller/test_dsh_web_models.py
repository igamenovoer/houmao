"""Native Web models separate browser authority from tmux process supervision."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from tests.unit.agents.realm_controller.test_dsh_web_observation import _metadata
from tests.unit.agents.realm_controller.test_gateway_support import _sample_headless_plan
from tests.unit.passive_server.test_discovery import _make_record


def _manifest(tmp_path: Path) -> dict:
    """Build a complete synthetic Web manifest without launching any process."""

    plan = replace(
        _sample_headless_plan(tmp_path),
        backend="dsh_web",
        tool="dsh",
        home_env_var="DSH_HOME",
        native_surface_kind="web",
    )
    return build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            backend_state={
                "origin": _metadata().origin,
                "browser_url": _metadata().browser_url,
                "web_identity": _metadata().identity.model_dump(),
                "turn_index": 2,
                "tmux_session_name": "supervisor",
                "tmux_pane_id": "%4",
            },
            agent_name="web-agent",
            agent_id="owner",
            session_id="runtime",
            registry_generation_id="generation",
            tmux_session_name="supervisor",
            agent_def_dir=tmp_path / "agent-defs",
        )
    )


def test_web_manifest_serializes_a_browser_surface_and_separate_log_supervision(
    tmp_path: Path,
) -> None:
    """The native session remains queryable without a fake terminal backend section."""

    payload = _manifest(tmp_path)
    parsed = parse_session_manifest_payload(payload, source="synthetic Web manifest")
    assert parsed.backend == "dsh_web"
    assert parsed.launch_plan.native_surface_kind == "web"
    assert payload["native_surface"] == {
        "kind": "web",
        "origin": _metadata().origin,
        "native_session_id": "native",
    }
    assert payload["tmux"]["primary_window_role"] == "supervisor_logs"
    assert payload["tmux"]["primary_pane_id"] == "%4"
    assert payload["headless"] is None and payload["local_interactive"] is None
    assert payload["interactive"]["terminal_id"] is None
    assert payload["interactive"]["parsing_mode"] is None


@pytest.mark.parametrize(
    "damage",
    [
        "surface_missing",
        "surface_terminal",
        "native_id",
        "generation",
        "runtime",
        "agent",
        "incarnation",
        "parser",
        "log_role",
    ],
)
def test_web_manifest_rejects_missing_mismatched_or_terminal_authority(
    tmp_path: Path, damage: str
) -> None:
    """No record may reinterpret a supervisor pane as authoritative native Web state."""

    payload = _manifest(tmp_path)
    if damage == "surface_missing":
        payload["native_surface"] = None
    elif damage == "surface_terminal":
        payload["native_surface"] = {
            "kind": "terminal",
            "tmux_session_name": "supervisor",
            "pane_id": "%4",
        }
    elif damage == "native_id":
        payload["native_surface"]["native_session_id"] = "other-session"
    elif damage in {"generation", "runtime", "agent", "incarnation"}:
        key = {
            "generation": "generation",
            "runtime": "runtime_session_id",
            "agent": "agent_id",
            "incarnation": "agent_incarnation",
        }[damage]
        payload["backend_state"]["web_identity"][key] = (
            "" if damage == "incarnation" else "replacement"
        )
    elif damage == "parser":
        payload["interactive"]["parsing_mode"] = "shadow_only"
    else:
        payload["tmux"]["primary_window_role"] = "managed_agent_surface"
    with pytest.raises(SessionManifestError):
        parse_session_manifest_payload(payload, source="invalid synthetic Web manifest")


def test_registry_web_discovery_requires_typed_surface_and_keeps_supervisor_separate() -> None:
    """Web records retain a real supervisor without claiming that it is a terminal UI."""

    payload = _make_record(agent_id="owner", session_name="supervisor").model_dump(mode="json")
    payload["identity"] = {"backend": "dsh_web", "tool": "dsh"}
    payload["mode"] = "web"
    payload["native_surface"] = {
        "kind": "web",
        "origin": _metadata().origin,
        "native_session_id": "native",
    }
    record = ManagedAgentRegistryRecordV3.model_validate(payload)
    assert record.native_surface is not None and record.native_surface.kind == "web"
    assert record.terminal.session_name == "supervisor"
    invalid = deepcopy(payload)
    invalid["native_surface"] = None
    with pytest.raises(ValidationError, match="native Web surface"):
        ManagedAgentRegistryRecordV3.model_validate(invalid)
