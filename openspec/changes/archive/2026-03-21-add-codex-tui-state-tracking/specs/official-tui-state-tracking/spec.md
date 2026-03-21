## ADDED Requirements

### Requirement: Interactive Codex live tracking resolves through the Codex TUI tracker family
When the server tracks an interactive Codex session from raw captured TUI snapshots, the live tracked-TUI adapter SHALL resolve the shared tracker through the `codex_tui` tracker app family rather than through a headless backend label.

That tracker-family resolution SHALL apply only to the interactive screen-scraped Codex TUI case. Structured headless Codex control flows SHALL remain outside the official tracked-TUI live path unless they are explicitly re-expressed as interactive raw-snapshot sources.

This tracker-facing resolution change SHALL NOT rename runtime/backend identifiers outside the live tracked-TUI adapter boundary.

#### Scenario: Interactive Codex tmux session uses codex_tui in live tracking
- **WHEN** the server captures raw snapshots from an interactive Codex tmux pane for live tracked-state reduction
- **THEN** the live adapter resolves the shared tracker through `codex_tui`
- **AND THEN** the resulting live tracked state uses the standalone tracked-TUI contract rather than a backend-specific headless label

#### Scenario: Headless Codex control path is not routed through live TUI tracking
- **WHEN** a repo-owned Codex flow uses a structured headless contract instead of interactive raw TUI snapshots
- **THEN** the official live tracked-TUI path does not require that flow to resolve through `codex_tui`
- **AND THEN** the server does not model that headless control path as an interactive tracked-TUI session by default

#### Scenario: Tracker-facing Codex app-family resolution leaves backend names unchanged
- **WHEN** the live tracked-TUI adapter resolves an interactive Codex session through `codex_tui`
- **THEN** that resolution changes only the tracker-facing app-family identity used by the tracked-TUI subsystem
- **AND THEN** runtime/backend identifiers such as `codex_app_server` outside that boundary remain unchanged

### Requirement: Live Codex TUI tracking preserves ordered snapshots for profile-owned temporal inference
When the server feeds interactive Codex TUI snapshots into the shared tracker, it SHALL preserve their observation order so the selected `codex_tui` profile can derive temporal hints over its recent sliding window.

The live adapter SHALL NOT require callers or clients to manage that recent-window logic directly.

The live adapter MAY emit explicit input events when they are available, but snapshot-only tracking SHALL remain compatible with success settlement that relies on surface-inferred turn authority.

#### Scenario: Ordered Codex snapshots support temporal active inference
- **WHEN** the newest interactive Codex snapshot alone lacks a visible running row
- **AND WHEN** the selected `codex_tui` profile can still infer active work from the recent ordered snapshot window
- **THEN** the live adapter preserves the snapshot order needed for that temporal inference
- **AND THEN** the shared tracker may still publish `turn.phase=active` for the current live turn

#### Scenario: Snapshot-only live tracking can still settle ready-return success
- **WHEN** the live adapter streams ordered interactive Codex snapshots without a matching explicit input event
- **AND WHEN** the shared tracker has already armed turn authority through stronger active-turn evidence from those snapshots
- **THEN** a later stable ready-return completion may still settle as `success`
- **AND THEN** the live adapter does not need explicit keystroke reporting to support Codex TUI completion tracking
