"""Keep refresh requests and freshness claims within their public authority."""

from typing import Any

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller import native_refresh
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    CommonPluginResourceV1,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
    native_refresh_status_code,
)


def _home() -> NativeHomeV1:
    """Select an agent home independently of the invoking process environment."""

    return NativeHomeV1(agent_id="selected", backend="dsh_web", tool="dsh", home_dir="/native/home")


def _current() -> CommonPluginObservationV1:
    """Attest complete current common scope, including an empty MCP declaration set."""

    return CommonPluginObservationV1(
        home=_home(),
        resources=[
            CommonPluginResourceV1(
                kind=kind,
                component="catalog" if kind == "skills" else "declarations",
                freshness="current",
                boundary="now",
                supported=True,
                complete=True,
            )
            for kind in ("skills", "mcp")
        ],
        freshness="current",
        coverage_complete=True,
        native_reload=True,
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"restart": True},
        {"force": True},
        {"force_restart": False},
        {"skills": [{"name": "replacement", "body": "private"}]},
        {"mcp": {"server": {"command": "replacement"}}},
        {"home_dir": "/other"},
        {"agent_id": "other"},
        {"identity": {"generation": "other"}},
        {"unknown": None},
    ],
)
def test_refresh_request_has_no_install_restart_or_identity_authority(
    extra: dict[str, Any],
) -> None:
    """The request cannot substitute content, an execution target, or a restart."""

    with pytest.raises(ValidationError):
        NativeRefreshRequestV1.model_validate(extra)


@pytest.mark.parametrize("timeout", [0, -1, 121, float("nan"), float("inf"), "30", True, None])
def test_refresh_request_requires_finite_bounded_numeric_deadline(timeout: object) -> None:
    """Invalid deadlines fail before any native handoff."""

    with pytest.raises(ValidationError):
        NativeRefreshRequestV1.model_validate({"timeout_seconds": timeout})


@pytest.mark.parametrize(
    "changes",
    [
        {"coverage_complete": False},
        {"resources": []},
        {"scope": "native-special-plugin"},
        {"native_inventory": []},
    ],
)
def test_common_current_requires_complete_declared_scope(changes: dict[str, Any]) -> None:
    """An aggregate current claim cannot exceed the supported common scope."""

    with pytest.raises(ValidationError):
        CommonPluginObservationV1.model_validate({**_current().model_dump(), **changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"freshness": "unknown"},
        {"freshness": "pending"},
        {"complete": False},
        {"supported": False},
    ],
)
def test_one_unproven_common_component_prevents_aggregate_current(changes: dict[str, Any]) -> None:
    """MCP connection health or a cached catalog cannot replace freshness evidence."""

    payload = _current().model_dump()
    payload["resources"][1].update(changes)
    with pytest.raises(ValidationError):
        CommonPluginObservationV1.model_validate(payload)


def test_optional_unknown_implementation_does_not_expand_current_scope() -> None:
    """A current declaration set can explicitly retain unknown implementation revisions."""

    payload = _current().model_dump()
    payload["resources"].append(
        CommonPluginResourceV1(
            kind="mcp", component="implementation", required=False, reason="revision_unobservable"
        ).model_dump()
    )
    observation = CommonPluginObservationV1.model_validate(payload)
    result = native_refresh.plan_native_refresh(observation)
    assert result is not None and result.outcome == "already_current"
    assert result.observation.resources[-1].freshness == "unknown"


def test_unhealthy_current_resource_and_broad_native_pending_do_not_invent_staleness() -> None:
    """Known current common material remains distinct from connection and native-only state."""

    raw = {
        **_current().model_dump(exclude={"home"}),
        "identity": {},
        "native_special_pending": [{"reason": "host_module_requires_restart"}],
    }
    raw["resources"][1]["health"] = "disconnected"
    observation = native_refresh._observation(_home(), raw)
    result = native_refresh.plan_native_refresh(observation)
    assert observation.freshness == "current"
    assert observation.resources[1].health == "disconnected"
    assert result is not None and result.outcome == "already_current"


def test_unknown_coverage_never_becomes_already_current() -> None:
    """A missing backend proof produces an explicit unsupported observation."""

    result = native_refresh.plan_native_refresh(native_refresh.unknown_common_observation(_home()))
    assert result is not None and result.outcome == "unsupported"
    assert result.observation.freshness == "unknown"


def test_observation_exposes_names_without_configuration_bodies_or_environment() -> None:
    """The projection strips private native inputs instead of serializing its raw evidence."""

    raw = {
        **_current().model_dump(exclude={"home"}),
        "identity": {},
        "environment": {"PRIVATE_TOKEN": "secret-token"},
    }
    raw["resources"][0]["inventory"] = [
        {"name": "public-skill", "body": "secret-body", "path": "/private/skill"}
    ]
    raw["resources"][1]["inventory"] = [
        {"name": "public-mcp", "env": {"PRIVATE_TOKEN": "secret-token"}, "args": ["private-arg"]}
    ]
    observation = native_refresh._observation(_home(), raw)
    text = observation.model_dump_json()
    assert "public-skill" in text and "public-mcp" in text
    for private in (
        "secret-token",
        "secret-body",
        "/private/skill",
        "private-arg",
        "PRIVATE_TOKEN",
    ):
        assert private not in text


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        ("already_current", 200),
        ("refreshed", 200),
        ("partial", 503),
        ("restart_required", 409),
        ("busy", 409),
        ("unsupported", 501),
        ("failed", 503),
        ("outcome_unknown", 503),
        ("unavailable", 503),
    ],
)
def test_http_outcomes_retain_typed_common_and_native_evidence(outcome: str, expected: int) -> None:
    """Clients can distinguish operation refusal from a normal unknown observation."""

    result = NativeRefreshResultV1.model_validate(
        {
            "method": "noop" if outcome == "already_current" else "native_reload",
            "outcome": outcome,
            "observation": _current(),
            "effects": "absent" if outcome == "already_current" else "partial",
        }
    )
    assert native_refresh_status_code(result) == expected
