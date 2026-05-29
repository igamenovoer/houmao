## ADDED Requirements

### Requirement: Pro prepare-workspace routes current workspace-manager operations
The pro `prepare-workspace` guidance SHALL adapt generated workspace contracts, generated agent bindings, and prepared agent/profile facts into `houmao-utils-workspace-mgr` operations named `plan`, `create`, `validate`, and `summarize`.

The pro `prepare-workspace` guidance SHALL default to workspace-manager `plan` when the operator has not explicitly requested workspace mutation and has not approved a current workspace plan.

The pro `prepare-workspace` guidance SHALL route mutating workspace setup through workspace-manager `create`.

The pro `prepare-workspace` guidance SHALL route prepared-workspace readiness checks through workspace-manager `validate` when a standard Houmao workspace is used and validation evidence is needed.

The pro `prepare-workspace` guidance SHALL use workspace-manager `summarize` or an equivalent current workspace-manager report when downstream stages need compact prepared-workspace facts.

The pro `prepare-workspace` guidance MAY accept `execute` only as legacy generated material or legacy operator wording for workspace setup, and SHALL normalize that operation to `create` in new reports and guidance.

#### Scenario: Pro plans before mutation
- **WHEN** `prepare-workspace` has generated workspace requirements but the operator has not approved creation
- **THEN** it routes the workspace-manager request as `plan`
- **AND THEN** it reports planned workspace facts without treating workspace readiness as complete

#### Scenario: Pro creates through workspace manager
- **WHEN** the operator approves a standard Houmao workspace setup
- **THEN** `prepare-workspace` routes the mutating setup through workspace-manager `create`
- **AND THEN** it does not create worktrees, local-state links, submodules, memo seeds, or launch-profile cwd updates by hand

#### Scenario: Pro validates prepared workspace
- **WHEN** a standard Houmao workspace has been created or supplied and readiness evidence is required
- **THEN** `prepare-workspace` routes readiness checks through workspace-manager `validate`
- **AND THEN** the resulting workspace facts distinguish validation successes, validation failures, skipped checks, missing readiness facts, and follow-up actions

#### Scenario: Execute is normalized as legacy wording
- **WHEN** older generated material or operator wording asks `prepare-workspace` to use workspace-manager `execute`
- **THEN** pro guidance treats that as a request for workspace-manager `create`
- **AND THEN** new reports do not expose `execute` as a separate behavior path

### Requirement: Pro generated workspace contracts use standard workspace-manager surfaces
Generated pro workspace contracts SHALL express standard in-repo workspace requirements using the workspace-manager task root under `<repo-root>/houmao-ws/<task-name>`.

For standard in-repo workspaces, generated pro workspace contracts SHALL identify `<task-root>/shared-kb/` as cross-run shared task knowledge when shared task knowledge is needed.

For standard in-repo workspaces, generated pro workspace contracts SHALL identify `<task-root>/owner-states/<subdir>/...` as per-run task-owner bookkeeping when task-owner run state, reports, coordination records, or owner-managed evidence are needed.

For standard in-repo workspaces, generated pro workspace contracts SHALL identify `<task-root>/<agent-name>/states/` as per-agent local bookkeeping when participant-local notes, scratch state, or agent-owned evidence are needed.

Generated pro workspace contracts SHALL identify each agent's private source-mutation surface as the workspace-manager-provided per-agent `repo/` worktree when a standard in-repo workspace is selected.

Generated pro workspace contracts SHALL include explicit workspace-manager validation inputs when project-scope readiness commands are known, including operator-provided commands, documented project commands, or safe command references for tools such as Pixi, Python virtual environments, C or C++ build systems, package scripts, or in-project scripts.

Generated pro workspace contracts SHALL NOT model standard in-repo workspace `runs/`, `artifacts/`, per-agent `artifacts/`, or ignored `tmp/` directories as Git-tracked workspace-manager surfaces. Such needs SHALL be represented as loop run artifacts under the loop directory, task-owner state under `owner-states/<subdir>/...`, per-agent state under `<agent-name>/states/`, or explicit custom operator-owned workspace material.

#### Scenario: Standard in-repo workspace contract names current surfaces
- **WHEN** pro generates a standard in-repo workspace contract for a loop that needs shared task knowledge and run-owner bookkeeping
- **THEN** the contract names `<task-root>/shared-kb/` for cross-run shared knowledge
- **AND THEN** it names `<task-root>/owner-states/<subdir>/...` for per-run task-owner bookkeeping
- **AND THEN** it names each participant's `<task-root>/<agent-name>/states/` for per-agent local bookkeeping when needed

#### Scenario: Project readiness commands are passed to workspace validate
- **WHEN** a generated pro workspace contract knows the project command that proves a worktree is ready
- **THEN** the contract records that command as workspace-manager validation input
- **AND THEN** `prepare-workspace` can route it to workspace-manager `validate` instead of inventing a command

#### Scenario: Old artifact directory examples are not standard workspace surfaces
- **WHEN** a loop needs durable run artifacts or temporary participant scratch paths
- **THEN** generated pro guidance records them under loop run artifacts, owner state, agent state, or a custom workspace contract
- **AND THEN** it does not describe those paths as automatically tracked standard in-repo workspace-manager directories

### Requirement: Pro validation distinguishes workspace readiness evidence
Pro generated execplan validation guidance SHALL check that supported standard workspace setup routes planning, creation, validation, and summaries through `prepare-workspace` and `houmao-utils-workspace-mgr`.

Pro `validate-loop` guidance SHALL treat workspace readiness as complete only when the available evidence satisfies the generated workspace contract and includes a created standard workspace plus current validation evidence, an accepted workspace-manager summary/report, or explicit equivalent manual evidence.

Pro `validate-loop` guidance SHALL NOT treat a workspace-manager `plan` report alone as launch-ready workspace evidence.

Pro validation and reporting guidance SHALL distinguish planned, created, validated, summarized, missing, inconsistent, and custom/manual workspace facts.

Pro platform-boundary guidance SHALL identify `houmao-utils-workspace-mgr` as the owner of standard workspace planning, creation, validation, and summaries, while keeping generated loop material responsible only for loop-local requirements and evidence comparison.

#### Scenario: Planned workspace is not launch-ready
- **WHEN** `prepare-workspace` has only produced a workspace-manager plan
- **THEN** `validate-loop` reports workspace readiness as incomplete for managed workspace launches
- **AND THEN** it identifies the missing create or validation evidence needed before `launch-agents`

#### Scenario: Validated workspace satisfies readiness
- **WHEN** workspace-manager `validate` reports that required worktrees, local-state links, submodules, launch cwd posture, and project-scope commands are ready
- **THEN** pro `validate-loop` may treat the managed workspace requirement as satisfied
- **AND THEN** later stages can consume the validation report or workspace summary without restating the full workspace contract

#### Scenario: Custom workspace evidence remains explicit
- **WHEN** a generated execplan selects a custom operator-owned workspace instead of a standard workspace-manager layout
- **THEN** pro validation checks explicit manual readiness evidence against the generated custom contract
- **AND THEN** it does not translate that custom layout into a standard workspace-manager lane
