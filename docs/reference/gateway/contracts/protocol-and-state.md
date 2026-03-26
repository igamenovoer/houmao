# Gateway Protocol And State Contracts

This page explains the current v1 gateway contracts: how attachability is published, what the live HTTP surface looks like, and which files under `gateway/` are durable versus ephemeral.

For the broader runtime-root and session-root filesystem map around this subtree, use [Agents And Runtime](../../system-files/agents-and-runtime.md).

## Mental Model

The gateway contract has two layers.

- Stable attachability tells the runtime how a session could gain a gateway.
- Live gateway bindings describe one currently running gateway instance.

Those layers are kept separate so a session can stay gateway-capable even when no sidecar is running.

## Stable Attachability

Stable attachability is published through the manifest-first contract:

- tmux discovery env:
  - `AGENTSYS_MANIFEST_PATH`
  - `AGENTSYS_AGENT_ID`
- runtime-owned manifest authority:
  - `<session-root>/manifest.json`
- derived outward-facing gateway bookkeeping:
  - `<session-root>/gateway/gateway_manifest.json`
- internal bootstrap artifacts may also exist:
  - `<session-root>/gateway/attach.json`

The supported external contract for attach, resume, and relaunch is `manifest.json` together with tmux-local discovery and shared-registry fallback. `gateway_manifest.json` remains derived publication only.

`attach.json` may still exist as internal bootstrap state for gateway startup, offline status materialization, and metadata transfer. It is not the supported public attach authority.

Representative internal bootstrap payload for a `cao_rest` session:

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

Representative `houmao_server_rest` internal bootstrap payload:

```json
{
  "schema_version": 1,
  "attach_identity": "cao-gpu",
  "backend": "houmao_server_rest",
  "tmux_session_name": "cao-gpu",
  "working_directory": "/abs/path/repo",
  "backend_metadata": {
    "api_base_url": "http://127.0.0.1:9889",
    "session_name": "cao-gpu",
    "terminal_id": "term-123",
    "parsing_mode": "shadow_only"
  },
  "manifest_path": "/abs/path/.houmao/runtime/sessions/houmao_server_rest/cao-gpu/manifest.json",
  "agent_def_dir": "/abs/path/.agentsys/agents",
  "runtime_session_id": "cao-gpu",
  "desired_host": "127.0.0.1",
  "desired_port": 43123
}
```

Current v1 scope:

- Runtime-owned tmux-backed sessions publish gateway capability.
- Live attach and request execution currently support runtime-owned `local_interactive` sessions, runtime-owned REST-backed sessions (`cao_rest`, `houmao_server_rest`), and runtime-owned native headless sessions (`claude_headless`, `codex_headless`, `gemini_headless`).
- Gateway-owned live TUI tracking routes currently support attached runtime-owned REST-backed sessions and attached runtime-owned `local_interactive` sessions. For `local_interactive`, the gateway derives tracked identity from durable internal bootstrap metadata plus manifest-backed authority and uses the runtime session id as the public `terminal_id` compatibility value because no backend-provided terminal alias exists on that path.
- Native headless internal bootstrap metadata may also carry `managed_api_base_url` and `managed_agent_ref` together when the live gateway should route requests back through `houmao-server` for a server-managed headless agent instead of resuming that headless session locally.
- `attach.json` may keep `manifest_path` for gateway internals, but the runtime-owned session manifest remains the supported persisted mailbox-capability contract for gateway mailbox routes and mail notifier support.
- `gateway_manifest.json` is derived publication only. It may expose desired listener data and `gateway_pid`, but attach and control behavior must trust `manifest.json` plus tmux or registry discovery instead of treating `gateway_manifest.json` as primary authority.

Pair-managed current-session attach rules:

- tmux-published `AGENTSYS_MANIFEST_PATH` is the preferred current-session manifest locator
- when `AGENTSYS_MANIFEST_PATH` is missing or stale, `AGENTSYS_AGENT_ID` plus the shared registry must resolve exactly one fresh `runtime.manifest_path`
- the resolved manifest must belong to the current tmux session
- the resolved manifest must use `backend = "houmao_server_rest"`
- manifest-declared pair attach authority is authoritative for current-session pair attach
- delegated pair launch may publish these stable artifacts before the matching managed-agent registration exists, so current-session attach readiness is later than capability publication

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
- `GET /v1/control/tui/state`
- `GET /v1/control/tui/history`
- `POST /v1/control/tui/note-prompt`
- `POST /v1/control/send-keys`
- `GET /v1/control/headless/state`
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
  "execution_mode": "tmux_auxiliary_window",
  "queue_depth": 0,
  "gateway_host": "127.0.0.1",
  "gateway_port": 43123,
  "gateway_tmux_window_id": "@9",
  "gateway_tmux_window_index": "2",
  "gateway_tmux_pane_id": "%9",
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
  "execution_mode": "detached_process",
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
- `execution_mode`: `detached_process` or `tmux_auxiliary_window`
- `gateway_tmux_window_id` and `gateway_tmux_window_index`: present for live `tmux_auxiliary_window` status; `gateway_tmux_window_index` must never be `"0"`
- seeded offline status carries the resolved desired execution mode even when no live gateway is attached

### `POST /v1/requests`

Current public request kinds:

- `submit_prompt`
- `interrupt`

The notifier reminder path does not add a new public request kind. The gateway may enqueue an internal `mail_notifier_prompt` record in `queue.sqlite`, but callers still control notifier behavior only through the dedicated `/v1/mail-notifier` routes.

`POST /v1/requests` stays the semantic queued prompt surface. For raw terminal mutation that must preserve exact `<[key-name]>` send-keys behavior without creating managed prompt history, use `POST /v1/control/send-keys` instead.

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

### `GET /v1/control/tui/state`

This route returns the gateway-owned live `HoumaoTerminalStateResponse` for one attached TUI-backed session.

Current availability rules:

- attached runtime-owned REST-backed sessions (`cao_rest`, `houmao_server_rest`),
- attached runtime-owned `local_interactive` sessions, and
- HTTP `422` for attached backends that do not have a gateway-owned TUI tracker.

For attached `local_interactive`, the gateway synthesizes tracked identity from internal bootstrap `runtime_session_id` metadata (falling back to `attach_identity`), keeps `terminal_aliases` empty, and therefore exposes the runtime session id as the public `terminal_id` on this route.

For attached runtime-owned `local_interactive` sessions outside `houmao-server`, repo-owned local/serverless workflow guidance now centers on this route together with `POST /v1/control/tui/note-prompt`. That pairing is the supported local inspection and explicit-input-provenance surface.

### `GET /v1/control/tui/history`

This route returns the gateway-owned live `HoumaoTerminalHistoryResponse` for the same tracked TUI session.

The `limit` query parameter defaults to `100`. Attached `local_interactive` sessions use the same tracked-session identity and `terminal_id` fallback behavior as `GET /v1/control/tui/state`.

For attached runtime-owned `local_interactive` sessions outside `houmao-server`, this route remains a compatibility surface for shared consumers rather than part of the supported repo-owned local/serverless workflow. Local operator guidance should rely on `GET /v1/control/tui/state` plus explicit prompt-note evidence instead.

### `POST /v1/control/tui/note-prompt`

This route records explicit-input evidence on the gateway-owned tracker for the attached session and returns the updated `HoumaoTerminalStateResponse`.

It accepts the same payload shape as prompt submission (`GatewayRequestPayloadSubmitPromptV1`), but only the `prompt` value is consumed by the tracker. Successful `submit_prompt` execution through `POST /v1/requests` already records this prompt note automatically, so callers only need this route when they must preserve explicit-input provenance without routing the prompt through the gateway request queue.

### `POST /v1/control/send-keys`

This route is the dedicated raw control-input surface for gateway-managed sessions. It bypasses the durable prompt queue and therefore does not claim that a managed prompt turn was submitted.

Representative request:

```json
{
  "sequence": "/model<[Enter]><[Down]>",
  "escape_special_keys": false
}
```

Representative success response:

```json
{
  "status": "ok",
  "action": "control_input",
  "detail": "Delivered control input to the local interactive session."
}
```

Current behavior:

- the route accepts the same exact `<[key-name]>` grammar as runtime `send-keys`, including optional whole-string literal escaping with `escape_special_keys=true`
- the route does not enqueue a `submit_prompt` request in `queue.sqlite`
- the route does not create gateway-owned prompt-tracking notes by itself
- for attached `local_interactive` sessions, semantic prompt submission still belongs on `POST /v1/requests` with kind `submit_prompt`, while `POST /v1/control/send-keys` remains the operator/debug raw-control path
- REST-backed and server-managed headless gateway targets currently reject this route with HTTP `422` because they do not preserve exact tmux key semantics on that path

### `GET /v1/control/headless/state`

This route returns the read-optimized `GatewayHeadlessControlStateV1` for attached native headless backends.

`local_interactive` sessions do not use this route. When attached, they expose gateway-owned live TUI state through `/v1/control/tui/*` instead.

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

- The gateway resolves the runtime-owned session manifest through internal bootstrap metadata, typically `attach.json.manifest_path`.
- It inspects `payload.launch_plan.mailbox` in that manifest to determine whether notifier behavior is supported.
- Enabling the notifier fails explicitly when the internal bootstrap state cannot resolve a readable manifest or when the manifest launch plan has no mailbox binding.
- Unread-mail truth comes from the shared gateway mailbox facade rather than mailbox-local SQLite, while notifier cadence, deduplication, last-error bookkeeping, and durable per-poll notifier audit history remain gateway-owned state in `queue.sqlite`.
- Notifier audit rows now persist shared `message_ref` and `thread_ref` values instead of transport-local mailbox ids.
- Wake-up prompts nominate exactly one actionable unread target using the oldest unread message by `created_at_utc` with a stable tie-breaker.
- The prompt includes the nominated `message_ref`, optional `thread_ref`, sender context, subject, and the remaining unread count beyond that nominated target.
- Deduplication stays keyed to the full unread set rather than the prompt text or the nominated target alone, so reminder rewrites do not create duplicate wake-ups when mailbox truth is unchanged.

Detailed inspection note:

- `GET /v1/mail-notifier` stays a compact snapshot surface.
- Detailed per-poll decision history lives in the `gateway_notifier_audit` table inside `queue.sqlite`.
- Detailed per-poll decision history can be inspected via the `gateway_notifier_audit` table inside `queue.sqlite`.

## Current-Instance Execution Handle

`run/current-instance.json` is the authoritative live execution record for one attached gateway instance.

Representative detached-process payload:

```json
{
  "schema_version": 1,
  "protocol_version": "v1",
  "pid": 424242,
  "host": "127.0.0.1",
  "port": 43123,
  "execution_mode": "detached_process",
  "managed_agent_instance_epoch": 1,
  "managed_agent_instance_id": "term-123"
}
```

Representative same-session `houmao_server_rest` payload:

```json
{
  "schema_version": 1,
  "protocol_version": "v1",
  "pid": 424242,
  "host": "127.0.0.1",
  "port": 43123,
  "execution_mode": "tmux_auxiliary_window",
  "tmux_window_id": "@2",
  "tmux_window_index": "1",
  "tmux_pane_id": "%7",
  "managed_agent_instance_epoch": 1,
  "managed_agent_instance_id": "term-123"
}
```

Current rules:

- `execution_mode = "detached_process"` must omit tmux execution-handle fields
- `execution_mode = "tmux_auxiliary_window"` must include `tmux_window_id`, `tmux_window_index`, and `tmux_pane_id`
- same-session mode must never record `tmux_window_index = "0"`
- for pair-managed `houmao_server_rest`, the recorded tmux handle is the authoritative live gateway surface for attach, detach, cleanup, and auxiliary-window recreation
- non-zero tmux windows remain non-contractual by convention; callers should rely on the recorded current-instance handle rather than window naming heuristics

## Durable And Ephemeral Gateway Artifacts

For the full runtime-managed session tree that surrounds `gateway/`, use [Agents And Runtime](../../system-files/agents-and-runtime.md). This page keeps the gateway-local artifact semantics.

Representative gateway tree:

```text
<session-root>/gateway/
  attach.json
  gateway_manifest.json
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

- `attach.json`: internal bootstrap state
- `gateway_manifest.json`: derived outward-facing gateway bookkeeping
- `protocol-version.txt`: simple version marker for local artifacts
- `desired-config.json`: desired host and port to reuse on later starts
- `state.json`: read-optimized current status contract
- `queue.sqlite`: durable queue records, the singleton gateway-owned mail notifier record, and the `gateway_notifier_audit` table that records one structured notifier decision row per enabled poll cycle
- `events.jsonl`: append-only event log
- `logs/gateway.log`: append-only line-oriented running log for lifecycle, notifier polling, busy deferrals, and execution outcomes
- `run/current-instance.json`: current process id, host, port, upstream epoch and instance id, plus same-session execution-handle fields when the gateway is hosted in a tmux auxiliary window
- `run/gateway.pid`: pidfile mirror; still written for same-session mode, but the tmux execution handle in `current-instance.json` is the authoritative stop or cleanup target for pair-managed `houmao_server_rest`

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
