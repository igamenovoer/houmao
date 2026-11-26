---
name: houmao-adv-usage-pattern
description: Use when composing lightweight multi-step Houmao coordination patterns for self-notification, notifier-prompt-driven mail rounds, local-close pairwise edge loops, forward relay loops, or `houmao-cccc` push/pull queues below full loop packages.
license: MIT
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

# Houmao Advanced Usage Patterns

## Overview

Compose lightweight, non-polling multi-step Houmao patterns (self-notification, notifier mail loops, pairwise edge loops, relay loops, and `houmao-cccc` push/pull queues) layered above single-action skills and below generated `lite`/`pro` loop packages.

## Workflow

1. **Answer explicit `help` first** from **Help** without executing mailbox, gateway, or messaging commands.
2. **Enforce the Actor Frame Gate** and route single-step operations directly to their owning routines (`houmao-agent-email-comms`, `houmao-agent-gateway`, `houmao-agent-messaging`, `houmao-process-emails-via-gateway`) or full generated loops to `houmao-agent-loop-lite` / `houmao-agent-loop-pro`.
3. **Select one pattern** from **Subcommands** using **Multi-Agent Coordination Chooser**, then load only its command page (plus [references/shared-loop-ledger-and-resend.md](references/shared-loop-ledger-and-resend.md) for pairwise, relay, or `houmao-cccc` coordination).
4. **Execute one bounded turn** honoring channel pinning, idempotent ledger/dedupe state, and immediate turn termination without in-chat sleeping or polling.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **Multi-Agent Coordination Chooser**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Admin callers require explicit targets; verified `agent` callers default self-scoped wakeups to verified self and require explicit peer targets otherwise.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `self-notification` | Choose between focus-first gateway reminders and durable self-mail backlog (aliases `self-notification-via-reminders`, `self-wakeup-via-self-mail`). | [commands/self-notification.md](commands/self-notification.md) ([reminders mode](commands/self-notification-via-reminders.md), [self-mail mode](commands/self-wakeup-via-self-mail.md)) |
| `notifier-prompt-driven-mail-loop` | Drive bounded `on-event` mail processing (`schema_version: 3`) plus optional single-pass `on-tick` via `mail-notifier`. | [commands/notifier-prompt-driven-mail-loop.md](commands/notifier-prompt-driven-mail-loop.md) |
| `pairwise-edge-loop` | Run one local-close `driver -> worker -> driver` round via attributed `request` or queued `prompt` plus mail return (aliases `local-close-edge-loop`, `pairwise edge-loop`, `pairwise-edge-loop-via-gateway-and-mailbox`). | [commands/pairwise-edge-loop-via-gateway-and-mailbox.md](commands/pairwise-edge-loop-via-gateway-and-mailbox.md) |
| `relay-loop` | Run one ordered `origin -> ingress -> relay -> egress -> origin` forward lane (alias `relay-loop-via-gateway-and-mailbox`). | [commands/relay-loop-via-gateway-and-mailbox.md](commands/relay-loop-via-gateway-and-mailbox.md) |
| `help` | Read-only chooser across self-notification, notifier mail loops, pairwise/relay loops, `houmao-cccc`, and `lite`/`pro` loops. | **Help** |

## Multi-Agent Coordination Chooser and Help

- **`pairwise-edge-loop`**: one driver delegates one `edge_loop_id` to one worker (via `agents single ... request --text` under `agent-requester` default or `prompt` under `agent-operator`) and receives the final result back directly.
- **`relay-loop`**: one origin starts an ordered forward lane (`loop_id` + per-hop `handoff_id`) whose final egress emails the result back to the origin.
- **`notifier-prompt-driven-mail-loop`**: `mail-notifier` wakes an idle agent for bounded `schema_version: 3` mail handling plus at most one `on-tick` pass.
- **`houmao-cccc` push/pull/queue option**: when agents share a CCCC group via the gateway plugin (`/v1/plugins/{instance}/*`) or `--direct-profile`, use `houmao-cccc chat send|reply|pull|deliveries` (`--operation-id`, `--connection-token`, `--handle` / `--event-ref`) for group chat/queue coordination; see [references/shared-loop-ledger-and-resend.md](references/shared-loop-ledger-and-resend.md).
- **`houmao-agent-loop-lite` vs `houmao-agent-loop-pro`**: escalate to `lite` for generated Markdown contracts + direct SQLite state, or `pro` (`tree-loop` / `generic-loop`) for multi-edge graphs, schemas, harness validation, and run control.

Explicit `help` explains these choices read-only.

## Guardrails

- DO NOT use this skill for a single direct mail, prompt, request, reminder, or notifier command when the owning child routine suffices, or as a substitute for `houmao-agent-loop-lite` / `houmao-agent-loop-pro` graph orchestration.
- DO NOT claim durability beyond what the chosen transport (`reminders` vs `offline`/`online` mail vs `houmao-cccc`) guarantees.
- DO NOT instruct agents to sleep, poll, tail logs, or hold a chat turn open waiting for downstream replies or ticks.
