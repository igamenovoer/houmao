# Loop Authoring Guide

Houmao ships four packaged loop skills. This page helps you choose the right one, explains the pairwise-v2 routing-packet prestart model that pairwise-v3 extends, and introduces the `houmao-mgr internals graph` tooling that supports loop plan authoring.

## Choosing a Loop Skill

| Skill | Lifecycle verbs | Prestart model | Topology |
|---|---|---|---|
| `houmao-agent-loop-pairwise` | `start`, `status`, `stop` | None — send start charter directly | Pairwise edges only (master → named workers) |
| `houmao-agent-loop-pairwise-v2` | `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill` | Routing packets (default) or operator preparation wave (opt-in) | Pairwise edges only — enriched lifecycle |
| `houmao-agent-loop-pairwise-v3` | `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill` | Routing packets plus an authored workspace contract | Pairwise edges only — enriched lifecycle plus workspace posture |
| `houmao-agent-loop-generic` | `start`, `status`, `stop` | None — send start charter directly | Mixed: pairwise + relay components in one graph |

**Use `houmao-agent-loop-pairwise`** when you want the simplest stable surface: author a plan, send a start charter to the master, poll status, and stop. No prestart ceremony.

**Use `houmao-agent-loop-pairwise-v2`** when you need the enriched lifecycle: routing-packet-based initialization before start, mid-run peek and ping, pause-only `resume`, restart-aware `recover_and_continue`, or `hard-kill`. This is the right choice for complex or long-running pairwise runs where you want stronger runtime control and do not need the loop plan itself to own workspace posture.

**Use `houmao-agent-loop-pairwise-v3`** when you need the same enriched lifecycle as v2 and you also need the loop plan to declare where agents work and where they keep operator-visible bookkeeping. Pairwise-v3 is the workspace-aware extension of pairwise-v2.

**Use `houmao-agent-loop-generic`** when your communication graph has both pairwise components (immediate driver-worker local-close edges) and relay lanes (agent that receives from one side and forwards to another). Generic decomposes your intent into typed components and manages them in one graph.

> **Runnable example:** The [`examples/writer-team/`](../../examples/writer-team/) template contains a complete pairwise loop plan, role prompts, start charter, and local setup commands for a three-agent story-writing team (writer + character-designer + reviewer). Use it as a starting point for authoring your own loop plans.

---

## Pairwise-v3: Workspace Contracts

`houmao-agent-loop-pairwise-v3` keeps the pairwise-v2 control model but adds one more authored contract to the plan:

```text
workspace_contract:
  mode: standard | custom
```

That means a pairwise-v3 plan owns three different storage classes:

- authored plan files under the chosen plan output directory
- participant-facing durable guidance in managed memory pages when the run uses them
- runtime-owned recovery files under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/...`

The runtime-owned recovery files remain Houmao-owned state, not ordinary workspace or bookkeeping paths.

### `standard` versus `custom`

When the workspace contract uses `standard`, the plan records which Houmao-standard posture the run expects.

When the workspace contract uses `custom`, the plan records operator-owned paths directly:

- launch cwd
- source write paths
- shared writable paths
- bookkeeping paths
- read-only paths
- ad hoc worktree posture

Custom mode is deliberately direct. Pairwise-v3 does not silently translate those paths into `houmao-ws/...`, and `houmao-utils-workspace-mgr` does not become a custom-workspace abstraction layer. If the user wants a custom workspace, the loop plan owns it directly.

### Standard in-repo posture is task-scoped

The current standard in-repo posture is task-scoped so one repository can host multiple teams without path or branch collisions.

```text
<repo-root>/
  houmao-ws/
    workspaces.md
    <task-name>/
      workspace.md
      shared-kb/
      <agent-name>/
        kb/
        repo/
```

Important consequences:

- the task root is `<repo-root>/houmao-ws/<task-name>`
- `houmao-ws/workspaces.md` is only the repo-level index
- `houmao-ws/<task-name>/workspace.md` is the authoritative task-local contract
- shared knowledge is task-local under `shared-kb/`
- default in-repo branches are task-qualified, such as `houmao/<task-name>/<agent-name>/main`

Agents still launch from `<repo-root>` by default for shared visibility, but their standard write surfaces become task-local:

- source changes in `<repo-root>/houmao-ws/<task-name>/<agent-name>/repo`
- direct agent notes in `<repo-root>/houmao-ws/<task-name>/<agent-name>/kb`
- merge-oriented shared knowledge in the agent's private worktree copy of `houmao-ws/<task-name>/shared-kb`

### Relationship to `houmao-utils-workspace-mgr`

`houmao-utils-workspace-mgr` remains the standard workspace-preparation skill.

Use it when pairwise-v3 chooses a standard workspace and you want Houmao to prepare or summarize that standard layout.

Do not route custom operator-owned workspace contracts through workspace-manager. Pairwise-v3 custom mode records those paths directly in the loop plan.

### Bookkeeping is declared, not invented

Pairwise-v3 plans can declare bookkeeping paths, but Houmao does not impose one fixed subtree under per-agent `kb/`.

The plan should say which bookkeeping paths are valid for the run. It should not assume that every task uses the same note or log layout.

---

## Pairwise-v2: Routing Packets

The most important behavioral difference in `houmao-agent-loop-pairwise-v2` is its prestart model.

Pairwise-v3 inherits this model. The main difference is that v3 also records the authored workspace contract described above.

### What a routing packet is

A **routing packet** is a precomputed instruction block embedded in the plan before the run starts. Each non-leaf participant (the master and any intermediate agents) gets a packet that tells it:

- who it should receive the start charter from (its `immediate_driver`)
- who it is the `intended_recipient` for
- what child packets it should forward to each downstream worker when it delegates

Because routing packets are authored at plan time, not delivered over the wire during prestart, participants already have their delegation instructions when the run begins.

### What `initialize` does

`initialize` is the prestart action for pairwise-v2 runs. The default strategy is `precomputed_routing_packets`:

```text
plan authored      initialize (validate packets   start (write
      │            + write durable initialize     start-charter page
      │            pages and memo references)     + send compact trigger)
      ▼                         │                      │
 routing packets                ▼                      ▼
 embedded in plan        participants get        master receives page-
                         durable per-run         backed start contract
                         guidance before start   before dispatch
```

Default `initialize` validates the routing-packet set and writes durable run material into managed memory when those supported surfaces are available:

- one run-scoped participant initialize page under `pages/`, using a namespace such as `loop-runs/pairwise-v2/<run_id>/initialize.md`
- one compact memo reference block that links to that page and can be refreshed by exact `run_id` plus slot sentinels

`start` then writes the master-facing `start-charter` page under the same run-scoped namespace, refreshes the matching memo reference block, and sends a compact control-plane trigger that points the master at that durable page.

Accepted `start` also creates or refreshes the runtime-owned recovery record under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json` plus append-only history in `events.jsonl`. That record stays outside the authored plan bundle and outside participant-local memo/pages so the same logical `run_id` can survive participant relaunch.

The `operator_preparation_wave` strategy is an explicit opt-in in the plan. It sends standalone preparation mail to targeted participants and optionally waits for acknowledgement replies before the master trigger, but it is no longer the default carrier for initialize guidance. Use it for complex warmup scenarios, acknowledgement-gated preflight, or explicit participant confirmation before the run.

### `resume` versus `recover_and_continue`

`resume` is pause-only. Use it when the participant set and wakeup posture remained logically live and the run simply needs its paused clock restarted.

Use `recover_and_continue` when one or more participants were stopped, killed, or relaunched and the same logical `run_id` should continue. Restart recovery rebinds participants, refreshes durable continuation material such as `loop-runs/pairwise-v2/<run_id>/recover-and-continue.md`, restores declarative notifier posture, and returns the run to `running` only after the master explicitly accepts continuation.

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

- your workflow has both pairwise edges and relay lanes in one graph
- you want the generic skill to own graph decomposition, Mermaid rendering, run charter construction, and `start`/`status`/`stop` control
- you do not need the enriched pairwise-v2 or pairwise-v3 lifecycle verbs

Use the pairwise-only skills when your topology is purely pairwise edges. Use pairwise-v2 when you need enriched runtime control without authored workspace posture. Use pairwise-v3 when you need the enriched runtime control and the loop plan also needs to declare workspace posture.

### Graph rendering

`graph high render-mermaid` produces a deterministic Mermaid scaffold from a typed generic graph:

```bash
houmao-mgr internals graph high render-mermaid --input graph.json
```

This is a structural scaffold. The owning skill owns final semantic review of edge labels and delegation policy.

---

## Graph Tooling Summary

All `graph high` commands accept NetworkX node-link JSON via `--input` and are designed to be called from inside an agent session.

| Command | What it provides |
|---|---|
| `graph high analyze` | Root reachability, leaves, delegating nodes, cycle/DAG posture, shape warnings |
| `graph high packet-expectations` | Expected pairwise-v2 and pairwise-v3 routing-packet structure from graph topology |
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
| [`houmao-agent-loop-pairwise-v3` SKILL.md](../../src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v3/SKILL.md) | Workspace-aware extension of pairwise-v2, including `standard` versus `custom` workspace contracts |
| [`houmao-agent-loop-generic` SKILL.md](../../src/houmao/agents/assets/system_skills/houmao-agent-loop-generic/SKILL.md) | Generic graph decomposition, component types, plan templates, and operating pages |
| [System Skills Overview](system-skills-overview.md) | All packaged skills, auto-install behavior, and skill set reference |
| [internals graph reference](../reference/cli/internals.md) | Full `graph high` and `graph low` command reference |
