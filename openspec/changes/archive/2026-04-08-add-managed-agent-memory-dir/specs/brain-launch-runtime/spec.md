## ADDED Requirements

### Requirement: Managed runtime launch, join, and relaunch preserve resolved memory binding
For tmux-backed managed sessions, the runtime SHALL resolve the session's effective memory binding before publishing the session as live.

That resolved memory binding SHALL be preserved for:

- native managed launch,
- managed join of an existing tmux-backed session,
- managed relaunch of an existing runtime-owned tmux-backed session.

When a session resolves memory in `auto` mode, the runtime SHALL derive the default path from the selected active overlay and authoritative `agent-id` rather than from `session-id` or runtime workdir.

When a runtime-owned managed session is relaunched, the relaunch flow SHALL reuse the manifest-persisted resolved memory binding for that managed agent unless a stronger supported relaunch override is introduced by a later change.

#### Scenario: Native managed launch persists the overlay-local auto memory binding
- **WHEN** a native tmux-backed managed launch selects overlay `/repo/.houmao` for agent `researcher`
- **AND WHEN** that launch does not receive `--memory-dir` or `--no-memory-dir`
- **THEN** the runtime resolves memory binding to `/repo/.houmao/memory/agents/researcher/`
- **AND THEN** it persists that resolved binding before publishing the live session

#### Scenario: Managed join persists one explicit memory binding for the adopted session
- **WHEN** an operator joins an existing tmux-backed session with `--memory-dir /shared/reviewer`
- **THEN** the join runtime persists `/shared/reviewer` as the adopted session's resolved memory binding
- **AND THEN** later managed inspection and control use that persisted binding rather than recomputing a different default

#### Scenario: Relaunch preserves the previously resolved memory binding
- **WHEN** managed agent `researcher` already has manifest-persisted resolved memory directory `/repo/.houmao/memory/agents/researcher/`
- **AND WHEN** an operator relaunches that managed agent through the supported relaunch surface
- **THEN** the relaunched session reuses `/repo/.houmao/memory/agents/researcher/` as its resolved memory binding
- **AND THEN** relaunch does not derive a different default memory directory from the new session id

### Requirement: Managed runtime publishes resolved memory binding through manifest-backed state and environment
For tmux-backed managed sessions, the runtime SHALL persist the resolved memory binding as session-owned runtime metadata.

When memory is enabled, that runtime metadata SHALL store the resolved absolute directory path.

When memory is disabled, that runtime metadata SHALL store that disabled result without inventing a placeholder path.

When memory is enabled, the runtime SHALL publish `HOUMAO_MEMORY_DIR` into the live tmux session environment before provider startup completes.

When memory is disabled, the runtime SHALL omit `HOUMAO_MEMORY_DIR` from the live tmux session environment.

#### Scenario: Enabled managed runtime publishes the resolved memory directory
- **WHEN** a tmux-backed managed runtime resolves memory directory `/repo/.houmao/memory/agents/researcher/`
- **THEN** the session-owned runtime metadata stores `/repo/.houmao/memory/agents/researcher/` as an absolute path
- **AND THEN** the live tmux session environment contains `HOUMAO_MEMORY_DIR=/repo/.houmao/memory/agents/researcher/`

#### Scenario: Disabled managed runtime omits the memory env var
- **WHEN** a tmux-backed managed runtime resolves memory binding as disabled
- **THEN** the session-owned runtime metadata records that disabled state
- **AND THEN** the live tmux session environment does not contain `HOUMAO_MEMORY_DIR`
