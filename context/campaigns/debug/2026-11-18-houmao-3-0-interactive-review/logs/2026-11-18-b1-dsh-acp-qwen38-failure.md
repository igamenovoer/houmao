# Failure Log: Arm B1 Headless `dsh_acp` Against Self-Hosted Qwen 3.8

Date: 2026-11-18. Campaign: [Houmao 3.0 Interactive Feature Review](../debug-intent.md). Iteration Plan: [Iteration 1 Plan](../iterations/2026-11-18-plan-1-dsh-basic-functionality.md).

## Session and Environment Identity

- **Houmao version**: `3.0.0rc1` (branch `devel`), invoked via `houmao-mgr` through [iter1_dsh.py](../../../../../scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py)
- **DSH runtime**: `@deepseek-ai/dsh` `0.2.2-rc.1` (`/home/huangzhe/.bun/install/global/node_modules/@deepseek-ai/dsh/lib/bin.js`)
- **Model endpoint**: Self-hosted SGLang `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1` (`GET /v1/models` returned HTTP `200`, `max_model_len: 262144`)
- **Profile and agent**: Specialist `dsh-qwen38`, launch profile `dsh-qwen38-acp`, managed agent `dsh-qwen38-acp` (`agent_id`: `670616f3-4292-4048-ae57-cae2f7727e4a`, `runtime_session_id`: `dsh_acp-20261118-094822Z-9ad1d551`)
- **DSH setup declaration**: `adapter: pi-ai`, `protocol: openai-completions`, `route: houmao-compatible`, `context_window: 262144`, `max_output_tokens: 16384`, `reasoning: {"0": "off", "1": "low", "2": "medium", "3": "high"}`
- **Gateway and tmux**: Isolated tmux socket `tmp/houmao-30-iter1/tsock/tmux-1001/default` (`HOUMAO-dsh-qwen38-acp-1794995302724`); detached gateway on `http://127.0.0.1:41829` seeded with two Ed25519 admin keys (`/home/huangzhe/.local/state/houmao-30-iter1/keys/gateway-admin-seed.json`)

## Primary Failure 1: Default Reasoning Preset (`off`) Rejected With HTTP 400

### Observed Command and Output

Command executed while the operator was attached live to tmux:

```bash
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py send --arm b1 --text "hello"
```

This invoked `houmao-mgr --print-json agents single --agent-name dsh-qwen38-acp prompt --prompt hello` (resolved turn `turn-d1ea8de88858`).

- **Exit code**: `1` (wall-clock `2.978s`)
- **CLI stderr**: `Error: dsh_acp: DSH invocation failed: ACP request failed (-32603)`
- **Attached tmux pane output**: `[diagnostic] [warning] DSH invocation failed: ACP request failed (-32603)`
- **Persisted turn stderr** (`manifest.turn-artifacts/turn-d1ea8de88858/stderr.log`): `DSH invocation failed: ACP request failed (-32603)`

Verbatim JSON-RPC response in `manifest.turn-artifacts/turn-d1ea8de88858/provider-stdout.jsonl`:

```json
{"jsonrpc":"2.0","id":2,"result":{"sessionId":"f44254f2-474e-4ee0-a899-aec14382ef2a","configOptions":[{"id":"model","name":"Model","category":"model","type":"select","currentValue":"[\"houmao-compatible\",\"Qwen/Qwen3.8-27B-FP8\"]","options":[{"group":"houmao-compatible","name":"houmao-compatible","options":[{"value":"[\"houmao-compatible\",\"Qwen/Qwen3.8-27B-FP8\"]","name":"Qwen/Qwen3.8-27B-FP8"}]}]},{"id":"reasoning_effort","name":"Reasoning effort","category":"thought_level","type":"select","currentValue":"off","options":[{"value":"off","name":"Off"},{"value":"low","name":"Low"},{"value":"medium","name":"Medium"},{"value":"high","name":"High"}]}]}}
{"jsonrpc":"2.0","id":3,"error":{"code":-32603,"message":"Internal error: turn failed: 400: {\"object\":\"error\",\"message\":\"2 validation errors:\\n  {'type': 'literal_error', 'loc': ('body', 'reasoning_effort', \\\"literal['none','minimal','low','medium','high','xhigh','ultra','max']\\\"), 'msg': \\\"Input should be 'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'ultra' or 'max'\\\", 'input': 'off', 'ctx': {'expected': \\\"'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'ultra' or 'max'\\\"}}\\n  {'type': 'float_parsing', 'loc': ('body', 'reasoning_effort', 'constrained-float'), 'msg': 'Input should be a valid number, unable to parse string as a number', 'input': 'off'}\\n\\n  File \\\"/mnt/data/huangzhe/rsi-kernel-study/.pixi/envs/serve/lib/python3.12/site-packages/sglang/srt/entrypoints/http_server.py\\\", line 1870, in openai_v1_chat_completions\\n    POST /v1/chat/completions [{'type': 'literal_error', 'loc': ('body', 'reasoning_effort', \\\"literal['none','minimal','low','medium','high','xhigh','ultra','max']\\\"), 'msg': \\\"Input should be 'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'ultra' or 'max'\\\", 'input': 'off', 'ctx': {'expected': \\\"'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'ultra' or 'max'\\\"}}, {'type': 'float_parsing', 'loc': ('body', 'reasoning_effort', 'constrained-float'), 'msg': 'Input should be a valid number, unable to parse string as a number', 'input': 'off'}]\",\"type\":\"Bad Request\",\"param\":null,\"code\":400}"}}
```

### Root Cause Analysis

In [dsh_configuration.py](../../../../../src/houmao/agents/dsh_configuration.py#L145-L163), `DshSetup.from_mapping` requires reasoning preset `"0"` to use the literal value `"off"`. When generating the `llm-pi-ai` block of `houmao-profile.patch.json`, lines `510–515` and `575–576` emit `"reasoningEfforts": {"off": "off", "low": "low", "medium": "medium", "high": "high"}` and `"reasoning": "off"`.

Inspection of DSH's [catalog.ts](../../../../../extern/orphan/deepseek-harness/packages/llm/llm-pi-ai/src/catalog.ts#L750-L774) shows that `llm-pi-ai` treats `reasoningEfforts` values as the exact wire string sent in `reasoning_effort`, and explicitly expects `"off": null` (leaving the wire field empty unless a backend wire string such as `"none"` is intended): `"only 'off' may leave it empty"`. Because Houmao writes `"off": "off"`, DSH forwards `"reasoning_effort": "off"` in `POST /v1/chat/completions`, which SGLang rejects with HTTP `400`.

### Post-Failure State and Usage Behavior

After `turn-d1ea8de88858` failed, `houmao-mgr agents single state` returned `turn.phase: "ready"` and `last_turn.result: "known_failure"`. Authenticated `GET /v1/usage` via `GatewayClient` returned the recorded failed turn with `wall_time_ms: 1534.763` and `inputTokens: 0, outputTokens: 0, totalTokens: 0`.

## Primary Failure 2: Non-Off Reasoning Preset (`--reasoning-level 1`) Triggers Rejected `developer` Role

### Observed Command and Output

Command executed to bypass the `"off"` wire spelling error:

```bash
pixi run python scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py send --arm b1 --text "hello" --reasoning-level 1
```

This invoked `houmao-mgr --print-json agents single --agent-name dsh-qwen38-acp prompt --prompt hello --reasoning-level 1` (resolved turn `turn-4dfa2e94177b`).

- **Exit code**: `1` (wall-clock `2.813s`)
- **CLI stderr**: `Error: dsh_acp: DSH invocation failed: ACP request failed (-32603)`
- **Attached tmux pane output**: `[diagnostic] [warning] DSH invocation failed: ACP request failed (-32603)`

Verbatim JSON-RPC response in `manifest.turn-artifacts/turn-4dfa2e94177b/provider-stdout.jsonl`:

```json
{"jsonrpc":"2.0","id":2,"result":{"configOptions":[{"id":"model","name":"Model","category":"model","type":"select","currentValue":"[\"houmao-compatible\",\"Qwen/Qwen3.8-27B-FP8\"]","options":[{"group":"houmao-compatible","name":"houmao-compatible","options":[{"value":"[\"houmao-compatible\",\"Qwen/Qwen3.8-27B-FP8\"]","name":"Qwen/Qwen3.8-27B-FP8"}]}]},{"id":"reasoning_effort","name":"Reasoning effort","category":"thought_level","type":"select","currentValue":"low","options":[{"value":"off","name":"Off"},{"value":"low","name":"Low"},{"value":"medium","name":"Medium"},{"value":"high","name":"High"}]}]}}
{"jsonrpc":"2.0","id":3,"error":{"code":-32603,"message":"Internal error: turn failed: 400: {\"object\":\"error\",\"message\":\"Unexpected message role.\",\"type\":\"BadRequest\",\"param\":null,\"code\":400}"}}
```

### Direct Endpoint Verification (`curl`)

Running direct `POST http://127.0.0.1:14888/v1/chat/completions` calls against the running Qwen 3.8 server confirmed the role rejection:

- Request with `"role": "developer"`: returned `{"object":"error","message":"Unexpected message role.","type":"BadRequest","param":null,"code":400}`
- Identical request with `"role": "system"`: returned HTTP `200` with assistant reply text, `reasoning_content`, and usage (`prompt_tokens: 57`, `completion_tokens: 32`, `total_tokens: 89`, `reasoning_tokens: 27`)

### Root Cause Analysis

Per DSH's [catalog.ts](../../../../../extern/orphan/deepseek-harness/packages/llm/llm-pi-ai/src/catalog.ts#L389-L398), `pi-ai` automatically switches the system prompt message role to `"developer"` whenever `model.reasoning` is `true`, unless `compat.supportsDeveloperRole` is set to `false` (`"which pi-ai sends only to a reasoning model; false keeps system"`).

However, Houmao's `DshSetup.from_mapping` in [dsh_configuration.py](../../../../../src/houmao/agents/dsh_configuration.py#L74-L122) validates strict closed field sets (`_fields(model, {"id", "context_window", "max_output_tokens", "reasoning"}, "model")` and provider keys `{"adapter", "protocol", "route", "base_url_env", "api_key_env"}`) and emits no `compat` block in `houmao-profile.patch.json` (`llm-pi-ai`). As a result, operators have no supported configuration field in `dsh-setup.yaml` to disable `developer` role emission (`supportsDeveloperRole: false`) or tune other `pi-ai` `OpenAICompletionsCompat` switches (`supportsStore`, `thinkingFormat`, `requiresReasoningContentOnAssistantMessages`, and related fields) for SGLang or other OpenAI-compatible self-hosted servers.

## Secondary Runtime and UX Issues Observed in the Same Run

### 1. Non-Fatal DSH Permission-Preset Activation Failure

Both turns recorded the following warning in `provider-stderr.log` (`turn-d1ea8de88858` and `turn-4dfa2e94177b`):

```text
dsh: warning: 1 entry did not activate
permission (@deepseek-ai/dsh-permission-presets): Error: permission: composed sandbox and approval defaults match no preset; configure defaultPreset explicitly
    at new PermissionPresetService (file:///home/huangzhe/.bun/install/global/node_modules/@deepseek-ai/dsh-permission-presets/lib/index.js:183:42)
```

In [dsh_configuration.py](../../../../../src/houmao/agents/dsh_configuration.py#L541-L547), Houmao patches `approval: {policy: "never"}` and `sandbox-policy: {mode: "workspace-write"}` for `unattended` mode without configuring `permission.defaultPreset`. Per DSH's [permission-presets service](../../../../../extern/orphan/deepseek-harness/packages/interaction/permission-presets/src/index.ts#L219-L229), that combination resolves to `CUSTOM_PRESET` and throws during plugin initialization.

### 2. Opaque Error Reporting on CLI and Tmux Console

On both failed turns, both `houmao-mgr` stderr and the attached tmux console printed only `ACP request failed (-32603)`. Operators must manually inspect nested `manifest.turn-artifacts/turn-*/provider-stdout.jsonl` files to see the HTTP `400` payload returned by the model server.

### 3. Setup and Isolation UX Friction Leading Into Arm B1

- **Deferred agent-name validation**: `houmao-mgr project profile create --agent-name houmao-dsh-qwen38-acp` succeeded with exit code `0`; only `houmao-mgr project agents launch` later failed (`Error: Managed-agent names must not begin with reserved HOUMAO plus a separator.`).
- **Checkout rejection inside gitignored `tmp/`**: Placing `--gateway-admin-seed` or `XDG_CONFIG_HOME` inside gitignored `<repo>/tmp/` caused [gateway_access_runtime.py](../../../../../src/houmao/agents/realm_controller/gateway_access_runtime.py#L166-L173) and `_access_storage._reject_checkout()` to reject access paths because `<repo>/.git` exists on an ancestor directory (`SessionManifestError: Gateway admin seed is unavailable or invalid.` and `GatewayAccessError: Gateway access policy is unavailable.`). Keys and `XDG_CONFIG_HOME` therefore had to be placed under `~/.local/state/houmao-30-iter1/`.
- **Misattributed launch JSON details**: Launching inside `b1` used `<project>/.houmao/runtime` and `<project>/.houmao/mailbox` while stdout JSON printed `"Selected shared runtime root from HOUMAO_GLOBAL_RUNTIME_DIR."` and `"Selected shared mailbox root from HOUMAO_GLOBAL_MAILBOX_DIR."`.

## Status and Open Decision

- **Current live state**: Agent `dsh-qwen38-acp` (`b1`) remains running and idle (`turn.phase: "ready"`, gateway `http://127.0.0.1:41829`) on the isolated tmux socket.
- **Unmodified production tree**: No files under `src/houmao/` were modified during this diagnostic run.
- **Next decision**: Either test `dsh-setup.yaml` with `reasoning: false` as a non-source workaround (so `pi-ai` sets `model.reasoning = false`, keeps `"role": "system"`, and omits `reasoning_effort`), or patch [dsh_configuration.py](../../../../../src/houmao/agents/dsh_configuration.py) to emit `"off": null` for `pi-ai` `reasoningEfforts`, forward `pi-ai` `compat` fields (such as `supportsDeveloperRole: false`), and configure `permission.defaultPreset` cleanly.
