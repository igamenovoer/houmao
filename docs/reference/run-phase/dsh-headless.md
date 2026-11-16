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

Managed configuration isolates the DSH home, shared-agent root, persistence root, selected skills, and credentials. The native DeepSeek adapter uses Messages and the explicit `DEEPSEEK_BASE_URL_ANTHROPIC` reference. Generic compatible routes separately declare their adapter, protocol, endpoint, model capacities, and reasoning metadata. A shared hostname does not establish protocol compatibility. Keys remain in local environment inputs; public provenance stores references rather than values.

### Setup Fields

The selected tool setup supplies `dsh-setup.yaml`. Packaged starter and fixture adapters both project it into the private managed home. The starter intentionally has an empty model catalog, so a contributor must provide exact model metadata before building an agent.

| Field | Required Meaning |
| --- | --- |
| `version` | `1`, the current Houmao setup format. |
| `provider.adapter` / `provider.protocol` | `deepseek` / `messages`, or `pi-ai` / `openai-completions`. These pairs are validated before native startup. |
| `provider.route` | `deepseek-official` for the native adapter; a separate lowercase route identifier for the generic adapter. |
| `provider.base_url_env` / `provider.api_key_env` | Distinct environment references from the selected credential bundle. The document contains names, never key values. |
| `models` | A nonempty exact catalog. Each entry requires `id`, positive `context_window`, positive `max_output_tokens`, and explicit `reasoning`. Output capacity cannot exceed context capacity. |
| `selected_model` | One exact declared model ID. Common launch/profile model overrides must also resolve to this catalog. |
| `models[].reasoning` | `false` for a model without reasoning, or consecutive numbered positive presets starting at `1`. Optional preset `0` maps to `off`. Positive presets name supported native efforts; common integer reasoning overrides saturate at the highest declared positive preset. |
| `skill_roots` | Optional absolute directories, added to the managed selected-skill projection. Native user-global skill discovery and skill watching are disabled. |
| `mcp_servers` | Optional ACP stdio or Streamable HTTP declarations. Stdio requires an absolute `command`, string `args`, and ordered `env` name/value entries. HTTP uses `type: http`, an absolute HTTP(S) `url`, and ordered `headers`. SSE is unsupported by the pinned ACP build. |
| `hmr` | `false`; configuration and projected assets activate at startup. |

The endpoint must implement the selected protocol. Preserve the base path required by that deployment; Houmao does not rewrite a Chat Completions endpoint into Messages or add a guessed version suffix. Credential-bearing URLs and query strings are rejected for provider endpoints.

The following is a synthetic controlled-model setup. Replace all model metadata with values qualified for the actual selected model when preparing a live account:

```yaml
version: 1
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
    reasoning: false
selected_model: controlled
skill_roots: []
mcp_servers: []
hmr: false
```

A generic compatible route instead uses the following provider block with its own explicitly declared model catalog. Its protocol is Chat Completions through the pinned pi-ai adapter:

```yaml
provider:
  adapter: pi-ai
  protocol: openai-completions
  route: controlled-generic
  base_url_env: OPENAI_BASE_URL
  api_key_env: OPENAI_API_KEY
```

The packaged `openai-compatible` setup and its matching fixture seed provide that generic route separately from the native `default` setup. Both require an explicit model catalog before launch.

### Project and Profile Preparation

In a disposable project outside the Houmao checkout, prepare a synthetic native-route credential through the maintained CLI:

```bash
houmao_checkout=/absolute/path/to/houmao
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project init
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project credentials dsh add \
  --name controlled --adapter deepseek \
  --api-key synthetic-local-only --base-url http://127.0.0.1:9000/v1
```

Write the controlled setup above into `.houmao/agents/tools/dsh/setups/default/dsh-setup.yaml`, then create the specialist and headless profile:

```bash
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project specialist create \
  --name controlled --tool dsh --credential controlled \
  --model controlled --system-prompt 'Preserve {{literal}} instructions.' --no-system-skills
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project profile create \
  --name controlled --specialist controlled --agent-name controlled --headless
pixi run --manifest-path "$houmao_checkout/pyproject.toml" houmao-mgr project agents launch \
  --profile controlled --no-gateway
```

The launch command requires the qualified DSH executable and a model server at the selected endpoint. The headless parameter of `test_dsh_project_profile_prepares_the_selected_managed_native_surface` checks the real project, credential, specialist, profile, model, and brain preparation paths with synthetic inputs, stopping at the provider-start boundary. It does not claim live-provider qualification. For the generic route, create the credential with `--adapter pi-ai` and use the corresponding generic setup. DSH adoption and native-login imports fail explicitly; managed headless launches use the `dsh_acp` backend.

### Startup Permissions and Prompt Provenance

The default `unattended` posture writes the qualified native approval policy `never` and sandbox mode `workspace-write`. Native hard denies remain enforceable. Selecting `as_is` through the specialist's `--no-unattended` option omits those permission overrides and preserves native defaults. ACP permission requests without a supported responder are rejected; headless mode does not invent an operator dialog. The selected mode is recorded with configuration provenance and carried into each per-turn preparation.

Prompt provenance records the SHA-256 digest of the complete effective launch prompt. The private role file retains the literal bytes, while public metadata contains no prompt or key values. Rebuilding with an empty prompt replaces the old managed role file, and the companion registers no stale section. The companion and starter setup ship as package resources; provider launch requires no JavaScript build or package installation. DSH's built-in system sections, working-directory project instructions, and tool schemas remain native inputs alongside the additive Houmao section.

## Accounting Contract

The pinned runtime writes physical journal version 4 to `session.v4.jsonl` when managed persistence selects `compression: none`. The collector verifies the native session header and continuity before interpreting events. Documentation examples naming v3 are not evidence for the current schema.

Consumed tokens come from settled provider attempts, not ACP context-occupancy updates. Uncached input, cache reads, cache writes, output, and reasoning preserve their native meanings. Missing buckets remain unknown; repeated samples contribute once and separately billed retries remain distinct. One managed ACP interval can cover several proven native root turns. Inherited or pre-attachment history is nonchargeable, and descendant inclusion requires explicit lineage evidence.

## Capability Limits

The selected contract supports creation, exact resume, prompt, cancel, close, native system instructions, selected skills, and native journal accounting. `session/load`, transcript replay, deletion, fork, additional workspaces, raw keystrokes, and coordinated resource refresh are unsupported. Change 01 makes no interactive support claim; the succeeding change owns the browser surface selected by `tui`.

Gateway attach/manifest metadata exposes these lists under `backend_metadata.native_capabilities`, including `resource_activation: startup-only` and `accounting_source: dsh-journal-v4`. Unsupported selectors fail validation before native mutation. Profile edits do not advertise coordinated live activation; launch a later explicitly selected invocation to apply startup inputs.

## Qualification

Hermetic subprocess tests exercise protocol concurrency, failure, exact selection, and receipt binding without external accounts. Native conformance runs the actual identified DSH executable against a controlled local Messages endpoint:

```bash
HOUMAO_DSH_EXECUTABLE="$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
  pixi run pytest -q tests/integration/agents/dsh/test_native_companion.py
```

These tests establish native behavior without a paid provider. The required live DeepSeek gate separately exercises prompt/tool completion, interruption, continuation, accounting, and isolation. An unavailable self-hosted lane must be recorded as not run. Neither passing unit tests nor a version-matched executable establishes live provider acceptance.

Run all controlled native scenarios with the same explicit executable using `pixi run pytest -q tests/integration/agents/dsh`. Managed scenarios install a private tmux wrapper whose every invocation targets an explicit isolated socket. Both inherited `TMUX` and `TMUX_PANE` are cleared, and cleanup addresses only that private server. Live qualification uses the [opt-in DSH runner](../../../scripts/qualification/dsh/README.md) and an explicitly selected external env file.
