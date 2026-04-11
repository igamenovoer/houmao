# Loop Authoring Guide

Houmao ships three packaged loop skills. This page helps you choose the right one, explains the pairwise-v2 routing-packet prestart model, and introduces the `houmao-mgr internals graph` tooling that supports loop plan authoring.

## Choosing a Loop Skill

| Skill | Lifecycle verbs | Prestart model | Topology |
|---|---|---|---|
| `houmao-agent-loop-pairwise` | `start`, `status`, `stop` | None — send start charter directly | Pairwise edges only (master → named workers) |
| `houmao-agent-loop-pairwise-v2` | `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`, `hard-kill` | Routing packets (default) or operator preparation wave (opt-in) | Pairwise edges only — enriched lifecycle |
| `houmao-agent-loop-generic` | `start`, `status`, `stop` | None — send start charter directly | Mixed: pairwise + relay components in one graph |

**Use `houmao-agent-loop-pairwise`** when you want the simplest stable surface: author a plan, send a start charter to the master, poll status, and stop. No prestart ceremony.

**Use `houmao-agent-loop-pairwise-v2`** when you need the enriched lifecycle: routing-packet-based initialization before start, mid-run peek and ping, pause/resume support, or `hard-kill`. This is the right choice for complex or long-running pairwise runs where you want stronger runtime control.

**Use `houmao-agent-loop-generic`** when your communication graph has both pairwise components (immediate driver-worker local-close edges) and relay lanes (agent that receives from one side and forwards to another). Generic decomposes your intent into typed components and manages them in one graph.

---

## Pairwise-v2: Routing Packets

The most important behavioral difference in `houmao-agent-loop-pairwise-v2` is its prestart model.

### What a routing packet is

A **routing packet** is a precomputed instruction block embedded in the plan before the run starts. Each non-leaf participant (the master and any intermediate agents) gets a packet that tells it:
- who it should receive the start charter from (its `immediate_driver`),
- who it is the `intended_recipient` for,
- what child packets it should forward to each downstream worker when it delegates.

Because routing packets are authored at plan time — not delivered over the wire during prestart — participants already have their delegation instructions when the run begins.

### What `initialize` does

`initialize` is the prestart action for pairwise-v2 runs. The default strategy is `precomputed_routing_packets`:

```
plan authored      initialize (validate packets)     start
      │                         │                      │
      ▼                         ▼                      ▼
 routing packets         confirm root packet      send start
 embedded in plan        + child packets          charter to
                         are present and          master only
                         structurally valid
```

The `operator_preparation_wave` strategy is an explicit opt-in in the plan. It sends standalone preparation mail to targeted participants and optionally waits for acknowledgement replies before the master trigger. Use it for complex warmup scenarios, acknowledgement-gated preflight, or explicit participant confirmation before the run.

### CLI helpers for routing packets

`houmao-mgr internals graph high` provides two commands purpose-built for routing-packet authoring:

```bash
# Derive expected packet structure from the graph topology
houmao-mgr --print-json internals graph high packet-expectations --input graph.json

# Validate an authored packet document against the graph-derived expectations
houmao-mgr --print-json internals graph high validate-packets \
    --graph graph.json --packets packets.json
```

`packet-expectations` tells you what the root packet and each child packet must contain. `validate-packets` confirms a packet document is structurally correct before `initialize` runs.

---

## Generic Loop Graphs

`houmao-agent-loop-generic` is for multi-agent topologies that mix component types.

### Component types

- **`pairwise` component**: One immediate driver-worker local-close edge. The worker returns the result to the same driver that sent the component request. Uses the elemental pairwise edge-loop protocol from `houmao-adv-usage-pattern`.
- **`relay` component**: An agent that receives from one upstream agent and forwards to a downstream agent. The egress return goes back along the relay lane. Uses the elemental relay-loop protocol from `houmao-adv-usage-pattern`.

### When to use it

Use `houmao-agent-loop-generic` when:
- Your workflow has both pairwise edges and relay lanes in one graph.
- You want the generic skill to own graph decomposition, Mermaid rendering, run charter construction, and `start`/`status`/`stop` control.
- You do not need the enriched pairwise-v2 lifecycle verbs (peek, ping, pause, routing packets).

Use the pairwise-only skills when your topology is purely pairwise edges. Use `houmao-agent-loop-pairwise-v2` when you need enriched runtime control on a pairwise graph.

### Graph rendering

`graph high render-mermaid` produces a deterministic Mermaid scaffold from a typed generic graph:

```bash
houmao-mgr internals graph high render-mermaid --input graph.json
```

This is a structural scaffold — the owning skill owns final semantic review of edge labels and delegation policy.

---

## Graph Tooling Summary

All `graph high` commands accept NetworkX node-link JSON via `--input` and are designed to be called from inside an agent session.

| Command | What it provides |
|---|---|
| `graph high analyze` | Root reachability, leaves, delegating nodes, cycle/DAG posture, shape warnings |
| `graph high packet-expectations` | Expected pairwise-v2 routing-packet structure from graph topology |
| `graph high validate-packets` | Structural validation of a routing-packet document |
| `graph high slice` | Ancestor, descendant, reachable, or component subgraph extraction |
| `graph high render-mermaid` | Deterministic Mermaid scaffolding from graph structure |

For the full option reference for all graph commands, see [internals graph](../reference/cli/internals.md).

---

## Next Steps

| Resource | What it covers |
|---|---|
| [`houmao-agent-loop-pairwise` SKILL.md](../../src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/SKILL.md) | Full plan templates, authoring pages, and `start`/`status`/`stop` operating pages |
| [`houmao-agent-loop-pairwise-v2` SKILL.md](../../src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/SKILL.md) | Enriched lifecycle vocabulary, routing-packet prestart, and all operating pages |
| [`houmao-agent-loop-generic` SKILL.md](../../src/houmao/agents/assets/system_skills/houmao-agent-loop-generic/SKILL.md) | Generic graph decomposition, component types, plan templates, and operating pages |
| [System Skills Overview](system-skills-overview.md) | All packaged skills, auto-install behavior, and skill set reference |
| [internals graph reference](../reference/cli/internals.md) | Full `graph high` and `graph low` command reference |
