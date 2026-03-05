## ADDED Requirements

### Requirement: Runtime CLI uses `--agent-identity` for session control and drops `--session-manifest`
The system SHALL expose a `--agent-identity <name|manifest-path>` argument on runtime CLI commands that control an existing session (at minimum `send-prompt` and `stop-session`).

The system SHALL NOT accept `--session-manifest` on those commands.

#### Scenario: `send-prompt` targets a session via `--agent-identity`
- **WHEN** a developer runs the `send-prompt` CLI command with `--agent-identity <identity>`
- **THEN** the runtime resolves `<identity>` to a session manifest and sends the prompt to that session

#### Scenario: `stop-session` targets a session via `--agent-identity`
- **WHEN** a developer runs the `stop-session` CLI command with `--agent-identity <identity>`
- **THEN** the runtime resolves `<identity>` to a session manifest and stops that session

#### Scenario: Legacy `--session-manifest` is rejected
- **WHEN** a developer invokes `send-prompt` or `stop-session` with `--session-manifest`
- **THEN** the CLI rejects the invocation with an explicit argument validation error

### Requirement: CAO session start supports a human agent identity name and uses it as the tmux session name
When starting a CAO-backed session, the system SHALL allow the caller to provide an agent identity name via `start-session --agent-identity <name>` (name-only for CAO in this change).
For CAO-backed sessions, the system SHALL use the canonical `AGENTSYS-...` identity as the tmux session name.

If the caller does not provide a name, the system SHALL generate a short, easy-to-type name derived from the tool and role/blueprint identity, and SHALL add a conflict-avoiding suffix when needed.

#### Scenario: Start CAO session with an explicit name uses the canonical tmux session name
- **WHEN** a developer starts a CAO-backed session with `start-session --agent-identity gpu`
- **THEN** the tmux session name used for the session is `AGENTSYS-gpu`

#### Scenario: Start CAO session without a name auto-generates a short identity
- **WHEN** a developer starts a CAO-backed session without providing `--agent-identity`
- **THEN** the runtime selects a short `AGENTSYS-...` tmux session name derived from tool + role/blueprint
- **AND THEN** the selected name is unique among existing tmux sessions

### Requirement: CAO session start returns the selected agent identity
For CAO-backed sessions, the `start-session` CLI output SHALL include the selected canonical agent identity so callers can reuse it for subsequent prompt/stop operations.

#### Scenario: `start-session` output includes the canonical identity
- **WHEN** a developer starts a CAO-backed session
- **THEN** the `start-session` CLI output includes the selected canonical agent identity (for example `AGENTSYS-gpu`)
