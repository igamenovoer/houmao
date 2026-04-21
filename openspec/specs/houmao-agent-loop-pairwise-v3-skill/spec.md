# houmao-agent-loop-pairwise-v3-skill Specification

## Purpose
Define the packaged workspace-aware pairwise-v3 skill as the extension of pairwise-v2 that adds an authored workspace contract without collapsing runtime-owned recovery boundaries into workspace bookkeeping.

## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v3` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise-v3` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise-v3` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The packaged `houmao-agent-loop-pairwise-v3` skill SHALL be the workspace-aware extension of `houmao-agent-loop-pairwise-v2` rather than a replacement for the stable pairwise skill or a mutation of v2 in place.

#### Scenario: Reader sees v3 as a new packaged skill
- **WHEN** a reader inspects the packaged loop-skill assets
- **THEN** the inventory includes `houmao-agent-loop-pairwise-v3`
- **AND THEN** the skill is described as the workspace-aware extension of pairwise-v2

### Requirement: Pairwise-v3 plans declare standard or custom workspace contracts
The authoring guidance in `houmao-agent-loop-pairwise-v3` SHALL require the authored run contract to include a workspace contract.

The workspace contract SHALL declare one mode:

- `standard`
- `custom`

When the workspace contract uses `standard`, the plan SHALL identify the selected standard posture and any required values such as `task-name` for in-repo mode.

When the workspace contract uses `custom`, the plan SHALL identify explicit operator-owned paths and rules for the run, including launch cwd, writable source paths, shared writable paths when applicable, bookkeeping paths, and ad hoc worktree posture.

#### Scenario: Standard workspace contract is recorded in v3 plan
- **WHEN** a user authors a pairwise-v3 plan that uses Houmao's standardized workspace
- **THEN** the authored plan records a `standard` workspace contract
- **AND THEN** it identifies the selected standard posture and any required task-scoping fields

#### Scenario: Custom workspace contract is recorded in v3 plan
- **WHEN** a user authors a pairwise-v3 plan that uses operator-provided workspace paths
- **THEN** the authored plan records a `custom` workspace contract
- **AND THEN** it identifies the explicit paths and rules instead of inventing a Houmao-standard layout

### Requirement: Pairwise-v3 standard in-repo workspace posture is task-scoped
When `houmao-agent-loop-pairwise-v3` uses the standard in-repo workspace posture, the run SHALL treat the team workspace as task-scoped under:

```text
<repo-root>/houmao-ws/<task-name>
```

The standard in-repo contract SHALL identify:

- the selected `task-name`,
- the task-local `workspace.md`,
- the task-local `shared-kb/`,
- one task-scoped agent directory per participant,
- task-qualified branch names such as `houmao/<task-name>/<agent-name>/main`.

#### Scenario: Standard in-repo v3 plan is task-scoped
- **WHEN** a pairwise-v3 plan selects the standard in-repo workspace posture
- **THEN** the plan records a task-scoped workspace under `houmao-ws/<task-name>/`
- **AND THEN** it does not describe the in-repo workspace as one flat repo-wide `houmao-ws/<agent-name>/...` layout

### Requirement: Pairwise-v3 standard workspace mode may rely on workspace-manager, but custom mode does not
When `houmao-agent-loop-pairwise-v3` uses a standard workspace contract, the guidance MAY rely on a workspace prepared or summarized by `houmao-utils-workspace-mgr`.

When `houmao-agent-loop-pairwise-v3` uses a custom workspace contract, the guidance SHALL NOT require the workspace-manager skill to translate, prepare, or validate that custom layout as if it were a standard Houmao workspace.

#### Scenario: Standard mode can reference workspace-manager output
- **WHEN** a pairwise-v3 plan uses a standard workspace contract
- **THEN** the plan may reference task-local workspace output prepared through `houmao-utils-workspace-mgr`
- **AND THEN** the standard workspace posture remains aligned with the workspace-manager contract

#### Scenario: Custom mode does not route through workspace-manager
- **WHEN** a pairwise-v3 plan uses a custom workspace contract
- **THEN** the plan records operator-owned paths directly
- **AND THEN** the guidance does not require invoking `houmao-utils-workspace-mgr` as if custom mode were a workspace-manager lane

### Requirement: Pairwise-v3 preserves pairwise-v2 recovery boundaries
The initialize, start, and `recover_and_continue` guidance in `houmao-agent-loop-pairwise-v3` SHALL preserve the pairwise-v2 boundary between participant-facing run material and Houmao runtime-owned recovery state.

The guidance MAY point participants at declared workspace or bookkeeping paths, but SHALL NOT redefine Houmao runtime-owned recovery files as normal user-authored workspace or bookkeeping surfaces.

#### Scenario: Recover-and-continue keeps runtime-owned recovery files separate
- **WHEN** pairwise-v3 performs `recover_and_continue` for a recoverable run
- **THEN** the participant-facing continuation material may reference declared workspace paths
- **AND THEN** the runtime-owned recovery record and event history remain outside the authored workspace contract
