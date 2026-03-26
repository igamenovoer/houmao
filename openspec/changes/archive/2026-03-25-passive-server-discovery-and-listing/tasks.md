## 1. Configuration

- [x] 1.1 Add `discovery_poll_interval_seconds` field to `PassiveServerConfig` (float, default 5.0, validated > 0)
- [x] 1.2 Add unit tests for the new config field (default, custom, non-positive rejection)

## 2. Response Models

- [x] 2.1 Add `DiscoveredAgentSummary` model to `passive_server/models.py` with fields: `agent_id`, `agent_name`, `generation_id`, `tool`, `backend`, `tmux_session_name`, `manifest_path`, `session_root`, `has_gateway`, `has_mailbox`, `published_at`, `lease_expires_at`
- [x] 2.2 Add `DiscoveredAgentListResponse` model (wrapping `agents: list[DiscoveredAgentSummary]`)
- [x] 2.3 Add `DiscoveredAgentConflictResponse` model for 409 ambiguity errors (with `agent_ids` list and diagnostic message)

## 3. Discovery Service

- [x] 3.1 Create `passive_server/discovery.py` with `DiscoveredAgentIndex` (dict keyed by `agent_id` under `threading.Lock`, with `get_by_id`, `get_by_name`, `list_all`, and `replace` methods)
- [x] 3.2 Implement `RegistryDiscoveryService` with `start()` / `stop()` lifecycle and a background polling thread that: scans `live_agents/*/record.json`, validates and filters by freshness, checks tmux liveness, and rebuilds the index
- [x] 3.3 Handle tmux server unavailability gracefully (log warning, treat as zero live sessions, continue polling)
- [x] 3.4 Add unit tests for `DiscoveredAgentIndex` (add, lookup by id, lookup by name, ambiguous name, empty index)
- [x] 3.5 Add unit tests for `RegistryDiscoveryService` scan logic (fresh+live → included, expired → excluded, dead tmux → excluded, malformed record → excluded, tmux unavailable → empty)

## 4. Service Integration

- [x] 4.1 Add `RegistryDiscoveryService` as a member of `PassiveServerService`, created in `__init__` from config
- [x] 4.2 Call discovery `start()` in `PassiveServerService.startup()` and `stop()` in `shutdown()`
- [x] 4.3 Add `list_agents()` and `resolve_agent(agent_ref)` methods to `PassiveServerService` that delegate to the discovery index
- [x] 4.4 Add unit tests for service-level agent listing and resolution (including 404 and 409 cases)

## 5. HTTP Routes

- [x] 5.1 Add `GET /houmao/agents` route in `app.py` returning `DiscoveredAgentListResponse`
- [x] 5.2 Add `GET /houmao/agents/{agent_ref}` route in `app.py` returning `DiscoveredAgentSummary` (200), 404, or 409
- [x] 5.3 Add HTTP contract tests for both endpoints (200 with agents, 200 empty, 404 not found, 409 ambiguous)
