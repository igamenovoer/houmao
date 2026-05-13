# Execplan Specs Contract

## Read First

- `../reference/generation-pipeline.md`
- `../reference/generated-contract-defaults.md`
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
6. For mail-driven loops, derive notifier prompt contracts from the process model, including which on-event skill handles each received message family and which on-tick skill runs after mail when required.
7. For controllable loops, derive run lifecycle state, execution mode, operator intent events, mode-switch rules, and notifier-posture expectations.
8. When managed workspaces are needed, generate workspace-manager inputs under `execplan/specs/workspace/workspace.toml`.
9. Generate task-specific records only when intention or process specs introduce them.
10. Record explicit omissions for irrelevant default layers.

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

When the process model requires managed workspaces, `workspace.toml` is the authority for workspace requirements. It should provide enough structured input for `prepare-workspace` to call `houmao-utils-workspace-mgr` without inventing topology, while still expecting `prepare-agents` to confirm concrete agent/profile facts before workspace execution.

Include applicable fields:
- workspace flavor, defaulting to `in-repo` unless source selects another supported flavor;
- task name, repo root policy, and workspace root policy;
- launch cwd policy;
- loop-requested bookkeeping directories, including durable task/agent artifact paths and ignored transient paths;
- expected concrete agent workspace names and launch profile names, or the fields that `prepare-agents` must resolve before `prepare-workspace`;
- per-agent work-root, knowledge-path, shared-resource, memo-seed, and read/write requirements.
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

# Loop-owned directories requested from the workspace manager.
[workspace.bookkeeping]
description = "Durable and transient loop bookkeeping paths."
task_dirs = ["runs", "artifacts"]
per_agent_dirs = ["artifacts"]
per_agent_ignored_dirs = ["tmp"]

# Workspace needs for one concrete participant agent.
[[workspace.agents]]
description = "Workspace requirements for agent-a."
agent_id = "agent-a"
launch_profile = "agent-a"
workspace_agent_name = "agent-a"
needs_worktree = true
needs_kb = true
needs_memo_seed = true
```

Agent bindings later reference the relevant workspace policy; they do not replace this contract.

During execution, `prepare-workspace` combines this contract with prepared agent/profile facts from `prepare-agents`. If prepared facts differ from the generated contract, the workspace stage reports the inconsistency instead of inventing replacement names. If the operator uses manual workspace setup, `validate-loop` checks the manual evidence against the same contract before `launch-agents`.

## Downstream Effects

- Changes here invalidate harness, skills, agent bindings, final docs, and final manifest.

## Constraints

- Do not generate harness code, role skills, concrete agent configs, or final docs from this stage.
- Do not require a specific state backend unless the process model selects it.
- Do not create platform side effects.
- Do not define any contract that requires an agent to wait inside a chat turn for future work.
- Do not read a flat `execplan/specs/process.md` as the canonical process source; require the process stage to emit `execplan/specs/collab/collab-overview.md`.
