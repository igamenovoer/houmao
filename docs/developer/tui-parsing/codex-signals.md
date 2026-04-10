# Codex Signal Reference

This page records the concrete visible Codex TUI signals the repository currently uses when tracking tmux-backed Codex surfaces reliably. It is intentionally closer to source than the higher-level parser and runtime contract pages.

Use it together with:

- [Shared Contracts](shared-contracts.md)
- [Codex](codex.md)
- [Runtime Lifecycle](runtime-lifecycle.md)
The concrete examples here were confirmed from the maintained complex capture logged in [20260323-124129.md](../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md).

## Scoping Rules

Codex tracking now uses two scopes at once. Before reading any individual signal, separate them correctly:

1. Find the latest visible Codex prompt anchor line beginning with `›`.
2. Walk upward to the previous visible Codex prompt anchor before the current prompt.
3. Treat the region above the current prompt and back to that previous prompt as the latest-turn region.
4. Separately, take the bounded live-edge tail from the latest visible non-empty lines on screen.

Current implementation note:

- The latest-turn region is still used for interruption, success context, and temporal transcript growth.
- The live-edge tail is used for current status-row and tool-cell activity.
- Full tmux scrollback may still be captured for parser and history use, but activity detection must not trust arbitrary historical rows above the live edge.
- When no current prompt is visible, Codex falls back to a bounded recent non-empty window rather than using the entire pane.

## Reliable Signal Families

| Signal family | Concrete examples seen in captures | Used for | Reliability notes |
|------|---------|---------|---------|
| Current prompt anchor | `› Reply with the single word READY and stop.`, `› Search this repository for files related to tmux and prepare a grouped summary. Think carefully before answering.`, `› Reply with the single word RECOVERED and stop.` | latest-turn boundary, accepting-input, draft classification | The latest visible `›` line is the prompt anchor. Plain prompt payload means real draft text; dim prompt payload is placeholder; empty prompt means not editing. |
| Active status row | `• Working (0s • esc to interrupt)`, `• Working (47s • esc to interrupt)` | active evidence (`status_row`) | This is the primary visible active cue for Codex when it is present in the live-edge tail. Old rows higher in scrollback are stale. |
| In-flight tool cell | `• Calling ...`, `• Running ...`, `• Waited for background terminal · ...` | active evidence (`tool_cell`) | Tool cells are also live-edge signals. They keep the turn active even if no `Working` row is visible. |
| Temporal transcript growth | later latest-turn region grows while the active status row is not visible yet | active evidence (`transcript_growth`) | Codex can still be active before the status row stabilizes. The detector treats meaningful recent growth in the latest-turn region as temporal active evidence. |
| Response bullet | `• READY`, `• RECOVERED` | settled success context | These bullet response lines are the visible success content in the maintained complex fixture family. |
| Interrupted-ready banner | `■ Conversation interrupted - tell the model what to do differently. Something went wrong? Hit /feedback to report the issue.` | ready/interrupted posture | This banner can wrap across multiple terminal lines. Normalize whitespace before judging it. |
| Completion marker | `─ Worked for ...` | completion context when visible | This is useful supporting success context, but current success tracking also depends on the prompt/ready posture and the absence of stronger blocking or active evidence. |

## Signal Meanings Used Today

### Ready placeholder

Typical surface:

- latest prompt anchor visible
- dim placeholder payload or empty prompt
- no current active status row
- no current interrupted banner

Tracker meaning:

- `surface_accepting_input=yes`
- `surface_editing_input=no`
- `surface_ready_posture=yes`
- `turn_phase=ready`
- `last_turn=none`

### Ready draft

Typical surface:

- latest prompt anchor contains real plain-text user-authored input
- no current active status row
- no current interrupted banner

Tracker meaning:

- `surface_accepting_input=yes`
- `surface_editing_input=yes`
- `surface_ready_posture=yes`
- `turn_phase=ready`
- newer-turn authority clears stale `last_turn`

### Active turn

Typical surface:

- active status row visible in the live-edge tail
- or in-flight tool cell visible in the live-edge tail
- or the latest-turn region is still growing across recent frames enough to satisfy temporal activity inference

Tracker meaning:

- `turn_phase=active`
- `last_turn=none`

Important reliability rule:

- Current activity checks are scoped to the live-edge tail, not the entire pane.
- Interrupted and success checks still use the latest-turn region.
- A stale interrupted banner visible above the current prompt must not override a later active or success turn once newer-turn authority exists.
- A stale `• Working (... esc to interrupt)` row far above the prompt must not keep the turn active once the visible surface has returned to a prompt-ready posture.

### Active turn with overlapping draft

Typical surface:

- Codex still shows active status or temporal growth for the current turn
- a newer prompt line below already contains typed follow-up text

Concrete example from the complex capture:

- interrupted or older transcript content above
- current prompt below: `› Now search this repository for files related to terminal recording ...`

Tracker meaning:

- `turn_phase=active`
- `surface_editing_input=yes`
- visible newer draft still clears stale terminal state

### Interrupted ready

Typical surface:

- wrapped or unwrapped interrupted banner text is visible in the latest-turn region
- current prompt is visible
- active status row is no longer visible

Tracker meaning:

- `turn_phase=ready`
- `last_turn_result=interrupted`
- `last_turn_source=explicit_input` in the maintained interrupt workflow

Operational note:

- Normalize whitespace before matching the interrupted banner because Codex commonly wraps it.

### Settled success

Typical surface:

- bullet response line such as `• READY` or `• RECOVERED`
- current prompt is visible and back in a ready posture
- no current active status row
- no current interrupted banner
- prompt is empty or placeholder-only rather than an active visible draft

Tracker meaning:

- `turn_phase=ready`
- `last_turn_result=success`
- `last_turn_source=explicit_input`

## Cues That Are Not Authoritative By Themselves

- The top-of-screen bubblewrap warning is not latest-turn authority.
- Generic tip lines are not latest-turn authority.
- An older interrupted banner outside the latest-turn region is stale until proven otherwise.
- A visible typed draft should prevent the surface from being treated as a success candidate even if earlier success-looking transcript content remains above it.

## Practical Checklist

When investigating a Codex tracking bug from pane snapshots:

1. Find the latest visible `›` prompt anchor.
2. Bound the latest-turn region using the previous prompt before it.
3. Look for the active status row in that region first.
4. If the status row is absent, check whether recent latest-turn growth is supplying temporal active evidence.
5. Normalize whitespace and then look for the interrupted banner inside the latest-turn region.
6. Look for `• <payload>` and any `─ Worked for ...` completion marker as success context.
7. Decide whether the current prompt payload is plain draft text, dim placeholder text, or empty.
8. Ignore bubblewrap warnings, generic tips, and stale banners outside the latest-turn region when judging current-turn state.
9. Ignore stale `Working` rows and tool cells outside the live-edge tail when judging current activity.
