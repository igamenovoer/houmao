## Why

The existing pending-state capture runner only collects the single-prompt-queue case (one prompt processing plus one pending follow-up). To train a detector that understands queue depth and remains robust against long prompts, we need labeled recordings that cover 1, 2, and 3 pending prompts coexisting in the same CLI session, including one prompt that is roughly 500 characters long. These additional cases exercise provider-specific rendering of stacked queued messages and surface signatures that the single-pending dataset cannot capture.

## What Changes

- Add count-targeted lifecycle manifests to `scripts/qualification/tui-prompt-admission/lifecycles/`:
  - `<provider>-1-pending.json`
  - `<provider>-2-pending.json`
  - `<provider>-3-pending-long.json`
- Extend the binary label template in `tui_pending_state_capture/labels.py` with a `pending_count` field (`0|1|2|3|unknown`) while keeping `has_pending_message` as the primary detector target.
- Add provider-specific `pending_count_patterns` to lifecycle manifests so the analyzer can estimate queue depth from visible signatures.
- Update `tui_pending_state_capture/video.py` to render `pending_count` in the right-side info panel of the review MP4.
- Add a 500-character canary prompt to the 3-pending-long manifests.
- Preserve failed or capped-partial attempts (e.g., a provider that supports only 2 pending prompts) with explicit taint reasons.
- Document calibration procedures for queue depth and long-prompt rendering in `<provider>-calibration.md`.

## Capabilities

### New Capabilities
- `tui-pending-state-multi-prompt-capture`: Tracker-blind tmux capture of CLI sessions with 1, 2, or 3 coexisting pending prompts, including a 500-character long prompt, plus automated binary/count labels and review video output.

### Modified Capabilities
- (none — this change is strictly test-data collection under `scripts/`; it does not change gateway control APIs, tracker public-state schemas, or `houmao-mgr` CLI semantics.)

## Impact

- Affects `scripts/qualification/tui-prompt-admission/lifecycles/` with new per-provider count-targeted manifests.
- Affects `scripts/qualification/tui-prompt-admission/tui_pending_state_capture/labels.py`, `models.py`, `video.py`, and unit tests.
- Reuses existing long-horizon launch and `terminal-record` capture helpers; no changes under `src/houmao/`.
- May produce additional large video files under `tmp/houmao-dev-testing/` during capture runs.
