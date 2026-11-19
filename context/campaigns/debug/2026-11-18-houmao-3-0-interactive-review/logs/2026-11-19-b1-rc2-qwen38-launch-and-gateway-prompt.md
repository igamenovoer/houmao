# B1 RC2 Qwen 3.8 Launch and Gateway Prompt Log

Date: 2026-11-19. Campaign: [Houmao 3.0 Interactive Feature Review](../debug-intent.md). Iteration: [Iteration 1 Plan](../iterations/2026-11-18-plan-1-dsh-basic-functionality.md), Arm B1 (`dsh_acp`, self-hosted Qwen 3.8).

## Result

A fresh Houmao `3.0.0rc2` B1 agent was launched with DSH `0.2.2-rc.3` and self-hosted `Qwen/Qwen3.8-27B-FP8`. P1 and a subsequent `hello` prompt completed through the local runtime controller. A direct gateway prompt initially failed authentication, then succeeded through `POST /v1/control/prompt` with the enrolled admin key. The agent and gateway were left running, connected, healthy, and idle.

This log covers launch and basic prompt qualification only. P2 tool execution, P3 exact resume, P4 interruption, and the remaining campaign arms were not exercised in this session.

## Environment and Runtime Identity

- Houmao: `3.0.0rc2`, Git tag `v3.0.0rc2`, commit `ebae2e22`.
- DSH: `0.2.2-rc.3`, selected by prepending `tmp/dsh/npm-runtime/node_modules/.bin` to `PATH`.
- Model endpoint: `http://127.0.0.1:14888/v1`; `GET /v1/models` returned HTTP 200 with model `Qwen/Qwen3.8-27B-FP8` and `max_model_len: 262144`.
- Fresh run root: `tmp/houmao-30-iter1-rc2/`.
- Fresh access root: `~/.local/state/houmao-30-iter1-rc2/`.
- Agent: `dsh-qwen38-acp-rc2`, agent ID `562afa85-5ecf-4c28-8caa-745685bb4e6e`.
- Runtime session: `dsh_acp-20261119-050536Z-7a90f5eb`.
- tmux session: `HOUMAO-dsh-qwen38-acp-rc2-1795064736492`.
- Isolated tmux socket: `tmp/houmao-30-iter1-rc2/tsock/tmux-1001/default`.
- Gateway: `http://127.0.0.1:36127`.

The following shorthand is used in the commands below:

```bash
export RUN_ROOT=/data/huangzhe/code/houmao/tmp/houmao-30-iter1-rc2
export ACCESS_ROOT="$HOME/.local/state/houmao-30-iter1-rc2"
export PATH="/data/huangzhe/code/houmao/tmp/dsh/npm-runtime/node_modules/.bin:$PATH"
export DRIVER=scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py
```

## Key Steps

### 1. Prerequisite and Isolation Gate

```bash
pixi run python "$DRIVER" --run-root "$RUN_ROOT" --access-root "$ACCESS_ROOT" g0 \
  --qwen-base-url http://127.0.0.1:14888/v1
```

G0 passed. DSH version-policy checks accepted `0.2.2-rc.1`, `0.2.2-rc.3`, and later releases while rejecting `0.2.1` and `0.2.2-alpha.3`. The Qwen endpoint returned the expected model. The isolated tmux smoke session was created successfully, and the default server session list remained unchanged.

### 2. Fresh RC2 Profile and Launch

```bash
pixi run python "$DRIVER" --run-root "$RUN_ROOT" --access-root "$ACCESS_ROOT" setup-arm \
  --arm b1 \
  --model Qwen/Qwen3.8-27B-FP8 \
  --base-url http://127.0.0.1:14888/v1 \
  --specialist-name dsh-qwen38-rc2 \
  --profile-name dsh-qwen38-acp-rc2 \
  --agent-name dsh-qwen38-acp-rc2 \
  --with-admin-keys

pixi run python "$DRIVER" --run-root "$RUN_ROOT" --access-root "$ACCESS_ROOT" launch --arm b1
```

Project initialization, credential creation, specialist creation, profile creation, and profile inspection all returned exit code 0. The effective Qwen settings included:

```yaml
reasoning_efforts:
  off: none
  low: low
  medium: medium
  high: high
compat:
  supports_developer_role: false
```

Launch returned exit code 0 in `2.848s`. Two new admin identities were enrolled. Private keys and seed contents were not copied into this log.

### 3. Direct Attach Script

Created executable `tmp/houmao-30-iter1-rc2/attach-b1.sh` with mode `0700`; `bash -n` passed. It clears inherited `TMUX`, `TMUX_PANE`, and `TMUX_TMPDIR`, then attaches to the exact isolated socket and session.

```bash
/data/huangzhe/code/houmao/tmp/houmao-30-iter1-rc2/attach-b1.sh
```

The equivalent direct command is:

```bash
env -u TMUX -u TMUX_PANE -u TMUX_TMPDIR \
  tmux -S /data/huangzhe/code/houmao/tmp/houmao-30-iter1-rc2/tsock/tmux-1001/default \
  attach-session -t HOUMAO-dsh-qwen38-acp-rc2-1795064736492
```

### 4. Local P1 and Hello Smoke Turns

```bash
pixi run python "$DRIVER" --run-root "$RUN_ROOT" --access-root "$ACCESS_ROOT" send \
  --arm b1 --prompt-id P1

pixi run python "$DRIVER" --run-root "$RUN_ROOT" --access-root "$ACCESS_ROOT" send \
  --arm b1 --text "hello"
```

Both commands returned exit code 0. P1 completed in `5.649s` and produced:

```text
{{ITER1_LITERAL}} OK

Note: `$KEEP_LITERAL` is left as-is per instructions.
[complete] completed
```

Signed usage recorded P1 as `turn-98a78559db23`, outcome `completed`, with 12,394 input tokens, 22 output tokens, and 12,416 total tokens. The agent state returned `turn.phase: ready`, `last_turn.result: success`, and no diagnostics. No permission-preset activation or DSH invocation errors were found.

The subsequent local `hello` turn completed in `4.639s` and produced:

```text
Hello! What can I help you with?
[complete] completed
```

### 5. Gateway Health

The gateway reported:

```json
{
  "gateway_health": "healthy",
  "managed_agent_connectivity": "connected",
  "request_admission": "open",
  "active_execution": "idle",
  "queue_depth": 0,
  "gateway_host": "127.0.0.1",
  "gateway_port": 36127
}
```

Signed admin status and usage queries succeeded. Unsigned `/v1/usage` returned HTTP 401 with `error_code: proof_required`, confirming that private gateway routes required proof.

## Failures and Resolutions

### Failure 1: Existing B1 Scratch Overlay Used Removed RC1 Configuration

The first setup attempt reused `tmp/houmao-30-iter1/arms/b1/workdir`. `project init` returned 0, but `project credentials dsh add` failed with exit code 1:

```text
Error: .../.houmao/agents/tools/dsh/adapter.yaml: launch.metadata.tool_params was removed. Use launch.default_tool_params.
```

**Resolution:** The old scratch state was preserved for diagnosis. A fresh run root, `tmp/houmao-30-iter1-rc2/`, and access root, `~/.local/state/houmao-30-iter1-rc2/`, were created. G0, setup, and launch then succeeded without modifying production code or migrating the obsolete overlay in place.

### Failure 2: Gateway CLI Prompt Was Refused Without Accepted Proof

The first gateway prompt attempt used the campaign driver's gateway route:

```bash
pixi run python "$DRIVER" --run-root "$RUN_ROOT" --access-root "$ACCESS_ROOT" send \
  --arm b1 \
  --via gateway \
  --admission-policy ready-only \
  --text "Hello via gateway. Please reply briefly."
```

It returned exit code 1 in `1.165s`:

```json
{
  "action": "submit_prompt",
  "admission_policy": "ready_only",
  "detail": "Gateway proof was refused.",
  "error_code": "dispatch_failed",
  "sent": false,
  "status": "error"
}
```

No prompt was sent by this attempt. The gateway CLI did not select an accepted signer for this launch. The campaign launch enrolled admin keys with `--gateway-admin-seed`, but the CLI prompt command exposed no admin-key option and its default owner-client path did not supply the enrolled admin proof.

**Resolution:** The same enrolled `iter1-operator-admin` identity already used by the campaign's signed gateway status checks was bound explicitly to `GatewayClient`. The public endpoint descriptor supplied the owner and target incarnation. No authentication check was disabled or bypassed.

The successful client sequence was:

```python
from houmao.agents.realm_controller.gateway_models import GatewayPromptControlRequestV1
from houmao.gateway.access import GatewayClientBinding
from houmao.gateway.client import GatewayClient

base_url = "http://127.0.0.1:36127"
descriptor = GatewayClient(base_url=base_url).describe_endpoint()
binding = GatewayClientBinding(
    base_url=base_url,
    owner=descriptor.target.owner,
    purpose="admin",
    private_key_path=(
        "/home/huangzhe/.local/state/houmao-30-iter1-rc2/keys/"
        "iter1-operator-admin_ed25519"
    ),
)
client = GatewayClient(
    base_url=base_url,
    binding=binding,
    target_incarnation=descriptor.target.incarnation,
    timeout_seconds=180.0,
)
result = client.control_prompt(
    GatewayPromptControlRequestV1(
        prompt="Hello via gateway. Please reply briefly.",
        admission_policy="ready_only",
    )
)
```

The gateway accepted and dispatched the request:

```json
{
  "status": "ok",
  "action": "submit_prompt",
  "sent": true,
  "admission_policy": "ready_only",
  "detail": "Prompt dispatched."
}
```

After the turn settled, the tmux pane showed:

```text
Hello! Got your message. What would you like me to work on?
[complete] completed
```

The final signed status check showed `active_execution: idle`, `request_admission: open`, `gateway_health: healthy`, and `managed_agent_connectivity: connected`.

## Final State and Boundaries

The B1 agent remains available in its isolated tmux session, and its gateway remains available on `127.0.0.1:36127`. The default tmux server was not used for launch or teardown. No production source files, committed tests, or OpenSpec specifications were modified during these operations.
