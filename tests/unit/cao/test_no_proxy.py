from __future__ import annotations

import os

import pytest

from gig_agents.cao.no_proxy import (
    LOOPBACK_NO_PROXY_ENTRIES,
    PRESERVE_NO_PROXY_ENV_VAR,
    inject_loopback_no_proxy_env,
    inject_loopback_no_proxy_env_for_cao_base_url,
    is_supported_loopback_cao_base_url,
    scoped_loopback_no_proxy_for_cao_base_url,
)


def test_is_supported_loopback_cao_base_url_accepts_supported_values() -> None:
    assert is_supported_loopback_cao_base_url("http://localhost:9889")
    assert is_supported_loopback_cao_base_url("http://127.0.0.1:9889/")
    assert is_supported_loopback_cao_base_url("  http://localhost:9889  ")


def test_is_supported_loopback_cao_base_url_rejects_non_loopback_values() -> None:
    assert not is_supported_loopback_cao_base_url("http://cao.internal:9889")
    assert not is_supported_loopback_cao_base_url("https://localhost:9889")
    assert not is_supported_loopback_cao_base_url("not-a-url")


def test_inject_loopback_no_proxy_env_merges_and_dedupes() -> None:
    env = {
        "NO_PROXY": "corp.internal,LOCALHOST",
        "no_proxy": "localhost,service.local",
    }

    applied = inject_loopback_no_proxy_env(env)

    assert applied is True
    merged = env["NO_PROXY"].split(",")
    assert "corp.internal" in merged
    assert "LOCALHOST" in merged
    assert "service.local" in merged
    assert "localhost" not in merged
    merged_lower = {token.lower() for token in merged}
    for token in LOOPBACK_NO_PROXY_ENTRIES:
        assert token.lower() in merged_lower
    assert env["no_proxy"] == env["NO_PROXY"]


def test_inject_loopback_no_proxy_env_respects_preserve_mode() -> None:
    env = {
        PRESERVE_NO_PROXY_ENV_VAR: "1",
        "NO_PROXY": "corp.internal",
    }

    applied = inject_loopback_no_proxy_env(env)

    assert applied is False
    assert env["NO_PROXY"] == "corp.internal"
    assert "no_proxy" not in env


def test_inject_loopback_no_proxy_env_for_base_url_is_loopback_scoped() -> None:
    loopback_env = {"NO_PROXY": "corp.internal"}
    remote_env = {"NO_PROXY": "corp.internal"}

    applied_loopback = inject_loopback_no_proxy_env_for_cao_base_url(
        loopback_env,
        base_url="http://localhost:9889",
    )
    applied_remote = inject_loopback_no_proxy_env_for_cao_base_url(
        remote_env,
        base_url="http://cao.internal:9889",
    )

    assert applied_loopback is True
    assert "127.0.0.1" in loopback_env["NO_PROXY"].split(",")
    assert applied_remote is False
    assert remote_env["NO_PROXY"] == "corp.internal"
    assert "no_proxy" not in remote_env


def test_scoped_loopback_no_proxy_for_cao_base_url_restores_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    with scoped_loopback_no_proxy_for_cao_base_url("http://localhost:9889") as applied:
        assert applied is True
        assert "localhost" in (os.environ.get("NO_PROXY") or "")
        assert os.environ.get("no_proxy") == os.environ.get("NO_PROXY")

    assert os.environ.get("NO_PROXY") == "corp.internal"
    assert os.environ.get("no_proxy") is None


def test_scoped_loopback_no_proxy_for_cao_base_url_propagates_errors() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with scoped_loopback_no_proxy_for_cao_base_url("http://localhost:9889"):
            raise RuntimeError("boom")
