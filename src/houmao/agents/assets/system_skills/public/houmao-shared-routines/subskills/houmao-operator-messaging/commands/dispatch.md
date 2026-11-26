---
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

# Dispatch Confirmed Operator Packets

## Workflow

1. **Verify dispatch readiness**: start from confirmed chat `clarify` state, an explicit `dispatch` request, or an operator-supplied Markdown intent file (read only that exact path). If broad intent is still unclear, stop and recommend `clarify`; if durable loop orchestration is needed, recommend `houmao-agent-loop-pro` or `houmao-agent-loop-lite`.
2. **Build the one-agent or multi-agent packet plan** (`Target`, `Route`, `Content`, `Order`, `Reply expectation`, `Record update`) without asking the operator to pick separate single vs multi-agent modes.
3. **Select each packet's delivery route** using **Route Selection Matrix** below, stopping for any blocking ambiguity rather than guessing or silently switching channels.
4. **Delegate last-mile execution** in the required order (halting partial batches if a failure would leave misleading coordination state):
   - `prompt` or `request`: delegate to `houmao-shared-routines->houmao-agent-messaging`.
   - `mailbox`: delegate to `houmao-shared-routines->houmao-agent-email-comms` (using operator-origin `post` when outside a managed mailbox session, or own mailbox `send` when acting from a bound managed session).
5. **Update any operator-specified Markdown record** concisely and report packets planned/sent, targets reached, routes used, blocked packets, and expected replies.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step dispatch plan from **Route Selection Matrix** and the confirmed intent, then execute the plan.

## Route Selection Matrix

| Route | When to Select | Authority & Run-Mode Behavior |
| --- | --- | --- |
| `prompt` (default) | Default for operator packets unless `request` attribution or `mailbox` delivery is requested. | Requires `agent-operator` on keyed gateways; uses `ready-only` gateway admission by default (`if-no-pending` or `always` only when requested) across `tui`, `headless`, `service` (persistent service request protocol), and `web`. |
| `request` | Operator wants attributed task submission under the target agent's existing instructions or caller holds `agent-requester` default authority without `agent-operator`. | Uses `agents single ... request --text <task>` (`agent.request.submit`, allowed by default `agent-requester` group) across live/passive targets including `service` and `web`. |
| `mailbox` | Prompt or context asks for mail, inbox, threaded, or asynchronous mailbox delivery. | Uses `houmao-shared-routines->houmao-agent-email-comms` (`post` for external operator origin); never chosen merely because a mailbox exists. |
| `houmao-cccc` (out of band) | Explicit `houmao-cccc` group chat/queue work only. | Handled via `houmao-cccc` CLI / gateway plugin (`houmao-shared-routines->houmao-agent-gateway`), separate from operator `prompt`, `request`, and `mailbox` dispatch. |

## Guardrails

- DO NOT silently downgrade a denied `prompt` to `request`/`mailbox` or switch channels without operator approval.
- DO NOT invent per-operator mailbox addresses or search for unstated Markdown record files.
