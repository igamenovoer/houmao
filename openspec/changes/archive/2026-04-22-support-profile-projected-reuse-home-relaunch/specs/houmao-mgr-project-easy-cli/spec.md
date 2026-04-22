## MODIFIED Requirements

### Requirement: `project easy instance launch` supports explicit preserved-home reuse

`houmao-mgr project easy instance launch` SHALL accept optional `--reuse-home` for the current easy launch.

`--reuse-home` SHALL be launch-owned only and SHALL NOT be persisted into the stored specialist or easy profile.

When `--reuse-home` is supplied, easy instance launch SHALL treat the request as restart of one stopped logical managed agent on one compatible preserved home for the resolved managed identity instead of allocating a new home.

The command SHALL support `--reuse-home` for both specialist-backed launch and easy-profile-backed launch.

For easy-profile-backed launch, reused-home restart SHALL apply the currently stored easy-profile inputs, together with any stronger direct CLI overrides, onto the preserved home before startup. Updating the stored easy profile after the prior run SHALL therefore affect the restarted agent even though the prior stopped instance was not mutated in place.

The command SHALL require the prior runtime to already be down and its tmux session to already be absent. `--reuse-home` SHALL NOT by itself replace a fresh live owner of the same managed identity.

When the stopped lifecycle metadata carries a prior tmux session name and the operator does not provide `--session-name`, the command SHALL request restart using that same tmux session name.

When `--session-name` is provided, that explicit override SHALL take precedence over the stopped record's prior tmux session name.

The command SHALL use the stopped local lifecycle record and preserved manifest/home metadata as restart authority and SHALL NOT require separate registry cleanup before restarting.

If no compatible stopped preserved home can be resolved, the command SHALL fail clearly and SHALL NOT silently launch on a new home.

#### Scenario: Easy-profile-backed launch restarts one stopped preserved home with updated profile inputs
- **WHEN** easy profile `reviewer-default` resolves managed identity `reviewer-default`
- **AND WHEN** a stopped compatible preserved home exists for that identity with prior tmux session name `HOUMAO-reviewer-default-1700000000000`
- **AND WHEN** the stored easy profile `reviewer-default` has been updated since the prior run
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default --reuse-home`
- **THEN** the delegated native launch requests reused-home restart for that managed identity
- **AND THEN** the current stored easy-profile inputs are projected onto the preserved home before startup
- **AND THEN** the restart does not require separate registry cleanup
- **AND THEN** the restart requests tmux session name `HOUMAO-reviewer-default-1700000000000` by default

#### Scenario: Specialist-backed launch rejects reuse-home when no preserved home exists
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer --name reviewer-a --reuse-home`
- **AND WHEN** no compatible stopped preserved home exists for managed identity `reviewer-a`
- **THEN** the command fails clearly
- **AND THEN** it does not silently start a fresh-home launch

#### Scenario: Reuse-home does not bypass easy-launch ownership conflict on its own
- **WHEN** a fresh live session already owns managed identity `reviewer-a`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer --name reviewer-a --reuse-home`
- **THEN** the command fails rather than replacing that live owner
- **AND THEN** the failure tells the operator to stop the live owner before attempting reused-home restart

#### Scenario: Easy explicit session-name override wins over the stopped record
- **WHEN** easy profile `reviewer-default` resolves one stopped compatible preserved home
- **AND WHEN** the stopped lifecycle metadata carries prior tmux session name `HOUMAO-reviewer-default-1700000000000`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default --reuse-home --session-name reviewer-restart-debug`
- **THEN** the delegated native launch requests reused-home restart on the preserved home
- **AND THEN** the restart uses tmux session name `reviewer-restart-debug`
- **AND THEN** it does not silently force the old tmux session name when the operator supplied a stronger override
