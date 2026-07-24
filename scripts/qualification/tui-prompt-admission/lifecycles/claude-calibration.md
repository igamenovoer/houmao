# Claude Calibration Notes

## Initial Patterns

- **ready**: native prompt glyph `❯` at the start of a line.
- **active**: `Working (`, `Running tool/command`, or interrupt markers.
- **pending**: placeholder regex for any visible queued-message signature.
- **pending_count**: `count_markers` over `↳`-style queued-message bullets.

## Count-Targeted Manifests

| Manifest | Target queue depth | Long prompt |
|---|---|---|
| `claude-1-pending.json` | 1 | no |
| `claude-2-pending.json` | 2 | no |
| `claude-3-pending-long.json` | 3 | yes (~482 chars) |

The `3-pending-long` manifest marks the final `wait_for_pattern: pending` step as `non_fatal_on_timeout`. If Claude Code caps its queue below three, the run taints with `pending_count_capped_at_N_target_3` and still freezes the evidence.

## Calibration Status

Not yet calibrated. Run a capture and update this file with the observed Claude Code version and the exact pending-signature text.

## Procedure

1. `pixi run tui-pending-state-capture --provider claude --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/claude-1-pending.json --run-root tmp/houmao-dev-tui-testing/claude-cal-1`
2. `pixi run tui-pending-state-capture --provider claude --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/claude-2-pending.json --run-root tmp/houmao-dev-tui-testing/claude-cal-2`
3. `pixi run tui-pending-state-capture --provider claude --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/claude-3-pending-long.json --run-root tmp/houmao-dev-tui-testing/claude-cal-3`
4. Inspect each `<run-root>/claude-attempt-001/review/labels.mp4`.
5. Record the version from each `<run-root>/claude-attempt-001/capture/run-summary.json`.
6. Update the matching `lifecycles/claude-*-pending*.json` `calibrated_version` and `pending.regex`.
7. Tune `pending_count_patterns.marker_regex` to match the exact queued-message bullet glyph.
8. Re-run and verify each pending span is labeled with the correct `pending_count`.
