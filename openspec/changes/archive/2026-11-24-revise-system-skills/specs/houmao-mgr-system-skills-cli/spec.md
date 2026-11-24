## MODIFIED Requirements

### Requirement: System-skills doctor diagnoses an expected static pack
`houmao-mgr system-skills doctor` SHALL perform a read-only diagnostic of repeatable `--pack admin|agent` selections and default to `agent`. It SHALL check each expected standalone root for destination shape, complete owned content, matching name, and exact `metadata.houmao_version` equality with the running package. It SHALL check the shared root for the declared parent-scoped child entrypoints.

#### Scenario: Healthy managed agent pack
- **WHEN** doctor examines a complete current agent pack
- **THEN** it reports the agent entrypoint, shared routines, pro loop, and lite loop as healthy
- **AND THEN** it reports every observed `houmao_version` as equal to the running package version

#### Scenario: Expected root is absent
- **WHEN** doctor examines an agent pack without `houmao-shared-routines`
- **THEN** it reports that expected root as absent
- **AND THEN** the aggregate diagnostic is unhealthy

#### Scenario: A declared shared child is absent
- **WHEN** doctor finds the shared root but an expected child entrypoint is missing
- **THEN** it reports the shared root as incomplete
- **AND THEN** the aggregate diagnostic is unhealthy

### Requirement: Doctor separates installation integrity from version status
Structured doctor output SHALL include the resolved target, expected running Houmao version, selected packs, config posture, aggregate health, and one record per expected standalone skill.

Each member record SHALL include its name, role, destination, integrity status, observed version when available, version status, and issue details. Version status SHALL distinguish `match`, `mismatch`, `missing`, `invalid`, and `unavailable`.

#### Scenario: Version matches but content was edited
- **WHEN** an installed root retains the current `metadata.houmao_version` but its owned content differs from the packaged source
- **THEN** doctor reports version status `match` and integrity status `drifted`
- **AND THEN** the aggregate diagnostic is unhealthy

#### Scenario: Old release is structurally complete
- **WHEN** every expected root is complete but declares an older valid `metadata.houmao_version`
- **THEN** doctor reports each differing value as `mismatch`
- **AND THEN** it reports the running package version as the expected value

#### Scenario: Running version is unavailable
- **WHEN** the running package reports `0+unknown`
- **THEN** doctor reports version comparison as `unavailable`
- **AND THEN** it does not claim a version match

### Requirement: Doctor remains independent of skill config ownership
`houmao-mgr system-skills doctor` SHALL directly inspect expected installed roots and their `metadata.houmao_version` values in `SKILL.md`. Missing `houmao-skill-config.json` alone SHALL NOT make a complete and release-matching copy-paste or Skills CLI installation unhealthy.

Doctor SHALL report config evidence separately when present and use config terminology in plain and structured output.

#### Scenario: Configless static pack is healthy
- **WHEN** doctor inspects a complete static pack whose roots and frontmatter match the running release but no skill config exists
- **THEN** doctor reports all expected members healthy
- **AND THEN** it reports config state as absent

#### Scenario: Config release is diagnostic evidence
- **WHEN** doctor inspects a config-managed pack
- **THEN** it reports the config's `houmao_version` separately from each installed root's observed frontmatter version
- **AND THEN** it uses the installed metadata for the running-version comparison

### Requirement: System-skills list reports the static collection and pack membership
`houmao-mgr system-skills list` SHALL report the six standalone skills, declared shared child logical IDs, admin and agent pack members, default lanes, and activation posture. Both output formats SHALL distinguish standalone install units from parent-scoped routines. Structured output SHALL report each skill or routine's declared commands and aliases.

#### Scenario: Operator lists current system skills
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the output reports six standalone skills
- **AND THEN** it reports five admin members and four agent members
- **AND THEN** it identifies the three overlapping members and all declared shared children
- **AND THEN** it identifies `houmao-shared-routines` and both loop skills as standalone install units

#### Scenario: Operator inspects the structured command inventory
- **WHEN** an operator requests structured `system-skills list` output
- **THEN** it includes the declared commands and aliases for `agent-access` and `agent-files`
- **AND THEN** it includes definition authoring, deployment and batch commands and the instance runtime-variable, mindset and private-workspace commands
