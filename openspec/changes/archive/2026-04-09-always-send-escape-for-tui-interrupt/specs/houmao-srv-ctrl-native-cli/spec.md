## ADDED Requirements

### Requirement: `houmao-mgr agents interrupt` keeps TUI interrupt transport-neutral
`houmao-mgr agents interrupt` SHALL keep one transport-neutral operator contract across managed-agent transports.

For TUI-backed managed agents, the command SHALL dispatch one best-effort `Escape` interrupt signal through the resolved managed-agent control authority and SHALL NOT require the operator to know or supply raw TUI key semantics.

For TUI-backed managed agents, the command SHALL NOT reject or no-op solely because coarse tracked TUI phase currently reports `idle` or another non-active posture.

For headless managed agents, the command SHALL continue using the managed execution interrupt path and MAY return no-op behavior when no headless work is active.

#### Scenario: Operator interrupts a server-backed TUI agent without tracking-phase veto
- **WHEN** an operator runs `houmao-mgr agents interrupt --agent-id abc123` for a managed TUI agent
- **AND WHEN** the resolved managed-agent control path is reachable
- **AND WHEN** coarse tracked TUI phase is currently non-active
- **THEN** `houmao-mgr` still submits one best-effort TUI interrupt request
- **AND THEN** the operator is not forced to switch to a raw `send-keys` command just to deliver `Escape`

#### Scenario: Operator interrupt keeps headless no-op semantics
- **WHEN** an operator runs `houmao-mgr agents interrupt --agent-id abc123` for a managed headless agent with no active execution
- **THEN** `houmao-mgr` returns the headless interrupt no-op result
- **AND THEN** the command does not fabricate a delivered TUI-style `Escape` interrupt for headless state
