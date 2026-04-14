## REMOVED Requirements

### Requirement: `houmao-mgr agents launch` supports one-off memory-directory controls
**Reason**: Replaced by persist-lane controls under the unified workspace contract.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports one-off persist-lane controls
`houmao-mgr agents launch` SHALL accept optional `--persist-dir <path>` and `--no-persist-dir` launch-time controls for tmux-backed managed sessions.

`--persist-dir` and `--no-persist-dir` SHALL be mutually exclusive on this surface.

When neither flag is supplied, `agents launch` SHALL resolve persist binding from any selected launch-profile persist configuration and otherwise fall back to the system default behavior for that launch surface.

When `agents launch` resolves the system default behavior in project context, the default persist lane SHALL derive from the selected source overlay rather than from `--workdir`.

Launch completion output SHALL report workspace root, scratch directory, persist binding, and persist directory when enabled.

#### Scenario: Project-context launch derives persist lane from the source overlay
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --workdir /repo-b`
- **AND WHEN** no stored launch-profile persist configuration and no direct persist override are supplied
- **THEN** the resulting managed launch resolves persist lane under `/repo-a/.houmao/memory/agents/<agent-id>/persist/`
- **AND THEN** it does not derive the default persist lane from `/repo-b`

#### Scenario: Explicit no-persist override suppresses the persist lane
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --no-persist-dir`
- **THEN** the resulting managed launch resolves persist binding as disabled
- **AND THEN** the launch still creates a scratch lane for that managed agent

#### Scenario: Explicit persist-dir override wins over a profile that disables persistence
- **WHEN** launch profile `alice` stores disabled persist binding
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --persist-dir /tmp/alice-persist`
- **THEN** the resulting managed launch resolves persist directory `/tmp/alice-persist`
- **AND THEN** the stored launch profile still records disabled persist binding as its reusable default
