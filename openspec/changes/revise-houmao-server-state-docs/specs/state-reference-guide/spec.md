## ADDED Requirements

### Requirement: State value catalog covers all public enums
The state reference guide SHALL contain an entry for every value of every public state enum: `TrackedDiagnosticsAvailability` (`available`, `unavailable`, `tui_down`, `error`, `unknown`), `Tristate` surface observables (`yes`, `no`, `unknown` for `accepting_input`, `editing_input`, `ready_posture`), `ManagedAgentTurnPhase` (`ready`, `active`, `unknown`), `TrackedLastTurnResult` (`success`, `interrupted`, `known_failure`, `none`), and `TrackedLastTurnSource` (`explicit_input`, `surface_inference`, `none`).

#### Scenario: All diagnostics availability values documented
- **WHEN** a reader looks up `diagnostics.availability`
- **THEN** the guide lists all five values (`available`, `unavailable`, `tui_down`, `error`, `unknown`) with definitions

#### Scenario: All surface observable values documented
- **WHEN** a reader looks up any surface observable (`accepting_input`, `editing_input`, `ready_posture`)
- **THEN** the guide lists all three tristate values (`yes`, `no`, `unknown`) with per-field definitions

#### Scenario: All turn phase values documented
- **WHEN** a reader looks up `turn.phase`
- **THEN** the guide lists `ready`, `active`, `unknown` with definitions

#### Scenario: All last-turn result values documented
- **WHEN** a reader looks up `last_turn.result`
- **THEN** the guide lists `success`, `interrupted`, `known_failure`, `none` with definitions

### Requirement: Each state group opens with a Mermaid overview diagram
Each major state group section (`diagnostics.availability`, `turn.phase`, `last_turn.result`) in the state reference guide SHALL open with a compact Mermaid `stateDiagram-v2` showing all values as states with brief transition labels. These are simplified overview diagrams for quick orientation; the full transition details and sequence diagrams live in `state-transitions.md`. Each diagram SHALL include a cross-reference link to the corresponding full diagram in the transitions guide.

#### Scenario: Diagnostics section opens with statechart
- **WHEN** a reader scrolls to the `diagnostics.availability` section
- **THEN** a compact Mermaid statechart showing all five values with transition labels appears before the per-value entries, with a link to the full transitions guide

#### Scenario: Turn phase section opens with statechart
- **WHEN** a reader scrolls to the `turn.phase` section
- **THEN** a compact Mermaid statechart showing `unknown`, `ready`, `active` with transition labels appears before the per-value entries

#### Scenario: Last-turn section opens with statechart
- **WHEN** a reader scrolls to the `last_turn.result` section
- **THEN** a compact Mermaid statechart showing `none`, `success`, `interrupted`, `known_failure` with transition labels appears before the per-value entries

### Requirement: Each state value entry has three-layer structure
Each state value entry SHALL include: (1) an intuitive meaning in one sentence, (2) a technical derivation summary explaining what pipeline stage produces it, and (3) operational implications describing what operations are safe or expected when this value is active.

#### Scenario: Intuitive meaning present for every value
- **WHEN** a reader looks up any state value
- **THEN** the entry starts with a plain-language one-sentence meaning that does not require knowledge of the pipeline internals

#### Scenario: Technical derivation present for every value
- **WHEN** a reader looks up any state value
- **THEN** the entry includes a derivation summary referencing the pipeline stage (transport, process inspection, parser, signal detection, or reduction) that produces it

#### Scenario: Operational implications present for every value
- **WHEN** a reader looks up any state value
- **THEN** the entry includes guidance on what operations are safe (e.g., "safe to send input"), what to expect next (e.g., "will transition to available once TUI starts"), or what to avoid (e.g., "do not send input — it will not reach a prompt")

### Requirement: Source-of-truth pointer to shared_tui_tracking
The state reference guide SHALL include an explicit note that the canonical definitions of core state type literals (`Tristate`, `TrackedDiagnosticsAvailability`, `TurnPhase`, `TrackedLastTurnResult`, `TrackedLastTurnSource`, `TransportState`, `ProcessState`, `ParseStatus`) live in `src/houmao/shared_tui_tracking/models.py`, that the authoritative mapping functions live in `src/houmao/shared_tui_tracking/public_state.py`, and that `src/houmao/server/models.py` re-exports these types for the server's Pydantic response models. The guide is a human-readable companion, not a replacement.

#### Scenario: Source pointer present
- **WHEN** a reader opens the state reference guide
- **THEN** a header-level note links to `src/houmao/shared_tui_tracking/models.py` as the canonical type definition source, `src/houmao/shared_tui_tracking/public_state.py` as the canonical mapping logic source, and `src/houmao/server/models.py` as the Pydantic response model surface

### Requirement: Architecture note on two-consumer contract
The state reference guide SHALL include a brief architecture note explaining that the public state contract is implemented by two consumers: `LiveSessionTracker` in `src/houmao/server/tui/tracking.py` (live server polling) and `StreamStateReducer` in `src/houmao/shared_tui_tracking/reducer.py` (replay/offline). Both use the same type definitions and mapping helpers. The note SHALL clarify that `ManagedAgentTurnPhase` in the server models is an alias of `TurnPhase` from `shared_tui_tracking.models`, meaning TUI terminals and managed headless agents share the same turn vocabulary.

#### Scenario: Two-consumer architecture explained
- **WHEN** a reader opens the state reference guide
- **THEN** a dedicated section explains that `LiveSessionTracker` and `StreamStateReducer` both produce the same public state vocabulary

#### Scenario: TurnPhase alias clarified
- **WHEN** a reader encounters `ManagedAgentTurnPhase` in server models
- **THEN** the guide explains it is an alias of `TurnPhase` from `shared_tui_tracking.models`

### Requirement: Detector families listed with selection logic
The state reference guide SHALL include a section listing the three detector families (`claude_code` with version selector `2.1.x`, `codex_app_server`, and `unsupported_tool` fallback), their source in `src/houmao/shared_tui_tracking/detectors.py`, and the selection logic (`select_tracked_turn_signal_detector`). The section SHALL explain that surface observables and signal evidence are detector-produced, and that different tools may yield different `unknown` vs `yes`/`no` distributions for the same underlying conditions.

#### Scenario: Detector families listed
- **WHEN** a reader looks up how surface observables are derived
- **THEN** the guide lists the three detector families and their tool-to-detector mapping

#### Scenario: Detector variation explained
- **WHEN** a reader wonders why `ready_posture` is `unknown` for an unsupported tool but `yes` for Claude
- **THEN** the guide explains that detectors have different evidence thresholds per tool family
