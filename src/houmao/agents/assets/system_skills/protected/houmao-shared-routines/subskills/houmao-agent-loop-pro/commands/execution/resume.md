# Resume

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
6. Restore wakeup posture through `<public-entrypoint>->houmao-shared-routines->agent-gateway` when pause disabled reminders or mail notifiers and auto mode is intended.
7. Deliver resume prompts or mail through `<public-entrypoint>->houmao-shared-routines->agent-messaging` or `<public-entrypoint>->houmao-shared-routines->agent-email-comms`.
8. Report resumed participants, execution mode, notifier posture, and the next expected status check.

## Constraints

- Do not use resume for interrupted, inconsistent, or partially relaunched runs; use `recover`.
- Do not update execplan during resume.
- Do not bypass generated resume guidance when the execplan provides it.
