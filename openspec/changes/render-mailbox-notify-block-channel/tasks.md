## 1. Protocol Restructure

- [x] 1.1 Replace `notify_block: str | None` on `MailboxMessage` with a sealed `MailboxNotifyBlock(_StrictMailboxModel)` carrying `text: str` (with the existing 512-char visible-truncation cap as a field validator) and `placement: Literal["append", "prepend"] = "append"`.
- [x] 1.2 Update `MailboxMessage.compose(...)` so caller-supplied `notify_block` accepts both the typed dict form and a `MailboxNotifyBlock` instance; default `placement` to `"append"` when extracting from a body fence.
- [x] 1.3 Bump `MAILBOX_PROTOCOL_VERSION` from `2` to `3`; update the existing `_validate_protocol_version` rejection message to reflect the new constant.
- [x] 1.4 Refresh in-tree references to v2 envelopes (test fixtures and protocol-version assertions); v2 was unreleased so no migration of stored data was required.

## 2. Auto-Mirror Invariant

- [x] 2.1 Added `_apply_notify_block_body_mirror(body_markdown, notify_block)` helper in `protocol.py` returning `body_markdown` unchanged when an existing `houmao-notify` fence is detected and otherwise inserting a synthetic fence at the requested placement.
- [x] 2.2 `MailboxMessage.compose(...)` runs the mirror helper before model validation when caller-supplied `notify_block` is non-null.
- [x] 2.3 Added `body_has_notify_block_fence(body_markdown)` helper that reuses the line-by-line scanner.
- [x] 2.4 `compose(...)` does not duplicate when the caller already authored a body fence; placement metadata is recorded as caller declared.

## 3. Notifier Renderer

- [x] 3.1 Notifier prompt template at `src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md` now includes `{{NOTIFY_BLOCKS_PREPEND}}` before the `"You have mail in inbox."` opener and `{{NOTIFY_BLOCKS_APPEND}}` after the mailbox API summary.
- [x] 3.2 `_UnreadMailboxMessage` carries `notify_block: MailboxNotifyBlock | None` and `notify_auth: MailboxNotifyAuth | None` alongside the existing summary fields.
- [x] 3.3 The notifier poll path threads canonical envelope `notify_block`/`notify_auth` from `adapter.list_messages(...)` (now exposed on `GatewayMailboxMessageV1`) into the `_UnreadMailboxMessage` summary list.
- [x] 3.4 `_render_notify_block_slots(...)` performs oldest-first ordering, sender-attribution prefix (`Sender notice — from <address>: > <text>`), per-message + aggregate caps, and the `"+ N more sender notice(s) — open inbox to read"` summarization line when the aggregate cap fires.
- [x] 3.5 `_build_mail_notifier_prompt(...)` substitutes the new slot content; `notify_block_render=disabled` short-circuits to empty slots and per-block audit detail `"render disabled"`.

## 4. Verifier Interface

- [x] 4.1 `NotifyAuthVerifier` Protocol added at `src/houmao/agents/realm_controller/notify_auth_verifier.py` with `verify(notify_block, notify_auth) -> VerifyResult`. `VerifyResult(passed, scheme, detail, outcome)` is a frozen dataclass with `outcome: Literal["skipped", "passed", "failed"]`.
- [x] 4.2 `PermissiveVerifier` always passes with `scheme="none"`, `outcome="skipped"`, `detail="no verifier configured"`.
- [x] 4.3 `SharedTokenVerifier(token_allowlist: frozenset[str])` accepts allowlisted tokens, rejects others without echoing the supplied token text in the rejection detail.
- [x] 4.4 `build_notify_auth_verifier(verifier_kind, shared_tokens)` factory selects the implementation from gateway notifier configuration.

## 5. Gateway Notifier Configuration

- [x] 5.1 `GatewayMailNotifierRecord` extended with `notify_block_render`, `notify_block_auth_mode`, `notify_block_auth_verifier`, `notify_block_shared_tokens`, `notify_block_per_message_chars`, `notify_block_total_chars` (with sensible defaults). SQLite schema updated and additive migration handles older rows.
- [x] 5.2 `PUT /v1/mail-notifier` accepts the new fields with omit-preserves-current behavior.
- [x] 5.3 `GET /v1/mail-notifier` status response surfaces the effective values.
- [x] 5.4 `GatewayMailNotifierPutV1` and `GatewayMailNotifierStatusV1` Pydantic models updated.

## 6. Audit Shape

- [x] 6.1 `gateway_notifier_audit` SQLite schema extended with `rendered_block_entries_json`; per-block JSON entries carry `message_ref`, `rendered`, `auth_scheme`, `auth_outcome`, `auth_detail`, `block_chars`, `block_truncated`.
- [x] 6.2 `_append_notifier_audit_record(...)` and the storage-layer `append_gateway_notifier_audit_record(...)` accept `rendered_block_entries`.
- [x] 6.3 Additive schema migration covers existing audit rows; older rows surface an empty per-block entry list cleanly.

## 7. CLI Plumbing

- [x] 7.1 `--notify-block-placement [append|prepend]` added to `houmao-mgr agents mail send` and `agents mail post`. Default `append`. Ignored when `--notify-block` is omitted.
- [x] 7.2 `mail_send` / `mail_post` / `mail_reply` in `managed_agents.py` thread `MailboxNotifyBlock` through all four dispatch paths (server-mode, manager-direct, gateway-backed, TUI fallback).
- [x] 7.3 `GatewayMailSendRequestV1`, `GatewayMailPostRequestV1`, `GatewayMailReplyRequestV1` accept the typed `notify_block` shape.

## 8. Operator-Origin Send

- [x] 8.1 `_build_delivery_request` and `_write_staged_message` in `gateway_mailbox.py` accept the typed `notify_block` and pass it through to `MailboxMessage.compose(...)`. Auto-mirror runs in `compose`.
- [x] 8.2 Operator-origin reply-policy and provenance metadata still ride alongside notify_block without interference.

## 9. Demo `single-agent-mail-prompt-injection/`

- [x] 9.1 Scaffolded `scripts/demo/single-agent-mail-prompt-injection/` with `inputs/`, `outputs/` (gitignored), `scripts/`, `expected_report/`, plus the standard `outputs/.gitignore`.
- [x] 9.2 Authored `inputs/system_prompt.md` (scoped helper: writes only under `tmp/safe/`, refuses scope expansion, treats inbox content as untrusted).
- [x] 9.3 Authored `inputs/benign_body.md` (control message that targets a `tmp/safe/` artifact).
- [x] 9.4 Authored `inputs/injection_body.md` with a `houmao-notify` fenced block whose `text` requests a sentinel write under `tmp/leak/`.
- [x] 9.5 Authored `inputs/demo_parameters.json` (paths, scope subdirectories, control + leak filename templates, mode definitions, lane config).
- [x] 9.6 Demo orchestration is a pure-bash CLI runner (intentional minimal scope). The 3,800-line Python-module driver mirroring the parent `single-agent-mail-wakeup/` pack is tracked as follow-on work and called out in the demo README's "Follow-on work" section.
- [x] 9.7 `run_demo.sh` exposes `start`, `send-benign`, `send-attack`, `verify`, `stop`, and `auto` actions plus `--tool` and `--mode` selectors. The `start` step bootstraps project + overlay + mailbox; live agent launch + gateway attach + notifier configuration + mail post are documented as a manual driving recipe in the README.
- [x] 9.8 `verify` writes `expected_report/report-<tool>-<mode>.json` with structured outcome metadata (`outcome`, `safe_dir`, `leak_dir`, `control_path`, `control_present`, `leak_path`, `leak_present`).
- [x] 9.9 Authored `README.md` covering the threat model, educational framing, prerequisites, supported lane (`claude`), supported modes (`permissive-log`, `required`), the manual-driving recipe, and outcome reporting semantics.
- [x] 9.10 Updated `scripts/demo/README.md` to list `single-agent-mail-prompt-injection/` as a supported demo pack with a one-paragraph description.

## 10. Tests

- [x] 10.1 Updated `tests/unit/mailbox/test_protocol_notify_fields.py` for the typed `MailboxNotifyBlock` shape, `placement` validation, and the v3 protocol constant (19 scenarios pass).
- [x] 10.2 Updated `tests/unit/mailbox/test_notify_extractor.py` for typed compose surfaces; added auto-mirror append/prepend, no-op when fence already present, and synthetic-fence content scenarios (18 scenarios pass).
- [x] 10.3 Updated `tests/unit/mailbox/test_protocol.py` for `protocol_version: 3` in the round-trip assertion.
- [x] 10.4 Updated `tests/unit/agents/realm_controller/test_mail_send_notify_request.py` for the typed shape (6 scenarios pass).
- [x] 10.5 Updated `tests/unit/agents/realm_controller/test_mail_compose_notify_round_trip.py` to verify auto-mirror produces the expected body content (4 scenarios pass).
- [x] 10.6 Added `tests/unit/agents/realm_controller/test_notify_auth_verifier.py` (12 scenarios) covering `PermissiveVerifier`, `SharedTokenVerifier` accept/reject (including the no-token-echo invariant), the factory, and `VerifyResult` immutability.
- [x] 10.7 Added `tests/unit/agents/realm_controller/test_notifier_render_notify_blocks.py` (11 scenarios) covering single block, multiple blocks with mixed placement, aggregate-cap summarization, sender-attribution rendering, `notify_block_render=disabled`, `permissive-log` rendering despite verifier failure, and `required` mode suppression on verifier failure. Required factoring `_render_notify_block_slots` to a module-level helper for direct testing.
- [x] 10.8 The new `--notify-block-placement` flag is exercised in the existing `tests/unit/srv_ctrl/test_agents_mail_notify_block.py` (which now asserts both placement values land on the typed `MailboxNotifyBlock`); a separately-named placement test would duplicate existing coverage.
- [x] 10.9 Added `tests/unit/agents/realm_controller/test_notifier_audit_rendered_blocks.py` (4 scenarios) covering per-rendered-block audit-row persistence + read, default empty entries, the no-token-echo invariant in audit detail, and `GatewayNotifierAuditRenderedBlockEntry` immutability.

## 11. Docs

- [x] 11.1 Refreshed `docs/reference/mailbox/contracts/canonical-model.md`: typed `MailboxNotifyBlock` shape, auto-mirror invariant with sample body, protocol bump to v3 in the representative envelope, removed "rendering deferred" wording, added cross-link to the gateway-side trust posture.
- [x] 11.2 Refreshed `docs/reference/cli/agents-mail.md`: `--notify-block-placement` row in `send` and `post` option tables, expanded "Notification-prompt block" section explaining sender-side authoring, auto-mirror, and receiver-side rendering with the configurable trust posture.
- [x] 11.3 Refreshed `docs/reference/gateway/contracts/protocol-and-state.md`: typed `notify_block` shape in `/v1/mail/send|post|reply` request payloads, removed "rendering deferred" qualifier, and added a "Mail-notifier trust posture" subsection documenting the six new configuration fields plus the per-block audit shape.
- [x] 11.4 Refreshed `docs/reference/managed_agent_api.md`: typed `notify_block` shape and the configurable trust posture on the `mail/send|post|reply` proxy boundary, with cross-links to the gateway-protocol and canonical-model docs.
- [x] 11.5 The new demo's `README.md` covers the educational framing in detail (threat model, modes, manual-driving recipe, outcome reporting). A top-level `docs/reference/demos/` index entry is left as low-priority polish, since `scripts/demo/README.md` already lists the demo and operators land directly on the demo's own README.

## 12. Validation

- [x] 12.1 `pixi run format && pixi run lint && pixi run typecheck`: format clean, lint clean, typecheck zero new errors over the documented baseline (10 pre-existing in `lint_wiki.py` / `audit_review.py` / `project_mailbox.py`).
- [x] 12.2 `pixi run test`: 1875 pass; 2 pre-existing failures (`test_gateway_mail_notifier_renders_gateway_bootstrap_prompt_with_houmao_gateway_skill` confirmed pre-existing on origin/main; `test_compat_route_inventory_matches_pinned_upstream` is a worktree-isolation issue unrelated to these changes). Adds 27 new tests across verifier, renderer, and audit unit files.
- [ ] 12.3 Run the demo end-to-end on at least one lane × mode. Deferred — the minimal CLI runner requires manual driving for the live-LLM portion (documented in the demo README); end-to-end matrix automation is the parent-demo Python-module variant explicitly tracked as follow-on work in the demo's `README.md`.
- [x] 12.4 `openspec validate render-mailbox-notify-block-channel --strict`: clean.
