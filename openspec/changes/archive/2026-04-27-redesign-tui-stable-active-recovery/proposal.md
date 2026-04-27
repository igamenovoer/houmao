## Why

Long-running gateway-managed sessions can latch `turn.phase=active` indefinitely after a turn really ends, silently blocking the mail-notifier (issue #51). The existing final stable-active recovery is supposed to be the safety net that breaks such latches, but its candidate signature mixes raw tmux bytes with parser-derived state, and its readiness gate consults the same activity-detection pipeline whose false positives the recovery is meant to correct. As a result, recovery either never settles (raw signature flips on byte-level noise) or fails to even build a candidate (parser gate excludes the reading the recovery exists to repair). The recovery must instead judge purely from raw rendered surface stability so that no parser fault can disable it.

## What Changes

- **BREAKING** Final stable-active recovery uses a parser-independent rendered-surface stability signature only. The recovery no longer reads `parsed_surface`, `tracker_state.active_reasons`, `tracker_state.stability_signature`, or any other activity-detection output when deciding whether to settle.
- **BREAKING** Final stable-active recovery's readiness gate is reduced to two preconditions: `turn.phase == "active"` (something to recover) and a rendered-surface stability signature is observable (input is available). All other parser-derived gates (`business_state`, `input_mode`, `accepting_input`, `editing_input`, blocking overlay checks, `stream_retry_status` exclusion, `surface.ready_posture`, etc.) are removed from the recovery contract.
- Define one rendered-surface stability signature derived from ANSI-stripped, per-line right-trimmed tmux capture text — independent of detector/profile interpretation — used solely by recovery candidate keying.
- When recovery fires, the tracker SHALL clear `turn.phase` to `ready` and expire any stale server-owned turn-anchor authority, regardless of what the activity-detection pipeline currently reports as "the TUI is busy".
- Stale-active fast-path recovery is left in place but is no longer a prerequisite for late recovery to function; it remains as an opportunistic 5 s shortcut for the narrow `active_reasons ⊆ {status_row}` shape.
- Recovery candidate signatures and gate decisions are emitted on the tracker debug stream so the new behavior is observable from `houmao-server` debug output without source-level inspection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-tui-state-tracking`: redefine the final stable-active recovery contract so it depends only on `turn.phase=active` plus rendered-surface stability, removing every parser-derived precondition and replacing the mixed raw-plus-tracked-state signature with one rendered-surface signature.

## Impact

- Affected runtime tracker code in `src/houmao/server/tui/tracking.py` (`_build_final_stable_active_recovery_candidate`, `_update_final_stable_active_recovery_locked`, `_raw_surface_signature`, the call site at `record_cycle`, and the recovery-applied branch).
- Affected ANSI-scrubbing helper sharing in `src/houmao/shared_tui_tracking/surface.py` (the new rendered-surface signature reuses `ANSI_ESCAPE_RE`).
- Affected unit tests under `tests/unit/server/tui/` covering recovery candidate building and timer settlement, including new tests where the parser misclassifies the surface yet recovery still fires.
- Affected debug payload schema for `tracker-recovery` events emitted by the tracker.
- No changes to gateway timing-configuration plumbing, mail-notifier deferral logic, or the mail-notifier surface, so existing `--gateway-tui-final-stable-active-recovery-seconds` knobs and `agents state` projections continue to work unchanged.
