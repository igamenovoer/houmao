## 1. Core Defaults

- [x] 1.1 Change operator-origin header creation defaults so new omitted-policy posts use `operator_mailbox`.
- [x] 1.2 Keep stored-message reply-policy parsing conservative so missing, malformed, or unrecognized headers still resolve as `none`.
- [x] 1.3 Change `GatewayMailPostRequestV1` omitted `reply_policy` default to `operator_mailbox` and confirm pair-managed post requests inherit the same default.
- [x] 1.4 Change `houmao-mgr agents mail post --reply-policy` default and help output to `operator_mailbox` while preserving explicit `none`.

## 2. Reply Behavior Coverage

- [x] 2.1 Update protocol tests so `operator_origin_headers()` defaults to `operator_mailbox` and explicit `none` remains supported.
- [x] 2.2 Update gateway mail tests so omitted `/v1/mail/post` creates a reply-enabled operator-origin message with `reply_to = HOUMAO-operator@houmao.localhost`.
- [x] 2.3 Add or update tests proving explicit `reply_policy=none` still rejects replies to that operator-origin message.
- [x] 2.4 Add or preserve coverage proving missing legacy reply-policy headers still resolve as no-reply.
- [x] 2.5 Add or update CLI/help tests for the new `houmao-mgr agents mail post` reply-policy default.

## 3. Guidance And Docs

- [x] 3.1 Update `houmao-agent-email-comms` operator-origin post guidance to present reply-enabled behavior as the default and `none` as the no-reply opt-out.
- [x] 3.2 Update `docs/reference/cli/agents-mail.md` option tables, narrative, and examples for the new default.
- [x] 3.3 Update mailbox quickstart, common workflows, index, and canonical-model docs where they describe operator-origin reply policy defaults.
- [x] 3.4 Remove or rewrite stale “one-way by default” wording while preserving the filesystem-only and reserved-operator-mailbox boundaries.

## 4. Verification

- [x] 4.1 Run focused mailbox protocol and gateway tests covering operator-origin post and reply behavior.
- [x] 4.2 Run focused CLI/help tests covering `agents mail post`.
- [x] 4.3 Run `openspec validate default-operator-origin-replies --strict` and fix any proposal/spec/task issues.
