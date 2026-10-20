# Proposal

## Why

The `cli-hook-observation` capability shipped with a Claude adapter only; Codex sessions still rely on TUI parsing alone, which cannot see permission waits truthfully, mistakes compaction repaints, and has no provider-side terminal evidence. The 2026-10-20 debug campaign (`context/campaigns/debug/2026-10-20-codex-hook-observation/`) proved against 12 live sessions that Codex's stable hooks system (v0.124+, verified at the installed 0.163.0) can be observed the same way — with auto-trust fully automated and zero user action — and produced the validated payload catalog, settle rules, and rule amendments to build on.

## What Changes

- Add a Codex adapter to the hook observation channel: managed Codex `local_interactive` launches write `hooks.json` into the runtime-owned `CODEX_HOME` and pre-trust every handler via `[hooks.state."<key>".trusted_hash]` entries synthesized into the runtime-home `config.toml` (the campaign's E1 decision; `--dangerously-bypass-hook-trust` stays a tested fallback). No operator file is touched and no trust modal can appear.
- Extend the channel's enablement, install, and launch lifecycle from Claude-only to per-adapter (`HOUMAO_HOOK_OBSERVATION_CODEX=1` opt-in, adapter-scoped artifact dirs, per-tool applicability rules), reusing the collector, store, health, and reader infrastructure unchanged.
- Add a Codex normalizer mapping the 10 live Codex events to the provider-neutral observation model (`turn_id` turn epochs, `tool_use_id` tool pairing, `PermissionRequest` without `tool_use_id`, compaction `trigger`, session `source`), tolerating the 4 events that never fire at the supported floor.
- Add Codex reducer rules per the campaign's dated amendments: `Stop` latches success, `Interrupt` settles `interrupted` (including the deny-aborts-turn path), `PermissionRequest` enters `blocked` paired to the preceding `PreToolUse` and settles on the matching `PostToolUse` (allow) or `Interrupt` (deny), compaction holds posture across the window and mints a new turn epoch, steered input stays in the running epoch, and terminal gaps (kill/crash) fall back to a truthful unknown.
- Port the campaign-validated hook trust hash (`scripts/explore/codex-hook-observation/hash_hook.py`, verified 12/12 byte-identical against Codex's own trust writes) into production as the pre-trust mechanism, kept honest by a fixture test against Codex's published test vectors.
- Update the tracked-state merge so a Codex `Interrupt` hook event is authoritative interrupted evidence for Codex sessions only, and update docs.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cli-hook-observation`: add Codex adapter requirements — runtime-home injection with automated pre-trust, Codex payload normalization, Codex terminal/blocked/compaction/terminal-gap posture rules, and Codex version-gated event selection.
- `official-tui-state-tracking`: modify the turn-semantics and shared-core requirements so that for Codex sessions a provider hook `Interrupt` event settles the `interrupted` outcome (it remains TUI-derived for Claude), reflecting the deny-aborts-turn and Esc semantics measured in the campaign.

## Impact

- `src/houmao/hook_observation/`: new `codex_hooks_generator.py`, `codex_normalizer.py`, `trust_hash.py`; generalized per-adapter gating in `install.py`; reducer rules for Codex semantics; shared collector/store/health/reader reused.
- `src/houmao/agents/realm_controller/` (`hook_observation_launch.py`, `launch_plan.py`, codex backend/launch policy `registry/codex.yaml`): Codex launch-time install — `hooks.json` + `config.toml [hooks.state]` synthesis in the runtime home, wrapper env for token/collector, per-adapter applicability.
- `src/houmao/server/tui/tracking.py`: Codex hook-posture merge including hook-derived `interrupted` for Codex sessions.
- Tests: unit coverage for generator/hash/normalizer/reducer (mirroring the Claude adapter's suites), hermetic reducer fixtures derived from the campaign's sanitized captured streams, launch-policy tests for the synthesized pre-trust block.
- Docs: hook observation and launch-policy references updated for the Codex adapter.
- Out of scope: `codex exec`/headless hook adoption, subagent events and `apply_patch` payload specialization (campaign leftovers), the deferred hung-collector and async-loss reliability arms, Kimi Code.
