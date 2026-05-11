# Resume

Use this page when a paused loop should continue from known valid state.

## Inputs

Require:
- `<loop-dir>`
- run identity
- evidence that the loop is paused rather than interrupted or inconsistent

## Procedure

1. Validate the execplan.
2. Query generated harness state or read-only status surfaces.
3. Confirm the run is paused and has a coherent continuation point.
4. Restore wakeup posture through `houmao-agent-gateway` when pause disabled reminders or mail notifiers.
5. Deliver resume prompts or mail through `houmao-agent-messaging` or `houmao-agent-email-comms`.
6. Report resumed participants and the next expected status check.

## Boundaries

- Do not use resume for interrupted, inconsistent, or partially relaunched runs; use `recover`.
- Do not regenerate execplan during resume.
- Do not bypass generated resume guidance when the execplan provides it.
