# Claude Signal Reference

This page records the concrete visible Claude Code signals the repository currently uses when tracking tmux-backed Claude surfaces reliably. It is intentionally closer to source than the higher-level parser and runtime contract pages.

The current contract is qualified against Claude Code 2.1.296 (the support floor) on the frozen 2026-10-12 campaign recordings; see the [campaign repair report](../../../context/campaigns/debug/2026-10-12-claude-code-tui-parsing/reports/2026-10-12-claude-2-1-296-parsing-repair.md) for the evidence base. Claude below 2.1.296 raises `UnsupportedToolVersionError` at tracker resolution; there is no claude fallback detector.

Use it together with:

- [Shared Contracts](shared-contracts.md)
- [Claude](claude.md)
- [Runtime Lifecycle](runtime-lifecycle.md)
- [Hook Observation Channel](../houmao-server/state-tracking.md#hook-observation-channel)

## Hook Observation Support

Hook observation is an optional second signal source for managed Claude `local_interactive` sessions. Its supported floor is Claude Code 2.1.296 or later, the same floor used for TUI tracking: the Claude launch policy declares `supported_versions: ">=2.1.296"` in `src/houmao/agents/launch_policy/registry/claude.yaml`, and the detector registry sets the Claude minimum supported version to `(2, 1, 296)` in `src/houmao/shared_tui_tracking/registry.py`. The hook installer itself does not re-check the version, so do not enable the channel on an unsupported Claude build. The channel is opt-in and off by default. Enable it for new managed launches with `HOUMAO_HOOK_OBSERVATION_CLAUDE=1`; only the exact value `1` enables it, and any other value leaves TUI-only behavior unchanged. v1 is Claude-only and covers the managed `local_interactive` backend. `claude_headless`, joined sessions, unmanaged launches, Codex, and Kimi do not get a channel.

### v1 Event Set

The observer subscribes to nine provider events. `SessionStart` uses a command handler because HTTP hooks cannot deliver it; the other eight use HTTP handlers that post to the loopback collector.

| Event | Delivery | Posture contribution |
|---|---|---|
| `SessionStart` | Command hook (`houmao.hook_observation.emitter`) | Opens the session and can reset turn state for `startup`, `clear`, and `fork` sources |
| `UserPromptSubmit` | HTTP | Arms a prompt; a provider-synthesized `<task-notification>` prompt marks a ghost turn rather than operator input |
| `Stop` | HTTP | Latches a successful terminal and updates the background-work axis from its payload |
| `StopFailure` | HTTP | Latches a `known_failure` terminal with the provider error class |
| `PermissionRequest` | HTTP | Enters the hook-only `blocked` phase |
| `PreCompact` | HTTP | Opens a maintenance window |
| `PostCompact` | HTTP | Closes the maintenance window |
| `PostToolUse` | HTTP | Records activity and resolves an outstanding permission wait |
| `PostToolUseFailure` | HTTP | Records activity and resolves an outstanding permission wait |

`PreToolUse`, `PostToolBatch`, `SubagentStart`, `SubagentStop`, `Notification`, and `SessionEnd` are not subscribed in v1.

### Observer Injection

The primary injection path is a marker merge into the managed home's `settings.json` (the `CLAUDE_CONFIG_DIR` user-settings layer). The installer identifies Houmao-owned entries by the `/v1/hook` URL path or the `houmao.hook_observation.emitter` module, replaces stale observer entries, and preserves operator, bundle, and plugin hook entries. It rewrites the block at every provider start and relaunch generation, so a reused home is repaired in place and receives the new collector port and generation.

When the managed home settings file cannot be safely merged, the installer falls back to a session-scoped `--settings <session_root>/hook-observation/claude/observer-settings.json` argument. If neither path is safe (for example the resolved launch arguments already carry a `--settings` source), the channel reports `unavailable` and the session continues TUI-only. The observer block never embeds the bearer token: HTTP handlers reference `$HOUMAO_HOOK_TOKEN` through the provider's `allowedEnvVars` mechanism, and the token reaches the provider process through a `0600` launch wrapper rather than the launch plan environment.

### Workspace Trust

Claude withholds hooks for an untrusted workdir. At 2.1.296 the workspace trust dialog still renders even under `--dangerously-skip-permissions`, so the seeded trust keys are load-bearing. Managed Claude launches run `claude.ensure_project_trust`, which seeds the project entry in `.claude.json`:

- `projects.<resolved_workdir>.hasCompletedProjectOnboarding`
- `projects.<resolved_workdir>.hasTrustDialogAccepted`
- `projects.<resolved_workdir>.projectOnboardingSeenCount`

If trust is missing, no `SessionStart` event arrives and the channel stays `unavailable`. The current managed-launch path does not publish `untrusted_workspace` itself; that state is a defined terminal channel state that consumers honor when channel metadata carries it. Do not expect it to appear automatically on a managed launch today.

### Collector And Store

Each opted-in session runs one collector process bound to `127.0.0.1` on an ephemeral port. Deliveries go to `/v1/hook` with a bearer token; the collector also serves `/health`. Accepted events are stamped with `channel_generation`, `sequence`, and `received_at_utc` and appended to `<session_root>/hook-observation/claude/events.ndjson` with owner-only permissions. The directory also holds the secret-free `channel.json` status document and `collector.json` liveness record. Tracking consumers tail `events.ndjson` with their own offsets and fold new observations at their next read or poll cycle. The `SessionStart` command emitter always exits 0 and appends a fallback envelope directly to the store if HTTP delivery fails.

### Channel States And Troubleshooting

Read the current state from `observation_channels[0].state` (or `diagnostics.hook_channel_state`) on the terminal state response, or from `observation_channels` on gateway status. A passive server that cannot see the session root reports `state="unavailable"` with `detail="remote observation"`.

| State | What it means | What to check |
|---|---|---|
| `active` | Current-generation events are arriving; hook facts have lifecycle authority. | No action. |
| `unavailable` | No event yet, the 15-second startup grace elapsed with no event, the install failed, or the store is remote. | Confirm `HOUMAO_HOOK_OBSERVATION_CLAUDE=1`, a managed Claude `local_interactive` launch, and Claude at or above 2.1.296. Read `channel.json` `install.detail` for a settings conflict or collector-start failure, and inspect `collector.json` and `collector.log`. Confirm the provider process inherited `HOUMAO_HOOK_TOKEN`. |
| `stale` | The channel was active, then delivered no event for more than 30 seconds while the visible TUI kept changing. TUI regains lifecycle authority. | Confirm the collector is alive in `collector.json` and answers `/health`, check whether `events.ndjson` is still growing, and verify the hook block survived the latest settings rewrite. During the stale window, a hook-only terminal result is temporarily not shown; it returns when the channel recovers with the terminal still latched. |
| `untrusted_workspace` | Terminal trust state. Claude withheld hooks because the workspace is not trusted. | Verify the `claude.ensure_project_trust` seed in the managed `.claude.json` keys listed above, especially after a fresh scratch home or a changed workdir. The session remains TUI-only. |
| `disabled_by_policy` | Terminal state; hooks are disabled by policy or client mode. | Remove the disabling policy or client mode. The session remains TUI-only. |
| `error` | The event store could not be read. | Check ownership and permissions on `<session_root>/hook-observation/claude/`. A read failure clears on the next healthy read; an `error` published in channel metadata is terminal. |
| `stopped` | The collector stopped or the session stopped. Terminal. | Expected at session stop. If it appears mid-session, the collector died; a later resume starts a new generation when no live collector exists, and a live collector is reused without a generation bump. |

In v1, `untrusted_workspace` and `disabled_by_policy` are consumed from channel metadata but are not produced by the managed-launch path. The rows above describe how to respond if an external producer or a future launch path publishes them.

Unsetting the flag prevents new launches from starting a collector or installing observer settings. A reused managed home can still carry an observer block from an earlier generation; it points at a stopped collector and produces no observations. The next opted-in launch rewrites the block with the current port and generation.

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
