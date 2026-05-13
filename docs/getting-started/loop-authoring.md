# Loop Authoring Guide

Houmao ships five packaged loop skills. This page helps you choose the right one, explains the pairwise-v2 routing-packet prestart model that pairwise-v3 and pairwise-v4 extend, and introduces the `houmao-mgr internals graph` tooling that supports loop plan authoring.

For mailbox-driven loops, first understand the runtime model: agents are normally woken by gateway notifier prompts, process bounded mail event work, optionally run one prompt-invoked tick, then finish the chat turn. They should not wait in-chat for future mail or periodic ticks. See [Notifier-Prompt-Driven Loop Runtime](../reference/gateway/operations/notifier-prompt-driven-loops.md).

## Choosing a Loop Skill

| Skill | Lifecycle verbs | Prestart model | Topology |
|---|---|---|---|
| `houmao-agent-loop-pairwise` | `start`, `status`, `stop` | None — send start charter directly | Tree-loop local-close edges only (master → named workers) |
| `houmao-agent-loop-pairwise-v2` | `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill` | Routing packets | Tree-loop local-close edges only — enriched lifecycle |
| `houmao-agent-loop-pairwise-v3` | `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill` | Routing packets plus an authored workspace contract | Tree-loop local-close edges only — enriched lifecycle plus workspace posture |
| `houmao-agent-loop-pairwise-v4` | `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill` | Routing packets plus authored workspace and strict generated document templates | Tree-loop local-close edges only — enriched lifecycle plus source-contract coverage |
| `houmao-agent-loop-generic` | `start`, `status`, `stop` | None — send start charter directly | Generic loop: local-close + relay components in one graph |

**Use `houmao-agent-loop-pairwise`** when you want the simplest stable surface: author a plan, send a start charter to the master, poll status, and stop. No prestart ceremony.

**Use `houmao-agent-loop-pairwise-v2`** when you need the enriched lifecycle: routing-packet-based initialization before start, mid-run peek and ping, pause-only `resume`, restart-aware `recover_and_continue`, or `hard-kill`. This is the right choice for complex or long-running tree-loop runs where you want stronger runtime control and do not need the loop plan itself to own workspace posture.

**Use `houmao-agent-loop-pairwise-v3`** when you need the same enriched lifecycle as v2 and you also need the loop plan to declare where agents work and where they keep operator-visible bookkeeping. This package is the workspace-aware extension of pairwise-v2.

**Use `houmao-agent-loop-pairwise-v4`** when you need v3 workspace-aware planning and the source task or user-provided documents are rich enough that generated documents need strict templates. This package keeps source-contract summaries, policy-bearing source rules, role-local agent notes, report/bookkeeping template schemas, and a constraint coverage audit visible in the generated bundle.

**Use `houmao-agent-loop-generic`** when your communication graph has both pairwise components (immediate driver-worker local-close edges) and relay lanes (agent that receives from one side and forwards to another). Generic decomposes your intent into typed components and manages them in one graph.

> **Runnable example:** The [`examples/writer-team/`](../../examples/writer-team/) template contains a complete tree loop plan, role prompts, start charter, and local setup commands for a three-agent story-writing team (writer + character-designer + reviewer). Use it as a starting point for authoring your own loop plans.

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

When the run needs reusable report forms or bookkeeping scaffolds, those files live inside the authored plan bundle under `<plan-output-dir>/templates/`. They are still authored plan files, not a fourth runtime storage class.

## Pairwise-v4: Strict Template Authoring

`houmao-agent-loop-pairwise-v4` keeps the pairwise-v3 control and workspace model, then adds a template-driven source-contract layer for rich task notes and user-provided documents.

Use v4 when the plan should preserve schema-like task or document language instead of loosely summarizing it. The v4 authoring flow extracts high-salience source constraints, preserves policy-bearing source rules keyed by verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH` when they appear in task notes, rulebooks, commons files, or other user-provided documents, assigns stable source-constraint IDs, and projects those rules into the central plan, role-local agent notes, routing packets, reporting templates, bookkeeping templates, scripts, or an explicit unresolved entry.

The generated bundle uses strict document templates for:

- canonical `plan.md`
- participant notes under `agents/`
- reusable reporting templates under `templates/reporting/`
- reusable bookkeeping templates under `templates/bookkeeping/`
- `constraint-coverage-audit.md`

The coverage audit maps each extracted source rule to a central projection and a runtime-facing projection, or marks it `UNRESOLVED - <reason>`. This makes v4 a better fit than v3 for tasks derived from structured commons files, tuned examples, instruction-heavy loop task notes, or user-supplied design documents that use schema-like policy verbs.

### V4 generated plan structure

A v4 rich bundle should make the source contract visible in `plan.md` instead of scattering it across supporting notes. The canonical `plan.md` includes:

- `# Source Contract Summary`
- `## Referenced Sources`
- `## Policy-Bearing Source Rules`
- `## Source Constraints Carried Forward`
- `## Unresolved Source Inputs`
- `# Constraint Coverage Audit`

The generated files should also include `constraint-coverage-audit.md` for bundle plans. That audit is the final checklist for whether each extracted `SC-*` rule appears in the central plan and in the runtime-facing surface that must enforce it. A rule that cannot be projected safely should remain visible as `UNRESOLVED - <reason>` rather than disappearing into prose.

### V4 generated support files

When v4 produces a bundle, the support files should be structured rather than reminder-shaped. Role notes under `agents/` should say what the participant owns, which source constraints apply locally, what hard gates must pass, what SOP verbs govern the work, and what evidence or reports must be returned. Reusable templates under `templates/reporting/` and `templates/bookkeeping/` should carry state schemas, evidence fields, ownership, update rules, and output format expectations from the source material.

Use v3 when a workspace-aware plan only needs ordinary plan prose and routing packets. Use v4 when the source material itself has reusable structure that future agents must be able to inspect, audit, and fill section by section.

### V3 and V4 `standard` versus `custom`

When the workspace contract uses `standard`, the plan records which Houmao-standard posture the run expects.

When the workspace contract uses `custom`, the plan records operator-owned paths directly:

- launch cwd
- source write paths
- shared writable paths
- bookkeeping paths
- read-only paths
- ad hoc worktree posture

Custom mode is deliberately direct. Pairwise-v3 and pairwise-v4 do not silently translate those paths into `houmao-ws/...`, and `houmao-utils-workspace-mgr` does not become a custom-workspace abstraction layer. If the user wants a custom workspace, the loop plan owns it directly.

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

Use it when pairwise-v3 or pairwise-v4 chooses a standard workspace and you want Houmao to prepare or summarize that standard layout.

Do not route custom operator-owned workspace contracts through workspace-manager. Pairwise-v3 custom mode records those paths directly in the loop plan.

### Bookkeeping is declared, not invented

Pairwise-v3 plans can declare bookkeeping paths, but Houmao does not impose one fixed subtree under per-agent `kb/`.

The plan should say which bookkeeping paths are valid for the run. It should not assume that every task uses the same note or log layout.

### Plan-owned template bundles

Use bundle form for pairwise-v3 when the run needs reusable reporting or bookkeeping templates.

Typical bundle additions:

```text
<plan-output-dir>/
  plan.md
  ...
  templates/
    README.md
    reporting/
      peek.md
      completion.md
      stop-summary.md
    bookkeeping/
      <task-shaped-template>.md
```

These files are reusable authored scaffolds:

- `templates/reporting/` mirrors the plan's reporting contract for the report surfaces the run actually uses
- `templates/bookkeeping/` carries task-shaped checklists, ledgers, handoff outlines, or other bookkeeping aids derived from the run objective, topology, roles, and declared bookkeeping paths

Keep the boundary clear:

- files under `templates/` are authored source artifacts in the plan bundle
- mutable filled-in copies belong in declared bookkeeping paths during execution
- runtime-owned recovery files stay under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/...`

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

Pairwise-v3 keeps the same routing-packet preflight model, but changes how the run contract is materialized. In pairwise-v3, `initialize` may first launch missing participants from provided launch profiles, verifies email/mailbox support, verifies or enables gateway mail-notifier behavior for required mail-driven participants with supported live gateway and mailbox surfaces, then writes the durable per-agent run guidance directly into memo blocks, including workspace posture and local obligations. It refuses to reach `ready` when any required participant lacks email/mailbox support or required notifier setup is blocked. Ordinary `start` does not write a durable `start-charter` page and does not wait for `accepted` or `rejected`; it sends a compact master-only trigger telling the master to read its memo and begin, and that kickoff goes through mail by default unless the user explicitly asks for direct prompt delivery.

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

## Generic Loops

`houmao-agent-loop-generic` is for multi-agent topologies that mix component types.

### Component types

- **`pairwise` component**: One immediate driver-worker local-close edge. The worker returns the result to the same driver that sent the component request. Uses the elemental local-close edge-loop protocol from `houmao-adv-usage-pattern`.
- **`relay` component**: An agent that receives from one upstream agent and forwards to a downstream agent. The egress return goes back along the relay lane. Uses the elemental relay-loop protocol from `houmao-adv-usage-pattern`.

### When to use it

Use `houmao-agent-loop-generic` when:

- your workflow has both local-close edges and relay lanes in one graph
- you want the generic skill to own graph decomposition, Mermaid rendering, run charter construction, and `start`/`status`/`stop` control
- you do not need the enriched tree-loop or workspace-aware tree-loop lifecycle verbs

Use the tree loop skills when your topology is purely local-close tree-loop edges. Use the enriched tree loop skill when you need enriched runtime control without authored workspace posture. Use the workspace-aware tree loop skill when you need the enriched runtime control and the loop plan also needs to declare workspace posture.

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
| `graph high packet-expectations` | Expected pairwise-v2, pairwise-v3, and pairwise-v4 routing-packet structure from graph topology |
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
| [`houmao-agent-loop-pairwise-v4` SKILL.md](../../src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v4/SKILL.md) | Template-driven extension of pairwise-v3, including strict generated document templates and constraint coverage audits |
| [`houmao-agent-loop-generic` SKILL.md](../../src/houmao/agents/assets/system_skills/houmao-agent-loop-generic/SKILL.md) | Generic loop decomposition, component types, plan templates, and operating pages |
| [System Skills Overview](system-skills-overview.md) | All packaged skills, auto-install behavior, and skill set reference |
| [internals graph reference](../reference/cli/internals.md) | Full `graph high` and `graph low` command reference |
