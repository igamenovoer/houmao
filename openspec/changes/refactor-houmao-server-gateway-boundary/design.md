## Context

The current system already has the pieces needed for a distributed control model, but those pieces still overlap in ownership.

Today:

- `houmao-server` owns managed-agent naming, alias resolution, server-managed headless launch and stop flows, managed-agent request handling, managed-agent gateway attach or detach routes, and live TUI tracking for server-managed TUI sessions.
- the per-agent gateway already owns a durable per-agent queue, live status, mailbox facade, notifier state, and gateway-local recovery behavior.
- runtime-managed session roots already publish stable gateway attachability and session-root pointers independently from whether a live gateway is attached.
- the shared registry is already pointer-oriented and is explicitly not supposed to become a second runtime state store.

That leaves an architectural mismatch:

- the optional gateway already looks like a per-agent control plane, but the central server still owns too much per-agent live behavior;
- TUI tracking and headless live execution authority are not split the same way;
- server-managed agents and direct runtime-managed sessions do not yet follow one coherent “shared coordination plane vs per-agent control plane” model.

This refactor is intended to make that split explicit without forcing gateway to become mandatory. In the target model:

- `houmao-server` remains the shared coordination plane,
- the optional per-agent gateway becomes the per-agent control plane,
- tmux and runtime backends remain the execution substrate,
- and the existing managed-agent public routes stay as stable as practical in this phase.

## Goals / Non-Goals

**Goals:**

- Define a clear boundary where `houmao-server` owns shared coordination and the per-agent gateway owns session-local control work.
- Move TUI tracking authority for attached agents out of the central server and into the per-agent gateway.
- Move live per-agent headless execution admission and lifecycle authority behind the gateway when a gateway is attached.
- Keep `houmao-server` plus tmux-hosted agents working without a gateway through an explicit direct fallback path.
- Preserve the existing public managed-agent route shapes as much as possible in this phase, even if their backing source changes.
- Keep `houmao-server` as the shared-registry writer for agents created or admitted through server-owned authority.
- Preserve the pointer-oriented nature of the shared registry and the session-root gateway subtree.

**Non-Goals:**

- Making gateway mandatory for all agents.
- Redesigning mailbox transport storage, mailbox content ownership, or mailbox business workflows.
- Moving shared registry state, mailbox contents, or other shared resources into per-agent gateway storage.
- Replacing the managed-agent HTTP route family with a new public route tree in this phase.
- Changing the external payload shapes of managed-agent state, detail, or request routes more than necessary for the boundary split.
- Eliminating direct runtime-managed non-server workflows.

## Decisions

### Decision: The architecture is explicitly three-layered

The refactor will treat the system as three layers:

- `houmao-server` as the shared coordination plane,
- per-agent gateway as the optional per-agent control plane,
- runtime backends and tmux sessions as the execution substrate.

`houmao-server` owns:

- managed-agent naming and alias resolution,
- server-owned launch and admission,
- shared-registry publication for server-created or server-admitted agents,
- mailbox-root ownership and other shared-resource ownership,
- capability-aware request routing,
- stable public managed-agent HTTP routes.

The per-agent gateway owns, when attached:

- TUI tracking,
- prompt queueing and ready-wait semantics,
- prompt relay and interrupt sequencing,
- per-agent restart or kill operations,
- per-agent mailbox facade and notifier behavior,
- per-agent live status snapshots.

Runtime backends and tmux remain the place where work actually executes.

Rationale:

- This matches the natural fault and ownership boundaries already implied by the current code and filesystem layout.
- It prevents the central server from becoming a second per-agent supervisor.
- It keeps optional gateway behavior architectural rather than incidental.

Alternatives considered:

- Keep `houmao-server` as both shared coordination plane and primary per-agent control plane.
  Rejected because it preserves the current overlap and makes the gateway a partial duplicate rather than the real optional control plane.
- Move shared naming and registry logic into the gateway.
  Rejected because those are shared concerns and do not belong to a per-agent sidecar.

### Decision: Public managed-agent routes stay stable, but their backing implementation becomes capability-aware

The public managed-agent routes under `/houmao/agents/*` will remain the official external contract in this phase. The server will internally choose a control provider for each request:

- prefer a gateway-backed provider when an eligible live gateway is attached and healthy for that agent,
- otherwise use a direct fallback provider.

This applies to:

- transport-neutral managed-agent request submission,
- managed-agent state and detail projection,
- gateway summary projection,
- terminal-keyed compatibility projections for TUI agents where the public route still belongs to `houmao-server`.

The server will remain the public HTTP authority. The backing source changes; the public route family does not.

Rationale:

- This minimizes public contract churn while still making the ownership split real.
- Existing clients, docs, and demo flows can keep the same route family during the boundary change.
- The server remains the one place that resolves agent names and decides whether gateway features are available.

Alternatives considered:

- Expose new public route trees for gateway-backed agents immediately.
  Rejected because it introduces avoidable surface churn before the boundary is stabilized.
- Keep explicit `/gateway/requests` as the only gateway-backed path and leave ordinary `/requests` always direct.
  Rejected because the default managed-agent path should automatically benefit from attached gateway features.

### Decision: Attached-agent TUI tracking authority moves to the gateway, with direct server fallback when no gateway is attached

For TUI-backed managed agents with an attached gateway, the gateway becomes the authoritative owner of:

- continuous tmux or process observation for that agent,
- raw TUI snapshot capture,
- shared tracked-state reduction,
- bounded live state and recent transition history for that agent.

`houmao-server` will project that gateway-owned tracked state through the existing managed-agent and terminal-facing route families. When no gateway is attached, the server retains a direct fallback tracker so `houmao-server + tmux sessions` still works without a sidecar.

This means the central server is no longer the only continuous watch owner for TUI agents. The active control plane owner for a given TUI agent is:

- attached gateway, when present,
- otherwise direct server fallback.

Rationale:

- TUI tracking is a per-agent job, not a shared-resource job.
- Gateway already has the right lifecycle and locality for session-specific observation and readiness gating.
- Optional gateway only becomes meaningful if it really owns the live per-agent watch plane when attached.

Alternatives considered:

- Leave all TUI tracking in `houmao-server` and let the gateway only queue requests.
  Rejected because it preserves the mixed responsibility boundary.
- Remove direct server fallback immediately.
  Rejected because the system must continue to work without a gateway.

### Decision: Attached-agent headless live execution authority moves to the gateway, while `houmao-server` remains the durable catalog and public facade

For server-managed headless agents with an attached gateway, the gateway becomes the owner of live operational authority:

- prompt admission,
- queueing,
- readiness gating,
- interrupt sequencing,
- restart or kill,
- active-execution posture.

`houmao-server` remains responsible for:

- agent creation and admission,
- stable public route identity,
- session-root and manifest pointers,
- shared-registry publication for server-created agents,
- durable inspection surfaces such as turn identity, turn artifacts, and turn history projections.

In other words, the gateway becomes the live per-agent controller, while the server remains the durable shared authority and projection layer. When no gateway is attached, the server continues to use the existing direct headless execution path as the fallback provider.

Rationale:

- This aligns headless ownership with the same per-agent control-plane model used for TUI agents.
- It avoids keeping headless as a special case where the server still owns all live admission while the gateway is merely an optional proxy.
- It preserves the existing server-facing turn-inspection contract by treating server-owned turn records as the durable public projection, even when live admission is delegated to the gateway.

Alternatives considered:

- Keep all headless live admission in `houmao-server`, even when gateway is attached.
  Rejected because it leaves the most important per-agent live control path outside the per-agent control plane.
- Move all durable headless turn artifacts fully into the gateway in this phase.
  Rejected because it would create avoidable public-contract churn and complicate migration.

### Decision: Registry publication authority follows creation authority

The shared registry stays pointer-oriented, but its publisher depends on who owns agent creation.

- For direct runtime-owned sessions outside server-owned admission, runtime remains the registry publisher.
- For agents created or admitted through `houmao-server`, the server becomes the registry writer and refresher.

The registry record contents remain pointer-oriented and secret-free. This change does not move queue state, mailbox content, or live gateway internals into the registry.

Stable gateway capability and session-root artifacts continue to be materialized under the runtime session root so that whichever component is the publisher reads from the same pointer-oriented runtime truth.

Rationale:

- The component that owns agent creation should own shared discoverability for that agent.
- This avoids having both runtime and `houmao-server` compete to publish the same server-created agent.
- It keeps the registry aligned with the shared coordination plane for server-managed agents.

Alternatives considered:

- Keep runtime as the publisher for all sessions, including server-created agents.
  Rejected because server-owned creation would still depend on runtime-owned shared discoverability.
- Move all registry publication into `houmao-server`, even for non-server workflows.
  Rejected because runtime-only workflows should not require the server.

### Decision: Gateway capability publication remains separate from live attachment

Gateway capability will continue to be published independently from whether a live gateway is attached. A gateway-capable session still exposes:

- stable attach metadata,
- a seeded offline gateway status,
- stable session-root pointers,
- optional server-managed routing metadata when applicable.

This is true for both direct runtime topologies and server-managed topologies. Live attachment remains a later action. This keeps the gateway optional and attach-later semantics intact.

Rationale:

- Optional sidecars only work cleanly when capability and live attachment are separate concepts.
- Attach-later operation is already part of the gateway mental model and should stay that way.
- Public server routes can report offline gateway capability without forcing startup of a sidecar.

Alternatives considered:

- Create gateway capability only at attach time.
  Rejected because it makes the system discoverability model weaker and complicates capability-aware routing.

### Decision: Compatibility routes and terminal-facing routes remain server-owned projections

Even when the gateway owns live per-agent state for an attached agent, `houmao-server` remains the public server authority for:

- `/houmao/agents/*`,
- `/houmao/terminals/*`,
- pair-managed `/cao/*` behavior where applicable.

The server serves those routes by projecting gateway-owned state or forwarding gateway-backed actions, rather than by duplicating the same live ownership internally.

Rationale:

- The server is the stable shared HTTP authority and name resolver.
- Existing clients should not need to discover gateway endpoints or route keys directly.
- This preserves external stability while changing internal ownership.

Alternatives considered:

- Require clients to contact gateway endpoints directly for live state.
  Rejected because it breaks the shared coordination plane model and leaks sidecar topology to callers.

## Risks / Trade-offs

- [Risk] Gateway-backed and direct fallback modes could drift semantically over time. -> Mitigation: define one internal control-provider contract and keep server route projections shared across both implementations.
- [Risk] Headless durable turn inspection could become inconsistent if live gateway control and server turn persistence diverge. -> Mitigation: keep `houmao-server` as the durable public turn catalog and require gateway-backed headless execution to feed the same durable projection path.
- [Risk] Moving TUI tracking out of the server could break terminal-keyed compatibility routes. -> Mitigation: keep those routes server-owned and serve them from gateway-backed tracked-state projections when a gateway is attached.
- [Risk] Registry publication can race if both runtime and server believe they are responsible. -> Mitigation: make publisher selection explicit from creation authority and keep the non-publisher on pointer publication only.
- [Risk] Optional gateway behavior increases implementation complexity because every control path has two modes. -> Mitigation: keep the public route shapes stable, centralize mode selection in the server, and constrain the direct path to degraded but supported fallback semantics.
- [Risk] Attached gateway lifecycle actions such as restart or kill could accidentally redefine the contractual agent surface. -> Mitigation: keep the gateway as a sidecar over the stable runtime session root and preserve the existing contractual agent surface rules for TUI and headless sessions.

## Migration Plan

1. Introduce an internal control-provider seam in `houmao-server` that can select gateway-backed or direct fallback execution per agent.
2. Extend gateway-owned per-agent state so an attached gateway can publish tracked TUI state, live execution posture, queue state, and lifecycle posture for one agent.
3. Switch managed-agent state, detail, and terminal-facing TUI projections to consume gateway-owned state when a gateway is attached, while preserving direct fallback when no gateway is present.
4. Move attached-agent headless live admission and lifecycle handling behind the gateway-backed provider while retaining server-owned durable turn inspection surfaces.
5. Shift registry publication for server-created or server-admitted agents from runtime-owned publication to `houmao-server`, while preserving runtime publication for direct runtime-owned workflows.
6. Update route docs, CLI guidance, and tests so the public surface still points at `houmao-server` while attached gateways provide richer behavior behind that surface.

Rollback strategy:

- keep the public managed-agent and terminal route shapes unchanged;
- keep direct fallback implementations available while the gateway-backed path is introduced;
- if the gateway-backed path proves unstable, disable gateway-backed provider selection and fall back to direct server-backed behavior without requiring data migration of registry, manifests, or gateway roots.

## Open Questions

None for the first implementation phase captured by this change.
