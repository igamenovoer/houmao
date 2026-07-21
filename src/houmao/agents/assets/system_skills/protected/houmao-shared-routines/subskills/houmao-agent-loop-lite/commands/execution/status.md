# Status

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- run id or enough context to identify the run

## Actions

1. Read `execplan/manifest.md` and selected run artifacts.
2. Inspect SQLite state read-only according to `execplan/specs/state/README.md`.
3. Inspect generated process, pending mail refs, and artifact refs.
4. Use `<public-entrypoint>->houmao-shared-routines->agent-inspect`, mailbox, or gateway skills for live posture when needed.
5. Report run state, active participants, pending handoffs, blockers, and next operator action.

## Constraints

- Do not mutate runtime state.
- Do not send keepalive prompts.
