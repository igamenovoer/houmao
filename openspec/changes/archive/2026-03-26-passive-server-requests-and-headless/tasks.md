## 1. Models and Shared Infrastructure

- [x] 1.1 Add request models to `passive_server/models.py`: `PassivePromptRequest` (prompt: str), `PassiveHeadlessLaunchRequest` (tool, working_directory, agent_def_dir, brain_manifest_path, role_name?, agent_name?, agent_id?, mailbox?), `PassiveHeadlessTurnRequest` (prompt: str)
- [x] 1.2 Add response models to `passive_server/models.py`: `PassiveRequestAcceptedResponse`, `PassiveAgentActionResponse`, `PassiveHeadlessLaunchResponse`, `PassiveHeadlessTurnAcceptedResponse`, `PassiveNotImplementedResponse`
- [x] 1.3 Add `managed_agents_root` derived property to `PassiveServerConfig` returning `server_root / "managed_agents"`

## 2. Gateway Attach/Detach Stubs (Tier 5)

- [x] 2.1 Add `POST /houmao/agents/{agent_ref}/gateway/attach` route in `app.py` returning 501 with detail directing to `houmao-mgr agents gateway attach`
- [x] 2.2 Add `POST /houmao/agents/{agent_ref}/gateway/detach` route in `app.py` returning 501 with detail directing to `houmao-mgr agents gateway detach`
- [x] 2.3 Add unit tests for gateway attach/detach 501 responses in `tests/unit/passive_server/test_app_contracts.py`

## 3. Request Submission (Tier 6 — Prompt and Interrupt)

- [x] 3.1 Add `submit_request()` method to `PassiveServerService` that resolves agent, checks for gateway, and forwards prompt via `GatewayClient.create_request()`; returns 502 if no gateway
- [x] 3.2 Add `interrupt_agent()` method to `PassiveServerService` that forwards interrupt via gateway if available; for server-managed headless agents, delegates to `HeadlessAgentService`; returns 502 if neither path available
- [x] 3.3 Add `POST /houmao/agents/{agent_ref}/requests` and `POST /houmao/agents/{agent_ref}/interrupt` routes in `app.py`
- [x] 3.4 Add unit tests for request submission: gateway-mediated success, no-gateway 502, agent-not-found 404
- [x] 3.5 Add unit tests for interrupt: gateway-mediated success, managed-headless success, no-gateway 502

## 4. Stop Agent (Tier 6)

- [x] 4.1 Add `stop_agent()` method to `PassiveServerService` that resolves agent, kills tmux session via `kill_tmux_session()`, clears shared registry record, and for managed headless agents delegates cleanup to `HeadlessAgentService`
- [x] 4.2 Add `POST /houmao/agents/{agent_ref}/stop` route in `app.py`
- [x] 4.3 Add unit tests for stop: tmux kill + registry cleanup, managed headless cleanup, agent-not-found 404

## 5. Headless Agent Service (Tier 7 — Core)

- [x] 5.1 Create `src/houmao/passive_server/headless.py` with `HeadlessAgentService` class: constructor accepting `PassiveServerConfig`, `ManagedHeadlessStore` instance, in-memory handle map, start/stop lifecycle methods
- [x] 5.2 Implement `launch()` method: validate inputs, call `start_runtime_session()`, publish registry record, persist `ManagedHeadlessAuthorityRecord`, store in-memory handle, return launch response
- [x] 5.3 Implement startup rebuild: scan `ManagedHeadlessStore.list_authority_records()`, verify tmux liveness, resume `RuntimeSessionController` handles for live agents, log and optionally clean up dead ones
- [x] 5.4 Wire `HeadlessAgentService` into `PassiveServerService.__init__()` and startup/shutdown lifecycle

## 6. Headless Turn Lifecycle (Tier 7 — Turns)

- [x] 6.1 Implement `submit_turn()` in `HeadlessAgentService`: validate agent is managed headless, provision turn via controller, persist active turn and turn record, return accepted response
- [x] 6.2 Implement `turn_status()` in `HeadlessAgentService`: reconcile active turn, load turn record, return status response
- [x] 6.3 Implement `turn_events()` in `HeadlessAgentService`: load events from turn artifact, return events response
- [x] 6.4 Implement `turn_artifact_text()` in `HeadlessAgentService`: read stdout/stderr file from turn record paths, return text content
- [x] 6.5 Implement `interrupt_managed()` in `HeadlessAgentService`: signal interrupt via RuntimeSessionController handle

## 7. Headless Routes

- [x] 7.1 Add `POST /houmao/agents/headless/launches` route in `app.py` delegating to `service.launch_headless()`
- [x] 7.2 Add `POST /houmao/agents/{agent_ref}/turns` route in `app.py`
- [x] 7.3 Add `GET /houmao/agents/{agent_ref}/turns/{turn_id}` route in `app.py`
- [x] 7.4 Add `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` route in `app.py`
- [x] 7.5 Add `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/{name}` route in `app.py`

## 8. Headless Tests

- [x] 8.1 Add unit tests for `HeadlessAgentService` launch: valid launch, invalid working_directory, tool mismatch, unsupported backend
- [x] 8.2 Add unit tests for turn lifecycle: submit turn, turn status (active/completed), turn events, turn artifacts (stdout/stderr), unknown turn 404
- [x] 8.3 Add unit tests for startup rebuild: resume live agent, clean up dead agent
- [x] 8.4 Add route-level tests in `test_app_contracts.py` for headless launch, turns, and artifact endpoints

## 9. Integration Validation

- [x] 9.1 Run full passive-server unit suite (`pixi run python -m pytest tests/unit/passive_server -v`) and verify all tests pass
- [x] 9.2 Run `pixi run lint` and `pixi run typecheck` against the passive server package and fix any issues
