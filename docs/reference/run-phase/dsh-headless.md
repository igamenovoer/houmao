# DSH Headless

Use `houmao-mgr project agents launch --mode headless` or select `headless` in a DSH project profile to start a managed `dsh_headless` agent. The agent retains its Houmao identity between turns. Each prompt starts one native DeepSeek Harness CLI worker. [Gateway and passive control](dsh-headless-integrations.md), [DSH Web](dsh-web.md).

## Select a DSH Executable

Use the [development preparation helper](../../../tools/dsh/README.md) to identify and inspect the explicitly selected DSH executable. The native CLI reference is DSH `0.2.2-rc.3`, with the reference source at `39163dd30f703a79079e2d2446545cff3c453738`. The npm version and source revision are separate evidence. Houmao uses the installed executable and the bundled companion during a managed launch.

## Run and Continue a Conversation

The worker runs `dsh --profile headless` with the materialized home patch and a private attempt patch, then the profile's `--json` flag. Houmao supplies the task through stdin. Continuation adds `--session-id <saved-id>` and uses the original workspace. An explicit new conversation omits `--session-id`. An unavailable, incompatible, occupied, or wrong-workspace saved identity fails before new input.

For a managed request, the companion checks the current owner generation and revocable permission immediately before native input. It records handoff separately. A `session` stdout event establishes native identity for the attempt. A correlated native `final` event, persistence evidence, and worker exit establish terminal outcome. A partial stream or timeout preserves the evidence already collected and can leave the outcome uncertain. Inspection and recovery never resend input.

Interrupt targets the captured worker and checks process identity before signaling. Houmao bounds cleanup of the owned processes. A signal establishes an owner action, while native evidence establishes the provider's outcome. Keep the managed identity when detaching or reattaching a gateway. Earlier usage remains bound to its original conversation when you explicitly start a new one.

The managed turn artifacts keep the native JSON stream in `stdout.jsonl` and native diagnostics separately in `stderr.log`. The events route exposes normalized progress and outcomes. Prompt text, role text, and credential values remain private to the attempt and its native home. Public errors carry bounded, redacted diagnostics.

## Native Home and Defaults

Launch materializes `houmao-tool-params.yaml`, `houmao-profile.patch.json`, `houmao-role.txt`, a private native credentials stub, and separate persistence and skill roots. Each ordinary invocation reads the selected home and registers the current role as a literal, additive native system prompt section. Managed recovery reads artifacts without rewriting the home.

The native patch supplies the effective provider and model settings. An invocation can add a request-scoped model or reasoning override without changing the home. An overlay may mask an edit to a lower-priority setting. Skill discovery occurs at the next invocation. Home refresh can inspect that future boundary when the agent is between workers. Use native CLI-compatible configuration for this mode. Houmao rejects ACP `mcp_servers` declarations before invocation.

### Setup Fields

The selected tool setup supplies a `tool-params.yaml` layer. Houmao merges it with recipe or specialist overrides, launch-profile overrides, and direct overrides in that order. The starter has an empty model catalog, so supply exact model metadata in one of these layers before building an agent. Use the common `model.name` setting to select a model whenever the effective catalog contains several entries.

| Field | Required Meaning |
| --- | --- |
| `provider.adapter` / `provider.protocol` | `deepseek` uses `messages`. `pi-ai` supports `openai-completions`, `openai-responses`, `anthropic-messages`, and `google-generative-ai`. |
| `provider.route` | `deepseek-official` for DeepSeek. Supply a separate lowercase route identifier for pi-ai. |
| `provider.base_url_env` / `provider.api_key_env` | Names must match the stored roles in the selected credential bundle. Explicit `api_key_env: null` selects endpoint-only pi-ai Chat Completions. When omitted on pi-ai, the API-key reference defaults to `OPENAI_API_KEY`. |
| `provider.compat` / `models[].compat` | Optional pi-ai compatibility options, subject to the protocol's supported fields. Model options override route defaults. |
| `provider.retry_policy` | Optional native request retry settings. Set `mode` to `normal` or `always`. Normal mode supports `max_retries` and `retryable_codes`. Both modes accept `backoff` with `initial_delay_ms`, `max_delay_ms`, and `jitter_ratio`. |
| `models` | Each entry requires `id`, positive `context_window`, positive `max_output_tokens`, and explicit `reasoning_efforts`. Output capacity must fit the context window. Optional `name` labels the native selector, and `input_modalities` accepts `text` and `image` with a default of `[text]`. |
| `models[].reasoning_efforts` | `false` for a model without reasoning, or a map from DSH thinking slots to provider wire values. A reasoning-capable model requires at least one positive slot. |
| `skill_roots` | Optional absolute directories added during launch materialization. The native skill-provider configuration disables user-global discovery and watching. Later invocations consume the current native configuration. |
| `mcp_servers` | Leave this empty for headless mode. These declarations require an ACP session binding. |
| `permissions.sandbox` | Optional native file policy. Use `read-only`, `workspace-write`, or `danger-full-access`. |
| `permissions.approval` | Optional native approval policy. Use `ask` or `never`. |

Use a provider endpoint that implements the selected protocol, including the base path required by the deployment. The URL must omit user information, query parameters, and fragments.

Houmao maps positive integer reasoning levels to declared slots in DSH's canonical order of `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. Requests above the declared range use the highest configured slot. Level `0` selects `'off'` when declared, and models with `reasoning_efforts: false` also accept level `0`. Quote `'off'` as a YAML key or string value. On pi-ai, `'off': null` omits the upstream effort field and `'off': none` sends the string `none`. DeepSeek accepts `'off'`, `low`, `high`, and `max`, with matching wire names and an optional null value for `'off'`.


The following example uses synthetic model metadata. For a live account, supply the values qualified for the actual model.

```yaml
provider:
  adapter: deepseek
  protocol: messages
  route: deepseek-official
  base_url_env: DEEPSEEK_BASE_URL_ANTHROPIC
  api_key_env: DEEPSEEK_API_KEY
models:
  - id: controlled
    context_window: 8192
    max_output_tokens: 128
    reasoning_efforts: false
skill_roots: []
mcp_servers: []
```

The packaged `openai-compatible` setup selects endpoint-only Chat Completions. Supply an exact model catalog. The following example shows a local route and a model-specific compatibility setting.

```yaml
provider:
  adapter: pi-ai
  protocol: openai-completions
  route: controlled-generic
  base_url_env: OPENAI_BASE_URL
  api_key_env: null
models:
  - id: controlled
    context_window: 8192
    max_output_tokens: 128
    compat:
      supports_developer_role: false
    reasoning_efforts:
      'off': none
      low: low
      high: high
```

DSH's transport sends the fixed public header `Authorization: Bearer houmao-local-no-auth` on endpoint-only routes. Select a self-hosted endpoint that accepts this header. Houmao generates the header value at launch and leaves the credential bundle, authored settings, and launch metadata free of the placeholder value.

### Project and Profile Preparation

The commands below use a disposable project outside the Houmao checkout and a synthetic native-route credential.

```bash
houmao_checkout=/absolute/path/to/houmao
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project init
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project credentials dsh add \
  --name controlled --adapter deepseek \
  --api-key synthetic-local-only --base-url http://127.0.0.1:9000/v1
```

Write the controlled setup above into `.houmao/agents/tools/dsh/setups/default/tool-params.yaml`, then create the specialist and headless profile:

```bash
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project specialist create \
  --name controlled --tool dsh --credential controlled \
  --model controlled --system-prompt 'Preserve {{literal}} instructions.' --no-system-skills
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project profile create \
  --name controlled --specialist controlled --agent-name controlled --mode headless
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project agents launch \
  --profile controlled --no-gateway
```

The launch command requires a qualified DSH executable and a model server at the selected endpoint. The manager reports `mode=headless` and `backend=dsh_headless`. For an endpoint-only route, create the credential with `--adapter pi-ai --base-url <endpoint>` and select the `openai-compatible` setup. For an authenticated compatible route, add `--api-key` and set `provider.api_key_env` to the key role. The credential command accepts custom role names via `--base-url-env` and `--api-key-env`.

### Startup Permissions and Prompt Provenance

The `unattended` posture fills omitted fields with sandbox mode `danger-full-access` and approval policy `never`. An explicit value takes precedence for its field. Native hard denies and the selected execution user's operating-system permissions still apply. The specialist's `--no-unattended` option selects `as_is`, which uses the native baseline for omitted fields. Later workers read the materialized native permissions.

To keep the previous workspace boundary, add this to the selected setup's `tool-params.yaml`. In a specialist or launch profile, place the same mapping under `tool_params`.

```yaml
permissions:
  sandbox: workspace-write
  approval: never
```

In an unattended launch, omitting `approval` also selects `never`. Use an explicit `ask` to request the native approval behavior. The headless profile has no interactive answerer and fails closed when a native request needs one. [DSH Web](dsh-web.md) can present approval requests in the browser.

Remove any authored `hmr` entry, including `hmr: false`. Houmao reserves HMR to control when native settings take effect. Run a supported home refresh or relaunch to activate changes.

Prompt provenance records the SHA-256 digest of the complete effective launch prompt. The private role file retains the literal bytes, while public metadata contains no prompt or key values. Rebuilding with an empty prompt replaces the old managed role file, and the companion registers no stale section. The companion and starter setup ship as package resources; provider launch requires no JavaScript build or package installation. DSH's built-in system sections, working-directory project instructions, and tool schemas remain native inputs alongside the additive Houmao section.

## Accounting Contract

The pinned runtime writes physical journal version 4 to `session.v4.jsonl` when managed persistence selects `compression: none`. The collector verifies the native session header and continuity before interpreting events. Documentation examples naming v3 are not evidence for the current schema.

Consumed tokens come from settled provider attempts in the exact native journal. Missing buckets remain unknown. Retries that produced independently measured requests remain distinct, and the collector excludes inherited or pre-attachment history. [Usage record contract](usage-records.md).

## Qualification

Use the [DSH runner](../../../scripts/qualification/dsh/README.md) to exercise native one-shot execution with an explicit model, endpoint, and selected executable. Run the controlled native fixture suite without provider credentials:

```bash
env -u TMUX -u TMUX_PANE \
  HOUMAO_DSH_EXECUTABLE=/selected/qualified-runtime/node_modules/.bin/dsh \
  pixi run pytest -q tests/integration/agents/dsh/test_fixture_headless.py
```

The [RC2 acceptance map](dsh-headless-acceptance.md) records independent evidence for the earlier per-turn ACP implementation. Its results apply to that transport and release.
