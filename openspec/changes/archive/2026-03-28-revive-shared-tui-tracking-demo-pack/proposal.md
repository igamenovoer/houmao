## Why

The archived shared TUI tracking demo still captures an important operator and maintainer workflow: exercise the standalone tracker directly against real Claude and Codex tmux sessions, with optional recorder evidence, strict replay comparison, and robustness sweeps. It is currently not a supported surface, and its launch bootstrap is tied to `tests/fixtures/agents/` instead of a demo-local agent-definition tree like the neighboring minimal demo.

## What Changes

- Restore the shared TUI tracking demo pack as a supported `scripts/demo/` surface instead of leaving it only under `scripts/demo/legacy/`.
- Give the restored pack its own tracked secret-free `inputs/agents/` tree using the canonical minimal agent-definition layout.
- Generate a run-local `.agentsys/agents` working tree for each run and materialize a demo-local auth alias for the selected tool from host-local fixture auth bundles, following the same pattern as `minimal-agent-launch`.
- Rewire live watch and recorded capture to build brains from the generated demo-local agent-definition tree instead of from `tests/fixtures/agents/`.
- Preserve the existing demo ideas that remain valuable: demo-owned config resolution, optional recorder-backed live watch, scenario-driven recorded capture, strict public-state replay comparison, transition-contract sweeps, and durable tmux ownership cleanup.
- Update the supported demo documentation and operator paths to reference only the restored non-legacy demo location.
- Make recorded-corpus commands fail clearly when the configured committed fixture root is absent or empty instead of relying on stale assumptions about a present corpus.

## Capabilities

### New Capabilities
- `shared-tui-tracking-demo-pack`: Supported shared TUI tracking demo-pack surface, local tracked demo assets, and run-local generated agent-definition trees.
- `shared-tui-tracking-demo-configuration`: Demo-owned config contract, schema, deterministic merge order, and persisted resolved-config artifacts for the restored pack.
- `shared-tui-tracking-live-watch`: Live interactive watch workflow for Claude and Codex using the restored demo-local launch assets.
- `shared-tui-tracking-recorded-validation`: Scenario-driven recorded capture, replay validation, and cadence-sweep workflows for the restored pack.

### Modified Capabilities

## Impact

- Affected code:
  - `src/houmao/demo/legacy/shared_tui_tracking_demo_pack/` and its restored non-legacy replacement
  - `scripts/demo/legacy/shared-tui-tracking-demo-pack/` and the restored supported demo directory
  - `scripts/demo/README.md`
- Affected assets:
  - new demo-local `inputs/agents/` tree
  - demo config, scenarios, and operator docs under the restored demo directory
- Affected systems:
  - local tmux-backed Claude/Codex live watch
  - recorder-backed capture and replay validation
  - demo-local agent-definition materialization and auth aliasing
