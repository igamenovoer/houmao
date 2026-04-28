## Context

`houmao-agent-loop-pairwise-v3` is the current workspace-aware enriched pairwise loop skill. It already supports bundle plans, routing packets, memo-first initialize, standard/custom workspace contracts, generated reporting/bookkeeping templates, and mail-first start.

Issue 47 exposes a gap in rich task-note planning: v3 can distribute important rules across `plan.md`, `routing-packets.md`, `initialize-material.md`, `reporting.md`, templates, and `agents/*.md`, while flattening source-task verbs such as `ALWAYS`, `NEVER`, `UPDATE`, `DECIDE`, `COMMIT`, and `FOLLOW` into ordinary prose. The manually tuned `team-lcr-codex-v5-beam/loop-plan/agents/` files show the desired shape: role-local hard gates, schema-like SOP verbs, explicit evidence gates, and bookkeeping templates that preserve the source contract.

This change introduces pairwise-v4 as a new packaged skill rather than mutating v3 in place. V4 keeps the v3 lifecycle and runtime posture, but changes the authoring contract from "compose a reasonable bundle" to "fill strict generated document templates and prove coverage of source constraints."

## Goals / Non-Goals

**Goals:**

- Add a manual-invocation-only `houmao-agent-loop-pairwise-v4` system skill.
- Preserve the pairwise-v3 lifecycle, workspace contract model, memo-first initialize, mail-notifier readiness, mail-first start, and recovery boundaries.
- Add v4-specific document templates that prescribe required section order and required fields for `plan.md`, role-local agent notes, reporting templates, bookkeeping templates, and constraint coverage audits.
- Teach v4 authoring to extract high-salience source constraints from rich task notes and referenced rulebooks before writing bundle files.
- Preserve policy-bearing schema verbs when they carry operational meaning.
- Require planners to fill known fields, write an explicit unresolved marker when a required value is unknown, and avoid vague prose in required slots.
- Update packaged catalog and docs so v4 is installable and discoverable.

**Non-Goals:**

- Do not remove or replace `houmao-agent-loop-pairwise-v3`.
- Do not introduce a new runtime engine, daemon, plan executor, or parser for v4 plans.
- Do not require machine parsing of every generated Markdown field at runtime.
- Do not change the pairwise-v2 runtime recovery record location.
- Do not make generic pairwise requests auto-route to v4; v4 remains explicit/manual.

## Decisions

### Decision: Create v4 as a sibling skill

V4 will live under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v4/` and use `houmao-agent-loop-pairwise-v4` as its catalog key and skill name.

Rationale: v3 remains useful and already has a stable workspace-aware contract. The stricter template-first posture is a behavioral upgrade that may be too rigid for some existing v3 uses, so a versioned sibling is clearer than silently changing v3.

Alternative considered: modify v3 in place. Rejected because existing v3 users may expect flexible bundle generation.

### Decision: Keep v3 lifecycle semantics, change authoring discipline

V4 keeps the same operator verbs and observed states as the updated v3 skill: `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and `hard-kill`; observed states `authoring`, `initializing`, `ready`, `running`, `paused`, `recovering`, `recovered_ready`, `stopping`, `stopped`, and `dead`.

Rationale: issue 47 is about generated plan organization and semantic preservation, not a new lifecycle model.

Alternative considered: make v4 a new runtime abstraction. Rejected because the existing pairwise-v3 runtime posture is enough.

### Decision: Add bundled document templates, not only prose guidance

V4 will include a `document-templates/` or equivalent template reference surface inside the skill. The authoring pages will instruct planners to generate documents with exact section headers, section order, and required fields.

Required template families:

- canonical `plan.md` with a central source-contract summary and carried-forward constraints table,
- role-local `agents/<participant>.md` templates for lead, reviewer, coder/worker, and generic participant roles,
- `templates/bookkeeping/*.md` patterns for state schemas such as open-end ledgers, reviewer-request packets, and round ledgers,
- `templates/reporting/*.md` patterns for operator-facing status and evidence summaries,
- a `constraint-coverage-audit.md` template that maps each extracted source rule to central and runtime projections.

Rationale: strict templates reduce drift and make omissions visible. Prose instructions alone caused the v4/v5 example gap.

Alternative considered: keep templates only inside `templates/bundle-plan.md`. Rejected because the strict section contracts are large enough to deserve separate, reusable references.

### Decision: Require extract, project, audit

V4 authoring will follow three semantic passes:

1. Extract source constraints from the user task and explicitly referenced rulebooks.
2. Project each constraint to central plan, role-local agent notes, routing/reporting/bookkeeping templates, or mark it unresolved.
3. Audit coverage before finalizing the bundle.

Rationale: a central "source constraints carried forward" ledger makes review possible without diffing every support file.

Alternative considered: rely on the planner's final self-review. Rejected because a generic self-review does not force one-to-one traceability.

### Decision: Preserve schema-like verbs only when policy-bearing

V4 will preserve source verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH` when those verbs encode operational policy. It will not preserve decorative emphasis that does not define a rule.

Rationale: this keeps the generated contract readable while preserving the action semantics that matter to agents.

Alternative considered: preserve every emphasized word verbatim. Rejected because it can overfit formatting and clutter the generated plan.

## Risks / Trade-offs

- [Risk] V4 templates may become verbose for small loops. → Mitigation: keep v4 manual-invocation-only and recommend v3 for ordinary workspace-aware plans that do not need strict source-contract preservation.
- [Risk] A planner may over-preserve low-value emphasized prose. → Mitigation: define "policy-bearing" and require a coverage audit that distinguishes included rules from unresolved or intentionally non-policy text.
- [Risk] Strict templates can feel rigid across domains. → Mitigation: require stable section headers and slots, but allow task-shaped entries within those slots.
- [Risk] Catalog and docs can drift from the new skill inventory. → Mitigation: update catalog-driven tests and documentation assertions alongside the skill.
- [Risk] Generated files might imply machine-enforced runtime validation. → Mitigation: document v4 as an authoring and operator-audit contract, not a new runtime parser or executor.
