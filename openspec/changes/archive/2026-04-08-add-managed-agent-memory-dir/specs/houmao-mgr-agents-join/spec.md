## ADDED Requirements

### Requirement: `houmao-mgr agents join` supports memory-directory controls for adopted sessions
`houmao-mgr agents join` SHALL accept optional `--memory-dir <path>` and `--no-memory-dir` for both TUI and headless tmux-backed adoption flows.

`--memory-dir` and `--no-memory-dir` SHALL be mutually exclusive on this surface.

When neither flag is supplied, `agents join` SHALL resolve memory binding from the selected join invocation context's system default behavior.

A successful join SHALL persist the resolved memory binding for the adopted managed session without requiring the adopted tool to use any fixed memory-directory structure.

#### Scenario: Joined session resolves the default memory directory when no override is supplied
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer` without `--memory-dir` or `--no-memory-dir`
- **THEN** the adopted managed session resolves memory under `/repo/.houmao/memory/agents/<agent-id>/`
- **AND THEN** the join persists that resolved memory binding for later managed inspection

#### Scenario: Joined session may explicitly disable memory binding
- **WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer --no-memory-dir`
- **THEN** the adopted managed session resolves memory binding as disabled
- **AND THEN** the join does not create or publish a memory directory for that session

#### Scenario: Joined session may bind one explicit shared memory directory
- **WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer --memory-dir /shared/reviewer`
- **THEN** the adopted managed session resolves memory binding to `/shared/reviewer`
- **AND THEN** the join persists that exact directory as the session's managed memory binding
