## Context

`houmao-server` now owns continuous live TUI tracking for known tmux-backed sessions, but its lifecycle timing logic lives in an imperative reducer in [src/houmao/server/tui/tracking.py](/data1/huangzhe/code/houmao/src/houmao/server/tui/tracking.py). That reducer imported CAO-style states such as `candidate_complete`, `completed`, and `stalled` without importing the ReactiveX timing model that fixed the earlier `_TurnMonitor` problems in [context/issues/known/issue-002-shadow-turn-monitor-imperative-timing.md](/data1/huangzhe/code/houmao/context/issues/known/issue-002-shadow-turn-monitor-imperative-timing.md) and the archived [rx-shadow-turn-monitor](/data1/huangzhe/code/houmao/openspec/changes/archive/2026-03-18-rx-shadow-turn-monitor/design.md) change.

That mismatch is structural, not accidental:

- CAO runtime is post-submit and baseline-anchored.
- `houmao-server` background watch is continuous and submit-blind.

The current reducer therefore has to guess when a "turn" started and ended from periodic snapshots alone. That guess is weak enough to produce both failure classes at once:

- startup or prompt-surface churn can look like completion,
- fast real turns can still be missed when no intermediate working state is sampled.

The fix must therefore address both problems together:

1. restore ReactiveX as the timing substrate for timer-driven lifecycle semantics, and
2. stop treating unanchored background watching as if it were equivalent to submit-owned turn monitoring.

## Goals / Non-Goals

**Goals:**
- Move `houmao-server` timer-based lifecycle semantics onto ReactiveX observation streams instead of manual timestamp arithmetic.
- Distinguish continuous background watch semantics from submit-anchored turn semantics so `completed` means something causal rather than merely "the prompt looks ready again."
- Reuse one shared lifecycle timing kernel across CAO runtime and `houmao-server` instead of maintaining two drifting timing implementations.
- Keep the existing server worker/polling ownership imperative and synchronous where it already works well.
- Make the public tracked-state contract explicit about lifecycle authority so clients can interpret completion states correctly.

**Non-Goals:**
- Not rewriting tmux probing, parser selection, or worker supervision into Rx.
- Not changing parser surface classification rules or projector behavior in this change.
- Not introducing a brand-new public route family for tracked sessions.
- Not trying to retroactively infer turn anchors for prompts typed manually into tmux outside Houmao-owned control paths.
- Not making the in-progress demo-stability exploration the authoritative lifecycle source.

## Decisions

### 1. Use a shared Rx lifecycle kernel, not a second server-local state machine

**Choice:** Extract a shared lifecycle timing layer that accepts ordered parsed observations plus optional anchor events, and let both CAO runtime and `houmao-server` adapt into it.

That shared layer should own:
- readiness classification timing,
- unknown-to-stalled timing,
- completion candidate debounce,
- anchor-aware post-submit evidence accumulation,
- deterministic scheduler injection for tests.

CAO runtime and `houmao-server` should remain separate adapters around that kernel because their ownership boundaries differ.

**Rationale:** The CAO history already established that time-based lifecycle semantics are where imperative reducers drift. Rewriting only the server reducer into a different hand-rolled form would repeat the same mistake. A shared kernel keeps one timing model for both the submit-owned runtime path and the always-on server path.

**Alternatives considered:**
- Reuse [cao_rx_monitor.py](/data1/huangzhe/code/houmao/src/houmao/agents/realm_controller/backends/cao_rx_monitor.py) directly inside `houmao-server`.
  Rejected because its current API is terminal-result oriented and explicitly post-submit, while the server needs continuous state emissions.
- Keep duplicated Rx implementations in runtime and server.
  Rejected because timing drift would return as soon as one side changes.
- Keep the current server reducer and patch heuristics.
  Rejected because the underlying submit-blind imperative model is the actual problem.

### 2. Separate continuous watch lifecycle from turn-anchored completion

**Choice:** Model two lifecycle products over the same observation stream:

- **continuous watch lifecycle**
  - always active for background-tracked sessions
  - authoritative for `ready`, `waiting`, `blocked`, `failed`, `unknown`, `stalled`
  - authoritative for visible-signature stability metadata
  - conservative about completion when no turn anchor exists

- **turn-anchored lifecycle**
  - active only when `houmao-server` owns or has been given a concrete turn anchor
  - reuses CAO-style post-submit evidence and stability-window semantics
  - may emit `candidate_complete` and `completed`

Without an active anchor, background watch SHALL NOT manufacture authoritative `candidate_complete` or `completed` from ready-surface churn alone.

**Rationale:** This is the minimum design that respects both the continuous-watch contract and the original CAO Rx rationale. A background watcher can know a session is working or stalled. It cannot always know which ready-to-ready change belongs to which prompt unless it owns the submit boundary.

**Alternatives considered:**
- Treat continuous watch as equivalent to turn monitoring and keep inferring completion heuristically.
  Rejected because that is the source of the observed false completions.
- Remove completion states entirely from server tracking.
  Rejected because anchored server-owned flows still need them and existing consumers already expect lifecycle detail.

### 3. Turn anchors come only from server-owned control events or explicit future anchor sources

**Choice:** `houmao-server` should arm turn-anchored completion only from explicit anchor inputs it owns, starting with Houmao-owned terminal input submission through the public server surface. Future anchor sources can be added later, but passive tmux observation alone must not fabricate them.

When a server-owned anchor exists, the server records anchor metadata in memory and feeds the anchored observation stream into the shared Rx kernel.

When no anchor exists, the session remains in continuous-watch mode only.

**Rationale:** This keeps the meaning of completion honest. A server that saw the submit event can talk about post-submit activity and completion. A server that only saw periodic snapshots cannot.

**Alternatives considered:**
- Use "last observed ready projection" as an implicit anchor.
  Rejected because startup chrome and idle prompt churn already demonstrated that this is not a reliable turn boundary.
- Require every tracked session to be turn-anchored before any lifecycle is exposed.
  Rejected because background watch must still expose readiness, blockage, stalled, and TUI health even without active submissions.

### 4. Public tracked state exposes lifecycle authority explicitly

**Choice:** Extend the tracked-state response with explicit lifecycle authority metadata, separate from the parser surface and separate from the human-friendly operator summary.

At minimum the server should expose:
- whether completion is currently `turn_anchored` or `unanchored_background`,
- whether an anchor is active, absent, or lost/invalidated,
- enough timing metadata for clients to interpret stalled and candidate-complete semantics correctly.

The server should keep the existing terminal-keyed route family, but the route payload must tell clients when completion semantics are conservative background state rather than submit-owned turn state.

**Rationale:** Without this, clients will continue to over-trust `completed` or assume that `inactive` means "nothing happened" when the real answer is "no anchor existed."

**Alternatives considered:**
- Encode this only in free-text `detail`.
  Rejected because clients and tests need structured interpretation.
- Leave the payload unchanged and document the caveat informally.
  Rejected because the current bug already shows that ambiguous contracts get treated as authoritative.

### 5. Keep server polling imperative and feed Rx with ordered observations

**Choice:** Preserve the current server worker model:

- worker thread polls tmux/process/parser,
- worker emits ordered observation objects,
- Rx lifecycle streams reduce those observations,
- latest reduced state remains authoritative in memory.

The server should not turn the whole watch plane into an Rx-controlled scheduler. Rx is used for temporal semantics, not for ownership of tmux/process I/O.

**Rationale:** This matches the successful CAO design after issue-002 and avoids unnecessary re-architecture. The problem is timer logic, not the existence of a polling loop.

**Alternatives considered:**
- Rewrite watch workers into fully reactive interval pipelines.
  Rejected because it adds churn outside the broken part of the system.

### 6. Deterministic scheduler-based tests are part of the design, not an afterthought

**Choice:** The shared lifecycle kernel and the server adapter must be testable with deterministic scheduler control in the same way CAO Rx monitoring is. The implementation should expose unit seams that allow `TestScheduler`-style advancement for stalled recovery, candidate debounce resets, and anchor-loss cases without real sleeps.

**Rationale:** The repo already learned this lesson in the CAO runtime. If the server timing logic cannot be verified under virtual time, it will regress the next time a heuristic is adjusted.

**Alternatives considered:**
- Rely on integration tests with real polling delays.
  Rejected because they are too coarse and too slow to protect subtle temporal semantics.

## Risks / Trade-offs

- [Shared Rx kernel introduces cross-module refactor pressure] → Keep the kernel narrowly scoped to timing semantics and let runtime/server remain separate adapters.
- [Consumers may dislike more conservative completion behavior in unanchored sessions] → Expose lifecycle authority explicitly so clients can distinguish "not anchored" from "no activity."
- [Anchor capture from server-owned input surfaces will not cover manually typed tmux prompts] → Accept that limitation explicitly rather than hiding it behind false precision.
- [Overlap with `add-shadow-watch-state-stability-window`] → Treat that change as consumer smoothing and dashboard behavior only; it must not become a second authority for lifecycle timing.
- [Temporary runtime/server dual-path complexity during migration] → Keep CAO runtime behavior stable, move the server first, and converge both adapters onto the shared kernel behind tests.

## Migration Plan

1. Define the shared Rx lifecycle contract and its observation/anchor inputs.
2. Port server lifecycle timing from the imperative reducer to the shared Rx kernel while preserving existing worker ownership.
3. Add lifecycle authority metadata to server state models, routes, and client surfaces.
4. Capture server-owned turn anchors from supported control paths and wire anchored completion through the new kernel.
5. Re-point or refactor CAO runtime to consume the shared kernel without changing its external behavior.
6. Update the demo and overlapping stability work to consume the server contract rather than recreating timing semantics locally.

Rollback is straightforward: revert the server to the prior reducer and remove the new lifecycle authority fields. No persistent data migration is required because tracked state remains in memory.

## Open Questions

- Should the shared lifecycle kernel live under a new neutral subtree or remain adjacent to the existing CAO runtime backend helpers with a more neutral module name?
- Do we want a separate explicit "anchor lost" public state, or is structured metadata alongside existing lifecycle enums sufficient?
- Should server-owned turn anchoring start only from `POST /terminals/{terminal_id}/input`, or do we also want an explicit internal hook for future non-HTTP control paths in the same change?
