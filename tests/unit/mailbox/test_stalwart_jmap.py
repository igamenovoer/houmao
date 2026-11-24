"""Wire-level qualification of bounded Stalwart JMAP operations."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.agents import mailbox_runtime_support
from houmao.agents.mailbox_runtime_models import (
    MailboxesResolvedConfig,
    MailboxSlotConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.realm_controller import gateway_access_runtime, gateway_service, manifest
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.mailbox.online_authority import OnlineConnectionAuthority
from houmao.mailbox.online_binding import OnlineBindingService
from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineAuthorityContext,
    OnlineBindingError,
)
from houmao.mailbox.stalwart import (
    StalwartError,
    StalwartJmapClient,
    StalwartMethodError,
    StalwartMutationError,
)
from houmao.mailbox.stalwart_models import JmapMetadataQuery
from houmao.mailbox.sync import SyncBudget, SyncObserver, SyncScope
from houmao.srv_ctrl.commands import managed_agents

CORE = "urn:ietf:params:jmap:core"
MAIL = "urn:ietf:params:jmap:mail"
SUBMISSION = "urn:ietf:params:jmap:submission"


@pytest.mark.parametrize(
    ("policy_available", "expected_code"),
    [(True, "provider_delivery_unqualified"), (False, "recipient_policy_unavailable")],
)
def test_managed_stalwart_refuses_before_provider_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy_available: bool, expected_code: str
) -> None:
    """Refuse keyed or unavailable recipient authority before credentials or provider I/O."""

    context = OnlineAuthorityContext(tmp_path / "manifest.json", "bob", "runtime")
    monkeypatch.setattr(
        manifest,
        "load_session_manifest",
        lambda _path: SimpleNamespace(payload={"registry_generation_id": "g"}),
    )

    def resolve(_path: Path) -> SimpleNamespace:
        if not policy_available:
            raise SessionManifestError("private owner state unavailable")
        return SimpleNamespace(
            store=SimpleNamespace(snapshot=lambda: SimpleNamespace(admin_mode="keyed")),
            require_current=lambda: None,
        )

    monkeypatch.setattr(gateway_access_runtime, "gateway_access_for_manifest", resolve)
    authority = OnlineConnectionAuthority.from_context(context)
    with pytest.raises(OnlineBindingError) as operation:
        with authority.operation(expected_binding_id="stale-provider"):
            pytest.fail("Provider operation was admitted")
    assert operation.value.code == expected_code

    service = OnlineBindingService.from_context(context)
    with pytest.raises(OnlineBindingError) as attached:
        service.attach(
            OnlineAttachRequest(
                expected_revision="initial",
                address="bob@example.test",
                login_identity="bob",
                jmap_url="https://provider.example.test/jmap",
                credential_source_ref=str(tmp_path / "absent-secret"),
            )
        )
    assert attached.value.code == expected_code

    configured = StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id="bob",
        address="bob@example.test",
        jmap_url="https://provider.example.test/jmap",
        management_url=None,
        login_identity="bob",
        credential_ref="absent-secret",
        bindings_version="initial",
        agent_id="bob",
        binding_id="stale-provider",
    )
    mailboxes = MailboxesResolvedConfig(online=MailboxSlotConfig(binding=configured))
    selected_manifest = SimpleNamespace(
        agent_id="bob",
        launch_plan=SimpleNamespace(mailboxes=SimpleNamespace(model_dump=lambda **_: {})),
    )

    def unexpected_provider(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Status probed a protected provider binding")

    monkeypatch.setattr(
        mailbox_runtime_support,
        "mailboxes_resolved_config_from_payload",
        lambda *_args, **_kwargs: mailboxes,
    )
    monkeypatch.setattr(
        managed_agents,
        "mailboxes_resolved_config_from_payload",
        lambda *_args, **_kwargs: mailboxes,
    )
    monkeypatch.setattr(
        managed_agents, "_read_running_agent_manifest", lambda _authority: selected_manifest
    )
    monkeypatch.setattr(managed_agents, "build_gateway_mailbox_adapter", unexpected_provider)
    monkeypatch.setattr(gateway_service, "build_gateway_mailbox_adapter", unexpected_provider)
    local = managed_agents._local_manager_mail_status(context)
    remote = gateway_service.GatewayServiceRuntime.get_mail_status(
        SimpleNamespace(
            m_manifest_path=context.manifest_path,
            _load_manifest_payload_for_mailbox_support=lambda: selected_manifest,
        )
    )
    for status in (local, remote):
        assert status.online is not None and status.online.available is False


def _email(
    email_id: str, *, read: bool = False, received: str = "2026-01-01T00:00:00Z"
) -> dict[str, Any]:
    """Build provider metadata with selected content available only on explicit request."""
    return {
        "id": email_id,
        "threadId": f"thread-{email_id}",
        "receivedAt": received,
        "messageId": [f"{email_id}@example.test"],
        "inReplyTo": [],
        "references": [],
        "from": [{"email": "bob@example.test"}],
        "to": [{"email": "alice@example.test"}],
        "replyTo": [],
        "cc": [],
        "subject": f"Message {email_id}",
        "preview": "Short preview",
        "mailboxIds": {"inbox-id": True},
        "keywords": {"$seen": True} if read else {},
        "hasAttachment": True,
        "size": 100,
        "textBody": [{"partId": "text"}],
        "bodyValues": {
            "text": {"value": "Selected content", "isTruncated": False, "isEncodingProblem": False}
        },
        "attachments": [],
    }


def _matches(email: dict[str, Any], condition: dict[str, Any]) -> bool:
    """Implement the server-side subset used by the tested client."""
    operator = condition.get("operator")
    if operator == "AND":
        return all(_matches(email, item) for item in condition["conditions"])
    if operator == "NOT":
        return not any(_matches(email, item) for item in condition["conditions"])
    for key, value in condition.items():
        if key == "inMailbox" and not email["mailboxIds"].get(value):
            return False
        if key == "hasKeyword" and not email["keywords"].get(value):
            return False
        if key == "notKeyword" and email["keywords"].get(value):
            return False
        if key == "after" and email["receivedAt"] <= value:
            return False
    return True


@dataclass
class _WireState:
    """Mutable fake provider data and captured HTTP envelopes."""

    url: str = ""
    requests: list[tuple[str, str, str | None, Any]] = field(default_factory=list)
    methods: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    messages: dict[str, dict[str, Any]] = field(default_factory=dict)
    identities: list[dict[str, str]] = field(
        default_factory=lambda: [
            {"id": "identity-other", "email": "other@example.test"},
            {"id": "identity-alice", "email": "alice@example.test"},
        ]
    )
    mailboxes: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"id": "inbox-id", "role": "inbox", "name": "Inbox", "myRights": {}},
            {"id": "sent-id", "role": "sent", "name": "Sent", "myRights": {}},
            {"id": "archive-id", "role": "archive", "name": "Archive", "myRights": {}},
        ]
    )
    accounts: dict[str, Any] = field(
        default_factory=lambda: {
            "account-a": {"isReadOnly": False, "accountCapabilities": {MAIL: {}, SUBMISSION: {}}}
        }
    )
    primary_accounts: dict[str, str] = field(
        default_factory=lambda: {MAIL: "account-a", SUBMISSION: "account-a"}
    )
    api_url: str | None = None
    redirect_url: str | None = None
    get_limit: int = 200
    query_cap: int = 200
    state: str = "email-state-newer"
    query_state: str = "query-state-1"
    changes: dict[str, Any] = field(
        default_factory=lambda: {
            "oldState": "email-state-0",
            "newState": "email-state-intermediate",
            "hasMoreChanges": True,
            "created": ["old"],
            "updated": [],
            "destroyed": [],
        }
    )
    query_changes: dict[str, Any] = field(
        default_factory=lambda: {
            "oldQueryState": "query-state-0",
            "newQueryState": "query-state-1",
            "removed": [],
            "added": [],
        }
    )
    errors: dict[str, str] = field(default_factory=dict)
    http_errors: dict[str, int] = field(default_factory=dict)
    submission_rejection: bool = False
    update_rejection: bool = False
    fail_after_submission: bool = False
    submitted: bool = False
    malformed_get: bool = False

    def respond(self, method: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Produce one JMAP result while retaining request order for mutation tests."""
        if method in self.errors:
            return "error", {"type": self.errors[method], "description": "provider-private-text"}
        if method == "Mailbox/get":
            return method, {"list": self.mailboxes, "state": "mailboxes-1", "notFound": []}
        if method == "Identity/get":
            return method, {"list": self.identities, "state": "identities-1", "notFound": []}
        if method == "Email/query":
            messages = sorted(
                self.messages.values(), key=lambda item: item["receivedAt"], reverse=True
            )
            ids = [item["id"] for item in messages if _matches(item, args["filter"])]
            position = args.get("position", 0)
            limit = min(args["limit"], self.query_cap)
            result: dict[str, Any] = {
                "queryState": self.query_state,
                "position": position,
                "ids": ids[position : position + limit],
            }
            if len(ids) - position > limit:
                result["limit"] = limit
            return method, result
        if method == "Email/get":
            if self.fail_after_submission and self.submitted:
                return "error", {"type": "serverFail"}
            values = [self.messages[value] for value in args["ids"] if value in self.messages]
            properties = args.get("properties", [])
            values = [
                {key: value for key, value in item.items() if key in properties} for item in values
            ]
            return method, {
                "state": self.state,
                "list": [] if self.malformed_get else values,
                "notFound": [value for value in args["ids"] if value not in self.messages],
            }
        if method == "Email/changes":
            return method, dict(self.changes)
        if method == "Email/queryChanges":
            return method, dict(self.query_changes)
        if method == "Email/set" and "create" in args:
            self.messages["created-email"] = dict(
                _email("created-email"), **args["create"]["mail-1"]
            )
            return method, {"created": {"mail-1": {"id": "created-email"}}}
        if method == "EmailSubmission/set":
            if self.submission_rejection:
                return method, {"notCreated": {"submission-1": {"type": "forbiddenFrom"}}}
            self.submitted = True
            return method, {"created": {"submission-1": {"id": "submission-confirmed"}}}
        if method == "Email/set" and "update" in args:
            email_id, patch = next(iter(args["update"].items()))
            if self.update_rejection:
                return method, {"notUpdated": {email_id: {"type": "forbidden"}}}
            for key, value in patch.items():
                group, name = key.split("/", 1)
                if value is None:
                    self.messages[email_id][group].pop(name, None)
                else:
                    self.messages[email_id][group][name] = value
            return method, {"updated": {email_id: None}}
        raise AssertionError(f"Unexpected method: {method}")


@pytest.fixture
def wire(tmp_path: Path) -> Iterator[tuple[_WireState, Path]]:
    """Serve a hermetic fake JMAP provider over actual loopback HTTP."""
    state = _WireState(messages={"old": _email("old")})

    class Handler(BaseHTTPRequestHandler):
        """Capture authenticated wire requests and serve deterministic provider state."""

        def log_message(self, format: str, *args: object) -> None:
            """Keep fixture access logs out of test output."""

        def do_GET(self) -> None:
            """Return discovery or an explicitly configured redirect."""
            state.requests.append(("GET", self.path, self.headers.get("Authorization"), None))
            if state.redirect_url and self.path == "/.well-known/jmap":
                self.send_response(302)
                self.send_header("Location", state.redirect_url)
                self.end_headers()
                return
            self._json(
                {
                    "capabilities": {
                        CORE: {"maxObjectsInGet": state.get_limit, "maxCallsInRequest": 4},
                        MAIL: {},
                        SUBMISSION: {},
                    },
                    "accounts": state.accounts,
                    "primaryAccounts": state.primary_accounts,
                    "apiUrl": state.api_url or state.url + "/method-endpoint",
                    "uploadUrl": state.url + "/upload/{accountId}",
                }
            )

        def do_POST(self) -> None:
            """Return the requested method results or a deterministic transport failure."""
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append(("POST", self.path, self.headers.get("Authorization"), body))
            responses = []
            for method, args, call_id in body["methodCalls"]:
                state.methods.append((method, args))
                if method in state.http_errors:
                    self.send_response(state.http_errors[method])
                    self.end_headers()
                    self.wfile.write(b"private credential text must not escape")
                    return
                name, payload = state.respond(method, args)
                responses.append([name, payload, call_id])
            self._json({"methodResponses": responses})

        def _json(self, payload: dict[str, Any]) -> None:
            """Write one finite JSON HTTP response."""
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.url = f"http://127.0.0.1:{server.server_port}"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    credential = tmp_path / "credential.json"
    credential.write_text(json.dumps({"password": "test-only-secret"}))
    credential.chmod(0o600)
    try:
        yield state, credential
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _client(wire: tuple[_WireState, Path], **kwargs: Any) -> StalwartJmapClient:
    """Construct an explicitly addressed fake-provider connection."""
    state, credential = wire
    return StalwartJmapClient(
        jmap_url=state.url + "/.well-known/jmap",
        login_identity="login-is-not-address",
        credential_file=credential,
        sender_address="alice@example.test",
        **kwargs,
    )


def test_discovery_pins_exact_identity_and_reuses_account_and_roles(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    client = _client(wire)
    binding = client.validate_binding()
    assert binding.account_id == "account-a"
    assert binding.identity_id == "identity-alice"
    assert binding.sender_address == "alice@example.test"
    assert binding.api_url.endswith("/method-endpoint")
    for _ in range(3):
        assert client.query_metadata_page(query=JmapMetadataQuery()).messages[0]["body"] is None
    assert [method for method, _ in state.methods].count("Mailbox/get") == 1
    assert [method for method, _ in state.methods].count("Identity/get") == 1
    assert len([item for item in state.requests if item[0] == "GET"]) == 1
    assert all(item[1] == "/method-endpoint" for item in state.requests if item[0] == "POST")


def test_ambiguous_accounts_and_wrong_explicit_account_never_choose_first(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    state.accounts["account-b"] = state.accounts["account-a"]
    state.primary_accounts = {}
    with pytest.raises(StalwartError, match="ambiguous"):
        _client(wire).validate_binding()
    with pytest.raises(StalwartError, match="unauthorized"):
        _client(wire, account_id="account-missing").validate_binding()
    assert state.methods == []
    assert _client(wire, account_id="account-b").validate_binding().account_id == "account-b"


def test_sender_mismatch_does_not_fall_back_to_first_identity(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    state.identities = [{"id": "other", "email": "other@example.test"}]
    with pytest.raises(StalwartError, match="authorized sending identity"):
        _client(wire).validate_binding()
    assert not any(method.endswith("/set") for method, _ in state.methods)


def test_credential_epoch_is_immutable_after_source_replacement(
    wire: tuple[_WireState, Path],
) -> None:
    _, credential = wire
    client = _client(wire)
    header = client.authorization_header()
    credential.write_text('{"password":"rotated-test-only-secret"}')
    client.validate_binding()
    assert client.authorization_header() == header
    assert _client(wire).authorization_header() != header


def test_standard_discovery_redirect_stays_within_authorized_origin(
    wire: tuple[_WireState, Path],
) -> None:
    """Accept Stalwart's same-origin well-known session redirect."""
    state, _ = wire
    state.redirect_url = state.url + "/session"
    assert _client(wire).validate_binding().identity_id == "identity-alice"
    assert [item[1] for item in state.requests if item[0] == "GET"] == [
        "/.well-known/jmap",
        "/session",
    ]


@pytest.mark.parametrize("redirect", [False, True])
def test_unapproved_origin_and_redirect_never_receive_provider_credentials(
    wire: tuple[_WireState, Path], redirect: bool
) -> None:
    state, _ = wire
    if redirect:
        state.redirect_url = "https://another-provider.example.test/redirected"
    else:
        state.api_url = "https://another-provider.example.test/methods"
    with pytest.raises(StalwartError):
        _client(wire).validate_binding()
    assert len(state.requests) == 1
    assert state.methods == []


def test_server_filters_precede_limit_and_metadata_never_requests_body(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    for index in range(30):
        state.messages[f"new-{index}"] = _email(
            f"new-{index}", read=True, received=f"2026-02-{index + 1:02d}T00:00:00Z"
        )
    client = _client(wire)
    client.validate_binding()
    page = client.query_metadata_page(
        query=JmapMetadataQuery(read_state="unread", answered_state="unanswered", archived=False),
        limit=1,
    )
    assert [item["id"] for item in page.messages] == ["old"]
    query = next(args for method, args in state.methods if method == "Email/query")
    assert {"notKeyword": "$seen"} in query["filter"]["conditions"]
    assert {"notKeyword": "$answered"} in query["filter"]["conditions"]
    assert {"operator": "NOT", "conditions": [{"inMailbox": "archive-id"}]} in query["filter"][
        "conditions"
    ]
    assert query["collapseThreads"] is False
    for method, args in state.methods:
        if method == "Email/get":
            assert not {"attachments", "bodyValues", "textBody", "htmlBody", "bodyStructure"} & set(
                args["properties"]
            )
            assert "fetchTextBodyValues" not in args
            assert "hasAttachment" in args["properties"]
    assert page.messages[0]["hasAttachment"] is True


def test_since_is_exclusive_and_membership_preserves_multiple_mailboxes(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    state.messages["later"] = _email("later", received="2026-01-02T00:00:00Z")
    state.messages["later"]["mailboxIds"]["archive-id"] = True
    client = _client(wire)
    client.validate_binding()
    query = JmapMetadataQuery(since="2026-01-01T00:00:00Z", archived=True)
    page = client.query_metadata_page(query=query)
    assert [item["id"] for item in page.messages] == ["later"]
    assert page.messages[0]["box"] == "inbox"
    assert page.messages[0]["archived"] is True
    before = client.method_call_count
    assert client.metadata_matches_query(page.messages[0], query)
    assert not client.metadata_matches_query(page.messages[0], JmapMetadataQuery(archived=False))
    assert client.method_call_count == before


def test_missing_role_never_widens_to_account_query(wire: tuple[_WireState, Path]) -> None:
    state, _ = wire
    state.mailboxes = []
    with pytest.raises(StalwartError, match="inbox"):
        _client(wire).query_metadata_page(query=JmapMetadataQuery())
    assert not any(method == "Email/query" for method, _ in state.methods)


def test_provider_cap_uses_bounded_probe_and_rejects_state_drift(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    state.query_cap = 1
    state.messages["second"] = _email("second", received="2026-01-02T00:00:00Z")
    client = _client(wire)
    client.validate_binding()
    first = client.query_metadata_page(query=JmapMetadataQuery(), limit=50)
    assert len(first.messages) == 1
    assert first.has_more and not first.complete and first.next_position == 1
    assert first.method_calls == 3
    second = client.query_metadata_page(
        query=JmapMetadataQuery(), limit=50, position=1, expected_query_state=first.query_state
    )
    assert [item["id"] for item in second.messages] == ["old"]
    assert not second.has_more and second.complete
    state.query_state = "query-state-2"
    before = len([item for item in state.methods if item[0] == "Email/get"])
    with pytest.raises(StalwartMethodError) as captured:
        client.query_metadata_page(
            query=JmapMetadataQuery(), position=1, expected_query_state=first.query_state
        )
    assert captured.value.error_type == "staleCursor"
    assert len([item for item in state.methods if item[0] == "Email/get"]) == before


def test_probe_budget_is_conservative_instead_of_false_end(wire: tuple[_WireState, Path]) -> None:
    client = _client(wire)
    client.validate_binding()
    page = client.query_metadata_page(query=JmapMetadataQuery(), limit=1, max_method_calls=2)
    assert page.has_more and page.method_calls == 2
    empty = client.query_metadata_page(
        query=JmapMetadataQuery(),
        limit=1,
        position=page.next_position or 0,
        expected_query_state=page.query_state,
        max_method_calls=2,
    )
    assert empty.messages == [] and empty.complete


def test_page_counter_excludes_concurrent_client_operations(
    wire: tuple[_WireState, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Charge a page's context rather than unrelated requests on the connection."""
    state, _ = wire
    state.messages["second"] = _email("second", received="2026-01-02T00:00:00Z")
    client = _client(wire)
    client.validate_binding()
    original = client.call
    interleaved = False

    def call(method_calls: Any, *, timeout_seconds: float | None = None) -> dict[str, Any]:
        """Interleave a separate thread's state request before the page query."""
        nonlocal interleaved
        if method_calls[0][0] == "Email/query" and not interleaved:
            interleaved = True
            worker = Thread(target=client.email_state)
            worker.start()
            worker.join(timeout=2)
            assert not worker.is_alive()
        return original(method_calls, timeout_seconds=timeout_seconds)

    monkeypatch.setattr(client, "call", call)
    before = client.method_call_count
    page = client.query_metadata_page(query=JmapMetadataQuery(), limit=1, max_method_calls=2)
    assert page.method_calls == 2
    assert client.method_call_count - before == 3


def test_page_budget_includes_uncached_role_lookup(wire: tuple[_WireState, Path]) -> None:
    """Stop before exceeding the budget when role discovery was not prepared."""
    state, _ = wire
    with pytest.raises(StalwartError, match="budget"):
        _client(wire).query_metadata_page(query=JmapMetadataQuery(), max_method_calls=2)
    assert len(state.methods) == 2
    assert not any(method == "Email/get" for method, _ in state.methods)


@pytest.mark.parametrize("limit", [0, -1, 201, True])
def test_invalid_page_size_fails_before_discovery(
    wire: tuple[_WireState, Path], limit: int
) -> None:
    state, _ = wire
    with pytest.raises(StalwartError, match="limit"):
        _client(wire).query_metadata_page(query=JmapMetadataQuery(), limit=limit)
    assert state.requests == []


def test_metadata_missing_ids_are_authoritative_but_incomplete_batches_fail(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    client = _client(wire)
    batch = client.get_metadata(email_ids=["old", "gone"])
    assert batch.not_found == ["gone"] and batch.state == state.state
    state.malformed_get = True
    with pytest.raises(StalwartError, match="reconcile"):
        client.get_metadata(email_ids=["old"])


def test_email_boundary_and_intermediate_change_state_are_distinct_from_get_state(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    client = _client(wire)
    assert client.email_state() == "email-state-newer"
    boundary = next(args for method, args in state.methods if method == "Email/get")
    assert boundary["ids"] == [] and boundary["properties"] == ["id"]
    delta = client.changes(since_state="email-state-0", max_changes=1)
    assert delta.has_more_changes and delta.new_state == "email-state-intermediate"
    assert client.get_metadata(email_ids=delta.created).state == "email-state-newer"
    assert delta.new_state == "email-state-intermediate"
    assert client.method_call_count == 3


@pytest.mark.parametrize(
    "method,code",
    [("Email/changes", "cannotCalculateChanges"), ("Email/queryChanges", "tooManyChanges")],
)
def test_change_errors_preserve_safe_protocol_type(
    wire: tuple[_WireState, Path], method: str, code: str
) -> None:
    state, _ = wire
    state.errors[method] = code
    client = _client(wire)
    with pytest.raises(StalwartMethodError) as captured:
        if method == "Email/changes":
            client.changes(since_state="email-state-0")
        else:
            client.query_changes(query=JmapMetadataQuery(), since_query_state="query-state-0")
    assert captured.value.error_type == code
    assert "provider-private-text" not in str(captured.value)


def test_query_changes_has_query_state_without_fabricated_has_more(
    wire: tuple[_WireState, Path],
) -> None:
    client = _client(wire)
    result = client.query_changes(query=JmapMetadataQuery(), since_query_state="query-state-0")
    assert result.new_query_state == "query-state-1"
    assert not hasattr(result, "has_more_changes")


def test_content_truncation_and_multipart_budget_are_visible_and_nonmutating(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    state.messages["old"]["textBody"] = [{"partId": "text"}, {"partId": "second"}]
    state.messages["old"]["bodyValues"] = {
        "text": {"value": "abcdef", "isTruncated": True, "isEncodingProblem": False},
        "second": {"value": "ghijkl", "isTruncated": False, "isEncodingProblem": False},
    }
    result = _client(wire).get_content(email_id="old", max_body_value_bytes=8)
    assert not result["content_complete"] and result["content_limit_bytes"] == 8
    assert "body_value_truncated" in result["content_limit_reason"]
    assert "aggregate_content_limit" in result["content_limit_reason"]
    assert len(result["body"].encode()) <= 8
    assert not any(method.endswith("/set") for method, _ in state.methods)
    assert state.messages["old"]["keywords"] == {}


def _send(client: StalwartJmapClient) -> dict[str, Any]:
    """Submit exactly one test message."""
    return client.send(
        sender_address="alice@example.test",
        to_addresses=["bob@example.test"],
        cc_addresses=(),
        subject="Hello",
        body_content="Body",
        attachments=(),
    )


def test_send_checks_submission_failure_and_does_not_retry(wire: tuple[_WireState, Path]) -> None:
    state, _ = wire
    state.submission_rejection = True
    with pytest.raises(StalwartMutationError) as captured:
        _send(_client(wire))
    assert captured.value.outcome == "rejected"
    assert captured.value.email_id == "created-email"
    assert not state.submitted
    assert [name for name, _ in state.methods].count("EmailSubmission/set") == 1


@pytest.mark.parametrize("after_confirmed", [False, True])
def test_send_retains_uncertainty_or_confirmed_receipt_after_failure(
    wire: tuple[_WireState, Path], after_confirmed: bool
) -> None:
    state, _ = wire
    if after_confirmed:
        state.fail_after_submission = True
    else:
        state.http_errors["EmailSubmission/set"] = 503
    with pytest.raises(StalwartMutationError) as captured:
        _send(_client(wire))
    assert captured.value.outcome == ("confirmed" if after_confirmed else "uncertain")
    assert captured.value.email_id == "created-email"
    assert captured.value.submission_id == ("submission-confirmed" if after_confirmed else None)
    assert [name for name, _ in state.methods].count("EmailSubmission/set") == 1
    assert "private credential text" not in str(captured.value.__cause__)


def test_reply_uses_metadata_and_marks_parent_only_after_confirmed_submission(
    wire: tuple[_WireState, Path],
) -> None:
    state, _ = wire
    client = _client(wire)
    sent = client.reply(
        message_ref="stalwart:old",
        sender_address="alice@example.test",
        body_content="Reply",
        attachments=(),
    )
    assert sent["body"] is None
    assert sent["mutation_receipt"]["outcome"] == "confirmed"
    assert state.messages["old"]["keywords"] == {"$seen": True, "$answered": True}
    for method, args in state.methods:
        if method == "Email/get":
            assert not {"textBody", "bodyValues", "attachments"} & set(args["properties"])
    state.submission_rejection = True
    state.messages["old"]["keywords"] = {}
    with pytest.raises(StalwartMutationError):
        client.reply(
            message_ref="stalwart:old",
            sender_address="alice@example.test",
            body_content="Second",
            attachments=(),
        )
    assert state.messages["old"]["keywords"] == {}


def test_mark_rejection_and_keyword_removal_are_explicit(wire: tuple[_WireState, Path]) -> None:
    state, _ = wire
    client = _client(wire)
    state.update_rejection = True
    with pytest.raises(StalwartMethodError) as captured:
        client.mark(message_ref="old", read=True, answered=None, archived=None)
    assert captured.value.error_type == "forbidden"
    state.update_rejection = False
    state.messages["old"]["keywords"] = {"$seen": True}
    result = client.mark(message_ref="old", read=False, answered=None, archived=None)
    assert result["unread"] is True
    patch = [args for method, args in state.methods if method == "Email/set"][-1]
    assert patch["update"]["old"]["keywords/$seen"] is None


def test_explicitly_denied_right_prevents_mutation(wire: tuple[_WireState, Path]) -> None:
    state, _ = wire
    state.mailboxes[0]["myRights"] = {"maySetSeen": False}
    with pytest.raises(StalwartError, match="maySetSeen"):
        _client(wire).mark(message_ref="old", read=True, answered=None, archived=None)
    assert not any(method == "Email/set" for method, _ in state.methods)


def _wire_observer(tmp_path: Path, client: StalwartJmapClient) -> SyncObserver:
    """Bind an actual HTTP client after finite epoch validation has completed."""
    query = JmapMetadataQuery()

    def commit(callback: Any) -> bool:
        """Represent the binding authority's short SQLite-only commit section."""
        callback()
        return True

    return SyncObserver.from_config(
        sqlite_path=tmp_path / "gateway-sync.sqlite",
        client=client,
        scope=SyncScope.for_query(
            agent_id="agent",
            binding_id="binding",
            account_id="account-a",
            query=query,
            client=client,
        ),
        commit_guard=commit,
    )


def test_wire_observer_preserves_pre_query_boundary_and_intermediate_state(
    wire: tuple[_WireState, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real HTTP interleaving cannot promote the later Email/get object state."""
    state, _ = wire
    state.state = "s0"
    client = _client(wire)
    client.validate_binding(sender_address="alice@example.test")
    observer = _wire_observer(tmp_path, client)
    original = state.respond
    interleaved = False

    def interleave(method: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Insert new mail just after querying IDs, before metadata retrieval."""
        nonlocal interleaved
        if method == "Email/get" and args.get("ids") == ["old"] and not interleaved:
            state.messages["arrived"] = _email("arrived")
            state.state = "s99"
            state.query_state = "query-state-after-arrival"
            interleaved = True
        return original(method, args)

    monkeypatch.setattr(state, "respond", interleave)
    state.changes = {
        "oldState": "s0",
        "newState": "s1",
        "hasMoreChanges": True,
        "created": ["arrived"],
        "updated": [],
        "destroyed": [],
    }
    state.methods.clear()
    bootstrap = observer.observe(JmapMetadataQuery())
    assert bootstrap.email_state == "s0" and bootstrap.method_calls <= 5
    assert state.methods[0][0] == "Email/get" and state.methods[0][1]["ids"] == []
    state.methods.clear()
    view = observer.observe(JmapMetadataQuery())
    assert view.email_state == "s1" and view.email_state != "s99"
    assert "arrived" in {message["id"] for message in view.messages}
    assert [method for method, _ in state.methods] == [
        "Email/query",
        "Email/query",
        "Email/get",
        "Email/changes",
        "Email/get",
    ]
    assert view.method_calls == 5 and view.budget_limited
    for method, args in state.methods:
        if method == "Email/get":
            assert not {"textBody", "bodyValues", "attachments"}.intersection(args["properties"])
            assert "fetchTextBodyValues" not in args


def test_wire_observer_failed_fetch_keeps_checkpoint_until_reconciled_retry(
    wire: tuple[_WireState, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An incomplete real Email/get response never advances applied progress."""
    state, _ = wire
    state.state = "s0"
    state.changes = {
        "oldState": "s0",
        "newState": "s0",
        "hasMoreChanges": False,
        "created": [],
        "updated": [],
        "destroyed": [],
    }
    client = _client(wire)
    client.validate_binding(sender_address="alice@example.test")
    observer = _wire_observer(tmp_path, client)
    observer.observe(JmapMetadataQuery())
    observer.observe(JmapMetadataQuery())
    state.messages["changed"] = _email("changed")
    state.changes = {
        "oldState": "s0",
        "newState": "s1",
        "hasMoreChanges": False,
        "created": ["changed"],
        "updated": [],
        "destroyed": [],
    }
    state.malformed_get = True
    failed = observer.observe(JmapMetadataQuery())
    assert failed.phase == "degraded" and observer.snapshot().email_state == "s0"
    state.malformed_get = False
    state.state = "later-get-state"
    monkeypatch.setattr("houmao.mailbox.sync.time.time", lambda: (failed.retry_after_utc or 0) + 1)
    applied = observer.observe(JmapMetadataQuery())
    assert applied.email_state == "s1"
    assert "changed" in {message["id"] for message in applied.messages}


def test_wire_observer_expired_checkpoint_uses_finite_filtered_rebase(
    wire: tuple[_WireState, Path],
    tmp_path: Path,
) -> None:
    """Expired state recovers current inbox work without querying retained history."""
    state, _ = wire
    state.state = "s0"
    state.changes = {
        "oldState": "s0",
        "newState": "s0",
        "hasMoreChanges": False,
        "created": [],
        "updated": [],
        "destroyed": [],
    }
    client = _client(wire)
    client.validate_binding(sender_address="alice@example.test")
    observer = _wire_observer(tmp_path, client)
    observer.observe(JmapMetadataQuery())
    observer.observe(JmapMetadataQuery())
    state.errors["Email/changes"] = "cannotCalculateChanges"
    state.state = "rebase-boundary"
    state.methods.clear()
    view = observer.observe(JmapMetadataQuery(), SyncBudget())
    assert view.email_state == "rebase-boundary" and view.phase == "catching_up"
    assert view.method_calls <= 5
    query = [args for method, args in state.methods if method == "Email/query"]
    assert 1 <= len(query) <= 2 and query[0]["limit"] <= 51
    assert all(args["limit"] == 1 for args in query[1:])
    assert "inbox-id" in json.dumps(query[0]["filter"])
    assert not any(args.get("limit") is None for args in query)


def test_readonly_qualification_reports_actual_counts_and_unmeasured_reminders(
    wire: tuple[_WireState, Path],
    tmp_path: Path,
) -> None:
    """The standalone runner measures payload work without modifying provider mail."""
    state, credential = wire
    state.state = "s0"
    state.changes = {
        "oldState": "s0",
        "newState": "s0",
        "hasMoreChanges": False,
        "created": [],
        "updated": [],
        "destroyed": [],
    }
    root = Path(__file__).resolve().parents[3]
    work = tmp_path / "qualification"
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/qualification/stalwart-mail/observe.py"),
            "--discovery-url",
            state.url + "/.well-known/jmap",
            "--login",
            "login-is-not-address",
            "--address",
            "alice@example.test",
            "--agent-id",
            "agent",
            "--binding-id",
            "binding",
            "--service-release",
            "hermetic-fake",
            "--credential-file",
            str(credential),
            "--work-dir",
            str(work),
            "--cycles",
            "2",
            "--interval-seconds",
            "0",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["accounts_tested"] == 1
    assert report["traffic"]["http_requests"] > 0
    assert report["traffic"]["response_body_bytes_read"] > 0
    assert report["cycle_latency_p95_seconds"] >= report["cycle_latency_p50_seconds"]
    assert report["process_peak_rss_bytes"] > 0
    assert report["time_to_first_idle_seconds"] is not None
    assert report["reminder_count"] is None
    assert all(cycle["method_calls"] <= 5 for cycle in report["cycles"])
    assert not any(method in {"Email/set", "EmailSubmission/set"} for method, _ in state.methods)
    assert "login-is-not-address" not in result.stdout
    assert (work / "report.json").is_file()


def test_same_account_credential_refresh_preserves_scoped_provider_cursor(
    wire: tuple[_WireState, Path],
) -> None:
    """A new credential epoch keeps a valid account/query continuation in the same binding."""
    from dataclasses import replace
    from houmao.agents.mailbox_runtime_models import StalwartMailboxResolvedConfig
    from houmao.mailbox.scope import MailScope
    from houmao.mailbox.services import ScopedMailboxAdapter, StalwartGatewayMailboxAdapter

    state, credential = wire
    state.messages["second"] = _email("second", received="2026-01-02T00:00:00Z")
    old_client = _client(wire)
    selected = old_client.validate_binding()
    binding = StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id="owner-a",
        agent_id="owner-a",
        address="alice@example.test",
        jmap_url=state.url + "/.well-known/jmap",
        management_url=None,
        login_identity="login-is-not-address",
        credential_ref="protected-source",
        credential_file=credential,
        account_id=selected.account_id,
        identity_id=selected.identity_id,
        binding_id="binding-a",
        bindings_version="old-revision",
    )
    scope = MailScope("owner-a", "online", "binding-a")
    old_adapter = ScopedMailboxAdapter.from_backend(
        StalwartGatewayMailboxAdapter(binding, m_client=old_client), scope
    )
    first = old_adapter.list_page(
        box="inbox", read_state="any", answered_state="any", archived=None, limit=1
    )
    assert first.next_cursor is not None and first.has_more
    original_auth = old_client.authorization_header()
    credential.write_text('{"password":"refreshed-test-secret"}')
    refreshed_client = _client(
        wire, account_id=selected.account_id, identity_id=selected.identity_id
    )
    refreshed = refreshed_client.validate_binding()
    assert refreshed.account_id == selected.account_id
    assert refreshed.identity_id == selected.identity_id
    assert refreshed_client.authorization_header() != original_auth
    assert old_client.authorization_header() == original_auth
    new_adapter = ScopedMailboxAdapter.from_backend(
        StalwartGatewayMailboxAdapter(
            replace(binding, bindings_version="new-revision"), m_client=refreshed_client
        ),
        scope,
    )
    second = new_adapter.list_page(
        box="inbox",
        read_state="any",
        answered_state="any",
        archived=None,
        limit=1,
        cursor=first.next_cursor,
    )
    assert [scope.decode(message.message_ref) for message in second.messages] == ["stalwart:old"]
    assert second.complete and not second.has_more


def test_wire_role_refresh_between_scope_and_query_cannot_publish_old_policy(
    wire: tuple[_WireState, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Already-refreshed roles cannot evade the raw page's intra-request drift check."""
    state, _ = wire
    state.state = "s0"
    state.changes = {
        "oldState": "s0",
        "newState": "s0",
        "hasMoreChanges": False,
        "created": [],
        "updated": [],
        "destroyed": [],
    }
    client = _client(wire)
    client.validate_binding()
    observer = _wire_observer(tmp_path, client)
    old_key = observer.m_scope.key
    original_page = client.query_metadata_page
    changed = False

    def page(**kwargs: Any) -> Any:
        """Refresh shared roles after scope capture, before the page captures its policy."""
        nonlocal changed
        if not changed:
            changed = True
            state.mailboxes[0]["id"] = "new-inbox-id"
            state.messages = {
                "new-work": dict(_email("new-work"), mailboxIds={"new-inbox-id": True})
            }
            client.m_roles_loaded_at = 0
            assert client.mailbox_id_for_role("inbox") == "new-inbox-id"
        return original_page(**kwargs)

    monkeypatch.setattr(client, "query_metadata_page", page)
    result = observer.observe(JmapMetadataQuery())
    assert result.superseded and result.error_code == "query_policy_changed"
    assert result.messages == ()
    old = observer.snapshot()
    assert old.email_state == "s0" and old.query_state is None and old.messages == ()
    with sqlite3.connect(tmp_path / "gateway-sync.sqlite") as connection:
        assert connection.execute(
            "SELECT version FROM mail_sync_observations WHERE scope_key=?", (old_key,)
        ).fetchone() == (1,)
    current = _wire_observer(tmp_path, client)
    assert current.m_scope.key != old_key
    fresh = current.observe(JmapMetadataQuery())
    assert {message["id"] for message in fresh.messages} == {"new-work"}
