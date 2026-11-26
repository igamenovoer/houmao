# Proposal

## Why

Managed Hermes rejects Houmao reasoning presets, and fixture preparation accepts exact effort labels without applying them. This blocks the self-hosted Qwen `xhigh` launch verification. [Issue #103](https://github.com/igamenovoer/houmao/issues/103)

## What Changes

- Resolve Hermes launch presets through Houmao's shared reasoning policy. Project the resulting effort into the private Hermes home for service, TUI, and headless launches.
- Accept an exact Hermes effort through `tool_params.reasoning_effort`. A resolved numeric preset takes precedence. If both inputs are absent, Hermes selects its native default.
- Apply fixture effort from `--reasoning-effort` or the selected model-pool entry in both raw and managed runs. A manager fixture can also select a numeric preset on its launch profile.
- Validate fixture selections before creating run state, and verify the effort on an actual Hermes request to the synthetic Chat Completions peer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-model-selection` gains a Hermes launch reasoning ladder, a native effort default, and secret-free projection evidence.
- `test-agent-launch-fixtures` gains validated Hermes reasoning inputs from direct flags and model pools, with the same native projection across raw and managed fixtures.

## Impact

The change affects the shared model-mapping policy, Hermes tool parameters and home preparation, managed brain construction, and the fixture CLI and documentation. The model pool already has the fields needed for both selection forms.
