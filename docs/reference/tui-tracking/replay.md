# TUI Tracking Replay Engine

Modules: `src/houmao/shared_tui_tracking/reducer.py` and `src/houmao/shared_tui_tracking/session.py`

## Overview

The replay engine converts raw TUI pane observations into structured tracked state. It serves two modes of operation: **offline replay** for analysis and validation of detector behavior against recorded sessions, and **live tracking** for real-time state inference during active agent sessions.

## StreamStateReducer

The `StreamStateReducer` processes a stream of `RecordedObservation` samples through a detector to produce `TrackedTimelineState` rows. It is the core state machine that:

1. Feeds each observation's output text and parsed surface context to the detector's `detect()` method.
2. Accumulates temporal frames via `build_temporal_frame()` within the detector's configured temporal window.
3. Derives temporal hints from the recent frame window via `derive_temporal_hints()`.
4. Combines single-frame signals with temporal hints to produce a `TrackedTimelineState` for each observation.
5. Tracks surface signature stability across observations, computing `stable`, `stable_for_seconds`, and `stable_since_seconds`.

The reducer is stateful — it maintains the sliding window of temporal frames and the current stability tracking state across observations.

## replay_timeline()

Replays a recorded observation stream through the state machine, producing a full timeline of tracked state transitions.

```python
def replay_timeline(
    observations: Sequence[RecordedObservation],
    detector: BaseTrackedTurnSignalDetector,
) -> list[TrackedTimelineState]:
    ...
```

This function is the primary entry point for offline analysis. Given a sequence of recorded observations and a detector, it produces the complete timeline that the detector would have generated if it had been running live during the session. This is used for:

- **Detector development**: Validating that a new or modified detector produces correct state transitions against known-good recorded sessions.
- **Regression testing**: Ensuring detector updates do not change behavior on previously recorded sessions.
- **Diagnostics**: Replaying a problematic session to understand what the detector saw and why it reached a particular state.

## TuiTrackerSession

Manages a live tracking session. Holds detector state, processes incoming observations as they arrive, and emits tracked state snapshots and transitions in real time.

Unlike the offline `replay_timeline()` path, `TuiTrackerSession` is designed for incremental operation — each new observation is processed immediately, and the resulting state snapshot is available for downstream consumers (such as lifecycle pipelines) without waiting for the full session to complete.

The session manages:

- Detector selection and initialization (via the `DetectorProfileRegistry`).
- Incremental feeding of observations to the `StreamStateReducer`.
- Emission of `TrackedStateSnapshot` instances to observers.

## RecordedObservation

Frozen dataclass representing a single recorded observation from a TUI pane capture.

| Field | Type | Description |
|---|---|---|
| `sample_id` | `str` | Unique identifier for this observation sample |
| `elapsed_seconds` | `float` | Time elapsed since the start of the recording session |
| `ts_utc` | `str` | UTC timestamp of the observation |
| `output_text` | `str` | Raw text content captured from the TUI pane |
| `runtime` | `RuntimeObservation \| None` | Optional runtime-level observation (process state, transport state) |
| `surface_context` | `ParsedSurfaceContext \| None` | Optional pre-parsed surface context, if available from the capture pipeline |

## TrackedTimelineState

Frozen dataclass representing one row in the tracked state timeline produced by the replay engine.

| Field | Type | Description |
|---|---|---|
| `sample_id` | `str` | Identifier of the source observation |
| `elapsed_seconds` | `float` | Time elapsed since session start |
| `ts_utc` | `str` | UTC timestamp |
| `diagnostics_availability` | `TrackedDiagnosticsAvailability` | Whether diagnostics could be extracted from this observation |
| `surface_accepting_input` | `Tristate` | Whether the surface is accepting input |
| `surface_editing_input` | `Tristate` | Whether the surface is in input-editing mode |
| `surface_ready_posture` | `Tristate` | Whether the surface is in a ready/idle posture |
| `turn_phase` | `TurnPhase` | Current turn phase at this point in the timeline |
| `last_turn_result` | `TrackedLastTurnResult` | Result of the most recently completed turn |
| `last_turn_source` | `TrackedLastTurnSource` | How the most recent turn was initiated |
| `detector_name` | `str` | Detector that produced this state |
| `detector_version` | `str` | Detector version |
