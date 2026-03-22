## Why

The shared tracked-TUI demo pack and committed fixture corpus now prove the pipeline, but the current fixtures are still lightweight authored samples rather than real tmux session captures. That is enough to validate the mechanics, but not enough to trust the detector/reducer behavior against the repaint churn, timing edges, and real terminal surfaces that Claude Code and Codex actually produce.

## What Changes

- Define a maintained operator workflow for scouting, capturing, labeling, validating, reviewing, and promoting real recorded fixtures for the shared tracked-TUI suite.
- Tighten the canonical recorded-validation corpus so the committed Claude and Codex fixtures are sourced from real tmux-backed sessions rather than from synthetic hand-authored recorder payloads.
- Add a first-wave real capture matrix across Claude and Codex with concrete prompts, expected transition targets, and promotion gates for success, interruption, ambiguity, and diagnostics-loss coverage.
- Require a promotion gate for each published real fixture: zero replay mismatches, a persisted Markdown summary report, and a review video rendered from the exact pane snapshots that feed the tracker.
- Document how live watch and recorded capture should be used together during authoring so maintainers scout surfaces before recording and label ground truth from `pane_snapshots.ndjson` rather than from intuition.

## Capabilities

### New Capabilities
- `shared-tui-tracking-real-fixture-authoring`: Maintainer workflow, execution plan, and promotion rules for creating real Claude and Codex recorded fixtures and ground-truth labels.

### Modified Capabilities
- `shared-tui-tracking-recorded-validation`: Tighten the committed fixture corpus and publication requirements so canonical fixtures are real tmux recordings with validated labels and review artifacts.

## Impact

- Affected specs: new operator-facing fixture-authoring capability plus changed requirements for the recorded-validation corpus.
- Affected code and content: `scripts/demo/shared-tui-tracking-demo-pack/`, scenario recipes, maintainer docs, and `tests/fixtures/shared_tui_tracking/recorded/`.
- Affected workflows: maintainers will use live watch to scout, `recorded-capture` to author temporary runs under `tmp/`, and only then promote cleaned real artifacts into the committed corpus.
- Affected validation posture: replay correctness and label quality become promotion criteria for real fixtures, not just post hoc checks.
