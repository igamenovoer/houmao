# houmao-mgr-internals-graph-cli Specification

## Purpose
TBD - created by archiving change add-internals-graph-tools. Update Purpose after archive.
## Requirements
### Requirement: `houmao-mgr internals graph` uses NetworkX node-link JSON
`houmao-mgr` SHALL expose a top-level `internals` command family with a nested `graph` command family for internal graph tooling.

The `internals graph` command family SHALL use NetworkX node-link JSON as its only graph interchange format.

The graph reader SHALL accept node-link JSON objects with `nodes`, `edges`, and `graph` fields following the NetworkX node-link convention.

The graph reader SHALL normalize graph input to a NetworkX `MultiDiGraph` unless a low-level command explicitly constructs a different supported graph type.

The graph writer SHALL emit NetworkX node-link JSON with the `edges` key for edge records and the `nodes` key for node records.

Houmao-specific graph metadata, including `schema_version`, `mode`, `root`, `plan_id`, `plan_revision`, or `plan_digest`, SHALL live under the node-link `graph` object.

Node and edge attributes SHALL preserve agent, component, edge, and packet linkage metadata needed by high-level loop graph commands.

The graph CLI SHALL NOT support a separate Houmao YAML graph interchange format.

#### Scenario: Command reads node-link graph metadata
- **WHEN** an agent invokes a graph command with node-link JSON whose `graph` object contains `mode`, `root`, and `plan_revision`
- **THEN** the command loads that metadata as graph-level metadata
- **AND THEN** the command preserves the metadata in graph outputs that emit a transformed node-link graph

#### Scenario: Command rejects unsupported graph input shape
- **WHEN** an agent invokes a graph command with input that is not NetworkX node-link JSON
- **THEN** the command exits non-zero with a structured validation error
- **AND THEN** it does not attempt to infer a graph from arbitrary YAML or Markdown prose

### Requirement: `graph high` provides Houmao-aware loop graph helpers
`houmao-mgr internals graph high` SHALL expose Houmao-aware graph helper commands for loop authoring and validation.

At minimum, `graph high` SHALL include:

- `analyze`,
- `packet-expectations`,
- `validate-packets`,
- `slice`,
- `render-mermaid`.

The `analyze` command SHALL report structural facts that are useful to loop authoring, including at minimum:

- root identity when available,
- reachable nodes from the root,
- disconnected nodes,
- leaf nodes,
- non-leaf or delegating nodes,
- immediate children per node,
- ancestors or descendants when requested,
- cycle or DAG posture,
- weak and strong component summaries,
- branch points,
- component dependency ordering when dependency edges are present,
- warnings for graph shapes that are unsafe for the selected mode.

The `slice` command SHALL support authoring-time extraction of ancestor, descendant, reachable, or component slices and SHALL emit the selected slice as node-link JSON.

The `render-mermaid` command SHALL produce deterministic Mermaid graph scaffolding from graph structure while leaving final semantic review to the loop authoring skill.

High-level commands SHALL remain structural helpers. They SHALL NOT infer free delegation, free forwarding, hidden dependencies, or final loop policy when the graph and metadata do not explicitly authorize those semantics.

#### Scenario: High analyze identifies delegating participants
- **WHEN** an agent runs `houmao-mgr internals graph high analyze` on a directed pairwise-v2 topology with a configured root
- **THEN** the result identifies leaf and non-leaf participants
- **AND THEN** it identifies immediate child relationships without widening delegation authority beyond the graph edges

#### Scenario: High slice emits descendant subgraph
- **WHEN** an agent runs `houmao-mgr internals graph high slice --direction descendants --root agent-a`
- **THEN** the command emits a node-link JSON graph containing the requested descendant slice
- **AND THEN** the emitted slice preserves graph, node, and edge metadata for the included graph elements

#### Scenario: High Mermaid rendering is a scaffold
- **WHEN** an agent runs `houmao-mgr internals graph high render-mermaid` for a generic loop graph
- **THEN** the command emits deterministic Mermaid text based on the typed graph structure
- **AND THEN** the command does not claim that the generated text replaces the loop skill's final graph semantics review

### Requirement: `graph high` validates pairwise-v2 routing-packet structure
`houmao-mgr internals graph high packet-expectations` SHALL derive expected pairwise-v2 routing-packet coverage from a node-link graph topology.

For a pairwise-v2 graph, `packet-expectations` SHALL report at minimum:

- the expected root packet recipient,
- one expected child packet for each parent-to-child pairwise edge,
- the expected immediate driver and intended recipient for every child packet,
- the non-leaf participant set,
- the child dispatch table expected for each non-leaf participant,
- the graph metadata freshness marker that packet validation should compare when a plan revision or digest is available.

`houmao-mgr internals graph high validate-packets` SHALL compare a packet JSON document against the graph-derived packet expectations.

Packet validation SHALL report structured errors for at least:

- missing root packet,
- missing child packet,
- stale plan revision or digest,
- intended recipient mismatch,
- immediate driver mismatch,
- missing child dispatch table for a non-leaf participant,
- missing exact child packet text or exact child packet reference for a dispatch-table child.

Packet validation SHALL fail closed. When a packet is missing, mismatched, or stale, the command SHALL report the mismatch and SHALL NOT synthesize or repair replacement packet content from graph topology.

#### Scenario: Packet expectations cover each pairwise edge
- **WHEN** an agent runs `packet-expectations` on a pairwise-v2 graph with root `master` and edges `master -> agent-a` and `agent-a -> agent-b`
- **THEN** the result identifies the root packet recipient as `master`
- **AND THEN** the result identifies expected child packets for `master -> agent-a` and `agent-a -> agent-b`
- **AND THEN** the result identifies `agent-a` as requiring a child dispatch table

#### Scenario: Packet validation fails closed on stale packet
- **WHEN** an agent runs `validate-packets` with a packet document whose packet revision does not match the graph's active plan revision
- **THEN** the command reports a stale packet validation error
- **AND THEN** it does not repair or rewrite the packet from graph memory

#### Scenario: Packet validation detects wrong child recipient
- **WHEN** an agent runs `validate-packets` and the child packet for edge `agent-a -> agent-b` names `agent-c` as the intended recipient
- **THEN** the command reports an intended-recipient mismatch for that child packet
- **AND THEN** it returns a non-success validation result

### Requirement: `graph low` exposes constrained NetworkX-backed primitives
`houmao-mgr internals graph low` SHALL expose constrained low-level graph tools that map directly to whitelisted NetworkX graph construction, transformation, and algorithm capabilities.

At minimum, `graph low` SHALL include graph construction or mutation support for:

- creating an empty supported graph,
- adding nodes,
- adding edges,
- removing nodes,
- removing edges,
- setting graph metadata attributes.

At minimum, `graph low` SHALL include graph transformation support for:

- relabeling nodes,
- composing two graphs,
- extracting a node-induced subgraph,
- reversing directed edges,
- computing ego graphs.

At minimum, `graph low alg` SHALL include wrappers for:

- `ancestors`,
- `descendants`,
- `descendants-at-distance`,
- `topological-sort`,
- `is-dag`,
- bounded cycle enumeration,
- weakly connected components,
- strongly connected components,
- condensation,
- transitive reduction,
- DAG longest path,
- shortest path,
- all simple paths with cutoff.

Low-level algorithm commands that can expand combinatorially SHALL require explicit bounds or SHALL apply conservative default bounds and include the bound in the result payload.

The low-level graph CLI SHALL NOT expose arbitrary Python expression evaluation or arbitrary NetworkX function dispatch.

#### Scenario: Low descendants maps to NetworkX descendant analysis
- **WHEN** an agent runs `houmao-mgr internals graph low alg descendants --node agent-a`
- **THEN** the command returns the descendants of `agent-a` from the loaded graph
- **AND THEN** the command output identifies the algorithm name used for the result

#### Scenario: Low compose emits a node-link graph
- **WHEN** an agent runs `houmao-mgr internals graph low compose` with two valid node-link graph inputs
- **THEN** the command composes the graphs through the supported NetworkX compose behavior
- **AND THEN** it emits the composed graph as node-link JSON

#### Scenario: Low layer rejects unsupported arbitrary function dispatch
- **WHEN** an agent asks `graph low` to run a NetworkX function that is not in the whitelisted command surface
- **THEN** the CLI exits non-zero through normal Click command resolution
- **AND THEN** it does not evaluate arbitrary Python or dynamically dispatch to that function by name

### Requirement: Graph command output respects `houmao-mgr` print styles
Every `houmao-mgr internals graph` command that emits a structured result SHALL use the shared `houmao-mgr` output engine.

When the active print style is `json`, graph commands SHALL emit valid JSON payloads.

When a command's primary output is a graph, the JSON output SHALL use node-link JSON for that graph.

When a command's primary output is an analysis, validation, or algorithm result, the JSON output SHALL include stable top-level keys describing the operation and result.

Plain output MAY use compact human-readable summaries for analysis and validation commands, but it SHALL NOT drop machine-critical result fields from JSON output.

#### Scenario: Graph analysis emits JSON under print-json
- **WHEN** an agent runs `houmao-mgr --print-json internals graph high analyze --input graph.json`
- **THEN** the command emits a valid JSON object
- **AND THEN** the JSON object includes the operation name, graph summary, warnings, and validation errors when present

#### Scenario: Graph transform emits node-link JSON under print-json
- **WHEN** an agent runs `houmao-mgr --print-json internals graph low subgraph --input graph.json --nodes nodes.json`
- **THEN** the command emits a NetworkX node-link JSON graph for the selected subgraph
- **AND THEN** the emitted graph can be passed to another `internals graph` command without format conversion

### Requirement: Individual graph commands include input examples in help text
Every individual command under `houmao-mgr internals graph high`, `houmao-mgr internals graph low`, and `houmao-mgr internals graph low alg` SHALL include help text with at least one concrete example invocation.

For commands that read non-graph JSON documents, the command help SHALL describe the expected document role or shape, such as mutation ops JSON, node selection JSON, relabel mapping JSON, or pairwise-v2 packet JSON.

These examples SHALL be intended for agent consumption so that an agent can infer what file or stdin payload to feed to the command without consulting source code.

#### Scenario: High command help gives an invocation example
- **WHEN** an agent runs `houmao-mgr internals graph high validate-packets --help`
- **THEN** the help output includes an example `validate-packets` invocation
- **AND THEN** the help output describes that the packet document contains `root_packet` and `child_packets`

#### Scenario: Low command help gives a non-graph JSON shape
- **WHEN** an agent runs `houmao-mgr internals graph low mutate --help`
- **THEN** the help output includes an example `mutate` invocation
- **AND THEN** the help output describes the mutation ops JSON shape

