# Direct SQLite State

## Contract

- Use `execplan/specs/state/schema.sql` as the schema authority when durable state is needed.
- Use `execplan/specs/state/README.md` for initialization, reads, writes, validation, and recovery.
- Store runtime databases under `runs/<run-id>/state.sqlite3` unless `execplan/manifest.md` records an equivalent location.
- Generated skills manipulate SQLite directly according to the state README.
- Do not route state access through a generated harness.

## Data Rules

- Store compact facts and refs: run id, participant id, work item id, owner, status, mail ref, thread ref, artifact path, decision id, timestamp, and event type.
- Avoid full mail bodies, rendered Markdown, long rationale, or detailed analysis unless the loop defines a compact extraction field.
- Use short transactions; prefer `BEGIN IMMEDIATE` for serialized writes.
- Record audit or event rows for dispatch, ownership, completion, recovery, or stop changes.
