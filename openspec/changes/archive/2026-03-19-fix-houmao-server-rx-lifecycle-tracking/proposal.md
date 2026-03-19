## Why

`houmao-server` imported CAO-style lifecycle states such as `candidate_complete`, `completed`, and `stalled`, but it reimplemented the timing logic with an imperative in-memory reducer instead of the ReactiveX approach that previously fixed this exact class of bugs in CAO runtime monitoring. That has already produced the expected failure mode: background watch churn can be misclassified as completion, while fast real turns can still slip between polls when no explicit turn anchor exists.

This needs to be corrected now because the new dual shadow-watch demo and server-owned live-tracking contract are treating `houmao-server` as the authoritative state source. If the server keeps a submit-blind timer state machine, every consumer inherits timing drift and false completion semantics.

## What Changes

- Land the fix in safety-first order: expose lifecycle authority metadata and suppress unanchored completion first, then converge the server and CAO runtime on the shared Rx timing model in the same change.
- Replace timer-driven lifecycle reduction in `houmao-server` with ReactiveX-based observation pipelines instead of hand-rolled timestamp arithmetic and mutable reducer fields.
- Split server lifecycle semantics into continuous watch behavior and anchor-aware turn behavior so `houmao-server` does not claim authoritative request-relative completion when it lacks a turn anchor.
- Add server-owned lifecycle authority metadata in the same tracked-state payload revision that suppresses unanchored `candidate_complete` and `completed`, so consumers can tell whether completion is background-best-effort or submit-anchored.
- Scope turn-anchored completion to one anchored cycle at a time, starting from server-owned terminal input submission in v1 and auto-expiring the anchor on terminal outcome.
- Reuse the CAO runtime Rx design as the timing model while keeping server polling and worker ownership imperative.
- Introduce or extract a shared Rx lifecycle kernel under a neutral `src/houmao/lifecycle/` subtree so CAO runtime and `houmao-server` stop evolving separate timer semantics for the same TUI observation stream.
- Narrow overlapping dashboard work so demo or monitor smoothing remains a consumer concern instead of another competing lifecycle state machine.

## Capabilities

### New Capabilities

### Modified Capabilities
- `official-tui-state-tracking`: time-based lifecycle tracking must use ReactiveX observation semantics, and continuous background watch must distinguish unanchored live state from true turn-anchored completion authority.
- `houmao-server`: public tracked-state behavior must expose the server-owned lifecycle authority clearly enough that clients do not mistake submit-blind background churn for authoritative completion, and v1 turn anchoring starts only from supported server-owned terminal input submission.

## Impact

- `src/houmao/server/tui/tracking.py`, `src/houmao/server/service.py`, and related server state models/routes
- shared lifecycle timing logic around `src/houmao/agents/realm_controller/backends/cao_rx_monitor.py` and a new neutral `src/houmao/lifecycle/` kernel module
- server/client tracked-state payloads and tests
- the shadow-watch demo and the overlapping `add-shadow-watch-state-stability-window` exploration, which should consume the server contract rather than redefine timer semantics
