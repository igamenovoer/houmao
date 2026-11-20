"""Verify private Web authentication, origin binding, and mutation no-replay behavior."""

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

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
        assert request.headers["cookie"] == "native-api=private-cookie"
        message = json.loads(request.content)
        assert message["payload"]["protocol_version"] == 1
        method = message["method"].rsplit("/", 1)[-1]
        if method == "prompt" and failure == "lost":
            raise httpx.ReadTimeout("private-launch private-cookie transcript")
        if method == "prompt" and failure == "revoked":
            return httpx.Response(401)
        if method == "prompt" and failure == "structured":
            return httpx.Response(
                200,
                json={
                    "type": "server-response",
                    "rpcId": message["rpcId"],
                    "result": {
                        "ok": False,
                        "error": {
                            "code": "not_ready",
                            "message": "Native admission refused\nprivate-launch private-cookie api%2Fsecret",
                        },
                    },
                },
            )
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
        assert kwargs["logger"].disabled is True
        return socket

    def open_exchange(host: str, port: int, *, timeout: float) -> Mock:
        """Model the private one-shot HTTP exchange and its two response headers."""

        assert (host, port) == ("127.0.0.1", 1234)
        assert timeout > 0

        def exchange(method: str, target: str) -> None:
            """Check that the launch token is sent only over the native exchange."""

            assert method == "GET"
            location = urlsplit(target)
            assert location.path == "/connect"
            assert parse_qs(location.query) == {
                "interactions": ["none"],
                "token": ["private-launch"],
            }
            calls.append(location.path)

        return Mock(
            request=Mock(side_effect=exchange),
            getresponse=Mock(
                return_value=Mock(
                    status=302,
                    getheader=Mock(return_value="./api/remote.mux"),
                    getheaders=Mock(
                        return_value=[
                            ("location", "./api/remote.mux"),
                            (
                                "set-cookie",
                                "native-api=private-cookie; HttpOnly; SameSite=Strict; Path=/",
                            ),
                        ]
                    ),
                )
            ),
        )

    monkeypatch.setattr(client_module.httpx, "Client", new_client)
    monkeypatch.setattr(client_module, "connect", open_socket)
    monkeypatch.setattr(client_module, "HTTPConnection", open_exchange)
    return calls, socket


def test_private_api_credentials_and_socket_have_independent_lifetime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Persist a private origin-bound API cookie and close its owned socket exactly once."""

    calls, socket = _transport(monkeypatch)
    credentials = tmp_path / "private/api.json"
    with caplog.at_level(logging.DEBUG):
        client = DshWebClient.from_connection(
            "http://127.0.0.1:1234", launch_token="private-launch", cookie_file=credentials
        )
    assert "private-launch" not in caplog.text and "private-cookie" not in caplog.text
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


def test_api_exchange_checks_connected_peer_before_sending_the_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Close a stale connection without sending credentials or opening a WebSocket."""

    connection = Mock()
    socket = Mock()
    monkeypatch.setattr(client_module, "HTTPConnection", Mock(return_value=connection))
    monkeypatch.setattr(client_module, "connect", socket)

    def check() -> None:
        """Simulate changed ownership immediately after connecting."""

        connection.connect.assert_called_once_with()
        connection.request.assert_not_called()
        raise DshWebError("stale_identity", "Native listener was replaced")

    with pytest.raises(DshWebError, match="Native listener was replaced"):
        DshWebClient.from_connection(
            "http://127.0.0.1:1234", launch_token="private-launch", verify_listener=check
        )
    connection.request.assert_not_called()
    connection.close.assert_called_once_with()
    socket.assert_not_called()


def test_api_exchange_checks_the_websocket_peer_before_sending_the_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retained launch-token verification cannot authorize another listener for the cookie."""

    calls, _ = _transport(monkeypatch)
    checked_socket = Mock()
    create_socket = Mock(return_value=checked_socket)
    monkeypatch.setattr(client_module.socket, "create_connection", create_socket)
    open_socket = Mock()
    monkeypatch.setattr(client_module, "connect", open_socket)
    check = Mock(side_effect=[None, DshWebError("stale_identity", "Native listener was replaced")])

    with pytest.raises(DshWebError, match="Native listener was replaced"):
        DshWebClient.from_connection(
            "http://127.0.0.1:1234", launch_token="private-launch", verify_listener=check
        )

    assert calls == ["/connect"]
    create_socket.assert_called_once_with(("127.0.0.1", 1234), timeout=15.0)
    checked_socket.close.assert_called_once_with()
    open_socket.assert_not_called()


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


def test_native_refusal_keeps_code_and_scrubs_resolved_web_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scrub the launch token, current API cookie and selected key before raising."""

    calls, _socket = _transport(monkeypatch, "structured")
    client = DshWebClient.from_connection(
        "http://127.0.0.1:1234", launch_token="private-launch", secret_values=("api/secret",)
    )
    try:
        with pytest.raises(DshWebError, match="not_ready: Native admission refused") as failed:
            client.prompt({}, "prompt", operation_id="operation", deadline_epoch_ms=100)
        assert failed.value.code == "not_ready"
        assert str(failed.value).count("[REDACTED]") == 3
        assert "\n" not in str(failed.value)
        assert calls.count("/houmao/managed/v1/prompt") == 1
    finally:
        client.close()


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


def test_refresh_forwards_original_absolute_deadline_after_lock_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native preflight shares the remaining original budget rather than a reset timer."""

    client = DshWebClient()
    client.call = Mock(return_value={})
    monkeypatch.setattr(client_module.time, "monotonic", lambda: 100.0)
    client.refresh_common_plugins(
        {"native_session_id": "native"}, timeout_seconds=30, deadline_monotonic=102.0
    )
    client.call.assert_called_once_with(
        "refresh",
        {
            "identity": {"native_session_id": "native"},
            "timeout_seconds": 2.0,
            "deadline_monotonic_ms": 102000.0,
        },
    )


def test_refresh_does_not_send_after_serialization_consumes_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Waiting for an owned client lock cannot create a delayed native mutation."""

    client = DshWebClient()
    client.call = Mock()
    times = iter([100.0, 103.0])
    monkeypatch.setattr(client_module.time, "monotonic", lambda: next(times))
    with pytest.raises(DshWebError) as expired:
        client.refresh_common_plugins({}, timeout_seconds=30, deadline_monotonic=102.0)
    assert expired.value.code == "expired"
    client.call.assert_not_called()
