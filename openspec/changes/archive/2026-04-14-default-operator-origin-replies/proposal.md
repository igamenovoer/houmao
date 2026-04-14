## Why

Operator-origin mail is now being used as a practical way for operators to ask managed agents to do work, and the common case is that the agent should be able to answer the operator without extra flags. The current default makes those messages one-way unless the caller remembers `reply_policy=operator_mailbox`, which is easy to omit and causes replies to fail later.

## What Changes

- **BREAKING**: New operator-origin `post` requests that omit `reply_policy` default to `operator_mailbox` instead of `none`.
- Keep `reply_policy=none` as an explicit opt-out for one-way operator-origin notes.
- Route default replies to the reserved operator mailbox `HOUMAO-operator@houmao.localhost` through the existing reply-enabled operator-origin path.
- Preserve conservative handling for legacy or malformed operator-origin messages whose stored headers do not explicitly carry `operator_mailbox`; those messages continue to resolve as no-reply.
- Update CLI, gateway, server proxy, docs, tests, and packaged skill guidance so the default is consistently reply-enabled.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-mailbox-operator-origin-send`: Change operator-origin default reply policy from no-reply to `operator_mailbox`, while keeping explicit `none` as the no-reply opt-out.
- `houmao-srv-ctrl-native-cli`: Change `houmao-mgr agents mail post` default `--reply-policy` behavior and help text.
- `agent-gateway`: Change the `/v1/mail/post` request-model default for omitted `reply_policy`.
- `houmao-agent-email-comms-skill`: Update operator-origin post guidance to show reply-enabled default and explicit no-reply opt-out.
- `docs-cli-reference`: Update `agents mail post` CLI reference and operator-origin reply guidance.
- `mailbox-reference-docs`: Update mailbox reference and quickstart guidance for the reply-enabled default.

## Impact

- Affected code: `src/houmao/mailbox/protocol.py`, `src/houmao/srv_ctrl/commands/agents/mail.py`, `src/houmao/agents/realm_controller/gateway_models.py`, and request forwarding surfaces that preserve `reply_policy`.
- Affected guidance: `src/houmao/agents/assets/system_skills/houmao-agent-email-comms/`, `docs/reference/cli/agents-mail.md`, and `docs/reference/mailbox/`.
- Affected tests: protocol helper defaults, gateway `/v1/mail/post` default behavior, reply routing for default operator-origin posts, and CLI/help documentation assertions.
- No database migration is required; existing delivered messages keep their stored headers and continue to follow their recorded reply policy.
