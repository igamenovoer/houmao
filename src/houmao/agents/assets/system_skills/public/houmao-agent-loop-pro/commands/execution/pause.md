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

- MUST READ: [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Preconditions

- Operator wants to pause normal loop scheduling, wakeup, or dispatch.
- The loop should remain intact.

## Inputs

Require:
- `<loop-dir>`
- run identity

## Actions

1. Validate the execplan enough to locate pause-capable surfaces.
2. Use generated operator-control guidance or harness `control pause` when the execplan defines a pause record or pause command.
3. Confirm whether the operator wants `pause` or `manual` mode; manual mode changes wakeup authority but is not pause.
4. Use `houmao-shared-routines->houmao-agent-messaging` for direct pause prompts when required.
5. Use `houmao-shared-routines->houmao-agent-gateway` for reminder or mail-notifier suspension when the loop relies on those wakeup paths.
6. Report what was paused, current execution mode when known, and what remains live.

## Constraints

- Do not stop agents unless the user asks to stop.
- Do not treat pause as recovery.
- Do not treat manual mode as pause.
- Do not delete mailbox, runtime, or generated execplan state.
