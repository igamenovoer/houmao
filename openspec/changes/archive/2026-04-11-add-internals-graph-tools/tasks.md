## 1. Graph Helper Foundation

- [x] 1.1 Create the `houmao.agents.loop_graph` module package with typed models for node-link graph metadata, graph analysis results, packet expectations, packet validation errors, and algorithm outputs.
- [x] 1.2 Implement node-link JSON input/output helpers that load from file or stdin, call NetworkX node-link conversion with `nodes` and `edges` keys, normalize to `nx.MultiDiGraph`, and emit node-link JSON.
- [x] 1.3 Add validation for unsupported graph input shapes and ensure the graph tooling does not accept separate YAML or Markdown graph formats.

## 2. Low-Level Graph Tools

- [x] 2.1 Implement `graph low` construction or mutation support for empty graph creation and batched node, edge, removal, and graph-metadata operations.
- [x] 2.2 Implement `graph low` transform support for relabel, compose, subgraph, reverse, and ego graph operations.
- [x] 2.3 Implement `graph low alg` wrappers for ancestors, descendants, descendants-at-distance, topological sort, DAG check, bounded cycles, weak components, strong components, condensation, transitive reduction, DAG longest path, shortest path, and all simple paths with cutoff.
- [x] 2.4 Add bounds or conservative defaults for combinatorial low-level algorithms and include the effective bound in result payloads.

## 3. High-Level Houmao Graph Tools

- [x] 3.1 Implement `graph high analyze` for root reachability, disconnected nodes, leaves, non-leaf participants, immediate children, DAG or cycle posture, component summaries, branch points, and graph-shape warnings.
- [x] 3.2 Implement `graph high packet-expectations` for pairwise-v2 root packet expectations, one child packet expectation per pairwise edge, non-leaf dispatch-table expectations, and freshness-marker reporting.
- [x] 3.3 Implement `graph high validate-packets` against JSON packet documents with fail-closed errors for missing root packets, missing child packets, stale revisions or digests, intended-recipient mismatch, immediate-driver mismatch, missing dispatch tables, and missing exact child packet text or references.
- [x] 3.4 Implement `graph high slice` for ancestor, descendant, reachable, and component-slice extraction with node-link JSON output.
- [x] 3.5 Implement `graph high render-mermaid` as deterministic graph scaffolding for loop authoring without claiming to replace skill-owned semantic review.

## 4. CLI Integration

- [x] 4.1 Add `src/houmao/srv_ctrl/commands/internals.py` with `internals`, `graph`, `graph high`, and `graph low` Click groups.
- [x] 4.2 Register `internals_group` in the `houmao-mgr` root command tree.
- [x] 4.3 Route all structured graph command results through the shared `emit()` output engine so `--print-json`, `--print-plain`, and `--print-fancy` work consistently.
- [x] 4.4 Ensure graph commands return non-zero Click errors for invalid inputs and unsupported low-level operations without arbitrary Python or NetworkX dynamic dispatch.
- [x] 4.5 Add concrete examples to every individual `internals graph high`, `internals graph low`, and `internals graph low alg` command help text, including non-graph JSON input shapes where applicable.

## 5. Skill Asset Updates

- [x] 5.1 Update `houmao-agent-loop-pairwise-v2` authoring, prestart, and packet guidance to recommend `houmao-mgr internals graph high packet-expectations` and `validate-packets` when node-link graph and packet JSON inputs are available.
- [x] 5.2 Update `houmao-agent-loop-generic` authoring and graph-rendering guidance to mention `graph high analyze`, `slice`, and `render-mermaid` as deterministic structural helpers while preserving final semantic review in the skill.
- [x] 5.3 Add targeted system-skill content checks for the new graph-tool references and fail-closed routing-packet guidance.

## 6. Verification

- [x] 6.1 Add pure unit tests for node-link JSON loading, graph normalization, high-level analysis, packet expectation generation, packet validation errors, low-level transforms, and low-level algorithms.
- [x] 6.2 Add CLI shape and output tests for `houmao-mgr internals`, `internals graph high`, and `internals graph low`.
- [x] 6.3 Update existing top-level command inventory tests to include `internals`.
- [x] 6.4 Run `pixi run openspec validate add-internals-graph-tools --strict`.
- [x] 6.5 Run targeted unit tests for graph helpers, CLI command shape, and system-skill content checks.
