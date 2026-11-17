"""Keep one native refresh deadline across read-only preparation and mutating handoff."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import threading
import time
from unittest.mock import Mock

from fastapi import HTTPException
import pytest

from houmao.agents import dsh_configuration
from houmao.agents.realm_controller import gateway_service, native_refresh
from houmao.agents.realm_controller.errors import GatewayError
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    NativeHomeChangedError,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
    native_home_etag,
)
from tests.unit.agents.realm_controller.test_dsh_web_gateway import _runtime
from tests.unit.agents.realm_controller.test_gateway_native_refresh import (
    _bind_native,
    _observation,
)


def test_gateway_slow_initial_read_times_out_without_late_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An abandoned read may finish later but can never schedule a reload behind its caller."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    before = _observation()
    _bind_native(runtime, monkeypatch, before)
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    native = Mock()
    monkeypatch.setattr(gateway_service, "perform_native_refresh", native)

    def slow_read(_: object) -> CommonPluginObservationV1:
        """Hold a passive read after the request's absolute budget expires."""

        entered.set()
        try:
            assert release.wait(timeout=2)
            return before
        finally:
            finished.set()

    monkeypatch.setattr(gateway_service, "observe_common_plugins", slow_read)
    started = time.monotonic()
    try:
        with pytest.raises(HTTPException) as error:
            runtime.refresh_native(NativeRefreshRequestV1(timeout_seconds=0.02))
        assert error.value.status_code == 503
        assert time.monotonic() - started < 0.5
        assert entered.is_set()
        assert not runtime._native_refresh_blocks_input_locked()
        native.assert_not_called()
    finally:
        release.set()
        assert finished.wait(timeout=2)
    native.assert_not_called()
    assert not runtime._native_refresh_blocks_input_locked()


def test_gateway_does_not_reserve_mutation_after_observation_consumes_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Expiry between passive planning and admission leaves no mutating worker or guard."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    before = _observation()
    _bind_native(runtime, monkeypatch, before)
    now = [0.0]
    monkeypatch.setattr(gateway_service, "time", SimpleNamespace(monotonic=lambda: now[0]))

    def plan(_: object) -> None:
        """Account for preflight time before the gateway can reserve input admission."""

        now[0] = 2.0
        return None

    monkeypatch.setattr(gateway_service, "plan_native_refresh", plan)
    native = Mock()
    monkeypatch.setattr(gateway_service, "perform_native_refresh", native)
    result = runtime.refresh_native(NativeRefreshRequestV1(timeout_seconds=1.0))
    assert result.outcome == "unavailable"
    assert result.method == "none" and result.effects == "absent"
    assert result.diagnostics == ["native_refresh_deadline_expired_before_handoff"]
    assert not runtime._native_refresh_blocks_input_locked()
    native.assert_not_called()


def test_gateway_worker_receives_original_absolute_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Native worker time cannot restart the budget consumed by controller/observation reads."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    before = _observation()
    controller = _bind_native(runtime, monkeypatch, before)
    now = [0.0]
    monkeypatch.setattr(gateway_service, "time", SimpleNamespace(monotonic=lambda: now[0]))

    def read(_: object) -> CommonPluginObservationV1:
        """Consume two seconds of the original ten-second native request budget."""

        now[0] = 2.0
        return before

    monkeypatch.setattr(gateway_service, "observe_common_plugins", read)
    result = NativeRefreshResultV1(
        method="native_reload", outcome="refreshed", observation=_observation("current")
    )
    native = Mock(return_value=result)
    monkeypatch.setattr(gateway_service, "perform_native_refresh", native)
    payload = NativeRefreshRequestV1(timeout_seconds=10.0)
    assert runtime.refresh_native(payload) is result
    native.assert_called_once_with(controller, payload, deadline_monotonic=10.0, observation=before)


def test_gateway_conditional_home_refuses_retargeting_before_planning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reused gateway address cannot authorize another native-home identity."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    before = _observation()
    _bind_native(runtime, monkeypatch, before)
    plan = Mock()
    native = Mock()
    monkeypatch.setattr(gateway_service, "plan_native_refresh", plan)
    monkeypatch.setattr(gateway_service, "perform_native_refresh", native)
    changed = before.home.model_copy(update={"identity": {"generation": "other"}})
    with pytest.raises(NativeHomeChangedError):
        runtime.refresh_native(
            NativeRefreshRequestV1(), expected_home_etag=native_home_etag(changed)
        )
    plan.assert_not_called()
    native.assert_not_called()
    assert not runtime._native_refresh_blocks_input_locked()


def test_gateway_matching_conditional_home_keeps_readonly_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A captured matching target permits the usual observe-first current decision."""

    runtime, _, _ = _runtime(tmp_path, monkeypatch)
    current = _observation("current")
    _bind_native(runtime, monkeypatch, current)
    native = Mock()
    monkeypatch.setattr(gateway_service, "perform_native_refresh", native)
    result = runtime.refresh_native(
        NativeRefreshRequestV1(), expected_home_etag=native_home_etag(current.home)
    )
    assert result.method == "noop" and result.outcome == "already_current"
    native.assert_not_called()


def test_service_slow_reobservation_cannot_start_native_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh observation that consumes the remaining budget cannot authorize a late reload."""

    now = [0.0]
    monkeypatch.setattr(native_refresh, "time", SimpleNamespace(monotonic=lambda: now[0]))
    before = _observation()

    def slow_read(_: object) -> CommonPluginObservationV1:
        """Advance deterministic preflight time beyond the original caller deadline."""

        now[0] = 2.0
        return before

    monkeypatch.setattr(native_refresh, "observe_common_plugins", slow_read)
    mutate = Mock()
    controller = SimpleNamespace(backend_session=SimpleNamespace(refresh_common_plugins=mutate))
    result = native_refresh.perform_native_refresh(
        controller, NativeRefreshRequestV1(timeout_seconds=1.0), deadline_monotonic=1.0
    )
    assert result.outcome == "unavailable"
    assert result.method == "none" and result.effects == "absent"
    assert result.native_settled and result.native_ready
    mutate.assert_not_called()


def test_service_expired_before_reobservation_uses_known_absent_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A delayed worker declines without even starting another read or inventing native effects."""

    monkeypatch.setattr(native_refresh, "time", SimpleNamespace(monotonic=lambda: 2.0))
    read = Mock()
    monkeypatch.setattr(native_refresh, "observe_common_plugins", read)
    mutate = Mock()
    controller = SimpleNamespace(backend_session=SimpleNamespace(refresh_common_plugins=mutate))
    before = _observation()
    result = native_refresh.perform_native_refresh(
        controller,
        NativeRefreshRequestV1(timeout_seconds=1.0),
        deadline_monotonic=1.0,
        observation=before,
    )
    assert result.outcome == "unavailable"
    assert result.effects == "absent" and result.observation is before
    read.assert_not_called()
    mutate.assert_not_called()


def test_service_handoff_receives_remaining_budget_and_original_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backend authentication/native preflight receive the same deadline rather than a reset timer."""

    now = [0.0]
    monkeypatch.setattr(native_refresh, "time", SimpleNamespace(monotonic=lambda: now[0]))
    before = _observation()

    def read(_: object) -> CommonPluginObservationV1:
        """Consume observation time before native handoff."""

        now[0] = 3.0
        return before

    monkeypatch.setattr(native_refresh, "observe_common_plugins", read)
    monkeypatch.setattr(native_refresh, "inspect_native_home", lambda _: before.home)
    current = _observation("current")
    raw = {
        "outcome": "refreshed",
        "observation": {**current.model_dump(exclude={"home"}), "identity": {}},
        "effects": "confirmed",
        "native_ready": True,
        "native_settled": True,
    }
    mutate = Mock(return_value=raw)
    controller = SimpleNamespace(backend_session=SimpleNamespace(refresh_common_plugins=mutate))
    result = native_refresh.perform_native_refresh(
        controller, NativeRefreshRequestV1(timeout_seconds=10.0), deadline_monotonic=10.0
    )
    assert result.outcome == "refreshed"
    mutate.assert_called_once_with(
        timeout_seconds=7.0, deadline_monotonic=10.0, expected_identity=before.home.identity
    )


def test_service_reobservation_cannot_retarget_captured_native_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replacement between gateway observation and worker preflight receives no mutation."""

    before = _observation()
    changed = before.model_copy(
        update={"home": before.home.model_copy(update={"identity": {"generation": "other"}})}
    )
    monkeypatch.setattr(native_refresh, "observe_common_plugins", lambda _: changed)
    mutate = Mock()
    controller = SimpleNamespace(backend_session=SimpleNamespace(refresh_common_plugins=mutate))
    result = native_refresh.perform_native_refresh(
        controller, NativeRefreshRequestV1(), observation=before
    )
    assert result.outcome == "unavailable" and result.effects == "absent"
    assert result.observation.home == before.home
    assert result.diagnostics == ["native_authority_changed_before_handoff"]
    mutate.assert_not_called()


@pytest.mark.parametrize("selected", ["0.2.2-rc.3", "0.2.2-rc.1", None])
def test_headless_automatic_observation_rechecks_authority_after_version_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: str | None
) -> None:
    """Qualified, unqualified, and failed probes cannot publish facts from a superseded envelope."""

    home = NativeHomeV1(
        agent_id="agent",
        backend="dsh_acp",
        tool="dsh",
        home_dir=str(tmp_path),
        identity={"generation": "old"},
    )
    controller = SimpleNamespace(
        backend_session=SimpleNamespace(),
        launch_plan=SimpleNamespace(metadata={}, home_path=tmp_path, env={}, executable="unused"),
    )
    inspect = Mock(side_effect=[home, home.model_copy(update={"identity": {"generation": "new"}})])
    monkeypatch.setattr(native_refresh, "inspect_native_home", inspect)
    monkeypatch.setattr(dsh_configuration.DshSetup, "from_file", Mock(return_value=object()))
    monkeypatch.setattr(dsh_configuration, "load_dsh_home", Mock())
    probe = Mock(return_value=SimpleNamespace(stdout=selected))
    if selected is None:
        probe.side_effect = OSError("synthetic missing binary")
    monkeypatch.setattr(native_refresh.subprocess, "run", probe)
    with pytest.raises(GatewayError, match="authority changed during observation"):
        native_refresh.observe_common_plugins(controller)
    assert inspect.call_count == 2
