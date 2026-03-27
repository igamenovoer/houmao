## ADDED Requirements

### Requirement: Passive server creates and removes per-agent TUI observers based on the discovery index
The passive server SHALL maintain a `TuiObservationService` that reconciles active observers against the current discovery index on each observation poll cycle.

When a newly discovered agent appears in the index and has a tmux-based terminal (`terminal.session_name` is present), the service SHALL create an `AgentTuiObserver` for that agent. When an agent disappears from the index, the service SHALL remove and clean up its observer.

The observation service SHALL start during server startup (after discovery) and stop during server shutdown.

#### Scenario: Observer created when agent is discovered
- **WHEN** the discovery index contains an agent with agent_id `abc123` and a live tmux session
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

### Requirement: Each agent observer polls the tmux pane and produces tracked state
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
`GET /houmao/agents/{agent_ref}/state` SHALL resolve the agent, look up its observer, and return a compact observation state response containing:
- `agent_id`, `agent_name`
- `diagnostics` summary (availability, transport state, process state, parse status)
- `surface` signals (accepting_input, editing_input, ready_posture)
- `turn` state (phase)
- `last_turn` state (result, source, updated_at_utc)
- `stability` metadata (stable, stable_for_seconds, stable_since_utc)

The compact endpoint SHALL NOT include `probe_snapshot` or `parsed_surface`.

The endpoint SHALL return 404 if the agent is not found, 409 if ambiguous, and 503 if no observer exists for the agent (agent discovered but observation not yet initialized).

#### Scenario: Compact state returned for observed agent
- **WHEN** the agent `abc123` has an active observer with tracked state
- **THEN** `GET /houmao/agents/abc123/state` returns 200 with diagnostics, surface, turn, stability fields

#### Scenario: Compact state omits probe and parsed surface
- **WHEN** the agent has a fully parsed observation
- **THEN** the compact response does NOT include `probe_snapshot` or `parsed_surface` fields

#### Scenario: Agent not found returns 404
- **WHEN** no agent matches the `agent_ref`
- **THEN** the endpoint returns 404

### Requirement: Detailed agent state endpoint returns full observation
`GET /houmao/agents/{agent_ref}/state/detail` SHALL return the full observation state including all fields from the compact endpoint plus:
- `probe_snapshot` (observed_at_utc, pane_id, pane_pid, captured_text_hash, captured_text_length, captured_text_excerpt, matched_process_names)
- `parsed_surface` (parser_family, availability, business_state, input_mode, ui_context, etc.)

The endpoint SHALL return 404, 409, or 503 using the same rules as the compact endpoint.

#### Scenario: Detail state includes probe and parsed surface
- **WHEN** the agent has a fully parsed observation
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns 200 with `probe_snapshot` and `parsed_surface` included

#### Scenario: Detail state with diagnostics-only observation
- **WHEN** the agent's TUI process is down
- **THEN** the detail response includes diagnostics but `parsed_surface` is null

### Requirement: Agent history endpoint returns recent transitions
`GET /houmao/agents/{agent_ref}/history` SHALL return the most recent state transitions for the agent, up to a configurable limit (query parameter `limit`, default 50).

Each transition entry SHALL include: `recorded_at_utc`, `summary`, `changed_fields`, `diagnostics_availability`, `turn_phase`, `last_turn_result`, `last_turn_source`, `transport_state`, `process_state`, `parse_status`.

The endpoint SHALL return 404, 409, or 503 using the same rules as the state endpoints.

#### Scenario: History returns recent transitions
- **WHEN** the agent has recorded 5 state transitions
- **THEN** `GET /houmao/agents/{agent_ref}/history` returns all 5 transitions ordered most-recent-first

#### Scenario: History respects limit parameter
- **WHEN** the agent has 100 transitions and `limit=10` is specified
- **THEN** the response contains only the 10 most recent transitions

### Requirement: Observation poll interval is configurable
`PassiveServerConfig` SHALL include an `observation_poll_interval_seconds` field with a default of 2.0 seconds and a minimum of 0.5 seconds.

#### Scenario: Default observation poll interval
- **WHEN** no explicit value is provided for `observation_poll_interval_seconds`
- **THEN** the default is 2.0 seconds

#### Scenario: Invalid observation poll interval rejected
- **WHEN** `observation_poll_interval_seconds` is set to 0.1
- **THEN** config validation rejects the value
