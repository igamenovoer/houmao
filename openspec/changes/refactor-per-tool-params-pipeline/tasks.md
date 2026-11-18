# Tasks

## 1. Per-Tool Adapter Package and Launch-Override Refactor

- [ ] 1.1 Create `src/houmao/agents/tool_params/` (`base.py`, `registry.py`, `claude.py`, `codex.py`, `kimi.py`, `dsh.py`) implementing `ToolParamsAdapter[PartialT, EffectiveT]`, secret-free validation, `model_fields_set` deep merging, `parse_tool_params_cli_input()`, `ClaudeToolParamsAdapter` (`include_partial_messages`), `CodexToolParamsAdapter`, `KimiToolParamsAdapter`, and `DshToolParamsAdapter`, and verify with unit tests in `tests/unit/agents/test_tool_params.py` plus `pixi run typecheck`.
- [ ] 1.2 Remove the YAML `launch.metadata.tool_params` projection DSL and `launch.overrides.tool_params` from `src/houmao/agents/launch_overrides/{models,resolver}.py`, `src/houmao/agents/definition_parser.py`, `src/houmao/project/assets/starter_agents/tools/*/adapter.yaml`, and `tests/fixtures/plain-agent-def/tools/*/adapter.yaml`, promoting top-level `tool_params` on `AgentPreset`, and verify with `pixi run pytest tests/unit/agents/ -k "launch_override or definition_parser" -q`.

## 2. Brain Builder, Launch Plan, and DSH Home Materialization

- [ ] 2.1 Wire five-layer `tool_params` resolution (`adapter.yaml` -> `<setup>/tool-params.yaml` -> `preset/specialist` -> `launch_profile` -> `direct`) into `src/houmao/agents/brain_builder.py`, `src/houmao/agents/model_mapping_policy.py`, `src/houmao/agents/realm_controller/launch_plan.py`, and `src/houmao/agents/realm_controller/native_refresh.py`. Separate read-only effective and backend validation from materialization. Persist the validated layers and effective `tool_params` in the brain manifest. Verify with `pixi run pytest tests/unit/agents/ -k "brain_builder or launch_plan" -q`.
- [ ] 2.2 Replace `dsh-setup.yaml` and `selected_model` with `DshToolParams` (`tool-params.yaml` in `src/houmao/project/assets/starter_agents/tools/dsh/setups/{default,openai-compatible}/` and `tests/fixtures/plain-agent-def/tools/dsh/setups/default/`, materializing `<DSH_HOME>/houmao-tool-params.yaml` and `<DSH_HOME>/houmao-profile.patch.json`), update `docs/reference/run-phase/dsh-headless.md`, and verify with `pixi run pytest tests/unit/agents/test_dsh_configuration.py tests/unit/agents/test_dsh_launch_surfaces.py tests/unit/agents/test_dsh_current_home.py -q`.
- [ ] 2.3 Require `env_ref` for DSH MCP header and environment values. Validate references against the selected owner-private bundle and resolve their values for supported native invocations, including ACP turns that reload current MCP declarations. Preserve referenced values on unrelated bundle updates. Use synthetic values to test catalog, YAML, brain manifest, and generated home persistence, credential inspection, private invocation projection, and value-free errors for literal or unresolved references.

## 3. Project Catalog, Launch Profiles, and `houmao-mgr` CLI Surfaces

- [ ] 3.1 Add `tool_params` storage, patch merging, clear-on-replace semantics, and YAML projection to `src/houmao/project/catalog.py`, `src/houmao/project/launch_profiles.py`, and `src/houmao/project/agent_definitions.py` (with idempotent `launch_profiles.tool_params_payload` column upgrade), and verify with catalog and launch-profile unit tests in `tests/unit/project/`.
- [ ] 3.2 Add `--tool-params <json-or-@path>` and `--clear-tool-params` to `src/houmao/srv_ctrl/commands/{project_easy.py,project_definitions.py,project_launch_profiles.py,brains.py,managed_agents.py}`, expose `dsh` in `src/houmao/srv_ctrl/commands/project_tools.py`, update CLI/profile reference docs under `docs/`, and verify with CLI unit tests in `tests/unit/srv_ctrl/`.
- [ ] 3.3 In the managed launch path, including `src/houmao/srv_ctrl/commands/agents/core.py`, resolve and validate all five layers, the backend, the model, and the credential binding in the execution owner before runtime allocation or force takeover. Pass the validated inputs to brain construction and launch planning. Test owner-side `@<path>` loading, preservation of the predecessor and its artifacts on invalid merged inputs in both force modes, and use of the validated inputs when an authoring layer changes after preflight.

## 4. Test Fixtures and Cross-Suite Verification

- [ ] 4.1 Migrate `scripts/agents/test-fixtures/` (`fixturelib`) and `tests/integration/agents/dsh/**` from `dsh-setup.yaml` to `tool_params` (`tool-params.yaml` / `--tool-params`), and verify `pixi run pytest tests/unit/agents/test_dsh_fixture_tools.py -q`.
- [ ] 4.2 Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, and the isolated-tmux DSH integration suite (`tests/integration/agents/dsh/`), verifying zero regressions across Claude, Codex, Kimi, and DSH before starting `align-dsh-native-configuration`.

## Workflow follow-up

- Verify and archive `refactor-per-tool-params-pipeline` (or apply stacked `align-dsh-native-configuration` immediately on top once verified).
