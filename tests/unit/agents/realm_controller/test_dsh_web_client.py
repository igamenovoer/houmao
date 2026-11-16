"""Verify private Web authentication, origin binding, and mutation no-replay behavior."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import httpx
import pytest

import houmao.agents.realm_controller.backends.dsh_web_client as client_module
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient, DshWebError


@pytest.mark.parametrize(
    "origin",
    [
        "https://127.0.0.1:1234",
        "http://example.com:1234",
        "http://localhost:1234",
        "http://127.0.0.1",
        "http://127.0.0.1:1234/path",
        "http://user:key@127.0.0.1:1234",
        "http://127.0.0.1:1234/?token=private",
    ],
)
def test_client_refuses_unqualified_origins(origin: str) -> None:
    """Reject credentials, non-loopback authorities, and ambiguous native locations."""

    with pytest.raises(DshWebError) as refused:
        DshWebClient.from_connection(origin, launch_token="must-not-send")
    assert refused.value.code == "invalid_origin"
    assert "must-not-send" not in str(refused.value)


def _transport(
    monkeypatch: pytest.MonkeyPatch, failure: str | None = None
) -> tuple[list[str], Mock]:
    """Replace only physical I/O while exercising the real authentication and envelope code."""

    calls: list[str] = []
    socket = Mock()
    real_client = httpx.Client

    def respond(request: httpx.Request) -> httpx.Response:
        """Return native-shaped responses without network or personal credentials."""

        calls.append(request.url.path)
        if request.url.path == "/connect":
            assert request.url.params["interactions"] == "none"
            assert request.url.params["token"] == "private-launch"
            return httpx.Response(
                302,
                headers={
                    "location": "./api/remote.mux",
                    "set-cookie": "native-api=private-cookie; HttpOnly; SameSite=Strict; Path=/",
                },
            )
        assert request.headers["cookie"] == "native-api=private-cookie"
        message = json.loads(request.content)
        assert message["payload"]["protocol_version"] == 1
        method = message["method"].rsplit("/", 1)[-1]
        if method == "prompt" and failure == "lost":
            raise httpx.ReadTimeout("private-launch private-cookie transcript")
        if method == "prompt" and failure == "revoked":
            return httpx.Response(401)
        value: Any = (
            {"protocol_version": 1, "identity": {"native_session_id": None}}
            if method == "describe"
            else None
        )
        return httpx.Response(
            200,
            json={
                "type": "server-response",
                "rpcId": "mismatched" if failure == "envelope" else message["rpcId"],
                "result": {"ok": True, "value": value},
            },
        )

    def new_client(**kwargs: Any) -> httpx.Client:
        """Retain real cookie/HTTP logic with an entirely local transport."""

        assert kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False
        return real_client(transport=httpx.MockTransport(respond), **kwargs)

    def open_socket(uri: str, **kwargs: Any) -> Mock:
        """Verify the socket uses only this separately minted API credential."""

        assert uri == "ws://127.0.0.1:1234/api/remote.mux"
        assert kwargs["additional_headers"] == {"Cookie": "native-api=private-cookie"}
        assert kwargs["origin"] == "http://127.0.0.1:1234"
        assert kwargs["proxy"] is None
        return socket

    monkeypatch.setattr(client_module.httpx, "Client", new_client)
    monkeypatch.setattr(client_module, "connect", open_socket)
    return calls, socket


def test_private_api_credentials_and_socket_have_independent_lifetime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persist a private origin-bound API cookie and close its owned socket exactly once."""

    calls, socket = _transport(monkeypatch)
    credentials = tmp_path / "private/api.json"
    client = DshWebClient.from_connection(
        "http://127.0.0.1:1234", launch_token="private-launch", cookie_file=credentials
    )
    assert client.origin == "http://127.0.0.1:1234"
    assert credentials.stat().st_mode & 0o077 == 0
    assert json.loads(credentials.read_text())["cookies"] == {"native-api": "private-cookie"}
    assert calls == ["/connect", "/houmao/managed/v1/describe"]
    client.close()
    client.close()
    socket.close.assert_called_once()
    with pytest.raises(DshWebError) as closed:
        client.state()
    assert closed.value.code == "connection_unavailable"


@pytest.mark.parametrize(
    "failure,code", [("lost", "outcome_uncertain"), ("revoked", "authentication_failed")]
)
def test_failed_mutation_is_never_retried_or_reconstructed_from_text(
    monkeypatch: pytest.MonkeyPatch, failure: str, code: str
) -> None:
    """A lost response leaves one attempted insertion and permits only explicit receipt reads."""

    calls, _socket = _transport(monkeypatch, failure)
    client = DshWebClient.from_connection("http://127.0.0.1:1234", launch_token="private-launch")
    try:
        with pytest.raises(DshWebError) as failed:
            client.prompt({}, "private prompt", operation_id="operation", deadline_epoch_ms=100)
        assert failed.value.code == code
        assert "private" not in str(failed.value)
        assert calls.count("/houmao/managed/v1/prompt") == 1
        assert client.receipt({}, "operation") is None
        assert calls.count("/houmao/managed/v1/prompt") == 1
    finally:
        client.close()


def test_incompatible_response_closes_the_new_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject an uncorrelated descriptor before exposing the client to runtime control."""

    _calls, socket = _transport(monkeypatch, "envelope")
    with pytest.raises(DshWebError) as failed:
        DshWebClient.from_connection("http://127.0.0.1:1234", launch_token="private-launch")
    assert failed.value.code == "protocol_mismatch"
    socket.close.assert_called_once()


def test_prompt_forwards_only_the_optional_dispatch_permission_reference(tmp_path: Path) -> None:
    """Native admission receives a permission file reference without loading private contents."""

    client = DshWebClient()
    call = Mock(return_value={})
    client.call = call
    permission = tmp_path / "permission.json"
    client.prompt(
        {},
        "input",
        operation_id="operation",
        deadline_epoch_ms=100,
        dispatch_permission_path=permission,
    )
    assert call.call_args.args[1]["dispatch_permission_path"] == str(permission)
    client.prompt({}, "input", operation_id="direct", deadline_epoch_ms=100)
    assert "dispatch_permission_path" not in call.call_args.args[1]
