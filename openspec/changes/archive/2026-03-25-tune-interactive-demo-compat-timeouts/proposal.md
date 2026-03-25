## Why

The Houmao-server interactive full-pipeline demo previously failed automatic startup because its detached `houmao-mgr cao launch --headless` path still used the generic compatibility timeout budgets. The pair now supports configurable client and server compatibility timing, so the demo should use a demo-owned, more generous startup budget instead of depending on the product defaults.

## What Changes

- Tune the interactive demo's startup path to pass explicit generous compatibility timeout overrides when it starts its demo-owned `houmao-server` and launches the detached compatibility session.
- Add demo-owned CLI and shell-wrapper controls for those timeout values so automation can override them without patching code.
- Update the interactive demo contract, docs, and regression tests to describe and verify the demo-specific timeout budgeting, including a longer Codex warmup override.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-server-interactive-full-pipeline-demo`: startup requirements change so the demo-owned server and detached compatibility launch use explicit generous compatibility timeout overrides instead of the generic pair defaults.

## Impact

- Affected code:
  - `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/*`
  - `scripts/demo/houmao-server-interactive-full-pipeline-demo/*`
  - `tests/unit/demo/test_houmao_server_interactive_full_pipeline_demo.py`
- Affected specs:
  - `openspec/specs/houmao-server-interactive-full-pipeline-demo/spec.md`
- Operator impact:
  - Demo startup becomes more robust under real provider latency and automation.
  - Demo operators gain explicit timeout knobs for startup troubleshooting.
