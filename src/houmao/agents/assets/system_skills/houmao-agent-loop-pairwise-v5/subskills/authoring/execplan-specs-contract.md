# Execplan Specs Contract

## Preconditions

- `execplan-specs-process` has produced a current process model.

## Inputs

Require:
- `<loop-dir>`
- current intention source;
- generated process overview at `<loop-dir>/execplan/specs/collab/collab-overview.md`.

## Outputs

Generate or update concrete contracts derived from the process model:
- objective and success posture;
- participants and stable role instances;
- topology and route constraints;
- communication schemas, renderers, registry, and reply links;
- notification prompt and trigger contracts for mail-driven participants;
- state kernel and record schemas when durable bookkeeping is needed;
- workspace and run artifact contracts when work roots or durable artifacts are needed;
- explicit omission notes for unused contract areas.

Use these canonical paths when the corresponding concern exists:

```text
<loop-dir>/execplan/specs/
  README.md
  objective/
    README.md
    objective.toml
    policy.toml
  collab/
    README.md
    collab-overview.md
    loop-policy.toml
    topology/
      README.md
      topology.toml
    records/
      README.md
      <record-family>.schema.json
  comms/
    README.md
    comms-overview.md
    templates.toml
    schemas/
      README.md
      <message-family>.schema.json
    renderers/
      README.md
      <message-family>.md.j2
  state/
    README.md
    state-overview.md
    schema.sql
    seed.toml
    invariants.toml
    records/
      <record-family>.schema.json
  workspace/
    README.md
    workspace.toml
  run/
    README.md
    run-artifacts.toml
  participants/
    README.md
    participants.toml
    <participant-role>.md
```

`specs/collab/collab-overview.md` is created by the process stage and must not be replaced by a flat `specs/process.md`. Optional files may be omitted, but any omission of a default concern that later artifacts would normally need must be recorded in the manifest, generated docs, or validation notes.

## Actions

1. Read `<loop-dir>/execplan/specs/collab/collab-overview.md` first.
2. Derive objective, participant, topology, communication, state, record, workspace, and run contracts from process needs.
3. Keep participant role templates, participant instances, and concrete agent bindings separate; agent bindings are not generated in this stage.
4. Create or update README files for every emitted generated artifact directory using only `Purpose` and `Contents`.
5. Use schema-validated payload plus human-readable rendering for mail-driven or structurally recorded human-facing artifacts.
6. For mail-driven loops, derive notifier prompt contracts from the process model, including which on-event skill handles each received message family and which on-tick skill runs after mail when required.
7. Generate task-specific records only when intention or process specs introduce them.
8. Record explicit omissions for irrelevant default layers.

## Bookkeeping State Contracts

When durable bookkeeping is needed:

- treat state as runtime control-plane state for scheduling, ownership, validation, recovery, transition audit, and completion;
- keep rich request/reply prose, rendered Markdown, rationale, pseudocode, and detailed analysis in mail, docs, or artifacts;
- store compact facts and durable refs in state:
  - ids and stable refs;
  - statuses and allowed states;
  - active ownership and handoffs;
  - scalar gates, scores, pass/fail facts, decisions, and approvals;
  - mail, evidence, artifact, command, commit, or external-result refs;
  - timestamps and compact transition audit.
- make every important transition reconstructable from changed entity, actor or source, new state or decision, mail/evidence/artifact refs, and timestamp;
- model operator override, pause, prune, stop, repair, or recovery authority as explicit operator intent events when those controls exist;
- define finite valid state through allowed states, statuses, transitions, and invariants.

Default backend:

- use sqlite when stable entities and transitions can be expressed as a clear SQL schema;
- emit `specs/state/schema.sql` as the field-level authority for sqlite state;
- use JSONL plus explicit record schemas only for append-only, schema-light, or intentionally denormalized state;
- do not use unstructured ad hoc state files when sqlite or JSONL plus schema is feasible.

Default `specs/state/` package:

```text
specs/state/
  README.md
  state-overview.md
  schema.sql                 # sqlite default when SQL schema is clear
  seed.toml                  # when deterministic initialization is needed
  invariants.toml            # when validation needs named checks
  records/
    <record-family>.schema.json  # when JSONL or structured record payloads are emitted
```

`state-overview.md` must describe state authority, boundaries, minimal entity families, allowed transitions, invariants, scheduling queries, and what state must not store.

Consider these generic entity families and emit only the subset the loop needs:

- `process_state`
- `participants`
- `work_items`
- `handoffs`
- `mail_payloads`
- `attempts`
- `decisions`
- `evidence`
- `artifacts`
- `operator_intent_events`
- `events`

## Generated TOML Style

For generated TOML contracts:

- put a plain human-readable comment above each generated section or table-array header;
- include concise `description` fields for records or sections exposed through harness commands;
- use `description` fields, not comments, as the source for harness `--explain`;
- use comments only for in-place readability;
- do not require record-level descriptions for private mechanical TOML files that are never surfaced to agents or operators.

## Downstream Effects

- Changes here invalidate harness, skills, agent bindings, final docs, and final manifest.

## Constraints

- Do not generate harness code, role skills, concrete agent configs, or final docs from this stage.
- Do not require a specific state backend unless the process model selects it.
- Do not create platform side effects.
- Do not define any contract that requires an agent to wait inside a chat turn for future work.
- Do not read a flat `execplan/specs/process.md` as the canonical process source; require the process stage to emit `execplan/specs/collab/collab-overview.md`.
