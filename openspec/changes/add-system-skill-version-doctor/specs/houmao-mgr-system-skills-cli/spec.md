## ADDED Requirements

### Requirement: System-skills doctor diagnoses an expected static pack
`houmao-mgr system-skills doctor` SHALL perform a read-only diagnostic of repeatable `--pack admin|agent` selections. Omitted pack selection SHALL default to `agent`.

Doctor SHALL check every expected standalone root for destination shape, complete owned content, valid matching name frontmatter, and exact `houmao_version` equality with the running Houmao package. It SHALL check the shared root for the exact sixteen parent-scoped child entrypoints.

#### Scenario: Healthy managed agent pack
- **WHEN** doctor examines a complete current agent pack
- **THEN** it reports the agent entrypoint, shared routines, pro loop, and lite loop as healthy
- **AND THEN** it reports every observed `houmao_version` as equal to the running package version

#### Scenario: Expected root is absent
- **WHEN** doctor examines an agent pack without `houmao-shared-routines`
- **THEN** it reports that expected root as absent
- **AND THEN** the aggregate diagnostic is unhealthy

### Requirement: Doctor supports explicit home and managed-agent targets
Doctor SHALL support an explicit tool-home mode using `--tool` and the existing optional `--home` resolution. It SHALL also support managed-agent mode using exactly one of `--agent-id` or `--agent-name`.

Managed-agent mode SHALL resolve one known local managed-agent record, its session manifest, its brain manifest, its tool, and its persistent home. It SHALL reject ambiguous names, external agents, missing authority files, and combinations of managed-agent selectors with `--tool` or `--home`.

#### Scenario: Operator diagnoses by agent id
- **WHEN** an operator runs doctor with one authoritative managed-agent id
- **THEN** doctor resolves that agent's tool and persistent home without requiring a live session
- **AND THEN** it checks the expected agent pack in that home

#### Scenario: Friendly name is ambiguous
- **WHEN** `--agent-name` resolves to more than one known managed agent
- **THEN** doctor fails target resolution before inspecting any home
- **AND THEN** it asks for an authoritative agent id

#### Scenario: Operator provides incompatible target modes
- **WHEN** a doctor request combines `--agent-id` with `--tool` or `--home`
- **THEN** the command rejects the request as invalid usage
- **AND THEN** it does not inspect or mutate either target

### Requirement: Doctor separates installation integrity from version status
Structured doctor output SHALL include the resolved target, expected running Houmao version, selected packs, receipt posture, aggregate health, and one record per expected standalone skill.

Each member record SHALL include its name, role, destination, integrity status, observed version when available, version status, and issue details. Version status SHALL distinguish `match`, `mismatch`, `missing`, `invalid`, and `unavailable`.

#### Scenario: Version matches but content was edited
- **WHEN** an installed root retains the current `houmao_version` but its owned content differs from the packaged source
- **THEN** doctor reports version status `match` and integrity status `drifted`
- **AND THEN** the aggregate diagnostic is unhealthy

#### Scenario: Old release is structurally complete
- **WHEN** every expected root is complete but declares an older valid `houmao_version`
- **THEN** doctor reports each differing value as `mismatch`
- **AND THEN** it reports the running package version as the expected value

#### Scenario: Running version is unavailable
- **WHEN** the running package reports `0+unknown`
- **THEN** doctor reports version comparison as `unavailable`
- **AND THEN** it does not claim a version match

### Requirement: Doctor handles receiptless and receipt-managed homes
Doctor SHALL read installed frontmatter as the version authority. A current receipt MAY add ownership and projection evidence, but its `package_version` SHALL NOT substitute for installed skill metadata.

Receipt absence alone SHALL NOT make an otherwise complete externally installed pack unhealthy. Corrupt, unsupported, or inconsistent receipt evidence SHALL be reported separately and SHALL NOT prevent direct read-only frontmatter inspection.

#### Scenario: Receipt package version differs from installed metadata
- **WHEN** a receipt records one package version and an installed root declares another
- **THEN** doctor reports the installed frontmatter value as the observed skill version
- **AND THEN** it reports receipt evidence separately

#### Scenario: Complete receiptless copy matches
- **WHEN** a copy-paste installation contains every expected current root and no receipt
- **THEN** doctor reports receipt posture `absent`
- **AND THEN** it can still report the selected pack as healthy

### Requirement: Doctor uses diagnostic exit semantics without enforcement
Doctor SHALL exit with code 0 only when every expected root is complete and version-matched. It SHALL exit with code 1 for detected missing, malformed, incomplete, drifted, conflicting, mismatched, or unavailable health evidence. Click usage and target-resolution errors SHALL retain code 2.

Doctor SHALL NOT mutate files, install or remove skills, write a receipt, launch an agent, or change any lifecycle state.

#### Scenario: Automation checks an outdated home
- **WHEN** doctor detects one version mismatch
- **THEN** it emits the complete diagnostic and exits with code 1
- **AND THEN** the installed home remains byte-for-byte unchanged

#### Scenario: Automation checks a healthy home
- **WHEN** all expected members are complete and version-matched
- **THEN** doctor exits with code 0
- **AND THEN** it performs no lifecycle mutation
