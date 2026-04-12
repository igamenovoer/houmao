## 1. Mapping Policy

- [x] 1.1 Update `src/houmao/agents/model_mapping_policy.py` so Codex reasoning ladder resolution is model-aware instead of using one universal Codex enum ladder.
- [x] 1.2 Add maintained Codex coding-model ladder coverage for `gpt-5.4`, `gpt-5.3-codex`, and `gpt-5.2-codex` with positive presets `1=low`, `2=medium`, `3=high`, and `4=xhigh`.
- [x] 1.3 Ensure higher positive Codex levels saturate to `xhigh` and preserve `requested_level`, `effective_level`, and `saturated` provenance.
- [x] 1.4 Ensure `0` is accepted only for Codex model ladders that explicitly support an off preset and is rejected clearly otherwise.
- [x] 1.5 Ensure `minimal` is projected only when the resolved Codex model ladder explicitly includes `minimal`.

## 2. Tests

- [x] 2.1 Update `tests/unit/agents/test_model_mapping_policy.py` so current maintained Codex coding models map reasoning level `1` to `low` instead of `minimal`.
- [x] 2.2 Add coverage for saturation on the four-step Codex coding-model ladder, such as `reasoning.level=10` mapping to `xhigh`.
- [x] 2.3 Add coverage for Codex `0` behavior on a model ladder without an off preset.
- [x] 2.4 Update projection assertions so generated Codex runtime `config.toml` and CLI `--config=model_reasoning_effort=...` overrides use the revised native value.
- [x] 2.5 Update any affected brain-builder, launch-plan, or headless request-scoped override tests that assumed `1=minimal` or a five-step positive Codex ladder.

## 3. Documentation

- [x] 3.1 Update `docs/getting-started/easy-specialists.md` to describe Codex reasoning levels as model-aware and document the maintained current Codex coding-model ladder.
- [x] 3.2 Update `docs/reference/cli/houmao-mgr.md` to remove the universal Codex `1=minimal` table and replace it with model-aware guidance.
- [x] 3.3 Search docs and OpenSpec specs for stale Codex ladder text and update maintained user-facing references where appropriate.

## 4. Validation

- [x] 4.1 Run `pixi run test tests/unit/agents/test_model_mapping_policy.py`.
- [x] 4.2 Run targeted affected tests found during implementation, such as Codex CLI config, brain-builder, launch-plan, or headless tests.
- [x] 4.3 Run `pixi run openspec validate revise-codex-reasoning-mapping --strict`.
