## Context

`gateway-first-headless-mailbox-turns` introduced the shared `/v1/mail/state` route, transport-specific gateway mailbox adapters, and a normalized read-state acknowledgment returned from the gateway facade. The follow-up review found that most of the new behavior is sound, but three narrow areas still deserve cleanup:

- gateway mailbox normalization helpers currently accept `object` and use unchecked `getattr` even though the filesystem message path already carries concrete `MailboxPrincipal` and `MailboxAttachment` models,
- the local request model does not explain why v1 only accepts `read=true` even though the wider adapter interface uses `bool`, and
- the Stalwart gateway adapter derives its shared `read` acknowledgment from `payload.get("unread")` without enforcing that the normalized field is present and boolean at the final boundary.

The change is intentionally small. The broader gateway-first mailbox contract has already been synced into the main specs and archived, so this follow-up should harden the implementation without reopening unrelated product questions.

## Goals / Non-Goals

**Goals:**

- Remove unchecked type erasure from the filesystem-backed gateway mailbox normalization helpers.
- Make the bounded v1 `read=true` request intent explicit in local code near the request model and state-update path.
- Require the gateway mailbox adapter layer to validate normalized state evidence before it returns a shared `read` acknowledgment for Stalwart-backed state updates.
- Add focused tests and inline documentation that lock in the hardened behavior.

**Non-Goals:**

- Expanding the shared mailbox facade to support `read=false`, batching, or broader mailbox-state flags.
- Refactoring unrelated timestamp helpers, SQL filtering, or notifier prompt structure.
- Introducing new public mailbox routes or changing the existing successful response shape for valid state updates.
- Building a new live Stalwart integration harness beyond focused unit coverage.

## Decisions

### Decision: Gateway mailbox helper boundaries use concrete mailbox protocol models

The filesystem-backed normalization helpers in `gateway_mailbox.py` will accept the concrete mailbox protocol models they already receive from `MailboxMessage`: `MailboxPrincipal` for participants and `MailboxAttachment` for attachments.

This keeps the helper boundary aligned with the actual data model and lets static checking catch drift before runtime. It also avoids pseudo-defensive `getattr` fallbacks that would only hide a programming error until a later failure.

Alternatives considered:

- Keep `object` plus `getattr`: rejected because it preserves a runtime-only failure mode and defeats the value of the existing strict mailbox protocol models.
- Introduce a new protocol or adapter DTO layer just for helper conversion: rejected because the current call sites already use the concrete mailbox protocol models and do not need another abstraction.

### Decision: The v1 shared state-update request remains intentionally one-way

The public shared mailbox contract remains the bounded `read=true` update introduced by the prior change. This follow-up will not widen the HTTP request model or the spec to support mark-unread.

Instead, the implementation will add narrow local clarification near `GatewayMailStateRequestV1` and other closely related code so future maintainers can see that the wider internal `bool` adapter signature is a transport boundary choice, not evidence that the public request is supposed to accept `false`.

Alternatives considered:

- Widen the request model to `read: bool`: rejected because it changes the shipped v1 contract and reopens product questions that were intentionally excluded from the original design.
- Narrow every internal adapter signature to `Literal[True]`: rejected because transport-facing code benefits from a slightly broader internal shape and future changes may legitimately reuse that boundary.

### Decision: Stalwart state acknowledgments fail closed on malformed normalized state

The gateway-facing Stalwart adapter will validate that the normalized payload it receives after `update_read_state()` includes an explicit boolean `unread` signal before converting it to shared `read`.

Today the lower-level Stalwart client already normalizes `unread: bool` through `get_email()`, so this check is a defensive final boundary rather than a workaround for a known transport bug. That is still worthwhile because the gateway acknowledgment is the last place where malformed normalization could silently become a false successful `read=true` response.

The Stalwart client code will also gain a short inline note that shared `read` maps to JMAP `keywords/$seen` so the transport-specific semantics remain discoverable near the update path.

Alternatives considered:

- Trust the Stalwart client normalization and leave the adapter inference as-is: rejected because it leaves a brittle final boundary that would silently acknowledge bad data if the client changed later.
- Push the check only into the Stalwart client: rejected because the gateway adapter is the contract boundary that converts transport-normalized state into the shared acknowledgment model.

### Decision: Verification stays focused and unit-level

The follow-up will add focused unit coverage around the hardened adapter behavior and the clarified local request semantics instead of expanding into new live integration infrastructure.

That gives immediate regression protection for the accepted review items without coupling this narrow cleanup to broader Stalwart test-environment work.

## Risks / Trade-offs

- [Helper signature tightening may require small import or annotation updates] → Keep the change local to the gateway mailbox normalization path and rely on existing type-checked models rather than introducing new abstractions.
- [Fail-closed state validation could turn malformed transport normalization into explicit route failures] → Treat this as the desired behavior and cover it with focused tests so the failure mode is intentional and stable.
- [Local comments can drift from the synced spec wording] → Keep comments narrow and adjacent to the relevant model or transport code, and avoid duplicating large contract prose in implementation files.

## Migration Plan

No data migration or operator migration is required.

Implementation rollout is code-only:

1. Update gateway mailbox helper typing and read-state validation logic.
2. Refresh focused tests for the hardened failure path and clarified request semantics.
3. Land the inline code comments that explain the v1 request restriction and Stalwart `$seen` mapping.

If rollback is needed, revert the code and tests together. No persisted state shape changes are involved.

## Open Questions

- None. The review decisions already narrowed this follow-up to accepted and refined items only.
