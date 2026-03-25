# Distributed Agent Architecture — Migration Path

## Purpose

This note recommends a concrete, phased migration path from the current CAO-backed and registration-backed architecture toward the distributed, registry-first agent architecture described in `distributed-agent-architecture.md`.

The migration is structured so that each phase delivers independently useful value, later phases can be deferred or reordered based on experience, and the system remains functional at every phase boundary.

## Guiding Principles

1. **Always shippable.** Every phase ends with a working system. No phase depends on a future phase being completed.
2. **Surface retirement before authority refactor.** Disabling public creation paths is simpler and lower-risk than changing how the server discovers and admits sessions. Do the simpler thing first.
3. **Promote what already works.** The local `houmao-mgr agents launch` flow already follows the target architecture (tmux-backed, registry-published, server-optional). The migration should promote this pattern to the canonical path rather than inventing a new one.
4. **Shrink the CAO surface incrementally.** Rather than a single large removal, progressively narrow what CAO code is reachable from public APIs while keeping internal plumbing alive during transition.
5. **Let tests follow architecture.** Do not rush to delete CAO-touching tests. Instead, re-scope them: tests that validate internal plumbing can remain; tests that exercise retired public contracts should be migrated to the replacement flow.

## Current State Summary

### What already aligns with the target architecture

- `houmao-mgr agents launch` creates tmux-backed sessions locally without requiring a server.
- Sessions publish `LiveAgentRegistryRecordV2` to a filesystem-based shared registry.
- Sessions persist durable manifests (`SessionManifestPayloadV3`) for resume.
- Gateways attach as optional out-of-process companions with their own FastAPI surface.
- Agent identity resolution already checks the shared registry as a discovery path.
- `houmao-server` already reads the shared registry for enrichment when tracking TUI sessions.

### What must change

- `/cao/*` routes on `houmao-server` are still the primary public TUI session creation path.
- `/houmao/launches/register` is the bridge that admits externally-created TUI sessions into server tracking.
- `houmao_server_rest` backend exists as a public creation identity.
- Server TUI tracking admission is registration-backed: `KnownSessionRegistry` seeds trackers from `registrations/{session_name}/registration.json`, using shared-registry records only as enrichment.
- Multiple demo packs, docs, and tests assume CAO-backed creation as canonical.
- The child CAO process (`ChildCaoManager`) is still supervised by `houmao-server`.

## Recommended Migration Phases

### Phase 0 — Establish Foundations

**Goal:** Prepare infrastructure that later phases depend on, without changing any public behavior.

**Work items:**

1. **Registry lease renewal.** The current 24-hour lease is write-once. Add a lightweight lease-renewal mechanism so long-running agents remain discoverable without restart. This can be a periodic `touch` of the lease timestamp by the `RuntimeSessionController` or the gateway process. Without this, registry-first discovery is unreliable for sessions that run longer than 24 hours.

2. **Registry liveness enrichment.** Add a `verify_liveness(record) -> bool` utility that checks whether the tmux session named in a registry record is actually alive. This is needed by the server's future registry-driven admission logic. The TUI tracking supervisor already does tmux liveness checks; extract and generalize this.

3. **Canonical agent identity on all local launches.** Ensure that every `houmao-mgr agents launch` invocation (interactive and headless) generates and publishes a canonical `agent_name` and `agent_id` in both the manifest and the registry record. Some current paths may leave these fields as `None`. The server's future registry-driven discovery needs these to be reliable.

4. **Feature flag for CAO route retirement.** Add a server config flag (e.g., `cao_routes_enabled: bool`, default `true`) that controls whether `/cao/*` routes are mounted. This allows testing route retirement in staging without code removal.

**Exit criteria:** Registry records are reliably fresh, liveness-verifiable, and identity-complete for all local launches. A config flag exists to disable CAO routes.

---

### Phase 1 — Retire CAO Public Creation Paths

**Goal:** Stop presenting `/cao/*` and `/houmao/launches/register` as supported public interfaces for session creation and control. Return explicit, intentional errors on retired routes.

**Work items:**

1. **Disable `/cao/*` routes.** When `cao_routes_enabled` is `false` (flip the default), all `/cao/*` endpoints return `410 Gone` with a message directing users to the local launch flow. The route handlers and underlying `CompatibilityControlCore` remain in code but are unreachable.

2. **Disable `/houmao/launches/register`.** Return `410 Gone` with a message explaining that launch registration is no longer needed because the server discovers agents from the shared registry. The `KnownSessionRegistry` registration-write path becomes dead code but is not yet removed.

3. **Disable `houmao_server_rest` as a public creation backend.** `backend_for_tool()` in `launch_plan.py` should never select `houmao_server_rest` for new sessions. If explicitly requested (e.g., via CLI `--backend houmao_server_rest`), return an error explaining the retirement. Keep `cao_rest` available for users who run their own standalone CAO server (rare but possible).

4. **Update CLI help text and error messages.** `houmao-mgr` commands that previously suggested server-backed creation should now describe local launch as the primary path. Remove `register-launch` from the CLI surface or alias it to an error message.

5. **Mark demo packs.** Tag the following demo packs as `status: retired` in their metadata or a top-level comment:
   - `cao_interactive_demo`
   - `houmao_server_interactive_full_pipeline_demo`
   - `houmao_server_dual_shadow_watch`
   - Any script-based demos under `scripts/demo/cao-*` and `scripts/demo/houmao-server-*`

   They do not need to be deleted yet. They can serve as internal reference during migration.

6. **Adapt tests.** Tests that exercise `/cao/*` route contracts (`test_app_contracts.py`, `test_service.py`, `test_compatibility_control_core.py`) should be updated to assert the 410 response when the flag is off. Add a test variant that confirms routes still work when `cao_routes_enabled` is explicitly `true`, to support any transitional internal usage.

**Exit criteria:** No public user workflow reaches `/cao/*` or `/houmao/launches/register`. `houmao_server_rest` cannot be selected as a backend. All affected tests pass. Local launch remains fully functional.

**Risk:** Users or scripts that depend on CAO creation paths will break. This is intentional — the architecture note calls for explicit, intentional errors. Communicate the change before shipping.

---

### Phase 2 — Registry-Driven Server Discovery

**Goal:** Change `houmao-server`'s TUI tracking admission from registration-backed to registry-driven. This is the core authority-model change.

**Work items:**

1. **Add a `RegistryDiscoveryService` to the server.** This new service periodically scans the shared registry for live agent records that meet admission criteria. It replaces the registration-backed `KnownSessionRegistry` as the primary source of truth for "which agents does the server know about."

   Admission criteria (recommended starting set):
   - Record has a fresh lease (`is_live_agent_record_fresh()`).
   - Record's tmux session is alive (`verify_liveness()`).
   - Record's `agent_id` and `agent_name` are non-empty.
   - Optionally: record's `registry_launch_authority` is `"runtime"` (not `"gateway"`), to avoid double-tracking.

   The service should produce a `DiscoveredAgentSet` that the rest of the server consumes.

2. **Wire `TuiTrackingSupervisor` to `RegistryDiscoveryService`.** The supervisor currently reconciles trackers against `KnownSessionRegistry` (registration files). Rewire it to reconcile against `DiscoveredAgentSet` instead. Tracker creation should be driven by registry discovery, not by registration file existence.

3. **Preserve `/houmao/agents` API semantics.** The managed-agent listing and control routes (`GET /houmao/agents`, `GET /houmao/agents/{agent_ref}`, etc.) should continue to work, but their backing data now comes from registry discovery rather than registration. Agent addressing by name should work because the registry record carries `agent_name`.

4. **Handle server-owned stop for discovered sessions.** Define an explicit contract: when the server stops a registry-discovered agent, it sends SIGTERM to the tmux session and removes the registry record. Document this behavior. The server did not create the session, but it is allowed to stop it because it holds coordination authority when running.

5. **Preserve headless agent management.** Server-managed headless agents (`ManagedHeadlessStore`) do not go through the CAO/registration path. They should continue to work unchanged. They are already closer to the target architecture (server creates and owns them directly).

6. **Deprecate `KnownSessionRegistry`.** Once `RegistryDiscoveryService` is stable, `KnownSessionRegistry` becomes unused. Mark it deprecated. Do not remove it yet — Phase 4 handles code cleanup.

**Exit criteria:** `houmao-server`, when running, discovers and tracks agents from the shared registry without requiring any registration call. `/houmao/agents` returns registry-discovered agents. Server stop works on discovered agents. Headless agents are unaffected.

**This is the largest and riskiest phase.** It changes the trust and ownership boundary. Allocate time for integration testing, especially:
- Agent launched locally, discovered by server, controlled via server API.
- Agent launched locally with gateway, discovered by server, gateway proxied via server.
- Multiple agents with the same name (should the server track all or reject duplicates?).
- Agent that disappears (tmux session killed externally) — server should evict the tracker.
- Server restart — should re-discover agents from registry on startup.

---

### Phase 3 — Strengthen the Local-First Story

**Goal:** Make the local, server-optional experience complete and polished. Users should be able to do everything they need without `houmao-server` for single-host scenarios.

**Work items:**

1. **Local agent listing.** `houmao-mgr agents list` should show all locally-discoverable agents by scanning the shared registry and checking tmux liveness, without requiring a server. This may already partially work; ensure it is complete and documented.

2. **Local agent stop.** `houmao-mgr agents stop <agent-ref>` should resolve the agent from the registry, terminate the tmux session, remove the registry record, and optionally clean up the gateway. This should work without a server.

3. **Local gateway attach/detach.** Ensure `houmao-mgr agents gateway attach/detach <agent-ref>` works purely from registry resolution. The gateway system already supports this; verify and document.

4. **Local agent resume.** `houmao-mgr agents resume <agent-ref>` should resolve from registry, load the manifest, and reconstruct the `RuntimeSessionController`. This flow already exists via `resolve_agent_identity()` → `resume_runtime_session()`; ensure it is well-documented and tested.

5. **Document the local-only workflow.** Write a user-facing guide that describes the full lifecycle:
   - Launch: `houmao-mgr agents launch --agents=<selector>`
   - List: `houmao-mgr agents list`
   - Resume: `houmao-mgr agents resume <agent-ref>`
   - Gateway: `houmao-mgr agents gateway attach <agent-ref>`
   - Prompt: `houmao-mgr agents prompt <agent-ref> "do something"`
   - Stop: `houmao-mgr agents stop <agent-ref>`

   This guide should explicitly state that `houmao-server` is not required.

6. **Clean up `BackendKind` for new launches.** For new agent launches, the only backends a user should normally encounter are:
   - `local_interactive` (tmux-backed TUI)
   - `claude_headless`, `codex_headless`, `gemini_headless` (tmux-backed headless)
   - `codex_app_server` (remote Codex server — a special case)

   `cao_rest` and `houmao_server_rest` remain in the type system for resume of existing sessions but should not appear in default selection logic or documentation.

**Exit criteria:** A user can launch, list, resume, control, and stop agents entirely through `houmao-mgr` without `houmao-server`. The workflow is documented. The default backend selection never offers `cao_rest` or `houmao_server_rest` for new sessions.

---

### Phase 4 — Code Cleanup and Legacy Removal

**Goal:** Remove dead code paths left behind by Phases 1–3. Reduce maintenance burden.

**Work items:**

1. **Remove `/cao/*` route handlers from `app.py`.** The feature flag made them unreachable; now remove the code. Remove `CompatibilityControlCore`, `LocalCompatibilityTransportBridge`, and related imports.

2. **Remove `ChildCaoManager`.** If the server no longer needs a child CAO process (because no routes delegate to it), remove the supervised child process and its configuration.

3. **Remove `KnownSessionRegistry` and registration file I/O.** The registration-backed admission path is fully replaced by registry discovery.

4. **Remove `houmao_server_rest` backend.** Remove the class, its imports, its test fixtures, and its `BackendKind` variant. Manifests with `backend: houmao_server_rest` will fail to resume (acceptable; these sessions are from the retired architecture).

5. **Decide on `cao_rest` backend.** Two options:
   - **Keep it** as a supported backend for users who run standalone CAO-compatible servers externally. This is a niche use case but may have value.
   - **Remove it** if no real users depend on it. This simplifies the codebase significantly (the `cao_rest.py` module is 5000+ lines).

   Recommendation: keep `cao_rest` for now if it does not impose maintenance cost, but mark it as an advanced/unsupported backend. Revisit removal later.

6. **Remove or archive demo packs.** Move retired demo packs to an `archive/` directory or delete them. Keep at most one historical demo as a reference.

7. **Clean up tests.** Remove tests that only exercise retired flows. Consolidate remaining test coverage around:
   - Local interactive launch + registry publication + discovery + resume.
   - Headless launch + registry publication + server discovery + server API control.
   - Gateway attach + registry update + server proxy.

8. **Remove stale docs.** Archive or remove:
   - `docs/reference/cao_interactive_demo.md`
   - `docs/reference/cao_server_launcher.md`
   - `docs/reference/houmao_server_pair.md`
   - `docs/migration/houmao/server-pair/`
   - Any other docs that describe retired workflows as current.

**Exit criteria:** No dead code paths remain. The `BackendKind` type is cleaner. Test suite is smaller and focused on the target architecture. Documentation describes only the supported architecture.

---

### Phase 5 — Server Coordination Layer

**Goal:** Build out the server's value as a coordination, communication, and resource-management authority. This phase is where the server becomes useful for multi-agent scenarios rather than just mirroring what `houmao-mgr` can do locally.

**Work items (exploratory — scope depends on product direction):**

1. **Agent-name-based addressing.** The server should provide stable name resolution that works across agent restarts (a restarted agent gets a new `generation_id` but keeps the same `agent_name`). The server's `RegistryDiscoveryService` already has this data; expose it as a clean naming API.

2. **Inter-agent communication.** Design and implement a server-mediated communication protocol. Starting point: request-response RPC-like exchange where agent A asks the server to deliver a prompt to agent B and return the result. This likely uses the gateway's request queue as the delivery mechanism.

3. **Shared resource coordination.** If agents need shared state (e.g., a shared scratchpad, a task queue, a lock), the server can provide filesystem-backed or memory-backed coordination primitives.

4. **Centralized observation.** The server already tracks terminal state for TUI sessions. Extend this to provide a unified dashboard or API that shows all discovered agents, their current states, recent activity, and gateway status.

5. **Multi-agent workflow primitives.** Barriers, rendezvous points, fan-out/fan-in, or delegation chains. These are higher-level than simple messaging and may depend on product requirements.

**Exit criteria:** This phase has no fixed exit criteria. It is an ongoing extension of the server's value once the foundational architecture is in place.

---

## Phase Dependencies

```text
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 4
                │                       ↑
                └──→ Phase 3 ──────────┘
                                        │
                                        └──→ Phase 5
```

- Phase 0 is prerequisite to everything.
- Phase 1 (surface retirement) can proceed independently of Phase 2 (authority refactor) and Phase 3 (local-first polish). It is recommended to do Phase 1 first because it is simpler and establishes the retirement intent publicly.
- Phase 2 (registry-driven discovery) and Phase 3 (local-first story) can proceed in parallel. They touch different parts of the system (server internals vs. CLI/local workflows).
- Phase 4 (cleanup) requires Phases 1, 2, and 3 to be substantially complete.
- Phase 5 (coordination) can begin as soon as Phase 2 is stable. It does not depend on Phase 4.

## Estimated Effort Profile

| Phase | Scope | Risk | Parallelizable |
|-------|-------|------|----------------|
| 0 — Foundations | Small | Low | — |
| 1 — Surface retirement | Medium | Low–Medium | After 0 |
| 2 — Authority refactor | Large | High | After 0, parallel with 3 |
| 3 — Local-first story | Medium | Low | After 0, parallel with 2 |
| 4 — Cleanup | Medium | Low | After 1+2+3 |
| 5 — Coordination | Open-ended | Medium | After 2 |

## Key Risks And Mitigations

### 1. Registry reliability under load

**Risk:** Filesystem-based registry may have race conditions or performance issues with many agents.

**Mitigation:** The current atomic-write and generation-conflict detection is adequate for single-host scenarios. If multi-host distributed agents become real, consider upgrading to a more robust registry backend (SQLite, etcd, or a lightweight coordination service). This is a Phase 5+ concern.

### 2. Server restart loses tracking state

**Risk:** Because TUI tracking state is in-memory, a server restart loses all tracker state. With registration-backed admission, the server could re-read registration files. With registry-driven admission, the server must re-discover and re-create trackers from scratch.

**Mitigation:** This is already the expected behavior in the target architecture. The server's `RegistryDiscoveryService` should populate trackers on startup by scanning the registry. Document this as a feature: the server is stateless with respect to agent tracking and recovers from registry.

### 3. Breaking existing automation

**Risk:** Internal scripts, CI pipelines, or developer workflows that use `/cao/*` routes or `register-launch` will break.

**Mitigation:** Audit and migrate before flipping the Phase 1 feature flag. Provide a clear migration guide. The feature flag allows gradual rollout.

### 4. CAO-backend removal breaks manifest resume

**Risk:** Removing `cao_rest` or `houmao_server_rest` backends means old manifests cannot be resumed.

**Mitigation:** Keep the backends loadable for resume even if they cannot be selected for new sessions. Only remove them (Phase 4) after confirming no live sessions use them. Alternatively, provide a manifest migration tool that rewrites `backend` to `local_interactive` where applicable.

### 5. Scope creep in Phase 5

**Risk:** The coordination layer is open-ended and could absorb unbounded effort.

**Mitigation:** Treat Phase 5 as a collection of independent, scope-bounded features. Each feature should be a separate change with its own design note. Do not attempt a monolithic "coordination framework."

## What This Migration Does Not Cover

- **Multi-host distributed agents.** The current shared registry is filesystem-based and assumes a single host. Multi-host distribution requires a network-accessible registry. That is a future extension beyond this migration path.
- **Authentication and authorization.** The current system has no auth model. If `houmao-server` becomes a coordination authority over distributed agents, it will eventually need one. That design is out of scope here.
- **Wire protocol for inter-agent communication.** Phase 5 mentions communication but does not prescribe a protocol. That needs its own design note.
- **Client SDK or API versioning.** The current API is unstable and internal. If it becomes a public contract, versioning and stability guarantees need a separate decision.

## Summary

The recommended migration path is:

1. **Phase 0:** Prepare registry reliability, liveness checks, and feature flags.
2. **Phase 1:** Retire CAO and registration routes behind feature flags, then disable by default.
3. **Phase 2:** Replace registration-backed server admission with registry-driven discovery.
4. **Phase 3:** Polish the local-first, server-optional agent lifecycle.
5. **Phase 4:** Remove dead code, tests, docs, and demo packs.
6. **Phase 5:** Build server coordination features (naming, messaging, shared resources).

Each phase is independently valuable. The system remains functional at every phase boundary. The riskiest phase is Phase 2 (authority refactor), which should be tested carefully. The simplest win is Phase 1 (surface retirement), which should be done first.
