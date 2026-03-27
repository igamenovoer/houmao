## Context

The repository currently has a mixed state after the preset/setup/auth migration. Core launch and build paths now understand the canonical parsed agent-definition model, but multiple demo and tutorial packs still drive agent startup through old recipe and blueprint concepts.

That drift appears in three forms:

1. hard-coded filesystem lookups into `brains/brain-recipes/` or `blueprints/`
2. demo helper scripts that still shell out with deprecated launch flags such as `--blueprint` or `--recipe`
3. demo-owned config and state models that still name launch inputs `blueprint`, `brain_recipe_path`, or `recipe_path`

The user only needs the agent-launching process repaired for now. Launch-adjacent behavior after startup, such as mailbox round-trips, scripted prompt exchange, reporting, and expected-output cleanup, can remain broken and be fixed in follow-up changes.

## Goals / Non-Goals

**Goals:**

- Restore demo startup for the affected demo and tutorial packs against the current preset-backed agent-definition model.
- Remove launch-critical dependencies on legacy `blueprints/` and `brains/brain-recipes/` trees from demo launch helpers.
- Define one clear launch-success threshold that implementation and verification can target consistently across the affected demos.
- Keep the repair narrowly scoped so it can be implemented quickly without dragging in every broken downstream behavior.

**Non-Goals:**

- Fixing mailbox exchange, gateway operations, reporting, replay artifacts, or tutorial output correctness after startup.
- Fully renaming every demo-owned field, report key, or fixture artifact away from `recipe` / `blueprint` terminology in this change.
- Deleting every legacy compatibility loader or fixture tree in one pass.
- Reworking the core preset/build/runtime architecture introduced by `simplify-agent-definition-model`.

## Decisions

### Repair launch paths only

This change treats a demo as repaired when its startup path can resolve a current launch target and return a successful build/session startup result.

Why this over fixing full demo behavior now:

- The broken area identified by the user is startup, not post-launch orchestration.
- Several demos have broad downstream drift; coupling launch repair to mailbox/report/reporting cleanup would slow delivery substantially.
- A launch-only threshold gives a concrete cut line for implementation and tests.

### Use preset-backed launch selection as the target model

Affected demos will launch through the current preset/setup/auth model, either directly or through thin compatibility adapters that map old demo-owned fields onto preset-backed resolution.

Why this over restoring legacy recipe/blueprint launch behavior:

- Reinvesting in recipe/blueprint launch wiring would deepen the migration debt.
- The core runtime and build surfaces already accept preset-backed data.
- Thin adapters are acceptable when they only preserve demo-local field names while resolving through current launch surfaces.

### Prioritize launch-critical callers over terminology cleanup

Implementation will first fix the code paths that actually determine agent startup: demo runtime helpers, launch argument builders, and tracked launch-input files consumed by those helpers.

Why this over broad documentation and output cleanup first:

- Several demo packs still contain legacy README text or expected-report fields that do not block startup.
- The change goal is operational launch recovery, so launch-critical wiring should move first.
- This keeps the patch set smaller and reduces incidental churn.

### Preserve compatibility-only field names when they do not force legacy resolution

Demo-owned config or persisted state MAY temporarily keep names like `recipe_path` or `brain_recipe_path` if the value now points at preset-backed launch inputs and the demo no longer requires legacy source-tree lookups.

Why this over immediate full renaming:

- Some demos have wide config/schema/test surfaces where renaming would create large unrelated churn.
- The immediate defect is failed startup, not terminology purity.
- This allows a later cleanup change to rename fields after launch behavior is stable again.

### Verify repaired demos with launch-focused checks

Tests and smoke verification for this change will assert successful launch resolution, brain build/session start, and the presence of expected startup artifacts or startup metadata. They will not require post-launch business behavior to pass.

Why this over reusing full end-to-end demo assertions:

- Many existing end-to-end assertions include deferred behaviors that are explicitly out of scope.
- Launch-focused checks better match the temporary repair objective.

## Risks / Trade-offs

- [Partial recovery leaves demos operationally incomplete] -> Document that launch is the only success criterion for this change and leave follow-up tasks for post-launch behavior.
- [Compatibility field names linger longer] -> Restrict compatibility to demo-local surfaces and ensure the underlying launch path is preset-backed.
- [Different demos need different migration shapes] -> Group implementation by launch pattern: native resolver demos, realm-controller shell-out demos, and script-helper demos.
- [Launch-only tests may miss regressions in later steps] -> Call out that limitation explicitly and schedule later changes for mailbox/reporting/output repair.

## Migration Plan

1. Inventory affected demos by launch pattern and identify the exact launch-critical caller in each pack.
2. Update launch-critical helpers to resolve current preset-backed launch inputs and current public build/start surfaces.
3. Update tracked demo launch inputs only where required for startup.
4. Add launch-focused verification for the affected demos.
5. Leave post-launch behavior, reporting cleanup, and broader terminology cleanup for follow-up changes.

Rollback strategy: revert the demo-launch recovery change as one unit. This change is intentionally scoped so rollback does not need a mixed steady state.

## Open Questions

- Which demo packs should be included in the first implementation batch if the full inventory proves too large for one patch set?
- For demos with wide config/report schemas, is it preferable to keep compatibility field names temporarily or to rename them immediately when touching launch inputs?
