## ADDED Requirements

### Requirement: Recorded validation SHALL resolve workflow defaults from the demo-owned config
The recorded validation workflow under `scripts/demo/shared-tui-tracking-demo-pack/` SHALL load demo-owned defaults from `demo-config.toml` for launch posture, output layout, evidence cadence, tracker-semantic timing, and review-video presentation unless a later override source is applied.

The default recorded-capture evidence cadence SHALL use `sample_interval_seconds = 0.2`.

#### Scenario: Recorded validation uses demo-owned capture defaults
- **WHEN** a maintainer runs recorded validation without overriding capture cadence
- **THEN** the workflow resolves its defaults from the demo-owned config
- **AND THEN** the capture path uses `sample_interval_seconds = 0.2` by default

### Requirement: Recorded validation SHALL support config-defined capture-frequency robustness sweeps
The recorded validation workflow SHALL support named sweep definitions from the demo-owned configuration that vary evidence cadence for the same scenario or fixture workflow.

Sweep verdicts SHALL be based on transition-contract expectations rather than on blindly reusing a canonical sample-aligned ground-truth timeline across all cadences.

#### Scenario: Recorded validation executes a frequency sweep from config
- **WHEN** a developer runs a config-defined capture-frequency sweep
- **THEN** the workflow executes each configured cadence variant
- **AND THEN** the resulting verdicts explain whether required tracker transitions and terminal outcomes remained observable at each cadence

## MODIFIED Requirements

### Requirement: Recorded validation SHALL generate a staged-frame review video from pane snapshots
For each published recorded fixture, the workflow SHALL be able to render a human-review video from the same pane snapshots that feed the standalone tracker.

The workflow SHALL first save rendered review frames to disk, then encode the final video from those frames. The encoded review video SHALL:

- be rendered at `1920x1080`,
- default its effective video cadence from the capture cadence used for the underlying snapshots,
- encode to `.mp4` with `ffmpeg`,
- use `libx264`, and
- visually mark the saved ground-truth state and each ground-truth state transition.

Unless an operator explicitly overrides the presentation cadence, the review video SHALL reflect the capture cadence rather than a separate fixed default FPS. The review video SHALL be derived from pane snapshots rather than from the terminal cast.

#### Scenario: Review video reflects the underlying capture cadence
- **WHEN** a maintainer generates review media for one recorded fixture without overriding presentation cadence
- **THEN** the workflow first writes a staged sequence of rendered `1920x1080` frames to disk
- **AND THEN** it encodes `review.mp4` from those frames with `ffmpeg` and `libx264`
- **AND THEN** the resulting video cadence matches the capture cadence used for that fixture and visibly marks the ground-truth state changes for human verification
