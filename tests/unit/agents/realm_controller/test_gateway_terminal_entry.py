"""Exercise gateway terminal admission with the retained authorization store."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import WebSocket
from fastapi.testclient import TestClient
from httpx import Response
import pytest
from starlette.websockets import WebSocketDisconnect

import houmao.agents.realm_controller.gateway_terminal_entry as terminal_entry
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.gateway_terminal_pty import TerminalTarget
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    GatewayGrant,
)
from houmao.gateway.terminal_entry_contracts import (
    TERMINAL_INTERACT_STREAM_PATH,
    TERMINAL_INTERACT_TICKET_PATH,
    TERMINAL_VIEW_STREAM_PATH,
    TERMINAL_VIEW_TICKET_PATH,
)
from tests.fixtures.gateway_access import (
    FixtureProofAuth,
    enroll_fixture_admin,
    enroll_fixture_caller,
    fixture_admin_key,
    self_fixture_auth,
)
from tests.unit.agents.realm_controller.test_gateway_support import _seed_headless_gateway_root
from tests.unit.agents.realm_controller.test_gateway_terminal_login import _target

pytestmark = pytest.mark.usefixtures("gateway_fixture_access")


@pytest.fixture
def gateway_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[GatewayServiceRuntime, TestClient, list[TerminalTarget], list[bool]]:
    """Use a real gateway app and policy with an inert, revalidating PTY stream."""

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=_seed_headless_gateway_root(tmp_path, tool="claude"),
        host="127.0.0.1",
        port=43123,
    )
    runtime.prepare_access()
    authority = runtime._access_target()
    targets = [
        replace(
            _target(tmp_path), agent_id=authority.owner.agent_id, generation=authority.incarnation
        )
    ]
    calls: list[bool] = []
    monkeypatch.setattr(runtime, "_resolve_terminal_entry_target", lambda: targets[0])

    async def relay(
        websocket: WebSocket,
        target: TerminalTarget,
        *,
        interact: bool,
        check_current: Callable[[], None],
    ) -> None:
        """Represent one attach client and revalidate at each requested handoff."""

        calls.append(interact)
        assert target == targets[0]
        await websocket.send_bytes(b"attached")
        while (await websocket.receive())["type"] != "websocket.disconnect":
            check_current()
            await websocket.send_bytes(b"current")

    monkeypatch.setattr(terminal_entry, "run_terminal_stream", relay)
    client = TestClient(
        create_app(runtime=runtime),
        base_url=runtime.owner_connect_url,
        client=("127.0.0.1", 50100),
    )
    return runtime, client, targets, calls


def _grant(response: Response) -> dict[str, str]:
    """Extract the first-frame bearer from a successful ticket response."""

    assert response.status_code == 200, response.text
    fragment = urlsplit(response.json()["url"]).fragment
    assert fragment.startswith("ticket=")
    return {"type": "grant", "ticket": fragment.removeprefix("ticket=")}


def test_keyed_gateway_views_anonymously_but_only_enrolled_admins_get_interaction(
    gateway_terminal: tuple[GatewayServiceRuntime, TestClient, list[TerminalTarget], list[bool]],
    tmp_path: Path,
) -> None:
    """Exercise both routes with open, default, self, and exact admin decisions."""

    runtime, client, _, calls = gateway_terminal
    assert _grant(client.post(TERMINAL_INTERACT_TICKET_PATH))["type"] == "grant"
    assert client.post(TERMINAL_VIEW_TICKET_PATH).status_code == 200

    administrator, admin_key = fixture_admin_key(tmp_path, "terminal-admin")
    enroll_fixture_admin(client, administrator, admin_key)
    ordinary, ordinary_key = fixture_admin_key(tmp_path, "terminal-ordinary")
    enroll_fixture_caller(runtime, ordinary, permissions=())
    assert (
        client.put(
            "/v1/admin/default-permission-group",
            json={"group": "agent-admin"},
            auth=FixtureProofAuth(admin_key),
        ).status_code
        == 200
    )
    assert (
        client.post(TERMINAL_INTERACT_TICKET_PATH, auth=FixtureProofAuth(ordinary_key)).status_code
        == 403
    )
    assert (
        client.post(TERMINAL_INTERACT_TICKET_PATH, auth=self_fixture_auth(runtime)).status_code
        == 403
    )

    view = _grant(client.post(TERMINAL_VIEW_TICKET_PATH))
    admin = _grant(client.post(TERMINAL_INTERACT_TICKET_PATH, auth=FixtureProofAuth(admin_key)))
    origin = {"Origin": runtime.owner_connect_url}
    ws_origin = runtime.owner_connect_url.replace("http:", "ws:", 1)
    with client.websocket_connect(
        f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=origin
    ) as watcher:
        watcher.send_json(view)
        assert watcher.receive_bytes() == b"attached"
        with client.websocket_connect(
            f"{ws_origin}{TERMINAL_INTERACT_STREAM_PATH}", headers=origin
        ) as terminal:
            terminal.send_json(admin)
            assert terminal.receive_bytes() == b"attached"
            removed = client.delete(
                f"/v1/admin/keys/{administrator.key_id}", auth=FixtureProofAuth(admin_key)
            )
            assert removed.status_code == 204
            terminal.send_text("check")
            with pytest.raises(WebSocketDisconnect) as ended:
                terminal.receive_bytes()
            assert ended.value.code == 1008
        watcher.send_text("check")
        assert watcher.receive_bytes() == b"current"
    assert calls == [False, True]


def test_open_gateway_requires_valid_transport_and_policy_for_interaction(
    gateway_terminal: tuple[GatewayServiceRuntime, TestClient, list[TerminalTarget], list[bool]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow the open role and keep proof and owner-local checks authoritative."""

    runtime, client, _, calls = gateway_terminal
    ordinary, signer = fixture_admin_key(tmp_path, "enrolled-caller")
    enroll_fixture_caller(runtime, ordinary, permissions=())
    assert (
        client.post(TERMINAL_INTERACT_TICKET_PATH, auth=FixtureProofAuth(signer)).status_code == 200
    )
    assert (
        client.post(
            TERMINAL_INTERACT_TICKET_PATH,
            headers={CHALLENGE_HEADER: "invalid", SIGNATURE_HEADER: "invalid"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            TERMINAL_INTERACT_TICKET_PATH, headers={"Origin": "http://other.example"}
        ).status_code
        == 403
    )

    def unavailable() -> None:
        """Represent a retained policy that cannot be verified."""

        raise GatewayAccessError(503, "policy_unavailable")

    monkeypatch.setattr(runtime._require_access_policy().store, "snapshot", unavailable)
    assert client.post(TERMINAL_INTERACT_TICKET_PATH).status_code == 503
    assert client.post(TERMINAL_VIEW_TICKET_PATH).status_code == 200
    assert calls == []


def test_first_enrollment_during_open_issuance_refuses_the_ticket(
    gateway_terminal: tuple[GatewayServiceRuntime, TestClient, list[TerminalTarget], list[bool]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Close open issuance when the roster becomes keyed between authority checks."""

    runtime, client, _, calls = gateway_terminal
    administrator, signer = fixture_admin_key(tmp_path, "first-admin")
    policy = runtime._require_access_policy()
    original_check = policy.require_terminal_interaction
    enrolled = False

    def enroll_after_first_check(grant: GatewayGrant) -> None:
        """Enroll the first key immediately after validating the original open decision."""

        nonlocal enrolled
        original_check(grant)
        if not enrolled:
            enroll_fixture_admin(client, administrator, signer)
            enrolled = True

    monkeypatch.setattr(policy, "require_terminal_interaction", enroll_after_first_check)
    response = client.post(TERMINAL_INTERACT_TICKET_PATH)
    assert enrolled
    assert response.status_code == 403
    assert "url" not in response.json()
    assert calls == []


def test_open_interaction_ends_with_its_roster_epoch(
    gateway_terminal: tuple[GatewayServiceRuntime, TestClient, list[TerminalTarget], list[bool]],
    tmp_path: Path,
) -> None:
    """Fence existing streams and pending tickets to the epoch that admitted them."""

    runtime, client, _, calls = gateway_terminal
    active = _grant(client.post(TERMINAL_INTERACT_TICKET_PATH))
    pending = _grant(client.post(TERMINAL_INTERACT_TICKET_PATH))
    old_epoch = _grant(client.post(TERMINAL_INTERACT_TICKET_PATH))
    view = _grant(client.post(TERMINAL_VIEW_TICKET_PATH))
    administrator, signer = fixture_admin_key(tmp_path, "first-admin")
    origin = {"Origin": runtime.owner_connect_url}
    ws_origin = runtime.owner_connect_url.replace("http:", "ws:", 1)
    interact_url = f"{ws_origin}{TERMINAL_INTERACT_STREAM_PATH}"

    with client.websocket_connect(
        f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=origin
    ) as watcher:
        watcher.send_json(view)
        assert watcher.receive_bytes() == b"attached"
        with client.websocket_connect(interact_url, headers=origin) as terminal:
            terminal.send_json(active)
            assert terminal.receive_bytes() == b"attached"
            enroll_fixture_admin(client, administrator, signer)
            terminal.send_text("check")
            with pytest.raises(WebSocketDisconnect) as ended:
                terminal.receive_bytes()
            assert ended.value.code == 1008
        with client.websocket_connect(interact_url, headers=origin) as terminal:
            terminal.send_json(pending)
            with pytest.raises(WebSocketDisconnect):
                terminal.receive_bytes()

        removed = client.delete(
            f"/v1/admin/keys/{administrator.key_id}", auth=FixtureProofAuth(signer)
        )
        assert removed.status_code == 204
        with client.websocket_connect(interact_url, headers=origin) as terminal:
            terminal.send_json(old_epoch)
            with pytest.raises(WebSocketDisconnect):
                terminal.receive_bytes()
        fresh = _grant(client.post(TERMINAL_INTERACT_TICKET_PATH))
        with client.websocket_connect(interact_url, headers=origin) as terminal:
            terminal.send_json(fresh)
            assert terminal.receive_bytes() == b"attached"
        watcher.send_text("check")
        assert watcher.receive_bytes() == b"current"
    assert calls == [False, True, True]


def test_terminal_rejects_wrong_origin_mode_replay_and_replaced_target_before_pty(
    gateway_terminal: tuple[GatewayServiceRuntime, TestClient, list[TerminalTarget], list[bool]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fence the transport and one-time bearer before any terminal effect."""

    runtime, client, targets, calls = gateway_terminal
    grant = _grant(client.post(TERMINAL_VIEW_TICKET_PATH))
    origin = {"Origin": runtime.owner_connect_url}
    ws_origin = runtime.owner_connect_url.replace("http:", "ws:", 1)
    for headers in (
        {},
        {"Origin": "http://other.example"},
        {**origin, "X-Forwarded-For": "127.0.0.1"},
    ):
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=headers),
        ):
            pytest.fail("Unexpected WebSocket upgrade")
    with client.websocket_connect(
        f"{ws_origin}{TERMINAL_INTERACT_STREAM_PATH}", headers=origin
    ) as terminal:
        terminal.send_json(grant)
        with pytest.raises(WebSocketDisconnect):
            terminal.receive_bytes()
    assert calls == []

    with client.websocket_connect(
        f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=origin
    ) as watcher:
        watcher.send_json(grant)
        assert watcher.receive_bytes() == b"attached"
    with client.websocket_connect(
        f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=origin
    ) as watcher:
        watcher.send_json(grant)
        with pytest.raises(WebSocketDisconnect):
            watcher.receive_bytes()

    restart_grant = _grant(client.post(TERMINAL_VIEW_TICKET_PATH))
    with monkeypatch.context() as replacement:
        replacement.setattr(runtime, "m_presence_id", "replacement-listener")
        with client.websocket_connect(
            f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=origin
        ) as watcher:
            watcher.send_json(restart_grant)
            with pytest.raises(WebSocketDisconnect):
                watcher.receive_bytes()

    with monkeypatch.context() as expired:
        expired.setattr(terminal_entry, "_TICKET_SECONDS", 0)
        expired_grant = _grant(client.post(TERMINAL_VIEW_TICKET_PATH))
    with client.websocket_connect(
        f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=origin
    ) as watcher:
        watcher.send_json(expired_grant)
        with pytest.raises(WebSocketDisconnect):
            watcher.receive_bytes()

    replacement_grant = _grant(client.post(TERMINAL_VIEW_TICKET_PATH))
    targets[0] = replace(targets[0], generation="new-generation")
    with client.websocket_connect(
        f"{ws_origin}{TERMINAL_VIEW_STREAM_PATH}", headers=origin
    ) as watcher:
        watcher.send_json(replacement_grant)
        with pytest.raises(WebSocketDisconnect):
            watcher.receive_bytes()
    assert calls == [False]


def test_anonymous_ticket_load_cannot_exhaust_enrolled_administrator_capacity(
    gateway_terminal: tuple[GatewayServiceRuntime, TestClient, list[TerminalTarget], list[bool]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep public viewing capacity independent from interactive access."""

    _, client, _, _ = gateway_terminal
    monkeypatch.setattr(terminal_entry, "_MAX_TICKETS", 1)
    administrator, admin_key = fixture_admin_key(tmp_path, "terminal-admin")
    enroll_fixture_admin(client, administrator, admin_key)
    assert client.post(TERMINAL_VIEW_TICKET_PATH).status_code == 200
    assert client.post(TERMINAL_VIEW_TICKET_PATH).status_code == 429
    assert (
        client.post(TERMINAL_INTERACT_TICKET_PATH, auth=FixtureProofAuth(admin_key)).status_code
        == 200
    )
