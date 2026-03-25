## 1. Control-Plane Source Selection

- [ ] 1.1 Introduce an internal managed-agent control-provider seam in `houmao-server` for gateway-backed and direct fallback state and request handling.
- [ ] 1.2 Thread control-provider selection through managed-agent alias resolution so each request chooses gateway-backed control when an eligible live gateway is attached and direct fallback otherwise.
- [ ] 1.3 Preserve current managed-agent and terminal route payload shapes while adding regression coverage for both control modes.

## 2. Gateway-Owned Per-Agent Control

- [ ] 2.1 Extend gateway-owned runtime state and storage with read-optimized per-agent live control snapshots needed for server projection.
- [ ] 2.2 Move attached-agent TUI tracking ownership into the gateway for eligible attached TUI sessions while preserving direct server fallback when no gateway is attached.
- [ ] 2.3 Move attached-agent headless live admission and interrupt sequencing behind the gateway control plane while preserving the existing durable server turn-inspection surfaces.
- [ ] 2.4 Add gateway-focused tests for prompt queueing, readiness gating, tracked-state ownership, and attached headless admission behavior.

## 3. Server Route Projection

- [ ] 3.1 Update `/houmao/agents/{agent_ref}/state` and `/state/detail` to project gateway-backed live state when attached and direct fallback state otherwise.
- [ ] 3.2 Update `/houmao/agents/{agent_ref}/requests` and `/turns` handling so ordinary request submission prefers gateway-backed control without changing the public request contracts.
- [ ] 3.3 Update terminal-facing TUI routes to serve attached-agent tracked state through gateway-backed projections while keeping their existing public payloads.

## 4. Registry Publisher Split

- [ ] 4.1 Add explicit publisher selection so `houmao-server` writes shared-registry records for agents created or admitted through server-owned authority.
- [ ] 4.2 Restrict direct runtime shared-registry publication to direct runtime-owned workflows while keeping runtime-owned manifest, tmux, gateway, and mailbox pointers available for server publication.
- [ ] 4.3 Add teardown and conflict coverage for runtime-published versus server-published registry records.

## 5. Docs And Verification

- [ ] 5.1 Update gateway, managed-agent API, state-tracking, and shared-registry docs to describe the shared coordination plane versus per-agent control plane split.
- [ ] 5.2 Update CLI guidance and demo/reference material so existing managed-agent routes remain the preferred surface while attached gateways provide richer backing behavior automatically.
- [ ] 5.3 Add integration coverage for no-gateway fallback, attached gateway TUI control, attached gateway headless control, and server-owned registry publication.
