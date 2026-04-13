## Context

The live TUI tracker already has two related concepts:

- generic visible-state stability, currently based on a published tracked-state signature, and
- stale-active recovery, currently a narrow 5-second correction for unanchored sessions that are submit-ready but stuck active from limited stale `status_row` evidence.

That narrow recovery intentionally avoids correcting stronger active evidence or active server-owned turn anchors. The new problem is a final safety valve for detector false positives that still block gateway prompt input after the TUI has visibly stopped changing and independent readiness evidence says the prompt can accept input.

## Goals / Non-Goals

**Goals:**

- Add a final recovery tier that clears a stuck active TUI posture after a default 20-second stable unchanged window.
- Require independent prompt-ready evidence before recovering, so static real work is not treated as ready only because it is quiet.
- Recover both `turn.phase` and `surface.ready_posture` when needed, because gateway prompt admission checks both fields.
- Avoid manufacturing `last_turn.result=success`.
- Clear or expire active turn-anchor authority when final recovery fires, so old completion monitoring does not continue to block or mutate the reopened prompt.
- Expose the new timing through the existing gateway TUI timing configuration path.

**Non-Goals:**

- Do not make a generic "active for 20 seconds means ready" rule.
- Do not bypass gateway prompt-readiness checks or mail-notifier policy.
- Do not change the public tracked-state schema unless existing timing metadata needs to include the new value.
- Do not remove the existing 5-second narrow stale-active recovery path.

## Decisions

1. Add a second recovery tier instead of broadening the existing 5-second stale-active recovery.

   The existing path is intentionally fast and narrow. It only handles a known stale-active shape. A broader rule needs a longer default window and stronger evidence because it may override active evidence from arbitrary detector reasons.

   Alternative considered: expand the existing stale-active candidate to allow all active reasons. Rejected because 5 seconds is too aggressive for a broad fallback and would mask real long-running work.

2. Define final recovery around stable raw surface plus stable published state.

   The fallback should use the selected profile's current raw surface signature when available, not only the reduced published state. A detector can keep publishing the same active state while raw text continues to change; that should reset the final recovery window. The final candidate signature should also include parser readiness evidence and public state fields so changes in either evidence source cancel and restart the timer.

   Alternative considered: use only `HoumaoStabilityMetadata.stable_for_seconds`. Rejected because that metadata is derived from the published response signature and may not capture every raw surface repaint or scrollback change.

3. Require independent prompt-ready evidence but do not require `surface.ready_posture=yes`.

   The failure mode is that `surface.ready_posture` may be `no` because the detector still believes active evidence exists. Final recovery should therefore require `parsed_surface.business_state=idle`, `parsed_surface.input_mode=freeform`, `surface.accepting_input=yes`, and `surface.editing_input=no`, while allowing `surface.ready_posture=no` to be corrected.

   Alternative considered: require `surface.ready_posture=yes` like the existing stale-active recovery path. Rejected because it would not solve the intended false-positive active case.

4. Clear active turn-anchor authority when final recovery fires.

   If a server-owned prompt anchor remains active after the final fallback reopens input, later completion snapshots can still report against an old turn and confuse subsequent prompt control. Final recovery should expire that anchor as stale and dispose completion monitoring without producing a success result.

   Alternative considered: leave anchors intact and only publish `turn.phase=ready`. Rejected because the internal authority state would disagree with the public readiness correction.

5. Expose a new positive timing field.

   Add `final_stable_active_recovery_seconds` with default `20.0` to the existing gateway TUI timing model and override surfaces. This keeps operator tuning consistent with watch poll, completion stability, unknown-to-stalled, and narrow stale-active recovery timings.

## Risks / Trade-offs

- [Risk] A genuinely active tool may remain visually static and parser-idle for 20 seconds. -> Mitigation: require accepting input, non-editing posture, idle/freeform parser evidence, and raw-surface stability; keep the timeout configurable.
- [Risk] Raw-surface signature plumbing is not currently part of the public tracker snapshot. -> Mitigation: keep it internal to the recovery candidate and avoid changing public state unless necessary.
- [Risk] Clearing a turn anchor can hide a late completion for the old turn. -> Mitigation: only fire after the final recovery window and do not record success; emit debug evidence that the anchor expired through recovery.
- [Risk] Adding another timing field increases CLI/API surface. -> Mitigation: reuse existing validation, persistence, and override patterns for gateway TUI tracking timings.
