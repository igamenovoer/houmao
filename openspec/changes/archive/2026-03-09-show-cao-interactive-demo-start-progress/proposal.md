## Why

The interactive demo `start` command can spend a noticeable amount of time waiting for the CAO-backed Claude session to launch and become ready for input, but today it stays visually silent until the subprocess finally returns. That makes the demo feel hung even when it is progressing normally, which is a poor operator experience for a tutorial workflow that is meant to be trusted and repeatable.

## What Changes

- Add operator-visible progress output for the interactive demo `start` flow so users can see that setup is still advancing before the final success JSON is printed.
- Preserve the existing machine-readable success payload by keeping progress breadcrumbs separate from the final structured `start` result.
- Surface especially clear waiting feedback around the long-running `brain_launch_runtime start-session` phase, including periodic elapsed-time heartbeats while Claude startup/readiness is still in progress.
- Extend documentation and tests so the startup-progress contract is explicit and regression-covered.

## Capabilities

### New Capabilities
- `cao-interactive-demo-start-progress`: Operator-visible progress and waiting feedback for the interactive CAO demo startup flow.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py`, `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`, `scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh`, and related tests under `tests/unit/demo/`.
- Affected operator behavior: `run_demo.sh start` and wrapper-driven startup will print human-friendly progress breadcrumbs while the session is still launching, instead of appearing idle until the final JSON arrives.
- Compatibility: the final success payload on stdout should remain machine-readable so existing wrapper behavior and manual scripting do not break.
