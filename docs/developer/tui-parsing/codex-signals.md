# Codex Signal Reference

This page records the concrete visible Codex TUI signals the repository currently uses when tracking tmux-backed Codex surfaces reliably. It is intentionally closer to source than the higher-level parser and runtime contract pages.

Use it together with:

- [Shared Contracts](shared-contracts.md)
- [Codex](codex.md)
- [Runtime Lifecycle](runtime-lifecycle.md)
The concrete examples here were confirmed from the maintained complex capture logged in [20260323-124129.md](../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md) and updated for Codex 0.162.x from the blind-labeled 0.162.1 recordings of the [2026-10-12 codex TUI parsing campaign](../../../context/campaigns/debug/2026-10-12-codex-tui-parsing/), which is the current qualification evidence.

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
| Temporal transcript growth | later latest-turn region grows while the active status row is not visible yet and no `Worked for` dock has landed | active evidence (`transcript_growth_undocked`) | Codex 0.162 hides the status row while the final answer streams, so undocked growth with turn content counts as active; a status-row blink of about one second or less carries active (`status_row_blink_carry`). Startup or editing redraws without turn content do not manufacture activity. |
| Response bullet | `• READY`, `• RECOVERED` | settled success context | These bullet response lines are the visible success content in the maintained complex fixture family. |
| Compaction status row | `• Compacting context (12s • esc to interrupt)` | active evidence (`compaction_status`) | Provider maintenance, not operator prompt work: it neither clears the previous prompt turn's terminal outcome nor settles success over it, so `last_turn_result=interrupted` survives a post-interrupt compaction. |
| Queued follow-up echo | `› <follow-up text>` rendered above the status row mid-turn | pending-input and active-turn evidence (`queued_follow_up`) | A mid-busy submitted follow-up is steer-merged into the running turn. Disambiguation from turn-starting echoes is structural: in-flight prose above, no `Worked for` dock or interrupt notice between the echo and the composer. Once the echo collapses into `+ N lines (^t to expand)`, no single-snapshot pending evidence remains (documented blind spot). |
| Operator modal surfaces | `Trust this folder?` + `Trust and continue`; list pickers with the `enter select · esc back` footer; `Warnings · N of M · …` with a dismiss affordance; approval and send-input dialogs | blocked admission (accepting/editing/ready/pending = `no`, active suppressed) | Modal needles use bounded structure plus essential semantic tokens, never exact full-sentence literals. |
| Interrupted-ready banner | `■ Conversation interrupted - use /feedback if something went wrong` | ready/interrupted posture | 0.162.x renders this single-sentence form; the needle is the whitespace-normalized, case-insensitive `Conversation interrupted` prefix. A notice with concurrent status-row activity is stale scrollback and does not mark the surface interrupted. |
| Prompt-adjacent terminal failure | red error blocks such as compact/server failures, or warning rows carrying overload/high-load/context-window style terminal semantics | current-error evidence, success blocker, `known_failure` for recognized terminal families, recoverable degraded chat context for compact/server signatures | Only the bounded prompt-adjacent region counts. The matcher uses structural role plus essential semantic token families, not exact full-sentence literals. Long scrollback errors above the current prompt area are historical and must not degrade the current prompt state. |
| Live-edge retry or reconnect status | `Reconnecting... 2/5`, `Reconnecting to model stream (2/5)`, `• Reconnecting to server… (4s)` near the current prompt/live edge | active evidence (`stream_retry_status`) | This is active current-turn evidence, not a ready-success return. Historical retry text outside the live edge must not keep a later prompt-ready turn active. |
| Completion marker | `Worked for 3s • 2:09 PM` | completion context when visible | 0.162.x drops the legacy box-drawing prefix; the dock is `Worked for Ns • HH:MM`. Useful supporting success context, but current success tracking also depends on the prompt/ready posture and the absence of stronger blocking or active evidence. |

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
- or a bounded retry, reconnect, stream-recovery, or connection-loss status is visible near the live edge
- or the latest-turn region is still growing across recent frames enough to satisfy temporal activity inference

Tracker meaning:

- `turn_phase=active`
- `last_turn=none`
- retry/reconnect status uses active reason `stream_retry_status`

Important reliability rule:

- Current activity checks are scoped to the live-edge tail, not the entire pane.
- Interrupted and success checks still use the latest-turn region.
- A stale interrupted banner visible above the current prompt must not override a later active or success turn once newer-turn authority exists.
- A stale `• Working (... esc to interrupt)` row far above the prompt must not keep the turn active once the visible surface has returned to a prompt-ready posture.
- A current retry or reconnect status remains active while visible, even if the parser or prompt area also looks submit-ready.

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

### Prompt-ready terminal failure

Typical surface:

- prompt-adjacent red error block or warning-style failure row is visible near the current prompt
- bounded text carries a recognized terminal failure family such as overload/high-load, context-window exhaustion, invalid prompt, quota exhaustion, or similar terminal semantics
- current prompt is visible, accepting input, not editing input, and not blocked by an overlay

Tracker meaning:

- `turn_phase=ready`
- `current_error_present=true`
- `success_candidate=false`
- `known_failure=true` for recognized terminal failure families strong enough to publish that outcome
- prompt-derived readiness is preserved when the composer is otherwise genuinely ready

Operational note:

- Warning rows are not terminal failures by default. They must be prompt-adjacent and carry the essential terminal semantics for a recognized family. Matchers should be maintained as semantic token families inside the Codex profile instead of exact upstream full sentences.

### Prompt-ready compact/server error

Typical surface:

- prompt-adjacent red error cell is visible near the current prompt
- the bounded error text carries compact/server degraded semantics, such as compact plus stream, disconnect, server, or remote semantics
- current prompt is visible, accepting input, not editing input, and not blocked by an overlay

Tracker meaning:

- `turn_phase=ready`
- `current_error_present=true`
- `success_candidate=false`
- `chat_context=degraded`
- `chat_context_diagnostic.tool_name=codex`
- `chat_context_diagnostic.degraded_error_type` is Codex-scoped, for example `codex_remote_compact_stream_disconnected`, `codex_remote_compact_context_length_exceeded`, `codex_remote_compact_unknown_parameter`, `codex_remote_compact_server_error`, or `unknown`
- `known_failure=false`

Operational note:

- `chat_context=degraded` means the current context is recoverably unhealthy, not that the gateway must clear context. Ordinary prompt delivery can continue when the prompt-ready gates pass. An explicit clean-context request such as `chat_session.mode=new` still runs the reset workflow.
- Compact/server degraded context is intentionally separate from `known_failure`: it blocks success while preserving readiness, but it does not imply a mandatory reset.
- Degraded error labels belong to the detector's CLI tool. Do not reuse Codex-specific labels for Claude, Kimi, or other tools; only `unknown` is shared.

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
- A warning row without prompt-adjacent terminal semantics is not a failure result.
- An older interrupted banner outside the latest-turn region is stale until proven otherwise.
- Older terminal failure or retry text outside the bounded current-turn region is historical evidence, not current readiness or completion authority.
- A visible typed draft should prevent the surface from being treated as a success candidate even if earlier success-looking transcript content remains above it.

## Practical Checklist

When investigating a Codex tracking bug from pane snapshots:

1. Find the latest visible `›` prompt anchor.
2. Bound the latest-turn region using the previous prompt before it.
3. Look for active status, tool, retry, reconnect, or stream-recovery cues in the live-edge tail first.
4. If the status row is absent, check whether recent latest-turn growth is supplying temporal active evidence.
5. Normalize whitespace and then look for the interrupted banner inside the latest-turn region.
6. Look for `• <payload>` and any `Worked for ...` completion dock as success context.
7. Decide whether the current prompt payload is plain draft text, dim placeholder text, or empty.
8. Ignore bubblewrap warnings, generic tips, and stale banners outside the latest-turn region when judging current-turn state.
9. Ignore stale `Working` rows and tool cells outside the live-edge tail when judging current activity.
10. Treat prompt-adjacent warning or red failure blocks as current failures only when the bounded block carries recognized terminal semantics.
11. Treat compact/server error cells as current degraded-context evidence only when they are in the bounded prompt-adjacent region near the current prompt and carry the compact/server degraded family.
