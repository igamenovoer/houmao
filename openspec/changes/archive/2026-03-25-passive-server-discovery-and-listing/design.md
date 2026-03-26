## Context

The passive server scaffold is implemented: lifecycle management, health endpoint, current-instance endpoint, graceful shutdown, CLI entrypoint, and configuration model. The server starts, serves lifecycle endpoints, and stops — but has no agent awareness.

The shared `LiveAgentRegistryRecordV2` registry is the existing ground truth for live agent state. It stores per-agent `record.json` files under `~/.houmao/registry/live_agents/<agent_id>/` with lease-based freshness. The `registry_storage` module provides functions for loading records by `agent_id`, scanning by `agent_name`, and checking freshness. The `registry_models` module defines the record schema including `agent_name`, `agent_id`, `generation_id`, `terminal` (tmux session name), `runtime`, `gateway`, and `mailbox` fields.

The passive server's first functional capability is to consume these registry records and present discovered agents through HTTP endpoints.

## Goals / Non-Goals

**Goals:**
- Build a `RegistryDiscoveryService` that scans the shared registry periodically, verifies tmux liveness, and maintains an in-memory agent index.
- Expose `GET /houmao/agents` and `GET /houmao/agents/{agent_ref}` endpoints backed by the discovery index.
- Integrate discovery lifecycle into the passive server's startup/shutdown.
- Define response models that project registry records into a passive-server-native format (no CAO terminal IDs, no registration-era fields).

**Non-Goals:**
- TUI observation (state parsing, stability tracking) — separate future step.
- Gateway proxy endpoints — separate future step.
- Headless agent launch/turn management — separate future step.
- Modifying existing registry publication or cleanup behavior.
- Compatibility with the existing `houmao-server`'s `HoumaoManagedAgentIdentity` response shape. The passive server defines its own response models.

## Decisions

### 1. Discovery runs on a shared polling loop, not per-agent threads

A single background thread iterates over all registry directories each cycle. Simpler than per-agent threads and sufficient for the expected agent count (tens, not thousands).

The poll interval is configurable via `PassiveServerConfig.discovery_poll_interval_seconds` (default: 5.0).

**Alternative considered:** `asyncio.Task` polling loop. Rejected because tmux liveness checks call `libtmux` synchronously, and the existing registry I/O is also synchronous. A background `threading.Thread` avoids blocking the async event loop.

### 2. Tmux liveness verification via `libtmux.Server.sessions`

On each scan cycle, the discovery service checks whether the tmux session name from the registry record's `terminal.session_name` field exists as a live tmux session. This is done by querying the tmux server once per cycle (single call to list sessions) and checking membership, rather than probing each session individually.

If the tmux session no longer exists, the agent is evicted from the in-memory index even if the registry record's lease is still fresh. The passive server does not modify or remove the registry record — it only stops presenting the agent in its index.

**Alternative considered:** Skip tmux liveness and rely solely on lease expiry. Rejected because tmux sessions can die immediately (user kills them, machine restarts) while the lease has a 24-hour TTL. The passive server would present stale agents for hours.

### 3. Agent resolution accepts `agent_id` or `agent_name`

The `{agent_ref}` path parameter attempts direct `agent_id` lookup first, then falls back to canonical `agent_name` lookup. If `agent_name` matches multiple records, the endpoint returns a 409 Conflict (ambiguous).

This mirrors the existing `resolve_live_agent_record()` function's semantics but operates against the in-memory index rather than the filesystem.

### 4. Response models are passive-server-native

The passive server defines its own `DiscoveredAgentSummary` and `DiscoveredAgentListResponse` models. These project registry record fields directly:

- `agent_id`, `agent_name`, `generation_id`
- `tool` (from `identity.tool`)
- `backend` (from `identity.backend`)
- `tmux_session_name` (from `terminal.session_name`)
- `manifest_path` (from `runtime.manifest_path`)
- `session_root` (from `runtime.session_root`)
- `has_gateway` (boolean: gateway field is not None and has live bindings)
- `has_mailbox` (boolean: mailbox field is not None)
- `published_at`, `lease_expires_at`

No `tracked_agent_id`, `terminal_id`, `transport`, or CAO-era fields.

### 5. DiscoveredAgentIndex is a simple dict under a threading.Lock

The index is `dict[str, DiscoveredAgent]` keyed by `agent_id`. Name-based lookups iterate the dict (acceptable for expected agent counts). A `threading.Lock` synchronizes reads (from HTTP handlers) and writes (from the polling thread).

**Alternative considered:** `asyncio.Lock` + async-native index. Rejected because the polling thread is synchronous. A regular `threading.Lock` is simpler and the critical section is small (dict swap or lookup).

### 6. Full index rebuild on each poll cycle

Each poll cycle scans the registry directory, loads all fresh records, checks tmux liveness, and rebuilds the index from scratch. The new index replaces the old one atomically (dict swap under the lock).

This is the simplest correct approach. There is no incremental diffing, no file watchers, and no stale-entry tracking. At the expected scale (< 50 agents), a full rebuild every 5 seconds is negligible.

## Risks / Trade-offs

- **Tmux server unavailability:** If the tmux server is not running, the liveness check will find zero live sessions, and the index will be empty. This is correct behavior (no tmux = no agents visible). The discovery service should log a warning when the tmux server is unreachable rather than crashing.
- **Registry I/O latency on large directories:** If the `live_agents/` directory contains many stale directories, each scan reads and validates every `record.json`. Mitigation: rely on the existing `cleanup_stale_live_agent_records()` function (exposed via `houmao-mgr`) to keep the directory manageable. The passive server does not perform cleanup itself.
- **Index coherence window:** Between poll cycles, the index may be stale (an agent may have been stopped or launched). The 5-second default interval bounds the staleness window. This is acceptable for a coordination server.
- **Thread safety:** HTTP handlers read from the index on the async event loop; the polling thread writes. The `threading.Lock` ensures safety. The lock is held only for the duration of a dict swap or a dict lookup, not during the scan itself.
