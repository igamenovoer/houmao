# Update Execplan

## Read First

- `../reference/generation-pipeline.md`
- `../reference/generated-contract-defaults.md`
- `../reference/topology-modes.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- MUST READ: `../reference/runtime-mail-model.md`

## Preconditions

- Intention source changed.
- Generated `execplan/` needs to be updated.

## Inputs

Require:
- `<loop-dir>`
- current `<loop-dir>/intention/`
- existing or target `<loop-dir>/execplan/`

## Actions

1. Read current intention files.
2. Check whether a loop run is active or in an uncertain execution state.
3. If execution is active or uncertain, pause and ask the user whether to stop or recover before updating generated material.
4. Determine the earliest affected stage:
  - choose `execplan-specs-process` when intention changes affect phases, topology mode, cycles, events, handoffs, participants, tick responsibilities, ownership, terminal posture, recovery posture, message families, predecessor-context needs, result routing, or record families;
  - choose `execplan-specs-contract` when the process model is unchanged but derived objective, participant, topology, communication, state, record, workspace, or run contracts need revision;
  - choose `execplan-harness` when contracts are unchanged but harness commands, query surfaces, rendering, validation, explanations, completion, or controlled-apply behavior need revision;
  - choose `execplan-skills` when process/contracts/harness are unchanged but generated role, event, tick, shared, or operator skills need revision;
  - choose `execplan-agent-bindings` when generated skills are unchanged but concrete agent configs, definitions, installed skills, maintained support skills, memo policy, or workspace policy need revision;
  - choose `execplan-finalize` when only docs, README, manifest, generated metadata, omission notes, or consistency notes need revision.
5. Rerun the earliest affected stage and every downstream stage in dependency order.
6. Preserve stable generated names where the meaning is unchanged.
7. Assign new identifiers or mark migration needs where generated meaning changes incompatibly.
8. Run `validate-execplan`.

## Constraints

- Do not silently live-migrate active agents onto updated material.
- Do not preserve generated files merely because a user hand-edited `execplan/`; intention is the source.
- Do not require ADR files.
- Do not introduce domain policy that is absent from intention source.
