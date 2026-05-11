# Recover

Use this page after interruption, failed setup, partial handoff, inconsistent runtime state, stopped participants, or uncertain loop posture.

## Inputs

Require:
- `<loop-dir>`
- run identity or enough artifacts to identify the affected run

## Procedure

1. Stop ordinary scheduling before repair work.
2. Inspect generated execplan, harness diagnostics, managed-agent state, mailbox state, gateway state, memory posture, and runtime artifacts through maintained surfaces.
3. Identify the last known coherent state.
4. Use generated harness repair, backup, restore, validation, or migration surfaces when they exist.
5. Use direct raw state edits only as explicit operator-facing maintenance when no maintained surface can do the repair.
6. Validate after repair before resuming.
7. Report recovered state, unresolved obligations, and whether `resume` or `start` is the correct next operation.

## Boundaries

- Do not silently migrate an active run to a regenerated execplan.
- Do not hide duplicate or partially sent mail; report it as recovery context.
- Do not resume normal work until generated validation or equivalent checks pass.
- Do not treat user intention files as runtime repair records.
