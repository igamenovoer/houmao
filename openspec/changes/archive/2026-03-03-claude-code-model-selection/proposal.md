## Why

CAO-backed and headless Claude Code sessions currently inherit whatever default model Claude Code selects at runtime, which makes “full pipeline” agent launches hard to reproduce (capability/cost can drift when defaults change). Claude Code already supports model selection via environment variables; we want a first-class, documented, testable path in this repo to select Opus (or pin a specific Opus version) for orchestrated launches.

## What Changes

- Support Claude Code model selection for orchestrated sessions via Claude Code’s environment-variable controls (for example `ANTHROPIC_MODEL`, optional `ANTHROPIC_SMALL_FAST_MODEL`, alias pinning vars like `ANTHROPIC_DEFAULT_OPUS_MODEL`, and `CLAUDE_CODE_SUBAGENT_MODEL`).
- Ensure these model-selection env vars can be supplied via our credential profiles for Claude (so they work in both headless and CAO-backed launches).
- Update runtime docs/examples to show how to launch a CAO-backed Claude agent with an explicit model selection.
- Add lightweight tests that validate the launch plan/env propagation contract (no live API calls required).

## Capabilities

### New Capabilities

<!-- None -->

### Modified Capabilities

- `brain-launch-runtime`: model-selection env vars for Claude Code are propagated into both `claude_headless` and `cao_rest` launches.
- `claude-cli-noninteractive-startup`: Claude credential/tool configuration supports model-selection env vars in non-interactive orchestrated launches.

## Impact

- Runtime launcher/config:
  - `agents/brains/tool-adapters/claude.yaml` (credential env allowlist expansion).
  - `src/agent_system_dissect/agents/brain_launch_runtime/...` (documented behavior; potential small adjustments if gaps are found).
- Docs:
  - `docs/reference/brain_launch_runtime.md` (add model-selection guidance for Claude Code).
- Tests:
  - Add/extend unit tests to assert env propagation and launch-plan behavior for Claude sessions.
