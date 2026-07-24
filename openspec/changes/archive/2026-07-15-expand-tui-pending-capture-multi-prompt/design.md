## Context

The `tui_pending_state_capture` runner under `scripts/qualification/tui-prompt-admission/` already captures single-pending prompt-queue sessions for Claude Code, Codex CLI, and Kimi Code. It produces a frozen 20 Hz recording, binary per-snapshot labels (`can_accept_input`, `has_pending_message`), and a review video with labels on the right.

The detector we want to train needs to recognize queue depth, not just presence. A CLI that shows one pending message can look very different from one that shows three stacked messages, especially when one of them is a long prompt that wraps or truncates in the provider's retention surface.

## Goals / Non-Goals

**Goals:**
- Capture count-targeted sessions for 1, 2, and 3 coexisting pending prompts per provider.
- Include one ~500-character prompt in the 3-pending case.
- Extend the label template with a `pending_count` field while preserving the existing binary detector target.
- Render `pending_count` in the review video's right-side info panel.
- Keep the capture tracker-blind and reuse the existing long-horizon launch / terminal-record capture helpers.

**Non-Goals:**
- Changing tracker public-state schemas or `houmao-mgr` CLI semantics.
- Submitting prompts through the gateway; capture continues to use direct tmux keystrokes.
- Training or validating the detector.
- Supporting providers other than Claude Code, Codex CLI, and Kimi Code.
- Modifying source code under `src/houmao/`.

## Decisions

### Separate count-targeted sessions instead of one staircase

Create three lifecycle manifests per provider: `1-pending`, `2-pending`, and `3-pending-long`. Each session submits the base prompt plus the appropriate number of follow-ups.

**Rationale:** Isolated sessions keep per-count ground truth clean. If a provider caps the queue at two, the `3-pending-long` run is tainted independently without invalidating the 1-pending and 2-pending datasets.

**Alternative considered:** One session that walks 1→2→3 pending in a staircase. Rejected because a failure at the third step would waste the earlier transitions, and the resulting labels would need to cover mixed-count spans.

### Extend labels with `pending_count` while keeping `has_pending_message`

The label file gains a third field:

```json
{
  "can_accept_input": "no",
  "has_pending_message": "yes",
  "pending_count": 3,
  "evidence_note": "matched: pending; counted 3 queued markers"
}
```

`pending_count` is `0` when `has_pending_message=no`, and `1|2|3|unknown` when `has_pending_message=yes`.

**Rationale:** The binary `has_pending_message` remains the primary detector target. `pending_count` is auxiliary metadata that makes the expanded dataset explicit and reviewable.

### Count detection uses provider-specific marker counting

Each lifecycle manifest declares a `pending_count_patterns` block that tells the analyzer how to estimate queue depth from visible signatures, e.g.:

```json
"pending_count_patterns": {
  "extractor": "count_markers",
  "marker_regex": "^[\\s]*↳\\s"
}
```

**Rationale:** Provider surfaces expose queued messages as bullets, chips, or numbered lines. Counting those markers is more portable than parsing a single provider-native counter string, which may not exist on all versions.

**Alternative considered:** A single regex with a capture group for the number. Rejected because not all providers display an explicit count, and marker counting generalizes better.

### Place the 500-char prompt as the third pending prompt

In the `3-pending-long` scenario the third submitted prompt is the long one.

**Rationale:** This exercises the deepest queue state and the most crowded retention surface. If the provider truncates or wraps long queued text, the effect is visible while two other pending prompts still exist.

### Preserve cap-partial attempts

If a provider visibly queues only two prompts and rejects or collapses the third, the run is marked `taint_reasons: ["pending_count_capped_at_2"]` and the recording plus labels are still frozen.

**Rationale:** A cap is itself useful evidence. Discarding the run would lose the information that the provider supports at most two pending prompts.

## Risks / Trade-offs

- **[Risk]** A provider may not support three pending prompts at all.
  **Mitigation:** Run the `3-pending-long` scenario with `required: false` on the count=3 pattern step, record the cap, and still emit labels for whatever count was reached.

- **[Risk]** The 500-char prompt may wrap or truncate in a way that breaks the pending signature regex.
  **Mitigation:** Include a short unique canary substring in the long prompt so reviewers can grep for it in snapshots, and calibrate the pending regex against the visible wrapped form rather than the raw prompt text.

- **[Risk]** Rapid successive submissions may race with the provider UI update.
  **Mitigation:** Keep the existing 0.5 s settle after `send_text` and before `send_key`, and add a 0.5–1.0 s wait after each `Enter` before the analyzer checks count.

- **[Risk]** Count patterns are version-specific and fragile.
  **Mitigation:** Treat the first capture for a provider/version as calibration; update `pending_count_patterns` and record notes in `<provider>-calibration.md`.

- **[Trade-off]** Separate sessions triple the capture time compared with one staircase session.
  **Acceptance:** Cleaner ground truth and isolated failure modes outweigh the extra runtime.

## Migration Plan

No production migration. Deployment is:
1. Extend `tui_pending_state_capture/models.py` with `pending_count` on `LabelRow` and `SpanSummary`.
2. Extend `tui_pending_state_capture/labels.py` to compute `pending_count` from manifest patterns.
3. Extend `tui_pending_state_capture/video.py` to render `pending_count`.
4. Add per-provider count-targeted lifecycle manifests under `lifecycles/`.
5. Update unit tests for the analyzer and video renderer.
6. Capture and calibrate one run per provider/version, updating `<provider>-calibration.md`.

Rollback is directory/file removal; no schema or persisted state is affected.

## Open Questions

- Should we also capture a long prompt in the 1-pending and 2-pending scenarios, or is one long-prompt case sufficient?
- Should the 500-char prompt be exactly 500 characters, or is "roughly 500" (e.g., 480–520) acceptable?
- Do we need a separate `staircase` manifest that shows the 1→2→3 transition in one recording, or are the three isolated sessions enough?
