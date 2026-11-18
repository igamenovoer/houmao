# Proposal

## Why

Houmao's authoring and runtime manifests currently normalize cross-tool fields (`model`, `reasoning.level`, `operator_prompt_mode`, `env`, `skills`, `mailbox`) while lacking a structured, per-tool configuration slot across specialists, presets, launch profiles, and launch overrides. Existing `launch_overrides.tool_params` accepts only boolean CLI-flag projections declared in `adapter.yaml` (`claude.include_partial_messages`), which forced each CLI integration into ad hoc side channels such as DSH's standalone `dsh-setup.yaml` file outside `houmao-mgr` profiles and manifests.

## What Changes

- **BREAKING**: Remove the declarative YAML `launch.metadata.tool_params` boolean-only projection mini-DSL from `adapter.yaml` and `src/houmao/agents/launch_overrides/`, replacing it with a Python `ToolParamsAdapter` registry (`src/houmao/agents/tool_params/`) where each supported tool (`claude`, `codex`, `kimi`, `dsh`) owns its Pydantic v2 schema and launch materialization logic.
- **BREAKING**: Promote `tool_params` to a first-class per-tool mapping across all five Houmao configuration layers (`tools/<tool>/adapter.yaml` `launch.default_tool_params` -> optional `tools/<tool>/setups/<name>/tool-params.yaml` -> specialist/preset `tool_params` -> profile/launch-profile `tool_params` -> direct build/launch `tool_params`), removing `launch.overrides.tool_params` on presets while keeping `launch.overrides.args` for raw CLI argument overrides.
- **BREAKING**: Retire DSH's bespoke `dsh-setup.yaml` setup filename and `selected_model` field in favor of `DshToolParams` (`tool-params.yaml` in `setups/<name>/` plus `tool_params` overrides on specialists, presets, profiles, and launches), unifying DSH model selection onto Houmao's standard `model.name` field and materializing `<DSH_HOME>/houmao-tool-params.yaml` alongside `<DSH_HOME>/houmao-profile.patch.json`.
- Use field-presence-aware merging (`model_fields_set`), partial schema validation at authoring time, and effective schema validation before brain construction. For managed launches, resolve the backend, model, and credential binding in the execution owner and validate the merged inputs before creating runtime state or taking over an existing agent. Build and launch from the same validated configuration.
- Keep DSH MCP header and environment values in the selected private credential bundle. Store only value references in `tool_params` and resolve them when preparing the native invocation. Validation diagnostics identify the source layer and field without printing the input value.
- Migrate `claude.include_partial_messages` into `ClaudeToolParamsAdapter`, register strict extensible `CodexToolParamsAdapter` and `KimiToolParamsAdapter` schemas without altering existing `config.toml` behavior, and expose `dsh` under `houmao-mgr project agents tools` / `internals native-agent tools`.
- Add `--tool-params <json-or-@path>` and `--clear-tool-params` options across `houmao-mgr project specialist create|set`, `project profile create|set`, `internals native-agent recipes` / `project agents presets`, `internals native-agent launch-dossiers` / `project agents launch-profiles`, `brains build`, and `project agents launch`, persisting secret-free per-layer and effective `tool_params` in SQLite (`catalog.db`), compatibility YAML projections, and `brain_manifest.yaml`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `recipe-launch-overrides`: Replace the YAML `launch.metadata.tool_params` boolean flag projector with Python per-tool `ToolParamsAdapter` schemas, five-layer `tool_params` merging, and adapter-owned home/backend application while keeping `launch.overrides.args`.
- `component-agent-construction`: Accept layered `tool_params` inputs during brain construction, run per-tool `materialize_home()` hooks, and persist secret-free per-layer and effective `tool_params` in resolved brain manifests alongside `launch_overrides`. Preserve DSH MCP references in persisted tool parameters and resolve their values privately.
- `agent-launch-profiles`: Store optional birth-time `tool_params` on project profiles and explicit launch profiles with field-aware patch merging, clear-on-replace behavior, and compatibility YAML projection.
- `houmao-mgr-project-easy-cli`: Support `--tool-params` and `--clear-tool-params` on `project specialist`, `project profile`, and `project agents launch` commands with authoring-time per-tool validation and `get` inspection output.
- `houmao-mgr-project-agents-launch-profiles`: Support `--tool-params` and `--clear-tool-params` on explicit launch-dossier `add`, `set`, and `get` commands.
- `houmao-mgr-project-agent-tools`: Expose `dsh` in tool/setup administration commands and recognize optional `tool-params.yaml` seed files inside `tools/<tool>/setups/<name>/`.
- `houmao-mgr-agents-launch`: Support one-shot `--tool-params` overrides on `houmao-mgr project agents launch` and validate the effective launch in the execution owner before runtime creation or force takeover.
- `brain-launch-runtime`: Replace `dsh-setup.yaml` runtime configuration inputs with `DshToolParams` (`tool_params` layers materialized to `houmao-tool-params.yaml` and `houmao-profile.patch.json`) and unify DSH model selection with Houmao `model.name`.

## Impact

- New per-tool adapter package: `src/houmao/agents/tool_params/` (`base.py`, `registry.py`, `claude.py`, `codex.py`, `kimi.py`, `dsh.py`).
- Core parsing, catalog, build, and launch pipeline: `src/houmao/agents/definition_parser.py`, `src/houmao/agents/launch_overrides/{models.py,resolver.py}`, `src/houmao/project/catalog.py`, `src/houmao/project/launch_profiles.py`, `src/houmao/project/agent_definitions.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/dsh_configuration.py`, `src/houmao/agents/model_mapping_policy.py`, `src/houmao/agents/realm_controller/{launch_plan.py,native_refresh.py}`.
- CLI surfaces and starter/test assets: `src/houmao/srv_ctrl/commands/{project_easy.py,project_definitions.py,project_launch_profiles.py,project_tools.py,brains.py,managed_agents.py,agents/core.py}`, `src/houmao/project/assets/starter_agents/tools/{claude,codex,kimi,dsh}/`, `tests/fixtures/`, and `scripts/agents/test-fixtures/`.
- Downstream stacked change: `openspec/changes/align-dsh-native-configuration` builds directly on `DshToolParams` from this refactor rather than introducing `dsh-setup.yaml` v2.
