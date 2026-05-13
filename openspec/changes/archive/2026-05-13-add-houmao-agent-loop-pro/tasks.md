## 1. Skill Package Baseline

- [x] 1.1 Invoke or read the local `skill-creator` guidance before creating the new packaged skill.
- [x] 1.2 Copy `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/` to `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/`.
- [x] 1.3 Rename `SKILL.md` frontmatter, title, description, and routing text to use `houmao-agent-loop-pro`.
- [x] 1.4 Rename `agents/openai.yaml` metadata and shorten the prompt so it routes pro operations without v5 or pairwise-only wording.
- [x] 1.5 Remove user-facing mentions that the new skill is derived from v5 or from any CUDA/example-specific source.
- [x] 1.6 Add project-scope Codex, Claude, and Copilot symlinks for the new skill if the current repository pattern requires system skills to be exposed that way.

## 2. Topology Reference Model

- [x] 2.1 Add a pro reference page that defines `pairwise-tree` and `generic-graph` topology modes.
- [x] 2.2 Add a pro reference page that defines pairwise-tree cycle normalization using an existing participant as relay, root, or cycle breaker.
- [x] 2.3 Add a pro reference page that defines generic-graph predecessor-context considerations, including when to carry selected refs or summaries and when explicit omission is acceptable.
- [x] 2.4 Add a pro reference page or section for schema-typed templated mail, in-body metadata headers, template registry shape, validation/rendering flow, and schema-id event dispatch.
- [x] 2.5 Add a pro reference page or section for result routing across pairwise-tree and generic-graph modes.
- [x] 2.6 Update the pro entrypoint and routed `Read First` sections so topology, mail-schema, and predecessor-context references are read by relevant authoring, harness, generated-skill, and validation routes.

## 3. Authoring Subskills

- [x] 3.1 Revise `clarify-intent` to prioritize objective semantics, topology mode, agent communication, predecessor-context needs, loop process, termination, and validation.
- [x] 3.2 Revise `clarify-intent` to show high-level Mermaid architecture and loop-structure diagrams before the first clarification question when source material supports it.
- [x] 3.3 Revise `clarify-execplan` to ask about topology, task-specific predecessor-context choices, termination, dedupe, and pairwise normalization before low-impact generated-file details.
- [x] 3.4 Revise `execplan-specs-process` to record the selected topology mode, cycle posture, local-close or generic route semantics, and unresolved topology decisions.
- [x] 3.5 Revise `execplan-specs-contract` to generate topology contracts under `execplan/specs/collab/topology/` when topology material exists.
- [x] 3.6 Revise generated communication contract guidance so generic-graph handoff schemas include selected predecessor refs, required context keys, artifact refs, expected action, and reply or forward policy only when the execplan chooses those fields.
- [x] 3.7 Revise generated communication contract guidance so templated mail families get schema ids, JSON Schemas, Markdown renderers, and a template registry mapping template names to schema and renderer paths.
- [x] 3.8 Revise generated renderer guidance so templated mail bodies include a parseable in-body metadata header with `schema_id`, `schema_version`, `kind`, run id, plan revision, and route or exchange identifiers when applicable.

## 4. Harness And Generated Runtime Artifacts

- [x] 4.1 Revise `execplan-harness` guidance so generated harnesses can validate pairwise-tree topology and generic-graph selected-context payloads when those contracts exist.
- [x] 4.2 Revise state/bookkeeping guidance so generic-graph loops store compact lineage, visited-node or edge facts, cycle iterations, active ownership, and message refs.
- [x] 4.3 Revise `execplan-skills` guidance so generated on-event and on-tick skills read topology mode from generated specs, state, or harness output.
- [x] 4.4 Revise generated skill guidance so pairwise-tree participants reply to immediate upstream and generic-graph participants preserve selected carried context when forwarding.
- [x] 4.5 Revise generated skill guidance so on-event mail skills name their triggering `schema_id` and use detected schema id as the mail type.
- [x] 4.6 Revise `execplan-agent-bindings` guidance so notifier prompts can include schema-id dispatch, topology-mode, and predecessor-context instructions when generated skills need them.

## 5. Validation And Execution Guidance

- [x] 5.1 Revise `validate-execplan` to reject pairwise-tree direct cycles unless a recorded normalization converts them into local-close tree or forest execution.
- [x] 5.2 Revise `validate-execplan` to reject generic-graph cycles without explicit termination, dedupe, and repeat-visit contracts.
- [x] 5.3 Revise `validate-execplan` to check that generic rendered mail and schemas include selected carried-context fields and readable context sections when the generated execplan requires them, while accepting explicit no-context-needed omissions.
- [x] 5.4 Revise `validate-execplan` to check that templated mail schemas, renderers, template registry entries, in-body metadata headers, and event-skill schema-id triggers are coherent.
- [x] 5.5 Revise execution pages so `start`, `status`, `pause`, `resume`, `recover`, and `stop` do not assume a master participant unless the generated execplan names one.
- [x] 5.6 Preserve operator-control guidance as lifecycle control while keeping topology ownership and acceptance authority generated from intent.

## 6. Verification

- [x] 6.1 Run repository text checks to confirm `houmao-agent-loop-pro` does not contain stale skill-name references to pairwise-v5 except in developer-only migration notes, if any.
- [x] 6.2 Run repository text checks to confirm the pro skill does not require a master, lead, coordinator, or root owner by default.
- [x] 6.3 Run link/path checks for pro routed pages, reference pages, scaffold scripts, and template paths.
- [x] 6.4 Run `git diff --check`.
- [x] 6.5 Run OpenSpec status or validation for `add-houmao-agent-loop-pro` and confirm the change is apply-ready.
