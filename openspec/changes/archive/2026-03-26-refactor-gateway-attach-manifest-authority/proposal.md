## Why

Gateway attachability currently depends on a layered contract split across tmux gateway-pointer env vars, `gateway/gateway_manifest.json`, the runtime session manifest, and duplicated backend state inside the manifest itself. That makes current-session attach harder to reason about, makes stale metadata failure modes more likely, and keeps `gateway_manifest.json` acting as both attach authority and gateway bookkeeping.

This change is needed now because the repo already has both a shared live-agent registry and tmux-published manifest pointers, which are better discovery primitives than the current gateway-root pointer env contract. We also need a clearer ownership split between runtime session truth, gateway publication, and live gateway runtime state before more gateway behavior accumulates on top of the current contract.

One more issue emerged during exploration: attached gateways must be able to relaunch the agent they manage without rebuilding the already-built brain home. The manifest is intentionally secret-free, so relaunch cannot be expressed as "re-run `houmao-mgr agents launch`" or "copy launcher scripts and credentials into shared registry." The relaunch contract needs to combine manifest-owned secret-free launch posture with the effective env already published inside the owning tmux session.

## What Changes

- Refactor gateway attach resolution to be manifest-first for tmux-backed sessions, including native headless: current-session attach prefers `AGENTSYS_MANIFEST_PATH`, then falls back to `AGENTSYS_AGENT_ID` plus shared-registry resolution, instead of relying on `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`.
- Redefine `gateway/gateway_manifest.json` as a derived outward-facing gateway bookkeeping artifact rather than a stable attach authority.
- Require gateway attach to regenerate and force-overwrite `gateway_manifest.json` from manifest-derived authority on every attach action.
- Unify tmux-backed `local_interactive`, native headless, and `houmao_server_rest` session manifests under a normalized manifest authority model that makes attach authority and runtime control authority explicit.
- Add a tmux-session-local relaunch contract, exposed through `houmao-mgr agents relaunch` and reused internally by gateway-managed recovery, so relaunch uses the existing built home and current tmux session env instead of rebuilding.
- Replace native-headless-only launch metadata with manifest-owned `agent_launch_authority` that covers relaunch for both TUI and headless tmux-backed sessions.
- Reserve tmux window `0` for the managed agent surface, including native headless console output, and require relaunch to reuse window `0` instead of allocating a new tmux window; if a user repurposes window `0`, that is outside the contract.
- Add explicit process identity ownership rules: the agent process pid lives in `manifest.json` when a live agent process exists, while the gateway pid lives in `gateway_manifest.json`.
- **BREAKING**: current-session gateway attach no longer treats tmux-published gateway-root pointer env vars as the discovery contract.
- **BREAKING**: `gateway_manifest.json` is no longer the authoritative input for attach resolution; when it disagrees with `manifest.json`, readers must trust the manifest.
- **BREAKING**: relaunch recovery no longer goes through the build-time `houmao-mgr agents launch` semantics; tmux-backed relaunch is a separate surface that assumes the brain home already exists.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-gateway`: change gateway attach discovery to be manifest-first, redefine `gateway_manifest.json` as derived bookkeeping, formalize gateway pid publication semantics, and require gateway-managed relaunch to use the shared relaunch primitive instead of build-time launch.
- `brain-launch-runtime`: change tmux-backed runtime manifest requirements to own normalized session authority, including nullable headless pid semantics, manifest-owned `agent_launch_authority`, and manifest-first attach and relaunch authority for tmux-backed sessions.
- `agent-discovery-registry`: change the registry’s role to be the fallback/cross-session manifest locator keyed by authoritative `agent_id`, rather than a peer attach authority or a launcher-artifact store.

## Impact

- Affected code: `src/houmao/agents/realm_controller/{runtime.py,manifest.py,boundary_models.py,gateway_models.py,gateway_storage.py,gateway_service.py,registry_models.py,registry_storage.py,agent_identity.py}`, `src/houmao/srv_ctrl/commands/agents/{core.py,gateway.py}`, `src/houmao/srv_ctrl/commands/managed_agents.py`, and relevant server-side managed-agent attach paths.
- Affected files and contracts: `manifest.json`, `gateway/gateway_manifest.json`, tmux session env publication, shared-registry `record.json`, gateway startup resolution, current-session pair attach behavior, and the new tmux-backed relaunch contract.
- Operator/API impact: current-session attach semantics change for tmux-backed sessions, including native headless; attach continues to work, but discovery precedence and stale-metadata handling become manifest-first. A new `houmao-mgr agents relaunch` surface is introduced for tmux-backed recovery and it assumes the built home already exists and window `0` remains reserved for the managed agent surface.
- Testing impact: unit and integration coverage will need updates for runtime manifest schema, shared-registry resolution, current-session attach, tmux-backed relaunch, native headless between-turn attach, gateway startup, and attach artifact regeneration.
