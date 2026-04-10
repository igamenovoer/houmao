## Why

Houmao currently presents `--reasoning-level` as a portable normalized `1..10` scale and then distributes that request across each tool's native reasoning controls. That abstraction is misleading because reasoning settings are only meaningful relative to a resolved tool and often a resolved model, so operators who already know the target tool's semantics need a thinner and more predictable mapping.

## What Changes

- **BREAKING** Replace the normalized portable `1..10` reasoning contract with a tool-and-model-specific preset ladder for `reasoning.level`.
- Define `reasoning.level` as an ordinal preset index resolved against the final `(tool, model)` pair, where each increment maps to the next maintained native preset for that runtime.
- Allow `0` only for tool/model combinations that support an explicit off or no-thinking preset.
- Change overflow behavior so values above the highest maintained preset saturate to that preset instead of being evenly redistributed across a global `1..10` range.
- Define Gemini reasoning levels as documented Houmao presets that may map to multiple native Gemini thinking settings together.
- Clarify that operators who need finer vendor-native control should omit Houmao reasoning levels and manage native tool config or env directly.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-model-selection`: replace normalized `1..10` reasoning semantics with tool/model-specific preset ladders, `0` off support when available, and overflow saturation to the maximum maintained preset.
- `brain-launch-runtime`: resolve and record reasoning projection using the resolved tool/model preset ladder rather than evenly distributing a portable range.
- `houmao-mgr-agents-launch`: redefine launch-time `--reasoning-level` semantics around tool/model-specific preset ladders.
- `houmao-srv-ctrl-native-cli`: redefine request-scoped headless prompt `--reasoning-level` semantics and validation around tool/model-specific preset ladders.
- `houmao-mgr-project-agents-presets`: redefine stored recipe reasoning defaults away from normalized `1..10` semantics.
- `houmao-mgr-project-agents-launch-profiles`: redefine stored launch-profile reasoning overrides away from normalized `1..10` semantics.
- `houmao-mgr-project-easy-cli`: redefine easy specialist/profile/instance reasoning defaults and overrides away from normalized `1..10` semantics.
- `docs-cli-reference`: update CLI reference requirements so operator-facing docs describe tool/model-specific preset ladders and Gemini preset mapping guidance.

## Impact

- Affected code: `src/houmao/agents/model_selection.py`, `src/houmao/agents/model_mapping_policy.py`, `src/houmao/agents/brain_builder.py`, managed runtime request-override handling, and CLI flag validation in `src/houmao/srv_ctrl/commands/**`.
- Affected APIs: launch-owned `launch.model.reasoning.level`, request-scoped `execution.model.reasoning.level`, and all CLI help/docs that currently describe a normalized `1..10` scale.
- Affected systems: build manifests that record reasoning projection provenance and documentation for Codex, Claude, Gemini, and future tools with model-specific reasoning ladders.
