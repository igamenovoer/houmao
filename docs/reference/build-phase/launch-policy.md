# Launch Policy

The launch policy engine governs agent behavior during the run phase by applying a set of typed mutations to the launch environment. Policies are resolved during the build phase and control agent autonomy, prompt modes, and provider-specific configuration.

## Operator Prompt Mode

The `OperatorPromptMode` determines how the agent interacts with the operator during execution:

| Mode | Description |
|---|---|
| `as_is` | Standard mode. Normal operator interaction and prompts are enabled. No launch policy is applied. |
| `unattended` | Fully automated mode. All interactive prompts are suppressed and the launch policy strategy configures the tool for hands-off execution. |

When no mode is specified or `as_is` is selected, the policy engine returns the executable and base arguments without applying any strategy.

## Policy Strategy

A `LaunchPolicyStrategy` is the core unit of the policy engine. Each strategy contains:

- **strategy_id**: Unique identifier (e.g., `claude-unattended-2.1.81`).
- **operator_prompt_mode**: Which mode this strategy applies to.
- **backends**: List of supported launch surfaces (e.g., `raw_launch`, `claude_headless`, `codex_headless`). Note: `LaunchSurface` (build-phase) includes `raw_launch` for generic local execution, while the run-phase `BackendKind` type uses `local_interactive` instead; `raw_launch` maps to `local_interactive` at runtime.
- **supported_versions**: PEP 440-style version specifier for tool version compatibility (e.g., `>=2.1.81`).
- **minimal_inputs**: Contract requirements — acceptable credential forms, whether user-prepared state is needed.
- **owned_paths**: File paths and keys the strategy manages to avoid conflicts with user configuration.
- **actions**: Ordered list of mutations to apply to the launch environment.

## Policy Resolution

Strategies are resolved from the versioned registry with this precedence:

| Priority | Source | Description |
|---|---|---|
| 1 | `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` | Environment variable. Must name a strategy_id that matches the requested mode and backend. |
| 2 | Registry documents | Tool-specific YAML files in `agents/launch_policy/registry/`. Filtered by mode, backend, and detected tool version. Must produce exactly one match. |
| 3 | No policy | When mode is `None` or `as_is`, the engine returns the raw executable with no mutations. |

Resolution detects the tool version by running `<executable> --version` and parsing the semantic version. The detected version is matched against each strategy's `supported_versions` specifier.

## Provider Hooks

Provider hooks are named actions within a strategy that perform provider-specific setup:

### Claude Hooks

| Hook | Description |
|---|---|
| `claude.ensure_api_key_approval` | Seeds API-key approval state in `.claude.json` without storing the full key. |
| `claude.ensure_project_trust` | Seeds workspace trust state for the resolved working directory. |

### Codex Hooks

| Hook | Description |
|---|---|
| `codex.canonicalize_unattended_launch_inputs` | Strips caller-supplied overrides that target unattended surfaces (e.g., `--full-auto`, `--sandbox`). |
| `codex.validate_credential_readiness` | Ensures `auth.json` exists or a config-backed env-only provider is set up. |
| `codex.ensure_project_trust` | Seeds project trust level in `config.toml`. |
| `codex.ensure_model_migration_state` | Migrates known legacy Codex model pins without creating a model selection when none exists. |
| `codex.append_unattended_cli_overrides` | Appends final Codex CLI `-c` override arguments for `approval_policy`, `sandbox_mode`, `notice.hide_full_access_warning`, and `tui.show_tooltips` so project-local `config.toml` cannot weaken unattended posture. |

### Kimi Hooks

| Hook | Description |
|---|---|
| `kimi.canonicalize_unattended_launch_inputs` | Strips caller-supplied Kimi prompt-mode-owned args such as `-p`, `--prompt`, `--output-format`, `--session`, `--continue`, `--skills-dir`, `--auto`, `--yolo`, and `--plan` before the `kimi_headless` backend builds the final command. |
| `kimi.canonicalize_unattended_tui_launch_inputs` | Strips caller-supplied permission and session-startup flags before the `raw_launch` strategy restores its selected session selector and appends exactly one strategy-owned native `--auto`. |

Hooks run within a provider state mutation lock for thread-safe file access.

## Kimi Unattended Posture

Maintained Kimi unattended startup is version-scoped to Kimi Code 0.23.x and has two backend contracts:

- `kimi_headless` owns prompt-mode command placement. Exact resume uses `--session <session_id>`, latest resume uses `--continue`, the prompt value follows `-p`, output format is `stream-json`, and managed skills use `--skills-dir <KIMI_CODE_HOME>/skills`. Prompt mode removes TUI permission flags because `-p` is already non-interactive.
- Kimi TUI launch uses the `raw_launch` surface, which maps to `local_interactive`. The strategy strips caller-owned permission and session selectors, restores the selected fresh/latest/exact session selector, writes `.skip-migration-from-kimi-cli`, keeps `default_permission_mode = "auto"` as a managed-home fallback, and appends one native `--auto` argument.

Kimi Code 0.23.x accepts native `--auto` with fresh, `--continue`, and `--session <session_id>` TUI startup. Houmao no longer sends a post-readiness `/auto on` command. `as_is` launches preserve native approval behavior and do not receive the strategy-owned `--auto` argument.

Kimi auto permission mode is the provider-native no-question posture: normal tool approvals are automatic and `AskUserQuestion` requests are denied so the agent must decide and continue. It does not bypass explicit Kimi hard-deny policies or user-configured deny rules.

Kimi Code 0.23.x managed role delivery uses bootstrap or auto-skill workflows. Houmao can project `houmao-auto-system-prompt` into managed Kimi homes; users may need to invoke it before substantive chat when automatic skill startup does not run first.

## Current Reasoning Projection

Codex GPT-5.6 mapping uses model-specific ordered ladders. Sol and Terra map normalized levels 1 through 6 to `low`, `medium`, `high`, `xhigh`, `max`, and `ultra`; Luna maps levels 1 through 5 to `low`, `medium`, `high`, `xhigh`, and `max`. Level 0 is rejected, and values above a model's ladder saturate at its last native effort with provenance.

Kimi config-backed models derive their ordered ladder from the selected `[models.<alias>].capabilities.support_efforts` list after applying model overrides. Level 0 disables thinking only when the model does not require `always_thinking`; positive values select or saturate within that discovered order. Env-model credentials retain native effort environment values when no normalized override is requested, but normalized `reasoning_level` is rejected because that lane does not provide an ordered catalog.

## Versioned Registry

The registry stores strategies in per-tool YAML files under `agents/launch_policy/registry/`:

```
agents/launch_policy/registry/
  claude.yaml     # strategies for Claude Code
  codex.yaml      # strategies for Codex CLI
  kimi.yaml       # strategies for Kimi Code
```

Each file enforces `schema_version: 1` and contains one or more strategy definitions. Multiple strategies can coexist in one file with different `supported_versions` ranges — the resolution logic selects the unique matching strategy for the detected tool version.

## Integration with the Build Phase

During `BrainBuilder.build()`, the launch policy is resolved and included in the `BrainManifest`. The resolution flow:

1. The build request specifies an `operator_prompt_mode` (from the recipe, the resolved launch profile, or direct input).
2. The policy engine detects the tool version and finds the matching strategy from the registry.
3. The strategy's actions are applied to the launch environment (environment variables, config file mutations, provider hooks).
4. The resolved strategy provenance is recorded in the manifest for diagnostic traceability.

## See Also

- [Launch Overrides](launch-overrides.md) — the related override system for launch parameters
- [Backends](../run-phase/backends.md) — backend model and dispatch
- [Session Lifecycle](../run-phase/session-lifecycle.md) — how the resolved policy affects session startup
