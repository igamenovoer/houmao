## ADDED Requirements

### Requirement: Attached gateways can own live tracked state for runtime-owned local interactive sessions
For a runtime-owned `local_interactive` TUI session outside `houmao-server`, when an attached gateway is present and healthy, that gateway SHALL be allowed to act as the active control plane for live tracked-state authority for that session.

For this runtime-owned path, the active control plane SHALL be allowed to use the runtime-owned session identifier as the tracked-session identity and SHALL NOT require a CAO-style terminal alias so long as the public compatibility alias can fall back to the tracked session id.

#### Scenario: Gateway becomes the tracking owner for runtime-owned local interactive session
- **WHEN** a runtime-owned `local_interactive` TUI session outside `houmao-server` has an attached healthy gateway
- **THEN** the gateway owns continuous live tracked-state reduction for that session
- **AND THEN** the tracked identity for that session may be anchored by the runtime session id rather than by a CAO terminal id

### Requirement: Gateway-owned local interactive tracking preserves explicit-input authority
When prompt input for a runtime-owned `local_interactive` session is accepted through an attached gateway, the active gateway-owned control plane SHALL preserve that explicit-input evidence for tracked turn reduction in the same way as other gateway-owned tracked TUI flows.

#### Scenario: Gateway prompt note preserves explicit-input provenance for runtime-owned local interactive session
- **WHEN** an attached gateway accepts and executes prompt input for a runtime-owned `local_interactive` session outside `houmao-server`
- **THEN** the gateway forwards that explicit prompt-submission evidence to the active tracking control plane for that session
- **AND THEN** later tracked state for that session can report explicit-input provenance for the resulting completed turn
