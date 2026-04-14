## REMOVED Requirements

### Requirement: `houmao-mgr agents join` supports memory-directory controls for adopted sessions
**Reason**: Replaced by persist-lane controls under the unified workspace contract.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## ADDED Requirements

### Requirement: `houmao-mgr agents join` supports persist-lane controls for adopted sessions
`houmao-mgr agents join` SHALL accept optional `--persist-dir <path>` and `--no-persist-dir` for both TUI and headless tmux-backed adoption flows.

`--persist-dir` and `--no-persist-dir` SHALL be mutually exclusive on this surface.

When neither flag is supplied, `agents join` SHALL resolve persist binding from the selected join invocation context's system default behavior.

A successful join SHALL persist the resolved workspace root, scratch lane, persist binding, and optional persist lane for the adopted managed session.

#### Scenario: Joined session resolves default workspace lanes when no override is supplied
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer` without `--persist-dir` or `--no-persist-dir`
- **THEN** the adopted managed session resolves scratch under `/repo/.houmao/memory/agents/<agent-id>/scratch/`
- **AND THEN** the adopted managed session resolves persist under `/repo/.houmao/memory/agents/<agent-id>/persist/`
- **AND THEN** the join persists those resolved workspace lanes for later managed inspection

#### Scenario: Joined session may explicitly disable persistence
- **WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer --no-persist-dir`
- **THEN** the adopted managed session resolves persist binding as disabled
- **AND THEN** the join does not create or publish a persist directory for that session
- **AND THEN** the join still publishes a scratch lane for that session

#### Scenario: Joined session may bind one explicit shared persist directory
- **WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer --persist-dir /shared/reviewer`
- **THEN** the adopted managed session resolves persist binding to `/shared/reviewer`
- **AND THEN** the join persists that exact directory as the session's managed persist binding
