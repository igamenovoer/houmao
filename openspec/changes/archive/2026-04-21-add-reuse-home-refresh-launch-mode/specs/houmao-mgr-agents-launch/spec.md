## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports explicit preserved-home reuse

`houmao-mgr agents launch` SHALL accept optional `--reuse-home` for the current launch.

`--reuse-home` SHALL be launch-owned only and SHALL NOT be persisted into explicit launch profiles.

When `--reuse-home` is supplied, the command SHALL request fresh managed launch against one compatible preserved home for the resolved managed identity instead of allocating a new home.

The command SHALL support `--reuse-home` for both direct `--agents` launch and explicit `--launch-profile` launch.

`--reuse-home` alone SHALL NOT authorize replacing a fresh live owner of the same managed identity. Existing live-owner conflict behavior SHALL remain in force unless the operator also supplies supported managed takeover flags.

If no compatible preserved home can be resolved, the command SHALL fail clearly and SHALL NOT silently launch on a new home.

If `--reuse-home` is combined with `--force`, only bare `--force` or `--force keep-stale` SHALL be accepted. `--force clean` SHALL be rejected because it would destroy the preserved home.

#### Scenario: Launch-profile-backed launch reuses one stopped preserved home
- **WHEN** explicit launch profile `alice` resolves managed identity `alice`
- **AND WHEN** a stopped compatible preserved home exists for `alice`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reuse-home`
- **THEN** the command requests reused-home fresh launch for managed identity `alice`
- **AND THEN** stored launch profile `alice` remains unchanged

#### Scenario: Direct launch rejects reuse-home when no preserved home exists
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --agent-name reviewer --reuse-home`
- **AND WHEN** no compatible preserved home exists for managed identity `reviewer`
- **THEN** the command fails clearly
- **AND THEN** it does not silently start a fresh-home launch

#### Scenario: Reuse-home does not bypass live-owner conflict on its own
- **WHEN** a fresh live session already owns managed identity `reviewer`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --agent-name reviewer --reuse-home`
- **THEN** the command fails rather than replacing that live owner

#### Scenario: Reuse-home rejects destructive clean takeover
- **WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reuse-home --force clean`
- **THEN** the command fails before destructive cleanup begins
- **AND THEN** the failure explains that `clean` is incompatible with preserved-home reuse
