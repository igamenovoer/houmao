---
name: houmao-email-via-agent-gateway
description: Use Houmao's shared gateway mailbox facade through explicit `houmao` wording, manager-owned live discovery, and curl-first `/v1/mail/*` operations.
license: MIT
---

# Houmao Email Via Agent Gateway

Use this Houmao skill when the current mailbox resolver returns `gateway.base_url` and you need ordinary shared mailbox work through the live gateway facade.

The trigger word `houmao` is intentional. Use the `houmao-...` skill name directly when you intend to activate this Houmao-owned skill.

## Workflow

1. Run `pixi run houmao-mgr agents mail resolve-live`.
2. Read `gateway.base_url` from the resolver output.
3. Use the action doc that matches the mailbox task you need.
4. Use curl against that exact base URL for `/v1/mail/*`.
5. Mark messages read only after the corresponding mailbox work succeeds.

## Actions

- Read [actions/resolve-live.md](actions/resolve-live.md) first for discovery.
- Read [actions/check.md](actions/check.md) to inspect unread or current mailbox state.
- Read [actions/read.md](actions/read.md) when deciding which unread message to inspect next.
- Read [actions/send.md](actions/send.md) to send one new message.
- Read [actions/reply.md](actions/reply.md) to reply to one existing message.
- Read [actions/mark-read.md](actions/mark-read.md) to mark one processed message read.

## References

- Read [references/endpoint-contract.md](references/endpoint-contract.md) for the route summary.
- Read [references/curl-examples.md](references/curl-examples.md) for copy-paste curl forms.

## Guardrails

- Do not guess the gateway host or port; use `gateway.base_url` from `houmao-mgr agents mail resolve-live`.
- Do not scrape tmux state directly when the manager-owned resolver is available.
- Do not derive mailbox internals from visible `message_ref` or `thread_ref` prefixes.
- Do not mark a message read before the corresponding mailbox action succeeds.
