## ADDED Requirements

### Requirement: Kimi TUI tracking SHALL be based on recorded and labeled live evidence
Before Kimi Code TUI tracking is treated as implemented, the system SHALL produce a Kimi TUI signal corpus from live logged-in Kimi Code sessions.

The corpus SHALL include replay-grade tmux pane snapshots, input-event evidence when available, run metadata, Kimi CLI version metadata, manual labels, and notes describing the observed scenario.

The corpus SHALL include at least 5 labeled live sessions for development and at least 3 additional labeled live sessions held out as a test set. Held-out test sessions SHALL NOT be used to design detector rules, tune thresholds, or select the Kimi signal contract.

Each counted live session SHALL span multiple Kimi TUI state changes. Static one-state snapshots MAY be added as supplementary fixtures, but they SHALL NOT count toward the minimum live-session corpus.

The corpus SHALL live under a repo-local `tmp/kimi-tui-tracking/` root during capture and investigation. Curated committed fixtures MAY be promoted from that corpus after labels and replay validation are stable.

#### Scenario: Kimi capture run persists replay-grade evidence
- **WHEN** a maintainer records one live Kimi Code TUI scenario for signal investigation
- **THEN** the run root is created under `tmp/kimi-tui-tracking/`
- **AND THEN** the run root includes replay-grade pane snapshots, run metadata, and scenario notes
- **AND THEN** the metadata records the observed Kimi CLI version

#### Scenario: Kimi implementation waits for labels
- **WHEN** Kimi TUI detector implementation begins
- **THEN** a labeled Kimi capture corpus exists for the scenario families targeted by that implementation
- **AND THEN** detector behavior is verified against those labels rather than against only handwritten static snippets

#### Scenario: Development and held-out test sessions are separated
- **WHEN** the Kimi signal corpus is prepared for detector work
- **THEN** it contains at least 5 labeled development sessions and at least 3 labeled held-out test sessions
- **AND THEN** the held-out test sessions are not used for detector design or threshold tuning

#### Scenario: Counted Kimi sessions include multiple state changes
- **WHEN** one live Kimi session is counted toward the required corpus
- **THEN** its labels cover multiple state changes in sequence
- **AND THEN** a single static ready, active, or approval snapshot does not count as one required live session by itself

### Requirement: Kimi signal corpus SHALL include high-rate and derived low-rate streams
For each required Kimi TUI capture scenario, the corpus SHALL include a high-rate source snapshot stream sampled at about 10 fps and a low-rate derived stream sampled at about 2 fps from the high-rate source.

The low-rate stream SHALL preserve traceability to the source high-rate samples so validation can explain which original frames contributed to each derived sample.

#### Scenario: Low-rate Kimi stream is derived from high-rate source
- **WHEN** a maintainer records one Kimi scenario at about 10 fps
- **THEN** tooling derives an about 2 fps stream from that source run
- **AND THEN** each derived sample records or preserves the source sample identity used to create it

#### Scenario: Replay validation covers both sampling rates
- **WHEN** Kimi replay validation runs for one labeled scenario
- **THEN** validation compares tracker output against labels for the high-rate stream
- **AND THEN** validation also compares tracker output against labels for the derived low-rate stream

### Requirement: Kimi manual labels SHALL cover state ranges and evidence notes
Kimi signal labels SHALL support sample ranges as well as individual samples.

Each label SHALL record expected public tracked-state fields and MAY record parser-facing expectations such as `business_state`, `input_mode`, and `ui_context` when those fields are relevant to modal or approval surfaces.

Each label SHOULD include evidence notes that explain the human-observed structural, styling, temporal, or bounded semantic signals that justify the label.

At minimum, the Kimi corpus SHALL label these scenario families:

- idle welcome or editor-ready surface
- draft editing
- prompt submit, active response, completed response, and ready return
- command or tool approval prompt
- approval rejection
- interrupt during active turn
- footer metadata containing `thinking` while the current prompt is otherwise ready

#### Scenario: Approval range label records operator-blocked expectations
- **WHEN** a Kimi capture contains a command approval dialog over samples `s000120` through `s000145`
- **THEN** the label for that range records operator-blocked parser expectations
- **AND THEN** the label records public tracked-state expectations showing the surface is not ready for ordinary prompt submission

#### Scenario: Footer thinking label prevents false active inference
- **WHEN** a Kimi capture shows footer model metadata containing `thinking` while the prompt is otherwise ready
- **THEN** the label records ready public tracked-state expectations
- **AND THEN** the evidence note identifies the footer text as model metadata rather than current active-turn evidence

### Requirement: Kimi TUI signal design artifacts SHALL document stable signals before implementation
The change SHALL create Kimi signal design artifacts under change-local `context/`, `design/`, and `contracts/` directories before the Kimi detector profile is finalized.

Those artifacts SHALL document:

- captured scenarios and run roots
- Kimi TUI source-code investigation findings
- manually labeled state ranges
- stable structural anchors
- style-aware facts from ANSI rendering
- temporal signals and required sampling cadence
- bounded semantic signals allowed for Kimi
- forbidden fragile signals, including full exact-string matching outside bounded regions
- validation expectations for high-rate and low-rate replay

#### Scenario: Signal contract documents minimal stable Kimi signals
- **WHEN** a maintainer opens the Kimi signal contract artifact
- **THEN** it identifies the minimal Kimi TUI signals used by the detector
- **AND THEN** it explains which recorded samples justify those signals

#### Scenario: Signal design distinguishes source-backed structure from accidental text
- **WHEN** a maintainer opens the Kimi source-investigation notes
- **THEN** the notes identify which observed TUI signals come from Kimi component structure or style roles
- **AND THEN** the notes identify which observed words or layouts are treated as accidental or fragile

#### Scenario: Signal design rejects fragile exact-string dependence
- **WHEN** a Kimi detector rule depends on visible text
- **THEN** the signal design explains the bounded visual region and semantic role for that text
- **AND THEN** the design does not rely on one full upstream sentence as the primary long-term detector contract
