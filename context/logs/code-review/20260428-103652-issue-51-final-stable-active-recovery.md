# Code Review: Issue #51 Final Stable-Active Recovery Fix

Reviewed commit: `0b22bae4 fix: parser-independent final stable-active recovery (#51)`

Reviewed scope:

- `src/houmao/server/tui/tracking.py`
- `tests/unit/server/test_tui_parser_and_tracking.py`
- `openspec/specs/official-tui-state-tracking/spec.md`
- Archived change context under `openspec/changes/archive/2026-04-27-redesign-tui-stable-active-recovery/`

## Verdict

The fix very likely addresses the core failure mode from upstream issue #51: final stable-active recovery no longer keys on parser-derived state or active reasons, and it no longer lets those same parser signals veto recovery. For the exact modeled shape where the parser keeps reporting `turn.phase="active"` / `active_reasons=("tool_cell",)` while the rendered terminal surface is unchanged at an idle prompt, the new code recovers to `ready` and unblocks prompt-ready consumers.

The fix is not a complete proof that every live #51-style incident will recover. It deliberately trades parser safety checks for a rendered-surface watchdog. That is a good direction for this bug, but it introduces a broader false-ready risk and still depends on the rendered capture being stable under the exact live terminal bytes Houmao receives.

## Findings

### Medium: Final recovery can mark a genuinely active but visually still TUI as ready

`_build_final_stable_active_recovery_candidate()` now only checks `turn.phase == "active"` and a non-null rendered-surface signature before arming recovery. It does not consult `parsed_surface`, `surface.accepting_input`, `surface.editing_input`, `tracker_state.active_reasons`, or any process-level execution evidence. Once the same rendered text persists through the configured window, `_update_final_stable_active_recovery_locked()` returns recovered and the publish path forces `surface.ready_posture="yes"` / `turn.phase="ready"`.

References:

- `src/houmao/server/tui/tracking.py:690`
- `src/houmao/server/tui/tracking.py:699`
- `src/houmao/server/tui/tracking.py:1940`
- `openspec/specs/official-tui-state-tracking/spec.md:484`
- `openspec/specs/official-tui-state-tracking/spec.md:488`

This is intentional per the new spec, but it is the main behavioral cost. If Codex or Claude is genuinely doing work but renders no visible changes for 20 seconds, the tracker can publish `ready`. For gateway mail-notifier and prompt control, that can permit prompt injection into an actually busy TUI. The existing tests even codify one version of this broadened behavior with retry status: `test_live_session_tracker_retry_status_does_not_block_final_recovery()` recovers a stable `"Reconnecting to model stream"` surface after the final window.

Reference:

- `tests/unit/server/test_tui_parser_and_tracking.py:455`

Recommendation: keep the parser-independent recovery, but add one or both of:

- A regression test for an active surface whose visible status row changes over time, proving recovery does not fire while normal active progress ticks.
- A narrower denylist or longer dwell for known active, non-promptable rendered states such as stream retry / reconnect status if live behavior shows those can remain text-stable while still unsafe for prompt delivery.

### Medium: The regression test does not prove recovery survives the original live byte jitter

The issue analysis suspected the old recovery timer was re-arming because raw tmux bytes changed on an otherwise idle screen. The new `_rendered_surface_signature()` strips CSI ANSI escape sequences, replaces NBSP, and right-trims each line. That fixes ANSI styling and trailing padding jitter, but it still flips on any visible footer/status text change and on non-CSI escape/control noise that `ANSI_ESCAPE_RE` does not remove.

References:

- `src/houmao/server/tui/tracking.py:1966`
- `src/houmao/shared_tui_tracking/surface.py:10`
- `tests/unit/server/test_tui_parser_and_tracking.py:1645`

The issue #51 regression test uses a synthetic, fully stable `stable_surface` string rather than a pair of real captured panes from the stuck live agent. So the test proves the new parser-independent gate works, but it does not prove the new signature normalizes the actual byte-level drift that caused the live timer to churn.

Reference:

- `tests/unit/server/test_tui_parser_and_tracking.py:1579`

Recommendation: add a fixture pair from the original live stuck agent or from a reproduced idle Codex screen where old raw signatures differ but the screen should be considered stable. Assert `_rendered_surface_signature()` returns the same value for that pair. If it does not, consider normalizing additional invisible sequences or selected idle footer fields.

### Low: Developer docs still describe the old parser-evidence recovery contract

The main OpenSpec spec has been updated to the parser-independent contract, but developer docs still describe final stable-active recovery as requiring idle/freeform/input-ready parser evidence. That is now stale and can mislead future debugging.

References:

- `docs/developer/houmao-server/state-reference.md:178`
- `docs/developer/houmao-server/state-reference.md:225`
- `openspec/specs/official-tui-state-tracking/spec.md:488`

Recommendation: update the state-reference and state-tracking docs to say final stable-active recovery is keyed only by `turn.phase=active` plus rendered-surface stability, and that prompt-readiness parser evidence is only part of the fast stale-active path.

### Low: Recovery debug payload loses active-reason context

The final recovery candidate now always stores `active_reasons=()`, and the `final_stable_active_recovery_armed` / `applied` debug payloads continue emitting `active_reasons`, but it is always empty. That is compatible structurally, but less useful operationally: when recovery fires, the debug event no longer tells the operator which parser reason was being overridden.

References:

- `src/houmao/server/tui/tracking.py:1067`
- `src/houmao/server/tui/tracking.py:725`
- `src/houmao/server/tui/tracking.py:1960`

Recommendation: keep the recovery decision parser-independent, but consider logging a non-keying diagnostic snapshot beside the rendered signature, for example `overridden_active_reasons`, so operators can distinguish `tool_cell`, `transcript_growth`, `stream_retry_status`, or other detector causes without letting them affect the timer.

## Does It Truly Fix Issue #51?

For the modeled core: yes.

The issue had this essential shape:

```text
TUI rendered state: idle prompt
tracker phase:      active
active_turn_id:     tui-anchor:<agent_id>
mail notifier:      skips because turn.phase != ready
recovery:           never fires because candidate keeps re-arming
```

The fix changes the recovery path to this:

```text
current turn.phase == active
        |
        v
hash rendered tmux text after ANSI stripping / right-trimming
        |
        v
same hash for final_stable_active_recovery_seconds
        |
        v
publish turn.phase=ready and expire stale anchor
```

That directly removes the two bad couplings in the old design:

- Parser-derived active reasons no longer keep recovery from building a candidate.
- Parser-derived state no longer participates in the candidate signature.

The new `test_live_session_tracker_final_recovery_fires_under_persistent_tool_cell_active()` specifically captures the issue's persistent parser-active / stable idle surface shape and passes.

Reference:

- `tests/unit/server/test_tui_parser_and_tracking.py:1579`

The remaining uncertainty is whether the live terminal capture that originally churned will produce a stable `_rendered_surface_signature()`. The synthetic test does not establish that.

## Pros

- Breaks the circular dependency that made recovery depend on the same detector pipeline it was meant to repair.
- Keeps the recovery side effect conservative with respect to completion: it clears readiness but does not manufacture `last_turn.result=success`.
- Expires stale server-owned turn anchors when final recovery fires, which aligns the projected `tui-anchor:<agent_id>` state with recovered readiness.
- Reuses the existing ReactiveX timer machinery rather than introducing a second timeout mechanism.
- Adds focused regression tests for parser-active/stable-surface recovery, ANSI styling jitter, trailing whitespace jitter, visible text changes, `None` input, and anchor expiry.

## Cons / Tradeoffs

- Broader false-ready risk for real active turns whose rendered surface is static longer than the final recovery window.
- Still sensitive to visible idle-footer churn, terminal-width reflow, scrollback trimming, and non-CSI invisible escape/control sequences.
- Does not address the mail-notifier observability gap from the issue, such as `last_skip_reason`.
- Debug payloads no longer expose the active reason that recovery overrode.
- Some developer docs still describe the pre-#51 parser-gated recovery behavior.

## Test Evidence

Targeted tests:

```bash
pixi run pytest tests/unit/server/test_tui_parser_and_tracking.py -k 'final_recovery or rendered_surface_signature or retry_status'
```

Result: `11 passed, 18 deselected`.

OpenSpec validation for the changed capability:

```bash
pixi run openspec validate official-tui-state-tracking --strict
```

Result: valid.

Full OpenSpec validation:

```bash
pixi run openspec validate --all --strict
```

Result: `163 passed, 1 failed`. The failure is unrelated to this fix: `spec/houmao-agent-loop-pairwise-v3-skill` has `requirements.3.text: Requirement must contain SHALL or MUST keyword`.

## References

- Upstream issue: `https://github.com/igamenovoer/houmao/issues/51`
- Local commit: `0b22bae4 fix: parser-independent final stable-active recovery (#51)`
- Archived OpenSpec change: `openspec/changes/archive/2026-04-27-redesign-tui-stable-active-recovery/`
- Local review instruction: `magic-context/instructions/review-code-by-mem.md`

