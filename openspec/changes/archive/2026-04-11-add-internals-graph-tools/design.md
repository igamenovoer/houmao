## Context

The loop-planning assets now ask user-controlled agents to reason about directed communication graphs. `houmao-agent-loop-generic` decomposes composed runs into typed pairwise and relay components, dependencies, result-return paths, and rendered Mermaid graphs. `houmao-agent-loop-pairwise-v2` now depends on authoring-time descendant analysis so non-leaf participants receive precomputed child routing packets and runtime handoffs can fail closed instead of recomputing descendant slices from memory.

NetworkX is already a project dependency, and NetworkX 3.6.1 exposes node-link JSON helpers through `networkx.readwrite.json_graph.node_link_data()` and `node_link_graph()`. That gives Houmao a native graph interchange format without inventing a separate YAML or Markdown graph schema.

The new CLI should be internal and agent-oriented. It should help agents calculate graph facts and validate authored artifacts, but it should not become a new planner or a runtime loop engine.

## Goals / Non-Goals

**Goals:**

- Add a `houmao-mgr internals graph` command family with two layers:
  - `graph high ...` for Houmao-aware loop-graph and routing-packet helpers.
  - `graph low ...` for constrained NetworkX-backed graph construction, transformation, and algorithms.
- Use NetworkX node-link JSON as the only graph interchange format for this tooling.
- Normalize graph operations internally to `nx.MultiDiGraph` so parallel logical edges can carry distinct `id`, `kind`, and `component_id` attributes.
- Support pairwise-v2 authoring-time packet expectation and validation workflows.
- Support generic-loop authoring diagnostics and deterministic Mermaid graph scaffolding while preserving skill-owned semantic review.
- Emit structured payloads through the existing `houmao-mgr` print-style output path.

**Non-Goals:**

- Do not add a new runtime loop engine, queue, transport, mailbox protocol, or gateway API.
- Do not infer user authorization for free delegation or free forwarding.
- Do not repair missing, mismatched, or stale routing packets from graph memory.
- Do not support a separate Houmao YAML graph format.
- Do not expose arbitrary NetworkX function execution or Python expression evaluation.

## Decisions

### 1. Use NetworkX node-link JSON as the only graph format

The graph CLI will read and write node-link JSON using `nodes` and `edges` keys. Houmao metadata such as `schema_version`, `mode`, `root`, `plan_id`, `plan_revision`, or `plan_digest` will live under the node-link `graph` object. Agent, component, and packet linkage will live on node and edge attributes.

Example:

```json
{
  "directed": true,
  "multigraph": true,
  "graph": {
    "schema_version": 1,
    "mode": "pairwise-v2",
    "root": "master",
    "plan_id": "plan-123",
    "plan_revision": "rev-1"
  },
  "nodes": [
    { "id": "master", "kind": "agent" },
    { "id": "agent-a", "kind": "agent" }
  ],
  "edges": [
    {
      "source": "master",
      "target": "agent-a",
      "key": "e1",
      "id": "e1",
      "kind": "pairwise",
      "component_id": "c1"
    }
  ]
}
```

Rationale: node-link JSON is native to NetworkX, easy for agents to produce, easy to validate, and good enough for directed multigraphs with attributes.

Alternative considered: keep a Houmao YAML wrapper. That was rejected because users will not touch these files directly and a second graph format would add parsing and documentation cost without improving the agent workflow.

### 2. Split `graph high` from `graph low`

`graph high` will expose semantic operations for Houmao loop authoring:

- `analyze`: summarize roots, leaves, non-leaf participants, reachability, cycles, branches, component dependencies, and warnings.
- `packet-expectations`: compute pairwise-v2 root packet and child packet expectations from the authored topology.
- `validate-packets`: compare a packet JSON document against graph-derived expectations and return explicit errors for missing, stale, or mismatched packets.
- `slice`: produce authoring-time ancestor, descendant, reachable, or component slices.
- `render-mermaid`: produce deterministic Mermaid scaffolding from the graph while leaving final semantic review to the loop skill.

`graph low` will expose constrained NetworkX-style primitives:

- graph construction and edit operations, such as empty graph creation and batched `add_node`, `add_edge`, `remove_node`, `remove_edge`, and graph-attribute updates.
- graph transforms such as relabel, compose, subgraph, reverse, ego graph, condensation, and transitive reduction.
- algorithm wrappers such as ancestors, descendants, descendants-at-distance, topological sort, DAG check, bounded cycle enumeration, weak components, strong components, DAG longest path, shortest path, and all simple paths with cutoff.

Rationale: the high layer protects Houmao semantics, while the low layer gives agents a general graph calculator without forcing every future graph use case into loop-planning vocabulary.

Alternative considered: one flat `graph` namespace. That would be shorter, but it would blur the line between semantic Houmao checks and raw graph operations.

### 3. Keep high-level graph commands structural and fail-closed

High-level commands will report what the graph structurally implies. They will not decide that a missing policy means `delegate_any`, will not widen named delegation sets, and will not patch stale child packets. `validate-packets` will produce errors like `missing_child_packet`, `recipient_mismatch`, `driver_mismatch`, `stale_packet`, and `missing_child_dispatch_table`.

Rationale: this matches the loop-skill guardrails: silence is not authorization, runtime intermediates should not recompute descendant plan slices, and packet mismatch should stop downstream dispatch.

Alternative considered: auto-repair routing packets from graph topology. That would make the command convenient, but it would undermine pairwise-v2 fail-closed behavior and create a hidden planner.

### 4. Use a small typed helper layer around NetworkX

Implementation should add a pure helper package under `src/houmao/agents/loop_graph/` with Pydantic models for structured command payloads and validation results. CLI functions should remain thin Click adapters in `src/houmao/srv_ctrl/commands/internals.py`.

Suggested modules:

- `models.py`: node-link graph metadata, packet expectation, validation error, and analysis payload models.
- `io.py`: read stdin/file JSON, call NetworkX node-link conversion, normalize to `nx.MultiDiGraph`, and emit node-link JSON.
- `analysis.py`: low-level algorithm wrappers and high-level structural analysis.
- `packets.py`: pairwise-v2 packet expectation and validation.
- `mermaid.py`: deterministic Mermaid scaffolding.

Rationale: this keeps the CLI testable and lets graph logic receive focused unit coverage without Click runner overhead.

Alternative considered: implement everything in the Click command module. That would be faster initially but would make the high/low split harder to test and extend.

### 5. Use JSON packet documents for packet validation

`graph high validate-packets` will accept a packet JSON document rather than Markdown packet text. The packet document should contain root packet metadata, child packet metadata, and exact packet text or exact packet references where needed. The high-level tool validates structure, identity, and freshness markers; it does not parse arbitrary plan prose.

Rationale: packet validation needs deterministic identity checks. Markdown packet validation can be added later if authored packet files converge on a stable machine-readable frontmatter contract.

Alternative considered: parse routing packets from Markdown sections. That is brittle and would push the first implementation toward string heuristics.

## Risks / Trade-offs

- **Internal CLI grows too broad**: `graph low` could become an unbounded NetworkX clone. Mitigation: expose only whitelisted construction, transform, and algorithm wrappers needed by agents; do not add arbitrary function dispatch.
- **Packet schema drift**: pairwise-v2 packet JSON could diverge from the authored Markdown packet shape. Mitigation: keep the JSON packet contract minimal and identity-oriented, and update v2 templates to point at the machine-readable fields when packet validation is used.
- **Mermaid output becomes over-trusted**: deterministic Mermaid scaffolding may still omit semantics the skill must show. Mitigation: document `render-mermaid` as a starter graph and keep the loop skill responsible for final plan review.
- **Parallel edges complicate algorithms**: some algorithms operate on directed graphs and may ignore multiedge keys. Mitigation: normalize to `MultiDiGraph` for storage, and collapse to a `DiGraph` only for algorithms that require it while preserving edge summaries in output warnings.
- **Large graphs can create large payloads**: simple path and cycle enumeration can explode. Mitigation: require cutoffs or bounds for expensive commands and default to conservative limits.

## Migration Plan

1. Add the `internals` Click group and register it in the `houmao-mgr` root command tree.
2. Add the graph helper modules and implement node-link JSON input/output.
3. Implement `graph low` construction, transform, and algorithm wrappers with structured JSON output.
4. Implement `graph high` analysis, packet expectations, packet validation, slicing, and Mermaid scaffolding.
5. Update pairwise-v2 and generic loop skill assets to mention the new high-level graph tools where they reduce authoring-time graph reasoning.
6. Add unit tests for helper behavior, CLI shape tests for `internals graph high|low`, and targeted system-skill content tests.

Rollback is straightforward because the new command family is additive: remove `internals` registration and helper modules if the surface proves unsuitable before release.

## Open Questions

None.
