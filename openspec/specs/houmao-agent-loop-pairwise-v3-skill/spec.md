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

### Requirement: Pairwise-v3 initialize materializes per-agent memo guidance
The `initialize` guidance in `houmao-agent-loop-pairwise-v3` SHALL be the canonical prestart step that materializes run-owned guidance into the related agents' memo surfaces.

When the pairwise-v3 plan provides launch-profile references for required participants, `initialize` SHALL inspect the launch profile's mailbox association before launching that participant.

When the pairwise-v3 plan provides launch-profile references for required participants, `initialize` SHALL use those launch profiles to launch missing participants before email/mailbox verification and memo materialization continue.

If a required participant is still missing and no launch profile was provided for it, `initialize` SHALL fail closed rather than inventing a launch.

If a required participant's launch profile does not declare the mailbox association needed for the run's default email/mailbox communication posture, `initialize` SHALL fail closed before launching that participant.

For the designated master, `initialize` SHALL write memo material that captures the run's organization rules, objective, workspace contract summary, participant set, delegation boundaries, completion posture, stop posture, and the routing or dispatch guidance needed to supervise the run.

For each additional participant whose managed memory is being used, `initialize` SHALL write memo material that captures that participant's local goal, immediate-driver relationship, allowed obligations, result-return contract, and relevant workspace or bookkeeping posture.

Before pairwise-v3 `initialize` reaches `ready`, it SHALL verify that the designated master and every required participant can participate in the email/mailbox communication posture used by the run.

If any required participant lacks that email/mailbox support, pairwise-v3 `initialize` SHALL fail closed and SHALL NOT treat the run as ready for ordinary `start`.

The same email/mailbox capability check SHALL block `recover_and_continue` from returning the run to `running`.

When `recover_and_continue` restores one run whose accepted posture included agent email notification, it SHALL re-enable that notification for rebound participants that expose the required live gateway and mailbox surfaces before the run returns to `running`.

Pairwise-v3 `initialize` SHALL NOT require a durable initialize page plus memo-pointer pattern as the ordinary participant-facing contract for v3.

#### Scenario: Initialize writes master and worker memo guidance
- **WHEN** a pairwise-v3 run completes `initialize`
- **THEN** the designated master's memo contains the durable supervision contract for that run
- **AND THEN** each participant memo contains the local run guidance that participant needs before execution begins

#### Scenario: Initialize launches missing participants from provided launch profiles
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** one required participant is missing but the plan provides a launch profile for that participant
- **THEN** `initialize` launches that participant before continuing
- **AND THEN** email/mailbox verification and memo materialization use the launched participant

#### Scenario: Initialize refuses launch profiles without mailbox association
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** one required participant is missing
- **AND WHEN** the plan provides a launch profile for that participant but that profile does not declare mailbox association
- **THEN** `initialize` fails closed before launching that participant
- **AND THEN** the run does not become ready

#### Scenario: Initialize refuses missing participants without launch profiles
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** one required participant is missing and the plan provides no launch profile for that participant
- **THEN** `initialize` fails closed
- **AND THEN** the run does not become ready

#### Scenario: Initialize does not rely on durable initialize pages for ordinary v3 start
- **WHEN** a pairwise-v3 run uses the ordinary memo-first initialize flow
- **THEN** the participant-facing prestart contract is materialized directly into memo surfaces
- **AND THEN** ordinary start does not depend on a separate durable initialize page being created first

#### Scenario: Initialize refuses runs without email capability
- **WHEN** a pairwise-v3 run is being initialized
- **AND WHEN** the designated master or any required participant lacks email/mailbox support
- **THEN** the system refuses to treat the run as ready
- **AND THEN** ordinary `start` does not proceed

#### Scenario: Recovery refuses runs without email capability
- **WHEN** a pairwise-v3 run is being restored through `recover_and_continue`
- **AND WHEN** the designated master or any required participant lacks email/mailbox support
- **THEN** the system refuses to return the run to `running`
- **AND THEN** continuation does not proceed

#### Scenario: Recovery re-enables agent email notification
- **WHEN** a pairwise-v3 run is being restored through `recover_and_continue`
- **AND WHEN** rebound participants expose the required live gateway and mailbox surfaces
- **THEN** the system re-enables their agent email notification posture before the run returns to `running`
- **AND THEN** the recovery summary reports that notifier restoration

### Requirement: Pairwise-v3 ordinary start is a lightweight memo-read trigger
The ordinary `start` guidance in `houmao-agent-loop-pairwise-v3` SHALL treat `initialize` as the readiness boundary and SHALL send a compact kickoff trigger only after `initialize` is complete.

That kickoff trigger SHALL target the designated master and SHALL instruct the master to read its memo material and begin the run.

Pairwise-v3 ordinary `start` SHALL send that kickoff through the run's mail-capable communication posture by default.

Pairwise-v3 ordinary `start` SHALL use direct prompt delivery only when the user explicitly requests that transport.

Pairwise-v3 ordinary `start` SHALL NOT require writing or refreshing a durable `start-charter` page.

Pairwise-v3 ordinary `start` SHALL NOT require an explicit `accepted` or `rejected` reply from the designated master before the run is treated as started.

#### Scenario: Start triggers the master without start-charter material
- **WHEN** a pairwise-v3 run is ready after `initialize`
- **THEN** ordinary `start` sends a compact kickoff trigger to the designated master
- **AND THEN** that trigger does not depend on a durable `start-charter` page

#### Scenario: Start uses mail delivery by default
- **WHEN** ordinary `start` is invoked for a pairwise-v3 run whose initialize work is complete
- **AND WHEN** the user did not explicitly request direct prompt delivery
- **THEN** the system sends the kickoff trigger through mail
- **AND THEN** it does not default to direct prompt delivery

#### Scenario: Start does not wait for master acceptance
- **WHEN** ordinary `start` is invoked for a pairwise-v3 run whose initialize work is complete
- **THEN** the system does not wait for an explicit `accepted` or `rejected` reply from the designated master
- **AND THEN** the run proceeds based on the memo material already prepared during `initialize`

### Requirement: Pairwise-v3 bundle plans may include generated template bundles
The authoring guidance in `houmao-agent-loop-pairwise-v3` SHALL support an authored `<plan-output-dir>/templates/` directory when a run needs reusable reporting or bookkeeping scaffolds.

When the authored run needs those reusable templates, the guidance SHALL direct the planner to use bundle form rather than single-file form.

The generated template bundle SHALL remain part of the authored plan output directory and SHALL NOT be described as runtime-owned state.

#### Scenario: Bundle plan includes generated reporting and bookkeeping templates
- **WHEN** a user authors a pairwise-v3 run whose reporting contract or bookkeeping posture needs reusable scaffolds
- **THEN** the authored output uses bundle form under the selected plan output directory
- **AND THEN** that bundle may include a `<plan-output-dir>/templates/` directory with generated reporting and bookkeeping templates

#### Scenario: Compact plan remains single-file when template bundle is unnecessary
- **WHEN** a user authors a compact pairwise-v3 run that does not need reusable reporting or bookkeeping scaffolds
- **THEN** the guidance may keep the plan in single-file form
- **AND THEN** it does not require inventing a `templates/` directory

### Requirement: Pairwise-v3 generated templates align with reporting and bookkeeping contracts
When `houmao-agent-loop-pairwise-v3` generates reporting templates, those templates SHALL reflect the authored reporting contract for the relevant run surfaces, including the applicable fields for peek, completion, recovery, stop, or hard-kill summaries when those surfaces are part of the run.

When `houmao-agent-loop-pairwise-v3` generates bookkeeping templates, those templates SHALL be derived from the task objective, topology, participant responsibilities, and declared bookkeeping paths for that run.

The guidance SHALL NOT impose one fixed bookkeeping subtree or one universal bookkeeping template set for all runs.

The guidance SHALL distinguish authored template files from mutable run artifacts written into declared bookkeeping paths, and SHALL NOT redefine Houmao runtime-owned recovery files as template-backed bookkeeping surfaces.

#### Scenario: Reporting template follows the authored reporting contract
- **WHEN** a pairwise-v3 bundle plan includes a reusable peek or completion template
- **THEN** that template reflects the fields required by the authored reporting contract for that report surface
- **AND THEN** the template does not invent a separate reporting schema unrelated to the contract

#### Scenario: Bookkeeping template stays task-shaped and boundary-aware
- **WHEN** a pairwise-v3 bundle plan includes reusable bookkeeping templates for a task-specific run
- **THEN** those templates are shaped by the run's objective, participant roles, topology, and declared bookkeeping paths
- **AND THEN** they do not prescribe one fixed per-agent `kb/` subtree or treat runtime-owned recovery files as ordinary bookkeeping artifacts
