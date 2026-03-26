## Why

The greenfield `houmao-passive-server` (Steps 1–4) already provides registry-driven discovery, TUI observation, gateway proxy, and server lifecycle. However, it cannot yet accept prompt requests, interrupt or stop agents, manage gateway attach/detach lifecycle, or launch and manage headless agents. These are the remaining capabilities needed before the passive server can replace the old `houmao-server` for all managed-agent workflows. This is Step 5 of the migration path described in `context/design/future/distributed-agent-migration-path-greenfield.md`.

## What Changes

- Add `POST /houmao/agents/{agent_ref}/requests` — gateway-mediated prompt delivery. If the agent has a live gateway, forward to it; otherwise return an error directing the caller to attach a gateway first or use `houmao-mgr` locally.
- Add `POST /houmao/agents/{agent_ref}/interrupt` — gateway-mediated interrupt for headless agents managed by the passive server.
- Add `POST /houmao/agents/{agent_ref}/stop` — terminate an agent's tmux session and clear its shared-registry record. This is the one case where the passive server takes direct tmux action, as stop is coordination-level authority.
- Add `POST /houmao/agents/{agent_ref}/gateway/attach` and `POST /houmao/agents/{agent_ref}/gateway/detach` — return 501 errors directing the user to `houmao-mgr agents gateway attach/detach`, per the design doc's Option A recommendation that the passive server delegates subprocess-level gateway lifecycle to `houmao-mgr`.
- Add `POST /houmao/agents/headless/launches` — launch a native headless agent via `start_runtime_session()`, publish to the shared registry, persist a `ManagedHeadlessAuthorityRecord`, and track in-memory.
- Add `POST /houmao/agents/{agent_ref}/turns` — submit a turn to a managed headless agent.
- Add `GET /houmao/agents/{agent_ref}/turns/{turn_id}` — return turn status.
- Add `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` — return turn events.
- Add `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/{name}` — return turn artifact text (stdout/stderr).
- Introduce `src/houmao/passive_server/headless.py` containing `HeadlessAgentService` for turn lifecycle, authority persistence, and in-memory handle management. Reuse `ManagedHeadlessStore` from `houmao.server.managed_agents` for disk persistence.
- Add new passive-server–specific request/response models to `src/houmao/passive_server/models.py`.

## Capabilities

### New Capabilities
- `passive-server-request-submission`: Request submission (prompt delivery, interrupt, stop) and gateway attach/detach stubs on the passive server.
- `passive-server-headless-management`: Headless agent launch, turn lifecycle (submit, status, events, artifacts), and authority persistence on the passive server.

### Modified Capabilities

## Impact

- **Code**: New file `src/houmao/passive_server/headless.py`; extended `app.py`, `service.py`, and `models.py` in the passive server package. Reuses `ManagedHeadlessStore` from `houmao.server.managed_agents` and `start_runtime_session()` / `RuntimeSessionController` from `houmao.agents.realm_controller.runtime`.
- **APIs**: 10 new HTTP endpoints on the passive server (port 9891).
- **Dependencies**: New runtime dependency on `houmao.agents.realm_controller.runtime` (already a project dependency) and `houmao.server.managed_agents` (for `ManagedHeadlessStore`).
- **Tmux**: The `stop` endpoint will call `tmux kill-session` directly (via `kill_tmux_session()`) and clear the shared registry record.
- **Registry**: Headless launches publish `LiveAgentRegistryRecordV2` to the shared registry, making them visible to the old `houmao-server` running in parallel (Step 7 validation).
