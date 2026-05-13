## ADDED Requirements

### Requirement: V5 exposes launch-agents as the live launch stage
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `launch-agents` as an execution subcommand for launching prepared loop participants before loop start.

The normal execution sequence SHALL be `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence when required, `validate-loop`, `launch-agents`, then `start`.

The `launch-agents` subcommand SHALL read generated agent bindings, prepared agent/profile facts, workspace readiness facts or accepted manual equivalents, launch cwd posture, memo posture, notifier prompt posture, and generated run contracts when those facts apply.

The `launch-agents` subcommand SHALL launch missing live agents only through maintained Houmao launch surfaces such as `houmao-agent-instance` or supported easy-instance launch workflows.

The `launch-agents` subcommand SHALL verify and report live-agent or session facts for every required participant after launch.

The `launch-agents` subcommand SHALL NOT create or repair profiles, install generated skills, prepare workspaces, repair mailbox/gateway posture, mutate harness state, send loop-start work, or deliver the first loop trigger as its normal behavior.

#### Scenario: Launch-agents launches prepared participants
- **WHEN** a user asks v5 to run `launch-agents` for a generated loop with prepared profiles and validated pre-launch readiness
- **THEN** the skill launches required missing agents through maintained Houmao launch surfaces
- **AND THEN** it reports the live-agent/session facts needed by `start`

#### Scenario: Launch-agents does not begin loop work
- **WHEN** `launch-agents` starts managed agents successfully
- **THEN** it does not send the generated first work prompt or mail trigger
- **AND THEN** the loop remains unstarted until the user runs `start`

#### Scenario: Launch-agents blocks missing preparation
- **WHEN** required prepared profile facts, workspace readiness facts, launch cwd posture, or notifier prompt posture are missing
- **THEN** `launch-agents` reports the missing preparation
- **AND THEN** it does not repair those facts or start partially prepared agents as the normal path

### Requirement: V5 start begins loop work only after agents are live
The packaged `houmao-agent-loop-pairwise-v5` `start` execution subcommand SHALL treat live agents as a precondition for delivering the first loop trigger.

The `start` subcommand SHALL require a current `launch-agents` report or equivalent live-agent/session facts before sending loop-start work.

The `start` subcommand SHALL perform only a final lightweight liveness and start-trigger readiness check before initializing start-time runtime state and delivering the first generated trigger.

The `start` subcommand SHALL NOT launch agents, create or repair profiles, install skills, prepare workspaces, or perform full readiness validation as its normal behavior.

#### Scenario: Start sends first trigger after launch
- **WHEN** `launch-agents` has launched all required participants and reported live-agent facts
- **THEN** `start` can perform a final lightweight check
- **AND THEN** it sends the generated first loop trigger through the generated start contract and maintained communication surfaces

#### Scenario: Start blocks without live agents
- **WHEN** a user asks `start` but required participants are not live and no equivalent live-agent facts are available
- **THEN** `start` reports that `launch-agents` is required
- **AND THEN** it does not launch agents or send loop-start work

## MODIFIED Requirements

### Requirement: V5 skill guidance is split into authoring and execution subskills
The top-level `houmao-agent-loop-pairwise-v5` skill SHALL act as an index and router for v5 subskills rather than carrying the whole workflow in one instruction file.

The packaged v5 skill SHALL include authoring subskills for creating intention material, refining intention material, generating execplans, validating execplans, and updating generated execplans.

The packaged v5 skill SHALL include execution subskills for preparing agents, preparing workspaces or accepting equivalent manual workspace readiness evidence, validating loop readiness, launching agents, starting a loop, checking status, pausing, resuming, recovering, and stopping.

Each subskill SHALL define its trigger, inputs, outputs, and boundaries.

#### Scenario: Top-level skill routes authoring work
- **WHEN** a user asks v5 to create, refine, generate, validate, or update generated loop material
- **THEN** the top-level skill routes to an authoring subskill
- **AND THEN** the authoring subskill handles the requested authoring operation within the selected `<loop-dir>`

#### Scenario: Top-level skill routes execution work
- **WHEN** a user asks v5 to prepare agents, prepare workspaces, validate loop readiness, launch agents, start, inspect status, pause, resume, recover, or stop a loop
- **THEN** the top-level skill routes to an execution subskill
- **AND THEN** the execution subskill works from the generated `<loop-dir>/execplan/` and maintained Houmao operation surfaces

### Requirement: V5 execution uses generated execplan material and maintained Houmao operation surfaces
The v5 execution workflow SHALL operate from the generated `<loop-dir>/execplan/` package.

When execution needs platform operations such as managed-agent launch, prompt delivery, mailbox work, gateway work, memory work, lifecycle control, or inspection, the v5 execution subskills SHALL route through maintained Houmao operation skills or CLI surfaces rather than duplicating those contracts locally.

When execution needs loop-local state or generated role behavior, the v5 execution subskills SHALL use the generated execplan contracts, generated skills, generated agent bindings, generated docs, or generated harness surfaces.

Agent preparation SHALL create or update the concrete launchable agent/profile posture required by generated agent bindings.

Agent launch SHALL be owned by `launch-agents`, which uses maintained Houmao launch surfaces and does not send loop-start work.

Loop begin SHALL be owned by `start`, which uses generated start contracts and maintained communication surfaces to deliver the first loop trigger after required agents are live.

#### Scenario: Agent preparation composes existing Houmao surfaces
- **WHEN** a v5 execution subskill prepares agents for a generated execplan
- **THEN** it uses maintained Houmao specialist, mailbox, gateway, memory, or project-skill surfaces as appropriate
- **AND THEN** it does not hand-edit Houmao runtime internals or launch agents as the normal preparation path

#### Scenario: Launch composes existing Houmao surfaces
- **WHEN** a v5 execution subskill launches prepared agents for a generated execplan
- **THEN** it uses maintained Houmao instance or supported easy-instance launch surfaces
- **AND THEN** it does not duplicate managed-agent launch mechanics locally

#### Scenario: Loop-local execution consults execplan
- **WHEN** a v5 execution subskill needs loop role instructions or loop-local runtime behavior
- **THEN** it reads or invokes the relevant generated material under `<loop-dir>/execplan/`
- **AND THEN** it does not treat freeform intention Markdown as the direct runtime contract

### Requirement: V5 exposes an independent prepare-workspace execution stage
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `prepare-workspace` as an execution subcommand for preparing or verifying multi-agent workspaces from generated execplan workspace contracts and prepared concrete agent/profile facts.

The `prepare-workspace` stage SHALL be separate from `prepare-agents`.

The skill SHALL document the normal ordered execution sequence as `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence when required, `validate-loop`, `launch-agents`, then `start`.

The `prepare-agents` stage SHALL run before `prepare-workspace` when managed workspace setup needs concrete agent or launch-profile names.

The `prepare-agents` stage SHALL NOT call, route to, create, repair, execute `prepare-workspace`, or launch live agents as the normal preparation path.

The `prepare-workspace` stage SHALL NOT call, route to, or perform `prepare-agents`.

#### Scenario: Agent preparation precedes managed workspace preparation
- **WHEN** a generated loop requires managed workspaces with concrete agent or launch-profile names
- **THEN** the normal execution order prepares agent/profile identities before workspace setup
- **AND THEN** workspace preparation uses those prepared facts as workspace-manager inputs

#### Scenario: Workspace stage is routed independently
- **WHEN** a user asks the loop skill to run `prepare-workspace` for a selected loop directory
- **THEN** the skill routes to a dedicated workspace-preparation execution subskill
- **AND THEN** that subskill does not install generated agent skills, create specialists, launch agents, or perform other `prepare-agents` responsibilities

#### Scenario: Manual workspace setup can supply equivalent readiness evidence
- **WHEN** a generated loop requires workspace readiness and the user chooses not to run `prepare-workspace`
- **THEN** later readiness validation may accept explicit manual workspace facts that satisfy the generated workspace contract
- **AND THEN** the skill does not require the `prepare-workspace` command itself when equivalent evidence exists

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

Equivalent manual workspace evidence SHALL distinguish the same ready, missing, and inconsistent facts when the generated execplan requires workspace readiness but the user did not run `prepare-workspace`.

#### Scenario: Executed workspace is checked against prepared agents
- **WHEN** workspace-manager execution completes for a generated loop
- **THEN** `prepare-workspace` checks that the resulting workspace facts match the generated workspace contract, generated agent bindings, and prepared concrete agent/profile facts
- **AND THEN** it reports any missing worktrees, missing knowledge paths, missing bookkeeping directories, launch cwd mismatches, or conflicting mutable paths as blockers

#### Scenario: Plan-only run is not treated as ready execution
- **WHEN** `prepare-workspace` only produced a workspace-manager plan
- **THEN** the subskill reports the planned workspace facts as not yet executed
- **AND THEN** `validate-loop` treats workspace readiness as incomplete until the required facts exist or the execplan explicitly accepts plan-only/custom readiness

#### Scenario: Manual workspace facts are validated as evidence
- **WHEN** the user provides manual workspace readiness facts instead of a `prepare-workspace` report
- **THEN** `validate-loop` checks those facts against generated workspace contracts and prepared agent/profile facts
- **AND THEN** missing or inconsistent facts block `launch-agents`

### Requirement: V5 validation checks workspace stage separation
The `validate-execplan` guidance SHALL check that generated workspace contracts route supported workspace setup through `houmao-utils-workspace-mgr` or an explicit operator-owned custom workspace contract.

The `validate-execplan` guidance SHALL check that generated lifecycle docs or generated operator guidance represent `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence when required, `validate-loop`, `launch-agents`, and `start` as separate ordered stages.

The `validate-execplan` guidance SHALL check that `prepare-agents` and `prepare-workspace` remain separate execution stages and do not call each other.

The `validate-execplan` guidance SHALL check that `launch-agents` and `start` remain separate execution stages, where `launch-agents` launches live agents and `start` sends the first loop trigger.

The `validate-execplan` guidance SHALL NOT require live agent/profile/workspace/mailbox/gateway readiness; those execution-readiness checks belong to `validate-loop` and `launch-agents`.

#### Scenario: Validation catches missing launch stage
- **WHEN** authoring validation finds generated lifecycle guidance that sends first loop work from a stage that also launches agents
- **THEN** validation reports the generated execution stages as non-conforming
- **AND THEN** the plan is not considered conforming until launch and start are represented as separate stages

#### Scenario: Validation catches reversed generated stage order
- **WHEN** authoring validation finds generated lifecycle guidance that puts managed workspace preparation before concrete agent/profile preparation
- **THEN** validation reports the generated execution order as non-conforming
- **AND THEN** the plan is not considered conforming until the generated order is `prepare-agents`, workspace readiness, `validate-loop`, `launch-agents`, then `start`

#### Scenario: Validation catches cross-stage coupling
- **WHEN** validation finds `prepare-agents` guidance that instructs the agent to create worktrees, run workspace-manager execution, launch live agents, or route to `prepare-workspace`
- **THEN** validation reports the execplan or skill guidance as non-conforming
- **AND THEN** the plan is not considered ready until workspace setup and live launch are represented by their independent stages

#### Scenario: Execution readiness is checked by validate-loop and launch-agents
- **WHEN** concrete agent/profile/workspace/mailbox/gateway readiness is missing
- **THEN** `validate-execplan` does not treat that local runtime state as an authoring-time package-shape failure
- **AND THEN** `validate-loop` or `launch-agents` reports the runtime readiness blocker before `start`

#### Scenario: Validation accepts no-workspace loops
- **WHEN** a generated execplan explicitly does not require managed agent workspaces
- **THEN** validation does not require workspace-manager inputs for that loop
- **AND THEN** validation still accepts `prepare-workspace` as a no-op or verification-only stage when the omission is recorded in the manifest, docs, or validation notes
