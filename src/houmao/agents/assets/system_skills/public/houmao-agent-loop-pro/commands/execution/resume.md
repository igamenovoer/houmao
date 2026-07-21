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

# Resume

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Loop is paused.
- Continuation state is known and valid.

## Inputs

Require:
- `<loop-dir>`
- run identity
- evidence that the loop is paused rather than interrupted or inconsistent

## Actions

1. Validate the execplan.
2. Query generated operator-control guidance or harness control status when available.
3. Query generated harness state or read-only status surfaces.
4. Confirm the run is paused and has a coherent continuation point.
5. Preserve or restore the intended execution mode; do not silently convert manual mode to auto mode.
6. Restore wakeup posture through `houmao-shared-routines->houmao-agent-gateway` when pause disabled reminders or mail notifiers and auto mode is intended.
7. Deliver resume prompts or mail through `houmao-shared-routines->houmao-agent-messaging` or `houmao-shared-routines->houmao-agent-email-comms`.
8. Report resumed participants, execution mode, notifier posture, and the next expected status check.

## Constraints

- Do not use resume for interrupted, inconsistent, or partially relaunched runs; use `recover`.
- Do not update execplan during resume.
- Do not bypass generated resume guidance when the execplan provides it.
