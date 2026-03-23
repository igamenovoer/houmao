# Gateway Protocol And State Contracts

This page explains the current v1 gateway contracts: how attachability is published, what the live HTTP surface looks like, and which files under `gateway/` are durable versus ephemeral.

For the broader runtime-root and session-root filesystem map around this subtree, use [Agents And Runtime](../../system-files/agents-and-runtime.md).

## Mental Model

The gateway contract has two layers.

- Stable attachability tells the runtime how a session could gain a gateway.
- Live gateway bindings describe one currently running gateway instance.

Those layers are kept separate so a session can stay gateway-capable even when no sidecar is running.

## Stable Attachability

Stable attachability is published in two ways:

- tmux env pointers:
  - `AGENTSYS_GATEWAY_ATTACH_PATH`
  - `AGENTSYS_GATEWAY_ROOT`
- strict attach contract:
  - `<session-root>/gateway/attach.json`

Representative CAO-backed attach contract:

```json
{
  "schema_version": 1,
  "attach_identity": "cao-rest-1",
  "backend": "cao_rest",
  "tmux_session_name": "AGENTSYS-gpu",
  "working_directory": "/abs/path/repo",
  "backend_metadata": {
    "api_base_url": "http://localhost:9889",
    "terminal_id": "term-123",
    "profile_name": "runtime-profile",
    "profile_path": "/abs/path/runtime-profile.md",
    "parsing_mode": "shadow_only"
  },
  "manifest_path": "/abs/path/.houmao/runtime/sessions/cao_rest/cao-rest-1/manifest.json",
  "agent_def_dir": "/abs/path/tests/fixtures/agents",
  "runtime_session_id": "cao-rest-1",
  "desired_host": "127.0.0.1",
  "desired_port": 43123
}
```

Current v1 scope:

- Runtime-owned tmux-backed sessions publish gateway capability.
- Live attach and request execution currently support runtime-owned REST-backed sessions (`cao_rest`, `houmao_server_rest`) and runtime-owned native headless sessions (`claude_headless`, `codex_headless`, `gemini_headless`).
- Native headless attach metadata may also carry `managed_api_base_url` and `managed_agent_ref` together when the live gateway should route requests back through `houmao-server` for a server-managed headless agent instead of resuming that headless session locally.
- `attach.json` keeps `manifest_path`, and that runtime-owned session manifest is the sole persisted mailbox-capability contract for gateway mailbox routes and mail notifier support.

## Live Gateway Bindings

Live bindings exist only while a gateway process is running.

Published tmux env vars:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

Important rules:

- The runtime validates these bindings structurally before trusting them.
- `GET /health` is the authoritative liveness check for the live gateway.
- A dead gateway can leave stale env behind temporarily; validation plus health probing is what cleans that up.

## HTTP Surface

Current v1 routes:

- `GET /health`
- `GET /v1/status`
- `POST /v1/requests`
- `GET /v1/mail/status`
- `POST /v1/mail/check`
- `POST /v1/mail/send`
- `POST /v1/mail/reply`
- `POST /v1/mail/state`
- `GET /v1/mail-notifier`
- `PUT /v1/mail-notifier`
- `DELETE /v1/mail-notifier`

### `GET /health`

Gateway-local liveness only:

```json
{
  "protocol_version": "v1",
  "status": "ok"
}
```

This does not mean the managed agent is available. It only means the gateway control plane is alive enough to serve its contract.

### `GET /v1/status`

Status is shared by the live HTTP route and `state.json`.

Representative live status:

```json
{
  "schema_version": 1,
  "protocol_version": "v1",
  "attach_identity": "cao-rest-1",
  "backend": "cao_rest",
  "tmux_session_name": "AGENTSYS-gpu",
  "gateway_health": "healthy",
  "managed_agent_connectivity": "connected",
  "managed_agent_recovery": "idle",
  "request_admission": "open",
  "terminal_surface_eligibility": "ready",
  "active_execution": "idle",
  "queue_depth": 0,
  "gateway_host": "127.0.0.1",
  "gateway_port": 43123,
  "managed_agent_instance_epoch": 1,
  "managed_agent_instance_id": "term-123"
}
```

Representative seeded offline status:

```json
{
  "schema_version": 1,
  "protocol_version": "v1",
  "attach_identity": "cao-rest-1",
  "backend": "cao_rest",
  "tmux_session_name": "AGENTSYS-gpu",
  "gateway_health": "not_attached",
  "managed_agent_connectivity": "unavailable",
  "managed_agent_recovery": "idle",
  "request_admission": "blocked_unavailable",
  "terminal_surface_eligibility": "unknown",
  "active_execution": "idle",
  "queue_depth": 0,
  "managed_agent_instance_epoch": 0
}
```

Current status axes:

- `gateway_health`: `healthy` or `not_attached`
- `managed_agent_connectivity`: `connected` or `unavailable`
- `managed_agent_recovery`: `idle`, `awaiting_rebind`, or `reconciliation_required`
- `request_admission`: `open`, `blocked_unavailable`, or `blocked_reconciliation`
- `terminal_surface_eligibility`: `ready`, `unknown`, or `not_ready`
- `active_execution`: `idle` or `running`

### `POST /v1/requests`

Current public request kinds:

- `submit_prompt`
- `interrupt`

The notifier reminder path does not add a new public request kind. The gateway may enqueue an internal `mail_notifier_prompt` record in `queue.sqlite`, but callers still control notifier behavior only through the dedicated `/v1/mail-notifier` routes.

Representative prompt submission:

```json
{
  "schema_version": 1,
  "kind": "submit_prompt",
  "payload": {
    "prompt": "hello"
  }
}
```

Representative accepted response:

```json
{
  "request_id": "gwreq-20260313-000000Z-deadbeef",
  "request_kind": "submit_prompt",
  "state": "accepted",
  "accepted_at_utc": "2026-03-13T00:00:00+00:00",
  "queue_depth": 1,
  "managed_agent_instance_epoch": 1
}
```

Observable current error semantics:

- malformed request payloads return HTTP `422` from FastAPI validation,
- reconciliation-blocked admission returns HTTP `409`,
- unavailable managed-agent admission returns HTTP `503`.

The broader design leaves room for more policy-driven rejection states, but the current implementation should be documented as it exists today.

### `GET /v1/mail/status`

This route reports whether the attached session exposes the shared gateway mailbox facade and which transport-backed binding it is using.

Representative response:

```json
{
  "schema_version": 1,
  "transport": "filesystem",
  "principal_id": "AGENTSYS-gpu",
  "address": "AGENTSYS-gpu@agents.localhost",
  "bindings_version": "2026-03-19T08:00:00.000001Z"
}
```

### `POST /v1/mail/check`

This is the shared mailbox read path for both filesystem-backed and `stalwart`-backed sessions.

Representative request:

```json
{
  "schema_version": 1,
  "unread_only": true,
  "limit": 10
}
```

Representative response:

```json
{
  "schema_version": 1,
  "transport": "filesystem",
  "principal_id": "AGENTSYS-gpu",
  "address": "AGENTSYS-gpu@agents.localhost",
  "unread_only": true,
  "message_count": 1,
  "unread_count": 1,
  "messages": [
    {
      "message_ref": "filesystem:msg-20260319T080000Z-a1b2c3d4e5f64798aabbccddeeff0011",
      "thread_ref": "filesystem:msg-20260319T080000Z-a1b2c3d4e5f64798aabbccddeeff0011",
      "created_at_utc": "2026-03-19T08:00:00Z",
      "subject": "Gateway unread reminder",
      "unread": true,
      "body_preview": "Hello from the shared mailbox surface",
      "sender": {
        "address": "AGENTSYS-sender@agents.localhost"
      },
      "to": [
        {
          "address": "AGENTSYS-gpu@agents.localhost"
        }
      ],
      "cc": [],
      "reply_to": [],
      "attachments": []
    }
  ]
}
```

Shared mailbox reference rules:

- `message_ref` is the stable reply target for the shared gateway mailbox surface.
- `thread_ref` is optional and opaque for callers.
- Callers must not derive behavior from transport-specific prefixes embedded in those refs.

### `POST /v1/mail/send`

This route sends a new shared mailbox message without consuming the terminal-mutation slot used by `POST /v1/requests`.

Representative request:

```json
{
  "schema_version": 1,
  "to": ["AGENTSYS-orchestrator@agents.localhost"],
  "cc": [],
  "subject": "Investigate parser drift",
  "body_content": "Hello from the gateway facade",
  "attachments": []
}
```

### `POST /v1/mail/reply`

This route replies to an existing shared mailbox message using the opaque `message_ref` returned by `check`.

Representative request:

```json
{
  "schema_version": 1,
  "message_ref": "filesystem:msg-20260319T080000Z-a1b2c3d4e5f64798aabbccddeeff0011",
  "body_content": "Reply with next steps",
  "attachments": []
}
```

### `POST /v1/mail/state`

This route applies the shared single-message read-state mutation used by bounded mailbox turns after successful processing.

Representative request:

```json
{
  "schema_version": 1,
  "message_ref": "filesystem:msg-20260319T080000Z-a1b2c3d4e5f64798aabbccddeeff0011",
  "read": true
}
```

Representative response:

```json
{
  "schema_version": 1,
  "transport": "filesystem",
  "principal_id": "AGENTSYS-gpu",
  "address": "AGENTSYS-gpu@agents.localhost",
  "message_ref": "filesystem:msg-20260319T080000Z-a1b2c3d4e5f64798aabbccddeeff0011",
  "read": true
}
```

Shared state-update rules:

- `message_ref` is the full targeting contract; callers must not derive transport-local ids from it.
- v1 supports explicit single-message read mutation only. Broader mailbox-state fields such as `starred`, `archived`, or `deleted` are rejected.
- The response is a minimal acknowledgment of the resulting read state for that shared target, not a full message envelope.
- Like the other shared mailbox routes, this route does not consume the terminal-mutation slot behind `POST /v1/requests`.

Shared mailbox route availability rules:

- `/v1/mail/*` is available only when the live gateway listener is bound to `127.0.0.1`.
- A gateway listener bound to `0.0.0.0` rejects shared mailbox routes with HTTP `503`.
- Sessions without a usable manifest-backed mailbox binding reject shared mailbox routes with HTTP `422`.
- Transport adapter failures return HTTP `502`.

### `GET|PUT|DELETE /v1/mail-notifier`

These routes manage the gateway-owned unread-mail reminder loop for mailbox-enabled sessions.

Representative enable request:

```json
{
  "schema_version": 1,
  "enabled": true,
  "interval_seconds": 60
}
```

Representative status response:

```json
{
  "schema_version": 1,
  "enabled": true,
  "interval_seconds": 60,
  "supported": true,
  "support_error": null,
  "last_poll_at_utc": "2026-03-16T09:45:00+00:00",
  "last_notification_at_utc": "2026-03-16T09:45:00+00:00",
  "last_error": null
}
```

Support contract rules:

- The gateway loads the runtime-owned session manifest referenced by `attach.json.manifest_path`.
- It inspects `payload.launch_plan.mailbox` in that manifest to determine whether notifier behavior is supported.
- Enabling the notifier fails explicitly when the attach contract has no readable manifest or when the manifest launch plan has no mailbox binding.
- Unread-mail truth comes from the shared gateway mailbox facade rather than mailbox-local SQLite, while notifier cadence, deduplication, last-error bookkeeping, and durable per-poll notifier audit history remain gateway-owned state in `queue.sqlite`.
- Notifier audit rows now persist shared `message_ref` and `thread_ref` values instead of transport-local mailbox ids.
- Wake-up prompts nominate exactly one actionable unread target using the oldest unread message by `created_at_utc` with a stable tie-breaker.
- The prompt includes the nominated `message_ref`, optional `thread_ref`, sender context, subject, and the remaining unread count beyond that nominated target.
- Deduplication stays keyed to the full unread set rather than the prompt text or the nominated target alone, so reminder rewrites do not create duplicate wake-ups when mailbox truth is unchanged.

Detailed inspection note:

- `GET /v1/mail-notifier` stays a compact snapshot surface.
- Detailed per-poll decision history lives in the `gateway_notifier_audit` table inside `queue.sqlite`.
- The runnable walkthrough for this behavior lives at [`scripts/demo/gateway-mail-wakeup-demo-pack/README.md`](../../../../scripts/demo/gateway-mail-wakeup-demo-pack/README.md), using the copied dummy-project plus lightweight `mailbox-demo` fixture shape rather than a repository worktree.

## Durable And Ephemeral Gateway Artifacts

For the full runtime-managed session tree that surrounds `gateway/`, use [Agents And Runtime](../../system-files/agents-and-runtime.md). This page keeps the gateway-local artifact semantics.

Representative gateway tree:

```text
<session-root>/gateway/
  attach.json
  protocol-version.txt
  desired-config.json
  state.json
  queue.sqlite
  events.jsonl
  logs/
    gateway.log
  run/
    current-instance.json
    gateway.pid
```

Artifact roles:

- `attach.json`: stable attachability contract
- `protocol-version.txt`: simple version marker for local artifacts
- `desired-config.json`: desired host and port to reuse on later starts
- `state.json`: read-optimized current status contract
- `queue.sqlite`: durable queue records, the singleton gateway-owned mail notifier record, and the `gateway_notifier_audit` table that records one structured notifier decision row per enabled poll cycle
- `events.jsonl`: append-only event log
- `logs/gateway.log`: append-only line-oriented running log for lifecycle, notifier polling, busy deferrals, and execution outcomes
- `run/current-instance.json`: current process id, host, port, epoch, and instance id
- `run/gateway.pid`: pidfile mirror

Operator note:

```bash
tail -f <session-root>/gateway/logs/gateway.log
```

That log is the stable tail-watch surface for the running gateway. Request lifecycle history still lives in `events.jsonl`, while detailed mail-notifier decision history now lives in `queue.sqlite.gateway_notifier_audit`. `gateway.log` remains the human-oriented running log for day-to-day observation.

## Current Implementation Notes

- `state.json` exists even before the first live attach.
- Offline status must omit live `gateway_host` and `gateway_port`.
- The gateway client connects to `127.0.0.1` even when the published host is `0.0.0.0`, because `0.0.0.0` is a bind address, not a connect address.

## Source References

- [`src/houmao/agents/realm_controller/gateway_models.py`](../../../../src/houmao/agents/realm_controller/gateway_models.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/agents/realm_controller/gateway_client.py`](../../../../src/houmao/agents/realm_controller/gateway_client.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../../src/houmao/agents/realm_controller/runtime.py)
