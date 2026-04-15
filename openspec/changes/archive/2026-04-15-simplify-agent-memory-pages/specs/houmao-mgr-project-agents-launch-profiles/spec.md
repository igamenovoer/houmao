## REMOVED Requirements

### Requirement: `project agents launch-profiles` manages explicit persist-lane defaults
**Reason**: Explicit launch profiles no longer manage persist-lane defaults.

**Migration**: Remove `--persist-dir`, `--no-persist-dir`, and `--clear-persist-dir` from launch-profile add/set surfaces and remove persisted persist fields from inspection output.

## ADDED Requirements

### Requirement: Project launch profiles omit managed memory persist controls
`houmao-mgr project agents launch-profiles add` and `set` SHALL NOT accept managed memory persist controls.

Launch-profile inspection SHALL NOT report `persist_dir`, `persist_disabled`, or `persist_binding` as current launch-profile fields.

#### Scenario: Add rejects persist-dir
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --persist-dir ../shared/alice-persist`
- **THEN** the command fails before writing the launch profile
- **AND THEN** the error identifies `--persist-dir` as unsupported

#### Scenario: Get omits persist fields
- **WHEN** an operator inspects launch profile `alice`
- **THEN** the output does not include `persist_dir`
- **AND THEN** the output does not include `persist_binding`
