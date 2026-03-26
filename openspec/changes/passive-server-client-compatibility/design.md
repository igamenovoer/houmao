## Context

`houmao-passive-server` already implements the Step 6 lifecycle endpoints and most of the Step 5 request/headless surface, but the pair-facing client and CLI stack still assume `houmao-server` is the only supported managed authority. Today that assumption is enforced in several places:

- `src/houmao/server/client.py` is the only typed pair client and is shaped around the old server.
- `src/houmao/srv_ctrl/commands/common.py` rejects any `/health` response whose `houmao_service` is not `"houmao-server"`.
- `src/houmao/srv_ctrl/commands/server.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, and `src/houmao/agents/realm_controller/gateway_service.py` instantiate `HoumaoServerClient` directly.

The passive server's current HTTP surface is also not a drop-in replacement for those consumers. Discovery, lifecycle, gateway proxy, mail, request, stop, and headless turn routes exist, but `GET /houmao/agents/{agent_ref}/state`, `/state/detail`, and `/history` are observation-specific TUI routes. They do not currently provide the managed headless summary/detail/history views that `houmao-mgr agents state/show` and the managed headless gateway adapter expect.

Step 6 therefore needs two layers of work:

1. A passive-server-aware pair client selection path.
2. A compatibility projection surface so pair consumers can keep using the managed-agent view contract during the Step 7 side-by-side validation window.

## Goals / Non-Goals

**Goals:**

- Treat `houmao-passive-server` as a supported pair authority alongside `houmao-server`.
- Add a passive-server-aware typed client that exposes the subset of pair operations used by `houmao-mgr` and other managed-authority consumers.
- Preserve the existing `houmao-mgr` registry-first control model while allowing explicit `--port` targeting of a passive server.
- Provide passive-server compatibility views for managed-agent summary/detail/history, including managed headless agents.
- Update gateway-managed headless control paths to resolve their managed client from `managed_api_base_url` instead of hardcoding `HoumaoServerClient`.
- Keep the passive server's existing observation endpoints intact for Step 4 consumers.

**Non-Goals:**

- Making `backend='houmao_server_rest'` run against `houmao-passive-server`. That backend remains old-server-only until Step 8 retirement.
- Removing or renaming the old `houmao-server` client and API in this change.
- Replacing the passive server's observation routes with the managed-agent compatibility routes.
- Solving cross-host passive-server gateway attach/detach. Step 6 only guarantees same-host pair workflows where local registry/controller authority exists.

## Decisions

### Decision: add `PassiveServerClient` and a shared pair-authority client protocol instead of stretching `HoumaoServerClient`

The implementation will add a dedicated passive-server client (for example under `src/houmao/passive_server/client.py`) and a small shared protocol/factory for pair-facing consumers.

The factory will:

- Probe `GET /health`.
- Accept `houmao_service == "houmao-server"` and return `HoumaoServerClient`.
- Accept `houmao_service == "houmao-passive-server"` and return `PassiveServerClient`.
- Reject raw CAO or unknown identities with the existing explicit unsupported-pair guidance.

This keeps the old client focused on the old server's route/model contract. Extending `HoumaoServerClient` to hide both servers behind one concrete class would mix old CAO-era assumptions with passive-server-specific behavior and would make too many methods conditional on the remote identity.

**Alternatives considered**

- Extend `HoumaoServerClient` directly: rejected because the passive server does not share the old server's route map or model shapes closely enough.
- Branch in every caller: rejected because `srv_ctrl`, gateway service, and future pair consumers would all reimplement the same identity detection and response adaptation.

### Decision: add passive-server managed-agent compatibility routes instead of mutating the existing observation routes

The passive server will add a compatibility projection surface dedicated to pair-managed consumers:

- `GET /houmao/agents/{agent_ref}/managed-state`
- `GET /houmao/agents/{agent_ref}/managed-state/detail`
- `GET /houmao/agents/{agent_ref}/managed-history`

These routes will return the existing `HoumaoManagedAgentStateResponse`, `HoumaoManagedAgentDetailResponse`, and `HoumaoManagedAgentHistoryResponse` models from `houmao.server.models`.

This avoids breaking the Step 4 `passive-server-tui-observation` contract, which intentionally exposes observation-centric payloads. It also solves the headless gap cleanly: managed headless state/detail/history needs live turn metadata that is not currently derivable from the passive server's public observation routes.

**Alternatives considered**

- Reuse the existing `/state`, `/state/detail`, and `/history` routes for managed compatibility: rejected because those routes are already specified as observation surfaces and would silently change meaning.
- Synthesize all managed views entirely inside the passive client from current routes: rejected because current passive routes do not expose enough information to reconstruct live managed headless detail/history.

### Decision: build compatibility projections server-side from transport-specific sources

Compatibility projections will be assembled in one passive-server-specific mapping layer, rather than spreading ad hoc conversions across client code.

For TUI-backed agents, the compatibility layer will adapt discovery plus observation state into the managed-agent summary/detail/history models.

For passive-server-managed headless agents, the compatibility layer will adapt:

- discovery identity data,
- live/persisted headless authority metadata,
- latest turn status and artifacts,
- gateway/mailbox summaries when present.

This keeps `houmao-mgr` and the gateway-managed headless adapter operating on the same old managed-agent view models they already expect, which minimizes Step 6 churn and leaves Step 8 free to remove the compatibility layer once the old server is retired.

**Alternatives considered**

- Push all mapping into `houmao-mgr`: rejected because every pair-facing consumer would need transport-specific branching.
- Reuse `srv_ctrl.commands.managed_agents` helpers directly: rejected because those helpers are CLI-oriented and would create awkward cross-package coupling. Shared mapping code should live in a neutral passive-server compatibility module.

### Decision: keep gateway attach/detach local when the selected pair authority is a passive server

Step 5 intentionally made passive-server HTTP `gateway/attach` and `gateway/detach` return `501` with guidance to use `houmao-mgr`. Step 6 will preserve that server contract.

To keep `houmao-mgr agents gateway attach/detach` working in same-host passive-server workflows, the CLI will prefer local registry/controller authority for those two operations even when the operator supplied a passive-server port. If the target cannot be resolved to a local registry-backed session, the CLI will fail explicitly instead of round-tripping to the passive server's `501` response and pretending the operation is remotely supported.

**Alternatives considered**

- Implement passive-server HTTP attach/detach now: rejected because it contradicts the Step 5 contract and expands passive-server authority beyond the chosen design.
- Let `houmao-mgr` call the passive-server `501` routes: rejected because it creates a poor UX and breaks the native CLI contract for same-host validation.

### Decision: convert gateway-managed headless consumers to the pair-authority factory, not to passive-specific branching

`gateway_service.py` currently hardcodes `HoumaoServerClient` for managed headless targets discovered through `managed_api_base_url`. That code will instead request a client from the pair-authority factory and depend on the shared managed-authority protocol.

This keeps gateway-managed prompt/interrupt/status compatible with both server identities without baking passive-server special cases into gateway runtime logic.

`houmao_server_rest` remains excluded from this decision because it still depends on old `/cao` behavior and old server instance metadata.

## Risks / Trade-offs

- **[Compatibility projection duplicates view logic]** → Mitigation: keep the mapping in one dedicated passive-server compatibility module and add focused tests for TUI and headless projections.
- **[Managed headless compatibility depends on Step 5 correctness gaps]** → Mitigation: implement or co-land the required parts of `fix-passive-server-step5-headless-gaps` before relying on rebuilt handles, registry publication, and persisted turn metadata.
- **[Gateway attach/detach remains same-host only]** → Mitigation: document the limitation explicitly in CLI errors and Step 7 validation notes instead of pretending remote passive-server attach/detach works.
- **[Two pair clients increase maintenance surface]** → Mitigation: keep the shared protocol narrow and only cover the operations actually consumed by `houmao-mgr` and gateway-managed headless control.

## Migration Plan

1. Land the Step 5 headless-gap fixes needed for reliable managed headless resume/state if they are not already in the branch being used.
2. Add the passive-server compatibility projection module and the new managed-state/detail/history routes.
3. Add `PassiveServerClient` and the pair-authority client factory/protocol.
4. Update `srv_ctrl` common helpers, `server` commands, and managed-agent commands to resolve clients through the new factory.
5. Update gateway-managed headless runtime code to use the same client factory.
6. Add tests for passive pair detection, lifecycle commands, managed-agent state/show flows, headless turn flows, and gateway-managed headless control through a passive `managed_api_base_url`.
7. Validate Step 7 by running old `houmao-server` on 9889 and `houmao-passive-server` on 9891.

Rollback remains straightforward: point operators and scripts back to the old `houmao-server` port and keep using `HoumaoServerClient` paths only. This change is additive and does not remove the old server.

## Open Questions

None. The remaining uncertainty is implementation sequencing, not architecture.
