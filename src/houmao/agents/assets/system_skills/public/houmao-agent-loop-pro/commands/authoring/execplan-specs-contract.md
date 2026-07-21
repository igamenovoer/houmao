---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Execplan Specs Contract

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/generation-pipeline.md`
- `../reference/generated-contract-defaults.md`
- `../reference/topology-modes.md`
- `../reference/cycle-normalization.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- `../reference/result-routing.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- `execplan-specs-process` has produced a current process model.

## Inputs

Require:
- `<loop-dir>`
- current intention source;
- generated process overview at `<loop-dir>/execplan/specs/collab/collab-overview.md`.

## Outputs

Generate or update concrete contracts derived from the process model:
- objective and success posture;
- participants and stable role instances;
- topology and route constraints;
- communication schemas, renderers, registry, and reply links;
- notification prompt and trigger contracts for mail-driven participants;
- operator control contracts for lifecycle, execution mode, and manual stepping when the loop supports those controls;
- state kernel and record schemas when durable bookkeeping is needed;
- workspace and run artifact contracts when work roots or durable artifacts are needed;
- explicit omission notes for unused contract areas.

Use these canonical paths when the corresponding concern exists:

```text
<loop-dir>/execplan/specs/
  README.md
  objective/
    README.md
    objective.toml
    policy.toml
  collab/
    README.md
    collab-overview.md
    loop-policy.toml
    topology/
      README.md
      topology.toml
      graph.md
      context-posture.toml
    records/
      README.md
      <record-family>.schema.json
  comms/
    README.md
    comms-overview.md
    templates.toml
    schemas/
      README.md
      <message-family>.schema.json
    renderers/
      README.md
      <message-family>.md.j2
  state/
    README.md
    state-overview.md
    schema.sql
    seed.toml
    invariants.toml
    records/
      <record-family>.schema.json
  workspace/
    README.md
    workspace.toml
  run/
    README.md
    run-artifacts.toml
  participants/
    README.md
    participants.toml
    <participant-role>.md
```

`specs/collab/collab-overview.md` is created by the process stage and must not be replaced by a flat `specs/process.md`. Optional files may be omitted, but any omission of a default concern that later artifacts would normally need must be recorded in the manifest, generated docs, or validation notes.

## Actions

1. Read `<loop-dir>/execplan/specs/collab/collab-overview.md` first.
2. Derive objective, participant, topology, communication, control, state, record, workspace, and run contracts from process needs.
3. Keep participant role templates, participant instances, and concrete agent bindings separate; agent bindings are not generated in this stage.
4. Create or update README files for every emitted generated artifact directory using only `Purpose` and `Contents`.
5. Use schema-validated payload plus human-readable rendering for mail-driven or structurally recorded human-facing artifacts.
6. Emit `execplan/specs/collab/topology/` when participant routes are non-trivial:
  - `topology.toml` records the selected mode, participant nodes, routes, local-close or generic routing policy, cycle posture, and validation expectations;
  - `graph.md` explains the topology in readable form and includes a Mermaid diagram when useful;
  - `context-posture.toml` is emitted for generic routes when predecessor-context choices need machine-readable validation.
7. For `tree-loop`, record local-close immediate-upstream result return and any accepted cycle normalization through an existing participant.
8. For `generic-loop`, record route-level reply or forward policy, termination, dedupe or repeat-visit rules, and selected predecessor-context posture.
9. Generate new topology values as `tree-loop` or `generic-loop`; when updating existing material, accept `pairwise-tree`, `pairwise-loop`, `pairwise`, `generic-graph`, and `generic graph` as aliases.
10. For mail-driven loops, derive notifier prompt contracts from the process model, including schema-id event dispatch, which on-event skill handles each received message family, and which on-tick skill runs after mail when required.
11. For controllable loops, derive run lifecycle state, execution mode, operator intent events, mode-switch rules, and notifier-posture expectations.
12. When managed workspaces are needed, generate workspace-manager inputs under `execplan/specs/workspace/workspace.toml`.
13. Generate task-specific records only when intention or process specs introduce them.
14. Record explicit omissions for irrelevant default layers.

## Communication Contracts

For each ordinary templated mail family:
- assign a stable `schema_id` that acts as the mail type;
- create `execplan/specs/comms/schemas/<message-family>.schema.json`;
- create `execplan/specs/comms/renderers/<message-family>.md.j2`;
- register the template in `execplan/specs/comms/templates.toml`;
- include reply, result, forward, acknowledgement, error, freeform, or repair families only when the process needs them.

`templates.toml` maps each template name to:
- `schema_id`;
- schema path;
- renderer path;
- payload format;
- reply expectation or requested reply schema when applicable.

Generated schemas include validation-visible fields for:
- `schema_id`;
- `schema_version`;
- `kind`;
- `run_id`;
- `plan_revision`;
- payload, handoff, exchange, route, reply, result, work-item, sender, or receiver identifiers when the mail family needs them.

For `generic-loop` handoffs, include selected predecessor fields only when the execplan chooses them:
- predecessor or ancestor mail refs;
- artifact, branch, commit, state, or evidence refs;
- required context keys;
- compact summaries;
- current-hop deltas;
- expected receiver action;
- reply or forward policy.

When no predecessor context is needed for a non-obvious generic route, record the explicit omission in process, topology, comms overview, manifest, generated docs, or validation notes.

## Renderer Contracts

Generated Markdown renderers for templated mail include:
- a parseable in-body `houmao-email-metadata` fenced block near the top;
- `schema_id`, `schema_version`, `kind`, `run_id`, and `plan_revision`;
- route, payload, handoff, exchange, reply, result, work-item, sender, or receiver ids when applicable;
- a readable `Context` section when selected predecessor context exists;
- an explicit requested action and reply expectation when a reply or forward is expected.

Do not rely on subject text, sender identity, or hidden transport headers as the primary event type.

## Bookkeeping State Contracts

When durable bookkeeping is needed:

- apply the control-plane state, backend, and state-package defaults from `generated-contract-defaults.md`;
- emit only the entity families the generated loop needs;
- keep field-level authority in `schema.sql` or JSON schemas;
- keep README files to purpose and contents.

Default `specs/state/` package:

```text
specs/state/
  README.md
  state-overview.md
  schema.sql                 # sqlite default when SQL schema is clear
  seed.toml                  # when deterministic initialization is needed
  invariants.toml            # when validation needs named checks
  records/
    <record-family>.schema.json  # when JSONL or structured record payloads are emitted
```

`state-overview.md` must describe state authority, boundaries, minimal entity families, allowed transitions, invariants, scheduling queries, and what state must not store.

Consider these generic entity families and emit only the subset the loop needs:

- `process_state`
- `control_state`
- `participants`
- `work_items`
- `handoffs`
- `mail_payloads`
- `attempts`
- `decisions`
- `evidence`
- `artifacts`
- `operator_intent_events`
- `events`

For `generic-loop` loops with cycles or repeat visits, include compact facts for:
- lineage ids or parent refs;
- visited node or edge facts;
- cycle iteration counts;
- active ownership;
- message, handoff, exchange, result, and terminal refs.

## Control Contracts

When the loop has lifecycle or auto/manual control needs, derive control contracts from the process model:

- define `run_state`, with values such as `not_started`, `running`, `paused`, `recovering`, `stopped`, and `completed`, or an explicit equivalent;
- define `execution_mode`, normally `auto` and `manual` when both apply;
- default initial `execution_mode` to `auto` unless intention source or an accepted decision selects another initial mode;
- state that `manual` is not equivalent to `paused`;
- define which operator actions can change mode, pause, resume, stop, override, or enter recovery;
- define which state or record family stores operator intent events;
- define notifier-posture expectations for `auto` and `manual`;
- define which harness commands expose status, mode lookup, mode changes, and manual participant context.

Use state contracts for durable control facts when runtime state exists. If a simple loop intentionally has no durable state, record the equivalent control authority and validation surface in the manifest or generated docs.

## Generated TOML Style

For generated TOML contracts:

- apply the TOML defaults from `generated-contract-defaults.md`;
- include `description` fields for records exposed to agents, operators, or harness `--explain`;
- keep comments human-readable and non-authoritative.

## Workspace Contracts

When the process model requires managed workspaces, `workspace.toml` is the authority for workspace requirements. It should provide enough structured input for `prepare-workspace` to call `houmao-shared-routines->houmao-utils-workspace-mgr` without inventing topology, while still expecting `prepare-agents` to confirm concrete agent/profile facts before workspace creation or validation.

Include applicable fields:
- workspace flavor, defaulting to `in-repo` unless source selects another supported flavor;
- task name, repo root policy, and workspace root policy;
- launch cwd policy;
- task-local `shared-kb/` requirements for cross-run shared task knowledge;
- task-local `owner-states/<subdir>/...` requirements for per-run task-owner bookkeeping;
- per-agent `<task-root>/<agent-name>/states/` requirements for agent-local bookkeeping;
- per-agent `<task-root>/<agent-name>/repo/` worktree requirements for source mutation;
- project-scope validation command inputs, including explicit operator commands or documented safe project commands for tools such as Pixi, Python virtual environments, C or C++ build systems, package scripts, and in-project scripts;
- expected concrete agent workspace names and project profile names, or explicit raw launch profile fields that `prepare-agents` must resolve before `prepare-workspace`;
- per-agent work-root, shared-resource, memo-seed, and read/write requirements.
- manual workspace evidence fields required by `validate-loop` when the operator does not run `prepare-workspace`.

Use `description` fields for sections or records that agents, operators, or harness explanation commands may read.

Example shape:

```toml
# Workspace flavor and root policy used by prepare-workspace.
[workspace]
description = "Workspace requirements for this generated loop."
flavor = "in-repo"
task_name = "example-task"
repo_root = "auto"
ws_root = "houmao-ws"
launch_cwd_policy = "repo-root"

# Standard in-repo workspace-manager surfaces requested by this loop.
[workspace.shared_kb]
description = "Cross-run task knowledge requirements."
required = true

[workspace.owner_states]
description = "Per-run task-owner bookkeeping requirements."
required = true
subdir = "<run-id>"

[workspace.validation]
description = "Project-scope readiness checks to pass to workspace-manager validate."
commands = ["pixi run test"]

# Workspace needs for one concrete participant agent.
# The standard in-repo workspace maps this agent to <task-root>/agent-a/repo/
# for source mutation and <task-root>/agent-a/states/ for local bookkeeping.
[[workspace.agents]]
description = "Workspace requirements for agent-a."
agent_id = "agent-a"
easy_profile = "agent-a"
workspace_agent_name = "agent-a"
needs_worktree = true
needs_states = true
source_mutation_surface = "repo"
needs_memo_seed = true
```

Agent bindings later reference the relevant workspace policy; they do not replace this contract.

During execution, `prepare-workspace` combines this contract with prepared agent/profile facts from `prepare-agents`. If prepared facts differ from the generated contract, the workspace stage reports the inconsistency instead of inventing replacement names. If the operator uses manual workspace setup, `validate-loop` checks the manual evidence against the same contract before `launch-agents`.

Do not model standard in-repo workspace `runs/`, `artifacts/`, per-agent `artifacts/`, or ignored `tmp/` directories as Git-tracked workspace-manager surfaces. Represent durable loop execution artifacts under the loop run artifact layout, owner-managed workspace-local records under `owner-states/<subdir>/...`, agent-local workspace records under `<agent-name>/states/`, or an explicit custom operator-owned workspace contract.

## Downstream Effects

- Changes here invalidate harness, skills, agent bindings, final docs, and final manifest.

## Constraints

- Do not generate harness code, role skills, concrete agent configs, or final docs from this stage.
- Do not require a specific state backend unless the process model selects it.
- Do not create platform side effects.
- Do not define any contract that requires an agent to wait inside a chat turn for future work.
- Do not read a flat `execplan/specs/process.md` as the canonical process source; require the process stage to emit `execplan/specs/collab/collab-overview.md`.
