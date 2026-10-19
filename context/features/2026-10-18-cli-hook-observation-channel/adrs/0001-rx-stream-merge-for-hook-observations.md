# Resolve Hook and TUI Observations in One Rx Stream

Status: accepted

Houmao already resolves TUI and lifecycle state with RxPY: `TuiTrackerSession` uses `Subject` inputs and a tracker state machine, and `lifecycle/rx_lifecycle_kernel.py` uses `scan`, timed operators, and scheduler-driven pipelines. Hook observations must enter the same reactive resolution path as another observable source, rather than a separate imperative merge, so synchronous hook arrivals, TUI snapshots, temporal hints, and timer events share one ordered state machine and one virtual-time test surface.

## Considered Options

- Imperative merge inside `LiveSessionTracker` after each poll cycle. Rejected because it duplicates state resolution, makes ordering depend on poll boundaries, and is harder to test under virtual time.
- A file-only hook sink tailed on a separate loop. Rejected as the primary path because it cannot push a synchronous observation into the stream and introduces a second timing model.
- Gateway-hosted state resolution. Rejected because the gateway may not exist or may attach after the provider starts.

## Consequences

- Hook ingestion is an observable source. The collector validates, stamps, persists, and publishes into a `Subject`; it does not resolve turn state.
- The merge layer is a reactive pipeline. It combines hook observations with TUI detector snapshots and lifecycle observations, then uses `scan` and timed operators to produce the public state.
- Provider events carry `channel_generation` and `sequence`. Cross-source ordering uses monotonic receive time with an explicit deterministic tie-break.
- Qualification can use `TestScheduler` to replay hook and TUI events in virtual time, including out-of-order, stale, duplicate, and orphaned cases.
- The transport is narrowed to an ingress that can push synchronously into the stream: HTTP hooks for ordered events, command hooks for `SessionStart`/`Setup` and fallback delivery.
