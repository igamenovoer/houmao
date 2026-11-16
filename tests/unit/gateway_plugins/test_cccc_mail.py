"""Qualify explicit Mail routes without consuming through status or notice delivery."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.gateway.plugins import PluginDispatchError
from tests.unit.gateway_plugins.test_cccc_plugin import (
    event,
    eventually,
    harness,
    implementation as implementation,
    offer,
)


def mail_event(identifier: str = "mail1") -> dict[str, Any]:
    """Create a complete synthetic native deferred event."""

    value = event(identifier)
    value["data"]["message_mode"] = "mail"
    return value


def cursor(identifier: str = "") -> dict[str, str]:
    """Create the authoritative native boundary schema."""

    return {"event_id": identifier, "ts": "", "updated_at": ""}


def read_receipt(
    operation_id: str = "read1", *, ids: list[str] | None = None, before: str = ""
) -> dict[str, Any]:
    """Describe a finite authoritative read decision without a message cache."""

    event_ids = ["mail1"] if ids is None else ids
    return {
        "operation_id": operation_id,
        "actor_generation": "gen1",
        "before_cursor": before,
        "after_cursor": event_ids[-1] if event_ids else before,
        "event_ids": event_ids,
        "outcome": "consumed" if event_ids else "empty",
        "read_event_id": "read-fact1",
    }


class Authority:
    """Record bounded Mail calls and provide explicitly scripted native results."""

    def __init__(self) -> None:
        """Create observable response and failure boundaries."""

        self.m_calls: list[tuple[str, dict[str, Any], bool]] = []
        self.m_failures: dict[str, Exception] = {}
        self.m_results: dict[str, Any] = {
            "mail.cursor": {"cursor": cursor()},
            "mail.peek": {
                "messages": [mail_event()],
                "cursor": cursor(),
                "has_more": True,
                "consumed": False,
                "count_accuracy": "bounded",
            },
            "mail.read": {
                "messages": [mail_event()],
                "cursor": cursor("mail1"),
                "has_more": True,
                "outcome": "consumed",
                "receipt": read_receipt(),
            },
            "mail.read-receipts": {"found": True, "receipt": read_receipt()},
            "mail.send": {"stored": True, "consumed": False, "event": mail_event("sent1")},
            "mail.reply": {"stored": True, "consumed": False, "event": mail_event("reply1")},
        }

    async def call(
        self, operation: str, arguments: dict[str, Any], *, mutation: bool = False
    ) -> dict[str, Any]:
        """Return one configured result without hidden retries, reads, or consumption."""

        self.m_calls.append((operation, dict(arguments), mutation))
        if operation in self.m_failures:
            raise self.m_failures[operation]
        return self.m_results[operation]


@asynccontextmanager
async def mail_harness(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncIterator[SimpleNamespace]:
    """Add qualified Mail authority to the real plugin and existing public SDK harness."""

    async with harness(implementation, monkeypatch, tmp_path) as h:
        module = importlib.import_module("houmao_cccc.mail")
        h.plugin.m_provider_capabilities["mail"] = True
        h.plugin.m_provider_capabilities["operations"].extend(module.MAIL_OPERATIONS)
        h.plugin.m_provider_capabilities["features"] = dict.fromkeys(module.MAIL_FEATURES, True)
        h.plugin.m_provider_capabilities["limits"].update(
            max_mail_messages=200, max_mail_response_bytes=1048576
        )
        authority = Authority()
        original = h.plugin._call

        async def call(
            operation: str, arguments: dict[str, Any], *, mutation: bool = False
        ) -> dict[str, Any]:
            """Keep chat transport working independently of the Mail test authority."""

            if operation.startswith("mail."):
                return await authority.call(operation, arguments, mutation=mutation)
            return await original(operation, arguments, mutation=mutation)

        monkeypatch.setattr(h.plugin, "_call", call)
        h.authority = authority
        h.mail = h.plugin.m_mail
        yield h


@pytest.mark.parametrize("missing", ["operation", "feature", "count", "bytes", "mail"])
def test_mail_requires_complete_contract_while_chat_stays_available(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing: str
) -> None:
    """Never fall back to an unqualified consuming read on a valid chat connection."""

    async def exercise() -> None:
        """Remove one mandatory contract component before reading through HTTP."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            capabilities = h.plugin.m_provider_capabilities
            if missing == "operation":
                capabilities["operations"].remove("mail.read-receipts")
            elif missing == "feature":
                capabilities["features"]["mail_read_crash_recovery"] = False
            elif missing in {"count", "bytes"}:
                capabilities["limits"][
                    "max_mail_messages" if missing == "count" else "max_mail_response_bytes"
                ] = 0
            else:
                capabilities["mail"] = False
            status = await h.http.get("/v1/plugins/team/capabilities")
            assert status.json()["mail"]["qualified"] is False
            assert "mail.read" not in status.json()["operations"]
            read = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "read1",
                    "expected_cursor": h.mail._ref("mail-cursor", ""),
                },
            )
            assert read.status_code == 501 and not h.authority.m_calls
            sent = await h.http.post(
                "/v1/plugins/team/chat/send",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "chat1",
                    "to": ["a2"],
                    "text": "still chat",
                },
            )
            assert sent.status_code == 200

    asyncio.run(exercise())


@pytest.mark.parametrize("recipient", ["user", "@user", "agent@example.test", "g/actor"])
def test_mail_rejects_email_and_human_recipients_before_provider(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, recipient: str
) -> None:
    """Unsupported recipient classes receive a structured refusal without translation."""

    async def exercise() -> None:
        """Send invalid recipients through the actual Mail route."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            result = await h.http.post(
                "/v1/plugins/team/mail/send",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "send1",
                    "to": [recipient],
                    "text": "must remain unsent",
                },
            )
            assert result.status_code == 422
            assert result.json()["detail"]["error_code"] == "unsupported_recipient"
            assert h.authority.m_calls == []

    asyncio.run(exercise())


def test_mail_send_reply_are_deferred_and_do_not_read(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Only explicit deferred provider mutations run, with scoped native ancestry."""

    async def exercise() -> None:
        """Create correspondence and reply through returned targeting authority."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            sent = await h.http.post(
                "/v1/plugins/team/mail/send",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "deferred",
                },
            )
            assert sent.status_code == 200
            assert sent.json()["backend"] == "cccc-mail"
            assert sent.json()["stored"] and not sent.json()["consumed"]
            replied = await h.http.post(
                "/v1/plugins/team/mail/reply",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "reply1",
                    "event_ref": sent.json()["event"]["event_ref"],
                    "text": "deferred reply",
                },
            )
            assert replied.status_code == 200
            assert [operation for operation, _, _ in h.authority.m_calls] == [
                "mail.send",
                "mail.reply",
            ]
            assert h.authority.m_calls[1][1]["event_id"] == "sent1"
            assert all("mode" not in arguments for _, arguments, _ in h.authority.m_calls)
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_mail_status_peek_and_receipts_never_consume_and_report_outage_staleness(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Status remains an honest maintained snapshot through bounded inspection and failure."""

    async def exercise() -> None:
        """Read each non-consuming surface and then make the provider unavailable."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            initial = await h.http.get("/v1/plugins/team/mail/status")
            assert initial.json()["pending_count"] is None and initial.json()["stale"]
            assert not h.authority.m_calls
            for _ in range(2):
                peeked = await h.http.get("/v1/plugins/team/mail/peek?limit=1")
                assert peeked.status_code == 200
                assert peeked.json()["count_accuracy"] == "capped"
                assert peeked.json()["messages"][0]["event_id"] == "mail1"
            current = await h.http.get("/v1/plugins/team/mail/status")
            assert current.json()["pending_count"] == 1 and not current.json()["stale"]
            await h.http.get("/v1/plugins/team/mail/cursor")
            lookup = await h.http.get("/v1/plugins/team/mail/reads/read1")
            assert lookup.json()["receipt"]["event_ids"] == ["mail1"]
            assert len(lookup.json()["receipt"]["event_refs"]) == 1
            assert not lookup.json()["consumed"]
            h.authority.m_failures["mail.peek"] = implementation.ProviderError(
                "provider_unavailable", 503, True
            )
            assert (await h.http.get("/v1/plugins/team/mail/peek")).status_code == 503
            before = len(h.authority.m_calls)
            stale = (await h.http.get("/v1/plugins/team/mail/status")).json()
            assert len(h.authority.m_calls) == before
            assert stale["pending_count"] == 1 and stale["stale"]
            assert stale["current_truth"] == "unknown" and stale["observation_age_seconds"] >= 0
            assert all(
                not mutation and op != "mail.read" for op, _, mutation in h.authority.m_calls
            )

    asyncio.run(exercise())


def test_mail_read_passes_complete_budget_and_scoped_precondition_once(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The provider gets full wrapper/reference reserves before its only consuming call."""

    async def exercise() -> None:
        """Inspect the wire arguments and authoritative read projection."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            inspected = (await h.http.get("/v1/plugins/team/mail/cursor")).json()
            result = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "read1",
                    "expected_cursor": inspected["cursor_ref"],
                    "limit": 1,
                    "max_bytes": 262144,
                },
            )
            assert result.status_code == 200
            response = result.json()
            assert response["outcome"] == "consumed" and response["consumed"]
            assert response["receipt"]["event_ids"] == ["mail1"]
            assert response["messages"][0]["data"]["text"] == "Synthetic text"
            call = h.authority.m_calls[-1]
            assert call[0] == "mail.read" and call[2]
            assert call[1]["expected_cursor"] == "" and call[1]["limit"] == 1
            assert call[1]["response_overhead_bytes"] > 1024
            assert call[1]["per_event_overhead_bytes"] > 512
            assert len([op for op, _, _ in h.authority.m_calls if op == "mail.read"]) == 1
            assert h.mail._decode("mail-cursor", response["cursor_ref"]) == "mail1"
            assert h.mail._decode("mail-read", response["read_ref"]) == "read1"
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_mail_defaults_apply_smaller_provider_limits(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Negotiated smaller bounds apply to default requests and advertised defaults alike."""

    async def exercise() -> None:
        """Observe the complete budget sent to a provider with narrower capabilities."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            h.plugin.m_provider_capabilities["limits"].update(
                max_mail_messages=1, max_mail_response_bytes=16384
            )
            capabilities = (await h.http.get("/v1/plugins/team/capabilities")).json()["mail"]
            assert capabilities["limits"]["default_messages"] == 1
            assert capabilities["limits"]["default_response_bytes"] == 16384
            result = await h.http.get("/v1/plugins/team/mail/peek")
            assert result.status_code == 200
            assert h.authority.m_calls[0][1]["limit"] == 1
            assert h.authority.m_calls[0][1]["max_bytes"] == 16384

    asyncio.run(exercise())


@pytest.mark.parametrize("operation_id", [".", "..", "read/other", "非ASCII"])
def test_mail_operation_identity_is_safe_for_receipt_addressing(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, operation_id: str
) -> None:
    """Reject IDs that a later receipt URL would normalize or interpret as another path."""

    async def exercise() -> None:
        """Check operation identity before any provider mutation can occur."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            result = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": operation_id,
                    "expected_cursor": h.mail._ref("mail-cursor", ""),
                },
            )
            assert result.status_code == 422 and not h.authority.m_calls

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["cursor", "read", "binding"])
def test_mail_stale_authority_fails_before_provider(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str
) -> None:
    """A malformed or foreign targeting handle cannot reach native Mail authority."""

    async def exercise() -> None:
        """Attempt a cursor, receipt, or binding substitution through the actual routes."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            if kind == "read":
                result = await h.http.get(
                    "/v1/plugins/team/mail/reads/read1", params={"read_ref": "offline-reference"}
                )
            else:
                result = await h.http.post(
                    "/v1/plugins/team/mail/read",
                    json={
                        "expected_binding_id": "other" if kind == "binding" else "binding1",
                        "operation_id": "read1",
                        "expected_cursor": "foreign-cursor",
                    },
                )
            assert result.status_code in {409, 422}
            assert h.authority.m_calls == []

    asyncio.run(exercise())


def test_mail_unknown_read_preserves_operation_and_receipt_reconciliation(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A lost response triggers no new read and preserves signed recovery metadata."""

    async def exercise() -> None:
        """Lose one mutation response then inspect its native receipt explicitly."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            h.authority.m_failures["mail.read"] = implementation.ProviderError(
                "provider_unavailable", 503, True, outcome="unknown"
            )
            result = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "read1",
                    "expected_cursor": h.mail._ref("mail-cursor", ""),
                },
            )
            detail = result.json()["detail"]
            assert result.status_code == 503 and detail["dispatch_outcome"] == "unknown"
            assert detail["operation_id"] == "read1"
            receipt = await h.http.get(
                "/v1/plugins/team/mail/reads/read1", params={"read_ref": detail["read_ref"]}
            )
            assert receipt.json()["found"]
            assert receipt.json()["receipt"]["event_ids"] == ["mail1"]
            assert [op for op, _, _ in h.authority.m_calls] == ["mail.read", "mail.read-receipts"]
            h.authority.m_results["mail.read-receipts"] = {"found": False, "operation_id": "read1"}
            unresolved = await h.http.get("/v1/plugins/team/mail/reads/read1")
            assert unresolved.json()["outcome"] == "unknown"

    asyncio.run(exercise())


def test_mail_repeated_empty_decision_does_not_claim_pending_mail_is_empty(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Already-completed operation lookup does not manufacture a new pending observation."""

    async def exercise() -> None:
        """Observe pending work then repeat a previously empty provider operation."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            await h.http.get("/v1/plugins/team/mail/peek")
            observed = h.mail.m_observed_at
            h.authority.m_results["mail.read"] = {
                "messages": [],
                "cursor": cursor(),
                "has_more": False,
                "outcome": "already_completed",
                "receipt": read_receipt(ids=[]),
            }
            result = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "read1",
                    "expected_cursor": h.mail._ref("mail-cursor", ""),
                },
            )
            assert result.status_code == 200 and result.json()["outcome"] == "already_completed"
            assert result.json()["receipt"]["outcome"] == "empty"
            assert h.mail.m_pending_count == 1 and h.mail.m_observed_at == observed

    asyncio.run(exercise())


@pytest.mark.parametrize("code", ["cursor_conflict", "content_limit", "operation_conflict"])
def test_mail_provider_precommit_refusals_do_not_retry_or_change_target(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, code: str
) -> None:
    """Cursor, byte, and operation conflicts remain explicit single-call refusals."""

    async def exercise() -> None:
        """Propagate one native precommit decision without selecting another batch."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            h.authority.m_failures["mail.read"] = implementation.ProviderError(
                code, 422 if code == "content_limit" else 409
            )
            response = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "read1",
                    "expected_cursor": h.mail._ref("mail-cursor", "previous"),
                    "limit": 1,
                },
            )
            assert response.status_code in {409, 422}
            detail = response.json()["detail"]
            assert detail["error_code"] == code and detail["dispatch_outcome"] == "not_sent"
            assert detail["operation_id"] == "read1"
            assert len(h.authority.m_calls) == 1
            assert h.authority.m_calls[0][1]["expected_cursor"] == "previous"
            assert h.mail.m_pending_count is None

    asyncio.run(exercise())


@pytest.mark.parametrize("malformed", ["mode", "receipt", "boundary", "size"])
def test_mail_malformed_committed_result_is_unknown_and_never_trimmed(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, malformed: str
) -> None:
    """A malformed postcommit result cannot become a fabricated failed or partial read."""

    async def exercise() -> None:
        """Return invalid commit evidence while retaining the caller recovery handle."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            batch = h.authority.m_results["mail.read"]
            if malformed == "mode":
                batch["messages"][0]["data"]["message_mode"] = "send"
            elif malformed == "receipt":
                batch["receipt"]["event_ids"] = ["another"]
            elif malformed == "boundary":
                batch["cursor"]["event_id"] = "another"
            else:
                batch["messages"][0]["data"]["text"] = "x" * 300000
            response = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "read1",
                    "expected_cursor": h.mail._ref("mail-cursor", ""),
                },
            )
            assert response.status_code == 503
            detail = response.json()["detail"]
            assert detail["dispatch_outcome"] == "unknown" and detail["operation_id"] == "read1"
            assert h.mail._decode("mail-read", detail["read_ref"]) == "read1"
            assert "messages" not in response.json() and len(h.authority.m_calls) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["mail-cursor", "mail-read"])
def test_mail_authenticated_foreign_scope_is_rejected_before_access(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str
) -> None:
    """Even a correctly signed former-owner handle cannot target the current binding."""

    async def exercise() -> None:
        """Generate a genuine foreign-scope token using an isolated codec snapshot."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            codec = h.plugin._references()
            original_scope = dict(codec.m_scope)
            codec.m_scope["owner"] = "another-owner"
            foreign = h.mail._ref(kind, "read1" if kind == "mail-read" else "")
            codec.m_scope = original_scope
            if kind == "mail-read":
                response = await h.http.get(
                    "/v1/plugins/team/mail/reads/read1", params={"read_ref": foreign}
                )
            else:
                response = await h.http.post(
                    "/v1/plugins/team/mail/read",
                    json={
                        "expected_binding_id": "binding1",
                        "operation_id": "read1",
                        "expected_cursor": foreign,
                    },
                )
            assert response.status_code == 422 and not h.authority.m_calls

    asyncio.run(exercise())


def test_mail_precommit_reserves_cover_maximum_reference_expansion(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Selected wire reserves cover every wrapper/reference byte of complete batches."""

    async def exercise() -> None:
        """Compare actual decorated UTF-8 size to provider result plus declared reserves."""

        import json

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            ids = [str(index) + "x" * 508 for index in range(3)]
            messages = [mail_event(identifier) for identifier in ids]
            # Non-ASCII content is retained completely; refs only expand finite native IDs.
            messages[0]["data"]["text"] = "中文 correspondence" * 100
            h.authority.m_results["mail.read"] = {
                "messages": messages,
                "cursor": cursor(ids[-1]),
                "has_more": False,
                "outcome": "consumed",
                "receipt": read_receipt(ids=ids),
            }
            response = await h.http.post(
                "/v1/plugins/team/mail/read",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "read1",
                    "expected_cursor": h.mail._ref("mail-cursor", ""),
                    "limit": 3,
                },
            )
            assert response.status_code == 200
            native_size = len(
                json.dumps(
                    {"ok": True, "result": h.authority.m_results["mail.read"]},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            )
            arguments = h.authority.m_calls[0][1]
            declared = (
                native_size
                + arguments["response_overhead_bytes"]
                + 3 * arguments["per_event_overhead_bytes"]
            )
            assert len(response.content) <= declared <= arguments["max_bytes"]
            assert response.json()["messages"][0]["data"]["text"] == messages[0]["data"]["text"]

    asyncio.run(exercise())


@pytest.mark.parametrize("refused", [False, True])
def test_mail_notice_is_content_free_ordinary_and_never_consumes(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, refused: bool
) -> None:
    """A notice uses immediate handoff and ignores all provider-supplied body text."""

    async def exercise() -> None:
        """Offer one notice and observe its single provider settlement."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            if refused:
                h.context.events.dispatch.side_effect = PluginDispatchError(
                    error_code="readiness_conflict", status_code=409, retryable=True
                )
            await h.service.m_offers.put(
                offer(kind="mail_notice", pending_count=2, text="PRIVATE MAIL BODY MUST NOT ESCAPE")
            )
            await eventually(lambda: bool(h.service.m_outcomes))
            assert h.service.m_outcomes[0]["outcome"] == ("refused" if refused else "accepted")
            dispatched = h.context.events.dispatch.call_args.args[0]
            assert "deferred Mail notice" in dispatched.text
            assert "PRIVATE MAIL BODY" not in dispatched.text
            assert "/mail/read" in dispatched.text
            assert dispatched.metadata["backend"] == "cccc-mail"
            assert not h.authority.m_calls
            await asyncio.sleep(0.04)
            assert h.context.events.dispatch.await_count == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("path", ["archive", "move", "mark-unread", "attachments", "submission"])
def test_mail_email_lifecycle_requests_fail_explicitly(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, path: str
) -> None:
    """Unsupported email semantics neither pretend success nor read any pending work."""

    async def exercise() -> None:
        """Use an actual route declaration that cannot shadow supported Mail operations."""

        async with mail_harness(implementation, monkeypatch, tmp_path) as h:
            result = await h.http.post("/v1/plugins/team/mail/" + path, json={})
            assert result.status_code == 501
            assert result.json()["detail"]["error_code"] == "unsupported_operation"
            assert not result.json()["detail"]["consumed"]
            assert not h.authority.m_calls

    asyncio.run(exercise())
