# Codex Calibration Notes

## Initial Patterns

- **ready**: idle prompt area containing `Find and fix a bug`, `? for shortcuts`, or `Implement {feature}`.
- **active**: `Esc to interrupt`, `Working (`, or `Running tool/command`.
- **pending**: `Messages to be submitted after next tool call`, `messages to be submitted at end of turn`, or `queued follow-up inputs`.
- **pending_count**: `count_markers` over newline-prefixed `↳` bullets.

## Count-Targeted Manifests

| Manifest | Target queue depth | Long prompt |
|---|---|---|
| `codex-1-pending.json` | 1 | no |
| `codex-2-pending.json` | 2 | no |
| `codex-3-pending-long.json` | 3 | yes (~482 chars) |

The `3-pending-long` manifest marks the final `wait_for_pattern: pending` step as `non_fatal_on_timeout`. If Codex CLI caps its queue below three, the run taints with `pending_count_capped_at_N_target_3` and still freezes the evidence.

## Calibration Status

Pending regex is based on the signatures documented in UC-05 and the Codex TUI activity module. Confirm against the exact version used during capture.

## Procedure

1. `pixi run tui-pending-state-capture --provider codex --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/codex-1-pending.json --run-root tmp/houmao-dev-testing/codex-cal-1`
2. `pixi run tui-pending-state-capture --provider codex --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/codex-2-pending.json --run-root tmp/houmao-dev-testing/codex-cal-2`
3. `pixi run tui-pending-state-capture --provider codex --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/codex-3-pending-long.json --run-root tmp/houmao-dev-testing/codex-cal-3`
4. Inspect each `<run-root>/codex-attempt-001/review/labels.mp4`.
5. Record the version from each `<run-root>/codex-attempt-001/capture/run-summary.json`.
6. Update the matching `lifecycles/codex-*-pending*.json` `calibrated_version` and tighten `pending.regex` if needed.
7. Tune `pending_count_patterns.marker_regex` if Codex uses a different glyph for queued messages.
8. Re-run and verify each pending span is labeled with the correct `pending_count`.
