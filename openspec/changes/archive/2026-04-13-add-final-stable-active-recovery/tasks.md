## 1. Recovery State And Timing

- [x] 1.1 Add `final_stable_active_recovery_seconds` to live tracker timing metadata and gateway TUI timing config with a default of `20.0` seconds.
- [x] 1.2 Plumb the new timing through gateway attach, desired config persistence, runtime CLI args, server attach request models, and project easy launch overrides.
- [x] 1.3 Include the current raw surface signature, when available, in the final stable-active recovery candidate so raw TUI changes reset the final recovery window.

## 2. Final Stable-Active Recovery Logic

- [x] 2.1 Add a final stable-active recovery candidate path for `turn.phase=active` that requires parsed idle/freeform evidence, `surface.accepting_input=yes`, `surface.editing_input=no`, and stable unchanged evidence for the configured window.
- [x] 2.2 Ensure final recovery publishes `turn.phase=ready` and `surface.ready_posture=yes` without setting `last_turn.result=success`.
- [x] 2.3 Expire or clear active server-owned turn anchors and completion monitoring when final recovery fires.
- [x] 2.4 Keep the existing 5-second narrow stale-active recovery behavior unchanged.

## 3. Tests

- [x] 3.1 Add tracker regression coverage for final recovery correcting a stable false-active surface with `surface.ready_posture=no`.
- [x] 3.2 Add tracker regression coverage proving final recovery does not fire when the raw surface signature changes before the timeout.
- [x] 3.3 Add tracker regression coverage proving final recovery does not fire without parsed idle/freeform prompt-ready evidence.
- [x] 3.4 Add tracker regression coverage proving final recovery clears active turn-anchor authority without manufacturing success.
- [x] 3.5 Add gateway timing config, API model, and CLI option tests for `final_stable_active_recovery_seconds`.

## 4. Documentation And Verification

- [x] 4.1 Update relevant state-tracking and gateway timing documentation for the 20-second final stable-active recovery window.
- [x] 4.2 Run focused TUI tracker, gateway timing, server attach, and CLI tests.
- [x] 4.3 Run OpenSpec validation/status for `add-final-stable-active-recovery` and confirm the change is ready to apply/archive after implementation.
