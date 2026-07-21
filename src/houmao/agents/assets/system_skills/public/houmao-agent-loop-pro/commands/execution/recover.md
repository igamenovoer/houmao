# Recover

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Use after any of:
  - interruption;
  - failed setup;
  - partial handoff;
  - inconsistent runtime state;
  - stopped participants;
  - uncertain loop posture.

## Inputs

Require:
- `<loop-dir>`
- run identity or enough artifacts to identify the affected run

## Actions

1. Stop ordinary scheduling before repair work.
2. Inspect generated operator-control guidance, harness diagnostics, managed-agent state, mailbox state, gateway state, memory posture, and run artifacts through maintained surfaces.
3. Identify the last known coherent run state, execution mode, notifier posture, and participant ownership.
4. Use generated harness repair, backup, restore, validation, control, or migration surfaces when they exist.
5. Use direct raw state edits only as explicit operator-facing maintenance when no maintained surface can do the repair.
6. Validate after repair before resuming.
7. Report recovered state, execution mode, relevant run artifact evidence, unresolved obligations, and whether `resume`, `start`, or a manual step is the correct next operation.

## Constraints

- Do not silently migrate an active run to an updated execplan.
- Do not hide duplicate or partially sent mail; report it as recovery context.
- Do not resume normal work until generated validation or equivalent checks pass.
- Do not treat user intention files as runtime repair records.
- Do not discard recorded payloads, rendered outputs, responses, records, state files, logs, or evidence during recovery.
