## Purpose
Define replay, analysis, and operator-label semantics for persisted terminal-recorder artifacts.

## Requirements

### Requirement: Recorder artifacts support parser and state replay
The repository SHALL provide a replay/analyze flow that consumes recorder pane snapshot artifacts and derives parser-facing and official tracked-state observations from the recorded sequence.

The replay/analyze flow SHALL operate over persisted pane snapshots rather than requiring a live tmux session.

When recorder artifacts also preserve runtime diagnostics or authoritative input events, the replay/analyze flow SHALL use that additional evidence to refine tracked-state reduction without replacing pane snapshots as the machine source of truth.

The replay/analyze flow SHALL NOT depend on demo-owned reference trackers as its implementation dependency.

At minimum, replay output SHALL preserve sample identity together with derived parser observations and tracked-state observations expressed in the official tracked-state vocabulary, including diagnostics posture, foundational `surface` observables, `turn.phase`, `last_turn.result`, and `last_turn.source` for each selected snapshot.

#### Scenario: Analyze derives parser and official tracked-state observations from one recorded run
- **WHEN** a developer runs the replay or analyze flow against one recorded run
- **THEN** the tool reads the persisted pane snapshot sequence without attaching to a live tmux session
- **AND THEN** it emits parser-facing observations and tracked-state observations keyed to the recorded samples in the official tracked-state vocabulary

#### Scenario: Active-mode replay uses preserved input authority when available
- **WHEN** a recorded run includes authoritative managed input events in addition to pane snapshots
- **THEN** replay uses that input evidence as turn-authority input to tracked-state reduction
- **AND THEN** the derived replay state can distinguish explicit-input provenance from surface-only inference

#### Scenario: Recorder replay no longer imports the independent demo tracker
- **WHEN** the repository analyzes one recorded run through the generic terminal-record replay path
- **THEN** the replay implementation does not import the independent demo tracker as its reducer
- **AND THEN** the replay path remains usable even when demo-specific packages are absent from the dependency graph

### Requirement: Replay contracts use pane snapshots as the machine source of truth
For recorder-backed parser and state-tracking tests, the machine-readable replay contract SHALL use the persisted pane snapshot sequence as the source of truth.

The terminal cast MAY be used for operator review, but SHALL NOT be the required parser replay surface for automated state-tracking validation.

#### Scenario: Automated replay does not require cast reconstruction
- **WHEN** automated parser or state-tracking validation runs against recorder artifacts
- **THEN** the validation consumes the pane snapshot sequence as the machine source of truth
- **AND THEN** it does not require reconstructing tmux pane content from the terminal cast

### Requirement: Replay supports operator-provided labels over recorded samples
The repository SHALL support operator-provided labels that annotate selected recorded samples or sample ranges with expected parser or lifecycle meanings.

At minimum, the labeling surface SHALL support stable references to recorded samples together with expected state-oriented fields such as parser classification, diagnostics posture, foundational surface observables, `turn.phase`, `last_turn.result`, `last_turn.source`, or scenario identity.

The primary repo-owned authoring surface for those labels SHALL remain `terminal_record add-label`, updated to accept the official tracked-state vocabulary directly.

Recorded labels SHALL be persisted as structured artifacts within the recorder run root or in a repo-owned exported fixture layout.

Legacy readiness/completion expectations MAY appear only as transitional debug assertions; they SHALL NOT remain the primary replay contract for new replay-grade validation.

#### Scenario: Operator labels a blocked trust-prompt sample in the official tracked-state vocabulary
- **WHEN** a developer labels one recorded sample as a trust-prompt blocked state
- **THEN** the persisted label artifact records a stable reference to that sample together with official tracked-state expectations such as diagnostics posture or `turn.phase`
- **AND THEN** downstream replay or tests can assert the expected official parser and lifecycle interpretation for that labeled checkpoint

#### Scenario: `terminal_record add-label` accepts official tracked-state expectation fields
- **WHEN** a developer labels one recorded sample through `terminal_record add-label`
- **THEN** the CLI accepts official tracked-state expectation fields for diagnostics posture, `surface`, `turn`, and `last_turn`
- **AND THEN** the persisted label artifact records those expectations without requiring direct JSON editing as the primary workflow
