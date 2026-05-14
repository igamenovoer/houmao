## 1. Codex Setup Defaults

- [x] 1.1 Remove fixed `model` keys from repo-owned Codex starter setup assets while preserving provider routing and reasoning defaults.
- [x] 1.2 Update aligned test fixtures and demo assets that currently model repo-owned Codex setup defaults with `model = "gpt-5.4"`.
- [x] 1.3 Ensure the Yunwu/OpenAI-compatible setup keeps `model_provider = "yunwu-openai"` and its provider block without carrying a fixed model pin.

## 2. Launch Policy And Projection

- [x] 2.1 Change Codex launch-policy migration so a missing `model` key remains missing instead of being written to a fixed migration target.
- [x] 2.2 Preserve explicit Codex model projection from copied native baseline, source launch config, launch profile, and direct launch overrides.
- [x] 2.3 Keep reasoning-only Codex projection working when model selection is provider-owned and record clear launch-contract provenance.
- [x] 2.4 Add non-model Codex startup prompt/tooltip suppression for Houmao-managed launches where needed, without setting `model`.

## 3. Tests

- [x] 3.1 Update unit tests that expected missing Codex model state to become `gpt-5.4`.
- [x] 3.2 Add coverage that default Codex setup builds do not synthesize a model key or CLI model override.
- [x] 3.3 Add coverage that explicit Codex model overrides still project to runtime config and final CLI config overrides.
- [x] 3.4 Add coverage that reasoning-only Codex launches project `model_reasoning_effort` without forcing a model.
- [x] 3.5 Add coverage that Yunwu setup remains provider-configured and model-unpinned.

## 4. Documentation And Verification

- [x] 4.1 Update docs or comments that describe `gpt-5.4` as Houmao's maintained default Codex model.
- [x] 4.2 Run focused unit tests for Codex launch policy, brain building, project fixture setup, and model selection.
- [x] 4.3 Run `pixi run typecheck` after implementation.
