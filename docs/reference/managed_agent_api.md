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
| Gateway lifecycle, direct prompt control, raw gateway-owned TUI inspection, gateway-mediated requests, headless session control, and notifier control | `GET /houmao/agents/{agent_ref}/gateway`, `POST /houmao/agents/{agent_ref}/gateway/attach`, `POST /houmao/agents/{agent_ref}/gateway/detach`, `POST /houmao/agents/{agent_ref}/gateway/control/prompt`, `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`, `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`, `GET /houmao/agents/{agent_ref}/gateway/tui/state`, `GET /houmao/agents/{agent_ref}/gateway/tui/history`, `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`, `POST /houmao/agents/{agent_ref}/gateway/requests`, `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier` | TUI and headless | `POST /gateway/control/prompt` is immediate "send now or refuse now" control; `POST /gateway/requests` remains the queued gateway surface; `gateway/control/headless/*` is headless only |
| Pair-owned mailbox follow-up | `GET /houmao/agents/{agent_ref}/mail/status`, `POST /houmao/agents/{agent_ref}/mail/check`, `POST /houmao/agents/{agent_ref}/mail/send`, `POST /houmao/agents/{agent_ref}/mail/reply`, `POST /houmao/agents/{agent_ref}/mail/state` | TUI and headless when mailbox capability is present | These routes require pair-owned mailbox capability plus an eligible live gateway |
| Stop, native headless lifecycle, and durable turn detail | `POST /houmao/agents/{agent_ref}/stop`, `POST /houmao/agents/headless/launches`, `POST /houmao/agents/{agent_ref}/turns`, `POST /houmao/agents/{agent_ref}/interrupt`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr` | Stop applies to TUI and headless; turn detail is headless only | TUI stop reuses the managed session-delete lifecycle; durable headless turn evidence stays on `/turns/*` |

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

The canonical raw server-owned TUI inspection surface remains `/houmao/terminals/{terminal_id}/state`. When an attached gateway owns live tracking, the exact raw gateway-owned inspection surface is exposed separately through `/houmao/agents/{agent_ref}/gateway/tui/state` and `/houmao/agents/{agent_ref}/gateway/tui/history`.

For attached eligible TUI sessions, the live tracked state served here is gateway-owned and projected back through `houmao-server`. When no live gateway owns that session, the server falls back to its direct tracker.

### Headless detail

Headless detail is execution-centric and intentionally does not fabricate TUI parser concepts. It includes:

- `runtime_resumable`
- `tmux_session_live`
- `can_accept_prompt_now`
- `interruptible`
- optional `chat_session` state with `current`, `startup_default`, and gateway-owned `next_prompt_override` when that view is sourced from a live gateway-backed control plane
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

`tmux_session_live` is diagnostic only. Terminal headless status, readiness for the next managed prompt, and last-turn timestamps reconcile from authoritative active-turn state plus durable turn artifacts such as the persisted `exitcode` file. `last_turn_completion_source` remains optional diagnostic metadata when it can be recovered.

For attached healthy headless gateways, the server reads live control posture from the gateway HTTP surface before building this response. Durable turn records and turn reconciliation still remain server-owned.

## Transport-Neutral Request Submission

`POST /houmao/agents/{agent_ref}/requests` is the official prompt and interrupt surface across both transports.

The request body is typed by `request_kind`.

Prompt submission:

```json
{
  "request_kind": "submit_prompt",
  "prompt": "Summarize the current state.",
  "execution": {
    "model": {
      "name": "claude-3-7-sonnet",
      "reasoning": {
        "level": 7
      }
    }
  }
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
- TUI prompt submission prefers a healthy attached gateway and falls back to the direct transport only when no live gateway currently owns safe prompt admission for that session.
- Headless prompt submission keeps server-owned durable turn creation and turn-record authority, then prefers attached gateway admission when a healthy gateway owns live headless control.
- Headless prompt routes accept optional request-scoped `execution.model.name` plus optional `execution.model.reasoning.level` as a tool/model-specific preset index.
- Request-scoped execution overrides merge with launch-resolved defaults for the current headless turn only and never rewrite the stored manifest or later live state.
- TUI-backed prompt submission rejects any `execution` payload with HTTP `422` instead of silently dropping it.
- Discovery of a gateway does not change the public request contract; callers still use `/houmao/agents/{agent_ref}/requests`.

Observable admission and failure semantics:

- HTTP `422`: invalid request shape or other request validation failure
- HTTP `409`: headless prompt submission conflicts with an already-active managed headless turn
- HTTP `503`: the addressed managed agent is not currently operable for the requested action
- HTTP `200` with `disposition = "no_op"`: an interrupt request found no active interruptible TUI or headless work

The dedicated `POST /houmao/agents/{agent_ref}/interrupt` route still exists for headless-only best-effort interrupt delivery, but new cross-transport callers should prefer `POST /houmao/agents/{agent_ref}/requests`.

## Gateway Lifecycle, Gateway-Mediated Requests, And Notifier Control

Managed-agent gateway routes project the same gateway status, raw TUI tracking state, prompt-note provenance hook, and notifier state used by the live sidecar.

`GET /houmao/agents/{agent_ref}/gateway` returns the same `GatewayStatusV1` shape used by the direct gateway status surface. It can therefore report a seeded offline `not_attached` status even when no live sidecar exists yet.

`POST /houmao/agents/{agent_ref}/gateway/attach` is the official post-launch gateway attach action.

Important attach behavior:

- attach is idempotent when a healthy live gateway is already attached for the same managed agent
- attach accepts optional `tui_tracking_timings` with positive-second overrides for `watch_poll_interval_seconds`, `stability_threshold_seconds`, `completion_stability_seconds`, `unknown_to_stalled_timeout_seconds`, `stale_active_recovery_seconds`, and `final_stable_active_recovery_seconds`
- attach returns HTTP `409` when reconciliation is required or the underlying attach reports an already-in-use conflict
- attach returns HTTP `503` when runtime control is not resumable or gateway startup fails for an unavailable reason

For pair-managed `houmao_server_rest` sessions, operators normally reach this route through `houmao-mgr agents gateway attach`.

- explicit mode resolves either `--agent-name <friendly-name>` or `--agent-id <authoritative-id>` through the managed-agent selector contract first and then calls the managed-agent gateway attach route
- explicit tmux-session mode resolves `--target-tmux-session <tmux-session-name>` locally from that tmux session's manifest-backed authority and then uses the persisted managed-agent route target
- current-session mode runs inside the target tmux session, resolves the manifest through `HOUMAO_MANIFEST_PATH` or shared-registry fallback from `HOUMAO_AGENT_ID`, requires a `houmao_server_rest` manifest authority, and uses its persisted `gateway_authority.attach.api_base_url` plus `gateway_authority.attach.managed_agent_ref` as the authoritative route target
- current-session attach is not ready until the delegated launch has completed managed-agent registration on that same persisted server
- for same-session `houmao_server_rest` attach, tmux window `0` remains the contractual agent surface while any non-zero auxiliary gateway window remains implementation detail except for the exact live handle recorded in `gateway/run/current-instance.json`

`POST /houmao/agents/{agent_ref}/gateway/detach` removes the live sidecar when one is attached and returns the updated gateway status. The managed agent remains gateway-capable after detach because persisted manifest-backed attach authority stays in place.

`GET /houmao/agents/{agent_ref}/gateway/tui/state` proxies the raw `HoumaoTerminalStateResponse` exposed by the live gateway tracker for that managed agent.

`GET /houmao/agents/{agent_ref}/gateway/tui/history` proxies the gateway-owned bounded in-memory snapshot-history surface. This route is intentionally different from coarse managed-agent `/history` and from terminal transition `/history`: it returns recent raw tracked snapshots, capped in memory by the live gateway tracker.

`POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt` records explicit prompt-note provenance on the live gateway tracker without enqueueing a gateway request.

`POST /houmao/agents/{agent_ref}/gateway/requests` proxies live gateway `submit_prompt` and `interrupt` requests. It rejects the request explicitly when no eligible live gateway is attached instead of silently falling back to the transport-neutral `/requests` surface. For `submit_prompt`, the same optional headless-only `execution.model` shape is accepted here and rejected with HTTP `422` for TUI-backed targets.

`POST /houmao/agents/{agent_ref}/gateway/control/prompt` is the immediate "send now or refuse now" gateway-control surface. It accepts the same optional headless-only `execution.model.name` plus optional `execution.model.reasoning.level` (`>=0`, interpreted against the resolved tool/model ladder) payload as the queued `submit_prompt` surface, applies the override to exactly the current prompt admission, and rejects the request with HTTP `422` when the resolved target is TUI-backed. Partial overrides merge with launch-resolved defaults through the shared headless resolution helper.

`POST /houmao/agents/{agent_ref}/gateway/control/send-keys` proxies the live gateway raw control-input route. It carries the same `<[key-name]>` grammar and `escape_special_keys` behavior as the direct gateway `POST /v1/control/send-keys` contract.

`GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier` proxy the live gateway notifier control surface for that managed agent. These routes require a live attached gateway; they return HTTP `503` when no live gateway is currently attached or when the live gateway health check fails. The proxy preserves notifier `appendix_text` unchanged: status returns the live gateway's effective appendix, omitted fields stay omitted on `PUT`, non-empty strings replace the runtime appendix, and `appendix_text=""` clears it. Status also returns the effective `context_error_policy` and `pre_notification_context_action`. `PUT` accepts those fields to select degraded-context handling and optional pre-notification compaction through the live gateway contract.

The default documented prompt path remains `houmao-mgr agents prompt --agent-name <friendly-name> ...` over `POST /houmao/agents/{agent_ref}/requests`. That surface keeps working across direct and gateway-backed control modes. `houmao-mgr agents gateway prompt --agent-name <friendly-name> ...` is the explicit gateway-mediated alternative when live-gateway admission and queue semantics matter and the caller wants to require a live gateway instead of letting the server choose the safe backing path. `houmao-mgr agents gateway send-keys ...`, `houmao-mgr agents gateway tui ...`, and `houmao-mgr agents gateway mail-notifier ...` follow the same managed-agent selector rules outside tmux, the same explicit `--target-tmux-session` local-resolution rules from an ordinary shell, and the same manifest-first current-session resolution rules inside tmux. When a friendly name is ambiguous, operators should retry with `--agent-id <authoritative-id>`.

## Pair-Owned Mail Follow-Up

`GET /houmao/agents/{agent_ref}/mail/status`, `POST /houmao/agents/{agent_ref}/mail/check`, `POST /houmao/agents/{agent_ref}/mail/send`, `POST /houmao/agents/{agent_ref}/mail/reply`, and `POST /houmao/agents/{agent_ref}/mail/state` let callers perform mailbox follow-up through the managed-agent API without discovering the live gateway host or port.

Important boundary rules:

- these routes require pair-owned mailbox capability on the addressed managed agent
- they also require an eligible live gateway to be attached
- they coexist with `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `gateway/mail-notifier` remains background notifier configuration, while `mail/*` is the foreground mailbox-operation surface
- `POST /mail/state` is the shared foreground state-update route; in v1 it is intentionally one-way and is used to mark one processed `message_ref` read

Observable availability semantics:

- HTTP `503`: no eligible live gateway is attached, the gateway health check fails, or the managed agent does not expose pair-owned mailbox capability
- HTTP `4xx` from the live gateway is forwarded when the mailbox request shape is invalid or the requested mailbox action is rejected downstream

## Native Headless Lifecycle And Durable Turn Inspection

`POST /houmao/agents/headless/launches` launches a server-managed native headless agent.

The resolved launch request requires:

- `tool`
- `working_directory`
- `agent_def_dir`
- `brain_manifest_path`
- `role_name`

Optional launch fields:

- `agent_name`
- `agent_id`
- `headless_display_style`
- `headless_display_detail`
- `mailbox`

`headless_display_style` defaults to `plain` and `headless_display_detail` defaults to `concise` for managed headless sessions. These controls affect live bridge rendering and later CLI replay semantics; they do not change the raw provider artifacts.

Launch-time gateway flags are intentionally not part of this contract. Gateway lifecycle remains a later explicit `/gateway/attach` action.

For managed headless agents, durable post-turn inspection stays on the `/turns/*` family:

- `POST /houmao/agents/{agent_ref}/turns` accepts one managed headless prompt turn and returns a durable turn handle; it now also accepts optional `chat_session` with `mode = "auto" | "new" | "current" | "tool_last_or_new" | "exact"` and `id` required only for `mode = "exact"`. Note: `auto` and `current` are gateway-level selectors (`GatewayChatSessionSelectorMode`) resolved by the gateway before dispatch; the internal headless turn API accepts only `new`, `tool_last_or_new`, and `exact`
- `POST /houmao/agents/{agent_ref}/turns` also accepts optional request-scoped `execution.model.name` plus optional `execution.model.reasoning.level` (`>=0`, interpreted against the resolved tool/model ladder). The override is applied only to the submitted turn and does not persist as agent state.
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}` reports persisted turn status
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` returns canonical semantic headless event records with normalized assistant, action, completion, provider, and session semantics
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` and `/stderr` expose the durable raw provider artifacts directly

`/history` remains bounded and coarse even for headless agents. Durable headless detail lives on `/turns/*`, not on `/history`.

## CLI Reference

The managed-agent API routes are also reachable through the `houmao-mgr` CLI:

- [houmao-mgr agents gateway](cli/agents-gateway.md) — gateway lifecycle and explicit live-gateway request commands
- [houmao-mgr agents turn](cli/agents-turn.md) — managed headless turn submission and inspection
- [houmao-mgr agents mail](cli/agents-mail.md) — managed-agent mailbox follow-up commands

`houmao-mgr agents prompt` shares the transport-neutral `/requests` surface and accepts the same headless-only request-scoped `--model` plus optional `--reasoning-level` overrides.

## Source References

- [`src/houmao/server/app.py`](../../src/houmao/server/app.py)
- [`src/houmao/server/client.py`](../../src/houmao/server/client.py)
- [`src/houmao/server/models.py`](../../src/houmao/server/models.py)
- [`src/houmao/server/service.py`](../../src/houmao/server/service.py)
- [`tests/unit/server/test_app_contracts.py`](../../tests/unit/server/test_app_contracts.py)
- [`tests/unit/server/test_client.py`](../../tests/unit/server/test_client.py)
- [`tests/integration/server/test_managed_agent_gateway_contract.py`](../../tests/integration/server/test_managed_agent_gateway_contract.py)
