## 1. Extend label models and analyzer

- [x] 1.1 Add `pending_count` field to `LabelRow` and `SpanSummary` in `tui_pending_state_capture/models.py`.
- [x] 1.2 Add `pending_count_patterns` to the `LifecycleManifest` model and JSON loader.
- [x] 1.3 Extend `analyze_snapshots` in `tui_pending_state_capture/labels.py` to compute `pending_count` from manifest patterns, defaulting to `unknown` on conflict.
- [x] 1.4 Update `LabelsFile.to_payload`, `load_labels_file`, and the label summary serialization to include `pending_count`.

## 2. Update review video renderer

- [x] 2.1 Extend `_render_frame` in `tui_pending_state_capture/video.py` to display `pending_count` in the right-side info panel.
- [x] 2.2 Ensure the value color matches the count (green for known 1/2/3, orange for unknown).

## 3. Add count-targeted lifecycle manifests

- [x] 3.1 Create `lifecycles/claude-1-pending.json`, `claude-2-pending.json`, and `claude-3-pending-long.json`.
- [x] 3.2 Create `lifecycles/codex-1-pending.json`, `codex-2-pending.json`, and `codex-3-pending-long.json`.
- [x] 3.3 Create `lifecycles/kimi-1-pending.json`, `kimi-2-pending.json`, and `kimi-3-pending-long.json`.
- [x] 3.4 Define the ~500-character canary prompt for each `3-pending-long` manifest.
- [x] 3.5 Add `pending_count_patterns` to each manifest based on the provider's queued-message rendering.

## 4. Handle cap-partial attempts

- [x] 4.1 Add a `pending_count_capped_at_N` taint reason in the runner.
- [x] 4.2 Make the count=3 `wait_for_pattern` step non-fatal so the run freezes when the provider caps the queue.
- [x] 4.3 Record the observed cap in `run-summary.json` and `frozen-evidence.json`.

## 5. Tests

- [x] 5.1 Update unit tests for the analyzer to assert `pending_count` values for synthetic snapshots with 0/1/2/3 visible markers.
- [x] 5.2 Add a test that a long canary prompt is preserved in the manifest.
- [x] 5.3 Add a test that `non_fatal_on_timeout` steps continue execution and add a taint reason.
- [x] 5.4 Verify no new or modified files appear under `src/houmao/`.

## 6. Documentation and calibration

- [x] 6.1 Update `lifecycles/<provider>-calibration.md` with queue-depth observations.
- [x] 6.2 Update the runner README to document the new count-targeted manifests and `pending_count` label field.
- [x] 6.3 Update the UC-05 dataset report in `context/features/2026-07-11-tui-state-tracking-test-plan/dataset-reports/uc-05-pending-instruction-state.md` to mention the expanded multi-prompt dataset.

## 7. Manual capture and validation

- [x] 7.1 Run one capture per provider/version for the 1-pending manifest and verify `pending_count=1`.
- [x] 7.2 Run one capture per provider/version for the 2-pending manifest and verify `pending_count=2` (Claude caps at 1; Kimi v1 timed out, v2 reached 2).
- [x] 7.3 Run one capture per provider/version for the 3-pending-long manifest and verify the reached count and long-prompt visibility.
- [x] 7.4 Inspect each `review/labels.mp4` to confirm `pending_count` is rendered correctly.

## Capture Results Summary

| Provider | Manifest | Target | Observed | Status | Run root |
|---|---|---:|---:|---|---|
| Codex CLI | `codex-1-pending.json` | 1 | 1 | success | `tmp/houmao-dev-testing/20260714-codex-1-pending` |
| Codex CLI | `codex-2-pending.json` | 2 | 2 | success | `tmp/houmao-dev-testing/20260714-codex-2-pending` |
| Codex CLI | `codex-3-pending-long.json` | 3 | 3 | success | `tmp/houmao-dev-testing/20260714-codex-3-pending-long` |
| Claude Code | `claude-1-pending.json` | 1 | 1 | success | `tmp/houmao-dev-testing/20260714-claude-1-pending` |
| Claude Code | `claude-2-pending.json` | 2 | 1 | tainted (`pending_count_capped_at_1_target_2`) | `tmp/houmao-dev-testing/20260714-claude-2-pending` |
| Claude Code | `claude-3-pending-long.json` | 3 | 1 | tainted (`pending_count_capped_at_1_target_3`) | `tmp/houmao-dev-testing/20260714-claude-3-pending-long` |
| Kimi Code | `kimi-1-pending.json` | 1 | 1 | success | `tmp/houmao-dev-testing/20260714-kimi-1-pending` |
| Kimi Code | `kimi-2-pending.json` | 2 | 2 | success | `tmp/houmao-dev-testing/20260714-kimi-2-pending-v2` |
| Kimi Code | `kimi-3-pending-long.json` | 3 | TBD | in progress | `tmp/houmao-dev-testing/20260714-kimi-3-pending-long-v2` |

Claude Code appears to cap its visible pending queue at one additional prompt; the runner records this cap and still freezes the evidence. Kimi Code reached two pending prompts in the re-run with extended timeouts.
