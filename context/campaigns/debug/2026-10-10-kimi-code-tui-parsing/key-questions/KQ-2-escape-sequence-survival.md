# KQ-2: Do escape-sequence state channels survive tmux capture on kimi-code 2.1.1?

Date: 2026-10-10. Status: closed (answered negatively, 2026-10-10; disposition recorded 2026-10-12). Evidence: iteration 1 Arm B audit in the [iteration 1 plan](../iterations/2026-10-10-plan-1-state-matrix-capture.md) and the per-session evidence docs under `../evidences/`.

kimi-code 2.1.1 emits OSC 133 zone markers on transcript lines (`constant/rendering.ts:9-11`) and OSC `9;4;3` indeterminate progress while busy / `9;4;0` when idle (`packages/pi-tui/src/terminal.ts:9-10`, `kimi-tui.ts:3847-3855`). Would an escape-preserving capture (`tmux capture-pane -e`) give a cleaner busy/idle/approval signal than text scraping?

## Answer

No channel survives. Iteration 1's Arm B audit scanned all 2706 escape-preserving samples across both frozen sessions: zero OSC 133 zone markers and zero OSC `9;4` progress sequences; only OSC 8 hyperlinks survive tmux capture. Escape-sequence state channels are therefore infeasible for this capture path, and no dedicated iteration was needed. Event channels (hooks, print-mode stream-json) remain the only alternative oracle candidate; that question is KQ-3.

The production consequence landed in `openspec/changes/raise-kimi-code-floor-2-1-1/`: the maintained kimi 2.1.x detector is text-scraping (Arm A), with no escape-sequence channel.

## Scope

Covers tmux `capture-pane -e` output of kimi-code 2.1.1 regular (scrollback) mode on this host only. Does not evaluate other terminals, fullscreen mode, or non-tmux consumers of the raw stream.
