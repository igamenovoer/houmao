---
name: houmao-agent-email-comms
description: Use Houmao's unified email communication skill for operator-origin mailbox posts, shared mailbox operations, gateway-backed `/v1/mail/*` work, transport-local context, and no-gateway fallback.
license: MIT
---

# Houmao Agent Email Comms

Use this Houmao skill when you need mailbox work around Houmao-managed agents.

Classify the caller up front:

- If the caller is acting as operator rather than as one live Houmao-managed agent, use the operator-origin `post` path. Strong signals include: no agent gateway is attached, `houmao-mgr agents self mail resolve-live` returns no usable live binding for the current session, or current context already shows the caller is not part of the Houmao managed-agent system.
- If the caller is one live Houmao-managed agent, use the ordinary shared-mailbox workflow in this skill: prefer the live gateway `/v1/mail/*` facade when available, and fall back to `houmao-mgr agents self mail ...` when the resolver returns `gateway: null`.

For managed-agent gateway-notified open-mail rounds only, use `houmao-process-emails-via-gateway` first and return here when that round needs exact mailbox operations or transport-local guidance.

The trigger word `houmao` is intentional. Use the `houmao-...` skill name directly when you intend to activate this Houmao-owned skill.

## Help

When the user asks `$houmao-agent-email-comms help`, `help for houmao-agent-email-comms`, `usage for houmao-agent-email-comms`, `available functionality for houmao-agent-email-comms`, or what this skill can do, answer from this section before caller classification, action-page routing, transport-page routing, command execution, or missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me send mail to an agent", route to the matching workflow instead of stopping at generic help.

Purpose: perform ordinary Houmao shared-mailbox operations through the live gateway facade when available, with supported no-gateway fallback guidance.

Available functionality:

- Resolve live mailbox bindings and inspect mailbox status.
- List, peek, read, send, post, reply, mark, move, or archive mailbox messages.
- Choose operator-origin `post` versus managed-agent shared-mailbox workflows.
- Use filesystem or Stalwart transport guidance when no gateway facade is available.

Common starting prompts:

- `$houmao-agent-email-comms help`
- `$houmao-agent-email-comms status for the current mailbox`
- `$houmao-agent-email-comms send a message to <agent>`
- `$houmao-agent-email-comms reply to <message_ref>`

Related skills and boundaries:

- Use `houmao-process-emails-via-gateway` for one notifier-reported open-mail round.
- Use `houmao-mailbox-mgr` for mailbox root, registration, or late-binding administration.
- Use `houmao-agent-gateway` for notifier, reminder, or gateway lifecycle work.
- Use `houmao-agent-messaging` when the task starts as live-agent prompt, interrupt, or mailbox handoff routing.

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Decide the caller posture up front.
2. If the caller is acting as operator rather than as one live Houmao-managed agent, use the operator-origin `post` action instead of the ordinary managed-agent gateway workflow. Strong signals include: no agent gateway is attached, `houmao-mgr agents self mail resolve-live` returns no usable live binding for the current session, or current context already shows the caller is not part of the Houmao managed-agent system.
3. For Houmao-managed agent mailbox work, if the current prompt or recent mailbox context already provides the exact current gateway base URL, use that value directly for shared `/v1/mail/*` operations.
4. Otherwise render `agents.self.mail.resolve-live` for the current managed session, or `agents.single.mail.resolve-live` when the user explicitly selected another managed agent, then run the rendered `argv`.
5. Treat the resolver output as the supported mailbox-discovery contract for this turn.
6. When the resolver returns a `gateway` object, use the action page that matches the mailbox task you need and use that exact `gateway.base_url` for shared `/v1/mail/*` work.
7. When the resolver returns `gateway: null`, use the transport page that matches `mailbox.transport` and render the matching `agents.self.mail.<verb>` fallback template before running current-session CLI fallback commands.
8. Treat `message_ref` and `thread_ref` as opaque shared-mailbox references.
9. Archive processed messages only after the corresponding mailbox action and any required reply succeed.
10. Render sparse fallback intent with only fields the user explicitly supplied or that were recovered from explicit recent context:
   - `<chosen houmao-mgr launcher> --print-json internals command-templates show --id agents.self.mail.<verb>`
   - `<chosen houmao-mgr launcher> --print-json internals command-templates render --id agents.self.mail.<verb> --intent '<json>'`

## Missing Input Questions

- Recover required mailbox values from the current prompt, notifier context, resolver output, or recent mailbox context before asking.
- If caller posture, gateway base URL, mailbox binding, action, message ref, thread ref, recipient, subject, or body is still missing for the selected mailbox action, ask before proceeding.
- When asking for Houmao mailbox-system inputs, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected mailbox action or route
  - `Optional`: gateway-vs-fallback posture, filters, archive-after-success choice, output format, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when caller posture, route, or several required fields need clarification
- Do not use this format for user-task content inside a mail body unless the question is about Houmao runtime behavior.

## Actions

- Answer `help` from `## Help` before reading action, transport, or reference pages.
- Read [actions/resolve-live.md](actions/resolve-live.md) only when the current prompt or recent mailbox context does not already provide the exact gateway base URL or current binding set.
- Read [actions/status.md](actions/status.md) to inspect current mailbox identity, mailbox transport, or live gateway posture.
- Read [actions/list.md](actions/list.md) to list unread, open, archived, or current mailbox state.
- Read [actions/read.md](actions/read.md) when deciding whether to peek at or read one selected message.
- Read [actions/send.md](actions/send.md) to send one new message.
- Read [actions/post.md](actions/post.md) when the caller is acting as operator or otherwise outside the managed Houmao runtime and needs to leave one operator-origin note in a managed agent mailbox.
- Read [actions/reply.md](actions/reply.md) to reply to one existing message.
- Read [actions/archive.md](actions/archive.md) to archive one or more processed messages.

## Transport Pages

- Read [transports/filesystem.md](transports/filesystem.md) when `mailbox.transport` is `filesystem` and you need layout, policy, or no-gateway fallback guidance.
- Read [transports/stalwart.md](transports/stalwart.md) when `mailbox.transport` is `stalwart` and you need direct-access or no-gateway fallback guidance.

## References

- Read [references/endpoint-contract.md](references/endpoint-contract.md) for the shared `/v1/mail/*` route summary.
- Read [references/curl-examples.md](references/curl-examples.md) for copy-paste curl forms against the exact current `gateway.base_url`.
- Read [references/managed-agent-fallback.md](references/managed-agent-fallback.md) for the supported `houmao-mgr agents self mail ...` and `houmao-mgr agents single ... mail ...` fallback surfaces when no live gateway facade exists.
- Read [references/filesystem-resolver-fields.md](references/filesystem-resolver-fields.md) or [references/stalwart-resolver-fields.md](references/stalwart-resolver-fields.md) when transport-local resolver fields matter.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) only when filesystem mailbox layout details are relevant.

## Useful Patterns

- For supported higher-level mailbox and gateway compositions such as self-wakeup through self-mail plus notifier-driven rounds, switch to the Houmao advanced-usage skill `houmao-adv-usage-pattern`.

## Guardrails

- Do not guess the gateway host or port; use the exact base URL already present in prompt or context when available, otherwise use `gateway.base_url` from `houmao-mgr agents self mail resolve-live`.
- Do not scrape tmux state directly when the manager-owned resolver is available.
- Do not route operator-origin mailbox delivery through ordinary `/v1/mail/send`; use the dedicated `post` surface.
- Do not derive mailbox internals from visible `message_ref` or `thread_ref` prefixes.
- Do not archive a message before the corresponding mailbox action and any required reply succeed.
- Do not treat this ordinary communication skill as the whole notifier-round workflow when `houmao-process-emails-via-gateway` is available.
- Do not present direct transport-local access as the first-choice path when a live shared gateway mailbox facade is available.
- Do not hand-author supported `houmao-mgr agents self mail ...` or `houmao-mgr agents single ... mail ...` fallback commands from Markdown skeletons when a command template supports the surface.
