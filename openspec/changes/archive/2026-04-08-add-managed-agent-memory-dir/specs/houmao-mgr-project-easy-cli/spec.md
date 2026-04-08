## ADDED Requirements

### Requirement: `project easy profile create/get` supports reusable memory-directory defaults
`houmao-mgr project easy profile create` SHALL accept optional `--memory-dir <path>` and `--no-memory-dir` to store reusable memory-directory configuration on an easy profile.

`--memory-dir` and `--no-memory-dir` SHALL be mutually exclusive on this surface.

When an exact memory directory is stored on an easy profile, the stored value SHALL be the resolved absolute path.

`houmao-mgr project easy profile get --name <profile>` SHALL report whether the easy profile stores an exact memory directory, stores disabled memory binding, or stores no memory preference.

#### Scenario: Easy profile create stores one exact memory directory
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --memory-dir ../shared/alice-memory`
- **THEN** the stored easy profile records the resolved absolute path for `../shared/alice-memory`
- **AND THEN** later `project easy profile get --name alice` reports that stored absolute memory directory

#### Scenario: Easy profile create stores explicit disabled memory binding
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --no-memory-dir`
- **THEN** the stored easy profile records disabled memory binding
- **AND THEN** later `project easy profile get --name alice` reports that disabled state

### Requirement: `project easy instance launch/get` supports managed memory-directory binding
`houmao-mgr project easy instance launch` SHALL accept optional `--memory-dir <path>` and `--no-memory-dir` as one-off memory-binding controls.

`--memory-dir` and `--no-memory-dir` SHALL be mutually exclusive on this surface.

When neither flag is supplied, easy instance launch SHALL resolve memory binding from the selected easy profile's stored memory configuration and otherwise fall back to the system default behavior for that launch surface.

When easy instance launch resolves the system default behavior in project context, the default memory directory SHALL derive from the selected project overlay rather than from `--workdir`.

`houmao-mgr project easy instance get --name <instance>` SHALL report the resolved memory directory as an absolute path when enabled and as `null` when disabled.

#### Scenario: Easy-profile-backed launch uses the stored exact memory directory
- **WHEN** easy profile `alice` stores memory directory `/shared/alice-memory`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile alice --name alice-1`
- **THEN** the resulting managed session resolves memory directory `/shared/alice-memory`
- **AND THEN** later `project easy instance get --name alice-1` reports `/shared/alice-memory`

#### Scenario: Easy instance launch may explicitly disable memory binding
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name researcher-1 --no-memory-dir`
- **THEN** the resulting managed session resolves memory binding as disabled
- **AND THEN** later `project easy instance get --name researcher-1` reports `memory_dir: null`

#### Scenario: Easy instance default memory derives from the selected overlay instead of `--workdir`
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name researcher-1 --workdir /repo-b`
- **AND WHEN** no stored easy-profile memory configuration and no direct memory override are supplied
- **THEN** the resulting managed session resolves memory under `/repo-a/.houmao/memory/agents/<agent-id>/`
- **AND THEN** it does not derive the default memory directory from `/repo-b`
