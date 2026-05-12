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
  objective/
    objective.toml
    policy.toml
  collab/
    collab-overview.md
    loop-policy.toml
    topology/
      topology.toml
    records/
      <record-family>.schema.json
  comms/
    comms-overview.md
    templates.toml
    schemas/
      <message-family>.schema.json
    renderers/
      <message-family>.md.j2
  state/
    state-model.toml
    seed.toml
    invariants.toml
  workspace/
    workspace.toml
  run/
    run-artifacts.toml
  participants/
    participants.toml
    <participant-role>.md
```

`specs/collab/collab-overview.md` is created by the process stage and must not be replaced by a flat `specs/process.md`. Optional files may be omitted, but any omission of a default concern that later artifacts would normally need must be recorded in the manifest, generated docs, or validation notes.

## Actions

1. Read `<loop-dir>/execplan/specs/collab/collab-overview.md` first.
2. Derive objective, participant, topology, communication, state, record, workspace, and run contracts from process needs.
3. Keep participant role templates, participant instances, and concrete agent bindings separate; agent bindings are not generated in this stage.
4. Use schema-validated payload plus human-readable rendering for mail-driven or structurally recorded human-facing artifacts.
5. For mail-driven loops, derive notifier prompt contracts from the process model, including which on-event skill handles each received message family and which on-tick skill runs after mail when required.
6. Generate task-specific records only when intention or process specs introduce them.
7. Record explicit omissions for irrelevant default layers.

## Downstream Effects

- Changes here invalidate harness, skills, agent bindings, final docs, and final manifest.

## Constraints

- Do not generate harness code, role skills, concrete agent configs, or final docs from this stage.
- Do not require a specific state backend unless the process model selects it.
- Do not create platform side effects.
- Do not define any contract that requires an agent to wait inside a chat turn for future work.
- Do not read a flat `execplan/specs/process.md` as the canonical process source; require the process stage to emit `execplan/specs/collab/collab-overview.md`.
