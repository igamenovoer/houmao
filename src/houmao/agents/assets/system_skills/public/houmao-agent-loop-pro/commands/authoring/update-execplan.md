# Update Execplan

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/generation-pipeline.md](../../references/generation-pipeline.md)
- [../../references/generated-contract-defaults.md](../../references/generated-contract-defaults.md)
- [../../references/topology-modes.md](../../references/topology-modes.md)
- [../../references/predecessor-context.md](../../references/predecessor-context.md)
- [../../references/mail-schema-events.md](../../references/mail-schema-events.md)
- MUST READ: [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

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
3. If execution is active or uncertain, pause and ask with `Required` lifecycle decision (`stop`, `recover`, or do not update now) and `Optional` notes such as run id or operator evidence before updating generated material.
4. Determine the earliest affected stage:
  - choose `execplan-specs-process` when intention changes affect phases, topology mode, cycles, events, handoffs, participants, tick responsibilities, ownership, terminal posture, recovery posture, message families, predecessor-context needs, result routing, or record families;
  - choose `execplan-specs-contract` when the process model is unchanged but derived objective, participant, topology, communication, state, record, workspace, or run contracts need revision;
  - choose `execplan-harness` when contracts are unchanged but harness commands, query surfaces, rendering, validation, explanations, completion, or controlled-apply behavior need revision;
  - choose `execplan-skills` when process/contracts/harness are unchanged but generated role, event, tick, shared, or operator skills need revision;
  - choose `execplan-agent-bindings` when generated skills are unchanged but concrete agent configs, definitions, installed generated skills, Houmao system-skill preinstall posture, memo policy, or workspace policy need revision;
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
