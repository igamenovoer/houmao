## ADDED Requirements

### Requirement: Launch-profile auth overrides track auth profile identity across auth rename
Stored explicit launch-profile auth overrides SHALL resolve through auth profile identity rather than using auth display-name text as the authoritative relationship key.

When a launch profile selects an auth override, the stored relationship SHALL remain valid after that auth profile is renamed.

Operator-facing launch-profile inspection SHALL render the current auth display name for the referenced auth profile.

#### Scenario: Launch-profile auth override survives auth rename
- **WHEN** explicit launch profile `alice` stores an auth override referencing one Codex auth profile named `work`
- **AND WHEN** that auth profile is renamed to `breakglass`
- **THEN** later launch from profile `alice` still resolves the same auth profile
- **AND THEN** the operator does not need to edit `alice` only because the auth display name changed

#### Scenario: Launch-profile get renders the current auth display name
- **WHEN** explicit launch profile `alice` references one auth profile whose current display name is `breakglass`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles get --name alice`
- **THEN** the command reports auth override `breakglass`
- **AND THEN** it does not require the caller to know the internal auth profile id or opaque bundle reference
