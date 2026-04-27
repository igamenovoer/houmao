## Context

The Houmao gateway mail-notifier currently submits a generic "you have mail in inbox" reminder when a managed agent has unread inbox mail (`gateway_service.py:_build_mail_notifier_prompt`, template at `agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md`). The notifier deliberately renders no per-message content — neither subject nor body — so sender-controlled text never reaches the receiver's instruction-following surface.

Issue #48 asks for a sender-authored block that future notifier rendering can surface in that prompt. Doing this safely requires a sender-identity / sender-trust mechanism, since the new channel injects sender-controlled text directly into the receiver's prompt context. We do not want to gate the feature on building that mechanism end-to-end before any progress lands.

This change therefore separates the protocol slot from the rendering surface. It defines the canonical-envelope shape and authoring path now, leaving the gateway notifier render path content-free as it is today. A follow-on change will consume the new envelope fields, add a verifier plug, and flip the trust knobs.

## Goals / Non-Goals

**Goals:**
- Lock the canonical envelope shape for sender-marked notification content, including a forward-compatible authentication slot.
- Provide a low-friction authoring path through a Markdown body fence so existing send tooling needs minimal change.
- Reject non-`none` authentication schemes at validation in this change, so the slot's enum is committed even though no verifier ships yet.
- Bump `MAILBOX_PROTOCOL_VERSION` once and absorb the cost in the same change.
- Give operator-origin send and the `houmao-mgr agents mail` CLI surfaces clear acceptance contracts.

**Non-Goals:**
- Render the notification block in the gateway notifier prompt, the mailbox UI, or any agent-facing surface. Stays content-free until the follow-on rendering change.
- Implement any verifier (`shared-token`, `hmac-sha256`, `jws`). The enum is reserved; only `none` is accepted in this change.
- Introduce gateway notifier configuration (`notify_block_render`, `notify_block_auth_mode`, etc.). That belongs to the rendering change.
- Per-recipient state for notification blocks. The block is part of the immutable canonical envelope, not recipient state.
- Stalwart-side projection of the new fields into JMAP-native headers. Stalwart adapters preserve the canonical envelope content unchanged through the existing `headers` projection path.

## Decisions

### Decision 1 — Typed envelope fields with protocol version bump

Add `notify_block: str | None` and `notify_auth: MailboxNotifyAuth | None` directly to `MailboxMessage`, and bump `MAILBOX_PROTOCOL_VERSION` to `2`. Define `MailboxNotifyAuth` as a sealed `_StrictMailboxModel` with `scheme: Literal["none", "shared-token", "hmac-sha256", "jws"]`, `token`, `iss`, `iat`, `exp`.

Alternatives considered:
- **Open `headers` dict (`x-houmao-notify`, `x-houmao-notify-auth`)** — zero schema cost but no validation, every consumer hand-parses, future verifier work has no compile-time contract.
- **Single union field carrying both block and auth** — collapses two concepts; rejected because they have different lifecycles (block extraction is one-shot at composition; auth is a separate verifier concern).

Rationale: pydantic v2 validation, IDE/mypy support, single canonical shape consumed by both filesystem and Stalwart transports, and clarity for the upcoming verifier work. The cost — one protocol version bump — is acceptable per CLAUDE.md's "breaking changes are allowed" stance.

### Decision 2 — Markdown fenced code block as authoring surface

Senders author the notification block as a fenced code block with info-string `houmao-notify`:

```text
```houmao-notify
If speedup ≥ 50x, re-run on official timing path before reporting.
```
```

Alternatives considered:
- **`:::houmao-notify ... :::` admonition fence** (issue author's sketch) — not part of CommonMark, renders as literal text in plain renderers, harder to extract robustly.
- **Header-only authoring** (no body fence; `--notify-block` flag mandatory) — clean machine surface but every send path needs an explicit param, and authoring agents are unlikely to know to use it.

Rationale: CommonMark-native fences render gracefully in every Markdown viewer, are unambiguous for regex extraction with the `houmao-notify` info-string, and let humans see the same sender intent inline.

### Decision 3 — Composition-time extraction, body source preserved

Canonical-message construction extracts the first `houmao-notify` fenced block in `body_markdown` into the typed `notify_block` field, after trimming surrounding whitespace and applying the size cap. The body source is not modified — the original fence stays in `body_markdown` so receivers reading the full message see the same text.

Alternatives considered:
- **Per-read extraction** (notifier scans body each poll) — re-parse cost, no canonical record of what got extracted, harder to audit.
- **Strip the fence from the body after extraction** — surprises authors reading raw stored mail; receivers opening the message would see the extracted block twice (in audit/notifier and in body) but that's the same in both options once notifier renders.

Rationale: parse once, store canonical, leave source authoritative. The fence stays in the body so authors can validate what they wrote and so existing renderers display it as a normal code block.

### Decision 4 — First-occurrence wins, multiple fences allowed in body

When a body contains more than one `houmao-notify` fence, the first occurrence (lowest source offset) is extracted. Additional occurrences remain in the body but are not extracted.

Alternatives considered:
- **Reject messages with more than one fence** — surfaces ambiguity at send time but adds an authoring failure mode for agents that include the fence inside quoted history.
- **Concatenate all fences** — dilutes sender intent and complicates the size cap.

Rationale: deterministic, forgiving toward forwarded/quoted content, and easy to specify.

### Decision 5 — 512-character extracted block cap with explicit truncation marker

Extracted `notify_block` content SHALL be at most 512 characters. Content longer than that SHALL be truncated to 511 characters plus a single trailing `…` (U+2026). Truncation SHALL be visible in the stored field — no hidden silent drop.

Rationale: keeps eventual notifier prompts cheap, prevents abuse of the channel for body-length payloads, and gives callers a deterministic upper bound. The follow-on rendering change can apply an additional total-prompt cap across multiple unread messages without re-deriving per-message limits.

### Decision 6 — Reject non-`none` `scheme` values during this change

Validation accepts only `scheme="none"` for `notify_auth` in this change. The other enum members (`shared-token`, `hmac-sha256`, `jws`) are present in the `Literal` so callers and stored data using them in the future do not require another envelope-level change, but this change rejects them at validation time with a clear "verifier not yet supported" error.

Alternatives considered:
- **Accept all schemes; ignore unknown ones at render time** — silently accepts garbage, leaks half-built features.
- **Restrict the enum to `Literal["none"]` and widen it later** — every future verifier is a protocol bump.

Rationale: locks the shape, keeps storage and validation honest, and gives the follow-on change a one-line validator update rather than a schema migration.

### Decision 7 — `--notify-block` CLI flag overrides body-fence extraction

`houmao-mgr agents mail send` and `houmao-mgr agents mail post` gain `--notify-block <text>`. When supplied, the flag value SHALL be used directly (subject to the same size-cap and validation), and any body-fence content SHALL NOT be re-extracted on top of it. When omitted, body-fence extraction proceeds as the default authoring path.

Rationale: gives scripted callers a deterministic non-Markdown path while keeping the body-fence form as the natural authoring surface.

### Decision 8 — Operator-origin send shares the same composition path

Operator-origin send composes canonical messages through the same `MailboxMessage` constructor, so the extraction, validation, and size-cap rules apply identically. No separate operator-origin code path for notification blocks.

Rationale: avoids divergence and matches how operator-origin send already inherits the rest of the canonical envelope contract.

## Risks / Trade-offs

- **Risk**: callers stuff long content into `notify_block` to bypass body length norms → **Mitigation**: 512-character cap with visible truncation; the field is documented as a short instruction surface, not a body alternative.
- **Risk**: protocol bump breaks readers of older stored canonical messages on filesystem mailboxes → **Mitigation**: keep both fields optional; readers ignore unknown future-versioned envelopes only when validation explicitly opts in. Spec change covers backwards-compat semantics for missing fields.
- **Risk**: sender uses `notify_auth.scheme="none"` and a future operator flips notifier `auth_mode` to `required` → **Mitigation**: `none` is documented as "no claim of identity beyond the canonical sender principal"; the rendering change is responsible for defining how `required` interacts with `none`-scheme blocks (most likely: drop and audit).
- **Risk**: body-fence extraction misfires on quoted history that included a `houmao-notify` fence from an earlier message → **Mitigation**: first-occurrence-wins is deterministic; senders forwarding history should re-author the block intentionally. Documented as a known authoring constraint, not silently corrected.
- **Risk**: large-scale audits of stored mail need to re-extract blocks → **Mitigation**: extraction happens once at composition; the canonical field is the source of truth thereafter. Re-extraction tooling is out of scope.
- **Trade-off**: declaring the `scheme` enum without shipping verifiers means stored data may name schemes whose semantics are not yet defined. We accept this because the alternative — narrowing the enum and bumping again later — is worse.
- **Risk**: Stalwart-bound mailboxes do not yet project canonical envelope fields into JMAP-native headers, so naively passing `notify_block`/`notify_auth` through would drop sender intent silently → **Mitigation**: the Stalwart gateway adapter accepts the new params for protocol-conformance and raises `GatewayMailboxUnsupportedError` when either is non-`None`. Stalwart-side projection lands in a follow-on change that wires `X-Houmao-Notify-Block` / `X-Houmao-Notify-Auth` headers through the JMAP client. Filesystem mailboxes are fully covered by this change.

## Migration Plan

1. Land protocol model + extractor + validation in one PR. Existing canonical messages without the new fields remain valid because both fields are optional.
2. Bump `MAILBOX_PROTOCOL_VERSION` to `2`. Document in `docs/reference/mailbox/` that v2 envelopes carry the new optional fields.
3. Update operator-origin send and the gateway `/v1/mail/send` handler in the same PR; both run through the same constructor.
4. Update `houmao-mgr agents mail send|post` CLI flags in the same PR.
5. Tests: protocol unit, extractor edge cases (no fence, single fence, multiple fences, fence with non-string info-string surroundings, oversized block, empty block, body with only the fence), CLI integration, filesystem and Stalwart round-trips, operator-origin path.
6. Rollback: revert is a straight schema downgrade; v2 envelopes with populated `notify_block`/`notify_auth` regress to ignored fields under v1 readers if those fields were stored as plain JSON. No data loss for `body_markdown` content because the fence remains in the body source.
7. The follow-on rendering change consumes these fields without modifying the protocol again.

## Open Questions

- Should the `notify_auth.iat`/`exp` fields be ISO-8601 strings (consistent with `created_at_utc`) or epoch seconds? Default proposal: ISO-8601 strings, matching the rest of the envelope.
- For Stalwart-backed transports, should the typed fields project into JMAP keywords or `X-Houmao-*` headers? Default proposal: existing `X-Houmao-*` header convention via the transport's existing header projection. No new JMAP keyword in this change.
- For nested/quoted messages where the `houmao-notify` fence was authored by a prior sender, do we want a structured way to disable extraction for that mail? Default proposal: no — first-occurrence-wins is deterministic and authoring discipline is sender's responsibility. Revisit if real-world abuse appears.
