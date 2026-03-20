## ADDED Requirements

### Requirement: State transition diagram in Mermaid
The transitions guide SHALL include a Mermaid state diagram showing how `diagnostics.availability` transitions compose into `surface` observables, how surface observables combine with anchor state to produce `turn.phase`, and how terminal outcomes produce `last_turn.result`.

#### Scenario: Diagnostics-to-surface flow visible
- **WHEN** a reader views the Mermaid diagram
- **THEN** the diagram shows that `diagnostics.availability=available` is a prerequisite for meaningful `surface` values, and that non-available diagnostics degrade surface observables to `unknown`

#### Scenario: Surface-to-turn flow visible
- **WHEN** a reader views the Mermaid diagram
- **THEN** the diagram shows how `surface.ready_posture=yes` with no active anchor maps to `turn.phase=ready`, and how anchor arming maps to `turn.phase=active`

### Requirement: Operation acceptability per state
The transitions guide SHALL document, for each major state combination, which operations are acceptable: sending input (`POST /terminals/{id}/input`), expecting meaningful state polling, or waiting for stability.

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
