## ADDED Requirements

### Requirement: Explore harness SHALL capture live Claude Code tmux sessions through a scripted scenario runner
The repository SHALL provide an explore-only harness under `scripts/explore/claude-code-state-tracking/` that can launch `claude-yunwu` in tmux, drive scripted scenario actions, and capture the resulting live session for later state-model verification.

The harness SHALL support at minimum:

- launching a fresh tmux-backed Claude session,
- driving prompt or control actions against that session,
- optionally launching Claude through a subprocess-owned fault-injection wrapper when a scenario needs deliberate network failure,
- recording the run with the existing terminal recorder, and
- persisting harness-owned control-action events alongside the raw recorded session artifacts, and
- persisting runtime liveness observations that distinguish tmux-target availability from Claude child-process liveness.

#### Scenario: Success scenario is captured from a live Claude run
- **WHEN** a developer runs the explore harness for a Claude success scenario
- **THEN** the harness launches `claude-yunwu` in tmux and drives the scripted turn actions
- **AND THEN** the run artifacts include the raw recorder output together with harness-owned control-action events for that scenario

#### Scenario: Injected failure scenario launches Claude through a fault-injection wrapper
- **WHEN** a developer runs a scenario that intentionally provokes a Claude network failure
- **THEN** the harness launches the Claude subprocess through a subprocess-owned fault-injection path rather than relying on ambient network breakage
- **AND THEN** the run artifacts record that injection mode as part of the scenario control trace

#### Scenario: Kill scenario records runtime liveness evidence
- **WHEN** a developer runs a scenario that kills the Claude process or removes the target tmux session
- **THEN** the harness records runtime liveness observations alongside the raw pane capture
- **AND THEN** later replay and comparison can distinguish process-down from target-unavailable paths

### Requirement: Explore harness SHALL treat recorder pane snapshots as the authoritative replay surface
For this capability, raw recorded `pane_snapshots.ndjson` SHALL be the authoritative replay surface used for classification and replay validation.

The harness MAY preserve additional artifacts such as terminal casts or derived analysis files, but those artifacts SHALL NOT replace pane snapshots as the machine source of truth for replay-grade validation.

#### Scenario: Replay validation uses pane snapshots instead of cast reconstruction
- **WHEN** the harness derives groundtruth or replay-tracked state from a recorded Claude run
- **THEN** it reads the recorder pane snapshot sequence as the authoritative machine-readable surface
- **AND THEN** it does not require reconstructing the replay surface from the terminal cast

### Requirement: Explore harness SHALL preserve runtime diagnostics evidence for abrupt process-loss paths
For scenarios where the supported Claude subprocess exits abruptly or the tmux target disappears, the harness SHALL preserve runtime diagnostics evidence in addition to pane snapshots.

That diagnostics evidence SHALL be sufficient to distinguish, at minimum:

- tmux target still observable while the supported Claude process is no longer running, and
- tmux target no longer observable at all.

#### Scenario: Abrupt process loss is classified with runtime diagnostics evidence
- **WHEN** the Claude subprocess is killed while tmux remains alive
- **THEN** the harness artifacts preserve enough runtime evidence to classify that path as process-down rather than target-unavailable
- **AND THEN** replay validation does not need to guess that distinction from pane text alone

#### Scenario: Target disappearance is classified with runtime diagnostics evidence
- **WHEN** the tmux target disappears entirely during a scenario run
- **THEN** the harness artifacts preserve enough runtime evidence to classify that path as target-unavailable
- **AND THEN** replay validation does not mistake that disappearance for a normal terminal turn outcome

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

### Requirement: Explore harness SHALL support deliberate subprocess-level fault injection for error-path scenarios
The harness SHALL support controlled child-process fault injection so error-path Claude scenarios can be reproduced intentionally rather than depending only on ambient live failures.

The first supported mechanism MAY be syscall-level subprocess injection, such as targeted network syscall failure for the launched Claude process. If additional disruption methods are added later, they SHALL remain explicit scenario mechanisms rather than invisible environment assumptions.

The harness SHALL record the selected fault-injection mechanism and target timing in the scenario control artifacts.

#### Scenario: Startup failure scenario uses deliberate injected fault
- **WHEN** a developer runs a startup-network-failure scenario
- **THEN** the harness uses a deliberate subprocess-level fault injection mechanism to provoke the failure
- **AND THEN** the captured artifacts allow the resulting Claude TUI failure surface to be analyzed as a reproducible state-discovery case

#### Scenario: Mid-turn failure scenario uses deliberate injected fault
- **WHEN** a developer runs a mid-turn-network-failure scenario
- **THEN** the harness applies a deliberate subprocess-level fault injection mechanism during an active Claude turn
- **AND THEN** the captured artifacts allow replay and groundtruth comparison to verify whether the resulting surface is classified as `known_failure`, `unknown`, or later recovery

### Requirement: Abrupt process loss SHALL remain a diagnostics path unless a recognized visible crash signal exists
When the supported Claude process exits abruptly because it is killed, segfaults, or otherwise disappears without a separately recognized visible failure signal, the harness SHALL treat that path as a diagnostics outcome rather than automatically turning it into `interrupted` or `known_failure`.

At minimum:

- process-down while tmux survives SHALL map to the equivalent of `tui_down`,
- target disappearance SHALL map to the equivalent of `unavailable`, and
- neither path SHALL automatically emit a new terminal turn outcome unless a separately recognized visible signal supports it.

#### Scenario: Process killed while tmux survives does not fabricate interrupted or known-failure
- **WHEN** an active or ready Claude session has its subprocess killed while the tmux target remains observable
- **THEN** the resulting replay and groundtruth classification reflect the process-down diagnostics path
- **AND THEN** the harness does not fabricate `interrupted` or `known_failure` from process death alone

#### Scenario: Target disappearance does not fabricate a normal terminal turn result
- **WHEN** the tmux target disappears entirely during a scenario run
- **THEN** the resulting replay and groundtruth classification reflect the unavailable diagnostics path
- **AND THEN** the harness does not fabricate `success`, `interrupted`, or `known_failure` from that disappearance alone

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

### Requirement: Explore harness SHALL formalize newly discovered stable signals as state-discovery notes
When live capture, replay comparison, or validation of the explore harness reveals a new stable and useful Claude TUI signal, the workflow SHALL record that signal as a formal state-discovery note rather than leaving it only in implementation code or transient run logs.

Each formalized signal note SHALL capture, at minimum:

- tool and observed version context,
- the visible pattern or structural matcher,
- recency or current-region constraints,
- the supported state or terminal outcome, and
- at least one concrete observed example or artifact reference.

#### Scenario: Validation discovers a new Claude signal and records it formally
- **WHEN** a developer validates the harness and finds a new stable Claude signal that improves state detection
- **THEN** that signal is recorded as a formal state-discovery note with matcher and non-match guidance
- **AND THEN** the detector and later validation can refer back to that maintained signal note instead of relying on undocumented implementation heuristics

### Requirement: Explore harness SHALL ship an initial scenario corpus for the highest-value Claude turn boundaries
The explore harness SHALL include an initial scenario set that exercises the most important boundaries of the simplified state model for Claude Code.

At minimum, the initial scenario corpus SHALL include:

- one success scenario,
- one interruption scenario, and
- one active-turn noise scenario where slash-menu or similar prompt-overlay churn appears during an otherwise active turn,
- one current known-failure scenario,
- one scenario where stale known-failure history is superseded by a later successful turn,
- one ready-surface noise scenario where local prompt churn happens without starting a turn,
- one ambiguous-surface scenario that drives `turn.phase=unknown` and later recovers to a known posture, and
- one settle-reset scenario where apparent completion evidence changes before the settle window elapses and success must be delayed until the later stable surface,
- one startup-network-failure-injected scenario, and
- one mid-turn-network-failure-injected scenario,
- one process-killed-tmux-still-alive scenario, and
- one target-disappeared-unavailable scenario.

#### Scenario: Initial corpus exercises slash-menu noise during active Claude processing
- **WHEN** a developer runs the initial slash-noise scenario
- **THEN** the captured and replayed artifacts include a period where prompt-overlay churn appears during an already-active Claude turn
- **AND THEN** the comparison flow can verify whether replay tracking preserved `turn_active` instead of misclassifying that overlay as a different semantic turn kind

#### Scenario: Initial corpus exercises current known failure
- **WHEN** a developer runs the initial known-failure scenario
- **THEN** the captured and replayed artifacts include a current Claude surface that matches one supported known-failure rule
- **AND THEN** the comparison flow can verify whether replay tracking records `known_failure` rather than collapsing the current turn into a generic `unknown` or stale-history artifact

#### Scenario: Initial corpus exercises stale known-failure suppression before later success
- **WHEN** a developer runs the initial stale-known-failure scenario
- **THEN** the captured and replayed artifacts include an older failure-bearing transcript block that remains visible while a later turn reaches success
- **AND THEN** the comparison flow can verify whether replay tracking suppresses the stale failure as current state for the later successful turn

#### Scenario: Initial corpus exercises ready-surface noise without submit
- **WHEN** a developer runs the initial ready-noise scenario
- **THEN** the captured and replayed artifacts include visible prompt-area churn such as local editing or slash-menu opening without an actual submitted turn
- **AND THEN** the comparison flow can verify whether replay tracking keeps the posture out of false `active` or false terminal outcomes

#### Scenario: Initial corpus exercises unknown-state recovery
- **WHEN** a developer runs the initial ambiguous-surface scenario
- **THEN** the captured and replayed artifacts include a period where the current Claude surface is not safely classifiable as `ready` or `active`
- **AND THEN** the comparison flow can verify whether replay tracking emits `turn.phase=unknown` for that period and later recovers to the correct known posture when clearer evidence returns

#### Scenario: Initial corpus exercises settle reset before final success
- **WHEN** a developer runs the initial settle-reset scenario
- **THEN** the captured and replayed artifacts include a candidate completion surface that changes again before the settle window elapses
- **AND THEN** the comparison flow can verify whether replay tracking resets pending success and emits `success` only after the later stable completion surface

#### Scenario: Initial corpus exercises injected startup network failure
- **WHEN** a developer runs the initial startup-network-failure-injected scenario
- **THEN** the captured and replayed artifacts include a Claude startup failure surface caused by deliberate subprocess fault injection
- **AND THEN** the comparison flow can verify the resulting known-failure or unknown classification against the recorded surface

#### Scenario: Initial corpus exercises injected mid-turn network failure
- **WHEN** a developer runs the initial mid-turn-network-failure-injected scenario
- **THEN** the captured and replayed artifacts include a Claude active-turn surface followed by a deliberate injected network failure
- **AND THEN** the comparison flow can verify the resulting transition through active, failure or unknown, and any later recovery semantics

#### Scenario: Initial corpus exercises process killed while tmux survives
- **WHEN** a developer runs the initial process-killed-tmux-still-alive scenario
- **THEN** the captured and replayed artifacts include a Claude subprocess death while the tmux target remains observable
- **AND THEN** the comparison flow can verify diagnostics classification for process-down without a fabricated terminal turn result

#### Scenario: Initial corpus exercises target disappearance as unavailable
- **WHEN** a developer runs the initial target-disappeared-unavailable scenario
- **THEN** the captured and replayed artifacts include loss of the tmux target itself
- **AND THEN** the comparison flow can verify diagnostics classification for target-unavailable without a fabricated normal terminal outcome
