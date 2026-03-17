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

### Requirement: Interactive demo startup SHALL force-replace the verified local loopback CAO server during agent recreation
For the fixed local CAO target `http://127.0.0.1:9889`, interactive demo startup SHALL establish a fresh standalone local `cao-server` context for each agent recreation instead of silently reusing stale or incompatible server state.

If launcher `status` verifies that a healthy local `cli-agent-orchestrator`
service is already serving the fixed loopback target, the demo SHALL treat that
service as a verified local `cao-server` and SHALL stop it before launching the
replacement server context for the new run.

If launcher status is not healthy but the fixed loopback target is still
occupied, the demo MAY use best-effort process inspection as a fallback
verification path. That fallback SHALL skip unreadable or disappearing procfs
entries and SHALL only fail when the loopback occupant still cannot be safely
verified as `cao-server`.

If the process serving the fixed loopback target cannot be safely verified as
`cao-server`, the demo SHALL fail explicitly and SHALL NOT create an active
interactive state artifact.

If the demo cannot complete the stop-and-restart sequence for the verified
fixed-loopback CAO service, it SHALL fail explicitly and SHALL NOT continue
with interactive session creation.

#### Scenario: Verified stale loopback CAO server is recycled automatically
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already healthy on `http://127.0.0.1:9889`
- **THEN** the demo stops that server before creating the replacement local CAO server context
- **AND THEN** the subsequent interactive session launch uses the demo's configured launcher-home context instead of the stale server context

#### Scenario: Unreadable unrelated procfs entries do not block verified replacement
- **WHEN** a developer starts the interactive demo and launcher status already verifies a healthy local `cao-server` on the fixed loopback target
- **AND WHEN** unrelated `/proc/<pid>/fd` directories on the same machine are unreadable
- **THEN** the demo still treats the loopback occupant as verified for replacement purposes
- **AND THEN** startup does not fail solely because those unrelated procfs entries were unreadable

#### Scenario: Fallback process verification skips unreadable procfs entries
- **WHEN** a developer starts the interactive demo and launcher status is not healthy while the fixed loopback target is still occupied
- **AND WHEN** procfs inspection encounters unreadable or disappearing `/proc/<pid>/fd` entries during fallback verification
- **THEN** the demo skips those entries and continues best-effort verification
- **AND THEN** startup does not crash solely because one procfs entry could not be inspected

#### Scenario: Unverifiable loopback port occupant fails safely
- **WHEN** a developer starts the interactive demo and the fixed loopback target is occupied by a process that cannot be safely verified as `cao-server`
- **THEN** startup fails with an explicit diagnostic
- **AND THEN** the demo does not write `state.json` as active

#### Scenario: Replacement failure leaves no active interactive state
- **WHEN** a developer starts the interactive demo and a verified local `cao-server` is already serving `http://127.0.0.1:9889`
- **AND WHEN** the demo cannot successfully stop that server or cannot start its replacement CAO context
- **THEN** startup fails explicitly
- **AND THEN** the demo does not continue with interactive session creation

### Requirement: Verified fixed-loopback CAO replacement SHALL continue across known launcher configs
The interactive demo SHALL treat launcher-stop attempts against known configs as a search for the config that owns the live service rather than assuming the first candidate must succeed when it is replacing a verified local `cao-server` on `http://127.0.0.1:9889`.

If one known-config launcher-stop attempt fails to produce usable structured
output but the fixed loopback target is still listening and later known configs
remain available, the demo SHALL continue trying later known configs before
declaring replacement failure.

If all known configs are exhausted and the fixed loopback service is still
listening, the demo SHALL fail explicitly and SHALL NOT create an active
interactive state artifact.

#### Scenario: Fresh current config does not block replacement of an older verified CAO owner
- **WHEN** a developer starts the interactive demo and launcher `status` verifies a healthy local `cli-agent-orchestrator` service on `http://127.0.0.1:9889`
- **AND WHEN** the current run's fresh launcher config does not own that live service
- **AND WHEN** a launcher `stop` attempt for the fresh config does not produce usable structured output
- **AND WHEN** a later known launcher config does own the verified live service
- **THEN** the demo continues to the later known config instead of aborting on the first stop attempt
- **AND THEN** the verified fixed-loopback `cao-server` is replaced before interactive session startup continues

#### Scenario: Exhausted known configs fail safely
- **WHEN** a developer starts the interactive demo and launcher `status` verifies a healthy local `cli-agent-orchestrator` service on `http://127.0.0.1:9889`
- **AND WHEN** every known launcher config fails to stop that verified live service
- **AND WHEN** the fixed loopback target is still listening after the known-config replacement attempts finish
- **THEN** startup fails with an explicit replacement diagnostic
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

The reset SHALL attempt to stop any existing session addressed by canonical agent identity `AGENTSYS-alice`, SHALL clean leftover tmux/demo state that survives that stop, and SHALL clear prior-run demo artifacts that would otherwise contaminate the new run.

When the live tmux handle for the tutorial session differs from the canonical agent identity because it includes an authoritative agent-id suffix, the reset flow SHALL use persisted or discovered tmux session metadata to clean that leftover tmux session instead of assuming the tmux handle is exactly `AGENTSYS-alice`.

When persisted demo state is missing, discovered tmux session metadata SHALL be matched by canonical agent identity. The reset flow MAY still clean an exact canonical tmux session name as a legacy fallback, but it SHALL NOT remove a tmux session solely because its tmux session name shares a string prefix with `AGENTSYS-alice`.

#### Scenario: Stale suffixed tmux session does not block replacement startup
- **WHEN** a stale tmux session named `AGENTSYS-alice-270b87` exists before the user runs tutorial startup
- **AND WHEN** the persisted demo state is absent, inactive, or does not describe that exact tmux session
- **AND WHEN** discovered tmux session metadata for that session resolves canonical agent identity `AGENTSYS-alice`
- **THEN** startup removes the stale tutorial tmux state associated with canonical identity `AGENTSYS-alice` before launching the replacement session
- **AND THEN** the new launch succeeds without asking the user to manually clean up `AGENTSYS-alice-270b87`

#### Scenario: Prefix-only tmux-name similarity does not justify cleanup
- **WHEN** a tmux session named `AGENTSYS-alice-extended-270b87` exists before the user runs tutorial startup
- **AND WHEN** persisted demo state is absent, inactive, or does not describe that session
- **AND WHEN** discovered tmux session metadata does not associate that session with canonical agent identity `AGENTSYS-alice`
- **THEN** startup does not remove that tmux session solely because its tmux session name begins with `AGENTSYS-alice-`

#### Scenario: Prior run artifacts are cleared before the new run
- **WHEN** a previous tutorial run left turn records or a verification report in the demo workspace
- **THEN** the next `start` clears those prior-run artifacts before launching the replacement session
- **AND THEN** the resulting session behaves like a fresh run for subsequent verification
