## Purpose
Define the optional durable memory-directory binding contract for tmux-backed managed sessions.
## Requirements
### Requirement: Managed sessions support optional persistent memory through the persist lane
Tmux-backed managed sessions SHALL support optional persistent memory through a persist lane that resolves to exactly one of these outcomes:

- `auto`, which derives the default persist lane as `<active-overlay>/memory/agents/<agent-id>/persist/`
- `exact`, which binds the persist lane to one explicit operator-supplied directory path
- `disabled`, which binds no persist lane for that session

When persistence resolves to `auto` or `exact`, the system SHALL ensure the resolved persist directory exists before launch or join completes successfully.

When persistence resolves to `disabled`, the system SHALL not create a persist directory for that session.

The system SHALL allow exact persist binding to target any usable directory, including one intentionally shared by multiple managed agents.

#### Scenario: Auto persist binding uses the workspace persist lane
- **WHEN** a tmux-backed managed session resolves persistence in `auto` mode for agent id `researcher-id`
- **AND WHEN** the selected active overlay is `/repo/.houmao`
- **THEN** the resolved persist directory is `/repo/.houmao/memory/agents/researcher-id/persist/`
- **AND THEN** the system ensures that directory exists before the session is considered launched or joined

#### Scenario: Exact persist binding may point multiple agents at one shared directory
- **WHEN** one operator launches or joins agent `reviewer-a` with `--persist-dir /shared/notes`
- **AND WHEN** another operator launches or joins agent `reviewer-b` with `--persist-dir /shared/notes`
- **THEN** both managed sessions resolve persistence in `exact` mode at `/shared/notes`
- **AND THEN** the system accepts that shared directory as explicit operator intent

#### Scenario: Disabled persist binding creates no persist directory
- **WHEN** a tmux-backed managed session resolves persistence in `disabled` mode
- **THEN** the system does not create a persist directory for that session
- **AND THEN** the session remains valid with its scratch lane still available

### Requirement: Managed persist binding is discoverable through runtime-backed inspection
For every tmux-backed managed session, the runtime SHALL persist the resolved persist-binding result in session-owned runtime state.

When persistence is enabled, that runtime state SHALL include the resolved absolute persist directory path.

When persistence is disabled, that runtime state SHALL preserve the disabled result without fabricating a placeholder persist directory path.

Supported `houmao-mgr` inspection surfaces for the managed session SHALL report the workspace root, scratch directory, persist binding, and persist directory as an absolute path when enabled or as `null` when disabled.

#### Scenario: Enabled persist binding is visible through manifest env and CLI inspection
- **WHEN** managed agent `researcher` is running with persist directory `/repo/.houmao/memory/agents/researcher-id/persist/`
- **THEN** the session-owned runtime state records that absolute persist directory
- **AND THEN** the tmux session environment publishes `HOUMAO_AGENT_PERSIST_DIR=/repo/.houmao/memory/agents/researcher-id/persist`
- **AND THEN** supported `houmao-mgr` inspection surfaces report the resolved persist directory

#### Scenario: Disabled persist binding reports null and omits the env var
- **WHEN** managed agent `researcher` is running with persistence disabled
- **THEN** the session-owned runtime state records that persistence is disabled without inventing a path
- **AND THEN** the tmux session environment does not publish `HOUMAO_AGENT_PERSIST_DIR`
- **AND THEN** supported `houmao-mgr` inspection surfaces report `persist_dir: null`
