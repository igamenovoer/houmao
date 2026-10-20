# Design

## Context

The `cli-hook-observation` capability is in production for Claude and Codex: `src/houmao/hook_observation/` (collector, emitter, store, health, reader, per-adapter normalizers, reducer, settings/hooks generators, install) plus launch lifecycle in `src/houmao/agents/realm_controller/hook_observation_launch.py` and the tracking merge in `src/houmao/server/tui/tracking.py`. Per-adapter gating (`HOUMAO_HOOK_OBSERVATION_{CLAUDE,CODEX}`, `HOOK_OBSERVATION_PAIRS`, adapter-scoped artifact dirs) already exists; kimi is currently excluded by an explicit `{"claude", "codex"}` gate in `launch_plan.py`.

The 2026-10-20 campaign (`context/campaigns/debug/2026-10-20-kimi-hook-observation/`) established against kimi 2.2.0 across 14 live capture arms (113 events, 0 replay label mismatches): hooks are stable, configured via `[[hooks]]` in `$KIMI_CODE_HOME/config.toml`, and run unattended with **no trust mechanism**; 16 of 20 events fired live; the payload catalog, settle rules, and 11 dated rule amendments are recorded in the campaign report and KQ answers. The supported Kimi floor (`src/houmao/agents/launch_policy/registry/kimi.yaml`: `>=2.1.1`) already includes the full enriched payload contract (upstream 0.32.0), so every supported version can carry the channel. `KIMI_CODE_HOME` and `config.toml` are launch-owned surfaces today.

## Goals / Non-Goals

**Goals:**

- Managed Kimi `local_interactive` sessions get the hook observation channel with zero operator action (no trust step exists).
- One provider-neutral channel core; per-adapter generator, normalizer, and posture rules (third adapter after Claude and Codex).
- Kimi hook posture merges into tracked state per the campaign-validated rules, including hook-derived `interrupted` for Kimi.
- The installer's strict read-back validation makes the provider's silent-section-drop failure mode impossible to ship.

**Non-Goals:**

- `kimi -p` headless backend, ACP, and kap-server hook adoption (campaign verified hooks fire headless; the named `SessionEnd` gap and lifecycle wiring are follow-ups).
- `StopFailure`, `TaskStarted`, `Notification`, `PermissionResult(cancelled|error)` specialization (never exercised live; subscribed and tolerated as silent families).
- Changing Claude or Codex adapter behavior (Claude interrupted stays TUI-derived; Codex deny-aborts-turn rule unchanged for Codex).
- Background-task/`work`-axis signals (Kimi `Stop` carries no background payload).

## Decisions

### D1: Injection is a marker-delimited `[[hooks]]` merge into the runtime-home `config.toml` with strict read-back validation

The managed launch merges a Houmao-owned observer block (all 20 events, one entry each, matcher omitted, 5 s timeout, absolute emitter command) into the launch-owned `KIMI_CODE_HOME/config.toml` between marker comments, idempotently rewritten per generation and removed on teardown — the same lifecycle pattern as the Codex `[hooks.state]` block, on a file houmao already owns. Kimi has no trust gate, so there is nothing to pre-compute; the campaign's E1 control arms instead proved the two kimi-specific failure modes: one malformed entry silently voids the whole section (warning only, S2), and the hook table loads once per process (H1/S7). The installer therefore validates the merged file by strict `tomllib` read-back (keys subset of `{event, matcher, command, timeout}`, event in the pinned 20-name enum, timeout int in 1..600) and degrades to `unavailable` on any violation rather than launching a dead channel. Alternatives considered: plugin-manifest hooks (rejected — requires shipping a plugin, heavier than config); project-local `local.toml` (rejected — hooks are not supported there, only `[workspace] additional_dir`).

### D2: Read-back validation is the install-time tripwire; event silence is the runtime one

The provider validates the hooks section against *its* schema at load and drops the whole section with only a warning on mismatch, so a future kimi version that renames or removes an event would kill the channel silently. Two-layer defense: the installer's read-back guard catches houmao-side generation defects deterministically, and the runtime channel treats missing `SessionStart` after the first prompt (with collector liveness) as `degraded`, exactly as the Codex adapter treats hash drift. Kimi's hook table loads once at process start, which makes install-before-launch ordering sufficient — no reload race exists.

### D3: One channel core, third adapter registration

Collector, store, health, reader, emitter transport, and launch-collector lifecycle are reused unchanged. Per-adapter pieces: `kimi_hooks_generator.py` (config.toml block render/merge/validate/remove), `kimi_normalizer.py`, Kimi posture rules in the reducer, adapter-scoped artifact dir (`<session_root>/hook-observation/kimi/`), `HOUMAO_HOOK_OBSERVATION_KIMI` env flag, and `("kimi", "local_interactive")` in `HOOK_OBSERVATION_PAIRS`. Channel attach follows the Codex precedent (lazy `ensure_hook_channel_from_session_root`; no eager-attach change in `service.py`/`ownership.py`).

### D4: Subscribe all 20 events; tolerate silent families

The observer subscribes every Kimi event (sync semantics via the emitter contract, 5 s timeout, exit-0-silent). `StopFailure`, `TaskStarted`, `Notification`, and the `cancelled`/`error` permission variants were never exercised live (campaign leftovers) but stay subscribed for forward-compatibility; the normalizer counts unseen/unknown families in diagnostics instead of failing. The emitter contract is unchanged: read stdin to EOF, POST-or-file-fallback, always exit 0, empty stdout (Kimi appends non-empty stdout to model context on the `UserPromptSubmit` allow path).

### D5: Kimi normalizer maps via arm/bind turn correlation and `tool_call_id` pairing

Kimi `turn_id` is an integer, session-scoped counter that continues across `--continue` resume (campaign replay correction: generation 2 starts at 1, not 0) and is present only on `TurnStarted`, `PermissionRequest`/`PermissionResult`, and `Interrupt`. Correlation is therefore two-phase: `UserPromptSubmit` arms an epoch, the following `TurnStarted(origin_kind=user)` binds its `turn_id`; tool events and `Stop` attribute to the armed epoch by stream ordering. `prompt` arrives as a ContentPart[] array and is collapsed to joined text (raw shape kept in diagnostics). Tool cycles pair by `tool_call_id` directly (no pair-back heuristic — that was Codex-specific). `UserPromptQueued` records queue evidence; no second `UserPromptSubmit` arrives for steered input. `SubagentStart`/`SubagentStop` and nested `TurnStarted(origin_kind=system_trigger)` open/close nested scopes because subagent `turn_id` collides with the parent's. `SessionHeartbeat` is liveness evidence only.

### D6: Kimi posture rules follow the campaign amendments

Full rules live in [`design/state-transitions.md`](design/state-transitions.md). Headline: `Stop` latches success (defensive `stop_hook_active` continuation); `Interrupt(reason=cancelled)` settles `interrupted`; `PermissionRequest` enters `blocked` and settles at `PermissionResult` for both decisions — deny is followed by `PostToolUseFailure` and the turn continues to `Stop` (Kimi deny is non-terminal, unlike Codex's deny-aborts-turn); permission events exist only under an ask policy, so never-ask sessions legitimately have none; `PreCompact`/`PostCompact` hold posture and the post-compact turn mints a fresh `turn_id` with no `SessionStart(source=compact)`; stream end or `SessionEnd` with an open turn is a terminal gap — presence lost, turn truthfully `unknown`, never success; heartbeat cessation is liveness loss at 60 s granularity.

### D7: Hook-derived `interrupted` for Kimi, extending the Codex carve-out

The tracked-state spec's TUI-derived-interrupted rule already carves out the Codex adapter. The delta extends that carve-out to Kimi: kimi's `Interrupt` is authoritative (Esc fires it within ~50 ms of the keypress; the TUI merely repaints). Claude sessions keep TUI-derived interrupted. Gateway prompt admission already treats `blocked` generically and needs no change.

### D8: Launch wiring reuses the existing lifecycle; kimi.yaml gains the owned hooks surface

`hook_observation_launch.py` adds the Kimi install branch (merge + validate the `[[hooks]]` block); collector start/token/wrapper machinery runs unchanged (token and collector coordinates travel in the launch wrapper env, never `plan.env`). `launch_plan.py` opens its adapter gate to kimi. `registry/kimi.yaml` documents the owned `[[hooks]]` block in `config.toml` and the evidence refs. Install runs after the launch policy's own `config.toml` synthesis and before provider start; the launch policy's kimi canonicalizers strip CLI args, not `config.toml` sections, but a regression test pins the coexistence both write orders (campaign leftover P1.4).

### D9: Degradation mirrors the existing adapters

Any install/collector failure degrades to `unavailable` and the session launches TUI-only. The emitter's 1.5 s POST timeout sits far inside the 5 s hook budget, and the campaign's T1 arm quantified the awaited-lifecycle cost (a 3 s hook delays session create and exit by ~3 s each), so the observer's speed is a correctness property, not a nicety. Heartbeat loss alone never fails the channel (60 s cadence is too coarse); it is supplementary liveness evidence.

### D10: The `work` axis stays `unknown` for Kimi

Kimi `Stop` has no background-task payload and no `TaskStarted`/`Notification` traffic was captured at 2.2.0. The channel publishes `work=unknown` and does not claim `settled` from hooks alone; if Kimi later emits task lifecycle events in supported configurations, a follow-up change adds the clearing rule.

## Risks / Trade-offs

- Upstream renames/removes a hooks event or schema key → provider silently drops the whole section → runtime detection as `degraded` via missing `SessionStart` after first prompt (D2); install-time enum/key pinning fails CI on regeneration against a new kimi version.
- Awaited lifecycle hooks make observer latency user-visible (T1: +3 s create, +3 s exit with a 3 s hook) → emitter budget 1.5 s POST inside a 5 s hook timeout; failure behavior is fail-open by provider design.
- Ordering-based tool-event correlation could misattribute under interleaved parallel tool calls → mitigated by `tool_call_id` pairing (identifier-based, not positional); only turn attribution uses ordering, and subagent interleavings are isolated by the scope rule.
- Permission absence under `--auto` is semantically ambiguous with a dead channel → distinguished by collector liveness plus other event families firing; S1's total permission absence under auto is the recorded control.
- `config.toml` write-order coupling with launch-policy synthesis → marker-scoped merge, install-after-synthesize ordering, and a both-orders regression test (D8).

## Migration Plan

No data migration. The channel is opt-in per adapter via `HOUMAO_HOOK_OBSERVATION_KIMI=1`; without it, Kimi sessions are byte-identical to today. Rollback is unsetting the flag; the observer block lives only in the per-session runtime home and is removed on teardown.

## Open Questions

- Whether the `kimi_headless` backend should adopt the channel (the S8 headless `SessionEnd` gap would need a reducer accommodation); deferred to a follow-up change.
- Whether upstream 2.1.x floors dispatch the identical event set as 2.2.0 (the campaign measured 2.2.0 only; a floor-repeat of the S1 capture is part of the qualification tasks).
