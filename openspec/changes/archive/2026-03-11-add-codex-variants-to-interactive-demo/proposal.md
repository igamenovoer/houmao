## Why

The interactive CAO full-pipeline demo currently presents itself as a Claude-only workflow and still starts Claude through hard-coded tool/config/credential defaults, even though the repo already supports CAO-backed Codex sessions and already uses repo-owned brain recipes as the declarative source of truth for supported Codex launch paths. We need one operator-facing demo pack that launches through brain recipes for both Claude and Codex so the interactive workflow uses one startup model, the default Claude path stops being a special case, and the repo gains the missing tracked Claude recipe needed to make that startup path explicit and maintainable.

## What Changes

- Refactor the interactive CAO full-pipeline demo so startup always resolves through a brain recipe, with the existing no-arg Claude walkthrough mapping to a tracked default Claude recipe instead of hard-coded build inputs.
- Treat `--agent-name` in the interactive demo as an optional override of the selected recipe's default agent name instead of as a demo-owned special-case identity.
- Add first-class recipe selection for the interactive demo so operators can launch supported Claude or Codex variants by a selector relative to the fixed brain-recipe root, with optional subdirectories and optional `.yaml`.
- Add the missing tracked Claude Code brain recipe and extend the shared recipe model plus tracked demo recipe set to carry default agent-name metadata, so the demo and the underlying construction model share the same declarative startup surface.
- Resolve recipe metadata in the demo engine for selector normalization and identity defaults, while delegating the actual brain build through the existing `build-brain --recipe` path instead of reconstructing tool, skill, config, and credential inputs in the demo layer.
- Make recipe-owned `skills` authoritative for this demo path, removing the need for a parallel demo-owned skill default.
- Prefer the clean recipe-first startup contract over backward compatibility with existing demo call shapes, and update any in-repo callers, wrappers, tests, and docs that break as part of this change.
- Persist the resolved recipe-backed demo metadata in the workspace state so follow-up commands such as `send-turn`, `send-keys`, `inspect`, `verify`, and `stop` continue to operate on the same active session without requiring repeated startup arguments.
- Generalize the inspect and verification surfaces so they report tool-appropriate live state and projected output instead of hard-coding Claude-specific field names and parser assumptions.
- Update the tutorial README and wrapper entrypoints so the default Claude walkthrough remains simple while explicit Claude and Codex recipe launches are documented and runnable from the same demo pack.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cao-interactive-full-pipeline-demo`: startup, persisted state, verification, and wrapper-driven lifecycle behavior now need to support recipe-driven Claude and Codex demo variants within one interactive pack.
- `cao-interactive-demo-inspect-surface`: inspect output currently exposes Claude-specific live-state and dialog-tail behavior and must be updated to support tool-aware parsing and generic live-state reporting.
- `cao-interactive-demo-operator-workflow`: the README and wrapper contract must expand from a fixed Claude walkthrough to a single tutorial workflow that includes recipe-backed Claude and Codex launch variants while preserving the current default path.
- `component-agent-construction`: the shared brain-recipe model plus the repo-owned brain-recipe set must support `default_agent_name`, include the tracked default Claude recipe used by the interactive demo, and provide tool-specific defaults for the tracked interactive-demo recipes.

## Impact

- `scripts/demo/cao-interactive-full-pipeline-demo/`
- `src/gig_agents/agents/brain_builder.py`
- `src/gig_agents/agents/brain_launch_runtime/cli.py`
- `src/gig_agents/agents/brain_launch_runtime/loaders.py`
- `src/gig_agents/demo/cao_interactive_demo/`
- `tests/fixtures/agents/brains/brain-recipes/`
- `tests/unit/demo/test_cao_interactive_demo.py`
- `tests/integration/demo/test_cao_interactive_demo_cli.py`
- `docs/reference/cao_interactive_demo.md`
- `docs/index.md`
