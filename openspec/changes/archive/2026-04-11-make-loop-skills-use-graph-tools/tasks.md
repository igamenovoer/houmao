## 1. Pairwise-V2 Graph-Tool Preflight Guidance

- [x] 1.1 Update the `houmao-agent-loop-pairwise-v2` top-level routing guidance so `houmao-mgr internals graph high` is the first-class structural helper when node-link graph and packet JSON artifacts exist.
- [x] 1.2 Update pairwise-v2 authoring and revision pages to describe the expected `analyze` -> optional `slice` -> `packet-expectations` sequence before packet authoring for default `precomputed_routing_packets` plans.
- [x] 1.3 Update pairwise-v2 prestart guidance so `validate-packets` is the explicit deterministic check before `ready` when graph and packet JSON artifacts exist, with manual visible-coverage fallback when they do not.
- [x] 1.4 Update pairwise-v2 plan structure, templates, and run-charter references to keep graph artifact, packet JSON, packet inventory, dispatch-table, and freshness-marker expectations easy to find.
- [x] 1.5 Ensure pairwise-v2 runtime handoff wording says intermediate agents use dispatch tables and exact child packets, not graph analysis or descendant-slice recomputation.

## 2. Generic Loop Graph-Tool Guidance

- [x] 2.1 Update the `houmao-agent-loop-generic` top-level routing guidance so routine structural graph checks route to `houmao-mgr internals graph high`, not `graph low`.
- [x] 2.2 Update generic authoring and revision pages to present `graph high analyze` and `graph high slice` as the first-class structural preflight when a node-link graph artifact exists.
- [x] 2.3 Update generic graph-rendering guidance so `graph high render-mermaid` is deterministic scaffolding that still requires final semantic review against typed component, result-routing, stop, and completion requirements.
- [x] 2.4 Update generic plan structure or templates if needed so graph artifact references and semantic-review boundaries are visible in finalized plans.

## 3. Tests And Validation

- [x] 3.1 Add or update targeted system-skill content checks for the pairwise-v2 graph-tool preflight sequence, validate-packets readiness gate, and no-runtime-graph-recomputation guardrail.
- [x] 3.2 Add or update targeted system-skill content checks for generic `graph high analyze|slice|render-mermaid` guidance and the absence of routine `graph low` guidance.
- [x] 3.3 Run `pixi run openspec validate make-loop-skills-use-graph-tools --strict`.
- [x] 3.4 Run targeted system-skill tests covering the updated packaged skill content.
