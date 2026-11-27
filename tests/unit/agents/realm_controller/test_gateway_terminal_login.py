"""Exercise the administrator browser login for terminal interaction."""

from __future__ import annotations

import base64
from dataclasses import replace
import json
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Callable
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller import gateway_terminal_login
from houmao.agents.realm_controller.gateway_terminal_login import register_terminal_login_routes
from houmao.agents.realm_controller.gateway_terminal_pty import TerminalTarget
from houmao.gateway._web_login import TERMINAL_LOGIN_NAMESPACE, WEB_LOGIN_NAMESPACE
from houmao.gateway.access import GatewayAccessPolicy, GatewayGrant
from houmao.gateway.authorization_models import Credential, Principal
from houmao.gateway.roster import remove_admin_key
from houmao.gateway.terminal_entry_contracts import (
    TERMINAL_INTERACT_PATH,
    TERMINAL_LOGIN_CLAIM_PATH,
    TERMINAL_LOGIN_PATH,
    TERMINAL_LOGIN_PROVE_PATH,
    GatewayTerminalEntryTicketV1,
)
from tests.unit.gateway.test_web_login import _keygen, _policy, _stock_sign

_ORIGIN = "http://127.0.0.1:39473"
_ORIGIN_HEADER = {"Origin": _ORIGIN}


def _target(tmp_path: Path) -> TerminalTarget:
    """Supply exact pinned terminal authority without allocating a tmux client."""

    return TerminalTarget(
        agent_id="agent",
        generation="generation",
        runtime_session_id="runtime",
        socket_path=str(tmp_path / "tmux.sock"),
        session_id="$0",
        session_created="1134",
        window_id="@0",
        pane_id="%0",
        pane_pid="2",
        server_pid="1",
        server_started="1133",
        server_birth="birth",
        manifest_path=str(tmp_path / "manifest.json"),
        cols=80,
        rows=24,
    )


def _application(
    *,
    policy: GatewayAccessPolicy,
    resolve_target: Callable[[], TerminalTarget],
    mint_ticket: Callable[[TerminalTarget, GatewayGrant], GatewayTerminalEntryTicketV1],
) -> TestClient:
    """Publish only the owner-local login routes with a recorded ticket callback."""

    app = FastAPI()
    register_terminal_login_routes(
        app,
        issuer=lambda: _ORIGIN,
        listener=lambda: policy.listener_id,
        agent_id="agent",
        resolve_target=resolve_target,
        policy=lambda: policy,
        mint_ticket=mint_ticket,
    )
    return TestClient(app, base_url=_ORIGIN, client=("127.0.0.1", 40126))


def _start(client: TestClient) -> dict[str, str]:
    """Start an attempt on the exact browser origin."""

    response = client.post(TERMINAL_LOGIN_PATH, headers=_ORIGIN_HEADER)
    assert response.status_code == 200
    attempt: dict[str, str] = response.json()
    return attempt


def _challenge(attempt: dict[str, str]) -> bytes:
    """Decode the exact signed challenge bytes from the browser receipt."""

    challenge = attempt["challenge"]
    return base64.urlsafe_b64decode(challenge + "=" * (-len(challenge) % 4))


def _claim_headers(attempt: dict[str, str]) -> dict[str, str]:
    """Return the proof of ownership retained only by the initiating browser."""

    return {**_ORIGIN_HEADER, "X-Houmao-Terminal-Claim": attempt["claim_secret"]}


def test_admin_terminal_login_uses_exact_purpose_and_independent_browser_claim(
    tmp_path: Path,
) -> None:
    """Select the actual enrolled admin even after an eligible default signer."""

    admin = tmp_path / "admin"
    ordinary = tmp_path / "ordinary"
    policy = _policy(tmp_path, _keygen(admin))
    credential = Credential(principal_id="ordinary", public_key=_keygen(ordinary))
    policy.store.update(
        lambda current: current.model_copy(
            update={
                "default_permission_group": "agent-admin",
                "principals": (
                    *current.principals,
                    Principal(principal_id="ordinary", kind="operator", label="Ordinary"),
                ),
                "credentials": (*current.credentials, credential),
            }
        ),
        actor="owner",
        action="test.terminal.enroll",
    )
    target = _target(tmp_path)
    ticket = GatewayTerminalEntryTicketV1(
        url=f"{_ORIGIN}{TERMINAL_INTERACT_PATH}#ticket=abc",
        mode="interact",
        expires_at_utc="2026-11-27T14:03:00+00:00",
    )
    mint = Mock(return_value=ticket)
    client = _application(policy=policy, resolve_target=lambda: target, mint_ticket=mint)

    page = client.get(TERMINAL_LOGIN_PATH)
    assert page.status_code == 200
    assert "Houmao Terminal Admin Login" in page.text
    assert f'data-entry-path="{TERMINAL_INTERACT_PATH}"' in page.text
    assert "nonce-" in page.headers["Content-Security-Policy"]
    assert page.headers["Cache-Control"] == "no-store"
    assert client.post(TERMINAL_LOGIN_PATH).status_code == 403
    assert (
        client.post(
            TERMINAL_LOGIN_PATH, headers={**_ORIGIN_HEADER, "Houmao-Relay": "not-direct"}
        ).status_code
        == 403
    )

    attempt = _start(client)
    message = _challenge(attempt)
    proof_path = TERMINAL_LOGIN_PROVE_PATH.format(attempt_id=attempt["attempt_id"])
    claim_path = TERMINAL_LOGIN_CLAIM_PATH.format(attempt_id=attempt["attempt_id"])
    challenge = json.loads(message)
    assert challenge["purpose"] == TERMINAL_LOGIN_NAMESPACE
    assert challenge["mode"] == "interact"
    assert challenge["path"] == proof_path
    assert challenge["generation"] == target.generation
    assert target.socket_path.encode() not in message

    assert client.post(claim_path, headers=_ORIGIN_HEADER).status_code == 403
    assert client.post(claim_path, headers=_claim_headers(attempt)).status_code == 202
    assert (
        client.post(
            proof_path, content=_stock_sign(admin, message, WEB_LOGIN_NAMESPACE)
        ).status_code
        == 401
    )
    ordinary_proof = _stock_sign(ordinary, message, TERMINAL_LOGIN_NAMESPACE)
    assert client.post(proof_path, content=ordinary_proof).status_code == 403
    proof = ordinary_proof + _stock_sign(admin, message, TERMINAL_LOGIN_NAMESPACE)
    approved = client.post(proof_path, content=proof)
    assert approved.json() == {"status": "approved"}
    assert client.post(proof_path, content=proof).status_code == 410
    receipt = client.post(claim_path, headers=_claim_headers(attempt))
    assert receipt.json() == ticket.model_dump(mode="json")
    assert client.post(claim_path, headers=_claim_headers(attempt)).status_code == 410
    mint.assert_called_once()
    observed_target, grant = mint.call_args.args
    assert observed_target == target
    assert grant.basis == "admin"
    assert grant.actor.principal_id == "operator"


@pytest.mark.parametrize("cause", ["expiry", "last admin", "terminal replacement"])
def test_terminal_login_claim_fails_after_admitted_authority_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    """Prevent one admitted login from following a new epoch, incarnation, or deadline."""

    admin = tmp_path / "admin"
    policy = _policy(tmp_path, _keygen(admin))
    resolve = Mock(return_value=_target(tmp_path))
    mint = Mock()
    clock = Mock(return_value=time.monotonic())
    monkeypatch.setattr(gateway_terminal_login, "time", SimpleNamespace(monotonic=clock))
    client = _application(policy=policy, resolve_target=resolve, mint_ticket=mint)
    attempt = _start(client)
    proof_path = TERMINAL_LOGIN_PROVE_PATH.format(attempt_id=attempt["attempt_id"])
    claim_path = TERMINAL_LOGIN_CLAIM_PATH.format(attempt_id=attempt["attempt_id"])
    proof = _stock_sign(admin, _challenge(attempt), TERMINAL_LOGIN_NAMESPACE)
    assert client.post(proof_path, content=proof).status_code == 200
    if cause == "expiry":
        clock.return_value += 121
    elif cause == "last admin":
        key_id = policy.store.snapshot().credentials[0].key_id
        policy.store.update(
            lambda state: remove_admin_key(state, key_id), actor="owner", action="admin.key.remove"
        )
    else:
        resolve.return_value = replace(resolve.return_value, server_birth="new-incarnation")
    assert client.post(claim_path, headers=_claim_headers(attempt)).status_code == 410
    mint.assert_not_called()
