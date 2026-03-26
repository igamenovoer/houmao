# Claude Signal Reference

This page records the concrete visible Claude Code signals the repository currently uses when tracking tmux-backed Claude surfaces reliably. It is intentionally closer to source than the higher-level parser and runtime contract pages.

Use it together with:

- [Shared Contracts](shared-contracts.md)
- [Claude](claude.md)
- [Runtime Lifecycle](runtime-lifecycle.md)
The concrete examples here were confirmed from the maintained complex captures logged in [20260323-124129.md](../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md).

## Latest-Turn Scoping Rule

Before reading any individual signal, scope the latest visible turn correctly:

1. Find the latest visible Claude prompt anchor line beginning with `❯`, including the empty input row.
2. Walk upward to the previous non-empty Claude prompt anchor.
3. Treat the region between those two prompt anchors as the latest-turn region.
4. Only treat interrupted or failure-like status lines inside that region as current-turn authority.

Why this matters:

- Claude keeps older transcript text visible for a long time.
- An older interrupted line can remain on screen after the next draft has already started.
- A later response block inside the scoped region should clear older interrupted or failure-like status inside that same region.
- If no current prompt anchor is visible, degrade conservatively rather than scanning the whole pane and reviving stale transcript status.

## Reliable Signal Families

| Signal family | Concrete examples seen in captures | Used for | Reliability notes |
|------|---------|---------|---------|
| Current prompt anchor | `❯`, `❯ Return exactly READY and nothing else. Do not use tools.`, `❯ Now search this repository for files related to terminal recording ...` | latest-turn boundary, accepting-input, draft classification | The latest visible `❯` is the anchor even when the prompt row is empty. Non-empty typed text means real draft input; placeholder or empty prompt means not editing. |
| Active spinner line | `✽ Ionizing…`, `✻ Ionizing…`, `· Vibing…`, `✢ Vibing…`, `✽ Frolicking…`, `✶ Frolicking…`, `· Skedaddling…`, `* Skedaddling…` | active evidence (`thinking_line`) | The rotating symbol and the `…` form are the reliable cue. The verb text changes across versions and should not be treated as the stable contract. |
| Response block | `● READY`, `● RECOVERED` | success candidate and settled success | Treat `● <payload>` in the latest-turn region as response-block success evidence. It still counts even when the current empty prompt is visible below it. |
| Interrupted-ready status | `⎿ Interrupted · What should Claude do instead?` | ready/interrupted posture | This is the real interrupted-ready surface. It can appear while the next prompt draft is already visible below it. |
| Footer interrupt hint | `⏵⏵ bypass permissions on (shift+tab to cycle) · esc to…` | supporting context only | This can coexist with active surfaces, but it is not a sufficient active cue by itself. Use the spinner line as the primary active authority. |
| Ready footer / installer notice | `⏵⏵ bypass permissions on (shift+tab to cycle)`, `Claude Code has switched from npm to native installer.` | supporting context only | These lines are not active authority and must not suppress a real stable response block. |

## Signal Meanings Used Today

### Ready placeholder

Typical surface:

- latest prompt anchor visible
- no real draft text in the current prompt
- no current spinner line
- no current interrupted-ready line

Tracker meaning:

- `surface_accepting_input=yes`
- `surface_editing_input=no`
- `surface_ready_posture=yes`
- `turn_phase=ready`
- `last_turn=none`

### Ready draft

Typical surface:

- latest prompt anchor contains real user-authored text
- no current spinner line
- no current interrupted-ready line for the same turn

Tracker meaning:

- `surface_accepting_input=yes`
- `surface_editing_input=yes`
- `surface_ready_posture=yes`
- `turn_phase=ready`
- newer-turn authority clears stale `last_turn`

Important reliability rule:

- If an older interrupted line is still visible above the current prompt but outside the latest-turn region, it is stale and must not keep the new draft in `last_turn=interrupted`.

### Active turn without overlapping draft

Typical surface:

- spinner line visible in the latest-turn region
- current prompt row is empty or placeholder-only

Tracker meaning:

- `turn_phase=active`
- `surface_editing_input=no`
- `last_turn=none`

### Active turn with overlapping draft

Typical surface:

- spinner line visible above
- latest prompt anchor contains newer user-authored draft text below

Concrete example from the complex capture:

- upper region: `✢ Vibing…`
- lower prompt: `❯ Now search this repository for files related to terminal recording ...`

Tracker meaning:

- `turn_phase=active`
- `surface_editing_input=yes`
- visible newer draft still clears stale terminal state

This is one of the most important Claude-specific overlap cases. Older-turn activity must not downgrade the visible current draft to `surface.editing_input=unknown`.

### Interrupted ready

Typical surface:

- status line `⎿ Interrupted · What should Claude do instead?`
- prompt is visible for follow-up input

Tracker meaning:

- `turn_phase=ready`
- `last_turn_result=interrupted`
- `last_turn_source=explicit_input` when it follows an intentional interrupt

Operational note:

- For fixture authoring, the first visible interrupted-ready occurrence is sufficient. Do not wait for a repeated footer or summary line if the interrupted status line is already visible.

### Settled success

Typical surface:

- response block `● READY` or `● RECOVERED`
- no current spinner line
- current prompt is visible and ready again
- surface remains stable long enough to satisfy the settle window

Tracker meaning:

- `turn_phase=ready`
- `last_turn_result=success`
- `last_turn_source=explicit_input`

Operational note:

- The native-installer footer notice may still be visible below the prompt. That notice is context, not a reason to reject the success surface.

## Cues That Are Not Authoritative By Themselves

- The changing working-summary verb such as `Ionizing…`, `Vibing…`, `Frolicking…`, or `Skedaddling…` is not the stable part of the contract. Use the rotating leading symbol plus ellipsis structure instead.
- Footer lines alone are not enough to decide active vs ready.
- Old interrupted or failure-looking transcript lines above the previous non-empty prompt are stale until proven otherwise.
- Historical slash-command or menu text in scrollback is not enough to keep the current prompt classified as modal once a fresh normal prompt has recovered.

## Practical Checklist

When investigating a Claude tracking bug from pane snapshots:

1. Find the latest visible `❯` prompt anchor.
2. Scope the latest-turn region against the previous non-empty prompt.
3. Look for a spinner line in that region first when deciding active.
4. Look for `⎿ Interrupted · What should Claude do instead?` in that region when deciding interrupted-ready.
5. Look for `● <payload>` in that region when deciding success candidate or settled success.
6. Decide whether the current prompt is real draft text, placeholder, or empty.
7. Treat footer hints and notices as supporting context only unless another maintained doc explicitly says otherwise.
