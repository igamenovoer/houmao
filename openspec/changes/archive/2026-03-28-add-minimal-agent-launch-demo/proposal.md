## Why

The repository currently documents the canonical `agents/` layout and launch flow, but it does not ship a small supported runnable example under `scripts/demo/` that shows the minimum tracked files and local-only auth wiring needed to launch an agent. That leaves operators and maintainers reading multiple docs and fixture trees to reconstruct the simplest working setup.

## What Changes

- Add one supported tutorial-style demo under `scripts/demo/` that shows the smallest canonical `agents/` tree needed to launch a managed agent.
- Support both Claude and Codex lanes from one shared demo role by providing provider-specific presets, setups, and run-time auth wiring.
- Keep the demo secret-free in git by tracking only setup, role, and preset assets while creating local auth symlinks at run time from `tests/fixtures/agents/tools/<tool>/auth/...`.
- Make the demo headless-first and tutorial-shaped, with a runnable script, tracked inputs, generated outputs, verification steps, and troubleshooting guidance.
- Replace the current `scripts/demo/README.md` archive-only framing with a supported demo index that still preserves `scripts/demo/legacy/` as historical reference material.

## Capabilities

### New Capabilities
- `minimal-agent-launch-demo`: Define the supported minimal demo surface, tracked asset shape, run-time auth symlink strategy, and verification flow for launching one agent through either Claude or Codex.

### Modified Capabilities
- `docs-getting-started`: Add a supported pointer from the getting-started docs to the new minimal demo as the runnable companion to the canonical agent-definition and launch documentation.

## Impact

- Affected areas: `scripts/demo/README.md`, a new `scripts/demo/minimal-agent-launch/` demo directory, and getting-started documentation that points readers to the supported runnable example.
- Affected systems: managed-agent local launch flow, canonical `agents/` source layout examples, and local fixture-auth reuse for demo execution.
- Dependencies: existing `houmao-mgr agents launch` behavior, canonical preset-backed agent parsing/building, and local auth bundles already maintained under `tests/fixtures/agents/tools/*/auth/`.
