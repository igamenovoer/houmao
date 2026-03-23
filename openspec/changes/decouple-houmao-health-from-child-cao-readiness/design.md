## Context

`houmao-server` exposes two distinct surfaces today:

- Houmao-owned root and `/houmao/*` routes
- CAO-compatible `/cao/*` routes

The repository already uses `startup_child=False` for native managed-headless flows such as the mail ping-pong gateway demo and for managed-headless gateway tests. Those paths use Houmao-owned managed-agent routes and do not need the child CAO server to exist.

Despite that split, the current root health payload and current-instance payload still always project child-CAO status, and at least one demo startup waiter treats that child status as mandatory readiness. That makes a valid no-child launch mode fail before any native headless work begins.

## Goals / Non-Goals

**Goals:**

- Make Houmao root health and current-instance semantics correct for `startup_child=false`.
- Ensure native Houmao-managed flows can treat root health as sufficient readiness when they do not use `/cao/*`.
- Preserve an explicit path for CAO-dependent flows to check CAO readiness.
- Add verification that guards against this coupling returning in future demos or server changes.

**Non-Goals:**

- Re-architect the CAO-backed `/cao/*` compatibility surface.
- Remove child-CAO metadata from child-enabled server runs.
- Change the public managed-headless launch or gateway APIs.
- Generalize every demo onto one shared startup helper in this change.

## Decisions

### Decision: No-child mode publishes absent child metadata rather than unhealthy child metadata

When `houmao-server` starts with `startup_child=false`, `GET /health` and `GET /houmao/server/current-instance` will continue to report Houmao-server liveness and identity, but `child_cao` will be omitted (`null`) rather than populated with a failing derived-port probe.

Rationale:

- The response models already make `child_cao` optional.
- Existing callers already have a natural interpretation for `None`: child metadata is not required for this mode.
- Publishing an unhealthy child object for an intentionally absent child makes valid no-child runs look broken.

Alternatives considered:

- Keep returning a failing child object and require callers to inspect `startup_child`.
  Rejected because the current payload does not expose that mode directly and existing callers already treat unhealthy child status as failure.
- Add a new explicit status enum for child lifecycle state.
  Rejected for this change because it expands the public contract more than needed to fix the coupling.

### Decision: Readiness checks must align with the surface a workflow actually uses

Native Houmao-managed workflows that use `/houmao/*` routes only will treat root `GET /health` as the readiness gate. CAO-dependent workflows that require `/cao/*` compatibility routes should check `/cao/health` or an equivalent CAO-dependent operation instead of inferring readiness from Houmao root health metadata.

Rationale:

- Root health is already specified as Houmao-owned rather than CAO-compatible.
- The child CAO process is an upstream adapter for compatibility work, not the authority for Houmao-native managed-headless flows.
- This split makes the dependency boundary explicit for demos and future tooling.

Alternatives considered:

- Continue using root health plus embedded child metadata for all readiness checks.
  Rejected because it mixes two different readiness domains and recreates the bug that blocked the mail ping-pong demo.

## Risks / Trade-offs

- [Risk] Existing debug tooling may expect `child_cao` to always be present. → Mitigation: the field is already optional in the API model; update server and app-contract tests to cover both child-enabled and no-child cases.
- [Risk] A CAO-dependent workflow could accidentally weaken its readiness gate if it only checks root health after this change. → Mitigation: update affected demo startup logic to use a CAO-specific readiness check when CAO routes are actually required.
- [Risk] The spec line that v1 supervises a child CAO can be read too absolutely. → Mitigation: capture the no-child semantics explicitly in the `houmao-server` delta spec so startup mode and health semantics are aligned.

## Migration Plan

No persisted data migration is required.

Implementation rollout should:

1. update `houmao-server` root health/current-instance behavior for `startup_child=false`
2. update native no-child waiters to stop requiring child health
3. update any CAO-dependent waiters to query CAO readiness explicitly
4. extend unit and integration coverage for both modes

Rollback is low risk because the change is limited to readiness semantics and optional metadata projection.

## Open Questions

None at proposal time.
