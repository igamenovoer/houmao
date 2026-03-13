## Context

The current runtime model already has a strong authority boundary:

- runtime-owned session state lives under each session root,
- tmux session environment publishes local discovery pointers such as `AGENTSYS_MANIFEST_PATH`,
- gateway-capable sessions publish stable attach metadata under the same runtime-owned session root,
- mailbox-enabled sessions publish mailbox identity and transport bindings through runtime-owned env and manifest state.

That works well when the caller shares the target tmux server or already knows the target runtime-root layout. It does not give the system one central place to answer "where is agent `AGENTSYS-gpu`?" when different groups of agents run under different projects or different runtime roots.

The requested solution is a central registry rooted at `~/.houmao/registry`, while keeping authoritative runtime details in each agent's own runtime directory. In implementation terms, that root should be interpreted as `<resolved-user-home>/.houmao/registry`, where the user-home path is obtained through `platformdirs`-aware resolution rather than a hardcoded Linux-specific home prefix. For controlled environments such as CI, the registry root should also support explicit redirection through `AGENTSYS_GLOBAL_REGISTRY_DIR`. That means the new registry should be a locator layer, not a replacement for `manifest.json`, `gateway/attach.json`, mailbox state, or tmux session environment publication.

## Goals / Non-Goals

**Goals:**
- Add one fixed per-user shared registry at `~/.houmao/registry` by default.
- Define a strict secret-free record contract for locating a live published agent across runtime roots.
- Make runtime-owned tmux-backed sessions publish and refresh registry records automatically as part of existing lifecycle flows.
- Preserve session-root and gateway-root artifacts as the authoritative runtime state.
- Support future terminal-container backends beyond tmux by keeping the registry record contract generic enough for later `psmux`-style publication.
- Allow CI and other controlled environments to redirect the registry root through `AGENTSYS_GLOBAL_REGISTRY_DIR` without changing the default user-facing contract.

**Non-Goals:**
- Replacing tmux session environment publication for local same-host control flows.
- Moving full runtime state, gateway queue state, or mailbox contents into the registry.
- Introducing a network daemon, central database service, or cross-host distributed registry in v1.
- Solving manifest portability or `agent_def_dir` portability across checkouts in this change.
- Redesigning mailbox or gateway protocols beyond publishing secret-free pointers into the new registry.

## Decisions

### 1. Use a fixed default filesystem root at `~/.houmao/registry`, with an explicit CI override

The shared registry will live at the fixed path `~/.houmao/registry` by default.

Implementation should resolve that as `<resolved-user-home>/.houmao/registry`, where the user-home path comes from `platformdirs`-aware path handling rather than a hardcoded `/home/<user>`-style prefix.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the system should use that environment value as the effective registry root instead of the home-relative default. The override should be intended for CI, tests, and similarly controlled environments rather than as the primary documented user-facing location.

Inside that root, the registry will own:

```text
~/.houmao/registry/
  live_agents/
    <agent-key>/
      record.json
```

Rationale:
- the user explicitly requested a fixed root,
- a fixed path is easy to inspect, debug, and clean manually,
- `platformdirs` gives us a cross-platform way to obtain the user-home anchor without pretending the home layout is Linux-only,
- an explicit env override gives CI and tests a safe isolated registry location without mutating a developer's real home-scoped registry,
- the registry is user-level durable state and should not depend on any one project runtime root.

Alternatives considered:
- a `platformdirs` state-root location such as `user_state_path(...)`: rejected for this change because the user wants the explicit `~/.houmao/registry` contract rather than a platform-native state directory contract.
- no override path at all: rejected because CI and automated tests need a safe way to isolate registry state from a real user-home registry.
- storing the registry under a shared runtime root: rejected because the whole problem is that there is no guaranteed shared runtime root.
- using SQLite at the registry root: rejected because it would reintroduce a shared writable surface and lock coordination we do not need.

### 2. Store one authoritative record per live agent in an isolated hashed directory

Each published live agent will own one hashed directory under `~/.houmao/registry/live_agents/`.

The directory name will be a deterministic hash of the globally unique published agent name rather than the raw name itself. The only authoritative file inside that directory will be `record.json`, updated atomically.

Rationale:
- isolated per-agent directories remove most inter-publisher write races,
- hashed directory names avoid path-separator, case-sensitivity, and reserved-name issues,
- one-record-per-live-agent is enough for direct name resolution and avoids a shared mutable index.

Alternatives considered:
- raw agent names as directory names: rejected because they are less portable and less robust across filesystems.
- global `index.json`: rejected because it would create a shared hot file and cross-process write contention.
- shared SQLite: rejected because direct known-name lookup does not require a database.

### 3. Use the globally unique logical agent name as the registry identity, defaulting to canonical `AGENTSYS-...` for runtime-owned tmux sessions

The registry will key records by a globally unique logical `agent_name`.

For runtime-owned tmux-backed sessions in v1, that `agent_name` will default to the canonical `AGENTSYS-...` agent identity already used for the tmux session. This fits the current runtime model because tmux session names are already required to be unique among active tmux sessions, and the user problem is missing cross-root lookup rather than missing live-session naming.

Registry-facing input should accept agent names with or without the exact `AGENTSYS-` prefix and canonicalize them using the same normalization rules already established by the `agent-identity` contract. Internally, publication, hashing, duplicate detection, and lookup should all operate on the canonical `AGENTSYS-...` form.

Each record will also include a `generation_id` that changes per process start or per publication generation.

Rationale:
- reusing canonical `AGENTSYS-...` identity keeps the first implementation aligned with the existing identity model,
- optional input prefix keeps operator ergonomics aligned with the rest of runtime naming,
- the `generation_id` distinguishes "same logical name, replacement live instance" from "same live process still publishing",
- this avoids inventing project or group naming layers that do not yet exist in current runtime configuration.

Alternatives considered:
- using runtime session id as the registry key: rejected because it is not the operator-facing logical identity and is less useful for discovery.
- inventing a required `group/project/name` hierarchy now: rejected because current runtime configuration does not yet carry those concepts consistently.
- treating prefixed and unprefixed names as distinct registry identities: rejected because it would create duplicate logical entries for the same agent and diverge from existing agent-identity behavior.
- last-writer-wins publication without generations: rejected because readers would lose a clear way to distinguish stale versus replacement publishers.

### 4. Keep registry records secret-free and pointer-oriented

The registry record will publish:
- identity metadata such as `agent_name`, `generation_id`, backend, tool, and tmux session name,
- freshness metadata such as publication time and lease expiry,
- runtime-owned pointers such as manifest path, runtime session root, and agent-definition root when known,
- stable gateway pointers such as gateway root and attach-contract path when available,
- mailbox identity fields such as principal id and full address when mailbox bindings are available,
- optional live gateway connect metadata only while a listener is actually attached,
- terminal-container hints such as `kind=tmux` and the session name.

The record will not copy or centralize:
- full manifest payloads,
- gateway durable queue state,
- mailbox messages or mailbox SQLite state,
- secrets.

Rationale:
- this preserves the existing authority boundary around session-root state,
- it keeps the registry small and safe to inspect,
- it reduces drift between the registry and the authoritative runtime-owned artifacts.

Alternatives considered:
- embedding the full manifest or gateway state in the registry: rejected because that would create duplicated authority and drift risk.
- publishing secrets or environment snapshots: rejected because the registry is shared discovery metadata, not a credential store.

### 5. Make publication lease-based with atomic replace semantics

Each record will carry lease/freshness timestamps, and readers will trust lease freshness rather than directory existence.

Publishers will update records by writing a temp file in the same live-agent directory and atomically replacing `record.json`.

Graceful teardown will remove or expire the record. Unexpected crashes may leave stale live-agent directories behind, which readers will ignore once the lease expires and which cleanup tooling can remove later.

If a fresh record already exists for the same `agent_name` but a different `generation_id`, publication will fail or the new publisher will otherwise stand down rather than allowing two fresh live records for one logical identity.

Rationale:
- atomic replace avoids partial reads,
- lease-based freshness makes crash recovery simple,
- rejecting fresh duplicate publishers keeps the registry semantically single-owner per logical name.

Alternatives considered:
- relying on directory existence for liveness: rejected because stale directories are inevitable after crashes.
- delete-only cleanup with no lease: rejected because it makes crash recovery brittle.
- silent last-writer-wins duplicate handling: rejected because it can hide live ownership mistakes.

### 6. Provide cleanup tooling for stale `live_agents/` directories

The registry should treat `live_agents/` as the set of agents expected to be running now. Because crashes can still leave behind expired directories, the system should provide cleanup tooling that removes stale `live_agents/` entries whose records are missing or lease-expired beyond a grace period.

Rationale:
- the directory name `live_agents/` should reflect the operator-facing expectation,
- explicit cleanup tooling keeps that expectation true over time even after crashes,
- cleanup belongs alongside the registry contract rather than being left to manual filesystem surgery.

Alternatives considered:
- relying on manual deletion only: rejected because stale directories are an expected operational outcome after crashes.
- making readers delete stale entries opportunistically during lookup: rejected because discovery reads should stay side-effect-light and predictable.

### 7. Anchor registry publication in runtime lifecycle integration points

Registry publication will live in the runtime layer, not inside backend-specific tmux helpers.

The main lifecycle integration points will be:
- session start,
- session resume,
- gateway capability publication,
- gateway attach,
- gateway detach,
- mailbox binding refresh,
- authoritative stop-session teardown.

That likely means introducing registry helpers alongside the current runtime-owned manifest and gateway helpers, then calling them from `RuntimeSessionController` and the gateway/mailbox lifecycle paths that already own session-level publication side effects.

Rationale:
- the runtime already owns manifest persistence, gateway capability publication, and mailbox binding publication,
- keeping registry publication in the same layer preserves one owner for secret-free session discovery metadata,
- backend-specific code should continue to focus on tool/session execution rather than global registry policy.

Alternatives considered:
- publish directly from tmux backend launch helpers: rejected because mailbox and gateway state changes happen above backend launch.
- publish from a standalone background janitor only: rejected because publication needs to happen synchronously with runtime-owned lifecycle events.

### 8. Support direct known-name resolution without a shared mutable index

Known-name resolution will compute the hashed `agent-key`, load the corresponding `record.json`, validate the stored `agent_name`, and then validate record freshness and structure before returning it.

The implementation may later offer a "list active" helper, but direct resolution by known name is the primary contract and will not depend on a shared index.

Rationale:
- the main use case is "find agent X",
- O(1)-style deterministic lookup is simpler than maintaining a global index,
- the registry design remains append/update-friendly without central coordination.

Alternatives considered:
- index-first lookup: rejected because it adds a shared mutable artifact without improving the common path.
- scan-all-directories for every resolve: rejected because deterministic keyed lookup is cleaner and more scalable.

## Example

Representative default layout:

```text
~/.houmao/registry/
  live_agents/
    8f6c1f9d5a4c.../
      record.json
    a19b7c4e2190.../
      record.json

<runtime-root-a>/sessions/cao_rest/cao-rest-1/
  manifest.json
  gateway/
    attach.json
    state.json

<runtime-root-b>/sessions/claude_headless/session-20260313-xyz12345/
  manifest.json
  gateway/
    attach.json
    state.json
```

Representative CI layout with `AGENTSYS_GLOBAL_REGISTRY_DIR`:

```text
<ci-temp>/shared-registry/
  live_agents/
    8f6c1f9d5a4c.../
      record.json

<ci-workdir>/tmp/runtime/
  sessions/
    cao_rest/
      cao-rest-1/
        manifest.json
        gateway/
          attach.json
          state.json
```

The important shape is:
- the registry keeps only secret-free discovery records under one shared root,
- `live_agents/` is expected to contain only currently running published agents under normal operation,
- each session's authoritative runtime state remains in its own runtime-owned session directory,
- `record.json` points at those runtime-owned artifacts instead of copying them into the registry,
- stale crash leftovers can be removed by dedicated cleanup tooling.

## Risks / Trade-offs

- [Risk] A fixed root at `~/.houmao/registry` is less platform-native than an XDG or `platformdirs` state path. -> Mitigation: keep the fixed root as the explicit user-facing contract for this change, but resolve the home anchor through `platformdirs` so implementation does not hardcode Linux-specific home paths.
- [Risk] Stale registry files may remain after crashes. -> Mitigation: make freshness lease-based, require readers to validate expiry, and provide cleanup tooling for old `live_agents/` directories.
- [Risk] Reusing canonical `AGENTSYS-...` identity assumes live uniqueness only for active tmux-backed sessions. -> Mitigation: pair the logical name with `generation_id` and fail publication when a different fresh generation already owns the same agent name.
- [Risk] Callers may mix prefixed and unprefixed forms and accidentally expect them to resolve differently. -> Mitigation: canonicalize all registry-facing input to the exact `AGENTSYS-...` form before hashing, comparison, publication, or lookup.
- [Risk] Registry pointers may not be portable across workspaces when `agent_def_dir` or runtime paths differ. -> Mitigation: keep the registry contract honest by publishing pointers only and explicitly treating portability as out of scope for this change.
- [Risk] Readers may misinterpret stable gateway pointers as proof of a live gateway listener. -> Mitigation: publish live gateway connect metadata only while attached and keep the stable/live distinction explicit in the record contract.
- [Risk] This could become a second discovery path that drifts from tmux env publication. -> Mitigation: anchor registry publication in the same runtime-owned lifecycle paths that already publish tmux and gateway metadata.
- [Risk] An env override could accidentally leak into normal user workflows and fragment registry state. -> Mitigation: document `AGENTSYS_GLOBAL_REGISTRY_DIR` as a controlled-environment override, require explicit opt-in, and keep `~/.houmao/registry` as the default contract.

## Migration Plan

1. Add strict shared-registry models and storage helpers for path derivation from either `AGENTSYS_GLOBAL_REGISTRY_DIR` or the `platformdirs`-resolved user home, plus `live_agents/` path helpers, hashing, atomic record publication, loading, freshness validation, and cleanup.
2. Add runtime-layer publication helpers that build secret-free registry records from existing runtime, gateway, and mailbox state.
3. Integrate publication and refresh calls into session start/resume, gateway capability publication, gateway attach/detach, mailbox refresh, and stop-session teardown.
4. Add cleanup tooling that removes stale `live_agents/` directories whose records are expired or missing beyond a grace period.
5. Add discovery helpers that resolve a known shared-registry agent name into a validated record for downstream agent-to-agent or runtime control flows, canonicalizing optional `AGENTSYS-` input first.
6. Add unit and integration coverage for record publication, optional-prefix canonicalization, refresh, expiry handling, duplicate-name behavior, cleanup behavior, and runtime lifecycle integration.
7. Document the registry contract, on-disk layout, freshness semantics, cleanup tooling, and its boundary relative to manifest, gateway, and mailbox artifacts.

Rollback strategy:
- stop publishing or consuming shared-registry records,
- ignore `~/.houmao/registry` for discovery,
- leave runtime-owned manifests, gateway artifacts, mailbox state, and tmux env publication as the existing source of truth.

## Open Questions

- Should v1 expose operator-facing CLI commands for registry resolution, inspection, and stale cleanup, or is library/runtime-helper support enough for the first implementation?
- Should non-tmux runtime sessions publish into the shared registry in v1, or should first implementation scope stay limited to runtime-owned tmux-backed sessions?
