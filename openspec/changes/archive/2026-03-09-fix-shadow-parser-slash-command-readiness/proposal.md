## Why

The interactive CAO demo can become unable to send additional turns after an operator uses a Claude slash command such as `/model` or performs manual model switching. This blocks a core multi-turn workflow and is especially confusing because the session can still look `idle` at the raw CAO terminal-status level while runtime shadow gating refuses to submit the next prompt.

## What Changes

- Tighten Claude/Codex shadow-parser surface classification so slash-command context is derived from the live prompt surface instead of any historical slash-command line still visible in full scrollback.
- Update CAO `shadow_only` readiness rules so resumed prompt submission is allowed once the visible surface returns to a normal input prompt after slash-command handling.
- Extend the interactive CAO full-pipeline demo contract to preserve `send-turn` usability across operator-driven slash-command/model-switch interactions within the same session.
- Add regression coverage for parser classification and CAO runtime/demo flows that previously wedged after `/model` remained in scrollback history.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: refine `shadow_only` readiness semantics so historical slash-command output does not keep a recovered normal prompt blocked.
- `versioned-shadow-parser-stack`: refine slash-command surface detection to follow the active prompt region rather than any slash command present in prior scrollback.
- `cao-interactive-full-pipeline-demo`: require follow-up `send-turn` operations to keep working after in-session slash commands or model switching when the session has returned to its normal prompt.

## Impact

- `src/gig_agents/agents/brain_launch_runtime/backends/claude_code_shadow.py`
- `src/gig_agents/agents/brain_launch_runtime/backends/codex_shadow.py`
- `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py`
- `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py`
- Runtime/demo regression tests under `tests/unit/agents/brain_launch_runtime/` and `tests/unit|integration/demo/`
