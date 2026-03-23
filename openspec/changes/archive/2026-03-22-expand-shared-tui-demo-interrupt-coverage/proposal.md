## Why

The shared tracked-TUI demo currently proves only a single interrupted turn, and even that coverage is incomplete because the committed Codex interrupted fixture does not surface a true interrupted-ready public state. The demo needs an explicit repeated-interruption lifecycle so tracker correctness can be judged for the real operator pattern of interrupting one turn, prompting again, interrupting again, and then closing the session.

## What Changes

- Add a canonical repeated intentional-interruption coverage path for the shared tracked-TUI demo pack, covering `prompt -> active -> interrupt -> prompt -> interrupt -> close`.
- Expand the maintained real-fixture matrix with dedicated repeated-interruption cases for Claude and Codex, while retaining the current single-interrupt cases as smaller debug targets.
- Require recorded validation for the new cases to verify the public tracked-state lifecycle across both interrupted turns, including interruption-result reset when the second turn begins and correct diagnostics posture after close.
- Revise the demo’s scenario-driving contract so intentional interrupt and intentional close are represented as semantic operator intents rather than only as raw literal keystrokes or crash-style session kills.
- Strengthen cadence-sweep expectations for repeated interruption so the demo can optionally assert repeated transition families instead of only first-occurrence label presence.
- Update the demo README and authoring guidance so maintainers can recapture, label, validate, and interpret the new repeated-interruption cases consistently.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `shared-tui-tracking-real-fixture-authoring`: expand the maintained real-fixture matrix and authoring guidance to include repeated intentional interruption followed by session close.
- `shared-tui-tracking-recorded-validation`: require recorded validation to support and judge repeated interrupted-turn lifecycles, including intent-driven scenario actions and stronger sweep semantics for repeated transitions.

## Impact

- Affected code under `src/houmao/demo/shared_tui_tracking_demo_pack/`, especially scenario loading, recorder-driven scenario execution, sweep evaluation, and reporting.
- Scenario definitions and maintainer documentation under `scripts/demo/shared-tui-tracking-demo-pack/`.
- Canonical recorded fixtures under `tests/fixtures/shared_tui_tracking/recorded/`.
- Unit tests covering demo-pack scenario parsing, config/sweep validation, and recorded-validation behavior.
