## Context

Houmao already owns the supported product boundary: `houmao-server` as the public HTTP authority, `houmao-srv-ctrl` as the paired CLI, and Houmao-owned watch, parser, gateway, mailbox, and managed-agent state on top of tmux-backed sessions. The remaining CAO dependency is much narrower than the framework boundary suggests. Today the pair still depends on CAO for:

- CAO-shaped session and terminal lifecycle
- tmux terminal bootstrap quirks per provider
- profile install and profile-store behavior
- the current child-CAO proxy model under `/cao/*`
- selected `houmao-srv-ctrl cao ...` command behaviors

That split creates three problems:

- the supported pair still carries a heavy runtime dependency for a narrow control-plane slice;
- Houmao remains constrained by CAO process behavior even where Houmao already owns the public contract; and
- future upstream CAO improvements are hard to import surgically because the current architecture imports CAO as a runtime authority instead of as a capability reference.

Recent implementation work under `reserve-window-zero-and-allow-auxiliary-agent-windows` also made part of the pair boundary concrete in code:

- `houmao-srv-ctrl agent-gateway attach` is now the pair-owned gateway attach surface;
- pair-managed `houmao_server_rest` sessions now publish stable gateway attachability through runtime-owned artifacts such as `gateway/attach.json`, `gateway/state.json`, tmux env pointers like `AGENTSYS_GATEWAY_ATTACH_PATH`, and the live execution record under `gateway/run/current-instance.json`; and
- the pair now treats window `0` plus the persisted `houmao_server_rest` attach contract as stable authority for same-session gateway and auxiliary-window behavior.

That means the CAO-absorption design cannot treat gateway capability publication, `houmao_server_rest`, or the pair-managed tmux session contract as incidental implementation details. They are now stable pair-facing seams that the absorption work must preserve while replacing CAO underneath them.

The design direction accepted during explore still stands: absorb the used CAO control-plane slice into Houmao, preserve the supported pair behavior, and keep explicit insertion points so interesting upstream CAO changes can still be ported later without restoring CAO as a dependency.

## Goals / Non-Goals

**Goals:**

- Replace child-CAO and installed-`cao` dependence in the supported pair with a Houmao-owned native control core.
- Keep `houmao-server` and `houmao-srv-ctrl` working at the current supported boundary, including `/cao/*` and `houmao-srv-ctrl cao ...`.
- Preserve a clear internal seam for tmux transport, provider-specific bootstrap behavior, profile-store behavior, compatibility payload projection, and CLI compatibility wrappers.
- Preserve the existing pair-managed `houmao_server_rest` contract, including runtime-owned gateway capability artifacts, current-session attach metadata, and the reserved window `0` agent surface.
- Keep Houmao mailbox, gateway, tracking, and managed-agent state as Houmao-owned subsystems rather than re-centering them on CAO concepts.
- Fail deprecated standalone CAO-facing entrypoints such as raw `houmao-cli` CAO paths and `houmao-cao-server` with explicit migration guidance to the supported pair.
- Keep the pinned CAO checkout as a parity oracle and capability-import reference instead of a runtime dependency.

**Non-Goals:**

- Absorb the entire CAO framework, daemon model, or standalone product UX into Houmao.
- Redesign Houmao mailbox or agent gateway around CAO inbox semantics.
- Preserve mixed-pair contracts such as `houmao-server + cao` or `cao-server + houmao-srv-ctrl`.
- Keep a supported standalone `houmao-cao-server` lifecycle.
- Promise byte-for-byte human-oriented parity for every CAO CLI line of prose when script-facing compatibility is preserved.
- Rewrite the pair-owned gateway attachability contract, `houmao_server_rest` manifest shape, or reserved-window semantics beyond what is required to keep them working over the new Houmao-owned control authority.

## Decisions

### Decision 1: Introduce a Houmao-owned CAO-compatible control core and treat CAO as a compatibility dialect

Houmao will add one native control-core seam that owns the control slice currently delegated to CAO:

- session registry and lifecycle
- terminal registry and lifecycle
- tmux transport operations
- prompt and control input delivery
- terminal output and working-directory lookup
- provider bootstrap and exit behavior
- profile install and profile lookup
- compatibility inbox queue behavior when the CAO route surface still exposes it

That seam will stay behind Houmao-owned interfaces and models. CAO-shaped HTTP payloads and CAO-shaped CLI behaviors will be projections over the core, not the core's native types.

The intended internal decomposition is:

- `control_core/service`: authoritative lifecycle API
- `control_core/registry`: in-memory live session and terminal registry
- `control_core/tmux_controller`: tmux create/send/capture/lookup logic
- `control_core/provider_adapters/*`: provider-specific bootstrap, readiness, input, exit, and cleanup quirks
- `control_core/profile_store`: Houmao-owned compatibility profile storage and install behavior
- `control_core/compat/cao_router` and `control_core/compat/cao_models`: `/cao/*` request and response projection
- `control_core/compat/cao_cli`: CLI compatibility helpers for `houmao-srv-ctrl cao ...`

Rationale:

- It keeps Houmao's public pair contract Houmao-owned.
- It removes the heavy external runtime dependency without hiding the capability split.
- It gives future upstream CAO imports an obvious home by capability instead of by framework.

Alternatives considered:

- Vendor the CAO framework wholesale under a Houmao namespace. Rejected because it preserves CAO's architectural weight and behavior constraints.
- Keep the child-CAO shallow cut permanently. Rejected because it leaves runtime authority outside the supported pair.

### Decision 2: Land the absorption underneath the existing `houmao_server_rest` pair seam

The recent pair implementation already has one explicit layering boundary:

- `HoumaoServerRestSession` is the pair runtime backend;
- it routes control through `houmao-server` using a CAO-compatible client with `path_prefix="/cao"`;
- `houmao-srv-ctrl agent-gateway attach` resolves from runtime-owned attach artifacts rather than from raw CAO identities; and
- pair-managed gateway lifecycle already depends on runtime-owned `houmao_server_rest` manifests and gateway capability publication.

The absorption work should therefore land underneath that existing seam first. In practice that means:

- keep `backend = "houmao_server_rest"` as the pair-facing runtime identity;
- keep pair-owned gateway capability artifacts and attach contracts stable;
- replace the server-side CAO authority behind `/cao/*` and the pair CLI implementations beneath those existing seams; and
- avoid introducing a second parallel pair-managed control path that bypasses the existing `houmao_server_rest` runtime and gateway artifacts.

Rationale:

- The recent implementation already established these artifacts and identities as working pair contracts.
- Reusing the existing seam reduces migration risk and avoids duplicating attachability, runtime-manifest, and gateway-publication logic.
- It keeps the user-visible pair stable while changing where the underlying control authority lives.

Alternatives considered:

- Replace `houmao_server_rest` with a brand-new pair runtime identity as part of CAO absorption. Rejected because it would create avoidable churn in the newly stabilized pair contract.
- Rebuild pair gateway attachability on top of a new server-only discovery path. Rejected because `houmao-srv-ctrl agent-gateway attach` already depends on runtime-owned attach artifacts and tmux-published pointers.

### Decision 3: Keep watch, mailbox, and gateway separate from compatibility control while preserving pair-owned gateway contracts

Houmao's direct tmux/process watch path remains authoritative for live tracked state. Houmao mailbox and gateway remain separate Houmao-owned subsystems.

If the CAO-compatible inbox route family remains exposed under `/cao/terminals/{terminal_id}/inbox/messages`, it will be implemented as a compatibility-only terminal wake queue inside the control core. It will not become the Houmao mailbox transport, message store, or gateway notifier input.

The recent pair-owned gateway contracts remain in force during this absorption:

- current-session attach continues to resolve from tmux-published attach metadata rather than from `terminal_id` or raw CAO state;
- `gateway/attach.json`, `gateway/state.json`, and `gateway/run/current-instance.json` remain runtime-owned authoritative artifacts for attachability and live gateway execution; and
- auxiliary gateway windows remain non-authoritative while window `0` stays the contractual agent surface.

Rationale:

- Houmao mailbox carries message semantics, addresses, read state, and transport-specific bindings.
- CAO inbox is only a terminal-scoped deferred input queue.
- Mixing them would blur two different authority boundaries and complicate the existing gateway/mailbox architecture for no product gain.
- Preserving the existing gateway publication seam avoids breaking the current pair attach workflow while the underlying CAO authority is being removed.

Alternatives considered:

- Reuse Houmao mailbox as the implementation of CAO inbox. Rejected because mailbox delivery and inbox terminal wake-up are different contracts.
- Keep CAO inbox in a standalone preserved CAO subprocess. Rejected because it restores the dependency the change is removing.

### Decision 4: `houmao-server` becomes the only supported `/cao/*` authority

`houmao-server` will stop supervising a child `cao-server` as part of the supported pair path. Instead, `/cao/*` routes will dispatch directly into the local control core and project CAO-compatible responses there.

The root `GET /health`, `/houmao/*`, managed-agent APIs, watch workers, gateway routes, and mailbox routes remain Houmao-owned exactly as before. The change is specifically about where `/cao/*` compatibility work lands.

Derived child-CAO port behavior, child-home filesystem layout, and child readiness bookkeeping disappear from the supported server contract. If server-local health needs to report compatibility-core degradation, it will do so as Houmao-owned fields rather than as child process metadata.

Rationale:

- The supported product boundary is already `houmao-server + houmao-srv-ctrl`.
- Removing the proxy/subprocess layer simplifies the architecture while preserving the same public route family.
- Houmao can keep the route contract stable without keeping CAO as the runtime authority.

Alternatives considered:

- Keep `/cao/*` as a pure reverse-proxy surface to a local CAO child. Rejected because that leaves the wrong authority in the critical path.
- Rename the compatibility routes away from `/cao/*`. Rejected because the user wants the pair to keep working as it does today.

### Decision 5: `houmao-srv-ctrl` keeps the `cao` namespace but stops delegating to external `cao`

`houmao-srv-ctrl` will preserve its explicit `cao` namespace, but the implementation will become repo-owned.

Command behavior splits into two buckets:

- session-backed compatibility commands such as `launch`, `info`, `shutdown`, and `install` route through `houmao-server` and its local control core;
- local compatibility commands that remain part of the documented `houmao-srv-ctrl cao` family, such as `flow`, `init`, or `mcp-server`, use Houmao-owned compatibility helpers instead of shelling out to `cao`.

Script-facing behavior still matters: exit codes, machine-readable output, and compatibility-significant argument handling need to stay aligned with the pinned CAO source where those behaviors are part of the current contract.

Rationale:

- It preserves the supported pair CLI without requiring `cao` on `PATH`.
- The namespace stays stable while the implementation authority moves into Houmao.
- Upstream CAO CLI behavior can still be compared and selectively imported, but it no longer drives runtime execution directly.

Alternatives considered:

- Keep delegating to installed `cao` for local-only verbs. Rejected because it keeps the dependency alive and weakens the supported pair boundary.
- Narrow the `houmao-srv-ctrl cao` namespace to only pair-backed verbs immediately. Rejected because the user asked to keep `houmao-srv-ctrl` working like the current supported surface.

### Decision 6: Retire standalone CAO-facing operator entrypoints with explicit migration failures while keeping internal pair runtime machinery

The supported operator path after this change is the pair:

- `houmao-server`
- `houmao-srv-ctrl`

If `houmao-cli` is invoked in ways that would create or control standalone CAO-backed sessions, those commands will fail fast with explicit migration guidance to `houmao-server` and `houmao-srv-ctrl`.

`houmao-cao-server` becomes a retirement surface: it always fails fast with the same migration guidance and does not attempt to read config, spawn CAO, or mutate launcher artifacts.

This retirement applies to public standalone operator entrypoints, not to the internal runtime machinery that the supported pair still uses. Pair-owned runtime artifacts such as `houmao_server_rest` manifests and gateway capability publication remain valid internal building blocks unless and until a later change replaces them deliberately.

Rationale:

- The user explicitly does not want to preserve those standalone CAO entrypoints.
- Fast failure is cleaner than half-preserving a deprecated surface that no longer has a supported backend.
- It keeps the migration story unambiguous.

Alternatives considered:

- Preserve a best-effort compatibility shim for `houmao-cao-server`. Rejected because it keeps a misleading supported surface alive.
- Let deprecated commands fail implicitly due to missing CAO pieces. Rejected because the failure mode would be noisy and unhelpful.

### Decision 7: Keep provider quirks and profile behavior in explicit Houmao-owned seams

Provider-specific bootstrap and shutdown quirks will be absorbed into provider adapters. CAO-format agent-profile semantics that Houmao still needs will be preserved in a Houmao-owned profile store and loader.

The profile store remains a compatibility-format store, not a hidden CAO `HOME`. Pair install flows mutate that Houmao-owned store through `houmao-server`.

Rationale:

- Provider behavior is one of the few CAO slices Houmao still needs.
- Making provider quirks explicit avoids hard-coding CAO behavior across unrelated modules.
- Profile install/store behavior becomes understandable and testable without depending on hidden CAO home layout.

Alternatives considered:

- Keep provider/bootstrap logic scattered across route handlers or CLI wrappers. Rejected because it would make future upstream imports difficult.

### Decision 8: Verification uses CAO as oracle, not runtime authority, and preserves the recent pair contracts

The pinned CAO source remains the compatibility oracle. Verification will compare Houmao-owned implementations against that oracle at the route, payload, and CLI-shape level.

This means:

- route and payload parity tests for `/cao/*`
- CLI compatibility tests for `houmao-srv-ctrl cao ...`
- selected live oracle comparisons against the pinned CAO source where a real process is the easiest parity check
- direct Houmao regression tests for server root routes, watch behavior, install behavior, `houmao_server_rest` manifests, gateway capability publication, current-session attachability, and migration-failure surfaces

CAO may still be used in verification or manual parity workflows, but it is no longer a supported runtime dependency of the product path.

Rationale:

- It preserves an objective compatibility target.
- It avoids conflating parity testing with runtime architecture.

Alternatives considered:

- Drop all parity checks once Houmao owns the implementation. Rejected because compatibility drift would become hard to detect.

## Risks / Trade-offs

- Compatibility drift without CAO in the runtime path → Mitigation: keep the pinned CAO checkout as an explicit parity oracle and add route/CLI parity coverage.
- Reimplementing local-only `houmao-srv-ctrl cao` verbs adds ownership cost → Mitigation: confine them to small compatibility-helper modules instead of spreading them across the pair.
- Provider bootstrap quirks are easy to accidentally duplicate → Mitigation: centralize them under provider adapters and forbid route handlers from embedding provider-specific launch logic.
- Removing child-CAO state may break hidden assumptions in current-instance, health, or docs → Mitigation: make retirement and server-local replacement fields explicit and cover them in regression tests.
- Replacing CAO underneath the pair could accidentally break the newly implemented `houmao_server_rest` gateway attach workflow → Mitigation: preserve runtime-owned attach artifacts, `current-instance.json`, tmux-published gateway env pointers, and reserved window `0` semantics as explicit non-goals of this change.
- Deprecated standalone surfaces may still be used by old scripts → Mitigation: fail fast with migration guidance that names the replacement pair explicitly.

## Migration Plan

1. Introduce the Houmao-owned control-core interfaces, registries, tmux controller, provider adapters, profile store, and compatibility inbox queue underneath the existing `houmao_server_rest` pair seam.
2. Rewire `houmao-server` `/cao/*` routes from child-CAO proxying to the local control core while keeping Houmao root, `/houmao/*`, watch, gateway, mailbox, runtime-owned gateway capability artifacts, and reserved-window behavior intact.
3. Move pair install behavior and compatibility profile-store access onto the Houmao-owned profile store.
4. Rework `houmao-srv-ctrl cao ...` to use repo-owned compatibility helpers and pair APIs instead of invoking external `cao`.
5. Add explicit migration failures for deprecated standalone CAO-facing `houmao-cli` paths and for `houmao-cao-server`, while preserving internal pair runtime machinery and `houmao_server_rest` artifacts.
6. Update docs, help text, and regression coverage to reflect the pair-owned control core, stable `houmao_server_rest` and gateway-publication contracts, and retired standalone surfaces.
7. Keep the pinned CAO checkout available for parity verification and future selective imports.

Rollback strategy:

- If parity or behavior gaps are found during implementation, keep the new control-core seam and restore specific compatibility behaviors inside the seam rather than restoring child-CAO or installed-`cao` as product dependencies.
- If a low-value compatibility-local CLI verb proves too expensive, keep the `houmao-srv-ctrl` namespace stable and fail only that verb explicitly with migration guidance rather than rolling the whole pair back to external CAO dependence.

## Open Questions

None at proposal time. The architectural direction is now explicit: the supported pair keeps the public compatibility surfaces, CAO becomes an oracle and import source rather than a runtime authority, and deprecated standalone CAO-facing entrypoints fail with migration guidance instead of remaining supported.
