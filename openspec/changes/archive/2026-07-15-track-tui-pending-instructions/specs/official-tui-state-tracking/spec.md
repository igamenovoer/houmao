## ADDED Requirements

### Requirement: Public tracked TUI state exposes provider-native pending input

For supported tmux-backed TUI sessions, the authoritative tracked state SHALL expose `surface.pending_input` with the same `yes | no | unknown` tristate vocabulary as the other foundational surface observables.

`surface.pending_input=yes` SHALL mean that the current visible provider TUI contains decisive evidence of at least one already-submitted instruction waiting behind the active turn. `surface.pending_input=no` SHALL mean that the captured provider surface is complete enough to make a negative decision and contains no such pending instruction. Cropped, incomplete, unsupported, or structurally ambiguous evidence SHALL produce `surface.pending_input=unknown`.

The system SHALL keep pending input distinct from user-authored composer draft text, gateway-durable queued requests, and tracker explicit-input provenance. Prompt-submission notes and Houmao dispatch history SHALL NOT manufacture `surface.pending_input=yes` without matching provider-visible evidence.

The pending-input field SHALL appear in current state, public transitions, bounded history, compact and detailed TUI projections, state serialization, and the operator-visible stability signature. A pending-input change SHALL therefore remain observable even when `turn.phase` does not change.

#### Scenario: Busy TUI with no queued follow-up reports no pending input

- **WHEN** a supported provider TUI is actively processing a turn and its complete visible queue/composer structure contains no submitted follow-up
- **THEN** the authoritative tracked state reports `turn.phase=active`
- **AND THEN** it reports `surface.pending_input=no`

#### Scenario: Provider-native queued follow-up is independent of active phase

- **WHEN** a supported provider TUI is actively processing a turn and visibly retains at least one submitted follow-up for later processing
- **THEN** the authoritative tracked state reports `surface.pending_input=yes`
- **AND THEN** that field remains independent of `surface.editing_input` and the gateway durable request queue

#### Scenario: Consuming the last queued follow-up clears pending input

- **WHEN** the provider consumes the last visibly queued follow-up and the next complete captured surface contains no remaining pending structure
- **THEN** the authoritative tracked state reports `surface.pending_input=no`
- **AND THEN** the pending-input transition remains visible even if the provider continues processing and `turn.phase` stays `active`

#### Scenario: Incomplete queue structure degrades conservatively

- **WHEN** a captured pane is cropped or lacks the provider-specific boundaries needed to decide whether submitted input is pending
- **THEN** the authoritative tracked state reports `surface.pending_input=unknown`
- **AND THEN** it does not infer `no` merely from the absence of one text fragment

#### Scenario: Houmao prompt note does not synthesize provider queue state

- **WHEN** the active control plane records explicit prompt-submission evidence before the provider TUI has repainted
- **THEN** that note may arm explicit-input turn provenance
- **AND THEN** it does not set `surface.pending_input=yes` until provider-visible evidence establishes that state
