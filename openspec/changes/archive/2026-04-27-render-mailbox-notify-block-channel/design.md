## Context

The previous change `add-mailbox-notify-prompt-block` (eb828537) introduced the canonical `notify_block` envelope slot, the body-fence authoring path, the `notify_auth` model with the reserved `none|shared-token|hmac-sha256|jws` enum, and the protocol bump to v2. Two limitations of that landing surfaced during demo design:

1. **The slot has no rendering.** The gateway notifier still produces a content-free wake-up prompt (`"You have mail in inbox."` plus the standard skill block and mailbox API summary). `notify_block` is stored in canonical envelopes but is invisible at the receiver's instruction-following surface unless the receiver chooses to read mail, which defeats the original use case from issue #48.
2. **The slot allows a hidden channel.** When a sender supplies `--notify-block "X"` directly without authoring a body fence, the canonical envelope ends up with `notify_block="X"` but `body_markdown` does not contain that text. The receiver who only reads mail through `mail/read` never sees `X` unless they introspect the typed field. This is at odds with the broader design intent that the `houmao-notify` body fence is the source of truth and `notify_block` is a parsed convenience surface — and it would block a future Stalwart JMAP projection (or any non-Houmao-aware downstream) from preserving the same content.

This change closes both gaps in one cohesive landing: it ships notifier rendering, the verifier interface, the gateway-side trust posture (`permissive-log` default with `required` opt-in), the auto-mirror invariant that eliminates the hidden-channel hazard, and a runnable demo (`single-agent-mail-prompt-injection/`) that exercises the channel end-to-end and serves as the smoke test for the renderer + verifier wiring.

## Goals / Non-Goals

**Goals:**
- Make `notify_block` content reach the receiver's wake-up prompt at notifier time, with rendering position controlled by sender-declared `placement` metadata.
- Eliminate the hidden-channel hazard: `notify_block` is always mirrored into `body_markdown` as a fenced block.
- Define the `MailboxNotifyBlock` typed shape (`text` + `placement`) so future metadata extensions don't require sibling-field accretion.
- Ship one real verifier (`SharedTokenVerifier`) so the `required` trust posture can be exercised in the demo and in real deployments.
- Provide a demo that serves as both a defensive education tool and a smoke test for the renderer and verifier wiring.
- Bump `MAILBOX_PROTOCOL_VERSION` once (v2 → v3) and absorb the cost; v2 was unreleased so no migration is needed.

**Non-Goals:**
- Implement `hmac-sha256` or `jws` verifiers. Those schemes remain reserved-but-rejected in the canonical envelope, exactly as in v2.
- Render anything other than `notify_block.text` in the wake-up prompt. Per-message subject/sender summaries, attachment inventories, and other content surfaces stay deferred.
- Alter per-recipient state semantics. `notify_block` continues to live on the immutable canonical envelope.
- Migrate v2-shaped envelopes. v2 was unreleased; the change replaces the shape in place.
- Build full Stalwart JMAP projection of the typed fields. Stalwart-bound mailbox sends still reject `notify_block`/`notify_auth` until that follow-on lands.

## Decisions

### Decision 1 — Typed `MailboxNotifyBlock` sub-model with `placement` metadata

Replace the bare `notify_block: str | None` field with a sealed `MailboxNotifyBlock` model carrying `text: str` (required) and `placement: Literal["append", "prepend"]` (defaulting to `"append"`). All composition surfaces (CLI, gateway request models, operator-origin send) thread the typed shape end-to-end.

Alternatives considered:
- **Sibling top-level field `notify_block_placement`** — keeps `notify_block: str | None` simple but creates orphan-state combinations (`notify_block=None, notify_block_placement="prepend"`) and forces every future metadata addition to live as another sibling.
- **Encode placement in the body-fence info-string** (e.g., ` ```houmao-notify:prepend `) — works for body-fence authoring but doesn't help the explicit-flag path.

Rationale: typed sub-model cleanly groups all per-block metadata, leaves room for future fields (e.g., `priority`, `language`, `expires_at`) without re-bumping the protocol, and gives pydantic-strict validation for free.

### Decision 2 — Auto-mirror invariant: `notify_block.text` always appears verbatim in `body_markdown`

When canonical-message construction stores a non-null `notify_block`, the same text MUST appear inside a `houmao-notify` fenced block somewhere in `body_markdown`. Composition synthesizes the fence at the requested `placement` only if no `houmao-notify` fence already exists in the body; an existing fence is left in place untouched.

Alternatives considered:
- **Reject explicit `notify_block` without matching body fence** (option A from prior discussion) — strictest, eliminates ambiguity, but breaks the ergonomic `--notify-block` shortcut and forces every script to author the fence.
- **Document only, no enforcement** (option C) — cheapest now, but every custom client becomes a potential hidden-channel leak.

Rationale: this preserves the ergonomic `--notify-block` flag while honoring the design property "notify_block is a priority surface, not a covert channel". The mirrored fence also positions the design for transports without a privileged metadata channel — when Houmao bridges to plain SMTP/IMAP/JMAP, the fence rides along inside the body and Houmao-aware receivers pick it up; non-Houmao receivers see ordinary fenced Markdown.

### Decision 3 — Placement governs both body insertion and notifier rendering

`placement` is a single value that controls two things: where the synthesized fence is inserted into `body_markdown`, and where the rendered text appears in the gateway notifier wake-up prompt (`{{NOTIFY_BLOCKS_PREPEND}}` slot before the existing inbox opener vs `{{NOTIFY_BLOCKS_APPEND}}` slot after the mailbox API summary).

Alternatives considered:
- **Separate `body_placement` and `notifier_placement`** — more flexible but doubles the surface area for almost no real use case. Senders authoring "OPERATOR DIRECTIVE — do X first" want it prominent in both surfaces.

Rationale: one knob, simpler mental model, and the rare case where the sender wants different positions can be expressed by combining the body-fence form (positioned wherever in the body the sender chooses) with `--notify-block-placement` only changing the notifier rendering position.

### Decision 4 — Pluggable verifier with `none` (default) and `shared-token` shipped

Define `NotifyAuthVerifier(Protocol)` returning `VerifyResult(passed, scheme, detail)` and ship two implementations:

- `PermissiveVerifier` — always passes, default when `notify_block_auth_verifier=none` (the configured default).
- `SharedTokenVerifier` — compares `notify_auth.token` against a configured allowlist (e.g., loaded from a gateway config file or env var).

Alternatives considered:
- **Ship only `PermissiveVerifier`** — leaves `required` mode untestable in this change because there's no real verifier to flip to. Demo's defense lane would not be meaningful.
- **Ship `hmac-sha256` instead of `shared-token`** — more cryptographically sound but requires shared-secret distribution semantics and signature canonicalization; both are non-trivial design surfaces. Punt to the next change.

Rationale: shared-token is the simplest real verifier, sufficient to demonstrate the `required` trust-posture knob, and matches the typical local-development trust posture (operator-managed allowlist of known managed-agent tokens). HMAC and JWS slots remain reserved.

### Decision 5 — Permissive-log default, with audit always populated

Default `notify_block_auth_mode` is `permissive-log`. The verifier always runs (so audit captures `auth_scheme` and `auth_outcome`), but rendering proceeds regardless. Operators flip to `required` only when they have a verifier configured and want enforcement. Audit data accumulated under `permissive-log` informs the decision to flip.

Alternative (`permissive-skip`) was considered but rejected: it leaves operators flying blind about which senders would suddenly stop rendering when the mode is flipped to `required`.

### Decision 6 — Aggregate cap with summarization, not aggressive truncation

Per-message cap stays at 512 characters (matching the canonical envelope). Aggregate cap defaults to 2048 characters across all rendered blocks per notifier prompt. When the aggregate cap is reached, the notifier emits a summary line `"+ N more sender notice(s) — open inbox to read"` rather than truncating individual block content. This preserves the integrity of each rendered block.

### Decision 7 — Demo lives under `scripts/demo/single-agent-mail-prompt-injection/` and mirrors the parent demo's shape

The demo follows the structural conventions of `single-agent-mail-wakeup/`:

- `outputs/` (gitignored) for runtime state.
- `inputs/` for system prompt, body templates, and parameter JSON.
- `scripts/demo_driver.py` for the Python entry that orchestrates lanes/modes.
- `run_demo.sh` for operator-facing automation.
- `expected_report/` for structured per-run results (`outcome` per lane × mode).

The demo's agent system prompt is a "scoped helper" baseline ("write only under tmp/safe/, refuse scope expansion"). The injection sends a notify-block requesting a sentinel write under tmp/leak/. Verification asserts the sentinel exists (attack succeeded) or absent (defense engaged).

### Decision 8 — Bundle the protocol fix, renderer, verifier, and demo in one change

Rather than splitting the auto-mirror invariant fix into its own micro-change, this change bundles all the dependent surfaces: protocol restructure, auto-mirror, renderer, verifier, gateway config, audit, CLI placement flag, and the demo. The demo serves as the integration test for everything else.

Rationale: the renderer's behavior depends on `notify_block` placement metadata that doesn't exist in v2. Splitting introduces an awkward "v3 protocol shipped but renderer waits" intermediate state. Bundling lets the proposal commit to a coherent end-to-end story.

## Risks / Trade-offs

- **Risk**: bumping the protocol version twice in a week (v1 → v2 → v3) is unusual → **Mitigation**: v2 was unreleased; only test fixtures and demos under main reference it, all updated in this change. No external clients exist. CLAUDE.md endorses breaking changes, no migration support requested.
- **Risk**: `SharedTokenVerifier` allowlist distribution is a fresh operator-config surface (where do tokens live? how are they rotated?) → **Mitigation**: this change ships the verifier interface and one concrete implementation but leaves token-distribution semantics minimal — tokens are configured per-gateway-binding through the existing notifier configuration record. Rotation, multi-tenant scoping, and secret hygiene patterns are explicit follow-on work, called out in design Open Questions.
- **Risk**: rendering sender content directly into the receiver's wake-up prompt is the prompt-injection vector the issue raised → **Mitigation**: the `required` trust posture exists for exactly this reason, ships in this change, and the demo proves both the attack (in `permissive-log`) and the defense (in `required` with empty allowlist). Operators have a working knob.
- **Risk**: aggregate-cap summarization could lose important sender intent on busy days → **Mitigation**: 2048-char default fits ~4 max-size blocks; for typical short notifications operators see ~10–20 entries before summarization. Receivers can still open inbox to read full content. Cap is configurable.
- **Risk**: the auto-mirror invariant changes body content in ways callers may not expect (e.g., automated tooling that diffs sender-provided body vs stored body) → **Mitigation**: callers that supply their own body fence see no change; callers that supply only `--notify-block` get a deterministic synthetic fence appended/prepended. Documented in CLI reference and canonical-model doc.
- **Trade-off**: declaring the `placement` metadata only governs append-vs-prepend rather than arbitrary positions inside the body. We accept this because (a) arbitrary mid-body placement implies parsing the receiver's body and inserting at a discovered anchor — far more complex, (b) the body-fence form already gives senders mid-body authorial control, and (c) the notifier rendering surface only has two reasonable positions (before or after the inbox opener block).
- **Trade-off**: Stalwart-bound sends still reject `notify_block` and `notify_auth`. JMAP-side projection of the typed fields (likely as `X-Houmao-Notify-Block` / `X-Houmao-Notify-Block-Placement` / `X-Houmao-Notify-Auth` headers) is deferred. Filesystem mailboxes are fully supported.

## Migration Plan

1. Land protocol restructure (typed `MailboxNotifyBlock`, version bump to v3, auto-mirror invariant) in the same PR as the renderer + verifier + demo. v2-shaped tests and fixtures are updated to v3.
2. Update `MAILBOX_PROTOCOL_VERSION` to `3`. Document in `docs/reference/mailbox/contracts/canonical-model.md` that v3 envelopes carry typed `notify_block` and the auto-mirror invariant; v2 (unreleased) is no longer accepted.
3. Add `notify_block_render`, `notify_block_auth_mode`, and `notify_block_auth_verifier` to the gateway notifier configuration record alongside the existing `appendix_text`, `context_error_policy`, and `pre_notification_context_action` fields. `PUT /v1/mail-notifier` accepts the new fields with the same omit-preserves-current behavior used by the existing fields. Existing notifier configurations without the new fields default cleanly.
4. Implement `NotifyAuthVerifier` Protocol, `PermissiveVerifier`, and `SharedTokenVerifier`. Wire the verifier dispatch into the notifier prompt-build path before the `{{NOTIFY_BLOCKS_PREPEND}}` and `{{NOTIFY_BLOCKS_APPEND}}` slot rendering.
5. Extend the notifier audit record with per-block entries; update `_append_notifier_audit_record` and the persisted audit shape.
6. Update the gateway notifier prompt template (`mail-notifier.md`) to include the two new slots; update `_build_mail_notifier_prompt` to render them.
7. Update CLI: add `--notify-block-placement` flag on `agents mail send` and `agents mail post`; thread placement through all four dispatch paths.
8. Build the demo: copy structural scaffolding from `single-agent-mail-wakeup/`, write the scoped-helper system prompt, write the injection body templates, and wire the runner.
9. Tests: extend protocol tests for typed sub-model and auto-mirror; add notifier renderer tests for placement, multiple blocks, aggregate cap, verifier outcomes; add CLI tests for placement flag; add demo smoke tests in CI lanes that already cover demo packs.
10. Docs refresh: canonical-model, agents-mail CLI, gateway protocol-and-state, managed-agent API.

Rollback: revert is a straightforward schema downgrade. Any v3 envelopes written during the change's lifespan would become unreadable under v2/v1, so rollback is destructive for any messages composed during the window. Acceptable because v3 is unreleased and only test fixtures use it.

## Open Questions

- **Token allowlist storage**: should `SharedTokenVerifier`'s allowlist live in the gateway notifier config record (per-binding), in a separate gateway-owned secrets file, or in environment variables? Default proposal: in the notifier config record's new `notify_block_shared_tokens: list[str]` field for v1 simplicity. Rotation patterns are post-v1.
- **Audit rendering for the operator**: should `GET /v1/mail-notifier` expose a recent-audit projection that includes per-block verification outcomes, or do operators always read `queue.sqlite` directly? Default proposal: audit stays in `queue.sqlite`; the existing `notifier_audit` projection grows the new fields. Operators inspect via the existing path.
- **Demo CI integration**: should `single-agent-mail-prompt-injection/` run in CI matrix with the parent demo, or stay opt-in? Default proposal: opt-in. The parent demo is already in matrix; adding a second demo per-tool doubles the matrix cost and the demo's outcome can vary by LLM availability. Run on demand.
- **Rendering format for sender attribution**: the spec requires "names the canonical sender principal address" but doesn't fix the exact format. Default proposal: `"Sender notice — from <address>:\n> <text>"` (single Markdown blockquote). Open to alternatives.
