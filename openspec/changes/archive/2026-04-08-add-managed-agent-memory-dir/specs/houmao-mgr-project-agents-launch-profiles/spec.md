## ADDED Requirements

### Requirement: `project agents launch-profiles` manages explicit memory-directory defaults
`houmao-mgr project agents launch-profiles add` SHALL accept optional `--memory-dir <path>` and `--no-memory-dir` to store reusable memory-directory configuration on an explicit launch profile.

`houmao-mgr project agents launch-profiles set` SHALL accept optional `--memory-dir <path>`, `--no-memory-dir`, and `--clear-memory-dir` for the same stored field.

`--memory-dir`, `--no-memory-dir`, and `--clear-memory-dir` SHALL be mutually exclusive on `launch-profiles set`.

`--memory-dir` and `--no-memory-dir` SHALL be mutually exclusive on `launch-profiles add`.

When an exact memory directory is stored on this surface, the stored value SHALL be the resolved absolute path.

`launch-profiles get --name <profile>` SHALL report whether the profile stores an exact memory directory, stores disabled memory binding, or stores no memory preference.

#### Scenario: Add stores one exact memory directory as an absolute path
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --memory-dir ../shared/alice-memory`
- **THEN** the created explicit launch profile stores the resolved absolute path for `../shared/alice-memory`
- **AND THEN** later `launch-profiles get --name alice` reports that stored absolute memory directory

#### Scenario: Set stores explicit disabled memory binding
- **WHEN** explicit launch profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --no-memory-dir`
- **THEN** the stored explicit launch profile records disabled memory binding
- **AND THEN** later `launch-profiles get --name alice` reports that disabled state

#### Scenario: Set can clear stored memory configuration back to no profile preference
- **WHEN** explicit launch profile `alice` already stores one exact memory directory
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-memory-dir`
- **THEN** the stored explicit launch profile no longer records profile-owned memory configuration
- **AND THEN** later launches from `alice` fall back to the launch surface's system default behavior unless a stronger override is supplied
