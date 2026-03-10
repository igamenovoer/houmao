## Context

`shadow_only` currently treats provider parsers as one-snapshot classifiers and lets runtime `TurnMonitor` reason over ordered snapshots. That split is still correct, but the current runtime logic in `cao_rest.py` only tracks a small set of transition facts: whether the surface is `unknown`, whether post-submit `working` was seen, and whether projected dialog changed after submit.

This misses an important cue already available from tmux polling: whether the visible TUI is still changing. In practice, a session that keeps updating should stay in an active lifecycle path even when parser state briefly looks `ready_for_input` or remains `unknown`, while a session that has stopped changing for a configured quiet window can be treated as settled for readiness, completion, or stall decisions.

The change is cross-cutting enough to justify a design document because it affects runtime lifecycle semantics, configuration shape, diagnostics, tests, and the internal programming model. The repository already ships `reactivex`, which is a good fit for restartable timers and virtual-time tests.

## Contract Documents

This design is paired with provider and runtime contract notes:

- `contracts/claude-state-contracts.md`
- `contracts/codex-state-contracts.md`
- `contracts/turn-monitor-contracts.md`

## Goals / Non-Goals

**Goals:**

- Add restartable quiescence detection to `shadow_only` runtime lifecycle handling.
- Distinguish transport-level TUI change from projected-dialog change so spinner churn and transcript growth can influence decisions differently.
- Keep provider parsers focused on single-snapshot interpretation and preserve the existing parser/runtime ownership boundary.
- Refactor timer-heavy lifecycle logic into a model that is easier to test deterministically with virtual time.
- Preserve existing terminal failure behavior for `unsupported`, `disconnected`, and explicit `waiting_user_answer` states.

**Non-Goals:**

- Changing provider regex/preset detection or moving lifecycle timing into Claude/Codex parsers.
- Reworking `cao_only` parsing mode.
- Exposing raw tmux scrollback as a new primary caller-facing payload field.
- Guaranteeing that every kind of visible TUI churn becomes caller-visible status; some change signals remain runtime-internal.

## Decisions

### 1. Introduce runtime-owned observation and change-signal objects

Each `shadow_only` poll should produce a runtime observation object that carries:

- poll timestamp,
- raw `output?mode=full` text,
- parsed `SurfaceAssessment`,
- parsed `DialogProjection`,
- a transport fingerprint derived from normalized snapshot text, and
- a projection fingerprint derived from `dialog_projection.dialog_text`.

Runtime then derives change signals by comparing each observation to the previous one:

- `transport_changed`: normalized TUI content changed,
- `projection_changed`: projected dialog changed,
- `surface_changed`: parser activity/availability/context changed.

Using normalized snapshot text for the transport fingerprint avoids treating ANSI-only repaint noise as meaningful activity. Keeping a separate projection fingerprint preserves the existing “visible dialog changed” notion without conflating it with spinner churn.

Alternative considered: diff raw tmux output directly inside the parser. Rejected because it would mix transport sequencing into provider-owned single-snapshot parsing and would be overly sensitive to ANSI/control-noise churn.

### 2. Make quiescence a runtime concept with restartable quiet windows

Runtime should treat quiescence as “no new `transport_changed` event has occurred for a configured quiet window.” The quiet-window countdown restarts every time transport changes again.

The runtime policy expands from the current stalled-only timing model to a broader shadow timing policy with at least:

- `ready_quiet_window_seconds`,
- `completion_quiet_window_seconds`,
- `unknown_to_stalled_timeout_seconds`,
- `stalled_is_terminal`.

When quiet-window values are unset, runtime uses positive built-in defaults and surfaces the effective values in diagnostics. `unknown_to_stalled_timeout_seconds` continues to default to 30 seconds.

Quiescence semantics by phase:

- Readiness: runtime submits only when `accepts_input=true` and the surface has been transport-quiet for `ready_quiet_window_seconds`.
- Completion: runtime completes only when `accepts_input=true`, post-submit progress evidence exists, and the surface has been transport-quiet for `completion_quiet_window_seconds`.
- Unknown/stalled: the unknown-to-stalled countdown applies only while the surface remains unknown without intervening transport change; a new transport change resets that countdown.

Alternative considered: continue using immediate `accepts_input` and only add more boolean flags to `_TurnMonitor`. Rejected because restartable timers become difficult to reason about and test once several countdowns interact.

### 3. Use RxPY as the lifecycle timing engine, with the poll loop as the source

The existing polling contract can remain the source of observations, but timing and transitions should move into a reactive pipeline:

1. polling source emits observations,
2. a `scan` stage annotates change signals and carries prior fingerprints,
3. derived streams emit phase-specific quiet-window events and unknown-window events,
4. a reducer consumes observation events plus timer events to produce runtime lifecycle state.

This design keeps network/tmux fetching imperative while moving countdown orchestration into RxPY, where restartable timers naturally map to operators like `distinct_until_changed`, `debounce`, `switch_latest`, `merge`, and `scan`.

The implementation should inject the scheduler so tests can use `reactivex.testing.TestScheduler` instead of `time.sleep()` / `time.monotonic()` patching for the new timing paths.

Alternative considered: preserve the existing imperative monitor and replace `time.monotonic()` comparisons with more timestamps. Rejected because it would keep transition logic scattered across loops and make restartable quiet-window tests harder to express and maintain.

### 4. Keep completion semantics as “progress seen + quiet ready surface”

The existing stale-protection rule remains useful: completion still requires evidence that something happened after submit. Quiescence is an additional guard, not a replacement.

Post-submit progress evidence remains:

- `working` observed after submit, or
- projected dialog changed after submit.

The new completion rule becomes:

- `accepts_input=true`,
- post-submit progress evidence exists, and
- no transport change has occurred for `completion_quiet_window_seconds`.

This prevents early completion when the surface flickers back to a prompt while output is still evolving, while preserving the earlier protection against “idle alone” false positives.

Alternative considered: let a quiet ready surface complete even without post-submit progress evidence. Rejected because it reintroduces the stale-idle bug class that motivated the earlier `TurnMonitor` design.

### 5. Split implementation into a quiescence stream layer and a reducer layer

Rather than continuing to grow `_TurnMonitor` inside `cao_rest.py`, the refactor should introduce two internal pieces:

- a stream/observation module responsible for fingerprints, change detection, and RxPY timer composition,
- a reducer-style monitor responsible for lifecycle state transitions and anomaly emission.

`cao_rest.py` should stay the orchestration boundary that fetches snapshots, wires the stream/reducer together, and shapes caller-facing payloads and errors.

This split reduces the risk that parser details, timing logic, and CAO transport retries become entangled again.

Alternative considered: keep all logic inside `_TurnMonitor` in `cao_rest.py`. Rejected because it would preserve the current concentration of responsibilities and make the reactive pieces harder to isolate in tests.

## Risks / Trade-offs

- [Reactive pipeline complexity] -> Mitigation: keep the poll source imperative, isolate RxPY to quiescence/timer composition, and model transitions through small named observation/timer events.
- [Over-sensitive change detection from benign repaint churn] -> Mitigation: base transport fingerprints on normalized ANSI-stripped text and verify against real Claude/Codex fixtures before finalizing defaults.
- [Longer perceived latency before readiness/completion] -> Mitigation: use small configurable quiet windows, expose effective timing values in diagnostics, and cover fast-return/common-path behavior in tests.
- [Unknown output that changes forever never enters `stalled`] -> Mitigation: rely on the existing outer turn timeout as the hard stop, and document that “active but unclassified” is intentionally different from “stalled.”
- [Incremental migration risk inside `cao_rest.py`] -> Mitigation: stage the refactor behind observation/reducer helpers first, then swap the current loops to use them without changing caller payload shape in the same commit.

## Migration Plan

1. Introduce runtime observation/change-signal dataclasses and a shadow timing policy shape that includes quiet-window settings.
2. Extract the current `_TurnMonitor` logic into a reducer-oriented module and preserve current completion semantics before adding quiescence.
3. Add RxPY-based quiet-window and unknown-window composition around the observation stream, with scheduler injection for tests.
4. Update `shadow_only` readiness and completion loops in `cao_rest.py` to consume reducer outputs instead of direct timestamp bookkeeping.
5. Extend unit tests to cover restartable quiet windows, unknown-with-churn behavior, and completion/readiness settling behavior using virtual time where possible.
6. Update developer/reference docs to describe quiescence as a runtime-owned concept and to document the new timing policy fields.

Rollback strategy: keep the refactor isolated to shadow runtime monitoring so the project can revert to the current imperative `TurnMonitor` if the reactive implementation proves too fragile in practice.

## Open Questions

- Should readiness and completion use separate built-in quiet-window defaults, or should both default to one shared value until real-session telemetry shows they need different tuning?
- Do we want to surface transport-quiescence timing fields in caller-facing `mode_diagnostics`, or keep them strictly as log/debug diagnostics unless a consumer asks for them?
