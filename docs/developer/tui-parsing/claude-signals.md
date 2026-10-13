# Claude Signal Reference

This page records the concrete visible Claude Code signals the repository currently uses when tracking tmux-backed Claude surfaces reliably. It is intentionally closer to source than the higher-level parser and runtime contract pages.

The current contract is qualified against Claude Code 2.1.296 (the support floor) on the frozen 2026-10-12 campaign recordings; see the [campaign repair report](../../../context/campaigns/debug/2026-10-12-claude-code-tui-parsing/reports/2026-10-12-claude-2-1-296-parsing-repair.md) for the evidence base. Claude below 2.1.296 raises `UnsupportedToolVersionError` at tracker resolution; there is no claude fallback detector.

Use it together with:

- [Shared Contracts](shared-contracts.md)
- [Claude](claude.md)
- [Runtime Lifecycle](runtime-lifecycle.md)

## Latest-Turn Scoping Rule

Before reading any individual signal, scope the latest visible turn correctly:

1. Find the latest visible Claude prompt anchor line beginning with `❯`, including the empty input row.
2. Walk upward to the previous non-empty Claude prompt anchor.
3. Treat the region between those two prompt anchors as the latest-turn region.
4. Only treat interrupted or failure-like status lines, completion docks, and response blocks inside that region as current-turn authority.

Why this matters:

- Claude keeps older transcript text visible for a long time, and completed docks persist in scrollback indefinitely.
- An older interrupted line or dock can remain on screen after the next turn has already started; unscoped matching completes or interrupts the wrong turn.
- A later response block inside the scoped region clears older interrupted or failure-like status inside that same region.
- If no current prompt anchor is visible, the surface is blocked (`no` on all four booleans), not `unknown` — for example the blank frame after a trust-dialog dismissal.

## Modal Shield Rule

Before classifying the prompt at all, decide whether a modal holds the surface. Modals render `❯`-option rows that false-fire the bare prompt anchor. The bounded modal needles are:

- workspace trust dialog: `Quick safety check` plus `trust this folder` (renders even under `--dangerously-skip-permissions` for an untrusted workdir)
- approval panels: `Do you want to …` plus the `Esc to cancel · Tab to amend` footer
- pickers: a `Select model` title, or numbered `❯ N.` options beside a `▔` border

While a modal holds, all four surface booleans are `no`, turn activity is suppressed, and the surface reports `ambiguous_interactive_surface=true`. A modal opened from an idle interrupted surface restores the interrupted outcome on dismissal (the modal command's echo re-anchors the region and hides the pre-modal interrupt line from the static needle).

## Reliable Signal Families

| Signal family | Concrete examples seen in captures | Used for | Reliability notes |
|------|---------|---------|---------|
| Current prompt anchor | `❯`, `❯ Return exactly READY and nothing else. Do not use tools.` | latest-turn boundary, accepting-input, draft classification | The latest visible `❯` is the anchor even when the prompt row is empty. Non-empty typed text means real draft input; placeholder or empty prompt means not editing. |
| Busy footer | `⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt` | primary active evidence (`interruptable_footer`) | The `esc to interrupt` footer suffix is the primary busy signal at 2.1.296; it stays visible while the answer streams and the spinner hides. |
| Active spinner line | `✽ Ionizing…`, `✻ Cerebrating… `, `✢ Vibing… (12s · ↓ 340 tokens)` | secondary active evidence (`thinking_line`) | The rotating leading glyph plus `…` (or `...`) is the reliable cue; the `(Ns · ↓ N tokens)` suffix and trailing whitespace are optional. The verb text changes across versions and is not the stable contract. |
| Completion dock | `✻ Worked for 3s · done 12:04`, `✻ Cogitated for 1m 16s · done 09:57` | completion marker, settled success | The dock is `✻` plus one of `Baked`, `Brewed`, `Churned`, `Cogitated`, `Cooked`, `Crunched`, `Sautéed`, `Worked` plus `for <Nm Ns>`; only a dock inside the latest-turn region completes the current turn. Docks persist in scrollback — never match full-surface. |
| Response block | `● READY`, `● RECOVERED` | secondary success candidate | Treat `● <payload>` in the latest-turn region as success evidence even without a dock. It still counts when the current empty prompt is visible below it. |
| Interrupted status | `⎿ Interrupted · What should Claude do instead?`, `⎿ User rejected the proposed plan` | ready/interrupted posture | Match `^⎿\s+(Interrupted|User rejected)` on the latest region status line. The C-c/preemption form and the approval-denial form both persist in scrollback. |
| Queued-input placeholder | composer placeholder `Press up to edit queued messages` | `surface_pending_input` | 2.1.296 renders the queue as the composer's own placeholder payload; `yes` when the placeholder carries the hint, `no` on a complete composer without it. The pre-2.1.296 ghost-cell queue structure is dead. |
| Ready footer / installer notice | `⏵⏵ bypass permissions on (shift+tab to cycle)`, `Claude Code has switched from npm to native installer.` | supporting context only | These lines are not active authority and must not suppress a real stable response block. |

## Signal Meanings Used Today

### Ready placeholder

Typical surface:

- latest prompt anchor visible
- no real draft text in the current prompt
- no busy footer, no current spinner line
- no current interrupted-ready line, no modal

Tracker meaning:

- `surface_accepting_input=yes`
- `surface_editing_input=no`
- `surface_ready_posture=yes`
- `turn_phase=ready`
- `last_turn=none`

### Ready draft

Typical surface:

- latest prompt anchor contains real user-authored text
- no busy footer, no current spinner line
- no current interrupted-ready line for the same turn

Tracker meaning:

- `surface_accepting_input=yes`
- `surface_editing_input=yes`
- `surface_ready_posture=yes`
- `turn_phase=ready`
- a latched `last_turn` outcome persists while the operator edits

Important reliability rules:

- If an older interrupted line is still visible above the current prompt but outside the latest-turn region, it is stale and must not keep the new draft in `last_turn=interrupted`.
- A visible draft does not clear a latched terminal outcome. 2.1.296 restores an aborted turn's prompt into the composer as a draft, and the previous outcome stays correct until explicit submission or newer active-turn evidence.
- Typing is not a settle surface: success candidacy is refused while the composer carries a draft, even with the dock still visible in the region.

### Active turn without overlapping draft

Typical surface:

- busy footer and/or spinner line visible in the latest-turn region
- current prompt row is empty or placeholder-only

Tracker meaning:

- `turn_phase=active`
- `surface_ready_posture=no` (asserted, not `unknown`)
- `surface_editing_input=no`
- `last_turn=none`

### Active turn with overlapping draft

Typical surface:

- busy footer or spinner line visible above
- latest prompt anchor contains newer user-authored draft text below

Tracker meaning:

- `turn_phase=active`
- `surface_ready_posture=no`
- `surface_editing_input=yes`
- the active-turn evidence clears any stale terminal outcome

This is one of the most important Claude-specific overlap cases. Older-turn activity must not downgrade the visible current draft to `surface.editing_input=unknown`.

### Interrupted ready

Typical surface:

- status line `⎿ Interrupted · What should Claude do instead?` or `⎿ User rejected …`
- prompt is visible for follow-up input

Tracker meaning:

- `turn_phase=ready`
- `last_turn_result=interrupted`
- `last_turn_source=explicit_input` when it follows an intentional interrupt

### Silent Esc abort (temporal)

Typical sequence:

- an active frame (busy footer and/or spinner)
- then an idle frame with no modal, no interrupt status line, and no *freshly appeared* region dock — the aborted prompt reappears in the composer as a restored draft

Tracker meaning (from the 600 s temporal channel, not the static needles):

- `last_turn_result=interrupted`
- `surface_editing_input=yes` (the restored draft is real editing)
- the outcome persists across the restored-draft span until the next submission or active-turn evidence

A dock counts as fresh only when it was not visible during the active frames; this keeps the previous turn's dock (re-anchored into the region when the aborted turn's echo scrolls off) from reading as a completion. A completed turn without any visible dock is the recorded qualification boundary of this inference.

### Settled success

Typical surface:

- completion dock `✻ <Verb> for <Nm Ns>` and/or a response block `● <payload>` in the latest-turn region
- no busy footer, no current spinner line
- current prompt is visible, empty, and ready again
- surface remains stable long enough to satisfy the settle window

Tracker meaning:

- `turn_phase=ready`
- `last_turn_result=success`
- `last_turn_source=explicit_input`

Operational notes:

- The native-installer footer notice may still be visible below the prompt. That notice is context, not a reason to reject the success surface.
- Settle identity hashes state-bearing lines only (transcript anchors, box rules, the mode footer), so volatile furniture — tip lines below the dock, transient hints, the effort indicator — cannot invalidate a settled success.

## Cues That Are Not Authoritative By Themselves

- The changing working-summary verb such as `Ionizing…`, `Vibing…`, `Cerebrating…` is not the stable part of the contract. Use the rotating leading symbol plus ellipsis structure instead.
- A dock in scrollback above the latest-turn region is history, not completion.
- Old interrupted or failure-looking transcript lines above the previous non-empty prompt are stale until proven otherwise.
- Historical slash-command or menu text in scrollback is not enough to keep the current prompt classified as modal once a fresh normal prompt has recovered. A slash-autocomplete frame that hides busy evidence for a moment does not end the turn (the temporal channel carries activity across a ≤1 s blink).

## Practical Checklist

When investigating a Claude tracking bug from pane snapshots:

1. Check the modal needles first; a modal forces all four booleans to `no`.
2. Find the latest visible `❯` prompt anchor.
3. Scope the latest-turn region against the previous non-empty prompt.
4. Look for the `esc to interrupt` footer and a spinner line when deciding active; readiness asserts `no` while either holds.
5. Look for a `✻ <Verb> for <Nm Ns>` dock or `● <payload>` block inside that region when deciding success.
6. Look for `⎿ Interrupted` or `⎿ User rejected` in that region when deciding interrupted-ready; remember silent aborts leave no line at all.
7. Read the composer placeholder for queued input (`Press up to edit queued messages`).
8. Decide whether the current prompt is real draft text, placeholder, or empty — and remember a draft never clears a latched outcome by itself.
