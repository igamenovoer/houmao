## REMOVED Requirements

### Requirement: Runtime resolves managed workspace lanes before session publication
**Reason**: Runtime no longer resolves managed workspace lanes.

**Migration**: Runtime resolves the managed memory root, memo file, and pages directory before session publication.

### Requirement: Runtime publishes workspace lanes through manifest-backed state and environment
**Reason**: Workspace lane metadata and environment variables are removed.

**Migration**: Runtime persists and publishes memo-pages memory metadata and `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`.

## ADDED Requirements

### Requirement: Runtime resolves managed memory pages before session publication
For tmux-backed managed sessions, the runtime SHALL resolve memory root, memo file, and pages directory before publishing the session as live.

That resolved memory state SHALL be preserved for native managed launch, managed join of an existing tmux-backed session, and managed relaunch of an existing runtime-owned tmux-backed session.

When memory state resolves in the default mode, the runtime SHALL derive the memory root from the selected active overlay and authoritative `agent-id` rather than from `session-id` or runtime workdir.

#### Scenario: Native managed launch persists the overlay-local memory root
- **WHEN** a native managed launch for agent id `researcher-id` uses active overlay `/repo/.houmao`
- **THEN** the runtime resolves memory root `/repo/.houmao/memory/agents/researcher-id/`
- **AND THEN** it resolves memo file `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** it resolves pages directory `/repo/.houmao/memory/agents/researcher-id/pages/`
- **AND THEN** it persists that resolved memory state before publishing the live session

#### Scenario: Relaunch preserves the previously resolved memory paths
- **WHEN** managed agent `researcher` already has manifest-persisted memory root `/repo/.houmao/memory/agents/researcher-id/`
- **AND WHEN** Houmao relaunches that managed agent
- **THEN** the relaunched session reuses the manifest-persisted memory root, memo file, and pages directory
- **AND THEN** relaunch does not derive memory paths from the new session id

### Requirement: Runtime publishes memory pages through manifest-backed state and environment
For tmux-backed managed sessions, the runtime SHALL persist `memory_root`, `memo_file`, and `pages_dir` as session-owned runtime metadata.

The runtime SHALL publish `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR` into the live session environment before provider startup completes.

The runtime SHALL NOT publish workspace-lane metadata or `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_SCRATCH_DIR`, or `HOUMAO_AGENT_PERSIST_DIR`.

#### Scenario: Runtime manifest records memory pages
- **WHEN** a tmux-backed managed runtime resolves memory root `/repo/.houmao/memory/agents/researcher-id/`
- **THEN** the session-owned runtime metadata stores that memory root as an absolute path
- **AND THEN** it stores the memo file as an absolute path
- **AND THEN** it stores the pages directory as an absolute path
- **AND THEN** it does not store `scratch_dir`, `persist_binding`, or `persist_dir` as current memory metadata

#### Scenario: Runtime environment publishes memory variables
- **WHEN** a tmux-backed managed runtime resolves pages directory `/repo/.houmao/memory/agents/researcher-id/pages/`
- **THEN** the live tmux session environment contains `HOUMAO_AGENT_MEMORY_DIR`
- **AND THEN** the live tmux session environment contains `HOUMAO_AGENT_MEMO_FILE`
- **AND THEN** the live tmux session environment contains `HOUMAO_AGENT_PAGES_DIR`
- **AND THEN** the live tmux session environment does not contain `HOUMAO_AGENT_SCRATCH_DIR`
