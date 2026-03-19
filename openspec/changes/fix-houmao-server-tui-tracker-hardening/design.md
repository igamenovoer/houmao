## Context

`add-houmao-server-official-tui-tracker` moved live TUI parsing and tracking into `houmao-server`, but review of the implementation found four concrete hardening gaps:

- registration currently uses raw `session_name` as a filesystem path segment without a containment guarantee
- the tracking supervisor and per-session worker threads can die permanently on one unexpected exception
- in-memory trackers and terminal aliases can outlive the live known-session registry after tmux disappears
- the immediate post-registration tracker creation path loses tmux window identity and can resolve the wrong pane until a later reconcile pass

These are cross-cutting issues because they touch request validation, filesystem layout, in-memory authority, and long-running background concurrency. They are also contract-relevant: the server claims server-owned registration, continuous background tracking, and terminal-keyed live lookup over in-memory authority, so the lifecycle and trust-boundary semantics need to be explicit before implementation changes.

## Goals / Non-Goals

**Goals:**
- Keep server-owned registration storage contained under the configured `sessions/` root.
- Ensure background tracking keeps running across unexpected reconcile or poll failures instead of silently dying.
- Align terminal-keyed live-state lookup with the live known-session registry so stale aliases do not remain authoritative after tmux loss or registry removal.
- Preserve tracked pane identity from registration time so the first live tracking cycles target the intended tmux window when that information is available.
- Add verification that exercises the hardening paths directly.

**Non-Goals:**
- Not redesigning the official TUI tracker architecture introduced by `add-houmao-server-official-tui-tracker`.
- Not adding persistence for tracker state after a session leaves the live registry.
- Not introducing a new public route family for session-keyed lookup.
- Not changing the parser stack or supported-tool scope.

## Decisions

### 1. Treat registration storage keys as validated server-owned identifiers, not raw filesystem paths

**Choice:** The registration path must no longer be formed from an unchecked `session_name`. `houmao-server` should validate the registration identifier before it becomes a storage key, reject path-unsafe values, and enforce that every resolved registration path remains under the configured `sessions/` root before writing or deleting.

The same storage-key rule must be used consistently for:

- `POST /houmao/launches/register`
- registration lookup or rediscovery
- session deletion cleanup
- terminal deletion cleanup

**Rationale:** The bug is caused by treating untrusted logical identity as a filesystem path. The fix needs to be structural, not “best effort.” The service should own a narrow server-local storage namespace and never let a request shape directory traversal semantics.

**Alternatives considered:**
- Only add a post-`resolve()` containment check: rejected because it still leaves identifier semantics underspecified and makes failures later than necessary.
- Hash or percent-encode arbitrary session names into opaque directory names: possible, but rejected for this change because the registration bridge already operates on server-scoped session identifiers and a validated safe identifier is simpler to reason about and debug.

### 2. Make worker and supervisor loops exception-resilient by default

**Choice:** The tracking supervisor and session workers must catch unexpected exceptions at the thread boundary, record or log the failure, and continue operating instead of letting the thread die.

The resilience rule should differ slightly by scope:

- supervisor reconcile failures are server-level and should be logged, then retried on the next reconcile interval
- worker poll failures are session-level and should update tracked state to an explicit probe/runtime error for that session when possible, then continue polling unless the session has genuinely left the live registry

**Rationale:** Continuous background tracking is the core value of this subsystem. A thread model where one bug or transient runtime fault permanently disables tracking violates that contract too easily.

**Alternatives considered:**
- Let threads crash and rely on external restart: rejected because it makes failure invisible inside the live-state surface and drops tracking until operator intervention.
- Only catch “expected” exceptions: rejected because unexpected exceptions are exactly what currently kill the loops.

### 3. Evict in-memory aliases and trackers when a session leaves live authority

**Choice:** When the supervisor concludes that a tracked session is no longer in the live known-session registry, or when a worker exits because tmux is gone and the reconcile pass no longer admits that session, `houmao-server` must evict the corresponding in-memory tracker and terminal alias from the authoritative live-state maps.

The live-state route family remains terminal-keyed, but terminal-keyed lookup should only resolve through live authoritative aliases. It should not succeed indefinitely from stale in-memory residue after the session stops being known.

**Rationale:** The server's live-state routes are explicitly described as in-memory authority for live known sessions. Keeping stale aliases queryable after live authority has been withdrawn creates a mismatch between the registry, workers, and route behavior.

**Alternatives considered:**
- Keep the last tracked state queryable until explicit delete: rejected because it makes the live-state route double as an implicit tombstone cache and conflicts with the live known-session contract.
- Persist a final tombstone record in memory or on disk: rejected because that introduces a new retention contract outside the scope of this hardening change.

### 4. Preserve tmux window identity during registration-seeded tracker creation

**Choice:** The registration bridge should carry optional tmux window identity into the first tracker record. If the caller provides tmux window metadata, the service should persist and use it immediately. If the caller omits it but provides a manifest path, the server should enrich the registration-derived record from the manifest before creating the dormant tracker.

The initial tracker path should not wait for a later reconcile pass to recover information that is already available at registration time.

**Rationale:** The first polling cycles happen immediately after registration and are part of the public live-state behavior. Falling back to “active pane” during that window can parse the wrong pane in a multi-window tmux session.

**Alternatives considered:**
- Keep current behavior and rely on the next reconcile to fill in the window name: rejected because it leaves an avoidable wrong-pane race in the hot path.
- Require tmux window metadata on every registration request: rejected because manifest-backed enrichment can recover it in many cases and the field should remain optional.

## Risks / Trade-offs

**[Stricter registration validation may reject currently tolerated identifiers]** → Keep the rule aligned with server-owned registration semantics and add focused tests so failures are explicit and predictable.

**[Exception handling can hide real bugs if it only swallows errors]** → Record structured failures into tracked state where possible and log thread-boundary exceptions rather than suppressing them silently.

**[Evicting aliases on tmux loss removes access to the last observed state]** → Accept that the route is for live authority, not archived inspection. If retained tombstones are needed later, define that as a separate capability.

**[Registration-time manifest enrichment adds a little more coupling between registration and manifest parsing]** → Keep the enrichment narrow and optional, using the same metadata helpers already used by registry rebuild.

## Migration Plan

1. Tighten the registration model and storage-key resolution so registration writes and deletes are root-contained.
2. Extend registration-seeded tracker creation to preserve or enrich tmux window identity before the first poll.
3. Harden the supervisor and worker loops with thread-boundary exception handling and session-level error recording.
4. Add explicit runtime hooks so reconcile can evict stale trackers and aliases when sessions leave the live registry.
5. Add unit coverage for invalid registration identifiers, exception-resilient loops, stale alias eviction, and registration-to-window propagation.

**Rollback:** Revert the hardening change. The change does not require a persisted data migration because the registration bridge remains under the same server-owned root and the live tracker remains memory-primary.

## Open Questions

- Should unexpected worker exceptions produce a generic `probe_error` state immediately, or should there be a distinct runtime-internal error kind for failures outside tmux/process/parser probing?
