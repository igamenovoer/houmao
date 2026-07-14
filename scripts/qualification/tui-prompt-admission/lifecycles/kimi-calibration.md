# Kimi Calibration Notes

## Initial Patterns

- **ready**: composer footer containing `type a message or use /help`.
- **active**: `Thinking`, `Generating`, `Running tool`, or `Esc to interrupt`.
- **pending**: placeholder regex for any visible queued-message chip.
- **pending_count**: `count_markers` over queued-message bullets.

## Count-Targeted Manifests

| Manifest | Target queue depth | Long prompt |
|---|---|---|
| `kimi-1-pending.json` | 1 | no |
| `kimi-2-pending.json` | 2 | no |
| `kimi-3-pending-long.json` | 3 | yes (~482 chars) |

The `3-pending-long` manifest marks the final `wait_for_pattern: pending` step as `non_fatal_on_timeout`. If Kimi Code caps its queue below three, the run taints with `pending_count_capped_at_N_target_3` and still freezes the evidence.

## Calibration Status

Not yet calibrated. Run a capture and update this file with the observed Kimi Code version and the exact pending-signature text.

## Procedure

1. `pixi run tui-pending-state-capture --provider kimi --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/kimi-1-pending.json --run-root tmp/houmao-dev-testing/kimi-cal-1`
2. `pixi run tui-pending-state-capture --provider kimi --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/kimi-2-pending.json --run-root tmp/houmao-dev-testing/kimi-cal-2`
3. `pixi run tui-pending-state-capture --provider kimi --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/kimi-3-pending-long.json --run-root tmp/houmao-dev-testing/kimi-cal-3`
4. Inspect each `<run-root>/kimi-attempt-001/review/labels.mp4`.
5. Record the version from each `<run-root>/kimi-attempt-001/capture/run-summary.json`.
6. Update the matching `lifecycles/kimi-*-pending*.json` `calibrated_version` and `pending.regex`.
7. Tune `pending_count_patterns.marker_regex` to match the exact queued-message bullet glyph.
8. Re-run and verify each pending span is labeled with the correct `pending_count`.
