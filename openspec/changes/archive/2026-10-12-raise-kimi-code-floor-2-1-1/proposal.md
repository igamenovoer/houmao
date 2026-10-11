# Proposal

## Why

Houmao's kimi-code TUI tracking carries detector assumptions recorded against kimi-code 0.11.x/0.23.x surfaces. The 2026-10-10 debug campaign (`context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/`) measured the current `>=0.34.0` profile against two blind-labeled 5 fps recordings of kimi-code 2.1.1: 139/1909 and 254/797 false-ready samples, with every operator-modal span reading as idle-ready and all braille-phase busy spans invisible to the dead 0.11-era activity-label regex. kimi-code releases move fast enough that maintaining per-version scraping intervals is dead weight; per repository policy, breaking changes are allowed. The campaign also produced the repaired detector (monkey-patched candidate, zero false-ready / zero false-busy on both sessions), so the cut and the repair land together.

## What Changes

- **BREAKING**: kimi-code support floor becomes the current latest version, 2.1.1, with an open-ended `>=2.1.1` registration. kimi-code below 2.1.1, or an unparseable kimi version, resolves to an explicit unsupported-version error surface rather than a detector. There is no kimi fallback detector registration; existing deployments running older kimi will see an error until they upgrade (migration path: upgrade kimi-code to 2.1.1 or later).
- Promote the campaign's 2.1.x candidate repairs into the production detector: 2.1 activity labels (`Thinking…`/`Working…` with U+2026, `Retrying (N/M)`, `Compacting context…`, `Orchestrating…`, subagent `… Agent Running (…)` rows), spinner-union busy detection, AskUserQuestion and goal-start modal detection, trust-modal startup mapping, composer-accepts-input-while-busy semantics, and stale-interrupt suppression when activity is present.
- Operator-modal spans (approval panels, question dialog, trust modal, goal prompt) report `turn_phase=active` with a blocked reason, formalizing the reducer-observed convention over the campaign's `unknown` labeling.
- Reducer guard: `interrupted` no longer outranks concurrent `active_evidence` when the detector has already suppressed stale notices; the interrupt priority at `session.py` is kept but fed sanitized signals (detector-level fix; reducer unchanged).
- No user-facing warning when a kimi version newer than the qualified version resolves; code-side metadata (`qualified_through_version` on the registration/detector notes) records the qualified version for developers.
- Refresh kimi test fixtures and detector unit tests from the campaign's frozen 2.1.1 recordings; drop 0.11.x/0.23.x-era profile classes, registry intervals, and version-pinned assertions.
- Retarget the kimi signal-corpus spec from 0.23.x unattended-only captures to 2.1.1-and-up captures that include operator-interaction surfaces.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `versioned-tui-signal-profiles`: kimi-code profile resolution becomes floor-gated with an explicit unsupported-version error below the floor, no kimi fallback registration, and code-side qualified-version metadata instead of user-facing warnings.
- `official-tui-state-tracking`: kimi detection requirements updated to the 2.1.1 signal contract (spinner-union busy evidence, modal surfaces as blocked-active, composer acceptance while busy, stale-interrupt suppression, trust-modal parser mapping).
- `kimi-tui-signal-corpus`: corpus target version and scenario scope move from 0.23.x unattended-only to 2.1.1-and-up including operator-interaction surfaces.

## Impact

- Code: `src/houmao/shared_tui_tracking/registry.py` (kimi registrations, unsupported-version path), `src/houmao/shared_tui_tracking/apps/kimi_code/profile.py` (repaired detector, old profile classes removed), `src/houmao/shared_tui_tracking/detectors.py` and `__init__.py` exports, `src/houmao/server/tui/parser.py` (modal needles, preset version from resolved detector instead of hardcode), `src/houmao/server/tui/tracking.py` and `src/houmao/server/service.py` (per-session containment of the floor error), campaign tooling at `scripts/explore/kimi-code-tui-parsing/` (candidate code moves into production).
- Launch floor (scope addition surfaced during apply): `src/houmao/agents/launch_policy/registry/kimi.yaml`, `src/houmao/agents/realm_controller/launch_plan.py`, `src/houmao/agents/brain_builder.py` move the managed-launch kimi floor from `>=0.34.0` to `>=2.1.1`, so below-floor kimi fails explicitly at managed launch instead of launching and then failing only in tracking.
- Tests/fixtures: `tests/unit/shared_tui_tracking/`, `tests/unit/server/test_kimi_tui_parser.py`, `tests/unit/agents/` launch tests, `tests/fixtures/shared_tui_tracking/kimi_code/` refreshed from campaign captures (including the gzipped qualification recordings with frozen labels).
- Specs: the three capability deltas above.
- Downstream: any deployment tracking kimi-code below 2.1.1 breaks loudly at tracker resolution; fix is upgrading kimi-code. No runtime behavior change for claude_code or codex_tui.
