## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` supports explicit preserved-home reuse

`houmao-mgr agents launch` SHALL accept optional `--reuse-home` for the current launch.

`--reuse-home` SHALL be launch-owned only and SHALL NOT be persisted into explicit launch profiles.

When `--reuse-home` is supplied, the command SHALL treat the request as restart of one stopped logical managed agent on one compatible preserved home for the resolved managed identity instead of allocating a new home.

The command SHALL support `--reuse-home` for both direct `--agents` launch and explicit `--launch-profile` launch.

For explicit `--launch-profile` launch, reused-home restart SHALL apply the currently stored launch-profile inputs, together with any stronger direct CLI overrides, onto the preserved home before startup. Updating the stored launch profile after the prior run SHALL therefore affect the restarted agent even though the prior stopped instance was not mutated in place.

The command SHALL require the prior runtime to already be down and its tmux session to already be absent. `--reuse-home` SHALL NOT by itself replace a fresh live owner of the same managed identity.

When the stopped lifecycle metadata carries a prior tmux session name and the operator does not provide `--session-name`, the command SHALL request restart using that same tmux session name.

When `--session-name` is provided, that explicit override SHALL take precedence over the stopped record's prior tmux session name.

The command SHALL use the stopped local lifecycle record and preserved manifest/home metadata as restart authority and SHALL NOT require separate registry cleanup before restarting.

If no compatible stopped preserved home can be resolved, the command SHALL fail clearly and SHALL NOT silently launch on a new home.

#### Scenario: Launch-profile-backed launch restarts one stopped preserved home with updated profile inputs
- **WHEN** explicit launch profile `alice` resolves managed identity `alice`
- **AND WHEN** a stopped compatible preserved home exists for `alice` with prior tmux session name `HOUMAO-alice-1700000000000`
- **AND WHEN** the stored launch profile `alice` has been updated since the prior run
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reuse-home`
- **THEN** the command requests reused-home restart for managed identity `alice`
- **AND THEN** the current stored launch-profile inputs are projected onto the preserved home before startup
- **AND THEN** the restart does not require separate registry cleanup
- **AND THEN** the restart requests tmux session name `HOUMAO-alice-1700000000000` by default

#### Scenario: Direct launch rejects reuse-home when no preserved home exists
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --agent-name reviewer --reuse-home`
- **AND WHEN** no compatible stopped preserved home exists for managed identity `reviewer`
- **THEN** the command fails clearly
- **AND THEN** it does not silently start a fresh-home launch

#### Scenario: Reuse-home does not bypass live-owner conflict on its own
- **WHEN** a fresh live session already owns managed identity `reviewer`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --agent-name reviewer --reuse-home`
- **THEN** the command fails rather than replacing that live owner
- **AND THEN** the failure tells the operator to stop the live owner before attempting reused-home restart

#### Scenario: Explicit session-name override wins over the stopped record
- **WHEN** explicit launch profile `alice` resolves one stopped compatible preserved home
- **AND WHEN** the stopped lifecycle metadata carries prior tmux session name `HOUMAO-alice-1700000000000`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reuse-home --session-name alice-restart-debug`
- **THEN** the command requests reused-home restart on the preserved home
- **AND THEN** the restart uses tmux session name `alice-restart-debug`
- **AND THEN** it does not silently force the old tmux session name when the operator supplied a stronger override
