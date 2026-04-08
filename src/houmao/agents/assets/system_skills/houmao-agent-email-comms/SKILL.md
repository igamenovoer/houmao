---
name: houmao-agent-email-comms
description: Use Houmao's unified email communication skill for shared mailbox operations, gateway-backed `/v1/mail/*` work, transport-local context, and no-gateway fallback.
license: MIT
---

# Houmao Agent Email Comms

Use this Houmao skill when you need ordinary shared-mailbox work for a Houmao-managed agent session, whether that work goes through the live shared gateway facade or a no-gateway fallback surface.

This is the ordinary mailbox communication skill. When a notifier or operator prompt tells you to process one gateway-notified unread-email round, use `houmao-process-emails-via-gateway` first and return here when that round needs exact mailbox operations or transport-local guidance.

The trigger word `houmao` is intentional. Use the `houmao-...` skill name directly when you intend to activate this Houmao-owned skill.

## Workflow

1. If the current prompt or recent mailbox context already provides the exact current gateway base URL, use that value directly for shared `/v1/mail/*` operations.
2. Otherwise run `houmao-mgr agents mail resolve-live`.
3. Treat the resolver output as the supported mailbox-discovery contract for this turn.
4. When the resolver returns a `gateway` object, use the action page that matches the mailbox task you need and use that exact `gateway.base_url` for shared `/v1/mail/*` work.
5. When the resolver returns `gateway: null`, use the transport page that matches `mailbox.transport` and the supported `houmao-mgr agents mail ...` fallback surface for that turn.
6. Treat `message_ref` and `thread_ref` as opaque shared-mailbox references.
7. Mark messages read only after the corresponding mailbox action succeeds.

## Actions

- Read [actions/resolve-live.md](actions/resolve-live.md) only when the current prompt or recent mailbox context does not already provide the exact gateway base URL or current binding set.
- Read [actions/status.md](actions/status.md) to inspect current mailbox identity, mailbox transport, or live gateway posture.
- Read [actions/check.md](actions/check.md) to inspect unread or current mailbox state.
- Read [actions/read.md](actions/read.md) when deciding which unread message to inspect next.
- Read [actions/send.md](actions/send.md) to send one new message.
- Read [actions/post.md](actions/post.md) to leave one operator-origin note in the current managed agent mailbox.
- Read [actions/reply.md](actions/reply.md) to reply to one existing message.
- Read [actions/mark-read.md](actions/mark-read.md) to mark one processed message read.

## Transport Pages

- Read [transports/filesystem.md](transports/filesystem.md) when `mailbox.transport` is `filesystem` and you need layout, policy, or no-gateway fallback guidance.
- Read [transports/stalwart.md](transports/stalwart.md) when `mailbox.transport` is `stalwart` and you need direct-access or no-gateway fallback guidance.

## References

- Read [references/endpoint-contract.md](references/endpoint-contract.md) for the shared `/v1/mail/*` route summary.
- Read [references/curl-examples.md](references/curl-examples.md) for copy-paste curl forms against the exact current `gateway.base_url`.
- Read [references/self-notification-via-gateway.md](references/self-notification-via-gateway.md) when a managed agent with a live gateway and mailbox binding needs to leave itself one mailbox-driven follow-up reminder and then wait for the next gateway notification round.
- Read [references/managed-agent-fallback.md](references/managed-agent-fallback.md) for the supported `houmao-mgr agents mail ...` fallback surface when no live gateway facade exists.
- Read [references/filesystem-resolver-fields.md](references/filesystem-resolver-fields.md) or [references/stalwart-resolver-fields.md](references/stalwart-resolver-fields.md) when transport-local resolver fields matter.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) only when filesystem mailbox layout details are relevant.

## Useful Patterns

- A managed agent with a live gateway and mailbox binding can send mail to its own mailbox, leave the gateway mail-notifier enabled, and then wait for the next notification round instead of polling mail proactively. Use [references/self-notification-via-gateway.md](references/self-notification-via-gateway.md) for the exact pattern boundary and guardrails.

## Guardrails

- Do not guess the gateway host or port; use the exact base URL already present in prompt or context when available, otherwise use `gateway.base_url` from `houmao-mgr agents mail resolve-live`.
- Do not scrape tmux state directly when the manager-owned resolver is available.
- Do not derive mailbox internals from visible `message_ref` or `thread_ref` prefixes.
- Do not mark a message read before the corresponding mailbox action succeeds.
- Do not treat this ordinary communication skill as the whole notifier-round workflow when `houmao-process-emails-via-gateway` is available.
- Do not present direct transport-local access as the first-choice path when a live shared gateway mailbox facade is available.
