## REMOVED Requirements

### Requirement: Runtime creates and reuses a per-agent job dir for each started session
**Reason**: Replaced by the per-agent workspace scratch lane and `HOUMAO_AGENT_SCRATCH_DIR`.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

### Requirement: Managed runtime launch, join, and relaunch preserve resolved memory binding
**Reason**: Replaced by persist-lane binding under the unified workspace contract.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

### Requirement: Managed runtime publishes resolved memory binding through manifest-backed state and environment
**Reason**: Replaced by workspace root, scratch lane, persist binding, and persist lane publication.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## ADDED Requirements

### Requirement: Runtime resolves managed workspace lanes before session publication
For tmux-backed managed sessions, the runtime SHALL resolve workspace root, memo file, scratch lane, persist binding, and optional persist lane before publishing the session as live.

That resolved workspace state SHALL be preserved for native managed launch, managed join of an existing tmux-backed session, and managed relaunch of an existing runtime-owned tmux-backed session.

When workspace state resolves in the default mode, the runtime SHALL derive the workspace root from the selected active overlay and authoritative `agent-id` rather than from `session-id` or runtime workdir.

#### Scenario: Native managed launch persists the overlay-local workspace
- **WHEN** a native tmux-backed managed launch selects overlay `/repo/.houmao` for agent id `researcher-id`
- **THEN** the runtime resolves workspace root `/repo/.houmao/memory/agents/researcher-id/`
- **AND THEN** it resolves memo file `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** it resolves scratch lane `/repo/.houmao/memory/agents/researcher-id/scratch/`
- **AND THEN** it persists that resolved workspace state before publishing the live session

#### Scenario: Managed join persists workspace lanes for the adopted session
- **WHEN** an operator joins an existing tmux-backed session for agent id `reviewer-id`
- **AND WHEN** the active overlay is `/repo/.houmao`
- **THEN** the join runtime persists workspace root `/repo/.houmao/memory/agents/reviewer-id/`
- **AND THEN** the join runtime persists memo file `/repo/.houmao/memory/agents/reviewer-id/houmao-memo.md`
- **AND THEN** later managed inspection and control use that persisted workspace state rather than recomputing a different default

#### Scenario: Relaunch preserves the previously resolved workspace
- **WHEN** managed agent `researcher` already has manifest-persisted workspace root `/repo/.houmao/memory/agents/researcher-id/`
- **AND WHEN** an operator relaunches that managed agent through the supported relaunch surface
- **THEN** the relaunched session reuses the manifest-persisted workspace root, memo file, and lanes
- **AND THEN** relaunch does not derive a scratch directory from the new session id

### Requirement: Runtime publishes workspace lanes through manifest-backed state and environment
For tmux-backed managed sessions, the runtime SHALL persist workspace root, memo file, scratch lane, persist binding, and optional persist lane as session-owned runtime metadata.

The runtime SHALL publish `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_SCRATCH_DIR` into the live session environment before provider startup completes.

When persistence is enabled, the runtime SHALL publish `HOUMAO_AGENT_PERSIST_DIR` into the live session environment.

When persistence is disabled, the runtime SHALL omit `HOUMAO_AGENT_PERSIST_DIR`.

#### Scenario: Runtime manifest records workspace lanes
- **WHEN** a tmux-backed managed runtime resolves workspace root `/repo/.houmao/memory/agents/researcher-id/`
- **THEN** the session-owned runtime metadata stores that workspace root as an absolute path
- **AND THEN** it stores the memo file as an absolute path
- **AND THEN** it stores the scratch lane as an absolute path
- **AND THEN** it stores the persist binding and persist path when persistence is enabled

#### Scenario: Runtime environment publishes new workspace variables
- **WHEN** a tmux-backed managed runtime resolves scratch lane `/repo/.houmao/memory/agents/researcher-id/scratch/`
- **THEN** the live tmux session environment contains `HOUMAO_AGENT_STATE_DIR`
- **AND THEN** the live tmux session environment contains `HOUMAO_AGENT_MEMO_FILE`
- **AND THEN** the live tmux session environment contains `HOUMAO_AGENT_SCRATCH_DIR`
- **AND THEN** the live tmux session environment does not contain `HOUMAO_JOB_DIR`
