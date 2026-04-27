## 1. Implement parser-independent rendered-surface signature

- [x] 1.1 Add a `_rendered_surface_signature(output_text: str | None) -> str | None` helper in `src/houmao/server/tui/tracking.py` that ANSI-strips the input (reuse `ANSI_ESCAPE_RE` from `src/houmao/shared_tui_tracking/surface.py` via import), per-line right-trims, and returns a `sha256` hex of the joined normalized text. Return `None` when `output_text` is `None`.
- [x] 1.2 Delete the existing `_raw_surface_signature` helper and any tests asserting against it.
- [x] 1.3 Confirm `ANSI_ESCAPE_RE` is exported from `houmao.shared_tui_tracking.surface` (it is, as `ANSI_ESCAPE_RE`); no shared-tui-tracking changes required.

## 2. Redesign final stable-active recovery candidate

- [x] 2.1 Rewrite `_build_final_stable_active_recovery_candidate` in `src/houmao/server/tui/tracking.py` to take only `turn: HoumaoTrackedTurn` and `rendered_surface_signature: str | None`. Return `None` when `turn.phase != "active"` or `rendered_surface_signature is None`. Otherwise return a `_FinalStableActiveRecoveryCandidate` whose `.signature` is the rendered-surface signature and whose `.active_reasons` is `()`.
- [x] 2.2 Remove all parser-derived gates from the candidate builder: `parsed_surface is None or diagnostics.availability != "available"`, `_is_submit_ready(parsed_surface)`, `surface.accepting_input != "yes" or surface.editing_input != "no"`, and `"stream_retry_status" in active_reasons`.
- [x] 2.3 Update the call site in `record_cycle` (currently around `tracking.py` L689–696) to pass the new keyword arguments and to compute the signature via `_rendered_surface_signature(output_text)`.
- [x] 2.4 Verify `_update_final_stable_active_recovery_locked`, `_handle_final_stable_active_recovery_timer`, and `_cancel_final_stable_active_recovery_locked` need no behavior changes; the candidate signature comparison still drives timer arming, settling, and cancellation correctly.

## 3. Adjust recovery debug payload

- [x] 3.1 Confirm the `tracker-recovery` debug stream's `final_stable_active_recovery_armed` and `final_stable_active_recovery_applied` events still emit a meaningful `recovery_signature_sha1` (now sourced from the rendered-surface signature) and an empty `active_reasons` list.
- [x] 3.2 If any debug consumer parses the event payload by field name, ensure the empty `active_reasons` field does not break it.

## 4. Update existing unit tests

- [x] 4.1 Update tests in `tests/unit/server/test_tui_parser_and_tracking.py` and `tests/unit/server/test_tracking_debug.py` that build recovery fixtures with parser-derived inputs. The existing recovery tests should still pass under the new contract because they exercise scenarios where the redesigned recovery should also fire.
- [x] 4.2 Remove or rewrite any test that asserted recovery does *not* fire while parser readiness is ambiguous (e.g., scenarios derived from the removed "Stable promptable error surfaces" requirement). Under the new contract, recovery should fire under those conditions once the rendered surface is stable for the configured window.
- [x] 4.3 Remove or rewrite any test that depended on `_raw_surface_signature` directly; replace with assertions against `_rendered_surface_signature` where the underlying intent is to test signature stability.

## 5. Add regression tests for the redesigned contract

- [x] 5.1 Add a test that reproduces the issue #51 shape: tracker is currently publishing `turn.phase=active` because the activity detector keeps returning non-empty `active_reasons` on every snapshot, but the rendered-surface signature is constant for the configured window. Assert that final stable-active recovery fires and clears phase to `ready` after the window elapses.
- [x] 5.2 Add a test that the recovery does not consult `parsed_surface`, `tracker_state.active_reasons`, or `tracker_state.stability_signature`: provide deliberately-broken parser output (e.g., `parsed_surface.business_state="working"`) but a stable rendered surface, and assert recovery still fires.
- [x] 5.3 Add a test that ANSI styling differences between cycles do not flip the rendered-surface signature: feed two captures whose only differences are ANSI color codes, and assert the helper returns the same hash.
- [x] 5.4 Add a test that trailing-whitespace differences between cycles do not flip the rendered-surface signature: feed two captures whose only differences are trailing spaces per line, and assert the helper returns the same hash.
- [x] 5.5 Add a test that any visible text change does flip the rendered-surface signature: feed two captures differing by one printable character, and assert the helper returns different hashes.
- [x] 5.6 Add a test that confirms the recovery still expires server-owned turn-anchor authority when it fires and does not manufacture `last_turn.result=success`.

## 6. Validate change against spec and run quality gates

- [x] 6.1 Run `pixi run openspec validate redesign-tui-stable-active-recovery --strict` and resolve any structural errors.
- [x] 6.2 Run `pixi run format`, `pixi run lint`, and `pixi run typecheck` and resolve any failures introduced by the implementation.
- [x] 6.3 Run `pixi run test-runtime` (covers `tests/unit/agents` and `tests/unit/cao`) plus the targeted suites `python -m pytest tests/unit/server/test_tui_parser_and_tracking.py tests/unit/server/test_tracking_debug.py -v`.
