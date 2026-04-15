## REMOVED Requirements

### Requirement: `houmao-mgr agents join` supports persist-lane controls for adopted sessions
**Reason**: Joined managed sessions no longer bind or disable persist lanes.

**Migration**: Joined sessions receive the same memo-pages memory root, memo file, and pages directory as native launches.

## ADDED Requirements

### Requirement: `houmao-mgr agents join` creates memo-pages memory for adopted sessions
`houmao-mgr agents join` SHALL create and persist memory root, memo file, and pages directory for adopted tmux-backed sessions.

The command SHALL NOT accept `--persist-dir` or `--no-persist-dir`.

A successful join SHALL publish `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR` into the adopted session environment when the backend supports environment publication.

#### Scenario: Joined session resolves default memory pages
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer`
- **THEN** the adopted managed session resolves memory root under `/repo/.houmao/memory/agents/<agent-id>/`
- **AND THEN** the adopted managed session resolves pages under `/repo/.houmao/memory/agents/<agent-id>/pages/`
- **AND THEN** the join persists those resolved memory paths for later managed inspection

#### Scenario: Persist flags are not supported on join
- **WHEN** an operator runs `houmao-mgr agents join --agent-name reviewer --persist-dir /shared/reviewer`
- **THEN** the command fails before adopting the session
- **AND THEN** the error identifies `--persist-dir` as unsupported
