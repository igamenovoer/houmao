# Claude Code Ready-Footer Advisory Signal

## Context

- Observed on 2026-03-20 during interactive-watch validation
- Tool: Claude Code
- Command-reported version: `claude --version` -> `2.1.80 (Claude Code)`
- Visible UI banner version during observation: `v2.1.80`
- Primary artifacts:
  - `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/interactive-watch/validate-success-live/terminal-record-validate-success-live/pane_snapshots.ndjson`
  - `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/interactive-watch/validate-success-live/analysis/groundtruth_timeline.ndjson`
  - `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/interactive-watch/validate-success-live/analysis/replay_timeline.ndjson`
- Intent: define a current-surface footer pattern that blocks early `last_turn=success` even when answer text and a fresh prompt are already visible

## Classification

When this footer-advisory signal matches:

- current posture may still be `turn_ready`
- `last_turn=success` MUST NOT be emitted yet

The tracker should continue waiting for a later stable ready surface and only allow `success` after the advisory footer disappears and the settle window passes.

## Required Conditions

All conditions below must be true in the same current surface:

1. The latest turn already shows visible answer content or other success-candidate output
2. A fresh `❯` prompt is visible
3. The bottom ready footer still contains the Claude advisory/installer notice, for example a line containing:
   - `Claude Code has switched from npm to native installer.`
   - `Run \`claude install\``
4. No current interrupt signal is present
5. No current known-failure signal is present

This advisory may appear truncated in the footer; the detector should treat the visible advisory fragment as sufficient if it still clearly matches the installer notice family.

## Observed Example

Representative pre-success samples:

- `s000470` at `99.520439s`
- `s000475` at `100.577766s`

Representative surface:

```text
❯ Reply with the single word READY and stop.

● READY

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ? for shortcuts  Claude Code has switched from npm to native installer. Run `claude install` ...
```

Observed post-advisory ready surface:

- `s000497` at `105.222337s`

Observed settled success:

- `s000502` at `106.285725s`

## Non-Match Guidance

- Do not classify this advisory footer as `turn_active`
- Do not classify this advisory footer as `known_failure`
- Do not emit `last_turn=success` while this advisory footer is still present for the current ready surface
- Once the advisory footer disappears and only the benign ready footer remains, the success settle window may start normally
