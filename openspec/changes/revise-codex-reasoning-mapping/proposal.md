## Why

Houmao's current Codex reasoning-level mapping treats Codex's generic `ReasoningEffort` enum as if every Codex model supports every enum value. That is materially wrong for current Codex models: for example, the local Codex model catalog exposes `gpt-5.4` and `gpt-5.3-codex` with supported reasoning levels `low`, `medium`, `high`, and `xhigh`, while Houmao currently maps reasoning level `1` to `minimal`.

This creates a mismatch between Houmao-managed launches, Codex TUI model-selection behavior, and Codex model metadata. The mapping needs to become model-aware so Houmao only projects reasoning efforts supported by the resolved Codex model.

## What Changes

- Revise Codex reasoning-level mapping to use a maintained model-aware ladder rather than one broad Codex enum ladder.
- Map current maintained Codex coding models such as `gpt-5.4`, `gpt-5.3-codex`, and `gpt-5.2-codex` to `1=low`, `2=medium`, `3=high`, and `4=xhigh`, with higher positive values saturating to `xhigh`.
- Preserve `0=none` only for resolved Codex models whose supported reasoning ladder explicitly includes an off/no-reasoning preset.
- Reject `0` clearly for resolved Codex models that do not support an off preset.
- Keep Codex projection behavior unchanged after mapping resolution: write `model_reasoning_effort` into the constructed runtime `config.toml` and emit final Codex CLI config override arguments.
- Update documentation and tests so user-facing `--reasoning-level` guidance matches Codex TUI and Codex model metadata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-model-selection`: Codex reasoning preset requirements become model-aware and no longer imply that `minimal` is the first supported preset for all Codex models.

## Impact

- Affected implementation: `src/houmao/agents/model_mapping_policy.py` and related Codex model-selection projection tests.
- Affected docs: CLI and getting-started pages that currently document Codex as `0=none`, `1=minimal`, `2=low`, `3=medium`, `4=high`, `5=xhigh`.
- Affected behavior: existing authored `--reasoning-level 1` or stored `reasoning.level: 1` for current Codex coding models will resolve to `low` instead of `minimal`. This aligns with Codex model metadata and the TUI picker for those models.
- No credential, auth-bundle, or setup-bundle format migration is required.
