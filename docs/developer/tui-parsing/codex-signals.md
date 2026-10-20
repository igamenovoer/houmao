# Codex Signal Reference

This page records the concrete visible Codex TUI signals the repository currently uses when tracking tmux-backed Codex surfaces reliably. It is intentionally closer to source than the higher-level parser and runtime contract pages.

Use it together with:

- [Shared Contracts](shared-contracts.md)
- [Codex](codex.md)
- [Runtime Lifecycle](runtime-lifecycle.md)
- [Hook Observation Channel](../houmao-server/state-tracking.md#hook-observation-channel)

The concrete examples here were confirmed from the maintained complex capture logged in [20260323-124129.md](../../../context/logs/runs/20260323-124129-robust-tui-turn-lifecycle-quality-gate-signals/20260323-124129.md) and updated for Codex 0.162.x from the blind-labeled 0.162.1 recordings of the [2026-10-12 codex TUI parsing campaign](../../../context/campaigns/debug/2026-10-12-codex-tui-parsing/), which is the current qualification evidence. The hook adapter contract below was validated against codex-cli 0.163.0 in the [2026-10-20 Codex hook observation campaign](../../../context/campaigns/debug/2026-10-20-codex-hook-observation/), with the trust hash mirroring `extern/orphan/codex/codex-rs/hooks/` (`src/lib.rs`, `src/events/common.rs`, and `src/events/session_end.rs`).

## Hook Observation Support

Hook observation is an optional second signal source for managed Codex `local_interactive` sessions. Its supported floor is Codex 0.162.1 or later, the same floor used for TUI tracking: the Codex launch policy declares `supported_versions: ">=0.162.1"` in `src/houmao/agents/launch_policy/registry/codex.yaml`, and Codex hooks are stable and enabled by default across that range. The channel is opt-in and off by default. Enable the Codex adapter for new managed launches with `HOUMAO_HOOK_OBSERVATION_CODEX=1`; only the exact value `1` enables it, and any other value leaves TUI-only behavior unchanged. The adapter covers the managed `local_interactive` backend. `codex_headless`, joined sessions, unmanaged launches, and Kimi do not get this adapter; Claude uses the separate `HOUMAO_HOOK_OBSERVATION_CLAUDE` flag described in the [Claude Signal Reference](claude-signals.md#hook-observation-support).

### Event Set

The observer subscribes all 14 Codex hook events with one synchronous command handler each. Every handler runs the packaged emitter, which posts to the loopback collector and falls back to a file append; handlers always exit 0 and write nothing to standard output. Matchers are omitted so each handler observes every occurrence. `SessionEnd` uses a 2-second timeout inside Codex's 1-3 second clamp, and every other event uses 5 seconds.

| Event | Dispatched at the supported floor | Posture contribution |
|---|---|---|
| `SessionStart` | Yes, lazily at first turn start | Opens the session; `source` is `startup`, `resume`, `compact`, `clear`, or `fork` |
| `UserPromptSubmit` | Yes | Arms a turn; a second event carrying the running `turn_id` is steered input, not a new turn |
| `PreToolUse` | Yes | Starts a tool call keyed by `tool_use_id` |
| `PermissionRequest` | Yes | Enters `blocked`; carries no `tool_use_id`, so it pairs back to the preceding `PreToolUse` in the same turn by tool name and `tool_input.command` |
| `PostToolUse` | Yes | Completes the tool call and settles an allow-path blocked wait |
| `PreCompact` | Yes | Opens a maintenance window; `trigger` is `manual` or `auto` |
| `PostCompact` | Yes | Closes the maintenance window |
| `Stop` | Yes | Latches turn success; `stop_hook_active=true` marks a non-terminal stop |
| `Interrupt` | Yes | Settles `interrupted`; also the deny path of an approval modal |
| `SessionEnd` | Yes | Ends presence; an open turn becomes a terminal gap |
| `PreModelRequest` | No | Counted as an unavailable event family |
| `PostModelRequest` | No | Counted as an unavailable event family |
| `SubagentStart` | No | Counted as an unavailable event family |
| `SubagentStop` | No | Counted as an unavailable event family |

The four non-dispatching events stay subscribed for forward compatibility. The reducer counts them as unavailable families in diagnostics and does not fail or degrade because of their silence. No model-request event and no `Stop` payload carries token usage, and no Codex payload exposes background-task state, so the `work` axis stays `unknown` for Codex sessions and hooks alone never produce `settled`. Codex also has no hook failure event at this floor, so a hook-settled `known_failure` remains Claude-only; a Codex stream that ends without `Stop`, `Interrupt`, or `SessionEnd` leaves the open turn truthfully `unknown`.

### Trust Model

Codex requires a trust decision for every hook handler. The managed launch writes the observer `hooks.json` into the runtime-owned `CODEX_HOME` and pre-trusts each handler with a Houmao-owned `[hooks.state."<absolute hooks.json path>:<snake_case event label>:<group index>:<handler index>"]` table carrying a `trusted_hash` value in the runtime-home `config.toml`. The generated hash reproduces Codex's own normalization: the matcher is kept only for matcher-capable events, the timeout is normalized (including the `SessionEnd`/`Interrupt` clamp), `commandWindows` is cleared, and `additionalContextLimit` is retained only for context-capable events and only when non-default.

The pre-trust block is marker-delimited and generation-scoped, rewritten at every provider start. Cleanup removes the block and the observer `hooks.json` while preserving operator-authored `hooks.state` entries and every other `config.toml` line. The managed path does not add `--dangerously-bypass-hook-trust`, does not write the operator's Codex home or profile, and requires no operator action. The bypass flag remains a manual-lane fallback only. If either runtime-home surface cannot be written safely, the channel reports `unavailable` and the launch proceeds TUI-only.

### Collector And Store

Each opted-in session runs one collector process bound to `127.0.0.1` on an ephemeral port, using the same implementation as the Claude adapter but scoped to `<session_root>/hook-observation/codex/`. Deliveries authenticate with a per-session bearer token; the token reaches the provider through a `0600` launch wrapper rather than the launch plan environment. The collector appends accepted events to `events.ndjson` with owner-only permissions and publishes the secret-free `channel.json` and `collector.json` alongside it. Tracking consumers tail the file with their own offsets.

### Channel States And Troubleshooting

Read the current state from `observation_channels[0].state` (or `diagnostics.hook_channel_state`) on the terminal state response, or from `observation_channels` on gateway status. A passive server that cannot see the session root reports `state="unavailable"` with `detail="remote observation"`.

| State | What it means | What to check |
|---|---|---|
| `active` | Current-generation events are arriving; hook facts have lifecycle authority. | No action. |
| `unavailable` | No event yet, the 15-second startup grace elapsed with no event, the install failed, or the store is remote. Because `SessionStart` is lazy, an idle session can legitimately show `unavailable` before its first prompt. | Confirm `HOUMAO_HOOK_OBSERVATION_CODEX=1`, a managed Codex `local_interactive` launch, and Codex at or above 0.162.1. Read `channel.json` `install.detail`, verify the observer `hooks.json` and the pre-trust block in the runtime-home `config.toml`, and confirm the provider process inherited `HOUMAO_HOOK_TOKEN`. |
| `stale` | The channel was active, then delivered no event for more than 30 seconds while the visible TUI kept changing. TUI regains lifecycle authority. | Confirm the collector is alive in `collector.json` and answers `/health`, check whether `events.ndjson` is still growing, and verify the pre-trust block survived the latest `config.toml` rewrite. A hook-latched terminal result persists through the stale window. |
| `error` | The event store could not be read. | Check ownership and permissions on `<session_root>/hook-observation/codex/`. A read failure clears on the next healthy read; an `error` published in channel metadata is terminal. |
| `stopped` | The collector stopped or the session stopped. Terminal. | Expected at session stop. If it appears mid-session, the collector died; a same-generation `collector.json` record with `status=stopped` is detected on the next poll cycle. |
| `disabled_by_policy`, `untrusted_workspace` | Terminal policy states consumed from channel metadata. | The managed Codex launch path does not publish these today; honor them if an external producer does. The session remains TUI-only. |

A provider upgrade that changes the trust hash algorithm or event names makes Codex skip the untrusted handlers silently. The channel detects this as startup event silence with a live collector, reports `unavailable` (a degraded channel), and keeps tracking TUI-only; a channel that was already active and then loses events follows the ordinary staleness rule to `stale`. The trust-hash fixture tests pin Codex's published vectors, so an upstream algorithm change fails CI before a production launch silently loses hooks.

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
