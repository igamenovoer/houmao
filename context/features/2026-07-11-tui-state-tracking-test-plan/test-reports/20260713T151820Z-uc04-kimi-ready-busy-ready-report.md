# UC-04: Kimi Code ready → busy → ready transition test

Date: 2026-07-13

Scenario: `tmp/houmao-dev-testing/2026-07-13-uc04-kimi-ready-busy-ready/definitions/scenario.json`
Recording root: `tmp/houmao-dev-testing/2026-07-13-uc04-kimi-ready-busy-ready/capture/recording`
Validation root: `tmp/houmao-dev-testing/2026-07-13-uc04-kimi-ready-busy-ready/validate`
Review video: `tmp/houmao-dev-testing/2026-07-13-uc04-kimi-ready-busy-ready/validate/review/review.mp4`

## Purpose

UC-03 long-horizon replay showed that Kimi Code ST03 eventually returned to a ready posture after the readiness fix. The question remained whether the current detector can observe a full `ready → busy → ready` cycle on a fresh live Kimi Code session. UC-04 is a detector-driven live test that intentionally gates every action on the current detector's state so the recording itself is evidence of detector behavior.

## Procedure

The test harness was run with the `kimi` tool profile using auth bundle `tests/fixtures/auth-bundles/kimi/personal-a-default/`, which symlinks `~/.kimi-code/config` and credentials.

The scenario steps:

1. `wait_for_ready` — wait until detector reports `ready`.
2. `send_text` — submit first prompt asking for marker `UC04-FIRST-DONE` plus a 200-word summary.
3. `wait_for_active` — wait until detector reports `active`/`busy`.
4. `wait_for_ready` — wait until detector reports `ready` again.
5. `wait_seconds(3)` — idle gap.
6. `send_text` — submit second prompt asking for marker `UC04-SECOND-DONE` plus a 200-word summary.
7. `wait_for_active` — wait until detector reports `active`/`busy` again.
8. `wait_for_ready` — wait until detector reports `ready` again.
9. `wait_seconds(3)` — final idle gap.

Two failed capture attempts preceded the successful run:

- Attempt 01: bad launch pattern, session never entered the expected pane.
- Attempt 02: wrong active pane, detector could not see Kimi Code.

These failed attempts are excluded from analysis.

## Recording facts

- Tool: Kimi Code CLI `0.23.6`
- Samples: 160
- Sample interval: 0.05 s
- Wall duration: ~17.2 s
- Review video: 164 frames, 5 fps, 32.8 s, 1920×1080

Heuristic labels were added post-capture in `capture/recording/labels.json` using visible spinner/composer heuristics. They are **not** operator-reviewed ground truth; they serve only as a coarse reference for the validation comparison.

## Detector replay timeline

The current detector timeline (`validate/analysis/replay_timeline.ndjson`) shows the intended transition sequence:

| From | To | First sample | Wall time (s) | Triggering event note |
| --- | --- | --- | --- | --- |
| `unknown` | `ready` | `s000021` | 2.76 | `success_candidate` after initial wait |
| `ready` | `active` | `s000025` | 3.17 | `active_signal` after first prompt submission |
| `active` | `ready` | `s000071` | 7.90 | `success_candidate` when first response finished |
| `ready` | `active` | `s000103` | 11.23 | `active_signal` after second prompt submission |
| `active` | `ready` | `s000128` | 13.86 | `success_candidate` when second response finished |

The `replay_events.ndjson` confirms both `wait_for_ready` actions settled as `success` with `last_turn_source: explicit_input`:

- `s000081` at 8.90 s — first ready return settled.
- `s000137` at 14.86 s — second ready return settled.

Phase sample counts from detector replay:

- `unknown`: 20 samples
- `ready`: 69 samples
- `active`: 71 samples

## Validation against heuristic labels

`validate/analysis/comparison.json` reports 110 mismatched samples out of 160. The high mismatch is expected because the heuristic labels were generated with a simple rubric and do not accurately reflect the visible Kimi Code surface. Key discrepancies:

- Heuristic ranges label several mid-recording intervals as `ready` when the visible surface shows an active spinner/queue (e.g., `s000025`–`s000051`).
- The detector correctly classifies those intervals as `active`.
- The first divergence sample is `s000001`, on `surface_accepting_input` and `surface_editing_input`, because the heuristic labels those as `no` while the detector reports `unknown` during the initial launch transient.

`transition_order_matches: false` in the comparison is therefore an artifact of the heuristic label quality, not evidence that the detector failed the scenario.

## Manual review

The review video (`validate/review/review.mp4`) overlays the detector state in a side panel without covering the tmux pane. At 5 fps it is possible to step through and confirm:

- Kimi Code starts with the prompt editor visible.
- After the first prompt is sent, the active spinner/composer appears.
- After the first response completes, the editor returns empty and the detector reads `ready`.
- After the second prompt is sent, the active spinner/composer appears again.
- After the second response completes, the detector reads `ready` again and remains ready until stop.

## Conclusion

The current Kimi Code detector successfully observed two complete `ready → active → ready` cycles on a live session. Because the scenario actions were gated by the detector itself, the recording demonstrates that the detector can both:

1. Detect when Kimi Code becomes busy after prompt submission.
2. Return to `ready` after the model finishes and the prompt editor is available again.

This addresses the concern raised in `20260713T145521Z-current-detector-video-verification.md` about whether Kimi ST03's ready return was a one-off or a genuine capability.

## Caveats

- The test is detector-driven: success is defined relative to the current detector, not an independent human ground-truth label set.
- Heuristic labels are coarse and should not be used to claim 110 "errors"; a human-reviewed label set would be needed for a canonical accuracy score.
- Only Kimi Code `0.23.6` was tested; other tools or versions need their own UC-04 runs.

## Artifacts

- Scenario: `definitions/scenario.json`
- Recording: `capture/recording/`
- Labels: `capture/recording/labels.json`
- Validation manifest: `validate/artifacts/recorded_validation_manifest.json`
- Detector timeline: `validate/analysis/replay_timeline.ndjson`
- Comparison: `validate/analysis/comparison.json`
- Review video: `validate/review/review.mp4`
