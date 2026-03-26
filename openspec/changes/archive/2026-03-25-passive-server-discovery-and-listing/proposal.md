## Why

The passive server scaffold (lifecycle, health, config, CLI) is complete but the server cannot yet discover or list agents. This is the first functional capability the passive server needs: registry-driven agent discovery with tmux liveness verification and HTTP endpoints for listing and resolving agents. Without this, the passive server is a health-check-only shell with no agent awareness.

## What Changes

- Add a `RegistryDiscoveryService` that periodically scans the shared `LiveAgentRegistryRecordV2` registry, verifies tmux session liveness, and maintains an in-memory `DiscoveredAgentIndex` keyed by `agent_id` and `agent_name`.
- Add agent listing endpoints to the passive server:
  - `GET /houmao/agents` — list all discovered agents from the index.
  - `GET /houmao/agents/{agent_ref}` — resolve a single agent by `agent_id` or `agent_name`.
- Integrate the discovery service into the passive server lifecycle (start on server startup, stop on shutdown).
- Evict agents from the index when their registry records expire or their tmux sessions disappear.
- Support re-discovery on startup (the server is stateless with respect to agent tracking — all state is rebuilt from the registry).

## Capabilities

### New Capabilities
- `passive-server-agent-discovery`: Covers registry-driven agent discovery (periodic scan, tmux liveness verification, in-memory index) and HTTP endpoints for listing and resolving discovered agents.

### Modified Capabilities
<!-- No spec-level requirement changes to existing capabilities. The passive server reuses the existing
     agent-discovery-registry contract as a consumer — it reads records but does not change publication
     or cleanup semantics. The passive-server-lifecycle spec does not need requirement changes; discovery
     service startup/shutdown is an implementation-level integration, not a lifecycle contract change. -->

## Impact

- **New code in `src/houmao/passive_server/`**: `discovery.py` (RegistryDiscoveryService, DiscoveredAgentIndex), new route handlers in `app.py`, new response models in `models.py`.
- **Dependencies on existing code**: `houmao.agents.realm_controller.registry_storage` (scan/load functions), `houmao.agents.realm_controller.registry_models` (LiveAgentRegistryRecordV2), `libtmux` (tmux liveness checks).
- **New tests in `tests/unit/passive_server/`**: discovery service unit tests, agent listing endpoint contract tests.
- **No changes to existing server, registry, or CLI code.** The passive server is a new consumer of the shared registry — it does not modify publication or cleanup behavior.
