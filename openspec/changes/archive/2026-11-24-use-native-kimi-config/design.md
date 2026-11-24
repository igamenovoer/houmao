# Design

## Context

See [the proposal](proposal.md) for the motivating failure. `validate_brain_inputs()` reads `setup_dir` as the Kimi home. `build_brain_home()` later copies the credential bundle's config over the setup config and repeats the effort lookup in the constructed home. `LaunchPlan` and the tmux publisher already distinguish provider-private values from values available to panes. [Brain construction](../../../src/houmao/agents/brain_builder.py) · [Launch environment](../../../src/houmao/agents/realm_controller/launch_plan.py) · [Tmux publisher](../../../src/houmao/agents/realm_controller/backends/tmux_runtime.py)

## Goals / Non-Goals

**Goals**

- Make the same native config drive preflight and Kimi startup across managed run modes.
- Keep model effort names in Kimi's native catalog and numeric selection in Houmao's launch profile.
- Reuse the private credential and session environment boundaries for the inputs that still need environment variables.

**Non-Goals**

- Changes to other providers' config or numeric reasoning rules.
- New OAuth login flows, cross-version guarantees for undocumented Kimi keys, or automatic conversion of old credential bundles.

## Decisions

### Resolve One Native Config Before Startup

Read the setup `config.toml` and any auth file mapped to the runtime `config.toml` before mutating the home. Follow the adapter's declared paths. Recursively overlay credential tables on the setup baseline, with credential scalars and arrays replacing matching setup values. A credential entry under `providers`, `models`, or `services` replaces the complete same-named entry. For example, a credential provider with a different endpoint receives only that entry's credentials and headers. Entries with distinct names and setup-only preferences survive. Arrays such as `hooks` replace as a unit. Houmao adds its runtime-owned hooks and skill paths in the existing projection steps.

Carry the resolved config with validated build inputs. Read the native `default_model`, selected alias, and effort catalog from this snapshot. Materialize it once as owner-private `$KIMI_CODE_HOME/config.toml`, then apply launch-owned model, reasoning, and existing launch policy writes in the runtime home. If parsing, alias resolution, or numeric mapping fails, report the input and alias before creating the home or replacing an existing agent. Diagnostics can name files, keys, and effort labels. Config contents that carry secrets belong in private files.

Two possible sources were the current whole-file overwrite and the effective config after home creation. Whole-file precedence drops unrelated setup preferences. Post-build validation can discover an invalid catalog after a force launch has already stopped the old agent. The preflight snapshot handles both cases and keeps launch-time and per-turn reads tied to their respective runtime generation.

### Keep Each Model's Native Effort Names

Use the selected alias's `[models.<alias>].support_efforts`, with a list in `[models.<alias>.overrides]` taking precedence. This ordered list declares the positive levels for models with multiple native settings. Houmao resolves `--reasoning-level N` against the resulting list and passes the exact string to `[thinking].effort`. For example, level `2` from `['brief', 'deliberate']` maps to `deliberate`, while level `2` from `['quick', 'extended', 'maximum']` maps to `extended`. The catalog order drives both examples. A request above the catalog length saturates at the last entry and records that outcome. Level `0` uses Kimi's native off posture when supported, including any native model metadata governing that posture. An omitted numeric override preserves the native default.

Require a usable ordered catalog for positive overrides, with a diagnostic naming the selected alias and its config field when the catalog is missing or malformed. Use Kimi's native support metadata for the off check. Managed headless request overrides read the committed runtime config for their selected model and restore the prior thinking settings when the turn ends. TUI and headless startup can keep the native `--model` selection for an explicit profile or one-shot override. ACP and Web set the resolved alias in private runtime TOML through the existing service setup.

A fixed common list would assign meanings Kimi leaves to each provider. The native list already carries both the names and their ordering. A catalog is required when a maintained config advertises multiple selectable efforts or an operator requests a positive Houmao level. Models that use a native default can launch with the numeric field omitted.

### Reserve Config-Owned Environment Names at Launch

Use one Kimi policy for the environment inputs with supported, persistent TOML equivalents. Apply it to credential and raw build inputs, durable profile or specialist records, a launch's `--env-set`, and restored launch inputs before provider start. Reject authored config-owned bindings with the TOML destination in the error. Ignore ambient bindings and mask their names in the owned tmux session so an existing server's global values cannot reach a new pane. Reconcile the same names on relaunch. Reuse the publisher's session-local masking rather than editing the server's global environment.

| Environment input | Native setting |
| --- | --- |
| `KIMI_MODEL_NAME`, `KIMI_MODEL_PROVIDER_TYPE`, `KIMI_MODEL_BASE_URL` | `default_model`, the model alias, and its `[providers.<provider>]` entry |
| `KIMI_MODEL_MAX_CONTEXT_SIZE`, `KIMI_MODEL_MAX_OUTPUT_SIZE`, `KIMI_MODEL_CAPABILITIES`, `KIMI_MODEL_DISPLAY_NAME`, `KIMI_MODEL_REASONING_KEY`, `KIMI_MODEL_ADAPTIVE_THINKING` | The selected `[models.<alias>]` fields |
| `KIMI_MODEL_THINKING_EFFORT`, `KIMI_MODEL_THINKING_KEEP`, obsolete thinking-mode variables | Native `[thinking]` defaults and per-model effort metadata |
| `KIMI_DISABLE_TELEMETRY` | Top-level `telemetry` |
| Kimi managed provider routing (`KIMI_CODE_BASE_URL`, `KIMI_CODE_OAUTH_HOST`, `KIMI_OAUTH_HOST`) | Managed provider `base_url` and `oauth.oauth_host` with the matching stored credential |
| Kimi loop, task, MCP, identity, image, watch, database, and WebSearch or FetchURL overrides with documented persistent equivalents | Native `[loop_control]`, `[task]` or `[background]`, `[mcp]`, `[identity]`, `[image]`, `[watch]`, `[database]`, and `[services]` fields |

Tie the last row to a concrete mapping of variable names to supported fields. Kimi releases can add settings, and some settings use older native TOML section names on older supported builds. Document the applicable TOML field for the selected version. A process-wide variable whose behavior has no persistent equivalent stays outside this mapping.

The existing `--api-key` input can store `KIMI_MODEL_API_KEY` as a private secret referenced by `[providers.<provider>].api_key_env`. Native provider TOML can also carry an inline API key in the private credential bundle or an OAuth reference with its imported token store. A referenced key must come from the selected, explicitly allowed credential input. Houmao delivers it only to the provider. Home selection, engine selection, and update handling keep their existing process inputs. The documented sampling and global completion-cap variables remain explicit private inputs because the corresponding internal `[model_overrides]` keys can be stripped by native TOML writes. OAuth login bootstrap takes place before managed launch and can still use its native environment inputs. [Kimi 2.7.2 environment reference](https://github.com/MoonshotAI/kimi-code/blob/56145f849caa305d42acd09b67fb65d11146f887/docs/en/configuration/env-vars.md) · [Kimi 2.7.2 TOML reference](https://github.com/MoonshotAI/kimi-code/blob/56145f849caa305d42acd09b67fb65d11146f887/docs/en/configuration/config-files.md)

Dropping names only from the starter adapter would leave older project adapters, explicit launch records, and inherited tmux values effective. The policy enforces the ownership at the shared runtime boundary and gives authoring commands the same names for validation and guidance.

### Use Native Config in Maintained Authoring and Fixtures

Keep `--config-toml`, `--code-home`, `--credential-json`, and credential-only `--api-key`. Remove the Kimi flags and clear options that write retired settings to `vars.env`. Update specialist and demo input handling to pass TOML and use the generic API-key flag only for a matching `api_key_env` reference. Project callers still choose a model alias and numeric level through their launch profiles.

Render fixture API case provider and model data in a private config from the existing selected endpoint, protocol, model, and model metadata. Let fixtures declare ordered effort names when an endpoint or model supports multiple efforts. Use the same config inputs for native and managed fixtures. Native-login fixtures import explicitly selected state through the maintained workflow.

## Risks / Trade-offs

- A credential overlay replaces a matching provider, model, or service entry as a unit. Document complete entry replacement and exercise distinct aliases, setup-only settings, and endpoint changes with synthetic credentials.
- A stale environment value can bypass native effort selection. Exercise provider startup and actual tmux panes with both an ambient binding and a stale server-global binding. Use an isolated tmux server and the current session-local removal behavior.
- Kimi config can carry credentials and headers. Use owner-private runtime writes and report projection evidence through paths, alias names, and approved metadata. Exercise redaction with synthetic secrets.
- A model refresh can change its native catalog order. Apply Kimi's native `overrides` before selection and record the selected label and index for the launch or turn.

## Migration Plan

Ship the runtime policy, starter data, fixture materialization, and operator guidance together. Replace env-only Kimi bundles with a native provider and model entry before the next managed provider start. Import that config into the selected credential bundle, or use a secret-free setup config with a private key reference. Clear retired authored env values in the credential or launch record. A rollback uses the prior release and its saved credential definitions. Current-generation inspection continues to read recorded runtime artifacts.
