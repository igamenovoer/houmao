# passive-server-tui-observation Specification

## Purpose

Define how the passive server observes discovered tmux-backed agents, tracks their live TUI state, and exposes compact, detailed, and historical observation APIs.

## Requirements

### Requirement: Passive server creates and removes per-agent TUI observers based on the discovery index
The passive server SHALL maintain a `TuiObservationService` that reconciles active observers against the current discovery index on each observation poll cycle.

The service SHALL create an `AgentTuiObserver` when discovery finds a parser-backed `tui` agent with a terminal native surface and `terminal.session_name`. When an agent disappears from the index, the service SHALL remove and clean up its observer.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The observation service SHALL start during server startup (after discovery) and stop during server shutdown.

An interactive Web agent SHALL use structured native observation instead of an `AgentTuiObserver`, even when registry metadata includes its supervisory tmux session. Disappearance SHALL clean up that agent's Web observation independently of terminal observers.

#### Scenario: Observer created when agent is discovered
- **WHEN** the discovery index contains a parser-backed `tui` agent with agent_id `abc123`, a terminal surface, and a live tmux session
- **AND WHEN** no observer exists for `abc123`
- **THEN** the observation service creates an `AgentTuiObserver` for `abc123`

#### Scenario: Observer removed when agent disappears
- **WHEN** an observer exists for agent_id `abc123`
- **AND WHEN** the discovery index no longer contains `abc123`
- **THEN** the observation service removes and cleans up the observer for `abc123`

#### Scenario: Observer is not duplicated for an already-observed agent
- **WHEN** an observer already exists for agent_id `abc123`
- **AND WHEN** the discovery index still contains `abc123`
- **THEN** the observation service keeps the existing observer without replacement

#### Scenario: DSH Web Has a Supervisory Terminal
- **WHEN** discovery finds `dsh_web` with a Web native surface and a tmux supervisor
- **THEN** the passive server selects native Web observation and creates no terminal TUI parser for that pane

#### Scenario: A service has a supervisory tmux session

- **WHEN** the passive server discovers a `service` agent with an owner pane
- **THEN** it reads verified native service observation and never installs a TUI parser for the owner pane

#### Scenario: Hermes TUI Has a Live Terminal

- **WHEN** discovery finds Hermes in tui mode with a live terminal and structured native control
- **THEN** the passive server uses the structured control source and publishes its non-secret terminal handoff
- **AND THEN** discovery and removal do not create or retain a terminal-text observer for Hermes

### Requirement: Each agent observer polls the tmux pane and produces tracked state
Each `AgentTuiObserver` SHALL poll its tmux pane on every observation cycle and use the captured text to update tracked state. It SHALL record diagnostics and continue polling after a failure.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Each `AgentTuiObserver` SHALL execute a polling pipeline on each observation cycle that:
1. Resolves the tmux target (session, pane) using `TmuxTransportResolver`.
2. Inspects the pane's process tree using `PaneProcessInspector` to determine TUI process liveness.
3. Captures the pane text content.
4. Parses the captured text through `OfficialTuiParserAdapter` to produce a `HoumaoParsedSurface`.
5. Feeds the output text to the `TuiTrackerSession` for signal detection and state tracking.
6. Records diagnostics: transport state, process state, parse status, probe snapshot.

If any step fails (tmux unavailable, process down, parse error), the observer SHALL record the appropriate diagnostic state and continue to the next cycle.

#### Scenario: Successful poll cycle produces parsed state
- **WHEN** the tmux session is live and the TUI process is running
- **AND WHEN** the pane text is captured and parsed successfully
- **THEN** the observer produces a tracked state with `diagnostics.availability == "available"` and a non-null `parsed_surface`

#### Scenario: Poll cycle with dead tmux session records transport error
- **WHEN** the tmux session for the agent no longer exists
- **THEN** the observer records `diagnostics.transport_state == "tmux_missing"` and `diagnostics.availability == "unavailable"`

#### Scenario: Poll cycle with TUI process down records process state
- **WHEN** the tmux session exists but no supported TUI process is running in the pane
- **THEN** the observer records `diagnostics.process_state == "tui_down"` and `diagnostics.availability == "tui_down"`

#### Scenario: Poll cycle with parse error records parse status
- **WHEN** the pane text is captured but the parser fails
- **THEN** the observer records `diagnostics.parse_status == "parse_error"` and the parse error detail

### Requirement: Observation service runs a shared background polling loop
The `TuiObservationService` SHALL run a single background thread that iterates over all active observers on a configurable interval (default 2 seconds, configured via `observation_poll_interval_seconds` in `PassiveServerConfig`).

Each iteration SHALL:
1. Read the current discovery index snapshot.
2. Reconcile observers (create new, remove stale).
3. Poll each active observer.

#### Scenario: Polling loop runs at the configured interval
- **WHEN** `observation_poll_interval_seconds` is set to 3.0
- **THEN** the observation loop waits approximately 3 seconds between iterations

#### Scenario: Polling loop survives individual observer failures
- **WHEN** one observer's poll cycle raises an exception
- **THEN** the loop logs the error and continues to the next observer without crashing

### Requirement: Compact agent state endpoint returns observation summary
`GET /houmao/agents/{agent_ref}/state` SHALL resolve the agent and report compact state from its qualified source. Parser-backed state contains:
- `agent_id`, `agent_name`
- `diagnostics` summary (availability, transport state, process state, parse status)
- `surface` signals (accepting_input, editing_input, ready_posture)
- `turn` state (phase)
- `last_turn` state (result, source, updated_at_utc)
- `stability` metadata (stable, stable_for_seconds, stable_since_utc)

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The compact endpoint SHALL NOT include `probe_snapshot` or `parsed_surface`.

The endpoint SHALL return 404 if the agent is not found, 409 if ambiguous, and 503 if its required observation source has not initialized.

For headless and service modes, the endpoint SHALL project native turn or connection evidence for the recorded mode and expose unavailable evidence explicitly. For an interactive Web agent, the endpoint SHALL return a Web-discriminated compact state with common identity, diagnostics, turn, and admission facts sourced from native observation. It SHALL NOT require a terminal observer or fabricate terminal signal fields. Missing or stale Web authority SHALL produce explicit unavailable semantics.

#### Scenario: Compact state returned for observed agent
- **WHEN** the agent `abc123` has an active observer with tracked state
- **THEN** `GET /houmao/agents/abc123/state` returns 200 with diagnostics, surface, turn, stability fields

#### Scenario: Compact state omits probe and parsed surface
- **WHEN** the agent has a fully parsed observation
- **THEN** the compact response does NOT include `probe_snapshot` or `parsed_surface` fields

#### Scenario: Agent not found returns 404
- **WHEN** no agent matches the `agent_ref`
- **THEN** the endpoint returns 404

#### Scenario: Compact Web State Is Available Without a Terminal Observer
- **WHEN** verified structured Web observation exists for the bound DSH session
- **THEN** the compact state route returns native Web state without requiring a terminal observer

#### Scenario: Idle service without a terminal observer

- **WHEN** a service owner reports a verified idle session
- **THEN** the compact response uses the service observation source and includes its actual admission state

#### Scenario: Hermes TUI State Uses Native Observation

- **WHEN** the passive server resolves a Hermes TUI agent
- **THEN** the compact state identifies the TUI mode, verified native activity, and terminal attachment separately
- **AND THEN** unavailable native observation leaves the pane reference inspectable without reporting the agent ready from terminal rendering

### Requirement: Detailed agent state endpoint returns full observation

`GET /houmao/agents/{agent_ref}/state/detail` SHALL extend compact state and use its 404/409/503 rules. Structured TUI, headless, service, and Web agents SHALL use their native detail models and omit terminal parser fields.

#### Scenario: Parser-Backed Detail Exposes Its Existing Fields

- **WHEN** the route returns parser-backed terminal detail
- **THEN** it adds `probe_snapshot` with `observed_at_utc`, `pane_id`, `pane_pid`, `captured_text_hash`, `captured_text_length`, `captured_text_excerpt`, and `matched_process_names`
- **AND THEN** `parsed_surface` includes `parser_family`, `availability`, `business_state`, `input_mode`, and `ui_context` when it is available

#### Scenario: Detail state includes probe and parsed surface
- **WHEN** the agent has a fully parsed observation
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns 200 with `probe_snapshot` and `parsed_surface` included

#### Scenario: Detail state with diagnostics-only observation
- **WHEN** the parser-backed agent's TUI process is down
- **THEN** the detail response includes diagnostics but `parsed_surface` is null

#### Scenario: Web Detail Does Not Contain Parsed Console State
- **WHEN** the agent is interactive DSH Web
- **THEN** the detail response identifies its Web surface and native execution state
- **AND THEN** the supervisor's log excerpt is not represented as a parsed agent interface

#### Scenario: Service owner loses its native connection

- **WHEN** the owner remains discoverable after a service exits
- **THEN** detail reports the unavailable connection and retains only attributable last-known evidence

#### Scenario: Hermes TUI Detail Uses Native Evidence

- **WHEN** a caller requests details for a Hermes TUI agent
- **THEN** detail includes native control status and terminal attachment and omits parser fields

### Requirement: Agent history endpoint returns recent transitions

`GET /houmao/agents/{agent_ref}/history` SHALL return latest transitions (query `limit`, default 50) with state-route 404/409/503 rules. Entries SHALL include recorded_at_utc,summary,changed_fields,diagnostics_availability,turn_phase,last_turn_result,last_turn_source,transport_state,process_state,parse_status. Web history SHALL retain bounded native transitions and Web transport/execution identities. Process/parser fields stay terminal-only; host logs SHALL NOT generate Web history.

#### Scenario: History returns recent transitions
- **WHEN** the agent has recorded 5 state transitions
- **THEN** `GET /houmao/agents/{agent_ref}/history` returns all 5 transitions ordered most-recent-first

#### Scenario: History respects limit parameter
- **WHEN** the agent has 100 transitions and `limit=10` is specified
- **THEN** the response contains only the 10 most recent transitions

#### Scenario: Human Web Input Changes Shared History
- **WHEN** a human starts or interrupts work through the bound browser session
- **THEN** Web observation history records the corresponding native transitions within its bounded retention

### Requirement: Observation poll interval is configurable
`PassiveServerConfig` SHALL include an `observation_poll_interval_seconds` field with a default of 2.0 seconds and a minimum of 0.5 seconds.

#### Scenario: Default observation poll interval
- **WHEN** no explicit value is provided for `observation_poll_interval_seconds`
- **THEN** the default is 2.0 seconds

#### Scenario: Invalid observation poll interval rejected
- **WHEN** `observation_poll_interval_seconds` is set to 0.1
- **THEN** config validation rejects the value

### Requirement: Passive-server TUI observation projects pending input consistently

The maintained passive-server observation path SHALL include `surface.pending_input` in compact TUI state, detailed TUI state, bounded history, and any managed-agent TUI projection that exposes the canonical tracked surface.

The projected field SHALL preserve the authoritative tracker value without deriving a second pending-input interpretation from parsed sidecar state, gateway requests, or passive-server submission records.

#### Scenario: Compact TUI state includes pending input

- **WHEN** a caller requests compact state for an observed TUI agent
- **THEN** the response surface includes `pending_input` alongside `accepting_input`, `editing_input`, and `ready_posture`
- **AND THEN** the value matches the authoritative current tracked snapshot

#### Scenario: Detailed and history responses preserve pending transitions

- **WHEN** an observed TUI changes from no provider-native pending instruction to a visible pending instruction
- **THEN** detailed state exposes the current `surface.pending_input=yes`
- **AND THEN** bounded history preserves the corresponding pending-input transition even when the turn phase remains active

#### Scenario: Passive-server projection does not infer pending from prompt submission

- **WHEN** the passive server proxies or records a prompt submission before the TUI observation changes
- **THEN** the projected pending-input value remains the tracker-owned value from the latest observed surface
- **AND THEN** the passive server does not set it from submission history
