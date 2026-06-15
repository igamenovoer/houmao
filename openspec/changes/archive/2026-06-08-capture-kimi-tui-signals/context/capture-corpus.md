# Kimi TUI Capture Corpus

This corpus was captured on 2026-06-05 from the installed logged-in Kimi Code CLI at `/home/huangzhe/.kimi-code/bin/kimi`, version `0.11.0`. The local source reference used for stability investigation is `extern/orphan/kimi-code` at commit `b64f3b4`.

All counted sessions live under `tmp/kimi-tui-tracking/`. The source stream for each run is `pane_snapshots.ndjson`, captured at `sample_interval_seconds=0.1`. The derived low-rate stream is `pane_snapshots_2fps.ndjson`, produced from the source stream with `target_sample_interval_seconds=0.5` and `source_sample_id` traceability. Every run uses passive recorder mode with `input_capture_level=output_only`; input was delivered by scripted `tmux send-keys`, so labels record input authority as scenario metadata rather than authoritative input events.

The recorder marked every run with `visual_recording_exited`. That taint records the human-facing asciinema observer exiting early; pane snapshots continued to the requested duration and remain the replay-grade artifact.

| Set | Run | Source Frames | Derived Frames | Labels | Scenario |
| --- | --- | ---: | ---: | ---: | --- |
| Development | `dev-001-ready-draft-submit` | 162 | 47 | 4 | Ready editor, draft editing, submit, active response, completed success, footer model `thinking` metadata |
| Development | `dev-002-active-thinking` | 221 | 63 | 4 | Longer active thinking/composing response and ready return |
| Development | `dev-003-approval-reject` | 266 | 76 | 6 | Bash approval prompt, rejection, rejected-tool transcript, second approval prompt |
| Development | `dev-004-interrupt` | 234 | 67 | 4 | Active response interrupted with Escape and ready return |
| Development | `dev-005-footer-thinking-ready` | 165 | 48 | 4 | Ready return where footer says `Kimi-k2.6 thinking` after completion |
| Held-out | `test-001-heldout-simple` | 192 | 56 | 4 | Different simple response prompt with active and completed states |
| Held-out | `test-002-heldout-approval` | 260 | 76 | 6 | Different Bash approval prompt, rejection, rejected-tool summary, ready success |
| Held-out | `test-003-heldout-interrupt` | 231 | 67 | 4 | Different long response prompt interrupted with Escape |

Manual labels cover these state families: idle/editor-ready, draft editing, prompt submit and active response, completed response and ready return, approval blocked, approval rejection, interrupt, and footer-thinking metadata. Labels target public tracked-state fields and selected parser-facing fields (`business_state`, `input_mode`, `ui_context`) rather than detector-internal notes.

Validation results after implementation:

| Set | Run | 10 fps | Checked | 2 fps | Checked |
| --- | --- | --- | ---: | --- | ---: |
| Development | `dev-001-ready-draft-submit` | pass | 121 | pass | 36 |
| Development | `dev-002-active-thinking` | pass | 183 | pass | 51 |
| Development | `dev-003-approval-reject` | pass | 250 | pass | 70 |
| Development | `dev-004-interrupt` | pass | 227 | pass | 64 |
| Development | `dev-005-footer-thinking-ready` | pass | 131 | pass | 38 |
| Held-out | `test-001-heldout-simple` | pass | 158 | pass | 45 |
| Held-out | `test-002-heldout-approval` | pass | 222 | pass | 64 |
| Held-out | `test-003-heldout-interrupt` | pass | 224 | pass | 64 |
