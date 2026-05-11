# Status

Use this page for read-only inspection of one loop.

## Inputs

Require:
- `<loop-dir>`
- the run identity or enough context to identify the generated loop run

## Procedure

1. Read `execplan/manifest.toml` to locate generated status or docs surfaces.
2. Query generated harness status or view commands when available.
3. Use `houmao-agent-inspect` for managed-agent liveness, screen, logs, mailbox posture, gateway state, or artifacts.
4. Use mailbox or gateway skills only for read-oriented status when needed.
5. Report current run state, active participants, pending handoffs, blockers, and the next expected operator action.

## Boundaries

- Do not mutate runtime state.
- Do not send keepalive prompts as part of status.
- Do not infer completion from stale intention notes.
- Do not inspect raw runtime internals when a maintained status surface exists.
