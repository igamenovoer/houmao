# UC-03 Prompt-Admission Classification Test Report

Date: 2026-07-13

Run root: `tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers`

Video output: `tmp/uc03-trace-videos/`

## What Was Done

1. **Selected fixtures** — Used the nine replay-ready attempts listed in `20260713T095944Z-long-horizon-test-report.md`:
   - Claude ST01 `a007`, ST02 `a001`, ST03 `a001`
   - Codex ST01 `a004`, ST03 `a004`, ST04 `a002`, ST05 `a004`
   - Kimi ST03 `a008`, ST04 `a003`

2. **Built a UC-03 classification comparator** — Added `scripts/qualification/tui-prompt-admission/uc03_label.py` and `uc03_classification_test.py`. Both the existing tracker timeline and the human groundtruth timeline were mapped to UC-03 readiness labels (`ready_immediate`, `busy_active`, `busy_draft`, `busy_overlay`, `indeterminate`) before comparison. This tests **classification correctness** (does the tracker know when the surface is busy or ready?) rather than admission correctness.

3. **Rendered trace videos** — Added `uc03_render_trace_video.py` and produced one MP4 per attempt in `tmp/uc03-trace-videos/`. Each frame shows the bottom 36 rows of the tmux pane on the left and a right-hand panel with sample id/time, groundtruth label, tracker label, and the public-state fields behind the labels. All 11,202 samples across the nine attempts are preserved at the original 20 Hz cadence.

## How to Render Videos for Manual Verification

To inspect classification mismatches visually, render side-by-side videos that show the tmux screen, the operator ground-truth label, and the tracker label for every captured sample.

### Render all replay-ready attempts

```bash
pixi run python scripts/qualification/tui-prompt-admission/uc03_render_trace_video.py \
    --run-root tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers \
    --output-root tmp/uc03-trace-videos
```

### Render a single attempt

```bash
pixi run python scripts/qualification/tui-prompt-admission/uc03_render_trace_video.py \
    tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers/sessions/claude-st-01/attempts/a007 \
    --output-root tmp/uc03-trace-videos
```

### Output layout

Each attempt is rendered to its own directory:

```
tmp/uc03-trace-videos/
└── {provider}-{cell}-{attempt}/
    ├── trace.mp4      # Full video at 20 Hz
    └── frames/        # Individual PNG frames (one per sample)
```

For example:

- `tmp/uc03-trace-videos/claude-st-01-a007/trace.mp4`
- `tmp/uc03-trace-videos/codex-st-05-a004/trace.mp4`
- `tmp/uc03-trace-videos/kimi-st-03-a008/trace.mp4`

### How to use the videos

1. Locate the attempt with mismatches in the **Classification Results** table.
2. Open the corresponding `trace.mp4`.
3. Scrub to the mismatch timestamps. The right-hand panel highlights when the **Tracker** label differs from the **Groundtruth** label.
4. Compare the tmux screen on the left with the two labels to decide whether the tracker or the operator label is correct.

This is the fastest way to validate the high-mismatch cells — especially **Kimi ST03 a008**, **Codex ST05 a004**, and **Codex ST04 a002** — before changing detector profiles or oracles.

## Classification Results

| Provider | Cell | Attempt | Samples | Mismatches | Mismatch rate |
| --- | --- | --- | ---: | ---: | ---: |
| Claude | ST01 | a007 | 652 | 0 | 0.0% |
| Claude | ST02 | a001 | 2,310 | 3 | 0.1% |
| Claude | ST03 | a001 | 3,371 | 0 | 0.0% |
| Codex | ST01 | a004 | 563 | 64 | 11.4% |
| Codex | ST03 | a004 | 2,032 | 20 | 1.0% |
| Codex | ST04 | a002 | 230 | 41 | 17.8% |
| Codex | ST05 | a004 | 1,234 | 342 | 27.7% |
| Kimi | ST03 | a008 | 753 | 748 | 99.3% |
| Kimi | ST04 | a003 | 57 | 7 | 12.3% |
| **Total** | | | **11,202** | **1,225** | **10.9%** |

### Label distribution

| Provider | Cell | Tracker ready | GT ready | Tracker busy | GT busy | Tracker draft | GT draft | Tracker overlay | GT overlay | Tracker indet. | GT indet. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Claude ST01 | a007 | 39 | 39 | 609 | 609 | 4 | 4 | 0 | 0 | 0 | 0 |
| Claude ST02 | a001 | 8 | 8 | 2,297 | 2,294 | 5 | 8 | 0 | 0 | 0 | 0 |
| Claude ST03 | a001 | 81 | 81 | 3,285 | 3,285 | 5 | 5 | 0 | 0 | 0 | 0 |
| Codex ST01 | a004 | 59 | 51 | 502 | 511 | 2 | 1 | 0 | 0 | 0 | 0 |
| Codex ST03 | a004 | 118 | 100 | 1,732 | 1,751 | 182 | 181 | 0 | 0 | 0 | 0 |
| Codex ST04 | a002 | 15 | 16 | 139 | 138 | 36 | 76 | 40 | 0 | 0 | 0 |
| Codex ST05 | a004 | 368 | 56 | 764 | 1,077 | 91 | 84 | 0 | 17 | 11 | 0 |
| Kimi ST03 | a008 | 643 | 81 | 108 | 640 | 2 | 32 | 0 | 0 | 0 | 0 |
| Kimi ST04 | a003 | 7 | 13 | 7 | 0 | 7 | 8 | 36 | 36 | 0 | 0 |

## Observations

### Claude

- Claude ST01 and ST03 are **clean** under UC-03 label mapping: zero mismatches.
- The long-horizon report noted that Claude often reports `surface_ready_posture=unknown` during active periods. Because UC-03 maps `turn_phase=active` to `busy_active` first, that conservative ready-posture does **not** become a UC-03 mismatch.
- Claude ST02 has only three mismatches. In all three the tracker sees `turn_phase=active` with a `thinking_line` active reason while the operator labeled the surface `busy_draft`. These are at the boundary where a recovery prompt remained queued in the editor after an interrupted turn.

### Codex

- Codex ST01, ST03, and ST04 show small boundary disagreements between `busy_active`, `busy_draft`, and `ready_immediate`.
- Codex ST05 is the serious case: the tracker labels **368** samples as `ready_immediate` where the groundtruth labels only **56**. The tracker misses a large active block (764 tracker `busy_active` vs. 1,077 groundtruth `busy_active`). This matches the long-horizon report's finding that ST05 missed 313 manually active samples as ready and failed liveness oracles around exit/restart.
- Codex ST04 also shows the tracker using `busy_overlay` (40 samples) where the operator labeled `busy_draft`. This indicates the overlay detector is firing on draft/editor surfaces that are not true modal overlays.

### Kimi

- Kimi ST03 is the worst cell: **748 of 753 samples** mismatch. The tracker reports **643** `ready_immediate` samples while the groundtruth reports **81**; conversely the tracker reports only **108** `busy_active` samples while the groundtruth reports **640**. This is a severe active/ready inversion.
- Kimi ST04 has only 57 samples but 7 mismatches, mostly boundary disagreements between `busy_draft` and `ready_immediate` around the `/model` overlay sequence.
- The long-horizon report noted that fixed-rate safety oracles still passed for Kimi ST03 because the oracle set does not reject sustained active/ready inversion. That weakness is exactly what makes this failure mode dangerous for downstream admission decisions.

## Proposed Reasons for Bad Cases

| Bad case | Proposed reason |
| --- | --- |
| Kimi ST03 active/ready inversion | The Kimi detector profile (`KimiCodeSignalDetectorV0_23_X`) misreads active spinner/growth signals as an idle prompt surface. Possibly the active-reason parser does not recognize Kimi's current "thinking" UI elements, or the ready-posture heuristic is too aggressive when no explicit modal overlay is present. |
| Codex ST05 large false-ready block | Around the exit/restart operation the detector loses the active turn anchor and reports `ready` while the provider is still settling or re-launching. The long-horizon run already identified a harness defect (initially no retained shell for restart) and liveness-loss propagation failures in every schedule for this cell. |
| Codex ST04 overlay vs. draft confusion | The overlay classifier labels editor/draft surfaces as `busy_overlay` when the operator sees a normal text draft (`busy_draft`). The detector may be using overly broad accept-input or ready-posture rules that classify non-empty editor states as overlays. |
| Claude ST02 active/draft boundary | The tracker correctly sees active reasoning (`thinking_line`) but the operator labels the surface as `busy_draft` because the recovery prompt is visibly queued in the editor. This is a genuine ambiguity at the active-to-draft transition. |

## What to Fix

1. **Kimi detector profile** — Update `KimiCodeSignalDetectorV0_23_X` (or the 0.23.6-specific variant) so that active-turn evidence produces `turn_phase=active` and `surface_ready_posture=no` consistently. The current profile must be re-qualified before it can be trusted for UC-03 admission decisions.

2. **Add a sustained active/ready inversion safety oracle** — The long-horizon fixed-rate safety oracle set should reject a tracker timeline that reports `ready_immediate` while independent labels show `busy_active` for a sustained interval. This would have caught Kimi ST03 before it reached UC-03 testing.

3. **Codex ST05 liveness handling** — Harden the detector around provider exit/restart so that `tui_down`, restart-in-progress, and post-restart settling surfaces are not reported as `ready_immediate`. Ensure the retained-shell harness fix is retained and that the detector waits for a real ready editor before declaring readiness.

4. **Codex overlay classification** — Review the rules that map editor-with-draft surfaces to `busy_overlay`. A visible user-authored draft should map to `busy_draft`, not `busy_overlay`, unless a true modal/selector overlay is present.

5. **Fresh independent labels for Codex** — The long-horizon report noted a drafting-rubric defect for Codex that can overstate some active/ready mismatch counts. Relabel fresh Codex attempts with the corrected live-edge rubric before using them as UC-03 qualification ground truth.

6. **Proceed to UC-03 live capture only after classifier fixes** — The current replay fixtures are sufficient for simulator development, but the tracker profiles must pass the classification comparator cleanly before CAL-01, AR-01, and AR-02 live runs are used for qualification.

## Artifacts

- Comparator code: `scripts/qualification/tui-prompt-admission/uc03_label.py`, `scripts/qualification/tui-prompt-admission/uc03_classification_test.py`
- Video renderer: `scripts/qualification/tui-prompt-admission/uc03_render_trace_video.py`
- Trace videos: `tmp/uc03-trace-videos/*/{trace.mp4,frames/}` (frames retained for inspection)
- Source recordings: `tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers/sessions/<provider-cell>/attempts/<attempt>/`
