"""Reject ambiguous native evidence before it can establish current authority."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.agents.realm_controller import native_refresh
from houmao.agents.realm_controller.errors import GatewayError
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    CommonPluginResourceV1,
    NativeHomeV1,
    NativeRefreshResultV1,
    refresh_guard_can_release,
)


def _identity(**changes: str) -> dict[str, str]:
    """Describe one exact live native execution without credentials."""

    return {
        "agent_id": "selected-agent",
        "runtime_session_id": "runtime",
        "generation": "generation",
        "host_incarnation": "host",
        "native_session_id": "native-session",
        "agent_incarnation": "native-agent",
        **changes,
    }


def _home(**identity_changes: str) -> NativeHomeV1:
    """Retain exact native authority in the public home descriptor."""

    return NativeHomeV1(
        agent_id="selected-agent",
        backend="dsh_web",
        tool="dsh",
        home_dir="/owned/native-home",
        home_env_var="DSH_HOME",
        identity=_identity(**identity_changes),
    )


def _raw(**changes: Any) -> dict[str, Any]:
    """Build explicit native completeness/readiness evidence for both common kinds."""

    return {
        "identity": _identity(),
        "observed_at_utc": "2026-01-01T00:00:00+00:00",
        "resources": [
            {
                "kind": kind,
                "component": "native",
                "freshness": "current",
                "boundary": "now",
                "inventory": [],
                "complete": True,
                "supported": True,
            }
            for kind in ("skills", "mcp")
        ],
        "coverage_complete": True,
        "native_settled": True,
        "native_ready": True,
        "native_reload": True,
        "automatic": False,
        **changes,
    }


@pytest.mark.parametrize("field", ["native_settled", "native_ready"])
@pytest.mark.parametrize("value", ["false", 1, None, []])
def test_malformed_native_readiness_cannot_release_guard(field: str, value: object) -> None:
    """Strict native state refuses truthiness coercion into a ready current no-op."""

    try:
        observation = native_refresh._observation(_home(), _raw(**{field: value}))
    except (ValueError, TypeError):
        return
    assert not refresh_guard_can_release(observation)
    planned = native_refresh.plan_native_refresh(observation)
    assert planned is not None and planned.outcome != "already_current"


@pytest.mark.parametrize("field", ["native_settled", "native_ready"])
def test_missing_native_readiness_cannot_release_guard(field: str) -> None:
    """Absent completion evidence remains unknown rather than defaulting ready."""

    raw = _raw()
    del raw[field]
    try:
        observation = native_refresh._observation(_home(), raw)
    except (ValueError, TypeError):
        return
    assert not refresh_guard_can_release(observation)
    planned = native_refresh.plan_native_refresh(observation)
    assert planned is not None and planned.outcome != "already_current"


def test_malformed_native_coverage_cannot_establish_current() -> None:
    """A truthy nonboolean cannot attest complete common source/runtime coverage."""

    try:
        observation = native_refresh._observation(_home(), _raw(coverage_complete="false"))
    except (ValueError, TypeError):
        return
    assert observation.freshness != "current"
    assert not observation.coverage_complete


@pytest.mark.parametrize("field", ["automatic", "native_reload"])
def test_malformed_native_capability_cannot_select_refresh_strategy(field: str) -> None:
    """Unknown native capability cannot become an automatic or mutating strategy."""

    raw = _raw(coverage_complete=False, native_reload=False)
    raw[field] = "false"
    for resource in raw["resources"]:
        resource["freshness"] = "unknown"
    try:
        observation = native_refresh._observation(_home(), raw)
    except (ValueError, TypeError):
        return
    planned = native_refresh.plan_native_refresh(observation)
    assert planned is not None and planned.outcome in {"unsupported", "unavailable"}


@pytest.mark.parametrize(
    "changed", [{"generation": "other-generation"}, {"host_incarnation": "other-host"}]
)
def test_raw_native_identity_cannot_be_relabelled_with_selected_home(
    monkeypatch: pytest.MonkeyPatch, changed: dict[str, str]
) -> None:
    """Current facts from another native incarnation cannot authorize this target."""

    controller = SimpleNamespace(
        backend_session=SimpleNamespace(
            observe_common_plugins=lambda: _raw(identity=_identity(**changed))
        )
    )
    monkeypatch.setattr(native_refresh, "inspect_native_home", lambda _: _home())
    try:
        observation = native_refresh.observe_common_plugins(controller)
    except GatewayError:
        return
    assert observation.freshness != "current"
    assert not refresh_guard_can_release(observation)


@pytest.mark.parametrize(
    "changed", [{"generation": "other-generation"}, {"host_incarnation": "other-host"}]
)
def test_stale_controller_cannot_claim_current_manifest_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: dict[str, str]
) -> None:
    """Same agent/home/backend do not replace generation and incarnation fences."""

    controller = SimpleNamespace(
        manifest_path=tmp_path / "manifest.json",
        agent_id="selected-agent",
        registry_generation_id="generation",
        launch_plan=SimpleNamespace(backend="dsh_web", home_path=Path("/owned/native-home")),
        backend_session=SimpleNamespace(state=SimpleNamespace(web_identity=_identity())),
    )
    monkeypatch.setattr(
        native_refresh, "inspect_native_home_from_manifest", lambda _: _home(**changed)
    )
    with pytest.raises(GatewayError):
        native_refresh.inspect_native_home(controller)


def test_projection_preserves_native_observation_time() -> None:
    """Mapping native evidence cannot silently replace its timestamp with now."""

    raw = _raw()
    observation = native_refresh._observation(_home(), raw)
    assert observation.observed_at_utc == raw["observed_at_utc"]


@pytest.mark.parametrize("field", ["native_settled", "native_ready"])
@pytest.mark.parametrize("outcome", ["already_current", "refreshed"])
def test_confirmed_result_cannot_contradict_native_observation(field: str, outcome: str) -> None:
    """Top-level success cannot erase an explicit unsafe native observation."""

    observation = native_refresh._observation(_home(), _raw(**{field: False}))
    with pytest.raises(ValueError):
        NativeRefreshResultV1.model_validate(
            {
                "method": "noop" if outcome == "already_current" else "native_reload",
                "outcome": outcome,
                "observation": observation,
                "effects": "absent" if outcome == "already_current" else "confirmed",
                "native_settled": True,
                "native_ready": True,
            }
        )


@pytest.mark.parametrize("case", ["empty", "unsupported", "no_future_boundary", "missing_mcp"])
def test_automatic_strategy_requires_qualified_remaining_common_scope(case: str) -> None:
    """A capability boolean alone cannot attest future common discovery."""

    resources = [
        CommonPluginResourceV1(
            kind=kind,
            component="next_invocation",
            boundary="next_turn" if case != "no_future_boundary" else "now",
            supported=case != "unsupported",
            reason="qualified_current_home_loading",
        )
        for kind in ("skills", "mcp")
        if case != "empty" and not (case == "missing_mcp" and kind == "mcp")
    ]
    try:
        observation = CommonPluginObservationV1(home=_home(), resources=resources, automatic=True)
        planned = native_refresh.plan_native_refresh(observation)
    except ValueError:
        return
    assert planned is not None and planned.outcome != "automatic"


def test_automatic_strategy_can_retain_unknown_discovery_at_qualified_future_boundary() -> None:
    """Future discovery qualification does not fabricate a live worker catalog."""

    observation = CommonPluginObservationV1(
        home=_home(),
        automatic=True,
        resources=[
            CommonPluginResourceV1(
                kind=kind,
                component="next_invocation",
                boundary="next_turn",
                supported=True,
                reason="qualified_current_home_loading",
            )
            for kind in ("skills", "mcp")
        ],
    )
    planned = native_refresh.plan_native_refresh(observation)
    assert planned is not None and planned.outcome == "automatic"
    assert planned.observation.freshness == "unknown"
