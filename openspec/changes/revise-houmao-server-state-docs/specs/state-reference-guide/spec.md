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

### Requirement: Source-of-truth pointer to models.py
The state reference guide SHALL include an explicit note that the canonical definitions of all state enums live in `src/houmao/server/models.py` and that the guide is a human-readable companion, not a replacement.

#### Scenario: Source pointer present
- **WHEN** a reader opens the state reference guide
- **THEN** a header-level note links to `src/houmao/server/models.py` as the canonical source of truth
