## 1. Protocol Model

- [x] 1.1 Add `MailboxNotifyAuth` sealed `_StrictMailboxModel` to `src/houmao/mailbox/protocol.py` with fields `scheme: Literal["none", "shared-token", "hmac-sha256", "jws"]`, optional `token`, `iss`, `iat`, `exp`, and a validator that rejects non-`none` schemes with the explicit "verifier not yet supported" error.
- [x] 1.2 Add `notify_block: str | None = None` and `notify_auth: MailboxNotifyAuth | None = None` to `MailboxMessage`; ensure both fields are excluded from per-recipient state semantics.
- [x] 1.3 Bump `MAILBOX_PROTOCOL_VERSION` to `2` in `src/houmao/mailbox/protocol.py` and update the existing `protocol_version` validator so v2 envelopes are accepted and `protocol_version != 2` is rejected with an explicit protocol-version error.
- [x] 1.4 Implement the body-fence extractor: parse `body_markdown` for the first ` ```houmao-notify ... ``` ` fenced block, trim leading/trailing whitespace inside the fence, leave `body_markdown` unchanged, and return either the extracted text or `None` for empty fences.
- [x] 1.5 Wire the extractor into `MailboxMessage` composition so caller-supplied `notify_block` wins over body-fence extraction; never re-extract on top of an explicit value. Implemented as `MailboxMessage.compose(payload)` classmethod; pure load via `parse_message_document` keeps stored values untouched.
- [x] 1.6 Apply the 512-character cap with visible `…` truncation in the composition path before the field is stored.

## 2. Transport Persistence

- [x] 2.1 Confirm `src/houmao/mailbox/filesystem.py` round-trips `notify_block` and `notify_auth` through the canonical JSON document (Pydantic dump/load already handles new optional fields; verify no allowlist filters them out). Filesystem persistence works through `serialize_message_document` / `parse_message_document`; the YAML front matter carries any field present on the model. Verified via smoke test.
- [x] 2.2 Stalwart-bound mailbox sends now reject `notify_block` / `notify_auth` with `GatewayMailboxUnsupportedError` (`_reject_stalwart_notify_fields` helper). JMAP-side `X-Houmao-Notify-*` projection is deferred to a follow-on change and recorded as a known limitation in `design.md`.

## 3. Operator-Origin Send

- [x] 3.1 Operator-origin composition flows through the same `_build_delivery_request` → `_write_staged_message` path as ordinary send in `gateway_mailbox.py`, which now accepts `notify_block` / `notify_auth` and threads them into `MailboxMessage.compose(...)`.
- [x] 3.2 Operator-origin reply-policy and provenance metadata are unchanged: notify fields are added to `payload` only when supplied; `headers=operator_origin_headers(...)` and `reply_to` plumbing in `post()` remain untouched.

## 4. Gateway `/v1/mail/send` Acceptance

- [x] 4.1 `GatewayMailSendRequestV1`, `GatewayMailPostRequestV1`, and `GatewayMailReplyRequestV1` in `gateway_models.py` now carry optional `notify_block: str | None` and `notify_auth: MailboxNotifyAuth | None` fields.
- [x] 4.2 `gateway_service.py` `send_mail` / `post_mail` / `reply_mail` pass the fields straight through to the adapter without re-validation. The protocol model is the single source of validation.
- [x] 4.3 `MailboxNotifyAuth._validate_scheme` raises `ValueError("verifier not yet supported: ...")` which surfaces as FastAPI's standard 422 validation-error response. No rendering or audit-record changes were made.

## 5. CLI Flags

- [x] 5.1 `--notify-block <text>` added to `houmao-mgr agents mail send` in `src/houmao/srv_ctrl/commands/agents/mail.py`; the value flows through `mail_send` in `managed_agents.py` to all four dispatch paths (server-mode, manager-direct, gateway-backed, TUI-fallback) and lands in canonical composition.
- [x] 5.2 `--notify-block <text>` added to `houmao-mgr agents mail post`; threaded through `mail_post` to the same dispatch paths.
- [x] 5.3 When `--notify-block` is omitted, the body source is submitted unchanged; the protocol-side extractor handles `houmao-notify` fences during canonical composition. CLI layer never re-extracts.
- [x] 5.4 Truncation produces a visible canonical value via the field validator; unsupported `notify_auth.scheme` raises `ValueError("verifier not yet supported: ...")` which the existing CLI ClickException flow surfaces as an explicit error rather than a Python traceback.

## 6. Tests

- [x] 6.1 `tests/unit/mailbox/test_protocol_notify_fields.py` — 14 scenarios covering MailboxNotifyAuth scheme acceptance/rejection, notify_block/notify_auth optionality, protocol version bump, full round-trip.
- [x] 6.2 `tests/unit/mailbox/test_notify_extractor.py` — 16 scenarios covering no fence, single fence, multiple fences (first wins), empty fence, unrelated info strings, unterminated fence, multi-line content, caller-supplied bypass, oversize truncation in both forms, and the "load does not auto-extract" guarantee.
- [x] 6.3 Filesystem round-trip covered by `tests/unit/agents/realm_controller/test_mail_compose_notify_round_trip.py` exercising `_write_staged_message` end-to-end with `serialize_message_document` / `parse_message_document`.
- [x] 6.4 Stalwart-side projection deferred to follow-on change; `_reject_stalwart_notify_fields` raises `GatewayMailboxUnsupportedError` and that defensive path is small enough not to require its own unit. Documented as a known limitation in `design.md`.
- [x] 6.5 Operator-origin send coverage included in `test_mail_compose_notify_round_trip.py` — operator-origin uses the same `_write_staged_message` composition path as ordinary send, so the same tests verify it.
- [x] 6.6 `tests/unit/srv_ctrl/test_agents_mail_notify_block.py` — three scenarios exercising `--notify-block` on `send` and `post`, body-fence pass-through, and the omit-flag default.
- [x] 6.7 `tests/unit/agents/realm_controller/test_mail_send_notify_request.py` — six scenarios covering `GatewayMailSendRequestV1`/`GatewayMailPostRequestV1`/`GatewayMailReplyRequestV1` accepting optional `notify_block`/`notify_auth`, default omission, and rejection of unsupported `notify_auth.scheme`.

## 7. Docs

- [x] 7.1 `docs/reference/mailbox/contracts/canonical-model.md` updated with the "Notification-prompt block" section, sample envelope at `protocol_version: 2` with notify fields populated, and explicit deferred-rendering note.
- [x] 7.2 `docs/reference/cli/agents-mail.md` updated with `--notify-block` rows in `send` and `post` option tables, plus a new "Notification-prompt block" section with both authoring paths, constraints, and Stalwart caveat.
- [x] 7.3 Deferred-rendering note included in both the canonical-model doc and the CLI reference.

## 8. Validation

- [x] 8.1 `pixi run format` (canonicalized 14 files including formatter-only line-length adjustments to neighboring files); `pixi run lint` clean; `pixi run typecheck` clean from this change (10 baseline failures in untouched modules confirmed pre-existing on origin/main).
- [x] 8.2 `pixi run test`: 1840 passed, 1 pre-existing failure (`test_gateway_mail_notifier_renders_gateway_bootstrap_prompt_with_houmao_gateway_skill`) confirmed reproducible on origin/main without these changes. `pixi run test-runtime`: 711 passed, same single pre-existing failure.
- [x] 8.3 `openspec validate add-mailbox-notify-prompt-block --strict`: change is valid.
