"""Unit tests for agent-identity parsing and normalization helpers."""

from __future__ import annotations

import pytest

from houmao.agents.realm_controller.agent_identity import (
    derive_tmux_session_name,
    is_path_like_agent_identity,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.errors import SessionManifestError


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("tmp/agents-runtime/sessions/cao_rest/s1.json", True),
        (r"tmp\\agents-runtime\\sessions\\cao_rest\\s1.json", True),
        ("relative/path/no-extension", True),
        ("AGENTSYS-gpu", False),
        ("gpu", False),
    ],
)
def test_is_path_like_agent_identity(value: str, expected: bool) -> None:
    assert is_path_like_agent_identity(value) is expected


def test_normalize_agent_identity_without_prefix() -> None:
    normalized = normalize_agent_identity_name("gpu")
    assert normalized.canonical_name == "AGENTSYS-gpu"
    assert normalized.name_portion == "gpu"
    assert normalized.warnings == ()


def test_normalize_agent_identity_preserves_exact_prefix() -> None:
    normalized = normalize_agent_identity_name("AGENTSYS-gpu")
    assert normalized.canonical_name == "AGENTSYS-gpu"
    assert normalized.name_portion == "gpu"


def test_normalize_agent_identity_warns_on_inexact_prefix() -> None:
    normalized = normalize_agent_identity_name("agentsys-gpu")
    assert normalized.canonical_name == "AGENTSYS-agentsys-gpu"
    assert len(normalized.warnings) == 1
    assert "does not start with exact `AGENTSYS-`" in normalized.warnings[0]


@pytest.mark.parametrize("value", ["AGENTSYS", "AGENTSYS-AGENTSYS"])
def test_reserved_agentsys_token_is_rejected(value: str) -> None:
    with pytest.raises(SessionManifestError, match="AGENTSYS"):
        normalize_agent_identity_name(value)


@pytest.mark.parametrize("value", ["foo-AGENTSYS-bar", "foo_AGENTSYS_bar"])
def test_standalone_agentsys_token_is_rejected(value: str) -> None:
    with pytest.raises(SessionManifestError, match="standalone token"):
        normalize_agent_identity_name(value)


@pytest.mark.parametrize("value", ["MYAGENTSYS", "AGENTSYSFOO"])
def test_agentsys_substring_inside_alnum_run_is_allowed(value: str) -> None:
    normalized = normalize_agent_identity_name(value)
    assert normalized.canonical_name == f"AGENTSYS-{value}"


def test_derive_tmux_session_name_uses_default_agent_id_prefix_length() -> None:
    assert (
        derive_tmux_session_name(
            canonical_agent_name="AGENTSYS-gpu",
            agent_id="270b8738f2f97092e572b73d19e6f923",
        )
        == "AGENTSYS-gpu-270b87"
    )


def test_derive_tmux_session_name_extends_prefix_until_unique() -> None:
    assert (
        derive_tmux_session_name(
            canonical_agent_name="AGENTSYS-gpu",
            agent_id="270b8738f2f97092e572b73d19e6f923",
            occupied_session_names={"AGENTSYS-gpu-270b87"},
        )
        == "AGENTSYS-gpu-270b873"
    )


def test_derive_tmux_session_name_uses_explicit_agent_id_override() -> None:
    assert (
        derive_tmux_session_name(
            canonical_agent_name="AGENTSYS-gpu",
            agent_id="deadbeefcafefeed",
        )
        == "AGENTSYS-gpu-deadbe"
    )


def test_derive_tmux_session_name_fails_when_full_agent_id_still_collides() -> None:
    with pytest.raises(SessionManifestError, match="Failed to derive a unique tmux session name"):
        derive_tmux_session_name(
            canonical_agent_name="AGENTSYS-gpu",
            agent_id="deadbe",
            occupied_session_names={"AGENTSYS-gpu-deadbe"},
        )
