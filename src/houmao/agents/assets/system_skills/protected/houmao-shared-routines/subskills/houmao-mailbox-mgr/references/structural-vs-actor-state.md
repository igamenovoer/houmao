---
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

# Structural Mailbox State Versus Actor State

Use this reference when the task mentions mailbox messages and it is unclear whether the operator needs structural inspection or actor-scoped follow-up state.

## Structural Message Inspection

Use these maintained admin commands:

- `houmao-mgr mailbox messages list|get`
- `houmao-mgr project mailbox messages list|get`

Those commands inspect canonical mailbox metadata plus address-scoped structural projection data for one registered mailbox address.

## Actor-Scoped Mailbox Participation

Use `<public-entrypoint>->houmao-shared-routines->agent-email-comms` and the maintained `houmao-mgr agents self mail ...` or `houmao-mgr agents single ... mail ...` surfaces when the task is about:

- unread, read, answered, archived, and box state
- replying, sending, or checking mail as one managed agent
- message processing through a live gateway facade
- participant-local mutable state such as read, archived, or deleted follow-up

## Guardrail

Do not present structural message inspection as if it were the same thing as open-mail triage for one managed agent.
