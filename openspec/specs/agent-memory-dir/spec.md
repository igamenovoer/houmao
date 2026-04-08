## Purpose
Define the optional durable memory-directory binding contract for tmux-backed managed sessions.

## Requirements

### Requirement: Managed sessions support an optional durable memory-directory binding
Tmux-backed managed sessions SHALL support one optional durable memory-directory binding that resolves to exactly one of these outcomes:

- `auto`, which derives the default memory directory as `<active-overlay>/memory/agents/<agent-id>/`
- `exact`, which binds the session to one explicit operator-supplied directory path
- `disabled`, which binds no memory directory for that session

When a session resolves to `auto` or `exact`, the system SHALL ensure the resolved directory exists before launch or join completes successfully.

When a session resolves to `disabled`, the system SHALL not create a memory directory for that session.

The system SHALL allow explicit exact-path binding to target any usable directory, including one intentionally shared by multiple managed agents.

#### Scenario: Auto memory binding uses the conservative overlay-local default
- **WHEN** a tmux-backed managed session resolves memory binding in `auto` mode for agent `researcher`
- **AND WHEN** the selected active overlay is `/repo/.houmao`
- **THEN** the resolved memory directory is `/repo/.houmao/memory/agents/researcher/`
- **AND THEN** the system ensures that directory exists before the session is considered launched or joined

#### Scenario: Exact memory binding may point multiple agents at one shared directory
- **WHEN** one operator launches or joins agent `reviewer-a` with `--memory-dir /shared/notes`
- **AND WHEN** another operator launches or joins agent `reviewer-b` with `--memory-dir /shared/notes`
- **THEN** both managed sessions resolve memory binding in `exact` mode at `/shared/notes`
- **AND THEN** the system accepts that shared directory as explicit operator intent

#### Scenario: Disabled memory binding creates no directory
- **WHEN** a tmux-backed managed session resolves memory binding in `disabled` mode
- **THEN** the system does not create any memory directory for that session
- **AND THEN** the session remains valid without a bound durable memory path

### Requirement: Managed memory binding is discoverable through runtime-backed inspection
For every tmux-backed managed session, the runtime SHALL persist the resolved memory-binding result in session-owned runtime state.

When memory is enabled, that runtime state SHALL include the resolved absolute directory path.

When memory is disabled, that runtime state SHALL preserve the disabled result without fabricating a placeholder directory path.

When memory is enabled, the running tmux session environment SHALL publish `HOUMAO_MEMORY_DIR=<absolute-path>`.

When memory is disabled, the running tmux session environment SHALL not publish `HOUMAO_MEMORY_DIR`.

Supported `houmao-mgr` inspection surfaces for the managed session SHALL report the resolved memory directory as an absolute path when enabled and as `null` when disabled.

#### Scenario: Enabled memory binding is visible through manifest, env, and CLI inspection
- **WHEN** managed agent `researcher` is running with resolved memory directory `/repo/.houmao/memory/agents/researcher/`
- **THEN** the session-owned runtime state records that absolute memory directory
- **AND THEN** the tmux session environment publishes `HOUMAO_MEMORY_DIR=/repo/.houmao/memory/agents/researcher/`
- **AND THEN** supported `houmao-mgr` inspection surfaces report `/repo/.houmao/memory/agents/researcher/` as the resolved memory directory

#### Scenario: Disabled memory binding reports null and omits the env var
- **WHEN** managed agent `researcher` is running with memory binding disabled
- **THEN** the session-owned runtime state records that memory is disabled without inventing a path
- **AND THEN** the tmux session environment does not publish `HOUMAO_MEMORY_DIR`
- **AND THEN** supported `houmao-mgr` inspection surfaces report `memory_dir: null`

### Requirement: Houmao does not define or clean memory-directory contents
Houmao SHALL treat the memory directory as operator-owned or agent-owned durable filesystem state.

Houmao SHALL NOT require any fixed subdirectory layout, Markdown file names, metadata sidecars, or catalog indexing inside the memory directory.

Cleanup flows that stop, remove, or garbage-collect managed runtime state SHALL NOT delete the resolved memory directory only because one managed session stopped or was cleaned up.

#### Scenario: Session cleanup preserves the memory directory
- **WHEN** a managed session previously used memory directory `/repo/.houmao/memory/agents/researcher/`
- **AND WHEN** an operator stops or cleans up that managed session through supported runtime cleanup flows
- **THEN** the managed runtime state may be removed according to normal cleanup rules
- **AND THEN** `/repo/.houmao/memory/agents/researcher/` and its contents remain untouched
