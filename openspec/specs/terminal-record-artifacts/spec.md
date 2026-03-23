## Purpose
Define the persisted artifact contract and capture-authority metadata for tmux-backed terminal recorder runs.

## Requirements

### Requirement: Recorder persists synchronized visual, snapshot, and metadata artifacts
Each recorder run SHALL persist a synchronized artifact set under one recorder-owned run root.

At minimum, the persisted artifact set SHALL include:
- one human-facing terminal cast artifact,
- one machine-readable pane snapshot stream derived from the targeted tmux pane,
- one recorder manifest describing the run,
- one live-state or finalized-state record describing recorder process state, and
- one structured input-event stream when the selected mode provides managed input capture.

The recorder SHALL preserve these artifacts after stop for later inspection and replay.

#### Scenario: Stopped run preserves required artifacts
- **WHEN** a developer stops a completed recorder run
- **THEN** the run root still contains the cast artifact, pane snapshot stream, manifest, and finalized run-state record
- **AND THEN** any available structured input-event stream is preserved for later analysis

### Requirement: Recorder artifacts declare capture authority boundaries
Recorder metadata SHALL explicitly declare the authority boundary of each run's input and output capture so downstream tooling can distinguish replay-grade evidence from operator-facing convenience artifacts.

At minimum, recorder metadata SHALL include:
- the selected mode,
- the targeted tmux session and pane,
- a visual recording kind,
- an input capture level, and
- whether the run became tainted together with recorded taint reasons when capture guarantees degraded.

The recorder SHALL treat tmux pane snapshots as the authoritative replay surface for parser and state-tracking analysis.

The recorder SHALL treat the terminal cast as an operator-facing visual record rather than as the authoritative parser replay surface.

#### Scenario: Active mode records authoritative managed input posture
- **WHEN** a recorder run starts in `active` mode and remains on its managed input path
- **THEN** recorder metadata marks the run with an authoritative managed-input capture level
- **AND THEN** downstream tooling can treat the input-event stream as authoritative for managed input delivered during that run

#### Scenario: Passive mode records output-only or managed-only posture
- **WHEN** a recorder run starts in `passive` mode
- **THEN** recorder metadata marks the run with a non-authoritative manual-input capture level
- **AND THEN** downstream tooling does not mistake the run for complete manual input capture

### Requirement: Recorder continuously samples exact tmux pane content
For the targeted tmux pane, the recorder SHALL persist a time-ordered pane snapshot stream based on exact tmux-visible pane content rather than on projected dialog text or terminal-player reconstruction.

Each persisted pane snapshot SHALL include enough timing and identity metadata to replay the sample sequence later against parser and state-tracking tooling.

The recorder SHALL capture a final pane snapshot during orderly stop before finalizing the run.

#### Scenario: Snapshot stream preserves ordered pane evidence
- **WHEN** the recorder is running against a target tmux pane
- **THEN** it persists ordered pane snapshots with timing metadata for that pane
- **AND THEN** the snapshot stream can be replayed later without reconstructing pane content from the visual cast alone

#### Scenario: Stop captures a final pane snapshot
- **WHEN** a developer stops an active recorder run
- **THEN** the recorder captures one final pane snapshot during shutdown
- **AND THEN** the finalized artifact set reflects the terminal's last recorded pane state
