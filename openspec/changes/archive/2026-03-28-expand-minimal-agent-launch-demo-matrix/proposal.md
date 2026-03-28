## Why

The new `scripts/demo/minimal-agent-launch/` surface currently proves the minimal tracked launch shape, but its supported workflow is still effectively headless-first. Operators who want to use the same demo to validate interactive Claude/Codex TUI lanes still have to improvise outside the documented demo contract.

## What Changes

- Expand `scripts/demo/minimal-agent-launch/` from a headless-first example into an explicit launch matrix covering Claude Code and Codex across both TUI and headless transport modes.
- Add one supported runner interface that defaults to TUI for a selected provider and uses `--headless` only when the operator wants the headless lane.
- Make the tutorial explain the four supported lanes, including how non-interactive callers receive a tmux attach command for TUI launches.
- Record provider/transport-specific outputs and verification guidance so the demo can be used as a reproducible smoke surface for the full matrix.

## Capabilities

### New Capabilities
- `minimal-agent-launch-demo-matrix`: Define the supported Claude/Codex × TUI/headless launch matrix for `scripts/demo/minimal-agent-launch/`, including runner inputs, expected outputs, and verification behavior.

### Modified Capabilities

## Impact

- Affected areas: `scripts/demo/minimal-agent-launch/`, `scripts/demo/README.md`, and the tutorial content for the minimal demo.
- Affected systems: local managed-agent launch paths for `local_interactive`, `claude_headless`, and `codex_headless`.
- Dependencies: the existing minimal demo assets, `houmao-mgr agents launch`, local fixture auth bundles, and tmux-backed TUI session startup.
