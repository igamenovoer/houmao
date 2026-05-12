# Status

## Read First

- `../reference/generated-contract-defaults.md`
- `../reference/platform-boundaries.md`

## Preconditions

- User wants read-only inspection of one loop.

## Inputs

Require:
- `<loop-dir>`
- the run identity or enough context to identify the generated loop run

## Actions

1. Read `execplan/manifest.toml` to locate generated status, harness, run artifact, or docs surfaces.
2. Query generated harness status, validation, completion, or view commands when available.
3. Inspect the generated run artifact layout for recorded payloads, responses, records, state, logs, evidence, and blockers when those artifacts exist.
4. Use `houmao-agent-inspect` for managed-agent liveness, screen, logs, mailbox posture, gateway state, or artifacts.
5. Use mailbox or gateway skills only for read-oriented status when needed.
6. Report current run state, active participants, pending handoffs, blockers, relevant run artifacts, and the next expected operator action.

## Constraints

- Do not mutate runtime state.
- Do not send keepalive prompts as part of status.
- Do not infer completion from stale intention notes.
- Do not inspect raw runtime internals when a maintained status surface exists.
