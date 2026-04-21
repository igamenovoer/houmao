## ADDED Requirements

### Requirement: `project agents launch-profiles` enforces explicit lane ownership
`houmao-mgr project agents launch-profiles list|get|set|remove` SHALL operate only on stored `launch_profile` entries even though easy profiles share the same catalog-backed launch-profile family and compatibility projection path.

When `project agents launch-profiles get --name <profile>`, `set --name <profile>`, or `remove --name <profile>` targets a stored profile whose `profile_lane` is `easy_profile`, the command SHALL fail clearly instead of reading, mutating, or deleting that easy profile through the explicit lane.

That wrong-lane failure SHALL identify that the named resource belongs to the easy profile lane and SHALL direct the operator to the corresponding `houmao-mgr project easy profile <verb> --name <profile>` command.

`project agents launch-profiles list` SHALL continue returning only explicit launch-profile entries in `launch_profiles`. When that explicit-lane result is empty and one or more easy profiles exist in the selected overlay, the output SHALL include operator guidance to use `houmao-mgr project easy profile list`.

#### Scenario: Explicit get rejects easy profile with redirect guidance
- **WHEN** easy profile `alice` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles get --name alice`
- **THEN** the command fails clearly instead of returning `alice`
- **AND THEN** the error explains that `alice` belongs to the easy profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project easy profile get --name alice`

#### Scenario: Explicit set rejects easy profile with redirect guidance
- **WHEN** easy profile `alice` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --workdir /repos/alice-next`
- **THEN** the command fails clearly before mutating `alice`
- **AND THEN** the error explains that `alice` belongs to the easy profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project easy profile set --name alice`

#### Scenario: Explicit remove rejects easy profile with redirect guidance
- **WHEN** easy profile `alice` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles remove --name alice`
- **THEN** the command fails clearly before deleting `alice`
- **AND THEN** the error explains that `alice` belongs to the easy profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project easy profile remove --name alice`

#### Scenario: Explicit list keeps lane filtering and adds note when only easy profiles exist
- **WHEN** the selected project overlay contains one or more easy profiles
- **AND WHEN** the selected project overlay contains no explicit launch profiles that match the current explicit-list query
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles list`
- **THEN** the structured output reports an empty `launch_profiles` list
- **AND THEN** the structured output includes guidance to use `houmao-mgr project easy profile list`
- **AND THEN** the explicit list output does not inline easy profiles under `launch_profiles`
