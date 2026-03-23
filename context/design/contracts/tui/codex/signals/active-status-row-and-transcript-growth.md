# Active Status Row And Transcript Growth

**Verified CLI Version:** `codex-cli 0.116.0` for capture-backed evidence, within the maintained `0.116.x` detector family

## Chosen Signals

The current Codex signal stack uses two active-turn signals:

- primary active signal: the latest-turn active status row
- fallback temporal active signal: meaningful recent latest-turn transcript growth

Typical status-row example:

- `gpt-5.4 xhigh · 98% left · /data1/...`

## Why These Signals Are Chosen

### Active status row

- It is the clearest visible Codex current-turn activity cue when present.
- It is prompt-local and turns off naturally when the surface becomes interrupted-ready or fully ready.
- It avoids depending on older transcript text such as earlier response bullets.

### Temporal transcript growth

- Codex can still be meaningfully active before the status row has stabilized or while the visible latest-turn region is still expanding.
- Recent growth lets the tracker preserve activity in sparse but still clearly in-flight latest-turn windows.
- The growth rule is bounded by time and minimum size so it does not overfit tiny edits or stale history.

## Why The Alternatives Were Rejected

### Reject: status row only

Why rejected:

- it misses active spans where the latest-turn transcript is still growing but the status row has not yet stabilized visibly

Observed failure mode:

- without temporal growth inference, some early active spans collapse back to ready

### Reject: any latest-turn text change counts as active

Why rejected:

- tiny or widely separated changes are too noisy
- Codex needs minimum growth thresholds and a bounded contiguous time window

Observed safeguard:

- sparse or small growth should not infer activity

## Evidence

### Real capture evidence

From `capture-20260323T115828Z`:

- active phases before each interruption and before the final success show the Codex status row during in-flight turns

### Tests that lock this in

- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_temporal_growth_marks_turn_active`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_sparse_window_does_not_infer_active`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_steer_handoff_surface_stays_active`

## Current Use

Current implementation points:

- `src/houmao/shared_tui_tracking/apps/codex_tui/signals/activity.py`
- `src/houmao/shared_tui_tracking/apps/codex_tui/profile.py`

Current rule shape:

- latest-turn status row creates `active_reasons=("status_row", ...)`
- meaningful recent growth creates temporal hints with `active_reasons=("transcript_growth",)`
- active evidence is suppressed by stronger conflicting surfaces such as blocking overlays or current interrupted-ready state
