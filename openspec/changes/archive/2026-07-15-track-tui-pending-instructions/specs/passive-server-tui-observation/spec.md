## ADDED Requirements

### Requirement: Passive-server TUI observation projects pending input consistently

The maintained passive-server observation path SHALL include `surface.pending_input` in compact TUI state, detailed TUI state, bounded history, and any managed-agent TUI projection that exposes the canonical tracked surface.

The projected field SHALL preserve the authoritative tracker value without deriving a second pending-input interpretation from parsed sidecar state, gateway requests, or passive-server submission records.

#### Scenario: Compact TUI state includes pending input

- **WHEN** a caller requests compact state for an observed TUI agent
- **THEN** the response surface includes `pending_input` alongside `accepting_input`, `editing_input`, and `ready_posture`
- **AND THEN** the value matches the authoritative current tracked snapshot

#### Scenario: Detailed and history responses preserve pending transitions

- **WHEN** an observed TUI changes from no provider-native pending instruction to a visible pending instruction
- **THEN** detailed state exposes the current `surface.pending_input=yes`
- **AND THEN** bounded history preserves the corresponding pending-input transition even when the turn phase remains active

#### Scenario: Passive-server projection does not infer pending from prompt submission

- **WHEN** the passive server proxies or records a prompt submission before the TUI observation changes
- **THEN** the projected pending-input value remains the tracker-owned value from the latest observed surface
- **AND THEN** the passive server does not set it from submission history
