## 1. Model Projection Plumbing

- [x] 1.1 Update Claude model-name projection so launch-owned model names produce secret-free final CLI args metadata for `--model <name>` instead of relying on a newly projected `ANTHROPIC_MODEL` value.
- [x] 1.2 Update Claude reasoning projection so resolved native effort values produce secret-free final CLI args metadata for `--effort <level>`.
- [x] 1.3 Preserve Claude auth-bundle and copied-native env vars as baseline inputs, including `ANTHROPIC_MODEL` and alias pinning variables, without treating them as the primary launch-owned override surface.
- [x] 1.4 Extend model-selection manifest/provenance payloads to record Claude generated CLI args alongside the resolved model/reasoning sources and native mapping summary.

## 2. Launch Plan Integration

- [x] 2.1 Teach launch-plan construction to extract generated Claude model-selection CLI args from the brain manifest.
- [x] 2.2 Append generated Claude `--model` and `--effort` args to final provider launch args for local interactive TUI launches.
- [x] 2.3 Append generated Claude `--model` and `--effort` args to final provider launch args for Claude headless launches.
- [x] 2.4 Keep generated Claude args non-secret and scoped to the current launch; do not rewrite source recipes, specialists, launch profiles, or auth bundles.
- [x] 2.5 Handle conflicting caller-supplied Claude model/effort args deterministically, preserving the existing precedence rule that direct launch overrides win over source and profile defaults.

## 3. Request-Scoped Headless Overrides

- [x] 3.1 Update Claude request-scoped headless model overrides to use temporary `--model` CLI args when a prompt request supplies `execution.model.name`.
- [x] 3.2 Update Claude request-scoped headless reasoning overrides to use temporary `--effort` CLI args when a prompt request supplies `execution.model.reasoning.level`.
- [x] 3.3 Ensure request-scoped Claude model/effort args apply only to the accepted prompt execution and do not persist as later default execution state.

## 4. Tests and Validation

- [x] 4.1 Add or update unit tests for Claude brain-home/model-selection projection metadata for `--model` and `--effort`.
- [x] 4.2 Add or update launch-plan tests proving local interactive Claude launch args include generated `--model` and `--effort`.
- [x] 4.3 Add or update headless backend tests proving Claude headless launch args include generated `--model` and `--effort`.
- [x] 4.4 Add or update request-scoped headless override tests proving temporary Claude `--model` and `--effort` args are not persisted.
- [x] 4.5 Run focused unit tests for model selection and launch-plan behavior, then run the broader relevant test target before marking the change implemented.
  - Focused tests passed: `pixi run pytest tests/unit/agents/test_model_mapping_policy.py tests/unit/agents/test_brain_builder.py tests/unit/agents/realm_controller/test_loaders_and_launch_plan.py tests/unit/agents/realm_controller/test_headless_base.py`.
  - Touched files passed Ruff: `pixi run ruff check src/houmao/agents/model_mapping_policy.py src/houmao/agents/brain_builder.py src/houmao/agents/realm_controller/launch_plan.py tests/unit/agents/test_model_mapping_policy.py tests/unit/agents/test_brain_builder.py tests/unit/agents/realm_controller/test_loaders_and_launch_plan.py tests/unit/agents/realm_controller/test_headless_base.py`.
  - Touched source modules passed targeted type checking: `pixi run mypy src/houmao/agents/model_mapping_policy.py src/houmao/agents/brain_builder.py src/houmao/agents/realm_controller/launch_plan.py`.
  - Live Claude TUI probe passed in `tmp/claude-cli-live.BCRThK`: project easy launch generated `claude --model sonnet --effort high`, and the live pane rendered `Sonnet 4.6 with high effort · Claude Max`.
  - Broader unit target was run with `pixi run test` and failed in unrelated existing areas: CLI project-catalog setup, runtime-registry fake method signatures, legacy demo copy text, passive-server client payload expectations, and system-skill inventory.
