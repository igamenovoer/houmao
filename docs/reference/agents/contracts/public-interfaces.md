# Runtime-Managed Agent Public Interfaces

This page explains the runtime-managed surfaces that operators and developers actually call: how sessions are targeted, which CLI commands exist for which job, and which runtime-owned artifacts back those commands.

For the canonical filesystem layout behind generated homes, runtime session roots, nested gateway files, and workspace-local job directories, use [Agents And Runtime](../../system-files/agents-and-runtime.md).

## Mental Model

The runtime is the stable front door for a session, even though the live backend may be tmux-backed, headless, or server-backed.

- `houmao-mgr agents launch` or `houmao-mgr agents join` creates a runtime-owned session root and persists a manifest.
- Later control commands address that session by `--agent-name` or `--agent-id`.
- The runtime exposes several interaction paths on purpose; each exists because it makes a different guarantee.
- Optional gateway support extends this model, but it does not replace direct runtime control.

## Session Targeting

The supported operator surface targets sessions by friendly name or authoritative id.

### Name-based control

Pass the agent name you used at launch or join time:

```bash
pixi run houmao-mgr agents prompt \
  --agent-name gpu \
  --prompt "Summarize the current plan"
```

Rules:

- `--agent-name` accepts the unprefixed friendly name (e.g., `gpu`).
- The runtime normalizes names into the canonical `AGENTSYS-<name>` namespace internally.
- Name resolution checks the shared registry and the local tmux session environment.
- The manifest must exist and pass schema validation before control continues.

### Id-based control

Pass the authoritative managed-agent id when you need exact targeting:

```bash
pixi run houmao-mgr agents prompt \
  --agent-id 270b8738f2f97092e572b73d19e6f923 \
  --prompt "Continue from the prior answer"
```

Rules:

- `--agent-id` accepts the authoritative id assigned at launch or join time.
- Id-based control bypasses name normalization and goes directly to the shared registry.

## Control Surface Intent

The main `houmao-mgr agents` commands are intentionally different:

| Surface | What it does now | Waits for completion? | Notes |
| --- | --- | --- | --- |
| `agents prompt` | Runs the normal prompt-turn path against the resumed backend session | Yes | Advances persisted backend state after the turn |
| `agents gateway send-keys` | Sends raw control input through the live gateway | No | For TUI situations where prompt submission is wrong |
| `agents mail check/send/reply` | Prepares a structured prompt and sends it through the normal prompt-turn path | Yes | Mailbox transport is `filesystem` only in v1 |
| `agents gateway attach` | Starts a live gateway sidecar for a gateway-capable session | N/A | Supported for `local_interactive`, `houmao_server_rest`, and native headless backends with implemented adapters |
| `agents gateway status` | Reads live gateway status or seeded offline state | No | Falls back to `state.json` when no live gateway is attached |
| `agents gateway prompt` | Queues a prompt through the live gateway | No | Returns an accepted queue record instead of waiting for turn completion |
| `agents gateway interrupt` | Queues an interrupt through the live gateway | No | Requires a live attached gateway |
| `agents stop` | Terminates the backend session and persists updated state | No | For tmux-backed sessions, stop tries to detach any live gateway first |

## Runtime-Owned Artifacts

Runtime-managed sessions persist a durable manifest under `<runtime_root>/sessions/<backend>/<session-id>/manifest.json` and may materialize a nested `gateway/` subtree plus a workspace-local `job_dir`. Use [Agents And Runtime](../../system-files/agents-and-runtime.md) for the canonical tree, contract levels, and cleanup guidance.

Publicly relevant details:

- `manifest.json` is the runtime's durable session record.
- Tmux-backed sessions publish `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, and `AGENTSYS_AGENT_DEF_DIR`.
- `gateway/attach.json` is internal runtime bootstrap state, not part of the supported external discovery contract.
- Live gateway env vars appear only while a gateway instance is actually attached.
- For attached shared-mailbox work, the supported runtime-owned discovery path is `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live`.
- Inside the managed session, that resolver prefers current process env, falls back to the owning tmux session env, and validates the resulting live gateway binding before returning `gateway.base_url`.
- Outside the managed session, shared-registry discovery uses `runtime.manifest_path` as a locator and treats `gateway/run/current-instance.json` as the authoritative local live-gateway record once the session root is known.

Pair-managed note:

- `houmao-mgr agents gateway attach` is the supported public pair command
- explicit pair attach resolves either `--agent-name <friendly-name>` or `--agent-id <authoritative-id>` through the managed-agent selector contract on `houmao-server`
- current-session pair attach resolves the manifest through `AGENTSYS_MANIFEST_PATH` or shared-registry fallback from `AGENTSYS_AGENT_ID` and uses persisted manifest authority as the only route target
- for pair-managed sessions, tmux window `0` remains the contractual agent surface while live gateway auxiliary windows are implementation detail except for the exact handle recorded in `gateway/run/current-instance.json`

Representative `houmao-mgr agents launch` output for a gateway-capable session:

```json
{
  "session_manifest": "/abs/path/.houmao/runtime/sessions/local_interactive/li-1/manifest.json",
  "backend": "local_interactive",
  "tool": "claude",
  "agent_identity": "gpu",
  "agent_name": "gpu",
  "agent_id": "270b8738f2f97092e572b73d19e6f923",
  "tmux_session_name": "AGENTSYS-gpu-1760000123456",
  "job_dir": "/abs/path/workspace/.houmao/jobs/li-1"
}
```

## Interaction Path Boundaries

The runtime keeps these paths separate because they promise different things.

- `agents prompt` is the high-level prompt-turn path. It waits for readiness and completion and persists the updated backend state after the turn.
- `agents gateway send-keys` is the low-level control-input path. It is meant for partial typing, menu navigation, escape delivery, or explicit key sequences that should not auto-submit.
- `agents mail` commands are not a separate transport client. They prepare a structured mailbox prompt and send it through the same prompt-turn path used by `agents prompt`.
- Gateway-routed commands (`agents gateway prompt`, `agents gateway interrupt`) are queue submission surfaces. They require a live attached gateway and return accepted request records instead of turn results.

## Current Implementation Scope

These docs intentionally describe the implemented behavior, not the full design space.

- Gateway capability publication exists for runtime-owned tmux-backed sessions.
- Live gateway attach supports runtime-owned `local_interactive`, `houmao_server_rest`, and runtime-owned native headless backends whose execution adapters are implemented.
- Raw control input (`agents gateway send-keys`) is supported for `local_interactive` and `houmao_server_rest` backends.
- Mailbox control currently supports the filesystem transport only.
- The public managed-agent server surface for TUI-backed and server-managed headless agents lives under `/houmao/agents/*`; use [Managed-Agent API](../../managed_agent_api.md) for the server-owned request, detail-state, and gateway-route contracts.

## Low-Level Access

The underlying runtime module CLI still works for advanced targeting, scripting, and workflows not yet exposed by `houmao-mgr`. Use `houmao-mgr agents` for standard operator work and the raw module only when you need manifest-path control or features not yet surfaced by the managed-agent commands.

### Manifest-path control

```bash
pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-identity <runtime-root>/sessions/claude_headless/<session-id>/manifest.json \
  --prompt "Continue from the prior answer"
```

### Name-based tmux control

```bash
pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-identity AGENTSYS-gpu \
  --prompt "Summarize the current plan"
```

Rules for the low-level surface:

- Path-like `--agent-identity` values resolve directly to a manifest path.
- Name-based `--agent-identity` resolves the manifest through `AGENTSYS_MANIFEST_PATH` in the tmux session environment.
- For name-based control, the effective agent-definition directory is either explicit `--agent-def-dir` or the addressed tmux session's `AGENTSYS_AGENT_DEF_DIR`.
- Name-based control does not fall back to the caller's ambient `AGENTSYS_AGENT_DEF_DIR` when the tmux pointer is stale or missing.

## Source References

- [`src/houmao/agents/realm_controller/cli.py`](../../../../src/houmao/agents/realm_controller/cli.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/realm_controller/agent_identity.py`](../../../../src/houmao/agents/realm_controller/agent_identity.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../../src/houmao/agents/realm_controller/manifest.py)
- [`docs/reference/system-files/agents-and-runtime.md`](../../system-files/agents-and-runtime.md)
- [`docs/reference/realm_controller_send_keys.md`](../../realm_controller_send_keys.md)
