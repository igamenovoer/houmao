"""Verify conservative secondary-tool refresh without starting native control work."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller import native_refresh
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
