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

### Requirement: Recorder artifacts support style-preserving Kimi high-rate capture
The terminal recorder SHALL support Kimi tool identity for capture runs and SHALL preserve ANSI/style-bearing pane text for Kimi replay analysis.

For Kimi signal investigation, the recorder SHALL be able to write capture runs under a caller-selected repo-local run root such as `tmp/kimi-tui-tracking/<run-id>/`.

The recorder SHALL support sampling intervals suitable for about 10 fps capture. Recorder metadata SHALL record the configured sample interval and enough target metadata to replay or inspect the captured pane later.

#### Scenario: Kimi capture accepts Kimi tool identity
- **WHEN** a maintainer starts a terminal recorder run with `--tool kimi`
- **THEN** the recorder persists `tool = kimi` in the manifest
- **AND THEN** later analysis can select Kimi parser and tracker behavior from that manifest

#### Scenario: Kimi high-rate capture preserves ANSI style data
- **WHEN** the recorder samples a Kimi TUI pane at about 10 fps
- **THEN** each replay-grade pane snapshot preserves ANSI escape data from the captured pane
- **AND THEN** Kimi detector development can inspect style facts such as dim, bold, color, focused border, or selected row rendering

### Requirement: Recorder artifacts support derived low-rate snapshot streams
The recorder or companion tooling SHALL support deriving a low-rate snapshot stream from an existing high-rate pane snapshot stream.

The derived stream SHALL preserve timing metadata, stable sample identifiers, and traceability to the source high-rate sample selected for each derived frame.

The derived stream SHALL live beside the source stream in the same run root or in a clearly linked derived run root.

#### Scenario: Derived 2 fps stream records source sample mapping
- **WHEN** a maintainer derives an about 2 fps stream from one about 10 fps Kimi capture
- **THEN** each derived sample records the high-rate source sample id it came from
- **AND THEN** replay validation can explain failures against either sample cadence

#### Scenario: Derived stream does not require another live Kimi run
- **WHEN** a high-rate Kimi capture already exists
- **THEN** the low-rate stream is produced from persisted snapshots
- **AND THEN** the maintainer does not need to repeat the live Kimi scenario to obtain low-rate evidence

### Requirement: Recorder sampling SHALL remain replay-grade even when visual cast recording degrades
For signal-corpus capture, the machine-readable pane snapshot stream SHALL remain the authoritative artifact even if the human-facing terminal cast recorder exits early or becomes unavailable.

When the visual cast recorder fails or exits before the requested capture is complete, the recorder SHALL either continue snapshot sampling when safe or mark the run with explicit taint metadata that distinguishes cast degradation from pane-snapshot loss.

#### Scenario: Cast recorder exit does not silently invalidate snapshots
- **WHEN** the visual cast recorder exits during a Kimi capture but pane snapshot sampling continues
- **THEN** the run metadata records the visual recording degradation
- **AND THEN** the persisted pane snapshots remain usable as replay-grade evidence

