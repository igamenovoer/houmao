# Recover

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

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
