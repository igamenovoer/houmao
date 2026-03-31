## Context

Mailbox association is currently split across several layers:

- the durable session manifest mailbox payload,
- runtime launch-plan env and tmux-published `AGENTSYS_MAILBOX_*` bindings,
- the manager-owned `agents mail resolve-live` projection,
- registry-visible mailbox summary,
- transport-owned state such as filesystem mailbox roots or session-local Stalwart credential files.

That layering made sense when mailbox work depended on live tmux env refresh, but it now creates unnecessary authority overlap. The largest practical cost is that mailbox actionability, mailbox status, gateway notifier readiness, system-skill guidance, and docs all have to reason about a mailbox-specific env projection that is no longer needed.

This change removes mailbox-specific `AGENTSYS_*` env publication as a mailbox contract and collapses mailbox association onto one manifest-backed source of truth.

## Goals / Non-Goals

**Goals:**

- Make the persisted session mailbox binding the single authoritative mailbox association record for managed sessions.
- Remove mailbox-specific `AGENTSYS_MAILBOX_*` env publication from launch-time env, tmux env, and mailbox discovery guidance.
- Keep `houmao-mgr agents mail resolve-live` as the supported current-mailbox discovery surface, but make it resolver-backed structured output rather than an env-export surface.
- Simplify mailbox activation and notifier readiness so they derive from the durable binding plus transport validation instead of tmux mailbox env refresh state.
- Update projected mailbox skills, docs, and tests to follow the manifest-first mailbox contract.

**Non-Goals:**

- Removing tmux env pointers unrelated to mailbox state such as `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, or gateway attach pointers.
- Redesigning filesystem mailbox storage or Stalwart provisioning beyond what is needed to remove mailbox env dependence.
- Moving mailbox authority into a new standalone `mailbox_binding.json` or another new persistence file.
- Changing `houmao-mgr mailbox` local filesystem administration semantics beyond mailbox discovery wording that depends on env-based runtime bindings.

## Decisions

### 1. Keep the session manifest as the only durable mailbox authority

The runtime will treat the persisted session mailbox binding as the only authoritative mailbox association for a managed session. Near term, that binding stays in the existing manifest-backed session payload rather than adding a new persistence file or requiring a larger manifest-schema move in the same change.

Why this approach:

- It removes ambiguity without adding new on-disk state.
- Existing resume, runtime bootstrap, and gateway attach paths already understand the manifest mailbox payload.
- The user-visible simplification is authority-related, not file-layout-related.

Alternatives considered:

- Move immediately to a new top-level `mailbox_binding` manifest field. This would be cleaner semantically, but it adds a schema and migration concern that is not required to eliminate mailbox env dependence.
- Add `mailbox_binding.json`. Rejected because it would create another mailbox source instead of fewer.

### 2. Remove mailbox-specific env publication from both launch env and tmux env

Mailbox-specific `AGENTSYS_MAILBOX_*` bindings will no longer be injected into provider launch env, persisted as mailbox env names for later refresh, or published into tmux session env as a live mailbox projection.

The runtime may still compute transport-specific mailbox details internally, but those details become derived runtime state rather than ambient session env.

Why this approach:

- It removes the current dual-authority model between manifest mailbox state and tmux mailbox env.
- It deletes mailbox-specific relaunch and refresh complexity that no longer provides value.
- It makes mailbox support consistent with the user's new requirement that mailbox env is unnecessary.

Alternatives considered:

- Keep mailbox env only as an internal manager contract while hiding it from skills. Rejected because it preserves most of the same drift and testing complexity.
- Keep tmux mailbox env only for joined or interactive sessions. Rejected because it preserves mailbox-specific posture branching.

### 3. `agents mail resolve-live` becomes the structured mailbox-discovery API

`houmao-mgr agents mail resolve-live` remains the supported mailbox discovery surface for skills, operators, and gateway-aware workflows, but its contract becomes structured runtime output derived from the manifest-backed binding plus current transport validation.

This change removes mailbox shell-export expectations from that command. The command should return mailbox binding data, actionable transport-derived fields, and optional validated `gateway.base_url` metadata as JSON.

Why this approach:

- It keeps one supported discovery surface for current mailbox work.
- It avoids forcing agents or operators to parse manifests directly.
- It lets runtime helpers derive transport-specific actionable details without making those details persistent ambient env.

Alternatives considered:

- Require callers to read the manifest directly. Rejected because it would spread mailbox parsing logic into skills, operators, and gateway-adjacent helpers.
- Keep `--format shell` but stop exporting mailbox keys. Rejected because it leaves an awkward partial contract and keeps mailbox discovery framed as env export.

### 4. Mailbox actionability is computed from durable binding plus transport validation

Late mailbox registration, mailbox status, and gateway notifier readiness will determine actionability from:

- the existence of a durable mailbox binding in the session manifest, and
- successful runtime validation or materialization of transport-local prerequisites.

For filesystem, actionable resolution means the active mailbox registration and derived mailbox paths resolve from the bound address. For Stalwart, actionable resolution means the runtime can validate or materialize the required session-local credential file and expose the transport metadata needed for mailbox work.

This change removes mailbox-specific `pending_relaunch` semantics. A mailbox mutation should either produce an actionable binding or fail explicitly rather than persisting a mailbox binding that is known to be non-actionable only because a tmux mailbox env refresh did not happen.

Why this approach:

- It matches the new single-authority model.
- It removes a mailbox-specific runtime posture category that existed only to explain env refresh lag.
- It gives gateway notifier and `agents mail` readiness one common decision rule.

Alternatives considered:

- Keep `pending_relaunch` as a generic “not actionable yet” state. Rejected because the motivating non-actionable case was mailbox env projection drift rather than an independent mailbox requirement.

### 5. Registry mailbox data remains non-authoritative and shallow

The registry continues to act as a discovery layer, not a mailbox source of truth. This change does not introduce new mailbox state into the registry. Any existing registry-visible mailbox summary remains summary-only and must not be used as the authoritative source for actionable mailbox work.

Why this approach:

- It keeps the simplification focused on authority and discovery.
- It aligns with the registry's existing pointer-oriented contract.
- It avoids a second migration axis while mailbox env removal is in flight.

Alternatives considered:

- Remove mailbox summary from the registry entirely in the same change. Possible, but not required to eliminate mailbox env or simplify runtime mailbox actionability.

## Risks / Trade-offs

- [Breaking `resolve-live --format shell` automation] -> Remove that mailbox contract explicitly, update docs, and replace test coverage with JSON-shape assertions.
- [Runtime code paths currently assume mailbox env bindings exist] -> Centralize manifest-backed mailbox resolution helpers first, then switch callers to those helpers before deleting env-specific code.
- [Filesystem mailbox work still needs path-shaped data] -> Keep those fields in resolver output as derived data, not persistent env.
- [The manifest still stores mailbox binding under launch-plan state] -> Accept that temporary naming mismatch now and defer a deeper schema cleanup to a later change if it still matters after env removal.

## Migration Plan

1. Introduce or refactor one manifest-backed mailbox resolution path that derives actionable mailbox state without reading mailbox env.
2. Switch mailbox command readiness, gateway notifier readiness, and system-skill guidance to that resolution path.
3. Remove mailbox env publication from launch-plan assembly, tmux mailbox projection helpers, resolver shell output, and mailbox-env-specific tests.
4. Update runtime, mailbox, and CLI documentation to remove mailbox env guidance and describe the resolver-first contract.
5. Keep existing persisted session mailbox payloads readable so there is no on-disk data migration for current manifests.

## Open Questions

- Should a later cleanup move the durable mailbox binding from `launch_plan.mailbox` to a top-level manifest field once this env-removal change is complete?
