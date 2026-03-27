## Context

Gateway attach behavior is currently spread across four different authority surfaces:

- tmux gateway-pointer env vars such as `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- `gateway/gateway_manifest.json`
- `manifest.json`
- duplicated backend-specific state inside `manifest.json.backend_state`

That split leaks into several entrypoints:

- current-session attach in `houmao-mgr`
- runtime-owned gateway capability publication
- live gateway startup
- shared-registry fallback discovery

The result is a contract where `gateway_manifest.json` acts as both attach authority and gateway bookkeeping, while the manifest already contains much of the same truth. This refactor needs to simplify the authority chain without breaking existing runtime-owned tmux-backed flows such as `local_interactive`, native headless, and `houmao_server_rest`.

Exploration also surfaced a recovery problem: gateway-managed sessions need a relaunch surface that reuses the existing built home instead of re-entering the build-time `houmao-mgr agents launch` flow. Because the manifest stays secret-free, relaunch authority must be split cleanly between manifest-owned secret-free launch posture and the effective env already published inside the owning tmux session.

## Goals / Non-Goals

**Goals:**
- Make `manifest.json` the only stable attach authority.
- Make current-session attach prefer `AGENTSYS_MANIFEST_PATH` and fall back to `AGENTSYS_AGENT_ID` via shared-registry resolution.
- Keep shared registry as the cross-session and fallback manifest locator keyed by authoritative `agent_id`.
- Redefine `gateway_manifest.json` as outward-facing gateway bookkeeping that is derived from manifest authority and force-overwritten by attach.
- Normalize tmux-backed manifest semantics so `local_interactive`, native headless, and `houmao_server_rest` share one clearer authority model.
- Add a tmux-session-local relaunch contract for tmux-backed sessions, exposed as `houmao-mgr agents relaunch` and reused by gateway-managed recovery.
- Ensure tmux-backed relaunch reuses the already-built brain home plus current tmux session env rather than rebuilding with `houmao-mgr agents launch`.
- Keep current-session headless attach inside the owning tmux session, with window `0` reserved for the headless agent console and gateway surfaces kept away from window `0`.
- Make relaunch always target window `0` and avoid allocating a replacement tmux window; if a user repurposes window `0`, that is outside contract.
- Require the manifest to carry enough authority for gateway-managed headless turns even when no live headless worker process currently exists.
- Split process ownership clearly: agent pid in `manifest.json`, gateway pid in `gateway_manifest.json`.

**Non-Goals:**
- Remove `gateway_manifest.json`, `state.json`, or `run/current-instance.json` entirely in this change.
- Rework unrelated gateway HTTP routes, mailbox behavior, or same-session auxiliary-window policy.
- Change the managed-agent API surface beyond the attach resolution contract needed for this refactor.
- Solve all historical manifest schema cleanup in one step beyond what is required for the new manifest authority model.
- Add per-agent launcher directories, copied launcher scripts, or copied credentials under shared registry.
- Reuse the build-time `houmao-mgr agents launch` semantics as the public relaunch surface.

## Decisions

### 1. Introduce a manifest-first session authority resolver

Add a new internal resolver layer that produces one manifest-derived authority object for gateway attach and gateway startup.

Proposed shape:

- `resolve_current_session_manifest()`
  - reads current tmux session name
  - prefers `AGENTSYS_MANIFEST_PATH` when valid
  - falls back to `AGENTSYS_AGENT_ID -> shared registry -> runtime.manifest_path`
- `resolve_session_authority(manifest_path)`
  - parses the manifest
  - validates session identity and backend-specific authority
  - returns normalized attach authority and runtime control authority

This current-session path applies to any tmux-backed managed session, including native headless sessions. For native headless, the operator is still assumed to be inside the owning tmux session when using current-session attach, but window `0` remains reserved for the headless console surface rather than a gateway surface.

This is preferable to directly reading `gateway_manifest.json` because it centralizes the one rule that matters: attach authority is derived from the manifest.

Alternative considered:
- Keep resolving directly from `gateway_manifest.json` and only validate it against the manifest.
- Rejected because that preserves dual authority and keeps stale `gateway_manifest.json` as a first-class failure surface.

### 2. Keep `gateway_manifest.json`, but strip it down to derived gateway publication

`gateway_manifest.json` stays on disk under `<session-root>/gateway/gateway_manifest.json`, but it changes role.

New role:

- externally useful gateway bookkeeping
- operator-visible publication
- compatibility surface for non-authoritative readers

It is not the source of truth for attach resolution. Gateway attach regenerates it from manifest-derived authority and force-overwrites it on every attach action.

Required ownership split:

- `manifest.json` owns session truth
- `gateway_manifest.json` owns what the gateway publishes about itself
- live gateway runtime state remains in memory plus `state.json` and `run/current-instance.json`

Alternative considered:
- delete `gateway_manifest.json` entirely.
- Rejected for the first refactor stage because there are multiple readers today and a derived publication file gives a safer migration seam.

### 3. Normalize tmux-backed manifest authority around runtime, tmux, interactive, agent-launch-authority, and gateway-authority sections

Introduce `SessionManifestPayloadV4` with normalized authority sections rather than relying on `backend_state` plus backend-specific duplicated sections.

Key sections:

- `runtime`
  - `session_id`
  - `job_dir`
  - `agent_def_dir`
  - `agent_pid` nullable when no live agent worker process exists
  - `registry_generation_id`
  - `registry_launch_authority`
- `tmux`
  - `session_name`
  - primary agent surface metadata
  - primary window role metadata, with window `0` reserved for the managed agent surface
- `interactive`
  - shared interactive state for `local_interactive` and `houmao_server_rest`
- `agent_launch_authority`
  - required for tmux-backed relaunchable sessions
  - secret-free relaunch posture derived from the persisted launch plan plus backend-specific surface metadata
  - combines with the effective env already published inside the owning tmux session
  - sufficient for the gateway or resumed controller to relaunch the managed agent surface without rebuilding the brain home
- `gateway_authority`
  - `attach`
  - `control`

For native headless backends, gateway attach must target the logical tmux-backed session described by the manifest rather than a currently running worker process. A successful attach therefore does not imply that a headless turn is already in progress. The same manifest must also remain sufficient to relaunch the next headless turn later, even when no worker pid is currently published.

This is preferable to extending v3 indefinitely because the current v3 model already duplicates authority and requires resume-time cross-validation between typed sections and `backend_state`.

Alternative considered:
- keep v3 layout and add a small number of new fields.
- Rejected because it would leave the current “typed fields plus blob” duplication intact.

### 4. Expose relaunch as a session-local primitive shared by gateway recovery and `houmao-mgr`

Introduce one internal tmux-backed relaunch primitive that both gateway-managed recovery and the operator CLI use.

Public surface:

- `houmao-mgr agents relaunch`
  - current-session mode for tmux-local recovery from inside the owning session
  - explicit `--agent-id` or `--agent-name` targeting that resolves to the same manifest-backed relaunch authority

Contract:

- relaunch resolves the manifest using the same manifest-first discovery chain as attach
- relaunch consumes manifest-owned secret-free `agent_launch_authority` plus the effective env already published into the owning tmux session
- relaunch SHALL NOT call `build_brain_home()`
- relaunch SHALL NOT depend on copied launcher files, copied credentials, or registry-owned launcher directories
- relaunch SHALL always target window `0` of the owning tmux session and SHALL NOT allocate a replacement tmux window
- if a user repurposes or occupies window `0`, the runtime is not required to preserve that content or to search for another window

For native headless sessions, relaunch remains valid between turns even when `runtime.agent_pid` is `null`.

Alternative considered:
- create a `launcher/` subtree under each shared-registry record and store relaunch scripts plus credentials there.
- Rejected because shared registry is intentionally pointer-oriented and secret-free; duplicating launcher state there would drift from the tmux session env and from any user-modified built home.

### 5. Publish only manifest-first discovery envs for stable current-session attach

Stable tmux discovery for attach becomes:

- `AGENTSYS_MANIFEST_PATH`
- `AGENTSYS_AGENT_ID`

Do not keep publishing stable gateway attach pointer envs as the contract:

- `AGENTSYS_GATEWAY_ATTACH_PATH`
- `AGENTSYS_GATEWAY_ROOT`

Live gateway bindings remain a separate ephemeral contract:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

Alternative considered:
- publish only `AGENTSYS_AGENT_ID` and always require shared-registry lookup.
- Rejected because a direct tmux-published manifest path provides a local recovery path when shared-registry state is stale or unavailable.

### 6. Treat shared registry as manifest locator fallback, not attach authority or launcher store

The registry remains the cross-session discovery layer and the fallback path for current-session attach.

Required behavior:

- direct resolution by `agent_id` remains authoritative
- registry records must include `runtime.manifest_path`
- registry records must not be required to carry stable gateway attach path or gateway root for attach resolution
- registry records must not become the persistent store for relaunch scripts, copied credentials, or other session-local launcher artifacts
- gateway metadata in the registry is limited to externally useful live metadata when present

Alternative considered:
- move all attach discovery into shared registry and stop publishing `AGENTSYS_MANIFEST_PATH`.
- Rejected because that makes current-session attach depend on registry health for a session that already has a live tmux-local manifest pointer.

### 7. Split pid ownership explicitly

Process identity follows ownership:

- `manifest.json.runtime.agent_pid` when a live agent worker process exists
- `gateway_manifest.json.gateway_pid`

For native headless sessions, `manifest.json.runtime.agent_pid` may be `null` or absent between turns because the headless worker process can exit after each turn. This keeps agent process truth with the runtime session while acknowledging that headless process liveness is episodic rather than continuous.

Alternative considered:
- keep all pids in `run/current-instance.json`.
- Rejected because `run/current-instance.json` is strictly live-gateway runtime state and does not represent the long-lived session truth for the agent process.

## Risks / Trade-offs

- [Mixed-reader transition] → During migration, some code paths may still read `gateway_manifest.json` as authority. Mitigation: introduce the resolver layer first, then migrate all readers to manifest-first resolution before shrinking `gateway_manifest.json` semantics.
- [Schema migration churn] → `SessionManifestPayloadV4` touches multiple resume and publication paths. Mitigation: add v3->v4 parsing/upgrade support and keep v3 read compatibility during the refactor window.
- [Current-session attach regressions] → tmux-local attach may fail if manifest-path validation or registry fallback handling is incomplete. Mitigation: add contract tests for valid manifest-pointer, stale manifest-pointer with registry fallback, and total failure cases.
- [Relaunch env dependency] → manifest is secret-free, so tmux-backed relaunch still depends on effective env surviving inside the owning tmux session. Mitigation: specify relaunch as session-local behavior and keep tmux env publication part of the runtime contract rather than inventing a second secret store.
- [Headless between-turn ambiguity] → readers may incorrectly equate “no live agent pid” with “attach is impossible.” Mitigation: specify that native headless attach targets the logical session and future turn-launch authority, not only a currently running worker process.
- [Window-0 operator drift] → users may repurpose tmux window `0` and expect the runtime to adapt. Mitigation: codify that relaunch always targets window `0` and does not allocate another window; that drift is outside contract.
- [External tooling assumptions] → some tools may expect `gateway_manifest.json` or tmux gateway pointer env vars to remain authoritative. Mitigation: keep `gateway_manifest.json` as a derived publication artifact during the first phase and document the new precedence clearly.
- [Pair-managed authority ambiguity] → `houmao_server_rest` currently mixes `session_name` and `terminal_id`. Mitigation: make manifest `gateway_authority.attach` and `gateway_authority.control` explicit and validate them independently.

## Migration Plan

1. Add a manifest-first resolver layer without changing public behavior.
2. Introduce `SessionManifestPayloadV4` and teach manifest parsing to accept both v3 and v4.
3. Update runtime manifest writes to populate normalized authority sections, manifest-owned `agent_launch_authority`, and nullable `runtime.agent_pid`.
4. Change current-session attach to prefer `AGENTSYS_MANIFEST_PATH`, then fall back to `AGENTSYS_AGENT_ID -> shared registry -> manifest`.
5. Add the shared tmux-backed relaunch primitive and expose `houmao-mgr agents relaunch` without routing through build-time `launch`.
6. Change gateway runtime startup to derive behavior from manifest authority rather than loading `gateway_manifest.json` as the primary input, including native headless startup when no worker process is currently live.
7. Change `gateway_manifest.json` publication to be derived output only and force-overwrite it on every attach action, including `gateway_pid`.
8. Stop treating `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT` as stable discovery contracts.
9. Keep live gateway binding env publication unchanged.
10. Preserve window `0` as the managed agent surface for native headless and pair-managed sessions, and reuse that same window for relaunch instead of creating new windows.
11. After all readers are migrated, remove obsolete v3-only duplication and stale attach-pointer code paths.

Rollback strategy:

- Because `gateway_manifest.json` remains present as a derived file during migration, rollback can restore old readers temporarily.
- The main rollback boundary is the manifest parser/writer: maintain v3 read support until the new contract has been validated across runtime, gateway, and pair-managed attach flows.

## Open Questions

- Should `gateway_manifest.json` exist before the first live gateway attach with `gateway_pid = null`, or should the force-overwrite contract only apply once a live gateway attach is attempted?
- Should the first implementation keep writing stable gateway metadata into shared-registry `gateway` for compatibility, even though attach resolution no longer depends on it?
- Should the `houmao_server_rest` manifest attach authority use `managed_agent_ref = agent_id` immediately, or should the first migration stage tolerate `session_name` and convert later?
