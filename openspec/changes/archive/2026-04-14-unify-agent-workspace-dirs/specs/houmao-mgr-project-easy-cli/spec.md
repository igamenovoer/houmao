## REMOVED Requirements

### Requirement: `project easy profile create/get` supports reusable memory-directory defaults
**Reason**: Replaced by reusable persist-lane defaults.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

### Requirement: `project easy instance launch/get` supports managed memory-directory binding
**Reason**: Replaced by managed workspace lanes and persist-lane binding.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## ADDED Requirements

### Requirement: `project easy profile create/get` supports reusable persist-lane defaults
`houmao-mgr project easy profile create` SHALL accept optional `--persist-dir <path>` and `--no-persist-dir` to store reusable persist-lane configuration on an easy profile.

`--persist-dir` and `--no-persist-dir` SHALL be mutually exclusive on this surface.

`project easy profile get` SHALL report the stored persist-lane configuration.

#### Scenario: Easy profile stores exact persist directory
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --persist-dir ../shared/alice-persist`
- **THEN** the easy profile stores that resolved persist directory
- **AND THEN** `project easy profile get --name alice` reports that persist directory

#### Scenario: Easy profile stores disabled persistence
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --no-persist-dir`
- **THEN** the easy profile stores disabled persist binding
- **AND THEN** `project easy profile get --name alice` reports persistence as disabled

### Requirement: `project easy instance launch/get` supports managed workspace lanes and persist binding
`houmao-mgr project easy instance launch` SHALL accept optional `--persist-dir <path>` and `--no-persist-dir` as one-off persist-binding controls.

`--persist-dir` and `--no-persist-dir` SHALL be mutually exclusive on this surface.

`project easy instance get` SHALL report workspace root, scratch directory, persist binding, and persist directory when enabled.

#### Scenario: Easy instance launch disables persistence while keeping scratch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name researcher-1 --no-persist-dir`
- **THEN** the launched instance reports disabled persistence
- **AND THEN** later `project easy instance get --name researcher-1` reports `persist_dir: null`
- **AND THEN** later `project easy instance get --name researcher-1` reports a scratch directory
