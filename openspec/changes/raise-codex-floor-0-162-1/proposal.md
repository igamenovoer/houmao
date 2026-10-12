# Proposal

## Why

Houmao's codex TUI tracking carries detector assumptions recorded against codex 0.116.x/0.144.x surfaces. The 2026-10-12 debug campaign (`context/campaigns/debug/2026-10-12-codex-tui-parsing/`) measured the current profiles against two blind-labeled 5 fps recordings of codex 0.162.1: the fallback path produced 147 false-ready samples on the lifecycle session and 68 on the operator-surfaces session, compaction read `ready` 88/88 samples because the status-row check sits behind the assistant-prose break, every operator modal (trust screen, model picker, warnings screen) read as idle-ready, the `─ Worked for ` dock prefix and the two-sentence interrupt needle are dead, and temporal inference reads 0.162's hidden-status-row streaming as turn-over. The campaign also produced the repaired detector (monkey-patched candidate, 0.9984-1.0000 agreement on the two admission booleans across both sessions), so the floor cut and the repair land together, mirroring the kimi 2.1.1 change.

## What Changes

- **BREAKING**: codex TUI support floor becomes the current latest version, 0.162.1, with an open-ended `>=0.162.1` registration. Codex below 0.162.1, or an unparseable codex version, resolves to the explicit `UnsupportedToolVersionError` surface rather than a detector. The codex fallback registration and the 0.116.x/0.144.x profile registrations are removed; existing deployments running older codex will see an error until they upgrade (migration path: upgrade codex to 0.162.1 or later).
- Promote the campaign's 0.162.x candidate repairs into the production detector: status-row label check ahead of the assistant-prose break (compaction and other status labels count as busy), `Conversation interrupted` prefix needle with stale suppression, `Worked for ` dock prefix (box-drawing `─` prefix dropped in 0.162), 0.162.x modal surfaces as blocking overlays (workspace-trust screen, list-selection picker footer `enter select · esc back`, warnings screen, send-input-to-terminal dialog), modal-or-splash blocked detect() semantics, and dock-aware temporal hints (growth while undocked with turn content counts as active; a short status-row blink does not end the turn).
- Queued follow-up input detection moves to the 0.162 queued-echo surface (`› <text>` above the status row, disambiguated from turn-starting echoes); the legacy pending-section headers (`Messages to be submitted …`, `Queued follow-up inputs`) are dead in 0.162 and their needles are removed. The queued-echo collapse window (~27 s in the campaign window) is a documented single-snapshot blind spot; persistent pending state across the collapse is tracker-side memory, decided against for this change (the documented contract is "visibly holds"), recorded as a follow-up rather than silently shipped.
- Maintenance turns no longer erase the previous prompt-turn result: provider maintenance activity (context compaction) does not count as newer-turn evidence and does not settle success over a prior terminal outcome, so `last_turn_result=interrupted` survives a post-interrupt compaction. This is a shared-reducer carve-out keyed on the compaction-tagged active reason, per the campaign's operator-audited labels.
- No user-facing warning when a codex version newer than the qualified version resolves; code-side metadata (`qualified_through_version = "0.162.1"` on the registration/detector) records the qualified version for developers.
- Launch floor moves with the tracking floor: `launch_policy/registry/codex.yaml` strategy id `codex-unattended-0.116.x` renamed and `supported_versions` realigned to `>=0.162.1`, with the live-probe evidence re-run on 0.162.1 (0.162 removed the `-a untrusted` flag; the trust screen renders under bypass in untrusted git workdirs).
- **BREAKING**: the `codex_app_server` backend is declared unmaintained — it has not been qualified against current codex releases and is blocked at launch: new session requests and retained manifests naming it raise an explicit unmaintained-backend error pointing at the maintained alternatives (`codex_headless`, `local_interactive`), ending its deprecation window.
- Refresh codex test fixtures from the campaign's frozen 0.162.1 recordings; promote the two blind-labeled sessions into `tests/fixtures/shared_tui_tracking/codex/` with a qualification replay test mirroring the kimi 2.1.x gate; rewrite `test_codex_prompt_behavior.py` and `test_codex_tui_session.py` around 0.162.1 fixtures; delete or re-derive the stale `stale_active_*` ANSI captures.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `versioned-tui-signal-profiles`: codex_tui profile resolution becomes floor-gated with an explicit unsupported-version error below the floor, no codex fallback registration, and code-side qualified-version metadata; the evidence-backed-profiles requirement moves from Codex 0.144.x to Codex 0.162.x qualified against labeled 0.162.1 recordings.
- `codex-tui-state-tracking`: codex detection requirements updated to the 0.162.x signal contract (status-row-before-prose busy evidence, `Worked for` dock, `Conversation interrupted` prefix, 0.162.x modal surfaces as blocking overlays, dock-aware temporal hints, queued-echo pending-input evidence replacing the dead pending-section headers, model-picker footer update).
- `official-tui-state-tracking`: the newer-turn invalidation requirement gains a maintenance-turn carve-out — compaction neither clears nor settles over the previous prompt turn's terminal outcome.
- `brain-launch-runtime`: the `codex_app_server` deprecation window closes — the backend becomes unmaintained and is blocked at launch with an explicit error; the codex bootstrap backend list drops it.
- `shared-tui-tracking-recorded-validation`: recorded-validation target versions move from Codex 0.144.x / Kimi 0.23.x to Codex 0.162.x / Kimi 2.1.x so the validation spec stops contradicting both floors.

## Impact

- Code: `src/houmao/shared_tui_tracking/registry.py` (codex registrations collapse to one floor-gated entry; fallback and 0.116.x/0.144.x registrations removed), `src/houmao/shared_tui_tracking/apps/codex_tui/` (`profile.py`, `signals/activity.py`, `signals/interrupted.py`, `signals/overlays.py` — candidate repairs promoted from `scripts/explore/codex-tui-parsing/campaign_lib/patches.py`), `src/houmao/shared_tui_tracking/detectors.py` and `__init__.py` exports.
- Launch floor: `src/houmao/agents/launch_policy/registry/codex.yaml` (strategy rename, `supported_versions: ">=0.162.1"`, `codex_app_server` dropped from the strategy backends, re-probed live evidence), plus any launch-plan/brain-builder references to the old strategy id or codex floor, and the realm-controller paths that must reject `codex_app_server` (`src/houmao/agents/realm_controller/launch_plan.py`, `runtime.py`, manifest loading) with an explicit unmaintained-backend error.
- Tests/fixtures: `tests/unit/shared_tui_tracking/` (registry floor cases, detector tests rewritten), `tests/fixtures/shared_tui_tracking/codex/` (frozen campaign sessions promoted with labels and provenance), qualification replay test added, `test_codex_prompt_behavior.py` / `test_codex_tui_session.py` rewritten, stale ANSI captures removed.
- Campaign wrap-up: `context/campaigns/debug/2026-10-12-codex-tui-parsing/` artifacts updated to record the integration decision and link this change.
- Specs: the five capability deltas above.
- Downstream: any deployment tracking codex below 0.162.1 breaks loudly at tracker resolution (fix: upgrade codex); any launch requesting `codex_app_server` fails with an explicit unmaintained-backend error (fix: use `codex_headless` or `local_interactive`). No runtime behavior change for claude_code or kimi_code.
