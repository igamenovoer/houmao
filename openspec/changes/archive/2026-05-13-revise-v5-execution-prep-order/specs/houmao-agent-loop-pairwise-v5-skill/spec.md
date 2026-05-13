## ADDED Requirements

### Requirement: V5 exposes validate-loop as the execution readiness gate
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `validate-loop` as an execution subcommand for checking whether a generated loop is ready to start.

`validate-loop` SHALL be distinct from `validate-execplan`.

`validate-loop` SHALL check concrete runtime preparation state, including prepared agent/profile identities, generated and maintained skill binding posture, prepared workspace facts, launch cwd and memo posture, mailbox/gateway/notifier readiness for mail-driven loops, harness availability, run artifact readiness, state initialization readiness, and no in-chat waiting posture when those facts apply.

`validate-loop` SHALL report blockers and warnings without mutating agent profiles, workspaces, mailboxes, gateways, harness state, or run artifacts as its normal behavior.

`start` SHALL require a current `validate-loop` pass or perform only a final lightweight readiness check before sending the first trigger.

#### Scenario: Validate-loop checks runtime readiness
- **WHEN** a user asks the loop skill to run `validate-loop` for a selected loop directory
- **THEN** the skill checks prepared agent/profile facts, workspace facts, mail/gateway/notifier posture, harness posture, and run artifact posture as applicable
- **AND THEN** it reports blockers without starting loop work

#### Scenario: Validate-loop is distinct from execplan validation
- **WHEN** generated execplan artifacts are structurally valid but concrete agents or workspaces are not prepared
- **THEN** `validate-execplan` can still pass
- **AND THEN** `validate-loop` reports runtime readiness blockers before `start`

#### Scenario: Start depends on loop readiness
- **WHEN** a user asks to start a generated loop
- **THEN** the start guidance requires a current `validate-loop` pass or repeats only essential final readiness checks
- **AND THEN** it does not silently repair missing agent, workspace, mailbox, gateway, harness, or run artifact preparation

## MODIFIED Requirements

### Requirement: V5 skill guidance is split into authoring and execution subskills
The top-level `houmao-agent-loop-pairwise-v5` skill SHALL act as an index and router for v5 subskills rather than carrying the whole workflow in one instruction file.

The packaged v5 skill SHALL include authoring subskills for creating intention material, refining intention material, generating execplans, validating execplans, and updating generated execplans.

The packaged v5 skill SHALL include execution subskills for preparing agents, preparing workspaces, validating loop readiness, starting a loop, checking status, pausing, resuming, recovering, and stopping.

Each subskill SHALL define its trigger, inputs, outputs, and boundaries.

#### Scenario: Top-level skill routes authoring work
- **WHEN** a user asks v5 to create, refine, generate, validate, or update generated loop material
- **THEN** the top-level skill routes to an authoring subskill
- **AND THEN** the authoring subskill handles the requested authoring operation within the selected `<loop-dir>`

#### Scenario: Top-level skill routes execution work
- **WHEN** a user asks v5 to prepare agents, prepare workspaces, validate loop readiness, start, inspect status, pause, resume, recover, or stop a loop
- **THEN** the top-level skill routes to an execution subskill
- **AND THEN** the execution subskill works from the generated `<loop-dir>/execplan/` and maintained Houmao operation surfaces

### Requirement: V5 exposes an independent prepare-workspace execution stage
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `prepare-workspace` as an execution subcommand for preparing or verifying multi-agent workspaces from generated execplan workspace contracts and prepared concrete agent/profile facts.

The `prepare-workspace` stage SHALL be separate from `prepare-agents`.

The skill SHALL document the normal ordered execution sequence as `prepare-agents`, `prepare-workspace`, `validate-loop`, then `start` when the generated execplan requires managed workspaces.

The `prepare-agents` stage SHALL run before `prepare-workspace` when managed workspace setup needs concrete agent or launch-profile names.

The `prepare-agents` stage SHALL NOT call, route to, create, repair, or execute `prepare-workspace`.

The `prepare-workspace` stage SHALL NOT call, route to, or perform `prepare-agents`.

#### Scenario: Agent preparation precedes managed workspace preparation
- **WHEN** a generated loop requires managed workspaces with concrete agent or launch-profile names
- **THEN** the normal execution order prepares agent/profile identities before workspace setup
- **AND THEN** workspace preparation uses those prepared facts as workspace-manager inputs

#### Scenario: Workspace stage is routed independently
- **WHEN** a user asks the loop skill to run `prepare-workspace` for a selected loop directory
- **THEN** the skill routes to a dedicated workspace-preparation execution subskill
- **AND THEN** that subskill does not install generated agent skills, create specialists, launch agents, or perform other `prepare-agents` responsibilities

#### Scenario: Preparation stages do not call each other
- **WHEN** a user asks the loop skill to run either `prepare-agents` or `prepare-workspace`
- **THEN** the selected stage performs only its own preparation responsibility
- **AND THEN** it does not call or route to the other preparation stage

### Requirement: V5 prepare-workspace delegates supported workspace setup to the workspace manager
The `prepare-workspace` execution subskill SHALL route supported Houmao workspace planning and execution through `houmao-utils-workspace-mgr`.

The `prepare-workspace` execution subskill SHALL adapt generated workspace contracts, generated agent bindings, and prepared concrete agent/profile facts into workspace-manager inputs.

The `prepare-workspace` execution subskill SHALL default to workspace-manager `plan` mode unless the user explicitly requests execution or has approved a current workspace plan.

The `prepare-workspace` execution subskill SHALL NOT implement ad hoc worktree, branch, shared repo, `.gitignore`, memo-seed, launch-profile cwd, local-state symlink, or submodule materialization mechanics when `houmao-utils-workspace-mgr` can represent the requested layout.

#### Scenario: Prepare-workspace uses prepared agent facts
- **WHEN** workspace-manager inputs require concrete agent or launch-profile names
- **THEN** `prepare-workspace` reads the prepared agent/profile facts produced by `prepare-agents`
- **AND THEN** it does not invent placeholder agent names independently of agent preparation

#### Scenario: Prepare-workspace plans before side effects by default
- **WHEN** a user asks `prepare-workspace` without explicitly asking to execute an approved plan
- **THEN** the skill uses workspace-manager plan mode
- **AND THEN** it reports the planned workspace organization without creating worktrees or changing launch profiles

#### Scenario: Prepare-workspace executes through workspace manager
- **WHEN** a user asks `prepare-workspace` to execute a supported workspace layout from an approved generated execplan and prepared agent facts
- **THEN** the skill uses `houmao-utils-workspace-mgr` execution guidance for the selected workspace flavor
- **AND THEN** it does not create the workspace by duplicating workspace-manager mechanics inside the loop skill

### Requirement: V5 prepare-workspace verifies workspace postconditions
After workspace planning or execution, the `prepare-workspace` execution subskill SHALL report workspace readiness facts and blockers relative to the generated execplan and prepared concrete agent/profile facts.

For executed standard workspace layouts, the subskill SHALL verify expected workspace contract docs, per-agent worktree paths, per-agent knowledge paths, shared knowledge paths, loop-requested bookkeeping directories, ignored transient paths, launch cwd posture, memo-seed files, and uniqueness of mutable per-agent workspace targets when those facts apply.

The `prepare-workspace` report SHALL distinguish ready facts, planned-but-not-executed facts, missing facts, and inconsistencies.

#### Scenario: Executed workspace is checked against prepared agents
- **WHEN** workspace-manager execution completes for a generated loop
- **THEN** `prepare-workspace` checks that the resulting workspace facts match the generated workspace contract, generated agent bindings, and prepared concrete agent/profile facts
- **AND THEN** it reports any missing worktrees, missing knowledge paths, missing bookkeeping directories, launch cwd mismatches, or conflicting mutable paths as blockers

#### Scenario: Plan-only run is not treated as ready execution
- **WHEN** `prepare-workspace` only produced a workspace-manager plan
- **THEN** the subskill reports the planned workspace facts as not yet executed
- **AND THEN** `validate-loop` treats workspace readiness as incomplete until the required facts exist or the execplan explicitly accepts plan-only/custom readiness

### Requirement: V5 validation checks workspace stage separation
The `validate-execplan` guidance SHALL check that generated workspace contracts route supported workspace setup through `houmao-utils-workspace-mgr` or an explicit operator-owned custom workspace contract.

The `validate-execplan` guidance SHALL check that generated lifecycle docs or generated operator guidance represent `prepare-agents`, `prepare-workspace`, `validate-loop`, and `start` as separate ordered stages when managed workspaces are required.

The `validate-execplan` guidance SHALL check that `prepare-agents` and `prepare-workspace` remain separate execution stages and do not call each other.

The `validate-execplan` guidance SHALL NOT require live agent/profile/workspace/mailbox/gateway readiness; those execution-readiness checks belong to `validate-loop`.

#### Scenario: Validation catches reversed generated stage order
- **WHEN** authoring validation finds generated lifecycle guidance that puts managed workspace preparation before concrete agent/profile preparation
- **THEN** validation reports the generated execution order as non-conforming
- **AND THEN** the plan is not considered conforming until the generated order is `prepare-agents`, `prepare-workspace`, `validate-loop`, then `start`

#### Scenario: Validation catches cross-stage coupling
- **WHEN** validation finds `prepare-agents` guidance that instructs the agent to create worktrees, run workspace-manager execution, or route to `prepare-workspace`
- **THEN** validation reports the execplan or skill guidance as non-conforming
- **AND THEN** the plan is not considered ready until workspace setup is represented by the independent `prepare-workspace` stage

#### Scenario: Execution readiness is checked by validate-loop
- **WHEN** concrete agent/profile/workspace/mailbox/gateway readiness is missing
- **THEN** `validate-execplan` does not treat that local runtime state as an authoring-time package-shape failure
- **AND THEN** `validate-loop` reports the runtime readiness blocker before `start`

#### Scenario: Validation accepts no-workspace loops
- **WHEN** a generated execplan explicitly does not require managed agent workspaces
- **THEN** validation does not require workspace-manager inputs for that loop
- **AND THEN** validation still accepts `prepare-workspace` as a no-op or verification-only stage when the omission is recorded in the manifest, docs, or validation notes
