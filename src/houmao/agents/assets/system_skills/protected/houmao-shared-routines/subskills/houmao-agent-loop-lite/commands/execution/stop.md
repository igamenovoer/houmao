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

# Stop

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`

## Actions

1. Confirm the target run and stop authority.
2. Record stop intent according to generated state guidance.
3. Route live-agent lifecycle actions through `<public-entrypoint>->houmao-shared-routines->agent-instance` only when stop policy requires them.
4. Route notifier disablement through `<public-entrypoint>->houmao-shared-routines->agent-gateway` when needed.
5. Report stopped, partially stopped, or blocked posture.

## Constraints

- Do not delete run artifacts or SQLite state as part of normal stop.
