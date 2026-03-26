# Managed-Agent API

`/houmao/agents/*` is the official Houmao-owned control and inspection surface for managed agents. It unifies TUI-backed managed agents and server-managed native headless agents under one identity namespace. The route family keeps coarse orchestration state, transport-specific detail, request submission, server-owned gateway lifecycle, pair-owned mailbox follow-up, and transport-neutral stop behavior on the server, while durable headless turn artifacts stay on the headless `/turns/*` routes.

`houmao-server` is the shared coordination plane for this surface. An attached healthy gateway becomes the live per-agent control plane behind that same public API. Callers do not switch route families when a gateway attaches; the server keeps the public contracts stable and changes only the backing control path.

For the pair boundary that exposes these routes, use [Houmao Server Pair](houmao_server_pair.md). For the durable server-owned filesystem artifacts behind native headless authority and turn records, use [Houmao Server](system-files/houmao-server.md). For the live sidecar HTTP surface that the managed-agent gateway routes project or proxy, use [Agent Gateway Reference](gateway/index.md).

## Route Families

| Surface | Routes | Applies to | Notes |
| --- | --- | --- | --- |
| Discovery and summary state | `GET /houmao/agents`, `GET /houmao/agents/{agent_ref}`, `GET /houmao/agents/{agent_ref}/state`, `GET /houmao/agents/{agent_ref}/history` | TUI and headless | Summary state stays coarse and transport-neutral; history stays bounded and coarse |
| Detailed inspection | `GET /houmao/agents/{agent_ref}/state/detail` | TUI and headless | Returns one shared envelope with a transport-discriminated detail payload |
| Transport-neutral request submission | `POST /houmao/agents/{agent_ref}/requests` | TUI and headless | Official prompt and interrupt surface across both transports |
| Gateway lifecycle, gateway-mediated requests, and notifier control | `GET /houmao/agents/{agent_ref}/gateway`, `POST /houmao/agents/{agent_ref}/gateway/attach`, `POST /houmao/agents/{agent_ref}/gateway/detach`, `POST /houmao/agents/{agent_ref}/gateway/requests`, `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier` | TUI and headless | `POST /gateway/requests` proxies live gateway `submit_prompt` and `interrupt` kinds without exposing the listener endpoint |
| Pair-owned mailbox follow-up | `GET /houmao/agents/{agent_ref}/mail/status`, `POST /houmao/agents/{agent_ref}/mail/check`, `POST /houmao/agents/{agent_ref}/mail/send`, `POST /houmao/agents/{agent_ref}/mail/reply` | TUI and headless when mailbox capability is present | These routes require pair-owned mailbox capability plus an eligible live gateway |
| Stop, native headless lifecycle, and durable turn detail | `POST /houmao/agents/{agent_ref}/stop`, `POST /houmao/agents/headless/launches`, `POST /houmao/agents/{agent_ref}/turns`, `POST /houmao/agents/{agent_ref}/interrupt`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr` | Stop applies to TUI and headless; turn detail is headless only | TUI stop reuses the pair-managed session-delete lifecycle; durable headless turn evidence stays on `/turns/*` |

## Identity And Alias Resolution

`tracked_agent_id` is the canonical managed-agent identity returned by the API. Route lookups also resolve through explicit aliases when they are unique.

Supported aliases include:

- `tracked_agent_id`
- TUI `terminal_id`
- TUI `session_name`
- runtime `runtime_session_id` when present
- `agent_name`
- `agent_id`

Alias resolution applies consistently across `GET /houmao/agents/{agent_ref}`, `/state`, `/state/detail`, `/history`, `/requests`, `/stop`, `/gateway/*`, and `/mail/*`. Ambiguous aliases are rejected explicitly instead of silently selecting one managed agent.

## Summary State

`GET /houmao/agents/{agent_ref}/state` is the coarse shared state surface. It is meant for orchestration, availability checks, and quick inspection without transport-specific parsing.

The response includes:

- `identity`: transport discriminator plus managed-agent identity fields
- `availability`: coarse operability summary
- `turn`: shared current-turn posture and optional active turn id
- `last_turn`: shared coarse result summary
- `diagnostics`: structured availability or recovery details
- `mailbox`: redacted mailbox posture when the managed agent has mailbox support
- `gateway`: redacted gateway posture when gateway capability is known

Representative summary behavior:

- TUI agents expose coarse turn posture without requiring callers to interpret the raw tracked terminal payload.
- Headless agents expose coarse turn posture without requiring callers to read raw turn artifacts.
- When an attached gateway is healthy, summary and detail projection prefer the gateway HTTP read surface.
- When no live gateway is attached, or when direct fallback is the only safe option, the same routes continue projecting from direct server or runtime state.
- `/history` stays bounded and coarse for both transports; it is not a second durable per-turn store.
- TUI-backed `/history` is derived from bounded in-memory recent transitions, while headless `/history` is derived from persisted server-owned turn records.

## Detailed State

`GET /houmao/agents/{agent_ref}/state/detail` returns one shared envelope:

- `tracked_agent_id`
- `identity`
- `summary_state`
- `detail`

`detail` is discriminated by `transport`.

### TUI detail

TUI detail is a curated projection, not a second raw terminal contract. It includes:

- `terminal_id`
- `canonical_terminal_state_route`
- `canonical_terminal_history_route`
- tracked `diagnostics`
- optional `probe_snapshot`
- optional `parsed_surface`
- tracked `surface`
- `stability`

The canonical raw TUI inspection surface remains `/houmao/terminals/{terminal_id}/state`.

For attached eligible TUI sessions, the live tracked state served here is gateway-owned and projected back through `houmao-server`. When no live gateway owns that session, the server falls back to its direct tracker.

### Headless detail

Headless detail is execution-centric and intentionally does not fabricate TUI parser concepts. It includes:

- `runtime_resumable`
- `tmux_session_live`
- `can_accept_prompt_now`
- `interruptible`
- shared `turn`
- shared `last_turn`
- `active_turn_started_at_utc`
- `active_turn_interrupt_requested_at_utc`
- `last_turn_status`
- `last_turn_started_at_utc`
- `last_turn_completed_at_utc`
- `last_turn_completion_source`
- `last_turn_returncode`
- `last_turn_history_summary`
- `last_turn_error`
- optional redacted `mailbox`
- optional redacted `gateway`
- structured `diagnostics`

This route is the canonical rich inspection surface for managed headless agents when a caller needs current runtime posture without scraping `stdout`, `stderr`, or exit-code files.

For attached healthy headless gateways, the server reads live control posture from the gateway HTTP surface before building this response. Durable turn records and turn reconciliation still remain server-owned.

## Transport-Neutral Request Submission

`POST /houmao/agents/{agent_ref}/requests` is the official prompt and interrupt surface across both transports.

The request body is typed by `request_kind`.

Prompt submission:

```json
{
  "request_kind": "submit_prompt",
  "prompt": "Summarize the current state."
}
```

Interrupt submission:

```json
{
  "request_kind": "interrupt"
}
```

Accepted responses use one shared envelope:

```json
{
  "success": true,
  "tracked_agent_id": "claude-headless-1",
  "request_id": "mreq-123",
  "request_kind": "submit_prompt",
  "disposition": "accepted",
  "detail": "accepted",
  "headless_turn_id": "turn-1",
  "headless_turn_index": 1
}
```

Important rules:

- `disposition` is `accepted` when the request caused or targeted real work, and `no_op` when an interrupt request found no active interruptible work.
- `headless_turn_id` and `headless_turn_index` are present only when the accepted request created or targeted a managed headless turn.
- TUI prompt submission prefers a healthy attached gateway and falls back to the compatibility transport only when no live gateway currently owns safe prompt admission for that session.
- Headless prompt submission keeps server-owned durable turn creation and turn-record authority, then prefers attached gateway admission when a healthy gateway owns live headless control.
- Discovery of a gateway does not change the public request contract; callers still use `/houmao/agents/{agent_ref}/requests`.

Observable admission and failure semantics:

- HTTP `422`: invalid request shape or other request validation failure
- HTTP `409`: headless prompt submission conflicts with an already-active managed headless turn
- HTTP `503`: the addressed managed agent is not currently operable for the requested action
- HTTP `200` with `disposition = "no_op"`: an interrupt request found no active interruptible TUI or headless work

The dedicated `POST /houmao/agents/{agent_ref}/interrupt` route still exists for headless-only best-effort interrupt delivery, but new cross-transport callers should prefer `POST /houmao/agents/{agent_ref}/requests`.

## Gateway Lifecycle, Gateway-Mediated Requests, And Notifier Control

Managed-agent gateway routes project the same gateway status and notifier state used by the live sidecar.

`GET /houmao/agents/{agent_ref}/gateway` returns the same `GatewayStatusV1` shape used by the direct gateway status surface. It can therefore report a seeded offline `not_attached` status even when no live sidecar exists yet.

`POST /houmao/agents/{agent_ref}/gateway/attach` is the official post-launch gateway attach action.

Important attach behavior:

- attach is idempotent when a healthy live gateway is already attached for the same managed agent
- attach returns HTTP `409` when reconciliation is required or the underlying attach reports an already-in-use conflict
- attach returns HTTP `503` when runtime control is not resumable or gateway startup fails for an unavailable reason

For pair-managed `houmao_server_rest` sessions, operators normally reach this route through `houmao-mgr agents gateway attach`.

- explicit mode resolves either `--agent-name <friendly-name>` or `--agent-id <authoritative-id>` through the managed-agent selector contract first and then calls the managed-agent gateway attach route
- current-session mode runs inside the target tmux session, resolves the manifest through `AGENTSYS_MANIFEST_PATH` or shared-registry fallback from `AGENTSYS_AGENT_ID`, requires a `houmao_server_rest` manifest authority, and uses its persisted `gateway_authority.attach.api_base_url` plus `gateway_authority.attach.managed_agent_ref` as the authoritative route target
- current-session attach is not ready until the delegated launch has completed managed-agent registration on that same persisted server
- for same-session `houmao_server_rest` attach, tmux window `0` remains the contractual agent surface while any non-zero auxiliary gateway window remains implementation detail except for the exact live handle recorded in `gateway/run/current-instance.json`

`POST /houmao/agents/{agent_ref}/gateway/detach` removes the live sidecar when one is attached and returns the updated gateway status. The managed agent remains gateway-capable after detach because persisted manifest-backed attach authority stays in place.

`POST /houmao/agents/{agent_ref}/gateway/requests` proxies live gateway `submit_prompt` and `interrupt` requests. It rejects the request explicitly when no eligible live gateway is attached instead of silently falling back to the transport-neutral `/requests` surface.

`GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier` proxy the live gateway notifier control surface for that managed agent. These routes require a live attached gateway; they return HTTP `503` when no live gateway is currently attached or when the live gateway health check fails.

The default documented prompt path remains `houmao-mgr agents prompt --agent-name <friendly-name> ...` over `POST /houmao/agents/{agent_ref}/requests`. That surface keeps working across direct and gateway-backed control modes. `houmao-mgr agents gateway prompt --agent-name <friendly-name> ...` is the explicit gateway-mediated alternative when live-gateway admission and queue semantics matter and the caller wants to require a live gateway instead of letting the server choose the safe backing path. When a friendly name is ambiguous, operators should retry with `--agent-id <authoritative-id>`.

## Pair-Owned Mail Follow-Up

`GET /houmao/agents/{agent_ref}/mail/status`, `POST /houmao/agents/{agent_ref}/mail/check`, `POST /houmao/agents/{agent_ref}/mail/send`, and `POST /houmao/agents/{agent_ref}/mail/reply` let callers perform mailbox follow-up through the managed-agent API without discovering the live gateway host or port.

Important boundary rules:

- these routes require pair-owned mailbox capability on the addressed managed agent
- they also require an eligible live gateway to be attached
- they coexist with `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `gateway/mail-notifier` remains background notifier configuration, while `mail/*` is the foreground mailbox-operation surface

Observable availability semantics:

- HTTP `503`: no eligible live gateway is attached, the gateway health check fails, or the managed agent does not expose pair-owned mailbox capability
- HTTP `4xx` from the live gateway is forwarded when the mailbox request shape is invalid or the requested mailbox action is rejected downstream

## Native Headless Lifecycle And Durable Turn Inspection

`POST /houmao/agents/headless/launches` launches a server-managed native headless agent without creating a CAO session or terminal first.

The resolved launch request requires:

- `tool`
- `working_directory`
- `agent_def_dir`
- `brain_manifest_path`
- `role_name`

Optional launch fields:

- `agent_name`
- `agent_id`
- `mailbox`

Launch-time gateway flags are intentionally not part of this contract. Gateway lifecycle remains a later explicit `/gateway/attach` action.

For managed headless agents, durable post-turn inspection stays on the `/turns/*` family:

- `POST /houmao/agents/{agent_ref}/turns` accepts one managed headless prompt turn and returns a durable turn handle
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}` reports persisted turn status
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` returns structured event records derived from machine-readable output
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` and `/stderr` expose the durable artifacts directly

`/history` remains bounded and coarse even for headless agents. Durable headless detail lives on `/turns/*`, not on `/history`.

## Source References

- [`src/houmao/server/app.py`](../../src/houmao/server/app.py)
- [`src/houmao/server/client.py`](../../src/houmao/server/client.py)
- [`src/houmao/server/models.py`](../../src/houmao/server/models.py)
- [`src/houmao/server/service.py`](../../src/houmao/server/service.py)
- [`tests/unit/server/test_app_contracts.py`](../../tests/unit/server/test_app_contracts.py)
- [`tests/unit/server/test_client.py`](../../tests/unit/server/test_client.py)
- [`tests/integration/server/test_managed_agent_gateway_contract.py`](../../tests/integration/server/test_managed_agent_gateway_contract.py)
