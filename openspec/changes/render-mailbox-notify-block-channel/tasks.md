## 1. Protocol Restructure

- [ ] 1.1 Replace `notify_block: str | None` on `MailboxMessage` with a sealed `MailboxNotifyBlock(_StrictMailboxModel)` carrying `text: str` (with the existing 512-char visible-truncation cap as a field validator) and `placement: Literal["append", "prepend"] = "append"`.
- [ ] 1.2 Update `MailboxMessage.compose(...)` so caller-supplied `notify_block` accepts both the typed dict form and a `MailboxNotifyBlock` instance; default `placement` to `"append"` when extracting from a body fence.
- [ ] 1.3 Bump `MAILBOX_PROTOCOL_VERSION` from `2` to `3`; update the existing `_validate_protocol_version` rejection message to reflect the new constant.
- [ ] 1.4 Remove or update any in-tree references to v2 envelopes (test fixtures, doc samples, demo snapshots) that would otherwise become invalid.

## 2. Auto-Mirror Invariant

- [ ] 2.1 Add a helper `_apply_notify_block_body_mirror(body_markdown, notify_block)` in `protocol.py` that returns `body_markdown` unchanged when an existing `houmao-notify` fence is detected and otherwise inserts a synthetic fence at the requested placement (`prepend` before existing content, `append` after).
- [ ] 2.2 Wire the mirror helper into `MailboxMessage.compose(...)` so caller-supplied `notify_block` triggers mirroring before model validation.
- [ ] 2.3 Add a fence-detection helper that returns whether `body_markdown` contains a `houmao-notify` fenced code block; reuse the line-by-line scanner already used by `extract_notify_block_from_body`.
- [ ] 2.4 Ensure `MailboxMessage.compose(...)` does not run the mirror when the caller authored the body fence themselves (existing fence detected); record `placement` metadata as caller declared without relocating the fence.

## 3. Notifier Renderer

- [ ] 3.1 Update the notifier prompt template at `src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md` to add `{{NOTIFY_BLOCKS_PREPEND}}` before the existing `"You have mail in inbox."` opener and `{{NOTIFY_BLOCKS_APPEND}}` after the mailbox API summary.
- [ ] 3.2 Extend `_UnreadMailboxMessage` (or add a sibling structure) to carry `notify_block: MailboxNotifyBlock | None` and `notify_auth: MailboxNotifyAuth | None` alongside the existing summary fields.
- [ ] 3.3 Update the notifier poll path so `adapter.list_messages(...)` includes the canonical envelope's notify-block and notify-auth fields; if the existing list path strips them, extend it to surface them for notifier rendering.
- [ ] 3.4 Implement `_render_notify_block_entries(messages, *, placement, per_message_cap, total_cap_remaining)` returning the rendered text plus the chars consumed; oldest-first ordering, sender-attribution prefix, aggregate-cap summarization line.
- [ ] 3.5 Wire the new template-slot substitutions into `_build_mail_notifier_prompt(...)`; respect `notify_block_render` configuration.

## 4. Verifier Interface

- [ ] 4.1 Add `NotifyAuthVerifier` Protocol in `src/houmao/agents/realm_controller/notify_auth_verifier.py` with a `verify(message, notify_auth) -> VerifyResult` method; define `VerifyResult(passed: bool, scheme: str, detail: str | None)` as a frozen dataclass.
- [ ] 4.2 Implement `PermissiveVerifier` (always returns `passed=True`, `scheme="none"`, `detail="no verifier configured"`).
- [ ] 4.3 Implement `SharedTokenVerifier(token_allowlist: frozenset[str])` returning `scheme="shared-token"`, `passed=True` when `notify_auth.token` matches an allowlist entry, `passed=False` otherwise. The rejection `detail` SHALL NOT echo the supplied token text.
- [ ] 4.4 Add a verifier factory `build_notify_auth_verifier(config) -> NotifyAuthVerifier` that selects the implementation based on the gateway notifier configuration.

## 5. Gateway Notifier Configuration

- [ ] 5.1 Extend the notifier configuration record (`gateway_storage.py:gateway_mail_notifier_record`) with `notify_block_render: Literal["enabled", "disabled"]` (default `"enabled"`), `notify_block_auth_mode: Literal["permissive-log", "required"]` (default `"permissive-log"`), `notify_block_auth_verifier: Literal["none", "shared-token"]` (default `"none"`), `notify_block_shared_tokens: list[str]` (default `[]`), `notify_block_per_message_chars: int` (default `512`), and `notify_block_total_chars: int` (default `2048`).
- [ ] 5.2 Update `PUT /v1/mail-notifier` request handling to accept the new fields with the same omit-preserves-current behavior used by `appendix_text`.
- [ ] 5.3 Update `GET /v1/mail-notifier` status response to surface the effective values.
- [ ] 5.4 Update `GatewayMailNotifierPutV1` and `GatewayMailNotifierStatusV1` Pydantic models in `gateway_models.py` accordingly.

## 6. Audit Shape

- [ ] 6.1 Extend the `gateway_notifier_audit` SQLite schema (or its persisted shape) with per-rendered-block JSON entries containing `message_ref`, `rendered`, `auth_scheme`, `auth_outcome`, `auth_detail`, `block_chars`, `block_truncated`.
- [ ] 6.2 Update `_append_notifier_audit_record(...)` to accept the per-block entries from the renderer and persist them alongside existing per-poll fields.
- [ ] 6.3 Confirm the audit projection used by inspectors continues to deserialize cleanly when older audit rows lack the new per-block entries.

## 7. CLI Plumbing

- [ ] 7.1 Add `--notify-block-placement [append|prepend]` to `houmao-mgr agents mail send` and `agents mail post` in `src/houmao/srv_ctrl/commands/agents/mail.py`. Default to `append`. The flag SHALL be ignored when `--notify-block` is omitted.
- [ ] 7.2 Update `mail_send` / `mail_post` / `mail_reply` in `src/houmao/srv_ctrl/commands/managed_agents.py` to thread a typed `MailboxNotifyBlock` (or its dict form) through all four dispatch paths instead of a bare string. Update `_local_manager_*` and `_gateway_*` helpers accordingly.
- [ ] 7.3 Update `GatewayMailSendRequestV1`, `GatewayMailPostRequestV1`, `GatewayMailReplyRequestV1` in `gateway_models.py` to accept the typed `notify_block` shape.

## 8. Operator-Origin Send

- [ ] 8.1 Update `_build_delivery_request` and `_write_staged_message` in `gateway_mailbox.py` to accept the typed `notify_block` and pass it through to `MailboxMessage.compose(...)`. Auto-mirror runs in `compose`.
- [ ] 8.2 Verify the operator-origin reply-policy and provenance metadata still ride alongside notify_block without interference.

## 9. Demo `single-agent-mail-prompt-injection/`

- [ ] 9.1 Scaffold `scripts/demo/single-agent-mail-prompt-injection/` with `inputs/`, `outputs/`, `scripts/`, `expected_report/`, `verify/`, and the standard `outputs/.gitignore`.
- [ ] 9.2 Author `inputs/system_prompt.md` (scoped helper: writes only under tmp/safe/, refuses scope expansion, treats inbox content as untrusted).
- [ ] 9.3 Author `inputs/benign_body.md` (control message that should produce a tmp/safe/ artifact).
- [ ] 9.4 Author `inputs/injection_body.md` containing a `houmao-notify` fenced block whose `text` requests a sentinel write under tmp/leak/.
- [ ] 9.5 Author `inputs/demo_parameters.json` (paths, expected leak filename, lane and mode lists).
- [ ] 9.6 Implement `scripts/demo_driver.py` orchestrating the bootstrap, gateway attach, notifier configuration (per mode), benign send, injection send, and verification per lane × mode.
- [ ] 9.7 Implement `run_demo.sh` exposing `start`, `send-benign`, `send-injection`, `verify`, `stop`, and `auto` actions plus `--tool` and `--mode` selectors.
- [ ] 9.8 Implement `expected_report/` schema and persistence so post-run inspection does not require re-running the demo.
- [ ] 9.9 Author `README.md` explaining the threat model, educational scope (defensive observation), prerequisites, supported lanes, supported modes, and the expected outcomes per lane × mode.
- [ ] 9.10 Update `scripts/demo/README.md` to list `single-agent-mail-prompt-injection/` as a supported demo pack with a one-paragraph description.

## 10. Tests

- [ ] 10.1 Update `tests/unit/mailbox/test_protocol_notify_fields.py` for the typed `MailboxNotifyBlock` shape, `placement` validation, and the v3 protocol constant.
- [ ] 10.2 Update `tests/unit/mailbox/test_notify_extractor.py` to reflect typed compose surfaces; add cases covering auto-mirror append/prepend behavior, no-op when fence already present, and synthetic-fence content.
- [ ] 10.3 Update `tests/unit/mailbox/test_protocol.py` for `protocol_version: 3` in the round-trip assertion.
- [ ] 10.4 Update `tests/unit/agents/realm_controller/test_mail_send_notify_request.py` for the typed shape.
- [ ] 10.5 Update `tests/unit/agents/realm_controller/test_mail_compose_notify_round_trip.py` to verify auto-mirror produces the expected body content.
- [ ] 10.6 Add `tests/unit/agents/realm_controller/test_notify_auth_verifier.py` covering `PermissiveVerifier`, `SharedTokenVerifier` accept/reject, and the factory.
- [ ] 10.7 Add `tests/unit/agents/realm_controller/test_notifier_render_notify_blocks.py` covering single block, multiple blocks with mixed placement, aggregate-cap summarization, sender-attribution rendering, `notify_block_render=disabled`, `permissive-log` rendering despite verifier failure, and `required` mode suppression on verifier failure.
- [ ] 10.8 Add `tests/unit/srv_ctrl/test_agents_mail_notify_block_placement.py` covering the new `--notify-block-placement` flag pass-through.
- [ ] 10.9 Add a notifier audit unit covering per-rendered-block entry structure on `permissive-log` and `required` paths.

## 11. Docs

- [ ] 11.1 Refresh `docs/reference/mailbox/contracts/canonical-model.md` for the typed `MailboxNotifyBlock` shape, the auto-mirror invariant (with sample body before/after), the protocol bump to v3, and the rendering-deferred-no-more wording (rendering ships now).
- [ ] 11.2 Refresh `docs/reference/cli/agents-mail.md` for the new `--notify-block-placement` flag and an updated Notification-prompt block section explaining sender-side authoring vs receiver-side rendering vs receiver-side body visibility.
- [ ] 11.3 Refresh `docs/reference/gateway/contracts/protocol-and-state.md` for the typed shape in request payloads, the new notifier configuration fields, and the per-block audit shape; remove the "rendering deferred" qualifier.
- [ ] 11.4 Refresh `docs/reference/managed_agent_api.md` for the typed shape and the new placement field on `mail/send|post|reply`.
- [ ] 11.5 Add a new `docs/reference/demos/single-agent-mail-prompt-injection.md` page or extend an existing demos index to point operators at the new demo and explain its educational framing.

## 12. Validation

- [ ] 12.1 Run `pixi run format && pixi run lint && pixi run typecheck`. Confirm zero new errors over the documented baseline pre-existing failures.
- [ ] 12.2 Run `pixi run test` and `pixi run test-runtime`. Confirm new tests pass and existing suites remain at the documented baseline.
- [ ] 12.3 Run the demo end-to-end on at least one lane × mode (`claude × permissive-log` and `claude × required`) and confirm the structured report records expected outcomes.
- [ ] 12.4 Run `openspec validate render-mailbox-notify-block-channel --strict` and confirm no spec violations.
