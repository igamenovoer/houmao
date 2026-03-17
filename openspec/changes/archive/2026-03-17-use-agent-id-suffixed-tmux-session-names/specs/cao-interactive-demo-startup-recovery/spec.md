## MODIFIED Requirements

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
