# Code Review: gateway-first-headless-mailbox-turns

**Reviewed:** 2026-03-23T15:42:57
**Scope:** OpenSpec change `gateway-first-headless-mailbox-turns` — all implementation artifacts
**Reviewer basis:** Knowledge-based review with online verification as needed

## Change Summary

This change makes routine mailbox work in bounded headless agent turns *gateway-first* instead of falling back to direct transport-local mechanics. The implementation spans five areas:

1. **New `POST /v1/mail/state` route** for single-message read-state updates by opaque `message_ref`
2. **Restructured notifier prompt** to nominate one oldest-first actionable unread target
3. **Gateway adapter protocol extension** with `update_read_state` method on both transports
4. **Projected skill rewrites** making gateway-first the default section, transport-local as fallback
5. **Demo pack and role prompt alignment** to gateway-first shared mailbox operations

## Files Reviewed

### Source

| File | Lines | Area |
| --- | --- | --- |
| `src/houmao/agents/realm_controller/gateway_mailbox.py` | 709 | Adapter protocol + both transport implementations |
| `src/houmao/agents/realm_controller/gateway_models.py` | 919 | `GatewayMailStateRequestV1`, `GatewayMailStateResponseV1` models |
| `src/houmao/agents/realm_controller/gateway_service.py` | ~1640 | Route wiring, `_UnreadMailboxMessage`, notifier prompt builder |
| `src/houmao/agents/realm_controller/gateway_client.py` | 288 | `update_mail_state` client method |
| `src/houmao/agents/realm_controller/boundary_models.py` | 487 | Boundary model context (no direct change needed) |
| `src/houmao/agents/mailbox_runtime_support.py` | 640 | Mailbox config resolution and skill projection |
| `src/houmao/mailbox/stalwart.py` | 600+ | `StalwartJmapClient.update_read_state` |
| `src/houmao/mailbox/managed.py` | 1400+ | `StateUpdateRequest`, `update_mailbox_state` |
| `src/houmao/demo/mail_ping_pong_gateway_demo_pack/driver.py` | 624 | Kickoff prompt, demo lifecycle |

### Skills

| File | Area |
| --- | --- |
| `src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-filesystem/SKILL.md` | Gateway-first section first, then direct fallback |
| `src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-stalwart/SKILL.md` | Gateway-first section first, then direct fallback |

### Tests

| File | Area |
| --- | --- |
| `tests/unit/agents/realm_controller/test_gateway_support.py` | State route, rejection, notifier nomination |
| `tests/integration/agents/realm_controller/test_gateway_runtime_contract.py` | Gateway runtime integration |
| `tests/unit/demo/test_mail_ping_pong_gateway_demo_pack.py` | Demo pack unit tests |

### Docs

| File | Area |
| --- | --- |
| `docs/reference/gateway/contracts/protocol-and-state.md` | Full `POST /v1/mail/state` contract |
| `docs/reference/gateway/operations/mailbox-facade.md` | Adapter selection, availability rules, notifier |
| `docs/reference/mailbox/contracts/runtime-contracts.md` | Projected skill contract updated |
| `docs/reference/mailbox/operations/common-workflows.md` | Gateway-first preference |

### Fixtures

| File | Area |
| --- | --- |
| `tests/fixtures/agents/roles/mail-ping-pong-initiator/system-prompt.md` | Gateway-first role prompt |
| `tests/fixtures/agents/roles/mail-ping-pong-responder/system-prompt.md` | Gateway-first role prompt |

---

## Positive Findings

### 1. Clean protocol extension pattern

The `GatewayMailboxAdapter` Protocol (`gateway_mailbox.py:49-91`) cleanly adds `update_read_state` alongside the existing `check`/`send`/`reply` methods. Both `FilesystemGatewayMailboxAdapter` and `StalwartGatewayMailboxAdapter` implement it with consistent error wrapping through `GatewayMailboxError`. The method signature uses `message_ref: str` and `read: bool` — keeping the contract narrow and consistent with the spec decision (single-target, minimal ack).

### 2. Notifier prompt is well-structured and actionable

The `_build_mail_notifier_prompt` method (`gateway_service.py:1085-1121`) produces a deterministic, gateway-first prompt:
- Nominates exactly one target (oldest-first, stable tie-breaker)
- Includes `message_ref`, optional `thread_ref`, sender context, subject, and remaining-unread count
- Explicitly names the four shared operations and tells the agent to mark read only after success
- Excludes transport-local helper references (`deliver_message.py`, `update_mailbox_state.py`)
- Test `test_gateway_mail_notifier_nominates_oldest_target_with_gateway_first_prompt` verifies all of these properties

### 3. Full-set deduplication preserved correctly

The `_mail_notifier_digest` method (`gateway_service.py:1079-1083`) hashes all `message_ref` values in the unread set, not just the nominated target. This correctly prevents duplicate wake-ups when the unread set is unchanged even if the prompt text changes.

### 4. Model validation is tight

`GatewayMailStateRequestV1` (`gateway_models.py:744-762`) uses `read: Literal[True]` and `extra="forbid"`, which means:
- Only `read=true` is accepted (no false, no other state flags)
- Extra fields like `starred`, `archived`, `deleted` are rejected with 422
- The test `test_gateway_mail_state_route_rejects_unsupported_mailbox_state_fields` verifies this

### 5. Skills are well-structured with clear priority

Both skill files lead with "Routine Actions With A Live Gateway Facade" before "Direct ... Fallback Actions". This makes the gateway-first priority architecturally visible to the agent reading the skill.

### 6. Demo pack kickoff is policy-thin

The kickoff prompt (`driver.py:518-562`) tells the initiator *what to send* and to use the runtime-owned mailbox skill, without prescribing transport mechanics. Later turns receive nominated targets from the notifier.

### 7. Comprehensive test coverage

The state route has two dedicated tests (happy path + rejection). The notifier nomination test verifies oldest-first ordering, prompt content, gateway-first language, and audit persistence. These are meaningful behavioral tests, not just smoke tests.

---

## Issues and Suggestions

### MUST FIX

#### M1. `GatewayMailStateRequestV1.read` typed as `Literal[True]` — cannot mark messages unread

**File:** `src/houmao/agents/realm_controller/gateway_models.py:749`

```python
read: Literal[True] = True
```

While the `GatewayMailboxAdapter.update_read_state` protocol accepts `read: bool`, the HTTP request model only accepts `True`. This means the API cannot be used to mark a message *unread* — which contradicts the adapter protocol's `bool` parameter and the response model's `read: bool` field. If this is intentional (v1 is read-only, no mark-unread), document the restriction explicitly in the protocol-and-state doc and add a comment on the model field. If unintentional, widen to `read: bool`.

**Recommendation:** If intentionally v1-narrowed, add a brief docstring or inline comment such as `# v1: only mark-read is supported; mark-unread deferred`. Also consider whether the adapter protocol should mirror this restriction or remain wider for future readiness.

#### M2. `_participant_from_mailbox_principal` uses unsafe `getattr` without type narrowing

**File:** `src/houmao/agents/realm_controller/gateway_mailbox.py:534-539`

```python
def _participant_from_mailbox_principal(principal: object) -> GatewayMailboxParticipantV1:
    return GatewayMailboxParticipantV1(
        address=getattr(principal, "address"),
        display_name=getattr(principal, "display_name", None),
        principal_id=getattr(principal, "principal_id", None),
    )
```

Using `getattr(principal, "address")` without a default will raise `AttributeError` at runtime if the object lacks `address` — this is effectively an unchecked cast hidden behind `object` typing. The same pattern appears in `_attachment_from_mailbox_attachment` (line 542).

**Recommendation:** Type the parameter as the actual Pydantic model (`MailboxPrincipal` or `MailboxParticipant`) imported from the protocol module, or at minimum use `getattr(principal, "address", "")` with a fallback plus validation. The `object` typing here defeats mypy's ability to catch regressions.

#### M3. Stalwart `update_read_state` inverts the read-state response without documentation

**File:** `src/houmao/agents/realm_controller/gateway_mailbox.py:518`

```python
read=not bool(payload.get("unread")),
```

The Stalwart JMAP response uses `unread: bool` while the gateway model uses `read: bool`. The negation is correct, but:
1. If the JMAP response omits `unread` entirely, `payload.get("unread")` returns `None`, `bool(None)` is `False`, and `not False` is `True` — silently treating a missing field as "read".
2. There is no assertion or validation that `unread` is actually present in the payload.

**Recommendation:** Add an explicit check: if `unread` is not in `payload` or not a `bool`, raise `GatewayMailboxError` rather than silently inferring read-state from a missing field.

### SHOULD FIX

#### S1. Duplicate `_parse_timestamp` / `_parse_gateway_timestamp` implementations

**File:** `gateway_mailbox.py:669-676` and `gateway_service.py:154-163`

These are nearly identical functions parsing ISO timestamps to UTC `datetime`. `_parse_timestamp` in `gateway_mailbox.py` and `_parse_gateway_timestamp` in `gateway_service.py` handle the same edge cases (trailing `Z`, missing timezone) the same way.

**Recommendation:** Extract into a shared utility (e.g., `gateway_models.py` or a small `gateway_utils.py`) and import from both modules. This avoids future drift if one is updated and the other forgotten.

#### S2. Filesystem adapter `check` doesn't use SQL filtering for `since` and `unread_only`

**File:** `src/houmao/agents/realm_controller/gateway_mailbox.py:115-166`

The SQL query fetches *all* rows ordered by `created_at_utc DESC`, then filters `since` and `unread_only` in Python. For a mailbox with many messages, this loads unnecessary data. The `limit` is also applied in Python after loading all messages.

**Recommendation:** Push the `since` and `unread_only` predicates into the SQL `WHERE` clause, and apply `LIMIT` in SQL. This would look like:

```sql
WHERE (? IS NULL OR message.created_at_utc >= ?)
  AND (? = 0 OR local_mailbox.message_state.is_read = 0)
ORDER BY message.created_at_utc DESC
LIMIT ?
```

This is not a correctness issue but becomes a performance issue as mailbox history grows.

#### S3. `body_text` included in every `check` response message

**File:** `src/houmao/agents/realm_controller/gateway_mailbox.py:422`

The filesystem adapter's `_message_to_model` always includes full `body_text` for every message in a check response. For a check with `limit=50`, this could be a very large response. The Stalwart adapter has the same behavior (`body` from JMAP).

**Recommendation:** Consider making `body_text` opt-in (e.g., only when `limit=1` or with a separate parameter) for list-style checks, returning only `body_preview` by default. This is a minor optimization but matters for large mailbox views.

#### S4. Notifier prompt text is tightly coupled to the runtime and not easily testable in isolation

The `_build_mail_notifier_prompt` method is a private method on `GatewayServiceRuntime`. To test the prompt structure, the test (`test_gateway_mail_notifier_nominates_oldest_target_with_gateway_first_prompt`) has to spin up a full `GatewayServiceRuntime`, enable the notifier, wait for polling, and inspect submitted prompts through a fake client.

**Recommendation:** Extract the prompt builder into a pure function (or static method) that takes `unread_messages: list[_UnreadMailboxMessage]` and returns `str`. This enables fast unit tests of prompt content without the full runtime overhead.

### NICE TO HAVE

#### N1. Consider explicit `__all__` in `gateway_mailbox.py`

The module exports the `GatewayMailboxAdapter` protocol, both transport implementations, `GatewayMailboxError`, and `build_gateway_mailbox_adapter`. An `__all__` would make the public API explicit and help IDEs auto-import correctly.

#### N2. Add type alias for the opaque `message_ref` string

Throughout the codebase, `message_ref: str` is used as an opaque shared mailbox reference. A `NewType("MessageRef", str)` would improve self-documentation and help catch accidental mixing of raw message IDs with shared refs.

#### N3. Stalwart `update_read_state` uses `keywords/$seen` — consider documenting the JMAP mapping

**File:** `src/houmao/mailbox/stalwart.py:572-589`

The mapping from the gateway `read: bool` to JMAP `keywords/$seen: bool` is a Stalwart-specific semantic. A brief inline comment explaining this mapping would help future maintainers understand the JMAP keyword semantics.

#### N4. Integration test coverage for `POST /v1/mail/state` on Stalwart transport

The current test coverage uses the filesystem adapter. If Stalwart integration is testable in CI (even with a mock JMAP server), adding a parallel test for the Stalwart path would catch regressions in the `unread`→`read` inversion logic (see M3).

---

## Spec Alignment Assessment

| Spec | Alignment |
| --- | --- |
| `agent-gateway` — `POST /v1/mail/state` route | Fully aligned. Route exists, accepts `message_ref` + `read`, rejects extra fields, returns minimal ack, does not consume queue slot. |
| `agent-gateway-mail-notifier` — actionable wake-up prompt | Fully aligned. Nominates oldest unread, includes `message_ref`, `thread_ref`, sender, subject, remaining count. Full-set deduplication preserved. |
| `agent-mailbox-protocol` — read-state as fourth operation | Aligned. `GatewayMailboxAdapter` protocol has `update_read_state` alongside `check`/`send`/`reply`. |
| `agent-mailbox-system-skills` — gateway-first structure | Aligned. Both skill files lead with gateway-first section, transport-local as explicit fallback. |
| `mail-ping-pong-gateway-demo-pack` — gateway-first demo | Aligned. Kickoff is policy-thin, role prompts use gateway-first language, no transport reconstruction. |

## Review Decisions from `review-20260323-145600.md`

| Finding | Decision | Implementation |
| --- | --- | --- |
| F1: Protocol needs `update_read_state` | Required | Done — method on `GatewayMailboxAdapter` protocol |
| F2: Deduplication must use full set | Required | Done — `_mail_notifier_digest` hashes all refs |
| F3: Read-state as fourth operation | Required | Done — adapter and docs both include it |
| F4: `_UnreadMailboxMessage` needs sender | Required | Done — has `sender_address` + `sender_display_name` |
| F5: Clarify gateway-only scope | Required | Done — docs describe loopback-only availability |
| F6: Skills distinguish gateway vs fallback | Required | Done — separate sections with clear priority |
| F7: Split documentation task | Required | Done — gateway and mailbox docs updated separately |
| Q1: Single vs batch | Single (Option A) | Done |
| Q2: Include thread_ref + count | Yes (Option A) | Done |
| Q3: Gateway-first structuring | Restructure (Option A) | Done |
| Q4: Minimal ack | Option B | Done |
| Q5: Oldest-first selection | Option A | Done |

---

## Summary

The implementation is well-executed and closely aligned with its specs. The gateway-first pattern is consistently applied across adapters, skills, notifier, demo, and docs. The main concerns are:

- **M1** (request model locked to `Literal[True]` — document or widen)
- **M2** (unsafe `getattr` on `object` defeats type safety)
- **M3** (silent `None`→`True` coercion on missing Stalwart `unread` field)

These are real issues that should be addressed before or shortly after merge. The SHOULD FIX items (duplicate timestamp parsing, in-Python filtering, full body in list checks, coupled prompt builder) are quality improvements worth tracking for near-term cleanup.

Overall: **solid implementation with clear spec traceability and good test coverage**. The three MUST FIX items are all localized and straightforward to address.
