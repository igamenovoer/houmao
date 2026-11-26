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

# Clarify Operator Message Plan

## Workflow

1. **Keep `clarify` strictly read-only and in-chat**: never send prompts, requests, or mail, mutate runtime state, or create/update Markdown decision files (unless the operator explicitly names an output file path).
2. **Assess coverage** across objective, target agent(s), message content, context references, safety/authorization constraints (`prompt` `agent-operator` vs `request` `agent-requester` vs `mailbox`), target run mode (`tui`, `headless`, `service`, `web`), ordering, and accepted ambiguity.
3. **Render the current send-plan table** at the start of every round (marking unresolved cells explicitly rather than guessing):

   | Target or selection rule | Route (`prompt` \| `request` \| `mailbox`) | Message to send |
   | --- | --- | --- |
   | `<agent or rule>` | `<route>` | `<summary or exact short message>` |

4. **Ask at most one high-impact decision question** per round (preferring `<= 5` rounds total before summarizing) using three concrete choices (`1` marked `(Recommended)` + short reason) plus `4. Other`, followed by: `"After that choice, should I dispatch this plan or continue clarifying?"`
5. **Stop when ready or accepted**: once targets, route, safety, and success criteria are clear (or remaining ambiguity is explicitly accepted), summarize readiness and wait for explicit `dispatch` confirmation.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded in-chat clarification plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the operator prompt, then execute the plan.

## Guardrails

- DO NOT dispatch any packet during `clarify` or write unrequested clarification Markdown files.
- DO NOT ask cosmetic wording questions while targets, channel (`prompt` vs `request` vs `mailbox`), safety, or ordering remain unclear, or force `Required`/`Optional` CLI labels onto domain-intent questions.
