## 1. Configuration

- [x] 1.1 Add `observation_poll_interval_seconds` field to `PassiveServerConfig` (default 2.0, min 0.5)
- [x] 1.2 Add config unit tests for the new field (default, custom, invalid)

## 2. Response Models

- [x] 2.1 Add `AgentTuiStateResponse` model to `passive_server/models.py` with agent_id, agent_name, diagnostics, surface, turn, last_turn, stability fields (reuse sub-models from `server/models.py`)
- [x] 2.2 Add `AgentTuiDetailResponse` model extending the compact response with probe_snapshot and parsed_surface
- [x] 2.3 Add `AgentTuiHistoryResponse` model with agent_id, agent_name, and list of `HoumaoRecentTransition` entries

## 3. Agent Observer

- [x] 3.1 Create `src/houmao/passive_server/observation.py` with `AgentTuiObserver` class that holds per-agent state: tracker session, transport resolver target, parser baseline, last probe snapshot, diagnostics
- [x] 3.2 Implement `AgentTuiObserver.poll_cycle()` method that executes the full pipeline: resolve tmux target → inspect process → capture pane → parse → feed tracker session → update diagnostics
- [x] 3.3 Implement `AgentTuiObserver.current_state()` that builds `AgentTuiStateResponse` from the observer's tracked state
- [x] 3.4 Implement `AgentTuiObserver.current_detail()` that builds `AgentTuiDetailResponse` from the observer's tracked state
- [x] 3.5 Implement `AgentTuiObserver.history(limit)` that builds `AgentTuiHistoryResponse` from recent transitions

## 4. Observation Service

- [x] 4.1 Add `TuiObservationService` class to `observation.py` with start/stop lifecycle and a background polling thread
- [x] 4.2 Implement observer reconciliation: on each cycle, compare active observers against the discovery index, create new observers, remove stale ones
- [x] 4.3 Implement the per-cycle poll loop that iterates over all active observers, calling `poll_cycle()` with exception isolation per observer
- [x] 4.4 Add `get_observer(agent_id)` accessor that returns the `AgentTuiObserver | None` for a given agent

## 5. Service Integration

- [x] 5.1 Add `m_observation` field to `PassiveServerService.__init__()` creating a `TuiObservationService` and wire start/stop into startup/shutdown lifecycle
- [x] 5.2 Add `agent_state(agent_ref)` method to `PassiveServerService` that resolves the agent, looks up the observer, and returns the compact state or error tuple
- [x] 5.3 Add `agent_state_detail(agent_ref)` method that returns the detailed state or error tuple
- [x] 5.4 Add `agent_history(agent_ref, limit)` method that returns the history or error tuple

## 6. HTTP Routes

- [x] 6.1 Add `GET /houmao/agents/{agent_ref}/state` route returning `AgentTuiStateResponse` (200), 404, 409, or 503
- [x] 6.2 Add `GET /houmao/agents/{agent_ref}/state/detail` route returning `AgentTuiDetailResponse` (200), 404, 409, or 503
- [x] 6.3 Add `GET /houmao/agents/{agent_ref}/history` route with optional `limit` query parameter returning `AgentTuiHistoryResponse` (200), 404, 409, or 503

## 7. Unit Tests

- [x] 7.1 Add unit tests for `AgentTuiObserver`: successful poll cycle, tmux missing, process down, parse error, current_state/current_detail/history accessors
- [x] 7.2 Add unit tests for `TuiObservationService`: observer creation on discovery, observer removal on disappearance, poll loop exception isolation
- [x] 7.3 Add service-level tests for `agent_state()`, `agent_state_detail()`, `agent_history()`: success, not found, no observer
- [x] 7.4 Add HTTP contract tests for all three endpoints: 200 success with mocked observer, 404 not found, 409 ambiguous, 503 no observer
- [x] 7.5 Update existing service and app tests to patch observation service start/stop (prevent real polling threads in tests)
