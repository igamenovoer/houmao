# Generate Execplan

Use this page when the user wants generated execution material from current v5 intention source.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read the relevant files under `<loop-dir>/intention/`. Do not require `adrs/`.

## Generated Shape

Create or replace generated material under:

```text
<loop-dir>/execplan/
  manifest.toml
  specs/
    objective/
    collab/
    comms/
    state/
    workspace/
    participants/
  skills/
  agents/
  harness/
  docs/
```

Minimum responsibilities:
- `manifest.toml` indexes generated artifacts, generated-source posture, and plan revision.
- `specs/` contains machine-readable loop contracts. Use subdirectories only when the loop needs them:
  - `specs/objective/` for goals, constraints, success posture, and references to policy sections.
  - `specs/collab/` for topology, scheduling policy, handoff rules, and structured collaboration record schemas.
  - `specs/comms/` for mail or message schemas, template registries, and renderers.
  - `specs/state/` for runtime state schemas, seed data, and invariants when the loop needs bookkeeping state.
  - `specs/workspace/` for workdir, command, artifact, environment, or path contracts.
  - `specs/participants/` for abstract participant roles and stable role instances.
- `skills/` contains generated on-event skills, on-tick skills, lifecycle skills, or shared utility skills. Keep each skill bounded to one trigger or role responsibility.
- `agents/` contains concrete agent bindings and prompt sources that map live Houmao agents to participant roles, installed skills, and workspace policy.
- `harness/` contains the plan-local command surface for data-model validation, dynamic lookup, query, rendering, controlled record application, and other deterministic loop-local mechanics.
- `docs/` contains generated human support views that explain generated contracts without becoming source authority.

For mail-driven loops, generate communication around this path:

```text
TOML payload -> schema validation -> Markdown rendering -> maintained Houmao mail send
```

Use the same structured-payload, schema-validation, and renderer pattern for any artifact that must be both machine-recorded and human-readable.

## Procedure

1. Confirm `<loop-dir>` and intention files exist.
2. Derive the execplan from intention source only.
3. Identify which generated contract layers are needed: objective, collaboration, communication, state, workspace, participants, skills, agents, harness, and docs.
4. Generate domain-specific objectives, roles, policies, evidence gates, and tools only when intention source states them.
5. Put dynamic values that agents need during work into generated specs, runtime state, or harness lookup surfaces rather than baking them into static skill prose.
6. Generate on-event skills for concrete incoming events such as received schema-specific mail, and on-tick skills for scheduler-like responsibilities that do not belong to one incoming event.
7. Mark generated Markdown with a clear generated-source note or metadata block.
8. Keep generated skill files concise and progressively disclosed.
9. Preserve unresolved assumptions as explicit `UNRESOLVED - <reason>` entries.
10. Run the v5 `validate-execplan` operation before reporting completion.

## Boundaries

- Do not treat generated `execplan/` as editable source.
- Do not require ADR discovery.
- Do not copy CUDA/Hopper policies into unrelated loops.
- Do not make one reference topology, state backend, scheduler, communication schema set, or harness command set mandatory for all loops.
- Do not create platform launch side effects from this page.
