## 1. Control-Plane Source Selection

- [ ] 1.1 Introduce a distinct internal `ManagedAgentControlPlane` seam in `houmao-server`, replacing ad-hoc managed-agent branching for state and control routing. Acceptance: one typed service-layer contract covers summary/detail/history projection, request submission, gateway summary projection, and headless turn-admission hooks.
- [ ] 1.2 Thread `ManagedAgentControlPlane` selection through managed-agent alias resolution so each interaction prefers an attached healthy gateway and otherwise uses direct fallback only when safe. Acceptance: regression covers healthy gateway selection, unhealthy gateway safe fallback, and unavailable gateway rejection with existing `409` / `503` semantics.
- [ ] 1.3 Preserve current managed-agent and terminal route payload shapes while switching to the new internal seam. Acceptance: existing response envelopes remain stable for `/state`, `/state/detail`, `/requests`, `/turns`, and terminal-facing tracked-state routes across both control modes.

## 2. Gateway-Owned Per-Agent Control

- [ ] 2.1 Extend the gateway with versioned HTTP read endpoints and `GatewayClient` methods for read-optimized per-agent live control state needed by server projection. Acceptance: attached TUI and headless agents expose current live-control posture over the live gateway API without requiring direct filesystem reads from `houmao-server`.
- [ ] 2.2 Refactor any tracking ownership or supervision helpers needed beyond `houmao.shared_tui_tracking` into neutral shared modules importable by both the gateway and the direct server fallback, then move attached-agent TUI tracking ownership into the gateway for eligible attached TUI sessions. Acceptance: gateway-owned tracking does not depend on importing `houmao.server.tui` as its runtime package boundary.
- [ ] 2.3 Move attached-agent headless live admission and interrupt sequencing behind the gateway control plane while preserving server-owned durable turn creation and reconciliation. Acceptance: `houmao-server` creates the durable `turn_id` before gateway-backed admission and reconciles terminal state back into the existing managed headless turn store.
- [ ] 2.4 Add gateway-focused tests for prompt queueing, readiness gating, tracked-state ownership, attach or detach single-owner handoff, and attached headless admission behavior.

## 3. Server Route Projection

- [ ] 3.1 Update `/houmao/agents/{agent_ref}/state` and `/state/detail` to project gateway-backed live state through the gateway HTTP read surface when attached and healthy, direct fallback otherwise, and never treat stale gateway snapshots as indefinitely authoritative.
- [ ] 3.2 Update `/houmao/agents/{agent_ref}/requests` and `/turns` handling so ordinary request submission prefers gateway-backed control only when the attached gateway is healthy and admissible, falls back directly only when safe, and otherwise preserves the existing `409` / `503` semantics without changing the public request contracts.
- [ ] 3.3 Update terminal-facing TUI routes to serve attached-agent tracked state through gateway-backed projections while keeping their existing public payloads and enforcing single-owner tracking authority during attach, detach, or health transitions.

## 4. Registry Publisher Split

- [ ] 4.1 Add explicit publisher selection persisted in runtime-readable session or authority metadata so `houmao-server` writes shared-registry records for agents created or admitted through server-owned authority and runtime can detect when it must defer publication.
- [ ] 4.2 Restrict direct runtime shared-registry publication to direct runtime-owned workflows while keeping runtime-owned manifest, tmux, gateway, and mailbox pointers available for server publication. Acceptance: runtime consults the persisted publisher-selection signal before publish, refresh, or teardown.
- [ ] 4.3 Add teardown and conflict coverage for runtime-published versus server-published registry records, including server-managed runtime no-op publication and server-owned registry removal.

## 5. Docs And Verification

- [ ] 5.1 Update `docs/reference/gateway/index.md`, `docs/reference/managed_agent_api.md`, `docs/developer/houmao-server/state-tracking.md`, and `docs/reference/system-files/shared-registry.md` to describe the shared coordination plane versus per-agent control plane split and the gateway HTTP projection path.
- [ ] 5.2 Update `docs/reference/cli.md`, `docs/reference/agents_brains.md`, and relevant demo/reference material so existing managed-agent routes remain the preferred surface, attached gateways provide richer backing behavior automatically, and CAO compatibility remains outside this seam in phase 1.
- [ ] 5.3 Add integration coverage for no-gateway fallback, attached gateway TUI control, attached gateway headless control, degraded attached gateway behavior, and server-owned registry publication.
