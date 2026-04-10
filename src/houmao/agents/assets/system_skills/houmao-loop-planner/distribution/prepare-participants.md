# Prepare `participants.md`

Use this page when the bundle needs participant-local guidance written in `participants.md`.

## Workflow

1. Create one section per named participant.
2. Use the section shape from `references/section-conventions.md`.
3. Record the participant's local role and boundaries in plain language rather than forcing every field into TOML.
4. Keep each participant section focused on what that participant needs to know locally.

## Participant Section Shape

Each participant section should include:

- `Role`
- `Receives From`
- `Reports To`
- `May Call`
- `Work Artifacts`
- `Must Send`
- `Escalate When`
- `Must Not`

## Guardrails

- Do not create one separate participant TOML file by default.
- Do not leave `May Call` implied when the participant's calling boundary matters.
- Do not use `participants.md` as a hidden runtime ledger or work log.
