# Launch Agents

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
4. Launch missing live agents through `<public-entrypoint>->houmao-shared-routines->agent-instance` or supported `houmao-mgr project` surfaces.
5. Inspect live agents through maintained inspection surfaces when needed.
6. Do not send loop-start prompts or mail.

## Report

Report launched agents, already-live agents, session ids, cwd, mailbox posture when known, launch surface used, warnings for `start`, and whether `start` may proceed.
