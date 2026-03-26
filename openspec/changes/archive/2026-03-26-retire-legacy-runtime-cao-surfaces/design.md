## Context

The repository has already shifted its supported operator story toward `houmao-server` plus `houmao-mgr`, but several active specs and runtime contracts still preserve older `houmao-cli` and standalone `houmao-cao-server` assumptions as if they were first-class public surfaces. That conflict shows up in three places at once:

- runtime and gateway authority is split across `manifest.json`, registry records, tmux env vars, `gateway_manifest.json`, and `attach.json`
- active identity guidance still teaches `houmao-cli`, `houmao-cao-server`, and runtime module entrypoints as canonical operator-facing surfaces
- registry and gateway publication still carry legacy pointer contracts even though the supported attach path is moving to manifest-first discovery

The result is a hybrid system where supported pair-managed flows already rely on managed-agent identity and manifest-backed state, while implementation and documentation still spend effort preserving standalone CAO-era contracts that are about to be retired.

This follow-up change does not replace the ongoing manifest-authority refactor. It closes the remaining supported-surface contract around that refactor and explicitly demotes the legacy surfaces so they stop constraining the target design.

## Goals / Non-Goals

**Goals:**
- Define one supported operator contract centered on `houmao-server` and `houmao-mgr`.
- Finish the manifest-first discovery model for supported tmux-backed attach, startup, resume, and relaunch flows.
- Shrink registry and tmux discovery to authoritative identity plus `runtime.manifest_path`.
- Add a native `houmao-mgr agents relaunch` contract that reuses the persisted session and built home instead of build-time launch.
- Re-scope gateway publication files and old pointer env vars so they are derived or internal only, not supported public authority.
- Revise active repository identity guidance so legacy `houmao-cli` and standalone `houmao-cao-server` are no longer taught as active first-class surfaces.

**Non-Goals:**
- Remove every internal CAO-compatible helper or `/cao/*` compatibility path in one step.
- Redesign gateway HTTP routes, mailbox contracts, or unrelated managed-agent APIs.
- Delete all legacy artifacts immediately if an internal bootstrap reader still needs them during migration.
- Rework the Python package namespace, `AGENTSYS_*` env namespace, or the shared tmux-backed runtime model itself.

## Decisions

### 1. Supported operator surfaces are `houmao-server` and `houmao-mgr`

Active docs, specs, and help surfaces will treat `houmao-server` plus `houmao-mgr` as the supported public operator path.

`houmao-cli` runtime-management flows become legacy-only guidance. Standalone `houmao-cao-server` remains retired. This means new runtime and gateway design work does not need to preserve those entrypoints as equal peers.

Houmao-owned CAO-compatible HTTP behavior is a separate compatibility concern. It may remain internally or on the server side, but it no longer justifies preserving standalone CAO launcher or raw runtime CLI workflows as first-class operator contracts.

Alternative considered:
- Keep documenting `houmao-cli` as a parallel supported path until every legacy implementation detail disappears.
- Rejected because it would continue to make old contracts normative even after the product direction has moved away from them.

### 2. `manifest.json` is the only stable session authority for supported tmux-backed flows

For supported attach, startup, resume, and relaunch flows, the stable authority chain is:

1. tmux-local `AGENTSYS_MANIFEST_PATH`
2. tmux-local `AGENTSYS_AGENT_ID`
3. shared-registry lookup to `runtime.manifest_path`
4. manifest-owned gateway or launch authority

The supported contract no longer includes `AGENTSYS_GATEWAY_ATTACH_PATH`, `AGENTSYS_GATEWAY_ROOT`, registry `gateway_root`, or registry `attach_path` as stable discovery authority.

Alternative considered:
- Keep gateway pointer envs and registry pointers as supported fallback contracts during the retirement window.
- Rejected because that preserves the dual-authority model that is causing the unfinished migration.

### 3. Gateway publication artifacts become derived or internal only

`gateway_manifest.json` remains as outward-facing publication for operator tooling and compatibility readers, but it is derived from manifest-backed authority and force-refreshed by attach.

`attach.json` or equivalent gateway bootstrap files may remain temporarily if runtime or server internals still need them to seed gateway startup, offline state, or managed-agent metadata. In this change they are explicitly internal runtime artifacts, not supported external authority. External attach and control logic must not depend on them.

This allows the codebase to finish migration without forcing a risky all-at-once deletion of internal bootstrap state.

Alternative considered:
- Remove `attach.json` and `gateway_manifest.json` entirely in the same change.
- Rejected because some server-managed paths still use attach bootstrap metadata today, and the user asked to retire old surfaces, not to add avoidable migration risk.

### 4. Relaunch is a tmux-backed runtime primitive, not a second launch path

`houmao-mgr agents relaunch` becomes the supported operator surface for relaunching tmux-backed managed sessions. Gateway-managed recovery uses the same internal primitive.

That primitive consumes:

- manifest-owned secret-free `agent_launch_authority`
- the owning tmux session environment
- the existing built home already referenced by the persisted session

It does not rebuild the brain home, does not create registry-owned launcher state, and always reuses tmux window `0` as the managed-agent surface.

Alternative considered:
- Reuse `houmao-mgr agents launch` for relaunch or add a registry-owned launcher cache.
- Rejected because relaunch is recovery of an existing live session contract, not construction of a new one.

### 5. Registry contracts shrink to discovery, not gateway pointer storage

The shared registry remains a secret-free discovery layer keyed by authoritative `agent_id`.

The required runtime pointer is `runtime.manifest_path`. Optional gateway publication data is limited to externally useful live connect metadata when a live gateway exists.

The registry is not a stable store for gateway roots, attach paths, launcher scripts, copied credentials, or other session-local runtime state.

Alternative considered:
- Keep required gateway pointer fields in the live record for compatibility.
- Rejected because those fields encode the old authority model and keep legacy readers alive by specification.

### 6. Identity specs are revised rather than layered with exceptions

Current repository identity specs still contradict the actual product direction. This change updates those specs directly instead of layering more “except legacy” notes around them.

Active repository guidance will keep the `houmao` package and module namespace, but it will stop teaching `houmao-cli` and standalone `houmao-cao-server` as canonical active public surfaces. Legacy references remain allowed only in historical, archive, retirement, or migration contexts.

Alternative considered:
- Leave identity specs untouched and rely on docs-only cleanup.
- Rejected because the current contradiction is spec-level, not just editorial.

## Risks / Trade-offs

- [Internal bootstrap readers still depend on `attach.json`] → Keep `attach.json` internal for now, but remove it from supported discovery and control contracts.
- [Docs and implementation may drift during retirement] → Update identity specs, native CLI specs, and manifest-authority specs in the same change so active guidance and runtime behavior move together.
- [Legacy users may still rely on `houmao-cli`] → Treat that path as legacy-only with explicit migration guidance rather than silent breakage.
- [Registry cleanup may break older local tooling] → Limit the required registry contract to `runtime.manifest_path` and optional live connect metadata, and keep migration notes explicit in the delta specs and tasks.
- [Relaunch semantics can be confused with build-time launch] → Separate the relaunch requirement clearly and prohibit build-home reconstruction in the relaunch contract.

## Migration Plan

1. Update OpenSpec requirements so the supported operator story is unambiguous.
2. Finish manifest-first runtime and gateway readers for supported tmux-backed flows.
3. Add the shared relaunch primitive and expose it through `houmao-mgr agents relaunch`.
4. Remove stable gateway pointer env vars and required registry pointer fields from supported contracts.
5. Re-scope `gateway_manifest.json` and `attach.json` as derived or internal artifacts only.
6. Revise docs, help text, and identity guidance so active materials teach the supported surfaces and move legacy material into retirement or migration guidance.
7. Keep explicit migration failures for deprecated standalone runtime or launcher paths until those entrypoints are removed completely.

Rollback strategy:

- The main rollback boundary is contract enforcement, not file layout. If needed, internal readers can temporarily continue consuming `attach.json` or older gateway artifacts while manifest-first readers remain in place.
- The supported spec contract after this change does not require rollback to old pointer-based discovery.

## Open Questions

- Should a later follow-up remove `attach.json` entirely once all internal bootstrap readers are migrated, or is there value in keeping it as a purely runtime-internal seed file?
- Should legacy `houmao-cli` reference docs remain in-tree as archived material, or should they move out of the active docs tree once migration guidance is complete?
