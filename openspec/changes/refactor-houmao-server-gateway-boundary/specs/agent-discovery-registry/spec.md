## ADDED Requirements

### Requirement: Shared-registry publication follows agent creation authority
The system SHALL choose one shared-registry publisher for a live agent based on the authority that created or admitted that agent.

The selected publisher SHALL be persisted in runtime-readable session or authority metadata so runtime and `houmao-server` consult the same signal before publish, refresh, or teardown.

For agents created or admitted through `houmao-server`-owned authority, `houmao-server` SHALL create and refresh the shared-registry record for that agent.

For direct runtime-owned workflows outside `houmao-server`-owned admission, runtime publication MAY continue to create and refresh the shared-registry record for that live agent.

The system SHALL NOT infer publisher identity from current shared-registry contents alone.

This publisher split SHALL NOT change the pointer-oriented nature of the shared registry. Regardless of publisher, the shared-registry record SHALL remain a secret-free locator layer that points at runtime-owned or server-owned artifacts rather than copying queue state, mailbox content, or other mutable per-agent control state into the registry.

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

#### Scenario: Server-managed runtime consults persisted publisher selection and defers registry writes
- **WHEN** a runtime-managed session started under `houmao-server` authority reads publisher metadata that selects `houmao-server` as the shared-registry writer
- **THEN** the runtime does not independently publish or refresh the shared-registry record for that session
- **AND THEN** it still preserves the pointer artifacts that `houmao-server` needs for its own registry publication
