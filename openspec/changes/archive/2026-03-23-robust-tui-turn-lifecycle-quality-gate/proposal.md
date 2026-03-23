## Why

The shared tracked-TUI stack currently misses two important correctness boundaries in real multi-turn sessions: terminal `last_turn` results can leak into the next turn instead of clearing when the new turn begins, and Claude-specific detector drift can misread both old interrupted status lines and live draft editing during active turns. The repository also lacks a maintained complex recorded interaction that keeps these regressions under an automated quality gate, so bugs can slip past the existing explicit-success and simpler interrupt fixtures.

## What Changes

- Fix shared turn-lifecycle reduction so a new draft or newly active turn clears the prior terminal `last_turn` outcome instead of carrying stale `success`, `interrupted`, or `known_failure` state into the next turn.
- Tighten Claude detector semantics so interruption and failure signals are scoped to the latest turn region rather than to any stale visible status text still present in scrollback.
- Make Claude prompt editing detection robust during active turns so styled prompt-marker color and reset sequences do not downgrade real typed draft text to `surface.editing_input=unknown`.
- Add and preserve a complex recorded interaction fixture family for both Claude and Codex that exercises `short prompt -> success -> long prompt -> active draft -> interrupt -> prompt again -> active draft -> interrupt -> short prompt -> success`.
- Promote those complex recorded fixtures into the maintained validation and sweep suite so they serve as a regression gate for `last_turn` reset behavior, active-draft editing semantics, and repeated interrupted-turn lifecycles.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `official-tui-state-tracking`: clarify that terminal `last_turn` state is invalidated when a new turn becomes visible and that stale transcript status lines must not override the latest-turn posture.
- `versioned-tui-signal-profiles`: extend profile-owned drift handling so Claude can scope status evidence to the latest turn region and classify active draft input robustly under style drift.
- `shared-tui-tracking-recorded-validation`: require a maintained complex multi-turn recorded corpus and automated validation gates that detect stale `last_turn` carry, repeated interruption mistakes, and active-draft editing regressions.
- `shared-tui-tracking-real-fixture-authoring`: extend the maintained real-fixture matrix and authoring guidance to include the longer success-interrupt-success interaction as a canonical replay-grade fixture family.

## Impact

- Affected code under `src/houmao/shared_tui_tracking/`, especially the session reducer, surface helpers, Claude profile code, and Claude prompt/status behavior helpers.
- Affected demo-pack code under `src/houmao/demo/shared_tui_tracking_demo_pack/` for recorded-validation scenarios, sweep expectations, and fixture-corpus quality gates.
- Affected maintained assets under `tests/fixtures/shared_tui_tracking/recorded/` and the related demo-pack documentation and authoring workflow.
- Affected tests spanning shared tracker unit coverage, demo-pack recorded validation, sweep assertions, and fixture-corpus regression gates.
