"""Test read-only dashboard discovery for an owner-local managed tmux terminal."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller import gateway_terminal_pty
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.gateway_web_entry import WEB_ENTER_PATH
from houmao.agents.realm_controller.owner_admission import OwnerAdmissionError
from houmao.gateway.terminal_entry_contracts import TERMINAL_INTERACT_PATH, TERMINAL_VIEW_PATH
from tests.fixtures.gateway_access import (
    FixtureGatewayAccess,
    enroll_fixture_admin,
    fixture_admin_key,
)
from tests.unit.agents.realm_controller.test_gateway_access_http import _runtime


_ORIGIN = "http://127.0.0.1:43123"


@pytest.fixture
def terminal_dashboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gateway_fixture_access: FixtureGatewayAccess
) -> tuple[GatewayServiceRuntime, TestClient, SimpleNamespace, Mock]:
    """Serve the dashboard while making all live terminal effects fail the test."""

    runtime = _runtime(tmp_path)
    target = gateway_fixture_access.target
    manifest = SimpleNamespace(
        agent_name="Local <worker>",
        agent_id=target.owner.agent_id,
        registry_generation_id=target.incarnation,
        mode="tui",
        backend="hermes_tui",
        tmux=object(),
    )
    observe = Mock(return_value=object())
    monkeypatch.setattr(gateway_terminal_pty, "resolve_terminal_target", observe)
    monkeypatch.setattr(runtime, "_verified_owner_manifest", Mock(return_value=manifest))
    side_effect = AssertionError("Dashboard rendering performed a terminal or gateway effect")
    monkeypatch.setattr(gateway_terminal_pty, "run_terminal_stream", Mock(side_effect=side_effect))
    monkeypatch.setattr(runtime, "resolve_web_entry", Mock(side_effect=side_effect))
    monkeypatch.setattr(runtime, "fence_access", Mock(side_effect=side_effect))
    monkeypatch.setattr(runtime, "status", Mock(side_effect=side_effect))
    client = TestClient(create_app(runtime=runtime), base_url=_ORIGIN, client=("127.0.0.1", 45000))
    return runtime, client, manifest, observe


@pytest.mark.parametrize("keyed", [False, True])
def test_dashboard_offers_independent_terminal_and_native_web_actions(
    terminal_dashboard: tuple[GatewayServiceRuntime, TestClient, SimpleNamespace, Mock],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    keyed: bool,
) -> None:
    """A verified Web agent can offer its native UI and supervised tmux console."""

    runtime, client, manifest, observe = terminal_dashboard
    manifest.mode, manifest.backend = "web", "dsh_web"
    monkeypatch.setattr(runtime, "_dashboard_web_available", Mock(return_value=True))
    if keyed:
        key, signer = fixture_admin_key(tmp_path, "dashboard-admin")
        enroll_fixture_admin(client, key, signer)
    endpoint = Mock(wraps=runtime.endpoint_descriptor)
    monkeypatch.setattr(runtime, "endpoint_descriptor", endpoint)

    page = client.get("/")
    assert page.status_code == 200, page.text
    assert f'href="{WEB_ENTER_PATH}">Open agent Web UI</a>' in page.text
    assert f'href="{TERMINAL_VIEW_PATH}">View tmux terminal</a>' in page.text
    assert f'href="{TERMINAL_INTERACT_PATH}">Interact with tmux</a>' in page.text
    assert "Supervisor console" in page.text
    if keyed:
        assert "Sign in with an enrolled administrator key to interact." in page.text
    else:
        assert "The gateway opens the interactive terminal directly." in page.text
    assert "<dt>Tmux terminal availability</dt><dd>Available</dd>" in page.text
    assert "Local &lt;worker&gt;" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert page.headers["referrer-policy"] == "no-referrer"
    assert "#ticket=" not in page.text
    if keyed:
        assert key.principal not in page.text
        assert key.public_key not in page.text
    endpoint.assert_called_once_with(read_only=True)
    observe.assert_called_once_with(manifest, manifest_path=runtime.m_manifest_path)


def test_dashboard_allows_viewing_when_roster_is_unavailable(
    terminal_dashboard: tuple[GatewayServiceRuntime, TestClient, SimpleNamespace, Mock],
    gateway_fixture_access: FixtureGatewayAccess,
) -> None:
    """Owner-local viewer discovery uses terminal authority without a readable roster."""

    _, client, manifest, observe = terminal_dashboard
    manifest.mode, manifest.backend = "headless", "hermes_headless"
    (gateway_fixture_access.private_root / "authorization.sqlite3").unlink()

    page = client.get("/")
    assert page.status_code == 200, page.text
    assert "<dt>Roster mode</dt><dd>Unavailable</dd>" in page.text
    assert f'href="{TERMINAL_VIEW_PATH}"' in page.text
    assert f'href="{TERMINAL_INTERACT_PATH}"' not in page.text
    assert "Gateway administrator policy is unavailable." in page.text
    assert "Headless console" in page.text
    observe.assert_called_once()


@pytest.mark.parametrize("state", ["no-tmux", "stale-tmux", "no-owner", "proxy"])
def test_dashboard_withholds_terminal_actions_when_ineligible(
    terminal_dashboard: tuple[GatewayServiceRuntime, TestClient, SimpleNamespace, Mock],
    state: str,
) -> None:
    """Unavailable or ineligible attachments show safe guidance on the public page."""

    runtime, client, manifest, observe = terminal_dashboard
    if state == "no-tmux":
        manifest.tmux = None
    elif state == "stale-tmux":
        observe.side_effect = gateway_terminal_pty.TerminalUnavailable("/private/socket")
    elif state == "no-owner":
        assert isinstance(runtime._verified_owner_manifest, Mock)
        runtime._verified_owner_manifest.side_effect = OwnerAdmissionError(
            "unavailable", "/private/path"
        )
    page = (
        client.get("https://example.test/", headers={"X-Forwarded-Proto": "https"})
        if state == "proxy"
        else client.get("/")
    )
    assert page.status_code == 200, page.text
    assert f'href="{TERMINAL_VIEW_PATH}"' not in page.text
    assert f'href="{TERMINAL_INTERACT_PATH}"' not in page.text
    expected = {
        "no-tmux": "This agent has no managed tmux terminal.",
        "stale-tmux": "The managed tmux terminal is unavailable.",
        "no-owner": "The current managed agent is unavailable.",
        "proxy": "private TCP forward",
    }
    assert expected[state] in page.text
    assert "/private/" not in page.text
    assert observe.call_count == (1 if state == "stale-tmux" else 0)
