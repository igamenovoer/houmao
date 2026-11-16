# Spec Delta

## MODIFIED Requirements

### Requirement: Passive server creates and removes per-agent TUI observers based on the discovery index
The passive server SHALL maintain a `TuiObservationService` that reconciles active observers against the current discovery index on each observation poll cycle.

When a newly discovered agent appears in the index and declares a terminal native surface with a tmux-based terminal (`terminal.session_name` is present), the service SHALL create an `AgentTuiObserver` for that agent. When an agent disappears from the index, the service SHALL remove and clean up its observer.

The observation service SHALL start during server startup (after discovery) and stop during server shutdown.

An interactive Web agent SHALL use structured native observation instead of an `AgentTuiObserver`, even when registry metadata includes its supervisory tmux session. Disappearance SHALL clean up that agent's Web observation independently of terminal observers.

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

#### Scenario: DSH Web Has a Supervisory Terminal
- **WHEN** discovery finds `dsh_web` with a Web native surface and a tmux supervisor
- **THEN** the passive server selects native Web observation and creates no terminal TUI parser for that pane


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

For an interactive Web agent, the endpoint SHALL return a Web-discriminated compact state with common identity, diagnostics, turn, and admission facts sourced from native observation. It SHALL NOT require a terminal observer or fabricate terminal signal fields. Missing or stale Web authority SHALL produce explicit unavailable semantics.

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


### Requirement: Detailed agent state endpoint returns full observation

`GET /houmao/agents/{agent_ref}/state/detail` SHALL add probe_snapshot(observed_at_utc,pane_id,pane_pid,captured_text_hash,captured_text_length,captured_text_excerpt,matched_process_names) and parsed_surface(parser_family,availability,business_state,input_mode,ui_context,etc.) to compact terminal state, using its 404/409/503 rules. Web agents SHALL use the managed-agent structured Web variant; supervisor output SHALL NOT synthesize terminal probe/parser fields.

#### Scenario: Detail state includes probe and parsed surface
- **WHEN** the agent has a fully parsed observation
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns 200 with `probe_snapshot` and `parsed_surface` included

#### Scenario: Detail state with diagnostics-only observation
- **WHEN** the agent's TUI process is down
- **THEN** the detail response includes diagnostics but `parsed_surface` is null

#### Scenario: Web Detail Does Not Contain Parsed Console State
- **WHEN** the agent is interactive DSH Web
- **THEN** the detail response identifies its Web surface and native execution state
- **AND THEN** the supervisor's log excerpt is not represented as a parsed agent interface


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
