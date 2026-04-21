## ADDED Requirements

### Requirement: `project easy instance launch` supports explicit preserved-home reuse

`houmao-mgr project easy instance launch` SHALL accept optional `--reuse-home` for the current easy launch.

`--reuse-home` SHALL be launch-owned only and SHALL NOT be persisted into the stored specialist or easy profile.

When `--reuse-home` is supplied, easy instance launch SHALL forward preserved-home reuse intent to the delegated native managed launch for the resolved managed identity.

The command SHALL support `--reuse-home` for both specialist-backed launch and easy-profile-backed launch.

When `--reuse-home` is requested and the resolved managed identity currently has only a stopped compatible preserved home, easy instance launch SHALL use that preserved home without requiring `agents relaunch`.

`--reuse-home` alone SHALL NOT authorize replacement of a fresh live owner for the same managed identity.

If no compatible preserved home can be resolved, the command SHALL fail clearly and SHALL NOT silently launch on a new home.

If `--reuse-home` is combined with `--force`, only bare `--force` or `--force keep-stale` SHALL be accepted. `--force clean` SHALL be rejected because it would destroy the preserved home.

#### Scenario: Easy-profile-backed launch reuses one stopped preserved home
- **WHEN** easy profile `reviewer-default` resolves managed identity `reviewer-default`
- **AND WHEN** a stopped compatible preserved home exists for that identity
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default --reuse-home`
- **THEN** the delegated native launch requests reused-home fresh launch for that managed identity
- **AND THEN** stored easy profile `reviewer-default` remains unchanged

#### Scenario: Specialist-backed launch rejects reuse-home when no preserved home exists
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer --name reviewer-a --reuse-home`
- **AND WHEN** no compatible preserved home exists for managed identity `reviewer-a`
- **THEN** the command fails clearly
- **AND THEN** it does not silently start a fresh-home launch

#### Scenario: Reuse-home does not bypass easy-launch ownership conflict on its own
- **WHEN** a fresh live session already owns managed identity `reviewer-a`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist reviewer --name reviewer-a --reuse-home`
- **THEN** the command fails rather than replacing that live owner

#### Scenario: Easy reuse-home rejects destructive clean takeover
- **WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default --reuse-home --force clean`
- **THEN** the command fails before destructive cleanup begins
- **AND THEN** the failure explains that `clean` is incompatible with preserved-home reuse
