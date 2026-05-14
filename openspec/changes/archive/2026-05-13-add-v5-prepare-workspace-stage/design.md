## Context

The loop skill already generates workspace contracts under `execplan/specs/workspace/` and agent bindings under `execplan/agents/`. Its execution guidance currently places workspace setup inside `prepare-agents`, while also saying workspace creation should be delegated to `houmao-utils-workspace-mgr`.

That coupling is awkward because workspace setup is a separate lifecycle concern:

- it may create Git worktrees and branches;
- it may create task and per-agent knowledge directories;
- it may update `.gitignore`;
- it may update launch-profile cwd values;
- it may create memo-seed files;
- it may create loop bookkeeping directories needed before agents run.

The loop skill should therefore expose `prepare-workspace` as a first-class execution stage. `prepare-agents` should treat workspace readiness as a precondition when the execplan requires workspace setup, but should not call or route to `prepare-workspace`.

## Goals / Non-Goals

**Goals:**

- Add an execution subskill page for `prepare-workspace`.
- Add top-level operation and routing entries for `prepare-workspace`.
- Make generated workspace contracts explicit enough to drive `houmao-utils-workspace-mgr`.
- Define the stage order as `prepare-workspace`, then `prepare-agents`, then `start` when workspaces are required.
- Revise `prepare-agents` to verify workspace readiness without creating, repairing, or routing workspace setup.
- Revise validation and generation guidance so workspace specs, bindings, and postconditions are coherent.
- Keep skill body wording generic; version labels should remain in file or skill names, not operational prose.

**Non-Goals:**

- Do not implement new workspace-manager functionality.
- Do not add ad hoc worktree, branch, or `.gitignore` mechanics to the loop skill.
- Do not make `prepare-workspace` launch agents or install generated agent skills.
- Do not make `prepare-agents` call `prepare-workspace`.
- Do not change the Houmao mail runtime model.

## Decisions

### Add `prepare-workspace` As An Independent Execution Stage

`prepare-workspace` should be a sibling of `prepare-agents`, not a helper called by it.

The intended operator order is:

```text
prepare-workspace
prepare-agents
start
```

If a loop does not require managed workspaces, `prepare-workspace` can report that no workspace setup is required or validate custom/operator-owned workspace facts when the execplan defines them.

Alternative considered: keep workspace setup inside `prepare-agents`. This hides significant filesystem and Git side effects behind agent preparation and makes approval/recovery harder.

### Route Supported Workspace Creation Through `houmao-utils-workspace-mgr`

The new execution page should adapt generated workspace contracts into workspace-manager inputs. It should not directly create worktrees, branches, symlinks, shared repos, memo seeds, or launch-profile cwd updates when the workspace manager can represent the requested layout.

The subskill should pass or recover these inputs:

- operation: `plan` or `execute`;
- workspace flavor: default `in-repo`, unless the execplan or operator selects another supported flavor;
- task name;
- workspace root or repo root;
- concrete agent names;
- launch profile names;
- loop-requested bookkeeping directories;
- memo-seed preference;
- launch-profile adjustment preference.

Alternative considered: copy workspace-manager rules into the loop skill. This would duplicate maintained platform behavior and drift from the workspace manager.

### Keep Workspace Specs And Agent Bindings Separate But Linked

Generated workspace specs should describe workspace requirements. Generated agent bindings should map participant instances to concrete Houmao agent/profile names and point to their workspace policy.

Recommended generated shape:

```text
execplan/specs/workspace/
  README.md
  workspace.toml

execplan/agents/
  README.md
  bindings.toml
```

`workspace.toml` should include enough structured fields for planning:

```toml
[workspace]
description = "Workspace requirements for this loop."
flavor = "in-repo"
task_name = "example-task"
repo_root = "auto"
ws_root = "houmao-ws"

[workspace.bookkeeping]
description = "Loop-owned bookkeeping paths requested by the execplan."
task_dirs = ["runs", "artifacts"]
per_agent_dirs = ["artifacts"]
per_agent_ignored_dirs = ["tmp"]

[[workspace.agents]]
description = "Workspace requirements for one concrete participant agent."
agent_id = "agent-a"
launch_profile = "agent-a"
workspace_agent_name = "agent-a"
needs_worktree = true
needs_kb = true
needs_memo_seed = true
```

`bindings.toml` should not replace the workspace spec, but should reference its policy:

```toml
[[bindings]]
participant = "reviewer"
agent_id = "agent-a"
launch_profile = "agent-a"
workspace_policy = "workspace.agents.agent-a"
```

Alternative considered: store all workspace facts in `bindings.toml`. That makes agent bindings too broad and weakens the separation between workspace requirements and concrete agent setup.

### Use Plan-Then-Execute Semantics For Workspace Side Effects

`prepare-workspace` should default to a workspace-manager `plan` unless the user explicitly asks for execution or has already approved a current plan. Execution should produce a concise report of created/updated paths and unresolved blockers.

This mirrors the existing workspace manager's model and gives the operator a review point before Git and launch-profile changes.

Alternative considered: always execute immediately. That is faster but too risky for workspace topology changes.

### Validate Workspace Postconditions Before Later Stages

After `prepare-workspace`, the skill should verify that generated expectations match actual workspace facts where feasible:

- workspace contract docs exist;
- per-agent worktrees exist when required;
- per-agent knowledge directories exist when required;
- shared knowledge paths exist when required;
- loop bookkeeping directories exist;
- ignored transient paths are covered by ignore rules;
- launch-profile cwd changes match the selected workspace flavor when profiles were adjusted;
- memo-seed files exist when requested;
- no two agents are assigned the same mutable worktree or private knowledge directory.

`prepare-agents` should check the same readiness surface only as a precondition. If facts are missing, it should stop and report missing `prepare-workspace` postconditions. It should not invoke or repair workspace setup.

Alternative considered: let `prepare-agents` repair missing workspace facts. That blurs stage ownership and makes execution less predictable.

### Update Validation And Design Docs

Validation guidance should check:

- `prepare-workspace` exists in operations and routing;
- workspace specs are explicit enough for workspace-manager inputs;
- workspace creation is not implemented by generated harnesses or generated skills;
- `prepare-workspace` and `prepare-agents` do not call each other;
- `prepare-agents` reports missing workspace readiness as a blocker.

Developer design docs should describe the stage boundary so future edits preserve the separation.

## Risks / Trade-offs

- Separate stage adds one more operator command → Mitigation: document the normal execution order clearly and allow `prepare-workspace` to be a no-op/verification stage when no managed workspace is required.
- Workspace spec may still be under-specified in generated plans → Mitigation: add validation checks and concrete field expectations for workspace-manager inputs.
- Existing `prepare-agents` text may continue to imply workspace creation → Mitigation: rewrite the relevant steps to precondition checks only.
- Workspace-manager plans may expose choices not represented in the generated workspace spec → Mitigation: let `prepare-workspace` report selected decisions and require consistency with generated bindings before later stages.
