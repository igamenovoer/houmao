## ADDED Requirements

### Requirement: Live tracked-state reduction SHALL be implemented through the shared TUI tracking core
For supported parsed tmux-backed sessions, the server SHALL derive tracked-state semantics for diagnostics posture, `surface`, `turn`, `last_turn`, and stability through the repo-owned shared TUI tracking core rather than through a package-local reducer that replay and validation tools cannot reuse.

The server SHALL remain responsible for live tmux/process/probe observation, session identity, explicit prompt-submission capture, and in-memory authority, but the tracked-state reduction itself SHALL come from the shared core.

#### Scenario: Live cycle adapts parsed surface and diagnostics into the shared core
- **WHEN** the server records one live tracking cycle for a supported tmux-backed session
- **THEN** it supplies parsed-surface observations, diagnostics, and any explicit prompt-submission evidence to the shared core
- **AND THEN** the published tracked-state response preserves the official live contract while sharing reduction semantics with replay consumers

#### Scenario: Server-owned input remains authoritative through the shared core
- **WHEN** the server accepts prompt input through its owned input route
- **THEN** the live adapter arms turn authority in the shared core from that explicit input event
- **AND THEN** later tracked state can still report `last_turn.source=explicit_input`
