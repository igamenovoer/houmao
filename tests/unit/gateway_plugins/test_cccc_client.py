"""Verify the optional CCCC transport, immutable binding, and reference boundaries."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Load optional source explicitly for hermetic unit checks only."""

    source = Path(__file__).resolve().parents[3] / "packages/houmao-cccc/src"
    monkeypatch.syspath_prepend(str(source))
    return SimpleNamespace(
        configuration=importlib.import_module("houmao_cccc.configuration"),
        client=importlib.import_module("houmao_cccc.client"),
        references=importlib.import_module("houmao_cccc.references"),
        cli=importlib.import_module("houmao_cccc.cli"),
    )


def _configuration(modules: SimpleNamespace, **overrides: Any) -> Any:
    """Return an explicit local Actor fixture without ambient inputs."""

    return modules.configuration.CcccConfiguration(
        **{
            "endpoint": "http://127.0.0.1:8848",
            "group_id": "group-1",
            "actor_id": "actor-1",
            "actor_generation": "generation-1",
            **overrides,
        }
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://remote.example",
        "http://user:secret@127.0.0.1",
        "http://127.0.0.1?token=secret",
        "http://127.0.0.1#secret",
        "http://127.0.0.1/../admin",
        "ftp://127.0.0.1",
        "http://127.0.0.1/%2fadmin",
        "http://127.0.0.1:wrong",
        "http://127.0.0.1\\@remote",
    ],
)
def test_endpoint_rejects_secrets_traversal_and_insecure_remote(
    modules: SimpleNamespace, endpoint: str
) -> None:
    """Keep selected credentials off URLs and remote plaintext connections."""

    with pytest.raises(ValueError):
        _configuration(modules, endpoint=endpoint)


def test_configuration_is_strict_stable_and_owner_checked(modules: SimpleNamespace) -> None:
    """Normalize equivalent bindings and reject unselected identity inputs."""

    configuration = _configuration(modules, endpoint="http://LOCALHOST:8848/")
    assert configuration.endpoint == "http://localhost:8848"
    same = _configuration(modules, endpoint="http://localhost:8848")
    assert modules.configuration.binding_identity(
        configuration
    ) == modules.configuration.binding_identity(same)
    with pytest.raises(ValueError):
        _configuration(modules, history_limit=101)
    with pytest.raises(ValueError):
        _configuration(modules, request_timeout_seconds=float("nan"))
    document = {
        "agent_id": "owner",
        "endpoint": configuration.endpoint,
        "group_id": "group-1",
        "actor_id": "actor-1",
        "actor_generation": "generation-1",
        "token": "synthetic-grant",
    }
    assert (
        modules.configuration.validate_credentials(configuration, "owner", document)
        == "synthetic-grant"
    )
    for field in ("agent_id", "endpoint", "group_id", "actor_id", "actor_generation"):
        with pytest.raises(ValueError, match="owner binding"):
            modules.configuration.validate_credentials(
                configuration, "owner", {**document, field: "other"}
            )


def test_provider_single_request_uses_fixed_rpc_and_selected_token(
    modules: SimpleNamespace,
) -> None:
    """Observe the wire rather than mirroring internal HTTP construction."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Return a synthetic successful service result."""

        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"stored": True}})

    async def exercise() -> None:
        """Execute a real asynchronous client against the wire oracle."""

        client = modules.client.ProviderClient.from_config(
            _configuration(modules), "synthetic-grant", transport=httpx.MockTransport(handler)
        )
        result = await client.request(
            "chat.send",
            {"operation_id": "operation-1", "text": "hello", "to": ["actor-2"], "mode": "send"},
        )
        assert result == {"stored": True}
        await client.aclose()

    asyncio.run(exercise())
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "http://127.0.0.1:8848/api/v1/external-receiver/v1/rpc"
    assert request.headers["Authorization"] == "Bearer synthetic-grant"
    assert json.loads(request.content)["operation"] == "chat.send"


def test_mutation_transport_loss_is_uncertain_and_never_retried(modules: SimpleNamespace) -> None:
    """An accepted-but-disconnected sender does not silently send another request."""

    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        """Simulate connection loss after provider-side side effects were possible."""

        nonlocal requests
        requests += 1
        raise httpx.ReadError("synthetic private provider diagnostic", request=request)

    async def exercise() -> None:
        """Inspect safe error metadata after a single failed mutation."""

        client = modules.client.ProviderClient.from_config(
            _configuration(modules), "synthetic-grant", transport=httpx.MockTransport(handler)
        )
        with pytest.raises(modules.client.ProviderError) as raised:
            await client.request("chat.send", {"text": "synthetic"})
        assert raised.value.outcome == "unknown"
        assert "private" not in str(raised.value)
        await client.aclose()

    asyncio.run(exercise())
    assert requests == 1


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (
            httpx.Response(302, headers={"location": "https://other.example"}),
            "provider_redirect_refused",
        ),
        (httpx.Response(404, text="private stock HTML"), "receiver_incompatible"),
        (
            httpx.Response(
                404, json={"ok": False, "error": {"code": "event_not_found", "message": "private"}}
            ),
            "event_not_found",
        ),
        (httpx.Response(200, content=b"x" * 1025), "provider_response_limit"),
        (httpx.Response(200, json={"ok": True, "result": []}), "invalid_provider_response"),
        (
            httpx.Response(200, content=b'{"ok":true,"result":{"x":NaN}}'),
            "invalid_provider_response",
        ),
        (
            httpx.Response(
                503,
                json={
                    "ok": False,
                    "error": {"code": "private-secret", "message": "private", "retryable": True},
                },
            ),
            "provider_error",
        ),
    ],
)
def test_provider_bounds_redirects_and_sanitizes_wire_errors(
    modules: SimpleNamespace, response: httpx.Response, code: str
) -> None:
    """Reject unsafe or oversized responses before projecting private content."""

    async def exercise() -> None:
        """Exercise the exact response boundary with a small configured budget."""

        client = modules.client.ProviderClient.from_config(
            _configuration(modules, max_response_bytes=1024),
            "synthetic-grant",
            transport=httpx.MockTransport(lambda _request: response),
        )
        with pytest.raises(modules.client.ProviderError) as raised:
            await client.request("binding", {})
        assert raised.value.code == code
        if code == "event_not_found":
            assert raised.value.status_code == 404
        assert "private" not in json.dumps(raised.value.to_detail())
        await client.aclose()

    asyncio.run(exercise())


def test_provider_disallows_identity_overrides_before_network(modules: SimpleNamespace) -> None:
    """An ordinary caller cannot turn the narrow transport into an admin client."""

    async def exercise() -> None:
        """Verify unsupported authority fails without any network client."""

        client = modules.client.ProviderClient.from_config(_configuration(modules), "synthetic")
        for operation, arguments in [("admin.takeover", {}), ("chat.send", {"by": "user"})]:
            with pytest.raises(modules.client.ProviderError):
                await client.request(operation, arguments)
        await client.aclose()

    asyncio.run(exercise())


def _context(tmp_path: Path, owner: str = "owner", binding: str = "binding") -> SimpleNamespace:
    """Represent a private SDK-selected state scope for reference tests."""

    return SimpleNamespace(
        owner=SimpleNamespace(agent_id=owner, runtime_session_id="runtime"),
        instance_id="team",
        binding_id=binding,
        state=SimpleNamespace(path=lambda name: tmp_path / name),
    )


def test_references_survive_restart_and_reject_wrong_scope(
    modules: SimpleNamespace, tmp_path: Path
) -> None:
    """Authenticate handle scope even when copied into the same signing-key directory."""

    references = modules.references
    first = references.ReferenceCodec.from_context(_context(tmp_path))
    handle = first.encode("event", {"event_id": "native-event-1"})
    restarted = references.ReferenceCodec.from_context(_context(tmp_path))
    assert restarted.decode(handle, "event") == {"event_id": "native-event-1"}
    assert (tmp_path / "reference-key").stat().st_mode & 0o077 == 0
    for context, target in [
        (_context(tmp_path, owner="other"), "event"),
        (_context(tmp_path, binding="replacement"), "event"),
        (_context(tmp_path), "cursor"),
    ]:
        with pytest.raises(references.ReferenceError):
            references.ReferenceCodec.from_context(context).decode(handle, target)
    for invalid in [handle + "x", "wrong." + handle, "cccc1.!!.!!"]:
        with pytest.raises(references.ReferenceError):
            first.decode(invalid, "event")
    assert [p.name for p in tmp_path.iterdir()] == ["reference-key"]


def test_reference_key_rejects_symlinks_and_unsafe_permissions(
    modules: SimpleNamespace, tmp_path: Path
) -> None:
    """Do not follow a signing-key replacement outside the private state scope."""

    target = tmp_path / "outside"
    target.write_bytes(b"x" * 32)
    os.chmod(target, 0o600)
    key = tmp_path / "reference-key"
    key.symlink_to(target)
    with pytest.raises(modules.references.ReferenceError):
        modules.references.ReferenceCodec.from_context(_context(tmp_path))
    key.unlink()
    key.write_bytes(b"x" * 32)
    os.chmod(key, 0o644)
    with pytest.raises(modules.references.ReferenceError):
        modules.references.ReferenceCodec.from_context(_context(tmp_path))


def test_cli_is_gateway_only_and_keeps_explicit_operation_identity(
    modules: SimpleNamespace,
) -> None:
    """Translate body-side actions without reading CCCC auth or selecting a backend."""

    args = modules.cli._parser().parse_args(
        [
            "--gateway-url",
            "http://127.0.0.1:9000",
            "--instance",
            "team",
            "chat",
            "send",
            "--binding-id",
            "binding",
            "--operation-id",
            "operation-1",
            "--to",
            "other",
            "--text",
            "hello",
        ]
    )
    method, path, body = modules.cli._request(args)
    assert method == "POST" and path == "/chat/send"
    assert body == {
        "expected_binding_id": "binding",
        "operation_id": "operation-1",
        "to": ["other"],
        "text": "hello",
        "mode": "send",
    }
    with pytest.raises(ValueError):
        modules.configuration.normalize_endpoint("https://remote.example", loopback_only=True)


def test_cli_retry_round_trip_matches_actual_plugin_schema(
    modules: SimpleNamespace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pass CLI JSON through the real ASGI router before observing provider arguments."""

    plugin_module = importlib.import_module("houmao_cccc.plugin")
    context = _context(tmp_path)
    plugin = plugin_module.CcccPlugin.from_config(context, _configuration(modules))
    plugin.m_codec = modules.references.ReferenceCodec.from_context(context)
    event_ref = plugin.m_codec.encode("event", {"event_id": "event-1"})
    call = AsyncMock(return_value={"deliveries": []})
    plugin._call = call
    app = FastAPI()
    app.include_router(plugin.router, prefix="/v1/plugins/team")
    with TestClient(app) as gateway:

        def handler(request: httpx.Request) -> httpx.Response:
            """Forward the CLI's actual HTTP request into the actual plugin router."""

            result = gateway.request(
                request.method,
                request.url.path,
                content=request.content,
                headers={"content-type": request.headers["content-type"]},
            )
            assert result.status_code == 200, result.text
            return httpx.Response(result.status_code, content=result.content)

        result = modules.cli.run(
            [
                "--gateway-url",
                "http://127.0.0.1:9000",
                "--instance",
                "team",
                "chat",
                "retry",
                "--binding-id",
                "binding",
                "--event-ref",
                event_ref,
                "--to",
                "actor-2",
                "--allow-uncertain-retry",
            ],
            transport=httpx.MockTransport(handler),
        )
    assert result == 0, capsys.readouterr()
    call.assert_awaited_once_with(
        "chat.retry",
        {"event_id": "event-1", "actor_ids": ["actor-2"], "allow_uncertain_retry": True},
        mutation=True,
    )


def test_delivery_lookup_preserves_provider_order(
    modules: SimpleNamespace,
    tmp_path: Path,
) -> None:
    """Return newest-first provider receipts and the provider's count indicator."""

    plugin_module = importlib.import_module("houmao_cccc.plugin")
    context = _context(tmp_path)
    plugin = plugin_module.CcccPlugin.from_config(context, _configuration(modules))
    plugin.m_codec = modules.references.ReferenceCodec.from_context(context)
    event_ref = plugin.m_codec.encode("event", {"event_id": "event-1"})
    deliveries = [
        {"attempt_id": "z", "state": "accepted"},
        {"attempt_id": "a", "state": "refused"},
    ]
    plugin._call = AsyncMock(return_value={"deliveries": deliveries, "has_more": True})
    app = FastAPI()
    app.include_router(plugin.router, prefix="/v1/plugins/team")
    with TestClient(app) as gateway:
        response = gateway.get(
            "/v1/plugins/team/chat/deliveries", params={"event_ref": event_ref, "limit": 2}
        )

    plugin._call.assert_awaited_once_with("chat.deliveries", {"event_id": "event-1", "limit": 2})
    assert response.status_code == 200
    assert response.json()["deliveries"] == deliveries
    assert response.json()["has_more"] is True


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9000/v1/plugins/team",
        "http://127.0.0.1:9000/v1/plugins/team/chat/reply",
        "http://127.0.0.1:invalid",
        "http://user:redacted-value@127.0.0.1:9000",
    ],
)
def test_cli_rejects_bad_gateway_url_before_selecting_managed_self(
    modules: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    url: str,
) -> None:
    """Diagnose a malformed base or pasted route before authority or network work."""

    monkeypatch.setenv("HOUMAO_MANIFEST_PATH", "/private/manifest.json")
    select_self = Mock()
    open_request = Mock()
    monkeypatch.setattr(modules.cli, "managed_self_gateway_client", select_self)
    monkeypatch.setattr(modules.cli.GatewayClient, "_open_request", open_request)

    assert modules.cli.run(["--gateway-url", url, "binding"]) == 1
    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert error["error_code"] == "invalid_gateway_url"
    assert "--gateway-url" in error["message"] and "--instance" in error["message"]
    assert url not in captured.err
    assert "redacted-value" not in captured.err
    assert captured.out == ""
    select_self.assert_not_called()
    open_request.assert_not_called()


def test_cli_reports_unavailable_managed_self_without_a_request(
    modules: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Keep unavailable current-generation authority distinct from bad URL input."""

    monkeypatch.setenv("HOUMAO_MANIFEST_PATH", "/private/manifest.json")
    resolve = Mock(side_effect=ValueError("private-manifest-diagnostic"))
    open_request = Mock()
    monkeypatch.setattr("houmao.agents.instance_state.resolve_verified_self", resolve)
    monkeypatch.setattr(modules.cli.GatewayClient, "_open_request", open_request)

    assert modules.cli.run(["--gateway-url", "http://127.0.0.1:9000", "binding"]) == 1
    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert error["error_code"] == "managed_self_authority_unavailable"
    assert "owning gateway base URL" in error["message"]
    assert "private" not in captured.err
    assert captured.out == ""
    resolve.assert_called_once_with()
    open_request.assert_not_called()


@pytest.mark.parametrize(
    "base_url",
    ["https://gateway.example/agents/alex", "https://127.0.0.1/v1/plugins/proxy-prefix"],
)
def test_cli_uses_exact_signer_bound_https_base(
    modules: SimpleNamespace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    base_url: str,
) -> None:
    """Preserve a configured proxy prefix and reject a plugin route appended to it."""

    signer_binding = tmp_path / "signer.json"
    signer_binding.write_text(
        json.dumps(
            {
                "base_url": base_url,
                "owner": {"agent_id": "agent", "context_id": "context"},
                "purpose": "caller",
                "private_key_path": str(tmp_path / "key"),
            }
        )
    )
    signer_binding.chmod(0o600)
    monkeypatch.setenv("HOUMAO_MANIFEST_PATH", "/private/manifest.json")
    proof = Mock(return_value={})
    open_request = Mock(return_value=b"{}")
    monkeypatch.setattr(modules.cli.GatewayClient, "caller_proof_headers", proof)
    monkeypatch.setattr(modules.cli.GatewayClient, "_open_request", open_request)
    args = ["--signer-binding", str(signer_binding), "--instance", "team", "binding"]

    assert modules.cli.run(["--gateway-url", base_url, *args]) == 0
    proof.assert_called_once_with("GET", "/v1/plugins/team/binding", b"")
    assert open_request.call_args.kwargs["request_obj"].full_url == (
        base_url + "/v1/plugins/team/binding"
    )
    assert json.loads(capsys.readouterr().out) == {}
    open_request.reset_mock()
    proof.reset_mock()

    assert modules.cli.run(["--gateway-url", base_url + "/v1/plugins/team", *args]) == 1
    assert json.loads(capsys.readouterr().err)["error_code"] == "invalid_gateway_url"
    proof.assert_not_called()
    open_request.assert_not_called()


def test_cli_uses_unsigned_loopback_https_proxy_prefix(
    modules: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Allow an HTTPS proxy prefix that resembles an advertised local HTTP plugin route."""

    monkeypatch.delenv("HOUMAO_MANIFEST_PATH", raising=False)
    open_request = Mock(return_value=b"{}")
    monkeypatch.setattr(modules.cli.GatewayClient, "_open_request", open_request)
    base_url = "https://127.0.0.1/v1/plugins/gateway-prefix"

    assert modules.cli.run(["--gateway-url", base_url, "--instance", "team", "binding"]) == 0
    assert open_request.call_args.kwargs["request_obj"].full_url == (
        base_url + "/v1/plugins/team/binding"
    )
    assert json.loads(capsys.readouterr().out) == {}


def test_cli_retains_safe_uncertainty_and_caller_operation_id(
    modules: SimpleNamespace, capsys: pytest.CaptureFixture[str]
) -> None:
    """Expose reconciliation data while excluding raw provider diagnostic content."""

    def handler(_request: httpx.Request) -> httpx.Response:
        """Return the gateway's normal structured uncertain response."""

        return httpx.Response(
            503,
            json={
                "detail": {
                    "error_code": "provider_unavailable",
                    "retryable": True,
                    "dispatch_outcome": "unknown",
                    "message": "private-diagnostic-value",
                    "token": "private-secret-value",
                }
            },
        )

    result = modules.cli.run(
        [
            "--gateway-url",
            "http://127.0.0.1:9000",
            "chat",
            "send",
            "--binding-id",
            "binding",
            "--operation-id",
            "operation-1",
            "--to",
            "actor-2",
            "--text",
            "hello",
        ],
        transport=httpx.MockTransport(handler),
    )
    output = capsys.readouterr().out
    assert result == 1
    assert json.loads(output) == {
        "error_code": "provider_unavailable",
        "status": 503,
        "retryable": True,
        "dispatch_outcome": "unknown",
        "operation_id": "operation-1",
        "expected_binding_id": "binding",
    }
    assert "private" not in output


def test_cli_connection_loss_is_uncertain_without_new_operation(
    modules: SimpleNamespace, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed outgoing mutation keeps its caller correlation identity visible."""

    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        """Fail a single actual HTTP request after possible upstream acceptance."""

        nonlocal calls
        calls += 1
        raise httpx.ReadError("private-provider-error", request=request)

    result = modules.cli.run(
        [
            "--gateway-url",
            "http://127.0.0.1:9000",
            "chat",
            "send",
            "--binding-id",
            "binding",
            "--operation-id",
            "operation-1",
            "--to",
            "actor-2",
            "--text",
            "hello",
        ],
        transport=httpx.MockTransport(handler),
    )
    error = json.loads(capsys.readouterr().err)
    assert result == 1 and calls == 1
    assert error["dispatch_outcome"] == "unknown"
    assert error["operation_id"] == "operation-1"


@pytest.mark.parametrize(
    ("operation", "outcome"),
    [
        ("mail.send", "unknown"),
        ("mail.reply", "unknown"),
        ("mail.read", "unknown"),
        ("mail.peek", "not_sent"),
        ("mail.cursor", "not_sent"),
        ("mail.read-receipts", "not_sent"),
    ],
)
@pytest.mark.parametrize("error_type", [httpx.ReadError, httpx.DecodingError])
def test_mail_transport_classifies_consumption_without_automatic_retry(
    modules: SimpleNamespace,
    operation: str,
    outcome: str,
    error_type: type[httpx.RequestError],
) -> None:
    """Response loss never repeats a read or turns inspection into consumption."""

    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Lose the one selected request after its possible provider acceptance."""

        requests.append(json.loads(request.content))
        raise error_type("private-provider-value", request=request)

    async def exercise() -> None:
        """Observe the actual asynchronous transport and its safe outcome metadata."""

        client = modules.client.ProviderClient.from_config(
            _configuration(modules), "synthetic-grant", transport=httpx.MockTransport(handler)
        )
        with pytest.raises(modules.client.ProviderError) as raised:
            await client.request(operation, {"operation_id": "caller-operation"})
        assert raised.value.outcome == outcome
        assert "private" not in str(raised.value)
        await client.aclose()

    asyncio.run(exercise())
    assert requests == [{"operation": operation, "arguments": {"operation_id": "caller-operation"}}]


def test_mail_transport_accepts_explicitly_configured_larger_bound(
    modules: SimpleNamespace,
) -> None:
    """A configured Mail budget can exceed chat without weakening its bound."""

    def handler(_request: httpx.Request) -> httpx.Response:
        """Return a complete synthetic response above the default chat limit."""

        return httpx.Response(200, json={"ok": True, "result": {"content": "a" * 270000}})

    async def exercise() -> None:
        """Use the same selected transport with independently enforced operation limits."""

        client = modules.client.ProviderClient.from_config(
            _configuration(modules, mail_max_bytes=524288),
            "synthetic-grant",
            transport=httpx.MockTransport(handler),
        )
        assert len((await client.request("mail.peek"))["content"]) == 270000
        with pytest.raises(modules.client.ProviderError, match="CCCC operation failed"):
            await client.request("chat.history")
        await client.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("arguments", "method", "path", "body"),
    [
        (["cursor"], "GET", "/mail/cursor", {}),
        (["status"], "GET", "/mail/status", {}),
        (
            ["peek", "--limit", "200", "--max-bytes", "1048576"],
            "GET",
            "/mail/peek",
            {"limit": "200", "max_bytes": "1048576"},
        ),
        (
            [
                "send",
                "--binding-id",
                "binding",
                "--operation-id",
                "send-1",
                "--to",
                "receiver",
                "--text",
                "deferred",
            ],
            "POST",
            "/mail/send",
            {
                "expected_binding_id": "binding",
                "operation_id": "send-1",
                "to": ["receiver"],
                "text": "deferred",
            },
        ),
        (
            [
                "reply",
                "--binding-id",
                "binding",
                "--operation-id",
                "reply-1",
                "--event-ref",
                "event-ref",
                "--text",
                "deferred reply",
            ],
            "POST",
            "/mail/reply",
            {
                "expected_binding_id": "binding",
                "operation_id": "reply-1",
                "event_ref": "event-ref",
                "text": "deferred reply",
            },
        ),
        (
            [
                "read",
                "--binding-id",
                "binding",
                "--operation-id",
                "read-1",
                "--expected-cursor",
                "cursor-ref",
            ],
            "POST",
            "/mail/read",
            {
                "expected_binding_id": "binding",
                "operation_id": "read-1",
                "expected_cursor": "cursor-ref",
            },
        ),
        (
            ["reads", "--operation-id", "read-1", "--read-ref", "scoped-ref"],
            "GET",
            "/mail/reads/read-1",
            {"read_ref": "scoped-ref"},
        ),
    ],
)
def test_cli_mail_wire_is_explicit_and_credential_free(
    modules: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    method: str,
    path: str,
    body: dict[str, Any],
) -> None:
    """Match the public Mail routes without hidden modes, reads, or operation IDs."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Observe one actual CLI request without a provider connection."""

        requests.append(request)
        return httpx.Response(200, json={"outcome": "empty"})

    assert (
        modules.cli.run(
            ["--gateway-url", "http://127.0.0.1:9000", "mail", *arguments],
            transport=httpx.MockTransport(handler),
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {"outcome": "empty"}
    assert len(requests) == 1
    request = requests[0]
    assert request.method == method
    assert request.url.path == "/v1/plugins/cccc" + path
    assert (dict(request.url.params) if method == "GET" else json.loads(request.content)) == body
    assert "authorization" not in request.headers


def test_cli_mail_read_loss_preserves_reconciliation_identity(
    modules: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A possibly consumed batch remains unknown under the caller's original identity."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Drop the only consuming request's reply."""

        requests.append(request)
        raise httpx.ReadError("private-upstream-diagnostic", request=request)

    assert (
        modules.cli.run(
            [
                "--gateway-url",
                "http://127.0.0.1:9000",
                "mail",
                "read",
                "--binding-id",
                "binding",
                "--operation-id",
                "caller-read-1",
                "--expected-cursor",
                "scoped-cursor",
            ],
            transport=httpx.MockTransport(handler),
        )
        == 1
    )
    result = json.loads(capsys.readouterr().err)
    assert len(requests) == 1
    assert result["outcome"] == "unknown"
    assert result["operation_id"] == "caller-read-1"
    assert result["expected_binding_id"] == "binding"
    assert "private" not in json.dumps(result)


def test_unavailable_read_receipt_keeps_original_consumption_unknown(
    modules: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Failure to inspect a receipt never establishes that its earlier read failed."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Make non-consuming receipt inspection unavailable."""

        requests.append(request)
        raise httpx.ConnectError("private-detail", request=request)

    assert (
        modules.cli.run(
            [
                "--gateway-url",
                "http://127.0.0.1:9000",
                "mail",
                "reads",
                "--operation-id",
                "original-read",
            ],
            transport=httpx.MockTransport(handler),
        )
        == 1
    )
    result = json.loads(capsys.readouterr().err)
    assert result["outcome"] == "unknown"
    assert result["operation_id"] == "original-read"
    assert len(requests) == 1 and requests[0].method == "GET"


@pytest.mark.parametrize("response", [b'{"incomplete":', b"[]", b"x" * 1048577])
def test_invalid_consuming_read_reply_preserves_original_reconciliation_identity(
    modules: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
    response: bytes,
) -> None:
    """A malformed or oversized successful reply cannot erase a possibly committed read."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Return an invalid response after the gateway may have consumed the batch."""

        requests.append(request)
        return httpx.Response(200, content=response)

    assert (
        modules.cli.run(
            [
                "--gateway-url",
                "http://127.0.0.1:9000",
                "mail",
                "read",
                "--binding-id",
                "binding",
                "--operation-id",
                "original-read",
                "--expected-cursor",
                "scoped-cursor",
            ],
            transport=httpx.MockTransport(handler),
        )
        == 1
    )
    result = json.loads(capsys.readouterr().err)
    assert result["error_code"] == "gateway_response_invalid"
    assert result["outcome"] == result["dispatch_outcome"] == "unknown"
    assert result["operation_id"] == "original-read"
    assert result["expected_binding_id"] == "binding"
    assert len(requests) == 1


@pytest.mark.parametrize("status", [408, 500, 502, 503])
def test_unstructured_consuming_read_http_failure_remains_unknown(
    modules: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
    status: int,
) -> None:
    """A server/proxy error without authoritative outcome cannot imply no consumption."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Return a non-JSON error after possible committed consumption."""

        requests.append(request)
        return httpx.Response(status, content=b"private non-JSON upstream diagnostic")

    assert (
        modules.cli.run(
            [
                "--gateway-url",
                "http://127.0.0.1:9000",
                "mail",
                "read",
                "--binding-id",
                "binding",
                "--operation-id",
                "original-read",
                "--expected-cursor",
                "scoped-cursor",
            ],
            transport=httpx.MockTransport(handler),
        )
        == 1
    )
    result = json.loads(capsys.readouterr().out)
    assert result["outcome"] == result["dispatch_outcome"] == "unknown"
    assert result["operation_id"] == "original-read"
    assert result["expected_binding_id"] == "binding"
    assert "private" not in json.dumps(result)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "bounds",
    [["--limit", "201"], ["--limit", "0"], ["--max-bytes", "1048577"], ["--max-bytes", "1023"]],
)
def test_cli_rejects_unqualified_mail_bounds_before_http(
    modules: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
    bounds: list[str],
) -> None:
    """Oversized Mail requests fail before issuing any service operation."""

    def handler(_request: httpx.Request) -> httpx.Response:
        """Reject accidental HTTP activity from invalid CLI limits."""

        raise AssertionError("Unqualified Mail budget reached HTTP")

    assert (
        modules.cli.run(
            ["--gateway-url", "http://127.0.0.1:9000", "mail", "peek", *bounds],
            transport=httpx.MockTransport(handler),
        )
        == 1
    )
    assert json.loads(capsys.readouterr().err) == {"error_code": "cccc_cli_failed"}


@pytest.mark.parametrize(
    ("status", "envelope", "code", "outcome"),
    [
        (
            200,
            {"ok": False, "error": {"code": "cursor_conflict"}},
            "invalid_provider_response",
            "unknown",
        ),
        (503, {"error": {"code": "cursor_conflict"}}, "invalid_provider_response", "unknown"),
        (
            503,
            {"ok": True, "error": {"code": "cursor_conflict"}},
            "invalid_provider_response",
            "unknown",
        ),
        (409, {"ok": False, "error": {"code": "cursor_conflict"}}, "cursor_conflict", "not_sent"),
        (
            408,
            {"ok": False, "error": {"code": "daemon_unavailable"}},
            "daemon_unavailable",
            "unknown",
        ),
    ],
)
def test_mail_read_error_requires_authoritative_failure_envelope(
    modules: SimpleNamespace,
    status: int,
    envelope: dict[str, Any],
    code: str,
    outcome: str,
) -> None:
    """Malformed protocol errors cannot establish that a possibly committed read failed."""

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Return the selected protocol envelope after possible consumption."""

        requests.append(request)
        return httpx.Response(status, json=envelope)

    async def exercise() -> None:
        """Classify the single response without automatically repeating consumption."""

        client = modules.client.ProviderClient.from_config(
            _configuration(modules), "synthetic-grant", transport=httpx.MockTransport(handler)
        )
        with pytest.raises(modules.client.ProviderError) as raised:
            await client.request("mail.read", {"operation_id": "original-read"})
        assert raised.value.code == code
        assert raised.value.outcome == outcome
        await client.aclose()

    asyncio.run(exercise())
    assert len(requests) == 1
