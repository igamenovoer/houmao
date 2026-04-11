# houmao-mgr internals

Internal Houmao utility commands for agents and maintainers.

`houmao-mgr internals` exposes the `graph` command family — a set of NetworkX-backed helpers for loop plan authoring, structural analysis, and low-level graph manipulation. All commands use NetworkX node-link JSON as their graph interchange format.

## When to use these commands

**`graph high`** is designed for **loop plan authoring and validation**. When an agent is building or validating a `houmao-agent-loop-pairwise-v2` or `houmao-agent-loop-generic` plan, these commands give it deterministic structural facts — root reachability, packet expectations, validation errors, and Mermaid scaffolding — without requiring graph reasoning inside the skill prompt.

**`graph low`** is for **generic graph construction and NetworkX algorithm access**. Use it when you need to build or transform a graph from scratch, extract subgraphs, or run standard graph algorithms not covered by the high-level surface.

All graph commands accept a node-link JSON file via `--input` (or `--graph` where noted) and use `-` to read from stdin. Commands that produce a graph output emit NetworkX node-link JSON with `nodes`, `edges`, and `graph` keys.

---

## graph high

Houmao-aware loop graph helpers.

### analyze

Analyze Houmao loop graph structure. Reports root reachability, leaves, non-leaf (delegating) participants, immediate children, cycle or DAG posture, component summaries, branch points, and mode-specific shape warnings.

**Synopsis:**
```
houmao-mgr [--print-json] internals graph high analyze [OPTIONS]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--input PATH` | yes | — | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--root TEXT` | no | `graph.root` | Root node override. |
| `--mode TEXT` | no | `graph.mode` | Mode override (e.g. `pairwise-v2`, `generic`). |
| `--cycle-limit INT` | no | `20` | Maximum cycle examples to include in the result. |

**Examples:**
```bash
houmao-mgr --print-json internals graph high analyze --input graph.json
houmao-mgr internals graph high analyze --input graph.json --root master --mode pairwise-v2
```

---

### packet-expectations

Derive pairwise-v2 routing-packet expectations from graph topology. Returns the expected root packet shape, one child packet expectation per pairwise edge, non-leaf dispatch-table expectations, and freshness-marker requirements. Use the output to author or audit routing packets before a pairwise-v2 run.

**Synopsis:**
```
houmao-mgr [--print-json] internals graph high packet-expectations [OPTIONS]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--input PATH` | yes | — | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--root TEXT` | no | `graph.root` | Root node override. |

**Examples:**
```bash
houmao-mgr --print-json internals graph high packet-expectations --input graph.json
houmao-mgr internals graph high packet-expectations --input graph.json --root master
```

---

### validate-packets

Validate pairwise-v2 routing packets against graph-derived expectations. Checks for missing root packets, missing child packets, stale revisions or digests, intended-recipient mismatches, immediate-driver mismatches, missing dispatch tables, and missing exact child packet text or references. Returns a structured validation result with any errors.

Packet JSON shape: `root_packet` plus `child_packets`, where each packet includes `intended_recipient`, `immediate_driver`, freshness markers, and optional `child_dispatch_table` entries with `packet_text` or `packet_ref`.

**Synopsis:**
```
houmao-mgr [--print-json] internals graph high validate-packets [OPTIONS]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--graph PATH` | yes | — | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--packets PATH` | yes | — | Pairwise-v2 routing packet JSON document. |
| `--root TEXT` | no | `graph.root` | Root node override. |

**Examples:**
```bash
houmao-mgr --print-json internals graph high validate-packets --graph graph.json --packets packets.json
houmao-mgr internals graph high validate-packets --graph graph.json --packets packets.json --root master
```

---

### slice

Extract an authoring-time graph slice as node-link JSON. Supports four slice directions: `ancestors`, `descendants`, `reachable` (all nodes reachable from root), and `component` (a named component subgraph). Emits a node-link JSON graph preserving all node, edge, and graph metadata for the included elements.

**Synopsis:**
```
houmao-mgr [--print-json] internals graph high slice [OPTIONS]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--input PATH` | yes | — | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--root TEXT` | yes | — | Root node for ancestor, descendant, or reachable slices. |
| `--direction CHOICE` | yes | — | One of `ancestors`, `descendants`, `reachable`, `component`. |
| `--component-id TEXT` | no | — | Component ID required when `--direction component`. |

**Examples:**
```bash
houmao-mgr --print-json internals graph high slice --input graph.json --root agent-a --direction descendants
houmao-mgr --print-json internals graph high slice --input graph.json --direction component --component-id c1 --root master
```

---

### render-mermaid

Render deterministic Mermaid scaffolding from graph structure. Produces a Mermaid flowchart based on node and edge types in the graph. This is a structural scaffold — final semantic review of loop logic and edge labels belongs in the owning Houmao skill.

With `--print-plain` (the default), emits the Mermaid text directly. With `--print-json`, emits a JSON payload with a `mermaid` field.

**Synopsis:**
```
houmao-mgr [--print-json | --print-plain] internals graph high render-mermaid [OPTIONS]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--input PATH` | yes | — | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--root TEXT` | no | `graph.root` | Root node override. |
| `--mode TEXT` | no | `graph.mode` | Mode override. |

**Examples:**
```bash
houmao-mgr internals graph high render-mermaid --input graph.json
houmao-mgr --print-json internals graph high render-mermaid --input graph.json --mode generic
```

---

## graph low

Constrained NetworkX-style low-level graph primitives. These commands emit node-link JSON graphs and accept node-link JSON as input.

### create

Create an empty supported NetworkX graph.

| Option | Required | Default | Description |
|---|---|---|---|
| `--type CHOICE` | no | `multidigraph` | One of `multidigraph`, `digraph`, `multigraph`, `graph`. |

```bash
houmao-mgr --print-json internals graph low create --type multidigraph
```

### mutate

Apply constrained graph mutation operations. The ops JSON must have an `ops` array; each op must have an `op` field (e.g. `add_node`, `add_edge`, `remove_node`, `remove_edge`, `set_node_attr`, `set_edge_attr`, `set_graph_attr`).

Ops JSON shape: `{ "ops": [{ "op": "add_node", "node": "agent-a", "attrs": {"kind": "agent"} }] }`.

| Option | Required | Description |
|---|---|---|
| `--input PATH` | yes | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--ops PATH` | yes | Mutation ops JSON file. |

```bash
houmao-mgr --print-json internals graph low mutate --input graph.json --ops ops.json
```

### relabel

Relabel graph nodes with a JSON object mapping old node IDs to new node IDs.

| Option | Required | Description |
|---|---|---|
| `--input PATH` | yes | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--mapping PATH` | yes | JSON object mapping old node IDs to new IDs. |

```bash
houmao-mgr --print-json internals graph low relabel --input graph.json --mapping mapping.json
```

### compose

Compose two node-link graphs (NetworkX `compose` semantics — nodes and edges from both graphs are merged; right-graph attributes override on conflict).

| Option | Required | Description |
|---|---|---|
| `--left PATH` | yes | Left graph JSON. |
| `--right PATH` | yes | Right graph JSON. |

```bash
houmao-mgr --print-json internals graph low compose --left a.json --right b.json
```

### subgraph

Extract a node-induced subgraph. The nodes JSON must have a `nodes` array of node IDs.

| Option | Required | Description |
|---|---|---|
| `--input PATH` | yes | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--nodes PATH` | yes | JSON file with a `nodes` array. |

```bash
houmao-mgr --print-json internals graph low subgraph --input graph.json --nodes nodes.json
```

### reverse

Reverse directed graph edges.

| Option | Required | Description |
|---|---|---|
| `--input PATH` | yes | NetworkX node-link JSON graph file; use `-` for stdin. |

```bash
houmao-mgr --print-json internals graph low reverse --input graph.json
```

### ego

Compute an ego graph (a subgraph centered on one node within a given radius).

| Option | Required | Default | Description |
|---|---|---|---|
| `--input PATH` | yes | — | NetworkX node-link JSON graph file; use `-` for stdin. |
| `--node TEXT` | yes | — | Center node. |
| `--radius INT` | no | `1` | Ego radius (hop count). |
| `--undirected` | no | off | Treat graph as undirected for ego expansion. |

```bash
houmao-mgr --print-json internals graph low ego --input graph.json --node agent-a --radius 2
```

---

## graph low alg

Whitelisted low-level graph algorithm wrappers. All algorithm subcommands share the same option schema; only the options relevant to each algorithm need to be supplied.

### Shared option schema

| Option | Description |
|---|---|
| `--input PATH` | NetworkX node-link JSON graph file; use `-` for stdin. **Required for all alg commands.** |
| `--node TEXT` | Node argument for node-centered algorithms. |
| `--source TEXT` | Source node for path algorithms. |
| `--target TEXT` | Target node for path algorithms. |
| `--distance INT` | Exact-distance value for distance-bounded algorithms. |
| `--cutoff INT` | Path length cutoff for path-enumeration algorithms. |
| `--length-bound INT` | Cycle length bound for cycle-enumeration algorithms. |
| `--limit INT` | Maximum result count for expansive algorithms. Default: `50`. |

### Subcommand summary

| Subcommand | Required options (beyond `--input`) | Description |
|---|---|---|
| `ancestors` | `--node` | Return all NetworkX ancestors of a node. |
| `descendants` | `--node` | Return all NetworkX descendants of a node. |
| `descendants-at-distance` | `--node`, `--distance` | Return descendants at an exact hop distance. |
| `topological-sort` | — | Return a deterministic topological ordering. Graph must be a DAG. |
| `is-dag` | — | Report whether the directed graph is acyclic. |
| `cycles` | — | Return bounded simple cycle examples. Use `--length-bound` and `--limit` to bound results. |
| `weak-components` | — | Return weakly connected component sets. |
| `strong-components` | — | Return strongly connected component sets. |
| `condensation` | — | Return NetworkX condensation graph summary. |
| `transitive-reduction` | — | Return a transitive-reduction adjacency summary. Graph must be a DAG. |
| `dag-longest-path` | — | Return a DAG longest path. Graph must be a DAG. |
| `shortest-path` | `--source`, `--target` | Return one shortest path between source and target. |
| `all-simple-paths` | `--source`, `--target` | Return bounded simple paths between source and target. Use `--cutoff` and `--limit` to bound results. |

**Examples:**
```bash
houmao-mgr --print-json internals graph low alg ancestors --input graph.json --node agent-b
houmao-mgr --print-json internals graph low alg descendants-at-distance --input graph.json --node master --distance 2
houmao-mgr --print-json internals graph low alg cycles --input graph.json --length-bound 6 --limit 10
houmao-mgr --print-json internals graph low alg shortest-path --input graph.json --source master --target agent-b
houmao-mgr --print-json internals graph low alg all-simple-paths --input graph.json --source master --target agent-b --cutoff 5 --limit 20
```
