## MODIFIED Requirements

### Requirement: Live tracked-state reduction SHALL be implemented through the shared TUI tracking core
For supported parsed tmux-backed sessions, the server SHALL derive tracker-owned `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics through the repo-owned shared TUI tracking core rather than through a package-local reducer that replay and validation tools cannot reuse.

The server SHALL remain responsible for live tmux/process/probe observation, session identity, explicit prompt-submission capture, parsed-surface metadata, diagnostics, lifecycle readiness/completion pipelines, effective visible stability, and in-memory authority, but the tracker-owned reduction itself SHALL come from the shared standalone tracker session.

The server's live adapter SHALL feed raw captured TUI snapshot text and any explicit prompt-submission evidence into that shared tracker and SHALL then merge the resulting tracker state back into the published live contract together with server-owned diagnostics, lifecycle snapshots, and visible-stability metadata.

#### Scenario: Live cycle adapts raw TUI snapshot and diagnostics into the shared core
- **WHEN** the server records one live tracking cycle for a supported tmux-backed session
- **THEN** it supplies the captured raw TUI snapshot and any explicit prompt-submission evidence to the shared core
- **AND THEN** it keeps tmux/process/probe/parse diagnostics and lifecycle readiness/completion under server ownership
- **AND THEN** the published tracked-state response preserves the official live contract while sharing tracker reduction semantics with replay consumers

#### Scenario: Server-owned input remains authoritative through the shared core
- **WHEN** the server accepts prompt input through its owned input route
- **THEN** the live adapter arms turn authority in the shared core from that explicit input event
- **AND THEN** later tracked state can still report `last_turn.source=explicit_input`

#### Scenario: Visible stability remains server-owned when diagnostics participate
- **WHEN** the published live stability signature depends on transport/process/parse diagnostics or other host-owned fields in addition to tracker state
- **THEN** the server computes the visible stability view over the merged live contract
- **AND THEN** tracker-owned stability from the shared core remains limited to tracker-state transitions
