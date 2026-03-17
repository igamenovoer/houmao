## Why

The current mailbox roundtrip automation still treats `cao_only` as an acceptable CAO parsing mode for the live tutorial-pack path, even though recent investigation showed that this path hides or misclassifies the mailbox failures we actually need to see for Claude. At the same time, Codex now has a functional runtime shadow parser, so the live mailbox roundtrip path should stop mixing parsing strategies and standardize on `shadow_only` for both agents.

## What Changes

- Add a mailbox-roundtrip automation contract that requires both CAO-backed agents in the automatic live workflow to run with `parsing_mode=shadow_only`.
- Require the tutorial-pack automatic workflow to persist and reuse `shadow_only` across `start`, `roundtrip`, and `stop` for the same demo root instead of treating `cao_only` as an equally valid live-test mode.
- Require live mailbox automation failures under `shadow_only` to surface directly as the product result; the automation must not switch the Claude sender or Codex receiver to `cao_only` to make the roundtrip appear healthier.
- Update the live tutorial-pack tests and maintainer docs so Codex shadow parsing is treated as supported coverage for this workflow and `cao_only`-based runs do not satisfy the mailbox automation requirement.

## Capabilities

### New Capabilities
- `mailbox-roundtrip-shadow-only-automation`: Defines the automatic CAO-backed mailbox roundtrip contract that pins both agents to `shadow_only`, persists that mode across the demo workflow, and excludes `cao_only` runs from satisfying the live automation requirement.

### Modified Capabilities
<!-- None. -->

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`, `tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_live.py`, and related tutorial-pack fixtures/docs.
- Affected systems: CAO-backed mailbox roundtrip automation, runtime parsing-mode selection/persistence for demo workflows, Claude shadow-only mailbox execution, and Codex shadow-parser-backed live coverage.
- Affected workflow: maintainers will treat `shadow_only` as the only valid CAO parsing mode for automatic live mailbox roundtrip coverage, while any `cao_only` experimentation becomes debug-only and does not count as passing automation.
