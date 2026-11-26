# Spec Delta

## MODIFIED Requirements

### Requirement: Run admission follows existing gateway controls

AG-UI run submission SHALL use the existing per-agent gateway admission controls instead of bypassing or duplicating Houmao request scheduling.

The run service SHALL reject invalid input, unavailable transports, and busy agents at its final check before emitting `RUN_STARTED`.

The run service SHALL pass the AG-UI `runId` as the gateway prompt `turn_id` so headless artifacts have a stable run-specific location.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The run service SHALL reject overlapping AG-UI runs for the same target unless a later change explicitly adds queued AG-UI stream semantics.

#### Scenario: Invalid input is rejected before streaming

- **WHEN** a caller posts malformed AG-UI input to `POST /v1/ag-ui/runs`
- **THEN** the gateway returns an HTTP validation error before any SSE frame is emitted
- **AND THEN** no prompt is submitted
- **AND THEN** no `RUN_STARTED` event is emitted

#### Scenario: Busy agent is rejected before streaming

- **WHEN** the target gateway reports active work or a non-empty admitted queue
- **AND WHEN** a caller posts otherwise valid AG-UI run input
- **THEN** the gateway returns a deterministic busy response before any SSE frame is emitted
- **AND THEN** no prompt is submitted for that AG-UI run

#### Scenario: Unavailable transport is rejected before streaming

- **WHEN** the target gateway transport is unavailable or cannot admit prompt work
- **AND WHEN** a caller posts otherwise valid AG-UI run input
- **THEN** the gateway returns a deterministic unavailable response before any SSE frame is emitted
- **AND THEN** no prompt is submitted for that AG-UI run

#### Scenario: AG-UI run id becomes gateway turn id

- **WHEN** a caller posts valid AG-UI run input with `runId` equal to `run-alpha`
- **AND WHEN** the gateway admits the run
- **THEN** the submitted gateway prompt payload uses `turn_id` equal to `run-alpha`

#### Scenario: Hermes Accepts After a Human Starts First

- **WHEN** an otherwise eligible AG-UI run passes Hermes TUI's final idle check and Hermes accepts it in the native queue
- **THEN** the stream emits `RUN_STARTED` for the admitted Houmao run and reports queued native activity
- **AND THEN** the AG-UI admission does not claim that native execution has started or admit a second overlapping AG-UI run

### Requirement: TUI targets stream lower-fidelity AG-UI output

Parser-backed TUI run streams SHALL use their lower-fidelity observation source and remain protocol-compatible.

The TUI stream SHALL emit `RUN_STARTED` after admission.

The TUI stream SHALL emit a sanitized `STATE_SNAPSHOT` or activity event with current gateway and TUI status.

The TUI stream SHALL emit final assistant text when a parsed terminal surface or dialog tail is available.

The TUI stream SHALL NOT claim headless-level tool-call semantics from raw terminal text.

#### Scenario: TUI output maps to status and final text

- **WHEN** an AG-UI run is admitted for a parser-backed TUI gateway target
- **THEN** the stream emits `RUN_STARTED`
- **AND THEN** the stream emits state or activity events describing gateway and TUI status
- **AND THEN** the stream emits final assistant text when parsed final text is available
- **AND THEN** the stream emits `RUN_FINISHED` or `RUN_ERROR`

#### Scenario: TUI stream does not invent tool calls

- **WHEN** a parser-backed terminal surface contains text that resembles a tool call
- **THEN** the AG-UI mapper does not emit `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, or `TOOL_CALL_RESULT` unless a structured Houmao event exists

### Requirement: Run streams preserve mode-specific correlation

An AG-UI run SHALL submit through the selected agent's shared control boundary and map events only at the correlation strength supported by that mode. Native service notifications, structured TUI events, and Web activity SHALL be bound to the selected native session and attributable turn before publication as that run's output.

#### Scenario: A browser starts another turn

- **WHEN** the native Web host reports activity for a human turn while an AG-UI run exists
- **THEN** the stream keeps that activity distinct and does not use it to complete the AG-UI run

#### Scenario: Service stream loses attribution

- **WHEN** a service reconnects without evidence binding a terminal notification to the original run
- **THEN** the stream reports a bounded error or uncertainty through its documented terminal path without fabricating a successful result or resubmitting input

#### Scenario: A Human Turn Settles While the Hermes Run Is Queued

- **WHEN** a Hermes TUI human turn emits output and completes while the tracked AG-UI native admission is queued
- **THEN** the stream does not attribute the human turn's assistant or tool output to the tracked run
- **AND THEN** it settles only from the matching native admission's terminal outcome or the documented error path for lost attribution
