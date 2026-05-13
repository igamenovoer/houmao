## Context

Houmao currently has two relevant loop-skill lines. The older `houmao-agent-loop-generic` skill defines useful graph vocabulary: typed pairwise and relay components, graph policy, result routing, and explicit component dependencies. It still assumes a designated master or root run owner. The newer `houmao-agent-loop-pairwise-v5` skill has the stronger generated-execplan workflow: editable `intention/`, generated `execplan/`, staged generation, scaffold templates, loop-local harnesses, generated skills, generated agent bindings, execution-stage separation, and mail-notifier-driven runtime guidance.

The new `houmao-agent-loop-pro` skill should combine those strengths without mutating either source skill. It should use v5 as the structural baseline, rename the new copy so it is not pairwise-v5 branded, and add topology-mode contracts that can express both tree-shaped pairwise execution and true generic directed loops.

The important semantic gap is predecessor-context handling. Pairwise local-close trees can rely on each downstream worker replying to its immediate upstream, but a generic directed loop such as `A -> B -> C -> A` can otherwise strand useful distant-upstream context. In generic mode, execplan generation must consider what each downstream participant needs from predecessors, then select task-specific context refs, summaries, artifact pointers, or an explicit "no carried upstream context needed" posture for each relevant route.

A mature loop-plan example also shows a reusable mail classification pattern: every templated participant mail family has a JSON Schema id, outgoing TOML payloads validate against that schema before rendering, rendered Markdown starts with a fenced in-body metadata block, and generated `on-<event>` skills trigger on the detected `schema_id`. The schema id becomes the loop-local mail type, while the rendered body remains readable for agents.

## Goals / Non-Goals

**Goals:**

- Add a new `houmao-agent-loop-pro` packaged system skill derived from the current pairwise-v5 implementation shape.
- Preserve v5’s generated-execplan pipeline, scaffold generator, subskill routing, mail-driven runtime model, operator-control defaults, workspace preparation flow, and validation posture.
- Define two topology modes: `pairwise-tree` and `generic-graph`.
- Make pairwise-tree mode enforce local-close tree/forest execution, with explicit normalization for non-tree intent.
- Make generic-graph mode allow cycles and non-tree directed communication when predecessor-context choices, termination, dedupe, and state contracts are explicit enough for the task.
- Make schema ids the default classifier for generated templated mail events, with an in-body metadata header visible in rendered mail.
- Generate topology, result-routing, predecessor-context consideration, harness, state, and validation guidance into the new skill.
- Avoid requiring a master, lead, coordinator, or root owner unless the loop intent or accepted clarification decisions choose one.

**Non-Goals:**

- Do not modify `houmao-agent-loop-pairwise-v5`, `houmao-agent-loop-generic`, or older pairwise skill behavior.
- Do not add a new Houmao runtime loop engine.
- Do not change core Houmao mail, gateway, mailbox, managed-agent launch, or workspace-manager APIs.
- Do not create new agents during pairwise-cycle normalization; choose an existing participant as the relay or cycle breaker.
- Do not make generated docs the authority over generated specs, harness registries, generated skills, agent bindings, or manifest entries.

## Decisions

### Decision: Create `houmao-agent-loop-pro` as a copied skill, not an in-place rename

Create a new system-skill package under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/` by copying the current pairwise-v5 skill as the baseline. Rename frontmatter, `agents/openai.yaml`, title text, references, and wording inside the new copy. Leave v5 intact so existing workflows and current project-scope symlinks remain stable.

Alternative considered: rename v5 in place. That is too disruptive because v5 is already installed and referenced by active workflows.

### Decision: Keep v5’s staged execplan pipeline as the pro authoring spine

The pro skill should keep the same high-level route shape: `init`, `clarify-intent`, `clarify-execplan`, `execplan-fast-forward`, `execplan-step-by-step`, `execplan-specs-process`, `execplan-specs-contract`, `execplan-harness`, `execplan-skills`, `execplan-agent-bindings`, `execplan-finalize`, `validate-execplan`, `update-execplan`, and execution stages. This preserves the already-refined split between intention source, generated process authority, derived contracts, harness, generated skills, concrete agent bindings, and runtime execution stages.

Alternative considered: port old generic-loop plan files directly. Those files are useful vocabulary sources but are less aligned with the current generated-package workflow.

### Decision: Add topology modes as generated contracts

The skill should introduce a required topology-mode decision during intent clarification or process generation:

- `pairwise-tree`: execution is a rooted tree or forest of local-close upstream/downstream handoffs. A downstream participant replies to its immediate upstream; results do not bypass immediate upstream.
- `generic-graph`: execution is a directed graph whose edges may form cycles or non-tree routes. Receivers may need context from distant predecessors, so execplan generation must decide per route or message family what predecessor information, if any, should be carried, summarized, referenced, or intentionally omitted.

The selected mode belongs in generated process and topology contracts, not just prose. The normal generated location should be `execplan/specs/collab/topology/`.

Alternative considered: reuse generic skill `pairwise`/`relay` component vocabulary directly as the only mode model. That is useful but not enough because pro needs a higher-level validation distinction between local-close trees and arbitrary directed loops.

### Decision: Normalize pairwise cycles by choosing an existing relay/cycle-breaker participant

When user intent asks for pairwise behavior but describes a non-tree cycle, the pro skill should not silently generate cyclic pairwise execution. It should either clarify mode or normalize the pairwise shape into local-close tree execution. Normalization must choose an existing participant as the relay or cycle breaker and record the decision in generated topology/process artifacts or ADRs. It must not invent a synthetic participant.

Example:

```text
Intent: A -> B -> C -> A
Pairwise-tree execution: A -> B -> C, then C replies upstream to B, then B replies upstream to A
```

Alternative considered: reject all cyclic pairwise input. That is safe but too rigid; many users describe cycles loosely when they actually want a local-close chain with upstream aggregation.

### Decision: Treat predecessor-context propagation as a task-specific generic-mode design choice

Generic graph handoff schemas should support carrying selected predecessor context, but the generated execplan decides what is needed. Depending on the task, a route may carry predecessor mail refs, ancestor mail refs, artifact refs, commit refs, context summaries, required context keys, edge identity, work item identity, lineage, expected next action, or no upstream context beyond the current message. The important requirement is that generation considers this explicitly and records the selected posture.

When the execplan selects carried context, rendered mail should show it in readable Markdown while preserving machine-readable structure. The harness should expose commands to build, validate, explain, and query context bundles only when the generated contracts need those surfaces. State should store compact refs and lineage when needed, not full mail bodies or rich rationale.

Alternative considered: require every generic handoff to carry a fixed context bundle. That is too rigid because some tasks need only the current instruction or current result, while others need deep predecessor lineage. Another rejected alternative is requiring downstream agents to inspect upstream files or mailboxes without guidance; that is brittle when predecessor context is task-critical.

### Decision: Use schema ids as generated mail event types

Generated pro communication contracts should model each templated participant mail family as a schema-typed event. The normal package shape should include:

```text
execplan/specs/comms/
  templates.toml
  schemas/<message-family>.schema.json
  renderers/<message-family>.md.j2
```

`templates.toml` should map each template name to a `schema_id`, JSON Schema path, and Markdown renderer. Payload authoring should flow through TOML payload -> JSON Schema validation -> Markdown rendering -> Houmao mail delivery. Generated schemas should include a constant `schema_id`, `schema_version`, `kind`, `run_id`, `plan_revision`, and route or exchange identifiers when those concepts apply.

Rendered Markdown should start with a fenced in-body metadata block, normally:

````text
```houmao-email-metadata
schema_id = "<loop-slug>.email.<message-family>"
schema_version = "1"
kind = "request"
run_id = "..."
plan_revision = "..."
payload_id = "..."
handoff_id = "..."
```
````

Generated on-event skills should state their trigger as a schema id, for example "Use this skill when mail arrives with schema id `<loop-slug>.email.<message-family>`." This makes schema id the dispatchable mail type. Receiver-side event skills may assume sender-side form validation for ordinary templated mail, inspect the rendered metadata and body semantically, and use harness/state schemas for the role-owned action. Repair or operator-origin paths can still handle malformed or freeform mail explicitly.

Alternative considered: classify mail only by subject, sender, or freeform body text. That is too fragile for generated event skills and makes notifier prompts less precise. Transport-level headers are also not enough because Houmao agents read the mail body; the type marker must be visible in the rendered body.

### Decision: Separate lifecycle control from topology ownership

The pro skill should retain loop-local operator control defaults, but it should not require every generated loop to have a master. A generated loop may have a start node, acceptance authority, scheduler/tick owner, relay participant, root run owner, or no central owner depending on intention source and clarification decisions. If such an authority exists, generated contracts must name it explicitly.

Alternative considered: inherit generic skill’s root-owner requirement. That would keep old semantics but would prevent pro from representing truly decentralized or cyclic collaboration models.

## Risks / Trade-offs

- **Risk: Pro becomes too broad and confusing** → Mitigation: make topology mode a first-class early decision, keep mode-specific rules in separate reference pages, and keep the entrypoint short.
- **Risk: Generic-graph communication payloads become verbose** → Mitigation: make context carrying task-specific, prefer refs and compact summaries when needed, and allow explicit omission when downstream work does not need upstream context.
- **Risk: Event skill dispatch is ambiguous** → Mitigation: require templated mail renderers to expose a schema id in an in-body metadata block and have generated event skills name the triggering schema id.
- **Risk: Pairwise normalization hides user intent** → Mitigation: require an explicit recorded normalization decision and route ambiguous cases to `clarify-intent` or `clarify-execplan`.
- **Risk: Generated validation is underspecified** → Mitigation: add concrete validation rules for cycles, task-selected context fields, lineage when selected, termination, dedupe keys, reply expectations, and mode-specific omissions.
- **Risk: Skill-copy drift from v5** → Mitigation: copy once for the new skill, then make the pro skill self-contained; do not require future v5 and pro pages to stay text-identical.

## Migration Plan

1. Add the new `houmao-agent-loop-pro` system skill as a separate package.
2. Add project-scope symlinks only if the existing project-scope skill exposure pattern requires them for new system skills.
3. Leave existing loop skills and current installed behavior unchanged.
4. Validate the new skill by checking its metadata, routed page links, scaffold scripts/templates, generated reference paths, and OpenSpec requirements.
5. Roll back by removing only the new `houmao-agent-loop-pro` package and any project-scope symlinks created for it.
