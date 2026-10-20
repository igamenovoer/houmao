# Proposal

## Why

The `cli-hook-observation` capability ships with Claude and Codex adapters; Kimi Code sessions still rely on TUI parsing alone (a single detector profile qualified through 2.1.1), which cannot see permission waits truthfully, mistakes compaction repaints, and has no provider-side terminal evidence. The 2026-10-20 debug campaign (`context/campaigns/debug/2026-10-20-kimi-hook-observation/`) proved across 14 live capture arms at the installed kimi 2.2.0 that Kimi Code's native hooks system (20 events, full payload contract since upstream 0.32.0 — below houmao's supported floor of 2.1.1) can be observed the same way, with **no trust step at all**: configured hooks run unattended with zero operator action. The campaign produced the validated payload catalog, settle rules, and kimi-specific rule amendments to build on.

## What Changes

- Add a Kimi adapter to the hook observation channel: managed Kimi `local_interactive` launches merge a Houmao-owned, marker-delimited `[[hooks]]` observer block (all 20 events, one entry each, no matchers, 5 s timeout, emitter command) into the launch-owned runtime `KIMI_CODE_HOME/config.toml` (the campaign's E1 decision). Installation validates the merged file by strict `tomllib` read-back — one malformed entry silently voids the whole hooks section at the provider, so the installer fails loudly and degrades the channel to `unavailable` instead. No trust prompt, hash, or bypass flag exists for Kimi hooks; no operator file is touched.
- Extend the channel's enablement and launch lifecycle to the Kimi adapter (`HOUMAO_HOOK_OBSERVATION_KIMI=1` opt-in, adapter-scoped artifact dir, `("kimi", "local_interactive")` applicability), reusing the collector, store, health, and reader infrastructure unchanged.
- Add a Kimi normalizer mapping the 20 subscribed events to the provider-neutral observation model: `prompt` arrives as a raw ContentPart[] array and is collapsed to text; tool events pair by `tool_call_id` (tool events carry no `turn_id`, so turn correlation is ordering-based); `turn_id` is an integer, session-scoped counter that continues across `--continue` resume; queued input surfaces as `UserPromptQueued` without a second `UserPromptSubmit`; subagent activity opens nested scopes (`SubagentStart`/`SubagentStop`, whose `turn_id` collides with the parent's); `SessionHeartbeat` is liveness evidence only.
- Add Kimi reducer rules per the campaign's dated amendments: `Stop` latches success, `Interrupt(reason=cancelled)` settles `interrupted` in place of `Stop`, `PermissionRequest` enters `blocked` and settles at `PermissionResult` for both allow and deny (deny is followed by `PostToolUseFailure` and the turn continues to `Stop` — unlike Codex's deny-aborts-turn), compaction holds posture across the window and the post-compaction turn mints a fresh `turn_id` (Kimi emits no `SessionStart(source=compact)`), terminal gaps (kill/crash) fall back to a truthful unknown.
- Update the tracked-state merge so a Kimi `Interrupt` hook event is authoritative interrupted evidence for Kimi sessions only, and update docs.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cli-hook-observation`: add Kimi adapter requirements — runtime-home `[[hooks]]` injection with strict read-back validation and no trust step, Kimi payload normalization (ContentPart[] prompt, `tool_call_id` pairing, session-scoped integer `turn_id`, queue and subagent scope events), Kimi terminal/blocked/compaction/terminal-gap posture rules, and tolerated unexercised event families.
- `official-tui-state-tracking`: modify the turn-semantics and shared-core requirements so that for Kimi sessions a provider hook `Interrupt` event settles the `interrupted` outcome (it remains TUI-derived for Claude), extending the existing Codex adapter carve-out per the campaign's measured Esc semantics.

## Impact

- `src/houmao/hook_observation/`: new `kimi_hooks_generator.py` (config.toml `[[hooks]]` merge + strict read-back validation) and `kimi_normalizer.py`; per-adapter gating in `install.py` (new env flag, applicability pair, artifact dir); Kimi rules in `reducer.py`; `store.py`/`reader.py` adapter registration; shared collector/store/health/reader reused.
- `src/houmao/agents/realm_controller/` (`hook_observation_launch.py`, `launch_plan.py`, launch policy `registry/kimi.yaml`): Kimi launch-time install — `[[hooks]]` merge into the launch-owned home's `config.toml` alongside the launch policy's existing owned fields, wrapper env for token/collector, per-adapter applicability. `KIMI_CODE_HOME` and `config.toml` are already launch-owned surfaces.
- `src/houmao/server/tui/tracking.py`: Kimi hook-posture merge including hook-derived `interrupted` for Kimi sessions.
- Tests: unit coverage for generator/normalizer/reducer (mirroring the Claude and Codex adapter suites), hermetic reducer fixtures derived from the campaign's sanitized captured streams, launch-policy tests for the merged hooks block, registry content tests.
- Docs: hook observation and launch-policy references updated for the Kimi adapter.
- Out of scope: `kimi -p` headless and ACP/kap-server hook adoption (the campaign verified hooks fire headless, with a named `SessionEnd` gap; adoption is a follow-up), `StopFailure`/`TaskStarted`/`Notification` fixture specialization (never exercised live — tolerated as silent families), the `HOUMAO_HOOK_OBSERVATION_*` flag semantics for the kimi headless backend, Codex/Claude behavior changes.
