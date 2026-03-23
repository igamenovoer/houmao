## ADDED Requirements

### Requirement: Diagnostics availability statechart diagram
The transitions guide SHALL include a Mermaid `stateDiagram-v2` showing all five `diagnostics.availability` values (`unknown`, `available`, `unavailable`, `tui_down`, `error`) as states, with labeled transitions indicating what causes each transition (tmux session appearing/disappearing, TUI process starting/stopping, parser success/failure, probe error). The entry state SHALL be `unknown`. The diagram SHALL visually highlight that `available` is the only state that enables meaningful surface and turn tracking.

#### Scenario: New developer reads diagnostics transitions
- **WHEN** a new developer opens the transitions guide
- **THEN** they see a statechart diagram where all five diagnostics values are states with labeled transition arrows, and can trace the path from initial `unknown` to `available` without reading prose

#### Scenario: Available highlighted as gateway state
- **WHEN** a reader views the diagnostics statechart
- **THEN** the diagram makes clear that `available` is the prerequisite for meaningful surface/turn values, and that non-available states degrade surface observables to `unknown`

### Requirement: Turn phase statechart diagram
The transitions guide SHALL include a Mermaid `stateDiagram-v2` showing all three `turn.phase` values (`unknown`, `ready`, `active`) as states, with labeled transitions indicating what causes each transition (anchor arming, active evidence from detector, completion settle, diagnostics degradation, ambiguous interactive surface). The entry state SHALL be `unknown`.

#### Scenario: New developer reads turn phase transitions
- **WHEN** a new developer opens the transitions guide
- **THEN** they see a statechart diagram for turn phase and can trace how `ready` → `active` → `ready` works during a normal turn

#### Scenario: Unknown phase causes visible
- **WHEN** a reader views the turn phase statechart
- **THEN** the diagram shows that diagnostics degradation and ambiguous interactive surfaces both produce `unknown`, and that `unknown` is not an error — it means the system cannot confidently classify the posture

### Requirement: Last-turn result statechart diagram
The transitions guide SHALL include a Mermaid `stateDiagram-v2` showing all four `last_turn.result` values (`none`, `success`, `interrupted`, `known_failure`) as states, with labeled transitions indicating what causes each transition (settle timer fires for `success`, interruption signal for `interrupted`, failure signal for `known_failure`). The entry state SHALL be `none`. The diagram SHALL indicate that `last_turn` is sticky — it only changes on terminal outcomes, not on every poll cycle.

#### Scenario: Sticky nature of last_turn visible
- **WHEN** a reader views the last-turn statechart
- **THEN** the diagram shows that `last_turn.result` persists across poll cycles and only updates when a new terminal outcome is detected

#### Scenario: Success retraction path visible
- **WHEN** a reader views the last-turn statechart
- **THEN** the diagram shows that a premature `success` can be retracted if the surface proves to still be evolving within the same anchor

### Requirement: Turn lifecycle sequence diagram
The transitions guide SHALL include a Mermaid `sequenceDiagram` showing a complete turn lifecycle from the TUI consumer's perspective. The diagram SHALL show two variants: (1) **successful turn**: consumer sends input via API → server arms explicit_input anchor → `turn.phase` becomes `active` → detector sees active evidence → detector sees success candidate → settle timer fires → `last_turn.result` becomes `success` → `turn.phase` becomes `ready`; (2) **interrupted turn**: same start, but detector sees interruption signal → `last_turn.result` becomes `interrupted` → `turn.phase` becomes `ready`. Participants SHALL include Consumer, Server (`/houmao/terminals/` API), LiveSessionTracker, and Detector.

#### Scenario: New developer traces a successful turn
- **WHEN** a new developer reads the sequence diagram
- **THEN** they can follow the temporal flow of a turn from input submission through active phase to settled success without reading reducer code

#### Scenario: Interrupted variant visible alongside success
- **WHEN** a reader views the sequence diagram
- **THEN** the interrupted path is shown as an alternate branch from the same active phase, making the divergence point clear

### Requirement: State composition flowchart
The transitions guide SHALL include a Mermaid `flowchart TD` showing how low-level observations (tmux probe, process inspection, parser output) compose upward through detectors (`shared_tui_tracking/detectors.py`) and mapping helpers (`shared_tui_tracking/public_state.py`) into the four public state groups (`diagnostics`, `surface`, `turn`, `last_turn`), plus `stability` and `recent_transitions`. This updates and replaces the existing composition flowchart in `state-tracking.md` to reflect the shared module extraction.

#### Scenario: Full derivation pipeline visible
- **WHEN** a new developer wants to understand how raw tmux output becomes public state
- **THEN** the flowchart shows the pipeline from probe → process → parse → detect → reduce → public state in one visual

### Requirement: Operation acceptability per state
The transitions guide SHALL document, for each major state combination, which operations are acceptable: sending input (`POST /houmao/terminals/{terminal_id}/input`), expecting meaningful state polling (`GET /houmao/terminals/{terminal_id}/state`), or waiting for stability. All route references SHALL use Houmao-native `/houmao/*` paths. This section SHALL appear after the diagrams, so readers arrive at the operational guidance already understanding the state model.

#### Scenario: Available + ready state operations documented
- **WHEN** diagnostics is `available` and turn phase is `ready`
- **THEN** the guide states that sending input is safe, the terminal is ready to accept a new prompt

#### Scenario: Active state operations documented
- **WHEN** turn phase is `active`
- **THEN** the guide states that input submission is not expected (the agent is working), and the consumer should poll for turn completion or stability

#### Scenario: Unavailable/error state operations documented
- **WHEN** diagnostics is `unavailable`, `tui_down`, or `error`
- **THEN** the guide states that input submission will not reach a prompt and the consumer should wait for recovery or investigate the tmux/process layer

#### Scenario: Unknown state operations documented
- **WHEN** turn phase is `unknown`
- **THEN** the guide states that the consumer should wait for the state to resolve rather than assuming ready or active

### Requirement: Stability and timing guidance
The transitions guide SHALL explain how `stability.stable_for_seconds` affects operation timing — specifically, that consumers should wait for stable state before acting on a turn outcome, and that premature action on an unstable surface risks acting on a transient state.

#### Scenario: Stability window guidance present
- **WHEN** a reader looks up how to determine when a turn is truly complete
- **THEN** the guide explains that `last_turn.result` combined with `stability.stable_for_seconds` above a threshold indicates a settled outcome, and that acting before stability risks seeing a retracted premature success

### Requirement: Turn anchor effects on operation timing
The transitions guide SHALL explain that `last_turn.source` indicates whether the turn was initiated via the server API (`explicit_input`) or inferred from direct tmux interaction (`surface_inference`), and that `explicit_input` turns have tighter settle guarantees.

#### Scenario: Anchor source timing difference documented
- **WHEN** a reader looks up turn source differences
- **THEN** the guide explains that `explicit_input` turns are armed immediately on API input submission, while `surface_inference` turns require a multi-condition guard (prior stable ready surface + material output growth) and may have slightly longer settle times

### Requirement: Reducer transition rules documented
The transitions guide SHALL explain that the `StreamStateReducer` in `shared_tui_tracking/reducer.py` applies the same state transition priorities as the live tracker: diagnostics degradation overrides surface signals; `interrupted` and `known_failure` immediately produce terminal outcomes and cancel pending success timers; `active_evidence` arms a turn source via surface inference when no explicit input exists; `success_candidate` arms a settle timer that promotes to `success` only after the settle window elapses without surface change or error.

#### Scenario: Reducer priority chain documented
- **WHEN** a reader wants to understand why `interrupted` overrides an in-progress `success_candidate`
- **THEN** the guide explains the reducer's priority chain: diagnostics → interrupted → known_failure → active_evidence → success_candidate → default
