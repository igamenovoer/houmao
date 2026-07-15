"""Tests for unattended provider preparation and native surface probes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon import preflight
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import ProviderName
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    initialize_owned_run_root,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]


@pytest.mark.parametrize("provider", ["claude", "codex", "kimi"])
def test_qualification_presets_are_bare_and_unattended(provider: ProviderName) -> None:
    """Every provider preset requests no skill and unattended prompt policy."""

    preset = (
        _REPO_ROOT
        / "scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/presets"
        / f"long-horizon-{provider}-unattended.yaml"
    )
    payload = yaml.safe_load(preset.read_text(encoding="utf-8"))

    assert payload["tool"] == provider
    assert payload["skills"] == []
    assert payload["launch"]["prompt_mode"] == "unattended"


def test_codex_proxy_projection_uses_port_7990() -> None:
    """Codex receives matching upper- and lower-case proxy variables."""

    environment = preflight.codex_proxy_environment()

    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        assert environment[name] == "http://127.0.0.1:7990"
    assert "127.0.0.1" in environment["NO_PROXY"]


def test_codex_proxy_preflight_fails_closed(monkeypatch) -> None:
    """An unreachable port fails before a Codex provider launch."""

    def fail_connection(*_args, **_kwargs):
        raise OSError("closed")

    monkeypatch.setattr(preflight.socket, "create_connection", fail_connection)

    with pytest.raises(RuntimeError, match="proxy is unreachable"):
        preflight.require_codex_proxy()


def test_confirmation_watchdog_and_allowlist() -> None:
    """The watchdog reports unallowlisted intervention surfaces only."""

    text = "Approval required: allow this command?"

    assert preflight.find_confirmation_violation(visible_text=text) is not None
    assert (
        preflight.find_confirmation_violation(
            visible_text=text,
            allowlist_patterns=("Approval required",),
        )
        is None
    )
    assert preflight.find_confirmation_violation(visible_text="Ready for a prompt") is None


@pytest.mark.parametrize(
    ("provider", "visible_text"),
    [
        ("claude", 'Try "fix typecheck errors"'),
        ("codex", "Find and fix a bug in @filename"),
        ("kimi", "type a message or use /help for commands."),
    ],
)
def test_native_ready_markers(provider: ProviderName, visible_text: str) -> None:
    """Raw provider placeholders establish readiness without tracker state."""

    assert preflight.detect_ready_marker(provider=provider, visible_text=visible_text) is not None


def test_sanitized_manifest_excludes_environment_secrets(tmp_path: Path) -> None:
    """Retained launch metadata contains names and fixed proxy values only."""

    prepared = preflight.PreparedProviderHome(
        provider="codex",
        home_path=tmp_path / "home",
        manifest_path=tmp_path / "manifest.json",
        launch_helper_path=tmp_path / "launch.sh",
        observed_version="1.2.3",
        strategy_id="codex-test",
        launch_command_sha256="a" * 64,
        environment={
            **preflight.codex_proxy_environment(),
            "OPENAI_API_KEY": "secret-canary",
        },
    )

    payload = preflight.sanitized_provider_manifest(prepared=prepared)
    serialized = json.dumps(payload)

    assert "secret-canary" not in serialized
    assert "OPENAI_API_KEY" in payload["environment_names"]
    assert payload["codex_proxy_projection"]["HTTP_PROXY"].endswith(":7990")


def test_disposable_probe_reports_unsupported_model_surface(tmp_path: Path, monkeypatch) -> None:
    """A failed exact `/model` probe is incomplete instead of substituted."""

    paths = _owned_paths(tmp_path=tmp_path)
    launch_helper = tmp_path / "launch.sh"
    launch_helper.write_text("#!/bin/sh\n", encoding="utf-8")
    prepared = preflight.PreparedProviderHome(
        provider="claude",
        home_path=paths.provider_homes_dir / "claude-st-04-a001/home",
        manifest_path=tmp_path / "manifest.json",
        launch_helper_path=launch_helper,
        observed_version="1.2.3",
        strategy_id="claude-test",
        launch_command_sha256="a" * 64,
        environment={},
    )
    monkeypatch.setattr(preflight, "launch_tmux_session", lambda **_kwargs: None)
    monkeypatch.setattr(preflight, "resolve_active_pane_id", lambda **_kwargs: "%1")
    monkeypatch.setattr(
        preflight,
        "_wait_for_native_ready",
        lambda **_kwargs: ('Try "', None),
    )
    monkeypatch.setattr(preflight, "capture_visible_pane_text", lambda **_kwargs: "same")
    monkeypatch.setattr(preflight, "_send_sequence", lambda **_kwargs: None)
    monkeypatch.setattr(preflight, "kill_tmux_session_if_exists", lambda **_kwargs: None)
    monkeypatch.setattr(preflight.time, "sleep", lambda _seconds: None)

    result = preflight.run_disposable_probe(
        paths=paths,
        prepared=prepared,
        project_root=tmp_path,
        require_steering=False,
        require_model_selector=True,
        require_empty_editor_exit=False,
    )

    assert result.status == "incomplete"
    assert result.code == "unsupported_navigation_surface"


def test_sensitive_provider_home_removal_is_owned(tmp_path: Path) -> None:
    """Credential-bearing runtime state is deleted only beneath provider-homes."""

    paths = _owned_paths(tmp_path=tmp_path)
    runtime_root = paths.provider_homes_dir / "codex-st-01-a001"
    home = runtime_root / "homes" / "home-id"
    home.mkdir(parents=True)
    (home / "secret").write_text("canary", encoding="utf-8")
    prepared = preflight.PreparedProviderHome(
        provider="codex",
        home_path=home,
        manifest_path=home / "manifest.json",
        launch_helper_path=home / "launch.sh",
        observed_version="1.2.3",
        strategy_id="codex-test",
        launch_command_sha256="a" * 64,
        environment={},
    )

    preflight.remove_sensitive_provider_home(paths=paths, prepared=prepared)

    assert not runtime_root.exists()


def _owned_paths(*, tmp_path: Path) -> LongHorizonRunPaths:
    """Return one initialized hermetic run tree."""

    repo = tmp_path / "repo"
    paths = LongHorizonRunPaths.from_requested_root(
        repo_root=repo,
        requested_root=Path("tmp/run"),
    )
    initialize_owned_run_root(paths=paths, suite_id="suite")
    return paths
