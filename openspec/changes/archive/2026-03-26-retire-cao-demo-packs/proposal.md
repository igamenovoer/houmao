## Why

The repository still presents `scripts/demo/cao-server-launcher/` and `scripts/demo/cao-interactive-full-pipeline-demo/` as active supported demo packs even though the standalone launcher CLI already fails fast with retirement guidance and the interactive workflow has a maintained Houmao-server replacement. Keeping the CAO-era demo packs live in specs, docs, tests, and dedicated workflow code preserves stale operator guidance and blocks cleanup.

## What Changes

- **BREAKING** Retire the `scripts/demo/cao-server-launcher/` tutorial pack and remove its active docs, tests, and spec contract.
- **BREAKING** Retire the `scripts/demo/cao-interactive-full-pipeline-demo/` tutorial pack and remove its active docs, tests, and spec family.
- Remove interactive-demo workflow source code that exists only to support the retired CAO demo pack, while preserving any helper modules that are still imported by maintained packs.
- Update active documentation to stop routing operators to the retired CAO demo packs and point them to retirement notes or the maintained `scripts/demo/houmao-server-interactive-full-pipeline-demo/` workflow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cao-server-launcher-demo-pack`: retire the standalone launcher tutorial-pack requirement set.
- `cao-interactive-full-pipeline-demo`: retire the CAO interactive full-pipeline tutorial-pack requirement set.
- `cao-interactive-demo-startup-recovery`: remove startup-hardening requirements that only applied to the retired CAO interactive demo.
- `cao-interactive-demo-start-progress`: remove startup progress-output requirements that only applied to the retired CAO interactive demo.
- `cao-interactive-demo-module-structure`: remove the retired demo's dedicated package-structure contract while keeping shared helper preservation out of scope.
- `cao-interactive-demo-inspect-surface`: remove the retired demo's inspect and verify contract.

## Impact

- Affected scripts: `scripts/demo/cao-server-launcher/`, `scripts/demo/cao-interactive-full-pipeline-demo/`
- Affected demo workflow code: exclusive modules under `src/houmao/demo/cao_interactive_demo/`
- Affected tests: `tests/unit/demo/test_cao_interactive_demo.py`, `tests/integration/demo/test_cao_interactive_demo_cli.py`, and any launcher-demo-specific coverage tied only to the retired demo pack
- Affected docs: active README and reference pages that still teach the retired demo packs
- Explicit non-impact: shared internal launcher library and any helper modules still imported by maintained packs remain in place
