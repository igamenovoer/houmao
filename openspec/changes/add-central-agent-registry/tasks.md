## 1. Shared Registry Foundations

- [ ] 1.1 Add strict shared-registry models and path helpers for `~/.houmao/registry/live_agents/` by default, with `AGENTSYS_GLOBAL_REGISTRY_DIR` override support and home-anchor derivation via `platformdirs`, plus hashed live-agent directories and versioned `record.json` payloads
- [ ] 1.2 Implement shared-registry storage helpers for atomic publish, load, freshness validation, and stale-record handling
- [ ] 1.3 Implement canonical agent-name normalization for registry-facing input so `gpu` and `AGENTSYS-gpu` map to the same live-agent record
- [ ] 1.4 Implement duplicate-name/generation ownership checks so one fresh logical agent name cannot publish as two live records at once
- [ ] 1.5 Add cleanup tooling for stale `live_agents/` directories left behind by crashes or expired leases

## 2. Runtime Lifecycle Integration

- [ ] 2.1 Publish or refresh shared-registry records during runtime-owned tmux-backed session start and resume
- [ ] 2.2 Refresh shared-registry records when gateway capability is materialized and when live gateway attach or detach changes session reachability
- [ ] 2.3 Refresh shared-registry records when mailbox bindings change and clear or expire records during authoritative `stop-session` teardown

## 3. Discovery Validation And Documentation

- [ ] 3.1 Add shared-registry resolution helpers for validated known-name lookup by globally unique agent name
- [ ] 3.2 Add unit and integration tests covering default-root publication, optional-prefix canonicalization, `AGENTSYS_GLOBAL_REGISTRY_DIR` override behavior, freshness expiry, duplicate-name rejection, cleanup behavior, and runtime lifecycle refresh behavior
- [ ] 3.3 Document the shared-registry contract, `~/.houmao/registry/live_agents/` layout, cleanup tooling, and the boundary between registry metadata and runtime-owned session state
