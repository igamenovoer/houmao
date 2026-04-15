## REMOVED Requirements

### Requirement: `project easy profile create/get` supports reusable persist-lane defaults
**Reason**: Easy profiles no longer store reusable persist-lane defaults.

**Migration**: Remove `--persist-dir` and `--no-persist-dir` from easy profile creation and remove stored persist fields from easy profile inspection.

### Requirement: `project easy instance launch/get` supports managed workspace lanes and persist binding
**Reason**: Easy instance launch/get no longer exposes workspace lanes or persist binding.

**Migration**: Easy instances report memory root, memo file, and pages directory for the resolved managed session.

## ADDED Requirements

### Requirement: `project easy` surfaces use memo-pages managed memory
`houmao-mgr project easy profile create` and `project easy instance launch` SHALL NOT accept `--persist-dir` or `--no-persist-dir`.

`project easy instance get` SHALL report memory root, memo file, and pages directory when available.

`project easy profile get` SHALL NOT report reusable persist-lane defaults.

#### Scenario: Easy profile create rejects persist-dir
- **WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist cuda-coder --persist-dir ../shared/alice-persist`
- **THEN** the command fails before writing the profile
- **AND THEN** the error identifies `--persist-dir` as unsupported

#### Scenario: Easy instance get reports memory pages
- **WHEN** an operator runs `houmao-mgr project easy instance get --name researcher-1`
- **AND WHEN** the instance exposes managed memory metadata
- **THEN** the output reports the memory root
- **AND THEN** the output reports the memo file
- **AND THEN** the output reports the pages directory
- **AND THEN** the output does not report `persist_dir`
