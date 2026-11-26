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

# Pause

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

## Actions

1. Confirm the generated loop defines pause control.
2. Record pause intent in direct SQLite state or operator notes as defined by `execplan/specs/state/README.md`.
3. Route notifier posture changes through `houmao-shared-routines->houmao-agent-gateway`.
4. Report paused posture and remaining live-agent state.

## Constraints

- Do not stop live agents unless the generated loop or operator explicitly asks.
