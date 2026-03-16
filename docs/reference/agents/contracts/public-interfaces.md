# Runtime-Managed Agent Public Interfaces

This page explains the runtime-managed surfaces that operators and developers actually call: how sessions are targeted, which CLI commands exist for which job, and which runtime-owned artifacts back those commands.

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
  --agent-identity tmp/agents-runtime/sessions/claude_headless/<session-id>/manifest.json \
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
- Tmux-backed names are normalized into the `AGENTSYS-<name>` namespace.

## Control Surface Intent

The main runtime-managed commands are intentionally different:

| Surface | What it does now | Waits for completion? | Notes |
| --- | --- | --- | --- |
| `send-prompt` | Runs the normal prompt-turn path against the resumed backend session | Yes | Advances persisted backend state after the turn |
| `send-keys` | Sends raw control input to resumed `cao_rest` sessions | No | CAO-only in the current implementation |
| `mail check/send/reply` | Prepares a structured prompt and sends it through the normal prompt-turn path | Yes | Mailbox transport is `filesystem` only in v1 |
| `attach-gateway` | Starts a live gateway sidecar for a gateway-capable session | N/A | Live attach is implemented first for `backend=cao_rest` |
| `gateway-status` | Reads live gateway status or seeded offline state | No | Falls back to `state.json` when no live gateway is attached |
| `gateway-send-prompt` | Queues a prompt through the live gateway | No | Returns an accepted queue record instead of waiting for turn completion |
| `gateway-interrupt` | Queues an interrupt through the live gateway | No | Requires a live attached gateway |
| `stop-session` | Terminates the backend session and persists updated state | No | For tmux-backed sessions, stop tries to detach any live gateway first |

## Runtime-Owned Artifacts

Runtime-managed sessions persist state under:

```text
<runtime_root>/sessions/<backend>/<session-id>/
  manifest.json
  gateway/
    attach.json
    state.json
    desired-config.json
    queue.sqlite
    events.jsonl
```

Publicly relevant details:

- `manifest.json` is the runtime's durable session record.
- Tmux-backed sessions publish `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR`.
- Gateway-capable sessions publish stable attach pointers through `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`.
- Live gateway env vars appear only while a gateway instance is actually attached.

Representative `start-session` output for a gateway-capable session:

```json
{
  "session_manifest": "/abs/path/.houmao/runtime/sessions/cao_rest/cao-rest-1/manifest.json",
  "backend": "cao_rest",
  "tool": "codex",
  "agent_identity": "AGENTSYS-gpu",
  "agent_name": "AGENTSYS-gpu",
  "agent_id": "270b8738f2f97092e572b73d19e6f923",
  "tmux_session_name": "houmao-cao-rest-1",
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
- Live gateway attach is implemented first for `backend=cao_rest`.
- `send-keys` is implemented only for resumed `cao_rest` sessions.
- Mailbox control currently supports the filesystem transport only.
- Broader backend-extensible gateway intent exists in the models and specs, but the live adapter boundary in v1 is narrower than the attachability contract.

## Source References

- [`src/houmao/agents/realm_controller/cli.py`](../../../../src/houmao/agents/realm_controller/cli.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/realm_controller/agent_identity.py`](../../../../src/houmao/agents/realm_controller/agent_identity.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../../src/houmao/agents/realm_controller/manifest.py)
- [`docs/reference/realm_controller_send_keys.md`](../../realm_controller_send_keys.md)
