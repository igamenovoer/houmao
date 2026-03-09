# cao-interactive-demo-startup-recovery Specification

## Purpose
TBD - created by archiving change harden-cao-interactive-demo-startup. Update Purpose after archive.
## Requirements
### Requirement: Interactive demo defaults SHALL be repository-root anchored
The interactive CAO demo pack SHALL derive its omitted repository-sensitive paths from the checked-out repository root rather than the caller's current working directory.

Repository-sensitive defaults include at least:
- the default per-run demo root,
- the default git worktree path used as the session workdir,
- the default agent-definition directory, and
- the default launcher home directory used for local CAO startup.

This repository-root anchoring requirement SHALL apply to the interactive demo wrapper scripts and `gig_agents.demo.cao_interactive_full_pipeline_demo`, and SHALL NOT change shared runtime-wide default behavior outside this demo pack.

#### Scenario: Wrapper flow works from outside the repo root
- **WHEN** a developer runs `scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh` from this repository checkout while their shell `pwd` is some other directory
- **THEN** the demo resolves the repo workdir to this checkout's root
- **AND THEN** the default workspace and agent-definition paths resolve relative to this checkout
- **AND THEN** startup behavior does not depend on the caller first changing directory into the repo root

#### Scenario: Explicit overrides still take precedence
- **WHEN** a developer provides explicit override inputs for workspace or launcher-home paths
- **THEN** the demo uses the provided override values
- **AND THEN** repo-root anchoring only applies to omitted defaults

### Requirement: Interactive demo default startup SHALL provision a per-run trusted home and git worktree
When the operator omits custom workspace, launcher-home, and workdir inputs, the interactive CAO demo SHALL create a fresh per-run directory under `<repo-root>/tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`, SHALL create a git worktree at `<run-root>/wktree`, SHALL use `<run-root>` as the default CAO trusted home, and SHALL use `<run-root>/wktree` as the default workdir for interactive session startup.

#### Scenario: Default startup avoids workdir rejection
- **WHEN** a developer launches the interactive demo with default path settings and local prerequisites satisfied
- **THEN** the effective trusted home used for local CAO startup contains the effective session workdir
- **AND THEN** startup does not fail because the workdir is outside the CAO trusted home tree

#### Scenario: Repeated default starts use isolated per-run roots
- **WHEN** a developer runs the default startup flow on two different occasions without providing path overrides
- **THEN** each run gets its own per-run demo root under `tmp/demo/cao-interactive-full-pipeline-demo/`
- **AND THEN** CAO trusted-home state and demo-local artifacts are scoped to that run root rather than a shared workspace directory

### Requirement: Interactive demo startup SHALL confirm before recycling an existing verified local loopback CAO server
For the fixed local CAO target `http://127.0.0.1:9889`, interactive demo startup SHALL establish a fresh local `cao-server` context instead of silently reusing stale or incompatible server state.

If a local `cao-server` is already serving the fixed loopback target and can be verified as `cao-server`, the demo SHALL prompt for confirmation before stopping it and launching the replacement server context for the tutorial run.

If the operator supplies `-y` through the demo script surface, the demo SHALL treat that confirmation as already granted.

If the process serving the fixed loopback target cannot be safely verified as `cao-server`, the demo SHALL fail explicitly and SHALL NOT create an active interactive state artifact.

#### Scenario: Verified stale loopback CAO server is recycled after confirmation
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **AND WHEN** the developer confirms the replacement prompt
- **THEN** the demo stops that server before creating the replacement local CAO server context
- **AND THEN** the subsequent interactive session launch uses the demo's configured launcher-home context instead of the stale server context

#### Scenario: `-y` bypasses the replacement prompt
- **WHEN** a developer starts the interactive demo with `-y`
- **AND WHEN** a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **THEN** the demo replaces that server without waiting for an interactive confirmation prompt
- **AND THEN** the new session launch continues with the demo's configured launcher-home context

#### Scenario: Declining replacement leaves no active state
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **AND WHEN** the developer declines the replacement prompt
- **THEN** startup exits without replacing the existing CAO server
- **AND THEN** the demo does not write `state.json` as active

#### Scenario: Unverifiable loopback port occupant fails safely
- **WHEN** a developer starts the interactive demo and the fixed loopback target is occupied by a process that cannot be safely verified as `cao-server`
- **THEN** startup fails with an explicit diagnostic
- **AND THEN** the demo does not write `state.json` as active

### Requirement: Interactive demo wrapper scripts SHALL accept a consistent `-y` contract
The interactive demo wrapper commands `run_demo.sh`, `launch_alice.sh`, `send_prompt.sh`, and `stop_demo.sh` SHALL all accept `-y` as a demo-wide yes-to-all flag.

Commands that do not currently prompt SHALL still accept `-y` without error so future prompt-bearing extensions do not require divergent CLI contracts.

#### Scenario: Non-prompting helper scripts still accept `-y`
- **WHEN** a developer runs `send_prompt.sh` or `stop_demo.sh` with `-y`
- **THEN** the wrapper accepts the flag without a usage error
- **AND THEN** the command continues to perform its normal behavior

### Requirement: Interactive demo startup SHALL reset canonical tutorial state to a fresh-run baseline
Interactive demo startup SHALL reset `AGENTSYS-alice` and prior-run demo leftovers before launching the replacement tutorial session, even when local persisted demo state is missing, inactive, or stale.

The reset SHALL attempt to stop any existing `AGENTSYS-alice` session, SHALL clean leftover tmux/demo state that survives that stop, and SHALL clear prior-run demo artifacts that would otherwise contaminate the new run.

#### Scenario: Stale tmux session does not block replacement startup
- **WHEN** a stale tmux session named `AGENTSYS-alice` exists before the user runs tutorial startup
- **AND WHEN** the persisted demo state is absent, inactive, or does not describe that tmux session
- **THEN** startup removes the stale canonical tutorial identity before launching the replacement session
- **AND THEN** the new launch succeeds without asking the user to manually clean up `AGENTSYS-alice`

#### Scenario: Prior run artifacts are cleared before the new run
- **WHEN** a previous tutorial run left turn records or a verification report in the demo workspace
- **THEN** the next `start` clears those prior-run artifacts before launching the replacement session
- **AND THEN** the resulting session behaves like a fresh run for subsequent verification

