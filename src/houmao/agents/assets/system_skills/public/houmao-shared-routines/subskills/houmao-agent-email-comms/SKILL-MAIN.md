---
name: houmao-agent-email-comms
description: Use when ordinary Houmao mailbox work needs operator-origin posting, managed-agent shared mail, gateway-backed `/v1/mail/*`, or a supported no-gateway transport fallback.
license: MIT
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Agent Email Comms

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent; otherwise stop before mailbox routing.

- Admin branch: use the operator-origin `post` path and require explicit mailbox or managed-agent targets. Do not resolve the operator session as managed self.
- Agent branch: require freshly verified self identity, use the verified agent's ordinary mailbox context by default, and require an explicit peer or account target when the command is not self-scoped.

Preserve the branch through gateway discovery and transport fallback. A notifier-driven unread round enters the agent-only `process-emails-via-gateway` route first.

Use this Houmao skill when you need mailbox work around Houmao-managed agents.

Classify the caller up front:

- If the caller is acting as operator rather than as one live Houmao-managed agent, use the operator-origin `post` path. Strong signals include: no agent gateway is attached, `houmao-mgr agents self mail resolve-live` returns no usable live binding for the current session, or current context already shows the caller is not part of the Houmao managed-agent system.
- If the caller is one live Houmao-managed agent, use the ordinary shared-mailbox workflow in this skill: prefer the live gateway `/v1/mail/*` facade when available, and fall back to `houmao-mgr agents self mail ...` when the resolver returns `gateway: null`.

For managed-agent gateway-notified open-mail rounds only, use `houmao-shared-routines->houmao-process-emails-via-gateway` first and return here when that round needs exact mailbox operations or transport-local guidance.

The trigger word `houmao` is intentional. Enter this parent-scoped routine only through `houmao-shared-routines->houmao-agent-email-comms`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$houmao-shared-routines agent-email-comms help`, `help for houmao-agent-email-comms`, `usage for houmao-agent-email-comms`, `available functionality for houmao-agent-email-comms`, or what this skill can do, answer from this section before caller classification, action-page routing, transport-page routing, command execution, or missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me send mail to an agent", route to the matching workflow instead of stopping at generic help.

Purpose: perform ordinary Houmao shared-mailbox operations through the live gateway facade when available, with supported no-gateway fallback guidance.

Available functionality:

- Resolve live mailbox bindings and inspect mailbox status.
- List, peek, read, send, post, reply, mark, move, or archive mailbox messages.
- Choose operator-origin `post` versus managed-agent shared-mailbox workflows.
- Use filesystem or Stalwart transport guidance when no gateway facade is available.

Common starting prompts:

- `$houmao-shared-routines agent-email-comms help`
- `$houmao-shared-routines agent-email-comms status for the current mailbox`
- `$houmao-shared-routines agent-email-comms send a message to <agent>`
- `$houmao-shared-routines agent-email-comms reply to <message_ref>`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-process-emails-via-gateway` for one notifier-reported open-mail round.
- Use `houmao-shared-routines->houmao-mailbox-mgr` for mailbox root, registration, or late-binding administration.
- Use `houmao-shared-routines->houmao-agent-gateway` for notifier, reminder, or gateway lifecycle work.
- Use `houmao-shared-routines->houmao-agent-messaging` when the task starts as live-agent prompt, interrupt, or mailbox handoff routing.

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Decide the caller posture up front.
2. If the caller is acting as operator rather than as one live Houmao-managed agent, use the operator-origin `post` action instead of the ordinary managed-agent gateway workflow. Strong signals include: no agent gateway is attached, `houmao-mgr agents self mail resolve-live` returns no usable live binding for the current session, or current context already shows the caller is not part of the Houmao managed-agent system.
3. For Houmao-managed agent mailbox work, if the current prompt or recent mailbox context already provides the exact current gateway base URL, use that value directly for shared `/v1/mail/*` operations.
4. Otherwise run `agents self mail resolve-live` for the current managed session, or `agents single ... mail resolve-live` when the user explicitly selected another managed agent.
5. Treat the resolver output as the supported mailbox-discovery contract for this turn.
6. When the resolver returns a `gateway` object, use the action page that matches the mailbox task you need and use that exact `gateway.base_url` for shared `/v1/mail/*` work.
7. When the resolver returns `gateway: null`, use the transport page that matches `mailbox.transport` and run the matching `agents self mail <verb>` fallback command for current-session CLI fallback.
8. Treat `message_ref` and `thread_ref` as opaque shared-mailbox references.
9. Archive processed messages only after the corresponding mailbox action and any required reply succeed.
10. Include only fields the user explicitly supplied or that were recovered from explicit recent context in fallback commands.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Missing Input Questions

- Recover required mailbox values from the current prompt, notifier context, resolver output, or recent mailbox context before asking.
- If caller posture, gateway base URL, mailbox binding, action, message ref, thread ref, recipient, subject, or body is still missing for the selected mailbox action, ask before proceeding.
- When asking for Houmao mailbox-system inputs, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected mailbox action or route
  - `Optional`: gateway-vs-fallback posture, filters, archive-after-success choice, output format, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when caller posture, route, or several required fields need clarification
- DO NOT use this format for user-task content inside a mail body unless the question is about Houmao runtime behavior.

## Subcommands

- Answer `help` from `## Help` before reading action, transport, or reference pages.
- Read [commands/resolve-live.md](commands/resolve-live.md) only when the current prompt or recent mailbox context does not already provide the exact gateway base URL or current binding set.
- Read [commands/status.md](commands/status.md) to inspect current mailbox identity, mailbox transport, or live gateway posture.
- Read [commands/list.md](commands/list.md) to list unread, open, archived, or current mailbox state.
- Read [commands/read.md](commands/read.md) when deciding whether to peek at or read one selected message.
- Read [commands/send.md](commands/send.md) to send one new message.
- Read [commands/post.md](commands/post.md) when the caller is acting as operator or otherwise outside the managed Houmao runtime and needs to leave one operator-origin note in a managed agent mailbox.
- Read [commands/reply.md](commands/reply.md) to reply to one existing message.
- Read [commands/archive.md](commands/archive.md) to archive one or more processed messages.

## Transport Pages

- Read [references/transports/filesystem.md](references/transports/filesystem.md) when `mailbox.transport` is `filesystem` and you need layout, policy, or no-gateway fallback guidance.
- Read [references/transports/stalwart.md](references/transports/stalwart.md) when `mailbox.transport` is `stalwart` and you need direct-access or no-gateway fallback guidance.

## References

- Read [references/endpoint-contract.md](references/endpoint-contract.md) for the shared `/v1/mail/*` route summary.
- Read [references/curl-examples.md](references/curl-examples.md) for copy-paste curl forms against the exact current `gateway.base_url`.
- Read [references/managed-agent-fallback.md](references/managed-agent-fallback.md) for the supported `houmao-mgr agents self mail ...` and `houmao-mgr agents single ... mail ...` fallback surfaces when no live gateway facade exists.
- Read [references/filesystem-resolver-fields.md](references/filesystem-resolver-fields.md) or [references/stalwart-resolver-fields.md](references/stalwart-resolver-fields.md) when transport-local resolver fields matter.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) only when filesystem mailbox layout details are relevant.

## Useful Patterns

- For supported higher-level mailbox and gateway compositions such as self-wakeup through self-mail plus notifier-driven rounds, switch to the Houmao advanced-usage skill `houmao-shared-routines->houmao-adv-usage-pattern`.

## Guardrails

- DO NOT guess the gateway host or port; use the exact base URL already present in prompt or context when available, otherwise use `gateway.base_url` from `houmao-mgr agents self mail resolve-live`.
- DO NOT scrape tmux state directly when the manager-owned resolver is available.
- DO NOT route operator-origin mailbox delivery through ordinary `/v1/mail/send`; use the dedicated `post` surface.
- DO NOT derive mailbox internals from visible `message_ref` or `thread_ref` prefixes.
- DO NOT archive a message before the corresponding mailbox action and any required reply succeed.
- DO NOT treat this ordinary communication skill as the whole notifier-round workflow when `houmao-shared-routines->houmao-process-emails-via-gateway` is available.
- DO NOT present direct transport-local access as the first-choice path when a live shared gateway mailbox facade is available.
- DO NOT invent alternate fallback command shapes; use the direct scoped `houmao-mgr agents self mail ...` and `houmao-mgr agents single ... mail ...` commands shown in this skill package.
