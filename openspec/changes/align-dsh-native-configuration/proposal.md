# Proposal

## Why

Live qualification of Houmao 3.0.0rc1 with DeepSeek Harness and self-hosted SGLang `Qwen/Qwen3.8-27B-FP8` exposed gaps in native model configuration, reasoning dispatch, unattended permission presets, and error diagnostics. The installed OpenAI-compatible transport also requires a credential value or authorization header even for a self-hosted endpoint that expects no operator-supplied key. [Issue #85](https://github.com/igamenovoer/houmao/issues/85) · [DSH integration issue #74](https://github.com/igamenovoer/houmao/issues/74)

This change builds on the five-layer `tool_params` pipeline from `refactor-per-tool-params-pipeline`. It aligns the DSH schema and runtime projection with the native adapter while preserving isolated homes, literal role projection, and unattended sandbox policy.

## What Changes

- **BREAKING**: Upgrade `DshToolParams` (`src/houmao/agents/tool_params/dsh.py` and `src/houmao/agents/dsh_configuration.py`, introduced in `refactor-per-tool-params-pipeline`) to replace legacy per-index `models[].reasoning` with native-aligned `models[].reasoning_efforts` and full `@deepseek-ai/dsh-llm-pi-ai` / `@deepseek-ai/dsh-llm-deepseek` capabilities.
- Support the four configurable `pi-ai` wire protocols (`openai-completions`, `openai-responses`, `anthropic-messages`, `google-generative-ai`) alongside `deepseek/messages`, with protocol-gated route and model `compat`, `input_modalities`, and `retry_policy`. Retain keyed layer merging across setups, specialists, profiles, and direct overrides.
- For explicitly selected self-hosted `pi-ai/openai-completions` routes, `api_key_env: null` selects endpoint-only configuration. Houmao supplies a fixed public placeholder through a reserved variable in the native process environment. The endpoint must accept the resulting `Authorization` header. Qualify this path with a completed SGLang prompt.
- Preserve the distinction between a non-reasoning model (`reasoning_efforts: false`) and a reasoning-capable model set to `off`. A reasoning map requires at least one positive slot. Level `0` selects a declared `off` slot, and positive levels follow the canonical order with saturation. Preserve supported wire values, including `null` for `off` omission on `pi-ai` and custom strings. On DeepSeek Messages, keep positive per-turn choices available when the launch default is `off`.
- Compose unattended DSH startup permissions coherently across `permission` (`@deepseek-ai/dsh-permission-presets`), `approval`, and `sandbox-policy` directly in `houmao-profile.patch.json` by registering `houmao-unattended` alongside `read-only`, `workspace-write`, and `danger-full-access` with `defaultPreset: "houmao-unattended"`, removing the duplicate Web-only `permission` patch block in `dsh_web.py`.
- Propagate secret-redacted provider, JSON-RPC, Web API, and startup failure details through `DshAcpRequestError`, `DshAcpProtocolError`, `dsh_acp_driver`, and `dsh_web` so CLI stderr, gateway turn status, and managed console logs surface actionable failure reasons without leaking resolved secret environment values, cookies, or authentication tokens.
- Store DSH API-key and endpoint roles alongside the credential bundle's `vars.env`. Use the stored roles for inspection, updates, clearing, and launch projection, including custom environment names. Reject persistent and one-shot launch environment overrides that collide with those names.
- Update `scripts/agents/test-fixtures/` (`fixturelib`), campaign helper `scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py`, and DSH reference documentation to author `DshToolParams` with `reasoning_efforts`, `compat`, protocol selection, and endpoint-only self-hosted OpenAI-compatible routes. Non-DSH `houmao-mgr project` authoring checks remain out of scope.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Extend `DSH Runtime Configuration Is Explicit and Isolated` with native protocol settings, endpoint-only OpenAI-compatible launch, role-bound environment projection, and coherent unattended permission presets.
- `agent-model-selection`: Derive the DSH reasoning ladder from `tool_params.models[].reasoning_efforts`, preserve wire values, and project non-reasoning models and the `off` slot according to the native adapter.
- `dsh-headless-control`: Require secret-redacted JSON-RPC and worker-startup error details on failed ACP requests and turn outcomes instead of bare numeric JSON-RPC codes.
- `dsh-web-control`: Require secret-redacted startup and Web control error details on failed supervisor startup and turn operations instead of bare error codes or generic static messages.
- `houmao-mgr-credentials-cli`: Add `dsh` to maintained credential lanes with persisted API-key and endpoint roles, role-based redaction and clearing, and endpoint-only bundles for the supported OpenAI-compatible route.
- `test-agent-launch-fixtures`: Update DSH headless and Web fixture preparation with native reasoning, compatibility metadata, protocol selection, and endpoint-only self-hosted OpenAI-compatible prompts.

## Impact

- Prerequisite change: Requires `refactor-per-tool-params-pipeline` (`src/houmao/agents/tool_params/` and five-layer `tool_params` support across setups, specialists, presets, profiles, and launches).
- DSH tool-params schema, materialization, and reasoning policy: `src/houmao/agents/tool_params/dsh.py`, `src/houmao/agents/dsh_configuration.py`, `src/houmao/agents/model_mapping_policy.py`, and `src/houmao/agents/launch_policy/registry/dsh.yaml`.
- DSH control backends and diagnostics: `src/houmao/agents/realm_controller/backends/{dsh_acp_connection.py,dsh_acp_driver.py,dsh_acp.py,dsh_web.py}`.
- Starter setups, CLI credentials, fixtures, and docs: `src/houmao/project/assets/starter_agents/tools/dsh/`, `src/houmao/srv_ctrl/commands/credentials.py`, `tests/fixtures/plain-agent-def/tools/dsh/`, `tests/fixtures/agent-launch/`, `scripts/agents/test-fixtures/`, `scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py`, `docs/reference/run-phase/{dsh-headless.md,dsh-web.md}`, `tests/unit/agents/`, and `tests/integration/agents/dsh/`.
