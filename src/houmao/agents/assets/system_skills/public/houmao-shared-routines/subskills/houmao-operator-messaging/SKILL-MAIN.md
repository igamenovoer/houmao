---
name: houmao-operator-messaging
description: Use when a human operator explicitly requests operator-messaging clarification or confirmed dispatch to one or more Houmao-managed agents via attributed request, direct prompt, or mailbox.
metadata:
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

## Overview

Clarify human-operator message plans in chat and dispatch confirmed packets to one or more managed agents via direct `prompt`, attributed `request`, or `mailbox` delivery.

## Workflow

1. **Answer explicit `help` first** from **Help** without probing targets, writing files, or sending messages.
2. **Enforce the Actor Frame Gate**: require `actor_kind=admin` from `houmao-shared-routines` and explicit target agents before dispatch; reject `agent` frames.
3. **Select one subcommand** from **Subcommands**: an actionable operator prompt without a subcommand always enters `clarify` (never dispatching automatically); an empty invocation asks which operation the operator wants.
4. **Clarify in chat** via [commands/clarify.md](commands/clarify.md), presenting the send-plan table and asking at most one high-impact question per round without writing Markdown decision files.
5. **Require explicit operator confirmation** before running [commands/dispatch.md](commands/dispatch.md), then delegate last-mile delivery to `houmao-shared-routines->houmao-agent-messaging` (`prompt` or `request`) or `houmao-shared-routines->houmao-agent-email-comms` (`mailbox`).
6. **Report per-packet outcomes** (targets reached, delivery route used, blocked packets, and any operator-supplied Markdown record updates).

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **Channel Selection**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine is `admin`-only under `houmao-shared-routines` and activates only when explicitly selected (do not auto-route casual single-turn "tell agent X" requests unless the operator asks for operator-messaging clarification or multi-packet dispatch). Reject `agent` frames, preserve the human operator as author, and recommend `houmao-agent-loop-pro` or `houmao-agent-loop-lite` when durable state, retries, scheduling, or loop recovery is requested.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `clarify` | Refine targets, delivery route, message text, and ordering strictly in chat (default for actionable prompts with no subcommand). | [commands/clarify.md](commands/clarify.md) |
| `dispatch` | Send confirmed one-agent or multi-agent packets (from chat plan, explicit dispatch prompt, or user-supplied Markdown record). | [commands/dispatch.md](commands/dispatch.md) |
| `help` | Read-only summary of in-chat `clarify`, confirmed `dispatch`, and `prompt` vs `request` vs `mailbox` vs `houmao-cccc` boundaries. | **Help** |

## Channel Selection and Help

- **Direct `prompt` (default)**: `agents single ... prompt` (`ready-only` admission when gateway-attached unless `if-no-pending`/`always` is requested; requires `agent-operator` authority on keyed gateways; supported across `tui`, `headless`, `service`, and `web`).
- **Attributed `request`**: `agents single ... request --text ...` (`agent-requester` default authority; use when submitting attributed work under the target agent's standing instructions without `agent-operator` turn injection).
- **`mailbox` packet**: operator `post` (or managed-origin `send`) via `houmao-shared-routines->houmao-agent-email-comms`, selected only when the operator or context asks for mail, inbox, or asynchronous thread delivery.
- **`houmao-cccc` boundary**: `houmao-cccc` group chat and delivery queues (`houmao-shared-routines->houmao-agent-gateway` / `houmao-adv-usage-pattern`) are separate plugin group-chat channels, not native operator `prompt`, `request`, or `mailbox` packets.

Explicit `help` explains these boundaries read-only without requiring targets.

## Guardrails

- DO NOT dispatch messages or write Markdown decision files during `clarify`, or dispatch an actionable prompt without explicit confirmation.
- DO NOT invent target IDs, gateway URLs, mailbox addresses, or external Markdown record paths.
- DO NOT silently fall back across `prompt`, `request`, `mailbox`, or `houmao-cccc` when the requested route is blocked or unauthorized.
- DO NOT turn temporary operator dispatch into a durable polling or retry loop; recommend `houmao-agent-loop-pro` or `houmao-agent-loop-lite` instead.
