"""Exercise safe mode capability and read-only execution evidence projections."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.headless_snapshots import (
    headless_control_observation,
    latest_headless_turn,
)
from houmao.agents.realm_controller.managed_control import (
    ManagedControlObservationV1,
    managed_control_capabilities,
)
from houmao.agents.realm_controller.native_surface import (
    TerminalNativeSurfaceV1,
    WebNativeSurfaceV1,
)
from houmao.agents.realm_controller.usage_models import UsageTurnSnapshot


@pytest.mark.parametrize(
    ("tool", "mode", "backend", "surface", "source", "correlation", "can_dispatch", "raw_keys"),
    [
        ("kimi", "headless", "kimi_headless", None, "headless_artifacts", "request", True, False),
        (
            "kimi",
            "tui",
            "local_interactive",
            TerminalNativeSurfaceV1(tmux_session_name="test", pane_id="%1"),
            "terminal_tracker",
            "surface",
            True,
            True,
        ),
        ("kimi", "tui", "local_interactive", None, "owner_registry", "none", False, False),
        (
            "dsh",
            "web",
            "dsh_web",
            WebNativeSurfaceV1(origin="http://127.0.0.1:8123", native_session_id="session-web"),
            "web_native",
            "native_turn",
            True,
            False,
        ),
        ("dsh", "service", "dsh_acp", None, "service_native", "native_turn", True, False),
        ("kimi", "service", "kimi_acp", None, "service_native", "native_turn", True, False),
        (
            "codex",
            "service",
            "codex_app_server",
            None,
            "service_native",
            "native_turn",
            True,
            False,
        ),
    ],
)
def test_managed_capabilities_reflect_the_verified_surface(
    tool, mode, backend, surface, source, correlation, can_dispatch, raw_keys
) -> None:
    """Keep control capability independent of tmux supervision and current readiness."""

    capabilities = managed_control_capabilities(
        tool=tool, mode=mode, backend=backend, native_surface=surface
    )
    assert capabilities.mode == mode
    assert capabilities.backend == backend
    assert capabilities.evidence_source == source
    assert capabilities.correlation == correlation
    assert {"state", "stop", "relaunch"} <= set(capabilities.operations)
    for operation in ("prompt", "interrupt", "events", "usage"):
        assert (operation in capabilities.operations) == can_dispatch
    if raw_keys:
        capabilities.require("send_keys")
    else:
        with pytest.raises(BackendExecutionError, match="send_keys.*unsupported"):
            capabilities.require("send_keys")
    if backend == "kimi_acp":
        assert not {"human_handoff", "native_refresh"} & set(capabilities.operations)


@pytest.mark.parametrize(
    "extra",
    [
        {"freshness": "stale"},
        {"connection_ready": False},
        {"owner_available": False},
        {"active_turn_id": "ongoing"},
        {"active_request_id": "ongoing"},
    ],
)
def test_observation_cannot_admit_from_incomplete_readiness(extra: dict[str, object]) -> None:
    """Refuse state claiming readiness despite stale, disconnected, or active evidence."""

    observation = {
        "source": "service_native",
        "freshness": "current",
        "can_accept_prompt_now": True,
        **extra,
    }
    with pytest.raises(ValidationError, match="Ready observations"):
        ManagedControlObservationV1.model_validate(observation)


def test_headless_evidence_orders_owner_request_ids_by_actual_turn(tmp_path: Path) -> None:
    """Correlate the most recent artifact independently of its caller-selected ID."""

    manifest = tmp_path / "manifest.json"
    root = tmp_path / "manifest.turn-artifacts"
    for index, request_id in enumerate(("a-initial", "z-next", "b-latest"), 1):
        turn = root / request_id
        turn.mkdir(parents=True)
        start = UsageTurnSnapshot(
            agent_id="agent-1",
            runtime_session_id="runtime-1",
            turn_id=request_id,
            backend="kimi_headless",
            provider="kimi",
            turn_index=index,
            started_at_utc=f"2026-11-19T17:00:0{index}+00:00",
        )
        (turn / "usage-start.json").write_text(start.model_dump_json(), encoding="utf-8")
        if request_id != "b-latest":
            (turn / "exitcode").write_text("0\n", encoding="utf-8")

    latest = latest_headless_turn(manifest_path=manifest, tool="kimi", backend="kimi_headless")

    assert latest is not None
    assert latest.turn_id == "b-latest"
    assert latest.turn_index == 3
    assert latest.status == "active"
    assert latest.returncode is None
    assert latest.process_alive is False
    assert latest.completion_source is None
    observation = headless_control_observation(latest, owner_available=True)
    assert observation.freshness == "unknown"
    assert observation.can_accept_prompt_now is False
    assert observation.last_request_id == "b-latest"
    assert observation.last_outcome == "uncertain"
