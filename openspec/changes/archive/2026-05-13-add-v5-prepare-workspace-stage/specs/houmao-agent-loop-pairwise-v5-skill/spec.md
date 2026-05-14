## ADDED Requirements

### Requirement: V5 exposes an independent prepare-workspace execution stage
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `prepare-workspace` as an execution subcommand for preparing or verifying multi-agent workspaces from generated execplan workspace contracts.

The `prepare-workspace` stage SHALL be separate from `prepare-agents`.

The skill SHALL document the normal ordered execution sequence as `prepare-workspace`, `prepare-agents`, then `start` when the generated execplan requires managed workspaces.

The `prepare-workspace` stage SHALL NOT call, route to, or perform `prepare-agents`.

The `prepare-agents` stage SHALL NOT call, route to, create, repair, or execute `prepare-workspace`.

#### Scenario: Workspace stage is routed independently
- **WHEN** a user asks the loop skill to run `prepare-workspace` for a selected loop directory
- **THEN** the skill routes to a dedicated workspace-preparation execution subskill
- **AND THEN** that subskill does not install generated agent skills, create specialists, launch agents, or perform other `prepare-agents` responsibilities

#### Scenario: Agent preparation does not invoke workspace preparation
- **WHEN** a user asks the loop skill to run `prepare-agents`
- **AND WHEN** the generated execplan requires workspace readiness
- **THEN** the `prepare-agents` guidance checks workspace readiness as a precondition
- **AND THEN** it stops with missing workspace postconditions when the workspace is not ready instead of calling `prepare-workspace`

### Requirement: V5 generated workspace contracts provide workspace-manager inputs
When a generated loop needs managed agent workspaces, the packaged skill SHALL guide execplan generation to emit workspace contracts that provide enough structured information for `houmao-utils-workspace-mgr` planning and execution.

Generated workspace contracts SHALL identify the workspace flavor, task name, workspace root or repo root policy, concrete agent workspace names, launch profile names, launch cwd policy, required per-agent work roots, required per-agent note or knowledge paths, shared resources, loop-requested bookkeeping directories, ignored transient paths, and memo-seed posture when those facts apply.

Generated agent bindings SHALL keep concrete participant-to-agent/profile mapping under the agent binding area and SHALL reference the applicable workspace policy instead of replacing the workspace contract.

#### Scenario: Workspace contract can drive workspace planning
- **WHEN** a generated execplan requires standard managed workspaces
- **THEN** `execplan/specs/workspace/workspace.toml` contains structured workspace-manager inputs for flavor, task name, agent workspace names, launch profile names, cwd policy, and bookkeeping directories
- **AND THEN** `execplan/agents/bindings.toml` maps participant instances to concrete agents and references the relevant workspace policy

#### Scenario: Workspace facts are not hidden in agent bindings only
- **WHEN** generated agent bindings identify concrete agents and launch profiles
- **THEN** workspace requirements remain authoritative in the generated workspace contract
- **AND THEN** the bindings refer to that workspace policy rather than becoming the only source of workspace behavior

### Requirement: V5 prepare-workspace delegates supported workspace setup to the workspace manager
The `prepare-workspace` execution subskill SHALL route supported Houmao workspace planning and execution through `houmao-utils-workspace-mgr`.

The `prepare-workspace` execution subskill SHALL adapt generated workspace contracts and generated agent bindings into workspace-manager inputs.

The `prepare-workspace` execution subskill SHALL default to workspace-manager `plan` mode unless the user explicitly requests execution or has approved a current workspace plan.

The `prepare-workspace` execution subskill SHALL NOT implement ad hoc worktree, branch, shared repo, `.gitignore`, memo-seed, launch-profile cwd, local-state symlink, or submodule materialization mechanics when `houmao-utils-workspace-mgr` can represent the requested layout.

#### Scenario: Prepare-workspace plans before side effects by default
- **WHEN** a user asks `prepare-workspace` without explicitly asking to execute an approved plan
- **THEN** the skill uses workspace-manager plan mode
- **AND THEN** it reports the planned workspace organization without creating worktrees or changing launch profiles

#### Scenario: Prepare-workspace executes through workspace manager
- **WHEN** a user asks `prepare-workspace` to execute a supported workspace layout from an approved generated execplan
- **THEN** the skill uses `houmao-utils-workspace-mgr` execution guidance for the selected workspace flavor
- **AND THEN** it does not create the workspace by duplicating workspace-manager mechanics inside the loop skill

### Requirement: V5 prepare-workspace verifies workspace postconditions
After workspace planning or execution, the `prepare-workspace` execution subskill SHALL report workspace readiness facts and blockers relative to the generated execplan.

For executed standard workspace layouts, the subskill SHALL verify expected workspace contract docs, per-agent worktree paths, per-agent knowledge paths, shared knowledge paths, loop-requested bookkeeping directories, ignored transient paths, launch cwd posture, memo-seed files, and uniqueness of mutable per-agent workspace targets when those facts apply.

The `prepare-workspace` report SHALL distinguish ready facts, planned-but-not-executed facts, missing facts, and inconsistencies.

#### Scenario: Executed workspace is checked against generated bindings
- **WHEN** workspace-manager execution completes for a generated loop
- **THEN** `prepare-workspace` checks that the resulting workspace facts match the generated workspace contract and agent bindings
- **AND THEN** it reports any missing worktrees, missing knowledge paths, missing bookkeeping directories, launch cwd mismatches, or conflicting mutable paths as blockers

#### Scenario: Plan-only run is not treated as ready execution
- **WHEN** `prepare-workspace` only produced a workspace-manager plan
- **THEN** the subskill reports the planned workspace facts as not yet executed
- **AND THEN** later execution stages can treat workspace readiness as incomplete until the required facts exist or the execplan explicitly accepts plan-only/custom readiness

### Requirement: V5 validation checks workspace stage separation
The `validate-execplan` guidance SHALL check that generated workspace contracts route supported workspace setup through `houmao-utils-workspace-mgr` or an explicit operator-owned custom workspace contract.

The `validate-execplan` guidance SHALL check that `prepare-workspace` and `prepare-agents` remain separate execution stages and do not call each other.

The `validate-execplan` guidance SHALL check that `prepare-agents` treats missing required workspace readiness as a blocker instead of creating or repairing workspaces.

#### Scenario: Validation catches cross-stage coupling
- **WHEN** validation finds `prepare-agents` guidance that instructs the agent to create worktrees, run workspace-manager execution, or route to `prepare-workspace`
- **THEN** validation reports the execplan or skill guidance as non-conforming
- **AND THEN** the plan is not considered ready until workspace setup is represented by the independent `prepare-workspace` stage

#### Scenario: Validation accepts no-workspace loops
- **WHEN** a generated execplan explicitly does not require managed agent workspaces
- **THEN** validation does not require workspace-manager inputs for that loop
- **AND THEN** validation still accepts `prepare-workspace` as a no-op or verification-only stage when the omission is recorded in the manifest, docs, or validation notes
