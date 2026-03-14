## 1. Shared Registry Foundations

- [x] 1.1 Add `registry_models.py` and `registry_storage.py` under `src/houmao/agents/realm_controller/` for `~/.houmao/registry/live_agents/` by default, with `AGENTSYS_GLOBAL_REGISTRY_DIR` override support, home-anchor derivation via `platformdirs`, full SHA-256 hex `agent_key` directories, `schema_version=1` `record.json` payloads, a 24-hour default lease TTL, and a persisted stable-per-live-session `generation_id`
- [x] 1.2 Implement shared-registry storage helpers for atomic publish, load, freshness validation, duplicate-name conflict detection, and stale-record handling
- [x] 1.3 Implement canonical agent-name normalization for registry-facing input so `gpu` and `AGENTSYS-gpu` map to the same live-agent record
- [x] 1.4 Implement duplicate-name/generation ownership checks so one fresh logical agent name cannot publish as two live records at once
- [x] 1.5 Add cleanup tooling and a minimal operator-facing cleanup entrypoint for stale `live_agents/` directories left behind by crashes or expired leases

## 2. Runtime Lifecycle Integration

- [x] 2.1 Publish or refresh shared-registry records during runtime-owned tmux-backed session start, resume, and manifest-persisting control flows for the same live session
- [x] 2.2 Refresh shared-registry records when gateway capability is materialized and when live gateway attach or detach changes session reachability
- [x] 2.3 Refresh shared-registry records when mailbox bindings change and clear or expire records during authoritative `stop-session` teardown

## 3. Discovery Validation And Documentation

- [x] 3.1 Add shared-registry resolution helpers for validated known-name lookup by globally unique agent name
- [x] 3.2 Add unit and integration tests covering default-root publication, full SHA-256 `agent_key` derivation, optional-prefix canonicalization, `AGENTSYS_GLOBAL_REGISTRY_DIR` override behavior, 24-hour lease defaults, `generation_id` reuse across resume, duplicate-name rejection, conflict stand-down behavior, cleanup-entrypoint behavior, and runtime lifecycle refresh behavior
- [x] 3.3 Document the shared-registry contract, `~/.houmao/registry/live_agents/` layout, 24-hour soft-lease behavior without a v1 heartbeat, cleanup tooling, deferred broader registry CLI scope, and the boundary between registry metadata and runtime-owned session state
