# DSH Headless Compatibility

This reference is for contributors implementing and qualifying DeepSeek Harness (DSH) support. The ACP backend is under implementation in change `dsh-01-add-acp-headless-backend`; this document does not claim that all managed launch paths are accepted. The [scenario map](dsh-headless-acceptance.md) records the remaining gates.

## Qualified Reference and Executable

The source reference is `39163dd30f703a79079e2d2446545cff3c453738`, whose CLI package declares `0.2.2-rc.3`. Use the [development preparation helper](../../../tools/dsh/README.md) to verify the ignored reference and identify an explicitly selected executable. Product launch must never clone sources or install npm dependencies.

The development host's Bun-global DSH is `0.2.2-rc.1`, which differs from this reference. Qualification uses an isolated `0.2.2-rc.3` installation instead. Its executable SHA-256 is `36f86742e0c3cc1c3b2dbaa6582ee00b0c37bc4f5a190f7531b5303bf3efb6d9`; the DeepSeek package-code digest is `ac0a9f14c56acd12081b12702887fccc5948a07e0a9c9f27128e0d5eff6a088c`. The generated build receipt records the complete package inventory and lockfile digest. Published npm metadata does not attest to a source commit; matching versions are qualified through native conformance tests rather than treated as source attestation. ACP's `agentInfo.version: 0.0.1` identifies neither the installed release nor its source revision.

## Control Contract

Headless selection uses ACP stdio through the managed headless envelope. One explicit turn owns one driver, native process, and exclusive runtime-session lock. The driver creates a session only for a new conversation. Continuation resumes the saved exact identity in its recorded workspace, with no latest-session or new-conversation fallback.

Native input admission, prompt settlement, persistence flush, and process cleanup are separate facts. Sending an ACP request does not prove admission. The packaged companion records input insertion, claim, and root-turn identities in a private metadata journal. A correlated successful prompt settlement also establishes handoff. Ordinary delivery fails immediately when unavailable or busy, and a failed or uncertain attempt is never automatically resubmitted.

Native cancellation precedes bounded forced cleanup. A controller timeout with a live worker leaves the attempt pending. Explicit resume must reconcile identified abandoned pending input through the native inbox before activation; unknown pending input blocks continuation. Conversation history remains history.

### Turn Outcomes and Recovery

The [integration reference](dsh-headless-integrations.md) describes maintained gateway, passive-server, mailbox, and plugin routes. Their acknowledgements describe distinct boundaries:

| Boundary | Evidence and Meaning |
| --- | --- |
| Houmao acceptance | A managed attempt and its accounting start exist. This does not establish native input admission. |
| Native handoff | The companion proves input insertion/claim for the captured attempt, or the correlated ACP prompt settles. Helper startup and a written request are insufficient. |
| Native outcome | `end_turn` means completed; `cancelled` means interrupted. Limit/refusal outcomes retain their native stop reason and incomplete/failed meaning. |
| Managed cleanup | Native closure flushes persistence and owned processes are reaped. Failure here remains separate from an already observed native result. |

A controller wait timeout preserves pending accounting until durable terminal evidence arrives. This includes startup whose process identity is still unknown. If the actual success marker appears concurrently with timeout, recovery uses that marker rather than fabricating a failed result. Reading status or restarting a recorder never recreates the driver or resubmits the prompt.

Each invocation holds the runtime-session lock through native closure and cleanup. Another controller refuses overlapping work. Explicit interruption first requests ACP cancellation and continues consuming updates. Hung cancellation triggers bounded cleanup of the captured native process group and verified descendants. Process-birth checks prevent stale metadata from signalling a replacement. Missing process identity returns uncertainty without terminal-key fallback.

Continuation uses the exact recorded native session and workspace. Missing, occupied, incompatible, or wrong-workspace selection fails before new input; there is no latest-session fallback. An explicit new-conversation selection creates a fresh native identity and accounting binding while preserving earlier runtime-session records. Model/reasoning overrides select advertised native ACP options before the resumed prompt, so a previous persisted model cannot silently override the explicit selection.

After abrupt death, explicit continuation removes only proven abandoned, unclaimed Houmao input through the native inbox before activation. Claimed input remains historical evidence. Unknown pending input blocks continuation. Recovery never edits journal files or automatically replays earlier input.

### Execution Artifacts

`provider-stdout.jsonl` preserves raw ACP frames. `stdout.jsonl` contains driver events, `canonical-events.jsonl` contains their semantic projection, and the tmux console renders that projection. Bounded native stderr is saved separately in owner-only `provider-stderr.log`. Cleanup errors include their stage (`native_close`, `process_cleanup`, or diagnostic persistence) while preserving the original protocol/cancellation error. Accounting reads the native journal independently of these rendered/debug artifacts.

## Native Prompt and Configuration

The companion registers the full effective Houmao prompt as an additive native section with `interpolate: false`. Literal braces, dollar expressions, quotes, and multiline content survive unchanged. DSH's built-in instructions and tool schemas remain present. An empty effective prompt registers no managed section. There is no chat-bootstrap fallback.

Managed configuration isolates the DSH home, shared-agent root, persistence root, selected skills, and credentials. The native DeepSeek adapter uses Messages and the explicit `DEEPSEEK_BASE_URL_ANTHROPIC` reference. Each pi-ai route declares its protocol, endpoint, model capacities, and reasoning metadata. Private credential bundles hold key values. Public provenance records the environment references.

### Materialization and Current-Home Loading

Launch and explicit relaunch materialize `houmao-tool-params.yaml`, `houmao-profile.patch.json`, `houmao-role.txt`, the private native credentials stub, skill roots, and persistence directories. An ordinary ACP invocation reads those existing files. Removing required native inputs causes an explicit failure before prompt submission.

Each ordinary invocation rereads the selected home `houmao-tool-params.yaml` for current ACP MCP declarations and credential references. Houmao resolves MCP values from the selected private credential bundle at worker startup. The existing native patch supplies the current profile, provider configuration, model defaults, and skill-provider configuration. A lower-priority home setting can remain masked by the materialized launch overlay.

Request-scoped model/reasoning controls use a private per-attempt overlay and advertised ACP selectors. The next prompt selects the current materialized native default, so a previous request override does not become the next default. The companion/control patch, evidence files, dispatch guard, and selected credential environment remain private per-attempt inputs. These operations do not rewrite persistent home material.

For the qualified rc.3 ACP profile, a later ordinary invocation discovers skill additions, metadata edits, removals, and current MCP add/update/remove declarations while resuming the exact native conversation. Existing conversation history remains present, including older skill catalogs. The latest catalog and current tool schemas describe the next prompt's resources; old catalogs in history do not establish current discovery. Skill bodies remain native on-demand loads; editing a body does not replace material already recorded in conversation history.

The generic Houmao refresh contract uses this qualified next-invocation boundary without starting a worker, creating a conversation, or making a model request. Between prompts, there is no live native ACP worker whose resources Houmao can report as currently loaded. Passive inspection preserves that distinction. Refresh never restarts a worker or materializes edited Houmao profiles; explicit relaunch performs manifest-backed generation under its separate conversation policy.

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
| `mcp_servers` | Optional ACP stdio or Streamable HTTP declarations. Stdio requires an absolute `command` and accepts string `args` and `env` entries. HTTP uses `type: http`, an absolute HTTP(S) `url`, and `headers` entries. Each environment or header entry uses `name` for the native key and `env_ref` for its value in the private credential bundle. |
| `hmr` | `false` for this setup format. Native ACP inputs activate at each ordinary worker startup. |

Use a provider endpoint that implements the selected protocol, including the base path required by the deployment. The URL must omit user information, query parameters, and fragments.

Houmao maps positive integer reasoning levels to declared slots in DSH's canonical order of `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. Requests above the declared range use the highest configured slot. Level `0` selects `'off'` when declared, and models with `reasoning_efforts: false` also accept level `0`. Quote `'off'` as a YAML key or string value. On pi-ai, `'off': null` omits the upstream effort field and `'off': none` sends the string `none`. DeepSeek accepts `'off'`, `low`, `high`, and `max`, with matching wire names and an optional null value for `'off'`.

For a project credential, store MCP environment entries in the owner-private `.houmao/content/auth/dsh/<bundle-ref>/env/vars.env`. The `project credentials dsh get --name <name>` command reports `bundle_ref` and omits extra MCP values. Use an `env_ref` in `tool_params` to bind each value to its declared header or stdio environment variable.

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
hmr: false
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

In a disposable project outside the Houmao checkout, prepare a synthetic native-route credential through the maintained CLI:

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
  --name controlled --specialist controlled --agent-name controlled --headless
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project agents launch \
  --profile controlled --no-gateway
```

The launch command requires a qualified DSH executable and a model server at the selected endpoint. Managed headless launches use the `dsh_acp` backend. For an endpoint-only route, create the credential with `--adapter pi-ai --base-url <endpoint>` and select the `openai-compatible` setup. For an authenticated compatible route, add `--api-key` and set `provider.api_key_env` to the key role. The credential command accepts custom role names via `--base-url-env` and `--api-key-env`.

### Startup Permissions and Prompt Provenance

The default `unattended` posture selects the `houmao-unattended` native permission preset with approval policy `never` and sandbox mode `workspace-write`. Native hard denies remain enforceable. Selecting `as_is` through the specialist's `--no-unattended` option preserves the native permission defaults. ACP rejects permission requests without a supported responder. Later ordinary invocations use the materialized native permissions.

Prompt provenance records the SHA-256 digest of the complete effective launch prompt. The private role file retains the literal bytes, while public metadata contains no prompt or key values. Rebuilding with an empty prompt replaces the old managed role file, and the companion registers no stale section. The companion and starter setup ship as package resources; provider launch requires no JavaScript build or package installation. DSH's built-in system sections, working-directory project instructions, and tool schemas remain native inputs alongside the additive Houmao section.

## Accounting Contract

The pinned runtime writes physical journal version 4 to `session.v4.jsonl` when managed persistence selects `compression: none`. The collector verifies the native session header and continuity before interpreting events. Documentation examples naming v3 are not evidence for the current schema.

Consumed tokens come from settled provider attempts, not ACP context-occupancy updates. Uncached input, cache reads, cache writes, output, and reasoning preserve their native meanings. Missing buckets remain unknown; repeated samples contribute once and separately billed retries remain distinct. One managed ACP interval can cover several proven native root turns. Inherited or pre-attachment history is nonchargeable, and descendant inclusion requires explicit lineage evidence.

## Capability Limits

The selected ACP wire contract supports creation, exact resume, prompt, cancel, close, native system instructions, selected skills, and native journal accounting. `session/load`, transcript replay, deletion, fork, additional workspaces, raw keystrokes, and a live ACP wire reload are unsupported. The browser surface selected by `tui` has a separate native observation and refresh mechanism.

Gateway attach/manifest metadata exposes these capability lists under `backend_metadata.native_capabilities`, including `resource_activation: next-invocation` and `accounting_source: dsh-journal-v4`. Supported operations include native-home inspection, common-plugin observation, and home refresh. The unsupported `acp_wire_reload` operation remains separate from qualified future consumption through the generic refresh contract. Unsupported selectors fail validation before native mutation. The common view covers skills and MCP; native-special-plugin state remains agent-native. Live qualification and future boundaries come from the common observation rather than the static operation list.

## Qualification

Hermetic subprocess tests exercise protocol concurrency, failure, exact selection, and receipt binding without external accounts. Native conformance runs the actual identified DSH executable against a controlled local Messages endpoint:

```bash
HOUMAO_DSH_EXECUTABLE="$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
  pixi run pytest -q tests/integration/agents/dsh/test_native_companion.py
```

These tests establish native behavior without a paid provider. The required live DeepSeek gate separately exercises prompt/tool completion, interruption, continuation, accounting, and isolation. An unavailable self-hosted lane must be recorded as not run. Neither passing unit tests nor a version-matched executable establishes live provider acceptance.

Run all controlled native scenarios with the same explicit executable using `pixi run pytest -q tests/integration/agents/dsh`. Managed scenarios install a private tmux wrapper whose every invocation targets an explicit isolated socket. Both inherited `TMUX` and `TMUX_PANE` are cleared, and cleanup addresses only that private server. Live qualification uses the [opt-in DSH runner](../../../scripts/qualification/dsh/README.md) and an explicitly selected external env file.

`test_current_home.py::test_exact_continuation_consumes_external_skill_and_mcp_changes` executes raw and manager fixture flows with the explicit `cloud-api` case, synthetic selected credentials, and a controlled local Messages endpoint. Four ordinary turns qualify skill/MCP add, update, and remove, preserve edited role/credentials/profile/setup bytes, retain one exact conversation, and produce exactly four provider requests. `test_request_model_controls_return_to_current_native_defaults` qualifies transient model/reasoning overrides and externally edited native defaults. These tests establish selected rc.3 behavior; they do not qualify another installed version, every native plugin, or live-provider acceptance.
