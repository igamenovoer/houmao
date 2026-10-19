# Proposal

## Why

TUI parsing alone cannot authoritatively determine several lifecycle facts that managed-agent state tracking needs: turn start from direct (non-gateway) input, immediate turn completion, API-failure terminal results with an error class, permission waits before the modal paints, compaction maintenance windows, and background work still running after a turn ends. The Claude 2.1.296 parsing-repair campaign (`context/campaigns/debug/2026-10-12-claude-code-tui-parsing`) documented these failure classes, and the feature design in `context/features/2026-10-18-cli-hook-observation-channel` frames the fix. Claude Code at the maintained 2.1.296 support floor exposes provider lifecycle hooks (`UserPromptSubmit`, `Stop`, `StopFailure`, `PermissionRequest`, compaction events) that report exactly these facts, so Houmao can add a second, structured observation channel that complements TUI parsing instead of replacing it.

## What Changes

- Add a provider-neutral CLI hook observation channel with a first adapter for Claude Code, covering managed `local_interactive` launches only. In this release the channel is opt-in (maintainer-facing enablement), not default-on.
- Managed Claude launches gain a session-scoped observer configuration injected by marker-merging a Houmao-owned block into the managed home's `settings.json` (launch-owned `--settings` as fallback), plus a per-session loopback collector started before the provider. Raw events persist to a session-local, permission-restricted, append-only store that doubles as the fan-out point for all tracking consumers.
- `LiveSessionTracker` merges a hook-derived posture as a third authority alongside the existing TUI session facts and lifecycle-kernel facts, under an explicit authority table: hooks own lifecycle facts (turn start, turn end, terminal failure, permission waits, maintenance windows, background work); the TUI tracker keeps surface facts (readiness, pending input, draft input, modals, interrupt outcomes). `TuiTrackerSession` remains hook-free.
- Gateway prompt admission consults the merged hook posture: hook `active` or `blocked` closes `ready_only`, hook `blocked` closes `if_no_pending`, and a stale, unavailable, disabled, or errored channel adds no new refusal reasons (TUI-only fallback with byte-equivalent existing state).
- Public tracked state, tracked diagnostics, gateway status, and admission decision records gain additive optional hook fields. `last_turn.source` gains `hook_observation`. Raw payloads, prompts, tool inputs, final assistant text, and collector tokens never reach public surfaces.
- Qualification keeps TUI-only equivalence as the central gate: the existing Claude 2.1.296 replay suite must pass unchanged with the channel inactive; new coverage adds virtual-time merge tests, recorded replay with synthetic hook sidecars, and live managed-launch smoke.

No breaking changes. When the channel is absent, disabled, stale, untrusted, or errored, every existing state field and admission outcome behaves exactly as today.

## Capabilities

### New Capabilities

- `cli-hook-observation`: Provider-hook observation for managed CLI agents. Covers observer configuration injection, the per-session collector and event store, event normalization into a provider-neutral observation model, hook posture reduction, merge authority with TUI tracking, channel health and conflict diagnostics, degradation to TUI-only behavior, session lifecycle integration (start, resume, relaunch, stop, cleanup), and qualification evidence.

### Modified Capabilities

- `official-tui-state-tracking`: The tracked-state input contract and the `last_turn.source` vocabulary currently admit only raw TUI snapshot text, explicit prompt-submission evidence, and surface inference. Provider-hook observation evidence becomes an additional, optional authority for lifecycle facts, and `last_turn.source` gains `hook_observation`. All TUI-owned requirements remain unchanged and remain the sole authority when the hook channel is not active.
- `agent-gateway`: Direct prompt-control admission policies currently evaluate only TUI-tracked readiness and pending-input facts. When a hook channel is active for the session, admission also evaluates the merged hook posture, and admission decision records carry the hook facts used. Degraded channels add no new refusal reasons.

## Impact

- **New code**: one neutral hook-observation subpackage (collector, command-hook emitter, envelope store, normalizer, posture reducer) plus wiring. No new third-party dependencies; the collector and emitter use the standard library, and posture reduction reuses the existing `reactivex` dependency and scheduler patterns.
- **Launch/runtime**: `LaunchPlanRequest` gains an optional `session_root`; `build_launch_plan` and `start_runtime_session`/`resume_runtime_session` install observer artifacts and manage collector lifecycle; the `local_interactive` backend passes the collector token to the provider process through its launch wrapper only (never through the tmux session environment, which `_publish_tmux_session_environment` publishes wholesale today).
- **Tracking**: `LiveSessionTracker` gains a hook-posture input folded at poll-cycle boundaries and applied at its existing projection/reconciliation points; `shared_tui_tracking` models gain the `hook_observation` source value; `TuiTrackerSession` is untouched.
- **Gateway/server/passive**: admission policy checks and decision facts, gateway status, terminal-state response, and passive-server observation gain additive optional channel fields.
- **Specs/docs**: new `cli-hook-observation` capability; deltas to `official-tui-state-tracking` and `agent-gateway`; state-model and prompt-admission docs updated.
- **Out of scope for this change**: `claude_headless` (stays on `stream-json`), joined sessions and unmanaged launches, Codex and Kimi adapters, default-on rollout, publishing hook-derived final assistant text, automatic remediation based on hook observations.
