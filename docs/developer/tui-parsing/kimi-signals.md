# Kimi Signal Reference

This page records the concrete visible Kimi Code TUI signals and the hook observation adapter contract the repository uses when tracking tmux-backed Kimi surfaces reliably. It is intentionally closer to source than the higher-level parser and runtime contract pages.

The maintained TUI detector is `KimiCodeSignalDetectorV2_1_X` in [`src/houmao/shared_tui_tracking/apps/kimi_code/profile.py`](../../../src/houmao/shared_tui_tracking/apps/kimi_code/profile.py). It is qualified against the frozen 2026-10-10 campaign recordings of Kimi Code 2.1.1 in [`context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/`](../../../context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/), with one maintained profile at or above the 2.1.1 floor and no fallback detector. The hook adapter contract below was established at Kimi Code 2.2.0 by the [2026-10-20 Kimi hook observation campaign](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/reports/2026-10-20-kimi-hook-observation-synthesis.md); the managed-launch live smoke repeated the multi-turn leg at the 2.1.1 floor. See [`tests/manual/manual_kimi_hook_observation_smoke.py`](../../../tests/manual/manual_kimi_hook_observation_smoke.py).

Use it together with:

- [Shared Contracts](shared-contracts.md)
- [Runtime Lifecycle](runtime-lifecycle.md)
- [Hook Observation Channel](../houmao-server/state-tracking.md#hook-observation-channel)
- [State Reference](../houmao-server/state-reference.md)

## Hook Observation Support

Hook observation is an optional second signal source for managed Kimi `local_interactive` sessions. Its supported floor is Kimi Code 2.1.1 or later, the same floor used for TUI tracking: the Kimi launch policy declares `supported_versions: ">=2.1.1"` in [`src/houmao/agents/launch_policy/registry/kimi.yaml`](../../../src/houmao/agents/launch_policy/registry/kimi.yaml), and the detector registry registers `kimi_code` at the same floor. The full enriched hook payload contract has existed since upstream 0.32.0 (2026-08-04), below the registry floor, so every supported version can carry the channel.

The channel is opt-in and off by default. Enable the Kimi adapter for new managed launches with `HOUMAO_HOOK_OBSERVATION_KIMI=1`; only the exact value `1` enables it, and any other value leaves TUI-only behavior unchanged. The adapter covers the managed `local_interactive` backend only. `kimi_headless`, joined sessions, and unmanaged launches do not get this adapter. Claude and Codex use the separate adapters described in the [Claude Signal Reference](claude-signals.md#hook-observation-support) and the [Codex Signal Reference](codex-signals.md#hook-observation-support).

The managed-launch live smoke passed all legs at Kimi Code 2.2.0 and repeated the multi-turn leg at the 2.1.1 floor: multi-turn success, Escape interrupt, manual compaction with a post-compact turn, and a provider `kill -9` terminal gap. Each leg verified tracked state, channel health, and the secret-free public projection.

### Event Set

The observer subscribes all 20 Kimi hook events with one synchronous command entry each. Every entry runs the packaged emitter, which posts to the loopback collector and falls back to a file append; handlers always exit 0 and write nothing to standard output, because Kimi appends non-empty `UserPromptSubmit` hook stdout to model context. `matcher` is omitted so each entry observes every occurrence, and every entry uses a 5-second timeout.

| Event | Campaign status at 2.2.0 | Posture contribution |
|---|---|---|
| `SessionStart` | TUI and headless | Opens presence; `source` is `startup` or `resume` (fresh TUI delivery is lazy) |
| `UserPromptSubmit` | All prompt arms | Arms a turn epoch; `prompt` arrives as a `ContentPart[]` array |
| `TurnStarted` | Every turn, including nested subagent turns | Binds the integer `turn_id` when `origin_kind=user`; a `system_trigger` turn opens a nested scope |
| `UserPromptQueued` | Ctrl-S steer | Records queue evidence only; steered input produces no second `UserPromptSubmit` |
| `PreToolUse` | Bash, Write, Read, Agent | Starts a tool call keyed by `tool_call_id` |
| `PostToolUse` | Allow, read, and agent calls | Completes the tool call with a string `tool_output` |
| `PostToolUseFailure` | Deny path | Records the denied call; non-terminal |
| `PermissionRequest` | Ask permission policy only | Enters `blocked`; carries `tool_call_id` and `turn_id` |
| `PermissionResult` | Ask permission policy only | Settles `blocked` for `approved` and `rejected` |
| `Stop` | Completed turns | Latches success; `stop_hook_active=true` is a defensive non-terminal continuation; carries no `turn_id` |
| `StopFailure` | Never observed | Defensive `known_failure` mapping; carries no campaign evidence |
| `Interrupt` | Escape interrupt | Latches `interrupted`; `reason=cancelled`; no `Stop` follows |
| `SessionEnd` | TUI clean exits only | Loses presence; an open turn becomes a terminal gap; not emitted by headless `-p` |
| `SessionHeartbeat` | Long sessions | Presence and liveness evidence only, at a 60-second cadence |
| `PreCompact` | Manual `/compact` | Opens a maintenance window; carries `trigger` |
| `PostCompact` | Manual `/compact` | Closes the maintenance window |
| `SubagentStart` | Agent tool | Opens a nested subagent scope |
| `SubagentStop` | Agent tool | Closes the nested scope |
| `TaskStarted` | Never observed | Tolerated and counted as an unseen family |
| `Notification` | Never observed | Tolerated and counted as an unseen family |

The unseen families stay subscribed for forward compatibility, and the normalizer counts them in diagnostics instead of failing. Permission events exist only under an ask permission policy; `--auto` and print-mode sessions legitimately produce none, which is normal absence rather than a channel fault. `Stop` carries no background-task payload and `SessionHeartbeat` is not work evidence, so the adapter publishes `work=unknown` for every sample and hooks alone never produce `settled`.

### Observer Injection

The launch merges a marker-delimited, generation-scoped `[[hooks]]` observer block into the launch-owned `KIMI_CODE_HOME/config.toml` after launch-policy field synthesis. The block is rewritten at every provider start and removed on cleanup, and every byte outside the block, including operator-authored `[[hooks]]` entries, is preserved. The command is an absolute, POSIX shell-quoted invocation of the packaged emitter with the collector URL, artifact directory, and channel generation baked into argv; the bearer token reaches the provider through the launch wrapper and never appears in the command.

Kimi has no hook trust mechanism. The managed path needs no trust pre-seed, no bypass flag, and no operator action. The provider loads its hook table once per process, so install-before-start ordering is sufficient; a mid-session append or edit has no effect until restart, and there is no hot-reload recovery path.

Kimi validates the hooks section against its own schema and silently voids the entire section when any entry carries an unknown key, an unknown event name, or an invalid timeout. The TUI shows no warning; only print-mode stderr carries the diagnostic. The installer therefore validates the merged file by strict `tomllib` read-back before launch:

- every entry key must be in `{event, matcher, command, timeout}`
- every `event` must be in the pinned 20-name enum
- every `timeout` must be an integer in `1..600`

Any violation restores the pre-install text and reports the channel as `unavailable`; the launch proceeds TUI-only instead of carrying a dead channel. See [`src/houmao/hook_observation/kimi_hooks_generator.py`](../../../src/houmao/hook_observation/kimi_hooks_generator.py) for the render, merge, strip, and validation implementation.

### Collector And Store

Each opted-in session runs one collector process bound to `127.0.0.1` on an ephemeral port, using the same implementation as the Claude and Codex adapters but scoped to `<session_root>/hook-observation/kimi/`. Deliveries authenticate with a per-session bearer token. The collector appends accepted events to `events.ndjson` with owner-only permissions and publishes the secret-free `channel.json` and `collector.json` alongside it. Tracking consumers tail the file with their own offsets. When the collector is unreachable, the emitter appends a `via: command_fallback` row with `sequence: null` and a flock-protected `emitter_seq` so arrival order survives; fallback rows normalize identically to HTTP rows.

### Channel States And Troubleshooting

Read the current state from `observation_channels[0].state` (or `diagnostics.hook_channel_state`) on the terminal state response, or from `observation_channels` on gateway status. A passive server that cannot see the session root reports `state="unavailable"` with `detail="remote observation"`.

| State | What it means | What to check |
|---|---|---|
| `active` | Current-generation events are arriving; hook facts have lifecycle authority. | No action. |
| `unavailable` | No event yet, the startup grace elapsed with no event after the first prompt, the install failed read-back validation, or the store is remote. | Confirm `HOUMAO_HOOK_OBSERVATION_KIMI=1`, a managed Kimi `local_interactive` launch, and Kimi at or above 2.1.1. Read `channel.json` `install.detail`, verify the `# >>> houmao kimi hook observation` block in the runtime-home `config.toml`, and confirm the provider process inherited `HOUMAO_HOOK_TOKEN`. |
| `stale` | The channel was active, then delivered no event for more than 30 seconds while the visible TUI kept changing. TUI regains lifecycle authority. | Confirm the collector is alive in `collector.json` and answers `/health`, check whether `events.ndjson` is still growing, and verify the observer block survived the latest `config.toml` rewrite. A hook-latched terminal result persists through the stale window. |
| `error` | The event store could not be read. | Check ownership and permissions on `<session_root>/hook-observation/kimi/`. A read failure clears on the next healthy read; an `error` published in channel metadata is terminal. |
| `stopped` | The collector stopped or the session stopped. Terminal. | Expected at session stop. If it appears mid-session, the collector died; a same-generation `collector.json` record with `status=stopped` is detected on the next poll cycle. |
| `disabled_by_policy`, `untrusted_workspace` | Terminal policy states consumed from channel metadata. | The managed Kimi launch path does not publish these today; honor them if an external producer does. The session remains TUI-only. |

Kimi's `SessionStart` is awaited at session creation, but a fresh TUI creates its session lazily on the first message, so the first event arrives after the first prompt. A resumed session restores at launch and delivers `SessionStart(resume)` before the first prompt. Judge startup event silence after the first prompt, never at launch. A provider upgrade that renames or removes an event makes Kimi void the whole section silently; the install-time read-back guard is the deterministic tripwire, and runtime startup silence after the first prompt is the backstop.

## Interaction With The 2.1.x Detector Profile

The hook adapter and the TUI detector stay independent signal sources. `surface.*` remains TUI-owned, and hook facts merge only at the host projection layer.

- The 2.1.x profile renders approval panels as `active_evidence` with an `approval_panel` reason and, for modal surfaces, a `modal_blocked` reason; `turn.phase` stays `active`. Hook `PermissionRequest` is the only way to publish `blocked`, exactly as for the other adapters.
- The profile's static interrupt needle is the `Interrupted by user` (or `Step interrupted`) notice, and it suppresses that signal when concurrent activity is visible. Hook `Interrupt(cancelled)` is authoritative for the aborted turn and settles `interrupted`; the TUI repaint is corroboration.
- The profile treats `● Compacting context…` as active evidence. Hook `PreCompact`/`PostCompact` hold posture across the window, suppress TUI idle heuristics, and the post-compact turn binds a fresh `turn_id`; Kimi emits no `SessionStart(source=compact)`.
- The profile has no temporal transcript-growth channel at 2.1.x (`temporal_window_seconds=0.0`, `enable_temporal_growth=False`); activity comes from live-edge spinner labels, compaction bullets, approval surfaces, and queued-message hints. Hook events do not add TUI activity evidence.
- Queued input is visible in the editor footer (`↑ to edit · ctrl-s to steer immediately`, `will send after current task`, `will send after compaction`) and is also reported by `UserPromptQueued`. Both describe the same queue; the hook event is the durable correlation evidence.
- A degraded or unavailable channel reverts every hook-owned fact to TUI-only reduction: no `blocked`, no hook terminal settlement, `work=unknown`, and the profile's idle heuristics resume their normal authority.

## Turn Correlation Rules

Kimi correlation is identifier-and-ordering based, and the normalizer owns these rules:

- `UserPromptSubmit` arms a new epoch. The following `TurnStarted(origin_kind=user)` binds the integer, session-scoped `turn_id`. The counter continues across `--continue` resume (generation 2 starts at 1 when generation 1 ended at 0).
- `turn_id` is absent on `UserPromptSubmit`, `Stop`, and all tool events. Those attribute to the currently armed epoch by stream order. Tool cycles pair directly by `tool_call_id`, with no pair-back heuristic.
- `PermissionRequest` and `PermissionResult` carry both `tool_call_id` and `turn_id`, so the blocked window is identifier-based. The allow path is `PreToolUse → PermissionRequest → PostToolUse → PermissionResult → Stop`; the deny path is `PreToolUse → PermissionRequest → PermissionResult → PostToolUseFailure → Stop`.
- `UserPromptQueued` records `prompt_id`, `prompt`, and `queue_length` as queue evidence only. A Ctrl-S steered message produces no second `UserPromptSubmit` and no second `Stop`.
- `SubagentStart`/`SubagentStop` and a nested `TurnStarted(origin_kind=system_trigger, origin_name=subagent)` open and close nested scopes. Subagent `turn_id` values collide with the parent's, so scope, not id, disambiguates them.
- `SessionStart` and `SessionEnd` are generation boundaries. A resumed session starts a new channel generation with no open turn and `last_turn=none` until new hook evidence arrives.

## Campaign Evidence

The durable evidence for this adapter lives in `context/campaigns/debug/2026-10-20-kimi-hook-observation/`:

- [Synthesis report](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/reports/2026-10-20-kimi-hook-observation-synthesis.md): replay results, corrections, and the merged transition model.
- [Payload catalog](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-kimi-hook-payload-catalog.md): per-event fields and availability by permission mode at 2.2.0.
- [S0 gate smoke](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s0-gate-smoke.md): zero-operator injection and lazy `SessionStart`.
- [S2 malformed control](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s2-malformed-control.md): the silent whole-section drop that motivates strict read-back.
- [S3 permission lane](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s3-permission-lane.md): allow and deny ordering, result-settled windows.
- [S5 interrupt](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s5-interrupt.md): `Interrupt(cancelled)` with no `Stop`.
- [S6 queue and steer](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s6-queue-steer.md): `UserPromptQueued` without a second prompt submit.
- [S7 resume and hot reload](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s7-resume-hot-reload.md): the continuing `turn_id` counter and the load-once hook table.
- [S8 headless](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s8-headless.md): hooks fire in `-p`, and `SessionEnd` is absent.
- [S9 subagent](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-s9-subagent.md): nested scopes and colliding `turn_id` values.
- [F1 terminal gap](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-f1-sigkill-terminal-gap.md): `kill -9` mid-turn produces a truthful `unknown` terminal gap.
- [D1 transport fault](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-d1-transport-fault.md): collector death falls back to ordered file appends.
- [T1 slow lifecycle](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/evidences/2026-10-20-t1-slow-lifecycle.md): awaited lifecycle hooks add their full duration to session create and exit.

The upstream schema and event enum live under `extern/orphan/kimi-code/packages/agent-core-v2/src/features/externalHooks/configSection.ts` and `extern/orphan/kimi-code/packages/agent-core-v2/src/features/externalHooks/internal/types.ts`.
