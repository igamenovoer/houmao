## ADDED Requirements

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
