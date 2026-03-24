# Runtime-Managed Agent Public Interfaces

This page explains the runtime-managed surfaces that operators and developers actually call: how sessions are targeted, which CLI commands exist for which job, and which runtime-owned artifacts back those commands.

For the canonical filesystem layout behind generated homes, runtime session roots, nested gateway files, and workspace-local job directories, use [Agents And Runtime](../../system-files/agents-and-runtime.md).

## Mental Model

The runtime is the stable front door for a session, even though the live backend may be tmux-backed, headless, or CAO-backed.

- `start-session` creates a runtime-owned session root and persists a manifest.
- Later control commands either address that manifest directly or rediscover it from tmux session state.
- The runtime exposes several interaction paths on purpose; each exists because it makes a different guarantee.
- Optional gateway support extends this model, but it does not replace direct runtime control.

## Session Targeting

The runtime supports two targeting models.

### Manifest-path control

Pass a manifest path as `--agent-identity` when you already know the exact session root:

```bash
pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-identity <runtime-root>/sessions/claude_headless/<session-id>/manifest.json \
  --prompt "Continue from the prior answer"
```

Rules:

- Path-like `--agent-identity` values resolve directly to a manifest path.
- Manifest-path control uses the ambient agent-definition-directory precedence documented by the CLI help.
- The manifest must exist and pass schema validation before control continues.

### Name-based tmux control

Pass a tmux name such as `AGENTSYS-gpu` when you want the runtime to resolve the manifest through the live tmux session:

```bash
pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-identity AGENTSYS-gpu \
  --prompt "Summarize the current plan"
```

Rules:

- Runtime resolves the manifest path from `AGENTSYS_MANIFEST_PATH`.
- For name-based control, the effective agent-definition directory is either explicit `--agent-def-dir` or the addressed tmux session's `AGENTSYS_AGENT_DEF_DIR`.
- Name-based control does not fall back to the caller's ambient `AGENTSYS_AGENT_DEF_DIR` when the tmux pointer is stale or missing.
- Canonical agent identities are normalized into the `AGENTSYS-<name>` namespace, while live tmux session handles persist separately as `tmux_session_name`.

## Control Surface Intent

The main runtime-managed commands are intentionally different:

| Surface | What it does now | Waits for completion? | Notes |
| --- | --- | --- | --- |
| `send-prompt` | Runs the normal prompt-turn path against the resumed backend session | Yes | Advances persisted backend state after the turn |
| `send-keys` | Sends raw control input to resumed `cao_rest` sessions | No | CAO-only in the current implementation |
| `mail check/send/reply` | Prepares a structured prompt and sends it through the normal prompt-turn path | Yes | Mailbox transport is `filesystem` only in v1 |
| `attach-gateway` | Starts a live gateway sidecar for a gateway-capable session | N/A | Supported for runtime-owned `cao_rest`, `houmao_server_rest`, and runtime-owned native headless backends with implemented adapters |
| `gateway-status` | Reads live gateway status or seeded offline state | No | Falls back to `state.json` when no live gateway is attached |
| `gateway-send-prompt` | Queues a prompt through the live gateway | No | Returns an accepted queue record instead of waiting for turn completion |
| `gateway-interrupt` | Queues an interrupt through the live gateway | No | Requires a live attached gateway |
| `stop-session` | Terminates the backend session and persists updated state | No | For tmux-backed sessions, stop tries to detach any live gateway first |

## Runtime-Owned Artifacts

Runtime-managed sessions persist a durable manifest under `<runtime_root>/sessions/<backend>/<session-id>/manifest.json` and may materialize a nested `gateway/` subtree plus a workspace-local `job_dir`. Use [Agents And Runtime](../../system-files/agents-and-runtime.md) for the canonical tree, contract levels, and cleanup guidance.

Publicly relevant details:

- `manifest.json` is the runtime's durable session record.
- Tmux-backed sessions publish `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR`.
- Gateway-capable sessions publish stable attach pointers through `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`.
- Live gateway env vars appear only while a gateway instance is actually attached.

Pair-managed note:

- `attach-gateway` remains the repo runtime command surface, but the supported public pair command for `houmao_server_rest` is `houmao-srv-ctrl agents gateway attach`
- explicit pair attach resolves `<agent-ref>` through the managed-agent alias space on `houmao-server`
- current-session pair attach validates the tmux-published attach contract and uses its persisted `api_base_url` plus `session_name` as the only route target
- for pair-managed sessions, tmux window `0` remains the contractual agent surface while live gateway auxiliary windows are implementation detail except for the exact handle recorded in `gateway/run/current-instance.json`

Representative `start-session` output for a gateway-capable session:

```json
{
  "session_manifest": "/abs/path/.houmao/runtime/sessions/cao_rest/cao-rest-1/manifest.json",
  "backend": "cao_rest",
  "tool": "codex",
  "agent_identity": "AGENTSYS-gpu",
  "agent_name": "AGENTSYS-gpu",
  "agent_id": "270b8738f2f97092e572b73d19e6f923",
  "tmux_session_name": "AGENTSYS-gpu-270b87",
  "job_dir": "/abs/path/workspace/.houmao/jobs/cao-rest-1",
  "parsing_mode": "shadow_only",
  "gateway_root": "/abs/path/.houmao/runtime/sessions/cao_rest/cao-rest-1/gateway",
  "gateway_attach_path": "/abs/path/.houmao/runtime/sessions/cao_rest/cao-rest-1/gateway/attach.json"
}
```

## Interaction Path Boundaries

The runtime keeps these paths separate because they promise different things.

- `send-prompt` is the high-level prompt-turn path. It waits for readiness and completion and persists the updated backend state after the turn.
- `send-keys` is the low-level control-input path. It is meant for partial typing, menu navigation, escape delivery, or explicit key sequences that should not auto-submit.
- `mail` commands are not a separate transport client. They prepare a structured mailbox prompt and send it through the same prompt-turn path used by `send-prompt`.
- Gateway-routed commands are queue submission surfaces. They require a live attached gateway and return accepted request records instead of turn results.

## Current Implementation Scope

These docs intentionally describe the implemented behavior, not the full design space.

- Gateway capability publication exists for runtime-owned tmux-backed sessions.
- Live gateway attach supports runtime-owned `cao_rest`, `houmao_server_rest`, and runtime-owned native headless backends whose execution adapters are implemented.
- `send-keys` is implemented only for resumed `cao_rest` sessions.
- Mailbox control currently supports the filesystem transport only.
- The public managed-agent server surface for TUI-backed and server-managed headless agents lives under `/houmao/agents/*`; use [Managed-Agent API](../../managed_agent_api.md) for the server-owned request, detail-state, and gateway-route contracts.

## Source References

- [`src/houmao/agents/realm_controller/cli.py`](../../../../src/houmao/agents/realm_controller/cli.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/realm_controller/agent_identity.py`](../../../../src/houmao/agents/realm_controller/agent_identity.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../../src/houmao/agents/realm_controller/manifest.py)
- [`docs/reference/system-files/agents-and-runtime.md`](../../system-files/agents-and-runtime.md)
- [`docs/reference/realm_controller_send_keys.md`](../../realm_controller_send_keys.md)
