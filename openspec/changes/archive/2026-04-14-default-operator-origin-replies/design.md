## Context

Operator-origin mailbox delivery currently has two reply-policy values: `none` and `operator_mailbox`. New posts default to `none` through the CLI option default, the gateway `/v1/mail/post` request model default, and the protocol helper default. The filesystem gateway adapter already supports reply-enabled operator-origin messages by adding `reply_to = HOUMAO-operator@houmao.localhost` and setting `x-houmao-reply-policy: operator_mailbox`; reply handling already routes such replies back to the reserved operator mailbox.

The change is therefore a default flip, not a new transport or mailbox model. The affected entrypoints are the manager CLI, direct live gateway HTTP, pair-managed proxy models that inherit the gateway request model, and the packaged skill/docs that teach callers how to post operator-origin mail.

## Goals / Non-Goals

**Goals:**

- Make newly created operator-origin posts reply-enabled by default.
- Preserve explicit `reply_policy=none` as the supported no-reply opt-out.
- Keep replies routed to `HOUMAO-operator@houmao.localhost` through the existing reserved operator mailbox contract.
- Keep existing stored operator-origin messages governed by their recorded headers.
- Update docs, specs, packaged skill guidance, and tests to reflect the new default.

**Non-Goals:**

- Do not add Stalwart operator-origin delivery support; `post` remains filesystem-only in v1.
- Do not make the reserved operator mailbox a general-purpose free-send address.
- Do not reinterpret legacy or malformed operator-origin messages with missing reply-policy headers as reply-enabled.
- Do not add a data migration or rewrite delivered canonical Markdown messages.

## Decisions

### Decision: Flip creation-time defaults only

New calls that omit the reply policy will default to `operator_mailbox`. This includes `houmao-mgr agents mail post`, `GatewayMailPostRequestV1`, and the protocol helper used to create operator-origin provenance headers.

Alternative considered: change only the CLI default and leave gateway HTTP payload omission as no-reply. Rejected because different defaults across CLI, pair-managed proxy, and direct gateway HTTP would make behavior depend on routing path.

Alternative considered: remove `reply_policy=none`. Rejected because one-way operator-origin notes remain useful and the current contract already has a clear explicit opt-out value.

### Decision: Keep parse-time fallback conservative

`operator_origin_reply_policy(headers)` should continue to resolve missing, non-string, or unrecognized header values to `none`. That preserves the behavior of old delivered messages, partial test fixtures, and malformed headers that did not explicitly opt into replies.

Alternative considered: make missing headers default to `operator_mailbox`. Rejected because it would retroactively reinterpret stored messages without changing their canonical content and could enable replies for messages created under the old one-way default.

### Decision: Reuse existing reply-enabled routing

The filesystem gateway adapter already has the desired reply path: when `reply_policy == operator_mailbox`, it sets `reply_to` to the reserved operator sender, and later reply calls target `parent_message.reply_to` before falling back to the sender. The implementation should feed that existing path by changing defaults rather than adding another special-case reply branch.

Alternative considered: special-case replies to all operator-origin messages by sender address. Rejected because it would blur explicit policy metadata and make `reply_policy=none` ineffective.

### Decision: Update user-facing guidance alongside behavior

The CLI reference, mailbox quickstart/workflow docs, canonical-model docs, and `houmao-agent-email-comms` post action should describe reply-enabled operator-origin posts as the default, with `none` as the explicit no-reply option. Examples should omit `--reply-policy operator_mailbox` unless they are demonstrating the explicit value.

Alternative considered: leave examples unchanged because they still work. Rejected because the stale examples would continue teaching users to pass now-default behavior explicitly and would hide the new opt-out semantics.

## Risks / Trade-offs

- [Risk] Existing automation that omitted `reply_policy` expecting no-reply behavior will become reply-enabled. -> Mitigation: mark the proposal as breaking, keep explicit `reply_policy=none` as the opt-out, and update CLI help/docs.
- [Risk] Flipping helper defaults could accidentally change interpretation of existing message headers. -> Mitigation: change only creation defaults and keep `operator_origin_reply_policy()` fallback-to-`none`.
- [Risk] Pair-managed proxy and direct gateway defaults may drift if only one model changes. -> Mitigation: rely on the shared `GatewayMailPostRequestV1` default inherited by pair server request models and add tests for both omitted and explicit policy behavior where coverage exists.
- [Risk] Docs may continue to describe operator-origin mail as one-way. -> Mitigation: update docs and specs that currently name one-way/no-reply as the default.

## Migration Plan

No stored mailbox migration is required. Existing canonical messages continue to carry their original `x-houmao-reply-policy` header, and messages without an explicit reply-enabled header remain no-reply.

Rollout is a code/docs/test update:

1. Change creation-time defaults to `operator_mailbox`.
2. Keep explicit `none` support and parse-time fallback-to-`none`.
3. Update CLI/help text, skill guidance, and reference docs.
4. Update tests that assert omitted post policy is no-reply, and add/adjust tests for explicit no-reply opt-out.

Rollback is code rollback only; no data migration or cleanup is required.

## Open Questions

None.
