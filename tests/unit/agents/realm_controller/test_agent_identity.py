"""Unit tests for agent-identity parsing and normalization helpers."""

from __future__ import annotations

import pytest

from houmao.agents.realm_controller.agent_identity import (
    derive_tmux_session_name,
    is_path_like_agent_identity,
    normalize_agent_identity_name,
    normalize_user_managed_agent_name,
)
from houmao.agents.realm_controller.errors import SessionManifestError


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("tmp/agents-runtime/sessions/cao_rest/s1.json", True),
        (r"tmp\\agents-runtime\\sessions\\cao_rest\\s1.json", True),
        ("relative/path/no-extension", True),
        ("HOUMAO-gpu", False),
        ("gpu", False),
    ],
)
def test_is_path_like_agent_identity(value: str, expected: bool) -> None:
    assert is_path_like_agent_identity(value) is expected


def test_normalize_agent_identity_without_prefix() -> None:
    normalized = normalize_agent_identity_name("gpu")
    assert normalized.canonical_name == "HOUMAO-gpu"
    assert normalized.name_portion == "gpu"
    assert normalized.warnings == ()


def test_normalize_agent_identity_preserves_exact_prefix() -> None:
    normalized = normalize_agent_identity_name("HOUMAO-gpu")
    assert normalized.canonical_name == "HOUMAO-gpu"
    assert normalized.name_portion == "gpu"


def test_normalize_agent_identity_warns_on_inexact_prefix() -> None:
    normalized = normalize_agent_identity_name("houmao-gpu")
    assert normalized.canonical_name == "HOUMAO-houmao-gpu"
    assert len(normalized.warnings) == 1
    assert "does not start with exact `HOUMAO-`" in normalized.warnings[0]


@pytest.mark.parametrize("value", ["HOUMAO", "HOUMAO-HOUMAO"])
def test_reserved_agentsys_token_is_rejected(value: str) -> None:
    with pytest.raises(SessionManifestError, match="HOUMAO"):
        normalize_agent_identity_name(value)


@pytest.mark.parametrize("value", ["foo-HOUMAO-bar", "foo_HOUMAO_bar"])
def test_standalone_agentsys_token_is_rejected(value: str) -> None:
    with pytest.raises(SessionManifestError, match="standalone token"):
        normalize_agent_identity_name(value)


@pytest.mark.parametrize("value", ["MYAGENTSYS", "AGENTSYSFOO"])
def test_agentsys_substring_inside_alnum_run_is_allowed(value: str) -> None:
    normalized = normalize_agent_identity_name(value)
    assert normalized.canonical_name == f"HOUMAO-{value}"


@pytest.mark.parametrize("value", ["HOUMAO-gpu", "houmao-gpu", "HOUMAO_gpu"])
def test_normalize_user_managed_agent_name_rejects_reserved_leading_namespace(value: str) -> None:
    with pytest.raises(SessionManifestError, match="raw creation-time name"):
        normalize_user_managed_agent_name(value)


@pytest.mark.parametrize("value", ["AGENT-SYS-gpu", "gpu-HOUMAO", "AGENTSYS123"])
def test_normalize_user_managed_agent_name_allows_non_reserved_occurrences(value: str) -> None:
    assert normalize_user_managed_agent_name(value) == value


def test_derive_tmux_session_name_uses_canonical_name_plus_epoch_milliseconds() -> None:
    assert (
        derive_tmux_session_name(
            canonical_agent_name="HOUMAO-gpu",
            launch_epoch_ms=1760000123456,
        )
        == "HOUMAO-gpu-1760000123456"
    )


def test_derive_tmux_session_name_fails_explicitly_on_generated_name_conflict() -> None:
    with pytest.raises(SessionManifestError, match="already in use"):
        derive_tmux_session_name(
            canonical_agent_name="HOUMAO-gpu",
            launch_epoch_ms=1760000123456,
            occupied_session_names={"HOUMAO-gpu-1760000123456"},
        )
