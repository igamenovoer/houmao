## ADDED Requirements

### Requirement: Explore harness SHALL capture live Claude Code tmux sessions through a scripted scenario runner
The repository SHALL provide an explore-only harness under `scripts/explore/claude-code-state-tracking/` that can launch `claude-yunwu` in tmux, drive scripted scenario actions, and capture the resulting live session for later state-model verification.

The harness SHALL support at minimum:

- launching a fresh tmux-backed Claude session,
- driving prompt or control actions against that session,
- recording the run with the existing terminal recorder, and
- persisting harness-owned control-action events alongside the raw recorded session artifacts.

#### Scenario: Success scenario is captured from a live Claude run
- **WHEN** a developer runs the explore harness for a Claude success scenario
- **THEN** the harness launches `claude-yunwu` in tmux and drives the scripted turn actions
- **AND THEN** the run artifacts include the raw recorder output together with harness-owned control-action events for that scenario

### Requirement: Explore harness SHALL treat recorder pane snapshots as the authoritative replay surface
For this capability, raw recorded `pane_snapshots.ndjson` SHALL be the authoritative replay surface used for classification and replay validation.

The harness MAY preserve additional artifacts such as terminal casts or derived analysis files, but those artifacts SHALL NOT replace pane snapshots as the machine source of truth for replay-grade validation.

#### Scenario: Replay validation uses pane snapshots instead of cast reconstruction
- **WHEN** the harness derives groundtruth or replay-tracked state from a recorded Claude run
- **THEN** it reads the recorder pane snapshot sequence as the authoritative machine-readable surface
- **AND THEN** it does not require reconstructing the replay surface from the terminal cast

### Requirement: Explore harness SHALL derive content-first groundtruth outside of `houmao-server`
The harness SHALL derive a groundtruth state timeline from recorded Claude pane snapshots without importing or delegating to `houmao-server` tracker implementation code.

That groundtruth flow SHALL:

- use content-first signal detection over raw recorded pane content,
- support closest-compatible versioned Claude detectors rather than requiring an exact version match,
- apply current-region and recency interpretation so stale interruption or error text in scrollback does not automatically become current state, and
- allow future-aware settle interpretation for terminal outcomes such as success.

#### Scenario: Groundtruth suppresses stale historical interruption after a later active turn
- **WHEN** a recorded Claude pane still shows an older interrupted transcript block while a later turn is visibly active
- **THEN** the groundtruth classifier does not emit `turn_interrupted` as the current turn outcome from that stale block
- **AND THEN** it continues classifying the later current surface from the latest relevant visible region

### Requirement: Explore harness SHALL replay recorded observations through an independent ReactiveX tracker
The harness SHALL provide an independent replay tracker that consumes recorded snapshot observations and emits the simplified turn-state model using ReactiveX-driven timing rather than manual wall-clock bookkeeping.

This replay tracker SHALL remain outside of `houmao-server` implementation ownership and SHALL NOT import the server tracker as the state reducer under test.

At minimum, the replay tracker SHALL be able to emit:

- current turn phase `ready | active | unknown`
- terminal turn result `success | interrupted | known_failure | none`
- replay-timed settle behavior needed to distinguish active answer growth from settled success

#### Scenario: Replay tracker emits settled success only after replayed settle timing
- **WHEN** a recorded Claude run shows answer content followed by a stable completion marker and returned prompt posture
- **THEN** the replay tracker does not emit `success` immediately when answer text first appears
- **AND THEN** it emits `success` only after the replayed settle timing confirms the stable terminal surface

### Requirement: Explore harness SHALL compare groundtruth and replay timelines explicitly
The harness SHALL compare the offline groundtruth timeline against the replay-tracked timeline and SHALL persist a report that makes mismatches explicit.

At minimum, the comparison output SHALL identify:

- the first divergence point,
- transition-order mismatches,
- missed active or terminal intervals, and
- false positive terminal outcomes.

#### Scenario: Comparison report exposes replay mismatch against groundtruth
- **WHEN** the replay tracker disagrees with the groundtruth classifier for a recorded Claude run
- **THEN** the harness persists a comparison artifact identifying where the mismatch first occurred
- **AND THEN** the report includes enough sample or timestamp detail for a developer to inspect the raw pane sequence at that divergence

### Requirement: Explore harness SHALL ship an initial scenario corpus for the highest-value Claude turn boundaries
The explore harness SHALL include an initial scenario set that exercises the most important boundaries of the simplified state model for Claude Code.

At minimum, the initial scenario corpus SHALL include:

- one success scenario,
- one interruption scenario, and
- one active-turn noise scenario where slash-menu or similar prompt-overlay churn appears during an otherwise active turn.

#### Scenario: Initial corpus exercises slash-menu noise during active Claude processing
- **WHEN** a developer runs the initial slash-noise scenario
- **THEN** the captured and replayed artifacts include a period where prompt-overlay churn appears during an already-active Claude turn
- **AND THEN** the comparison flow can verify whether replay tracking preserved `turn_active` instead of misclassifying that overlay as a different semantic turn kind
