## REMOVED Requirements

### Requirement: `project agents launch-profiles` manages explicit memory-directory defaults
**Reason**: Replaced by explicit persist-lane defaults.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## ADDED Requirements

### Requirement: `project agents launch-profiles` manages explicit persist-lane defaults
`houmao-mgr project agents launch-profiles add` SHALL accept optional `--persist-dir <path>` and `--no-persist-dir` to store reusable persist-lane configuration on an explicit launch profile.

`houmao-mgr project agents launch-profiles set` SHALL accept optional `--persist-dir <path>`, `--no-persist-dir`, and `--clear-persist-dir` for the same stored field.

`--persist-dir`, `--no-persist-dir`, and `--clear-persist-dir` SHALL be mutually exclusive on `launch-profiles set`.

`--persist-dir` and `--no-persist-dir` SHALL be mutually exclusive on `launch-profiles add`.

#### Scenario: Add stores one exact persist directory
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --persist-dir ../shared/alice-persist`
- **THEN** the created launch profile stores that resolved persist directory
- **AND THEN** launch-profile inspection reports the stored persist directory

#### Scenario: Set stores disabled persistence
- **WHEN** launch profile `alice` exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --no-persist-dir`
- **THEN** the launch profile stores disabled persist binding
- **AND THEN** launch-profile inspection reports persistence as disabled
