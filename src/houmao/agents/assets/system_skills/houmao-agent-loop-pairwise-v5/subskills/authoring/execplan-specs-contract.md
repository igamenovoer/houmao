# Execplan Specs Contract

## Preconditions

- `execplan-specs-process` has produced a current process model.

## Inputs

Require:
- `<loop-dir>`
- current intention source;
- generated process specs under `<loop-dir>/execplan/specs/`.

## Outputs

Generate or update concrete contracts derived from the process model:
- objective and success posture;
- participants and stable role instances;
- topology and route constraints;
- communication schemas, renderers, registry, and reply links;
- state kernel and record schemas when durable bookkeeping is needed;
- workspace and run artifact contracts when work roots or durable artifacts are needed;
- explicit omission notes for unused contract areas.

## Actions

1. Read the process model first.
2. Derive objective, participant, topology, communication, state, record, workspace, and run contracts from process needs.
3. Keep participant role templates, participant instances, and concrete agent bindings separate; agent bindings are not generated in this stage.
4. Use schema-validated payload plus human-readable rendering for mail-driven or structurally recorded human-facing artifacts.
5. Generate task-specific records only when intention or process specs introduce them.
6. Record explicit omissions for irrelevant default layers.

## Downstream Effects

- Changes here invalidate harness, skills, agent bindings, final docs, and final manifest.

## Constraints

- Do not generate harness code, role skills, concrete agent configs, or final docs from this stage.
- Do not require a specific state backend unless the process model selects it.
- Do not create platform side effects.
