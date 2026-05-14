# Loop Authoring Guide

Houmao has two current loop authoring entrypoints: `houmao-agent-loop-lite` and `houmao-agent-loop-pro`. Both scaffold a loop directory, clarify intent, generate an execplan, prepare agents, validate readiness, launch agents, and operate the generated loop. Choose lite for Markdown/direct-SQL loops with required generated skills and no generated harness. Choose pro for schema-rich topology work, graph validation, harness-backed contracts, and heavier generated run-control surfaces.

For mailbox-driven loops, first understand the runtime model: agents are normally woken by gateway notifier prompts, process bounded mail event work, optionally run one prompt-invoked tick, then finish the chat turn. They should not wait in-chat for future mail or periodic ticks. See [Notifier-Prompt-Driven Loop Runtime](../reference/gateway/operations/notifier-prompt-driven-loops.md).

## Current Skills

| Skill | What it owns | Main operations |
|---|---|---|
| `houmao-agent-loop-lite` | Lightweight generated loop definitions with Markdown contracts, typed Markdown templates, direct SQLite state, and generated skills | `init`, `clarify`, `generate-skills`, `validate`, `prepare-agents`, `launch-agents`, `start`, `status`, `pause`, `resume`, `recover`, `stop` |
| `houmao-agent-loop-pro` | Schema-rich generated loop definitions for `tree-loop` and `generic-loop` topologies | `init`, `clarify-intent`, `clarify-execplan`, `execplan-fast-forward`, staged `execplan-*` generation, `prepare-agents`, `prepare-workspace`, `validate-loop`, `launch-agents`, `start`, `status`, `pause`, `resume`, `recover`, `stop` |

Do not choose among retired loop packages for new work. Choose lite explicitly for Markdown/direct-SQL/no-harness loops, or choose the topology mode inside the pro-generated execplan.

## Topology Choice

Choose `tree-loop` when:

- each downstream node should return useful results to its immediate upstream;
- the graph is a tree after any non-tree cycle is handled through an explicit relay choice;
- the task benefits from local-close handoffs and simple upstream integration.

Choose `generic-loop` when:

- the communication graph may contain cycles, relay lanes, or multiple predecessor paths;
- a downstream agent may need selected context from non-immediate predecessors;
- predecessor-context forwarding is a task-specific design choice rather than a universal payload rule.

The pro skill accepts legacy topology wording such as "pairwise" as compatibility language when reading older material, but newly generated material should use `tree-loop` or `generic-loop`.

## Lite Default Shape

Lite keeps the pro-like root spine while removing unused generated layers:

```text
<loop-dir>/
  intention/
  execplan/
    specs/
      templates/
      state/
    skills/
    agents/
  runs/
```

The default lite package uses `execplan/manifest.md`, Markdown specs for objective, organization, process, communication, and agent bindings, required communication templates under `execplan/specs/templates/`, `execplan/specs/state/schema.sql`, and `execplan/specs/state/README.md`. Templates start with a body-local `Loop-Template-Type` and `Loop-Template-Version` prologue, then use literal `<placeholder ...>` tokens. Generated skills are required: one shared guide plus receiver skills for each required template type. Agents manipulate `runs/<run-id>/state.sqlite3` directly according to the state README.

Lite does not generate `execplan/harness/` or `execplan/docs/` by default. Optional material such as workspace rules, seed SQL, query recipes, notifier prompts, concrete profile definitions, tick skills, and operator-control skills appears only when the selected loop process needs it.

## Pro Authoring Flow

1. Run `init` to create the loop directory, intention files, project-context notes, and scaffold placeholders.
2. Fill or revise the intention source files under `<loop-dir>/intention/`.
3. Run `clarify-intent` to resolve objective, communication, loop-process, and other high-impact ambiguity. Accepted decisions are recorded under `<loop-dir>/adrs/`.
4. Generate execplan artifacts with `execplan-fast-forward` for one-pass generation, or `execplan-step-by-step` when the user wants one decision at a time.
5. Use staged generation when needed:
   - `execplan-specs-process`: process-first pseudo-code and sequence model.
   - `execplan-specs-contract`: objective, participant, topology, communication, state, workspace, and run contracts.
   - `execplan-harness`: loop-local harness scripts and state/query surfaces.
   - `execplan-skills`: generated shared, on-event, on-tick, and operator skills.
   - `execplan-agent-bindings`: concrete Houmao agent bindings.
   - `execplan-finalize`: support docs, manifest, README files, metadata, and consistency notes.
6. Run `clarify-execplan` when generated artifacts leave implementation-level design choices unclear.
7. Run `validate-execplan` before preparing runtime assets.

## Pro Execution Flow

1. `prepare-agents`: create or update Houmao specialists/profiles and generated skill bindings.
2. `prepare-workspace`: prepare or verify the multi-agent workspace when the execplan requires one.
3. `validate-loop`: check pre-launch readiness and required evidence.
4. `launch-agents`: launch prepared agents without starting loop work.
5. `start`: send the first loop trigger.
6. `status`, `pause`, `resume`, `recover`, and `stop`: operate the generated loop through the loop-specific operator control surface.

`prepare-agents` and `prepare-workspace` are separate stages. Workspace preparation may depend on prepared agent names and profile facts, but neither stage should call the other implicitly.

## Pro Generated Artifacts

The generated execplan should make the runtime contract inspectable:

- process docs with Python-style pseudo-code, inline comments, and a high-level Mermaid sequence diagram;
- schema-typed mail families with human-readable templates and in-body metadata headers;
- harness surfaces for objective/config queries, state bookkeeping, TOML validation/rendering, mail creation, and loop mode;
- state schemas for durable bookkeeping, defaulting to SQLite when the schema is clear and falling back to JSONL plus schema when that is simpler;
- generated skills in one flat skills directory so installed skill names stay unique;
- agent bindings, workspace contracts, operator-control commands, and README files for generated artifact directories.

Generated TOML files should include comments above each section and a `description` field where the harness can expose `--explain` output.

## Graph Helpers

`houmao-mgr internals graph high` remains available when a generated execplan has graph artifacts that benefit from deterministic analysis:

```bash
houmao-mgr --print-json internals graph high analyze --input graph.json
houmao-mgr --print-json internals graph high render-mermaid --input graph.json
houmao-mgr --print-json internals graph high packet-expectations --input graph.json
houmao-mgr --print-json internals graph high validate-packets --graph graph.json --packets packets.json
```

Use these helpers as deterministic validation or rendering tools for pro-generated artifacts. They are helper commands, not separate loop skills.
