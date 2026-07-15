# Current-Detector UC-03 Video Verification

Date: 2026-07-13

Source recording root: `tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers`

Video output root: `tmp/uc03-trace-videos-current`

Comparator summary: `tmp/tui-readiness-regression/current-canonical-summary.json`

## Purpose

This pass repeats the visual procedure from `20260713T115323Z-uc03-classification-test-report.md` after the Codex and Kimi readiness fixes. The renderer now replays every raw recording through the detector code in the current checkout by default. The panel identifies this stream as `Tracker (current code)` and identifies the old generated state labels as `Legacy reference`.

The command used was:

```bash
pixi run python scripts/qualification/tui-prompt-admission/uc03_render_trace_video.py \
  --run-root tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers \
  --output-root tmp/uc03-trace-videos-current
```

Pass `--archived-tracker` to render the pre-fix stored tracker timelines instead.

## Render Coverage

`ffprobe -count_frames` confirmed that every MP4 contains exactly one encoded frame for every canonical source sample.

| Video | Source and encoded frames | SHA-256 |
| --- | ---: | --- |
| `claude-st-01-a007/trace.mp4` | 652 | `9f3c6b6ed574e9772feab23e5eaee3ff85736cde27326f4d497d709c459960c5` |
| `claude-st-02-a001/trace.mp4` | 2,310 | `9f592c16d2bc278f7b51c3148a91a387634b74f8127e7122b0e6a4d59df410e0` |
| `claude-st-03-a001/trace.mp4` | 3,371 | `a5df70beafc962f3dbdaae8b37985359b36400beee1ec5d9aa8177c6e225d83a` |
| `codex-st-01-a004/trace.mp4` | 563 | `0a3ea8148cb5dfa134f66c57bf3a3257ccb32c0708763ad0d898f9d16e6d096e` |
| `codex-st-03-a004/trace.mp4` | 2,032 | `205688497cff57ec29b57da0c4d24cf42e39bf320687942ec036aedc31908c0a` |
| `codex-st-04-a002/trace.mp4` | 230 | `6f32b9f45b33c0d42bbfd8c4d7c677b421da4b61710e4fefcf8d9d9824f7321a` |
| `codex-st-05-a004/trace.mp4` | 1,234 | `30e36bb131dba2a2f050374942fcb35e197d1e7f4c0e338452ae2702c4ddaaf3` |
| `kimi-st-03-a008/trace.mp4` | 753 | `44c620cb1e391a14ae3e76cf67467865c3294f9386dd8a81d3c925da3b3deab1` |
| `kimi-st-04-a003/trace.mp4` | 57 | `342dcf702e36200600b2a9d1c503b071341599f8453539ebfe66f162b82510be` |
| **Total** | **11,202** | |

The rendered video set occupies 32 MiB. Temporary full-frame PNG sequences were removed after encoding.

## Manual Checkpoints

Representative frames were extracted to `tmp/uc03-trace-videos-current/verification-frames` and inspected at original resolution.

| Recording sample | Visible evidence | Current tracker result | Finding |
| --- | --- | --- | --- |
| Kimi ST03 `s000003` | Active Kimi spinner/cancel surface after the submitted prompt | `busy_active`, `moon_spinner`, ready `no` | Correct. The legacy `ready_immediate` label is inconsistent with the visible active surface. |
| Kimi ST03 `s000020` | Retained follow-up pane with `ctrl-s to steer immediately` | `busy_active`, `queued_message`, ready `no` | Correct. The queued follow-up cannot be admitted as a new immediate turn. |
| Kimi ST03 `s000310` | Completed response, empty editor, no current spinner or queue | `ready_immediate`, ready `yes` | Correct ready return. |
| Codex ST05 `s000410` | `Working` row plus `Messages to be submitted after next tool call` | `busy_active`, `status_row` and `pending_input`, ready `no` | Correct. This was inside the former sustained false-ready block. |
| Codex ST05 `s000743` | Pending-input header remains visible while the normal status row is displaced by response text | `busy_active`, `pending_input`, ready `no` | Correct hidden-status fallback. |
| Codex ST05 `s001040` | Old transcript and a new shell launch command, without new Codex chrome | `indeterminate`, ready `unknown` | Correct conservative restart state. A newly observed process cannot inherit the old prompt's readiness. |
| Codex ST05 `s001046` | Fresh `OpenAI Codex (v0.144.1)` chrome and current empty prompt below the shell boundary | `ready_immediate`, ready `yes` | Correct generation recovery. |
| Codex ST04 `s000097` | Visible `Select Model and Effort` list and confirmation footer | `busy_overlay`, accepting `no` | Correct. The legacy `busy_draft` label misclassifies the selector row as editor text; both decisions block admission. |

## Result

The rendered evidence confirms that the large Kimi ST03 and Codex ST05 false-ready regions are gone in current-code replay. Canonical comparison still reports 190 exact-label differences and 104 ready-versus-blocked differences, but none forms a sustained prompt-admission interval of at least one second. The inspected residuals are short transition boundaries or defects in the legacy generated reference.

This visual pass supports the scoped conclusion from `20260713T123203Z-codex-kimi-readiness-fix-replay-report.md`: the frozen corpus contains no sustained prompt-admission inversion after the fix. It does not replace a fresh live UC-03 run with independently reviewed behavioral labels.
