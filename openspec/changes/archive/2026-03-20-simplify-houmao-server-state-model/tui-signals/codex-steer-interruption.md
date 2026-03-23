# Codex Steer-Interruption Handoff Signal

## Context

- Live-validated on 2026-03-20
- Tool: Codex TUI in a tmux-backed CAO session
- Recorder run root: `tmp/terminal_record/codex-signal-check-20260320/`
- Key live sample: `s000951`
- Intent: define the exact surface where Codex interrupts an older response so a newly submitted steer prompt can start immediately

## Classification

When this signal matches, the tracked current-turn posture is:

- current posture: `turn_active`

This note does not emit:

- terminal outcome: `turn_interrupted`

## Required Conditions

All conditions below MUST be true in the same current surface.

1. A visible transcript line contains the exact informational text `Model interrupted to submit steer instructions.`
2. A fresh submitted prompt for a newer turn is visible below that informational line
3. A current agent-turn status row is visible for that newer prompt

Representative live surface:

```text
• Model interrupted to submit steer instructions.

› Run `sleep 30` in the shell, then respond with AFTERSLEEP only.

• Working (0s • esc to interrupt)
```

## Why This Matches

This surface means:

- the previously streaming response was preempted
- Codex has already accepted the newer prompt
- the newer prompt is now the current active turn

The informational line is historical context about why the previous answer stopped. It is not the ready-return interruption result defined in the dedicated interruption note.

## Non-Match Guidance

- Do not emit terminal `turn_interrupted` from this message alone
- Do not rely on this message if it only appears in stale scrollback for an older turn
- Do not use this message as active evidence unless the same current surface also shows a newer submitted prompt or newer active-turn evidence
