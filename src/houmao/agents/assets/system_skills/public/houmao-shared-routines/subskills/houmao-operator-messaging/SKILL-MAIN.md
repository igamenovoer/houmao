---
name: houmao-operator-messaging
description: Use when a human operator explicitly requests operator-messaging clarification or confirmed dispatch to one or more Houmao-managed agents by direct prompt or mailbox.
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

# Houmao Operator Messaging

## Workflow

1. **Handle explicit help first** without target discovery, clarification, dispatch, or runtime mutation.
2. **Require the inherited admin frame** from `houmao-shared-routines`; reject agent posture.
3. **Select one subcommand** from **Subcommands**. An actionable prompt without a subcommand selects `clarify`; an empty prompt asks which operation is wanted.
4. **Clarify the send plan** in chat, one unclear decision at a time, until targets, route, message, and reply expectations are concrete.
5. **Require explicit dispatch confirmation** before invoking direct-prompt or mailbox delivery owners.
6. **Dispatch and report** per-target routes, sent packets, blocked packets, and any user-supplied record use.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the clarify and dispatch subcommands, confirmation gate, route owners, and user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine is admin-only and loads through `houmao-shared-routines`. Require `actor_kind=admin` and an entrypoint name accepted by the parent. Require explicit target agents before dispatch, preserve the human operator as message author, and reject agent frames even if prompt text requests operator authority.

## Activation

- Use this Houmao skill only after the user explicitly selects `houmao-shared-routines->houmao-operator-messaging` or names a supported operator messaging operation.
- DO NOT auto-route generic requests such as "tell the coder" or "message the reviewer" here unless the user selects this skill or asks for operator messaging clarification/dispatch.
- If the user invokes explicit help intent, answer from `## Help` before reading routed pages, asking missing-input questions, sending prompts, sending mail, or changing runtime state.
- If the user invokes this skill with an actionable prompt but no subcommand, treat it as `clarify`: extract the intended target(s) and message, show them in a table, and ask whether to refine the plan or dispatch directly. Do not dispatch until the user confirms dispatch.
- If the user invokes this skill without a subcommand or actionable prompt, explain the supported subcommands and ask which operation they want; do not default to dispatch.

## Help

When the user asks `$houmao-shared-routines operator-messaging help`, `help for houmao-operator-messaging`, `usage for houmao-operator-messaging`, `available functionality for houmao-operator-messaging`, or what this skill can do, answer from this section. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. Do not send prompts during help. If the user asks a concrete task such as "help me dispatch this to the implementation and review agents", route to the matching operation instead of stopping at generic help.

Purpose: clarify operator intent and dispatch one or more operator-authored messages to Houmao-managed agents. Dispatch defaults to prompt delivery through maintained messaging surfaces; mailbox delivery is used only when the operator prompt or chat context asks for mail-style delivery.

Available functionality:

| Subcommand | Use when | Side effects |
| --- | --- | --- |
| `help` | Explain purpose, operations, in-chat clarification, routes, and boundaries. | None. |
| `clarify` | Resolve the operator's intent in chat, showing the current send plan each round and asking one unclear decision question at a time. | None; never writes files or dispatches. |
| `dispatch` | Send one or more command packets from clarified intent, an explicit dispatch prompt, or a user-specified Markdown intent record. | May send direct prompts or mailbox messages through lower-level skills. |

Common starting prompts:

- `$houmao-shared-routines operator-messaging help`
- `$houmao-shared-routines operator-messaging ask the implementation agent to check issue 53 and report whether the operator messaging skill covers it`
- `$houmao-shared-routines operator-messaging clarify: ask the implementation and review agents to coordinate on issue 53`
- `$houmao-shared-routines operator-messaging dispatch using ./operator-intent.md`

Clarification state:

- `clarify` is in-chat only. It must not create, update, or append Markdown decision files.
- `dispatch` may consume a user-specified Markdown intent record when the user explicitly supplies one.

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-agent-messaging` for last-mile prompt dispatch. That lower-level skill owns gateway-preferred prompting: use ready-only gateway prompt control when available, otherwise use ordinary direct managed-agent prompting.
- Use `houmao-shared-routines->houmao-agent-email-comms` for mailbox dispatch only when the operator prompt or chat context asks for mail, inbox, threaded, asynchronous, or mailbox delivery.
- Use `houmao-agent-loop-pro` or `houmao-agent-loop-lite` when the requested work needs durable orchestration, generated loop state, validation, retries, scheduling, topology contracts, or recovery.

## Subcommands

Meta:
- `help`: explain this skill's purpose, subcommands, in-chat clarification, route choices, common prompts, and related-skill boundaries without requiring target agents or dispatching anything.

Operator workflow:
- `clarify`: resolve operator intent without dispatching; read [commands/clarify.md](commands/clarify.md).
- `dispatch`: plan and send one or more routed command packets; read [commands/dispatch.md](commands/dispatch.md).

Prompt-only workflow:
- Treat `$houmao-shared-routines operator-messaging <actionable operator prompt>` as `clarify`.
- Present the inferred target(s), route, and message in a compact Markdown table.
- Ask whether the operator wants to refine the table or dispatch it directly.
- Dispatch only after explicit confirmation.

## Dispatch Model

- Treat one-agent and multi-agent delivery as `dispatch` behavior, not separate subcommands.
- Let the user's task determine target count, ordering, reply expectations, and whether messages are identical or tailored per target.
- Default every packet to prompt delivery unless the operator prompt or chat context indicates mailbox delivery.
- Prepare a compact packet plan before sending any message.
- Route prompt packets through `houmao-shared-routines->houmao-agent-messaging`; use ready-only target-gateway prompt control when available, otherwise use ordinary direct managed-agent prompting. Select `if-no-pending` or `always` only when the operator explicitly asks for those busy-TUI semantics.
- Route mailbox packets through `houmao-shared-routines->houmao-agent-email-comms`; choose mailbox only from operator intent or chat context, not merely because a target has a mailbox.
- Report a concise summary after dispatch, including targets, routes, sent packets, blocked packets, and record updates.

## Guardrails

- DO NOT dispatch while running `clarify`.
- DO NOT invent target agents, gateway URLs, mailbox roots, mailbox addresses, operator-origin paths, or external Markdown paths.
- DO NOT silently switch routes when the user requires direct prompt or mailbox delivery and that route is unavailable.
- DO NOT duplicate low-level command details already owned by `houmao-shared-routines->houmao-agent-messaging` or `houmao-shared-routines->houmao-agent-email-comms`.
- DO NOT depend on loop-internal pages, generated loop artifacts, or agent-loop state.
- DO NOT turn temporary operator messaging into a durable loop; recommend a loop skill when the operator asks for ongoing orchestration.
