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

### Requirement: Recorder replay supports Kimi parser and tracker analysis
The terminal-record replay and analyze flow SHALL support recorded Kimi runs whose manifest tool is `kimi`.

For Kimi runs, replay SHALL derive parser-facing observations when a Kimi parser is available and SHALL derive shared tracked-state observations through the Kimi shared TUI profile when that profile is available.

Replay SHALL operate from persisted pane snapshots and labels without requiring a live Kimi process.

#### Scenario: Analyze accepts recorded Kimi run
- **WHEN** a maintainer runs terminal-record analysis against a recorded run whose manifest tool is `kimi`
- **THEN** the analyze command accepts the run
- **AND THEN** it emits Kimi parser or tracker observations keyed to recorded sample ids

#### Scenario: Kimi replay does not require live credentials
- **WHEN** the recorded Kimi pane snapshots and labels already exist
- **THEN** replay validation can run without launching Kimi or using live Kimi credentials

### Requirement: Replay validation compares Kimi labels against public tracked-state output
The Kimi replay validation flow SHALL compare labeled expectations against replayed public tracked-state fields.

At minimum, strict comparison SHALL cover:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

Parser-facing Kimi expectations such as `business_state`, `input_mode`, and `ui_context` MAY be compared when labels include them.

#### Scenario: Kimi validation reports label mismatches by sample
- **WHEN** replayed Kimi tracked-state output differs from a label expectation
- **THEN** validation reports the sample id or sample range that failed
- **AND THEN** the report includes the expected and actual public tracked-state fields

#### Scenario: Kimi approval labels validate parser and public state
- **WHEN** a Kimi approval dialog range has both parser-facing and public tracked-state labels
- **THEN** validation compares parser state for the modal approval context
- **AND THEN** validation compares public tracked-state readiness and turn posture for the same range

### Requirement: Terminal recording and replay preserve pending-input expectations

Terminal-record state timelines, operator labels, replay analysis, state comparison, and review rendering SHALL support the official `surface.pending_input` tristate.

Replay SHALL derive pending input from persisted pane snapshots through the selected provider profile. It SHALL NOT require a live provider process, credentials, or gateway submission history to reproduce the pending-input state.

The primary labeling surface SHALL let an operator assign pending-input expectations to stable samples or sample ranges, and comparison output SHALL identify mismatches by field and sample range.

#### Scenario: Recorded pending span replays without a live provider

- **WHEN** a frozen terminal-record run contains pane snapshots spanning a provider-native queued instruction
- **THEN** replay emits `surface_pending_input` for every selected sample through the provider profile
- **AND THEN** the replay does not require live credentials or a live tmux session

#### Scenario: Operator labels pending input in the official vocabulary

- **WHEN** an operator labels a recorded sample or range as pending, not pending, or unknown
- **THEN** the persisted structured label uses the official pending-input expectation field
- **AND THEN** replay comparison reports any expected-versus-actual mismatch with stable sample references

#### Scenario: Review output shows pending input separately from readiness

- **WHEN** the terminal-record tooling renders a review video or human-readable timeline
- **THEN** the output displays pending input independently from accepting-input, editing-input, ready-posture, and turn-phase fields
- **AND THEN** a reviewer can audit a busy-no-pending span against a busy-pending span visually

### Requirement: Pending-input replay supports deterministic cadence stress

The replay workflow SHALL support deterministic downsampled and irregular-cadence variants of a frozen pending-input recording without mutating the source recording.

At minimum, qualification SHALL cover the canonical 20 Hz stream, derived 10 Hz, 5 Hz, and 2 Hz streams, and seeded variants that introduce jitter, frame drops, or capture bursts. Each retained sample SHALL be compared with the audited expectation for that source sample.

A cadence variant SHALL NOT be required to reconstruct a transition that has no retained sample. It SHALL preserve meaningful classification for retained decisive surfaces and SHALL report transition drift against the retained cadence.

#### Scenario: Low-rate replay preserves decisive queued surfaces

- **WHEN** a derived low-rate stream retains snapshots with complete positive pending structure
- **THEN** replay does not classify those retained snapshots as `pending_input=no`
- **AND THEN** any transition-time drift is bounded and reported relative to the retained sample interval

#### Scenario: Seeded irregular replay is reproducible

- **WHEN** a maintainer reruns a jitter, drop, or burst variant with the same source recording and seed
- **THEN** the replay selects the same ordered samples and produces reproducible comparison output
- **AND THEN** cadence-only variation does not create unexplained `yes/no` oscillation on equivalent retained structures
