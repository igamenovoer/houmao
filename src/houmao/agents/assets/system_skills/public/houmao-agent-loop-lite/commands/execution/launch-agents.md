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

# Launch Agents

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/platform-boundaries.md`
- `../reference/runtime-mail-model.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- pre-launch readiness report from `validate-loop`
- prepared launch facts from `prepare-agents`

## Actions

1. Confirm `validate-loop` passed for the current execplan and prepared facts.
2. Confirm each participant has concrete agent/profile, launch mode, credential, workdir, generated skills, and memo posture.
3. Confirm no required participant is already live in an incompatible posture.
4. Launch missing live agents through `houmao-shared-routines->houmao-agent-instance` or supported `houmao-mgr project` surfaces.
5. Inspect live agents through maintained inspection surfaces when needed.
6. Do not send loop-start prompts or mail.

## Report

Report launched agents, already-live agents, session ids, cwd, mailbox posture when known, launch surface used, warnings for `start`, and whether `start` may proceed.
