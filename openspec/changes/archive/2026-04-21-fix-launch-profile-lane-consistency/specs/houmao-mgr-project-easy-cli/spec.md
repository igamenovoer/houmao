## ADDED Requirements

### Requirement: `project easy profile` enforces easy-profile lane ownership
`houmao-mgr project easy profile list|get|set|remove` SHALL operate only on stored `easy_profile` entries even though explicit launch profiles share the same catalog-backed launch-profile family and compatibility projection path.

When `project easy profile get --name <profile>`, `set --name <profile>`, or `remove --name <profile>` targets a stored profile whose `profile_lane` is `launch_profile`, the command SHALL fail clearly instead of reading, mutating, or deleting that explicit launch profile through the easy lane.

That wrong-lane failure SHALL identify that the named resource belongs to the explicit launch-profile lane and SHALL direct the operator to the corresponding `houmao-mgr project agents launch-profiles <verb> --name <profile>` command.

`project easy profile list` SHALL continue returning only easy-profile entries in `profiles`. When that easy-lane result is empty and one or more explicit launch profiles exist in the selected overlay, the output SHALL include operator guidance to use `houmao-mgr project agents launch-profiles list`.

#### Scenario: Easy get rejects explicit launch profile with redirect guidance
- **WHEN** explicit launch profile `nightly` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy profile get --name nightly`
- **THEN** the command fails clearly instead of returning `nightly`
- **AND THEN** the error explains that `nightly` belongs to the explicit launch-profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project agents launch-profiles get --name nightly`

#### Scenario: Easy set rejects explicit launch profile with redirect guidance
- **WHEN** explicit launch profile `nightly` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name nightly --workdir /repos/nightly-next`
- **THEN** the command fails clearly before mutating `nightly`
- **AND THEN** the error explains that `nightly` belongs to the explicit launch-profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project agents launch-profiles set --name nightly`

#### Scenario: Easy remove rejects explicit launch profile with redirect guidance
- **WHEN** explicit launch profile `nightly` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy profile remove --name nightly`
- **THEN** the command fails clearly before deleting `nightly`
- **AND THEN** the error explains that `nightly` belongs to the explicit launch-profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project agents launch-profiles remove --name nightly`

#### Scenario: Easy list keeps lane filtering and adds note when only explicit launch profiles exist
- **WHEN** the selected project overlay contains one or more explicit launch profiles
- **AND WHEN** the selected project overlay contains no easy profiles that match the current easy-list query
- **AND WHEN** an operator runs `houmao-mgr project easy profile list`
- **THEN** the structured output reports an empty `profiles` list
- **AND THEN** the structured output includes guidance to use `houmao-mgr project agents launch-profiles list`
- **AND THEN** the easy list output does not inline explicit launch profiles under `profiles`
