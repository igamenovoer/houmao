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

- Operator wants to end one loop run.

## Inputs

Require:
- `<loop-dir>`
- run identity
- desired stop posture when the user has one

## Actions

1. Validate enough execplan context to identify generated stop guidance.
2. Use generated operator-control guidance or harness `control stop` surfaces when available.
3. Route managed-agent lifecycle stop work through `houmao-shared-routines->houmao-agent-instance`.
4. Route final prompts, mailbox notices, or interrupts through `houmao-shared-routines->houmao-agent-messaging` or `houmao-shared-routines->houmao-agent-email-comms`.
5. Route gateway notifier shutdown or reminder cleanup through `houmao-shared-routines->houmao-agent-gateway`.
6. Run a final read-only status check and report stopped participants, final execution mode or notifier posture when known, retained artifacts, and cleanup options.

## Constraints

- Do not delete `<loop-dir>/intention/` or `<loop-dir>/execplan/`.
- Do not cleanup stopped-session artifacts unless the user asks for cleanup.
- Do not redefine stop as hard-kill unless the user asks for emergency interruption.
