---
name: houmao-email-via-agent-gateway
description: Use Houmao's shared gateway mailbox facade as the lower-level protocol and reference skill for context-first endpoint discovery and `/v1/mail/*` operations.
license: MIT
---

# Houmao Email Via Agent Gateway

Use this Houmao skill when you need the exact lower-level gateway contract for shared mailbox work through the live gateway facade, whether the gateway base URL came from the current prompt or from manager-based discovery.

When a notifier or operator prompt tells you to use `houmao-process-emails-via-gateway`, treat this skill as supporting material for the exact route contract rather than as the round-planning workflow itself.

The trigger word `houmao` is intentional. Use the `houmao-...` skill name directly when you intend to activate this Houmao-owned skill.

## Workflow

1. If the current prompt or recent mailbox context already provides the exact gateway base URL, use that value directly.
2. Otherwise run `houmao-mgr agents mail resolve-live`.
3. Read `gateway.base_url` from the resolver output when the resolver returns a `gateway` object.
4. Open `skills/mailbox/houmao-process-emails-via-gateway/SKILL.md` first when you are handling one notifier-driven email-processing round.
5. Use the action doc that matches the exact mailbox task you need.
6. Use curl against that exact base URL for `/v1/mail/*`.
7. Mark messages read only after the corresponding mailbox action succeeds.

## Actions

- Read [actions/resolve-live.md](actions/resolve-live.md) only when the current prompt or recent mailbox context does not already provide the exact gateway base URL.
- Read [actions/check.md](actions/check.md) to inspect unread or current mailbox state.
- Read [actions/read.md](actions/read.md) when deciding which unread message to inspect next.
- Read [actions/send.md](actions/send.md) to send one new message.
- Read [actions/reply.md](actions/reply.md) to reply to one existing message.
- Read [actions/mark-read.md](actions/mark-read.md) to mark one processed message read.

## References

- Read [references/endpoint-contract.md](references/endpoint-contract.md) for the route summary.
- Read [references/curl-examples.md](references/curl-examples.md) for copy-paste curl forms.

## Guardrails

- Do not guess the gateway host or port; use the exact base URL already present in prompt/context when available, otherwise use `gateway.base_url` from `houmao-mgr agents mail resolve-live`.
- Do not scrape tmux state directly when the manager-owned resolver is available.
- Do not derive mailbox internals from visible `message_ref` or `thread_ref` prefixes.
- Do not mark a message read before the corresponding mailbox action succeeds.
- Do not treat this lower-level protocol skill as the whole notifier-round workflow when `houmao-process-emails-via-gateway` is available.
