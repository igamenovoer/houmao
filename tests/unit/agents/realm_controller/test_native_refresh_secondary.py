"""Verify conservative secondary-tool refresh without starting native control work."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller import native_refresh
from houmao.agents.realm_controller.backends.kimi_web import KimiWebSession
from houmao.agents.realm_controller.backends.service_runtime import ManagedServiceSession
from houmao.agents.realm_controller.native_refresh_models import (
    NativeHomeV1,
    NativeRefreshRequestV1,
    native_refresh_status_code,
)


@pytest.mark.parametrize("tool", ["kimi", "codex", "claude"])
@pytest.mark.parametrize("mode", ["headless", "tui"])
def test_secondary_mode_keeps_unknown_scope_and_refuses_unowned_reload(
    monkeypatch: pytest.MonkeyPatch, tool: str, mode: str
) -> None:
    """Native capability evidence cannot fabricate a maintained transport or automatic boundary."""

    backend = f"{tool}_headless" if mode == "headless" else "local_interactive"
    home = NativeHomeV1(
        agent_id=f"{tool}-{mode}", backend=backend, tool=tool, home_dir=f"/owned/{tool}-{mode}"
    )
    native = Mock(spec=[])
    controller = SimpleNamespace(
        backend_session=native,
        launch_plan=SimpleNamespace(backend=backend),
    )
    monkeypatch.setattr(native_refresh, "inspect_native_home", lambda _: home)
    observation = native_refresh.observe_common_plugins(controller)
    assert observation.home == home
    assert observation.freshness == "unknown"
    assert not observation.coverage_complete
    assert not observation.automatic
    assert not observation.native_reload
    assert {resource.kind for resource in observation.resources} == {"skills", "mcp"}
    assert all(
        resource.freshness == "unknown" and not resource.complete and not resource.supported
        for resource in observation.resources
    )
    result = native_refresh.perform_native_refresh(controller, NativeRefreshRequestV1())
    assert result.method == "none"
    assert result.outcome == "unsupported"
    assert result.effects == "absent"
    assert native_refresh_status_code(result) == 501
    assert native.mock_calls == []


@pytest.mark.parametrize(
    ("tool", "backend", "version", "session_type"),
    [
        ("kimi", "kimi_web", "2.7.2", KimiWebSession),
        ("kimi", "kimi_acp", "2.7.2", ManagedServiceSession),
        ("codex", "codex_app_server", "0.171.0", ManagedServiceSession),
    ],
)
def test_native_startup_version_does_not_qualify_refresh(
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    backend: str,
    version: str,
    session_type: type,
) -> None:
    """Require native resource evidence even when a newer backend starts."""

    home = NativeHomeV1(agent_id="agent", backend=backend, tool=tool, home_dir="/owned/home")
    session = Mock(spec=session_type)
    controller = SimpleNamespace(
        backend_session=session,
        launch_plan=SimpleNamespace(
            backend=backend, metadata={backend: {"detected_version": version}}
        ),
    )
    monkeypatch.setattr(native_refresh, "inspect_native_home", lambda _: home)
    result = native_refresh.perform_native_refresh(controller, NativeRefreshRequestV1())

    assert result.outcome == "unsupported"
    assert result.effects == "absent"
    assert result.observation.freshness == "unknown"
    assert not result.observation.automatic
    assert not result.observation.native_reload
    assert session.mock_calls == []
