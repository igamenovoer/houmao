# shared-tui-tracking-recorded-validation Specification

## Purpose
Define the recorded validation workflow for the standalone shared tracked-TUI module, including recorder-backed capture, human-owned ground truth, replay/comparison artifacts, reports, and review-video generation.

## Requirements

### Requirement: Recorded validation SHALL capture replay-grade standalone-tracker fixtures from real tmux sessions
The repository SHALL provide a recorded validation workflow for the standalone shared TUI tracker under `scripts/demo/shared-tui-tracking-demo-pack/` that can launch Claude or Codex from repository fixture brains, drive real tmux-backed sessions, and persist replay-grade artifacts for later automated validation.

When the workflow itself is responsible for driving the session, it SHALL record through terminal-recorder active mode so pane snapshots remain the authoritative replay surface and managed input events are preserved when explicit-input provenance matters.

The recorded run root SHALL live under a repo-owned subtree such as `tmp/demo/shared-tui-tracking-demo-pack/recorded/<case-id>/`.

#### Scenario: Harness captures a driven fixture with authoritative input evidence
- **WHEN** a maintainer runs the recorded validation workflow for one scripted case
- **THEN** the workflow launches the selected tool in tmux from `tests/fixtures/agents/`
- **AND THEN** it records the session through terminal-recorder active mode
- **AND THEN** the resulting run root contains pane snapshots and any available managed input events for later replay

### Requirement: Recorded validation SHALL probe tmux and runtime state directly without `houmao-server`
The recorded validation workflow SHALL obtain pane text, session liveness, pane liveness, and supported-process liveness through direct tmux/runtime probing plus recorder artifacts.

The workflow SHALL feed those observations directly into the standalone shared tracker and SHALL NOT require `houmao-server` routes or server-owned tracker state to perform capture, replay, or comparison.

#### Scenario: Replay-grade validation runs without server-owned state
- **WHEN** a maintainer captures or replays one recorded standalone-tracker fixture
- **THEN** the workflow reads tmux and recorder evidence directly
- **AND THEN** it drives the standalone tracker from that direct evidence
- **AND THEN** it does not depend on `houmao-server` APIs or server-owned live tracking state

### Requirement: Recorded validation SHALL default capture launches to permissive supported tool posture
Normal harness-driven capture runs SHALL launch supported tools in the most permissive supported posture so routine fixture capture does not stall on unexpected approval or sandbox prompts.

For Claude, the launch SHALL include `--dangerously-skip-permissions`.

For Codex, the generated runtime home SHALL use the repo-supported permissive bootstrap posture with `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`.

#### Scenario: Default capture run avoids unexpected operator-blocked startup
- **WHEN** a maintainer records a normal shared-tracker fixture for Claude or Codex
- **THEN** the launch uses the tool’s permissive supported posture by default
- **AND THEN** the workflow does not intentionally rely on approval or sandbox prompts as part of that fixture

### Requirement: Recorded validation SHALL store human-owned ground truth derived from direct snapshot inspection
The repository SHALL support ground-truth authoring from direct inspection of the recorded pane snapshots that will later be fed into the standalone tracker.

That ground truth SHALL be stored as structured labels over official tracked-state fields, using stable sample or sample-range references. The validation workflow SHALL expand those labels into a per-sample `groundtruth_timeline.ndjson` before replay comparison.

The reducer under test SHALL NOT be used as the authoritative source of that ground-truth timeline.

#### Scenario: Ground truth is expanded from structured labels instead of reducer output
- **WHEN** a maintainer classifies the recorded sample sequence after capture
- **THEN** the classification is saved as structured label data keyed to recorded samples or ranges
- **AND THEN** the workflow expands those labels into a per-sample ground-truth timeline
- **AND THEN** the standalone tracker replay is compared against that expanded timeline rather than being reused as its own oracle

### Requirement: Recorded validation SHALL replay recorded artifacts through the standalone tracker and compare the result to ground truth
The repository SHALL provide a replay-and-compare flow that consumes the recorded pane snapshots, optional authoritative input events, and optional runtime diagnostics, replays them through the standalone shared TUI tracker, and emits comparison artifacts against the saved ground truth.

At minimum, the replay output and comparison SHALL preserve sample identity together with diagnostics posture, `surface` observables, `turn.phase`, `last_turn.result`, and `last_turn.source`.

#### Scenario: Recorded fixture produces replay and comparison artifacts
- **WHEN** a developer runs replay validation for one recorded standalone-tracker fixture
- **THEN** the workflow replays the recorded observation stream through the standalone shared tracker
- **AND THEN** it writes replay timeline and comparison artifacts keyed to the same sample ids as the recorded snapshots
- **AND THEN** mismatches against ground truth are explicit and machine-readable

### Requirement: Recorded validation SHALL finalize with a Markdown summary report and separate issue docs
Each recorded validation run SHALL finalize with a human-readable Markdown report inside the run output directory.

That report SHALL summarize:

- the scenarios or checks that passed,
- the scenarios or checks that failed,
- the key comparison or replay verdict, and
- links or paths to the important raw and derived artifacts for that run.

When the run detects failures, mismatches, or other actionable issues, it SHALL also write one separate Markdown issue document per issue inside an issue-specific subdirectory under the same output directory.

#### Scenario: Failed recorded validation run writes both summary and issue docs
- **WHEN** a recorded validation run finishes with one or more mismatches or failures
- **THEN** the run output directory contains a Markdown summary report describing what worked and what did not
- **AND THEN** the run output directory also contains one or more separate Markdown issue documents for the detected problems
- **AND THEN** each issue document points back to the relevant run artifacts or sample identifiers

### Requirement: Recorded validation SHALL generate a staged-frame review video from pane snapshots
For each published recorded fixture, the workflow SHALL be able to render a human-review video from the same pane snapshots that feed the standalone tracker.

The workflow SHALL first save rendered review frames to disk, then encode the final video from those frames. The encoded review video SHALL:

- be rendered at `1920x1080`,
- default to `8 fps`,
- be encoded to `.mp4` with `ffmpeg`,
- use `libx264`, and
- visually mark the saved ground-truth state and each ground-truth state transition.

The review video SHALL be derived from pane snapshots rather than from the terminal cast.

#### Scenario: Review video is encoded from staged 1080p frames
- **WHEN** a maintainer generates review media for one recorded fixture
- **THEN** the workflow first writes a staged sequence of rendered `1920x1080` frames to disk
- **AND THEN** it encodes `review.mp4` from those frames at the default `8 fps` with `ffmpeg` and `libx264`
- **AND THEN** the resulting video visibly marks the ground-truth state changes for human verification

### Requirement: Recorded validation SHALL ship an initial multi-tool fixture corpus for critical state transitions
The repository SHALL include an initial recorded fixture corpus for the standalone shared TUI tracker.

At minimum, that corpus SHALL contain at least four fixtures spanning Claude and Codex, and the set as a whole SHALL cover:

- a successful ready-to-active-to-settled-success path,
- an interrupted-after-active path, and
- a diagnostics-loss path such as `tui_down` or `unavailable`.

#### Scenario: Initial corpus covers critical shared-tracker boundaries across tools
- **WHEN** a developer runs the maintained recorded-validation test suite
- **THEN** the suite includes at least four committed recorded fixtures spanning Claude and Codex
- **AND THEN** the fixture set exercises critical standalone-tracker transitions for success, interruption, and diagnostics-loss behavior

