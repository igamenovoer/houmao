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

### Requirement: Recorded validation SHALL require successful authoring evidence before a fixture is promoted into the canonical corpus
The recorded validation workflow SHALL be used as a promotion gate for any real tmux-backed fixture that is copied into `tests/fixtures/shared_tui_tracking/recorded/`.

At minimum, the authoring run being promoted SHALL have:

- zero replay mismatches,
- complete label coverage,
- a generated Markdown summary report, and
- a generated review video rendered from the same pane snapshots that feed replay.

#### Scenario: Canonical fixture promotion is blocked until authoring evidence is complete
- **WHEN** a maintainer prepares to promote one temporary real capture into the committed fixture corpus
- **THEN** the recorded-validation workflow has already produced zero-mismatch replay output, a summary report, and a review video for that authoring run
- **AND THEN** the fixture is not considered canonical until those promotion checks pass

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

When a sweep covers a lifecycle that intentionally repeats the same transition family more than once, the configured transition contract SHALL be able to express repeated or ordered occurrence expectations rather than only first-occurrence label presence.

#### Scenario: Recorded validation executes a frequency sweep from config
- **WHEN** a developer runs a config-defined capture-frequency sweep
- **THEN** the workflow executes each configured cadence variant
- **AND THEN** the resulting verdicts explain whether required tracker transitions and terminal outcomes remained observable at each cadence
- **AND THEN** repeated-transition cases can require an ordered or repeated transition family rather than collapsing to one first occurrence

### Requirement: Recorded validation SHALL generate a staged-frame review video from pane snapshots
For each published recorded fixture, the workflow SHALL be able to render a human-review video from the same pane snapshots that feed the standalone tracker.

The workflow SHALL first save rendered review frames to disk, then encode the final video from those frames. The encoded review video SHALL:

- be rendered at `1920x1080`,
- default its effective video cadence from the capture cadence used for the underlying snapshots,
- be encoded to `.mp4` with `ffmpeg`,
- use `libx264`, and
- visually mark the saved ground-truth state and each ground-truth state transition.

Unless an operator explicitly overrides the presentation cadence, the review video SHALL reflect the capture cadence rather than a separate fixed default FPS. The review video SHALL be derived from pane snapshots rather than from the terminal cast.

#### Scenario: Review video reflects the underlying capture cadence
- **WHEN** a maintainer generates review media for one recorded fixture without overriding presentation cadence
- **THEN** the workflow first writes a staged sequence of rendered `1920x1080` frames to disk
- **AND THEN** it encodes `review.mp4` from those frames with `ffmpeg` and `libx264`
- **AND THEN** the resulting video cadence matches the capture cadence used for that fixture and visibly marks the ground-truth state changes for human verification

### Requirement: Recorded validation SHALL ship an initial multi-tool fixture corpus for critical state transitions
The repository SHALL include an initial recorded fixture corpus for the standalone shared TUI tracker, and the canonical committed version of that corpus SHALL be sourced from real tmux-backed captures authored with the recorded-validation workflow rather than from synthetic hand-authored recorder payloads.

At minimum, the first-wave canonical corpus SHALL contain:

- Claude `explicit_success`
- Claude `interrupted_after_active`
- Claude `double_interrupt_then_close`
- Claude `slash_menu_recovery`
- Claude `tui_down_after_active`
- Codex `explicit_success`
- Codex `interrupted_after_active`
- Codex `double_interrupt_then_close`
- Codex `tui_down_after_active`

Each published canonical fixture SHALL preserve the replay-grade canonical artifact set for that case, including the fixture manifest, pane snapshots, runtime observations, labels, and authoritative input events when present.

#### Scenario: Maintained recorded-validation suite runs against the real first-wave corpus
- **WHEN** a developer runs the maintained recorded-validation test suite
- **THEN** the suite includes a canonical first-wave fixture set spanning both Claude and Codex from real tmux-backed captures
- **AND THEN** that corpus exercises success, interruption, repeated intentional interruption with close, ambiguity, and diagnostics-loss boundaries for the standalone tracker

### Requirement: Recorded validation SHALL support semantic scenario intents for intentional interrupt and intentional close
The recorded validation workflow SHALL support intent-level scenario actions for intentional interrupt and intentional close in addition to raw low-level input actions.

The intent-level actions SHALL allow the workflow to express operator meaning without requiring every supported tool to share the same literal key sequence or close recipe.

#### Scenario: Harness executes a repeated-interruption scenario through tool-specific intents
- **WHEN** a maintainer runs a recorded-capture scenario that includes intentional interruption and final close
- **THEN** the scenario can express interruption and close as semantic operator intents
- **AND THEN** the workflow resolves those intents through the selected tool’s supported recipe rather than assuming one literal low-level key path for every tool

### Requirement: Recorded validation SHALL judge repeated interrupted-turn lifecycles against public tracked state
The recorded validation workflow SHALL support canonical fixtures that exercise a repeated interrupted-turn lifecycle of `prompt -> active -> interrupt -> prompt -> interrupt -> close`.

For such fixtures, the comparison contract SHALL make it possible to judge:

- first interrupted-ready posture,
- reset of `last_turn_result` when the second turn becomes active,
- second interrupted-ready posture, and
- final diagnostics-loss posture after close without inventing a terminal success or known failure.

#### Scenario: Repeated interruption fixture is replayed against ground truth
- **WHEN** a developer replays a repeated intentional-interruption fixture through recorded validation
- **THEN** the resulting replay and ground-truth comparison can distinguish both interrupted turn cycles
- **AND THEN** the comparison can detect whether interruption state was incorrectly carried into the second active turn
- **AND THEN** the comparison can detect whether close produced an incorrect terminal result

### Requirement: Recorded validation SHALL keep complex multi-turn regression fixtures as a maintained quality gate
The recorded validation workflow SHALL keep a maintained complex recorded interaction fixture for Claude and a parallel maintained complex recorded interaction fixture for Codex in the committed corpus under `tests/fixtures/shared_tui_tracking/recorded/`.

Each complex fixture SHALL be sourced from a real tmux-backed capture authored through the recorded-validation workflow and SHALL exercise the lifecycle:

- short prompt -> settled success,
- long prompt with a ready-draft span before submit,
- active turn with a visible active-draft span while the turn is still in flight,
- intentional interrupt to interrupted-ready,
- another prompt with another ready-draft span before submit,
- another active turn with another active-draft span,
- second intentional interrupt to interrupted-ready, and
- final short prompt -> settled success.

The maintained replay-validation suite SHALL continue to run those fixtures so they remain a standing regression gate rather than one-off authoring artifacts.
When tracker lifecycle semantics change in ways that can shift public-state labels, the maintained validation workflow SHALL revalidate any previously committed affected fixtures before the maintained corpus is treated as passing again.

#### Scenario: Maintained validation suite runs the complex regression fixtures
- **WHEN** a developer runs the maintained recorded-validation regression suite
- **THEN** the suite includes the canonical Claude and Codex complex interaction fixtures
- **AND THEN** those fixtures continue to serve as a standing quality gate for repeated interruption, overlapping draft editing, and terminal-result reset behavior

#### Scenario: Lifecycle-semantic changes force affected fixture revalidation
- **WHEN** the tracker changes turn-lifecycle semantics in a way that can shift replay labels for previously committed recorded fixtures
- **THEN** the maintained validation workflow replays those affected fixtures again
- **AND THEN** the maintained corpus is not treated as green until any changed labels are revalidated or updated explicitly

### Requirement: Recorded validation SHALL judge complex success-interrupt-success lifecycles against public tracked state
For the maintained complex fixtures, the replay comparison contract SHALL make it possible to judge:

- first settled-success posture,
- reset of `last_turn.result` and `last_turn.source` during both ready-draft spans,
- `surface.editing_input=yes` during both active-draft spans,
- first interrupted-ready posture,
- second interrupted-ready posture, and
- final settled-success posture without carrying interrupted state into the last turn.

The maintained cadence-sweep contract for these fixtures SHALL be able to require an ordered repeated transition sequence equivalent to `ready_success -> active -> ready_interrupted -> active -> ready_interrupted -> ready_success`.
That cadence-sweep contract SHALL remain a coarse transition gate; ready-draft and active-draft semantics SHALL continue to be judged by sample-aligned ground truth rather than by adding new sweep-only draft labels.

#### Scenario: Complex fixture replay detects stale last-turn carry or draft-editing regressions
- **WHEN** a developer replays one maintained complex success-interrupt-success fixture through recorded validation
- **THEN** the resulting replay and ground-truth comparison can detect whether interrupted state leaked into a later draft or active span
- **AND THEN** the comparison can detect whether overlapping active drafting failed to report `surface.editing_input=yes`
- **AND THEN** the ordered sweep contract can detect whether one of the repeated active or interrupted phases collapsed out of the lifecycle

#### Scenario: Draft semantics remain in the strict ground-truth path
- **WHEN** one maintained complex fixture includes ready-draft and active-draft spans
- **THEN** those draft-specific semantics are judged through the sample-aligned replay-versus-ground-truth comparison
- **AND THEN** the sweep contract is not required to introduce additional draft-only state labels to validate that fixture

