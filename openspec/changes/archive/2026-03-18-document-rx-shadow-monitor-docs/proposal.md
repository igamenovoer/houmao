## Why

The completed `rx-shadow-turn-monitor` change replaced the old `_TurnMonitor` implementation with ReactiveX-based readiness and completion pipelines, but the published TUI parsing docs still teach the pre-Rx model. That leaves maintainers and operators reading obsolete lifecycle rules, outdated change-detection semantics, and incomplete configuration guidance.

## What Changes

- Refresh the TUI parsing developer guide so it describes the shipped runtime monitor architecture built around `cao_rx_monitor.py` and current-thread CAO polling in `cao_rest.py`.
- Update lifecycle documentation to explain the current readiness and completion priority order, completion stability gating, normalized-text change evidence, and unknown-to-stalled recovery behavior.
- Update reference and troubleshooting pages to include the shipped `completion_stability_seconds` policy surface, current diagnostics fields, and the actual timeout/completion semantics operators see in `shadow_only`.
- Reconcile parser/provider pages so they stop implying that runtime lifecycle still depends on the old `TurnMonitor` abstraction or on `dialog_text` as the lifecycle-evidence surface.
- Keep docs navigation aligned with the maintained explanation, and add one focused developer page only if the existing architecture/lifecycle pages cannot cover the Rx monitor clearly without becoming muddled.

## Capabilities

### New Capabilities
- `tui-parsing-docs`: Provide maintained developer and reference documentation for CAO `shadow_only` TUI parsing, covering parser/runtime boundaries, runtime monitor lifecycle semantics, configuration and diagnostics, troubleshooting, and source-aligned navigation.

### Modified Capabilities
- None.

## Impact

- Affected docs: `docs/developer/tui-parsing/`, `docs/reference/realm_controller.md`, `docs/reference/cao_claude_shadow_parsing.md`, `docs/reference/cao_shadow_parser_troubleshooting.md`, and top-level docs navigation if a new page is added.
- Affected source material: `src/houmao/agents/realm_controller/backends/cao_rx_monitor.py`, `src/houmao/agents/realm_controller/backends/cao_rest.py`, `src/houmao/agents/realm_controller/launch_plan.py`, `tests/unit/agents/realm_controller/test_cao_rx_monitor.py`, and the completed `openspec/changes/rx-shadow-turn-monitor/` artifacts become the main inputs for the doc refresh.
- Runtime code impact: none intended; this change documents the already-shipped contract and makes the maintained explanation consistent with implementation and tests.
