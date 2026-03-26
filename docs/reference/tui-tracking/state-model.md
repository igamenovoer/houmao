# TUI Tracking State Model

Module: `src/houmao/shared_tui_tracking/` — Neutral tracked-TUI models shared by official/runtime adapters.

## Core Type Aliases

All type aliases are `Literal` unions used throughout the tracking subsystem.

### Tristate

```python
Tristate = Literal["yes", "no", "unknown"]
```

Three-valued logic for surface observations where the detector may not have enough evidence to commit to a boolean.

### TurnPhase

```python
TurnPhase = Literal["ready", "active", "unknown"]
```

Whether the agent is currently processing a turn or idle.

### TransportState

```python
TransportState = Literal["tmux_up", "tmux_missing", "probe_error"]
```

Reflects the health of the underlying tmux transport used to observe the TUI pane.

### ProcessState

```python
ProcessState = Literal["tui_up", "tui_down", "unsupported_tool", "probe_error", "unknown"]
```

Whether the tracked TUI process is alive and observable.

### ParseStatus

```python
ParseStatus = Literal["parsed", "skipped_tui_down", "unsupported_tool", "transport_unavailable", "probe_error", "parse_error"]
```

Outcome of attempting to parse a raw pane snapshot into structured surface context.

### ReadinessState

```python
ReadinessState = Literal["ready", "waiting", "blocked", "failed", "unknown", "stalled"]
```

Readiness of the agent surface to accept new input.

### CompletionState

```python
CompletionState = Literal["inactive", "in_progress", "candidate_complete", "completed", "waiting", "blocked", "failed", "unknown", "stalled"]
```

Completion status of the current logical turn, from inactive through in-progress to terminal states.

### TrackedDiagnosticsAvailability

```python
TrackedDiagnosticsAvailability = Literal["available", "unavailable", "tui_down", "error", "unknown"]
```

Whether diagnostic information can be extracted from the current surface state.

### TrackedLastTurnResult

```python
TrackedLastTurnResult = Literal["success", "interrupted", "known_failure", "none"]
```

Outcome of the most recently completed turn as inferred by the detector.

### TrackedLastTurnSource

```python
TrackedLastTurnSource = Literal["explicit_input", "surface_inference", "none"]
```

How the last turn was initiated — via explicit prompt submission or inferred from surface state transitions.

## TrackedStateSnapshot

Frozen dataclass representing a point-in-time snapshot of the tracked TUI state. This is the primary output of the tracking state machine.

| Field | Type | Description |
|---|---|---|
| `surface_accepting_input` | `Tristate` | Whether the surface is accepting new input |
| `surface_editing_input` | `Tristate` | Whether the surface is in an input-editing state |
| `surface_ready_posture` | `Tristate` | Whether the surface is in a ready posture (idle prompt visible) |
| `turn_phase` | `TurnPhase` | Current turn phase |
| `last_turn_result` | `TrackedLastTurnResult` | Result of the last completed turn |
| `last_turn_source` | `TrackedLastTurnSource` | How the last turn was initiated |
| `detector_name` | `str` | Name of the detector that produced this snapshot |
| `detector_version` | `str` | Version of the detector |
| `active_reasons` | `tuple[str, ...]` | Human-readable reasons the surface is considered active |
| `notes` | `tuple[str, ...]` | Additional detector notes for diagnostics |
| `stability_signature` | `str` | Hash-like signature of the observable surface state |
| `stable` | `bool` | Whether the surface state has been stable (unchanged) long enough to trust |
| `stable_for_seconds` | `float` | Duration the current signature has been stable |
| `stable_since_seconds` | `float` | Elapsed time at which the current stability window began |
| `observed_at_seconds` | `float` | Elapsed time at which this snapshot was observed |

## DetectedTurnSignals

Frozen dataclass representing the raw signals extracted by a detector from a single observation frame. This is the detector's immediate output before the state machine applies temporal smoothing and stability tracking.

| Field | Type | Description |
|---|---|---|
| `detector_name` | `str` | Name of the detector |
| `detector_version` | `str` | Version of the detector |
| `accepting_input` | `Tristate` | Whether the surface appears to accept input |
| `editing_input` | `Tristate` | Whether the surface appears to be editing input |
| `ready_posture` | `Tristate` | Whether the surface appears idle/ready |
| `prompt_visible` | `bool` | Whether a prompt is visible on the surface |
| `prompt_text` | `str \| None` | Extracted prompt text, if visible |
| `footer_interruptable` | `bool` | Whether the footer indicates the agent can be interrupted |
| `active_evidence` | `bool` | Whether there is evidence the agent is actively processing |
| `active_reasons` | `tuple[str, ...]` | Reasons the surface is considered active |
| `interrupted` | `bool` | Whether the turn appears to have been interrupted |
| `known_failure` | `bool` | Whether a known failure pattern was detected |
| `current_error_present` | `bool` | Whether an error is currently visible on the surface |
| `success_candidate` | `bool` | Whether the surface state is a candidate for successful completion |
| `completion_marker` | `str \| None` | Detected completion marker text |
| `latest_status_line` | `str \| None` | Most recent status line from the surface |
| `ambiguous_interactive_surface` | `bool` | Whether the surface is in an ambiguous interactive state |
| `success_blocked` | `bool` | Whether success detection is blocked by surface ambiguity |
| `surface_signature` | `str` | Signature of the observed surface for stability tracking |
| `notes` | `tuple[str, ...]` | Additional diagnostic notes |
