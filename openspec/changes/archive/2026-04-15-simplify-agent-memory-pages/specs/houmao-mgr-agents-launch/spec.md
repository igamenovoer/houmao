## REMOVED Requirements

### Requirement: `houmao-mgr agents launch` supports one-off persist-lane controls
**Reason**: Direct launch no longer binds or disables a managed persist lane.

**Migration**: Use the default memo-pages memory root for small notes. Use the launched workdir or explicit project paths for artifacts and shared durable data.

## ADDED Requirements

### Requirement: `houmao-mgr agents launch` reports simplified managed memory paths
`houmao-mgr agents launch` SHALL create and report memory root, memo file, and pages directory for tmux-backed managed sessions.

The command SHALL NOT accept `--persist-dir` or `--no-persist-dir`.

When project context supplies the default memory root, the root SHALL derive from the selected source overlay rather than from `--workdir`.

Launch completion output SHALL NOT report scratch directory, persist binding, or persist directory as current memory fields.

#### Scenario: Project-context launch derives memory root from source overlay
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --workdir /repo-b`
- **THEN** the resulting managed launch resolves memory root under `/repo-a/.houmao/memory/agents/<agent-id>/`
- **AND THEN** it does not derive the default memory root from `/repo-b`

#### Scenario: Persist flags are not supported on launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --no-persist-dir`
- **THEN** the command fails before provider launch
- **AND THEN** the error identifies `--no-persist-dir` as unsupported
