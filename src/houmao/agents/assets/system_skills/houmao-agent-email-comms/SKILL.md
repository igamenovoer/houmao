---
name: houmao-agent-email-comms
description: Use Houmao's unified email communication skill for operator-origin mailbox posts, shared mailbox operations, gateway-backed `/v1/mail/*` work, transport-local context, and no-gateway fallback.
license: MIT
---

# Houmao Agent Email Comms

Use this Houmao skill when you need mailbox work around Houmao-managed agents.

Classify the caller up front:

- If the caller is acting as operator rather than as one live Houmao-managed agent, use the operator-origin `post` path. Strong signals include: no agent gateway is attached, `houmao-mgr agents mail resolve-live` returns no usable live binding for the current session, or current context already shows the caller is not part of the Houmao managed-agent system.
- If the caller is one live Houmao-managed agent, use the ordinary shared-mailbox workflow in this skill: prefer the live gateway `/v1/mail/*` facade when available, and fall back to `houmao-mgr agents mail ...` when the resolver returns `gateway: null`.

For managed-agent gateway-notified unread-email rounds only, use `houmao-process-emails-via-gateway` first and return here when that round needs exact mailbox operations or transport-local guidance.

The trigger word `houmao` is intentional. Use the `houmao-...` skill name directly when you intend to activate this Houmao-owned skill.

## Workflow

1. Decide the caller posture up front.
2. If the caller is acting as operator rather than as one live Houmao-managed agent, use the operator-origin `post` action instead of the ordinary managed-agent gateway workflow. Strong signals include: no agent gateway is attached, `houmao-mgr agents mail resolve-live` returns no usable live binding for the current session, or current context already shows the caller is not part of the Houmao managed-agent system.
3. For Houmao-managed agent mailbox work, if the current prompt or recent mailbox context already provides the exact current gateway base URL, use that value directly for shared `/v1/mail/*` operations.
4. Otherwise run `houmao-mgr agents mail resolve-live`.
5. Treat the resolver output as the supported mailbox-discovery contract for this turn.
6. When the resolver returns a `gateway` object, use the action page that matches the mailbox task you need and use that exact `gateway.base_url` for shared `/v1/mail/*` work.
7. When the resolver returns `gateway: null`, use the transport page that matches `mailbox.transport` and the supported `houmao-mgr agents mail ...` fallback surface for that turn.
8. Treat `message_ref` and `thread_ref` as opaque shared-mailbox references.
9. Mark messages read only after the corresponding mailbox action succeeds.

## Actions

- Read [actions/resolve-live.md](actions/resolve-live.md) only when the current prompt or recent mailbox context does not already provide the exact gateway base URL or current binding set.
- Read [actions/status.md](actions/status.md) to inspect current mailbox identity, mailbox transport, or live gateway posture.
- Read [actions/check.md](actions/check.md) to inspect unread or current mailbox state.
- Read [actions/read.md](actions/read.md) when deciding which unread message to inspect next.
- Read [actions/send.md](actions/send.md) to send one new message.
- Read [actions/post.md](actions/post.md) when the caller is acting as operator or otherwise outside the managed Houmao runtime and needs to leave one operator-origin note in a managed agent mailbox.
- Read [actions/reply.md](actions/reply.md) to reply to one existing message.
- Read [actions/mark-read.md](actions/mark-read.md) to mark one processed message read.

## Transport Pages

- Read [transports/filesystem.md](transports/filesystem.md) when `mailbox.transport` is `filesystem` and you need layout, policy, or no-gateway fallback guidance.
- Read [transports/stalwart.md](transports/stalwart.md) when `mailbox.transport` is `stalwart` and you need direct-access or no-gateway fallback guidance.

## References

- Read [references/endpoint-contract.md](references/endpoint-contract.md) for the shared `/v1/mail/*` route summary.
- Read [references/curl-examples.md](references/curl-examples.md) for copy-paste curl forms against the exact current `gateway.base_url`.
- Read [references/managed-agent-fallback.md](references/managed-agent-fallback.md) for the supported `houmao-mgr agents mail ...` fallback surface when no live gateway facade exists.
- Read [references/filesystem-resolver-fields.md](references/filesystem-resolver-fields.md) or [references/stalwart-resolver-fields.md](references/stalwart-resolver-fields.md) when transport-local resolver fields matter.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) only when filesystem mailbox layout details are relevant.

## Useful Patterns

- For supported higher-level mailbox and gateway compositions such as self-wakeup through self-mail plus notifier-driven rounds, switch to the Houmao advanced-usage skill `houmao-adv-usage-pattern`.

## Guardrails

- Do not guess the gateway host or port; use the exact base URL already present in prompt or context when available, otherwise use `gateway.base_url` from `houmao-mgr agents mail resolve-live`.
- Do not scrape tmux state directly when the manager-owned resolver is available.
- Do not route operator-origin mailbox delivery through ordinary `/v1/mail/send`; use the dedicated `post` surface.
- Do not derive mailbox internals from visible `message_ref` or `thread_ref` prefixes.
- Do not mark a message read before the corresponding mailbox action succeeds.
- Do not treat this ordinary communication skill as the whole notifier-round workflow when `houmao-process-emails-via-gateway` is available.
- Do not present direct transport-local access as the first-choice path when a live shared gateway mailbox facade is available.
