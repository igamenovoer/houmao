# Evidence: Session 1 lifecycle capture (claude 2.1.296, OpenLux relay, sonnet)

Date: 2026-10-12. Iteration: [iteration 1](../iterations/2026-10-12-plan-1-state-matrix-capture.md). Key questions: [KQ-1](../key-questions/KQ-1-signal-survival.md), [KQ-2](../key-questions/KQ-2-transcript-oracle.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/houmao-dev-tui-testing/2026-10-12-claude-session1-lifecycle/` (session `HMDEV-claude-20261012T140229`) |
| Tool | `claude` 2.1.296 (binary SHA-256 `f1f6e96e0d8342b9dbf41d7e88255397a6a52ce3d8736ad6a4c6b59c9b62fefa`) |
| Launcher | `claude-openlux-0.5x --model sonnet` (SHA-256 `11eb143781ebc14943b51e6af68dab98dbe98622ef4dfc07077fe5eeb5f63a7a`), posture `unattended` (bypass baked in) |
| Model verification | banner `Sonnet 5.5 · API Usage Billing` (op 0 gate passed; picker later showed `❯ 5. Sonnet ✔`) |
| Recording | 5 fps active mode, 1563 samples, `pane_snapshots.ndjson` SHA-256 `0928bfc4e70273b4…` (5021445 B), `run_tainted=false` |
| Labels | 25 ranges, complete coverage, frozen as `e4b465b3041fb16e…` before any replay (G3) |
| Environment stability | stable (relay latency high on two turns: 87 s queue turn; otherwise nominal) |

## Driven State Matrix (as captured)

All spans below are blind-labeled from raw snapshots + drive events only.

| Span | Samples | Surface content (observed) |
| --- | --- | --- |
| startup_modal | s000001–s000051 | Trust dialog: `Quick safety check: Is this a project you created or one you trust?`, options `❯ No, exit` (default) / `Yes, I trust this folder`, footer `Enter to confirm · Esc to cancel`. Renders even under `--dangerously-skip-permissions` |
| ready (fresh) | s000052–s000067 | Banner `Claude Code v2.1.296` / `Sonnet 5.5 · API Usage Billing`; boxed composer with ghost placeholder `Try "create a util logging.py that..."`; footer `⏵⏵ bypass permissions on (shift+tab to cycle) · ← for agents` |
| editing | s000068–s000093 | Draft typing/append/erase; placeholder returns on empty |
| active (turn 1) | s000099–s000161 | Footer gains `· esc to interrupt ·…`; spinner `<glyph> <Gerund>… (Ns · ↓ N tokens)` with glyphs cycling `✽ * · ✻ ✢`; composer remains usable |
| ready (success) | s000162–s000312 | Dock `✻ Cooked for 14s · done 10:03 PM`; footer drops the interrupt suffix |
| active (turn 2, read) | s000313–s000387 | as turn 1 |
| ready (success) | s000388–s000511 | dock present |
| active (turn 3, write+test) | s000514–s000614 | `● Write(...)` with `⎿ Wrote 2 lines…`, `Ran 1 shell command`, then answer; bypass auto-allows |
| ready (success) | s000615–s000928 | dock `✻ Sautéed for 22s · done 10:04 PM` |
| queue_pending | s000957–s000968 | Composer placeholder becomes `Press up to edit queued messages` while the follow-up waits; no ghost-styled echo cell |
| active (merged turn) | s000969–s001317 | Queued follow-up echoes into the transcript as a `❯` user block and merges; one dock covers both (`✻ Cogitated for 1m 27s · done 10:07 PM`) |
| active (interrupt leg) | s001372–s001398 | IT-7 turn |
| interrupted (Esc abort) | s001399–s001420 | **Silent abort**: turn stops, footer idles, and the interrupted prompt is restored into the composer as an editable draft. No `⎿ Interrupted` transcript line renders |
| active (mangled turn) | s001422–s001509 | `/compact` typed onto the restored draft submitted `…IT-7/compact` (driver composition bug, declared); spinner `✽ Ebbing…` with streaming answer |
| model_picker | s001512–s001525 | Queued `/model` **preempts** the streaming turn (transcript ends `⎿ Interrupted`); `Select model` picker with numbered entries, per-Mtok prices, `❯ 5. Sonnet ✔`, `… +8 models`; Esc → `Kept model as Sonnet 5.5` |
| ready (interrupted) | s001526–s001563 | Idle composer; `⎿ Interrupted · What should Claude do instead?` visible in transcript; `Press Ctrl-C again to exit` hint s001538–s001540; double C-c at 1 s spacing did **not** exit (hint rendered after the second press); TUI alive at end — tui_down coverage gap |

## Arm A: Detector Replay vs Blind Labels (per-sample agreement)

Arm A1 = maintained `2.1.x` profile (`--observed-version 2.1.296`, today's resolution). Arm A2 = fallback (`--observed-version 0.0.0`). 1563 compared samples each.

| Field | A1 (2.1.x) | A2 (fallback) |
| --- | --- | --- |
| surface_accepting_input | 0.9584 | 0.9584 |
| surface_ready_posture | **0.4875** | **0.4875** |
| surface_editing_input | 0.9552 | 0.9219 |
| surface_pending_input | 0.8900 | 0.8900 |
| turn_phase | 0.9539 | 0.9539 |
| last_turn_result | 0.8772 | 0.8772 |
| last_turn_source | 0.8804 | 0.8880 |
| diagnostics_availability | 1.0 | 1.0 |

False-ready samples: 50 (A1) / 51 (A2); false-busy: 7 / 7. The false-ready set is the trust modal (51 samples): the dialog's `❯ No, exit` option line reads as a usable composer (the modal-shield gap codex also had). The ready_posture collapse is structural: the 2.1.x profile computes `ready_posture=yes` only when a prompt is visible and no interrupt footer exists, and `unknown` otherwise — it never asserts `no` during busy, so every active sample disagrees with the `no` ground truth (agreement ≈ the non-active fraction).

## Arm A Signal Audit (session 1, 1563 samples)

| Signal | Fired/Expected | False fires | Verdict | Note |
| --- | --- | --- | --- | --- |
| `❯` prompt token | 1498/1498 | 64 | degraded | false fires are modal `❯`-option lines (trust 51, picker 13) |
| composer `─` rules | 1497/1498 | 1 | surviving-ish | composer stays boxed at 2.1.296 |
| placeholder tip `Try "` | 19/1443 | 1 | broken as a needle | tip text renders only on the fresh empty composer; post-turn empty composers show a bare `❯` |
| ghost SGR (fg231/bg237) raw | 1422/1443 | 29 | degraded | ghost styling tracks the empty composer, not the tip text |
| spinner line regex | 511/744 | 21 | degraded | misses the suffix-less variant `✻ Cerebrating… ` (no `(Ns · …)` parenthetical, trailing space) and answer-streaming phases |
| footer `esc to interrupt` | 741/744 | 8 | surviving | best busy signal; footer suffix `· esc to interrupt ·…` |
| completion `Worked for \d+[smh]` | 0/646 | 0 | **broken** | pre-refuted by binary audit; session verbs were Cooked/Sautéed/Cogitated |
| completion verb-set `(Baked\|Brewed\|Churned\|Cogitated\|Cooked\|Crunched\|Sautéed\|Worked) for \d` | 646/646 | 740 | degraded | correct on dock, but the dock persists in scrollback — needs live-edge/dock scoping |
| interrupt `^⎿ Interrupted…$` (line-stripped) | 31/61 | 0 | degraded | detector matches when visible; the 30 misses are the silent-Esc-abort span (no line renders) plus frames before the line scrolls in |
| `● ` response block | 646/646 | 597 | degraded | present during active streaming too |
| queued-echo proxy (indented `❯` cell) | 0/12 | 434 | **broken** | the 2.1.296 queued surface is the composer hint, not a ghost echo cell |
| trust dialog `Quick safety check` / `Yes, I trust this folder` | 50/51 | 0 | surviving | candidate needles confirmed |

## Arm B: Escape-Sequence Audit

Zero OSC 133 and zero OSC `9;4` sequences in 1563 samples (same as codex). Other OSC traffic exists (1046 samples carry some OSC, e.g. window title) but nothing state-bearing. Escape sequences carry no turn-state signal on this build.

## Arm C: Transcript Oracle (KQ-2)

One transcript file (`~/.claude/projects/…/23c5f660-….jsonl`) matched the workdir+window. Type inventory: `user` 25, `assistant` 22, `attachment` 15, `last-prompt` 8, `queue-operation` 2, `mode` 7, `permission-mode` 7, `file-history-snapshot` 6, `ai-title` 6, `atis-latch` 7, `system` 4 (all subtype `turn_duration`), `cost-state` 1, `file-history-delta` 1.

Alignment to labeled turn docks (samples s000162 / s000388 / s000615 / s001318):

| turn_duration event (elapsed s) | labeled dock (elapsed s) | delta |
| --- | --- | --- |
| 36.406 | 36.52 | 0.11 |
| 87.178 | 87.33 | 0.15 |
| 138.170 | 138.38 | 0.21 |
| 295.934 | 296.14 | 0.21 |

`queue-operation` events at 214.953 (enqueue; driver submit at 214.96) and 217.703 (dequeue; queue-hint span ends 217.53–217.75). Sub-sample alignment at every seam.

## Observations That Drive the Repair

1. Busy is best decided by the footer suffix `esc to interrupt` (741/744) with the spinner as secondary; spinner regex needs a suffix-optional variant and tolerance for streaming phases.
2. Completion requires the verb-set pattern `✻ <Verb> for <dur>` with dock-position or live-edge scoping (scrollback persistence false-fires otherwise); durations take the `Nm Ns` form (`1m 27s`), not just `\d+[smh]`.
3. Queued input at 2.1.296 = composer placeholder `Press up to edit queued messages`; the ghost-echo-cell structure the detector expects is gone.
4. Esc abort is silent on the transcript (draft restore only); C-c-style interruptions and slash-command preemption render `⎿ Interrupted · What should Claude do instead?`. Interrupt detection needs the temporal channel (active → idle transition without a dock), not just the text needle.
5. Modals (trust dialog, picker) carry `❯`-option lines that false-fire the prompt token; a modal shield must precede prompt classification, same as codex.
6. The two C-c exit presses at 1 s spacing did not exit; `Press Ctrl-C again to exit` is a transient hint, not a state.
