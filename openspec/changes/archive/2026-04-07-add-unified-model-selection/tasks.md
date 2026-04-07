## 1. Shared Model-Configuration Data Model

- [x] 1.1 Extend the canonical launch-owned model field into structured model configuration that supports `name` plus normalized `reasoning.level`, including low-level recipe add/set support for `--model`, `--reasoning-level`, `--clear-model`, and `--clear-reasoning-level`.
- [x] 1.2 Extend project-easy specialist and easy-profile authoring plus explicit launch-profile persistence so stored specialist/profile metadata can carry reusable model and reasoning overrides.
- [x] 1.3 Add the required catalog and projection migration for launch-profile model-configuration storage and make list/get output report stored values as launch configuration rather than auth content.

## 2. Launch Resolution And Runtime Projection

- [x] 2.1 Extend direct launch and profile-backed launch resolution to accept unified `--model` and `--reasoning-level` overrides and compose effective model configuration through the defined precedence chain on a per-subfield basis.
- [x] 2.2 Add a dedicated Houmao Python mapping-policy module that converts normalized reasoning levels plus runtime context such as tool, model name, and tool version into native config/env edits and provenance.
- [x] 2.3 Extend brain-build inputs and manifest/runtime provenance so the resolved effective model, requested normalized reasoning level, resolved native mapping, and source layers are preserved in secret-free build metadata.
- [x] 2.4 Implement per-tool runtime-home projection for the resolved model name into Claude `ANTHROPIC_MODEL`, Codex `${CODEX_HOME}/config.toml` `model`, and Gemini `${GEMINI_CLI_HOME}/.gemini/settings.json` `model.name`, plus reasoning projection through the mapping policy into each tool's native reasoning surfaces.
- [x] 2.5 Integrate model-configuration projection with launch-policy and provider-hook flows so explicit resolved model or reasoning choices survive unattended policy mutation and legacy setup/auth state remains a fallback only when no unified launch-owned value is supplied.

## 3. Compatibility, Verification, And Documentation

- [x] 3.1 Add or update tests for recipe parsing, launch-profile persistence, and easy-specialist/easy-profile authoring of unified model configuration, including reasoning-level validation and field clearing.
- [x] 3.2 Add launch/build tests that verify source default, launch-profile default, and direct override precedence for both model name and reasoning level together with tool-specific runtime projection for Claude, Codex, and Gemini.
- [x] 3.3 Add mapping-policy tests that verify normalized level `1` maps to the lowest supported native reasoning configuration, `10` maps to the highest, and intermediate unsupported levels clamp or resolve according to policy with provenance.
- [x] 3.4 Update CLI help text and relevant docs to present `--model` and `--reasoning-level` as the supported unified surfaces, explain that `reasoning-level` is a Houmao-defined 1..10 scale, document any temporary compatibility treatment for legacy tool-specific model flags such as `--claude-model`, and direct detailed vendor-native tuning to skills rather than the core CLI.
