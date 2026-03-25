## MODIFIED Requirements

### Requirement: Runtime-owned tmux sessions may publish gateway attachability independently from a running gateway
The runtime SHALL be able to make a tmux-backed session gateway-capable without requiring a gateway process to already be running.

For runtime-owned tmux-backed sessions, the runtime SHALL publish secret-free gateway attach metadata that later attach flows can use to start a gateway for the live session.

That attachability publication SHALL be additive and SHALL NOT make legacy non-gateway start or resume behavior fail by itself.

Blueprint `gateway.host` and `gateway.port` values SHALL act only as defaults after gateway attach is requested and SHALL NOT make a session gateway-capable or gateway-running by themselves.

In this change, the runtime SHALL publish attach metadata by default for newly started runtime-owned tmux-backed sessions and SHALL re-publish attach metadata on resume whenever attachability can be reconstructed from persisted session state. It SHALL support live gateway attach for every runtime-owned tmux-backed backend whose gateway execution adapter is implemented, including the runtime-owned REST-backed sessions, runtime-owned native headless sessions, and runtime-owned `local_interactive` sessions.

Gateway attach MAY happen later against the already-running tmux-backed session by using the published attach metadata, tmux session environment, and persisted manifest pointer for that session rather than by requiring gateway lifecycle decisions to be baked into the original launch command.

Supplying gateway listener overrides during session startup without a separate attach lifecycle action SHALL fail with an explicit error.

If a caller requests live gateway attach for any backend whose gateway adapter is not yet implemented, the runtime SHALL fail with an explicit unsupported-backend error rather than silently falling back to implicit direct control.

#### Scenario: Blueprint gateway defaults do not auto-attach the gateway by themselves
- **WHEN** a developer starts a session from a blueprint that declares `gateway.host` or `gateway.port`
- **AND WHEN** the developer does not invoke a separate gateway attach lifecycle action
- **THEN** the runtime publishes attachability metadata for that session
- **AND THEN** the blueprint listener defaults do not cause a live gateway instance to start by themselves

#### Scenario: Gateway host or port overrides require an attach action
- **WHEN** a developer supplies gateway host or port overrides during session startup without an explicit attach lifecycle action
- **THEN** the runtime fails with an explicit gateway-lifecycle error
- **AND THEN** the session is not treated as having a live gateway instance implicitly

#### Scenario: Later gateway attach reuses tmux session env and manifest-backed authority
- **WHEN** a developer starts a runtime-owned tmux-backed session and later invokes gateway attach from the same tmux session or another attach-aware control path
- **THEN** the runtime resolves that live session through the published attach metadata and tmux session environment for that session
- **AND THEN** the developer does not need to have coupled gateway startup to the original launch command

#### Scenario: Runtime-owned headless backend can attach a live gateway when its adapter exists
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed native headless session whose gateway execution adapter is implemented
- **THEN** the runtime attaches a live gateway for that headless session
- **AND THEN** the runtime does not reject that attach request merely because the session is not REST-backed

#### Scenario: Runtime-owned local interactive backend can attach a live gateway when its adapter exists
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed `local_interactive` session whose gateway execution adapter is implemented
- **THEN** the runtime attaches a live gateway for that session
- **AND THEN** the runtime does not reject that attach request merely because the session is a serverless local interactive TUI rather than a REST-backed or native headless session

#### Scenario: Unsupported backend still rejects live gateway attach explicitly
- **WHEN** a developer requests live gateway attach for a runtime-owned tmux-backed backend whose gateway execution adapter is not implemented
- **THEN** the runtime fails that attach request with an explicit unsupported-backend error
- **AND THEN** the runtime does not silently convert that attach request into legacy direct control
