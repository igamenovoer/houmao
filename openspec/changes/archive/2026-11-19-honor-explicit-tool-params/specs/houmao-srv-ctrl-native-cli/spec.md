# Spec Delta

## ADDED Requirements

### Requirement: Self-status commands observe established current-session authority

The manager SHALL resolve `agents self state` and `agents self mail status` through verified current-session authority without requiring the caller to publish registry or gateway state, acquire a registry write lock, rewrite provider files, or modify tmux state. Mailbox status SHALL retain existing signed gateway and local owner access rules.

#### Scenario: A DSH workspace-restricted process reads its own state

- **WHEN** an owned DSH headless session executes `houmao-mgr agents self state` within an effective `workspace-write` sandbox and the registry is outside that workspace
- **THEN** the command reports the current managed session's observed state
- **AND THEN** the query needs no write permission to the shared registry

#### Scenario: A DSH workspace-restricted process reads its mailbox status

- **WHEN** the current DSH session executes `houmao-mgr agents self mail status` from that sandbox
- **THEN** the command reports the configured channels and their availability using the established authorization
- **AND THEN** resolving the session does not publish a registry record or create gateway capability files

#### Scenario: Self status is requested with invalid authority

- **WHEN** current-session discovery cannot verify a matching managed manifest or current identity
- **THEN** the command reports the resolution error without creating or reviving a session or retrying with broader authority

#### Scenario: The gateway is detached from a live current session

- **WHEN** an authorized managed session requests mailbox status and no live gateway is attached
- **THEN** the manager uses the supported local status source and identifies unavailable channels
- **AND THEN** the query does not attach a gateway
