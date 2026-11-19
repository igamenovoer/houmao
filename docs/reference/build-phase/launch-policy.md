# Launch Policy

The brain manifest records the authored launch inputs. At provider start, the launch policy engine resolves permission settings for the selected backend and projects them into native configuration, launch arguments, or session startup requests.

## Operator Prompt Mode

The `OperatorPromptMode` determines how the agent interacts with the operator during execution:

| Mode | Description |
|---|---|
| `as_is` | Applies supported authored values and uses the native baseline for omitted settings. |
| `unattended` | Supplies the most permissive supported native permission defaults with routine approvals disabled for omitted settings. |

An explicit supported value takes precedence in either mode and can require operator approval. Native administrative rules and the selected execution owner still bound the agent's authority.

| Tool | Native Fields in `tool_params` | Omitted Unattended Defaults |
|---|---|---|
| Claude | `permission_mode` | `bypassPermissions` |
| Codex | `approval_policy`, `sandbox_mode` | `never`, `danger-full-access` |
| Kimi | `permission_mode` | `auto` |
| DSH | `permissions.sandbox`, `permissions.approval` | `danger-full-access`, `never` |

Use the [launch override layers](launch-overrides.md) for configurable values. Machine-readable output, native session identity, private service endpoints, and DSH's `hmr` activation boundary belong to Houmao. A supplied value for a reserved setting causes a validation error, even if it is identical to the value Houmao derives.

To retain DSH's previous workspace restriction, set the following in a specialist or launch profile. Under unattended mode, the omitted approval field still resolves to `never`. The same settings apply to headless, ACP service, and Web.

```yaml
tool_params:
  permissions:
    sandbox: workspace-write
```

## Policy Strategy

A `LaunchPolicyStrategy` is the core unit of the policy engine. Each strategy contains:

- **strategy_id**: Unique identifier (e.g., `claude-unattended-2.1.296`).
- **operator_prompt_mode**: Which mode this strategy applies to.
- **backends**: List of supported launch surfaces (e.g., `raw_launch`, `claude_headless`, `codex_headless`). Note: `LaunchSurface` (build-phase) includes `raw_launch` for generic local execution, while the run-phase `BackendKind` type uses `local_interactive` instead; `raw_launch` maps to `local_interactive` at runtime.
- **supported_versions**: PEP 440-style version specifier for tool version compatibility (e.g., `>=2.1.296`).
- **minimal_inputs**: Contract requirements — acceptable credential forms, whether user-prepared state is needed.
- **system_prompt**: Explicit provider-native prompt method, owned surface, precedence conflicts, required engine environment, and source evidence.
- **owned_paths**: Files and keys used for startup projection and reserved runtime state.
- **permission_defaults**: Native defaults for permission fields omitted by the author.
- **actions**: Ordered list of mutations to apply to the launch environment.

## Policy Resolution

Strategies are resolved from the versioned registry with this precedence:

| Priority | Source | Description |
|---|---|---|
| 1 | `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` | Environment variable. Must name a strategy_id that matches the requested mode and backend. |
| 2 | Registry documents | Tool-specific YAML files in `agents/launch_policy/registry/`. Filtered by mode, backend, and detected tool version. Must produce exactly one match. |

Unattended resolution matches the detected tool version against each strategy's `supported_versions` specifier. It fills gaps after resolving authored layers. The launch diagnostics record the effective permission values and their sources. When reusing a home, Houmao distinguishes its prior permission projections from the native baseline.

## Provider Hooks

Provider hooks are named actions within a strategy that perform provider-specific setup:

### Claude Hooks

| Hook | Description |
|---|---|
| `claude.apply_permission_mode` | Projects the resolved mode into private settings and startup arguments. Bypass mode seeds its startup warning preference. |
| `claude.ensure_api_key_approval` | Seeds API-key approval state in `.claude.json` without storing the full key. |
| `claude.ensure_project_trust` | Seeds workspace trust state for the resolved working directory. |

### Codex Hooks

| Hook | Description |
|---|---|
| `codex.canonicalize_unattended_launch_inputs` | Normalizes the remaining arguments after recognized permission aliases have been resolved. |
| `codex.validate_credential_readiness` | Ensures `auth.json` exists or a config-backed env-only provider is set up. |
| `codex.ensure_project_trust` | Seeds project trust level in `config.toml`. |
| `codex.ensure_model_migration_state` | Migrates known legacy Codex model pins without creating a model selection when none exists. |
| `codex.apply_runtime_permissions` | Writes the resolved policy to the private runtime home. |
| `codex.append_unattended_cli_overrides` | Appends the resolved approval and sandbox values as final non-secret config arguments so project-local preferences cannot replace them. |

### Codex Hook Observation Pre-Trust

The Codex strategy also declares the launch-owned surfaces for the opt-in hook observation channel. Enablement is per adapter: `HOUMAO_HOOK_OBSERVATION_CODEX=1` covers managed `local_interactive` launches only, and any value other than `1` leaves the session TUI-only.

| Owned path | Keys | Purpose |
|---|---|---|
| `hooks.json` | `hooks.<Event>[<group index>].hooks[<handler index>]` (observer document presence) | Observer document written into the runtime home, with one synchronous command handler per subscribed event |
| `config.toml` | `hooks.state."<absolute hooks.json path>:<snake_case event label>:<group index>:<handler index>".trusted_hash` | Pre-trust entry for every generated handler |

The launch writes the observer `hooks.json` into the runtime-owned `CODEX_HOME` and merges a marker-delimited, generation-scoped `[hooks.state]` block into the runtime-home `config.toml` that it already synthesizes for project trust and unattended posture. Each `trusted_hash` reproduces Codex's own handler fingerprint over the normalized event label, matcher, timeout, and command, so Codex installs the handlers without a trust-review prompt. The block is rewritten at each provider start and removed on cleanup, and every operator-authored `hooks.state` entry and other `config.toml` line is preserved. The managed path never adds `--dangerously-bypass-hook-trust`; that flag remains a manual-lane fallback for invocations outside the managed launch. If either runtime-home surface cannot be written safely, the channel reports `unavailable` and the session launches TUI-only.

The evidence for this surface is the 2026-10-20 debug campaign (`context/campaigns/debug/2026-10-20-codex-hook-observation/`, including the E1 trust decision and the pre-trusted-hash probes) plus the upstream hook discovery and hashing code under `extern/orphan/codex/codex-rs/hooks/`.

### Kimi Hooks

| Hook | Description |
|---|---|
| `kimi.canonicalize_unattended_launch_inputs` | Prepares native prompt startup after managed input validation. |
| `kimi.canonicalize_unattended_tui_launch_inputs` | Seeds the marker that skips legacy Kimi startup migration. |
| `kimi.project_tui_permission` | Applies the resolved mode in the private config and adds the matching native flag when available. |
| `kimi.project_service_permission` | Applies the resolved private config for the ACP or Web owner. |
| `kimi.validate_native_system_prompt_contract` | Requires the v2 engine and rejects launch or project agent selection that would outrank the managed native prompt. |

Hooks run within a provider state mutation lock for thread-safe file access.

### Kimi Hook Observation

The Kimi strategy also declares the launch-owned surface for the opt-in hook observation channel. Enablement is per adapter: `HOUMAO_HOOK_OBSERVATION_KIMI=1` covers managed `local_interactive` launches only, and any value other than `1` leaves the session TUI-only.

| Owned path | Keys | Purpose |
|---|---|---|
| `config.toml` | `hooks.[<entry index>].{event, matcher, command, timeout}` (observer block presence) | Marker-delimited, generation-scoped `[[hooks]]` observer block with one entry per subscribed event |

The launch merges the observer block into the launch-owned runtime-home `KIMI_CODE_HOME/config.toml` after launch-policy field synthesis, rewrites it at every provider start, and removes it on cleanup. Every byte outside the block, including operator-authored `[[hooks]]` entries, is preserved. The block subscribes all 20 Kimi events with one entry each, omits `matcher` (match all), uses a 5-second timeout, and invokes the packaged emitter through a shell-quoted absolute command. Kimi has no hook trust mechanism, so the managed path needs no pre-trust seed and no bypass flag; the provider loads its hook table once per process, which makes install-before-start ordering sufficient.

Kimi validates the hooks section against its own schema and drops the entire section when any entry carries an unknown key, an unknown event, or a bad timeout; the TUI shows no warning, and only print-mode stderr carries the diagnostic. The installer therefore validates the merged file by strict `tomllib` read-back: every key must be in `{event, matcher, command, timeout}`, every event must be in the pinned 20-name enum, and every timeout must be an integer in `1..600`. Any violation restores the pre-install text and degrades the channel to `unavailable`; the session launches TUI-only instead of carrying a silently dead channel.

Kimi emits `PermissionRequest` and `PermissionResult` only under an ask permission policy. The managed unattended strategy runs the TUI with native `--auto`, so permission events are normally absent; that absence is expected and is not channel degradation.

The supported floor is Kimi Code 2.1.1, the same floor as TUI tracking. The full enriched hook payload contract has existed since upstream 0.32.0 (2026-08-04), below the registry floor, so every supported version can carry the channel. The evidence for this surface is the 2026-10-20 debug campaign (`context/campaigns/debug/2026-10-20-kimi-hook-observation/`, including the S2 malformed-section control and the S7 load-once probe) plus the upstream hook schema under `extern/orphan/kimi-code/packages/agent-core-v2/src/features/externalHooks/`.

## Kimi Unattended Posture

Kimi headless and TUI startup require Kimi Code 2.1.1 or later with no upper version limit. Houmao rejects versions below the floor.

- Native `-p` selects `auto`. Houmao rejects incompatible permissions such as `manual` or `yolo` before starting a managed headless agent. The final command uses the managed prompt and continuity arguments, with no `--auto`, `--yolo`, or `--plan` flag.
- Kimi TUI startup uses the resolved mode. For `auto` or `yolo`, Houmao supplies the corresponding native flag on fresh or resumed startup with `--continue` or `--session <session_id>`. A fresh TUI supports `manual` through the native config. The resumed TUI restores session permissions and lacks a native manual override flag, so Houmao rejects an explicit `manual` on native continuation.
- Kimi ACP and Web use their native session APIs on the supported 2.6.0 build to apply the resolved setting at launch or exact continuation. Later observation or gateway reattachment preserves native changes made during the session.

Policy and role setup happen outside the conversation. Kimi `as_is` uses native behavior for an omitted mode.

Kimi auto permission mode is the provider-native no-question posture: normal tool approvals are automatic and `AskUserQuestion` requests are denied so the agent must decide and continue. It does not bypass explicit Kimi hard-deny policies or user-configured deny rules.

Unattended Kimi launches also pre-seed the provider workspace-trust record before provider start. Kimi Code 2.1.1 or later gates project-level MCP config behind per-workspace trust and otherwise opens a blocking "Trust this folder?" modal at TUI startup, which unattended mode cannot answer. The trust check is presence-only state in the provider home, so provider-start planning writes `$KIMI_CODE_HOME/workspace-trust/<workdir-key>` for the actual launch working directory on fresh headless starts, fresh TUI starts, and relaunches, repairs a missing or drifted record, and records the workspace key in launch provenance. `as_is` launches receive no pre-seed and keep Kimi's native trust interaction.

Kimi managed role delivery uses the `native_home_system_prompt` contract. Brain construction writes the complete composed prompt to `$KIMI_CODE_HOME/SYSTEM.md` as `${base_prompt}`, a blank line, and the effective Houmao prompt. Provider-start planning locks the home, checks and repairs those canonical bytes, records effective and rendered SHA-256 digests, and forces `KIMI_CODE_LEGACY_FLAG=0` after other environment layers.

Kimi expands `${identifier}` tokens in the system template. Houmao therefore rejects every such token in role-authored effective prompt text; a literal dollar sign without that shape remains valid. Managed launch also rejects `--agent`, `--agent-file`, a project default `agent` profile with `override: true`, and the equivalent profile in configured `extra_agent_dirs`, because those surfaces outrank the managed home prompt. Houmao reports project-owned conflicts without editing them.

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
