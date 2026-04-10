# Prepare `distribution.md`

Use this page when the bundle needs operator-managed distribution guidance written in `distribution.md`.

## Workflow

1. Describe what the operator should send to each participant.
2. Describe which acknowledgements, readiness signals, or confirmations the operator should expect.
3. Add a pre-start checklist for the operator.
4. State which existing runtime skill should be used next once distribution is complete.

## Required Sections

`distribution.md` should include at minimum:

- `Send To Participants`
- `Expected Confirmations`
- `Before Start`
- `Next Runtime Skill`

## Guardrails

- Distribution remains the operator's responsibility.
- Do not imply that `houmao-loop-planner` delivers artifacts to agents automatically.
- Do not hide the next runtime skill choice inside `plan.md` only; keep it visible in `distribution.md`.
