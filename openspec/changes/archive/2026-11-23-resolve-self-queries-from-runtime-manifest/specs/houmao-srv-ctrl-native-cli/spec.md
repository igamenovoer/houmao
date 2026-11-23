# Spec Delta

## MODIFIED Requirements

### Requirement: `houmao-mgr agents gateway` supports current-session targeting for same-session tmux operation
Gateway commands that address one managed agent SHALL support existing explicit and current-session target scopes. Current-session targeting SHALL discover and verify the owning session through its manifest. Gateway operations SHALL use the verified manifest's runtime authority and current gateway binding.

#### Scenario: Gateway current-session targeting applies to managed operations
- **WHEN** a caller uses `attach`, `detach`, `status`, `prompt`, `interrupt`, `send-keys`, or `mail-notifier status|enable|disable` inside the owning tmux session
- **THEN** current-session scope selects that session
- **AND THEN** the CLI discovers the manifest through `HOUMAO_MANIFEST_PATH` or the live record named by `HOUMAO_AGENT_ID`
- **AND THEN** it performs the supported gateway operation using published runtime authority without reading the definition directory

#### Scenario: Current-session targeting requires the owning tmux session
- **WHEN** a caller requests tmux-backed current-session targeting without a verified binding to the owning tmux session
- **THEN** the CLI reports a missing target without guessing from cwd, gateway listener bindings, or unrelated tmux sessions

#### Scenario: Same-session send-keys resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents self gateway send-keys --sequence "<[Escape]>"` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** the CLI sends the control input to that session without requiring `--agent-id` or `--agent-name`

#### Scenario: Same-session notifier enable resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents self gateway mail-notifier enable --interval-seconds 60` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** the CLI enables notifier behavior on that session without requiring `--agent-id` or `--agent-name`

#### Scenario: Outside-tmux gateway control fails without explicit selectors
- **WHEN** an operator requests an operation that requires current tmux authority without that authority or an explicit selected-agent target
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd or ambient shell state

### Requirement: Self-status commands observe established current-session authority
The manager SHALL obtain agent details for `agents self state` and `agents self mail status` from the verified manifest. It SHALL observe state through its runtime bindings without reading launch definitions or writing registry, gateway, provider, or tmux state. Mailbox status SHALL retain existing signed gateway and local owner access rules.

#### Scenario: A DSH workspace-restricted process reads its own state
- **WHEN** an owned DSH headless session runs `houmao-mgr agents self state` with `workspace-write` and the registry outside the workspace
- **THEN** the command reports the current managed session's observed state
- **AND THEN** the query needs no write permission to the shared registry

#### Scenario: A DSH workspace-restricted process reads its mailbox status
- **WHEN** the current DSH session runs `houmao-mgr agents self mail status` from that sandbox
- **THEN** the command reports the configured channels and their availability using the established authorization
- **AND THEN** resolving the session does not publish a registry record or create gateway capability files

#### Scenario: Self status is requested with invalid authority
- **WHEN** current-session discovery cannot verify a matching managed manifest or current identity
- **THEN** the command reports the resolution error without creating or reviving a session or retrying with broader authority

#### Scenario: The gateway is detached from a live current session
- **WHEN** an authorized managed session requests mailbox status and no live gateway is attached
- **THEN** the manager uses the supported local status source and identifies unavailable channels
- **AND THEN** the query does not attach a gateway

#### Scenario: A manifest is valid and its live observer is unavailable
- **WHEN** self state can verify the session and lacks fresh runtime evidence for an observation
- **THEN** the result preserves the manifest-backed identity and reports the observation's actual availability
