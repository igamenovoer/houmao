# Motivating Issue: `houmao-server` Reintroduced Imperative Timing And Unanchored Completion Inference

## Priority
P1 — Background watch can report false completion; fast real turns can still be missed or misclassified.

## Status
Proposed fix tracked in `openspec/changes/fix-houmao-server-rx-lifecycle-tracking`.

## Historical Context

This is not a new class of problem. [Issue 002](/data1/huangzhe/code/houmao/context/issues/known/issue-002-shadow-turn-monitor-imperative-timing.md) already established why timer-driven TUI lifecycle tracking must not use a hand-rolled mutable reducer: it produces false completion, fragile stall timing, and drift as timing rules evolve.

CAO runtime was corrected by the archived [rx-shadow-turn-monitor](/data1/huangzhe/code/houmao/openspec/changes/archive/2026-03-18-rx-shadow-turn-monitor/design.md) change. `houmao-server` later adopted the same lifecycle vocabulary (`candidate_complete`, `completed`, `stalled`) in its continuous tracker, but it did not adopt the same ReactiveX timing model or the same post-submit anchor model.

## Summary

`houmao-server` currently combines two incompatible ideas:

1. **CAO-style turn-relative lifecycle states**
2. **continuous submit-blind background polling**

It then reduces those states with an imperative in-memory reducer in [src/houmao/server/tui/tracking.py](/data1/huangzhe/code/houmao/src/houmao/server/tui/tracking.py).

That creates two related failures:

### A. Imperative timer semantics return the old bug class

The server reducer uses mutable fields and manual elapsed-time tracking for:
- unknown-to-stalled timing,
- candidate-complete timing,
- ready-baseline tracking,
- projection-change evidence.

This is the same design shape that previously failed in CAO before the Rx rewrite.

### B. Background watch is claiming turn-relative completion without a turn anchor

CAO runtime monitors a turn after a known submit event and a captured baseline. `houmao-server` background watch does not own that boundary for every observed session. It only sees periodic snapshots of tmux state.

Without a real turn anchor, the server is forced to guess whether a ready-to-ready change means:
- a real completed prompt turn,
- startup UI settling,
- prompt chrome or tip-banner churn,
- or unrelated operator activity that happened outside Houmao-owned control paths.

That guess is not reliable enough to support authoritative `candidate_complete` and `completed`.

## Concrete Failure Mode

During interactive testing of the new dual shadow-watch demo, the server tracker showed both failure directions:

### A. Missed or weakly justified completion

A visible prompt turn could complete in tmux without the server seeing an intermediate `working` observation. The imperative reducer then had to guess from later ready surfaces whether the turn had completed.

### B. False completion from startup or prompt-surface churn

After heuristic patching, Claude and Codex sessions could transition to `candidate_complete` and `completed` on startup or idle prompt changes, before any new operator prompt was intentionally submitted through the demo flow.

The immediate trigger was ready-surface churn such as:
- welcome or tip-banner changes,
- prompt hint changes,
- startup chrome settling.

But the deeper problem is architectural: the tracker is using background-ready surface changes as if they were post-submit evidence.

## Root Cause

Two design mistakes compound each other:

### A. Timer-based lifecycle semantics were reimplemented imperatively

The server reducer reintroduced mutable timestamp and flag bookkeeping for exactly the kind of overtime/sliding-window semantics that the CAO runtime moved to ReactiveX to avoid.

### B. Continuous watch and turn-relative completion were not separated

The server contract imported turn-oriented completion states into a continuous watch system without requiring a concrete turn anchor. That makes "completion" under-specified in the background-watch case.

## Affected Code

- [src/houmao/server/tui/tracking.py](/data1/huangzhe/code/houmao/src/houmao/server/tui/tracking.py) — imperative lifecycle reducer and timing fields
- [src/houmao/server/service.py](/data1/huangzhe/code/houmao/src/houmao/server/service.py) — worker-owned observation flow, baseline capture, and state publication
- [openspec/specs/official-tui-state-tracking/spec.md](/data1/huangzhe/code/houmao/openspec/specs/official-tui-state-tracking/spec.md) — current server contract imported lifecycle richness without importing the Rx implementation constraint
- consumers such as the server-backed dual shadow-watch demo

## Fix Direction

### A. Restore ReactiveX for timer-driven lifecycle semantics

Use ReactiveX operators for:
- stalled timing,
- stalled recovery,
- completion debounce,
- post-submit evidence accumulation,
- deterministic scheduler-based tests.

The server should keep imperative polling ownership, but feed ordered observations into Rx lifecycle streams rather than another mutable timer reducer.

### B. Split continuous watch from turn-anchored completion

The server should expose two truths:

- **continuous watch lifecycle**
  - readiness, blocked, failed, unknown, stalled, visible-state stability
- **turn-anchored completion lifecycle**
  - `in_progress`, `candidate_complete`, `completed` only when a real server-owned anchor exists

If no anchor exists, background watch must not manufacture authoritative completion from ready-surface churn alone.

### C. Expose lifecycle authority explicitly on the public state contract

Tracked-state payloads should tell clients whether completion is:
- `turn_anchored`, or
- `unanchored_background`

so that dashboards and automation do not over-trust background-ready churn as a real completed turn.

## Connections

- Builds directly on [Issue 002](/data1/huangzhe/code/houmao/context/issues/known/issue-002-shadow-turn-monitor-imperative-timing.md): same timer-semantics failure class, different subsystem
- Aligns `houmao-server` with the archived [rx-shadow-turn-monitor](/data1/huangzhe/code/houmao/openspec/changes/archive/2026-03-18-rx-shadow-turn-monitor/design.md) design instead of diverging from it
- Clarifies the contract boundary for [official-tui-state-tracking](/data1/huangzhe/code/houmao/openspec/specs/official-tui-state-tracking/spec.md)
- Prevents the overlapping [add-shadow-watch-state-stability-window](/data1/huangzhe/code/houmao/openspec/changes/add-shadow-watch-state-stability-window/design.md) work from becoming a second lifecycle authority
