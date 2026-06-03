---
name: houmao-operator-messaging
description: Manual invocation only; use only when the user explicitly requests `houmao-operator-messaging` or an explicitly named operator messaging operation to clarify operator intent and dispatch messages to one or more Houmao-managed agents by direct prompt or mailbox.
---

# Houmao Operator Messaging

## Activation

- Use this Houmao skill only after the user explicitly selects `houmao-operator-messaging` or names a supported operator messaging operation.
- Do not auto-route generic requests such as "tell the coder" or "message the reviewer" here unless the user selects this skill or asks for operator messaging clarification/dispatch.
- If the user invokes explicit help intent, answer from `## Help` before reading routed pages, asking missing-input questions, sending prompts, sending mail, or changing runtime state.
- If the user invokes this skill with an actionable prompt but no subcommand, treat it as `clarify`: extract the intended target(s) and message, show them in a table, and ask whether to refine the plan or dispatch directly. Do not dispatch until the user confirms dispatch.
- If the user invokes this skill without a subcommand or actionable prompt, explain the supported subcommands and ask which operation they want; do not default to dispatch.

## Help

When the user asks `$houmao-operator-messaging help`, `help for houmao-operator-messaging`, `usage for houmao-operator-messaging`, `available functionality for houmao-operator-messaging`, or what this skill can do, answer from this section. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. Do not send prompts during help. If the user asks a concrete task such as "help me dispatch this to the implementation and review agents", route to the matching operation instead of stopping at generic help.

Purpose: clarify operator intent and dispatch one or more operator-authored messages to Houmao-managed agents. Dispatch defaults to prompt delivery through maintained messaging surfaces; mailbox delivery is used only when the operator prompt or chat context asks for mail-style delivery.

Available functionality:

| Subcommand | Use when | Side effects |
| --- | --- | --- |
| `help` | Explain purpose, operations, in-chat clarification, routes, and boundaries. | None. |
| `clarify` | Resolve the operator's intent in chat, showing the current send plan each round and asking one unclear decision question at a time. | None; never writes files or dispatches. |
| `dispatch` | Send one or more command packets from clarified intent, an explicit dispatch prompt, or a user-specified Markdown intent record. | May send direct prompts or mailbox messages through lower-level skills. |

Common starting prompts:

- `$houmao-operator-messaging help`
- `$houmao-operator-messaging ask the implementation agent to check issue 53 and report whether the operator messaging skill covers it`
- `$houmao-operator-messaging clarify: ask the implementation and review agents to coordinate on issue 53`
- `$houmao-operator-messaging dispatch using ./operator-intent.md`

Clarification state:

- `clarify` is in-chat only. It must not create, update, or append Markdown decision files.
- `dispatch` may consume a user-specified Markdown intent record when the user explicitly supplies one.

Related skills and boundaries:

- Use `houmao-agent-messaging` for last-mile prompt dispatch. That lower-level skill owns gateway-preferred prompting: use the target gateway when available, otherwise use direct managed-agent prompting with forced fallback behavior when the prompt surface supports it.
- Use `houmao-agent-email-comms` for mailbox dispatch only when the operator prompt or chat context asks for mail, inbox, threaded, asynchronous, or mailbox delivery.
- Use `houmao-agent-loop-pro` or `houmao-agent-loop-lite` when the requested work needs durable orchestration, generated loop state, validation, retries, scheduling, topology contracts, or recovery.

## Operations

Meta:
- `help`: explain this skill's purpose, subcommands, in-chat clarification, route choices, common prompts, and related-skill boundaries without requiring target agents or dispatching anything.

Operator workflow:
- `clarify`: resolve operator intent without dispatching; read [subskills/clarify.md](subskills/clarify.md).
- `dispatch`: plan and send one or more routed command packets; read [subskills/dispatch.md](subskills/dispatch.md).

Prompt-only workflow:
- Treat `$houmao-operator-messaging <actionable operator prompt>` as `clarify`.
- Present the inferred target(s), route, and message in a compact Markdown table.
- Ask whether the operator wants to refine the table or dispatch it directly.
- Dispatch only after explicit confirmation.

## Dispatch Model

- Treat one-agent and multi-agent delivery as `dispatch` behavior, not separate subcommands.
- Let the user's task determine target count, ordering, reply expectations, and whether messages are identical or tailored per target.
- Default every packet to prompt delivery unless the operator prompt or chat context indicates mailbox delivery.
- Prepare a compact packet plan before sending any message.
- Route prompt packets through `houmao-agent-messaging`; use the target gateway when available, otherwise use direct managed-agent prompting with forced fallback behavior when the prompt surface supports `--force`.
- Route mailbox packets through `houmao-agent-email-comms`; choose mailbox only from operator intent or chat context, not merely because a target has a mailbox.
- Report a concise summary after dispatch, including targets, routes, sent packets, blocked packets, and record updates.

## Guardrails

- Do not dispatch while running `clarify`.
- Do not invent target agents, gateway URLs, mailbox roots, mailbox addresses, operator-origin paths, or external Markdown paths.
- Do not silently switch routes when the user requires direct prompt or mailbox delivery and that route is unavailable.
- Do not duplicate low-level command details already owned by `houmao-agent-messaging` or `houmao-agent-email-comms`.
- Do not depend on loop-internal pages, generated loop artifacts, or agent-loop state.
- Do not turn temporary operator messaging into a durable loop; recommend a loop skill when the operator asks for ongoing orchestration.
