## ADDED Requirements

### Requirement: Shared-registry creation follows launch authority and cleanup follows the terminating actor
The system SHALL create a shared-registry record for a live agent according to the authority that launched or admitted that agent.

The launch authority SHALL be persisted in runtime-readable session or authority metadata so runtime and `houmao-server` consult the same signal before any shared-registry publish or refresh attempt.

For agents created or admitted through `houmao-server`-owned authority, `houmao-server` SHALL create and refresh the shared-registry record for that agent.

For direct runtime-owned workflows outside `houmao-server`-owned admission, runtime publication MAY continue to create and refresh the shared-registry record for that live agent.

Discovery or later management by `houmao-server` SHALL NOT by itself transfer shared-registry creation responsibility or imply that `houmao-server` must republish an already valid live entry.

The system SHALL assign shared-registry cleanup responsibility to the actor that terminates the live agent. If a user or external launcher terminates the agent outside `houmao-server` control, that same actor remains responsible for removing or repairing the registry entry.

The system SHALL NOT infer launch authority or cleanup responsibility from current shared-registry contents alone.

This launch-and-cleanup split SHALL NOT change the pointer-oriented nature of the shared registry. Regardless of who writes or clears the record, the shared-registry entry SHALL remain a secret-free locator layer that points at runtime-owned or server-owned artifacts rather than copying queue state, mailbox content, or other mutable per-agent control state into the registry.

#### Scenario: Server-launched managed headless agent is published by `houmao-server`
- **WHEN** `houmao-server` launches and admits a managed headless agent through its own launch authority
- **THEN** `houmao-server` creates and refreshes the shared-registry record for that agent
- **AND THEN** the registry record continues to publish only secret-free pointers rather than per-agent queue or mailbox state

#### Scenario: Pair-managed server-admitted TUI agent is published by `houmao-server`
- **WHEN** a TUI agent is admitted into `houmao-server` authority through the supported pair-managed launch path
- **THEN** `houmao-server` creates and refreshes the shared-registry record for that agent
- **AND THEN** runtime-owned session and gateway pointers remain the source material for that published record rather than a copied runtime payload

#### Scenario: Direct runtime-owned workflow continues runtime publication
- **WHEN** a live tmux-backed session is created through a direct runtime-owned workflow outside `houmao-server`-owned admission
- **THEN** the runtime may continue creating and refreshing the shared-registry record for that session
- **AND THEN** the registry does not require a running `houmao-server` instance solely to publish that direct runtime-owned session

#### Scenario: Runtime consults persisted launch authority and defers registry writes
- **WHEN** a runtime-managed session started under `houmao-server` authority reads launch metadata showing that `houmao-server` launched that session
- **THEN** the runtime does not independently publish or refresh the shared-registry record for that session
- **AND THEN** it still preserves the pointer artifacts that `houmao-server` needs for its own registry publication

#### Scenario: Server discovery does not republish an externally launched live agent
- **WHEN** `houmao-server` reads a valid shared-registry entry for an externally launched live agent
- **THEN** `houmao-server` may manage that agent through its APIs
- **AND THEN** it does not republish or overwrite the existing registry entry solely because discovery occurred

#### Scenario: Terminating actor clears or repairs the registry entry
- **WHEN** an externally launched live agent is terminated through a `houmao-server` termination path after discovery
- **THEN** `houmao-server` clears or updates the shared-registry entry as part of keeping registry integrity
- **AND THEN** cleanup responsibility follows the terminating actor rather than the original discovering actor

#### Scenario: Manual external termination keeps cleanup responsibility external
- **WHEN** an externally launched live agent is terminated manually outside `houmao-server` control
- **THEN** the external actor remains responsible for removing or repairing the shared-registry entry
- **AND THEN** the system does not assume discovery alone transferred cleanup ownership to `houmao-server`
