# Clarify Execplan

## Read First

- `../reference/clarification-protocol.md`
- `../reference/generation-pipeline.md`
- `../reference/generated-contract-defaults.md`
- `../reference/topology-modes.md`
- `../reference/cycle-normalization.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- `../reference/result-routing.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- User asks for `clarify-execplan`.
- `<loop-dir>/execplan/` exists.
- Goal:
  - clarify generated implementation choices;
  - record accepted execplan decisions as execplan ADRs;
  - update or flag affected generated execplan artifacts.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated process overview at `<loop-dir>/execplan/specs/collab/collab-overview.md`

Read before asking, when present:
- `<loop-dir>/execplan/specs/**`
- `<loop-dir>/execplan/harness/**`
- `<loop-dir>/execplan/skills/**`
- `<loop-dir>/execplan/agents/**`
- `<loop-dir>/execplan/docs/**`
- `<loop-dir>/execplan/adrs/*.md`
- relevant intention files only to check whether an implementation choice is justified by source intent

Missing input rule:
- If `execplan/` or required process specs are missing, ask with `Required` values for the missing generated artifacts and `Optional` choices such as running `execplan-fast-forward`, running `execplan-step-by-step`, running the missing staged generation command, or `none for this step`.

## Coverage Scan

Build an internal coverage map before asking. Use these execplan implementation categories:

- intent boundary: whether the gap belongs to `clarify-intent` rather than generated implementation;
- objective-derived parameters: thresholds, assumptions, hidden variables, constraints, evidence requirements, stop conditions, and generated values that can change objective meaning;
- topology mode, cycle posture, tree-loop normalization, route graph shape, terminal ownership, and result-routing posture;
- process phases, events, handoffs, ticks, terminal posture, repeat-visit rules, and recovery posture;
- mail schemas, schema-id event types, renderers, metadata headers, reply links, acknowledgement, result, error, and freeform families;
- predecessor context selected for generic routes, including explicit no-context-needed omissions;
- communication completeness: whether each handoff carries enough paths, refs, branch or commit ids, artifact ids, context, requested action, and reply expectations for the receiver to act without implicit workspace inspection;
- mail payload lifecycle, message refs, thread refs, and state effects;
- state schema, transitions, invariants, ownership, backend choice, and repair posture;
- harness commands for initialization, query, validation, record apply, rendering, and explain output;
- generated skill triggers, bounded procedures, stop points, archive-after-success behavior, and tick placement;
- agent bindings, notifier prompts, Houmao system-skill preinstall posture, workspace policy, and memo posture;
- workspace definition: workspace roots, shared vs per-agent paths, artifact-sharing protocol, and how in-loop work artifacts are referenced across agents;
- run artifacts, evidence refs, logs, validation coverage, generated docs, and manifest coherence;
- platform boundary compliance;
- no in-chat waiting, sleeping, polling, or periodic background tick assumptions.

Question priority:

1. Redirect missing or contradictory source intent to `clarify-intent`; do not patch around it in generated artifacts.
2. Resolve objective-derived parameter ambiguity: generated thresholds, assumptions, hidden variables, constraints, evidence requirements, stop conditions, or config values that can change objective meaning.
3. Resolve topology authority: selected mode, tree-loop normalization, generic-loop cycle bounds, dedupe keys, repeat-visit rules, and result-routing policy must be explicit.
4. Resolve process authority consistency: phases, ownership, event/tick advancement, terminal posture, and recovery posture must derive from `specs/collab/collab-overview.md`.
5. Resolve communication completeness and correctness: generated mail must include enough context, artifact refs, paths, git branch or commit ids, requested action, and reply or forward expectations for downstream agents to act.
6. Resolve task-specific predecessor context: generic routes must carry selected upstream refs or summaries when needed, and explicit omissions must be justified.
7. Resolve schema-typed mail dispatch: each ordinary templated mail family needs a `schema_id`, schema, renderer, registry entry, in-body metadata header, and matching event-skill trigger.
8. Resolve state, record, and harness authority: ownership, transitions, invariants, payload lifecycle, topology validation, operator intent events, validation, query, and apply surfaces.
9. Resolve workspace definition and artifact sharing: where workspaces live, what is shared, what is per-agent, and how in-loop artifacts are communicated through mail, paths, branches, commits, or manifests.
10. Resolve lifecycle, mode, and operator-control behavior: start, pause, resume, stop, recover, default `auto`, `manual`, notifier posture, and no in-chat waiting.
11. Resolve generated skills and agent bindings: schema-id triggers, bounded actions, stop points, generated skill installation, notifier prompts, and role ownership.
12. Resolve run artifacts, generated docs, manifest, and validation packaging after runtime semantics are coherent.

Prioritize questions whose answers affect runtime correctness, generated contract shape, scheduling, recovery, state validity, mail behavior, workspace/artifact handoff, validation, or operator acceptance.

## Question Focus

Ask only about generated implementation choices that are:

- unclear;
- unjustified by intention source, accepted ADRs, or reference defaults;
- contradictory across generated artifacts;
- likely to affect runtime correctness or recovery;
- likely to make validation or operator use ambiguous.

Good execplan questions confirm implementation details, for example:

- Which generated objective parameter decides whether a result is accepted?
- Does the generated topology contract correctly select `tree-loop` or `generic-loop`?
- If a tree-loop cycle was normalized, which existing participant is recorded as the relay or cycle breaker?
- What dedupe key and termination condition bound this generic-loop cycle?
- What branch, commit, path, or artifact ref must a work-complete mail include?
- Which selected predecessor refs or summaries must this generic handoff carry?
- Which `schema_id` should trigger this role's generated on-event skill?
- Should a missing result reply be handled by timeout tick, operator recovery, or no automatic action?
- Which shared workspace path may downstream agents read for in-loop artifacts?
- Which generated skill owns archiving a processed mail item?
- Is sqlite state the accepted authority for active ownership and completion?
- Should the notifier prompt always run a tick after one mail is processed?

If the answer would change intended loop behavior rather than generated implementation, report that it belongs in `clarify-intent` or direct intention edits.

## Actions

1. Read generated execplan artifacts and prior execplan ADRs.
2. Apply `clarification-protocol.md` to build an internal coverage map and question queue.
3. Ask at most five accepted questions per session, exactly one at a time.
4. Include a recommended or suggested answer when context supports one.
5. If the answer is discoverable from current execplan artifacts, accepted ADRs, intention source, or defaults, use that source instead of asking.
6. After each accepted answer:
  - create the next ADR under `<loop-dir>/execplan/adrs/`;
  - update the affected generated specs, harness material, generated skills, agent bindings, docs, manifest, or validation notes;
  - apply `generation-pipeline.md` to identify downstream artifacts that must be updated now or explicitly marked stale;
  - remove contradictory generated text;
  - report if intention source is missing or contradictory and should be clarified separately.
7. Stop when critical ambiguities are resolved, the user pauses, or five accepted questions have been recorded.
8. Finish with the coverage summary required by `clarification-protocol.md`.

## ADR Shape

Use sequential numeric filenames:

```text
<loop-dir>/execplan/adrs/0001-short-decision-slug.md
<loop-dir>/execplan/adrs/0002-short-decision-slug.md
```

Use this Markdown structure:

```markdown
# Execplan ADR 0001: Short Decision Title

## Status

Accepted

## Context

Which generated artifacts were ambiguous and why the decision affects runtime behavior.

## Question

The clarification question that was asked.

## Decision

The accepted answer.

## Consequences

- Which generated artifacts were updated.
- Which downstream artifacts are now current or stale.
- Any intention-source gap that still needs `clarify-intent`.
```

## Constraints

- Do not silently invent missing user intent inside generated artifacts.
- Do not rewrite `intention/` from this operation.
- Do not ask local wording or formatting questions while process, mail, state, harness, skill, binding, recovery, or validation logic remains ambiguous.
- Do not live-migrate active runs or running agents from this operation.
- Do not treat generated docs as authority over specs, harness registries, generated skills, agent bindings, or manifest entries.
